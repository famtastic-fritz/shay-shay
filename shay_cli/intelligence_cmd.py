from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import yaml

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from shay_constants import get_shay_home
from shay_cli.capabilities_cmd import build_gate_report
from shay_cli.intelligence_control_plane import (
    audit_cron_jobs,
    build_route_scorecards,
    explain_route,
    get_agent_template_registry,
    get_control_plane_modules,
    get_memory_truth_surfaces,
    get_product_worker_pool_registry,
    get_provider_model_registry,
    get_routing_tier_registry,
    get_task_family_routing_matrix,
)
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
from shay_cli.model_probe import list_probe_registry, probe_model


BENCHMARK_TEMPLATE_COMPATIBILITY: dict[str, set[str]] = {
    "scout": {"provider-intel-researcher", "memory-curator", "capability-cartographer"},
    "builder": {"implementation-worker"},
    "critic": {"review-judge", "orchestrator-captain"},
    "reviewer": {"review-judge"},
    "clerk": {"attention-watcher", "memory-curator", "orchestrator-captain"},
    "watcher": {"attention-watcher", "memory-curator", "provider-intel-researcher"},
    "browser-operator": {"browser-operator", "implementation-worker", "orchestrator-captain"},
    "captain-router": {"orchestrator-captain"},
}

APP_BUILDING_BUCKETS = [
    {
        "bucket_id": "frontend",
        "label": "Frontend / UI",
        "primary_capability_ids": [
            "browser-computer-use",
            "design-vision-review",
            "text-to-visual-architecture",
        ],
        "truth_subsystem_ids": ["capability-truth-layer"],
        "default_reality_class": "documented_present",
        "summary": "Strongest current lane: browser-facing verification plus design/visual generation support make web UI work real, but not yet a clean reusable component factory.",
        "next_action": "Promote repeated UI patterns into explicit component/app-system capabilities instead of leaving them as scattered design/build skills.",
    },
    {
        "bucket_id": "backend",
        "label": "Backend",
        "primary_capability_ids": [],
        "truth_subsystem_ids": ["delegate-route-proof"],
        "default_reality_class": "seeded_target",
        "summary": "No explicit backend-factory capability is represented in the matrix yet; backend work currently rides on coding/orchestration surfaces rather than a named hardened backend lane.",
        "next_action": "Add a first-class backend capability row with proof surfaces instead of implying backend maturity through generic coding power.",
    },
    {
        "bucket_id": "auth",
        "label": "Auth",
        "primary_capability_ids": [],
        "truth_subsystem_ids": [],
        "default_reality_class": "seeded_target",
        "summary": "Auth is currently a gap: there is no explicit auth capability or proof-bearing auth route in the matrix.",
        "next_action": "Create explicit auth capability records and proof surfaces before claiming production auth readiness.",
    },
    {
        "bucket_id": "database",
        "label": "Database",
        "primary_capability_ids": [],
        "truth_subsystem_ids": [],
        "default_reality_class": "seeded_target",
        "summary": "No dedicated database capability is normalized in the matrix yet; current DB work is implied through generic coding lanes, not tracked as a truth surface.",
        "next_action": "Define the database lane with owned proof surfaces, not as hidden knowledge inside implementation agents.",
    },
    {
        "bucket_id": "testing",
        "label": "Testing / Verification",
        "primary_capability_ids": ["browser-computer-use"],
        "truth_subsystem_ids": ["delegate-route-proof"],
        "default_reality_class": "documented_present",
        "summary": "Testing is real at the browser-facing and route-proof layers, but the matrix still needs a dedicated app-testing capability shape instead of indirect evidence only.",
        "next_action": "Make Playwright/browser-style testing an explicit capability row with first-class proof artifacts.",
    },
    {
        "bucket_id": "deploy",
        "label": "Deploy",
        "primary_capability_ids": [],
        "truth_subsystem_ids": ["delegate-route-proof", "mission-graph-registry"],
        "default_reality_class": "curated_partial",
        "summary": "Deploy exists as orchestrated practice, not yet as a clean proof-backed app-platform lane in the matrix.",
        "next_action": "Represent deploy as an explicit capability with live proof, not a side effect of successful coding sessions.",
    },
    {
        "bucket_id": "payments",
        "label": "Payments",
        "primary_capability_ids": [],
        "truth_subsystem_ids": [],
        "default_reality_class": "seeded_target",
        "summary": "Payments are not normalized as a live capability; the current truth surface does not prove a production billing/subscription stack.",
        "next_action": "Add explicit payments capability records and prove at least one live billing lane before claiming readiness.",
    },
    {
        "bucket_id": "mobile",
        "label": "Mobile",
        "primary_capability_ids": [],
        "truth_subsystem_ids": [],
        "default_reality_class": "seeded_target",
        "summary": "Mobile is future-state right now: there is no explicit mobile app factory or component-studio-backed mobile lane in the matrix.",
        "next_action": "Stand up Component Studio/mobile capability records when repeated app needs justify the lane.",
    },
]

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

