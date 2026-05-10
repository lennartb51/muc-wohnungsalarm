"""SZ Immobilien – Süddeutsche Zeitung Immobilienmarkt.

Kleiner aber kuratierter Bestand, oft hochwertige Objekte und kleine Vermieter,
die nicht auf IS24/Immowelt inserieren.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Listing
from .base import Adapter, parse_price, parse_rooms, parse_sqm

logger = logging.getLogger(__name__)


class SzImmobilienAdapter(Adapter):
    name = "SZ Immobilien"
    rate_limit_seconds = 3.0

    SEARCH_URL = (
        "https://immobilienmarkt.sueddeutsche.de/Wohnungen/mieten/Muenchen/"
        "Stadt?sort=createdate%2Bdesc"
    )

    def fetch(self) -> Iterable[Listing]:
        r = self.get(self.SEARCH_URL)
        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Ergebnisse haben Links mit /Anzeige/ oder /expose/
        seen = set()
        for a in soup.select("a[href*='/Anzeige/'], a[href*='/expose/'], "
                              "a[href*='-Wohnung'], a[href*='Wohnung-']"):
            href = a.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            container = a.find_parent(["article", "li", "div"]) or a
            text = container.get_text(" ", strip=True)
            if "m²" not in text and "€" not in text:
                continue

            ext_id = hashlib.md5(href.encode()).hexdigest()[:12]
            title = (a.get_text(strip=True) or text[:80])[:200]

            yield Listing(
                source=self.name,
                external_id=ext_id,
                url=urljoin("https://immobilienmarkt.sueddeutsche.de/", href),
                title=title,
                price_cold=parse_price(_find(text, r"([\d.,]+)\s*€")),
                size_sqm=parse_sqm(_find(text, r"([\d.,]+)\s*m²")),
                rooms=parse_rooms(_find(text, r"([\d.,]+)\s*(?:Zi|Zimmer)")),
            )


def _find(text: str, pattern: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None
