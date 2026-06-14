from __future__ import annotations

import json
import sys

import pytest

from shay_cli import process as process_cli


def test_process_cli_log_list_show_and_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    payload = {
        "run_id": "run-cli-001",
        "plan_id": "plan-cli",
        "job_id": "job-cli",
        "task_id": "task-cli",
        "lane": "qa",
        "task_name": "CLI wiring test",
        "instruction_summary": "Verify the process command can log and inspect a run.",
        "tools_used": ["pytest"],
        "commands_run": ["pytest tests/shay_cli/test_process.py"],
        "validation_results": [{"check": "cli", "status": "passed", "message": "command surface works"}],
        "outcome": "success",
        "next_actions": ["Wire automatic emitters later."],
    }

    assert process_cli.cli_main(["log", "--json", json.dumps(payload)]) == 0
    logged_out = capsys.readouterr().out
    assert "Logged process run: run-cli-001" in logged_out
    assert "what happened:" in logged_out

    assert process_cli.cli_main(["list", "--limit", "5"]) == 0
    list_out = capsys.readouterr().out
    assert "run-cli-001" in list_out
    assert "CLI wiring test" in list_out

    assert process_cli.cli_main(["show", "run-cli-001"]) == 0
    show_out = capsys.readouterr().out
    show_record = json.loads(show_out)
    assert show_record["run_id"] == "run-cli-001"
    assert show_record["outcome"] == "success"

    assert process_cli.cli_main(["summary", "run-cli-001"]) == 0
    summary_out = capsys.readouterr().out
    assert "what worked:" in summary_out
    assert "improvement recommendation:" in summary_out


def test_process_cli_log_accepts_input_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    payload_path = tmp_path / "process-run.json"
    payload_path.write_text(
        json.dumps(
            {
                "run_id": "run-cli-file",
                "task_name": "File payload test",
                "instruction_summary": "Log a run from a JSON file payload.",
                "outcome": "success",
            }
        ),
        encoding="utf-8",
    )

    assert process_cli.cli_main(["log", "--input", str(payload_path)]) == 0
    out = capsys.readouterr().out
    assert "run-cli-file" in out


def test_process_cli_rejects_path_traversal_run_ids(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    payload = {
        "run_id": "../../outside-test",
        "task_name": "Traversal attempt",
        "instruction_summary": "Should be rejected.",
    }

    assert process_cli.cli_main(["log", "--json", json.dumps(payload)]) == 1
    log_out = capsys.readouterr().out
    assert "invalid payload" in log_out
    assert "run_id" in log_out

    assert process_cli.cli_main(["show", "../../outside-test"]) == 1
    show_out = capsys.readouterr().out
    assert "invalid run id" in show_out


def test_top_level_process_command_exits_nonzero_on_invalid_run_id(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    monkeypatch.setattr(sys, "argv", ["shay", "process", "show", "../../outside-test"])

    from shay_cli import main as shay_main

    with pytest.raises(SystemExit) as excinfo:
        shay_main.main()

    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert "invalid run id" in out
