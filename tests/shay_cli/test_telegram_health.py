"""Regression tests for truthful Telegram local-readiness reporting."""

from types import SimpleNamespace

import pytest

import shay_cli.doctor as doctor
import shay_cli.gateway as gateway_cli
from shay_cli.telegram_health import assess_telegram_readiness


def test_configured_telegram_is_degraded_when_adapter_dependency_is_missing():
    readiness = assess_telegram_readiness(
        configured=True,
        dependency_available=False,
        gateway_running=True,
        gateway_process_count=1,
    )

    assert not readiness.ready
    assert readiness.status_label == "configured — degraded: python-telegram-bot missing"


def test_configured_telegram_is_degraded_when_gateway_is_stopped():
    readiness = assess_telegram_readiness(
        configured=True,
        dependency_available=True,
        gateway_running=False,
        gateway_process_count=0,
    )

    assert not readiness.ready
    assert readiness.status_label == "configured — degraded: gateway stopped"


def test_ready_status_does_not_claim_an_end_to_end_delivery_test():
    readiness = assess_telegram_readiness(
        configured=True,
        dependency_available=True,
        gateway_running=True,
        gateway_process_count=1,
    )

    assert readiness.ready
    assert readiness.status_label == "configured — runtime ready (delivery path unverified)"
    assert "delivery path unverified" in readiness.doctor_detail


def test_configured_telegram_is_degraded_when_duplicate_gateway_processes_exist():
    readiness = assess_telegram_readiness(
        configured=True,
        dependency_available=True,
        gateway_running=True,
        gateway_process_count=2,
    )

    assert not readiness.ready
    assert readiness.status_label == "configured — degraded: duplicate gateway processes"
    assert "one owner" in readiness.doctor_detail


def test_doctor_reports_stopped_gateway_as_a_telegram_issue(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "configured-for-test")
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: object() if name == "telegram" else None)
    monkeypatch.setattr(
        gateway_cli,
        "get_gateway_runtime_snapshot",
        lambda: SimpleNamespace(running=False, gateway_pids=()),
    )

    issues: list[str] = []
    doctor._check_telegram_operational_health(issues)

    output = capsys.readouterr().out
    assert "Telegram Operational Health" in output
    assert "gateway stopped" in output
    assert issues == ["Telegram is configured but the gateway is stopped — run: shay gateway start"]


def test_unverifiable_dependency_is_not_reported_installed_or_missing():
    readiness = assess_telegram_readiness(
        configured=True,
        dependency_available=None,
        gateway_running=True,
        gateway_process_count=1,
    )
    assert readiness.ready is False
    assert readiness.dependency_available is None
    assert "availability unverified" in readiness.status_label
    assert "missing" not in readiness.doctor_detail


@pytest.mark.parametrize("probe_error", [ValueError, ImportError, OSError])
def test_doctor_reports_unverifiable_dependency_without_crashing(monkeypatch, capsys, probe_error):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "configured-for-test")

    def unavailable_spec(name):
        raise probe_error("private probe detail must not be printed")

    monkeypatch.setattr(doctor.importlib.util, "find_spec", unavailable_spec)
    monkeypatch.setattr(
        gateway_cli,
        "get_gateway_runtime_snapshot",
        lambda: SimpleNamespace(running=True, gateway_pids=(123,)),
    )
    issues = []
    doctor._check_telegram_operational_health(issues)
    output = capsys.readouterr().out
    assert "availability unverified" in output
    assert "private probe detail" not in output
    assert len(issues) == 1
    assert "could not be inspected" in issues[0]
    assert "pip install" not in issues[0]
