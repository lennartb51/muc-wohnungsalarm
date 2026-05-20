"""Multi-Profile-Unterstützung.

Ein Profil = (name, chat_id, filter_config). Mehrere Profile teilen sich denselben
Scrape-Run, filtern aber unabhängig und schicken an unterschiedliche Telegram-Chats.

Backward-compat:
- Wenn config.yaml KEINE `profiles:` Liste hat → implizites Default-Profil aus
  Top-Level-Filter-Keys + TELEGRAM_CHAT_ID env var.
- Wenn `profiles:` definiert ist → jedes Profil ist eigenständig, top-level Filter
  fungieren als Defaults die Profil-Keys übersteuern können (aber nicht müssen).
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Filter-Keys die pro Profil überschrieben werden können. Andere Config-Keys
# (z.B. disabled_adapters) sind global.
FILTER_KEYS = (
    "max_price", "min_price",
    "min_sqm", "max_sqm",
    "min_rooms", "max_rooms",
    "districts_whitelist", "districts_blacklist",
    "postcode_whitelist", "postcode_strict",
    "exclude_keywords", "include_keywords",
    "require_balkon", "require_einbaukueche",
)


@dataclass
class Profile:
    """Ein Empfänger mit eigenen Filter-Kriterien."""
    name: str
    chat_id: str                     # Telegram chat_id (kann auch group_id sein)
    filter_config: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Profile(name={self.name!r}, chat_id={self.chat_id!r})"


def _resolve_env_refs(value: Any) -> Any:
    """Erlaubt ${ENV_VAR} in YAML-Strings. Beispiel:
    chat_id: ${TELEGRAM_CHAT_ID}  → wird zu os.environ['TELEGRAM_CHAT_ID']
    """
    if not isinstance(value, str):
        return value
    m = re.fullmatch(r"\$\{([A-Z_][A-Z0-9_]*)\}", value.strip())
    if not m:
        return value
    env_name = m.group(1)
    resolved = os.environ.get(env_name)
    if resolved is None:
        logger.warning(f"ENV-Variable {env_name} nicht gesetzt — Wert bleibt leer")
        return ""
    return resolved


def load_profiles(cfg: Dict[str, Any]) -> List[Profile]:
    """Baut die Profil-Liste aus dem Config-Dict.

    Reihenfolge der Auflösung:
    1. Wenn cfg["profiles"] vorhanden ist → jedes Element wird zu einem Profil.
       Top-Level-Keys (max_price etc.) sind Defaults, Profil-Keys überschreiben.
    2. Sonst → ein implizites Default-Profil mit chat_id aus env TELEGRAM_CHAT_ID
       und den Top-Level-Filter-Keys als Filter.
    """
    top_filter = {k: cfg[k] for k in FILTER_KEYS if k in cfg}

    raw = cfg.get("profiles")
    if not raw:
        # Legacy-Modus: ein implizites Default-Profil
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not chat_id:
            logger.warning("⚠️  TELEGRAM_CHAT_ID nicht gesetzt — Default-Profil hat keine chat_id")
        return [Profile(name="default", chat_id=chat_id, filter_config=top_filter)]

    profiles: List[Profile] = []
    for i, raw_p in enumerate(raw):
        if not isinstance(raw_p, dict):
            logger.warning(f"profiles[{i}] ist kein Dict, ignoriert")
            continue
        name = raw_p.get("name") or f"profile_{i}"
        chat_id = _resolve_env_refs(raw_p.get("chat_id", ""))
        if not chat_id:
            logger.warning(f"Profil '{name}' hat keine chat_id — wird übersprungen")
            continue
        # Filter: Top-Level als Default, Profil-spezifisch überschreibt
        merged_filter = dict(top_filter)
        for k in FILTER_KEYS:
            if k in raw_p:
                merged_filter[k] = raw_p[k]
        profiles.append(Profile(
            name=str(name),
            chat_id=str(chat_id),
            filter_config=merged_filter,
        ))

    if not profiles:
        logger.error("Keine gültigen Profile in config — fallback auf Default")
        return load_profiles({k: v for k, v in cfg.items() if k != "profiles"})

    return profiles
