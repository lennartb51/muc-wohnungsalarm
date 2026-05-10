"""Immowelt – größtes Nicht-IS24-Portal, viele eigene Listings."""
from __future__ import annotations

import json
import logging
import re
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Listing
from .base import Adapter, parse_price, parse_rooms, parse_sqm

logger = logging.getLogger(__name__)


class ImmoweltAdapter(Adapter):
    name = "Immowelt"
    rate_limit_seconds = 3.0

    # Suche München, Mietwohnungen, sortiert nach Aktualität
    SEARCH_URL = (
        "https://www.immowelt.de/classified-search?"
        "distributionTypes=Rent&estateTypes=Apartment&locations=AD08DE8634"
        "&order=DateDesc"
    )

    def fetch(self) -> Iterable[Listing]:
        r = self.get(self.SEARCH_URL)
        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Immowelt rendert viele Daten als JSON in einem Next.js __NEXT_DATA__ Script.
        # Robusteste Methode: dieses JSON parsen statt CSS-Selektoren raten.
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data:
            try:
                yield from self._from_next_data(next_data.string)
                return
            except Exception as e:
                logger.warning(f"[{self.name}] __NEXT_DATA__ parse failed: {e}, "
                               f"fallback auf HTML")

        # Fallback: HTML-Karten
        yield from self._from_html(soup)

    def _from_next_data(self, raw: str) -> Iterable[Listing]:
        data = json.loads(raw)
        # Pfad zu den Listings ist nicht stabil — wir suchen rekursiv nach Objekten
        # mit einem typischen Listing-Shape.
        for obj in _walk(data):
            if not isinstance(obj, dict):
                continue
            oid = obj.get("id") or obj.get("onlineId")
            title = obj.get("title")
            if not (oid and title):
                continue
            # Heuristik: muss URL/Slug + Preis-Feld haben
            slug = obj.get("relativeUrl") or obj.get("url")
            if not slug:
                continue

            price_obj = obj.get("price") or {}
            place = obj.get("place") or {}

            yield Listing(
                source=self.name,
                external_id=str(oid),
                url=urljoin("https://www.immowelt.de/", slug),
                title=title,
                price_cold=_num(price_obj.get("amountMin") or price_obj.get("amount")),
                size_sqm=_num((obj.get("livingSpace") or {}).get("amountMin")
                              or (obj.get("livingSpace") or {}).get("amount")),
                rooms=_num((obj.get("rooms") or {}).get("amountMin")
                           or (obj.get("rooms") or {}).get("amount")),
                district=place.get("district") or place.get("city"),
                address=", ".join(filter(None, [place.get("street"),
                                                 place.get("district")])),
            )

    def _from_html(self, soup: BeautifulSoup) -> Iterable[Listing]:
        # Fallback wenn Next.js-JSON-Schema sich ändert.
        # Listing-Karten haben üblicherweise einen Link mit /expose/... im href.
        for a in soup.select('a[href*="/expose/"]'):
            href = a.get("href", "")
            m = re.search(r"/expose/([a-z0-9]+)", href)
            if not m:
                continue
            external_id = m.group(1)
            card = a.find_parent() or a

            text = card.get_text(" ", strip=True)
            title = (a.get("title") or text[:80]).strip()

            yield Listing(
                source=self.name,
                external_id=external_id,
                url=urljoin("https://www.immowelt.de/", href),
                title=title,
                price_cold=parse_price(_find(text, r"([\d.,]+)\s*€")),
                size_sqm=parse_sqm(_find(text, r"([\d.,]+)\s*m²")),
                rooms=parse_rooms(_find(text, r"([\d.,]+)\s*Zi")),
            )


def _walk(obj):
    """Rekursiv durch dict/list iterieren."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _find(text: str, pattern: str):
    m = re.search(pattern, text)
    return m.group(1) if m else None
