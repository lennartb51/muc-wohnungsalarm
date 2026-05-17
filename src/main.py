"""Orchestrator: lädt Config, fragt alle Adapter ab, filtert, benachrichtigt."""
from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Parallelisierung: bei N Adaptern und K Workers ungefähr N/K * pro-Adapter-Dauer.
# 8 Workers ist konservativ — vermeidet Rate-Limits + IPv4-Stacking.
ADAPTER_PARALLELISM = 8


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    logger.info(f"Filter: max_price={cfg.get('max_price')}, "
                f"min_sqm={cfg.get('min_sqm')}, "
                f"districts={len(cfg.get('districts_whitelist') or [])}")

    store = SeenStore(STATE_PATH)
    disabled = set(cfg.get("disabled_adapters") or [])

    adapters = get_all_adapters()
    logger.info(f"{len(adapters)} Adapter aktiv (parallel: {ADAPTER_PARALLELISM})")

    for adapter in adapters:
        if adapter.name in disabled:
            adapter.enabled = False

    # Parallele Adapter-Abfrage. Reihenfolge der Logs nicht mehr deterministisch.
    all_listings = []
    with ThreadPoolExecutor(max_workers=ADAPTER_PARALLELISM) as pool:
        future_to_adapter = {
            pool.submit(adapter.safe_fetch): adapter for adapter in adapters
        }
        for future in as_completed(future_to_adapter):
            try:
                listings = future.result()
                all_listings.extend(listings)
            except Exception as e:
                adapter = future_to_adapter[future]
                logger.warning(f"[{adapter.name}] Crashed: {e}")

    logger.info(f"Insgesamt {len(all_listings)} Listings über alle Quellen")

    # 1) Auf neue Listings filtern (UID nicht im State)
    new_listings = [l for l in all_listings if store.is_new(l.uid)]
    logger.info(f"Davon {len(new_listings)} neu (vorher unbekannt)")

    # 2) Auf passende Listings filtern
    matched = [l for l in new_listings if matches(l, cfg)]
    logger.info(f"Davon {len(matched)} passen zu den Kriterien")

    # Detailzeile pro Match — so weißt du welche Quelle/Wohnung durchkam
    for m in matched:
        price = m.price_warm or m.price_cold
        price_str = f"{price:.0f}€" if price else "?€"
        size_str = f"{m.size_sqm:.0f}m²" if m.size_sqm else "?m²"
        rooms_str = f"{m.rooms:g}Zi" if m.rooms else "?Zi"
        loc = m.district or m.postcode or "Lage?"
        logger.info(f"  ✔ [{m.source}] {m.title[:60]} — "
                    f"{rooms_str} {size_str} {price_str} — {loc}")

    # 3) Push raus — und nur erfolgreich versendete als "seen" markieren
    sent_uids: set[str] = set()
    if matched:
        sent_uids = send_telegram(matched)
        logger.info(f"📨 {len(sent_uids)}/{len(matched)} Telegram-Nachrichten versendet")

    # 4) State-Update:
    # - Nicht-matched Listings → als seen markieren (sonst spammen wir uns
    #   in jedem Run mit denselben nicht-passenden Inseraten zu)
    # - Matched + erfolgreich versendet → als seen markieren
    # - Matched + Versand fehlgeschlagen → NICHT markieren, beim nächsten
    #   Run nochmal versuchen (verhindert Verlust durch Telegram-Hänger)
    matched_uids = {m.uid for m in matched}
    for l in new_listings:
        if l.uid not in matched_uids:
            store.mark_seen(l.uid)
        elif l.uid in sent_uids:
            store.mark_seen(l.uid)
        # else: nicht markieren, Retry beim nächsten Run

    store.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
