# Shay command surface map — 2026-06-13

## Scope

Mission-required command surface review for:
- `shay doctor`
- `shay sessions`
- `shay status`
- `shay mcp`
- `shay gateway`
- `shay model` and slash `/model`
- skills list/view
- memory/session search
- config validation
- diagnostics/provider/MCP/gateway health commands

Worktree scope:
- repo: `/Users/famtasticfritz/famtastic/shay-shay-main-sync-20260613`
- branch: `docs/hermes-removal-control-pr-20260613`
- no live mutation performed in this lane

## Evidence sources

Verified by direct command execution against worktree code using the shared main-checkout virtualenv:
- `"/Users/famtasticfritz/famtastic/shay-shay/.venv/bin/python" -m shay_cli.main --help`
- `... doctor --help`
- `... doctor`
- `... status --help`
- `... status`
- `... sessions --help`
- `... sessions list --help`
- `... sessions browse --help`
- `... sessions stats`
- `... sessions list --limit 5`
- `... mcp --help`
- `... mcp list`
- `... mcp test basic-memory`
- `... gateway --help`
- `... gateway status --help`
- `... gateway status`
- `... model --help`
- `... skills --help`
- `... skills list --help`
- `... skills list --source all`
- `... skills inspect --help`
- `... memory --help`
- `... memory status`
- `... config --help`
- `... config check --help`
- `... config check`

Code-read evidence:
- `shay_cli/main.py`
- `shay_cli/commands.py`
- `shay_state.py`
- `shay_cli/web_server.py`

Status labels used in this doc:
- verified: command exists and behavior/help was observed directly in this lane
- documented: code advertises the surface, but this lane did not fully execute the path
- unknown: mission-targeted surface is not clearly exposed, is ambiguous, or differs between layers

## Executive findings

1. The required top-level CLI surfaces all exist except a literal `skills view` command; the current concrete surface is `shay skills inspect`.
2. `shay doctor` is the main provider-health and dependency-health command. It performs parallel connectivity checks, tool availability checks, config/version checks, and directory/runtime checks.
3. `shay status` is lighter-weight than `doctor` and reports environment, provider selection, key presence, gateway service state, scheduled jobs, and active sessions.
4. `shay gateway status` is the clearest gateway-health command. In this lane it reported a running launchd service plus a stale service definition warning.
5. `shay mcp list` and `shay mcp test <name>` provide the verified MCP-health surface. `mcp test basic-memory` successfully connected and enumerated 23 tools.
6. Session management is strong, but non-interactive session search is weak at the CLI layer. `shay sessions browse` is documented as interactive browse/search/resume, while full-text session search is clearly implemented in storage and web API code, not as a dedicated `shay sessions search` command.
7. Memory search is not exposed as a top-level `shay memory search` CLI command. Memory retrieval/search currently appears to live through MCP servers/tools rather than the `shay memory` command group.
8. `/model` is real in the slash-command layer and is session-scoped there. `shay model` is a different top-level CLI flow focused on interactive provider/model setup.

## Command surface map

### 1) `shay doctor`

Status: verified

Observed surface:
- `shay doctor`
- `shay doctor --fix`

Observed help:
- description: diagnose issues with Shay-Shay setup
- only explicit flag: `--fix`

Observed behavior in this lane:
- confirmed Python and active virtualenv
- checked required Python packages
- checked `~/.shay/.env`, `~/.shay/config.yaml`, and config version
- checked auth-provider state
- checked directory structure including `state.db`
- ran parallel API connectivity checks
- reported tool availability including `session_search`
- checked Skills Hub state
- checked memory provider state
- reported command installation issue for this worktree (`shay` entry point missing from this worktree venv/bin/.venv/bin)

Major health finding:
- this is the strongest verified provider/diagnostics command in the current surface

Caveats:
- `--fix` exists but was not executed because it can mutate config/install state

### 2) `shay status`

Status: verified

Observed surface:
- `shay status`
- `shay status --all`
- `shay status --deep`

Observed behavior in this lane:
- reported current project path and Python version
- reported selected model/provider
- reported masked key/auth presence
- reported messaging platform configuration status
- reported gateway service status
- reported scheduled job counts and active session counts

Interpretation:
- good at current state summary
- weaker than `doctor` for root-cause diagnostics
- useful as a fast “is the system broadly alive?” command

### 3) `shay sessions`

Status: verified

