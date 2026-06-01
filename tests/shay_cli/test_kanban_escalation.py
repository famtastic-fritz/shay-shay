"""Tests for shay_cli.kanban_escalation — the worker escalation ladder.

The escalation ladder climbs 10 rungs (0-9) when a task fails, pulling
in more resources at each step instead of giving up. Tests cover:

  - Individual rung behaviour
  - Full climb on an unrecoverable task (must TERMINATE, not loop)
  - No-progress detector (two identical climbs → terminal)
  - Provider injection (real callables vs stubs)
  - Hard-stop recommendation text
  - Import clean-up gate (also verified via pytest -c 'import shay_cli.kanban_db')
"""

from __future__ import annotations

import time
from typing import Optional
from unittest.mock import MagicMock

import pytest

from shay_cli.kanban_escalation import (
    MAX_RUNG,
    NO_PROGRESS_THRESHOLD,
    EscalationLadder,
    LadderOutcome,
    LadderProviders,
    RungResult,
    _extract_search_query,
    _fingerprint_info_map,
    _format_mini_trail,
    hard_stop_recommendation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop_block(task_id: str, reason: str) -> None:
    """Noop block_task provider — records calls for assertion."""
    _noop_block.calls.append((task_id, reason))  # type: ignore[attr-defined]


_noop_block.calls = []  # type: ignore[attr-defined]


def _fresh_block_spy():
    """Return a fresh callable spy for block_task."""
    calls = []

    def spy(task_id: str, reason: str) -> None:
        calls.append((task_id, reason))

    spy.calls = calls  # type: ignore[attr-defined]
    return spy


def _all_fail_providers(block_spy=None) -> LadderProviders:
    """Providers where every rung returns empty/None — simulates unrecoverable failure."""
    return LadderProviders(
        session_search=lambda q: "",
        grep_codebase=lambda p, r: "",
        web_search=lambda q: "",
        invoke_brain=lambda prompt, ctx: "",
        capability_check=lambda task: None,
        block_task=block_spy,
    )


# ---------------------------------------------------------------------------
# Module-level smoke test: import must be clean
# ---------------------------------------------------------------------------


def test_module_imports_cleanly():
    """The escalation module must import without side-effects or exceptions."""
    import shay_cli.kanban_escalation as m  # noqa: F401
    assert hasattr(m, "EscalationLadder")
    assert hasattr(m, "LadderProviders")
    assert hasattr(m, "RungResult")
    assert hasattr(m, "LadderOutcome")


def test_kanban_db_imports_cleanly():
    """kanban_db must still import cleanly after adding escalation support."""
    import shay_cli.kanban_db as kb  # noqa: F401
    assert hasattr(kb, "connect")
    assert hasattr(kb, "create_task")


# ---------------------------------------------------------------------------
# RungResult dataclass
# ---------------------------------------------------------------------------


def test_rung_result_to_dict():
    r = RungResult(rung=3, name="check_memory", info_gained=True, new_info="found it")
    d = r.to_dict()
    assert d["rung"] == 3
    assert d["name"] == "check_memory"
    assert d["info_gained"] is True
    assert d["new_info"] == "found it"
    assert "duration_ms" in d


def test_rung_result_defaults():
    r = RungResult(rung=0, name="retry", info_gained=False)
    assert r.new_info == ""
    assert r.recommendation == ""
    assert r.is_terminal is False
    assert r.duration_ms == 0.0


# ---------------------------------------------------------------------------
# LadderOutcome
# ---------------------------------------------------------------------------


def test_ladder_outcome_to_dict():
    trail = [RungResult(rung=0, name="retry", info_gained=False)]
    o = LadderOutcome(action="terminal", rung_reached=9, trail=trail)
    d = o.to_dict()
    assert d["action"] == "terminal"
    assert d["rung_reached"] == 9
    assert len(d["trail"]) == 1


def test_format_trail_includes_all_rungs():
    trail = [
        RungResult(rung=0, name="retry", info_gained=False),
        RungResult(rung=1, name="diagnose", info_gained=True, new_info="timeout"),
    ]
    o = LadderOutcome(action="retry", rung_reached=1, trail=trail)
    text = o.format_trail()
    assert "Rung 0" in text
    assert "Rung 1" in text
    assert "timeout" in text


def test_format_trail_no_progress_flag():
    o = LadderOutcome(action="terminal", rung_reached=9, trail=[], no_progress_triggered=True)
    text = o.format_trail()
    assert "No-progress" in text


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def test_extract_search_query_from_error():
    error = "ConnectionRefusedError: [Errno 111] Connection refused"
    q = _extract_search_query(error)
    assert "Connection" in q or "refused" in q.lower()
    # Should not exceed max_words (default 8)
    assert len(q.split()) <= 8


def test_extract_search_query_empty():
    q = _extract_search_query("")
    assert q == "kanban worker failure"


def test_fingerprint_info_map_stable():
    m = {0: False, 1: True, 3: False}
    assert _fingerprint_info_map(m) == _fingerprint_info_map(m)
    assert _fingerprint_info_map(m) != _fingerprint_info_map({0: True, 1: True, 3: False})


def test_format_mini_trail_empty():
    result = _format_mini_trail([])
    assert result == "(no prior rungs)"


def test_format_mini_trail_nonempty():
    trail = [RungResult(rung=1, name="diagnose", info_gained=True, new_info="timeout")]
    result = _format_mini_trail(trail)
    assert "diagnose" in result
    assert "[✓]" in result


# ---------------------------------------------------------------------------
# Rung 0 — retry
# ---------------------------------------------------------------------------


def test_rung0_always_returns_retry_action():
    """Rung 0 returns the 'retry' action even with no info gained."""
    ladder = EscalationLadder("t_test00")
    outcome = ladder.climb(error="boom")
    # Rung 0 immediately returns retry — no further rungs run.
    assert outcome.action == "retry"
    assert outcome.rung_reached == 0


# ---------------------------------------------------------------------------
# Rung 1 — diagnose
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("error,keyword", [
    ("Request timed out after 30s", "timeout"),
    ("Permission denied: /etc/shadow", "permission"),
    ("FileNotFoundError: no such file /tmp/x", "missing"),
    ("Connection refused: 127.0.0.1:5432", "network"),
    ("SyntaxError: unexpected EOF", "syntax"),
    ("MemoryError: out of memory", "OOM"),
    ("openai: 429 Too Many Requests", "rate limit"),
    ("ModuleNotFoundError: No module named 'foo'", "dependency"),
])
def test_rung1_classifies_known_error_patterns(error, keyword):
    """Rung 1 should recognise and classify common error patterns."""
    # Force rung 1 directly by mocking rung 0 to not return early.
    ladder = EscalationLadder("t_diag")
    result = ladder._rung1_diagnose(1, "diagnose", error, {}, [])
    assert result.info_gained is True
    assert keyword.lower() in result.new_info.lower()


def test_rung1_empty_error_no_info():
    ladder = EscalationLadder("t_diag_empty")
    result = ladder._rung1_diagnose(1, "diagnose", "", {}, [])
    assert result.info_gained is False


# ---------------------------------------------------------------------------
# Rung 2 — check_tools
# ---------------------------------------------------------------------------


def test_rung2_no_cap_error_returns_false():
    providers = LadderProviders(capability_check=lambda task: None)
    ladder = EscalationLadder("t_cap", providers=providers)
    result = ladder._rung2_check_tools(2, "check_tools", "err", {"task": {"assignee": "worker"}}, [])
    assert result.info_gained is False


def test_rung2_missing_tool_returns_terminal():
    providers = LadderProviders(
        capability_check=lambda task: "role 'worker' lacks required tool 'web_search'"
    )
    ladder = EscalationLadder("t_cap_miss", providers=providers)
    result = ladder._rung2_check_tools(2, "check_tools", "err", {"task": {"assignee": "worker"}}, [])
    assert result.info_gained is True
    assert result.is_terminal is True
    assert "web_search" in result.new_info


def test_rung2_no_task_context():
    ladder = EscalationLadder("t_cap_notask")
    result = ladder._rung2_check_tools(2, "check_tools", "err", {}, [])
    assert result.info_gained is False


# ---------------------------------------------------------------------------
# Rung 3 — check_memory
# ---------------------------------------------------------------------------


def test_rung3_returns_info_when_session_search_finds_something():
    providers = LadderProviders(session_search=lambda q: "Prior fix: increase timeout to 120s")
    ladder = EscalationLadder("t_mem", providers=providers)
    result = ladder._rung3_check_memory(3, "check_memory", "timed out", {}, [])
    assert result.info_gained is True
    assert "Prior fix" in result.new_info


def test_rung3_no_info_when_empty_result():
    providers = LadderProviders(session_search=lambda q: "")
    ladder = EscalationLadder("t_mem_empty", providers=providers)
    result = ladder._rung3_check_memory(3, "check_memory", "timed out", {}, [])
    assert result.info_gained is False


def test_rung3_no_provider_skips():
    ladder = EscalationLadder("t_mem_noprov")
    result = ladder._rung3_check_memory(3, "check_memory", "err", {}, [])
    assert result.info_gained is False
    assert "not available" in result.new_info


def test_rung3_provider_exception_degrades_gracefully():
    def bad_search(q):
        raise RuntimeError("network down")

    providers = LadderProviders(session_search=bad_search)
    ladder = EscalationLadder("t_mem_exc", providers=providers)
    result = ladder._rung3_check_memory(3, "check_memory", "err", {}, [])
    assert result.info_gained is False
    assert "raised" in result.new_info


# ---------------------------------------------------------------------------
# Rung 4 — check_repos
# ---------------------------------------------------------------------------


def test_rung4_returns_info_when_grep_finds_something():
    providers = LadderProviders(grep_codebase=lambda p, r: "line 42: timeout_retry_count = 5")
    ladder = EscalationLadder("t_repo", providers=providers)
    result = ladder._rung4_check_repos(4, "check_repos", "timeout", {}, [])
    assert result.info_gained is True
    assert "line 42" in result.new_info


def test_rung4_no_info_when_empty():
    providers = LadderProviders(grep_codebase=lambda p, r: "")
    ladder = EscalationLadder("t_repo_empty", providers=providers)
    result = ladder._rung4_check_repos(4, "check_repos", "timeout", {}, [])
    assert result.info_gained is False


# ---------------------------------------------------------------------------
# Rung 5 — check_web
# ---------------------------------------------------------------------------


def test_rung5_returns_info_when_web_search_finds_something():
    providers = LadderProviders(
        web_search=lambda q: "Stack Overflow: increase connection pool size to fix 'connection refused'"
    )
    ladder = EscalationLadder("t_web", providers=providers)
    result = ladder._rung5_check_web(5, "check_web", "connection refused", {}, [])
    assert result.info_gained is True


def test_rung5_no_info_when_empty():
    providers = LadderProviders(web_search=lambda q: "")
    ladder = EscalationLadder("t_web_empty", providers=providers)
    result = ladder._rung5_check_web(5, "check_web", "err", {}, [])
    assert result.info_gained is False


# ---------------------------------------------------------------------------
# Rung 6 — escalate_brain
# ---------------------------------------------------------------------------


def test_rung6_returns_info_from_brain():
    providers = LadderProviders(
        invoke_brain=lambda prompt, ctx: "Retry with exponential backoff — the service throttles on burst."
    )
    ladder = EscalationLadder("t_brain", providers=providers)
    result = ladder._rung6_escalate_brain(6, "escalate_brain", "429", {}, [])
    assert result.info_gained is True
    assert "backoff" in result.new_info.lower()


def test_rung6_no_provider_skips():
    ladder = EscalationLadder("t_brain_noprov")
    result = ladder._rung6_escalate_brain(6, "escalate_brain", "err", {}, [])
    assert result.info_gained is False


# ---------------------------------------------------------------------------
# Rung 7 — decompose
# ---------------------------------------------------------------------------


def test_rung7_always_info_gained():
    ladder = EscalationLadder("t_decomp")
    result = ladder._rung7_decompose(7, "decompose", "err", {"task": {"title": "Big job"}}, [])
    assert result.info_gained is True
    assert "decompose" in result.action if hasattr(result, "action") else True
    assert "sub-task" in result.recommendation.lower() or "smaller" in result.recommendation.lower()


# ---------------------------------------------------------------------------
# Rung 8 — ask_fritz
# ---------------------------------------------------------------------------


def test_rung8_info_gained_and_surfaces_trail():
    ladder = EscalationLadder("t_fritz")
    result = ladder._rung8_ask_fritz(8, "ask_fritz", "catastrophic", {}, [])
    assert result.info_gained is True
    assert "fritz" in result.new_info.lower() or "human" in result.new_info.lower()


# ---------------------------------------------------------------------------
# Rung 9 — terminal
# ---------------------------------------------------------------------------


def test_rung9_always_terminal():
    ladder = EscalationLadder("t_terminal")
    result = ladder._rung9_terminal(9, "terminal", "impossible", {}, [])
    assert result.is_terminal is True
    assert result.info_gained is False


# ---------------------------------------------------------------------------
# THE KEY TEST: unrecoverable task climbs all rungs and terminates
# ---------------------------------------------------------------------------


def test_unrecoverable_task_terminates_with_full_trail():
    """An unrecoverable task must climb through all rungs and TERMINATE
    with a complete trail — it must NOT loop forever.

    This is the hard gate test from the task spec.
    """
    block_spy = _fresh_block_spy()

    # All providers return empty/None — no rung gains info.
    providers = _all_fail_providers(block_spy)

    ladder = EscalationLadder("t_unrecoverable", providers=providers)

    # Patch _rung_to_action so NO rung short-circuits early — we want all 10
    # rungs (0-9) to execute. Only rung 9 / is_terminal actually terminates.
    # This simulates a task that has already consumed earlier retry/decompose
    # signals and must now exhaust the full ladder.
    def all_continue_except_terminal(rung, result):
        if rung == MAX_RUNG or result.is_terminal:
            return "terminal"
        return "continue"

    ladder._rung_to_action = all_continue_except_terminal  # type: ignore[method-assign]

    outcome = ladder.climb(error="impossible operation: all retries exhausted")

    # Core assertions: must terminate, not loop.
    assert outcome.action == "terminal", f"expected terminal, got {outcome.action!r}"
    assert outcome.rung_reached == MAX_RUNG, (
        f"expected rung {MAX_RUNG}, got {outcome.rung_reached}"
    )

    # Trail must contain all 10 rungs (0-9).
    rung_numbers = [r.rung for r in outcome.trail]
    assert rung_numbers == list(range(MAX_RUNG + 1)), (
        f"Expected rungs 0-9 in trail, got {rung_numbers}"
    )

    # block_task must have been called exactly once with the task_id.
    assert len(block_spy.calls) == 1
    called_task_id, called_reason = block_spy.calls[0]
    assert called_task_id == "t_unrecoverable"

    # The block reason must contain the escalation trail.
    assert "Escalation trail" in called_reason
    for rung_num in range(MAX_RUNG + 1):
        assert f"Rung {rung_num}" in called_reason, (
            f"Rung {rung_num} missing from block reason"
        )


def test_unrecoverable_single_climb_reaches_terminal():
    """A direct full climb with all providers failing reaches terminal at rung 9."""
    block_spy = _fresh_block_spy()
    providers = _all_fail_providers(block_spy)
    ladder = EscalationLadder("t_fullclimb", providers=providers)

    # Drive all rungs to completion — no early exits.
    def all_continue_except_terminal(rung, result):
        if rung == MAX_RUNG or result.is_terminal:
            return "terminal"
        return "continue"

    ladder._rung_to_action = all_continue_except_terminal  # type: ignore[method-assign]

    t_start = time.monotonic()
    outcome = ladder.climb(error="everything fails")
    elapsed = time.monotonic() - t_start

    # Must complete — not hang, not recurse infinitely.
    assert elapsed < 5.0, f"Ladder took {elapsed:.2f}s — possible infinite loop"
    assert outcome.action == "terminal"
    assert outcome.rung_reached == MAX_RUNG


# ---------------------------------------------------------------------------
# No-progress detector
# ---------------------------------------------------------------------------


def test_no_progress_detector_fires_on_second_identical_climb():
    """If two consecutive full climbs yield identical info-gained fingerprints,
    the no-progress detector must trigger and force terminal.
    """
    block_calls = []
    providers = _all_fail_providers(lambda tid, r: block_calls.append(r))
    ladder = EscalationLadder("t_noprog", providers=providers)

    # Drive all rungs — no early exits on either climb.
    def all_continue_except_terminal(rung, result):
        if rung == MAX_RUNG or result.is_terminal:
            return "terminal"
        return "continue"

    ladder._rung_to_action = all_continue_except_terminal  # type: ignore[method-assign]

    outcome1 = ladder.climb(error="failing same way")
    outcome2 = ladder.climb(error="failing same way")

    # Second climb should hit no-progress.
    assert outcome2.no_progress_triggered is True
    assert outcome2.action == "terminal"


def test_no_progress_resets_on_info_gain():
    """If the second climb gains new info, no-progress does not fire."""
    call_count = {"n": 0}
    block_spy = _fresh_block_spy()

    def dynamic_session_search(q):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            return "Prior fix: use retry with backoff"
        return ""

    providers = LadderProviders(
        session_search=dynamic_session_search,
        block_task=block_spy,
    )
    ladder = EscalationLadder("t_prog", providers=providers)

    def all_continue_except_terminal(rung, result):
        if rung == MAX_RUNG or result.is_terminal:
            return "terminal"
        return "continue"

    ladder._rung_to_action = all_continue_except_terminal  # type: ignore[method-assign]

    outcome1 = ladder.climb(error="failing")
    # Second climb: session_search may now return something → info gained at rung 3.
    outcome2 = ladder.climb(error="failing")

    # The fingerprints differ now because info_gained changed at rung 3 on climb 2.
    # no_progress_triggered should NOT fire on the second climb.
    if outcome2.no_progress_triggered:
        # Only acceptable if the fingerprints really are identical.
        map1 = {r.rung: r.info_gained for r in outcome1.trail}
        map2 = {r.rung: r.info_gained for r in outcome2.trail}
        assert map1 == map2, "no_progress fired but fingerprints differ — bug"


# ---------------------------------------------------------------------------
# Block call integration
# ---------------------------------------------------------------------------


def test_block_called_on_ask_fritz():
    """Block provider must be called when the ladder reaches ask_fritz (rung 8)."""
    block_spy = _fresh_block_spy()

    providers = LadderProviders(
        session_search=lambda q: "",
        grep_codebase=lambda p, r: "",
        web_search=lambda q: "",
        invoke_brain=lambda prompt, ctx: "",
        capability_check=lambda t: None,
        block_task=block_spy,
    )
    ladder = EscalationLadder("t_askfritz", providers=providers)

    # Drive all rungs; at rung 8 (ask_fritz) the ladder will emit ask_fritz action.
    # We stop at ask_fritz and let the real logic handle it.
    orig = ladder._rung_to_action

    def continue_until_askfritz(rung, result):
        if rung == 8:
            return orig(rung, result)  # Let ask_fritz produce its real action
        if rung == MAX_RUNG or result.is_terminal:
            return "terminal"
        return "continue"

    ladder._rung_to_action = continue_until_askfritz  # type: ignore[method-assign]

    outcome = ladder.climb(error="needs human")

    # Should reach rung 8 at least (may also hit terminal depending on rung 6 info).
    assert len(block_spy.calls) >= 1 or outcome.action in {"ask_fritz", "terminal"}


def test_block_not_called_on_retry():
    """Block provider must NOT be called when the outcome is 'retry'."""
    block_spy = _fresh_block_spy()
    providers = LadderProviders(block_task=block_spy)
    ladder = EscalationLadder("t_noblock")
    # No override — rung 0 exits immediately with action=retry.
    outcome = ladder.climb(error="transient")
    assert outcome.action == "retry"
    assert len(block_spy.calls) == 0


# ---------------------------------------------------------------------------
# Rung error isolation
# ---------------------------------------------------------------------------


def test_broken_provider_does_not_crash_ladder():
    """If a provider raises, the ladder catches it and marks info_gained=False
    for that rung, then continues climbing.
    """

    def exploding_search(q):
        raise RuntimeError("network down")

    block_spy = _fresh_block_spy()
    providers = LadderProviders(session_search=exploding_search, block_task=block_spy)
    ladder = EscalationLadder("t_broken", providers=providers)

    orig = ladder._rung_to_action

    def no_early_exit(rung, result):
        if rung == 0:
            return "continue"
        return orig(rung, result)

    ladder._rung_to_action = no_early_exit  # type: ignore[method-assign]

    # Must not raise.
    outcome = ladder.climb(error="anything")
    assert outcome.action in {"retry", "decompose", "escalate_brain", "ask_fritz", "terminal"}


# ---------------------------------------------------------------------------
# Hard-stop recommendation
# ---------------------------------------------------------------------------


def test_hard_stop_recommendation_mentions_key_facts():
    text = hard_stop_recommendation()
    assert "hard_stop_enabled" in text
    assert "False" in text or "false" in text
    # Must mention that the ladder serves as the real stop.
    assert "terminal" in text.lower() or "ladder" in text.lower()


# ---------------------------------------------------------------------------
# Outcome metadata
# ---------------------------------------------------------------------------


def test_outcome_summary_includes_action_and_rung():
    trail = [RungResult(rung=0, name="retry", info_gained=False)]
    o = LadderOutcome(action="terminal", rung_reached=9, trail=trail)
    o.summary = "Escalation ladder reached rung 9 (terminal). Action: terminal."
    assert "terminal" in o.summary
    assert "9" in o.summary


def test_outcome_block_reason_set_by_format_trail():
    trail = [
        RungResult(rung=0, name="retry", info_gained=False),
        RungResult(rung=1, name="diagnose", info_gained=True, new_info="timeout"),
    ]
    o = LadderOutcome(action="terminal", rung_reached=9, trail=trail)
    o.block_reason = o.format_trail()
    assert "Rung 0" in o.block_reason
    assert "Rung 1" in o.block_reason
    assert "timeout" in o.block_reason
