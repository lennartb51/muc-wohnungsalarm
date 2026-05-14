"""WG-Gesucht.de – Filter auf 1-Zimmer und Wohnungen (NICHT WG-Zimmer).

WG-Gesucht hat im Bestand auch viele Privat-Wohnungen unter 1.5–2 Zi, oft
ohne Makler. Filter: type 0 = "Wohnung", type 2 = "1-Zimmer-Wohnung".
"""
from __future__ import annotations

import logging
import re
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Listing
from .base import Adapter, parse_price, parse_rooms, parse_sqm

logger = logging.getLogger(__name__)


class WgGesuchtAdapter(Adapter):
    name = "WG-Gesucht"
    rate_limit_seconds = 4.0

    # 90 = München, categories 1+2 = 1-Zi + Wohnung (kein WG-Zimmer = type 0)
    SEARCH_URL = (
        "https://www.wg-gesucht.de/wohnungen-und-1-zimmer-wohnungen-in-Muenchen.90.1+2.1.0.html"
    )

    def fetch(self) -> Iterable[Listing]:
        r = self.get(self.SEARCH_URL)
        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # WG-Gesucht hat Listings als <div class="wgg_card offer_list_item">
        for card in soup.select("div.wgg_card.offer_list_item, div[class*='offer_list_item']"):
            link = card.select_one("a[href*='.html']")
            if not link:
                continue

            href = link.get("href", "")
            ad_id = card.get("data-id") or card.get("id", "")
            if not ad_id:
                m = re.search(r"\.(\d{6,})\.html", href)
                ad_id = m.group(1) if m else href[-30:]

            text = card.get_text(" ", strip=True)
            title = link.get_text(" ", strip=True) or text[:80]

            # Preis-Logik: nur dann beides setzen, wenn beides explizit erkennbar
            # ist. Sonst nur die eine erkannte Größe — verhindert dass die selbe
            # Zahl als kalt UND warm in der Telegram-Nachricht erscheint.
            explicit_warm = parse_price(_find(text, r"([\d.,]+)\s*€[^\d]*warm"))
            explicit_cold = parse_price(_find(text, r"([\d.,]+)\s*€[^\d]*kalt"))
            first_price = parse_price(_find(text, r"([\d.,]+)\s*€"))

            if explicit_warm and explicit_cold:
                price_warm, price_cold = explicit_warm, explicit_cold
            elif explicit_warm:
                # Nur Warm explizit → Cold lassen wir None
                price_warm, price_cold = explicit_warm, None
            elif explicit_cold:
                price_warm, price_cold = None, explicit_cold
            else:
                # Keine explizite Markierung → erste Zahl als kalt interpretieren
                price_warm, price_cold = None, first_price

            yield Listing(
                source=self.name,
                external_id=str(ad_id),
                url=urljoin("https://www.wg-gesucht.de/", href),
                title=title[:200],
                price_warm=price_warm,
                price_cold=price_cold,
                size_sqm=parse_sqm(_find(text, r"([\d.,]+)\s*m²")),
                rooms=parse_rooms(_find(text, r"([\d.,]+)\s*(?:Zi|Zimmer)")),
            )


def _find(text: str, pattern: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None
