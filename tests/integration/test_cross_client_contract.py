"""Cross-transport lifecycle journey against one durable Kanban ledger."""

from pathlib import Path

from shay_cli.domain_contract import DomainService, contract_fixture
from shay_cli.kanban_db import claim_task, connect, create_task, record_run_event


def test_cli_api_tui_acp_share_one_task_and_event_cursor(tmp_path: Path):
    conn = connect(tmp_path / "kanban.db")
    task_id = create_task(conn, title="cross-client", body="one ledger")
    claim_task(conn, task_id, claimer="api")
    service = DomainService(conn)

    # These are the four existing transport identities; the service is the
    # only lifecycle owner and each adapter sees the same object keys/status.
    fixtures = [contract_fixture(task_id=task_id, client=name) for name in ("cli", "tui", "api", "acp")]
    assert {f["protocol"] for f in fixtures} == {"shay.client.v1"}
    assert {f["session"]["task_id"] for f in fixtures} == {task_id}

    event_id = record_run_event(conn, task_id, "run.started", {"client": "api"})
    for client in ("cli", "tui", "acp"):
        page = service.list_task_events(task_id, event_id - 1)
        assert [event["event_id"] for event in page["events"]] == [event_id]
        assert page["events"][0]["payload"]["client"] == "api"
        assert contract_fixture(task_id=task_id, client=client)["protocol"] == "shay.client.v1"

    # The task snapshot remains stable after reconnecting through another
    # adapter because it is read from the same durable connection/ledger.
    assert service.inspect_task(task_id)["task_id"] == task_id
