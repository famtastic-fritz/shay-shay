import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from run_agent import AIAgent
from shay_state import SessionDB


def _tool_defs():
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "search",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]


def _response(content="done", tool_calls=None):
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        reasoning=None,
        reasoning_content=None,
        reasoning_details=None,
    )
    choice = SimpleNamespace(
        message=message, finish_reason="tool_calls" if tool_calls else "stop"
    )
    return SimpleNamespace(choices=[choice], usage=None)


def _tool_call(call_id, secret):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="web_search", arguments=json.dumps({"query": secret}),
        ),
    )


def _agent(db):
    with (
        patch("run_agent.get_tool_definitions", return_value=_tool_defs()),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("shay_logging.setup_logging"),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key",
            base_url="https://example.invalid/v1",
            provider="test-provider",
            model="vendor/test-model",
            platform="telegram",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            session_db=db,
        )
    agent.client = MagicMock()
    agent._cached_system_prompt = "system secret"
    agent._use_prompt_caching = False
    agent.tool_delay = 0
    agent.compression_enabled = False
    agent.save_trajectories = False
    return agent


def _run(agent, prompt, responses):
    agent.client.chat.completions.create.side_effect = responses
    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
        patch("run_agent.handle_function_call", return_value="raw tool result secret"),
    ):
        return agent.run_conversation(prompt)


def test_run_conversation_records_safe_lifecycle_without_changing_transcript(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    agent = _agent(db)
    result = _run(agent, "raw prompt secret", [_response("raw completion secret")])

    assert result["messages"] == [
        {"role": "user", "content": "raw prompt secret"},
        {
            "role": "assistant",
            "content": "raw completion secret",
            "reasoning": None,
            "finish_reason": "stop",
        },
    ]
    receipt = db.get_turn_receipt(result["turn_id"])
    events = db.list_turn_events(result["turn_id"])
    assert (receipt.status, receipt.outcome) == ("succeeded", "completed")
    assert [event.event_type for event in events] == ["turn.started", "turn.finished"]
    assert events[0].payload == {
        "api_mode": "chat_completions",
        "model": "vendor/test-model",
        "provider": "test-provider",
        "source": "telegram",
        "surface": "telegram",
    }
    serialized = json.dumps([dict(event.payload) for event in events])
    assert "raw prompt secret" not in serialized
    assert "raw completion secret" not in serialized
    assert "system secret" not in serialized


def test_sequential_and_concurrent_tool_lifecycle_are_content_free(tmp_path):
    secret = "https://user:password@example.invalid/private raw arguments"
    for calls in (
        [_tool_call("seq-1", secret)],
        [_tool_call("con-1", secret + "?page=1"), _tool_call("con-2", secret + "?page=2")],
    ):
        db = SessionDB(tmp_path / f"state-{len(calls)}.db")
        agent = _agent(db)
        result = _run(agent, secret, [_response("", calls), _response("finished")])
        events = db.list_turn_events(result["turn_id"])
        tool_events = [event for event in events if event.event_type.startswith("tool.")]
        assert [event.event_type for event in tool_events].count("tool.started") == len(calls)
        assert [event.event_type for event in tool_events].count("tool.completed") == len(calls)
        completed = [event for event in tool_events if event.event_type == "tool.completed"]
        assert all(event.payload["outcome"] == "completed" for event in completed)
        assert secret not in json.dumps([dict(event.payload) for event in events])
        assert "raw tool result secret" not in json.dumps([dict(event.payload) for event in events])


def test_interrupted_and_failed_turn_receipts(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    agent = _agent(db)
    agent.interrupt()
    interrupted = _run(agent, "stop secret", [])
    receipt = db.get_turn_receipt(interrupted["turn_id"])
    assert (receipt.status, receipt.outcome) == ("abandoned", "interrupted")

    agent._ensure_db_session()
    failed_id = agent._begin_ledger_turn()
    agent._finish_ledger_turn(status="failed", outcome="failed")
    failed = db.get_turn_receipt(failed_id)
    assert (failed.status, failed.outcome) == ("failed", "failed")


def test_ledger_db_failure_is_nonfatal_and_does_not_change_messages(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    agent = _agent(db)
    with patch.object(db, "begin_turn", side_effect=RuntimeError("raw database secret")):
        result = _run(agent, "hello", [_response("unchanged")])
    assert "turn_id" not in result
    assert result["final_response"] == "unchanged"
    assert result["messages"] == [
        {"role": "user", "content": "hello"},
        {
            "role": "assistant",
            "content": "unchanged",
            "reasoning": None,
            "finish_reason": "stop",
        },
    ]


def test_early_error_return_terminalizes_receipt(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    agent = _agent(db)
    agent.provider = "nous"
    with (
        patch("agent.nous_rate_guard.nous_rate_limit_remaining", return_value=60),
        patch.object(agent, "_try_activate_fallback", return_value=False),
        patch.object(agent, "_persist_session"),
    ):
        result = agent.run_conversation("hello")

    receipt = db.get_turn_receipt(result["turn_id"])
    assert result["failed"] is True
    assert (receipt.status, receipt.outcome) == ("failed", "failed")


@pytest.mark.parametrize("surface", ["cli", "tui", "gateway", "dashboard", "acp", "cron", "telegram"])
def test_agent_surface_returns_same_durable_contract(tmp_path, surface):
    """Exercise the shared agent seam; this does not certify client UI rendering."""
    path = tmp_path / "state.db"
    db = SessionDB(path)
    agent = _agent(db)
    agent.platform = surface
    result = _run(agent, "fixture input", [_response("fixture reply")])
    turn_id = result["turn_id"]
    receipt = db.get_turn_receipt(turn_id)
    events = db.list_turn_events(turn_id)
    assert (receipt.status, receipt.outcome) == ("succeeded", "completed")
    assert events[0].payload["surface"] == surface
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    db.close()
    reopened = SessionDB(path)
    assert reopened.get_turn_receipt(turn_id) == receipt
    assert reopened.list_turn_events(turn_id) == events
    reopened.close()


@pytest.mark.parametrize("value", [
    "Bearer abcdefghijklmnop", "https://fixture:fixture-password@example.invalid/private",
    "arbitrary private text", "AKIAIOSFODNN7EXAMPLE", "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
    "sk-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "sk-proj-fictionalcredentialabcdefghijklmnop",
])
def test_runtime_metadata_is_checked_before_normalization(value):
    assert AIAgent._ledger_code(value) == "unknown"
    assert AIAgent._ledger_code("vendor/test-model", field="model") == "vendor/test-model"


@pytest.mark.parametrize("operation", ["begin_turn", "append_turn_event", "finish_turn"])
def test_ledger_failures_never_log_exception_content(tmp_path, caplog, operation):
    db = SessionDB(tmp_path / "state.db")
    agent = _agent(db)
    agent._ensure_db_session()
    with caplog.at_level("DEBUG", logger="run_agent"):
        agent._begin_ledger_turn()
        with patch.object(db, operation, side_effect=RuntimeError("fixture-password private request body")):
            if operation == "begin_turn":
                agent._begin_ledger_turn()
            elif operation == "append_turn_event":
                agent._append_ledger_event("tool.started", {"tool_name": "fixture"})
            else:
                agent._finish_ledger_turn(status="succeeded", outcome="completed")
    assert "fixture-password" not in caplog.text
    assert "private request body" not in caplog.text
    assert "Turn ledger unavailable" in caplog.text
    db.close()
