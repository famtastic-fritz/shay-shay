"""Operator-facing task inspection for Shay-Shay.

This is a deliberately opt-in bundled plugin.  It composes the existing
adapter-neutral domain contract; it does not own a registry, task store, or
parallel lifecycle service.
"""

from __future__ import annotations

from .commands import register_cli, run_operator_command


def register(ctx) -> None:
    """Register ``shay operator`` only when the owner enables this plugin."""
    ctx.register_cli_command(
        name="operator",
        help="Inspect durable Shay tasks and runs",
        setup_fn=register_cli,
        handler_fn=run_operator_command,
        description=(
            "Operator view over the shared Shay client contract. "
            "The plugin is disabled by default and never grants write authority."
        ),
    )


__all__ = ["register"]
