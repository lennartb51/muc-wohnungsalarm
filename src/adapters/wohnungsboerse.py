"""Wohnungsboerse.net – großer Aggregator, mit eigenen Privat-Inseraten."""
from __future__ import annotations

import logging
import re
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Listing
from .base import Adapter, parse_price, parse_rooms, parse_sqm

logger = logging.getLogger(__name__)


class WohnungsboerseAdapter(Adapter):
    name = "Wohnungsboerse"
    rate_limit_seconds = 3.0

    SEARCH_URL = "https://www.wohnungsboerse.net/searches/index?estate_marketing_types=2&estate_types[0]=1&cities[0]=M%C3%BCnchen"

    def fetch(self) -> Iterable[Listing]:
        r = self.get(self.SEARCH_URL)
        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Listing-Cards haben üblicherweise Links auf /immobilien/...
        seen_hrefs = set()
        for a in soup.select("a[href*='/immobilien/'], a[href*='/expose/']"):
            href = a.get("href", "")
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            # ID aus URL ziehen
            m = re.search(r"/(\d{5,})", href)
            ext_id = m.group(1) if m else href[-30:]

            container = a.find_parent(["article", "div", "li"]) or a
            text = container.get_text(" ", strip=True)
            if "m²" not in text and "€" not in text:
                continue

            title = a.get("title") or a.get_text(strip=True) or text[:80]

            yield Listing(
                source=self.name,
                external_id=str(ext_id),
                url=urljoin("https://www.wohnungsboerse.net/", href),
                title=title[:200],
                price_cold=parse_price(_find(text, r"([\d.,]+)\s*€")),
                size_sqm=parse_sqm(_find(text, r"([\d.,]+)\s*m²")),
                rooms=parse_rooms(_find(text, r"([\d.,]+)\s*Zi")),
            )


def _find(text: str, pattern: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None
