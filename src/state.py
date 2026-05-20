"""Persistenter State der schon gesehenen Listings.

Wir speichern als JSON im Repo und committen es nach jedem Run zurück.
Einfach, debugbar, keine externe DB nötig.

State-Format (v3, multi-profile):
{
  "_profiles": {
    "default": {"seen": {uid: timestamp, ...}, "saved_at": ts},
    "friend1": {"seen": {...}, ...}
  }
}

State-Format (v2, single-profile, legacy):
{"seen": {uid: timestamp, ...}}

State-Format (v1, älteste):
{"seen": [uid1, uid2, ...]}

Beim Laden wird automatisch in das neueste Format migriert. Migration ist
verlustfrei: alte Single-Profile-States werden zum "default"-Profil.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class SeenStore:
    def __init__(self, path: Path, profile: str = "default"):
        self.path = Path(path)
        self.profile = profile
        self._all_profiles: Dict[str, Dict[str, float]] = {}  # name → {uid → ts}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            logger.info(f"State-Datei {self.path} existiert nicht, starte leer")
            return
        try:
            data = json.loads(self.path.read_text())

            # v3: Multi-profile Format
            if isinstance(data, dict) and "_profiles" in data:
                self._all_profiles = {
                    pname: {uid: float(ts) for uid, ts in pdata.get("seen", {}).items()}
                    for pname, pdata in data["_profiles"].items()
                }
                count = len(self._all_profiles.get(self.profile, {}))
                logger.info(f"State geladen (multi-profile, '{self.profile}'): "
                            f"{count} bekannte UIDs")
                return

            # v2/v1: Single-Profile Legacy → wird zu "default"
            seen_raw = data.get("seen", [])
            if isinstance(seen_raw, list):
                # v1: Liste ohne Timestamps
                now = time.time()
                default_seen = {uid: now for uid in seen_raw}
                logger.info(f"State geladen (v1 → migriert): "
                            f"{len(default_seen)} bekannte UIDs")
            elif isinstance(seen_raw, dict):
                # v2: dict mit Timestamps
                default_seen = {uid: float(ts) for uid, ts in seen_raw.items()}
                logger.info(f"State geladen (v2 → migriert): "
                            f"{len(default_seen)} bekannte UIDs")
            else:
                logger.warning(f"State hat unbekanntes Format, starte leer")
                default_seen = {}
            self._all_profiles = {"default": default_seen}
        except Exception as e:
            logger.warning(f"State konnte nicht geladen werden: {e}, starte leer")
            self._all_profiles = {}

    @property
    def _seen(self) -> Dict[str, float]:
        """Bequemer Zugriff auf das eigene Profil. Wird live aus _all_profiles
        gelesen, sodass Updates aus anderen Profilen sichtbar bleiben."""
        return self._all_profiles.setdefault(self.profile, {})

    def is_new(self, uid: str) -> bool:
        return uid not in self._seen

    def mark_seen(self, uid: str) -> None:
        # Bei Re-Mark wird der Timestamp aktualisiert — das hält die UID
        # "frisch" und schützt sie vor dem Cap-Drop.
        self._all_profiles.setdefault(self.profile, {})[uid] = time.time()

    def save(self, max_keep: int = 20000) -> None:
        """Speichert ALLE Profile zurück. max_keep gilt pro Profil.

        Beim Cap werden die UIDs mit den ÄLTESTEN Timestamps verworfen.
        """
        for pname, seen in list(self._all_profiles.items()):
            if len(seen) > max_keep:
                sorted_items = sorted(seen.items(), key=lambda x: -x[1])[:max_keep]
                self._all_profiles[pname] = dict(sorted_items)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        out = {
            "_profiles": {
                pname: {"seen": pdata}
                for pname, pdata in self._all_profiles.items()
            }
        }
        self.path.write_text(json.dumps(out, indent=2))
        own_count = len(self._all_profiles.get(self.profile, {}))
        total_count = sum(len(p) for p in self._all_profiles.values())
        if len(self._all_profiles) > 1:
            logger.info(f"State gespeichert: {own_count} UIDs ('{self.profile}'), "
                        f"{total_count} gesamt über {len(self._all_profiles)} Profile")
        else:
            logger.info(f"State gespeichert: {own_count} UIDs")
