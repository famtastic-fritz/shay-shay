from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "research_capture.py"


def test_research_capture_writes_artifact_ledger_and_registry(tmp_path):
    research_root = tmp_path / "research"
    ledger = research_root / "_ledger" / "research-artifacts.jsonl"
    registry = research_root / "_ledger" / "research-registry.jsonl"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--title",
        "Research memory closed loop",
        "--summary",
        "Build a reusable research-memory loop.",
        "--question",
        "How should Shay prevent duplicate research?",
        "--observation",
        "The current system has durable research artifacts.",
        "--interpretation",
        "A preflight layer is still missing.",
        "--capability",
        "Can write reusable markdown research notes.",
        "--source",
        "repo|https://github.com/famtastic-fritz/shay-shay|url|implementation repo",
        "--next-action",
        "Add a preflight helper.",
        "--freshness",
        "current",
        "--verdict",
        "partial",
        "--related-topic",
        "duplicate research",
        "--tag",
        "memory",
        "--output-dir",
        str(research_root),
        "--ledger",
        str(ledger),
        "--registry",
        str(registry),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    stdout_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    artifact_path = Path(stdout_lines[0])

    assert artifact_path.exists()
    content = artifact_path.read_text(encoding="utf-8")
    assert "## Observations" in content
    assert "## Interpretations" in content
    assert "freshness: current" in content
    assert "verdict: partial" in content
    assert "related topics: duplicate research" in content

    ledger_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(ledger_rows) == 1
    assert ledger_rows[0]["freshness"] == "current"
    assert ledger_rows[0]["verdict"] == "partial"
    assert ledger_rows[0]["related_topics"] == ["duplicate research"]

    registry_rows = [json.loads(line) for line in registry.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(registry_rows) == 1
    assert registry_rows[0]["topic_key"] == "research-memory-closed-loop"
    assert registry_rows[0]["path"] == str(artifact_path)
    assert registry_rows[0]["verdict"] == "partial"


def test_research_capture_requires_observation_and_interpretation(tmp_path):
    research_root = tmp_path / "research"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--title",
        "Incomplete artifact",
        "--summary",
        "Missing evidence.",
        "--question",
        "What broke?",
        "--output-dir",
        str(research_root),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 2
    assert "at least one --observation is required" in result.stderr
