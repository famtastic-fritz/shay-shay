"""Shared helpers for direct xAI HTTP integrations."""

from __future__ import annotations


def shay_xai_user_agent() -> str:
    """Return a stable Shay-Shay-specific User-Agent for xAI HTTP calls."""
    try:
        from shay_cli import __version__
    except Exception:
        __version__ = "unknown"
    return f"Shay-Shay-Agent/{__version__}"
