"""Shay Run Model router — advisory routing driven by run-policy.yaml.

The router READS ``run-policy.yaml`` and applies its routing rules so the
policy *drives* behavior rather than merely describing it. It is PURE and
ADVISORY: ``select_run`` returns a recommendation (chosen orchestrator,
per-item executor, and human-readable reasoning). It does NOT execute work
and does NOT override an explicit human request.

Source spec: obsidian/Shay-Memory/_system/RUN-MODEL.md

Resolution order for the policy file (first hit wins):
    1. ``$SHAY_RUN_POLICY``                       (explicit override path)
    2. ``$SHAY_HOME/run-policy.yaml``             (user override, usually ~/.shay)
    3. ``<repo>/shay_cli/data/run-policy.yaml``   (packaged default)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "load_policy",
    "policy_path",
    "select_run",
    "render_plan",
    "RunPlan",
    "ItemPlan",
]

_PACKAGED_DEFAULT = Path(__file__).parent / "data" / "run-policy.yaml"


# --------------------------------------------------------------------------- #
# Policy loading
# --------------------------------------------------------------------------- #
def policy_path() -> Path:
    """Resolve which run-policy.yaml the router will read."""
    override = os.environ.get("SHAY_RUN_POLICY", "").strip()
    if override and Path(override).is_file():
        return Path(override)

    shay_home = os.environ.get("SHAY_HOME", "").strip()
    if not shay_home:
        # Mirror shay_constants.get_shay_home default without importing it
        # (keep this module import-light and side-effect free).
        shay_home = str(Path.home() / ".shay")
    candidate = Path(shay_home) / "run-policy.yaml"
    if candidate.is_file():
        return candidate

    return _PACKAGED_DEFAULT


def load_policy(path: Path | str | None = None) -> dict[str, Any]:
    """Load and parse the run policy. Returns the parsed dict."""
    p = Path(path) if path is not None else policy_path()
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"run-policy.yaml did not parse to a mapping: {p}")
    return data


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #
@dataclass
class ItemPlan:
    """The executor recommendation for a single work item."""

    item: str
    executor: str
    kind: str
    reason: str


@dataclass
class RunPlan:
    """The full advisory recommendation for a request."""

    request: str
    orchestrator: str
    parallel: bool
    item_count: int
    items: list[ItemPlan] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    mode: str = "advisory"
    collision_warning: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "mode": self.mode,
            "orchestrator": self.orchestrator,
            "parallel": self.parallel,
            "item_count": self.item_count,
            "items": [
                {
                    "item": i.item,
                    "executor": i.executor,
                    "kind": i.kind,
                    "reason": i.reason,
                }
                for i in self.items
            ],
            "collision_warning": self.collision_warning,
            "reasoning": self.reasoning,
        }


# --------------------------------------------------------------------------- #
# Routing helpers
# --------------------------------------------------------------------------- #
def _contains_keyword(text: str, keywords: list[str]) -> str | None:
    """Return the first keyword found in ``text`` (case-insensitive)."""
    low = text.lower()
    for kw in keywords:
        if kw.lower() in low:
            return kw
    return None


def _classify_kind(text: str, executor_rule: dict[str, Any]) -> tuple[str, str, str]:
    """Map a piece of text to (kind, executor, matched_keyword).

    Falls back to the rule's ``default`` executor and kind ``general`` when no
    keyword matches. Research/doc are checked before code so that a phrase like
    "research the API" routes to research rather than tripping on "api".
    """
    kinds = executor_rule.get("kinds", {})
    # Deterministic priority: research, doc, then code.
    for kind_name in ("research", "doc", "code"):
        spec = kinds.get(kind_name)
        if not spec:
            continue
        kw = _contains_keyword(text, spec.get("keywords", []))
        if kw:
            return kind_name, spec.get("executor", executor_rule.get("default")), kw

    default_exec = executor_rule.get("default", "claude-cli")
    return "general", default_exec, ""


def _extract_item_count(request: str, items: list[str] | None) -> int:
    """Best-effort item count: explicit list wins, else parse a number, else 1."""
    if items:
        return len(items)
    # Look for the first standalone integer in the request (e.g. "build 10 screens").
    import re

    nums = re.findall(r"\b(\d+)\b", request)
    if nums:
        try:
            n = int(nums[0])
            if n > 0:
                return n
        except ValueError:
            pass
    return 1


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def select_run(
    request: str,
    items: list[str] | None = None,
    policy: dict[str, Any] | None = None,
) -> RunPlan:
    """Apply run-policy.yaml to a request and return an advisory ``RunPlan``.

    Pure function: no side effects, no execution, no override of explicit
    human intent. ``items`` is an optional explicit work-item list; when
    omitted the router infers a count from the request text.
    """
    if policy is None:
        policy = load_policy()

    mode = policy.get("mode", "advisory")
    routing = policy.get("routing", {})
    orch_rule = routing.get("orchestrator_rule", {})
    exec_rule = routing.get("executor_rule", {})
    collision_rule = routing.get("collision_rule", {})

    reasoning: list[str] = []
    item_count = _extract_item_count(request, items)

    # ---- Rule 1: orchestrator by item count + swarm keyword (dependency) ----
    swarm_keywords = orch_rule.get("swarm_keywords", [])
    swarm_kw = _contains_keyword(request, swarm_keywords)

    if item_count <= 1:
        orchestrator = orch_rule.get("single_item", "interactive")
        reasoning.append(
            f"1 item -> '{orchestrator}' (single ask, no loop) [Rule 1]"
        )
    elif swarm_kw:
        orchestrator = orch_rule.get("swarm_orchestrator", "swarm")
        reasoning.append(
            f"{item_count} items + swarm keyword '{swarm_kw}' -> '{orchestrator}' "
            f"(fan out in parallel, independent items) [Rule 1]"
        )
    else:
        orchestrator = orch_rule.get("default_multi", "ralph")
        reasoning.append(
            f"{item_count} items, no swarm keyword -> '{orchestrator}' "
            f"(sequential, gate+commit each, resumable) [Rule 1, default]"
        )

    orch_spec = (policy.get("orchestrators", {}) or {}).get(orchestrator, {})
    parallel = bool(orch_spec.get("parallel", False))

    # ---- Rule 2: task-kind -> executor (per item, else whole request) -------
    item_texts: list[str]
    if items:
        item_texts = list(items)
    else:
        # Synthesize N identical items from the request so each gets a plan row.
        item_texts = [request] * item_count

    item_plans: list[ItemPlan] = []
    for text in item_texts:
        kind, executor, kw = _classify_kind(text, exec_rule)
        if kw:
            reason = f"matched '{kw}' -> kind={kind} -> {executor} [Rule 2]"
        else:
            reason = f"no kind keyword -> default executor {executor} [Rule 2]"
        item_plans.append(
            ItemPlan(item=text, executor=executor, kind=kind, reason=reason)
        )

    # Summarize executor choice in reasoning (collapse if homogeneous).
    distinct_execs = sorted({ip.executor for ip in item_plans})
    if len(distinct_execs) == 1:
        reasoning.append(
            f"task-kind routing -> all items use '{distinct_execs[0]}' [Rule 2]"
        )
    else:
        reasoning.append(
            f"task-kind routing -> mixed executors: {', '.join(distinct_execs)} [Rule 2]"
        )

    # ---- Rule 3: collision rule (parallel only across different targets) ----
    collision_warning: str | None = None
    if parallel and collision_rule.get("downgrade_to_serial_on_collision"):
        # Advisory: if explicit items collide on identical targets, warn and
        # recommend a serial downgrade. We compare item text as a proxy for
        # target since real file-target resolution is out of advisory scope.
        if items and len(items) != len(set(items)):
            collision_warning = (
                "duplicate item targets detected; collision rule recommends serial "
                "execution on the SAME file — consider 'ralph' instead of 'swarm' "
                "[Rule 3]"
            )
            reasoning.append(collision_warning)

    return RunPlan(
        request=request,
        orchestrator=orchestrator,
        parallel=parallel,
        item_count=item_count,
        items=item_plans,
        reasoning=reasoning,
        mode=mode,
        collision_warning=collision_warning,
    )


# --------------------------------------------------------------------------- #
# Human-readable rendering (used by `shay run-plan`)
# --------------------------------------------------------------------------- #
def render_plan(plan: RunPlan, policy_src: Path | str | None = None) -> str:
    """Render a ``RunPlan`` as a readable text block for the CLI."""
    lines: list[str] = []
    lines.append(f'Run plan for: "{plan.request}"')
    lines.append("=" * 60)
    lines.append(f"  mode:         {plan.mode} (recommendation only — nothing runs)")
    lines.append(f"  items:        {plan.item_count}")
    lines.append(
        f"  orchestrator: {plan.orchestrator} "
        f"({'parallel' if plan.parallel else 'sequential'})"
    )

    # Per-item executor breakdown (collapse if homogeneous and many).
    distinct = sorted({i.executor for i in plan.items})
    lines.append("")
    if len(distinct) == 1 and plan.item_count > 1:
        ip = plan.items[0]
        lines.append(f"  executor:     {ip.executor}  (kind={ip.kind}, all {plan.item_count} items)")
    else:
        lines.append("  executors:")
        for idx, ip in enumerate(plan.items, 1):
            label = ip.item if ip.item != plan.request else f"item {idx}"
            if len(label) > 44:
                label = label[:41] + "..."
            lines.append(f"    {idx:>2}. {ip.executor:<11} kind={ip.kind:<8} {label}")

    lines.append("")
    lines.append("  why:")
    for r in plan.reasoning:
        lines.append(f"    - {r}")

    if policy_src is not None:
        lines.append("")
        lines.append(f"  policy:       {policy_src}")
    return "\n".join(lines)
