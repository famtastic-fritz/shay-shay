"""CLI and machine-readable operator view.

The command delegates all task lifecycle operations to
``shay_cli.domain_contract.DomainService``.  It intentionally does not query
Kanban tables itself and reports fields unavailable in the R6 ancestry as
``None`` rather than inventing provider, model, cost, approval, effect, or
memory-provenance values.
"""

from __future__ import annotations

import argparse
import json
import os
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping

from shay_cli.config import get_shay_home
from shay_cli.domain_contract import DomainContractError, DomainService, require_compatible_version
from shay_cli.kanban_db import kanban_db_path, connect
from shay_constants import display_shay_home

PROTOCOL_VERSION = "shay.client.v1"
OPERATOR_SCHEMA = "shay.operator-view.v1"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_UNAVAILABLE = 4
EXIT_ERROR = 5


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Emit canonical JSON without ANSI or human-only decorations",
    )


def register_cli(parser: argparse.ArgumentParser) -> None:
    """Build the plugin-owned ``shay operator`` parser tree."""
    parser.add_argument(
        "--board",
        default=None,
        help="Inspect the named durable board (defaults to Shay's active board)",
    )
    _add_json_flag(parser)
    sub = parser.add_subparsers(dest="operator_action", required=False)

    def add_task_action(name: str, help_text: str, *, actor: bool = False) -> argparse.ArgumentParser:
        child = sub.add_parser(name, help=help_text)
        child.add_argument("task_id", help="Durable Shay task identifier")
        if actor:
            child.add_argument("--actor", default=None, help="Operator identity (default: $USER or cli)")
        _add_json_flag(child)
        return child

    add_task_action("inspect", "Show task, run, usage, and authority state")
    status = add_task_action("status", "Alias for inspect")
    # Keep a named alias in the parser help while using the same dispatch.
    status.set_defaults(operator_action="inspect")
    events = add_task_action("events", "Show durable task events after a cursor")
    events.add_argument("--after", type=int, default=0, help="Return events after this event id")
    add_task_action("cancel", "Cancel the active durable run", actor=True)
    add_task_action("retry", "Retry a blocked or ready durable task", actor=True)
    add_task_action("resume", "Resume a blocked or interrupted durable task", actor=True)


