"""Generic-Adapter mit Auto-Discovery für Hausverwaltungs-Sites.

Pattern:
  1. Lade die übergebene URL.
  2. Suche nach Listing-Blöcken (Text mit m²/€/Zimmer).
  3. Wenn keine gefunden UND auto_discover=True: Suche auf der Seite nach
     Links zu Listing-Subseiten ("Mietangebote", "Vermietung", "Immobilien",
     "Wohnungen", "Angebote", "Inserate", "Objekte"), folge dem stärksten
     Match und versuche dort nochmal.
  4. Wenn immer noch nichts: 0 zurückgeben.

Discovery-Heuristik:
  - Plurale & "Angebote/Inserate" werden höher gewichtet als generische Begriffe
  - Bestimmte Pfade werden explizit ausgeschlossen (Karriere, WEG-Verwaltung,
    Ratgeber, News etc. — typische False-Positives)
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ..models import Listing
from .base import Adapter, parse_price, parse_rooms, parse_sqm

logger = logging.getLogger(__name__)

DEFAULT_SELECTORS = [
    "article", "[class*='wohnung']", "[class*='angebot']", "[class*='objekt']",
    "[class*='listing']", "[class*='exposé']", "[class*='expose']",
    "[class*='immobilie']", ".card", ".news-list-item", "li.list-item",
    "[class*='estate']", "[class*='property']",
]

# Discovery: Keyword → Score. Plurale/spezifische Begriffe höher.
DISCOVERY_KEYWORDS = {
    # Sehr starke Signale (Plural, eindeutig Listing-Seite)
    "mietangebote": 5,
    "wohnungsangebote": 5,
    "freie wohnungen": 5,
    "aktuelle angebote": 5,
    "aktuelle objekte": 5,
    "aktuelle mietangebote": 6,
    "freie mietwohnungen": 6,
    "inserate": 4,
    "exposes": 4,
    "exposés": 4,
    "mietwohnungen": 4,
    "vermietungsangebote": 5,

    # Mittlere Signale
    "mietangebot": 3,
    "wohnungsangebot": 3,
    "vermietung": 2,
    "wohnungen": 2,
    "angebote": 2,
    "objekte": 2,
    "mieten": 2,
    "freie wohnung": 3,

    # Schwächere Signale (generische Begriffe)
    "immobilien": 1,
    "wohnung": 1,
    "miete": 1,
}

# Pfade die NIE eine Listing-Seite sein können — hard exclude
EXCLUDE_PATH_KEYWORDS = [
    "stellenangebot", "stellenangebote", "karriere", "career", "jobs", "job",
    "weg-verwaltung", "weg_verwaltung", "wegverwaltung",  # WEG = Eigentümer, kein Mietangebot
    "wissenswert", "ratgeber", "magazin", "news", "blog", "tipp",
    "datenschutz", "impressum", "agb", "kontakt", "ueber-uns", "über-uns",
    "team", "unternehmen", "geschichte",
    "kaufangebote", "verkauf",  # Kauf, kein Miet-Listing
    "sondermietverwaltung",
    "leistungen",  # meist nur Marketing
]


class GenericTextAdapter(Adapter):
    rate_limit_seconds = 2.5

    def __init__(
        self,
        name: str,
        list_url: str,
        selectors: Optional[List[str]] = None,
        base_url: Optional[str] = None,
        auto_discover: bool = True,
    ):
        super().__init__()
        self.name = name
        self.list_url = list_url
        self.selectors = selectors or DEFAULT_SELECTORS
        self.base_url = base_url or _domain_root(list_url)
        self.auto_discover = auto_discover

    def fetch(self) -> Iterable[Listing]:
        # Versuch 1: direkte URL
        listings = list(self._scrape_url(self.list_url))
        if listings:
            yield from listings
            return

        if not self.auto_discover:
            return

        # Versuch 2: Auto-Discovery
        discovered = self._discover_listing_url(self.list_url)
        if discovered and discovered != self.list_url:
            logger.info(f"[{self.name}] Auto-Discovery → {discovered}")
            yield from self._scrape_url(discovered)

    def _scrape_url(self, url: str) -> Iterable[Listing]:
        try:
            r = self.get(url)
        except Exception as e:
            logger.warning(f"[{self.name}] Request failed: {e}")
            return

        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code} für {url}")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        candidates: list[Tag] = []
        seen_blocks = set()

        for sel in self.selectors:
            for block in soup.select(sel):
                bid = id(block)
                if bid in seen_blocks:
                    continue
                text = block.get_text(" ", strip=True)
                if _looks_like_listing(text):
                    candidates.append(block)
                    seen_blocks.add(bid)

        candidates = _filter_nested(candidates)
        for block in candidates:
            listing = self._parse_block(block, url)
            if listing:
                yield listing

    def _discover_listing_url(self, start_url: str) -> Optional[str]:
        """Sucht auf der Seite nach Links zu wahrscheinlichen Listing-Subseiten."""
        try:
            r = self.get(start_url)
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception:
            return None

        scored: list[tuple[int, str]] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            full_url = urljoin(start_url, href)
            full_lower = full_url.lower()

            # Nur Links auf derselben Domain
            if urlparse(full_url).netloc != urlparse(start_url).netloc:
                continue

            # Harte Blacklist auf Pfad-Ebene
            if any(bad in full_lower for bad in EXCLUDE_PATH_KEYWORDS):
                continue

            text = a.get_text(" ", strip=True).lower()
            # Auch Text auf Blacklist checken (z.B. "Karriere" als Link-Text)
            if any(bad in text for bad in EXCLUDE_PATH_KEYWORDS):
                continue

            # Score-Berechnung mit gewichteten Keywords
            score = 0
            for kw, weight in DISCOVERY_KEYWORDS.items():
                if kw in text:
                    score += weight * 2  # Text-Match wichtiger
                if kw in full_lower:
                    score += weight

            if score > 0:
                scored.append((score, full_url))

        if not scored:
            return None

        scored.sort(reverse=True)
        return scored[0][1]

    def _parse_block(self, block: Tag, page_url: str) -> Optional[Listing]:
        text = block.get_text(" ", strip=True)
        if len(text) < 20:
            return None

        link = block.find("a", href=True)
        href = link["href"] if link else page_url
        url = urljoin(self.base_url, href)

        title = None
        if link:
            title = link.get_text(" ", strip=True)
        if not title or len(title) < 5:
            heading = block.find(["h1", "h2", "h3", "h4"])
            if heading:
                title = heading.get_text(" ", strip=True)
        if not title or len(title) < 5:
            title = text[:80]
        title = title[:200]

        if link and href and not href.startswith("#"):
            ext_id = hashlib.md5(href.encode()).hexdigest()[:12]
        else:
            ext_id = hashlib.md5(text[:200].encode()).hexdigest()[:12]

        return Listing(
            source=self.name,
            external_id=ext_id,
            url=url,
            title=title,
            price_warm=_extract_price_warm(text),
            price_cold=_extract_price(text),
            size_sqm=parse_sqm(_match(text, r"([\d.,]+)\s*(?:m²|qm|m2)")),
            rooms=parse_rooms(_match(text, r"([\d.,]+)\s*(?:Zi(?:mmer)?|-Zi)")),
            description=text[:500],
        )


# ---------- Hilfsfunktionen ----------

_INDICATORS = [r"\bm²", r"\bqm\b", r"€", r"Zimmer", r"\bZi\b"]
_INDICATOR_RE = re.compile("|".join(_INDICATORS), re.IGNORECASE)


def _looks_like_listing(text: str) -> bool:
    if len(text) < 30 or len(text) > 5000:
        return False
    return len(_INDICATOR_RE.findall(text)) >= 2


def _filter_nested(blocks: list[Tag]) -> list[Tag]:
    result = []
    for b in blocks:
        has_child = any(other is not b and other in b.descendants for other in blocks)
        if not has_child:
            result.append(b)
    return result


def _extract_price(text: str) -> Optional[float]:
    return parse_price(_match(text, r"([\d.,]+)\s*€"))


def _extract_price_warm(text: str) -> Optional[float]:
    for pat in [
        r"([\d.,]+)\s*€[^\d]*(?:warm|brutto|gesamt)",
        r"(?:warm|brutto|gesamt)[^\d]*([\d.,]+)\s*€",
        r"Warmmiete[^\d]*([\d.,]+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return parse_price(m.group(1))
    return None


def _match(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None


def _domain_root(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"
