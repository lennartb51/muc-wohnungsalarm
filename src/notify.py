"""Push-Benachrichtigung via Telegram-Bot.

Message-Format zeigt alle vorhandenen Felder strukturiert an.
3-stufiger Fallback gegen API-Fehler:
1. HTML mit Link-Preview
2. Plain-Text OHNE Link-Preview (umgeht Cloudflare-Preview-Probleme)
3. Minimal: nur URL als Plain-Text
"""
from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

import requests

from .models import Listing

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Max Länge der Kurzbeschreibung in der Telegram-Nachricht
DESCRIPTION_MAX_CHARS = 240


def send_telegram(listings: List[Listing]) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID fehlen")
        return 0

    sent = 0
    for listing in listings:
        if _send_one(token, chat_id, listing):
            sent += 1
        time.sleep(0.5)
    return sent


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

    # 1. HTML mit Preview
    ok, err = _post(url, {
        "chat_id": chat_id,
        "text": format_message_html(listing),
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })
    if ok:
        return True
    logger.warning(f"[Telegram] HTML+Preview fehlgeschlagen ({err})")

    # 2. Plain-Text ohne Preview
    ok, err = _post(url, {
        "chat_id": chat_id,
        "text": format_message_plain(listing),
        "disable_web_page_preview": True,
    })
    if ok:
        return True
    logger.warning(f"[Telegram] Plain ohne Preview fehlgeschlagen ({err})")

    # 3. Ultra-Minimal
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


# ---------- Nachrichten-Format ----------

def format_message_html(l: Listing) -> str:
    """HTML-Variante mit Bold und Detailfeldern."""
    lines = [f"🏠 <b>{_esc(l.title)}</b>"]

    # Stadtteil / Adresse
    location = l.district or l.address
    if location:
        lines.append(f"📍 {_esc(location)}")

    # Zimmer + m²
    size_facts = []
    if l.rooms:
        size_facts.append(f"{l.rooms:g} Zi")
    if l.size_sqm:
        size_facts.append(f"{l.size_sqm:.0f} m²")
    if size_facts:
        lines.append(f"📐 {' · '.join(size_facts)}")

    # Preise (kalt + warm wenn beide bekannt)
    price_facts = _price_facts(l)
    if price_facts:
        lines.append(f"💰 {' · '.join(price_facts)}")

    # Ausstattung: Balkon / Küche (nur wenn explizit erkannt)
    feat_facts = _feature_facts(l)
    if feat_facts:
        lines.append(f"🔑 {' · '.join(feat_facts)}")

    # Kurzbeschreibung
    desc = _short_description(l)
    if desc:
        lines.append(f"\n{_esc(desc)}")

    lines.append(f"\n🏷 {_esc(l.source)}")
    lines.append(f'<a href="{_esc(l.url)}">→ Original ansehen</a>')
    return "\n".join(lines)


def format_message_plain(l: Listing) -> str:
    """Plain-Text-Variante (kein parse_mode → safer bei Sonderzeichen)."""
    lines = [f"🏠 {l.title}"]

    location = l.district or l.address
    if location:
        lines.append(f"📍 {location}")

    size_facts = []
    if l.rooms:
        size_facts.append(f"{l.rooms:g} Zi")
    if l.size_sqm:
        size_facts.append(f"{l.size_sqm:.0f} m²")
    if size_facts:
        lines.append(f"📐 {' · '.join(size_facts)}")

    price_facts = _price_facts(l)
    if price_facts:
        lines.append(f"💰 {' · '.join(price_facts)}")

    feat_facts = _feature_facts(l)
    if feat_facts:
        lines.append(f"🔑 {' · '.join(feat_facts)}")

    desc = _short_description(l)
    if desc:
        lines.append(f"\n{desc}")

    lines.append(f"\n🏷 {l.source}")
    lines.append(l.url)
    return "\n".join(lines)


def _price_facts(l: Listing) -> list[str]:
    facts = []
    if l.price_cold:
        facts.append(f"{l.price_cold:,.0f} € kalt".replace(",", "."))
    if l.price_warm:
        facts.append(f"{l.price_warm:,.0f} € warm".replace(",", "."))
    return facts


def _feature_facts(l: Listing) -> list[str]:
    facts = []
    if l.has_balcony is True:
        facts.append("Balkon ✓")
    elif l.has_balcony is False:
        facts.append("Balkon ✗")
    if l.has_kitchen is True:
        facts.append("Küche ✓")
    elif l.has_kitchen is False:
        facts.append("Küche ✗")
    return facts


def _short_description(l: Listing) -> Optional[str]:
    """Kurzbeschreibung — gestrippt von redundanten Zahlen-Markern."""
    if not l.description:
        return None
    desc = l.description.strip()
    if len(desc) < 30:
        return None
    # Bei strukturierten Quellen (VfV etc.) ist desc oft schöner Prosa-Text.
    # Bei generic adapters ist desc der rohe Listing-Block-Text — der enthält
    # m²/€/Zimmer-Zahlen die wir schon strukturiert oben anzeigen. Trotzdem
    # zeigen, weil's Stichworte zur Lage/Ausstattung liefert.
    if len(desc) > DESCRIPTION_MAX_CHARS:
        # Sauber an Wortgrenze abschneiden
        desc = desc[:DESCRIPTION_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return desc


# Backwards-compat
def format_message(l: Listing) -> str:
    return format_message_html(l)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
