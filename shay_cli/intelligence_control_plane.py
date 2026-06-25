from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


from agent.process_intelligence import list_run_records, normalized_validation_results
from shay_constants import get_shay_home
from shay_cli.intelligence_seed import agent_by_id, get_agent_registry
from shay_cli.model_probe import score_routes_for_task


@dataclass
class ControlPlaneModule:
    module_id: str
    layer: str
    purpose: str
    owns: list[str]
    depends_on: list[str]
    primary_surfaces: list[str]
    shared_schema_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderModelRecord:
    route_id: str
    provider_id: str
    provider_label: str
    model_id: str
    release_tier: str
    production_state: str
    context_length: int
    supports_reasoning: bool
    supports_tools: bool
    supports_web: bool
    supports_code: bool
    supports_browser: bool
    auth_surface: str
    ecosystem_unlocks: list[str]
    cost_class: str
    latency_class: str
    reliability_notes: list[str]
    recommended_task_families: list[str]
    disallowed_task_families: list[str]
    source_urls: list[str]
    last_verified: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentTemplateRecord:
    template_id: str
    role_name: str
    task_families: list[str]
    required_capabilities: list[str]
    preferred_routes: list[str]
    allowed_tools: list[str]
    forbidden_tools: list[str]
    budget_profile: str
    latency_profile: str
    verification_path: list[str]
    output_contract: str
    escalation_rules: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingTierRecord:
    tier_id: str
    label: str
    purpose: str
    allowed_task_classes: list[str]
    forbidden_task_classes: list[str]
    preferred_routes: list[str]
    escalation_tier: str | None
    premium_allowed: bool
    runner_kind: str
    notifier_role: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskFamilyRoutingRecord:
    task_family: str
    lane_id: str
    template_id: str | None
    route_strategy: str
    default_route: str | None
    allowed_escalation_tier: str | None
    forbidden_routes: list[str]
    cron_eligible: bool
    script_preferred: bool
    premium_requires_explicit_opt_in: bool
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductWorkerPoolRecord:
    product_id: str
    stage_id: str
    stage_label: str
    objective: str
    template_id: str
    primary_routes: list[str]
    escalation_routes: list[str]
    forbidden_routes: list[str]
    required_capabilities: list[str]
    proof_surfaces: list[str]
    known_gaps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CONTROL_PLANE_SCHEMA_IDS = {
    "module_boundary": "intelligence-control-plane/module-boundary/v1",
    "provider_model_record": "intelligence-control-plane/provider-model-record/v1",
    "agent_template_record": "intelligence-control-plane/agent-template-record/v1",
    "worker_instance_record": "intelligence-control-plane/worker-instance-record/v1",
    "routing_decision_record": "intelligence-control-plane/routing-decision-record/v1",
    "telemetry_run_overlay": "intelligence-control-plane/telemetry-run-overlay/v1",
    "memory_surface_record": "intelligence-control-plane/memory-surface-record/v1",
    "routing_tier_record": "intelligence-control-plane/routing-tier-record/v1",
    "task_family_routing_record": "intelligence-control-plane/task-family-routing-record/v1",
    "product_worker_pool_record": "intelligence-control-plane/product-worker-pool-record/v1",
}

_UNIVERSAL_ROUTE_SYNC_ACTIVE = False


def _universal_route_export_path() -> Path:
    return get_shay_home() / "control-plane" / "universal-intelligence-route.json"


def get_control_plane_modules() -> list[dict[str, Any]]:
    modules = [
        ControlPlaneModule(
            module_id="memory-truth",
            layer="truth substrate",
            purpose="Unify seeded truth, observed ledger proof, and memory surfaces without collapsing them into one blob.",
            owns=["truth registry", "memory surfaces", "observation vs interpretation boundaries"],
            depends_on=["telemetry-proof"],
            primary_surfaces=[
                "shay_cli/intelligence_cmd.py::build_truth_registry",
                "shay_cli/capabilities_cmd.py",
                "agent/process_intelligence.py",
            ],
            shared_schema_ids=[
                CONTROL_PLANE_SCHEMA_IDS["module_boundary"],
                CONTROL_PLANE_SCHEMA_IDS["memory_surface_record"],
            ],
        ),
        ControlPlaneModule(
            module_id="capability-registry",
            layer="capability intelligence",
            purpose="Carry the curated capability matrix and merge it with observed proof overlays.",
            owns=["capability matrix", "capability gaps", "capability overlays"],
            depends_on=["telemetry-proof", "provider-model-registry"],
            primary_surfaces=[
                "shay_cli/intelligence_seed.py",
                "shay_cli/capabilities_cmd.py",
            ],
            shared_schema_ids=[CONTROL_PLANE_SCHEMA_IDS["routing_decision_record"]],
        ),
        ControlPlaneModule(
            module_id="provider-model-registry",
            layer="route truth",
            purpose="Keep provider/model lane facts in one routable registry instead of scattering them through policy prose.",
            owns=["provider-model records", "route fit", "cost/latency/reliability notes"],
            depends_on=[],
            primary_surfaces=["shay_cli/intelligence_control_plane.py"],
            shared_schema_ids=[CONTROL_PLANE_SCHEMA_IDS["provider_model_record"]],
        ),
        ControlPlaneModule(
            module_id="agency-registry",
            layer="dynamic agency",
            purpose="Refactor fixed agents into reusable templates plus instantiated workers for specific jobs.",
            owns=["agent templates", "worker instantiation defaults", "verification paths"],
            depends_on=["provider-model-registry", "capability-registry"],
            primary_surfaces=[
                "shay_cli/intelligence_seed.py",
                "shay_cli/intelligence_cmd.py",
                "shay_cli/intelligence_control_plane.py",
            ],
            shared_schema_ids=[
                CONTROL_PLANE_SCHEMA_IDS["agent_template_record"],
                CONTROL_PLANE_SCHEMA_IDS["worker_instance_record"],
            ],
        ),
        ControlPlaneModule(
            module_id="telemetry-proof",
            layer="proof substrate",
            purpose="Persist routed run outcomes so route quality can be defended with evidence instead of instinct.",
            owns=["run ledger", "routing overlays", "scorecards"],
            depends_on=[],
            primary_surfaces=[
                "agent/process_intelligence.py",
                "shay_cli/capabilities_cmd.py",
            ],
            shared_schema_ids=[
                CONTROL_PLANE_SCHEMA_IDS["telemetry_run_overlay"],
                CONTROL_PLANE_SCHEMA_IDS["routing_decision_record"],
            ],
        ),
        ControlPlaneModule(
            module_id="routing-engine",
            layer="decision surface",
            purpose="Explain route choices with template fit, provider/model fit, and observed telemetry evidence.",
            owns=["route decisions", "route explanations", "rejected alternatives"],
            depends_on=["provider-model-registry", "agency-registry", "telemetry-proof"],
            primary_surfaces=["shay_cli/intelligence_cmd.py"],
            shared_schema_ids=[CONTROL_PLANE_SCHEMA_IDS["routing_decision_record"]],
        ),
    ]
    return [module.to_dict() for module in modules]


