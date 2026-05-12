"""Filter, die ein Listing entweder durchlassen oder verwerfen."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, Optional

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

    # --- Lage-Check (PLZ ODER Stadtteil) ---
    if not _location_passes(listing, cfg):
        return False  # Reject-Log schon in _location_passes

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


def _location_passes(listing: Listing, cfg: Dict[str, Any]) -> bool:
    """Lage-Filter: PLZ ODER Stadtteil muss matchen.

    Regeln:
    - PLZ in Whitelist           → DURCH (egal ob Stadtteil match)
    - PLZ nicht in Whitelist     → Stadtteil-Backup-Check
    - PLZ unbekannt              → Stadtteil-Backup-Check
    - Keine PLZ, kein Stadtteil-Match:
        - postcode_strict=true   → RAUS
        - postcode_strict=false  → Stadtteil-Whitelist entscheidet
    - Beide Whitelists leer      → DURCH
    """
    plz_wl = cfg.get("postcode_whitelist")
    district_wl = cfg.get("districts_whitelist") or []

    # Kein Lage-Filter aktiv → durch
    if not plz_wl and not district_wl:
        return True

    plz_check: Optional[bool] = None   # True/False/None (None = unentscheidbar)
    district_check: Optional[bool] = None

    if plz_wl and listing.postcode:
        plz_check = _postcode_in_whitelist(listing.postcode, plz_wl)

    if district_wl:
        haystack = " ".join(filter(None, [
            listing.district, listing.address,
            listing.title, listing.description,
        ])).lower()
        # Word-Boundary-Match, damit z.B. "Au" nicht in "Hausverwaltung" matched
        district_check = any(
            re.search(rf"\b{re.escape(w.lower())}\b", haystack)
            for w in district_wl
        )

    # PLZ in Whitelist → durch (Stadtteil ignoriert)
    if plz_check is True:
        return True

    # PLZ nicht in Whitelist, aber Stadtteil-Match → durch (Backup)
    if district_check is True:
        return True

    # Hier sind wir nur, wenn weder PLZ noch Stadtteil positiv waren.
    # Beide gleichzeitig unentscheidbar (= keine PLZ + keine Stadtteil-Whitelist) →
    # nur dann durchlassen wenn postcode_strict NICHT gesetzt
    if plz_check is None and not district_wl:
        if cfg.get("postcode_strict"):
            return _reject(listing, "Keine PLZ erkennbar (strict mode)")
        return True

    reason = (
        f"Lage nicht in Whitelist (PLZ={listing.postcode or 'unbekannt'}, "
        f"Stadtteil-Match={district_check})"
    )
    return _reject(listing, reason)


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
    if isinstance(entry, int):
        return plz == entry
    if isinstance(entry, (list, tuple)) and len(entry) == 2:
        try:
            return int(entry[0]) <= plz <= int(entry[1])
        except (TypeError, ValueError):
            return False
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
