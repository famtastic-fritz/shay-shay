"""Tests for the drain-aware gateway restart handoff (Z3).

These exercise the verify-logic without touching a real gateway: the running
PID, dispatcher import, and health probes are monkeypatched, and no subprocess
is spawned in dry-run.
"""

import shay_cli.handoff_restart as hr


def test_dry_run_never_restarts_and_reads_status(monkeypatch):
    monkeypatch.setattr(hr, "_running_pid", lambda: 4242)
    monkeypatch.setattr(hr, "_dispatcher_imports_clean", lambda: True)
    monkeypatch.setattr(hr, "_health_ok", lambda: True)

    # Guard: a real restart would shell out — fail loudly if dry-run does.
    def _boom(*a, **k):
        raise AssertionError("dry-run must not spawn a restart")
    monkeypatch.setattr(hr.subprocess, "run", _boom)

    res = hr.handoff_restart(dry_run=True)
    assert res.dry_run is True
    assert res.ok is True
    assert res.before_pid == 4242
    assert res.after_pid == 4242  # unchanged — nothing restarted
    assert res.dispatcher_import_ok is True
    assert any("DRY-RUN" in m for m in res.messages)


def test_dry_run_flags_failed_dispatcher(monkeypatch):
    monkeypatch.setattr(hr, "_running_pid", lambda: 1)
    monkeypatch.setattr(hr, "_dispatcher_imports_clean", lambda: False)
    monkeypatch.setattr(hr, "_health_ok", lambda: True)
    res = hr.handoff_restart(dry_run=True)
    assert res.ok is False
    assert res.dispatcher_import_ok is False


def test_dry_run_no_gateway_running(monkeypatch):
    monkeypatch.setattr(hr, "_running_pid", lambda: None)
    monkeypatch.setattr(hr, "_dispatcher_imports_clean", lambda: True)
    monkeypatch.setattr(hr, "_health_ok", lambda: True)
    res = hr.handoff_restart(dry_run=True)
    assert res.ok is False  # nothing to hand off to
    assert any("No running gateway" in m for m in res.messages)


def test_real_restart_verifies_new_pid(monkeypatch):
    # Simulate: before PID 100, restart succeeds, new PID 200.
    pids = iter([100])  # _running_pid called once before restart

    def _running():
        try:
            return next(pids)
        except StopIteration:
            return 200
    monkeypatch.setattr(hr, "_running_pid", _running)
    monkeypatch.setattr(hr, "_dispatcher_imports_clean", lambda: True)
    monkeypatch.setattr(hr, "_health_ok", lambda: True)
    monkeypatch.setattr(hr, "_wait_for_new_pid", lambda old, **k: 200)

    class _Proc:
        returncode = 0
        stdout = "✓ service restarted (PID 200)"
        stderr = ""
    monkeypatch.setattr(hr.subprocess, "run", lambda *a, **k: _Proc())

    res = hr.handoff_restart(dry_run=False)
    assert res.ok is True
    assert res.before_pid == 100
    assert res.after_pid == 200


def test_real_restart_aborts_on_bad_dispatcher(monkeypatch):
    monkeypatch.setattr(hr, "_running_pid", lambda: 100)
    monkeypatch.setattr(hr, "_dispatcher_imports_clean", lambda: False)

    def _boom(*a, **k):
        raise AssertionError("must not restart when dispatcher import fails")
    monkeypatch.setattr(hr.subprocess, "run", _boom)

    res = hr.handoff_restart(dry_run=False)
    assert res.ok is False
    assert any("Aborting restart" in m for m in res.messages)


def test_health_ok_treats_startup_failed_as_degraded(monkeypatch):
    monkeypatch.setattr(
        hr, "read_runtime_status", None, raising=False
    )

    def _status():
        return {"gateway_state": "startup_failed"}
    import gateway.status as gs
    monkeypatch.setattr(gs, "read_runtime_status", _status)
    assert hr._health_ok() is False

    def _ok():
        return {"gateway_state": "running"}
    monkeypatch.setattr(gs, "read_runtime_status", _ok)
    assert hr._health_ok() is True
