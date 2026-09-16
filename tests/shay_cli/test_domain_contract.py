"""Contract-level tests for the adapter-neutral Kanban domain seam."""

from pathlib import Path

import pytest

from shay_cli.kanban_db import claim_task, connect, create_task, record_run_event
from shay_cli.domain_contract import (
    DomainContractError,
    DomainService,
    TaskObject,
    PROTOCOL_VERSION,
    contract_fixture,
    require_compatible_version,
)


def _service(tmp_path: Path) -> tuple[DomainService, str]:
    conn = connect(tmp_path / "kanban.db")
    task_id = create_task(conn, title="contract task", body="test", created_by="test")
    claim_task(conn, task_id, claimer="contract-test")
    return DomainService(conn), task_id


def test_inspection_and_replay_use_authoritative_identifiers(tmp_path: Path):
    service, task_id = _service(tmp_path)
    conn = service.connection
    first = record_run_event(conn, task_id, "message.delta", {"delta": "hi"})
    second = record_run_event(conn, task_id, "tool.completed", {"tool": "read"})

    snapshot = service.inspect_task(task_id)
    assert snapshot["object"] == "shay.task"
    assert snapshot["protocol"] == PROTOCOL_VERSION
    assert snapshot["task_id"] == task_id
    assert snapshot["run"]["task_id"] == task_id
    page = service.list_task_events(task_id, first)
    assert [event["event_id"] for event in page["events"]] == [second]
    assert page["next_event_id"] == second
    assert page["after_event_id"] == first


def test_cancel_is_durable_and_idempotent_then_retry_is_explicit(tmp_path: Path):
    service, task_id = _service(tmp_path)
    first = service.cancel_task(task_id, "operator")
    again = service.cancel_task(task_id, "operator")
    assert first["changed"] is True
    assert again["changed"] is True
    assert first["task"]["status"] == "blocked"
    retry = service.retry_task(task_id, "operator")
    assert retry["changed"] is True
    assert retry["task"]["status"] == "ready"


def test_resume_never_claims_a_worker(tmp_path: Path):
    service, task_id = _service(tmp_path)
    service.cancel_task(task_id, "operator")
    resumed = service.resume_task(task_id, "operator")
    assert resumed["task"]["status"] == "ready"
    assert resumed["task"]["run"]["outcome"] == "cancelled"
    assert resumed["changed"] is True


def test_unknown_fields_are_additive_and_major_versions_fail_closed():
    fixture = contract_fixture(client="api")
    fixture["future_field"] = {"safe": True}
    assert fixture["protocol"] == PROTOCOL_VERSION
    require_compatible_version(PROTOCOL_VERSION + ".1")
    with pytest.raises(DomainContractError) as exc:
        require_compatible_version("shay.client.v2")
    assert exc.value.code == "incompatible_version"


def test_missing_task_and_bad_cursor_have_stable_errors(tmp_path: Path):
    service, _ = _service(tmp_path)
    with pytest.raises(DomainContractError) as exc:
        service.inspect_task("missing")
    assert exc.value.code == "task_not_found"
    with pytest.raises(DomainContractError) as exc:
        service.list_task_events("missing", 0)
    assert exc.value.code == "task_not_found"


def test_populated_optional_projection_requires_schema_and_authority():
    with pytest.raises(DomainContractError, match="authority_ref"):
        TaskObject(task_id="t", effect={"schema_version": "shay.effect.v1"})
    with pytest.raises(DomainContractError, match="schema_version"):
        TaskObject(task_id="t", memory_provenance={"authority_ref": "r5"})
    valid = TaskObject(
        task_id="t",
        effect={
            "schema_version": "shay.effect.v1",
            "authority_ref": "r4-ledger",
            "effect_id": "e1",
            "status": "committed",
            "new_field": "ignored by old readers",
        },
    )
    assert valid.as_dict()["effect"]["authority_ref"] == "r4-ledger"
