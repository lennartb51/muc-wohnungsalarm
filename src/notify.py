"""Push-Benachrichtigung via Telegram-Bot.

Erweiterte Nachrichten:
- Smart-Title: aus extrahierten Fakten gebaut (Stadtteil · Zi · qm · Preis)
- Mietart-Detektion: kalt/warm/unklar aus Description-Indikatoren
- €/m²-Berechnung als Plausi-Marker
- Einzugsdatum-Extraktion (Datum oder "ab sofort")
- Ablöse-Extraktion (Möbel/Küchen-Ablöse, VHB, keine)
- Stellplatz/Tiefgarage-Erkennung (mit Preis falls genannt)
- Transit/Landmark-Erkennung (München U-/S-Bahn, bekannte Orte)
- Scam-Hinweis bei verdächtigen Mustern

3-stufiger Fallback gegen API-Fehler:
1. HTML mit Link-Preview
2. Plain-Text OHNE Link-Preview
3. Minimal: nur URL als Plain-Text
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import List, Optional, Tuple

import requests

from .models import Listing

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
DESCRIPTION_MAX_CHARS = 180


# ─── Mietart-Detektion ──────────────────────────────────────────────
PRICE_KALT_HINTS = (
    "nettokaltmiete", "kaltmiete", "netto kalt", "ohne nebenkosten",
    "exkl. nebenkosten", "exkl. nk", "zzgl. nk", "zzgl. nebenkosten",
    "zzgl nk", "zzgl nebenkosten",
)
PRICE_WARM_HINTS = (
    "warmmiete", "gesamtmiete", "bruttomiete", "brutto warm",
    "inkl. nk", "inkl. nebenkosten", "inkl nk", "inkl nebenkosten",
    "inklusive nebenkosten", "inklusiv nebenkosten",
    "alles inklusive", "all-in", "all in",
)


def _detect_price_type(listing: Listing) -> str:
    """'kalt', 'warm', 'beide', oder 'unklar'."""
    desc = (listing.description or "").lower()
    title = (listing.title or "").lower()
    blob = title + " " + desc

    has_kalt = any(h in blob for h in PRICE_KALT_HINTS)
    has_warm = any(h in blob for h in PRICE_WARM_HINTS)

    if has_warm and not has_kalt:
        return "warm"
    if has_kalt and not has_warm:
        return "kalt"
    if has_kalt and has_warm:
        if listing.price_cold and listing.price_warm:
            return "beide"
        return "unklar"

    if listing.price_warm and not listing.price_cold:
        return "warm"
    if listing.price_cold and not listing.price_warm:
        return "unklar"
    return "unklar"


# ─── Einzugsdatum-Extraktion ────────────────────────────────────────
# Findet Einzugstermine in vielen typischen Formaten (Feld + Fließtext).
_MONTHS = "(?:jan|feb|mär|mae|mrz|apr|mai|jun|jul|aug|sep|okt|nov|dez)[a-zä]*"


def _extract_einzug(text: str) -> Optional[str]:
    """Findet das Einzugsdatum. Returns formatted string or None."""
    if not text:
        return None
    t = text.lower()

    # Pattern 1: Field-Style "Einzugsdatum: 01.07.2026" / "Verfügbar ab 01.07.2026"
    for keyword in (r"einzugsdatum", r"einzugstermin",
                    r"verf[üu]gbar(?:keit)?", r"frei\s+ab", r"bezugsfertig",
                    r"bezugsfrei", r"beziehbar"):
        m = re.search(
            rf"{keyword}\s*[:\-]?\s*(?:ab|zum|am)?\s*"
            rf"(\d{{1,2}}\s*[./]\s*\d{{1,2}}\s*[./]\s*\d{{2,4}})",
            t,
        )
        if m:
            return f"ab {_normalize_date(m.group(1))}"

    # Pattern 2: "Einzug ab 01.07.2026" / "Einzug zum 1.7."
    m = re.search(
        r"einzug\s+(?:ab|zum|am)\s+"
        r"(\d{1,2}\s*[./]\s*\d{1,2}(?:\s*[./]\s*\d{2,4})?)",
        t,
    )
    if m:
        return f"ab {_normalize_date(m.group(1))}"

    # Pattern 3: "ab 01.07.2026" (kurz, freistehend)
    m = re.search(r"\bab\s+(\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4})\b", t)
    if m:
        return f"ab {_normalize_date(m.group(1))}"

    # Pattern 4: "verfügbar ab Juli 2026" / "frei ab August"
    m = re.search(
        rf"(?:verf[üu]gbar|frei|bezugsfrei|einzug)\s+ab\s+"
        rf"((?:anfang|mitte|ende)?\s*{_MONTHS}(?:\s+\d{{4}})?)",
        t,
    )
    if m:
        formatted = m.group(1).strip().title()
        return f"ab {formatted}"

    # Pattern 5: "ab sofort verfügbar" / "sofort beziehbar" / "ab sofort frei"
    if re.search(r"\b(?:ab\s+)?sofort\s+(?:verf[üu]gbar|frei|beziehbar|bezug|einzug)", t) or \
       re.search(r"\beinzug\s+(?:ab\s+)?sofort\b", t):
        return "ab sofort"

    # Pattern 6: standalone "ab Anfang/Mitte/Ende Monat [Jahr]"
    m = re.search(
        rf"\bab\s+(anfang|mitte|ende)\s+({_MONTHS})(?:\s+(\d{{4}}))?",
        t,
    )
    if m:
        parts = [m.group(1).capitalize(), m.group(2).capitalize()]
        if m.group(3):
            parts.append(m.group(3))
        return f"ab {' '.join(parts)}"

    # Pattern 7: standalone month-year "ab Juli 2026" (without verb prefix)
    m = re.search(rf"\bab\s+({_MONTHS}\s+\d{{4}})\b", t)
    if m:
        return f"ab {m.group(1).title()}"

    return None


def _normalize_date(s: str) -> str:
    """Normalisiert '01. 07. 2026' → '01.07.2026'."""
    return re.sub(r"\s+", "", s)


# ─── Ablöse-Extraktion ──────────────────────────────────────────────
def _extract_ablöse(text: str) -> Optional[str]:
    """Findet Möbel-/Küchen-Ablöse. Returns formatted string or None."""
    if not text:
        return None
    t = text.lower()

    # Explizit "keine Ablöse"
    if re.search(r"\b(?:keine?|ohne)\s+abl[öo]se\b", t):
        return "keine Ablöse"

    # Konkreter Betrag: "Ablöse: 2.500 €" / "Möbelablöse 1500€" / "1.500,50 €"
    m = re.search(
        r"(?:möbel[\-\s]?)?abl[öo]se(?:\s+f[üu]r\s+(?:möbel|küche|einrichtung|einbauküche))?"
        r"\s*[:\-]?\s*"
        r"(\d+(?:[.,]\d+)*)\s*(?:€|eur)",
        t,
    )
    if m:
        # Strip thousands separators (.), convert decimal (,) to (.)
        amount_str = m.group(1).replace(".", "").replace(",", ".")
        try:
            value = float(amount_str)
            if 50 <= value <= 50000:
                return f"Ablöse {value:,.0f}€".replace(",", ".")
        except ValueError:
            pass

    # "Ablöse VHB" / "nach Absprache" / "verhandelbar"
    if re.search(r"abl[öo]se\s+(?:vhb|nach\s+absprache|verhandelbar|n\.?v\.?b\.?)", t):
        return "Ablöse VHB"

    # "gegen Ablöse" ohne Betrag
    if re.search(r"\bgegen\s+abl[öo]se\b", t):
        return "Ablöse nötig"

    # Ablöse alleinstehend erwähnt
    if re.search(r"\babl[öo]se\b", t):
        return "Ablöse erwähnt"

    return None


# ─── Stellplatz/TG-Extraktion ───────────────────────────────────────
def _extract_parking(text: str) -> Optional[str]:
    """Findet Stellplatz/TG/Garage. Returns formatted string or None."""
    if not text:
        return None
    t = text.lower()

    # Explizit "kein Stellplatz" → nicht anzeigen (zu viel Lärm)
    if re.search(r"\b(?:kein|ohne)\s+(?:stellplatz|garage|parkplatz|tiefgarage)\b", t):
        return None

    # Typ erkennen (genauer zuerst)
    found_type = None
    if re.search(r"\b(?:tiefgaragen?(?:stellplatz)?|tg[\-\s]?stellplatz)\b", t):
        found_type = "Tiefgarage"
    elif re.search(r"\btg\b", t):
        found_type = "TG"
    elif re.search(r"\baußen[\-\s]?stellplatz\b", t):
        found_type = "Außenstellplatz"
    elif re.search(r"\bduplex[\-\s]?stellplatz\b", t):
        found_type = "Duplex-Stellplatz"
    elif re.search(r"\bstellplatz\b", t):
        found_type = "Stellplatz"
    elif re.search(r"\bgarage\b", t):
        found_type = "Garage"
    elif re.search(r"\bparkplatz\b", t):
        found_type = "Parkplatz"

    if not found_type:
        return None

    # Versuche Preis zu finden (im Umfeld von 50 Zeichen)
    price_str = None
    for kw_pattern in (r"tiefgarage", r"tg[\-\s]?stellplatz", r"tg\b",
                       r"stellplatz", r"garage", r"parkplatz"):
        m = re.search(
            rf"{kw_pattern}[^.]{{0,50}}?(\d{{1,4}}(?:[.,]\d{{1,3}})?)\s*(?:€|eur)",
            t,
        )
        if m:
            try:
                value = float(m.group(1).replace(",", "."))
                if 10 <= value <= 500:
                    price_str = f"{value:.0f}€/Monat"
                    break
            except ValueError:
                pass

    # Inklusive-Hinweis?
    inkl_match = re.search(
        rf"(?:tg|tiefgarage|stellplatz|garage)\s*(?:[^.]{{0,30}}?)(inklusive|inkl\.?\s+miete|in\s+miete\s+enthalten)",
        t,
    )
    if inkl_match:
        return f"{found_type} (inkl.)"

    if price_str:
        return f"{found_type} · {price_str}"
    return found_type


# ─── Transit / Landmark (München) ───────────────────────────────────
MUNICH_TRANSIT_AND_LANDMARKS = sorted([
    "Marienplatz", "Sendlinger Tor", "Karlsplatz (Stachus)", "Karlsplatz",
    "Hauptbahnhof", "Odeonsplatz", "Universität", "Münchner Freiheit",
    "Giselastraße", "Hohenzollernplatz", "Scheidplatz", "Kolumbusplatz",
    "Goetheplatz", "Harras", "Rotkreuzplatz", "Maillingerstraße",
    "Stiglmaierplatz", "Theresienstraße", "Königsplatz", "Lehel",
    "Max-Weber-Platz", "Ostbahnhof", "Donnersbergerbrücke", "Implerstraße",
    "Poccistraße", "Heimeranplatz", "Westendstraße", "Theresienwiese",
    "Fraunhoferstraße", "Müllerstraße", "Kieferngarten", "Studentenstadt",
    "Alte Heide", "Nordfriedhof", "Dietlindenstraße", "Innsbrucker Ring",
    "Karl-Preis-Platz", "Quiddestraße", "Neuperlach Süd", "Neuperlach Zentrum",
    "Trudering", "Moosach", "Hasenbergl", "Olympiazentrum", "Petuelring",
    "Oberwiesenfeld", "OEZ", "Olympia-Einkaufszentrum",
    "Frankfurter Ring", "Forstenrieder Allee", "Aidenbachstraße",
    "Klinikum Großhadern", "Holzapfelkreuth", "Mangfallplatz", "Silberhornstraße",
    "Candidplatz", "Wettersteinplatz", "Brudermühlstraße", "Kurfürstenplatz",
    "Hohenzollernstraße", "Josephsplatz", "Sendlinger-Tor-Platz",
    "Garching", "Garching-Forschungszentrum",
    "Donnersberger Brücke", "Hackerbrücke", "Isartor", "Rosenheimer Platz",
    "Pasing", "Laim", "Mittersendling", "Siemenswerke",
    "Viktualienmarkt", "Mariahilfplatz", "Englischer Garten", "Olympiapark",
    "Wittelsbacherplatz", "Promenadeplatz", "Gärtnerplatz", "Wiener Platz",
    "Münchner Hauptbahnhof", "Tierpark Hellabrunn", "Nymphenburg",
    "Schloss Nymphenburg", "BMW Welt", "Allianz Arena", "Westpark",
], key=lambda x: -len(x))


def _extract_transit(listing: Listing) -> List[str]:
    text = ((listing.description or "") + " " + (listing.title or "")).lower()
    if not text.strip():
        return []
    found = []
    for station in MUNICH_TRANSIT_AND_LANDMARKS:
        if station.lower() in text and station not in found:
            found.append(station)
            if len(found) >= 2:
                break
    return found


# ─── Scam-Detektion ─────────────────────────────────────────────────
SCAM_PATTERNS = (
    (r"\bauslandsaufenthalt\b", "Auslandsaufenthalt erwähnt"),
    (r"\beigent[üu]mer.{0,30}im ausland\b", "Eigentümer angeblich im Ausland"),
    (r"\b(vorauszahlung|anzahlung).{0,40}(notwendig|nötig|erforderlich|verlangt|überweis)\b",
        "Vorauszahlung gefordert"),
    (r"\bwestern union\b", "Western Union"),
    (r"\bkaution.{0,30}überweis", "Kaution-Überweisung gefordert"),
    (r"\b(schlüssel|key).{0,30}(per post|versand|spedition|fedex)\b",
        "Schlüssel per Post/Spedition"),
    (r"\bbesichtigung.{0,30}nicht möglich\b", "keine Besichtigung möglich"),
    (r"\babgewickelt.{0,30}(über|via|mit) airbnb\b", "Airbnb-Garantie-Trick"),
    (r"\bcryptocurrency\b|\bkrypto\b.{0,15}\bzahl", "Krypto-Zahlung"),
)


def _scam_check(listing: Listing) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    blob = ((listing.title or "") + " " + (listing.description or "")).lower()

    price = listing.price_warm or listing.price_cold
    if price and listing.size_sqm and listing.size_sqm > 10:
        p_per_sqm = price / listing.size_sqm
        if p_per_sqm < 12:
            score += 4
            reasons.append(f"€/m² extrem niedrig ({p_per_sqm:.0f}€/m² — München ø ~22€)")
        elif p_per_sqm < 15:
            score += 2
            reasons.append(f"€/m² niedrig ({p_per_sqm:.0f}€/m²)")

    for pattern, label in SCAM_PATTERNS:
        if re.search(pattern, blob):
            score += 3
            reasons.append(label)
            if len(reasons) >= 3:
                break

    if listing.description and 0 < len(listing.description.strip()) < 40:
        score += 1
        if "kaum Beschreibung" not in reasons:
            reasons.append("kaum Beschreibung")

    return min(score, 10), reasons


# ─── Smart-Title-Bau ────────────────────────────────────────────────
def _build_smart_title(listing: Listing) -> str:
    parts = []

    if listing.district:
        loc = listing.district.split(",")[0].strip()
        loc = re.sub(r"^München\s*[-–]?\s*", "", loc, flags=re.I).strip()
        loc = re.sub(r"\s*[-–,]?\s*München\s*$", "", loc, flags=re.I).strip()
        if loc:
            parts.append(loc)

    if listing.rooms:
        parts.append(f"{listing.rooms:g}-Zi")

    if listing.size_sqm:
        parts.append(f"{listing.size_sqm:.0f}m²")

    # Balkon-Status (nur wenn explizit erkannt)
    if getattr(listing, "has_balcony", None) is True:
        parts.append("Balkon")
    elif getattr(listing, "has_balcony", None) is False:
        parts.append("ohne Balkon")

    price = listing.price_warm or listing.price_cold
    if price:
        parts.append(f"{price:,.0f}€".replace(",", "."))

    if len(parts) >= 2:
        return " · ".join(parts)
    return (listing.title or "(ohne Titel)")[:90]


# ─── Telegram-Versand ───────────────────────────────────────────────
def send_telegram(listings: List[Listing], chat_id: Optional[str] = None) -> set[str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if chat_id is None:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN oder chat_id fehlen")
        return set()

    sent_uids: set[str] = set()
    for listing in listings:
        if _send_one(token, chat_id, listing):
            sent_uids.add(listing.uid)
        time.sleep(0.5)
    return sent_uids


def send_summary(text: str, chat_id: Optional[str] = None) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if chat_id is None:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    ok, err = _post(TELEGRAM_API.format(token=token), {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })
    if not ok:
        logger.warning(f"Summary-Send fehlgeschlagen: {err}")
    return ok


def _post(url: str, payload: dict) -> tuple[bool, str]:
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True, ""
        try:
            err = r.json().get("description", r.text[:300])
        except Exception:
            err = r.text[:300]
        return False, f"HTTP {r.status_code}: {err}"
    except Exception as e:
        return False, str(e)


def _send_one(token: str, chat_id: str, listing: Listing) -> bool:
    url = TELEGRAM_API.format(token=token)

    ok, err = _post(url, {
        "chat_id": chat_id,
        "text": format_message_html(listing),
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })
    if ok:
        return True
    logger.warning(f"[Telegram] HTML+Preview fehlgeschlagen ({err})")

    ok, err = _post(url, {
        "chat_id": chat_id,
        "text": format_message_plain(listing),
        "disable_web_page_preview": True,
    })
    if ok:
        return True
    logger.warning(f"[Telegram] Plain ohne Preview fehlgeschlagen ({err})")

    minimal = f"🏠 Neue Wohnung ({listing.source}): {listing.url}"
    ok, err = _post(url, {
        "chat_id": chat_id,
        "text": minimal,
        "disable_web_page_preview": True,
    })
    if ok:
        return True
    logger.error(f"[Telegram] ALLE Fallbacks fehlgeschlagen für {listing.url}: {err}")
    return False


# ─── Nachrichten-Format ─────────────────────────────────────────────
def format_message_html(l: Listing) -> str:
    """HTML-Variante mit Bold und Detailfeldern."""
    smart_title = _build_smart_title(l)
    lines = [f"🏠 <b>{_esc(smart_title)}</b>"]

    # Lage-Zeile
    location_bits = []
    if l.district:
        location_bits.append(l.district)
    if getattr(l, "postcode", None):
        location_bits.append(l.postcode)
    if l.address and (not location_bits or l.address not in location_bits[0]):
        location_bits.append(l.address)
    if location_bits:
        lines.append(f"📍 {_esc(' · '.join(str(b) for b in location_bits[:2]))}")

    # Zimmer + Größe + Features
    size_parts = []
    if l.rooms:
        size_parts.append(f"{l.rooms:g} Zi")
    if l.size_sqm:
        size_parts.append(f"{l.size_sqm:.0f} m²")
    if getattr(l, "has_balcony", None) is True:
        size_parts.append("Balkon ✓")
    if getattr(l, "has_kitchen", None) is True:
        size_parts.append("EBK ✓")
    if size_parts:
        lines.append(f"📐 {' · '.join(size_parts)}")

    # Preis mit Mietart + €/m²
    price_line = _format_price_line(l)
    if price_line:
        lines.append(price_line)

    # NEU: Einzugsdatum
    full_text = (l.title or "") + " " + (l.description or "")
    einzug = _extract_einzug(full_text)
    if einzug:
        lines.append(f"📅 Einzug: {_esc(einzug)}")

    # NEU: Stellplatz/TG
    parking = _extract_parking(full_text)
    if parking:
        lines.append(f"🚗 {_esc(parking)}")

    # NEU: Ablöse
    abloese = _extract_ablöse(full_text)
    if abloese:
        lines.append(f"💵 {_esc(abloese)}")

    # Transit
    transit = _extract_transit(l)
    if transit:
        lines.append(f"🚇 Nähe {' · '.join(transit)}")

    # Scam-Hinweis
    scam_score, scam_reasons = _scam_check(l)
    if scam_score >= 3:
        warning = "; ".join(scam_reasons[:2])
        lines.append(f"⚠️ <i>Vorsicht: {_esc(warning)}</i>")

    # Kurz-Description
    desc = _short_description(l)
    if desc:
        lines.append(f"\n💬 <i>{_esc(desc)}</i>")

    # Original-Titel als Referenz
    if l.title and l.title != smart_title and not _looks_redundant(l.title, smart_title):
        orig = l.title[:90]
        if len(l.title) > 90:
            orig += "…"
        lines.append(f"📝 <i>Inserat-Titel: {_esc(orig)}</i>")

    # Source + Link
    lines.append(f"\n🏷 {_esc(l.source)}")
    lines.append(f'<a href="{_esc(l.url)}">→ Original ansehen</a>')
    return "\n".join(lines)


def format_message_plain(l: Listing) -> str:
    """Plain-Text-Variante (kein parse_mode)."""
    smart_title = _build_smart_title(l)
    lines = [f"🏠 {smart_title}"]

    location_bits = []
    if l.district:
        location_bits.append(l.district)
    if getattr(l, "postcode", None):
        location_bits.append(l.postcode)
    if location_bits:
        lines.append(f"📍 {' · '.join(str(b) for b in location_bits[:2])}")

    size_parts = []
    if l.rooms:
        size_parts.append(f"{l.rooms:g} Zi")
    if l.size_sqm:
        size_parts.append(f"{l.size_sqm:.0f} m²")
    if getattr(l, "has_balcony", None) is True:
        size_parts.append("Balkon ✓")
    if getattr(l, "has_kitchen", None) is True:
        size_parts.append("EBK ✓")
    if size_parts:
        lines.append(f"📐 {' · '.join(size_parts)}")

    price = l.price_warm or l.price_cold
    if price:
        price_type = _detect_price_type(l)
        label_map = {"kalt": "kalt", "warm": "warm", "beide": "kalt+warm",
                     "unklar": "Mietart unklar"}
        label = label_map.get(price_type, price_type)
        line = f"💰 {price:,.0f} € {label}".replace(",", ".")
        if l.size_sqm:
            line += f" · {price / l.size_sqm:.0f}€/m²"
        lines.append(line)

    full_text = (l.title or "") + " " + (l.description or "")
    einzug = _extract_einzug(full_text)
    if einzug:
        lines.append(f"📅 Einzug: {einzug}")
    parking = _extract_parking(full_text)
    if parking:
        lines.append(f"🚗 {parking}")
    abloese = _extract_ablöse(full_text)
    if abloese:
        lines.append(f"💵 {abloese}")

    transit = _extract_transit(l)
    if transit:
        lines.append(f"🚇 Nähe {' · '.join(transit)}")

    scam_score, scam_reasons = _scam_check(l)
    if scam_score >= 3:
        warning = "; ".join(scam_reasons[:2])
        lines.append(f"⚠️ Vorsicht: {warning}")

    lines.append(f"\n🏷 {l.source}")
    lines.append(l.url)
    return "\n".join(lines)


# ─── Hilfsfunktionen ────────────────────────────────────────────────
def _format_price_line(l: Listing) -> Optional[str]:
    price_cold = l.price_cold
    price_warm = l.price_warm
    price_type = _detect_price_type(l)

    facts = []
    if price_type == "beide" and price_cold and price_warm:
        facts.append(f"<b>{price_cold:,.0f} €</b> kalt".replace(",", "."))
        facts.append(f"<b>{price_warm:,.0f} €</b> warm".replace(",", "."))
    elif price_type == "warm" and (price_warm or price_cold):
        p = price_warm or price_cold
        facts.append(f"<b>{p:,.0f} €</b> warm".replace(",", "."))
    elif price_type == "kalt" and price_cold:
        facts.append(f"<b>{price_cold:,.0f} €</b> kalt".replace(",", "."))
    elif price_type == "unklar" and (price_cold or price_warm):
        p = price_warm or price_cold
        facts.append(f"<b>{p:,.0f} €</b> <i>(Mietart unklar — bitte prüfen)</i>".replace(",", "."))
    elif price_cold:
        facts.append(f"<b>{price_cold:,.0f} €</b>".replace(",", "."))

    if not facts:
        return None

    price_for_calc = price_warm or price_cold
    if price_for_calc and l.size_sqm and l.size_sqm > 10:
        per_sqm = price_for_calc / l.size_sqm
        facts.append(f"{per_sqm:.0f}€/m²")

    return f"💰 {' · '.join(facts)}"


def _short_description(l: Listing) -> Optional[str]:
    if not l.description:
        return None
    desc = l.description.strip()
    if len(desc) < 30:
        return None
    if len(desc) > DESCRIPTION_MAX_CHARS:
        desc = desc[:DESCRIPTION_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return desc


def _looks_redundant(original: str, smart: str) -> bool:
    if not original:
        return True
    o = original.lower()
    generic_only_pattern = r"^\s*(\d+[\.,]?\d*\s*€?|\d+\s*zi|\d+\s*m²|wohnung|miete|kalt|warm|\s)+\s*$"
    if re.fullmatch(generic_only_pattern, o):
        return True
    return False


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def format_message(l: Listing) -> str:
    return format_message_html(l)