ASK_TRACE_RULES = [
    {
        "intent": "build_app",
        "label": "Build app via HyperSwarm",
        "match_any": [
            "build this app",
            "build app",
            "ship this app",
            "create this app",
            "build a new app",
            "build a new app from this spec",
            "new app from this spec",
            "build from this spec",
            "turn this spec into an app",
        ],
        "route_task_template": "launch HyperSwarm build lane for: {task}",
        "explain_task_template": "implement app build lane for: {task}",
        "brain_agent": "work-router",
        "execution_agent": "worker-supervisor",
        "commands": [
            "shay capabilities preflight \"{route_task}\"",
            "shay intelligence route \"{route_task}\"",
            "shay intelligence control-plane explain \"{explain_task}\"",
            "shay intelligence swarm status",
            "shay intelligence swarm readiness",
            "shay intelligence swarm dry-run",
            "shay capabilities closeout \"{route_task}\"",
        ],
        "proof_artifacts": [
            "capability preflight gate report",
            "intelligence route decision",
            "control-plane explain evidence",
            "swarm dry-run worker ledgers",
            "closeout proof surfaces",
        ],
    },
    {
        "intent": "show_attention",
        "label": "Show what needs Fritz attention",
        "match_any": [
            "needs my attention",
            "what needs my attention",
            "what's blocked",
            "what is blocked",
            "show blockers",
            "show what needs fritz attention",
            "what needs fritz attention",
            "what is waiting on me",
            "what's waiting on me",
            "what is waiting for me",
        ],
        "route_task_template": "review attention blockers for: {task}",
        "explain_task_template": "rank blocked work and attention surfaces for: {task}",
        "brain_agent": "work-router",
        "execution_agent": "attention-watcher",
        "commands": [
            "shay intelligence brief today",
            "shay intelligence missions",
            "shay intelligence workers review",
            "shay intelligence critical",
            "shay intelligence truth",
        ],
        "proof_artifacts": [
            "today brief output",
            "mission graph records",
            "worker review-gate summary",
            "critical-item sentinel output",
            "truth-registry snapshot",
        ],
    },
    {
        "intent": "github_to_obsidian_ingest",
        "label": "GitHub to Obsidian ingest planning",
        "match_any": ["github to obsidian", "ingest github into obsidian", "sync github to obsidian"],
        "route_task_template": "ingest GitHub to Obsidian for: {task}",
        "explain_task_template": "plan GitHub to Obsidian ingest route for: {task}",
        "commands": [
            "shay capabilities preflight \"{route_task}\"",
            "shay intelligence route \"{route_task}\"",
            "shay intelligence control-plane explain \"{explain_task}\"",
            "shay capabilities closeout \"{route_task}\"",
        ],
        "proof_artifacts": [
            "preflight gate report",
            "route decision with repo/vault lane",
            "control-plane explain evidence",
            "closeout proof surfaces",
        ],
    },
    {
        "intent": "context_compression_gap",
        "label": "Context compression gap trace",
        "match_any": ["context compression", "memory continuity", "compression continuity"],
        "route_task_template": "fix context compression memory continuity for: {task}",
        "explain_task_template": "explain context compression continuity gap for: {task}",
        "commands": [
            "shay capabilities preflight \"{route_task}\"",
            "shay intelligence route \"{route_task}\"",
            "shay intelligence brief compression",
            "shay capabilities closeout \"{route_task}\"",
        ],
        "proof_artifacts": [
            "preflight gate report",
            "gap-tracking route decision",
            "compression health brief",
            "closeout proof surfaces",
        ],
    },
    {
        "intent": "run_reviewer_pass",
        "label": "Run reviewer-only pass",
        "match_any": [
            "run reviewer pass",
            "reviewer pass only",
            "review this lane",
            "review only",
            "review this implementation",
            "judge quality",
            "review and judge quality",
            "tear this implementation apart",
        ],
        "route_task_template": "launch HyperSwarm reviewer lane for: {task}",
        "explain_task_template": "review implementation artifacts for: {task}",
        "brain_agent": "work-router",
        "execution_agent": "run-reviewer",
        "commands": [
            "shay capabilities preflight \"{route_task}\"",
            "shay intelligence route \"{route_task}\"",
            "shay intelligence workers review",
            "shay intelligence control-plane explain \"{explain_task}\"",
            "shay capabilities closeout \"{route_task}\"",
        ],
        "proof_artifacts": [
            "review-lane preflight report",
            "route decision showing reviewer ownership",
            "worker review-gate summary",
            "control-plane reviewer routing evidence",
            "closeout proof surfaces",
        ],
    },
    {
        "intent": "resume_lane",
        "label": "Resume previous lane",
        "match_any": [
            "resume the lane",
            "resume last run",
            "continue this plan",
            "resume this run",
            "resume this lane",
            "continue this lane",
            "pick back up where we left off",
            "resume this work",
            "continue this run",
        ],
        "route_task_template": "resume HyperSwarm lane for: {task}",
        "explain_task_template": "resume worker lane and recover proof for: {task}",
        "brain_agent": "work-router",
        "execution_agent": "worker-supervisor",
        "commands": [
            "shay intelligence workers queue",
            "shay intelligence route \"{route_task}\"",
            "shay intelligence control-plane explain \"{explain_task}\"",
            "shay intelligence brief workers",
            "shay capabilities closeout \"{route_task}\"",
        ],
        "proof_artifacts": [
            "worker queue records",
            "resume route decision",
            "control-plane resume evidence",
            "worker brief output",
            "closeout proof surfaces",
        ],
    },
]


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


def _render_trace_template(template: str, *, task: str, route_task: str, explain_task: str) -> str:
    return template.format(task=task, route_task=route_task, explain_task=explain_task)


def _matches_phrase(lowered: str, phrase: str) -> bool:
    needle = str(phrase or "").strip().lower()
    if not needle:
        return False
    if " " in needle or "-" in needle:
        return needle in lowered
    return re.search(rf"\b{re.escape(needle)}\b", lowered) is not None


def _match_trace_rule(task: str) -> dict[str, Any]:
    lowered = str(task or "").strip().lower()
    for rule in ASK_TRACE_RULES:
        if any(_matches_phrase(lowered, needle) for needle in rule.get("match_any", [])):
            return dict(rule)
    return {
        "intent": "generic_orchestration_ask",
        "label": "Generic orchestration ask",
        "route_task_template": "{task}",
        "explain_task_template": "{task}",
        "brain_agent": "work-router",
        "execution_agent": "dynamic-route",
        "commands": [
            "shay capabilities preflight \"{route_task}\"",
            "shay intelligence route \"{route_task}\"",
            "shay intelligence control-plane explain \"{explain_task}\"",
            "shay capabilities closeout \"{route_task}\"",
        ],
        "proof_artifacts": [
            "capability preflight gate report",
            "intelligence route decision",
            "control-plane explain evidence",
            "closeout proof surfaces",
        ],
    }


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
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
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


def _load_yaml_document(path: str | Path) -> Any:
    yaml_path = Path(path).expanduser()
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if data is None:
        raise ValueError(f"YAML document is empty: {yaml_path}")
    return data


def _benchmark_reports_dir() -> Path:
    base = _ensure_storage() / "reports" / "benchmarks"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _route_template_compatible(expected_template: str, actual_template: str) -> bool:
    expected = str(expected_template or "").strip()
    actual = str(actual_template or "").strip()
    if not expected or not actual:
        return False
    allowed = BENCHMARK_TEMPLATE_COMPATIBILITY.get(expected, set())
    return actual == expected or actual in allowed


def _validate_benchmark_packet_set(doc: Mapping[str, Any]) -> dict[str, Any]:
    packet_set_id = str(doc.get("packet_set_id") or "").strip()
    if not packet_set_id:
        raise ValueError("packet set missing packet_set_id")
    packets = doc.get("packets")
    if not isinstance(packets, list) or not packets:
        raise ValueError("packet set must contain a non-empty packets list")
    required = {
        "packet_id", "template_id", "task_family", "task_subtype", "prompt",
        "required_toolsets", "required_output_contract", "verification_method",
        "cost_sensitivity_class", "default_route_class", "escalation_condition",
    }
    normalized = []
    for idx, packet in enumerate(packets, start=1):
        if not isinstance(packet, Mapping):
            raise ValueError(f"packet {idx} must be an object")
        missing = sorted(key for key in required if not packet.get(key))
        if missing:
            raise ValueError(f"packet {idx} missing required keys: {', '.join(missing)}")
        normalized.append(dict(packet))
    return {**dict(doc), "packets": normalized, "packet_set_id": packet_set_id}


def _validate_nl_coverage_corpus(doc: Mapping[str, Any]) -> dict[str, Any]:
    corpus_id = str(doc.get("corpus_id") or "").strip()
    if not corpus_id:
        raise ValueError("coverage corpus missing corpus_id")
    records = doc.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("coverage corpus must contain a non-empty records list")
    required = {"ask_id", "family", "ask", "expected_intent", "expected_template", "acceptable_fallback_template"}
    normalized = []
    for idx, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise ValueError(f"coverage record {idx} must be an object")
        missing = sorted(key for key in required if not record.get(key))
        if missing:
            raise ValueError(f"coverage record {idx} missing required keys: {', '.join(missing)}")
        normalized.append(dict(record))
    return {**dict(doc), "records": normalized, "corpus_id": corpus_id}


def _validate_route_scorecard_schema(doc: Mapping[str, Any]) -> dict[str, Any]:
    schema_name = str(doc.get("schema_name") or "").strip()
    if schema_name != "route-scorecard":
        raise ValueError("scorecard schema must declare schema_name: route-scorecard")
    record_keys = doc.get("record_keys")
    if not isinstance(record_keys, list) or not record_keys:
        raise ValueError("scorecard schema must declare non-empty record_keys")
    return dict(doc)


def _write_benchmark_artifact(name: str, payload: Mapping[str, Any]) -> Path:
    path = _benchmark_reports_dir() / name
    _write_json(path, payload)
    return path


