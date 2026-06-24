from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping

from agent.process_intelligence import list_run_records, normalized_validation_results
from shay_cli.intelligence_seed import agent_by_id, get_agent_registry


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


CONTROL_PLANE_SCHEMA_IDS = {
    "module_boundary": "intelligence-control-plane/module-boundary/v1",
    "provider_model_record": "intelligence-control-plane/provider-model-record/v1",
    "agent_template_record": "intelligence-control-plane/agent-template-record/v1",
    "worker_instance_record": "intelligence-control-plane/worker-instance-record/v1",
    "routing_decision_record": "intelligence-control-plane/routing-decision-record/v1",
    "telemetry_run_overlay": "intelligence-control-plane/telemetry-run-overlay/v1",
    "memory_surface_record": "intelligence-control-plane/memory-surface-record/v1",
}


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
        route_id="openai-codex-gpt-5.4",
        provider_id="openai-codex",
        provider_label="OpenAI Codex",
        model_id="gpt-5.4",
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
    return [record.to_dict() for record in PROVIDER_MODEL_REGISTRY]


_TEMPLATE_SEEDS = [
    {
        "template_id": "orchestrator-captain",
        "role_name": "Orchestrator Captain",
        "agent_id": "work-router",
        "task_families": ["orchestration", "planning", "final synthesis"],
        "preferred_routes": ["openai-codex-gpt-5.4", "google-gemini-2.5-pro"],
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
        "preferred_routes": ["openai-codex-gpt-5.4", "openai-gpt-5.4-mini"],
        "budget_profile": "mid",
        "latency_profile": "balanced",
        "output_contract": "capability updates + caveats + next action",
    },
    {
        "template_id": "implementation-worker",
        "role_name": "Implementation Worker",
        "agent_id": "worker-supervisor",
        "task_families": ["code implementation", "schema wiring", "CLI additions", "implementation", "deploy"],
        "preferred_routes": ["openai-codex-gpt-5.4", "openai-gpt-5.4-mini"],
        "budget_profile": "mid",
        "latency_profile": "balanced",
        "output_contract": "file diff + tests + residue",
    },
    {
        "template_id": "review-judge",
        "role_name": "Review Judge",
        "agent_id": "run-reviewer",
        "task_families": ["adversarial review", "route challenge", "proof audit", "review"],
        "preferred_routes": ["google-gemini-2.5-pro", "openai-codex-gpt-5.4"],
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
        "preferred_routes": ["openai-codex-gpt-5.4", "openai-gpt-5.4-mini"],
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
        "audit",
        "review",
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

    if _matches_any(lowered, "swarm"):
        chosen_template = "orchestrator-captain"
        chosen_route = "openai-codex-gpt-5.4"
        task_family = "orchestration"
    elif _matches_any(lowered, "watcher"):
        chosen_template = "attention-watcher"
        chosen_route = "openai-gpt-5.4-mini"
        task_family = "monitoring"
    elif _matches_any(lowered, "attention"):
        chosen_template = "attention-watcher"
        chosen_route = "openai-gpt-5.4-mini"
        task_family = "attention"
    elif _matches_any(lowered, "recall"):
        chosen_template = "memory-curator"
        chosen_route = "openai-gpt-5.4-mini"
        task_family = "memory/truth"
    elif _matches_any(lowered, "review"):
        chosen_template = "review-judge"
        chosen_route = "google-gemini-2.5-pro"
        task_family = "review"
    elif _matches_any(lowered, "browser"):
        chosen_template = "browser-operator"
        chosen_route = "openai-codex-gpt-5.4"
        task_family = "browser-ui"
    elif _matches_any(lowered, "implementation"):
        chosen_template = "implementation-worker"
        chosen_route = "openai-codex-gpt-5.4"
        task_family = "implementation"
    elif _matches_any(lowered, "provider"):
        chosen_template = "provider-intel-researcher"
        chosen_route = "google-gemini-2.5-pro"
        task_family = "provider research"
    elif _matches_any(lowered, "memory"):
        chosen_template = "memory-curator"
        chosen_route = "openai-gpt-5.4-mini"
        task_family = "memory/truth"
    else:
        chosen_template = "orchestrator-captain"
        chosen_route = "openai-codex-gpt-5.4"
        task_family = "orchestration"

    template = next(row for row in templates if row["template_id"] == chosen_template)
    alternatives = [
        row for row in templates if row["template_id"] != chosen_template and task_family in row["task_families"]
    ]
    route_scorecard = next(
        (row for row in scorecards if row["template_id"] == chosen_template and row["route_id"] == chosen_route),
        None,
    )
    route_record = routes[chosen_route]

    return {
        "task": text,
        "task_family": task_family,
        "module_boundaries": get_control_plane_modules(),
        "chosen_template": chosen_template,
        "chosen_route": chosen_route,
        "template_record": template,
        "provider_model_record": route_record,
        "evidence": {
            "route_scorecard": route_scorecard,
            "memory_truth_surfaces": get_memory_truth_surfaces(),
            "selection_reason": [
                f"Template {chosen_template} serves {', '.join(template['task_families'])}.",
                f"Route {chosen_route} matches recommended task families: {', '.join(route_record['recommended_task_families'])}.",
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
    "build_route_scorecards",
    "explain_route",
    "get_agent_template_registry",
    "get_control_plane_modules",
    "get_memory_truth_surfaces",
    "get_provider_model_registry",
    "instantiate_worker_from_template",
]
