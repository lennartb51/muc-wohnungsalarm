"""Persistenter State der schon gesehenen Listings.

Wir speichern als JSON im Repo und committen es nach jedem Run zurück.
Einfach, debugbar, keine externe DB nötig.

State-Format: {"seen": {uid: timestamp, ...}}
Beim Cap (max_keep) werden die UIDs mit den ÄLTESTEN Timestamps verworfen —
NICHT alphabetisch sortiert wie früher (UIDs sind Hashes, da hieße
"alphabetisch" = "zufällig").

Backwards-compat: alte States mit Format {"seen": [uid1, uid2, ...]} werden
beim Laden in das neue Format konvertiert (alle bekommen Current-Timestamp).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class SeenStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._seen: Dict[str, float] = {}  # uid → timestamp
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            logger.info(f"State-Datei {self.path} existiert nicht, starte leer")
            return
        try:
            data = json.loads(self.path.read_text())
            seen_raw = data.get("seen", [])

            if isinstance(seen_raw, list):
                # Altes Format: nur UIDs, kein Timestamp.
                # Migration: alle bekommen die aktuelle Zeit als Pseudo-Timestamp.
                # Beim ersten Cap werden sie also "zusammen" gedroppt, aber das
                # ist nach 1 Run irrelevant — neue UIDs bekommen eigene Stamps.
                now = time.time()
                self._seen = {uid: now for uid in seen_raw}
                logger.info(f"State geladen (alt → migriert): "
                            f"{len(self._seen)} bekannte UIDs")
            elif isinstance(seen_raw, dict):
                self._seen = {uid: float(ts) for uid, ts in seen_raw.items()}
                logger.info(f"State geladen: {len(self._seen)} bekannte UIDs")
            else:
                logger.warning(f"State hat unbekanntes Format ({type(seen_raw).__name__}), "
                               "starte leer")
                self._seen = {}
        except Exception as e:
            logger.warning(f"State konnte nicht geladen werden: {e}, starte leer")
            self._seen = {}

    def is_new(self, uid: str) -> bool:
        return uid not in self._seen

    def mark_seen(self, uid: str) -> None:
        # Bei Re-Mark wird der Timestamp aktualisiert — das hält die UID
        # "frisch" und schützt sie vor dem Cap-Drop.
        self._seen[uid] = time.time()

    def save(self, max_keep: int = 20000) -> None:
        """Speichert State zurück. max_keep verhindert unbegrenztes Wachstum.

        Beim Cap werden die UIDs mit den ÄLTESTEN Timestamps verworfen.
        """
        if len(self._seen) > max_keep:
            # Sortiere nach Timestamp absteigend (neueste zuerst), nimm Top max_keep
            sorted_items = sorted(
                self._seen.items(),
                key=lambda x: -x[1],
            )[:max_keep]
            self._seen = dict(sorted_items)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"seen": self._seen}, indent=2))
        logger.info(f"State gespeichert: {len(self._seen)} UIDs")