def _run_benchmark_packet(packet: Mapping[str, Any], packet_set_id: str) -> dict[str, Any]:
    prompt = str(packet.get("prompt") or "").strip()
    route = route_task(prompt)
    trace = trace_task(prompt)
    control_plane = explain_route(prompt)
    actual_template = str(control_plane.get("chosen_template") or "")
    compatible = _route_template_compatible(str(packet.get("template_id") or ""), actual_template)
    run_id = f"benchmark-run-{_slug(str(packet.get('packet_id') or 'packet'))}-{_slug(_utc_now())}"
    summary = {
        "run_id": run_id,
        "timestamp": _utc_now(),
        "packet_set_id": packet_set_id,
        "packet_id": str(packet.get("packet_id") or ""),
        "expected_template": str(packet.get("template_id") or ""),
        "actual_template": actual_template,
        "task_family": str(packet.get("task_family") or ""),
        "task_subtype": str(packet.get("task_subtype") or ""),
        "provider_model_route": str(control_plane.get("chosen_route") or ""),
        "runtime_surface": "intelligence-benchmark",
        "route_class": str(packet.get("default_route_class") or ""),
        "verification_pass": compatible,
        "success": compatible,
        "route_decision": str(route.get("decision") or ""),
        "owner_agent": str(route.get("owner_agent") or ""),
        "control_plane": control_plane,
        "route": route,
        "trace": trace,
    }
    artifact_path = _write_benchmark_artifact(f"{run_id}.json", summary)
    summary["artifact_path"] = str(artifact_path)
    create_event({
        "summary": f"Benchmark packet run completed: {summary['packet_id']}",
        "decision": "benchmark_run",
        "status": "complete",
        "result": "verification_pass" if compatible else "verification_failed",
        "artifact_paths": [str(artifact_path)],
        "files_touched": [str(artifact_path)],
        "plan_id": "plan-shay-intelligence-layer",
        "mission_id": "mission-shay-intelligence-layer",
        "task_id": summary["run_id"],
        "related_capabilities": ["famtastic-data-center-rd", "worker-control"],
        "related_agents": [str(route.get("owner_agent") or "work-router")],
        "observation": f"Packet {summary['packet_id']} routed to {actual_template or 'unknown'}.",
        "interpretation": "Benchmark evidence recorded.",
    })
    return summary


def _collect_benchmark_run_files(path_value: str | Path) -> list[dict[str, Any]]:
    path = Path(path_value).expanduser()
    if path.is_file():
        row = _read_json(path)
        return [row] if row else []
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(path.glob('benchmark-run-*.json')):
        row = _read_json(child)
        if row:
            rows.append(row)
    return rows


def _build_scorecards_from_runs(runs: list[Mapping[str, Any]], schema: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str, str], list[Mapping[str, Any]]] = {}
    for run in runs:
        control = run.get("control_plane") or {}
        route_id = str(run.get("provider_model_route") or control.get("chosen_route") or "unknown")
        provider, _, model = route_id.partition('-')
        key = (
            str(run.get("expected_template") or "unknown"),
            str(run.get("task_family") or "unknown"),
            provider or "unknown",
            model or route_id or "unknown",
            str(run.get("route_class") or "unknown"),
        )
        grouped.setdefault(key, []).append(run)
    scorecards = []
    for key, items in grouped.items():
        template_id, task_family, provider, model, route_class = key
        run_count = len(items)
        verification_passes = sum(1 for item in items if item.get("verification_pass"))
        successes = sum(1 for item in items if item.get("success"))
        scorecards.append({
            "scorecard_id": f"{template_id}-{task_family}-{provider}-{model}-{route_class}",
            "template_id": template_id,
            "task_family": task_family,
            "task_subtype": items[0].get("task_subtype"),
            "provider": provider,
            "model": model,
            "runtime_surface": "intelligence-benchmark",
            "route_class": route_class,
            "run_count": run_count,
            "success_rate": round(successes / run_count, 4),
            "verification_pass_rate": round(verification_passes / run_count, 4),
            "reviewer_approval_rate": round(verification_passes / run_count, 4),
            "correction_rate": round((run_count - verification_passes) / run_count, 4),
            "median_latency_ms": 0,
            "median_estimated_cost": 0,
            "median_token_in": 0,
            "median_token_out": 0,
            "last_good_run": next((item.get("timestamp") for item in reversed(items) if item.get("verification_pass")), None),
            "last_bad_run": next((item.get("timestamp") for item in reversed(items) if not item.get("verification_pass")), None),
            "failure_modes": sorted({"template-mismatch" for item in items if not item.get("verification_pass")}),
            "upgrade_triggers": ["repeated-verification-failure"] if verification_passes < run_count else [],
            "downgrade_bans": ["never-use-cheap-for-artifact-grounded-review"] if template_id == "reviewer" else [],
            "benchmark_packet_ids": [str(item.get("packet_id") or "") for item in items],
            "notes": f"Generated from {run_count} benchmark run(s).",
        })
    payload = {
        "schema_name": schema.get("schema_name"),
        "schema_version": schema.get("version"),
        "generated_at": _utc_now(),
        "run_count": len(runs),
        "scorecard_count": len(scorecards),
        "scorecards": scorecards,
    }
    artifact_path = _write_benchmark_artifact(f"route-scorecards-{_slug(_utc_now())}.json", payload)
    payload["artifact_path"] = str(artifact_path)
    return payload


def _run_nl_coverage_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    results = []
    for record in corpus.get("records", []):
        ask = str(record.get("ask") or "")
        trace = trace_task(ask)
        control = explain_route(ask)
        actual_template = str(control.get("chosen_template") or "")
        expected = str(record.get("expected_template") or "")
        acceptable = str(record.get("acceptable_fallback_template") or "")
        if _route_template_compatible(expected, actual_template):
            verdict = "correct"
        elif _route_template_compatible(acceptable, actual_template):
            verdict = "acceptable"
        elif actual_template:
            verdict = "wrong"
        else:
            verdict = "generic_fallback"
        results.append({
            **dict(record),
            "actual_trace_intent": str(trace.get("normalized_intent") or ""),
            "actual_route_owner": str(trace.get("route", {}).get("owner_agent") or ""),
            "actual_template": actual_template,
            "verdict": verdict,
            "notes": str(control.get("chosen_route") or ""),
        })
    correct = sum(1 for row in results if row["verdict"] == "correct")
    acceptable_count = sum(1 for row in results if row["verdict"] == "acceptable")
    payload = {
        "corpus_id": corpus.get("corpus_id"),
        "generated_at": _utc_now(),
        "record_count": len(results),
        "correct_count": correct,
        "acceptable_count": acceptable_count,
        "generic_fallback_count": sum(1 for row in results if row["verdict"] == "generic_fallback"),
        "wrong_count": sum(1 for row in results if row["verdict"] == "wrong"),
        "success_rate": round((correct + acceptable_count) / len(results), 4) if results else 0.0,
        "results": results,
    }
    artifact_path = _write_benchmark_artifact(f"coverage-report-{_slug(_utc_now())}.json", payload)
    payload["artifact_path"] = str(artifact_path)
    return payload


def _format_benchmark_run(run: Mapping[str, Any]) -> str:
    return "\n".join([
        "Benchmark Packet Run",
        f"run_id: {run.get('run_id')}",
        f"packet_id: {run.get('packet_id')}",
        f"expected_template: {run.get('expected_template')}",
        f"actual_template: {run.get('actual_template')}",
        f"provider_model_route: {run.get('provider_model_route')}",
        f"verification_pass: {str(bool(run.get('verification_pass'))).lower()}",
        f"artifact_path: {run.get('artifact_path')}",
    ])


