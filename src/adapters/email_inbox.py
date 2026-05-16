"""Email-Inbox-Adapter.

Liest ungelesene Mails aus einer dedizierten IMAP-Inbox (typisch: Gmail mit
App-Password) und extrahiert Wohnungs-Inserate daraus. Setzt auf der gleichen
Block-Detection-Logik wie der GenericTextAdapter auf — wenn eine Mail HTML
enthält das wie ein Listing aussieht (≥2 von m²/€/Zimmer-Indikatoren, kein
VERMIETET-Status), wird's als Listing aufgenommen.

ZUSÄTZLICH: Links auf bekannte Listing-Portale (ImmoScout, Immowelt, etc.)
werden als separate Listing-Stubs erstellt, damit der User sie direkt
anklicken kann.

Aktivierung: nur wenn EMAIL_IMAP_USER + EMAIL_IMAP_PASSWORD als Env-Var
gesetzt sind. Ohne Credentials läuft der Adapter no-op und blockt den Run nicht.
"""
from __future__ import annotations

import email
import hashlib
import imaplib
import logging
import os
import re
from email.header import decode_header, make_header
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ..models import Listing
from .base import Adapter, parse_rooms, parse_sqm
from .generic import (
    _ADDRESS_RE,
    _STATUS_TAKEN_RE,
    _extract_apartment_sqm,
    _extract_price,
    _extract_price_warm,
    _filter_nested,
    _looks_like_listing,
)

logger = logging.getLogger(__name__)


# Domains deren Links wir als Listing-Stub aufnehmen.
# Tracking-Wrapper (z.B. ImmoScout email-tracking-links) werden zum Glück
# meist auf die echte Domain umgeleitet, sodass die URL im Telegram funktioniert.
LISTING_DOMAINS = {
    "immobilienscout24.de", "immowelt.de", "kleinanzeigen.de",
    "wg-gesucht.de", "wohnungsboerse.net", "immobilo.de",
    "ohne-makler.net", "immobilienmarkt.sueddeutsche.de",
    "immobilienmarkt.faz.net", "zuhause.idowa.de",
    "engelvoelkers.com", "von-poll.com", "pandion-service.de",
    "munich-property.de", "leg-wohnen.de",
    # Hausverwaltungen die per Newsletter Listings versenden
    "wagnis.org", "ebm-muenchen.de", "kswm.de", "wsb-bayern.de",
    "suedhausbau.de", "gid-muenchen.de", "monachia.de",
}

# Pfad-Patterns die EINDEUTIG auf ein Listing-Detail zeigen.
# Schützt vor Saved-Search/Profile/Login-URLs in Newsletter-Mails.
LISTING_URL_PATH_PATTERNS = [
    "/expose/", "/exposes/", "/objekt/", "/objekte/",
    "/inserat/", "/anzeige/", "/s-anzeige/",
    "/listing/", "/listings/",
    "/wohnung/", "/wohnungen/", "/wohnungsangebote/",
    "/mietangebote/", "/mietangebot/", "/mietobjekte/",
    "/freie-wohnungen", "/property/", "/properties/",
    "/immobilie/", "/immobilien-angebot",
    "/ad/", "/p/",  # Kurze IDs bei manchen Portalen
]

# Tracking- & Marketing-URL-Anker, die wir IGNORIEREN
LINK_SKIP_PATTERNS = [
    "/unsubscribe", "/abmelden", "/login", "/profile", "/preferences",
    "/account", "/datenschutz", "/impressum", "/agb",
    "/savedsearch", "/saved-search", "/suchauftrag", "/suche-bearbeiten",
    "/email/", "/newsletter",
    "click.email", "tracker", "pixel.gif",
]

# Erkennt Newsletter-Boilerplate-Blöcke die zufällig m²/€ enthalten
# (Such-Kriterien, Suchauftrag-Management, Footer mit Konto-Details).
# Diese sind KEINE echten Inserate.
_NEWSLETTER_BOILERPLATE_RE = re.compile(
    r"\b("
    # Suchauftrag-Management
    r"suchauftrag|gespeicherte\s+suche|gespeicherten\s+suche|"
    r"suchkriterien|gezeichnetes?\s+suchgebiet|"
    r"passe\s+deine|aktuelle\s+suche|deine\s+suche|"
    r"ohne\s+tauschwohnungen?|"
    # E-Mail-Verwaltung
    r"benachrichtigung(?:en)?\s+(?:einstellen|deaktivieren|verwalten)|"
    r"abmelden|unsubscribe|abbestellen|abo\s+kündigen|"
    r"newsletter\s+(?:einstellungen|verwalten|abbestellen)|"
    r"e-mail-einstellungen|email\s+preferences|"
    # Standard-Footer
    r"presse|impressum|datenschutz"
    r")\b",
    re.IGNORECASE,
)

