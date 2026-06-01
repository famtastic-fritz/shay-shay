"""Tests for the trace-grounded curator review (Feature 2).

The trace-grounded path is additive and gated behind ``curator.trace_grounded``
(default False). These tests verify:
  - is_trace_grounded() reads config and defaults False
  - _render_candidate_list() is backward compatible when off, and adds the
    measured-evidence columns when on
  - the trace-grounding preamble is prepended to the LLM prompt only when on
  - the base review behavior is unchanged when off
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def curator_env(tmp_path, monkeypatch):
    home = tmp_path / ".shay"
    (home / "skills").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SHAY_HOME", str(home))

    import tools.skill_usage as usage
    importlib.reload(usage)
    import agent.curator as curator
    importlib.reload(curator)

    monkeypatch.setattr(curator, "_load_config", lambda: {})
    return {"home": home, "curator": curator, "usage": usage}


def _write_skill(skills_dir: Path, name: str):
    d = skills_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: x\n---\n", encoding="utf-8",
    )
    return d


def _seed_agent_skill(u, skills_dir, name):
    _write_skill(skills_dir, name)
    now = datetime.now(timezone.utc).isoformat()
    data = u.load_usage()
    rec = u._empty_record()
    rec["created_by"] = "agent"
    rec["created_at"] = now
    rec["last_used_at"] = now
    rec["use_count"] = 3
    data[name] = rec
    u.save_usage(data)


# --------------------------------------------------------------------------
# config gate
# --------------------------------------------------------------------------

def test_trace_grounded_defaults_false(curator_env):
    assert curator_env["curator"].is_trace_grounded() is False


def test_trace_grounded_reads_config(curator_env, monkeypatch):
    c = curator_env["curator"]
    monkeypatch.setattr(c, "_load_config", lambda: {"trace_grounded": True})
    assert c.is_trace_grounded() is True


# --------------------------------------------------------------------------
# candidate list rendering
# --------------------------------------------------------------------------

def test_candidate_list_backward_compatible_when_off(curator_env):
    c = curator_env["curator"]
    u = curator_env["usage"]
    _seed_agent_skill(u, curator_env["home"] / "skills", "alpha")

    out = c._render_candidate_list(trace_grounded=False)
    assert "alpha" in out
    assert "use=3" in out
    # No trace columns when off.
    assert "win_loads=" not in out
    assert "win_cost=" not in out


def test_candidate_list_adds_trace_columns_when_on(curator_env, monkeypatch):
    c = curator_env["curator"]
    u = curator_env["usage"]
    _seed_agent_skill(u, curator_env["home"] / "skills", "alpha")

    # Stub the DB-backed trace builder so the test stays offline and
    # deterministic (no real SessionDB needed).
    monkeypatch.setattr(
        c, "_trace_evidence_by_skill",
        lambda days=30: {"alpha": {"win_loads": 7, "win_edits": 2, "win_cost": 0.42}},
    )
    out = c._render_candidate_list(trace_grounded=True)
    assert "alpha" in out
    assert "use=3" in out          # base columns still present
    assert "win_loads=7" in out
    assert "win_edits=2" in out
    assert "win_cost=$0.42" in out


def test_candidate_list_missing_evidence_shows_question_mark(curator_env, monkeypatch):
    c = curator_env["curator"]
    u = curator_env["usage"]
    _seed_agent_skill(u, curator_env["home"] / "skills", "alpha")
    # No evidence row for alpha → win_cost unknown.
    monkeypatch.setattr(c, "_trace_evidence_by_skill", lambda days=30: {})
    out = c._render_candidate_list(trace_grounded=True)
    assert "win_loads=0" in out
    assert "win_cost=?" in out


# --------------------------------------------------------------------------
# prompt assembly
# --------------------------------------------------------------------------

def test_review_prompt_includes_preamble_when_on(curator_env, monkeypatch):
    c = curator_env["curator"]
    u = curator_env["usage"]
    _seed_agent_skill(u, curator_env["home"] / "skills", "alpha")
    monkeypatch.setattr(c, "_load_config", lambda: {"trace_grounded": True})
    monkeypatch.setattr(c, "_trace_evidence_by_skill", lambda days=30: {})

    captured = {}

    def _fake_review(prompt):
        captured["prompt"] = prompt
        return {"final": "", "summary": "ok", "model": "m", "provider": "p",
                "tool_calls": [], "error": None}

    monkeypatch.setattr(c, "_run_llm_review", _fake_review)
    c.run_curator_review(synchronous=True, dry_run=True)

    assert "TRACE-GROUNDED REVIEW" in captured["prompt"]
    # Base review prompt is still there (additive, not replaced).
    assert "UMBRELLA-BUILDING" in captured["prompt"]


def test_review_prompt_omits_preamble_when_off(curator_env, monkeypatch):
    c = curator_env["curator"]
    u = curator_env["usage"]
    _seed_agent_skill(u, curator_env["home"] / "skills", "alpha")
    monkeypatch.setattr(c, "_load_config", lambda: {})  # trace_grounded default False

    captured = {}

    def _fake_review(prompt):
        captured["prompt"] = prompt
        return {"final": "", "summary": "ok", "model": "m", "provider": "p",
                "tool_calls": [], "error": None}

    monkeypatch.setattr(c, "_run_llm_review", _fake_review)
    c.run_curator_review(synchronous=True, dry_run=True)

    assert "TRACE-GROUNDED REVIEW" not in captured["prompt"]
    assert "win_loads=" not in captured["prompt"]
    assert "UMBRELLA-BUILDING" in captured["prompt"]