def _json_dump(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _human(value: Mapping[str, Any], action: str) -> None:
    if action == "events":
        print(f"Task {value.get('task_id')} events (after {value.get('after_event_id', 0)})")
        for event in value.get("events", ()):
            print(f"  #{event.get('event_id')} {event.get('kind')}")
        if not value.get("events"):
            print("  No events.")
        return
    task = value.get("task") if isinstance(value.get("task"), Mapping) else value
    print(f"Task: {task.get('task_id', 'unavailable')}")
    print(f"Title: {task.get('title', '')}")
    print(f"State: {task.get('status', 'unavailable')}")
    run = task.get("run") if isinstance(task.get("run"), Mapping) else {}
    print(f"Run: {run.get('run_id', 'unavailable')}")
    print(f"Provider: {run.get('provider') or 'unavailable'}")
    print(f"Model: {run.get('model') or 'unavailable'}")
    usage = run.get("usage")
    if isinstance(usage, Mapping):
        cost = usage.get("cost_usd")
        print(f"Usage: {usage.get('total_tokens', 'unavailable')} tokens; cost {cost if cost is not None else 'unavailable'}")
    else:
        print("Usage: unavailable")
    print(f"Authority: inspect-only; proposed/executed file changes unavailable")
    print(f"Profile: {display_shay_home()}")


def _decorate_task(task: Mapping[str, Any]) -> dict[str, Any]:
    """Add explicit R7 capability/availability fields without false claims."""
    result = dict(task)
    run = result.get("run")
    if isinstance(run, Mapping):
        run_copy = dict(run)
        run_copy.setdefault("provider", None)
        run_copy.setdefault("model", None)
        run_copy.setdefault("usage", None)
        result["run"] = run_copy
    result.setdefault("authority", {"mode": "inspect", "write": False})
    result.setdefault("file_changes", {"proposed": None, "executed": None, "available": False})
    result.setdefault("typed_effect", {"available": False, "reason": "unavailable until R8 integrates R4"})
    result.setdefault("memory_provenance", None)
    result["protocol"] = PROTOCOL_VERSION
    result["operator_schema"] = OPERATOR_SCHEMA
    return result


def _with_service(args: argparse.Namespace, operation):
    db = kanban_db_path(board=getattr(args, "board", None))
    if not db.exists():
        raise DomainContractError(
            "ledger_unavailable",
            "Durable task ledger is unavailable; no database exists for this profile/board.",
            details={"path": str(db), "profile": display_shay_home()},
        )
    # The domain service is the sole lifecycle seam.  This module never
    # executes SQL or reads task tables directly.
    with closing(connect(db, board=getattr(args, "board", None))) as conn:
        require_compatible_version(PROTOCOL_VERSION)
        return operation(DomainService(conn))


def _actor(args: argparse.Namespace) -> str:
    return str(getattr(args, "actor", None) or os.environ.get("USER") or "cli").strip() or "cli"


def _action(args: argparse.Namespace) -> str:
    return str(getattr(args, "operator_action", None) or "inspect")


def operator_command(args: argparse.Namespace) -> int:
    """Execute an operator action and return a stable process exit code."""
    action = _action(args)
    task_id = getattr(args, "task_id", None)
    if not task_id:
        payload = {
            "object": "shay.error",
            "operator_schema": OPERATOR_SCHEMA,
            "protocol": PROTOCOL_VERSION,
            "code": "task_id_required",
            "message": "operator action requires a task_id",
            "details": {},
        }
        if getattr(args, "json", False):
            _json_dump(payload)
        else:
            print("Usage: shay operator <inspect|events|cancel|retry|resume> <task_id>")
        return EXIT_USAGE
    try:
        if action in {"inspect", "status"}:
            payload = _with_service(args, lambda svc: _decorate_task(svc.inspect_task(task_id)))
        elif action == "events":
            payload = _with_service(args, lambda svc: svc.list_task_events(task_id, getattr(args, "after", 0)))
        elif action == "cancel":
            payload = _with_service(args, lambda svc: svc.cancel_task(task_id, _actor(args)))
            payload["task"] = _decorate_task(payload["task"])
        elif action == "retry":
            payload = _with_service(args, lambda svc: svc.retry_task(task_id, _actor(args)))
            payload["task"] = _decorate_task(payload["task"])
        elif action == "resume":
            payload = _with_service(args, lambda svc: svc.resume_task(task_id, _actor(args)))
            payload["task"] = _decorate_task(payload["task"])
        else:
            raise DomainContractError("unknown_action", f"Unknown operator action: {action}")
    except DomainContractError as exc:
        payload = exc.as_dict()
        payload["operator_schema"] = OPERATOR_SCHEMA
        if getattr(args, "json", False):
            _json_dump(payload)
        else:
            print(f"Error: {exc.message}")
        return EXIT_NOT_FOUND if exc.code == "task_not_found" else EXIT_UNAVAILABLE if exc.code == "ledger_unavailable" else EXIT_ERROR
    except (OSError, ValueError, RuntimeError) as exc:
        payload = {
            "object": "shay.error", "operator_schema": OPERATOR_SCHEMA,
            "protocol": PROTOCOL_VERSION, "code": "operator_unavailable",
            "message": str(exc), "details": {},
        }
        if getattr(args, "json", False):
            _json_dump(payload)
        else:
            print(f"Error: {exc}")
        return EXIT_UNAVAILABLE

    if getattr(args, "json", False):
        _json_dump(payload)
    else:
        _human(payload, action)
    return EXIT_OK


def run_operator_command(args: argparse.Namespace) -> None:
    """Plugin handler that propagates stable nonzero exit codes to the CLI."""
    code = operator_command(args)
    if code:
        raise SystemExit(code)


def bundled_plugin_status() -> dict[str, Any]:
    """Return truthful install/enable state for ``shay doctor``."""
    manifest = Path(__file__).with_name("plugin.yaml")
    enabled = False
    try:
        from shay_cli.plugins import _get_enabled_plugins
        values = _get_enabled_plugins()
        enabled = bool(values and ("operator_view" in values or "operator-view" in values))
    except Exception:
        enabled = False
    return {
        "name": "operator_view",
        "installed": manifest.is_file(),
        "enabled": enabled,
        "available": bool(manifest.is_file() and enabled),
        "reason": None if enabled else "disabled by default; enable explicitly with `shay plugins enable operator_view`",
    }


__all__ = [
    "EXIT_ERROR", "EXIT_NOT_FOUND", "EXIT_OK", "EXIT_UNAVAILABLE", "EXIT_USAGE",
    "OPERATOR_SCHEMA", "bundled_plugin_status", "operator_command", "register_cli",
    "run_operator_command",
]
