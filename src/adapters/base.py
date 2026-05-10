"""Base-Adapter, von dem alle Quell-Scraper erben."""
from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

import requests

from ..models import Listing

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class Adapter(ABC):
    """Eine Quelle (Genossenschaft, Portal, Hausverwaltung, ...)."""

    name: str = "base"  # Wird in Telegram-Nachrichten angezeigt
    rate_limit_seconds: float = 2.0  # Pause zwischen Requests, höflich bleiben
    enabled: bool = True

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._last_request: float = 0.0

    @abstractmethod
    def fetch(self) -> Iterable[Listing]:
        """Yieldet Listings. Muss von jedem konkreten Adapter implementiert sein."""
        raise NotImplementedError

    def safe_fetch(self) -> List[Listing]:
        """Wrapper mit Fehler-Isolation: ein gebrochener Adapter killt nicht den Run."""
        if not self.enabled:
            logger.info(f"[{self.name}] deaktiviert, übersprungen")
            return []
        try:
            results = list(self.fetch())
            logger.info(f"[{self.name}] {len(results)} Inserate gefunden")
            return results
        except Exception as e:
            logger.exception(f"[{self.name}] Fehler beim Fetchen: {e}")
            return []

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET mit Rate-Limit."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        kwargs.setdefault("timeout", 15)
        r = self.session.get(url, **kwargs)
        self._last_request = time.time()
        return r


# --- Hilfsfunktionen für die Adapter ---

_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def parse_number(text: Optional[str]) -> Optional[float]:
    """Extrahiert die erste Zahl aus einem String. '1.234,56 €' → 1234.56"""
    if not text:
        return None
    # Erst Tausender-Punkte raus, dann Komma → Punkt
    cleaned = text.replace(".", "").replace(",", ".")
    m = _NUM_RE.search(cleaned)
    return float(m.group(1)) if m else None


def parse_price(text: Optional[str]) -> Optional[float]:
    """Wie parse_number, aber mit Plausi-Check für Preise."""
    n = parse_number(text)
    if n is None:
        return None
    if n < 50 or n > 50000:  # Realistische Münchner Mietpreis-Range
        return None
    return n


def parse_sqm(text: Optional[str]) -> Optional[float]:
    """Größe in m² extrahieren."""
    n = parse_number(text)
    if n is None:
        return None
    if n < 5 or n > 1000:
        return None
    return n


def parse_rooms(text: Optional[str]) -> Optional[float]:
    """Zimmeranzahl extrahieren."""
    n = parse_number(text)
    if n is None:
        return None
    if n < 0.5 or n > 20:
        return None
    return n
