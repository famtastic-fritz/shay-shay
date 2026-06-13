#!/usr/bin/env python3
"""Pattern scanner for Shay Life OS Phase 4.

Consumes tracker state, watcher review packets, and process-intelligence ledgers.
Emits review packets only — never direct action.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from shay_constants import get_shay_home

DEFAULT_PATTERN_COOLDOWN_SECONDS = 3600


@dataclass
class PatternFinding:
    scanner: str
    status: str
    severity: str
    summary: str
    evidence_refs: List[str]
    metrics: Dict[str, Any]
    fingerprint: str
    recorded_at: float
    emitted: bool = False


class PatternStateStore:
    def __init__(self, state_dir: str | Path | None = None):
        self.state_dir = Path(state_dir) if state_dir else get_shay_home() / "watcher-state"
        self.pattern_dir = self.state_dir / "pattern-packets"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.pattern_dir.mkdir(parents=True, exist_ok=True)

    def should_emit(self, scanner: str, fingerprint: str, *, cooldown_seconds: int = DEFAULT_PATTERN_COOLDOWN_SECONDS) -> bool:
        path = self.state_dir / f"pattern-{scanner}.json"
        payload: Dict[str, Any] = {}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
        now = time.time()
        if payload.get("fingerprint") == fingerprint and (now - float(payload.get("recorded_at") or 0)) < cooldown_seconds:
            return False
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"fingerprint": fingerprint, "recorded_at": now}, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        return True

    def save_packet(self, finding: PatternFinding) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(finding.recorded_at))
        path = self.pattern_dir / f"{finding.scanner}-{stamp}.json"
        path.write_text(json.dumps(asdict(finding), indent=2, sort_keys=True), encoding="utf-8")
        return path


class LifeOSPatternScanner:
    def __init__(self, state_store: PatternStateStore | None = None):
        self.state_store = state_store or PatternStateStore()

    def run_all(
        self,
        *,
        tracker_path: str | Path,
        process_db_path: str | Path,
        watcher_state_dir: str | Path | None = None,
        now: Optional[float] = None,
        cooldown_seconds: int = DEFAULT_PATTERN_COOLDOWN_SECONDS,
    ) -> List[PatternFinding]:
        now_ts = now if now is not None else time.time()
        watcher_dir = Path(watcher_state_dir) if watcher_state_dir else self.state_store.state_dir
        findings = [
            self.scan_state_overclaim(Path(tracker_path), now=now_ts),
            self.scan_stale_gaps(Path(tracker_path), now=now_ts),
            self.scan_ask_storm(watcher_dir, now=now_ts),
            self.scan_missing_lineage(Path(tracker_path), Path(process_db_path), now=now_ts),
        ]
        emitted: List[PatternFinding] = []
        for finding in findings:
            finding.emitted = self.state_store.should_emit(finding.scanner, finding.fingerprint, cooldown_seconds=cooldown_seconds)
            if finding.emitted:
                packet_path = self.state_store.save_packet(finding)
                finding.evidence_refs = list(finding.evidence_refs) + [str(packet_path)]
            emitted.append(finding)
        return emitted

    def scan_state_overclaim(self, tracker_path: Path, *, now: float) -> PatternFinding:
        tracker = self._load_tracker(tracker_path)
        offenders = []
        for item in tracker.get("items", []):
            state = str(item.get("current_state") or "designed")
            evidence = item.get("evidence_refs") or []
            if state in {"live_wired", "validated_live"} and not evidence:
                offenders.append(item.get("id") or "unknown")
        status = "detected" if offenders else "clear"
        severity = "high" if offenders else "info"
        summary = f"State overclaim scanner found {len(offenders)} live-state item(s) without evidence"
        fingerprint = f"overclaim:{status}:{','.join(sorted(offenders))}"
        return PatternFinding(
            scanner="state-overclaim",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(tracker_path)],
            metrics={"offender_count": len(offenders), "offenders": offenders},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def scan_stale_gaps(self, tracker_path: Path, *, now: float, stale_days: int = 7) -> PatternFinding:
        tracker = self._load_tracker(tracker_path)
        cutoff = stale_days * 24 * 3600
        stale_ids = []
        for item in tracker.get("items", []):
            state = str(item.get("current_state") or "designed")
            if state not in {"designed", "blocked", "deferred", "sandbox_proven", "pr_ready"}:
                continue
            last = float(item.get("last_transition_at") or 0)
            if not last or (now - last) > cutoff:
                stale_ids.append(item.get("id") or "unknown")
        status = "detected" if stale_ids else "clear"
        severity = "medium" if stale_ids else "info"
        summary = f"Stale gap scanner found {len(stale_ids)} stale tracker item(s)"
        fingerprint = f"stale-gap:{status}:{','.join(sorted(stale_ids))}"
        return PatternFinding(
            scanner="stale-gap",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=[str(tracker_path)],
            metrics={"stale_count": len(stale_ids), "stale_ids": stale_ids, "stale_days": stale_days},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def scan_ask_storm(self, watcher_state_dir: Path, *, now: float, lookback_seconds: int = 24 * 3600) -> PatternFinding:
        packet_dir = watcher_state_dir / "review-packets"
        storm_packets = []
        if packet_dir.exists():
            for path in sorted(packet_dir.glob("ask-storm-*.json")):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if payload.get("status") != "storm":
                    continue
                recorded_at = float(payload.get("recorded_at") or 0)
                if recorded_at and (now - recorded_at) <= lookback_seconds:
                    storm_packets.append(str(path))
        status = "detected" if len(storm_packets) >= 2 else "clear"
        severity = "high" if len(storm_packets) >= 2 else "info"
        summary = f"Ask-storm scanner found {len(storm_packets)} storm packet(s) in the last 24h"
        fingerprint = f"ask-storm:{status}:{len(storm_packets)}"
        return PatternFinding(
            scanner="ask-storm-pattern",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=storm_packets[:5] if storm_packets else [str(packet_dir)],
            metrics={"storm_packet_count": len(storm_packets), "lookback_seconds": lookback_seconds},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    def scan_missing_lineage(self, tracker_path: Path, process_db_path: Path, *, now: float) -> PatternFinding:
        missing = []
        evidence = [str(tracker_path), str(process_db_path)]
        tracker = self._load_tracker(tracker_path)
        con = sqlite3.connect(process_db_path)
        try:
            con.row_factory = sqlite3.Row
            transition_rows = con.execute(
                "SELECT item_id, to_state, run_id, decision_id FROM tracker_transition_ledger"
            ).fetchall()
            by_item = {}
            for row in transition_rows:
                by_item.setdefault(row["item_id"], []).append(dict(row))
        finally:
            con.close()
        for item in tracker.get("items", []):
            item_id = item.get("id") or "unknown"
            state = str(item.get("current_state") or "designed")
            if state not in {"live_wired", "validated_live", "pr_open", "merged_to_main"}:
                continue
            transitions = by_item.get(item_id, [])
            if not transitions:
                missing.append(item_id)
                continue
            latest = transitions[-1]
            if not latest.get("run_id") or not latest.get("decision_id"):
                missing.append(item_id)
        status = "detected" if missing else "clear"
        severity = "high" if missing else "info"
        summary = f"Missing-lineage scanner found {len(missing)} promoted item(s) without full ledger lineage"
        fingerprint = f"missing-lineage:{status}:{','.join(sorted(missing))}"
        return PatternFinding(
            scanner="missing-lineage",
            status=status,
            severity=severity,
            summary=summary,
            evidence_refs=evidence,
            metrics={"missing_count": len(missing), "missing_items": missing},
            fingerprint=fingerprint,
            recorded_at=now,
        )

    @staticmethod
    def _load_tracker(tracker_path: Path) -> Dict[str, Any]:
        if not tracker_path.exists():
            return {"items": []}
        with tracker_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {"items": []}
