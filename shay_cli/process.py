"""CLI subcommand: `shay process`.

Process intelligence MVP command surface:
- `shay process log`
- `shay process list`
- `shay process show <run_id>`
- `shay process summary [run_id]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent import process_intelligence


def _finish(args: argparse.Namespace, code: int) -> int:
    if code and getattr(args, "command", None) == "process":
        raise SystemExit(code)
    return code


def _load_payload(args: argparse.Namespace) -> dict:
    source_count = sum(
        1
        for enabled in (
            bool(getattr(args, "input", None)),
            bool(getattr(args, "json_payload", None)),
            bool(getattr(args, "stdin", False)),
        )
        if enabled
    )
    if source_count == 0:
        raise ValueError("Provide one payload source: --input, --json, or --stdin")
    if source_count > 1:
        raise ValueError("Choose exactly one payload source: --input, --json, or --stdin")

    if getattr(args, "input", None):
        path = Path(args.input)
        return json.loads(path.read_text(encoding="utf-8"))
    if getattr(args, "json_payload", None):
        return json.loads(args.json_payload)
    return json.loads(sys.stdin.read())


def _cmd_log(args: argparse.Namespace) -> int:
    try:
        payload = _load_payload(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"process: unable to load payload — {exc}")
        return 1

    if not isinstance(payload, dict):
        print("process: payload must be a JSON object")
        return 1

    try:
        record = process_intelligence.log_run(payload)
    except ValueError as exc:
        print(f"process: invalid payload — {exc}")
        return 1
    print(f"Logged process run: {record['run_id']}")
    print(f"Record: {process_intelligence.run_record_path(record['run_id'])}")
    print(f"Index:  {process_intelligence.ledger_index_path()}")
    print()
    print(process_intelligence.render_after_action_report(record))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    records = process_intelligence.list_run_records(limit=args.limit)
    if not records:
        print("No process runs logged yet.")
        return 0

    print(f"Recent process runs ({len(records)}):")
    for record in records:
        duration = process_intelligence._format_duration(record.get("duration_seconds"))
        print(
            f"- {record.get('run_id', '')} | lane={record.get('lane', '')} | "
            f"outcome={record.get('outcome', '')} | duration={duration}"
        )
        task_name = record.get("task_name", "") or "(unnamed task)"
        print(f"  task: {task_name}")
        print(f"  trigger: {record.get('instruction_summary', '') or '(not recorded)'}")
        print(
            f"  ids: plan={record.get('plan_id', '') or '-'} "
            f"job={record.get('job_id', '') or '-'} "
            f"task={record.get('task_id', '') or '-'}"
        )
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    try:
        record = process_intelligence.get_run_record(args.run_id)
    except ValueError as exc:
        print(f"process: invalid run id — {exc}")
        return 1
    if not record:
        print(f"No process run found for id: {args.run_id}")
        return 1
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    if getattr(args, "run_id", None):
        try:
            record = process_intelligence.get_run_record(args.run_id)
        except ValueError as exc:
            print(f"process: invalid run id — {exc}")
            return 1
        if not record:
            print(f"No process run found for id: {args.run_id}")
            return 1
    else:
        record = process_intelligence.latest_run_record()
        if not record:
            print("No process runs logged yet.")
            return 0
    print(process_intelligence.render_after_action_report(record))
    return 0


def process_command(args: argparse.Namespace) -> int:
    action = getattr(args, "process_action", None)
    if action in {"log"}:
        return _finish(args, _cmd_log(args))
    if action in {"list", "ls"}:
        return _finish(args, _cmd_list(args))
    if action == "show":
        return _finish(args, _cmd_show(args))
    if action in {"summary", "report"}:
        return _finish(args, _cmd_summary(args))
    print("Usage: shay process {log|list|show|summary}")
    return _finish(args, 0)


def register_cli(parent: argparse.ArgumentParser) -> None:
    parent.set_defaults(func=process_command)
    subs = parent.add_subparsers(dest="process_action")

    p_log = subs.add_parser(
        "log",
        help="Write one process run record from a JSON payload",
        description=(
            "Create one process-intelligence ledger record. Payloads are JSON-only "
            "so machine-written callers can emit structured metadata safely."
        ),
    )
    p_log.add_argument("--input", help="Path to a JSON payload file")
    p_log.add_argument("--json", dest="json_payload", help="Inline JSON payload")
    p_log.add_argument("--stdin", action="store_true", help="Read the JSON payload from stdin")
    p_log.set_defaults(func=process_command)

    p_list = subs.add_parser(
        "list",
        aliases=["ls"],
        help="List recent process run records",
    )
    p_list.add_argument("--limit", type=int, default=10, help="Max records to show (default: 10)")
    p_list.set_defaults(func=process_command)

    p_show = subs.add_parser("show", help="Show one process run record as JSON")
    p_show.add_argument("run_id", help="Run ID to display")
    p_show.set_defaults(func=process_command)

    p_summary = subs.add_parser(
        "summary",
        aliases=["report"],
        help="Generate a compact after-action report for the latest or requested run",
    )
    p_summary.add_argument("run_id", nargs="?", help="Optional run ID (defaults to latest)")
    p_summary.set_defaults(func=process_command)


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shay process")
    register_cli(parser)
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
