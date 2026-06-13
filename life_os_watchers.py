#!/usr/bin/env python3
"""Read-only watcher control plane for Shay Life OS Phase 3.

These watchers only inspect live state and emit review packets. They do not
modify launchd, cron, services, asks, or tracker state.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from shay_constants import get_shay_home

DEFAULT_COOLDOWN_SECONDS = 1800


@dataclass
class WatcherObservation:
    watcher: str
    status: str
    severity: str
    summary: str
    evidence_refs: List[str]
    metrics: Dict[str, Any]
    fingerprint: str
    recorded_at: float
    emitted: bool = False


class WatcherStateStore:
    def __init__(self, state_dir: str | Path | None = None):
        self.state_dir = Path(state_dir) if state_dir else get_shay_home() / "watcher-state"
        self.review_dir = self.state_dir / "review-packets"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)

    def should_emit(self, watcher: str, fingerprint: str, *, cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS) -> bool:
        payload = self._load_state(watcher)
        now = time.time()
        if payload.get("fingerprint") == fingerprint and (now - float(payload.get("recorded_at") or 0)) < cooldown_seconds:
            return False
        self._save_state(watcher, {"fingerprint": fingerprint, "recorded_at": now})
        return True

    def save_packet(self, observation: WatcherObservation) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(observation.recorded_at))
        path = self.review_dir / f"{observation.watcher}-{stamp}.json"
        path.write_text(json.dumps(asdict(observation), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def _state_path(self, watcher: str) -> Path:
        return self.state_dir / f"{watcher}.json"

    def _load_state(self, watcher: str) -> Dict[str, Any]:
        path = self._state_path(watcher)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_state(self, watcher: str, payload: Dict[str, Any]) -> None:
        path = self._state_path(watcher)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)


class LifeOSWatchers:
    def __init__(self, state_store: WatcherStateStore | None = None):
        self.state_store = state_store or WatcherStateStore()

    def run_all(
        self,
        *,
        shay_home: str | Path | None = None,
        obsidian_root: str | Path | None = None,
        asks_dir: str | Path | None = None,
        now: Optional[float] = None,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ) -> List[WatcherObservation]:
        now_ts = now if now is not None else time.time()
        shay_home_path = Path(shay_home) if shay_home else get_shay_home()
        obsidian_path = Path(obsidian_root) if obsidian_root else Path.home() / "famtastic" / "obsidian" / "Shay-Memory"
        asks_path = Path(asks_dir) if asks_dir else Path.home() / "famtastic" / "shay-phone" / "asks"
        observations = [
            self.observe_scheduler_health(shay_home_path, now=now_ts),
            self.observe_ask_storm(shay_home_path, asks_path, now=now_ts),
            self.observe_reflection_freshness(obsidian_path, now=now_ts),
            self.observe_lessons_sync_freshness(obsidian_path, now=now_ts),
            self.observe_external_intelligence_health(Path.home() / ".famtastic-intel-loop.log", now=now_ts),
        ]
        emitted: List[WatcherObservation] = []
        for obs in observations:
            obs.emitted = self.state_store.should_emit(obs.watcher, obs.fingerprint, cooldown_seconds=cooldown_seconds)
            if obs.emitted:
                packet_path = self.state_store.save_packet(obs)
                obs.evidence_refs = list(obs.evidence_refs) + [str(packet_path)]
            emitted.append(obs)
        return emitted

    def observe_scheduler_health(self, shay_home: Path, *, now: float) -> WatcherObservation:
        jobs_path = shay_home / "cron" / "jobs.json"
        enabled_jobs = 0
        total_jobs = 0
        if jobs_path.exists():
            try:
                payload = json.loads(jobs_path.read_text(encoding="utf-8"))
                jobs = payload.get("jobs") if isinstance(payload, dict) else payload
                if isinstance(jobs, list):
                    total_jobs = len(jobs)
                    enabled_jobs = sum(1 for job in jobs if isinstance(job, dict) and job.get("enabled"))
            except json.JSONDecodeError:
                pass
        status = "quiet" if enabled_jobs == 0 else "active"
        severity = "info" if enabled_jobs == 0 else "medium"
        summary = f"Shay scheduler inventory has {enabled_jobs}/{total_jobs} enabled jobs"
        fingerprint = f"scheduler:{enabled_jobs}:{total_jobs}"
        return WatcherObservation(
            watcher="scheduler-health",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(jobs_path)],
            metrics={"enabled_jobs": enabled_jobs, "total_jobs": total_jobs},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def observe_ask_storm(self, shay_home: Path, asks_dir: Path, *, now: float, recent_window_seconds: int = 6 * 3600) -> WatcherObservation:
        events_path = shay_home / "events.jsonl"
        ask_files = list(asks_dir.glob("*.json")) if asks_dir.exists() else []
        recent_daily_brief_events = 0
        if events_path.exists():
            for raw in events_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if event.get("kind") != "daily_brief":
                    continue
                ts = float(event.get("ts") or event.get("created_at") or 0)
                if ts and (now - ts) <= recent_window_seconds:
                    recent_daily_brief_events += 1
        storm = recent_daily_brief_events >= 3
        status = "storm" if storm else "quiet"
        severity = "high" if storm else "info"
        summary = f"Daily brief emitted {recent_daily_brief_events} event(s) in the last 6h; asks dir holds {len(ask_files)} JSON file(s)"
        fingerprint = f"ask-storm:{recent_daily_brief_events}:{len(ask_files)}:{1 if storm else 0}"
        return WatcherObservation(
            watcher="ask-storm",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(events_path), str(asks_dir)],
            metrics={"recent_daily_brief_events": recent_daily_brief_events, "ask_file_count": len(ask_files)},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def observe_reflection_freshness(self, obsidian_root: Path, *, now: float) -> WatcherObservation:
        episodic_dir = obsidian_root / "reflections" / "episodic"
        latest = self._latest_mtime(episodic_dir.rglob("*.md"))
        age_seconds = int(now - latest) if latest else None
        stale = latest is None or age_seconds is None or age_seconds > 36 * 3600
        status = "stale" if stale else "fresh"
        severity = "medium" if stale else "info"
        summary = "Reflection freshness is stale" if stale else f"Reflection freshness is healthy at {age_seconds}s old"
        fingerprint = f"reflection:{status}:{self._age_bucket(age_seconds)}"
        return WatcherObservation(
            watcher="reflection-freshness",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(episodic_dir)],
            metrics={"latest_age_seconds": age_seconds},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def observe_lessons_sync_freshness(self, obsidian_root: Path, *, now: float) -> WatcherObservation:
        lessons_dir = obsidian_root / "lessons-mirror"
        latest = self._latest_mtime(lessons_dir.glob("*.md"))
        age_seconds = int(now - latest) if latest else None
        stale = latest is None or age_seconds is None or age_seconds > 3 * 3600
        status = "stale" if stale else "fresh"
        severity = "medium" if stale else "info"
        summary = "Lessons sync freshness is stale" if stale else f"Lessons sync freshness is healthy at {age_seconds}s old"
        fingerprint = f"lessons:{status}:{self._age_bucket(age_seconds)}"
        return WatcherObservation(
            watcher="lessons-sync-freshness",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(lessons_dir)],
            metrics={"latest_age_seconds": age_seconds},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def observe_external_intelligence_health(self, log_path: Path, *, now: float) -> WatcherObservation:
        latest = log_path.stat().st_mtime if log_path.exists() else None
        age_seconds = int(now - latest) if latest else None
        stale = latest is None or age_seconds is None or age_seconds > 4 * 24 * 3600
        status = "stale" if stale else "fresh"
        severity = "medium" if stale else "info"
        summary = "External intelligence loop looks stale" if stale else f"External intelligence loop updated {age_seconds}s ago"
        fingerprint = f"external-intel:{status}:{self._age_bucket(age_seconds)}"
        return WatcherObservation(
            watcher="external-intelligence-health",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(log_path)],
            metrics={"latest_age_seconds": age_seconds},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    @staticmethod
    def _latest_mtime(paths: Iterable[Path]) -> Optional[float]:
        mtimes = []
        for path in paths:
            try:
                mtimes.append(path.stat().st_mtime)
            except OSError:
                continue
        return max(mtimes) if mtimes else None

    @staticmethod
    def _age_bucket(age_seconds: Optional[int]) -> str:
        if age_seconds is None:
            return "missing"
        if age_seconds < 1800:
            return "lt30m"
        if age_seconds < 3 * 3600:
            return "lt3h"
        if age_seconds < 24 * 3600:
            return "lt24h"
        return "gte24h"
