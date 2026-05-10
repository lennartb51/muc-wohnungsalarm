"""Normalisiertes Datenmodell für ein Wohnungsangebot."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Listing:
    source: str  # z.B. "Immowelt", "Wogeno"
    external_id: str  # Eindeutige ID innerhalb der Quelle (URL-Slug, Anzeigen-ID etc.)
    url: str
    title: str

    price_warm: Optional[float] = None
    price_cold: Optional[float] = None
    size_sqm: Optional[float] = None
    rooms: Optional[float] = None

    district: Optional[str] = None  # z.B. "Glockenbach", "Maxvorstadt"
    address: Optional[str] = None
    description: Optional[str] = None

    posted_at: Optional[str] = None  # ISO-String, falls verfügbar
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def uid(self) -> str:
        """Stabile ID über alle Runs hinweg."""
        raw = f"{self.source}:{self.external_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["uid"] = self.uid
        return d
