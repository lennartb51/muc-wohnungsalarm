"""Orchestrator: lädt Config, fragt alle Adapter ab, filtert, benachrichtigt."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

from .adapters import get_all_adapters
from .filters import matches
from .notify import send_telegram
from .state import SeenStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "data" / "seen.json"


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    logger.info(f"Filter: max_price={cfg.get('max_price')}, "
                f"min_sqm={cfg.get('min_sqm')}, "
                f"districts={len(cfg.get('districts_whitelist') or [])}")

    store = SeenStore(STATE_PATH)
    disabled = set(cfg.get("disabled_adapters") or [])

    all_listings = []
    adapters = get_all_adapters()
    logger.info(f"{len(adapters)} Adapter aktiv")

    for adapter in adapters:
        if adapter.name in disabled:
            adapter.enabled = False
        all_listings.extend(adapter.safe_fetch())

    logger.info(f"Insgesamt {len(all_listings)} Listings über alle Quellen")

    # 1) Auf neue Listings filtern (UID nicht im State)
    new_listings = [l for l in all_listings if store.is_new(l.uid)]
    logger.info(f"Davon {len(new_listings)} neu (vorher unbekannt)")

    # 2) Auf passende Listings filtern
    matched = [l for l in new_listings if matches(l, cfg)]
    logger.info(f"Davon {len(matched)} passen zu den Kriterien")

    # 3) Push raus
    if matched:
        sent = send_telegram(matched)
        logger.info(f"📨 {sent}/{len(matched)} Telegram-Nachrichten versendet")

    # 4) ALLE neuen Listings als gesehen markieren — sonst spammen wir uns mit
    #    nicht-passenden Inseraten in jedem Run zu.
    for l in new_listings:
        store.mark_seen(l.uid)

    store.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