# Erkennt WOHNUNGSGESUCHE (Leute die eine Wohnung suchen, statt anbieten).
# Wichtig für Newsletter wie Budenschleuder, die fast nur Gesuche enthalten.
# Gesuche haben oft m²/€/Zimmer-Indikatoren ("suche 70qm bis 1500€") und
# würden sonst fälschlich als Listings erkannt werden.
_HOUSING_REQUEST_RE = re.compile(
    r"(?:"
    # Direkte Gesuch-Schlüsselwörter
    r"\bwohnungs.?gesuch\b|\bwohnung\s+gesucht\b|"
    r"\bgesuch[:!\s]|\bgesucht[:!\s\.]|"
    r"\bdringend\s+gesucht\b|\bsucht?\s+dringend\b|"
    # "Sucht/Suchen ab X" — zeitlicher Bezug, sehr typisch für Gesuche
    r"\bsucht\s+ab\s+\w+|\bsuchen\s+ab\s+\w+|"
    # "Wir suchen:" / "Ich suche:" — Doppelpunkt-Varianten
    r"\bwir\s+suchen\s*[:!]|\bich\s+suche\s*[:!]|"
    # "X sucht..." mit Subjekt
    r"\b(?:duo|paar|familie|wg|leute|student\w*|ehepaar|j[üu]nges?\s+\w+)\s+sucht\b|"
    r"\bsucht\s+(?:eine?|nach|noch)\s+\w*\s*(?:wohnung|zimmer|zuhause|\d.?zimmer|1.5|2.5|3.5)\b|"
    r"\bsucht\s+(?:eine?\s+)?(?:nette?|sch[öo]ne?|gem[üu]tliche?|kleine?|gro[ßs]e?|helle?|ruhige?)\s+\w*\s*(?:wohnung|zimmer)|"
    # Erste-Person-Suche
    r"\b(?:wir|ich)\s+suche[nt]?\s+(?:eine|ein|nach|aktuell|dringend|seit|ab\s+|noch|gerade)|"
    r"\bauf\s+der\s+suche\s+nach\s+(?:einer|einem|meiner|unserer|der|dem)|"
    # Höflichkeitsformeln am Ende eines Gesuchs (sehr typisch)
    r"\bfreue\s+mich\s+(?:[üu]ber|auf|sehr)|"
    r"\bfreuen\s+uns\s+(?:[üu]ber|auf|sehr)|"
    r"\btipps?\s+gerne\s+an\b|\banfragen\s+bitte\s+an\b|"
    r"\bhinweise?\s+(?:gerne|bitte)\s+an\b|"
    r"\bunterlagen\s+(?:wie|liegen|stelle|bei\s+bedarf|kann\s+ich)|"
    r"\bbei\s+(?:fragen|interesse|hinweisen)\s+(?:bitte|gerne)\s+(?:melden|kontakt)|"
    r"\bschufa.{0,50}(?:bei\s+bedarf|liegen\s+vor|gerne)"
    r")",
    re.IGNORECASE,
)


