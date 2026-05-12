"""VfV München – Verein für Volkswohnungen eG.

~1.500 Wohnungen, sehr aktiver Listing-Bereich. Die Übersicht /wohnungsangebote
leitet automatisch auf die Detail-Seite des ersten Listings weiter, listet aber
in der Sidebar alle anderen Wohnungen als Card-Links. Wir folgen jedem Link
und parsen die Detail-Seite einzeln, weil dort alle Daten strukturiert sind
(Kaltmiete, Gesamtmiete, Gesamtfläche, Beschreibung).
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Listing
from .base import Adapter, parse_price, parse_rooms, parse_sqm

logger = logging.getLogger(__name__)


class VfvAdapter(Adapter):
    name = "VfV München"
    rate_limit_seconds = 2.0  # eigene Site, nicht überlasten

    LIST_URL = "https://www.vfv-muenchen.de/wohnungsangebote"

    def fetch(self) -> Iterable[Listing]:
        try:
            r = self.get(self.LIST_URL)
        except Exception as e:
            logger.warning(f"[{self.name}] Request failed: {e}")
            return

        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Alle Detail-Links sammeln (Pattern: /wohnungsangebote/<slug>)
        detail_urls: set[str] = set()
        for a in soup.select("a[href*='/wohnungsangebote/']"):
            href = a.get("href", "")
            if not href:
                continue
            # Nur Detail-Seiten, nicht die Übersicht selbst
            if href.rstrip("/").endswith("/wohnungsangebote"):
                continue
            full = urljoin(self.LIST_URL, href)
            detail_urls.add(full)

        # Auch die aktuelle Seite (URL-Redirect-Ziel) ist eine Detail-Seite,
        # die wir direkt parsen können statt nochmal zu fetchen
        if r.url and "/wohnungsangebote/" in r.url:
            listing = self._parse_detail_from_soup(soup, r.url)
            if listing:
                yield listing
            detail_urls.discard(r.url)

        # Restliche Detail-Seiten einzeln fetchen
        for url in sorted(detail_urls):
            listing = self._fetch_detail(url)
            if listing:
                yield listing

    def _fetch_detail(self, url: str) -> Optional[Listing]:
        try:
            r = self.get(url)
        except Exception as e:
            logger.debug(f"[{self.name}] Detail-Fetch failed for {url}: {e}")
            return None
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        return self._parse_detail_from_soup(soup, url)

    def _parse_detail_from_soup(self, soup: BeautifulSoup,
                                 url: str) -> Optional[Listing]:
        # Titel: erstes H1 mit echter Wohnungs-Bezeichnung
        title = None
        for h1 in soup.find_all("h1"):
            t = h1.get_text(" ", strip=True)
            if t and t.lower() != "wohnungsangebote" and len(t) > 5:
                title = t
                break
        if not title:
            title = url.rstrip("/").split("/")[-1].replace("-", " ").title()

        # Volltext der Detail-Seite, daraus extrahieren wir die Eckdaten
        text = soup.get_text(" ", strip=True)
        if "m²" not in text and "m2" not in text:
            return None  # Kein echtes Listing auf dieser Seite

        # Stadtteil aus Titel oder Wohnanlagen-Hinweis
        district = _extract_district(title, text)

        external_id = url.rstrip("/").split("/")[-1][:60]

        return Listing(
            source=self.name,
            external_id=external_id,
            url=url,
            title=title[:200],
            price_warm=parse_price(_find(text, r"Gesamtmiete[^\d]*([\d.,]+)")),
            price_cold=parse_price(_find(text, r"Kaltmiete[^\d]*([\d.,]+)")),
            size_sqm=parse_sqm(_find(text, r"Gesamtfläche[^\d]*([\d.,]+)")
                                 or _find(text, r"([\d.,]+)\s*m²")),
            rooms=parse_rooms(_find(text, r"(\d+(?:[,.]\d+)?)\s*[\-]?\s*Zimmer")),
            district=district,
            description=_extract_description(soup, text),
        )


# ---------- Hilfsfunktionen ----------

KNOWN_DISTRICTS = [
    "Neuhausen", "Schwabing-West", "Schwabing", "Schwabing-Ost",
    "Tumblingerstraße", "Tumblingerstrasse", "Gotzinger Platz",
    "Oberländerstraße", "Thalkirchen", "Rupert-Mayer", "Unterföhring",
    "Garching", "Dreimühlen", "Fall-", "Zechstraße",
]


def _extract_district(title: str, text: str) -> Optional[str]:
    blob = f"{title} {text[:500]}"
    for d in KNOWN_DISTRICTS:
        if d.lower() in blob.lower():
            return d
    return None


def _extract_description(soup: BeautifulSoup, fulltext: str) -> str:
    # Suche nach dem "Beschreibung"-Abschnitt
    for header in soup.find_all(["h2", "h3"]):
        if "beschreibung" in header.get_text(strip=True).lower():
            next_p = header.find_next("p")
            if next_p:
                return next_p.get_text(" ", strip=True)[:500]
    return fulltext[:500]


def _find(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None
