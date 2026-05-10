"""Kleinanzeigen.de – viele Privatvermieter, oft günstigere Preise.

ACHTUNG: Kleinanzeigen hat Anti-Bot-Maßnahmen (Cloudflare). Wenn dieser Adapter
HTTP 403/503 zurückgibt, gibt es zwei Optionen:
  1. enabled=False setzen
  2. Auf Playwright umstellen (siehe README, Abschnitt "Schwierige Quellen")
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


class KleinanzeigenAdapter(Adapter):
    name = "Kleinanzeigen"
    rate_limit_seconds = 4.0

    # München, Wohnung-mieten, Stadt-Code 6411
    SEARCH_URL = "https://www.kleinanzeigen.de/s-wohnung-mieten/muenchen/c203l6411"

    def fetch(self) -> Iterable[Listing]:
        r = self.get(self.SEARCH_URL)
        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code} – evtl. blockiert")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Listings sind in <article class="aditem"> oder ähnlich
        for article in soup.select("article.aditem, li.ad-listitem article"):
            ad_id = article.get("data-adid") or article.get("data-id")
            link = article.select_one("a.ellipsis, a[href*='/s-anzeige/']")
            if not (ad_id and link):
                continue

            href = link.get("href", "")
            url = urljoin("https://www.kleinanzeigen.de/", href)
            title = link.get_text(strip=True)

            # Preis steht meist in einem Element mit Klasse "aditem-main--middle--price"
            price_el = article.select_one(
                "[class*='price'], .aditem-main--middle--price-shipping--price"
            )
            price = parse_price(price_el.get_text() if price_el else None)

            # Größe / Zimmer als Tags
            tags_text = " ".join(
                t.get_text(" ", strip=True)
                for t in article.select(".simpletag, [class*='tag'], "
                                          ".aditem-main--bottom")
            )
            size = parse_sqm(_find(tags_text, r"([\d.,]+)\s*m²"))
            rooms = parse_rooms(_find(tags_text, r"([\d.,]+)\s*Zi"))

            location_el = article.select_one("[class*='location'], "
                                               ".aditem-main--top--left")
            district = location_el.get_text(" ", strip=True) if location_el else None

            yield Listing(
                source=self.name,
                external_id=str(ad_id),
                url=url,
                title=title,
                price_cold=price,
                size_sqm=size,
                rooms=rooms,
                district=district,
            )


def _find(text: str, pattern: str):
    m = re.search(pattern, text)
    return m.group(1) if m else None