class EmailInboxAdapter(Adapter):
    """Liest ungelesene Mails per IMAP und extrahiert Listings.

    Wichtig: Mails werden nach erfolgreichem Processing als 'gelesen' markiert,
    damit sie nicht beim nächsten Run nochmal verarbeitet werden.
    """
    name = "Email Inbox"
    rate_limit_seconds = 0.0  # IMAP rate-limit handhabt Gmail selbst

    # Hard limit pro Run, damit eine volle Inbox uns nicht ins Workflow-Timeout reisst
    MAX_MAILS_PER_RUN = 100

    def __init__(self):
        super().__init__()
        self.host = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.user = os.environ.get("EMAIL_IMAP_USER")
        self.password = os.environ.get("EMAIL_IMAP_PASSWORD")
        # Leerzeichen aus App-Password rausfiltern (Gmail zeigt sie mit Spaces an)
        if self.password:
            self.password = self.password.replace(" ", "")

    @property
    def configured(self) -> bool:
        return bool(self.user and self.password)

    def fetch(self) -> Iterable[Listing]:
        if not self.configured:
            logger.info(f"[{self.name}] EMAIL_IMAP_USER/PASSWORD fehlen, übersprungen")
            return

        try:
            conn = imaplib.IMAP4_SSL(self.host)
            conn.login(self.user, self.password)
        except imaplib.IMAP4.error as e:
            logger.warning(f"[{self.name}] IMAP-Login failed: {e}")
            return
        except Exception as e:
            logger.warning(f"[{self.name}] IMAP-Verbindung failed: {e}")
            return

        try:
            conn.select("INBOX")
            status, data = conn.search(None, "UNSEEN")
            if status != "OK" or not data or not data[0]:
                logger.info(f"[{self.name}] Keine ungelesenen Mails")
                return

            uids = data[0].split()[: self.MAX_MAILS_PER_RUN]
            logger.info(f"[{self.name}] {len(uids)} ungelesene Mails")

            for uid in uids:
                try:
                    yield from self._process_mail(conn, uid)
                except Exception as e:
                    logger.warning(f"[{self.name}] Mail {uid!r} Fehler: {e}")
                finally:
                    # IMMER als gelesen markieren — egal ob Listings extrahiert
                    # wurden oder die Mail leer/fehlerhaft war. Sonst greifen
                    # wir die selben Mails endlos.
                    try:
                        conn.store(uid, "+FLAGS", "\\Seen")
                    except Exception as e:
                        logger.warning(f"[{self.name}] Konnte Mail {uid!r} "
                                       f"nicht als gelesen markieren: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
            try:
                conn.logout()
            except Exception:
                pass

    def _process_mail(self, conn, uid) -> Iterable[Listing]:
        status, data = conn.fetch(uid, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            return

        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        subject = _decode(msg.get("Subject", ""))
        from_addr = _decode(msg.get("From", ""))

        body_html, body_plain = _extract_body(msg)

        # Bei forwarded Mails: Original-Sender aus dem Body extrahieren statt
        # aus dem From-Header (der wäre dein eigener Account).
        sender_domain = _extract_original_sender(body_html, body_plain, from_addr)

        logger.info(f"[{self.name}] verarbeite Mail von {sender_domain or 'unknown'}: "
                    f"{subject[:60]}")

        # Quelle für Telegram: "Email: wagnis.org"
        mail_source = f"Email: {sender_domain}" if sender_domain else self.name

        yielded_ext_ids: set[str] = set()

        # 1. Block-basierte Extraktion (gleich wie GenericTextAdapter)
        if body_html:
            soup = BeautifulSoup(body_html, "html.parser")
            for block in _find_listing_blocks(soup):
                listing = _parse_block(block, mail_source, subject)
                if listing and listing.external_id not in yielded_ext_ids:
                    yielded_ext_ids.add(listing.external_id)
                    yield listing

        # 2. Link-basierte Extraktion: Stubs für Listing-URLs zum Anklicken
        if body_html:
            soup = BeautifulSoup(body_html, "html.parser")
            for stub in _extract_listing_stubs(soup, mail_source, subject):
                if stub.external_id not in yielded_ext_ids:
                    yielded_ext_ids.add(stub.external_id)
                    yield stub

        # 3. Fallback: Plain-Text-Block falls kein HTML
        if not body_html and body_plain:
            stub = _parse_plain_text(body_plain, mail_source, subject)
            if stub and stub.external_id not in yielded_ext_ids:
                yield stub


# ---------- Hilfsfunktionen ----------

def _decode(raw: str) -> str:
    """Decoded RFC 2047 encoded mail headers (UTF-8 etc.)."""
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return raw


def _extract_sender_domain(from_addr: str) -> Optional[str]:
    """Extrahiert die Domain aus 'Name <user@domain.de>' oder 'user@domain.de'."""
    if not from_addr:
        return None
    m = re.search(r"[\w\.\-+]+@([\w\.\-]+)", from_addr)
    if not m:
        return None
    domain = m.group(1).lower()
    # Subdomains entfernen für Anzeige: "newsletter.wagnis.org" → "wagnis.org"
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def _extract_original_sender(body_html: Optional[str], body_plain: Optional[str],
                              from_addr: str) -> Optional[str]:
    """Bei weitergeleiteten Mails enthält der Body typischerweise einen Block wie
    'Von: Newsletter <newsletter@wagnis.org>' (oder 'From:'). Das wollen wir
    als Sender, NICHT den User-Account der die Mail weitergeleitet hat.

    Strategie:
    1. Im Body nach 'Von:'/'From:' im Header-Stil suchen
    2. Wenn gefunden: Domain daraus extrahieren
    3. Sonst: Fallback auf From-Header der Mail
    """
    text = ""
    if body_html:
        try:
            text = BeautifulSoup(body_html, "html.parser").get_text(" ", strip=True)
        except Exception:
            text = ""
    if not text and body_plain:
        text = body_plain

    if text:
        # Suche nach "Von: Name <email@domain.de>" im weitergeleiteten Body
        # Stop bei Zeilenende/<br>/spaces — der Email kann irgendwo im Block stehen
        m = re.search(
            r"(?:Von|From|Gesendet von|Sent from):\s*[^<\n]{0,200}<\s*([\w\.\-+]+@[\w\.\-]+)\s*>",
            text,
            re.IGNORECASE,
        )
        if m:
            d = _extract_sender_domain(m.group(1))
            if d:
                return d

        # Alternativ: "Von: email@domain.de" ohne spitze Klammern
        m = re.search(
            r"(?:Von|From|Gesendet von|Sent from):\s*([\w\.\-+]+@[\w\.\-]+)",
            text,
            re.IGNORECASE,
        )
        if m:
            d = _extract_sender_domain(m.group(1))
            if d:
                return d

    # Fallback auf den From-Header
    return _extract_sender_domain(from_addr)


def _extract_body(msg) -> Tuple[Optional[str], Optional[str]]:
    """Extrahiert (html, plain) aus der Mail. HTML bevorzugt für Block-Parsing."""
    html_parts = []
    plain_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
            except Exception:
                continue
            if ctype == "text/html":
                html_parts.append(text)
            elif ctype == "text/plain":
                plain_parts.append(text)
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    html_parts.append(text)
                else:
                    plain_parts.append(text)
        except Exception:
            pass

    html = "\n".join(html_parts) if html_parts else None
    plain = "\n".join(plain_parts) if plain_parts else None
    return html, plain


def _find_listing_blocks(soup: BeautifulSoup) -> List[Tag]:
    """Findet Block-Elemente im Mail-HTML die wie Listings aussehen.

    Mails nutzen oft <table>-Layouts statt <div>, deshalb hier andere
    Selektoren als im GenericTextAdapter.
    """
    SELECTORS = [
        "table[class*='listing']", "table[class*='ad']", "table[class*='offer']",
        "div[class*='listing']", "div[class*='ad']", "div[class*='offer']",
        "div[class*='card']", "div[class*='angebot']", "div[class*='objekt']",
        "td[class*='listing']", "td[align]",  # Tabellen-Layouts
        "article", "li",
    ]
    candidates: List[Tag] = []
    seen_ids: set[int] = set()

    for sel in SELECTORS:
        try:
            for block in soup.select(sel):
                bid = id(block)
                if bid in seen_ids:
                    continue
                text = block.get_text(" ", strip=True)
                # Newsletter-Footer/Header mit Such-Kriterien sieht aus wie ein
                # Listing (enthält m²/€), ist aber keins. Ausfiltern.
                if _NEWSLETTER_BOILERPLATE_RE.search(text):
                    continue
                # Wohnungsgesuche (jemand sucht, statt anbietet) ebenfalls raus.
                # Wichtig für Budenschleuder & ähnliche Mailinglisten.
                if _HOUSING_REQUEST_RE.search(text):
                    continue
                if _looks_like_listing(text):
                    candidates.append(block)
                    seen_ids.add(bid)
        except Exception:
            continue

    return _filter_nested(candidates)


def _parse_block(block: Tag, source: str, subject: str) -> Optional[Listing]:
    """Parst einen Block aus dem Mail-HTML wie im GenericTextAdapter."""
    text = block.get_text(" ", strip=True)
    if len(text) < 20:
        return None

    # Status-Filter (VERMIETET) — schon in _looks_like_listing geprüft, hier
    # defensiv nochmal für den Fall dass jemand den Helper ändert
    if _STATUS_TAKEN_RE.search(text):
        return None

    link = block.find("a", href=True)
    href = link.get("href", "") if link else ""

    title = None
    if link:
        title = link.get_text(" ", strip=True)
    if not title or len(title) < 5:
        heading = block.find(["h1", "h2", "h3", "h4", "strong", "b"])
        if heading:
            title = heading.get_text(" ", strip=True)
    if not title or len(title) < 5:
        title = text[:80]
    title = title[:200]

    if href:
        ext_id = hashlib.md5(href.encode()).hexdigest()[:12]
    else:
        ext_id = hashlib.md5(text[:200].encode()).hexdigest()[:12]

    address = None
    addr_match = _ADDRESS_RE.search(text)
    if addr_match:
        address = f"{addr_match.group(1).strip()}, {addr_match.group(2)} München"

    return Listing(
        source=source,
        external_id=ext_id,
        url=href or "(aus E-Mail, keine URL)",
        title=title,
        address=address,
        price_warm=_extract_price_warm(text),
        price_cold=_extract_price(text),
        size_sqm=_extract_apartment_sqm(text),
        rooms=parse_rooms(_match(text, r"([\d.,]+)\s*(?:Zi(?:mmer)?|-Zi)")),
        description=text[:500],
    )


def _extract_listing_stubs(soup: BeautifulSoup, source: str, subject: str) -> Iterable[Listing]:
    """Sammelt Links auf bekannte Listing-Portale als Listing-Stubs.

    Auch wenn die Mail keine eigenen Listing-Daten enthält, kann sie Links
    auf ImmoScout/Immowelt/etc. enthalten — die geben wir als Stubs raus,
    damit der User sie schnell sieht.

    Zwei strikte Filter:
    - Domain muss in LISTING_DOMAINS sein
    - Pfad muss wie eine Inserats-Detailseite aussehen (LISTING_URL_PATH_PATTERNS),
      NICHT eine Saved-Search-Management-URL
    """
    seen_hrefs: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        href_lower = href.lower()
        if any(skip in href_lower for skip in LINK_SKIP_PATTERNS):
            continue

        parsed = urlparse(href)
        domain = parsed.netloc.lower().replace("www.", "")
        # Domain muss in LISTING_DOMAINS sein (oder Subdomain davon)
        if not any(d == domain or domain.endswith("." + d) for d in LISTING_DOMAINS):
            continue

        # Pfad muss wie ein konkretes Listing aussehen — nicht Profil/Suche/etc.
        path_lower = parsed.path.lower()
        if not any(p in path_lower for p in LISTING_URL_PATH_PATTERNS):
            continue

        # Dedup pro Mail
        href_clean = _strip_tracking_params(href)
        if href_clean in seen_hrefs:
            continue
        seen_hrefs.add(href_clean)

        link_text = a.get_text(" ", strip=True)
        # Wenn Link-Text aussagekräftig: nehmen. Sonst Subject als Titel.
        if len(link_text) > 10 and not _NEWSLETTER_BOILERPLATE_RE.search(link_text):
            title = link_text
        else:
            title = subject

        ext_id = hashlib.md5(href_clean.encode()).hexdigest()[:12]

        yield Listing(
            source=source,
            external_id=ext_id,
            url=href_clean,
            title=title[:200],
            description=f"Aus E-Mail: {subject[:200]}",
        )


def _parse_plain_text(text: str, source: str, subject: str) -> Optional[Listing]:
    """Letzter Fallback: Mail hat nur Plain-Text, kein HTML."""
    if not _looks_like_listing(text):
        return None
    ext_id = hashlib.md5(text[:200].encode()).hexdigest()[:12]
    addr_match = _ADDRESS_RE.search(text)
    address = (f"{addr_match.group(1).strip()}, {addr_match.group(2)} München"
               if addr_match else None)
    return Listing(
        source=source,
        external_id=ext_id,
        url="(aus E-Mail, keine URL)",
        title=subject[:200] if subject else text[:80],
        address=address,
        price_warm=_extract_price_warm(text),
        price_cold=_extract_price(text),
        size_sqm=_extract_apartment_sqm(text),
        rooms=parse_rooms(_match(text, r"([\d.,]+)\s*(?:Zi(?:mmer)?|-Zi)")),
        description=text[:500],
    )


def _strip_tracking_params(url: str) -> str:
    """Entfernt typische E-Mail-Tracking-Parameter (utm_*, mc_*, etc.)."""
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        # Behalte nur Parameter die nicht wie Tracking aussehen
        from urllib.parse import parse_qsl, urlencode, urlunparse
        params = parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in params
                    if not k.lower().startswith(("utm_", "mc_", "_hsenc",
                                                  "_hsmi", "trk", "gclid",
                                                  "fbclid"))]
        new_query = urlencode(filtered)
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return url


def _match(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None
