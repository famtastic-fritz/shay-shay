import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig


def _ensure_telegram_mock():
    if "telegram" in sys.modules and hasattr(sys.modules["telegram"], "__file__"):
        return

    telegram_mod = MagicMock()
    telegram_mod.ext.ContextTypes.DEFAULT_TYPE = type(None)
    telegram_mod.constants.ParseMode.MARKDOWN_V2 = "MarkdownV2"
    telegram_mod.constants.ChatType.GROUP = "group"
    telegram_mod.constants.ChatType.SUPERGROUP = "supergroup"
    telegram_mod.constants.ChatType.CHANNEL = "channel"
    telegram_mod.constants.ChatType.PRIVATE = "private"

    # Provide real exception classes so ``except (NetworkError, ...)`` in
    # connect() doesn't blow up with "catching classes that do not inherit
    # from BaseException" when another xdist worker pollutes sys.modules.
    telegram_mod.error.NetworkError = type("NetworkError", (OSError,), {})
    telegram_mod.error.TimedOut = type("TimedOut", (OSError,), {})
    telegram_mod.error.BadRequest = type("BadRequest", (Exception,), {})

    for name in ("telegram", "telegram.ext", "telegram.constants", "telegram.request"):
        sys.modules.setdefault(name, telegram_mod)
    sys.modules.setdefault("telegram.error", telegram_mod.error)


_ensure_telegram_mock()

from gateway.platforms.telegram import TelegramAdapter  # noqa: E402


@pytest.fixture(autouse=True)
def _no_auto_discovery(monkeypatch):
    """Disable DoH auto-discovery so connect() uses the plain builder chain."""
    async def _noop():
        return []
    monkeypatch.setattr("gateway.platforms.telegram.discover_fallback_ips", _noop)
    # Mock HTTPXRequest so the builder chain doesn't fail
    monkeypatch.setattr("gateway.platforms.telegram.HTTPXRequest", lambda **kwargs: MagicMock())


@pytest.mark.asyncio
async def test_connect_rejects_same_host_token_lock(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="secret-token"))

    monkeypatch.setattr(
        "gateway.status.acquire_scoped_lock",
        lambda scope, identity, metadata=None: (False, {"pid": 4242}),
    )

    ok = await adapter.connect()

    assert ok is False
    assert adapter.fatal_error_code == "telegram-bot-token_lock"
    assert adapter.has_fatal_error is True
    assert "already in use" in adapter.fatal_error_message


@pytest.mark.asyncio
async def test_polling_conflict_retries_before_fatal(monkeypatch):
    """A single 409 should trigger a retry, not an immediate fatal error."""
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))
    fatal_handler = AsyncMock()
    adapter.set_fatal_error_handler(fatal_handler)

    monkeypatch.setattr(
        "gateway.status.acquire_scoped_lock",
        lambda scope, identity, metadata=None: (True, None),
    )
    monkeypatch.setattr(
        "gateway.status.release_scoped_lock",
        lambda scope, identity: None,
    )

    captured = {}

    async def fake_start_polling(**kwargs):
        captured["error_callback"] = kwargs["error_callback"]

    updater = SimpleNamespace(
        start_polling=AsyncMock(side_effect=fake_start_polling),
        stop=AsyncMock(),
        running=True,
    )
    bot = SimpleNamespace(set_my_commands=AsyncMock(), delete_webhook=AsyncMock())
    app = SimpleNamespace(
        bot=bot,
        updater=updater,
        add_handler=MagicMock(),
        initialize=AsyncMock(),
        start=AsyncMock(),
    )
    builder = MagicMock()
    builder.token.return_value = builder
    builder.request.return_value = builder
    builder.get_updates_request.return_value = builder
    builder.build.return_value = app
    monkeypatch.setattr("gateway.platforms.telegram.Application", SimpleNamespace(builder=MagicMock(return_value=builder)))

    # Speed up retries for testing
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    ok = await adapter.connect()

    assert ok is True
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)
    assert callable(captured["error_callback"])

    conflict = type("Conflict", (Exception,), {})

    # First conflict: should retry, NOT be fatal
    captured["error_callback"](conflict("Conflict: terminated by other getUpdates request"))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    # Give the scheduled task a chance to run
    for _ in range(10):
        await asyncio.sleep(0)

    assert adapter.has_fatal_error is False, "First conflict should not be fatal"
    assert adapter._polling_conflict_count == 0, "Count should reset after successful retry"


