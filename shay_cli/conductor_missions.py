"""Conductor missions store for the Shay-Shay dashboard.

Backs the ``/api/conductor/missions`` REST surface that the hermes-workspace
v2.3 gateway probes to decide its ``conductor`` capability flag
(see ``src/server/gateway-capabilities.ts::probeConductor``). The probe flips
``conductor: true`` only when the list endpoint returns HTTP 200 with a JSON
content-type — but Workspace also POSTs to spawn missions and DELETEs to stop
them (``conductor-spawn.ts`` / ``conductor-stop.ts``), so the full CRUD must
round-trip.

Data shape mirrors ``src/server/swarm-missions.ts::SwarmMission`` exactly:

    SwarmMission = {
        id, title, state, createdAt, updatedAt, assignments[], events[]
    }

where ``state`` is one of
``planning|dispatching|executing|reviewing|blocked|complete|cancelled`` and
each assignment matches ``SwarmMissionAssignment``
(id, workerId, task, rationale, dependsOn[], reviewRequired, state,
dispatchedAt, completedAt, reviewedAt, reviewedBy, checkpoint).

Persistence is a single JSON file at ``$SHAY_HOME/conductor/missions.json``
of shape ``{ "version": 1, "missions": [...] }``. Writes are atomic
(write-temp-then-rename) and guarded by a module-level lock so concurrent
dispatcher writes don't corrupt the store.

NOTE — honest scope: a created mission is *registered* in ``planning`` state
with its assignments recorded and a ``created`` event. Bridging dispatch into
the shay-agent-os swarm pipeline is a documented follow-up; this module does
not fabricate checkpoints or results that did not happen.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from shay_constants import get_shay_home

# Mirror of SwarmMissionState in swarm-missions.ts.
VALID_MISSION_STATES = frozenset({
    "planning", "dispatching", "executing", "reviewing",
    "blocked", "complete", "cancelled",
})

# Serializes read-modify-write cycles within this process. The atomic rename
# guards against partial writes from other processes; this lock prevents two
# in-process requests from clobbering each other's read-modify-write.
_STORE_LOCK = threading.RLock()


def _store_path() -> Path:
    """Resolve the missions JSON file under the active SHAY_HOME.

    Resolved per-call (not cached) so tests that redirect SHAY_HOME to a
    per-test tempdir — and live profile switches — are honored.
    """
    return get_shay_home() / "conductor" / "missions.json"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _short_id(prefix: str) -> str:
    """Match the ``prefix-<base36 time>-<random>`` shape from swarm-missions.ts."""
    stamp = format(int(time.time() * 1000), "x")
    return f"{prefix}-{stamp}-{secrets.token_hex(3)}"


def _read_store() -> Dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"version": 1, "missions": []}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "missions": []}
    missions = parsed.get("missions") if isinstance(parsed, dict) else None
    return {"version": 1, "missions": missions if isinstance(missions, list) else []}


def _write_store(store: Dict[str, Any]) -> None:
    """Atomically persist the store (write-temp-then-rename)."""
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{_now_ms()}.tmp")
    tmp.write_text(json.dumps(store, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _event(event_type: str, message: str, **extra: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "id": _short_id("evt"),
        "type": event_type,
        "at": _now_ms(),
        "message": message,
    }
    evt.update({k: v for k, v in extra.items() if v is not None})
    return evt


def _normalize_assignment(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a SwarmMissionAssignment from a (possibly partial) input dict."""
    worker_id = str(raw.get("workerId") or raw.get("worker_id") or "").strip()
    task = str(raw.get("task") or "").strip()
    if not worker_id or not task:
        return None
    rationale = raw.get("rationale")
    depends_on = raw.get("dependsOn") or raw.get("depends_on") or []
    if not isinstance(depends_on, list):
        depends_on = []
    review_required = raw.get("reviewRequired", raw.get("review_required", False))
    return {
        "id": _short_id("assign"),
        "workerId": worker_id,
        "task": task,
        "rationale": str(rationale) if isinstance(rationale, str) else None,
        "dependsOn": [str(d) for d in depends_on],
        "reviewRequired": bool(review_required),
        "state": "queued",
        "dispatchedAt": None,
        "completedAt": None,
        "reviewedAt": None,
        "reviewedBy": None,
        "checkpoint": None,
    }


# ── Public store API ─────────────────────────────────────────────────────────


def list_missions() -> List[Dict[str, Any]]:
    """Return all missions, newest-updated first."""
    with _STORE_LOCK:
        missions = _read_store()["missions"]
    return sorted(
        missions,
        key=lambda m: m.get("updatedAt", 0),
        reverse=True,
    )


def get_mission(mission_id: str) -> Optional[Dict[str, Any]]:
    with _STORE_LOCK:
        for mission in _read_store()["missions"]:
            if mission.get("id") == mission_id:
                return mission
    return None


def create_mission(
    *,
    goal: str,
    title: Optional[str] = None,
    assignments: Optional[List[Dict[str, Any]]] = None,
    mission_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new mission in ``planning`` state and persist it.

    ``goal`` is the human mission goal Workspace sends. ``title`` defaults to
    a clipped form of the goal so the record carries a readable label even
    when Workspace only supplies ``{name, prompt}``.

    Actual worker dispatch is intentionally NOT performed here — the mission
    is registered honestly with a ``created`` event and any supplied
    assignments recorded in ``queued`` state.
    """
    goal = (goal or "").strip()
    resolved_title = (title or "").strip() or (
        f"Conductor: {goal[:120]}" if goal else "Untitled conductor mission"
    )
    normalized: List[Dict[str, Any]] = []
    for raw in assignments or []:
        if isinstance(raw, dict):
            norm = _normalize_assignment(raw)
            if norm is not None:
                normalized.append(norm)

    created_at = _now_ms()
    mission: Dict[str, Any] = {
        "id": (mission_id or "").strip() or _short_id("mission"),
        "title": resolved_title,
        "state": "planning",
        "createdAt": created_at,
        "updatedAt": created_at,
        "assignments": normalized,
        "events": [
            _event("created", f"Mission created: {resolved_title}", data={"goal": goal}),
        ],
    }

    with _STORE_LOCK:
        store = _read_store()
        store["missions"].append(mission)
        _write_store(store)
    return mission


def cancel_mission(mission_id: str) -> Optional[Dict[str, Any]]:
    """Mark a mission (and its non-terminal assignments) ``cancelled``.

    Returns the updated mission, or ``None`` if no mission matches.
    """
    cancelled_at = _now_ms()
    with _STORE_LOCK:
        store = _read_store()
        mission = next(
            (m for m in store["missions"] if m.get("id") == mission_id),
            None,
        )
        if mission is None:
            return None
        cancelled_ids: List[str] = []
        for assignment in mission.get("assignments", []):
            if assignment.get("state") in ("done", "cancelled"):
                continue
            assignment["state"] = "cancelled"
            assignment["completedAt"] = cancelled_at
            assignment["reviewedAt"] = cancelled_at
            assignment["reviewedBy"] = "conductor-stop"
            cancelled_ids.append(assignment.get("id"))
        mission["state"] = "cancelled"
        mission["updatedAt"] = cancelled_at
        mission.setdefault("events", []).append(
            _event(
                "mission_cancelled",
                "Cancelled mission",
                data={"actor": "conductor-stop", "cancelledAssignmentIds": cancelled_ids},
            )
        )
        _write_store(store)
        return mission
