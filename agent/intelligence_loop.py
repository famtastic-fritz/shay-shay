"""Executable Shay intelligence-loop slices.

The loop stays conservative: it synthesizes candidate artifacts and proposal
surfaces, but does not silently mutate canonical memory or capability truth.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from agent.ambient_context import LocalArtifactConnector, ProcessSnapshotConnector, collect_ambient_context
from agent.intelligence_governance import (
    IntelligenceLoopConfig,
    decide_pointer_promotions,
    run_generative_reflection,
    stage_capability_reconciliation,
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_POINTER_RE = re.compile(
    r"(?P<label>[A-Za-z0-9][A-Za-z0-9 _/-]{2,80}):\s*"
    r"(?P<path>~?/[^\n§]+\.(?:md|json|jsonl|txt))"
)
_CAPABILITY_RE = re.compile(
    r"(?P<capability>[a-z][a-z0-9_-]{2,})[^\n]{0,120}?"
    r"(?P<signal>proven_live|implemented|partial|seeded|blocked|gap|fails?|passed)",
    re.IGNORECASE,
)

@dataclass(frozen=True)
class SynthesizedClaim:
    claim: str
    confidence: float
    sources: tuple[str, ...]
    tags: tuple[str, ...]

@dataclass(frozen=True)
class ReflectivePattern:
    pattern: str
    triggers: tuple[str, ...]
    suggested_prefetch: tuple[str, ...]
    confidence: float

@dataclass(frozen=True)
class PointerCandidate:
    entry: str
    source_tag: str
    preferred_tool: str
    source: str
    confidence: float

@dataclass(frozen=True)
class CapabilityProposal:
    capability_id: str
    observed_signal: str
    proposed_status: str
    source: str
    confidence: float
    review_required: bool = True

@dataclass(frozen=True)
class SessionContextItem:
    label: str
    source: str
    summary: str
    preferred_tool: str = "session_search"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tokens(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for token in _TOKEN_RE.findall(text.lower()):
        if token in seen or len(token) < 3:
            continue
        seen.add(token)
        out.append(token)
    return out


def _split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for part in _SENTENCE_RE.split(text or ""):
        clean = " ".join(part.strip().split())
        if 24 <= len(clean) <= 240:
            sentences.append(clean)
    return sentences


def read_text_sources(paths: Sequence[Path]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in paths:
        try:
            if path.exists() and path.is_file():
                sources[str(path)] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return sources


def synthesize_reflection(sources: Mapping[str, str], *, max_claims: int = 12) -> dict:
    """Build L2/L3 candidate artifacts from local text without mutating truth."""
    scored: list[tuple[int, str, str, tuple[str, ...]]] = []
    trigger_counts: dict[str, int] = {}
    pointer_hits: list[str] = []
    for source, text in sources.items():
        source_tokens = _tokens(Path(source).stem + " " + text[:4000])
        for token in source_tokens[:80]:
            trigger_counts[token] = trigger_counts.get(token, 0) + 1
        for match in _POINTER_RE.finditer(text):
            pointer_hits.append(match.group("path").strip())
        for sentence in _split_sentences(text):
            lower = sentence.lower()
            score = 0
            for word in ("fritz", "prefers", "gap", "blocked", "proof", "memory", "capability", "shay"):
                if word in lower:
                    score += 2
            score += min(4, len(set(_tokens(sentence)) & set(source_tokens)))
            if score:
                scored.append((score, source, sentence, tuple(_tokens(sentence)[:8])))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    claims: list[SynthesizedClaim] = []
    seen_claims: set[str] = set()
    for score, source, sentence, tags in scored:
        key = sentence.lower()
        if key in seen_claims:
            continue
        seen_claims.add(key)
        confidence = min(0.95, 0.55 + (score * 0.04))
        claims.append(SynthesizedClaim(sentence, round(confidence, 2), (source,), tags))
        if len(claims) >= max_claims:
            break
    triggers = tuple(token for token, _ in sorted(trigger_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12])
    patterns: list[ReflectivePattern] = []
    if triggers:
        suggested = tuple(dict.fromkeys(pointer_hits[:5]))
        patterns.append(ReflectivePattern(
            "Recurring high-signal terms should be prefetched before related asks.",
            triggers,
            suggested,
            0.72 if claims else 0.5,
        ))
    return {
        "generated_at": _now(),
        "mode": "local_synthesis",
        "l2_claims": [asdict(c) for c in claims],
        "l3_patterns": [asdict(p) for p in patterns],
    }


def build_pointer_candidates(reflection: Mapping) -> list[PointerCandidate]:
    candidates: list[PointerCandidate] = []
    for pattern in reflection.get("l3_patterns", []) or []:
        for source in pattern.get("suggested_prefetch", []) or []:
            candidates.append(PointerCandidate(
                entry=f"Generated pointer candidate: {source}",
                source_tag="reflection:l3",
                preferred_tool="read_file",
                source=source,
                confidence=float(pattern.get("confidence", 0.5)),
            ))
    for claim in reflection.get("l2_claims", []) or []:
        for source in claim.get("sources", []) or []:
            if source.endswith((".md", ".json", ".jsonl", ".txt")):
                candidates.append(PointerCandidate(
                    entry=f"Reflection source pointer: {source}",
                    source_tag="reflection:l2",
                    preferred_tool="read_file",
                    source=source,
                    confidence=float(claim.get("confidence", 0.5)),
                ))
    dedup: dict[str, PointerCandidate] = {}
    for item in candidates:
        old = dedup.get(item.source)
        if old is None or item.confidence > old.confidence:
            dedup[item.source] = item
    return sorted(dedup.values(), key=lambda item: (-item.confidence, item.source))


def build_capability_proposals(sources: Mapping[str, str]) -> list[CapabilityProposal]:
    proposals: dict[str, CapabilityProposal] = {}
    for source, text in sources.items():
        for match in _CAPABILITY_RE.finditer(text):
            capability = match.group("capability").lower()
            signal = match.group("signal").lower()
            proposed = "partial"
            confidence = 0.62
            if signal in {"proven_live", "passed"}:
                proposed = "proven_live"
                confidence = 0.82
            elif signal in {"implemented"}:
                proposed = "implemented"
                confidence = 0.72
            elif signal in {"blocked", "gap", "fail", "fails"}:
                proposed = "partial"
                confidence = 0.68
            item = CapabilityProposal(capability, signal, proposed, source, confidence)
            old = proposals.get(capability)
            if old is None or item.confidence > old.confidence:
                proposals[capability] = item
    return sorted(proposals.values(), key=lambda item: (item.capability_id, -item.confidence))


def build_session_context(sources: Mapping[str, str], *, max_items: int = 6) -> list[SessionContextItem]:
    items: list[SessionContextItem] = []
    for source, text in sources.items():
        label = Path(source).stem.replace("-", " ")[:80]
        sentences = _split_sentences(text)
        summary = sentences[0] if sentences else "Recent session artifact available."
        items.append(SessionContextItem(label, source, summary[:220]))
    return items[:max_items]


def run_intelligence_loop_slices(
    source_paths: Sequence[Path],
    output_dir: Path,
    config: IntelligenceLoopConfig | Mapping | None = None,
) -> dict:
    """Run intelligence-loop surfaces into governed artifacts.

    The default remains conservative: deterministic local synthesis, review-gated
    capability changes, and no private ambient persistence.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = config if isinstance(config, IntelligenceLoopConfig) else IntelligenceLoopConfig.from_mapping(config)
    sources = read_text_sources(source_paths)
    reflection = synthesize_reflection(sources)
    generative = run_generative_reflection(
        {"sources": {k: v[:12000] for k, v in sources.items()}},
        cfg,
        client=None,
    )
    if generative.get("mode") == "generative_candidate" and (generative.get("l2_claims") or generative.get("l3_patterns")):
        reflection = {
            "generated_at": _now(),
            "mode": "local_plus_generative_candidate",
            "l2_claims": [*reflection.get("l2_claims", []), *generative.get("l2_claims", [])],
            "l3_patterns": [*reflection.get("l3_patterns", []), *generative.get("l3_patterns", [])],
        }
    pointers = build_pointer_candidates(reflection)
    pointer_decisions = decide_pointer_promotions([asdict(p) for p in pointers], cfg)
    capabilities = build_capability_proposals(sources)
    sessions = build_session_context(sources)
    ambient_items = collect_ambient_context(
        [
            LocalArtifactConnector(tuple(source_paths[:4]), ttl_seconds=cfg.ambient_default_ttl_seconds),
            ProcessSnapshotConnector(),
        ],
        enabled=cfg.ambient_context_enabled,
        persist_private_sources=cfg.ambient_persist_private_sources,
    )

    artifacts = {
        "reflection": output_dir / "reflection-synthesis.json",
        "generative_reflection": output_dir / "generative-reflection.json",
        "pointer_candidates": output_dir / "pointer-candidates.json",
        "pointer_promotions": output_dir / "pointer-promotions.json",
        "capability_proposals": output_dir / "capability-proposals.json",
        "capability_review_queue": output_dir / "capability-review-queue.jsonl",
        "session_context": output_dir / "session-context.json",
        "ambient_context": output_dir / "ambient-context.json",
        "closeout": output_dir / "intelligence-loop-closeout.json",
    }
    artifacts["reflection"].write_text(json.dumps(reflection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts["generative_reflection"].write_text(json.dumps(generative, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts["pointer_candidates"].write_text(json.dumps([asdict(p) for p in pointers], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts["pointer_promotions"].write_text(json.dumps([asdict(p) for p in pointer_decisions], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts["capability_proposals"].write_text(json.dumps([asdict(p) for p in capabilities], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    capability_stage = stage_capability_reconciliation([asdict(p) for p in capabilities], artifacts["capability_review_queue"], cfg)
    artifacts["session_context"].write_text(json.dumps([asdict(s) for s in sessions], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts["ambient_context"].write_text(json.dumps(ambient_items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    closeout = {
        "generated_at": _now(),
        "status": "completed",
        "slices": {
            "1_pointer_prefetch": "implemented in agent/intelligence_prefetch.py",
            "2_generative_reflection": str(artifacts["reflection"]),
            "3_pointer_promotion_governance": str(artifacts["pointer_promotions"]),
            "4_capability_matrix_reconciliation": str(artifacts["capability_review_queue"]),
            "5_session_ambient_context": str(artifacts["ambient_context"]),
        },
        "counts": {
            "sources": len(sources),
            "l2_claims": len(reflection.get("l2_claims", [])),
            "l3_patterns": len(reflection.get("l3_patterns", [])),
            "pointer_candidates": len(pointers),
            "pointer_auto_promotions": len([p for p in pointer_decisions if p.action == "auto_promote"]),
            "pointer_review_items": len([p for p in pointer_decisions if p.action != "auto_promote"]),
            "capability_proposals": len(capabilities),
            "session_context_items": len(sessions),
            "ambient_context_items": len(ambient_items),
        },
        "governance": "proposal-only; canonical memory and capability truth are not auto-mutated",
        "governance_details": {
            "canonical_memory_auto_mutation": False,
            "capability_direct_mutation": capability_stage.get("direct_mutation", False),
            "generative_mode": generative.get("mode"),
            "ambient_private_persistence": cfg.ambient_persist_private_sources,
        },
    }
    artifacts["closeout"].write_text(json.dumps(closeout, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return closeout