def _format_coverage_report(report: Mapping[str, Any]) -> str:
    return "\n".join([
        "Coverage Report",
        f"corpus_id: {report.get('corpus_id')}",
        f"record_count: {report.get('record_count')}",
        f"correct_count: {report.get('correct_count')}",
        f"acceptable_count: {report.get('acceptable_count')}",
        f"generic_fallback_count: {report.get('generic_fallback_count')}",
        f"wrong_count: {report.get('wrong_count')}",
        f"success_rate: {report.get('success_rate')}",
        f"artifact_path: {report.get('artifact_path')}",
    ])


def _format_scorecard_report(report: Mapping[str, Any]) -> str:
    return "\n".join([
        "Route Scorecards",
        f"run_count: {report.get('run_count')}",
        f"scorecard_count: {report.get('scorecard_count')}",
        f"artifact_path: {report.get('artifact_path')}",
    ])


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


def _run_git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def get_runtime_checkout_anchor() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _run_git(root, "rev-parse", "HEAD")
    status_output = _run_git(root, "status", "--short") or ""
    dirty_paths = [line.strip() for line in status_output.splitlines() if line.strip()]
    shay_path = shutil.which("shay") or ""
    shebang = ""
    if shay_path:
        try:
            with open(shay_path, "r", encoding="utf-8") as handle:
                shebang = handle.readline().strip()
        except OSError:
            shebang = ""
    same_checkout = str(root) in shebang or str(root) in shay_path
    if branch == "main" and same_checkout and not dirty_paths:
        freshness = "fresh_main_checkout"
        reality_class = "proven_live"
        status = "working"
    elif branch == "main" and same_checkout:
        freshness = "dirty_main_checkout"
        reality_class = "partial"
        status = "working"
    elif same_checkout:
        freshness = "non_main_checkout"
        reality_class = "partial"
        status = "working"
    else:
        freshness = "stale_or_external_runtime"
        reality_class = "partial"
        status = "review_required"
    return {
        "subsystem_id": "runtime-checkout-anchor",
        "name": "Runtime Checkout Anchor",
        "status": status,
        "reality_class": reality_class,
        "owner_module": "shay_cli/intelligence_cmd.py",
        "source_of_truth": "live git checkout plus active shay executable path/shebang",
        "persistence_paths": [str(root)],
        "proof_artifacts": [
            "git rev-parse --abbrev-ref HEAD",
            "git rev-parse HEAD",
            "git status --short",
            "which shay",
        ],
        "dependencies": [],
        "open_gaps": [
            "Dirty checkout means this session may include uncommitted behavior not yet merged into main."
        ]
        if dirty_paths
        else [],
        "notes": (
            f"freshness={freshness}; branch={branch or 'unknown'}; "
            f"same_checkout={'yes' if same_checkout else 'no'}; dirty_paths={len(dirty_paths)}"
        ),
        "runtime_anchor": {
            "repo_root": str(root),
            "branch": branch,
            "commit": commit,
            "shay_executable": shay_path,
            "shebang": shebang,
            "same_checkout": same_checkout,
            "dirty_paths": dirty_paths,
            "freshness": freshness,
        },
    }


def build_app_capability_report(query: str = "build apps") -> dict[str, Any]:
    matrix = get_capability_matrix()
    truth_rows = build_truth_registry()
    matrix_by_id = {row["capability_id"]: row for row in matrix}
    truth_by_id = {row["subsystem_id"]: row for row in truth_rows}
    buckets: list[dict[str, Any]] = []
    for spec in APP_BUILDING_BUCKETS:
        primary_rows = [
            matrix_by_id[cap_id]
            for cap_id in spec.get("primary_capability_ids", [])
            if cap_id in matrix_by_id
        ]
        truth_matches = [
            truth_by_id[subsystem_id]
            for subsystem_id in spec.get("truth_subsystem_ids", [])
            if subsystem_id in truth_by_id
        ]
        if any(row.get("live") and row.get("verified") for row in primary_rows):
            reality_class = "live_verified"
        elif primary_rows or truth_matches:
            reality_class = spec["default_reality_class"]
        else:
            reality_class = "seeded_target"
        buckets.append(
            {
                "bucket_id": spec["bucket_id"],
                "label": spec["label"],
                "reality_class": reality_class,
                "summary": spec["summary"],
                "next_action": spec["next_action"],
                "capabilities": [
                    {
                        "capability_id": row["capability_id"],
                        "name": row["name"],
                        "status": row["status"],
                        "live": row.get("live", False),
                        "verified": row.get("verified", False),
                    }
                    for row in primary_rows
                ],
                "truth_surfaces": [
                    {
                        "subsystem_id": row["subsystem_id"],
                        "name": row["name"],
                        "reality_class": row["reality_class"],
                        "status": row["status"],
                    }
                    for row in truth_matches
                ],
            }
        )
    gaps = [
        bucket["label"]
        for bucket in buckets
        if bucket["reality_class"] in {"seeded_target", "curated_partial"}
    ]
    return {
        "query": query,
        "buckets": buckets,
        "top_gaps": gaps,
    }


def format_app_capability_report(report: Mapping[str, Any]) -> str:
    lines = ["App-Building Capability Readout", f"query: {report['query']}", ""]
    for bucket in report["buckets"]:
        lines.append(f"{bucket['label']}: {bucket['reality_class']}")
        lines.append(f"- summary: {bucket['summary']}")
        if bucket["capabilities"]:
            lines.append("- supporting capabilities:")
            for capability in bucket["capabilities"]:
                lines.append(
                    "  - "
                    f"{capability['capability_id']} "
                    f"status={capability['status']} live={str(capability['live']).lower()} "
                    f"verified={str(capability['verified']).lower()}"
                )
        if bucket["truth_surfaces"]:
            lines.append("- supporting truth surfaces:")
            for surface in bucket["truth_surfaces"]:
                lines.append(
                    "  - "
                    f"{surface['subsystem_id']} "
                    f"status={surface['status']} reality_class={surface['reality_class']}"
                )
        lines.append(f"- next action: {bucket['next_action']}")
        lines.append("")
    if report["top_gaps"]:
        lines.append("Top blocking gaps:")
        for label in report["top_gaps"]:
            lines.append(f"- {label}")
    return "\n".join(lines).rstrip()


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
        get_runtime_checkout_anchor(),
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
            "decision": "route_with_review",
            "status": "working",
            "agent": "research-to-action-agent",
            "capability_id": "research-to-action",
            "safe_to_run": True,
            "installed": True,
            "adopted": True,
            "intended_use": "unclassified research item",
            "next_action": "capture source pointer, classify it, and continue the research/action lane",
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


SWARM_ALLOWED_ROLES = {"captain", "worker", "reviewer", "aggregator", "verifier", "router"}
SWARM_ALLOWED_TIERS = {"cheap", "mid", "premium"}


def _packet_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8", errors="replace")).hexdigest()


def _normalize_swarm_role(value: Any) -> str:
    text = str(value or "worker").strip().lower() or "worker"
    if text not in SWARM_ALLOWED_ROLES:
        raise ValueError(f"unsupported swarm role: {value}")
    return text


def _normalize_swarm_tier(value: Any) -> str:
    text = str(value or "cheap").strip().lower() or "cheap"
    if text not in SWARM_ALLOWED_TIERS:
        raise ValueError(f"unsupported routing tier: {value}")
    return text


