---
sidebar_position: 2
title: "ACP Internals"
description: "How the ACP adapter works: lifecycle, sessions, event bridge, approvals, and tool rendering"
---

# ACP Internals

The ACP adapter wraps Shay-Shay' synchronous `AIAgent` in an async JSON-RPC stdio server.

Key implementation files:

- `acp_adapter/entry.py`
- `acp_adapter/server.py`
- `acp_adapter/session.py`
- `acp_adapter/events.py`
- `acp_adapter/permissions.py`
- `acp_adapter/tools.py`
- `acp_adapter/auth.py`
- `acp_registry/agent.json`

## Boot flow

```text
shay acp / shay-acp / python -m acp_adapter
  -> acp_adapter.entry.main()
  -> load ~/.shay/.env
  -> configure stderr logging
  -> construct Shay-ShayACPAgent
  -> acp.run_agent(agent, use_unstable_protocol=True)
```

Stdout is reserved for ACP JSON-RPC transport. Human-readable logs go to stderr.

## Major components

### `Shay-ShayACPAgent`

`acp_adapter/server.py` implements the ACP agent protocol.

Responsibilities:

- initialize / authenticate
- new/load/resume/fork/list/cancel session methods
- prompt execution
- session model switching
- wiring sync AIAgent callbacks into ACP async notifications

### `SessionManager`

`acp_adapter/session.py` tracks live ACP sessions.

Each session stores:

- `session_id`
- `agent`
- `cwd`
- `model`
- `history`
- `cancel_event`

The manager is thread-safe and supports:

- create
- get
- remove
- fork
- list
- cleanup
- cwd updates

### Event bridge

`acp_adapter/events.py` converts AIAgent callbacks into ACP `session_update` events.

Bridged callbacks:

- `tool_progress_callback`
- `thinking_callback` (currently set to `None` in the ACP bridge — reasoning is forwarded through `step_callback` instead)
- `step_callback`

Because `AIAgent` runs in a worker thread while ACP I/O lives on the main event loop, the bridge uses:

```python
asyncio.run_coroutine_threadsafe(...)
```

### Permission bridge

`acp_adapter/permissions.py` adapts dangerous terminal approval prompts into ACP permission requests.

Mapping:

- `allow_once` -> Shay-Shay `once`
- `allow_always` -> Shay-Shay `always`
- reject options -> Shay-Shay `deny`

Timeouts and bridge failures deny by default.

### Tool rendering helpers

`acp_adapter/tools.py` maps Shay-Shay tools to ACP tool kinds and builds editor-facing content.

Examples:

- `patch` / `write_file` -> file diffs
- `terminal` -> shell command text
- `read_file` / `search_files` -> text previews
- large results -> truncated text blocks for UI safety

## Session lifecycle

```text
new_session(cwd)
  -> create SessionState
  -> create AIAgent(platform="acp", enabled_toolsets=["shay-acp"])
  -> bind task_id/session_id to cwd override

prompt(..., session_id)
  -> extract text from ACP content blocks
  -> reset cancel event
  -> install callbacks + approval bridge
  -> run AIAgent in ThreadPoolExecutor
  -> update session history
  -> emit final agent message chunk
```

### Cancelation

`cancel(session_id)`:

- sets the session cancel event
- calls `agent.interrupt()` when available
- causes the prompt response to return `stop_reason="cancelled"`

### Forking

`fork_session()` deep-copies message history into a new live session, preserving conversation state while giving the fork its own session ID and cwd.

## Provider/auth behavior

ACP does not implement its own auth store.

Instead it reuses Shay-Shay' runtime resolver:

- `acp_adapter/auth.py`
- `shay_cli/runtime_provider.py`

So ACP advertises and uses the currently configured Shay-Shay provider/credentials.

## Working directory binding

ACP sessions carry an editor cwd.

The session manager binds that cwd to the ACP session ID via task-scoped terminal/file overrides, so file and terminal tools operate relative to the editor workspace.

## Duplicate same-name tool calls

The event bridge tracks tool IDs FIFO per tool name, not just one ID per name. This is important for:

- parallel same-name calls
- repeated same-name calls in one step

Without FIFO queues, completion events would attach to the wrong tool invocation.

## Approval callback restoration

ACP temporarily installs an approval callback on the terminal tool during prompt execution, then restores the previous callback afterward. This avoids leaving ACP session-specific approval handlers installed globally forever.

## Current limitations

- ACP sessions are persisted to the shared `~/.shay/state.db` (SessionDB) and transparently restored across process restarts; they appear in `session_search`
- non-text prompt blocks are currently ignored for request text extraction
- editor-specific UX varies by ACP client implementation

## Related files

- `tests/acp/` — ACP test suite
- `toolsets.py` — `shay-acp` toolset definition
- `shay_cli/main.py` — `shay acp` CLI subcommand
- `pyproject.toml` — `[acp]` optional dependency + `shay-acp` script