@pytest.mark.asyncio
async def test_polling_conflict_becomes_fatal_after_retries(monkeypatch):
    """After exhausting retries, the conflict should become fatal."""
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))
    fatal_handler = AsyncMock()
    adapter.set_fatal_error_handler(fatal_handler)

    monkeypatch.setattr(
        "gateway.status.acquire_scoped_lock",
        lambda scope, identity, metadata=None: (True, None),
    )
    monkeypatch.setattr(
        "gateway.status.release_scoped_lock",
        lambda scope, identity: None,
    )

    captured = {}

    async def fake_start_polling(**kwargs):
        captured["error_callback"] = kwargs["error_callback"]

    # Make start_polling fail on retries to exhaust retries
    call_count = {"n": 0}

    async def failing_start_polling(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First call (initial connect) succeeds
            captured["error_callback"] = kwargs["error_callback"]
        else:
            # Retry calls fail
            raise Exception("Conflict: terminated by other getUpdates request")

    updater = SimpleNamespace(
        start_polling=AsyncMock(side_effect=failing_start_polling),
        stop=AsyncMock(),
        running=True,
    )
    bot = SimpleNamespace(set_my_commands=AsyncMock(), delete_webhook=AsyncMock())
    app = SimpleNamespace(
        bot=bot,
        updater=updater,
        add_handler=MagicMock(),
        initialize=AsyncMock(),
        start=AsyncMock(),
    )
    builder = MagicMock()
    builder.token.return_value = builder
    builder.request.return_value = builder
    builder.get_updates_request.return_value = builder
    builder.build.return_value = app
    monkeypatch.setattr("gateway.platforms.telegram.Application", SimpleNamespace(builder=MagicMock(return_value=builder)))

    # Speed up retries for testing
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    ok = await adapter.connect()
    assert ok is True

    conflict = type("Conflict", (Exception,), {})

    # One conflict must drive the stopped poller through its complete bounded
    # retry ladder even though failed restarts cannot emit another callback.
    await adapter._handle_polling_conflict(
        conflict("Conflict: terminated by other getUpdates request")
    )

    # After 3 failed retries the internally progressed fourth state exceeds
    # MAX_CONFLICT_RETRIES (3), entering the fatal branch.
    assert adapter.fatal_error_code == "telegram_polling_conflict", (
        f"Expected fatal after 4 conflicts, got code={adapter.fatal_error_code}, "
        f"count={adapter._polling_conflict_count}"
    )
    assert adapter.has_fatal_error is True
    fatal_handler.assert_awaited_once()
    assert updater.start_polling.await_count == 4  # initial connect + 3 retries


@pytest.mark.asyncio
async def test_connect_marks_retryable_fatal_error_for_startup_network_failure(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))

    monkeypatch.setattr(
        "gateway.status.acquire_scoped_lock",
        lambda scope, identity, metadata=None: (True, None),
    )
    monkeypatch.setattr(
        "gateway.status.release_scoped_lock",
        lambda scope, identity: None,
    )

    builder = MagicMock()
    builder.token.return_value = builder
    builder.request.return_value = builder
    builder.get_updates_request.return_value = builder
    app = SimpleNamespace(
        bot=SimpleNamespace(delete_webhook=AsyncMock(), set_my_commands=AsyncMock()),
        updater=SimpleNamespace(),
        add_handler=MagicMock(),
        initialize=AsyncMock(side_effect=RuntimeError("Temporary failure in name resolution")),
        start=AsyncMock(),
    )
    builder.build.return_value = app
    monkeypatch.setattr("gateway.platforms.telegram.Application", SimpleNamespace(builder=MagicMock(return_value=builder)))

    ok = await adapter.connect()

    assert ok is False
    assert adapter.fatal_error_code == "telegram_connect_error"
    assert adapter.fatal_error_retryable is True
    assert "Temporary failure in name resolution" in adapter.fatal_error_message


@pytest.mark.asyncio
async def test_connect_clears_webhook_before_polling(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))

    monkeypatch.setattr(
        "gateway.status.acquire_scoped_lock",
        lambda scope, identity, metadata=None: (True, None),
    )
    monkeypatch.setattr(
        "gateway.status.release_scoped_lock",
        lambda scope, identity: None,
    )

    updater = SimpleNamespace(
        start_polling=AsyncMock(),
        stop=AsyncMock(),
        running=True,
    )
    bot = SimpleNamespace(
        delete_webhook=AsyncMock(),
        set_my_commands=AsyncMock(),
    )
    app = SimpleNamespace(
        bot=bot,
        updater=updater,
        add_handler=MagicMock(),
        initialize=AsyncMock(),
        start=AsyncMock(),
    )
    builder = MagicMock()
    builder.token.return_value = builder
    builder.request.return_value = builder
    builder.get_updates_request.return_value = builder
    builder.build.return_value = app
    monkeypatch.setattr(
        "gateway.platforms.telegram.Application",
        SimpleNamespace(builder=MagicMock(return_value=builder)),
    )

    ok = await adapter.connect()

    assert ok is True
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)