Observed top-level subcommands:
- `list`
- `export`
- `delete`
- `prune`
- `stats`
- `rename`
- `browse`

Verified subcommand details:
- `shay sessions list [--source SOURCE] [--limit LIMIT]`
- `shay sessions browse [--source SOURCE] [--limit LIMIT]`
- `shay sessions stats`

Observed behavior in this lane:
- `stats` reported 570 sessions, 20367 messages, 322.2 MB database, dominant source `cli`
- `list --limit 5` returned recent sessions with title/preview/last-active/id columns
- `browse` help explicitly says interactive “browse, search, and resume sessions”

Session search finding:
- documented interactive search exists via `browse`
- verified non-interactive full-text session search command does not appear in the `sessions` CLI group
- code in `shay_state.py` confirms FTS5-backed session/message search exists in the storage layer
- code in `shay_cli/web_server.py` exposes `/api/sessions/search` over the dashboard API

Conclusion:
- session search capability exists in the system
- dedicated CLI search surface is incomplete/absent

### 4) `shay mcp`

Status: verified

Observed top-level subcommands:
- `serve`
- `add`
- `remove` / `rm`
- `list` / `ls`
- `test`
- `configure` / `config`
- `login`

Verified health-oriented surface:
- `shay mcp list`
- `shay mcp test <name>`

Observed behavior in this lane:
- `mcp list` showed three configured servers: `obsidian`, `basic-memory`, `vault-search`
- `mcp test basic-memory` connected successfully in ~2.5s and discovered 23 tools

Interpretation:
- `mcp list` is inventory/status
- `mcp test` is the clearest verified MCP connectivity/health check
- `mcp configure` is documented but not exercised here because it changes tool-selection state

### 5) `shay gateway`

Status: verified

Observed top-level subcommands:
- `run`
- `start`
- `stop`
- `restart`
- `status`
- `install`
- `uninstall`
- `list`
- `setup`
- `migrate-legacy`

Verified health-oriented surface:
- `shay gateway status [--deep] [--full] [--system]`
- `shay gateway list`

Observed behavior in this lane:
- `gateway status` reported the launchd plist path
- reported service definition stale relative to current install
- reported service loaded and running with PID
- showed underlying program arguments

Interpretation:
- `gateway status` is the primary gateway-health command
- `gateway migrate-legacy` is an important rename-cleanup/admin command, not a live health probe
- lifecycle commands (`start/stop/restart/install/uninstall`) exist but were not executed because they mutate live service state

### 6) `shay model` and slash `/model`

Top-level CLI `shay model`
- status: verified
- observed behavior: help shows an interactive provider/model flow with Nous-login related flags (`--portal-url`, `--inference-url`, `--client-id`, `--scope`, `--no-browser`, `--timeout`, `--ca-bundle`, `--insecure`)
- code confirms `cmd_model()` requires a TTY and is the interactive provider/model picker

Slash `/model`
- status: documented
- `shay_cli/commands.py` registers `model` with alias `provider` and args hint `[model] [--provider name] [--global]`
- description in slash registry: “Switch model for this session”
- this implies a session-scoped runtime control surface distinct from top-level `shay model`

Key finding:
- `shay model` and `/model` are not equivalent UX surfaces
- `shay model` = interactive default/provider setup flow
- `/model` = in-session model switching surface

### 7) Skills list/view

Status: partially verified

Verified commands:
- `shay skills list`
- `shay skills list --source {all,hub,builtin,local}`
- `shay skills inspect <identifier>`

Observed behavior in this lane:
- `skills list --source all` enumerated installed skills and sources during the earlier pass, ending with `3 hub-installed, 71 builtin, 100 local — 174 enabled, 0 disabled`
- follow-on runtime-truth audit later observed `shay skills list` ending with `3 hub-installed, 71 builtin, 102 local — 176 enabled, 0 disabled`, proving this surface changes over time and should be timestamped
- `skills inspect --help` exists and is the preview/view-like path

Finding:
- mission wording says “skills list/view”
- literal current surface is `list` + `inspect`, not `view`
- slash-command registry also advertises `skills` subcommands `search`, `browse`, `inspect`, `install`

### 8) Memory and session search

Memory search
- status: unknown at top-level CLI; documented via MCP/tooling
- verified `shay memory` subcommands are only `setup`, `status`, `off`, `reset`
- verified `shay memory status` reports provider/plugin state, not searchable memory content
- verified `basic-memory` MCP server exposes search/read/context tools and passed `mcp test`

