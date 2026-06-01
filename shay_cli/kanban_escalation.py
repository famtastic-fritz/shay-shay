"""Escalation ladder for kanban workers.

When a worker task fails, instead of giving up immediately the escalation
ladder climbs through increasingly expensive recovery strategies — pulling in
more information at each rung — until either the task can be retried with
new context or all options are exhausted and the worker must block with a
full audit trail.

Rungs (0-9):
  0  retry        — simple re-attempt with the same approach
  1  diagnose     — parse the real error text, form a hypothesis
  2  check_tools  — verify required tools/caps are available (reuses the
                    dispatcher's capability-check logic)
  3  check_memory — search buglog, lessons, and prior session memos for
                    the error signature
  4  check_repos  — grep the local codebase for working prior art
  5  check_web    — web-search the error or approach
  6  escalate_brain — switch to a stronger/different model for one attempt
  7  decompose    — break the task into smaller sub-units
  8  ask_fritz    — pause and surface the full trail to the human owner
  9  terminal     — block with the complete escalation trail; only reached
                    when ALL prior rungs yielded zero new information OR a
                    no-progress signal fires first (two identical full climbs
                    with zero new info).

Guards:
  - Never loops past rung 9 — terminal is unconditional.
  - No-progress detector: if two consecutive full climbs produce zero new
    info the ladder terminates immediately at whatever rung it's on.
  - hard_stop_enabled in tool_loop_guardrails is currently FALSE; this
    ladder's terminal rung IS the real stop for worker tasks — you should
    keep hard_stop_enabled=False for interactive sessions (would frustrate
    normal use) but consider setting it for headless kanban workers where
    the guardrails are your only circuit-breaker outside of this ladder.

Budget:
  - Escalate freely through all rungs; only NOTIFY (not block) when
    approaching cost limits via the cost signal.

Usage::

    from shay_cli.kanban_escalation import EscalationLadder, LadderProviders

    # Minimal — all providers use no-op stubs (safe for tests).
    ladder = EscalationLadder(task_id="t_abc123")
    outcome = ladder.climb(error="connection refused", context={})

    # Wired — pass real provider callables the worker already has.
    providers = LadderProviders(
        session_search=my_session_search,
        grep_codebase=my_grep,
        web_search=my_web_search,
        block_task=my_kanban_block,
    )
    ladder = EscalationLadder(task_id="t_abc123", providers=providers)
    outcome = ladder.climb(error=err, context={"task": task_dict})
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RUNG_NAMES: dict[int, str] = {
    0: "retry",
    1: "diagnose",
    2: "check_tools",
    3: "check_memory",
    4: "check_repos",
    5: "check_web",
    6: "escalate_brain",
    7: "decompose",
    8: "ask_fritz",
    9: "terminal",
}

MAX_RUNG = 9
NO_PROGRESS_THRESHOLD = 2  # consecutive full climbs with zero new info → terminal


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RungResult:
    """Outcome of executing one rung of the escalation ladder."""

    rung: int
    name: str
    info_gained: bool
    new_info: str = ""
    recommendation: str = ""
    is_terminal: bool = False
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rung": self.rung,
            "name": self.name,
            "info_gained": self.info_gained,
            "new_info": self.new_info,
            "recommendation": self.recommendation,
            "is_terminal": self.is_terminal,
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class LadderOutcome:
    """Final decision produced by the escalation ladder."""

    # One of: "retry" | "decompose" | "escalate_brain" | "ask_fritz" | "terminal"
    action: str
    rung_reached: int
    trail: list[RungResult] = field(default_factory=list)
    block_reason: str = ""
    no_progress_triggered: bool = False

    # Human-readable summary of what was tried and what was found.
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "rung_reached": self.rung_reached,
            "no_progress_triggered": self.no_progress_triggered,
            "trail": [r.to_dict() for r in self.trail],
            "block_reason": self.block_reason,
            "summary": self.summary,
        }

    def format_trail(self) -> str:
        """Format the escalation trail as human-readable text for block_reason."""
        lines = [f"Escalation trail (reached rung {self.rung_reached}/{MAX_RUNG}):"]
        for r in self.trail:
            badge = "✓" if r.info_gained else "✗"
            lines.append(f"  [{badge}] Rung {r.rung} {r.name}: {r.new_info or '(no new info)'}")
            if r.recommendation:
                lines.append(f"       → {r.recommendation}")
        if self.no_progress_triggered:
            lines.append(
                f"\nNo-progress detected: {NO_PROGRESS_THRESHOLD} consecutive full climbs "
                "with zero new information — stopping early."
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


@dataclass
class LadderProviders:
    """Pluggable I/O backends for each rung.

    All providers default to no-op stubs that return empty results so the
    ladder can be unit-tested without real infrastructure. Pass real
    implementations in production workers.
    """

    # Rung 3: search session history / lessons / buglog
    # Signature: (query: str) -> str
    session_search: Optional[Callable[[str], str]] = None

    # Rung 4: grep the codebase for prior art
    # Signature: (pattern: str, path: str) -> str
    grep_codebase: Optional[Callable[[str, str], str]] = None

    # Rung 5: web-search the error / approach
    # Signature: (query: str) -> str
    web_search: Optional[Callable[[str], str]] = None

    # Rung 6: invoke a stronger/different brain
    # Signature: (prompt: str, context: dict) -> str
    invoke_brain: Optional[Callable[[str, dict[str, Any]], str]] = None

    # Rung 2: capability check — returns error string or None
    # Signature: (task: dict) -> Optional[str]
    capability_check: Optional[Callable[[dict[str, Any]], Optional[str]]] = None

    # Terminal: call kanban_block with reason
    # Signature: (task_id: str, reason: str) -> None
    block_task: Optional[Callable[[str, str], None]] = None


# ---------------------------------------------------------------------------
# EscalationLadder
# ---------------------------------------------------------------------------


class EscalationLadder:
    """Stateful escalation ladder for a kanban worker task.

    Each call to ``climb()`` advances through the rungs from the current
    position, collecting information. The ladder remembers prior climbs to
    detect the no-progress condition.

    Typical worker usage::

        ladder = EscalationLadder(task_id=task_id, providers=providers)
        while True:
            result = do_the_work()
            if result.success:
                break
            outcome = ladder.climb(error=result.error, context={"task": task})
            if outcome.action == "retry":
                continue   # rung gave us new info; try the work again
            elif outcome.action == "decompose":
                break      # break work into sub-tasks
            elif outcome.action in {"ask_fritz", "terminal"}:
                break      # ladder handled the block
    """

    def __init__(
        self,
        task_id: str,
        providers: Optional[LadderProviders] = None,
        codebase_root: str = ".",
    ) -> None:
        self.task_id = task_id
        self.providers = providers or LadderProviders()
        self.codebase_root = codebase_root

        # Track prior climbs for the no-progress detector.
        self._climb_history: list[str] = []  # hash of each full climb's info-gained map

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def climb(self, error: str, context: Optional[dict[str, Any]] = None) -> LadderOutcome:
        """Climb the ladder starting from rung 0.

        Args:
            error: The error text / failure reason from the latest attempt.
            context: Optional dict with extra context (task dict, tool name, etc.)

        Returns:
            LadderOutcome — the final decision after exhausting rungs.
        """
        context = context or {}
        trail: list[RungResult] = []
        info_map: dict[int, bool] = {}  # rung → info_gained

        for rung in range(MAX_RUNG + 1):
            t0 = time.monotonic()
            result = self._execute_rung(rung, error, context, trail)
            result.duration_ms = (time.monotonic() - t0) * 1000
            trail.append(result)
            info_map[rung] = result.info_gained

            # Terminal rung — always stops here.
            if rung == MAX_RUNG or result.is_terminal:
                outcome = self._build_outcome(rung, trail, info_map, forced_terminal=True)
                self._record_climb(info_map)
                self._call_block(outcome)
                return outcome

            # Rungs that return a non-retry action immediately.
            action = self._rung_to_action(rung, result)
            if action and action != "continue":
                outcome = self._build_outcome(rung, trail, info_map, action=action)
                self._record_climb(info_map)
                if action in {"ask_fritz", "terminal"}:
                    self._call_block(outcome)
                return outcome

        # Shouldn't reach here — the rung==MAX_RUNG branch above catches it.
        outcome = self._build_outcome(MAX_RUNG, trail, info_map, forced_terminal=True)
        self._record_climb(info_map)
        self._call_block(outcome)
        return outcome

    # ------------------------------------------------------------------
    # Rung implementations
    # ------------------------------------------------------------------

    def _execute_rung(
        self,
        rung: int,
        error: str,
        context: dict[str, Any],
        trail: list[RungResult],
    ) -> RungResult:
        """Dispatch to the correct rung handler."""
        name = RUNG_NAMES[rung]
        handlers = {
            0: self._rung0_retry,
            1: self._rung1_diagnose,
            2: self._rung2_check_tools,
            3: self._rung3_check_memory,
            4: self._rung4_check_repos,
            5: self._rung5_check_web,
            6: self._rung6_escalate_brain,
            7: self._rung7_decompose,
            8: self._rung8_ask_fritz,
            9: self._rung9_terminal,
        }
        handler = handlers.get(rung, self._rung9_terminal)
        try:
            return handler(rung, name, error, context, trail)
        except Exception as exc:
            # Rung execution must never crash the ladder — degrade gracefully.
            return RungResult(
                rung=rung,
                name=name,
                info_gained=False,
                new_info=f"rung handler raised: {exc}",
                recommendation="rung error — treating as no new info",
            )

    def _rung0_retry(self, rung, name, error, context, trail) -> RungResult:
        """Rung 0: Signal a simple retry with the same approach."""
        return RungResult(
            rung=rung,
            name=name,
            info_gained=False,
            new_info="",
            recommendation="Retry the operation unchanged — first attempt at recovery.",
        )

    def _rung1_diagnose(self, rung, name, error, context, trail) -> RungResult:
        """Rung 1: Read the real error text and form a hypothesis."""
        if not error:
            return RungResult(rung=rung, name=name, info_gained=False, new_info="no error text")

        # Classify the error into a hypothesis.
        lower = error.lower()
        hypotheses: list[str] = []

        if "timeout" in lower or "timed out" in lower:
            hypotheses.append("operation timed out — consider chunking or increasing timeout")
        if "permission" in lower or "access denied" in lower or "forbidden" in lower:
            hypotheses.append("permission/auth error — check credentials and role grants")
        if "not found" in lower or "no such file" in lower or "404" in lower:
            hypotheses.append("resource missing — verify path/ID exists before operating on it")
        if "connection refused" in lower or "no route" in lower or "network" in lower:
            hypotheses.append("network/connectivity error — check service is up and reachable")
        if "syntax" in lower or "parse" in lower or "unexpected token" in lower:
            hypotheses.append("syntax/parse error — inspect the malformed input")
        if "memory" in lower or "oom" in lower or "out of memory" in lower:
            hypotheses.append("OOM — reduce batch size or request smaller context")
        if "rate limit" in lower or "429" in lower or "quota" in lower:
            hypotheses.append("rate limit — back off and retry with jitter")
        if "import" in lower or "module" in lower or "no module named" in lower:
            hypotheses.append("missing dependency — check install or virtual-env activation")

        if not hypotheses:
            # No known pattern matched — restating the raw error is not new info.
            return RungResult(
                rung=rung,
                name=name,
                info_gained=False,
                new_info=f"unclassified error (no known pattern) — raw: {error[:200]}",
                recommendation="",
            )

        hypothesis = "; ".join(hypotheses)
        return RungResult(
            rung=rung,
            name=name,
            info_gained=True,
            new_info=f"Error classified. Hypothesis: {hypothesis}",
            recommendation=f"Retry with diagnosis in mind: {hypothesis}",
        )

    def _rung2_check_tools(self, rung, name, error, context, trail) -> RungResult:
        """Rung 2: Verify required tools/caps are available (reuse H2 cap-check)."""
        task = context.get("task") or {}
        if not task:
            return RungResult(
                rung=rung, name=name, info_gained=False,
                new_info="no task context available for capability check",
            )

        cap_check = self.providers.capability_check
        if cap_check is None:
            # Fall back to importing the canonical implementation.
            try:
                from shay_cli.kanban_db import _capability_check_error
                cap_check = _capability_check_error  # type: ignore[assignment]
            except Exception:
                return RungResult(
                    rung=rung, name=name, info_gained=False,
                    new_info="capability_check unavailable — skip",
                )

        try:
            error_msg = cap_check(task)
        except Exception as exc:
            return RungResult(
                rung=rung, name=name, info_gained=False,
                new_info=f"capability_check raised: {exc}",
            )

        if error_msg:
            return RungResult(
                rung=rung, name=name, info_gained=True,
                new_info=f"Capability gap found: {error_msg}",
                recommendation="Install the missing tool or reassign to a profile that has it.",
                # Missing a REQUIRED tool can be terminal — signal is_terminal so
                # the caller can break the loop rather than climbing further.
                is_terminal=True,
            )

        return RungResult(
            rung=rung, name=name, info_gained=False,
            new_info="all required tools present — capability gap is not the issue",
        )

    def _rung3_check_memory(self, rung, name, error, context, trail) -> RungResult:
        """Rung 3: Search buglog, lessons, prior session memos for the error signature."""
        if not self.providers.session_search:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info="session_search not available — skip")

        # Build a focused query from the error text.
        query = _extract_search_query(error)
        try:
            result = self.providers.session_search(query)
        except Exception as exc:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info=f"session_search raised: {exc}")

        has_content = bool(result and result.strip() and "no results" not in result.lower())
        return RungResult(
            rung=rung, name=name, info_gained=has_content,
            new_info=f"Memory search for {query!r}: {result[:500] if has_content else 'no prior art found'}",
            recommendation="Apply lesson from memory to retry" if has_content else "",
        )

    def _rung4_check_repos(self, rung, name, error, context, trail) -> RungResult:
        """Rung 4: Grep the codebase for working prior art."""
        if not self.providers.grep_codebase:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info="grep_codebase not available — skip")

        pattern = _extract_search_query(error)
        try:
            result = self.providers.grep_codebase(pattern, self.codebase_root)
        except Exception as exc:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info=f"grep_codebase raised: {exc}")

        has_content = bool(result and result.strip())
        return RungResult(
            rung=rung, name=name, info_gained=has_content,
            new_info=f"Repo search for {pattern!r}: {result[:500] if has_content else 'nothing found'}",
            recommendation="Port the working pattern from the codebase" if has_content else "",
        )

    def _rung5_check_web(self, rung, name, error, context, trail) -> RungResult:
        """Rung 5: Web-search the error or approach."""
        if not self.providers.web_search:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info="web_search not available — skip")

        query = _extract_search_query(error)
        try:
            result = self.providers.web_search(query)
        except Exception as exc:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info=f"web_search raised: {exc}")

        has_content = bool(result and result.strip() and len(result) > 50)
        return RungResult(
            rung=rung, name=name, info_gained=has_content,
            new_info=f"Web search for {query!r}: {result[:500] if has_content else 'no useful results'}",
            recommendation="Apply web-sourced solution in next attempt" if has_content else "",
        )

    def _rung6_escalate_brain(self, rung, name, error, context, trail) -> RungResult:
        """Rung 6: Invoke a stronger/different model for one attempt."""
        if not self.providers.invoke_brain:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info="invoke_brain not available — skip")

        trail_summary = _format_mini_trail(trail)
        prompt = (
            f"A kanban worker task failed. Error: {error}\n\n"
            f"Escalation so far:\n{trail_summary}\n\n"
            "Provide a specific, actionable recommendation to resolve this failure."
        )
        try:
            result = self.providers.invoke_brain(prompt, context)
        except Exception as exc:
            return RungResult(rung=rung, name=name, info_gained=False,
                              new_info=f"invoke_brain raised: {exc}")

        has_content = bool(result and result.strip() and len(result) > 30)
        return RungResult(
            rung=rung, name=name, info_gained=has_content,
            new_info=f"Brain recommendation: {result[:400] if has_content else 'no useful output'}",
            recommendation=result[:400] if has_content else "",
        )

    def _rung7_decompose(self, rung, name, error, context, trail) -> RungResult:
        """Rung 7: Signal that the task should be broken into smaller sub-units."""
        task = context.get("task") or {}
        title = task.get("title", "this task") if isinstance(task, dict) else "this task"
        return RungResult(
            rung=rung, name=name, info_gained=True,
            new_info=f"Recommending decomposition of '{title}' into smaller sub-tasks.",
            recommendation=(
                "Break the task into sub-tasks — create child kanban cards for each "
                "atomic unit and let the dispatcher retry them independently."
            ),
        )

    def _rung8_ask_fritz(self, rung, name, error, context, trail) -> RungResult:
        """Rung 8: Pause and surface the full trail to the human owner."""
        return RungResult(
            rung=rung, name=name, info_gained=True,
            new_info="Escalating to Fritz (human owner) with full trail.",
            recommendation=(
                "Surface the full escalation trail to the human and await direction. "
                "The worker will block until unblocked with new instructions."
            ),
        )

    def _rung9_terminal(self, rung, name, error, context, trail) -> RungResult:
        """Rung 9: Terminal — all rungs exhausted, no new info. Block unconditionally."""
        return RungResult(
            rung=rung, name=name,
            info_gained=False,
            new_info="All escalation rungs exhausted — no new information found.",
            recommendation=(
                "Block the task with the complete escalation trail. "
                "Manual intervention required."
            ),
            is_terminal=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rung_to_action(self, rung: int, result: RungResult) -> Optional[str]:
        """Map a rung result to a LadderOutcome action, or 'continue' to keep climbing."""
        if result.is_terminal:
            return "terminal"
        if rung == 0:
            # Retry rung — signal retry, which exits the climb.
            # Only retry once (caller owns the outer loop).
            return "retry"
        if rung == 6 and result.info_gained:
            return "escalate_brain"
        if rung == 7:
            return "decompose"
        if rung == 8:
            return "ask_fritz"
        # For rungs 1-5 that gained info: signal retry so the caller can try again.
        if result.info_gained and rung in {1, 2, 3, 4, 5}:
            return "retry"
        return "continue"

    def _build_outcome(
        self,
        rung: int,
        trail: list[RungResult],
        info_map: dict[int, bool],
        *,
        action: Optional[str] = None,
        forced_terminal: bool = False,
    ) -> LadderOutcome:
        if forced_terminal or action in {"terminal", "ask_fritz"}:
            chosen = action or "terminal"
        else:
            chosen = action or "retry"

        # Check no-progress before finalizing.
        no_progress = self._check_no_progress(info_map)
        if no_progress:
            chosen = "terminal"

        outcome = LadderOutcome(
            action=chosen,
            rung_reached=rung,
            trail=trail,
            no_progress_triggered=no_progress,
        )
        outcome.block_reason = outcome.format_trail()
        outcome.summary = (
            f"Escalation ladder reached rung {rung} ({RUNG_NAMES.get(rung, '?')}). "
            f"Action: {chosen}. "
            f"Info gained at rungs: {[r for r, v in info_map.items() if v] or 'none'}."
        )
        return outcome

    def _check_no_progress(self, current_info_map: dict[int, bool]) -> bool:
        """Return True if the no-progress condition is met.

        Condition: the current climb's info-gained fingerprint matches the
        previous climb's fingerprint (i.e., no new info on a second full climb).
        """
        fingerprint = _fingerprint_info_map(current_info_map)
        if len(self._climb_history) >= 1 and self._climb_history[-1] == fingerprint:
            return True
        return False

    def _record_climb(self, info_map: dict[int, bool]) -> None:
        """Record the current climb's fingerprint for no-progress detection."""
        self._climb_history.append(_fingerprint_info_map(info_map))
        # Keep only the last two climbs — we only look back one.
        if len(self._climb_history) > NO_PROGRESS_THRESHOLD:
            self._climb_history = self._climb_history[-NO_PROGRESS_THRESHOLD:]

    def _call_block(self, outcome: LadderOutcome) -> None:
        """Call the block_task provider if available."""
        if self.providers.block_task:
            try:
                self.providers.block_task(self.task_id, outcome.block_reason)
            except Exception:
                pass  # If the block call fails, the outcome is still returned.


