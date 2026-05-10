"""Push-Benachrichtigung via Telegram-Bot."""
from __future__ import annotations

import logging
import os
import time
from typing import List

import requests

from .models import Listing

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


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


def _send_one(token: str, chat_id: str, listing: Listing) -> bool:
    """Erst HTML versuchen, bei Fehler Plain-Text-Fallback."""
    url = TELEGRAM_API.format(token=token)

    # Versuch 1: HTML-formatiert (mit Bold)
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": format_message_html(listing),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=10)
        if r.status_code == 200:
            return True
        logger.warning(f"HTML-Send fehlgeschlagen ({r.status_code}), "
                       f"versuche Plain-Text für {listing.url}")
    except Exception as e:
        logger.warning(f"HTML-Send Exception: {e}, versuche Plain-Text")

    # Versuch 2: Plain-Text-Fallback (kein parse_mode → keine Escape-Probleme)
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": format_message_plain(listing),
            "disable_web_page_preview": False,
        }, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram-Fehler für {listing.url}: {e}")
        return False


def format_message_html(l: Listing) -> str:
    """HTML-Variante mit Bold."""
    lines = [f"🏠 <b>{_esc(l.title)}</b>"]
    if l.district or l.address:
        lines.append(f"📍 {_esc(l.district or l.address)}")
    facts = _facts_strings(l)
    if facts:
        lines.append("💰 " + " · ".join(facts))
    lines.append(f"🏷 {_esc(l.source)}")
    lines.append(f'\n<a href="{_esc(l.url)}">→ Original ansehen</a>')
    return "\n".join(lines)


def format_message_plain(l: Listing) -> str:
    """Plain-Text-Variante. URLs werden von Telegram automatisch verlinkt."""
    lines = [f"🏠 {l.title}"]
    if l.district or l.address:
        lines.append(f"📍 {l.district or l.address}")
    facts = _facts_strings(l)
    if facts:
        lines.append("💰 " + " · ".join(facts))
    lines.append(f"🏷 {l.source}")
    lines.append(f"\n{l.url}")
    return "\n".join(lines)


def _facts_strings(l: Listing) -> list[str]:
    facts = []
    if l.price_warm:
        facts.append(f"{l.price_warm:.0f} € warm")
    elif l.price_cold:
        facts.append(f"{l.price_cold:.0f} € kalt")
    if l.size_sqm:
        facts.append(f"{l.size_sqm:.0f} m²")
    if l.rooms:
        facts.append(f"{l.rooms:g} Zi")
    return facts


# Backwards-compat
def format_message(l: Listing) -> str:
    return format_message_html(l)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