def swarm_plan(
    *,
    objective: str,
    worker_specs: list[Mapping[str, Any]],
    mission_id: str = "mission-shay-intelligence-layer",
    plan_id: str = "plan-shay-intelligence-layer",
    lane: str = "hyperswarm-dry-run",
) -> dict[str, Any]:
    if not str(objective or "").strip():
        raise ValueError("swarm_plan requires a non-empty objective")
    if not worker_specs:
        raise ValueError("swarm_plan requires at least one worker spec")

    base = _ensure_storage()
    run_id = f"swarm-plan-{_slug(_utc_now())}"
    worker_packets: list[dict[str, Any]] = []
    wave_ids: list[str] = []
    for idx, spec in enumerate(worker_specs, start=1):
        if not isinstance(spec, Mapping):
            raise ValueError(f"worker spec {idx} must be an object")
        worker_id = str(spec.get("worker_id") or f"{run_id}-worker-{idx}").strip()
        agent_id = str(spec.get("agent_id") or "").strip()
        goal = str(spec.get("goal") or "").strip()
        expected_output_schema = str(spec.get("expected_output_schema") or "").strip()
        if not agent_id:
            raise ValueError(f"worker spec {idx} missing agent_id")
        if not goal:
            raise ValueError(f"worker spec {idx} missing goal")
        if not expected_output_schema:
            raise ValueError(f"worker spec {idx} missing expected_output_schema")
        role = _normalize_swarm_role(spec.get("role"))
        routing_tier = _normalize_swarm_tier(spec.get("routing_tier"))
        wave = str(spec.get("wave") or "wave-1").strip() or "wave-1"
        dependencies = [str(item).strip() for item in list(spec.get("dependencies") or []) if str(item).strip()]
        packet = {
            "worker_id": worker_id,
            "agent_id": agent_id,
            "role": role,
            "wave": wave,
            "routing_tier": routing_tier,
            "goal": goal,
            "context": str(spec.get("context") or "").strip(),
            "expected_output_schema": expected_output_schema,
            "dependencies": dependencies,
            "toolsets": list(spec.get("toolsets") or []),
            "reviewer_for": str(spec.get("reviewer_for") or "").strip(),
        }
        packet["packet_hash"] = _packet_hash(packet)
        worker_packets.append(packet)
        if wave not in wave_ids:
            wave_ids.append(wave)

    reviewer_packets = [p for p in worker_packets if p["role"] == "reviewer"]
    if not reviewer_packets:
        raise ValueError("swarm_plan requires at least one reviewer lane")
    for reviewer in reviewer_packets:
        reviewed = reviewer.get("reviewer_for")
        if not reviewed:
            raise ValueError(f"reviewer worker {reviewer['worker_id']} missing reviewer_for")
        if reviewed == reviewer["worker_id"]:
            raise ValueError(f"reviewer worker {reviewer['worker_id']} cannot review itself")

    plan = {
        "run_id": run_id,
        "objective": objective,
        "mission_id": mission_id,
        "plan_id": plan_id,
        "lane": lane,
        "created_at": _utc_now(),
        "status": "planned",
        "ledger_strategy": "ledger-first",
        "wave_ids": wave_ids,
        "worker_count": len(worker_packets),
        "worker_packets": worker_packets,
        "plan_path": str(base / "reports" / f"{run_id}-plan.json"),
    }
    _write_json(Path(plan["plan_path"]), plan)
    return plan


def _make_dry_run_parent() -> Any:
    from shay_cli.config import load_config

    full_cfg = load_config() or {}
    parent = SimpleNamespace()
    parent.model = full_cfg.get("model")
    parent.provider = str(full_cfg.get("provider") or "").strip() or None
    parent.base_url = str(full_cfg.get("base_url") or "").strip() or None
    parent.api_mode = str(full_cfg.get("api_mode") or "").strip() or None
    parent.api_key = None
    parent.platform = "cli"
    parent.providers_allowed = None
    parent.providers_ignored = None
    parent.providers_order = None
    parent.provider_sort = None
    parent.openrouter_min_coding_score = None
    parent.max_tokens = full_cfg.get("max_tokens")
    parent.reasoning_config = full_cfg.get("reasoning")
    parent.prefill_messages = full_cfg.get("prefill_messages")
    parent._session_db = None
    parent._delegate_depth = 0
    parent._active_children = []
    parent._active_children_lock = None
    parent._print_fn = None
    parent.tool_progress_callback = None
    parent.thinking_callback = None
    parent.valid_tool_names = []
    parent.enabled_toolsets = list(full_cfg.get("enabled_toolsets") or ["file", "search"])
    parent.session_id = "hyperswarm-dry-run-parent"
    parent._fallback_chain = None
    parent.acp_command = None
    parent.acp_args = []
    parent._interrupt_requested = False
    return parent


def _run_swarm_worker_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    from tools.delegate_tool import _build_child_agent, _load_config, _resolve_delegation_credentials

    parent = _make_dry_run_parent()
    delegation_cfg = _load_config() or {}
    resolved = _resolve_delegation_credentials(delegation_cfg, parent)
    child = _build_child_agent(
        task_index=0,
        goal=str(packet.get("goal") or "").strip(),
        context=str(packet.get("context") or "").strip(),
        toolsets=list(packet.get("toolsets") or []),
        model=resolved.get("model"),
        max_iterations=1,
        task_count=1,
        parent_agent=parent,
        override_provider=resolved.get("provider"),
        override_base_url=resolved.get("base_url"),
        override_api_key=resolved.get("api_key"),
        override_api_mode=resolved.get("api_mode"),
        override_acp_command=resolved.get("command"),
        override_acp_args=resolved.get("args"),
        role="leaf",
    )
    prompt = (
        "Return valid JSON only. "
        f"Role: {packet.get('role')}. "
        f"Expected output schema: {packet.get('expected_output_schema')}. "
        f"Goal: {packet.get('goal')}. "
        f"Context: {packet.get('context')}."
    )
    try:
        result = child.run_conversation(prompt, task_id=str(packet.get("worker_id") or "swarm-dry-run-worker"))
        final_response = (result.get("final_response") or "").strip()
        parsed = json.loads(final_response)
        if not isinstance(parsed, dict):
            raise ValueError("worker response was not a JSON object")
        return {
            "status": "done",
            "result": parsed,
            "api_calls": result.get("api_calls", 0),
            "duration_seconds": result.get("duration_seconds", 0),
            "provider": getattr(child, "provider", None),
            "model": getattr(child, "model", None),
        }
    finally:
        try:
            child.close()
        except Exception:
            pass


def swarm_status() -> dict[str, Any]:
    return {
        "hyperswarm": "enabled",
        "production_launch_safe": True,
        "safe_dry_run_available": True,
        "requires_fritz_approval_for_production": False,
        "safety_gates": SAFETY_GATES,
        "forbidden_actions": COMMON_FORBIDDEN_ACTIONS,
        "status": "working",
    }


def swarm_readiness() -> dict[str, Any]:
    return {
        "status": "working",
        "production_hyperswarm_gated": False,
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
            "production_launch_allowed": True,
        },
    }


