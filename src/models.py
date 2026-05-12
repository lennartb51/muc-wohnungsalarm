"""Normalisiertes Datenmodell für ein Wohnungsangebot."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Listing:
    source: str
    external_id: str
    url: str
    title: str

    price_warm: Optional[float] = None
    price_cold: Optional[float] = None
    size_sqm: Optional[float] = None
    rooms: Optional[float] = None

    district: Optional[str] = None
    address: Optional[str] = None
    postcode: Optional[str] = None  # auto-detected aus address/district/title
    description: Optional[str] = None

    has_balcony: Optional[bool] = None
    has_kitchen: Optional[bool] = None

    posted_at: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if self.has_balcony is None:
            self.has_balcony = _detect_balcony(self.title, self.description)
        if self.has_kitchen is None:
            self.has_kitchen = _detect_kitchen(self.title, self.description)
        if self.postcode is None:
            # WICHTIG: PLZ nur aus expliziten Lage-Feldern, NICHT aus description.
            # Sonst riskieren wir die Hausverwalter-PLZ statt der Wohnungs-PLZ
            # (z.B. wenn im Block-Text "Kontakt: HV Müller, Trudering 81825" steht).
            self.postcode = _detect_postcode(
                self.address, self.district, self.title
            )

    @property
    def uid(self) -> str:
        raw = f"{self.source}:{self.external_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["uid"] = self.uid
        return d


# ---------- Feature-Detection ----------

_BALCONY_NEG = re.compile(r"ohne\s+(balkon|terrasse|loggia)", re.IGNORECASE)
_BALCONY_POS = re.compile(
    r"\b(balkon|loggia|dachterrasse|terrasse|s[üu]dbalkon|westbalkon|ostbalkon|nordbalkon)\b",
    re.IGNORECASE,
)
_KITCHEN_NEG = re.compile(
    r"ohne\s+(einbauk[üu]che|ebk|k[üu]che|k[üu]chenzeile)", re.IGNORECASE,
)
_KITCHEN_POS = re.compile(
    r"\b(einbauk[üu]che|ebk|wohnk[üu]che|k[üu]chenzeile|k[üu]che(?!nzeile)|pantry)\b",
    re.IGNORECASE,
)

# Münchner PLZ-Range 80xxx / 81xxx
_POSTCODE_RE = re.compile(r"\b(8[01]\d{3})\b")


def _detect_balcony(title: Optional[str], desc: Optional[str]) -> Optional[bool]:
    text = f"{title or ''} {desc or ''}".strip()
    if not text:
        return None
    if _BALCONY_NEG.search(text):
        return False
    if _BALCONY_POS.search(text):
        return True
    return None


def _detect_kitchen(title: Optional[str], desc: Optional[str]) -> Optional[bool]:
    text = f"{title or ''} {desc or ''}".strip()
    if not text:
        return None
    if _KITCHEN_NEG.search(text):
        return False
    if _KITCHEN_POS.search(text):
        return True
    return None


def _detect_postcode(*fields: Optional[str]) -> Optional[str]:
    """Sucht eine 5-stellige Münchner PLZ in den übergebenen Feldern.

    Felder werden in Reihenfolge geprüft (address > district > title).
    description wird BEWUSST NICHT übergeben — dort könnte die
    Hausverwalter-Adresse mit eigener PLZ stehen.
    """
    for f in fields:
        if not f:
            continue
        m = _POSTCODE_RE.search(f)
        if m:
            return m.group(1)
    return None
