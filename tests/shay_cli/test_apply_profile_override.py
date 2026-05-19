"""Regression tests for _apply_profile_override SHAY_HOME guard (issue #22502).

When SHAY_HOME is set to the shay root (e.g. systemd hardcodes
SHAY_HOME=/root/.shay), _apply_profile_override must still read
active_profile and update SHAY_HOME to the profile directory.

When SHAY_HOME is already a profile directory (.../profiles/<name>),
_apply_profile_override must trust it and return without re-reading
active_profile (child-process inheritance contract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


def _run_apply_profile_override(
    tmp_path, monkeypatch, *, shay_home: str | None, active_profile: str | None,
    argv: list[str] | None = None,
):
    """Run _apply_profile_override in isolation.

    Returns the value of os.environ["SHAY_HOME"] after the call,
    or None if unset.
    """
    shay_root = tmp_path / ".shay"
    shay_root.mkdir(parents=True, exist_ok=True)

    if active_profile is not None:
        (shay_root / "active_profile").write_text(active_profile)

    if active_profile and active_profile != "default":
        (shay_root / "profiles" / active_profile).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    if shay_home is not None:
        monkeypatch.setenv("SHAY_HOME", shay_home)
    else:
        monkeypatch.delenv("SHAY_HOME", raising=False)

    monkeypatch.setattr(sys, "argv", argv or ["shay", "gateway", "start"])

    from shay_cli.main import _apply_profile_override
    _apply_profile_override()

    return os.environ.get("SHAY_HOME")


class TestApplyProfileOverrideShayHomeGuard:
    """Regression guard for issue #22502.

    Verifies that SHAY_HOME pointing to the shay root does NOT suppress
    the active_profile check, while SHAY_HOME already pointing to a
    profile directory IS trusted as-is.
    """

    def test_shay_home_at_root_with_active_profile_is_redirected(
        self, tmp_path, monkeypatch
    ):
        """SHAY_HOME=/root/.shay + active_profile=coder must redirect
        SHAY_HOME to .../profiles/coder.

        Bug scenario from #22502: systemd sets SHAY_HOME to the shay root
        and the user switches to a profile via `shay profile use`.
        Before the fix, the guard returned early and active_profile was ignored.
        """
        shay_root = tmp_path / ".shay"
        shay_root.mkdir(parents=True, exist_ok=True)

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            shay_home=str(shay_root),
            active_profile="coder",
        )

        assert result is not None, "SHAY_HOME must be set after profile redirect"
        assert "profiles" in result, (
            f"Expected SHAY_HOME to point into profiles/ dir, got: {result!r}"
        )
        assert result.endswith("coder"), (
            f"Expected SHAY_HOME to end with 'coder', got: {result!r}"
        )

    def test_shay_home_already_profile_dir_is_trusted(self, tmp_path, monkeypatch):
        """SHAY_HOME=.../profiles/coder must not be overridden even when
        active_profile says something different.

        Preserves the child-process inheritance contract: a subprocess spawned
        with SHAY_HOME already set to a specific profile must stay in that
        profile.
        """
        shay_root = tmp_path / ".shay"
        profile_dir = shay_root / "profiles" / "coder"
        profile_dir.mkdir(parents=True, exist_ok=True)

        (shay_root / "active_profile").write_text("other")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("SHAY_HOME", str(profile_dir))
        monkeypatch.setattr(sys, "argv", ["shay", "gateway", "start"])

        from shay_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("SHAY_HOME") == str(profile_dir), (
            "SHAY_HOME must remain unchanged when already pointing to a profile dir"
        )

    def test_shay_home_unset_reads_active_profile(self, tmp_path, monkeypatch):
        """Classic case: SHAY_HOME unset + active_profile=coder must set
        SHAY_HOME to the profile directory (existing behaviour must not regress).
        """
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            shay_home=None,
            active_profile="coder",
        )

        assert result is not None
        assert "coder" in result

    def test_shay_home_unset_default_profile_no_redirect(self, tmp_path, monkeypatch):
        """active_profile=default must not redirect SHAY_HOME."""
        shay_root = tmp_path / ".shay"
        shay_root.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("SHAY_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", ["shay", "gateway", "start"])
        (shay_root / "active_profile").write_text("default")

        from shay_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("SHAY_HOME") is None
