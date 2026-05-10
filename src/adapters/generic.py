"""Generic-Adapter für simple Quellen (Genossenschaften, Hausverwaltungen).

Pattern: eine Liste-Seite mit Wohnungs-Cards/-Blöcken. Jeder Block enthält
irgendwo Text wie "3-Zimmer, 65 m², 1.450 € warm" und einen Link.

Konfigurierbar pro Instanz, daher kein eigener Adapter pro Quelle nötig.
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

# Default-Selektoren, die bei vielen kleinen Sites greifen
DEFAULT_SELECTORS = [
    "article",
    "[class*='wohnung']",
    "[class*='angebot']",
    "[class*='objekt']",
    "[class*='listing']",
    "[class*='exposé']",
    "[class*='expose']",
    ".card",
    ".news-list-item",
    "li.list-item",
]


class GenericTextAdapter(Adapter):
    """Konfigurierbarer Adapter für simple Quellen.

    Args:
        name: Anzeigename der Quelle ("WGMW", "Rohrer", ...).
        list_url: URL der Listing-Seite.
        selectors: CSS-Selektoren für Listings-Blöcke. Default ist eine breite
                   Auswahl, die bei den meisten Sites greift.
        base_url: Für die Auflösung relativer Links. Default = Domain von list_url.
        require_link: Wenn True, werden nur Blöcke mit eigenem <a> akzeptiert.
                      Manche Sites listen Wohnungen rein als Text ohne Detail-Link.
    """

    rate_limit_seconds = 3.0

    def __init__(
        self,
        name: str,
        list_url: str,
        selectors: Optional[List[str]] = None,
        base_url: Optional[str] = None,
        require_link: bool = True,
    ):
        super().__init__()
        self.name = name
        self.list_url = list_url
        self.selectors = selectors or DEFAULT_SELECTORS
        self.base_url = base_url or _domain_root(list_url)
        self.require_link = require_link

    def fetch(self) -> Iterable[Listing]:
        try:
            r = self.get(self.list_url)
        except Exception as e:
            logger.warning(f"[{self.name}] Request failed: {e}")
            return

        if r.status_code != 200:
            logger.warning(f"[{self.name}] HTTP {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Sammle alle Blöcke, die wie ein Listing aussehen (haben m²/€/Zimmer)
        candidates: list[Tag] = []
        seen_blocks = set()

        for sel in self.selectors:
            for block in soup.select(sel):
                block_id = id(block)
                if block_id in seen_blocks:
                    continue
                text = block.get_text(" ", strip=True)
                if _looks_like_listing(text):
                    candidates.append(block)
                    seen_blocks.add(block_id)

        # Dedupe: wenn Block A einen anderen Listing-Block enthält, nimm nur den inneren
        candidates = _filter_nested(candidates)

        for block in candidates:
            listing = self._parse_block(block)
            if listing:
                yield listing

    def _parse_block(self, block: Tag) -> Optional[Listing]:
        text = block.get_text(" ", strip=True)
        if len(text) < 20:
            return None

        # Link finden
        link = block.find("a", href=True)
        if self.require_link and not link:
            return None

        href = link["href"] if link else self.list_url
        url = urljoin(self.base_url, href)

        # Titel: Link-Text, oder erster Heading, oder erste 80 Zeichen
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

        # External ID aus URL ableiten, sonst aus Text-Hash
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
    """Heuristik: Block sieht aus wie ein Wohnungsangebot."""
    if len(text) < 30 or len(text) > 5000:
        return False
    matches = _INDICATOR_RE.findall(text)
    return len(matches) >= 2  # Mindestens 2 typische Marker (z.B. m² + €)


def _filter_nested(blocks: list[Tag]) -> list[Tag]:
    """Wenn Block A Block B enthält und beide Listings sind, behalte nur B."""
    result = []
    for b in blocks:
        # Hat dieser Block einen Listing-Nachfahren in der Liste?
        has_child = any(
            other is not b and other in b.descendants
            for other in blocks
        )
        if not has_child:
            result.append(b)
    return result


def _extract_price(text: str) -> Optional[float]:
    """Erste Eurozahl im Text."""
    return parse_price(_match(text, r"([\d.,]+)\s*€"))


def _extract_price_warm(text: str) -> Optional[float]:
    """Warmmiete, wenn explizit als solche markiert."""
    # Pattern: "1.450 € warm" oder "warm: 1.450 €" oder "Warmmiete 1450"
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
