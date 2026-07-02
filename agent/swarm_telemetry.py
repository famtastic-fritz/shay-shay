"""Tiny JSONL telemetry ledger for HyperSwarm-style runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class LaneRecord:
    run_id: str
    lane_id: str
    role: str
    task: str
    intended_model: str | None = None
    actual_model: str | None = None
    provider: str | None = None
    budget_class: str = "not_logged"
    toolsets: list[str] = field(default_factory=list)
    start_time: str = field(default_factory=utc_now)
    end_time: str | None = None
    duration_seconds: float | None = None
    status: str = "started"
    files_changed: list[str] = field(default_factory=list)
    verification_command: str | None = None
    verification_result: str | None = None
    artifact_paths: list[str] = field(default_factory=list)
    tokens: dict = field(default_factory=lambda: {"input": None, "output": None})
    notes: str = ""


class SwarmRunLedger:
    def __init__(self, run_id: str, base_dir: Path):
        self.run_id = run_id
        self.base_dir = base_dir.expanduser() / run_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.lanes_path = self.base_dir / "lanes.jsonl"
        self.review_path = self.base_dir / "review.jsonl"
        self.run_path = self.base_dir / "run.json"
        self.summary_path = self.base_dir / "summary.md"
        self.run_path.write_text(json.dumps({"run_id": run_id, "started_at": utc_now()}, indent=2) + "\n", encoding="utf-8")

    def write_lane(self, record: LaneRecord) -> None:
        with self.lanes_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def summarize(self) -> dict:
        rows = []
        if self.lanes_path.exists():
            for line in self.lanes_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        total = sum(float(row.get("duration_seconds") or 0) for row in rows)
        summary = {"run_id": self.run_id, "lane_count": len(rows), "total_logged_lane_seconds": round(total, 2), "statuses": {}}
        for row in rows:
            status = row.get("status", "unknown")
            summary["statuses"][status] = summary["statuses"].get(status, 0) + 1
        self.summary_path.write_text(
            f"# Swarm run {self.run_id}\n\n"
            f"- lanes: {summary['lane_count']}\n"
            f"- total_logged_lane_seconds: {summary['total_logged_lane_seconds']}\n"
            f"- statuses: {summary['statuses']}\n",
            encoding="utf-8",
        )
        return summary


class lane_timer:
    def __init__(self, ledger: SwarmRunLedger, record: LaneRecord):
        self.ledger = ledger
        self.record = record
        self._start = 0.0

    def __enter__(self) -> LaneRecord:
        self._start = monotonic()
        return self.record

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.record.end_time = utc_now()
        self.record.duration_seconds = round(monotonic() - self._start, 3)
        if exc is not None:
            self.record.status = "failed"
            self.record.notes = f"{type(exc).__name__}: {exc}"
        elif self.record.status == "started":
            self.record.status = "completed"
        self.ledger.write_lane(self.record)
        return False
