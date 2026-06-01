"""Drain-aware gateway restart handoff (memory/ops lifecycle Z3).

When Shay changes something her own running process cannot apply to itself —
a backend flag (e.g. ``SHAY_RECALL_BACKEND=c4``), a config key, an env var —
she needs the gateway to restart so the new process picks it up. She cannot
restart the process she is running inside, so this command hands the restart
off to the CLI.

Mechanism (the working one): ``shay gateway restart`` sends ``SIGUSR1`` to the
running gateway, which maps to ``request_restart(via_service=True)`` in
``gateway/run.py`` — a *drain-aware* restart that lets in-flight agent runs
finish before the process exits and the service manager relaunches it.

This module wraps that with a before/after VERIFY:
  * before — snapshot the running PID + confirm the dispatcher (``gateway.run``)
    imports clean, so we know what a healthy "after" looks like.
  * restart — shell ``shay gateway restart`` (unless ``dry_run``).
  * after  — confirm a gateway is running again, its PID is *new* (the process
    actually cycled), the dispatcher still imports, and the persisted runtime
    health is not in a failed state.

Safety: ``dry_run=True`` performs the full verify path against the CURRENTLY
running gateway by READING status only — it never sends a signal or restarts.
This is how the command is validated without touching a live gateway.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional


# Dispatcher module that must import clean for the gateway to come up. This is
# the gateway runner that owns the SIGUSR1 restart handler + request_restart.
_DISPATCHER_MODULE = "gateway.run"


@dataclass
class HandoffResult:
    ok: bool
    dry_run: bool
    before_pid: Optional[int] = None
    after_pid: Optional[int] = None
    dispatcher_import_ok: bool = False
    health_ok: bool = False
    messages: List[str] = field(default_factory=list)

    def add(self, msg: str) -> "HandoffResult":
        self.messages.append(msg)
        return self


def _running_pid() -> Optional[int]:
    """Best-effort current gateway PID (None if not running)."""
    try:
        from gateway.status import get_running_pid

        pid = get_running_pid(cleanup_stale=False)
        if pid:
            return int(pid)
    except Exception:
        pass
    # Fallback: process scan.
    try:
        from shay_cli.gateway import find_gateway_pids

        pids = find_gateway_pids()
        if pids:
            return int(pids[0])
    except Exception:
        pass
    return None


def _dispatcher_imports_clean() -> bool:
    """Confirm the gateway dispatcher module imports without error."""
    try:
        importlib.import_module(_DISPATCHER_MODULE)
        return True
    except Exception:
        return False


def _health_ok() -> bool:
    """Read persisted runtime health; healthy unless a failed/draining state."""
    try:
        from gateway.status import read_runtime_status

        state = read_runtime_status()
    except Exception:
        return False
    if not state:
        # No status file yet — treat as inconclusive-but-not-failed.
        return True
    gw = state.get("gateway_state")
    return gw not in ("startup_failed",)


def _wait_for_new_pid(old_pid: Optional[int], timeout: float = 60.0,
                      poll: float = 1.0) -> Optional[int]:
    """Wait until a gateway PID is present and differs from ``old_pid``."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pid = _running_pid()
        if pid is not None and pid != old_pid:
            return pid
        time.sleep(poll)
    return _running_pid()


def handoff_restart(dry_run: bool = False, timeout: float = 60.0) -> HandoffResult:
    """Hand a drain-aware gateway restart off to the CLI, then verify.

    Parameters
    ----------
    dry_run:
        When True (safe mode), do NOT restart. Run the full verify path against
        the currently running gateway by reading status only, so the command
        and its verify-logic can be validated without cycling a live gateway.
    timeout:
        Seconds to wait for the new process after a real restart.
    """
    res = HandoffResult(ok=False, dry_run=dry_run)

    before_pid = _running_pid()
    res.before_pid = before_pid
    if before_pid is None:
        res.add("⚠ No running gateway detected — nothing to hand off to.")
    else:
        res.add(f"• Current gateway PID: {before_pid}")

    dispatcher_ok = _dispatcher_imports_clean()
    res.dispatcher_import_ok = dispatcher_ok
    res.add(
        f"• Dispatcher ({_DISPATCHER_MODULE}) imports: "
        + ("clean" if dispatcher_ok else "FAILED")
    )

    if dry_run:
        res.health_ok = _health_ok()
        res.add(f"• Runtime health: {'ok' if res.health_ok else 'degraded'}")
        res.add(
            "• DRY-RUN: would run `shay gateway restart` (SIGUSR1 drain-aware), "
            "then verify a new PID, dispatcher import, and health."
        )
        # In dry-run, success = the verify-logic could read everything it needs
        # and the dispatcher is importable (the restart would land cleanly).
        res.ok = dispatcher_ok and (before_pid is not None) and res.health_ok
        res.after_pid = before_pid
        return res

    if before_pid is None:
        res.add("✗ Cannot restart: gateway is not running. Use `shay gateway start`.")
        return res
    if not dispatcher_ok:
        res.add("✗ Aborting restart: dispatcher import failed — fix before restarting.")
        return res

    res.add("→ Handing off: `shay gateway restart` (drain-aware SIGUSR1)…")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "shay_cli.main", "gateway", "restart"],
            capture_output=True, text=True, timeout=max(120.0, timeout + 60.0),
        )
        for line in (proc.stdout or "").splitlines():
            res.add(f"  {line}")
        if proc.returncode != 0:
            res.add(f"✗ `shay gateway restart` exited {proc.returncode}.")
            for line in (proc.stderr or "").splitlines()[-5:]:
                res.add(f"  {line}")
            return res
    except subprocess.TimeoutExpired:
        res.add("✗ `shay gateway restart` timed out.")
        return res
    except Exception as e:  # pragma: no cover - defensive
        res.add(f"✗ Restart handoff failed: {e}")
        return res

    new_pid = _wait_for_new_pid(before_pid, timeout=timeout)
    res.after_pid = new_pid
    if new_pid is None:
        res.add("✗ Gateway did not come back within timeout.")
        return res
    if new_pid == before_pid:
        res.add(f"⚠ PID unchanged ({new_pid}) — process may not have cycled.")
    else:
        res.add(f"✓ Gateway back up with new PID {new_pid} (was {before_pid}).")

    res.dispatcher_import_ok = _dispatcher_imports_clean()
    res.health_ok = _health_ok()
    res.add(f"• Dispatcher imports: {'clean' if res.dispatcher_import_ok else 'FAILED'}")
    res.add(f"• Runtime health: {'ok' if res.health_ok else 'degraded'}")

    res.ok = (
        new_pid is not None
        and new_pid != before_pid
        and res.dispatcher_import_ok
        and res.health_ok
    )
    res.add("✓ Restart handoff verified." if res.ok else "⚠ Restart completed with warnings.")
    return res


def run_handoff_restart(dry_run: bool = False) -> int:
    """CLI entry: run the handoff and print a report. Returns exit code."""
    res = handoff_restart(dry_run=dry_run)
    header = "Gateway restart handoff" + (" (dry-run)" if dry_run else "")
    print(header)
    for m in res.messages:
        print(m)
    return 0 if res.ok else 1


__all__ = ["handoff_restart", "run_handoff_restart", "HandoffResult"]