PROVIDER_MODEL_REGISTRY: list[ProviderModelRecord] = [
    ProviderModelRecord(
        route_id="anthropic-claude-code-sonnet-4.6",
        provider_id="anthropic",
        provider_label="Claude Code",
        model_id="claude-sonnet-4.6",
        release_tier="frontier",
        production_state="production-ready",
        context_length=200000,
        supports_reasoning=True,
        supports_tools=True,
        supports_web=True,
        supports_code=True,
        supports_browser=False,
        auth_surface="Claude Code OAuth",
        ecosystem_unlocks=["Claude Code session continuity", "strong code + tool reasoning"],
        cost_class="subscription",
        latency_class="medium",
        reliability_notes=[
            "Preferred builder lane when Fritz wants Claude Code execution semantics.",
            "Good fit for implementation-heavy work that still needs tool grounding.",
        ],
        recommended_task_families=["deep code work", "code implementation", "schema wiring", "deploy"],
        disallowed_task_families=["high-volume rote extraction"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-24",
    ),
    ProviderModelRecord(
        route_id="openai-codex-gpt-5.5",
        provider_id="openai-codex",
        provider_label="OpenAI Codex",
        model_id="gpt-5.5",
        release_tier="frontier",
        production_state="production-ready",
        context_length=131072,
        supports_reasoning=True,
        supports_tools=True,
        supports_web=True,
        supports_code=True,
        supports_browser=False,
        auth_surface="OAuth session",
        ecosystem_unlocks=["codex session continuity", "strong code + tool reasoning"],
        cost_class="subscription",
        latency_class="medium",
        reliability_notes=["Strong brain lane candidate.", "Use for captain/reviewer or high-ambiguity implementation."],
        recommended_task_families=["captain orchestration", "deep code work", "route review", "final synthesis"],
        disallowed_task_families=["high-volume rote extraction"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="openai-gpt-5.4-mini",
        provider_id="openai",
        provider_label="OpenAI",
        model_id="gpt-5.4-mini",
        release_tier="frontier-lite",
        production_state="production-ready",
        context_length=131072,
        supports_reasoning=True,
        supports_tools=True,
        supports_web=True,
        supports_code=True,
        supports_browser=False,
        auth_surface="API key",
        ecosystem_unlocks=["general fallback"],
        cost_class="paid",
        latency_class="fast",
        reliability_notes=["Good fallback lane when a smaller frontier model is enough."],
        recommended_task_families=["mid-cost implementation", "classification", "brief synthesis"],
        disallowed_task_families=["large unreviewed bulk fanout"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="google-gemini-2.5-pro",
        provider_id="google",
        provider_label="Google Gemini",
        model_id="gemini-2.5-pro",
        release_tier="frontier",
        production_state="production-ready",
        context_length=1048576,
        supports_reasoning=True,
        supports_tools=False,
        supports_web=True,
        supports_code=True,
        supports_browser=False,
        auth_surface="OAuth or API key",
        ecosystem_unlocks=["large-context reasoning", "multimodal research"],
        cost_class="free-or-paid",
        latency_class="medium",
        reliability_notes=["Useful reviewer lane when huge context matters."],
        recommended_task_families=["adversarial review", "comparative research", "vision-adjacent synthesis"],
        disallowed_task_families=["stateful tool-heavy orchestration"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="cerebras-llama-3.3-70b",
        provider_id="cerebras",
        provider_label="Cerebras",
        model_id="llama-3.3-70b",
        release_tier="mid",
        production_state="observed-usable",
        context_length=131072,
        supports_reasoning=True,
        supports_tools=False,
        supports_web=False,
        supports_code=True,
        supports_browser=False,
        auth_surface="API key",
        ecosystem_unlocks=["cheap throughput"],
        cost_class="free-tier",
        latency_class="fast",
        reliability_notes=["Good cheap worker lane when grounded artifacts are simple.", "Do not use as brain lane with full SOUL/PERSONA payload."],
        recommended_task_families=["classification", "rote code transforms", "telemetry summarization"],
        disallowed_task_families=["brain lane", "identity-heavy orchestration"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="groq-llama-3.3-70b",
        provider_id="groq",
        provider_label="Groq",
        model_id="llama-3.3-70b",
        release_tier="mid",
        production_state="observed-usable",
        context_length=131072,
        supports_reasoning=True,
        supports_tools=False,
        supports_web=False,
        supports_code=True,
        supports_browser=False,
        auth_surface="API key",
        ecosystem_unlocks=["low-latency worker lane"],
        cost_class="free-tier",
        latency_class="fast",
        reliability_notes=["Cheap worker or scorer lane.", "Keep away from final high-stakes route promotion without reviewer backup."],
        recommended_task_families=["fast classification", "cheap fanout", "draft synthesis"],
        disallowed_task_families=["brain lane", "unreviewed final answer"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="ollama-qwen3-14b",
        provider_id="ollama",
        provider_label="Ollama Local",
        model_id="qwen3:14b",
        release_tier="local-mid",
        production_state="local-only",
        context_length=65536,
        supports_reasoning=True,
        supports_tools=False,
        supports_web=False,
        supports_code=True,
        supports_browser=False,
        auth_surface="local endpoint",
        ecosystem_unlocks=["private local lane"],
        cost_class="local",
        latency_class="medium",
        reliability_notes=["Safe for auxiliary or private worker tasks.", "Do not use as full-SOUL brain lane."],
        recommended_task_families=["auxiliary search", "private summarization", "local worker tasks"],
        disallowed_task_families=["brain lane", "identity-critical synthesis"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="anthropic-api-sonnet",
        provider_id="anthropic",
        provider_label="Anthropic API",
        model_id="claude-sonnet",
        release_tier="frontier",
        production_state="policy-gated",
        context_length=200000,
        supports_reasoning=True,
        supports_tools=True,
        supports_web=True,
        supports_code=True,
        supports_browser=False,
        auth_surface="API key",
        ecosystem_unlocks=["strong reasoning"],
        cost_class="paid",
        latency_class="medium",
        reliability_notes=["Technically strong but avoid-by-policy for default autonomous use in this doctrine."],
        recommended_task_families=["manual override only"],
        disallowed_task_families=["default autonomous route"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
    ProviderModelRecord(
        route_id="openrouter-generic",
        provider_id="openrouter",
        provider_label="OpenRouter",
        model_id="generic",
        release_tier="mixed",
        production_state="policy-gated",
        context_length=128000,
        supports_reasoning=True,
        supports_tools=False,
        supports_web=False,
        supports_code=True,
        supports_browser=False,
        auth_surface="API key",
        ecosystem_unlocks=["wide provider access"],
        cost_class="mixed",
        latency_class="mixed",
        reliability_notes=["Good ecosystem reach but default autonomous use is avoid-by-policy here."],
        recommended_task_families=["manual override only"],
        disallowed_task_families=["default autonomous route"],
        source_urls=["https://shay-shay.nousresearch.com/docs/integrations/providers"],
        last_verified="2026-06-19",
    ),
]


def get_provider_model_registry() -> list[dict[str, Any]]:
    rows = [record.to_dict() for record in PROVIDER_MODEL_REGISTRY]
    _sync_universal_route_truth()
    return rows


_TEMPLATE_SEEDS = [
    {
        "template_id": "orchestrator-captain",
        "role_name": "Orchestrator Captain",
        "agent_id": "work-router",
        "task_families": ["orchestration", "planning", "final synthesis"],
        "preferred_routes": ["google-gemini-2.5-pro"],
        "budget_profile": "premium-when-ambiguous",
        "latency_profile": "quality-first",
        "output_contract": "routing decision + explicit proof + next actions",
    },
    {
        "template_id": "provider-intel-researcher",
        "role_name": "Provider Intelligence Researcher",
        "agent_id": "provider-capacity-broker",
        "task_families": ["provider research", "model comparison", "cost routing"],
        "preferred_routes": ["google-gemini-2.5-pro", "cerebras-llama-3.3-70b", "groq-llama-3.3-70b"],
        "budget_profile": "cheap-first",
        "latency_profile": "fast",
        "output_contract": "provider/model registry rows with sources and routing notes",
    },
    {
        "template_id": "capability-cartographer",
        "role_name": "Capability Cartographer",
        "agent_id": "capability-cartographer",
        "task_families": ["capability backfill", "gap classification", "truth merge"],
        "preferred_routes": ["openai-gpt-5.4-mini"],
        "budget_profile": "mid",
        "latency_profile": "balanced",
        "output_contract": "capability updates + caveats + next action",
    },
    {
        "template_id": "implementation-worker",
        "role_name": "Implementation Worker",
        "agent_id": "worker-supervisor",
        "task_families": ["code implementation", "schema wiring", "CLI additions", "implementation", "deploy"],
        "preferred_routes": ["anthropic-claude-code-sonnet-4.6", "openai-gpt-5.4-mini"],
        "budget_profile": "mid",
        "latency_profile": "balanced",
        "output_contract": "file diff + tests + residue",
    },
    {
        "template_id": "review-judge",
        "role_name": "Review Judge",
        "agent_id": "run-reviewer",
        "task_families": ["adversarial review", "route challenge", "proof audit", "review"],
        "preferred_routes": ["google-gemini-2.5-pro"],
        "budget_profile": "premium-review",
        "latency_profile": "quality-first",
        "output_contract": "verdict + cited proof + failures/rejects",
    },
    {
        "template_id": "memory-curator",
        "role_name": "Memory Curator",
        "agent_id": "episodic-recorder",
        "task_families": ["memory/truth unification", "resume surfaces", "evidence packaging", "recall", "resume"],
        "preferred_routes": ["openai-gpt-5.4-mini", "ollama-qwen3-14b"],
        "budget_profile": "cheap-first",
        "latency_profile": "balanced",
        "output_contract": "truth/memory surface update with observation vs interpretation preserved",
    },
    {
        "template_id": "attention-watcher",
        "role_name": "Attention Watcher",
        "agent_id": "work-router",
        "task_families": ["monitoring", "status", "attention", "watching"],
        "preferred_routes": ["openai-gpt-5.4-mini", "groq-llama-3.3-70b"],
        "budget_profile": "cheap-first",
        "latency_profile": "fast",
        "output_contract": "exception-oriented attention summary + escalation threshold",
    },
    {
        "template_id": "browser-operator",
        "role_name": "Browser Operator",
        "agent_id": "worker-supervisor",
        "task_families": ["browser-ui", "playwright", "user-flow verification"],
        "preferred_routes": ["openai-gpt-5.4-mini"],
        "budget_profile": "capability-first",
        "latency_profile": "balanced",
        "output_contract": "user-flow verdict + breakpoints + proof artifacts",
    },
]


def get_agent_template_registry() -> list[dict[str, Any]]:
    registry = {row["agent_id"]: row for row in get_agent_registry()}
    templates: list[dict[str, Any]] = []
    for seed in _TEMPLATE_SEEDS:
        agent = registry.get(seed["agent_id"], {})
        record = AgentTemplateRecord(
            template_id=seed["template_id"],
            role_name=seed["role_name"],
            task_families=list(seed["task_families"]),
            required_capabilities=list(agent.get("required_capabilities") or []),
            preferred_routes=list(seed["preferred_routes"]),
            allowed_tools=list(agent.get("allowed_actions") or []),
            forbidden_tools=list(agent.get("forbidden_actions") or []),
            budget_profile=str(seed["budget_profile"]),
            latency_profile=str(seed["latency_profile"]),
            verification_path=[
                "targeted pytest",
                "live CLI command",
                "parent review against files/git state",
            ],
            output_contract=str(seed["output_contract"]),
            escalation_rules=[
                "block unsafe provider/policy routes",
                "require reviewer lane for promotions",
                "log telemetry before claiming success",
            ],
        )
        payload = record.to_dict()
        payload["source_agent_id"] = seed["agent_id"]
        templates.append(payload)
    return templates


def instantiate_worker_from_template(
    template_id: str,
    *,
    worker_id: str,
    mission_id: str,
    plan_id: str,
    task: str,
) -> dict[str, Any]:
    templates = {row["template_id"]: row for row in get_agent_template_registry()}
    template = templates.get(template_id)
    if template is None:
        raise ValueError(f"unknown template_id: {template_id}")
    return {
        "worker_id": worker_id,
        "template_id": template_id,
        "mission_id": mission_id,
        "plan_id": plan_id,
        "task": task,
        "role_name": template["role_name"],
        "preferred_routes": list(template["preferred_routes"]),
        "required_capabilities": list(template["required_capabilities"]),
        "output_contract": template["output_contract"],
        "verification_path": list(template["verification_path"]),
        "source_agent_id": template["source_agent_id"],
    }


def get_memory_truth_surfaces() -> list[dict[str, Any]]:
    return [
        {
            "surface_id": "north-star-memory",
            "surface_type": "north_star",
            "owner": "memory-truth",
            "source_of_truth": "~/.shay/memory/memory.md (injected core identity/priorities)",
            "usage": "directional truths only",
        },
        {
            "surface_id": "active-state-file",
            "surface_type": "active_state",
            "owner": "memory-truth",
            "source_of_truth": "~/famtastic/obsidian/01-Shay-Platform/HOT-CONTEXT-POINTERS.md",
            "usage": "current operational state and resumability",
        },
        {
            "surface_id": "essence-vault",
            "surface_type": "essence",
            "owner": "memory-truth",
            "source_of_truth": "~/famtastic/obsidian/ via basic-memory/vault-search",
            "usage": "durable recall and historical search",
        },
        {
            "surface_id": "process-intelligence-ledger",
            "surface_type": "operational-proof",
            "owner": "telemetry-proof",
            "source_of_truth": "agent/process_intelligence.py ledger under ~/.shay/process-intelligence",
            "usage": "run evidence, validation, route outcomes",
        },
    ]


PHRASE_GROUPS: dict[str, tuple[str, ...]] = {
    "watchdog": (
        "watchdog",
        "heartbeat",
        "poll",
        "threshold",
        "ping",
        "health check",
        "sync",
        "ingest",
    ),
    "interactive": (
        "ask fritz",
        "interview fritz",
        "chat with fritz",
        "capture his words",
        "open-ended questions",
        "ask him",
        "ask her",
        "ask them",
        "structured interview",
    ),
    "swarm": (
        "break this into packets",
        "assign the right lanes",
        "run it with review",
        "swarm",
        "packets",
        "lanes",
        "captain",
        "orchestrate",
        "continue the next lane",
    ),
    "watcher": (
        "watch api spend",
        "only tell me when",
        "watch for failures",
        "watch this lane",
        "monitor this",
        "keep an eye on",
        "alert me if",
    ),
    "attention": (
        "what needs my attention",
        "show me the board",
        "show me the queues",
        "things that are stuck",
        "queue",
        "stuck",
        "attention",
        "board",
        "what is waiting on me",
    ),
    "recall": (
        "what did fritz and shay already decide",
        "before today",
        "recall",
        "what did we decide",
        "pick back up where we left off",
        "resume",
    ),
    "review": (
        "tear this implementation apart",
        "adversarial review",
        "only approve it if the proof is real",
        "proof audit",
        "route challenge",
        "review this implementation",
        "audit",
        "adversarial",
    ),
    "implementation": (
        "fix the broken",
        "patch the root cause",
        "verify the fix",
        "reproduce a failing behavior",
        "build this app",
        "ship the first working version",
        "get this build ready to deploy",
        "implement",
        "refactor",
        "build",
        "code",
        "cli",
        "schema",
        "bug",
        "fix",
        "deploy",
    ),
    "browser": (
        "playwright",
        "browser",
        "ui",
        "user flow",
        "click through",
        "form submission",
        "end-to-end",
        "e2e",
    ),
    "provider": (
        "provider",
        "model",
        "registry",
        "route",
    ),
    "memory": (
        "memory",
        "truth",
        "ledger",
        "telemetry",
    ),
}


def _matches_any(lowered: str, group_name: str) -> bool:
    for phrase in PHRASE_GROUPS[group_name]:
        if " " in phrase or "-" in phrase:
            if phrase in lowered:
                return True
        else:
            if re.search(rf"\b{re.escape(phrase)}\b", lowered):
                return True
    return False


ROUTING_TIER_REGISTRY: list[RoutingTierRecord] = [
    RoutingTierRecord(
        tier_id="cron-lite",
        label="Cron Lite",
        purpose="Zero-LLM script lane for scheduled checks, sync, ingest, and alerts.",
        allowed_task_classes=["watchdog", "sync", "polling", "ingest", "threshold alert", "heartbeat"],
        forbidden_task_classes=["implementation", "adversarial review", "interactive interview"],
        preferred_routes=[],
        escalation_tier="cron-cheap",
        premium_allowed=False,
        runner_kind="script/no-agent",
        notifier_role="Telegram is notifier only; the script is the runner.",
    ),
    RoutingTierRecord(
        tier_id="cron-cheap",
        label="Cron Cheap",
        purpose="Cheapest sufficient reasoning lane for triage, curation, summaries, and low-stakes research.",
        allowed_task_classes=["summary", "triage", "curation", "light research", "attention filtering", "memory packaging"],
        forbidden_task_classes=["code implementation", "deep debugging", "adversarial review"],
        preferred_routes=["ollama-qwen3-14b", "openai-gpt-5.4-mini"],
        escalation_tier="cron-build",
        premium_allowed=False,
        runner_kind="agent",
        notifier_role="Telegram is delivery only; do not treat notification as model selection.",
    ),
    RoutingTierRecord(
        tier_id="cron-build",
        label="Cron Build",
        purpose="Medium-cost builder lane for implementation-shaped scheduled work that still needs tools and grounded reasoning.",
        allowed_task_classes=["implementation", "repo evaluation", "structured diagnosis", "deploy prep"],
        forbidden_task_classes=["high-volume polling", "adversarial review as default"],
        preferred_routes=["anthropic-claude-code-sonnet-4.6", "openai-gpt-5.4-mini"],
        escalation_tier="premium-review",
        premium_allowed=False,
        runner_kind="agent",
        notifier_role="Delivery surface stays separate from the builder lane.",
    ),
    RoutingTierRecord(
        tier_id="premium-review",
        label="Premium Review",
        purpose="Explicit reviewer/breaker lane for adversarial review, high-ambiguity judgment, and architecture challenge.",
        allowed_task_classes=["adversarial review", "proof audit", "route challenge", "major architecture judgment"],
        forbidden_task_classes=["default cron runtime", "fallback route", "broad swarm default"],
        preferred_routes=["google-gemini-2.5-pro"],
        escalation_tier=None,
        premium_allowed=True,
        runner_kind="agent",
        notifier_role="Telegram may receive the verdict, but never defines premium eligibility.",
    ),
]


TASK_FAMILY_ROUTING_REGISTRY: list[TaskFamilyRoutingRecord] = [
    TaskFamilyRoutingRecord(
        task_family="watchdog",
        lane_id="cron-lite",
        template_id=None,
        route_strategy="script-first",
        default_route=None,
        allowed_escalation_tier="cron-cheap",
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5", "google-gemini-2.5-pro"],
        cron_eligible=True,
        script_preferred=True,
        premium_requires_explicit_opt_in=True,
        notes=["If bash/python can do it, do not wake a premium model.", "Use empty stdout as silent no-op for healthy checks."],
    ),
    TaskFamilyRoutingRecord(
        task_family="ingest",
        lane_id="cron-lite",
        template_id=None,
        route_strategy="script-first",
        default_route=None,
        allowed_escalation_tier="cron-cheap",
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5", "google-gemini-2.5-pro"],
        cron_eligible=True,
        script_preferred=True,
        premium_requires_explicit_opt_in=True,
        notes=["Ingestion jobs should be deterministic and resumable."],
    ),
    TaskFamilyRoutingRecord(
        task_family="attention",
        lane_id="cron-cheap",
        template_id="attention-watcher",
        route_strategy="cheap-reasoning",
        default_route="ollama-qwen3-14b",
        allowed_escalation_tier="cron-build",
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5"],
        cron_eligible=True,
        script_preferred=False,
        premium_requires_explicit_opt_in=True,
        notes=["Attention boards should surface exceptions, not premium chatter."],
    ),
    TaskFamilyRoutingRecord(
        task_family="memory/truth",
        lane_id="cron-cheap",
        template_id="memory-curator",
        route_strategy="cheap-reasoning",
        default_route="ollama-qwen3-14b",
        allowed_escalation_tier="cron-build",
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5"],
        cron_eligible=True,
        script_preferred=False,
        premium_requires_explicit_opt_in=True,
        notes=["Memory packaging is cheaper than implementation and should stay there."],
    ),
    TaskFamilyRoutingRecord(
        task_family="provider research",
        lane_id="cron-cheap",
        template_id="provider-intel-researcher",
        route_strategy="cheap-reasoning",
        default_route="google-gemini-2.5-pro",
        allowed_escalation_tier="premium-review",
        forbidden_routes=[],
        cron_eligible=True,
        script_preferred=False,
        premium_requires_explicit_opt_in=False,
        notes=["Provider/model comparison may use Gemini when context breadth matters."],
    ),
    TaskFamilyRoutingRecord(
        task_family="implementation",
        lane_id="cron-build",
        template_id="implementation-worker",
        route_strategy="builder-lane",
        default_route="anthropic-claude-code-sonnet-4.6",
        allowed_escalation_tier="premium-review",
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5"],
        cron_eligible=True,
        script_preferred=False,
        premium_requires_explicit_opt_in=False,
        notes=["Builder work defaults to Claude Code Sonnet, not Codex.", "Codex is intentionally blocked from the default builder lane to prevent subscription drain."],
    ),
    TaskFamilyRoutingRecord(
        task_family="browser-ui",
        lane_id="cron-build",
        template_id="browser-operator",
        route_strategy="capability-first",
        default_route="openai-gpt-5.4-mini",
        allowed_escalation_tier="premium-review",
        forbidden_routes=[],
        cron_eligible=True,
        script_preferred=False,
        premium_requires_explicit_opt_in=False,
        notes=["Browser work pays for capability only when direct API surfaces do not exist."],
    ),
    TaskFamilyRoutingRecord(
        task_family="review",
        lane_id="premium-review",
        template_id="review-judge",
        route_strategy="premium-explicit-only",
        default_route="google-gemini-2.5-pro",
        allowed_escalation_tier=None,
        forbidden_routes=[],
        cron_eligible=True,
        script_preferred=False,
        premium_requires_explicit_opt_in=True,
        notes=["Review lane is premium by design and must never be inherited."],
    ),
    TaskFamilyRoutingRecord(
        task_family="interactive interview",
        lane_id="blocked",
        template_id=None,
        route_strategy="manual-only",
        default_route=None,
        allowed_escalation_tier=None,
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5", "google-gemini-2.5-pro", "anthropic-claude-code-sonnet-4.6", "openai-gpt-5.4-mini", "ollama-qwen3-14b"],
        cron_eligible=False,
        script_preferred=False,
        premium_requires_explicit_opt_in=True,
        notes=["Human-dependent interviews should not be cron jobs."],
    ),
]


def get_routing_tier_registry() -> list[dict[str, Any]]:
    rows = [record.to_dict() for record in ROUTING_TIER_REGISTRY]
    _sync_universal_route_truth()
    return rows


def get_task_family_routing_matrix() -> list[dict[str, Any]]:
    rows = [record.to_dict() for record in TASK_FAMILY_ROUTING_REGISTRY]
    _sync_universal_route_truth()
    return rows


PRODUCT_WORKER_POOL_REGISTRY: list[ProductWorkerPoolRecord] = [
    ProductWorkerPoolRecord(
        product_id="famtastic-by-the-numbers",
        stage_id="v1",
        stage_label="Free chart + premium unlock foundation",
        objective="Ship the first real numerology app with transparent chart math, durable premium unlock architecture, and browser-proofed happy path.",
        template_id="implementation-worker",
        primary_routes=["glm-5.2", "glm-5.1", "ollama-qwen3-14b", "openai-gpt-5.4-mini"],
        escalation_routes=["anthropic-claude-code-sonnet-4.6", "google-gemini-2.5-pro"],
        forbidden_routes=["openai-codex-gpt-5.4", "openai-codex-gpt-5.5"],
        required_capabilities=["tools", "code", "browser-proof"],
        proof_surfaces=[
            "apps/famtastic-by-the-numbers/tests/smoke.mjs",
            "apps/famtastic-by-the-numbers/server.js",
            "apps/famtastic-by-the-numbers/lib/paypal.js",
        ],
        known_gaps=[
            "PayPal browser approval UI is still not wired; proof mode currently uses direct create/capture flow.",
            "Real production payment capture still depends on live PayPal credentials and reachable MySQL.",
        ],
    ),
    ProductWorkerPoolRecord(
        product_id="famtastic-by-the-numbers",
        stage_id="v2",
        stage_label="Deeper compatibility + stronger premium read",
        objective="Expand the premium value layer from teaser logic into a deeper compatibility and interpretation engine without overstating certainty.",
        template_id="local-bulk-drafter",
        primary_routes=["glm-5.2", "ollama-deepseek-r1-64k", "ollama-qwen3-32k", "ollama-gemma4"],
        escalation_routes=["google-gemini-2.5-pro", "openai-codex-gpt-5.5"],
        forbidden_routes=[],
        required_capabilities=["long-context synthesis", "structured writing", "review backup"],
        proof_surfaces=[
            "apps/famtastic-by-the-numbers/app.js::calculateCompatibility",
            "apps/famtastic-by-the-numbers/app.js::buildPremiumExperience",
            "apps/famtastic-by-the-numbers/README.md",
        ],
        known_gaps=[
            "Compatibility logic is materially deeper than the original gap log claimed, but still remains heuristic rather than full-chart or timing-driven.",
            "Premium interpretation copy can outrun the underlying scoring depth if not kept honest.",
        ],
    ),
    ProductWorkerPoolRecord(
        product_id="famtastic-by-the-numbers",
        stage_id="v3",
        stage_label="Richer timing + alternate lineage expansion",
        objective="Add timing depth and eventually alternate lineage support without mixing systems or drifting into fake precision.",
        template_id="provider-intel-researcher",
        primary_routes=["glm-5.2", "google-gemini-2.5-pro", "ollama-deepseek-r1-64k"],
        escalation_routes=["openai-codex-gpt-5.5", "anthropic-claude-code-sonnet-4.6"],
        forbidden_routes=[],
        required_capabilities=["research synthesis", "schema discipline", "lineage separation"],
        proof_surfaces=[
            "apps/famtastic-by-the-numbers/app.js::buildDailyGuidance",
            "obsidian/01-Shay-Platform/famtastic-by-the-numbers-wave1/v1-schema.md",
            "apps/famtastic-by-the-numbers/GAPS.md",
        ],
        known_gaps=[
            "Daily guidance is still lightweight and not yet multi-cycle.",
            "No Chaldean or alternate lineage mode exists yet; lineage separation is still doctrine, not implementation.",
        ],
    ),
]


def get_product_worker_pool_registry(product_id: str | None = None) -> list[dict[str, Any]]:
    rows = [record.to_dict() for record in PRODUCT_WORKER_POOL_REGISTRY]
    _sync_universal_route_truth()
    if not product_id:
        return rows
    wanted = str(product_id).strip().lower()
    return [row for row in rows if str(row["product_id"]).strip().lower() == wanted]


def _sync_universal_route_truth() -> None:
    global _UNIVERSAL_ROUTE_SYNC_ACTIVE
    if _UNIVERSAL_ROUTE_SYNC_ACTIVE:
        return
    _UNIVERSAL_ROUTE_SYNC_ACTIVE = True
    try:
        write_universal_route_truth()
    finally:
        _UNIVERSAL_ROUTE_SYNC_ACTIVE = False


def _brain_chain_for_task_family(
    row: Mapping[str, Any],
    providers: list[Mapping[str, Any]],
) -> list[str]:
    route_index = {provider["route_id"]: provider for provider in providers}
    ordered_routes: list[str] = []
    default_route = row.get("default_route")
    if isinstance(default_route, str) and default_route:
        ordered_routes.append(default_route)
    tier_id = row.get("lane_id")
    if isinstance(tier_id, str):
        try:
            tier = _routing_tier_record(tier_id)
            for route_id in tier.get("preferred_routes") or []:
                if route_id not in ordered_routes:
                    ordered_routes.append(route_id)
        except StopIteration:
            pass
    forbidden = set(row.get("forbidden_routes") or [])
    alias_by_provider = {
        "anthropic": "claude",
        "openrouter": "openrouter",
        "google": "gemini",
        "google-openai": "gemini",
        "ollama": "ollama",
    }
    brain_aliases: list[str] = []
    for route_id in ordered_routes:
        if route_id in forbidden:
            continue
        provider_id = str(route_index.get(route_id, {}).get("provider_id") or "")
        alias = alias_by_provider.get(provider_id)
        if alias and alias not in brain_aliases:
            brain_aliases.append(alias)
    for fallback in ["claude", "openrouter", "gemini", "ollama"]:
        if fallback not in brain_aliases:
            brain_aliases.append(fallback)
    return brain_aliases


def build_universal_route_truth() -> dict[str, Any]:
    providers = get_provider_model_registry()
    task_families = get_task_family_routing_matrix()
    generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    source_files = [
        str((Path(__file__).resolve())),
        str((Path(__file__).resolve().parent / "intelligence_cmd.py")),
        str((Path(__file__).resolve().parent / "main.py")),
    ]
    return {
        "schema_id": "intelligence-control-plane/universal-route-truth/v1",
        "source_repo": "famtastic-fritz/shay-shay",
        "source_surface": "shay intelligence control-plane export",
        "generated_at": generated_at,
        "source_files": source_files,
        "refresh_command": "uv run python -m shay_cli.main intelligence control-plane export",
        "routes": providers,
        "tiers": get_routing_tier_registry(),
        "task_families": task_families,
        "worker_pool": get_product_worker_pool_registry(),
        "bridges": {
            "shay_agent_os": {
                "brain_alias_to_route_ids": {
                    "claude": ["anthropic-claude-code-sonnet-4.6"],
                    "openrouter": ["openrouter-claude-sonnet-4.6"],
                    "gemini": ["google-gemini-2.5-flash", "google-gemini-2.5-pro"],
                    "ollama": ["ollama-qwen3-14b", "ollama-hermes3"],
                },
                "default_brain_chain": ["claude", "openrouter", "gemini", "ollama"],
                "task_family_brain_preferences": {
                    row["task_family"]: _brain_chain_for_task_family(row, providers)
                    for row in task_families
                },
            }
        },
    }


def write_universal_route_truth(path: str | Path | None = None) -> Path:
    target = Path(path).expanduser() if path else _universal_route_export_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_universal_route_truth()
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def read_universal_route_truth(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path).expanduser() if path else _universal_route_export_path()
    if not target.exists():
        write_universal_route_truth(target)
    return json.loads(target.read_text(encoding="utf-8"))


def classify_task_family(task: str, *, no_agent: bool = False, script: str | None = None) -> str:
    lowered = str(task or "").strip().lower()
    if no_agent or script:
        if _matches_any(lowered, "interactive"):
            return "interactive interview"
        return "watchdog" if _matches_any(lowered, "watchdog") else "ingest"
    if _matches_any(lowered, "interactive"):
        return "interactive interview"
    if _matches_any(lowered, "review"):
        return "review"
    if _matches_any(lowered, "browser"):
        return "browser-ui"
    if _matches_any(lowered, "implementation"):
        return "implementation"
    if _matches_any(lowered, "provider"):
        return "provider research"
    if _matches_any(lowered, "recall") or _matches_any(lowered, "memory"):
        return "memory/truth"
    if _matches_any(lowered, "watcher") or _matches_any(lowered, "attention"):
        return "attention"
    return "attention"


def _task_family_record(task_family: str) -> dict[str, Any]:
    return next(row for row in get_task_family_routing_matrix() if row["task_family"] == task_family)


def _routing_tier_record(tier_id: str) -> dict[str, Any]:
    return next(row for row in get_routing_tier_registry() if row["tier_id"] == tier_id)


def audit_cron_jobs() -> dict[str, Any]:
    jobs_file = Path(get_shay_home()).expanduser() / "cron" / "jobs.json"
    if not jobs_file.exists():
        return {
            "jobs_file": str(jobs_file),
            "job_count": 0,
            "jobs": [],
            "summary": {"pinned_jobs": 0, "unpinned_agent_jobs": 0, "invalid_cron_jobs": 0},
        }
    payload = json.loads(jobs_file.read_text())
    rows: list[dict[str, Any]] = []
    pinned_jobs = 0
    unpinned_agent_jobs = 0
    invalid_cron_jobs = 0
    for job in payload.get("jobs", []):
        task = " ".join([str(job.get("name") or ""), str(job.get("prompt") or ""), str(job.get("script") or "")])
        family = classify_task_family(task, no_agent=bool(job.get("no_agent")), script=str(job.get("script") or "") or None)
        policy = _task_family_record(family)
        lane_id = policy["lane_id"]
        pinned = bool(job.get("provider") or job.get("model"))
        if pinned:
            pinned_jobs += 1
        elif not bool(job.get("no_agent")):
            unpinned_agent_jobs += 1
        if not policy["cron_eligible"]:
            invalid_cron_jobs += 1
        rows.append(
            {
                "job_id": str(job.get("id") or ""),
                "name": str(job.get("name") or ""),
                "state": str(job.get("state") or ("paused" if not job.get("enabled") else "enabled")),
                "no_agent": bool(job.get("no_agent")),
                "script": str(job.get("script") or ""),
                "pinned": pinned,
                "provider": job.get("provider"),
                "model": job.get("model"),
                "task_family": family,
                "recommended_lane": lane_id,
                "cron_eligible": bool(policy["cron_eligible"]),
                "premium_allowed": bool(_routing_tier_record(lane_id).get("premium_allowed")) if lane_id != "blocked" else False,
                "risk": (
                    "invalid-cron" if not policy["cron_eligible"] else
                    "unpinned-agent-default-risk" if (not pinned and not bool(job.get("no_agent"))) else
                    "script-safe" if bool(job.get("no_agent")) else
                    "pinned-agent"
                ),
            }
        )
    return {
        "jobs_file": str(jobs_file),
        "job_count": len(rows),
        "jobs": rows,
        "summary": {
            "pinned_jobs": pinned_jobs,
            "unpinned_agent_jobs": unpinned_agent_jobs,
            "invalid_cron_jobs": invalid_cron_jobs,
        },
    }


def build_route_scorecards(limit: int = 200) -> list[dict[str, Any]]:
    scorecards: dict[str, dict[str, Any]] = {}
    for record in list_run_records(limit=limit):
        route_id = str(record.get("provider_model_route") or "").strip()
        template_id = str(record.get("template_id") or "").strip()
        if not route_id or not template_id:
            continue
        key = f"{template_id}::{route_id}"
        card = scorecards.setdefault(
            key,
            {
                "template_id": template_id,
                "route_id": route_id,
                "run_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "verifier_backed_successes": 0,
                "medianless_latency_samples": [],
                "task_families": [],
                "last_run_id": "",
                "last_outcome": "",
            },
        )
        card["run_count"] += 1
        outcome = str(record.get("outcome") or "unknown").strip().lower()
        if outcome in {"success", "passed", "ok", "green"}:
            card["success_count"] += 1
        elif outcome in {"failed", "failure", "error", "blocked", "unsafe"}:
            card["failure_count"] += 1
        for item in normalized_validation_results(record):
            if item.get("result_class") == "success" and item.get("is_verifier_backed"):
                card["verifier_backed_successes"] += 1
        duration = record.get("duration_seconds")
        if isinstance(duration, (int, float)):
            card["medianless_latency_samples"].append(float(duration))
        task_family = str(record.get("task_family") or "").strip()
        if task_family and task_family not in card["task_families"]:
            card["task_families"].append(task_family)
        card["last_run_id"] = str(record.get("run_id") or "")
        card["last_outcome"] = outcome
    results: list[dict[str, Any]] = []
    for card in scorecards.values():
        samples = sorted(card.pop("medianless_latency_samples"))
        if samples:
            mid = len(samples) // 2
            latency = samples[mid] if len(samples) % 2 else round((samples[mid - 1] + samples[mid]) / 2, 3)
        else:
            latency = None
        run_count = int(card["run_count"])
        success_count = int(card["success_count"])
        results.append(
            {
                **card,
                "success_rate": round(success_count / run_count, 3) if run_count else 0.0,
                "verification_rate": round(int(card["verifier_backed_successes"]) / run_count, 3) if run_count else 0.0,
                "median_latency_seconds": latency,
            }
        )
    return sorted(results, key=lambda item: (-item["success_rate"], -item["run_count"], item["template_id"], item["route_id"]))


def explain_route(task: str) -> dict[str, Any]:
    text = str(task or "").strip()
    lowered = text.lower()
    templates = get_agent_template_registry()
    routes = {row["route_id"]: row for row in get_provider_model_registry()}
    scorecards = build_route_scorecards()

    def _template(template_id: str) -> dict[str, Any]:
        return next(row for row in templates if row["template_id"] == template_id)

    def _preferred_route(template_id: str) -> str:
        template = _template(template_id)
        preferred = list(template.get("preferred_routes") or [])
        if not preferred:
            raise ValueError(f"template {template_id} has no preferred routes")
        return preferred[0]

    policy: dict[str, Any] | None = None
    tier: dict[str, Any] | None = None
    if _matches_any(lowered, "swarm"):
        chosen_template = "orchestrator-captain"
        chosen_route = _preferred_route(chosen_template)
        task_family = "orchestration"
    else:
        task_family = classify_task_family(text)
        policy = _task_family_record(task_family)
        chosen_template = str(policy.get("template_id") or "orchestrator-captain")
        if chosen_template == "orchestrator-captain" and task_family == "interactive interview":
            chosen_route = _preferred_route(chosen_template)
        else:
            template_routes = list(_template(chosen_template).get("preferred_routes") or [])
            policy_route = str(policy.get("default_route") or "")
            forbidden = set(policy.get("forbidden_routes") or [])
            allowed_routes = [route for route in template_routes if route not in forbidden]
            if policy_route and policy_route in allowed_routes:
                allowed_routes = [policy_route, *[route for route in allowed_routes if route != policy_route]]
            scored_allowed_routes = score_routes_for_task(
                text,
                [routes[route_id] for route_id in allowed_routes if route_id in routes],
            )
            if scored_allowed_routes:
                chosen_route = str(scored_allowed_routes[0]["route_id"])
            else:
                chosen_route = next(iter(allowed_routes), _preferred_route(chosen_template))
        if policy["lane_id"] != "blocked":
            tier = _routing_tier_record(policy["lane_id"])

    template = _template(chosen_template)
    alternatives = [
        row for row in templates if row["template_id"] != chosen_template and task_family in row["task_families"]
    ]
    route_scorecard = next(
        (row for row in scorecards if row["template_id"] == chosen_template and row["route_id"] == chosen_route),
        None,
    )
    route_record = routes[chosen_route]
    route_scores = score_routes_for_task(
        text,
        [routes[route_id] for route_id in template.get("preferred_routes") or [] if route_id in routes],
    )

    return {
        "task": text,
        "task_family": task_family,
        "module_boundaries": get_control_plane_modules(),
        "chosen_template": chosen_template,
        "chosen_route": chosen_route,
        "routing_tier": tier,
        "task_family_policy": policy,
        "template_record": template,
        "provider_model_record": route_record,
        "evidence": {
            "route_scorecard": route_scorecard,
            "route_scores": route_scores,
            "memory_truth_surfaces": get_memory_truth_surfaces(),
            "selection_reason": [
                f"Template {chosen_template} serves {', '.join(template['task_families'])}.",
                f"Route {chosen_route} matches recommended task families: {', '.join(route_record['recommended_task_families'])}.",
                f"Task family {task_family} maps to lane {policy['lane_id'] if policy else 'captain-default'}.",
                (
                    "Premium use is explicit-only for this task family."
                    if policy and policy.get("premium_requires_explicit_opt_in")
                    else "This lane may escalate when the task proves it needs a stronger route."
                ),
                "Parent verification still required before promotion claims.",
            ],
        },
        "rejected_alternatives": [
            {
                "template_id": row["template_id"],
                "reason": "Not the tightest task-family fit for this ask.",
            }
            for row in alternatives[:3]
        ],
    }


__all__ = [
    "CONTROL_PLANE_SCHEMA_IDS",
    "audit_cron_jobs",
    "build_route_scorecards",
    "build_universal_route_truth",
    "classify_task_family",
    "explain_route",
    "get_agent_template_registry",
    "get_control_plane_modules",
    "get_memory_truth_surfaces",
    "get_product_worker_pool_registry",
    "get_provider_model_registry",
    "get_routing_tier_registry",
    "get_task_family_routing_matrix",
    "instantiate_worker_from_template",
    "read_universal_route_truth",
    "write_universal_route_truth",
]
