import subprocess
from pathlib import Path

import pytest

from identity_guard import (
    _safe_copy_replace,
    ensure_identity_snapshot,
    lock_identity_backups,
    unlock_identity_backups,
)
from shay_cli.identity_cmd import cmd_identity


@pytest.fixture()
def shay_home(tmp_path, monkeypatch):
    root = tmp_path / ".shay"
    (root / "memories").mkdir(parents=True)
    monkeypatch.setenv("SHAY_HOME", str(root))

    (root / "SOUL.md").write_text(
        "Nothing supersedes Fritz.\nLearn Fritz\nFritz's direct message / directive right now\n",
        encoding="utf-8",
    )
    (root / "PERSONA.md").write_text(
        "Nothing supersedes Fritz.\nFritz's direct intent outranks everything.\n",
        encoding="utf-8",
    )
    (root / "memories" / "USER.md").write_text(
        "nothing supersedes Fritz or his direct directives\ndynamic ultra-brief responses\n",
        encoding="utf-8",
    )
    return root


def test_safe_copy_replace_unlocks_before_overwrite_on_macos(tmp_path, monkeypatch):
    src = tmp_path / "src.txt"
    dest = tmp_path / "dest.txt"
    src.write_text("new", encoding="utf-8")
    dest.write_text("old", encoding="utf-8")

    monkeypatch.setattr("identity_guard.sys.platform", "darwin")
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("identity_guard.subprocess.run", fake_run)

    _safe_copy_replace(src, dest, lock_after=True)

    assert dest.read_text(encoding="utf-8") == "new"
    assert calls == [
        ["chflags", "nouchg", str(dest)],
        ["chflags", "uchg", str(dest)],
    ]


def test_identity_lock_unlock_returns_manifest_paths(shay_home, monkeypatch):
    ensure_identity_snapshot(reason="baseline")
    monkeypatch.setattr("identity_guard.sys.platform", "linux")

    locked = lock_identity_backups()
    unlocked = unlock_identity_backups()

    assert len(locked) == 6
    assert len(unlocked) == 6
    assert all(path.endswith(".md") for path in locked)


def test_identity_status_command_reports_ok(shay_home, capsys, monkeypatch):
    ensure_identity_snapshot(reason="baseline")
    monkeypatch.setattr("identity_guard.sys.platform", "linux")

    class Args:
        identity_command = "status"
        json = False

    rc = cmd_identity(Args())
    out = capsys.readouterr().out

    assert rc == 0
    assert "Identity status: OK" in out
    assert "Mode: normal" in out
    assert "PERSONA.md" in out


def test_identity_status_command_reports_warn_for_warning_only_drift(shay_home, capsys, monkeypatch):
    ensure_identity_snapshot(reason="baseline")
    monkeypatch.setattr("identity_guard.sys.platform", "linux")
    (shay_home / "memories" / "USER.md").write_text(
        "nothing supersedes Fritz or his direct directives\n",
        encoding="utf-8",
    )

    class Args:
        identity_command = "status"
        json = False

    rc = cmd_identity(Args())
    out = capsys.readouterr().out

    assert rc == 0
    assert "Identity status: WARN" in out
    assert "missing_recommended_snippets" in out


def test_identity_snapshot_command_prints_version(shay_home, capsys, monkeypatch):
    monkeypatch.setattr("identity_guard.sys.platform", "linux")

    class Args:
        identity_command = "snapshot"
        reason = "manual-test"

    rc = cmd_identity(Args())
    out = capsys.readouterr().out

    assert rc == 0
    assert "Identity snapshot saved: v00001" in out
