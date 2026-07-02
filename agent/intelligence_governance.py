"""Governed intelligence autonomy helpers.

These helpers move Shay from proposal-only artifacts toward bounded
self-improvement without allowing silent mutation of identity, authority, or
capability truth.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Protocol


LOW_RISK_TAGS = {"reflection:l2", "reflection:l3", "artifact", "gap-research", "session-context"}
HIGH_RISK_WORDS = ("soul", "persona", "nothing supersedes", "authority", "password", "secret", "payment")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class IntelligenceLoopConfig:
    generative_reflection_enabled: bool = False
    generative_provider: str | None = None
    generative_model: str | None = None
    generative_allow_paid: bool = False
    pointer_auto_promote_low_risk: bool = True
    pointer_min_confidence: float = 0.85
    pointer_min_independent_sources: int = 2
    capability_auto_mutation_enabled: bool = False
    ambient_context_enabled: bool = True
    ambient_default_ttl_seconds: int = 3600
    ambient_persist_private_sources: bool = False
    telemetry_enabled: bool = True
    telemetry_base_dir: Path = Path("~/.shay/runtime/swarm-runs")

    @classmethod
    def from_mapping(cls, data: Mapping | None) -> "IntelligenceLoopConfig":
        root = dict(data or {})
        loop = root.get("intelligence_loop", root)
        gen = loop.get("generative_reflection", {}) or {}
        pointer = loop.get("pointer_promotion", {}) or {}
        cap = loop.get("capability_reconciliation", {}) or {}
        ambient = loop.get("ambient_context", {}) or {}
        telemetry = loop.get("swarm_telemetry", {}) or {}
        return cls(
            generative_reflection_enabled=bool(gen.get("enabled", False)),
            generative_provider=gen.get("provider"),
            generative_model=gen.get("model"),
            generative_allow_paid=bool(gen.get("allow_paid", False)),
            pointer_auto_promote_low_risk=bool(pointer.get("auto_promote_low_risk", True)),
            pointer_min_confidence=float(pointer.get("min_confidence", 0.85)),
            pointer_min_independent_sources=int(pointer.get("min_independent_sources", 2)),
            capability_auto_mutation_enabled=bool(cap.get("auto_mutation_enabled", False)),
            ambient_context_enabled=bool(ambient.get("enabled", True)),
            ambient_default_ttl_seconds=int(ambient.get("default_ttl_seconds", 3600)),
            ambient_persist_private_sources=bool(ambient.get("persist_private_sources", False)),
            telemetry_enabled=bool(telemetry.get("enabled", True)),
            telemetry_base_dir=Path(str(telemetry.get("base_dir", "~/.shay/runtime/swarm-runs"))).expanduser(),
        )


@dataclass(frozen=True)
class PromotionDecision:
    entry: str
    source: str
    risk: str
    action: str
    reason: str
    confidence: float
    generated_at: str


def classify_pointer_risk(candidate: Mapping) -> str:
    text = " ".join(str(candidate.get(k, "")) for k in ("entry", "source", "source_tag")).lower()
    if any(word in text for word in HIGH_RISK_WORDS):
        return "high"
    if candidate.get("source_tag") in LOW_RISK_TAGS and str(candidate.get("preferred_tool", "")) in {"read_file", "session_search"}:
        return "low"
    return "medium"


def decide_pointer_promotions(candidates: Iterable[Mapping], config: IntelligenceLoopConfig) -> list[PromotionDecision]:
    decisions: list[PromotionDecision] = []
    source_counts: dict[str, int] = {}
    candidate_list = [dict(c) for c in candidates]
    for item in candidate_list:
        source_counts[str(item.get("source", ""))] = source_counts.get(str(item.get("source", "")), 0) + 1
    for item in candidate_list:
        confidence = float(item.get("confidence", 0.0))
        source = str(item.get("source", ""))
        risk = classify_pointer_risk(item)
        action = "review"
        reason = f"{risk}-risk pointer requires review"
        if (
            config.pointer_auto_promote_low_risk
            and risk == "low"
            and confidence >= config.pointer_min_confidence
            and source_counts.get(source, 0) >= config.pointer_min_independent_sources
        ):
            action = "auto_promote"
            reason = "low-risk dereferenceable pointer passed confidence/source thresholds"
        decisions.append(PromotionDecision(str(item.get("entry", "")), source, risk, action, reason, confidence, utc_now()))
    return decisions


def write_review_queue(path: Path, decisions: Iterable[PromotionDecision]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for decision in decisions:
            if decision.action != "auto_promote":
                handle.write(json.dumps(asdict(decision), ensure_ascii=False) + "\n")


class GenerativeClient(Protocol):
    def synthesize(self, packet: Mapping) -> Mapping: ...


def run_generative_reflection(packet: Mapping, config: IntelligenceLoopConfig, client: GenerativeClient | None = None) -> Mapping:
    if not config.generative_reflection_enabled or client is None:
        return {"mode": "deterministic_fallback", "generated_at": utc_now(), "l2_claims": [], "l3_patterns": []}
    try:
        result = client.synthesize(packet)
    except Exception as exc:  # safe fallback
        return {"mode": "deterministic_fallback", "generated_at": utc_now(), "error": str(exc), "l2_claims": [], "l3_patterns": []}
    if not isinstance(result, Mapping):
        return {"mode": "deterministic_fallback", "generated_at": utc_now(), "error": "malformed_result", "l2_claims": [], "l3_patterns": []}
    return {
        "mode": "generative_candidate",
        "provider": config.generative_provider,
        "model": config.generative_model,
        "generated_at": utc_now(),
        "l2_claims": list(result.get("l2_claims", []) or []),
        "l3_patterns": list(result.get("l3_patterns", []) or []),
    }


def stage_capability_reconciliation(proposals: Iterable[Mapping], output_path: Path, config: IntelligenceLoopConfig) -> dict:
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for proposal in proposals:
        row = dict(proposal)
        row["action"] = "stage_patch" if config.capability_auto_mutation_enabled else "review_only"
        row["direct_mutation"] = False
        row["generated_at"] = utc_now()
        rows.append(row)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return {"path": str(output_path), "count": len(rows), "direct_mutation": False}
