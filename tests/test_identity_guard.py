import json
from pathlib import Path

import pytest

from identity_guard import (
    ensure_identity_snapshot,
    load_manifest,
    restore_from_emergency,
    startup_identity_check,
    verify_identity_files,
)


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


def test_snapshot_creates_manifest_and_emergency_files(shay_home):
    manifest = ensure_identity_snapshot(reason="test")
    guard_root = shay_home / "private" / "identity-guard"

    assert manifest["current_version"] == 1
    assert (guard_root / "identity-manifest.json").exists()
    assert (guard_root / "emergency" / "SOUL.md").exists()
    assert (guard_root / "emergency" / "PERSONA.md").exists()
    assert (guard_root / "emergency" / "USER.md").exists()
    assert (guard_root / "CURRENT_VERSION.txt").read_text(encoding="utf-8").strip() == "v00001"


def test_verify_detects_required_line_drift(shay_home):
    ensure_identity_snapshot(reason="baseline")
    (shay_home / "SOUL.md").write_text("Learn Fritz\n", encoding="utf-8")

    result = verify_identity_files()

    assert result.ok is False
    assert any(f.code == "missing_required_snippets" for f in result.findings)


def test_restore_from_emergency_restores_missing_file(shay_home):
    ensure_identity_snapshot(reason="baseline")
    (shay_home / "PERSONA.md").unlink()

    restored = restore_from_emergency("PERSONA.md")

    assert restored.exists()
    assert "Nothing supersedes Fritz." in restored.read_text(encoding="utf-8")


def test_startup_check_auto_restores_missing_file_and_writes_incident(shay_home):
    ensure_identity_snapshot(reason="baseline")
    (shay_home / "PERSONA.md").unlink()

    result = startup_identity_check(send_alert=False, auto_restore_missing=True)

    assert result.ok is True
    assert (shay_home / "PERSONA.md").exists()
    assert result.incident_path is not None
    assert result.interview_path is not None
    incident = json.loads(Path(result.incident_path).read_text(encoding="utf-8"))
    assert "PERSONA.md" in incident["auto_restored"]


def test_startup_check_bootstraps_manifest_when_missing(shay_home):
    result = startup_identity_check(send_alert=False, auto_restore_missing=True)
    manifest = load_manifest()

    assert result.ok is True
    assert manifest["current_version"] >= 1
    assert "SOUL.md" in manifest["files"]
