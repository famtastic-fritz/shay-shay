"""Reviewer route bake-off harness for grounded HyperSwarm review lanes.

The harness is intentionally model-agnostic: it scores reviewer outputs against
artifact-grounding gates, writes JSONL scorecards, and reduces repeated runs into
promotion/demotion recommendations. Live model invocation can wrap this module;
the core proof surface stays deterministic and testable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


CRITICAL_GATES = (
    "consumed_artifact",
    "cited_sources",
    "severity_ranked",
    "actionable_issues",
)

FABRICATION_PATTERNS = (
    "not provided",
    "please provide",
    "send me the",
    "i need the plan",
    "i don't have access",
    "cannot access the artifact",
)


@dataclass
class ReviewerCandidate:
    provider: str
    model: str
    budget_class: str = "not_logged"
    tool_capable: bool = False
    notes: str = ""

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.model}"


@dataclass
class BenchmarkPacket:
    packet_id: str
    task_family: str
    artifact_name: str
    artifact_content: str
    rubric: list[str]
    expected_issue_markers: list[str] = field(default_factory=list)
    min_citations: int = 2

    @property
    def packet_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ReviewerScore:
    timestamp: str
    run_id: str
    lane_id: str
    task_family: str
    artifact_path: str | None
    artifact_name: str
    provider: str
    model: str
    budget_class: str
    tool_capable: bool
    input_packet_hash: str
    consumed_artifact: bool
    cited_sources: bool
    severity_ranked: bool
    actionable_issues: bool
    fabricated_claims: bool
    found_real_issues_count: int
    actionable_issues_count: int
    useless_output: bool
    status: str
    captain_verdict: str
    promoted_for_roles: list[str] = field(default_factory=list)
    demoted_for_roles: list[str] = field(default_factory=list)
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_packets(path: Path) -> list[BenchmarkPacket]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    packets = raw.get("packets", raw if isinstance(raw, list) else [])
    return [BenchmarkPacket(**packet) for packet in packets]


def write_default_packets(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    packets = [
        BenchmarkPacket(
            packet_id="plan-review-001",
            task_family="plan_review",
            artifact_name="intelligence-autonomy-plan.md",
            artifact_content=(
                "# Plan\n\n"
                "## Config\n"
                "The loop accepts enable_generative_reflection but does not define rollback flags.\n\n"
                "## Verification\n"
                "Tests will be run later. Exact commands are TBD.\n\n"
                "## Telemetry\n"
                "Lanes record status and duration. Timestamp validation is not specified.\n"
            ),
            rubric=["Check config schema", "Check rollback", "Check verification", "Check telemetry"],
            expected_issue_markers=["rollback", "exact commands", "timestamp"],
            min_citations=2,
        ),
        BenchmarkPacket(
            packet_id="implementation-readiness-001",
            task_family="implementation_readiness",
            artifact_name="reviewer-routing-brief.md",
            artifact_content=(
                "# Reviewer Routing Brief\n\n"
                "Cheap reviewers may approve plans. No scorecard fields are defined. "
                "Failures should be logged somewhere. Promotion rules are manual.\n"
            ),
            rubric=["Check scorecard", "Check promotion gates", "Check failure logging"],
            expected_issue_markers=["scorecard", "promotion", "manual"],
            min_citations=2,
        ),
        BenchmarkPacket(
            packet_id="doc-consistency-001",
            task_family="doc_consistency",
            artifact_name="docs-routing.md",
            artifact_content=(
                "# Routing Docs\n\n"
                "Gemma is the default reviewer.\n\n"
                "## Later\n"
                "Gemma is not approved for adversarial review until it passes grounding probes.\n"
            ),
            rubric=["Find contradictions", "Separate default from candidate"],
            expected_issue_markers=["contradiction", "default", "not approved"],
            min_citations=2,
        ),
        BenchmarkPacket(
            packet_id="telemetry-schema-001",
            task_family="telemetry_schema",
            artifact_name="lanes.jsonl",
            artifact_content=(
                '{"lane_id":"review-1","start_time":"2026-07-02T15:50:28+00:00",'
                '"end_time":"2026-07-02T15:46:00+00:00","duration_seconds":25.06}\n'
            ),
            rubric=["Validate timestamp ordering", "Check duration consistency"],
            expected_issue_markers=["end_time", "start_time", "timestamp"],
            min_citations=1,
        ),
        BenchmarkPacket(
            packet_id="code-diff-review-001",
            task_family="code_diff_review",
            artifact_name="diff.patch",
            artifact_content=(
                "diff --git a/router.py b/router.py\n"
                "+def route(role):\n"
                "+    if role == 'reviewer':\n"
                "+        return 'gemma4:latest'\n"
                "+    return 'default'\n"
            ),
            rubric=["Check hard-coded routing", "Check reviewer tier fit"],
            expected_issue_markers=["hard-coded", "reviewer", "tier"],
            min_citations=1,
        ),
    ]
    path.write_text(json.dumps({"packets": [asdict(packet) for packet in packets]}, indent=2) + "\n", encoding="utf-8")


def count_citations(output: str, packet: BenchmarkPacket) -> int:
    lowered = output.lower()
    count = 0
    for token in {packet.artifact_name.lower(), packet.packet_id.lower(), "line", "section", "##", "#"}:
        if token and token in lowered:
            count += 1
    count += len(re.findall(r"\bL(?:ine)?\s*\d+\b", output, flags=re.IGNORECASE))
    count += len(re.findall(r"`[^`]+`", output))
    return count


def score_output(
    *,
    run_id: str,
    lane_id: str,
    candidate: ReviewerCandidate,
    packet: BenchmarkPacket,
    output: str,
    artifact_path: str | None = None,
) -> ReviewerScore:
    lowered = output.lower()
    consumed_artifact = packet.artifact_name.lower() in lowered or packet.packet_id.lower() in lowered
    citation_count = count_citations(output, packet)
    cited_sources = citation_count >= packet.min_citations
    severity_ranked = bool(re.search(r"\b(blocker|high|medium|low|nit|severity)\b", lowered))
    actionable_issues_count = len(re.findall(r"\b(fix|change|add|remove|define|record|validate|route|promote|demote)\b", lowered))
    actionable_issues = actionable_issues_count > 0
    fabricated_claims = any(pattern in lowered for pattern in FABRICATION_PATTERNS)
    found_real_issues_count = sum(1 for marker in packet.expected_issue_markers if marker.lower() in lowered)
    useless_output = len(output.strip()) < 80 or fabricated_claims or not consumed_artifact

    missing = [gate for gate, value in {
        "consumed_artifact": consumed_artifact,
        "cited_sources": cited_sources,
        "severity_ranked": severity_ranked,
        "actionable_issues": actionable_issues,
    }.items() if not value]

    if useless_output or missing:
        status = "quality_failed"
        verdict = f"failed reviewer gates: {', '.join(missing) or 'useless_output'}"
        promoted: list[str] = []
        demoted = ["adversarial_review", "final_blocker_review"]
    elif found_real_issues_count == 0 and packet.expected_issue_markers:
        status = "quality_failed"
        verdict = "grounded shape passed but missed seeded issue markers"
        promoted = []
        demoted = ["adversarial_review"]
    else:
        status = "pass"
        verdict = "passed grounded reviewer gates"
        promoted = [packet.task_family]
        demoted = []

    return ReviewerScore(
        timestamp=utc_now(),
        run_id=run_id,
        lane_id=lane_id,
        task_family=packet.task_family,
        artifact_path=artifact_path,
        artifact_name=packet.artifact_name,
        provider=candidate.provider,
        model=candidate.model,
        budget_class=candidate.budget_class,
        tool_capable=candidate.tool_capable,
        input_packet_hash=packet.packet_hash,
        consumed_artifact=consumed_artifact,
        cited_sources=cited_sources,
        severity_ranked=severity_ranked,
        actionable_issues=actionable_issues,
        fabricated_claims=fabricated_claims,
        found_real_issues_count=found_real_issues_count,
        actionable_issues_count=actionable_issues_count,
        useless_output=useless_output,
        status=status,
        captain_verdict=verdict,
        promoted_for_roles=promoted,
        demoted_for_roles=demoted,
        notes=f"citation_count={citation_count}",
    )


def append_score(path: Path, score: ReviewerScore) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(score), ensure_ascii=False) + "\n")


def load_scores(path: Path) -> list[ReviewerScore]:
    if not path.exists():
        return []
    scores = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            scores.append(ReviewerScore(**json.loads(line)))
    return scores


def reduce_scores(scores: Sequence[ReviewerScore]) -> dict:
    by_model: dict[str, dict] = {}
    for score in scores:
        key = f"{score.provider}/{score.model}"
        row = by_model.setdefault(
            key,
            {
                "provider": score.provider,
                "model": score.model,
                "budget_class": score.budget_class,
                "runs": 0,
                "passes": 0,
                "quality_failed": 0,
                "task_families_passed": {},
                "demoted_for_roles": {},
                "recommendation": "unclassified",
            },
        )
        row["runs"] += 1
        if score.status == "pass":
            row["passes"] += 1
            row["task_families_passed"][score.task_family] = row["task_families_passed"].get(score.task_family, 0) + 1
        if score.status == "quality_failed":
            row["quality_failed"] += 1
        for role in score.demoted_for_roles:
            row["demoted_for_roles"][role] = row["demoted_for_roles"].get(role, 0) + 1

    for row in by_model.values():
        pass_rate = row["passes"] / row["runs"] if row["runs"] else 0.0
        row["pass_rate"] = round(pass_rate, 3)
        if row["runs"] >= 3 and pass_rate >= 0.8:
            row["recommendation"] = "promote_for_passed_task_families"
        elif row["runs"] >= 2 and pass_rate == 0:
            row["recommendation"] = "demote_from_review; clerk_only_until_probe_passes"
        else:
            row["recommendation"] = "candidate_needs_more_evidence"
    return {"models": by_model, "total_scores": len(scores)}


def simulated_output(candidate: ReviewerCandidate, packet: BenchmarkPacket) -> str:
    model = candidate.model.lower()
    if "gemma" in model:
        return "Please provide the plan and artifact so I can review it."
    issue_lines = []
    for idx, marker in enumerate(packet.expected_issue_markers or ["grounding"], start=1):
        severity = "medium" if idx == 1 else "low"
        issue_lines.append(
            f"- severity: {severity}; source: `{packet.artifact_name}` section {idx}; "
            f"issue: {marker} is under-specified; fix: define and validate {marker}."
        )
    return (
        f"Reviewed artifact `{packet.artifact_name}` for packet {packet.packet_id}.\n"
        "Severity-ranked issues:\n"
        + "\n".join(issue_lines)
        + "\nCaptain note: no fabricated external files used."
    )


def run_simulated_bakeoff(run_id: str, packets: Sequence[BenchmarkPacket], scorecard_path: Path) -> list[ReviewerScore]:
    candidates = [
        ReviewerCandidate(provider="custom", model="gemma4:latest", budget_class="cheap", tool_capable=False),
        ReviewerCandidate(provider="custom", model="glm-5.1", budget_class="cheap", tool_capable=True),
    ]
    scores = []
    for candidate in candidates:
        for packet in packets:
            score = score_output(
                run_id=run_id,
                lane_id=f"{candidate.model}:{packet.packet_id}",
                candidate=candidate,
                packet=packet,
                output=simulated_output(candidate, packet),
            )
            append_score(scorecard_path, score)
            scores.append(score)
    return scores


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or reduce reviewer route bake-off scorecards.")
    parser.add_argument("--packets", type=Path, default=Path("docs/benchmarks/reviewer-bakeoff-packets.json"))
    parser.add_argument("--scorecard", type=Path, default=Path.home() / ".shay/runtime/model-routing/reviewer-scorecard.jsonl")
    parser.add_argument("--summary", type=Path, default=Path.home() / ".shay/runtime/model-routing/reviewer-summary.json")
    parser.add_argument("--run-id", default=f"reviewer-bakeoff-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}")
    parser.add_argument("--write-default-packets", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--reduce", action="store_true")
    args = parser.parse_args(argv)

    if args.write_default_packets:
        write_default_packets(args.packets)
    packets = load_packets(args.packets)
    if args.simulate:
        run_simulated_bakeoff(args.run_id, packets, args.scorecard)
    if args.reduce or args.simulate:
        summary = reduce_scores(load_scores(args.scorecard))
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
