"""Spezifischer Adapter für Südhausbau (TYPO3-Layout mit h3 + table + link).

Die Generic-Auto-Discovery findet die Listings nicht, weil sie nicht in
typischen Container-Tags stecken, sondern in einer h3+table+a-Struktur
ohne klare Listing-Container-Class.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .base import Adapter, parse_number
from ..models import Listing

logger = logging.getLogger(__name__)

BASE_URL = "https://www.suedhausbau.de"
LIST_URL = "https://www.suedhausbau.de/immobilienangebote/mietangebote.html"


class SuedhausbauAdapter(Adapter):
    """Specific Adapter für die Südhausbau Mietangebote-Seite."""

    name = "Südhausbau"
    rate_limit_seconds = 2.5

    def fetch(self) -> Iterable[Listing]:
        try:
            r = self.get(LIST_URL)
        except Exception as e:
            logger.warning(f"[{self.name}] Request failed: {e}")
            return

        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Layout: jedes Listing besteht aus einem <h3>-Titel, einer <table>
        # mit Daten und einem <a href=".../mietobjekt/...">. Wir verankern
        # auf den Detail-Links und gehen zurück zum Container.
        detail_links = soup.find_all("a", href=re.compile(r"/mietobjekt/[\w\-]+\.html"))

        seen_urls = set()
        for link in detail_links:
            href = link.get("href")
            full_url = urljoin(BASE_URL, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            listing = self._parse_listing(link, full_url)
            if listing:
                yield listing

    def _parse_listing(self, link_tag: Tag, detail_url: str) -> Optional[Listing]:
        """Sucht ausgehend vom 'mehr Details'-Link nach Titel + Tabellen-Daten."""
        # Titel: nächstes <h3> rückwärts im DOM
        title = None
        for prev in link_tag.find_all_previous(["h2", "h3", "h4"]):
            t = prev.get_text(" ", strip=True)
            # Stoppe bei Navigation/Sidebar-Titeln
            if t and not any(skip in t.lower() for skip in ["leistungen", "über uns", "referenzen", "downloads", "kontakt", "mieterservice"]):
                title = t
                break

        # Tabellen-Daten: nächste <table> rückwärts
        table = None
        for prev in link_tag.find_all_previous("table"):
            table = prev
            break

        if not table:
            return None

        table_text = table.get_text(" ", strip=True)

        # Address: Pattern "Straßenname Hausnr PLZ München"
        # Strikt: Straßenname endet auf -str./-straße/-platz/-weg etc.
        addr_match = re.search(
            r"([A-ZÄÖÜ][\wäöüß\.\- ]{1,40}?"
            r"(?:str(?:aße|\.)|straße|platz|weg|allee|gasse|ring|ufer|damm|"
            r"hof|tor|tal|markt|berg|park)"
            r"\s*\d+\s*[a-z]?)"
            r"\s*(\d{5})\s+M[üu]nchen",
            table_text,
            re.IGNORECASE,
        )
        address = f"{addr_match.group(1)}, {addr_match.group(2)} München" if addr_match else None
        postcode = addr_match.group(2) if addr_match else None

        # Preis: "1133 €" oder "1.133 €" oder "2.136 €"
        price_match = re.search(r"(\d[\d\.,]*)\s*€", table_text)
        price_warm = parse_number(price_match.group(1)) if price_match else None
        # Bei Südhausbau ist die Spalten-Überschrift "Miete inkl. NK/HZ" — also warm.

        # m²: "65,87 m²" oder "95,10 m²"
        sqm_match = re.search(r"(\d[\d\.,]*)\s*m²", table_text)
        sqm = parse_number(sqm_match.group(1)) if sqm_match else None

        if not (price_warm and sqm):
            return None  # ohne Preis+Größe ist es kein valides Listing

        # Zimmer: aus Titel extrahieren ("3-Zi.-DG-Wohnung" → 3, "2-Zimmer-Wohnung" → 2)
        rooms = None
        if title:
            r_match = re.search(r"(\d[,\.]?\d?)[\-\s]?(?:Zi|Zimmer)", title)
            if r_match:
                rooms = parse_number(r_match.group(1))

        # Stadtteil: aus Titel? Bei Südhausbau steht der oft im Titel
        # ("3-Zimmer-Wohnung in Solln"). Sonst leer lassen — der Match-Filter
        # nutzt eh die PLZ als Backup.
        district = None
        if title:
            d_match = re.search(r"\bin\s+([A-ZÄÖÜ][\wäöüß\-]+)", title)
            if d_match:
                district = d_match.group(1)

        return Listing(
            source="Südhausbau",
            external_id=detail_url,
            url=detail_url,
            title=title or "Südhausbau Mietangebot",
            address=address,
            postcode=postcode,
            district=district,
            rooms=rooms,
            size_sqm=sqm,
            price_warm=price_warm,
            price_cold=None,
            description=table_text[:500],
        )
