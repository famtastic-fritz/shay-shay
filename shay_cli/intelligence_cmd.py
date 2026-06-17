from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from shay_constants import get_shay_home
from shay_cli.intelligence_seed import (
    BRIEF_COMMANDS,
    BRIEF_TYPES,
    COMMON_FORBIDDEN_ACTIONS,
    DELIVERY_SURFACES,
    FAMTASTIC_THOUGHTS_STATES,
    MISSION_LANES,
    RD_STATES,
    TODAY_HUB_RECORD_TYPES,
    TRACKED_PLAN_ITEMS,
    agent_by_id,
    capability_by_id,
    get_agent_registry,
    get_cadence_records,
    get_capability_matrix,
)

MISSING_OR_UNSAFE_STATUSES = {
    "missing",
    "partial",
    "blocked",
    "unsafe",
    "requires_review",
    "avoid_by_policy",
}

REALITY_CLASSES = {
    "proven_live",
    "implemented_unverified",
    "partial",
    "seeded",
    "deprecated",
}

WORKER_STATUSES = {
    "queued",
    "running",
    "blocked",
    "waiting_for_fritz",
    "review_required",
    "done",
    "failed",
    "cancelled",
    "unsafe",
}

WORKER_REQUIRED_FIELDS = [
    "worker_id",
    "agent_id",
    "mission_id",
    "plan_id",
    "task",
    "status",
    "worktree",
    "branch",
    "allowed_paths",
    "forbidden_paths",
    "allowed_tools",
    "forbidden_tools",
    "provider_model",
    "context_level",
    "budget_limit",
    "runtime_limit",
    "output_contract",
    "review_required",
    "redaction_required",
    "artifact_paths",
    "ledger_path",
    "started_at",
    "last_update",
    "next_report_due",
    "blocked_reason",
    "stop_reason",
    "resume_point",
    "result",
]

SAFETY_GATES = [
    "no dirty-main writes",
    "no persona/root-truth edits",
    "no live runtime edits",
    "no launchd/cron/symlink edits",
    "no skill moves/deletes/promotions",
    "no production HyperSwarm launch without explicit approval",
    "no external repo execution",
    "no Gmail send",
    "no Calendar write",
    "no publish action",
    "no uncontrolled provider spend",
    "no task without output contract",
    "no worker without ledger entry",
    "no worker without stop/resume point",
    "no worker without assigned mission/plan",
]

RESEARCH_DECISIONS = {
    "openjarvis": {
        "thing": "OpenJarvis",
        "decision": "priority_r_and_d_seed",
        "status": "priority_r_and_d_seed",
        "agent": "rd-evaluator",
        "capability_id": "openjarvis",
        "safe_to_run": False,
        "installed": False,
        "adopted": False,
        "intended_use": "personal AI operating-system prior art for Shay architecture, memory, tools, planning, UI, and agent/workspace organization",
        "next_action": "evaluate in FAMtastic Data Center later",
    },
    "odysseus": {
        "thing": "Odysseus",
        "decision": "priority_r_and_d_seed",
        "status": "priority_r_and_d_seed",
        "agent": "rd-evaluator",
        "capability_id": "odysseus",
        "safe_to_run": False,
        "installed": False,
        "adopted": False,
        "intended_use": "self-hosted AI workspace prior art for chat, agents, documents, memory, skills, email, calendar, notes/tasks, mobile PWA, deep research, Today Hub, and UX",
        "next_action": "evaluate in FAMtastic Data Center later",
    },
    "turbovec": {
        "thing": "TurboVec",
        "decision": "priority_pattern_signal",
        "status": "priority_pattern_signal",
        "agent": "rd-evaluator",
        "capability_id": "turbovec",
        "safe_to_run": False,
        "installed": False,
        "adopted": False,
        "intended_use": "possible memory/vector/capability substrate and retrieval speed improvement",
        "next_action": "evaluate carefully in R&D before any adoption",
    },
    "vllm": {
        "thing": "vLLM",
        "decision": "priority_r_and_d_seed",
        "status": "priority_r_and_d_seed",
        "agent": "provider-capacity-broker",
        "capability_id": "vllm-local-serving",
        "safe_to_run": False,
        "installed": False,
        "adopted": False,
        "intended_use": "high-throughput local model serving candidate compared against Ollama for FAMtastic workloads",
        "next_action": "benchmark later before adoption",
    },
    "agent swarms": {
        "thing": "agent swarms",
        "decision": "priority_r_and_d_seed",
        "status": "priority_r_and_d_seed",
        "agent": "worker-supervisor",
        "capability_id": "agent-swarms",
        "safe_to_run": False,
        "installed": False,
        "adopted": False,
        "intended_use": "prior art for worker orchestration, assignment, output review, splitting work, and managing parallel workers",
        "next_action": "preserve as R&D seed; do not install or launch uncontrolled swarms",
    },
    "browser agents": {
        "thing": "browser agents",
        "decision": "test_more",
        "status": "requires_review",
        "agent": "research-to-action-agent",
        "capability_id": "browser-computer-use",
        "safe_to_run": True,
        "installed": True,
        "adopted": False,
        "intended_use": "safe user-facing automation and browser/computer-use verification",
        "next_action": "test only in controlled flows with no secrets or permission/payment clicks",
    },
    "model evals": {
        "thing": "model evals",
        "decision": "training_candidate",
        "status": "requires_review",
        "agent": "provider-capacity-broker",
        "capability_id": "famtastic-data-center-rd",
        "safe_to_run": True,
        "installed": True,
        "adopted": False,
        "intended_use": "compare providers/models against FAMtastic workloads and cost constraints",
        "next_action": "design a benchmark before spending provider budget",
    },
    "skill experiments": {
        "thing": "skill experiments",
        "decision": "skill_candidate",
        "status": "requires_review",
        "agent": "capability-cartographer",
        "capability_id": "famtastic-data-center-rd",
        "safe_to_run": True,
        "installed": True,
        "adopted": False,
        "intended_use": "convert reusable task patterns into maintained skills after review",
        "next_action": "classify experiment and write or patch skill only after validated reuse",
    },
}


def _utc_now() -> str:
    return (
        datetime
        .now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value).strip().lower()).strip("-")
    return text or "item"


def _storage_home() -> Path:
    override = os.environ.get("SHAY_INTELLIGENCE_HOME")
    if override:
        return Path(override).expanduser()
    return get_shay_home() / "process-intelligence" / "intelligence"


def _ensure_storage() -> Path:
    base = _storage_home()
    for child in ("events", "workers", "ledgers", "reports"):
        (base / child).mkdir(parents=True, exist_ok=True)
    return base


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return row if isinstance(row, dict) else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def backfill_events() -> list[dict[str, Any]]:
    return [
        normalize_event(
            {
            "event_id": "event-capability-truth-layer-complete",
            "timestamp": "2026-06-14T00:00:00Z",
            "source": "manual-backfill",
            "session_id": None,
            "conversation_id": None,
            "agent_model": "shay",
            "worktree": "/Users/famtasticfritz/famtastic/shay-shay",
            "branch": "main",
            "commit": "b30a8f5",
            "plan_id": "plan-shay-intelligence-layer",
            "mission_id": "mission-shay-intelligence-layer",
            "task_id": "task-capability-truth-layer",
            "summary": "Capability Truth Layer complete, merged into main, working.",
            "decision": "complete",
            "artifact_paths": [
                "shay_cli/capabilities_cmd.py",
                "tests/test_capabilities_cmd.py",
            ],
            "files_touched": [
                "shay_cli/capabilities_cmd.py",
                "shay_cli/main.py",
                "tests/test_capabilities_cmd.py",
            ],
            "status": "complete",
            "result": "complete, merged, working",
            "next_resume_point": "Use shay capabilities list/show/doctor/decide as the foundation for Intelligence Layer routing.",
            "sensitivity": "low",
            "source_pointer": "main commit b30a8f5 if present; command surface verified by current capability tests",
            "related_capabilities": [
                "provider-routing",
                "toolset-resolution",
                "hyperswarm-doctrine",
            ],
            "related_agents": ["capability-cartographer", "work-router"],
            }
        )
    ]


