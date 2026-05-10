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
    """Schickt eine Nachricht pro Listing. Gibt Anzahl erfolgreicher Sends zurück."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID fehlen")
        return 0

    sent = 0
    for listing in listings:
        text = format_message(listing)
        try:
            r = requests.post(
                TELEGRAM_API.format(token=token),
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            r.raise_for_status()
            sent += 1
            time.sleep(0.5)  # Telegram Rate-Limit: ~30 msg/sec, wir bleiben weit drunter
        except Exception as e:
            logger.error(f"Telegram-Fehler für {listing.url}: {e}")
    return sent


def format_message(l: Listing) -> str:
    """HTML-formatierte Nachricht für Telegram."""
    lines = [f"🏠 <b>{_esc(l.title)}</b>"]

    if l.district or l.address:
        loc = l.district or l.address
        lines.append(f"📍 {_esc(loc)}")

    facts = []
    if l.price_warm:
        facts.append(f"<b>{l.price_warm:.0f} €</b> warm")
    elif l.price_cold:
        facts.append(f"<b>{l.price_cold:.0f} €</b> kalt")
    if l.size_sqm:
        facts.append(f"{l.size_sqm:.0f} m²")
    if l.rooms:
        rooms_str = f"{l.rooms:g}"  # 2.0 → "2", 2.5 → "2.5"
        facts.append(f"{rooms_str} Zi")
    if facts:
        lines.append("💰 " + " · ".join(facts))

    lines.append(f"🏷 {_esc(l.source)}")
    lines.append(f'\n<a href="{l.url}">→ Original ansehen</a>')
    return "\n".join(lines)


def _esc(s: str) -> str:
    """HTML-Escape für Telegram parse_mode=HTML."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))
