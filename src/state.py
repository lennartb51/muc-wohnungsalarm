"""Persistenter State der schon gesehenen Listings.

Wir speichern als JSON im Repo und committen es nach jedem Run zurück.
Einfach, debugbar, keine externe DB nötig.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class SeenStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._seen: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            logger.info(f"State-Datei {self.path} existiert nicht, starte leer")
            return
        try:
            data = json.loads(self.path.read_text())
            self._seen = set(data.get("seen", []))
            logger.info(f"State geladen: {len(self._seen)} bekannte UIDs")
        except Exception as e:
            logger.warning(f"State konnte nicht geladen werden: {e}, starte leer")
            self._seen = set()

    def is_new(self, uid: str) -> bool:
        return uid not in self._seen

    def mark_seen(self, uid: str) -> None:
        self._seen.add(uid)

    def save(self, max_keep: int = 20000) -> None:
        """Speichert State zurück. max_keep verhindert unbegrenztes Wachstum."""
        seen_list = sorted(self._seen)[-max_keep:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"seen": seen_list}, indent=2))
        logger.info(f"State gespeichert: {len(seen_list)} UIDs")
