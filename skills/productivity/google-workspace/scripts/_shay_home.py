"""Resolve SHAY_HOME for standalone skill scripts.

Skill scripts may run outside the Shay-Shay process (e.g. system Python,
nix env, CI) where ``shay_constants`` is not importable.  This module
provides the same ``get_shay_home()`` and ``display_shay_home()``
contracts as ``shay_constants`` without requiring it on ``sys.path``.

When ``shay_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``shay_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``SHAY_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from shay_constants import display_shay_home as display_shay_home
    from shay_constants import get_shay_home as get_shay_home
except (ModuleNotFoundError, ImportError):

    def get_shay_home() -> Path:
        """Return the Shay-Shay home directory (default: ~/.shay).

        Mirrors ``shay_constants.get_shay_home()``."""
        val = os.environ.get("SHAY_HOME", "").strip()
        return Path(val) if val else Path.home() / ".shay"

    def display_shay_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``shay_constants.display_shay_home()``."""
        home = get_shay_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
