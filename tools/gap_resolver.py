"""
tools/gap_resolver.py — reuse-before-generate gap resolution.

When Shay (planner, the skill_manage create pre-flight guard, or the curator)
identifies a capability it cannot satisfy with installed skills, it asks the
GapResolver to look for an existing skill BEFORE authoring a new one.

Flow (per the community-gap-discovery design):
  1. discover()  — fan out across registered SkillSource adapters (local catalog
                   first, then SkillNet / clawhub / GitHub), dedupe by content
                   hash, score each candidate, return a ranked list with a
                   per-candidate verdict. READ-ONLY — never installs.
  2. resolve()   — given a gap descriptor, return a single decision:
                     ADOPT  (>= auto_install_threshold; strong match, safe),
                     REVIEW (a plausible candidate exists — surface, ask),
                     BUILD  (no good match — fall through to skill create).

The resolver NEVER installs here. Acting on an ADOPT verdict (the actual fetch +
skills_guard scan + quarantine + install) is the caller's job through the
existing hub install path — keeping this module pure orchestration + scoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default discovery search order (mirrors the design's config block). Local /
# installed catalog is implicitly first via the source router ordering.
DEFAULT_SOURCES = ["skillnet", "clawhub", "github"]

# Verdict thresholds (mirror gap_discovery config defaults).
ADOPT_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.45

# Source trust ranking — higher is safer/preferred.
_SOURCE_RANK = {
    "official": 1.0,
    "shay-index": 0.9,
    "skills-sh": 0.8,
    "well-known": 0.75,
    "github": 0.7,
    "skillnet": 0.6,    # ships 5-D evaluations but content is community
    "clawhub": 0.4,     # noisier corpus, no server search, no evaluations
    "lobehub": 0.4,
    "claude-marketplace": 0.5,
    "url": 0.5,
}

_EVAL_LEVEL_SCORE = {
    "high": 1.0,
    "good": 0.85,
    "medium": 0.6,
    "moderate": 0.6,
    "low": 0.25,
    "poor": 0.1,
    "unknown": 0.5,
}


def _tokenize(s: str) -> set:
    out = set()
    for tok in "".join(c if c.isalnum() else " " for c in (s or "").lower()).split():
        if len(tok) >= 3:
            out.add(tok)
    return out


def _name_similarity(query: str, meta) -> float:
    """Jaccard-ish overlap of the query tokens against name+description."""
    q = _tokenize(query)
    if not q:
        return 0.0
    text = _tokenize(f"{getattr(meta, 'name', '')} {getattr(meta, 'description', '')}")
    if not text:
        return 0.0
    inter = len(q & text)
    return inter / float(len(q))


def _evaluation_score(meta) -> Optional[float]:
    """Average the SkillNet 5-D evaluation levels into [0,1], or None."""
    extra = getattr(meta, "extra", {}) or {}
    evaluation = extra.get("evaluation")
    if not isinstance(evaluation, dict) or not evaluation:
        return None
    scores: List[float] = []
    for dim in evaluation.values():
        level = None
        if isinstance(dim, dict):
            level = dim.get("level")
        elif isinstance(dim, str):
            level = dim
        if level is not None:
            scores.append(_EVAL_LEVEL_SCORE.get(str(level).lower(), 0.5))
    if not scores:
        return None
    return sum(scores) / len(scores)


def _score_candidate(query: str, meta) -> float:
    """Combine source trust, evaluation, and name/desc similarity into [0,1]."""
    source = getattr(meta, "source", "")
    trust = _SOURCE_RANK.get(source, 0.4)
    sim = _name_similarity(query, meta)
    ev = _evaluation_score(meta)

    # Weighting: similarity is the strongest signal that this candidate matches
    # the gap; trust + evaluation gate whether it's safe enough to auto-adopt.
    if ev is None:
        # No evaluation data (clawhub/github): lean on similarity + trust.
        score = 0.6 * sim + 0.4 * trust
    else:
        score = 0.5 * sim + 0.3 * ev + 0.2 * trust
    return round(min(1.0, max(0.0, score)), 4)


def _verdict_for(score: float) -> str:
    if score >= ADOPT_THRESHOLD:
        return "ADOPT"
    if score >= REVIEW_THRESHOLD:
        return "REVIEW"
    return "BUILD"


def _candidate_dict(query: str, meta) -> Dict[str, Any]:
    score = _score_candidate(query, meta)
    return {
        "name": getattr(meta, "name", ""),
        "description": getattr(meta, "description", ""),
        "source": getattr(meta, "source", ""),
        "identifier": getattr(meta, "identifier", ""),
        "trust_level": getattr(meta, "trust_level", "community"),
        "score": score,
        "verdict": _verdict_for(score),
        "evaluation": (getattr(meta, "extra", {}) or {}).get("evaluation"),
    }


def discover(query: str, sources: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Read-only fan-out discovery. Returns ranked candidate dicts with verdicts.

    Local + installed catalog is searched first (via the source router
    ordering); community sources follow. Dedupes by content hash. Never installs.
    """
    from tools import skills_hub as hub

    router = hub.create_source_router()
    wanted = set(sources) if sources else None

    metas = []
    for src in router:
        sid = src.source_id()
        if wanted is not None and sid not in wanted and sid != "official":
            continue
        try:
            metas.extend(src.search(query, limit=limit) or [])
        except Exception as e:
            logger.debug("gap discovery: source %s failed: %s", sid, e)

    # Dedupe by the candidate's identifier (then name). A candidate fetched from
    # two sources resolves to the same GitHub identifier, so this collapses the
    # SkillNet-vs-GitHub duplicate the design calls out.
    import hashlib

    def _key(meta) -> str:
        ident = getattr(meta, "identifier", "") or getattr(meta, "name", "")
        return hashlib.sha1(ident.encode("utf-8", "ignore")).hexdigest()

    seen = set()
    deduped = []
    for m in metas:
        key = _key(m)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)

    ranked = sorted(
        (_candidate_dict(query, m) for m in deduped),
        key=lambda c: c["score"],
        reverse=True,
    )
    return ranked[:limit]


class GapResolver:
    """Orchestrates reuse-before-generate over the read-only discovery pass."""

    def __init__(self, auto_install_threshold: float = ADOPT_THRESHOLD,
                 sources: Optional[List[str]] = None, max_candidates: int = 5):
        self.auto_install_threshold = auto_install_threshold
        self.sources = sources or DEFAULT_SOURCES
        self.max_candidates = max_candidates

    def resolve(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a capability gap to a single decision + supporting candidates.

        *gap* is ``{capability, context?, why?}``. Returns
        ``{verdict, capability, candidates[], chosen?}`` where verdict is one of
        ADOPT / REVIEW / BUILD. Acting on ADOPT (the install) is the caller's
        job; this method only decides.
        """
        capability = gap.get("capability") or gap.get("query") or ""
        candidates = discover(capability, sources=self.sources, limit=self.max_candidates)

        decision = "BUILD"
        chosen = None
        if candidates:
            top = candidates[0]
            if top["score"] >= self.auto_install_threshold:
                decision = "ADOPT"
                chosen = top
            elif top["verdict"] in ("ADOPT", "REVIEW"):
                decision = "REVIEW"
                chosen = top

        return {
            "verdict": decision,
            "capability": capability,
            "candidates": candidates,
            "chosen": chosen,
        }