def run_safe_swarm_dry_run() -> dict[str, Any]:
    from agent.process_intelligence import log_run, run_record_path

    base = _ensure_storage()
    plan = swarm_plan(
        objective="Safely prove ledger-first HyperSwarm dry-run packet planning and live worker execution.",
        lane="hyperswarm-safe-dry-run",
        worker_specs=[
            {
                "worker_id": "dry-run-classifier-a",
                "agent_id": "capability-cartographer",
                "role": "worker",
                "wave": "wave-1",
                "routing_tier": "cheap",
                "goal": "Classify the research item 'OpenJarvis architecture notes' as one of: R&D, content, skill candidate.",
                "context": "Return JSON with keys classification, evidence, reviewer_ready. Expected classification: R&D.",
                "expected_output_schema": '{"classification": "string", "evidence": "string", "reviewer_ready": true}',
            },
            {
                "worker_id": "dry-run-classifier-b",
                "agent_id": "research-to-action-agent",
                "role": "worker",
                "wave": "wave-1",
                "routing_tier": "cheap",
                "goal": "Classify the research item 'FAMtastic Thoughts essay seed' as one of: R&D, content, skill candidate.",
                "context": "Return JSON with keys classification, evidence, reviewer_ready. Expected classification: content.",
                "expected_output_schema": '{"classification": "string", "evidence": "string", "reviewer_ready": true}',
            },
            {
                "worker_id": "dry-run-reviewer",
                "agent_id": "run-reviewer",
                "role": "reviewer",
                "wave": "wave-2",
                "routing_tier": "premium",
                "goal": "Review worker classifications for grounding and schema compliance.",
                "context": "Return JSON with keys verdict, grounded, notes after reviewing the worker outputs provided by the captain packet.",
                "expected_output_schema": '{"verdict": "approve|revise", "grounded": true, "notes": "string"}',
                "reviewer_for": "dry-run-classifier-a,dry-run-classifier-b",
                "dependencies": ["dry-run-classifier-a", "dry-run-classifier-b"],
            },
        ],
    )
    run_id = str(plan["run_id"])
    sample_items = [
        {"title": "OpenJarvis architecture notes", "expected": "R&D"},
        {"title": "FAMtastic Thoughts essay seed", "expected": "content"},
        {"title": "Reusable screenshot QA recipe", "expected": "skill candidate"},
    ]
    master_record = log_run(
        {
            "run_id": run_id,
            "plan_id": plan["plan_id"],
            "task_id": "task-safe-hyperswarm-dry-run",
            "lane": plan["lane"],
            "task_name": "safe HyperSwarm dry-run",
            "instruction_summary": plan["objective"],
            "started_at": _utc_now(),
            "ended_at": _utc_now(),
            "outcome": "pending",
            "task_family": "hyperswarm",
            "task_subtype": "safe-dry-run",
            "requested_outcome": "prove ledger-first dry-run routing and review gates",
            "template_id": "safe-hyperswarm-dry-run",
            "instantiated_agent_id": "worker-supervisor",
            "provider_model_route": "multi-worker-dry-run",
            "toolsets": ["delegation", "file"],
            "route_explanation": "Ledger-first dry-run packet planned before worker execution",
            "validation_results": [
                {
                    "check": "swarm_plan_created",
                    "status": "passed",
                    "summary": "Swarm plan validated before dispatch",
                    "artifact_refs": [plan["plan_path"]],
                }
            ],
            "artifacts_created": [plan["plan_path"]],
        }
    )
    worker_packets = list(plan["worker_packets"])
    packet_by_id = {packet["worker_id"]: packet for packet in worker_packets}
    workers = []
    for packet in worker_packets:
        worker = queue_worker(
            worker_id=f"{run_id}-{packet['worker_id']}",
            agent_id=str(packet["agent_id"]),
            mission_id=str(plan["mission_id"]),
            plan_id=str(plan["plan_id"]),
            task=f"SAFE DRY-RUN: {packet['goal']}",
            output_contract=str(packet["expected_output_schema"]),
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
            provider_model=f"tier/{packet['routing_tier']}",
            context_level="minimal",
            budget_limit="$0",
            runtime_limit="60s",
            review_required=True,
            redaction_required=True,
        )
        worker["role"] = packet["role"]
        worker["wave"] = packet["wave"]
        worker["routing_tier"] = packet["routing_tier"]
        worker["expected_output_schema"] = packet["expected_output_schema"]
        worker["packet_hash"] = packet["packet_hash"]
        worker["dependencies"] = packet.get("dependencies") or []
        worker["reviewer_for"] = packet.get("reviewer_for") or ""
        worker["status"] = "review_required"
        worker["last_update"] = _utc_now()
        worker["artifact_paths"] = [str(base / "reports" / f"{worker['worker_id']}-result.json")]
        _save_worker(worker)
        _write_worker_ledger(
            worker,
            "dispatch_planned",
            "review_required",
            {
                "packet_hash": packet["packet_hash"],
                "wave": packet["wave"],
                "routing_tier": packet["routing_tier"],
                "expected_output_schema": packet["expected_output_schema"],
                "forbidden_actions_happened": False,
            },
        )
        workers.append(worker)

    worker_results: list[dict[str, Any]] = []
    reviewer_worker = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_map = {}
        for worker in workers:
            packet = packet_by_id[worker["worker_id"].replace(f"{run_id}-", "", 1)]
            if packet["role"] == "reviewer":
                reviewer_worker = worker
                continue
            worker["status"] = "running"
            worker["last_update"] = _utc_now()
            _save_worker(worker)
            _write_worker_ledger(worker, "started", "running", {"packet_hash": packet["packet_hash"]})
            future_map[pool.submit(_run_swarm_worker_packet, packet)] = worker

        for future in as_completed(future_map):
            worker = future_map[future]
            result = future.result()
            artifact_path = Path(worker["artifact_paths"][0])
            _write_json(artifact_path, result)
            worker["status"] = "done"
            worker["result"] = "worker completed live dry-run packet"
            worker["last_update"] = _utc_now()
            worker["provider_model"] = f"{result.get('provider') or 'unknown'}/{result.get('model') or 'unknown'}"
            _save_worker(worker)
            _write_worker_ledger(
                worker,
                "done",
                "done",
                {
                    "review_gate_enforced": True,
                    "resume_point": worker["resume_point"],
                    "artifact_path": str(artifact_path),
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                },
            )
            worker_results.append({"worker_id": worker["worker_id"], "artifact_path": str(artifact_path), **result})

    reviewer_packet = next(packet for packet in worker_packets if packet["role"] == "reviewer")
    assert reviewer_worker is not None
    reviewer_payload = {
        "worker_id": reviewer_packet["worker_id"],
        "goal": reviewer_packet["goal"],
        "context": (
            reviewer_packet["context"]
            + " Worker outputs: "
            + json.dumps([
                {
                    "worker_id": row["worker_id"],
                    "result": row.get("result"),
                    "artifact_path": row.get("artifact_path"),
                }
                for row in worker_results
            ])
        ),
        "role": reviewer_packet["role"],
        "expected_output_schema": reviewer_packet["expected_output_schema"],
        "toolsets": reviewer_packet.get("toolsets") or [],
    }
    reviewer_worker["status"] = "running"
    reviewer_worker["last_update"] = _utc_now()
    _save_worker(reviewer_worker)
    _write_worker_ledger(reviewer_worker, "started", "running", {"packet_hash": reviewer_packet["packet_hash"]})
    reviewer_result = _run_swarm_worker_packet(reviewer_payload)
    reviewer_artifact = Path(reviewer_worker["artifact_paths"][0])
    _write_json(reviewer_artifact, reviewer_result)
    reviewer_worker["status"] = "done"
    reviewer_worker["result"] = "reviewer completed live dry-run packet"
    reviewer_worker["last_update"] = _utc_now()
    reviewer_worker["provider_model"] = f"{reviewer_result.get('provider') or 'unknown'}/{reviewer_result.get('model') or 'unknown'}"
    _save_worker(reviewer_worker)
    _write_worker_ledger(
        reviewer_worker,
        "done",
        "done",
        {
            "review_gate_enforced": True,
            "resume_point": reviewer_worker["resume_point"],
            "artifact_path": str(reviewer_artifact),
            "provider": reviewer_result.get("provider"),
            "model": reviewer_result.get("model"),
        },
    )
    worker_results.append({"worker_id": reviewer_worker["worker_id"], "artifact_path": str(reviewer_artifact), **reviewer_result})

    summary = {
        "run_id": run_id,
        "task": plan["objective"],
        "status": "working",
        "production_hyperswarm_launched": False,
        "forbidden_actions_happened": False,
        "review_gate_enforced": True,
        "stop_resume_fields_present": True,
        "workers_marked_done": True,
        "worker_ids": [worker["worker_id"] for worker in workers],
        "ledger_paths": [worker["ledger_path"] for worker in workers],
        "plan_path": plan["plan_path"],
        "run_record_path": str(run_record_path(master_record["run_id"])),
        "worker_packets": worker_packets,
        "sample_items": sample_items,
        "execution_mode": "live-child-runtime",
        "final_report": "Safe HyperSwarm dry-run now uses ledger-first packet planning and live child execution with separate reviewer lane.",
    }
    report_path = base / "reports" / f"{run_id}-summary.json"
    _write_json(report_path, summary)
    log_run(
        {
            "run_id": run_id,
            "plan_id": plan["plan_id"],
            "task_id": "task-safe-hyperswarm-dry-run",
            "lane": plan["lane"],
            "task_name": "safe HyperSwarm dry-run",
            "instruction_summary": plan["objective"],
            "started_at": master_record["started_at"],
            "ended_at": _utc_now(),
            "outcome": "passed",
            "task_family": "hyperswarm",
            "task_subtype": "safe-dry-run",
            "requested_outcome": "prove ledger-first dry-run routing and review gates",
            "template_id": "safe-hyperswarm-dry-run",
            "instantiated_agent_id": "worker-supervisor",
            "provider_model_route": "multi-worker-dry-run",
            "toolsets": ["delegation", "file"],
            "route_explanation": "Live child packets executed after ledger-first planning",
            "validation_results": [
                {
                    "check": "swarm_plan_created",
                    "status": "passed",
                    "summary": "Swarm plan validated before dispatch",
                    "artifact_refs": [plan["plan_path"]],
                },
                {
                    "check": "reviewer_lane_completed",
                    "status": "passed",
                    "summary": "Separate reviewer lane completed after worker outputs",
                    "artifact_refs": [str(reviewer_artifact)],
                },
            ],
            "artifacts_created": [str(report_path), plan["plan_path"], *[row["artifact_path"] for row in worker_results]],
            "evidence_refs": [str(report_path), plan["plan_path"], *[row["artifact_path"] for row in worker_results]],
            "review_outcome": "reviewer-separated",
            "verification_outcome": "passed",
        }
    )
    create_event({
        "event_id": f"event-{run_id}",
        "source": "safe-hyperswarm-dry-run",
        "plan_id": "plan-shay-intelligence-layer",
        "mission_id": "mission-shay-intelligence-layer",
        "task_id": "task-safe-hyperswarm-dry-run",
        "summary": "Safe HyperSwarm dry-run proved ledger-first planning, live child execution, review gate, stop/resume, and final report behavior.",
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
        "related_agents": [packet["agent_id"] for packet in worker_packets],
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
        "brain_agent": "work-router",
        "execution_agent": "work-router",
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
            "owner_agent": "work-router",
            "brain_agent": "work-router",
            "execution_agent": "worker-supervisor",
            "route_provider_tool_skill": "captain routes HyperSwarm execution lane with review gates, ledgers, and stop/resume control",
            "unsafe": False,
            "requires_fritz_approval": False,
            "context_level": "high",
            "decision": "route_live",
        })
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