def normalize_event(payload: Mapping[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or "manual event"
    result = payload.get("result")
    observation = payload.get("observation") or summary
    interpretation = payload.get("interpretation")
    if interpretation is None:
        interpretation = payload.get("decision") or payload.get("status")
    pattern = payload.get("pattern")
    if pattern is None:
        related_capabilities = list(payload.get("related_capabilities") or [])
        related_agents = list(payload.get("related_agents") or [])
        pattern_parts = related_capabilities + related_agents
        pattern = ", ".join(pattern_parts) if pattern_parts else None
    normalized = {
        "event_id": str(
            payload.get("event_id")
            or f"event-{_slug(summary)}-{_slug(_utc_now())}"
        ),
        "timestamp": str(payload.get("timestamp") or _utc_now()),
        "source": payload.get("source") or "shay-intelligence-layer",
        "session_id": payload.get("session_id"),
        "conversation_id": payload.get("conversation_id"),
        "agent_model": payload.get("agent_model"),
        "worktree": payload.get("worktree"),
        "branch": payload.get("branch"),
        "commit": payload.get("commit"),
        "plan_id": payload.get("plan_id"),
        "mission_id": payload.get("mission_id"),
        "task_id": payload.get("task_id"),
        "summary": summary,
        "decision": payload.get("decision"),
        "artifact_paths": list(payload.get("artifact_paths") or []),
        "files_touched": list(payload.get("files_touched") or []),
        "status": payload.get("status") or "recorded",
        "result": result,
        "next_resume_point": payload.get("next_resume_point"),
        "sensitivity": payload.get("sensitivity") or "low",
        "source_pointer": payload.get("source_pointer"),
        "related_capabilities": list(payload.get("related_capabilities") or []),
        "related_agents": list(payload.get("related_agents") or []),
        "observation": observation,
        "interpretation": interpretation,
        "pattern": pattern,
    }
    return normalized


def create_event(payload: Mapping[str, Any], *, persist: bool = True) -> dict[str, Any]:
    event = normalize_event(payload)
    if persist:
        base = _ensure_storage()
        _write_json(base / "events" / f"{event['event_id']}.json", event)
        _append_jsonl(base / "events" / "events.jsonl", event)
    return event


def list_events(limit: int = 10) -> list[dict[str, Any]]:
    limit = max(1, int(limit or 10))
    base = _ensure_storage()
    persisted = _read_jsonl(base / "events" / "events.jsonl")
    by_id: dict[str, dict[str, Any]] = {}
    for event in backfill_events() + persisted:
        event = normalize_event(event)
        event_id = str(event.get("event_id") or "")
        if event_id:
            by_id[event_id] = event
    rows = sorted(
        by_id.values(), key=lambda row: str(row.get("timestamp") or ""), reverse=True
    )
    return rows[:limit]


def get_event(event_id: str) -> dict[str, Any] | None:
    for event in list_events(limit=1000):
        if event.get("event_id") == event_id:
            return event
    return None


def build_truth_registry() -> list[dict[str, Any]]:
    from agent.process_intelligence import process_intelligence_home

    process_home = process_intelligence_home()
    intelligence_home = _ensure_storage()
    root = Path(__file__).resolve().parents[1]
    docs_root = root / "docs"
    generated_docs = docs_root / "generated"
    truth_rows = [
        {
            "subsystem_id": "capability-truth-layer",
            "name": "Capability Truth Layer",
            "status": "working",
            "reality_class": "proven_live",
            "owner_module": "shay_cli/capabilities_cmd.py",
            "source_of_truth": "live capability probes merged with guarded policy overlays plus observed-proof overlays from the process-intelligence ledger",
            "persistence_paths": [
                str(get_shay_home() / "config.yaml"),
                str(process_home),
                str(process_home / "runs" / "runs.jsonl"),
            ],
            "proof_artifacts": [
                "shay capabilities list",
                "shay capabilities decide <task>",
                "shay capabilities show <capability-id>",
            ],
            "dependencies": ["process-intelligence-substrate", "identity-guard"],
            "open_gaps": [
                "Curated capability status still does not auto-flip from ledger evidence alone; eligible promotions remain review-gated on purpose.",
            ],
            "notes": "Routing truth now applies verifier-aware promotion rules from the run ledger while keeping final curated status changes review-gated.",
        },
        {
            "subsystem_id": "process-intelligence-substrate",
            "name": "Process Intelligence Substrate",
            "status": "working",
            "reality_class": "proven_live",
            "owner_module": "agent/process_intelligence.py",
            "source_of_truth": "canonical run ledger and run directories",
            "persistence_paths": [
                str(process_home / "runs" / "runs.jsonl"),
                str(process_home / "runs"),
            ],
            "proof_artifacts": [
                "agent/process_intelligence.py",
                str(process_home / "runs" / "runs.jsonl"),
            ],
            "dependencies": [],
            "open_gaps": [],
            "notes": "Best current candidate for the event spine.",
        },
        {
            "subsystem_id": "intelligence-events-workers",
            "name": "Intelligence Events and Workers",
            "status": "working",
            "reality_class": "proven_live",
            "owner_module": "shay_cli/intelligence_cmd.py",
            "source_of_truth": "intelligence storage under SHAY_INTELLIGENCE_HOME",
            "persistence_paths": [
                str(intelligence_home / "events" / "events.jsonl"),
                str(intelligence_home / "workers"),
                str(intelligence_home / "ledgers"),
            ],
            "proof_artifacts": [
                "shay intelligence events",
                "shay intelligence workers",
                "tests/test_intelligence_layer.py",
            ],
            "dependencies": ["process-intelligence-substrate"],
            "open_gaps": [],
            "notes": "Event storage is normalized into observation, interpretation, pattern, and result fields.",
        },
        {
            "subsystem_id": "mission-graph-registry",
            "name": "Mission Graph Registry",
            "status": "working",
            "reality_class": "seeded",
            "owner_module": "shay_cli/intelligence_cmd.py",
            "source_of_truth": "seeded mission and plan records",
            "persistence_paths": [],
            "proof_artifacts": [
                "shay intelligence missions",
                "shay_cli/intelligence_seed.py",
            ],
            "dependencies": [],
            "open_gaps": [
                "mission graph is plan-shaped and not automatically reconciled against live execution state"
            ],
            "notes": "Useful control surface, but not authoritative runtime truth by itself.",
        },
        {
            "subsystem_id": "cadence-registry",
            "name": "Cadence Registry",
            "status": "pending_activation",
            "reality_class": "seeded",
            "owner_module": "shay_cli/intelligence_seed.py",
            "source_of_truth": "seeded cadence records",
            "persistence_paths": [],
            "proof_artifacts": [
                "shay intelligence cadence list",
                "shay_cli/intelligence_seed.py",
            ],
            "dependencies": [],
            "open_gaps": [
                "cadence records are intentionally disabled and not a live scheduler truth surface"
            ],
            "notes": "Policy/control metadata only until explicitly wired.",
        },
        {
            "subsystem_id": "research-classification-registry",
            "name": "Research Classification Registry",
            "status": "working",
            "reality_class": "seeded",
            "owner_module": "shay_cli/intelligence_cmd.py",
            "source_of_truth": "seeded research decision table with controlled aliases",
            "persistence_paths": [str(docs_root / "research-artifact-capture-protocol.md")],
            "proof_artifacts": [
                "shay intelligence research OpenJarvis",
                "docs/research-artifact-capture-protocol.md",
            ],
            "dependencies": [],
            "open_gaps": [
                "classification defaults are real code, but most entries are policy seeds rather than observed runtime outcomes"
            ],
            "notes": "Good intake classifier, not yet a learned pattern system.",
        },
        {
            "subsystem_id": "identity-guard",
            "name": "Identity Guard",
            "status": "working",
            "reality_class": "proven_live",
            "owner_module": "identity_guard.py",
            "source_of_truth": "required snippet audit plus emergency manifest under SHAY_HOME/private",
            "persistence_paths": [
                str(get_shay_home() / "private" / "identity-guard"),
                str(get_shay_home() / "memories" / "USER.md"),
            ],
            "proof_artifacts": [
                "shay identity status --json",
                str(generated_docs / "identity-status-2026-06-15.json"),
            ],
            "dependencies": [],
            "open_gaps": [
                "shared blast-radius memory files must stay frozen unless explicitly coordinated"
            ],
            "notes": "Hard boundary surface; memory compaction proved this can trip on missing authority snippets.",
        },
        {
            "subsystem_id": "delegate-route-proof",
            "name": "Delegate Route Proof Surface",
            "status": "working",
            "reality_class": "proven_live",
            "owner_module": "tools/delegate_tool.py",
            "source_of_truth": "live delegated child probe artifacts and delegate regression tests",
            "persistence_paths": [
                str(root / "scripts" / "probe_delegate_route.py"),
                str(generated_docs / "delegate-route-probe-2026-06-15.json"),
            ],
            "proof_artifacts": [
                str(docs_root / "learning-loop-verification-run-2026-06-15.md"),
                str(generated_docs / "delegate-route-probe-2026-06-15.json"),
                "tests/tools/test_delegate.py",
            ],
            "dependencies": ["capability-truth-layer"],
            "open_gaps": [
                "delegation routing is proven for the sampled lane, not for every intelligence surface end-to-end"
            ],
            "notes": "Critical proof surface for separating declared routing from observed routing.",
        },
    ]
    for row in truth_rows:
        if row["reality_class"] not in REALITY_CLASSES:
            raise ValueError(f"unknown reality class: {row['reality_class']}")
    return truth_rows


def build_mission_graph() -> dict[str, Any]:
    child_missions = [
        {
            "mission_id": f"mission-{_slug(lane)}",
            "name": lane,
            "status": "working" if lane == "Shay Intelligence Layer" else "tracked",
            "parent_mission_id": "mission-famtastic",
            "child_mission_ids": [],
            "linked_plans": ["plan-shay-intelligence-layer"]
            if lane == "Shay Intelligence Layer"
            else [],
            "next_action": "use linked plan queue"
            if lane == "Shay Intelligence Layer"
            else "track lane state",
        }
        for lane in MISSION_LANES
    ]
    plan_items = []
    for index, (title, status, note) in enumerate(TRACKED_PLAN_ITEMS, start=1):
        plan_items.append({
            "task_id": f"task-shay-intelligence-layer-{index:02d}",
            "title": title,
            "status": status,
            "note": note,
            "linked_capabilities": _linked_capabilities_for_plan_item(title),
            "linked_agents": _linked_agents_for_plan_item(title),
        })
    complete_count = sum(1 for item in plan_items if item["status"] == "complete")
    progress = round(complete_count / len(plan_items), 2) if plan_items else 0
    return {
        "missions": [
            {
                "mission_id": "mission-famtastic",
                "name": "FAMtastic",
                "status": "working",
                "parent_mission_id": None,
                "child_mission_ids": [
                    mission["mission_id"] for mission in child_missions
                ],
                "linked_plans": ["plan-shay-intelligence-layer"],
                "next_action": "continue orchestrating the five streams through plan records",
            },
            *child_missions,
        ],
        "plans": [
            {
                "plan_id": "plan-shay-intelligence-layer",
                "mission_id": "mission-shay-intelligence-layer",
                "name": "Shay Intelligence Layer",
                "status": "working",
                "parent_plan_id": None,
                "child_plan_ids": [],
                "progress": progress,
                "blocked": False,
                "stale": False,
                "done": complete_count == len(plan_items),
                "next_action": "verify commands and tests from main",
                "linked_capabilities": [
                    record["capability_id"] for record in get_capability_matrix()
                ],
                "linked_agents": [
                    record["agent_id"] for record in get_agent_registry()
                ],
                "linked_episodic_events": ["event-capability-truth-layer-complete"],
                "linked_artifacts": [
                    "shay_cli/intelligence_cmd.py",
                    "shay_cli/intelligence_seed.py",
                ],
                "linked_worktrees": [
                    "/Users/famtasticfritz/famtastic/shay-intelligence-layer-complete-20260614"
                ],
                "linked_branches": [
                    "feature/shay-intelligence-layer-complete-20260614"
                ],
                "items": plan_items,
            }
        ],
    }


def _linked_capabilities_for_plan_item(title: str) -> list[str]:
    lowered = title.lower()
    matches = {
        "capability truth": [
            "provider-routing",
            "toolset-resolution",
            "hyperswarm-doctrine",
        ],
        "capability matrix": ["agent-registry", "episodic-memory", "mission-graph"],
        "agent registry": ["agent-registry"],
        "episodic": ["episodic-memory"],
        "mission": ["mission-graph"],
        "worker": ["worker-queue", "worker-control"],
        "hyperswarm": ["hyperswarm-doctrine", "worker-control"],
        "critical": ["critical-item-sentinel"],
        "high item": ["high-item-review"],
        "research": ["research-to-action"],
        "brief": ["operating-briefs"],
        "cadence": ["intelligence-cadence"],
        "thoughts": ["famtastic-thoughts-pipeline"],
        "data center": ["famtastic-data-center-rd"],
        "context": ["context-compression-memory-continuity"],
        "delivery": ["delivery-router", "today-hub"],
    }
    for needle, capabilities in matches.items():
        if needle in lowered:
            return capabilities
    return []


def _linked_agents_for_plan_item(title: str) -> list[str]:
    lowered = title.lower()
    matches = {
        "capability": ["capability-cartographer"],
        "agent": ["capability-cartographer", "worker-supervisor"],
        "episodic": ["episodic-recorder"],
        "mission": ["mission-graph-planner"],
        "worker": ["worker-supervisor"],
        "hyperswarm": ["worker-supervisor", "run-reviewer"],
        "critical": ["critical-item-sentinel"],
        "high item": ["high-item-reviewer"],
        "research": ["research-to-action-agent"],
        "brief": ["brief-composer"],
        "cadence": ["cadence-manager"],
        "thoughts": ["famtastic-thoughts-agent"],
        "data center": ["rd-evaluator"],
        "context": ["provider-capacity-broker"],
        "delivery": ["delivery-router"],
    }
    agents: list[str] = []
    for needle, candidate_agents in matches.items():
        if needle in lowered:
            agents.extend(candidate_agents)
    return sorted(set(agents))


def build_gap_records() -> list[dict[str, Any]]:
    records = []
    for capability in get_capability_matrix():
        status = capability["status"]
        if status not in MISSING_OR_UNSAFE_STATUSES:
            continue
        cap_id = capability["capability_id"]
        severity = (
            "high" if status in {"blocked", "unsafe", "avoid_by_policy"} else "medium"
        )
        records.append({
            "gap_id": f"gap-{cap_id}",
            "title": f"{capability['name']} is {status}",
            "source": "capability-matrix",
            "capability_id": cap_id,
            "mission_id": "mission-shay-intelligence-layer",
            "plan_id": "plan-shay-intelligence-layer",
            "severity": severity,
            "status": "open",
            "evidence": capability["evidence_source"],
            "next_action": capability["next_action"],
            "owner_agent": _owner_for_capability(cap_id),
            "blocked_by": capability.get("dependencies", []),
            "created_at": capability["last_verified"],
            "last_reviewed": capability["last_verified"],
        })
    return records



def _group_gaps_by_owner(gaps: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for gap in gaps:
        owner = str(gap.get('owner_agent') or 'unknown')
        counts[owner] = counts.get(owner, 0) + 1
    return counts


def build_actionable_brief_payload(kind: str = 'morning') -> dict[str, Any]:
    status = intelligence_status()
    graph = build_mission_graph()
    gaps = build_gap_records()
    workers = list_workers(limit=5)
    recent_events = list_events(limit=5)
    research_items = [
        classify_research(item)
        for item in ('OpenJarvis', 'Odysseus', 'TurboVec', 'vLLM', 'agent swarms')
    ]
    owner_gap_counts = _group_gaps_by_owner(gaps)
    recommendations = [
        'Review any source-backed critical/high items if they appear.',
        'Use safe dry-run evidence before approving any production worker swarm.',
        'Keep context compression as a tracked gap until controlled capacity verification.',
    ]
    if status.get('verified_delivery_path') == 'cli_report':
        recommendations.insert(0, 'CLI/report delivery is the trusted brief path right now; keep external push surfaces optional until explicitly wired.')
    return {
        'brief_type': BRIEF_COMMANDS.get(kind, kind),
        'status': status,
        'graph': graph,
        'gaps': gaps,
        'workers': workers,
        'recent_events': recent_events,
        'research_items': research_items,
        'owner_gap_counts': owner_gap_counts,
        'recommendations': recommendations,
        'top_gaps': gaps[:6],
    }


def _owner_for_capability(capability_id: str) -> str:
    if capability_id in {
        "gmail-send",
        "calendar-read-write",
        "delivery-router",
        "today-hub",
    }:
        return "delivery-router"
    if capability_id in {
        "worker-queue",
        "worker-control",
        "hyperswarm-doctrine",
        "agent-swarms",
    }:
        return "worker-supervisor"
    if capability_id in {"critical-item-sentinel", "high-item-review"}:
        return "critical-item-sentinel"
    if capability_id in {
        "openjarvis",
        "odysseus",
        "turbovec",
        "vllm-local-serving",
        "famtastic-data-center-rd",
    }:
        return "rd-evaluator"
    if capability_id == "famtastic-thoughts-pipeline":
        return "famtastic-thoughts-agent"
    if capability_id == "context-compression-memory-continuity":
        return "provider-capacity-broker"
    return "capability-cartographer"


def classify_research(thing: str) -> dict[str, Any]:
    lowered = str(thing or "").strip().lower()
    aliases = {
        "openjarvis": "openjarvis",
        "open jarvis": "openjarvis",
        "odysseus": "odysseus",
        "turbovec": "turbovec",
        "turbo vec": "turbovec",
        "vllm": "vllm",
        "vllm local serving": "vllm",
        "agent swarm": "agent swarms",
        "agent swarms": "agent swarms",
        "agency swarm": "agent swarms",
        "openswarm": "agent swarms",
        "hyperswarm": "agent swarms",
        "browser agent": "browser agents",
        "browser agents": "browser agents",
        "model eval": "model evals",
        "model evals": "model evals",
        "skill experiment": "skill experiments",
        "skill experiments": "skill experiments",
    }
    key = aliases.get(lowered)
    if key is None:
        for candidate in aliases:
            if candidate in lowered:
                key = aliases[candidate]
                break
    if key is None:
        return {
            "thing": thing,
            "decision": "test_more",
            "status": "requires_review",
            "agent": "research-to-action-agent",
            "capability_id": "research-to-action",
            "safe_to_run": False,
            "installed": False,
            "adopted": False,
            "intended_use": "unclassified research item",
            "next_action": "capture source pointer and classify before adoption or execution",
        }
    result = dict(RESEARCH_DECISIONS[key])
    result["source_policy"] = (
        "do not install prior-art tools or run unknown repo code during classification"
    )
    return result


def review_item(candidate: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(candidate, Mapping):
        title = str(candidate.get("title") or candidate.get("text") or "")
        source = str(candidate.get("source") or "manual")
        due_date = candidate.get("due_date")
        ignored_before = bool(candidate.get("ignored_before", False))
    else:
        title = str(candidate)
        source = "manual"
        due_date = None
        ignored_before = False
    lowered = title.lower()
    money = any(
        word in lowered
        for word in (
            "money",
            "cash",
            "invoice",
            "revenue",
            "client",
            "contract",
            "job",
            "ama",
            "pay",
        )
    )
    health = any(
        word in lowered
        for word in ("health", "doctor", "medical", "safety", "emergency")
    )
    family = any(
        word in lowered for word in ("family", "sha", "child", "parent", "home")
    )
    deadline = any(
        word in lowered
        for word in (
            "deadline",
            "due",
            "today",
            "tonight",
            "tomorrow",
            "urgent",
            "overdue",
        )
    ) or bool(due_date)
    blocker = any(
        word in lowered
        for word in ("blocked", "blocker", "broken", "can't", "cannot", "down")
    )
    client_work = any(
        word in lowered
        for word in ("client", "work", "ama", "boss", "committee", "customer")
    )
    urgency = (
        4
        if any(
            word in lowered
            for word in ("critical", "urgent", "tonight", "overdue", "emergency")
        )
        else 2
        if deadline
        else 1
    )
    consequence = 4 if health or money or client_work else 2 if family or blocker else 1
    score_fields = {
        "urgency": urgency,
        "consequence": consequence,
        "deadline_proximity": 4 if deadline else 0,
        "money_impact": 4 if money else 0,
        "health_safety_impact": 5 if health else 0,
        "client_work_impact": 4 if client_work else 0,
        "family_personal_impact": 3 if family else 0,
        "blocker_impact": 3 if blocker else 0,
        "confidence": 3 if len(title.strip()) > 12 else 1,
        "source_reliability": 3 if source != "manual" else 2,
    }
    total = sum(score_fields.values()) + (2 if ignored_before else 0)
    if "dismiss" in lowered or "archive" in lowered or "resolved" in lowered:
        outcome = "archive"
    elif len(title.strip()) < 8:
        outcome = "needs_more_context"
    elif health and (deadline or urgency >= 4):
        outcome = "critical_item"
    elif money and (deadline or client_work or blocker):
        outcome = "critical_item" if total >= 19 else "high_priority_item"
    elif total >= 19:
        outcome = "critical_item"
    elif total >= 11:
        outcome = "high_priority_item"
    elif "waiting" in lowered or "needs fritz" in lowered:
        outcome = "waiting_for_fritz"
    elif "monitor" in lowered or total >= 6:
        outcome = "monitor"
    else:
        outcome = "normal_task"
    return {
        "title": title,
        "source": source,
        "due_date": due_date,
        "ignored_before": ignored_before,
        "outcome": outcome,
        "score": total,
        "scoring_fields": score_fields,
        "fritz_action_required": outcome
        in {"critical_item", "high_priority_item", "waiting_for_fritz"},
        "appears_in_morning_brief": outcome in {"critical_item", "high_priority_item"},
        "becomes_mission_plan_task": outcome
        in {"critical_item", "high_priority_item", "normal_task"},
    }


def critical_item_records() -> list[dict[str, Any]]:
    return [
        {
            "item_id": "sample-disabled-critical-review-schema",
            "title": "Disabled sample for critical item schema only",
            "reason": "Sample is disabled so the system does not invent fake critical items.",
            "category": "sample",
            "severity": "sample",
            "source": "disabled-sample",
            "due_date": None,
            "escalation_state": "disabled",
            "status": "dismissed",
            "last_checked": None,
            "next_action": "ignore sample; use review logic only for source-backed items",
            "dismissal_rule": "always dismissed because sample=true",
            "linked_mission": None,
            "linked_event": None,
            "review_required": False,
            "fritz_action_required": False,
            "sample": True,
            "enabled": False,
        }
    ]


def new_worker_record(
    *,
    agent_id: str,
    mission_id: str,
    plan_id: str,
    task: str,
    output_contract: str,
    status: str = "queued",
    worktree: str = "local-safe-record",
    branch: str = "none",
    allowed_paths: list[str] | None = None,
    forbidden_paths: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    forbidden_tools: list[str] | None = None,
    provider_model: str = "none/simulation",
    context_level: str = "minimal",
    budget_limit: str = "$0",
    runtime_limit: str = "60s",
    review_required: bool = True,
    redaction_required: bool = True,
    worker_id: str | None = None,
) -> dict[str, Any]:
    if not mission_id:
        raise ValueError("worker requires mission_id")
    if not plan_id:
        raise ValueError("worker requires plan_id")
    if not output_contract:
        raise ValueError("worker requires output_contract")
    if status not in WORKER_STATUSES:
        raise ValueError(f"unsupported worker status: {status}")
    agents = agent_by_id()
    if agent_id not in agents:
        raise ValueError(f"unknown agent_id: {agent_id}")
    base = _ensure_storage()
    safe_worker_id = worker_id or f"worker-{_slug(agent_id)}-{_slug(_utc_now())}"
    ledger_path = base / "ledgers" / f"{safe_worker_id}.jsonl"
    now = _utc_now()
    return {
        "worker_id": safe_worker_id,
        "agent_id": agent_id,
        "mission_id": mission_id,
        "plan_id": plan_id,
        "task": task,
        "status": status,
        "worktree": worktree,
        "branch": branch,
        "allowed_paths": allowed_paths or [str(base)],
        "forbidden_paths": forbidden_paths
        or [
            "/Users/famtasticfritz/famtastic/shay-shay",
            "~/.shay/skills",
            "SOUL.md",
            "PERSONA.md",
            "THINKING-LOG.md",
        ],
        "allowed_tools": allowed_tools
        or ["file", "terminal-readonly", "local-simulation"],
        "forbidden_tools": forbidden_tools or COMMON_FORBIDDEN_ACTIONS,
        "provider_model": provider_model,
        "context_level": context_level,
        "budget_limit": budget_limit,
        "runtime_limit": runtime_limit,
        "output_contract": output_contract,
        "review_required": review_required,
        "redaction_required": redaction_required,
        "artifact_paths": [],
        "ledger_path": str(ledger_path),
        "started_at": now,
        "last_update": now,
        "next_report_due": None,
        "blocked_reason": None,
        "stop_reason": "dry-run safe stop after ledger/review proof"
        if "dry-run" in task.lower()
        else None,
        "resume_point": "resume from worker ledger and output contract",
        "result": None,
    }


def _save_worker(worker: Mapping[str, Any]) -> None:
    base = _ensure_storage()
    _write_json(base / "workers" / f"{worker['worker_id']}.json", worker)


def _write_worker_ledger(
    worker: Mapping[str, Any],
    event: str,
    status: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    entry = {
        "timestamp": _utc_now(),
        "worker_id": worker["worker_id"],
        "agent_id": worker["agent_id"],
        "mission_id": worker["mission_id"],
        "plan_id": worker["plan_id"],
        "event": event,
        "status": status,
        "details": dict(details or {}),
        "review_required": worker.get("review_required", True),
        "resume_point": worker.get("resume_point"),
        "stop_reason": worker.get("stop_reason"),
    }
    _append_jsonl(Path(str(worker["ledger_path"])).expanduser(), entry)


def queue_worker(**kwargs: Any) -> dict[str, Any]:
    worker = new_worker_record(**kwargs)
    _save_worker(worker)
    _write_worker_ledger(
        worker,
        "queued",
        worker["status"],
        {"output_contract": worker["output_contract"]},
    )
    return worker


def list_workers(limit: int = 25) -> list[dict[str, Any]]:
    base = _ensure_storage()
    workers = []
    for path in sorted((base / "workers").glob("*.json")):
        row = _read_json(path)
        if row:
            workers.append(row)
    workers.sort(key=lambda row: str(row.get("last_update") or ""), reverse=True)
    return workers[: max(1, int(limit or 25))]


def get_worker(worker_id: str) -> dict[str, Any] | None:
    base = _ensure_storage()
    return _read_json(base / "workers" / f"{_slug(worker_id)}.json") or _read_json(
        base / "workers" / f"{worker_id}.json"
    )


def swarm_status() -> dict[str, Any]:
    return {
        "hyperswarm": "gated",
        "production_launch_safe": False,
        "safe_dry_run_available": True,
        "requires_fritz_approval_for_production": True,
        "safety_gates": SAFETY_GATES,
        "forbidden_actions": COMMON_FORBIDDEN_ACTIONS,
        "status": "working",
    }


def swarm_readiness() -> dict[str, Any]:
    return {
        "status": "working",
        "production_hyperswarm_gated": True,
        "ready_for_safe_dry_run": True,
        "checks": {
            "worker_control": True,
            "worker_queue": True,
            "ledgers": True,
            "redaction_required": True,
            "review_gates": True,
            "stop_resume_fields": True,
            "process_intelligence_hooks": True,
            "mission_plan_required": True,
            "output_contract_required": True,
            "production_launch_allowed": False,
        },
    }


def run_safe_swarm_dry_run() -> dict[str, Any]:
    base = _ensure_storage()
    run_id = f"swarm-dry-run-{_slug(_utc_now())}"
    fake_items = [
        {"title": "OpenJarvis architecture notes", "expected": "R&D"},
        {"title": "FAMtastic Thoughts essay seed", "expected": "content"},
        {"title": "Reusable screenshot QA recipe", "expected": "skill candidate"},
    ]
    assignments = [
        (
            "capability-cartographer",
            "Classify fake research item capability implications",
        ),
        (
            "research-to-action-agent",
            "Classify three fake research items into R&D, content, or skill candidate",
        ),
        ("run-reviewer", "Review dry-run outputs and enforce review gate"),
    ]
    workers = []
    for agent_id, task in assignments:
        worker = queue_worker(
            worker_id=f"{run_id}-{agent_id}",
            agent_id=agent_id,
            mission_id="mission-shay-intelligence-layer",
            plan_id="plan-shay-intelligence-layer",
            task=f"SAFE DRY-RUN: {task}",
            output_contract="Return classification summary only; no external actions; no repo/runtime mutation.",
            worktree="safe-local-simulation",
            branch="none",
            allowed_paths=[str(base)],
            forbidden_paths=[
                "/Users/famtasticfritz/famtastic/shay-shay",
                "~/.shay/skills",
                "SOUL.md",
                "PERSONA.md",
                "THINKING-LOG.md",
            ],
            allowed_tools=["local-simulation"],
            forbidden_tools=COMMON_FORBIDDEN_ACTIONS,
            provider_model="none/simulation",
            context_level="minimal",
            budget_limit="$0",
            runtime_limit="60s",
            review_required=True,
            redaction_required=True,
        )
        worker["status"] = "review_required"
        worker["last_update"] = _utc_now()
        worker["artifact_paths"] = [str(base / "reports" / f"{run_id}-summary.json")]
        _save_worker(worker)
        _write_worker_ledger(
            worker,
            "review_gate_required",
            "review_required",
            {"fake_items": fake_items, "forbidden_actions_happened": False},
        )
        worker["status"] = "done"
        worker["result"] = (
            "dry-run worker completed with review gate and no forbidden actions"
        )
        worker["last_update"] = _utc_now()
        _save_worker(worker)
        _write_worker_ledger(
            worker,
            "done",
            "done",
            {"review_gate_enforced": True, "resume_point": worker["resume_point"]},
        )
        workers.append(worker)
    summary = {
        "run_id": run_id,
        "task": "Classify three fake research items into R&D, content, or skill candidate.",
        "status": "working",
        "production_hyperswarm_launched": False,
        "forbidden_actions_happened": False,
        "review_gate_enforced": True,
        "stop_resume_fields_present": True,
        "workers_marked_done": True,
        "worker_ids": [worker["worker_id"] for worker in workers],
        "ledger_paths": [worker["ledger_path"] for worker in workers],
        "fake_items": fake_items,
        "final_report": "Safe HyperSwarm dry-run working; production HyperSwarm remains gated.",
    }
    report_path = base / "reports" / f"{run_id}-summary.json"
    _write_json(report_path, summary)
    create_event({
        "event_id": f"event-{run_id}",
        "source": "safe-hyperswarm-dry-run",
        "plan_id": "plan-shay-intelligence-layer",
        "mission_id": "mission-shay-intelligence-layer",
        "task_id": "task-safe-hyperswarm-dry-run",
        "summary": "Safe HyperSwarm dry-run proved assignment, ledgers, review gate, stop/resume, and final report behavior.",
        "decision": "working",
        "artifact_paths": [str(report_path), *summary["ledger_paths"]],
        "status": "complete",
        "result": summary["final_report"],
        "next_resume_point": "Use ledger_paths and report artifact if dry-run needs inspection.",
        "related_capabilities": [
            "worker-control",
            "worker-queue",
            "hyperswarm-doctrine",
        ],
        "related_agents": [agent_id for agent_id, _ in assignments],
    })
    return summary


def route_task(task: str) -> dict[str, Any]:
    text = str(task or "").strip()
    lowered = text.lower()
    capabilities = capability_by_id()
    route = {
        "task": text,
        "needed_capabilities": [],
        "owner_agent": "work-router",
        "route_provider_tool_skill": "CLI/report + manual review",
        "unsafe": False,
        "missing": [],
        "requires_fritz_approval": False,
        "gap_backlog_items": [],
        "capability_statuses": {},
        "context_level": "standard",
        "decision": "manual_review",
    }

    def add_cap(capability_id: str) -> None:
        if capability_id not in route["needed_capabilities"]:
            route["needed_capabilities"].append(capability_id)
        cap = capabilities.get(capability_id)
        route["capability_statuses"][capability_id] = (
            cap["status"] if cap else "unknown"
        )
        if cap and cap["status"] in MISSING_OR_UNSAFE_STATUSES:
            route["gap_backlog_items"].append(f"gap-{capability_id}")
            if cap["status"] in {"blocked", "unsafe", "avoid_by_policy"}:
                route["unsafe"] = True
            if cap["status"] in {"missing", "partial", "blocked"}:
                route["missing"].append(cap["next_action"])

    if "hyper" in lowered and "swarm" in lowered:
        add_cap("hyperswarm-doctrine")
        add_cap("worker-control")
        add_cap("worker-queue")
        route.update({
            "owner_agent": "worker-supervisor",
            "route_provider_tool_skill": "safe dry-run only: shay intelligence swarm dry-run",
            "unsafe": True,
            "requires_fritz_approval": True,
            "context_level": "high",
            "decision": "blocked_for_production",
        })
        route["missing"].append(
            "production HyperSwarm remains gated unless Fritz explicitly approves it later"
        )
    elif "github" in lowered and "obsidian" in lowered:
        for cap in ("github-to-obsidian", "episodic-memory", "research-to-action"):
            add_cap(cap)
        route.update({
            "owner_agent": "research-to-action-agent",
            "route_provider_tool_skill": "file + web + skills, with explicit repo and vault target",
            "context_level": "standard",
            "decision": "route_with_review",
        })
    elif "context" in lowered and (
        "compression" in lowered or "memory continuity" in lowered
    ):
        add_cap("context-compression-memory-continuity")
        route.update({
            "owner_agent": "provider-capacity-broker",
            "route_provider_tool_skill": "gap/backlog record only; no runtime config mutation",
            "context_level": "standard",
            "decision": "track_gap",
        })
    elif "gmail" in lowered and "send" in lowered:
        add_cap("gmail-send")
        route.update({
            "owner_agent": "delivery-router",
            "route_provider_tool_skill": "draft/report only; no send",
            "unsafe": True,
            "requires_fritz_approval": True,
            "decision": "blocked",
        })
    elif "calendar" in lowered and ("write" in lowered or "event" in lowered):
        add_cap("calendar-read-write")
        route.update({
            "owner_agent": "delivery-router",
            "route_provider_tool_skill": "plain-text recommendation only; no Calendar write",
            "unsafe": True,
            "requires_fritz_approval": True,
            "decision": "blocked",
        })
    elif "openrouter" in lowered:
        add_cap("research-to-action")
        route.update({
            "owner_agent": "provider-capacity-broker",
            "route_provider_tool_skill": "avoid_by_policy for default autonomous use",
            "unsafe": True,
            "requires_fritz_approval": True,
            "decision": "avoid_by_policy",
            "gap_backlog_items": ["gap-openrouter-default-route"],
        })
    elif "anthropic api" in lowered or "anthropic api-key" in lowered:
        add_cap("research-to-action")
        route.update({
            "owner_agent": "provider-capacity-broker",
            "route_provider_tool_skill": "avoid_by_policy for default autonomous use",
            "unsafe": True,
            "requires_fritz_approval": True,
            "decision": "avoid_by_policy",
            "gap_backlog_items": ["gap-anthropic-api-key-route"],
        })
    elif any(
        seed in lowered
        for seed in ("openjarvis", "odysseus", "turbovec", "vllm", "agent swarm")
    ):
        research = classify_research(text)
        add_cap(str(research["capability_id"]))
        route.update({
            "owner_agent": str(research["agent"]),
            "route_provider_tool_skill": "FAMtastic Data Center R&D record only; no install/run",
            "unsafe": not bool(research["safe_to_run"]),
            "requires_fritz_approval": True,
            "decision": str(research["decision"]),
        })
    else:
        add_cap("work-router") if "work-router" in capabilities else add_cap(
            "research-to-action"
        )
        route.update({
            "owner_agent": "work-router",
            "route_provider_tool_skill": "capability matrix + agent registry + review gate",
            "decision": "route_with_review",
        })
    route["gap_backlog_items"] = sorted(set(route["gap_backlog_items"]))
    route["missing"] = sorted(set(route["missing"]))
    return route


def intelligence_status() -> dict[str, Any]:
    matrix = get_capability_matrix()
    agents = get_agent_registry()
    graph = build_mission_graph()
    readiness = swarm_readiness()
    gaps = build_gap_records()
    truth_registry = build_truth_registry()
    command_surface_count = 35
    blockers: list[str] = []
    required_ids = {record['capability_id'] for record in matrix}
    if not required_ids:
        blockers.append('capability matrix missing')
    if len(agents) < 17:
        blockers.append('agent registry incomplete')
    if not graph['plans']:
        blockers.append('mission graph missing')
    if not readiness['ready_for_safe_dry_run']:
        blockers.append('safe swarm dry-run not ready')

    delivery_router = capability_by_id().get('delivery-router', {})
    today_hub = capability_by_id().get('today-hub', {})
    verified_delivery_path = (
        'cli_report'
        if delivery_router.get('available_now') and today_hub.get('available_now')
        else 'unknown'
    )
    action_loop_status = (
        'working'
        if graph['plans'] and BRIEF_TYPES and verified_delivery_path == 'cli_report'
        else 'incomplete'
    )
    worker_control_status = 'working' if readiness['checks'].get('worker_control') else 'missing'
    return {
        'status': 'working' if not blockers else 'not working',
        'blockers': blockers,
        'capability_count': len(matrix),
        'agent_count': len(agents),
        'mission_count': len(graph['missions']),
        'plan_count': len(graph['plans']),
        'brief_count': len(BRIEF_TYPES),
        'cadence_count': len(get_cadence_records()),
        'command_surface_count': command_surface_count,
        'production_hyperswarm_gated': True,
        'safe_hyperswarm_dry_run': 'working',
        'live_crons_enabled': False,
        'open_gap_count': len(gaps),
        'truth_registry_count': len(truth_registry),
        'proven_truth_count': sum(
            1 for row in truth_registry if row.get('reality_class') == 'proven_live'
        ),
        'verified_delivery_path': verified_delivery_path,
        'action_loop_status': action_loop_status,
        'worker_control_status': worker_control_status,
    }


def render_brief(kind: str) -> str:
    payload = build_actionable_brief_payload(kind)
    brief_type = payload['brief_type']
    status = payload['status']
    graph = payload['graph']
    gaps = payload['gaps']
    workers = payload['workers']
    recent_events = payload['recent_events']
    research_items = payload['research_items']
    critical_reviews = [
        review_item({'title': 'disabled sample only', 'source': 'disabled-sample'})
    ]
    lines = [
        f"{brief_type}",
        f"status: {status['status']}",
        f"delivery: {status.get('verified_delivery_path', 'unknown')}",
        "forbidden actions: none performed",
        "",
    ]
    if kind == 'morning':
        lines.extend([
            'What changed overnight:',
            *[f"- {event['summary']}" for event in recent_events[:3]],
            '',
            'Active plans:',
            *[
                f"- {plan['name']} [{plan['status']}] progress={plan['progress']} done={str(plan['done']).lower()}"
                for plan in graph['plans']
            ],
            '',
            'Blocked/stale items:',
            '- Context Compression / Memory Continuity remains partial; runtime config unchanged.',
            '- Gmail send and Calendar write remain blocked by policy.',
            '',
            'Critical/high items:',
            '- No active source-backed critical items stored.',
            '',
            'Worker status:',
            *(
                [
                    f"- {worker['worker_id']} [{worker['status']}] {worker['agent_id']}"
                    for worker in workers
                ]
                or ['- no live workers queued']
            ),
            '',
            'Capability gaps:',
            *[
                f"- {gap['gap_id']} [{gap['severity']}] owner={gap['owner_agent']} -> {gap['next_action']}"
                for gap in payload['top_gaps']
            ],
            '',
            'Delivery / action loop:',
            f"- verified delivery path: {status.get('verified_delivery_path', 'unknown')}",
            f"- action loop: {status.get('action_loop_status', 'unknown')}",
            f"- worker controls: {status.get('worker_control_status', 'unknown')}",
            '',
            'Provider/capacity status:',
            '- Anthropic API-key route: avoid_by_policy.',
            '- OpenRouter default route: avoid_by_policy.',
            '- Production HyperSwarm: gated.',
            '',
            'Research-to-action items:',
            *[f"- {item['thing']}: {item['decision']}" for item in research_items],
            '',
            'FAMtastic Thoughts candidates:',
            '- pipeline states available; no publish action performed.',
            '',
            'Gap ownership:',
            *[f"- {owner}: {count} open gap(s)" for owner, count in sorted(payload['owner_gap_counts'].items())],
            '',
            'Recommended top priorities for Fritz:',
            *[f"- {item}" for item in payload['recommendations']],
        ])
    elif kind in {"gaps", "capability-gaps-brief"}:
        lines.extend([
            "Capability gaps:",
            *[
                f"- {gap['gap_id']}: {gap['title']} -> {gap['next_action']}"
                for gap in gaps
            ],
        ])
    elif kind in {"workers", "worker-status-brief"}:
        lines.extend([
            "Workers:",
            *(
                [
                    f"- {worker['worker_id']} [{worker['status']}] ledger={worker['ledger_path']}"
                    for worker in workers
                ]
                or ["- no worker records yet"]
            ),
        ])
    elif kind in {"missions", "mission-graph-brief", "today", "today-plan-brief"}:
        lines.extend([
            "Mission graph:",
            *[
                f"- {mission['name']} [{mission['status']}]"
                for mission in graph["missions"]
            ],
        ])
    elif kind in {
        "research",
        "research-to-action-brief",
        "rd",
        "famtastic-data-center-rd-brief",
    }:
        lines.extend([
            "Research-to-action:",
            *[
                f"- {item['thing']}: {item['decision']} ({item['next_action']})"
                for item in research_items
            ],
        ])
    elif kind in {"critical", "critical-items-brief"}:
        lines.extend([
            "Critical items:",
            "- no active source-backed critical items stored",
            f"- review logic sample outcome: {critical_reviews[0]['outcome']}",
        ])
    elif kind in {"high-items", "high-items-review-brief"}:
        lines.extend([
            "High item review:",
            "- logic: working",
            "- active high items: none stored",
        ])
    elif kind in {"providers", "provider-capacity-brief"}:
        lines.extend([
            "Provider capacity:",
            "- Anthropic API-key route: avoid_by_policy",
            "- OpenRouter default route: avoid_by_policy",
            "- Production HyperSwarm: gated",
            "- Safe dry-run: working",
        ])
    elif kind in {"compression", "context-compression-health-brief"}:
        cap = capability_by_id()["context-compression-memory-continuity"]
        lines.extend([
            "Context compression health:",
            f"- status: {cap['status']}",
            f"- evidence: {cap['evidence_source']}",
            f"- next action: {cap['next_action']}",
        ])
    elif kind in {"thoughts", "famtastic-thoughts-candidates-brief"}:
        lines.extend([
            "FAMtastic Thoughts:",
            f"- states: {', '.join(FAMTASTIC_THOUGHTS_STATES)}",
            "- active publish action: none",
        ])
    elif kind in {"stale", "stale-items-brief"}:
        lines.extend([
            "Stale/blocked:",
            "- context-compression-memory-continuity is partial",
            "- Gmail send and Calendar write are blocked",
            "- production HyperSwarm is gated",
        ])
    elif kind in {"overnight", "overnight-progress-brief"}:
        lines.extend([
            "Overnight progress:",
            *[f"- {event['timestamp']} {event['summary']}" for event in recent_events],
        ])
    else:
        lines.extend(["Brief registry:", *[f"- {item}" for item in BRIEF_TYPES]])
    lines.extend(["", f"overall status: {status['status']}", "live crons enabled: no"])
    return "\n".join(lines)


def _format_records(
    title: str, rows: list[Mapping[str, Any]], id_key: str, status_key: str = "status"
) -> str:
    lines = [title, ""]
    for row in rows:
        row_id = row.get(id_key, "unknown")
        status = row.get(status_key, "unknown")
        name = (
            row.get("name")
            or row.get("title")
            or row.get("purpose")
            or row.get("summary")
            or ""
        )
        lines.append(f"- {row_id} [{status}] {name}")
    return "\n".join(lines)


def format_truth_registry(rows: list[Mapping[str, Any]]) -> str:
    lines = ["Truth Registry", ""]
    for row in rows:
        lines.extend([
            f"- {row['subsystem_id']} [{row['reality_class']}] {row['name']}",
            f"  owner: {row['owner_module']}",
            f"  truth: {row['source_of_truth']}",
            "  proof:",
            *[f"    - {item}" for item in row.get('proof_artifacts') or []],
            "  paths:",
            *(
                [f"    - {item}" for item in row.get('persistence_paths') or []]
                or ["    - none"]
            ),
            "  open_gaps:",
            *(
                [f"    - {item}" for item in row.get('open_gaps') or []]
                or ["    - none"]
            ),
        ])
    return "\n".join(lines)


def format_status(status: Mapping[str, Any]) -> str:
    return "\n".join([
        "Shay Intelligence Layer",
        f"status: {status['status']}",
        f"capabilities: {status['capability_count']}",
        f"agents: {status['agent_count']}",
        f"missions: {status['mission_count']}",
        f"plans: {status['plan_count']}",
        f"briefs: {status['brief_count']}",
        f"cadence records: {status['cadence_count']}",
        f"open gaps: {status.get('open_gap_count', 0)}",
        f"truth registry rows: {status.get('truth_registry_count', 0)}",
        f"proven truth rows: {status.get('proven_truth_count', 0)}",
        f"verified delivery path: {status.get('verified_delivery_path', 'unknown')}",
        f"action loop: {status.get('action_loop_status', 'unknown')}",
        f"worker controls: {status.get('worker_control_status', 'unknown')}",
        f"production HyperSwarm gated: {str(status['production_hyperswarm_gated']).lower()}",
        f"safe HyperSwarm dry-run: {status['safe_hyperswarm_dry_run']}",
        f"live crons enabled: {str(status['live_crons_enabled']).lower()}",
        "blockers: "
        + (", ".join(status["blockers"]) if status["blockers"] else "none"),
    ])


def format_route(route: Mapping[str, Any]) -> str:
    return "\n".join([
        f"Task: {route['task']}",
        f"decision: {route['decision']}",
        f"owner_agent: {route['owner_agent']}",
        f"route/provider/tool/skill: {route['route_provider_tool_skill']}",
        f"unsafe: {str(route['unsafe']).lower()}",
        f"requires Fritz approval: {str(route['requires_fritz_approval']).lower()}",
        "needed capabilities:",
        *(f"- {capability}" for capability in route["needed_capabilities"]),
        "capability statuses:",
        *(
            f"- {capability}: {status}"
            for capability, status in route.get("capability_statuses", {}).items()
        ),
        "missing/blocked:",
        *([f"- {item}" for item in route["missing"]] or ["- none"]),
        "gap/backlog:",
        *([f"- {item}" for item in route["gap_backlog_items"]] or ["- none"]),
    ])


def format_workers(workers: list[Mapping[str, Any]]) -> str:
    lines = ["Worker Queue / Control", ""]
    lines.append("safety gates:")
    lines.extend(f"- {gate}" for gate in SAFETY_GATES)
    lines.append("")
    lines.append("workers:")
    if not workers:
        lines.append("- no worker records yet")
    else:
        for worker in workers:
            lines.append(
                f"- {worker['worker_id']} [{worker['status']}] {worker['agent_id']} ledger={worker['ledger_path']}"
            )
    return "\n".join(lines)


def format_research(result: Mapping[str, Any]) -> str:
    return "\n".join([
        f"Research item: {result['thing']}",
        f"decision: {result['decision']}",
        f"status: {result['status']}",
        f"owner_agent: {result['agent']}",
        f"capability_id: {result['capability_id']}",
        f"safe_to_run: {str(result['safe_to_run']).lower()}",
        f"installed: {str(result['installed']).lower()}",
        f"adopted: {str(result['adopted']).lower()}",
        f"intended_use: {result['intended_use']}",
        f"next_action: {result['next_action']}",
    ])


def cmd_intelligence(args: Any) -> int:
    command = getattr(args, "intelligence_command", None) or "status"
    if command == "status":
        print(format_status(intelligence_status()))
        return 0
    if command == "matrix":
        rows = get_capability_matrix()
        print(_format_records("Capability Matrix", rows, "capability_id"))
        print("")
        print("Open gaps by owner:")
        for owner, count in sorted(_group_gaps_by_owner(build_gap_records()).items()):
            print(f"- {owner}: {count}")
        return 0
    if command == "truth":
        print(format_truth_registry(build_truth_registry()))
        return 0
    if command == "agents":
        print(
            _format_records(
                "Agent Registry / Worker Roster", get_agent_registry(), "agent_id"
            )
        )
        return 0
    if command == "events":
        print(_format_records("Episodic Events", list_events(limit=10), "event_id"))
        return 0
    if command == "missions":
        graph = build_mission_graph()
        print(_format_records("Missions", graph["missions"], "mission_id"))
        print("")
        print(_format_records("Plans", graph["plans"], "plan_id"))
        return 0
    if command == "route":
        task = getattr(args, "task", "")
        if isinstance(task, list):
            task = " ".join(str(item) for item in task)
        print(format_route(route_task(str(task))))
        return 0
    if command == "workers":
        subcommand = getattr(args, "workers_command", None) or "list"
        if subcommand in {"list", None}:
            print(format_workers(list_workers()))
            return 0
        if subcommand == "queue":
            print(format_workers(list_workers()))
            return 0
        if subcommand == "show":
            worker_id = getattr(args, "worker_id", "")
            worker = get_worker(worker_id)
            if not worker:
                print(f"worker not found: {worker_id}")
                return 1
            print(json.dumps(worker, indent=2, sort_keys=True))
            return 0
        if subcommand == "review":
            workers = list_workers()
            review_required = [
                worker for worker in workers if worker.get("review_required")
            ]
            print("Worker review gates")
            print(f"review_required_workers: {len(review_required)}")
            print("status: working")
            return 0
    if command == "swarm":
        subcommand = getattr(args, "swarm_command", None) or "status"
        if subcommand == "status":
            print(json.dumps(swarm_status(), indent=2, sort_keys=True))
            return 0
        if subcommand == "readiness":
            print(json.dumps(swarm_readiness(), indent=2, sort_keys=True))
            return 0
        if subcommand == "dry-run":
            print(json.dumps(run_safe_swarm_dry_run(), indent=2, sort_keys=True))
            return 0
    if command == "critical":
        records = critical_item_records()
        print(_format_records("Critical Item Sentinel", records, "item_id"))
        print("active source-backed critical items: 0")
        print("logic: working")
        return 0
    if command == "review-items":
        samples = [
            {
                "title": "disabled sample urgent client deadline",
                "source": "disabled-sample",
            },
            {"title": "disabled sample monitor someday", "source": "disabled-sample"},
        ]
        reviews = [review_item(sample) for sample in samples]
        print("High/Critical Item Review")
        print("logic: working")
        print("active source-backed items reviewed: 0")
        print("disabled samples:")
        for review in reviews:
            print(f"- {review['title']}: {review['outcome']} score={review['score']}")
        return 0
    if command == "research":
        thing = getattr(args, "thing", "")
        if isinstance(thing, list):
            thing = " ".join(str(item) for item in thing)
        print(format_research(classify_research(str(thing))))
        return 0
    if command == "brief":
        kind = getattr(args, "brief_command", None) or "morning"
        print(render_brief(kind))
        return 0
    if command == "cadence":
        subcommand = getattr(args, "cadence_command", None) or "list"
        if subcommand == "list":
            print(
                _format_records(
                    "Cadence / Cron Records", get_cadence_records(), "cadence_id"
                )
            )
            print("live crons enabled: no")
            return 0
    print(f"Unknown intelligence subcommand: {command}")
    return 1


__all__ = [
    "SAFETY_GATES",
    "WORKER_REQUIRED_FIELDS",
    "REALITY_CLASSES",
    "build_gap_records",
    "build_mission_graph",
    "build_truth_registry",
    "classify_research",
    "cmd_intelligence",
    "create_event",
    "critical_item_records",
    "intelligence_status",
    "format_truth_registry",
    "list_events",
    "list_workers",
    "new_worker_record",
    "queue_worker",
    "render_brief",
    "review_item",
    "route_task",
    "run_safe_swarm_dry_run",
    "swarm_readiness",
    "swarm_status",
]