@pytest.mark.asyncio
async def test_disconnect_skips_inactive_updater_and_app(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))

    updater = SimpleNamespace(running=False, stop=AsyncMock())
    app = SimpleNamespace(
        updater=updater,
        running=False,
        stop=AsyncMock(),
        shutdown=AsyncMock(),
    )
    adapter._app = app

    warning = MagicMock()
    monkeypatch.setattr("gateway.platforms.telegram.logger.warning", warning)

    await adapter.disconnect()

    updater.stop.assert_not_awaited()
    app.stop.assert_not_awaited()
    app.shutdown.assert_awaited_once()
    warning.assert_not_called()


def test_disconnect_cancels_conflict_retry_before_it_restarts_polling(monkeypatch):
    asyncio.run(_exercise_disconnect_during_conflict_retry(monkeypatch))


async def _exercise_disconnect_during_conflict_retry(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))
    adapter._mark_connected()
    retry_sleeping = asyncio.Event()

    async def cancellable_retry_delay(_delay):
        retry_sleeping.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            # Even if the delay wakes instead of propagating cancellation,
            # the stopping guard must prevent restart/recursion/fatal state.
            return

    monkeypatch.setattr("gateway.platforms.telegram.asyncio.sleep", cancellable_retry_delay)
    updater = SimpleNamespace(
        running=True,
        stop=AsyncMock(),
        start_polling=AsyncMock(side_effect=RuntimeError("must not restart")),
    )
    adapter._app = SimpleNamespace(
        updater=updater,
        running=False,
        stop=AsyncMock(),
        shutdown=AsyncMock(),
    )
    adapter._drain_polling_connections = AsyncMock()
    task = asyncio.create_task(
        adapter._handle_polling_conflict(Exception("Conflict: other getUpdates"))
    )
    adapter._polling_error_task = task
    await retry_sleeping.wait()

    await adapter.disconnect()

    assert task.done()
    assert adapter._polling_error_task is None
    updater.start_polling.assert_not_awaited()
    adapter._drain_polling_connections.assert_not_awaited()
    assert adapter.has_fatal_error is False


def test_stale_reconnect_generation_cannot_mutate_later_connection(monkeypatch):
    asyncio.run(_exercise_stale_reconnect_generation(monkeypatch))


@pytest.mark.asyncio
async def test_network_failure_after_conflict_uses_network_ladder(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="fixture"))
    updater = SimpleNamespace(
        running=True, stop=AsyncMock(),
        start_polling=AsyncMock(side_effect=[RuntimeError("Connection refused"), None]),
    )
    adapter._app = SimpleNamespace(updater=updater, bot=SimpleNamespace())
    adapter._drain_polling_connections = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    await adapter._handle_polling_conflict(RuntimeError("Conflict: other getUpdates"))

    assert updater.start_polling.await_count == 2
    assert adapter._polling_conflict_count == 1
    assert adapter._polling_network_error_count == 0
    assert not adapter.has_fatal_error
    pending = list(adapter._polling_recovery_tasks)
    assert all(task in adapter._background_tasks for task in pending)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


@pytest.mark.asyncio
async def test_network_retry_remains_callback_guard_owner(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="fixture"))
    adapter._app = SimpleNamespace(updater=SimpleNamespace(
        running=True, stop=AsyncMock(), start_polling=AsyncMock(side_effect=RuntimeError("Timed out")),
    ))
    adapter._drain_polling_connections = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    await adapter._handle_polling_network_error(RuntimeError("Bad Gateway"))
    retry = adapter._polling_error_task
    assert retry in adapter._polling_recovery_tasks
    assert retry in adapter._background_tasks
    retry.cancel()
    await asyncio.gather(retry, return_exceptions=True)


async def _exercise_stale_reconnect_generation(monkeypatch):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="***"))
    adapter._connection_generation = 1
    old_delay_started = asyncio.Event()
    release_old_delay = asyncio.Event()

    async def controlled_sleep(_delay):
        old_delay_started.set()
        await release_old_delay.wait()

    monkeypatch.setattr("gateway.platforms.telegram.asyncio.sleep", controlled_sleep)
    old_updater = SimpleNamespace(running=True, stop=AsyncMock(), start_polling=AsyncMock())
    adapter._app = SimpleNamespace(updater=old_updater, bot=SimpleNamespace())
    adapter._drain_polling_connections = AsyncMock()

    stale = asyncio.create_task(
        adapter._handle_polling_network_error(RuntimeError("old"), generation=1)
    )
    await old_delay_started.wait()

    adapter._connection_generation = 2
    new_updater = SimpleNamespace(running=True, stop=AsyncMock(), start_polling=AsyncMock())
    adapter._app = SimpleNamespace(updater=new_updater, bot=SimpleNamespace())
    release_old_delay.set()
    await stale

    old_updater.stop.assert_not_awaited()
    old_updater.start_polling.assert_not_awaited()
    new_updater.stop.assert_not_awaited()
    new_updater.start_polling.assert_not_awaited()
    adapter._drain_polling_connections.assert_not_awaited()
