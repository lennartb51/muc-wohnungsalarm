"""Persistente Statistik pro Adapter über alle Runs hinweg.

Wird in data/stats.json gespeichert plus auto-generierte data/STATS.md für
GitHub-View. main.py ruft record_run() am Ende jedes Runs auf.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StatsStore:
    """Persistente Per-Adapter-Statistik."""

    def __init__(self, path: Path):
        self.path = path
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"_meta": {}, "adapters": {}}
        try:
            return json.loads(self.path.read_text())
        except Exception as e:
            logger.warning(f"Stats konnten nicht geladen werden: {e}")
            return {"_meta": {}, "adapters": {}}

    def record_run(
        self,
        scrape_counts: Dict[str, int],
        matched_count: int,
        sent_count: int,
        errors: Optional[Dict[str, str]] = None,
    ) -> None:
        """Buchführung am Ende eines Runs.

        scrape_counts: {adapter_name: anzahl_listings_gefunden}
        errors: {adapter_name: fehlermeldung} (optional)
        """
        errors = errors or {}
        now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")

        meta = self._data.setdefault("_meta", {})
        meta.setdefault("first_run", now_str)
        meta["last_run"] = now_str
        meta["total_runs"] = meta.get("total_runs", 0) + 1
        meta["last_matched"] = matched_count
        meta["last_sent"] = sent_count
        meta["last_scraped"] = sum(scrape_counts.values())

        adapters = self._data.setdefault("adapters", {})
        all_names = set(scrape_counts.keys()) | set(errors.keys())

        for name in all_names:
            entry = adapters.setdefault(name, {
                "scraped_total": 0,
                "runs_total": 0,
                "runs_with_listings": 0,
                "first_seen": now_str,
                "last_active": None,
                "consecutive_empty": 0,
                "consecutive_errors": 0,
                "last_error": None,
                "last_error_time": None,
            })
            entry["runs_total"] += 1
            count = scrape_counts.get(name, 0)
            entry["scraped_total"] += count

            if name in errors:
                entry["consecutive_errors"] += 1
                entry["last_error"] = errors[name][:200]
                entry["last_error_time"] = now_str
            else:
                entry["consecutive_errors"] = 0

            if count > 0:
                entry["runs_with_listings"] += 1
                entry["last_active"] = now_str
                entry["consecutive_empty"] = 0
            else:
                entry["consecutive_empty"] += 1

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    # --- Summary-Trigger ---

    @property
    def total_runs(self) -> int:
        return self._data.get("_meta", {}).get("total_runs", 0)

    @property
    def last_run_stats(self) -> Dict[str, int]:
        meta = self._data.get("_meta", {})
        return {
            "scraped": meta.get("last_scraped", 0),
            "matched": meta.get("last_matched", 0),
            "sent": meta.get("last_sent", 0),
        }

    def _last_summary_time(self, kind: str) -> Optional[datetime]:
        ts = self._data.get("_meta", {}).get(f"last_{kind}_summary")
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None

    def should_send_daily_summary(self, now: Optional[datetime] = None) -> bool:
        """True wenn seit der letzten Daily-Summary ein neuer Kalendertag begonnen hat
        UND der aktuelle Run nach 08:00 UTC ist (gibt Aggregations-Fenster)."""
        now = now or datetime.now(timezone.utc)
        if now.hour < 8:
            return False
        last = self._last_summary_time("daily")
        if not last:
            return True
        return now.date() > last.date()

    def should_send_weekly_summary(self, now: Optional[datetime] = None) -> bool:
        """True wenn >= 7 Tage seit letzter Weekly-Summary."""
        now = now or datetime.now(timezone.utc)
        last = self._last_summary_time("weekly")
        if not last:
            return now.weekday() == 6 and now.hour >= 18  # Sonntag ab 18:00 UTC
        return (now - last).days >= 7

    def mark_daily_summary_sent(self) -> None:
        self._data.setdefault("_meta", {})["last_daily_summary"] = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
        )

    def mark_weekly_summary_sent(self) -> None:
        self._data.setdefault("_meta", {})["last_weekly_summary"] = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
        )

    # --- Markdown-Generation ---

    def generate_markdown(self) -> str:
        """Erzeugt STATS.md - sortierte Tabelle für GitHub."""
        meta = self._data.get("_meta", {})
        adapters = self._data.get("adapters", {})
        now = datetime.now(timezone.utc)

        lines = [
            "# Adapter-Statistik",
            "",
            f"_Auto-generiert. Letzter Run: {meta.get('last_run', '?')}_  ",
            f"_Total Runs: {meta.get('total_runs', 0)}_  ",
            f"_Letzte Run-Zusammenfassung: {meta.get('last_scraped', 0)} scraped, "
            f"{meta.get('last_matched', 0)} matches, {meta.get('last_sent', 0)} sent_",
            "",
            "## Adapter-Übersicht",
            "",
            "| Adapter | Scraped (Σ) | Avg/Run | Runs aktiv | Letzte Aktivität | Status |",
            "|---|---:|---:|---|---|---|",
        ]

        def status_icon(entry: Dict[str, Any]) -> str:
            if entry.get("consecutive_errors", 0) >= 5:
                return f"🔴 broken"
            if entry.get("scraped_total", 0) == 0:
                return "⚪ leer (nie aktiv)"
            if entry.get("consecutive_empty", 0) > 100:
                return "🟡 inaktiv (lange leer)"
            return "🟢 aktiv"

        def last_active_str(entry: Dict[str, Any]) -> str:
            la = entry.get("last_active")
            if not la:
                return "nie"
            try:
                dt = datetime.fromisoformat(la)
                delta = now - dt
                mins = delta.total_seconds() / 60
                if mins < 60:
                    return f"vor {int(mins)}min"
                if mins < 1440:
                    return f"vor {int(mins/60)}h"
                return f"vor {int(mins/1440)}d"
            except Exception:
                return la

        # Sortierung: aktive zuerst (nach scraped_total absteigend), dann broken, dann leer
        def sort_key(item):
            name, entry = item
            scraped = entry.get("scraped_total", 0)
            errs = entry.get("consecutive_errors", 0)
            # Tuple: (gruppe, -scraped, name)
            # gruppe 0=aktiv, 1=broken, 2=leer
            if errs >= 5:
                grp = 1
            elif scraped == 0:
                grp = 2
            else:
                grp = 0
            return (grp, -scraped, name.lower())

        sorted_items = sorted(adapters.items(), key=sort_key)

        for name, entry in sorted_items:
            scraped = entry.get("scraped_total", 0)
            runs = entry.get("runs_total", 0)
            runs_active = entry.get("runs_with_listings", 0)
            avg = scraped / runs if runs > 0 else 0
            lines.append(
                f"| {name} | {scraped} | {avg:.1f} | "
                f"{runs_active}/{runs} | {last_active_str(entry)} | "
                f"{status_icon(entry)} |"
            )

        # Broken-Detail
        broken = [(n, e) for n, e in adapters.items()
                  if e.get("consecutive_errors", 0) >= 5]
        if broken:
            lines.extend([
                "",
                "## Broken-Adapter (Detail)",
                "",
            ])
            for name, e in sorted(broken, key=lambda x: x[0].lower()):
                err = e.get("last_error", "?")
                lines.append(f"- **{name}**: `{err[:150]}`")

        return "\n".join(lines) + "\n"

    def summary_text(self, kind: str = "daily") -> str:
        """Kurzformat für Telegram. kind = daily | weekly."""
        meta = self._data.get("_meta", {})
        adapters = self._data.get("adapters", {})
        active = sum(1 for e in adapters.values() if e.get("scraped_total", 0) > 0)
        broken = sum(1 for e in adapters.values() if e.get("consecutive_errors", 0) >= 5)
        empty = sum(1 for e in adapters.values() if e.get("scraped_total", 0) == 0)

        if kind == "daily":
            return (
                f"📊 <b>Daily Stats</b>\n"
                f"Run #{meta.get('total_runs', 0)} — "
                f"{meta.get('last_scraped', 0)} scraped, "
                f"{meta.get('last_matched', 0)} matches, "
                f"{meta.get('last_sent', 0)} sent\n"
                f"🟢 {active} aktiv · 🔴 {broken} broken · ⚪ {empty} leer"
            )

        # Weekly: Top-Performer
        top = sorted(
            adapters.items(),
            key=lambda x: -x[1].get("scraped_total", 0),
        )[:10]
        top_lines = "\n".join(
            f"  · {name}: {e.get('scraped_total', 0)} ({e.get('scraped_total', 0) / max(e.get('runs_total', 1), 1):.0f}/run)"
            for name, e in top if e.get("scraped_total", 0) > 0
        )
        return (
            f"📊 <b>Weekly Stats</b>\n"
            f"{meta.get('total_runs', 0)} Runs total\n"
            f"🟢 {active} aktiv · 🔴 {broken} broken · ⚪ {empty} leer\n"
            f"\n<b>Top-Quellen (Σ-scraped):</b>\n{top_lines}"
        )
