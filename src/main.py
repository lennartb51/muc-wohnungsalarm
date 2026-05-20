"""Orchestrator: lädt Config, fragt alle Adapter ab, filtert pro Profil,
schickt Pings an verschiedene Telegram-Chats, trackt Stats."""
from __future__ import annotations

import logging
import re as _re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

import yaml

from .adapters import get_all_adapters
from .filters import matches
from .notify import send_summary, send_telegram
from .profiles import Profile, load_profiles
from .state import SeenStore
from .stats import StatsStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "data" / "seen.json"
STATS_PATH = ROOT / "data" / "stats.json"
STATS_MD_PATH = ROOT / "data" / "STATS.md"

ADAPTER_PARALLELISM = 8


def _fingerprint(listing) -> str:
    """Cross-Source-Dedupe-Schlüssel: Title-Stamm + Größe + Preisbucket (50€)."""
    title_stem = _re.sub(r"[^a-zäöüß0-9]+", "", (listing.title or "").lower())[:40]
    size = round(listing.size_sqm) if listing.size_sqm else 0
    price = (listing.price_warm or listing.price_cold or 0)
    price_bucket = int(price / 50) * 50 if price else 0
    return f"{title_stem}|{size}|{price_bucket}"


def _cross_source_dedupe(all_listings: list) -> list:
    """Entfernt das gleiche Listing das über mehrere Aggregatoren reinkommt."""
    seen_fp = set()
    deduped = []
    duplicates = 0
    for l in all_listings:
        fp = _fingerprint(l)
        if len(fp.split("|")[0]) < 5 and not (l.size_sqm and (l.price_warm or l.price_cold)):
            deduped.append(l)
            continue
        if fp in seen_fp:
            duplicates += 1
            continue
        seen_fp.add(fp)
        deduped.append(l)
    if duplicates:
        logger.info(f"Cross-Source-Dedupe: {duplicates} Duplikate entfernt → {len(deduped)} unique")
    return deduped


def _process_profile(
    profile: Profile,
    all_listings: list,
    state_path: Path,
) -> tuple[int, int]:
    """Filtert + sendet für ein einzelnes Profil. Returnt (matched, sent)."""
    store = SeenStore(state_path, profile=profile.name)

    new_listings = [l for l in all_listings if store.is_new(l.uid)]
    matched = [l for l in new_listings if matches(l, profile.filter_config)]

    prefix = f"[{profile.name}]" if profile.name != "default" else ""
    logger.info(f"{prefix} Davon {len(new_listings)} neu, {len(matched)} passen "
                f"(chat={profile.chat_id})")

    for m in matched:
        price = m.price_warm or m.price_cold
        price_str = f"{price:.0f}€" if price else "?€"
        size_str = f"{m.size_sqm:.0f}m²" if m.size_sqm else "?m²"
        rooms_str = f"{m.rooms:g}Zi" if m.rooms else "?Zi"
        loc = m.district or m.postcode or "Lage?"
        logger.info(f"  ✔ {prefix}[{m.source}] {m.title[:60]} — "
                    f"{rooms_str} {size_str} {price_str} — {loc}")

    sent_uids: set[str] = set()
    if matched:
        sent_uids = send_telegram(matched, chat_id=profile.chat_id)
        logger.info(f"{prefix} 📨 {len(sent_uids)}/{len(matched)} versendet")

    matched_uids = {m.uid for m in matched}
    for l in new_listings:
        if l.uid not in matched_uids:
            store.mark_seen(l.uid)
        elif l.uid in sent_uids:
            store.mark_seen(l.uid)

    store.save()
    return len(matched), len(sent_uids)


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    logger.info(f"Filter: max_price={cfg.get('max_price')}, "
                f"min_sqm={cfg.get('min_sqm')}, "
                f"districts={len(cfg.get('districts_whitelist') or [])}")

    profiles = load_profiles(cfg)
    if len(profiles) > 1:
        logger.info(f"Multi-Profile aktiv: {[p.name for p in profiles]}")

    stats = StatsStore(STATS_PATH)

    disabled = set(cfg.get("disabled_adapters") or [])
    adapters = get_all_adapters()
    logger.info(f"{len(adapters)} Adapter aktiv (parallel: {ADAPTER_PARALLELISM})")
    for adapter in adapters:
        if adapter.name in disabled:
            adapter.enabled = False

    all_listings = []
    scrape_counts: Dict[str, int] = {}
    errors: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=ADAPTER_PARALLELISM) as pool:
        future_to_adapter = {
            pool.submit(adapter.safe_fetch): adapter for adapter in adapters
        }
        for future in as_completed(future_to_adapter):
            adapter = future_to_adapter[future]
            try:
                listings = future.result()
                scrape_counts[adapter.name] = len(listings)
                all_listings.extend(listings)
            except Exception as e:
                logger.warning(f"[{adapter.name}] Crashed: {e}")
                scrape_counts[adapter.name] = 0
                errors[adapter.name] = str(e)

    logger.info(f"Insgesamt {len(all_listings)} Listings über alle Quellen")
    all_listings = _cross_source_dedupe(all_listings)

    total_matched = 0
    total_sent = 0
    for profile in profiles:
        m, s = _process_profile(profile, all_listings, STATE_PATH)
        total_matched += m
        total_sent += s

    stats.record_run(
        scrape_counts=scrape_counts,
        matched_count=total_matched,
        sent_count=total_sent,
        errors=errors,
    )

    try:
        STATS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATS_MD_PATH.write_text(stats.generate_markdown())
    except Exception as e:
        logger.warning(f"STATS.md konnte nicht geschrieben werden: {e}")

    summary_chat = profiles[0].chat_id if profiles else None
    if summary_chat:
        if stats.should_send_daily_summary():
            if send_summary(stats.summary_text("daily"), chat_id=summary_chat):
                stats.mark_daily_summary_sent()
                logger.info("📊 Daily-Summary an Telegram versendet")
        if stats.should_send_weekly_summary():
            if send_summary(stats.summary_text("weekly"), chat_id=summary_chat):
                stats.mark_weekly_summary_sent()
                logger.info("📊 Weekly-Summary an Telegram versendet")

    stats.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
