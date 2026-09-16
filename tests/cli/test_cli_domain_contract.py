"""CLI-facing compatibility checks for the shared domain contract."""

from shay_cli.domain_contract import (
    Capability,
    ErrorObject,
    PROTOCOL_VERSION,
    Session,
    Usage,
    contract_fixture,
)


def test_cli_fixture_contains_all_versioned_public_object_kinds():
    fixture = contract_fixture(client="cli")
    assert fixture["protocol"] == PROTOCOL_VERSION
    assert fixture["capability"]["object"] == "shay.capability"
    assert fixture["session"]["object"] == "shay.session"
    assert fixture["approval"]["object"] == "shay.approval"
    assert fixture["usage"]["object"] == "shay.usage"
    assert fixture["error"]["object"] == "shay.error"


def test_cli_and_other_transport_projections_have_identical_schema_keys():
    cli = contract_fixture(client="cli")
    tui = contract_fixture(client="tui")
    api = contract_fixture(client="api")
    acp = contract_fixture(client="acp")
    assert cli.keys() == tui.keys() == api.keys() == acp.keys()
    for name in ("capability", "session", "approval", "usage", "error"):
        assert cli[name].keys() == tui[name].keys() == api[name].keys() == acp[name].keys()


def test_optional_projections_are_explicitly_unavailable():
    # The constructors remain usable by transports that only have an absent
    # projection; no empty value is used to claim effect/memory authority.
    assert Capability(name="task.lifecycle").as_dict()["available"] is False
    assert Session(session_id="s").as_dict()["status"] == "unknown"
    assert Usage().as_dict()["cost_usd"] is None
    assert ErrorObject(code="x", message="bad").as_dict()["protocol"] == PROTOCOL_VERSION