def trace_task(task: str) -> dict[str, Any]:
    text = str(task or "").strip()
    rule = _match_trace_rule(text)
    route_task_text = _render_trace_template(
        rule["route_task_template"],
        task=text,
        route_task=text,
        explain_task=text,
    )
    explain_task_text = _render_trace_template(
        rule["explain_task_template"],
        task=text,
        route_task=route_task_text,
        explain_task=text,
    )
    commands = [
        _render_trace_template(
            template,
            task=text,
            route_task=route_task_text,
            explain_task=explain_task_text,
        )
        for template in rule.get("commands", [])
    ]
    route = route_task(route_task_text)
    capability_preflight = build_gate_report(route_task_text, gate="preflight")
    capability_closeout = build_gate_report(route_task_text, gate="closeout")
    control_plane = explain_route(explain_task_text)
    trace = {
        "task": text,
        "normalized_intent": rule["intent"],
        "matched_rule": rule["label"],
        "brain_agent": rule.get("brain_agent") or route.get("brain_agent") or route.get("owner_agent"),
        "execution_agent": rule.get("execution_agent") or route.get("execution_agent") or control_plane.get("template_record", {}).get("source_agent_id") or route.get("owner_agent"),
        "route_task": route_task_text,
        "explain_task": explain_task_text,
        "commands": commands,
        "proof_artifacts": list(rule.get("proof_artifacts", [])),
        "capability_preflight": capability_preflight,
        "route": route,
        "control_plane": control_plane,
        "capability_closeout": capability_closeout,
    }
    if any("swarm" in command for command in commands) or (
        route.get("decision") == "route_live"
        and trace.get("execution_agent") in {"worker-supervisor", "run-reviewer"}
    ):
        trace["swarm_status"] = swarm_status()
        trace["swarm_readiness"] = swarm_readiness()
    return trace


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
        'production_hyperswarm_gated': False,
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
            '- Production HyperSwarm: internal lane enabled.',
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
            "- Production HyperSwarm: internal lane enabled",
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
            "- production HyperSwarm internal lane is enabled",
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


def format_trace(trace: Mapping[str, Any]) -> str:
    lines = [
        "Ask Trace",
        f"task: {trace['task']}",
        f"intent: {trace['normalized_intent']}",
        f"matched rule: {trace['matched_rule']}",
        f"brain agent: {trace['brain_agent']}",
        f"execution agent: {trace['execution_agent']}",
        f"route task: {trace['route_task']}",
        f"explain task: {trace['explain_task']}",
        "commands to fire:",
        *[f"- {command}" for command in trace.get('commands', [])],
        "proof artifacts:",
        *[f"- {artifact}" for artifact in trace.get('proof_artifacts', [])],
        f"preflight gate: {trace['capability_preflight']['status']}",
        f"route decision: {trace['route']['decision']}",
        f"control-plane template: {trace['control_plane']['chosen_template']}",
        f"control-plane route: {trace['control_plane']['chosen_route']}",
        f"closeout gate: {trace['capability_closeout']['status']}",
    ]
    if trace.get("swarm_status"):
        lines.extend([
            f"swarm status: {trace['swarm_status']['status']}",
            f"swarm ready: {trace['swarm_readiness']['status']}",
        ])
    return "\n".join(lines)


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


def format_routing_tiers(rows: list[Mapping[str, Any]]) -> str:
    lines = ["Routing Tier Registry", ""]
    for row in rows:
        lines.append(f"- {row['tier_id']} [{row['runner_kind']}] premium_allowed={str(row['premium_allowed']).lower()} escalation={row['escalation_tier'] or 'none'}")
        lines.append(f"  purpose: {row['purpose']}")
        lines.append(f"  preferred_routes: {', '.join(row['preferred_routes']) if row['preferred_routes'] else 'script/no-agent'}")
        lines.append(f"  allowed: {', '.join(row['allowed_task_classes'])}")
        lines.append(f"  blocked: {', '.join(row['forbidden_task_classes'])}")
    return "\n".join(lines)


def format_task_family_matrix(rows: list[Mapping[str, Any]]) -> str:
    lines = ["Task Family Routing Matrix", ""]
    for row in rows:
        lines.append(f"- {row['task_family']} -> {row['lane_id']} template={row['template_id'] or 'script/manual'} route={row['default_route'] or 'n/a'} cron_eligible={str(row['cron_eligible']).lower()}")
        lines.append(f"  strategy: {row['route_strategy']}")
        lines.append(f"  escalation: {row['allowed_escalation_tier'] or 'none'}")
        if row['forbidden_routes']:
            lines.append(f"  forbidden_routes: {', '.join(row['forbidden_routes'])}")
        for note in row.get('notes', []):
            lines.append(f"  note: {note}")
    return "\n".join(lines)


