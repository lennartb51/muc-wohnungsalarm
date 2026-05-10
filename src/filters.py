"""Filter, die ein Listing entweder durchlassen oder verwerfen."""
from __future__ import annotations

import logging
from typing import Any, Dict

from .models import Listing

logger = logging.getLogger(__name__)


def matches(listing: Listing, cfg: Dict[str, Any]) -> bool:
    """True, wenn das Listing alle Kriterien erfüllt."""

    # --- Preis ---
    price = listing.price_warm or listing.price_cold
    max_price = cfg.get("max_price")
    if max_price and price and price > max_price:
        return _reject(listing, f"Preis {price} > {max_price}")

    min_price = cfg.get("min_price")
    if min_price and price and price < min_price:
        # Sehr niedrige Preise sind oft Scam-Anzeigen
        return _reject(listing, f"Preis {price} < {min_price} (Scam-Verdacht)")

    # --- Größe ---
    if listing.size_sqm:
        if (m := cfg.get("min_sqm")) and listing.size_sqm < m:
            return _reject(listing, f"Größe {listing.size_sqm} < {m}")
        if (m := cfg.get("max_sqm")) and listing.size_sqm > m:
            return _reject(listing, f"Größe {listing.size_sqm} > {m}")

    # --- Zimmer ---
    if listing.rooms:
        if (r := cfg.get("min_rooms")) and listing.rooms < r:
            return _reject(listing, f"Zimmer {listing.rooms} < {r}")
        if (r := cfg.get("max_rooms")) and listing.rooms > r:
            return _reject(listing, f"Zimmer {listing.rooms} > {r}")

    # --- Stadtteil-Whitelist (greift nur wenn definiert) ---
    whitelist = cfg.get("districts_whitelist") or []
    if whitelist:
        haystack = " ".join(filter(None, [
            listing.district, listing.address, listing.title, listing.description
        ])).lower()
        if not any(w.lower() in haystack for w in whitelist):
            return _reject(listing, "Kein Whitelist-Stadtteil")

    # --- Negativ-Keywords (in Titel/Beschreibung) ---
    blob = f"{listing.title} {listing.description or ''}".lower()
    for kw in cfg.get("exclude_keywords") or []:
        if kw.lower() in blob:
            return _reject(listing, f"Ausschluss-Keyword '{kw}'")

    return True


def _reject(listing: Listing, reason: str) -> bool:
    logger.debug(f"  ✗ {listing.source}/{listing.external_id}: {reason}")
    return False
