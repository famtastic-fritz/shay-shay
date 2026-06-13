#!/usr/bin/env python3
"""Tracker authority for process-intelligence items.

Phase 2 goal: make the YAML tracker the authoritative current-state surface,
with explicit transition rules and evidence-gated promotion to live states.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from utils import atomic_yaml_write

LIVE_PROOF_STATES = {"live_wired", "validated_live"}
_ALLOWED_TRANSITIONS = {
    "designed": {"sandbox_proven", "pr_ready", "blocked", "deferred"},
    "sandbox_proven": {"pr_ready", "blocked", "deferred"},
    "pr_ready": {"pr_open", "blocked", "deferred", "live_wired"},
    "pr_open": {"merged_to_main", "blocked", "deferred"},
    "merged_to_main": {"live_wired", "blocked", "deferred"},
    "live_wired": {"validated_live", "blocked", "deferred"},
    "validated_live": {"blocked", "deferred"},
    "blocked": {"designed", "sandbox_proven", "pr_ready", "pr_open", "merged_to_main", "deferred"},
    "deferred": {"designed", "sandbox_proven", "pr_ready", "blocked"},
}


class TrackerTransitionError(ValueError):
    """Raised when a requested tracker transition is not allowed."""


class ProcessTracker:
    def __init__(self, tracker_path: str | Path, *, db: Any | None = None):
        self.tracker_path = Path(tracker_path)
        self.db = db

    def load(self) -> Dict[str, Any]:
        with self.tracker_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def save(self, payload: Dict[str, Any]) -> None:
        atomic_yaml_write(self.tracker_path, payload, sort_keys=False)

    def get_item(self, item_id: str) -> Dict[str, Any]:
        data = self.load()
        for item in data.get("items", []):
            if item.get("id") == item_id:
                return item
        raise KeyError(f"tracker item not found: {item_id}")

    def transition_item(
        self,
        item_id: str,
        new_state: str,
        *,
        evidence_refs: List[str],
        summary: str,
        run_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        actor: str = "process_tracker",
    ) -> Dict[str, Any]:
        data = self.load()
        items = data.get("items") or []
        target: Optional[Dict[str, Any]] = None
        for item in items:
            if item.get("id") == item_id:
                target = item
                break
        if target is None:
            raise KeyError(f"tracker item not found: {item_id}")

        old_state = str(target.get("current_state") or "designed")
        self._validate_transition(old_state, new_state, evidence_refs)

        now = time.time()
        history = list(target.get("transition_history") or [])
        event_id = uuid.uuid4().hex
        transition = {
            "event_id": event_id,
            "from_state": old_state,
            "to_state": new_state,
            "summary": summary,
            "evidence_refs": list(evidence_refs),
            "run_id": run_id,
            "decision_id": decision_id,
            "actor": actor,
            "recorded_at": now,
        }
        history.append(transition)

        target["current_state"] = new_state
        target["last_transition_at"] = now
        target["last_transition_run_id"] = run_id
        target["last_transition_decision_id"] = decision_id
        target["evidence_refs"] = list(evidence_refs)
        target["transition_history"] = history

        self._refresh_state_counts(data)
        self.save(data)

        if self.db is not None:
            self.db.record_tracker_transition(
                {
                    "transition_id": uuid.uuid4().hex,
                    "item_id": item_id,
                    "from_state": old_state,
                    "to_state": new_state,
                    "summary": summary,
                    "run_id": run_id,
                    "decision_id": decision_id,
                    "evidence_refs": list(evidence_refs),
                    "recorded_at": now,
                    "metadata": {"actor": actor, "event_id": event_id},
                }
            )

        return transition

    def _validate_transition(self, old_state: str, new_state: str, evidence_refs: List[str]) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(old_state, set())
        if new_state == old_state:
            return
        if new_state not in allowed:
            raise TrackerTransitionError(f"illegal tracker transition: {old_state} -> {new_state}")
        if new_state in LIVE_PROOF_STATES and not evidence_refs:
            raise TrackerTransitionError(f"{new_state} requires explicit validation evidence")
        if new_state == "validated_live" and old_state != "live_wired":
            raise TrackerTransitionError("validated_live requires prior live_wired state")

    @staticmethod
    def _refresh_state_counts(data: Dict[str, Any]) -> None:
        counts: Dict[str, int] = {}
        for item in data.get("items", []):
            state = str(item.get("current_state") or "designed")
            counts[state] = counts.get(state, 0) + 1
        data["state_counts"] = counts