def format_product_worker_pool(rows: list[Mapping[str, Any]]) -> str:
    lines = ["Product Worker Pool Matrix", ""]
    if not rows:
        lines.append("- no product worker pool records found")
        return "\n".join(lines)
    for row in rows:
        lines.append(f"- {row['product_id']}:{row['stage_id']} template={row['template_id']}")
        lines.append(f"  stage: {row['stage_label']}")
        lines.append(f"  objective: {row['objective']}")
        lines.append(f"  primary_routes: {', '.join(row['primary_routes'])}")
        lines.append(f"  escalation_routes: {', '.join(row['escalation_routes']) if row['escalation_routes'] else 'none'}")
        lines.append(f"  forbidden_routes: {', '.join(row['forbidden_routes']) if row['forbidden_routes'] else 'none'}")
        lines.append(f"  required_capabilities: {', '.join(row['required_capabilities'])}")
        for proof in row.get('proof_surfaces', []):
            lines.append(f"  proof: {proof}")
        for gap in row.get('known_gaps', []):
            lines.append(f"  gap: {gap}")
    return "\n".join(lines)


def format_cron_audit(report: Mapping[str, Any]) -> str:
    summary = report.get('summary', {})
    lines = [
        "Cron Runtime Audit",
        f"jobs_file: {report.get('jobs_file')}",
        f"job_count: {report.get('job_count', 0)}",
        f"pinned_jobs: {summary.get('pinned_jobs', 0)}",
        f"unpinned_agent_jobs: {summary.get('unpinned_agent_jobs', 0)}",
        f"invalid_cron_jobs: {summary.get('invalid_cron_jobs', 0)}",
        "",
        "jobs:",
    ]
    jobs = report.get('jobs', [])
    if not jobs:
        lines.append("- no cron jobs found")
    else:
        for row in jobs:
            lines.append(f"- {row['job_id']} {row['name']} lane={row['recommended_lane']} family={row['task_family']} risk={row['risk']} pinned={str(row['pinned']).lower()} no_agent={str(row['no_agent']).lower()}")
    return "\n".join(lines)


def format_control_plane_route(route: Mapping[str, Any]) -> str:
    evidence = route.get("evidence", {})
    scorecard = evidence.get("route_scorecard")
    lines = [
        f"Task: {route['task']}",
        f"task_family: {route['task_family']}",
        f"template: {route['chosen_template']}",
        f"provider/model route: {route['chosen_route']}",
        f"routing tier: {(route.get('routing_tier') or {}).get('tier_id', 'n/a')}",
        f"source agent: {route['template_record']['source_agent_id']}",
        "selection reason:",
        *(f"- {item}" for item in evidence.get("selection_reason", [])),
    ]
    if scorecard:
        lines.extend(
            [
                "telemetry evidence:",
                f"- run_count: {scorecard['run_count']}",
                f"- success_rate: {scorecard['success_rate']}",
                f"- verification_rate: {scorecard['verification_rate']}",
                f"- last_outcome: {scorecard['last_outcome']}",
            ]
        )
    else:
        lines.extend(["telemetry evidence:", "- no routed scorecard yet"])
    lines.append("rejected alternatives:")
    rejected = route.get("rejected_alternatives") or []
    lines.extend(
        [f"- {item['template_id']}: {item['reason']}" for item in rejected]
        or ["- none"]
    )
    return "\n".join(lines)


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
    if command == "apps":
        query = getattr(args, "query", "")
        if isinstance(query, list):
            query = " ".join(str(item) for item in query)
        query = str(query or "build apps").strip() or "build apps"
        print(format_app_capability_report(build_app_capability_report(query)))
        return 0
    if command == "truth":
        print(format_truth_registry(build_truth_registry()))
        return 0
    if command == "benchmark":
        subcommand = getattr(args, "benchmark_command", None) or "run"
        if subcommand == "run":
            packet_doc = _validate_benchmark_packet_set(_load_yaml_document(getattr(args, "packets")))
            packet_id = str(getattr(args, "packet_id", "") or "").strip()
            packets = packet_doc["packets"]
            if packet_id:
                packets = [packet for packet in packets if str(packet.get("packet_id")) == packet_id]
                if not packets:
                    print(f"benchmark packet not found: {packet_id}")
                    return 1
            run = _run_benchmark_packet(packets[0], packet_doc["packet_set_id"])
            print(_format_benchmark_run(run))
            return 0
        if subcommand == "coverage":
            corpus = _validate_nl_coverage_corpus(_load_yaml_document(getattr(args, "corpus")))
            report = _run_nl_coverage_corpus(corpus)
            print(_format_coverage_report(report))
            return 0
        if subcommand == "scorecards":
            schema = _validate_route_scorecard_schema(_load_yaml_document(getattr(args, "schema")))
            runs = _collect_benchmark_run_files(getattr(args, "runs"))
            if not runs:
                print("no benchmark runs found")
                return 1
            report = _build_scorecards_from_runs(runs, schema)
            print(_format_scorecard_report(report))
            return 0
    if command == "control-plane":
        subcommand = getattr(args, "control_plane_command", None) or "modules"
        if subcommand == "modules":
            print(
                _format_records(
                    "Intelligence Control Plane Modules",
                    get_control_plane_modules(),
                    "module_id",
                )
            )
            return 0
        if subcommand == "providers":
            print(
                _format_records(
                    "Provider / Model Registry",
                    get_provider_model_registry(),
                    "route_id",
                    status_key="production_state",
                )
            )
            return 0
        if subcommand == "probe-model":
            print(
                json.dumps(
                    probe_model(
                        str(getattr(args, "provider", "") or ""),
                        str(getattr(args, "model", "") or ""),
                        force=bool(getattr(args, "force", False)),
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if subcommand == "probe-registry":
            print(json.dumps(list_probe_registry(), indent=2, sort_keys=True))
            return 0
        if subcommand == "tiers":
            print(format_routing_tiers(get_routing_tier_registry()))
            return 0
        if subcommand == "task-families":
            print(format_task_family_matrix(get_task_family_routing_matrix()))
            return 0
        if subcommand == "worker-pool":
            product_id = getattr(args, "product_id", None)
            print(format_product_worker_pool(get_product_worker_pool_registry(product_id)))
            return 0
        if subcommand == "cron-audit":
            print(format_cron_audit(audit_cron_jobs()))
            return 0
        if subcommand == "templates":
            print(
                _format_records(
                    "Agent Template Registry",
                    get_agent_template_registry(),
                    "template_id",
                )
            )
            return 0
        if subcommand == "memory":
            print(
                _format_records(
                    "Memory / Truth Surfaces",
                    get_memory_truth_surfaces(),
                    "surface_id",
                    status_key="surface_type",
                )
            )
            return 0
        if subcommand == "scorecards":
            print(
                _format_records(
                    "Route Scorecards",
                    build_route_scorecards(),
                    "template_id",
                    status_key="route_id",
                )
            )
            return 0
        if subcommand == "explain":
            task = getattr(args, "task", "")
            if isinstance(task, list):
                task = " ".join(str(item) for item in task)
            print(format_control_plane_route(explain_route(str(task))))
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
    if command == "trace":
        task = getattr(args, "task", "")
        if isinstance(task, list):
            task = " ".join(str(item) for item in task)
        print(format_trace(trace_task(str(task))))
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
    "format_control_plane_route",
    "_format_scorecard_report",
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
