import json
from pathlib import Path

from agent.intelligence_loop import (
    build_capability_proposals,
    build_pointer_candidates,
    build_session_context,
    run_intelligence_loop_slices,
    synthesize_reflection,
)
from agent.intelligence_prefetch import build_intelligence_prefetch


def test_synthesize_reflection_builds_l2_l3_candidates():
    result = synthesize_reflection({
        "gap.md": "Fritz has a recurring GoDaddy billing gap. Shay should keep proof before claiming completion."
    })

    assert result["mode"] == "local_synthesis"
    assert result["l2_claims"]
    assert result["l3_patterns"]
    assert "generated_at" in result


def test_pointer_candidates_are_review_gated_from_reflection_sources(tmp_path):
    source = tmp_path / "MEMORY-DETAILS.md"
    reflection = {
        "l2_claims": [{
            "claim": "Fritz prefers pointer memory.",
            "confidence": 0.88,
            "sources": [str(source)],
            "tags": ["fritz", "memory"],
        }],
        "l3_patterns": [],
    }

    candidates = build_pointer_candidates(reflection)

    assert candidates[0].source == str(source)
    assert candidates[0].source_tag == "reflection:l2"
    assert candidates[0].preferred_tool == "read_file"


def test_capability_proposals_stay_review_required():
    proposals = build_capability_proposals({
        "proof.md": "capability-prefetch passed with verifier evidence."
    })

    assert proposals
    assert proposals[0].capability_id == "capability-prefetch"
    assert proposals[0].proposed_status == "proven_live"
    assert proposals[0].review_required is True


def test_session_context_items_are_session_search_hinted():
    items = build_session_context({
        "session-1.md": "Fritz asked about billing. Shay found the prior gap note."
    })

    assert items[0].preferred_tool == "session_search"
    assert "billing" in items[0].summary.lower()


def test_run_intelligence_loop_slices_writes_all_artifacts(tmp_path):
    source = tmp_path / "source.md"
    output = tmp_path / "out"
    source.write_text(
        "Fritz has a memory pointer gap. capability-prefetch passed. "
        "Ledger: /tmp/example.md",
        encoding="utf-8",
    )

    closeout = run_intelligence_loop_slices([source], output)

    assert closeout["status"] == "completed"
    for artifact in closeout["slices"].values():
        if artifact.endswith(".json"):
            assert Path(artifact).exists()
    assert closeout["counts"]["sources"] == 1
    assert closeout["governance"].startswith("proposal-only")


def test_prefetch_loads_generated_loop_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    reflections = tmp_path / "famtastic" / "obsidian" / "Shay-Memory" / "reflections"
    reflections.mkdir(parents=True)
    (reflections / "reflection-synthesis.json").write_text(
        json.dumps({"l2_claims": [{"claim": "GoDaddy billing context exists"}]}),
        encoding="utf-8",
    )

    block = build_intelligence_prefetch("billing", home=tmp_path)

    assert "reflection synthesis" in block
    assert "GoDaddy billing context exists" in block
