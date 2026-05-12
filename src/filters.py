"""Filter, die ein Listing entweder durchlassen oder verwerfen."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Tuple

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

    # --- PLZ-Whitelist ---
    plz_whitelist = cfg.get("postcode_whitelist")
    if plz_whitelist:
        plz_strict = cfg.get("postcode_strict", False)
        if listing.postcode:
            if not _postcode_in_whitelist(listing.postcode, plz_whitelist):
                return _reject(listing, f"PLZ {listing.postcode} nicht in Whitelist")
        elif plz_strict:
            # Strikt: ohne PLZ raus
            return _reject(listing, "Keine PLZ erkennbar (strict mode)")
        # Sonst: ohne PLZ durchlassen (Default), damit interessante Treffer ohne
        # Adress-Info nicht verloren gehen.

    # --- Stadtteil-Whitelist ---
    whitelist = cfg.get("districts_whitelist") or []
    if whitelist:
        haystack = " ".join(filter(None, [
            listing.district, listing.address, listing.title, listing.description
        ])).lower()
        if not any(w.lower() in haystack for w in whitelist):
            return _reject(listing, "Kein Whitelist-Stadtteil")

    # --- Ausstattung (Pflicht-Flags) ---
    if cfg.get("require_balcony") and listing.has_balcony is not True:
        return _reject(listing, "Balkon Pflicht, nicht erkannt")
    if cfg.get("require_kitchen") and listing.has_kitchen is not True:
        return _reject(listing, "Küche Pflicht, nicht erkannt")

    # --- Negativ-Keywords ---
    blob = f"{listing.title} {listing.description or ''}".lower()
    for kw in cfg.get("exclude_keywords") or []:
        if kw.lower() in blob:
            return _reject(listing, f"Ausschluss-Keyword '{kw}'")

    return True


def _reject(listing: Listing, reason: str) -> bool:
    logger.debug(f"  ✗ {listing.source}/{listing.external_id}: {reason}")
    return False


# ---------- PLZ-Whitelist-Parsing ----------

def _postcode_in_whitelist(postcode: str, whitelist: Iterable) -> bool:
    """Akzeptiert: einzelne PLZ als Int oder String, Ranges als String
    'start-ende' oder als 2-Tuple/Liste [start, ende]."""
    try:
        plz = int(postcode)
    except (TypeError, ValueError):
        return False

    for entry in whitelist:
        if _entry_matches(plz, entry):
            return True
    return False


def _entry_matches(plz: int, entry: Any) -> bool:
    # Einzelne PLZ als Int
    if isinstance(entry, int):
        return plz == entry
    # Range als 2-Element-Liste/Tuple
    if isinstance(entry, (list, tuple)) and len(entry) == 2:
        try:
            return int(entry[0]) <= plz <= int(entry[1])
        except (TypeError, ValueError):
            return False
    # String: entweder "80331" oder "80331-80339"
    if isinstance(entry, str):
        entry = entry.strip()
        if "-" in entry:
            parts = entry.split("-", 1)
            try:
                return int(parts[0]) <= plz <= int(parts[1])
            except (TypeError, ValueError):
                return False
        try:
            return plz == int(entry)
        except ValueError:
            return False
    return False
