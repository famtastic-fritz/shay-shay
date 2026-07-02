from pathlib import Path

from agent.ambient_context import LocalArtifactConnector, ProcessSnapshotConnector, collect_ambient_context
from agent.intelligence_governance import (
    IntelligenceLoopConfig,
    decide_pointer_promotions,
    run_generative_reflection,
    stage_capability_reconciliation,
)


class GoodClient:
    def synthesize(self, packet):
        return {"l2_claims": [{"claim": "x", "confidence": 0.9, "sources": ["a"], "tags": ["t"]}], "l3_patterns": []}


class BadClient:
    def synthesize(self, packet):
        raise RuntimeError("boom")


def test_generative_reflection_disabled_falls_back():
    result = run_generative_reflection({}, IntelligenceLoopConfig(generative_reflection_enabled=False), GoodClient())
    assert result["mode"] == "deterministic_fallback"
    assert result["l2_claims"] == []


def test_generative_reflection_enabled_schema_output():
    cfg = IntelligenceLoopConfig(generative_reflection_enabled=True, generative_provider="test", generative_model="reviewer")
    result = run_generative_reflection({}, cfg, GoodClient())
    assert result["mode"] == "generative_candidate"
    assert result["provider"] == "test"
    assert len(result["l2_claims"]) == 1


def test_generative_reflection_provider_error_falls_back():
    cfg = IntelligenceLoopConfig(generative_reflection_enabled=True)
    result = run_generative_reflection({}, cfg, BadClient())
    assert result["mode"] == "deterministic_fallback"
    assert "boom" in result["error"]


def test_pointer_promotion_auto_promotes_only_low_risk_multi_source():
    cfg = IntelligenceLoopConfig(pointer_min_confidence=0.85, pointer_min_independent_sources=2)
    candidates = [
        {"entry": "Reflection source pointer: /tmp/a.md", "source": "/tmp/a.md", "source_tag": "reflection:l2", "preferred_tool": "read_file", "confidence": 0.9},
        {"entry": "Generated pointer candidate: /tmp/a.md", "source": "/tmp/a.md", "source_tag": "reflection:l3", "preferred_tool": "read_file", "confidence": 0.91},
        {"entry": "SOUL pointer", "source": "/tmp/soul.md", "source_tag": "reflection:l2", "preferred_tool": "read_file", "confidence": 0.99},
    ]
    decisions = decide_pointer_promotions(candidates, cfg)
    by_source = {d.source: d for d in decisions}
    assert by_source["/tmp/a.md"].action == "auto_promote"
    assert by_source["/tmp/soul.md"].action == "review"
    assert by_source["/tmp/soul.md"].risk == "high"


def test_capability_reconciliation_never_directly_mutates(tmp_path: Path):
    out = tmp_path / "capabilities.jsonl"
    result = stage_capability_reconciliation([{"capability_id": "x", "confidence": 0.9}], out, IntelligenceLoopConfig(capability_auto_mutation_enabled=True))
    assert result["direct_mutation"] is False
    assert out.exists()
    assert "stage_patch" in out.read_text()


def test_ambient_context_disable_and_local_collect(tmp_path: Path):
    source = tmp_path / "note.md"
    source.write_text("Fritz prefers proof-backed work.", encoding="utf-8")
    disabled = collect_ambient_context([LocalArtifactConnector((source,)), ProcessSnapshotConnector()], enabled=False)
    enabled = collect_ambient_context([LocalArtifactConnector((source,))], enabled=True)
    assert disabled == []
    assert enabled[0]["source"] == str(source)
    assert enabled[0]["ttl_seconds"] == 3600
