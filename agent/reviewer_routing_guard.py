"""Reviewer routing guard backed by live bakeoff scorecards.

This module turns reviewer bakeoff summaries into runtime decisions. It is
intentionally conservative: unknown or weakly-proven reviewers may still run in
experimental lanes, but protected reviewer lanes require promotion evidence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

DEFAULT_SUMMARY_PATH = Path.home() / ".shay/runtime/model-routing/reviewer-summary.json"
DEFAULT_DECISION_LOG = Path.home() / ".shay/runtime/model-routing/route-decisions.jsonl"
PROTECTED_REVIEW_LANES = {"adversarial_review", "final_blocker_review", "blocker_review"}
REVIEW_HINTS = ("review", "reviewer", "adversarial", "critic", "audit", "blocker")
FINAL_HINTS = ("final", "blocker", "adversarial", "production", "security")


@dataclass(frozen=True)
class ReviewerRouteDecision:
    lane: str
    task_family: str
    provider: str
    model: str
    decision: str
    reason: str
    recommendation: str = "unknown"
    fallback: str | None = None
    generated_at: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        if not data["generated_at"]:
            data["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def infer_reviewer_lane(goal: str, context: str = "", role: str = "") -> str:
    text = " ".join([goal or "", context or "", role or ""]).lower()
    if not any(hint in text for hint in REVIEW_HINTS):
        return "non_review"
    if any(hint in text for hint in FINAL_HINTS):
        return "adversarial_review"
    return "review"


def infer_task_family(goal: str, context: str = "") -> str:
    text = " ".join([goal or "", context or ""]).lower()
    if any(word in text for word in ("diff", "patch", "code", "implementation", "repo", "test")):
        return "code_diff_review"
    if any(word in text for word in ("doc", "changelog", "state", "learning", "markdown")):
        return "doc_consistency"
    if any(word in text for word in ("schema", "telemetry", "jsonl", "scorecard")):
        return "telemetry_schema"
    if any(word in text for word in ("plan", "readiness", "architecture")):
        return "implementation_readiness"
    return "general_review"


def load_reviewer_summary(path: Path = DEFAULT_SUMMARY_PATH) -> dict:
    path = path.expanduser()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _candidate_rows(summary: Mapping) -> list[dict]:
    if isinstance(summary.get("candidates"), list):
        return [row for row in summary.get("candidates", []) if isinstance(row, dict)]
    if isinstance(summary.get("by_candidate"), Mapping):
        rows = []
        for key, value in summary.get("by_candidate", {}).items():
            if isinstance(value, Mapping):
                row = dict(value)
                row.setdefault("candidate", key)
                rows.append(row)
        return rows
    rows = []
    for key, value in summary.items():
        if isinstance(value, Mapping) and ("recommendation" in value or "pass_rate" in value):
            row = dict(value)
            row.setdefault("candidate", key)
            rows.append(row)
    return rows


def find_candidate(summary: Mapping, provider: str, model: str) -> dict | None:
    provider_l = _norm(provider)
    model_l = _norm(model)
    for row in _candidate_rows(summary):
        row_provider = _norm(row.get("provider"))
        row_model = _norm(row.get("model"))
        candidate = _norm(row.get("candidate"))
        if row_provider == provider_l and row_model == model_l:
            return row
        if candidate in {f"{provider_l}/{model_l}", f"{provider_l}:{model_l}"}:
            return row
        if provider_l and model_l and provider_l in candidate and model_l in candidate:
            return row
    return None


def _passed_families(row: Mapping) -> set[str]:
    for key in ("passed_task_families", "passed", "task_families"):
        value = row.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return {_norm(item) for item in value}
    return set()


def decide_reviewer_route(
    *,
    provider: str | None,
    model: str | None,
    goal: str,
    context: str = "",
    role: str = "",
    summary: Mapping | None = None,
) -> ReviewerRouteDecision:
    lane = infer_reviewer_lane(goal, context, role)
    task_family = infer_task_family(goal, context)
    provider_s = provider or "inherited"
    model_s = model or "inherited"
    if lane == "non_review":
        return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "allow", "not a reviewer lane")
    summary = summary if summary is not None else load_reviewer_summary()
    if not provider or not model:
        if lane in PROTECTED_REVIEW_LANES:
            return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "deny", "protected reviewer lane cannot inherit an unproven default reviewer")
        return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "allow", "non-protected reviewer lane may inherit default reviewer")
    row = find_candidate(summary, provider, model)
    if row is None:
        if lane in PROTECTED_REVIEW_LANES:
            return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "deny", "no reviewer bakeoff evidence for protected lane")
        return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "allow_experimental", "unknown reviewer allowed only for non-protected review lane")
    recommendation = str(row.get("recommendation") or "unknown")
    passed = _passed_families(row)
    pass_rate = float(row.get("pass_rate", 0.0) or 0.0)
    if recommendation == "promote_for_passed_task_families" and (_norm(task_family) in passed or pass_rate >= 0.8):
        return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "allow", "reviewer promoted by bakeoff scorecard", recommendation)
    if lane in PROTECTED_REVIEW_LANES:
        return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "deny", "reviewer not promoted for protected review lane", recommendation)
    return ReviewerRouteDecision(lane, task_family, provider_s, model_s, "allow_experimental", "reviewer not fully promoted; allowed only outside protected lanes", recommendation)


def append_route_decision(decision: ReviewerRouteDecision, path: Path = DEFAULT_DECISION_LOG) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")