Session search
- status: partially verified
- interactive session search is documented in `shay sessions browse`
- system-level full-text session search is documented in code (`shay_state.py` FTS5, `web_server.py` `/api/sessions/search`)
- no verified dedicated non-interactive `shay sessions search` command exists

### 9) Config validation

Status: verified

Observed commands:
- `shay config show`
- `shay config edit`
- `shay config set`
- `shay config path`
- `shay config env-path`
- `shay config check`
- `shay config migrate`

Observed behavior in this lane:
- `config check` reported config version status plus a long required/optional env inventory with tool-mapping hints for some keys

Interpretation:
- `config check` is the main verified config validation command
- `config migrate` exists for config-shape upgrades but was not executed because it can write changes

### 10) Diagnostics/provider/MCP/gateway health commands

Verified primary commands by area:

Provider and runtime diagnostics
- `shay doctor`
- `shay status`
- `shay config check`

MCP health
- `shay mcp list`
- `shay mcp test <name>`

Gateway health
- `shay gateway status`
- `shay gateway list`

Session store health
- `shay sessions stats`
- `shay sessions list`

Memory/provider state
- `shay memory status`

Important gap:
- there is no single unified `shay health` or `shay diagnostics` super-command
- health is split across `doctor`, `status`, `config check`, `gateway status`, and `mcp test`

## Surface classification table

| Surface | Commands | Status | Notes |
| --- | --- | --- | --- |
| general diagnostics | `shay doctor` | verified | strongest provider/dependency diagnostics |
| runtime summary | `shay status` | verified | fast overview, less deep than doctor |
| session inventory | `shay sessions list`, `stats`, `browse` | verified | management is strong |
| session full-text search | interactive `browse`; web API `/api/sessions/search` | partial | no dedicated CLI `sessions search` found |
| MCP inventory/health | `shay mcp list`, `shay mcp test <name>` | verified | clear health surface |
| gateway health | `shay gateway status` | verified | reported stale launchd definition in this lane |
| gateway service lifecycle | `start/stop/restart/install/uninstall` | documented | intentionally not executed |
| model setup | `shay model` | verified | TTY-only interactive picker |
| in-session model switch | `/model` | documented | slash registry only in this lane |
| skills listing | `shay skills list` | verified | inventory works |
| skills “view” | `shay skills inspect` | verified | `inspect` is the current view-equivalent |
| memory provider status | `shay memory status` | verified | status only, not search |
| memory search | via MCP servers/tools | partial | not a top-level `shay memory search` command |
| config validation | `shay config check` | verified | validated config/env surface |

## Observed discrepancies and gaps

1. `skills view` vs actual surface
- mission wording says view
- actual current command is `shay skills inspect`

2. `shay model` vs `/model`
- same concept area, different semantics
- top-level command is setup/config oriented
- slash command is session runtime oriented

3. session search CLI gap
- backend/storage/web search exists
- dedicated non-interactive CLI search command was not found

4. memory search CLI gap
- memory provider management exists
- memory search currently appears MCP-first rather than `shay memory` CLI-first

5. split health surface
- diagnostics are useful but fragmented
- users must know whether to run `doctor`, `status`, `config check`, `gateway status`, or `mcp test`

## Recommended canonical phrasing for this mission branch

Use the following wording in downstream control docs:
- “Shay has verified diagnostics surfaces for general runtime health (`shay doctor`, `shay status`, `shay config check`), gateway health (`shay gateway status`), and MCP connectivity (`shay mcp test`).”
- “Skills are verified through `shay skills list` and `shay skills inspect`; there is not currently a literal `shay skills view` command.”
- “Session search exists, but the clean non-interactive CLI surface is incomplete; interactive search is documented via `shay sessions browse`, and full-text search is implemented in the session DB and dashboard API.”
- “Memory search is presently better understood as an MCP/tool surface than a `shay memory` CLI surface.”

## Bottom line

Required mission surfaces are mostly present and real.

Strongly verified:
- `shay doctor`
- `shay status`
- `shay sessions`
- `shay mcp`
- `shay gateway`
- `shay model`
- `shay skills list`
- `shay skills inspect`
- `shay memory status`
- `shay config check`

Needs careful wording:
- `/model` is documented from slash-command code, not directly exercised here
- session search exists but is not cleanly exposed as `shay sessions search`
- memory search exists through MCP/tooling, not as a verified top-level `shay memory search` command
