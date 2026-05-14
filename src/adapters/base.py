"""Base-Adapter, von dem alle Quell-Scraper erben."""
from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Iterable, List, Optional

import requests

from ..models import Listing

logger = logging.getLogger(__name__)

# Hartes Limit pro Adapter. Schützt gegen Hänger auf DNS-, TCP- oder
# read-Ebene. Adapter die mehr als 60s brauchen, sind kaputt oder
# liefern eh nichts Sinnvolles.
ADAPTER_HARD_TIMEOUT_SECONDS = 60

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
        """Wrapper mit Fehler-Isolation UND hartem Per-Adapter-Timeout.

        Jeder Adapter läuft in einem eigenen Thread mit Wall-Clock-Timeout.
        Wenn der Thread innerhalb des Limits nicht fertig wird (z.B. weil
        DNS oder Socket hängt), gibt safe_fetch() leere Liste zurück und
        der Run macht mit dem nächsten Adapter weiter. Der hängende Thread
        wird verwaist; bei Workflow-Ende kümmert sich Python um den Cleanup.
        """
        if not self.enabled:
            logger.info(f"[{self.name}] deaktiviert, übersprungen")
            return []

        executor = ThreadPoolExecutor(max_workers=1,
                                       thread_name_prefix=f"adapter-{self.name}")
        future = executor.submit(self._collect)
        try:
            results = future.result(timeout=ADAPTER_HARD_TIMEOUT_SECONDS)
            logger.info(f"[{self.name}] {len(results)} Inserate gefunden")
            return results
        except FutureTimeout:
            logger.warning(
                f"[{self.name}] Adapter-Timeout ({ADAPTER_HARD_TIMEOUT_SECONDS}s) — "
                "überspringe, Hänger läuft im Hintergrund weiter"
            )
            return []
        except Exception as e:
            logger.exception(f"[{self.name}] Fehler beim Fetchen: {e}")
            return []
        finally:
            # Nicht auf den evtl. hängenden Thread warten — sonst verlieren
            # wir den ganzen Sinn des Timeouts.
            executor.shutdown(wait=False, cancel_futures=True)

    def _collect(self) -> List[Listing]:
        """Materialisiert fetch() zu einer Liste, damit das Timeout greift."""
        return list(self.fetch())

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET mit Rate-Limit + striktem Connect+Read-Timeout."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        # (connect=5s, read=15s): bei toten Servern nicht endlos warten.
        kwargs.setdefault("timeout", (5, 15))
        r = self.session.get(url, **kwargs)
        self._last_request = time.time()
        return r


# --- Hilfsfunktionen für die Adapter ---

# Erkennt verschiedene Zahlenformate:
# - "1.234,56"  (deutsch mit Tausender-Punkt + Dezimal-Komma)
# - "1.234"     (deutsch nur Tausender-Punkt)
# - "1234,56"   (deutsch nur Dezimal-Komma)
# - "65.5"      (englisch Dezimal-Punkt, 1-2 Stellen)
# - "1500"      (keine Trenner)
_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def parse_number(text: Optional[str]) -> Optional[float]:
    """Extrahiert die erste Zahl aus einem String. Erkennt deutsches und
    englisches Format intelligent:

    - "1.234,56 €"   → 1234.56  (deutsch: Punkt=Tausender, Komma=Dezimal)
    - "1.234 €"      → 1234     (deutsch: Punkt=Tausender, 3 Stellen)
    - "1234,56 €"    → 1234.56  (deutsch: Komma=Dezimal)
    - "65.5 m²"      → 65.5     (englisch: Punkt=Dezimal, 1-2 Stellen)
    - "1.234.567"    → 1234567  (mehrere Tausender)
    - "1500"         → 1500     (keine Trenner)
    """
    if not text:
        return None
    text = text.strip()

    # Pattern 1: Deutsche Zahl mit Tausender-Punkten (immer 3 Stellen) und/oder Komma-Dezimal
    # Matched: 1.234 / 1.234,56 / 1.234.567 / 1.234.567,89 / 1234,56
    m = re.search(r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+)", text)
    if m:
        cleaned = m.group(1).replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            pass

    # Pattern 2: Englische Dezimal-Zahl (1-2 Stellen nach Punkt)
    # Matched: 65.5 / 12.50 / 1.5
    m = re.search(r"(\d+\.\d{1,2})(?!\d)", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Pattern 3: Einfache Ganzzahl ohne Trenner
    m = re.search(r"(\d+)", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    return None


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