# ---------------------------------------------------------------------------
# Utility helpers (module-level, pure functions)
# ---------------------------------------------------------------------------


def _extract_search_query(error: str, max_words: int = 8) -> str:
    """Extract the most signal-rich words from an error string for a search query."""
    if not error:
        return "kanban worker failure"
    # Strip common boilerplate and take the first meaningful fragment.
    import re
    cleaned = re.sub(r"\s+", " ", error.strip())
    # Remove Python traceback prefix lines.
    cleaned = re.sub(r"Traceback \(most recent call last\):.*?(\w+Error[^\n]*)", r"\1", cleaned, flags=re.DOTALL)
    # Take first 120 chars to avoid overly long queries.
    fragment = cleaned[:120]
    words = fragment.split()[:max_words]
    return " ".join(words)


def _format_mini_trail(trail: list[RungResult]) -> str:
    """Format a compact trail summary for the escalate_brain prompt."""
    lines = []
    for r in trail:
        badge = "✓" if r.info_gained else "✗"
        lines.append(f"  Rung {r.rung} {r.name} [{badge}]: {r.new_info[:100] or '—'}")
    return "\n".join(lines) if lines else "(no prior rungs)"


def _fingerprint_info_map(info_map: dict[int, bool]) -> str:
    """Stable hash of a rung→info_gained map for no-progress detection."""
    canonical = json.dumps(info_map, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Hard-stop recommendation (note — does NOT mutate config)
# ---------------------------------------------------------------------------


def hard_stop_recommendation() -> str:
    """Return a human-readable note about tool_loop_guardrails.hard_stop_enabled.

    The escalation ladder's terminal rung IS the real stop for worker tasks.
    Enabling the tool-loop hard_stop in config.yaml would add a secondary
    circuit-breaker for raw tool-loop repetition within a single turn, but
    the ladder already handles multi-turn exhaustion more intelligently.

    Recommendation:
      - Keep hard_stop_enabled: false for interactive CLI/TUI sessions (prevents
        frustrating early stops during normal deep-research turns).
      - Consider hard_stop_enabled: true ONLY for headless worker profiles where
        the ladder's terminal rung is insufficient (e.g. a worker with no kanban
        tools that somehow bypasses the ladder). For standard kanban workers, the
        ladder + rung 9 block is the canonical stop; the tool-loop guardrail is
        a redundant safety net.
    """
    return (
        "tool_loop_guardrails.hard_stop_enabled is currently FALSE (default).\n"
        "The escalation ladder's rung-9 terminal serves as the real stop for kanban workers.\n"
        "Recommendation: leave hard_stop_enabled=False for interactive sessions; optionally\n"
        "enable it in headless worker profile config.yaml as a secondary circuit-breaker.\n"
        "The ladder is the primary, intentional stop — the guardrail is a safety net."
    )
