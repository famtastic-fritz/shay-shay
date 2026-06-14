# Process Intelligence MVP

Status: implemented in the `shay-shay-process-intelligence-mvp-20260613` worktree branch

This is a manual CLI-backed process ledger MVP with reusable runtime helpers.
It is not yet universal automatic process capture across all Shay execution paths.

## Goal

Build the smallest safe runtime system that records enough structured execution metadata for Shay to answer:

- What did I do on that task?
- How long did it take?
- What tools/commands/files were involved?
- What decision did I make and why?
- What gaps did I open or close?
- What should happen next?

This is an MVP, not the final autonomous process-memory system.

## What is live now

1. A new top-level CLI command is wired into `shay`:
   - `shay process log`
   - `shay process list`
   - `shay process show <run_id>`
   - `shay process summary [run_id]`

2. A reusable runtime module exists at `agent/process_intelligence.py`.

3. Process records are written under `~/.shay/process-intelligence/` with two storage layers:
   - `runs/<run_id>.json` — full normalized record for direct lookup
   - `runs.jsonl` — append-style index for recent listing

4. Records are normalized so the required fields always exist, even when the payload is sparse.

5. Redaction happens before persistence, not after.

6. A compact after-action report helper is available through `process_intelligence.render_after_action_report()` and exposed through `shay process summary`.

## Storage layout

`~/.shay/process-intelligence/`

- `runs.jsonl`
- `runs/run-<timestamp>-<suffix>.json`

The implementation uses:
- atomic JSON write for each per-run record
- atomic JSONL rewrite for the index append step

That keeps the MVP simple while avoiding partial-file garbage from a crash mid-write.

## Required record fields

Every stored record contains these fields:

- `run_id`
- `plan_id`
- `job_id`
- `task_id`
- `parent_job_id`
- `lane`
- `task_name`
- `started_at`
- `ended_at`
- `duration_seconds`
- `instruction_summary`
- `instruction_hash`
- `full_instruction_stored`
- `tools_used`
- `commands_run`
- `files_inspected`
- `files_changed`
- `artifacts_created`
- `commits_created`
- `decisions_made`
- `assumptions_made`
- `gaps_opened`
- `gaps_closed`
- `validation_results`
- `safety_events`
- `blockers`
- `outcome`
- `next_actions`
- `lessons_learned`
- `redactions`

## Command surface

### 1. Log one run

Use one JSON payload source:

`shay process log --input /path/to/run.json`

or

`shay process log --json '{...}'`

or

`cat run.json | shay process log --stdin`

The payload is intentionally JSON-only for MVP. That keeps it machine-writable and avoids a giant flag matrix.

### 2. List recent runs

`shay process list --limit 10`

### 3. Show one full record

`shay process show <run_id>`

### 4. Generate a compact after-action report

`shay process summary`

or

`shay process summary <run_id>`

## Safety and privacy model

This MVP is deliberately conservative.

What it stores:
- IDs
- timestamps
- paths
- tool names
- commands after redaction
- structured summaries
- decisions / gaps / next actions

What it does not store by default:
- full raw instruction text
- private vault contents
- raw private session transcripts
- raw env values
- raw API keys / bearer tokens / passwords / cookies / private keys

Implementation details:
- `instruction_text` can be supplied for hashing, but the raw instruction is not persisted
- `full_instruction_stored` is forced to `false` in MVP
- env-like containers are replaced with a redacted placeholder
- secret-bearing strings are passed through `agent.redact.redact_sensitive_text(..., force=True)` before write
- transcript/body/messages/system_prompt style keys are replaced with content-not-captured sentinels

## What this MVP can answer well

If the run was logged, Shay can now answer:
- what task ran
- what lane it belonged to
- what triggered it
- how long it took
- what tools were used
- what commands/files were involved
- what validations passed or failed
- what blockers existed
- what gaps were opened or closed
- what next action was recommended

## What this MVP does NOT do yet

This is the part that matters.

1. It is not yet auto-emitted by every runtime path.
   Right now the capability is live through `shay process`, not universally auto-captured by chat sessions, tools, cron, or delegation.

2. It is not a full analytics layer.
   No rollups, clustering, or trend dashboards yet.

3. It is not transcript memory.
   This ledger is process metadata, not raw conversation/archive storage.

4. It does not infer missing facts.
   If a caller logs thin payloads, the answers will also be thin.

## Validation completed on this branch

Executed successfully:

- `uv run --extra dev pytest tests/agent/test_process_intelligence.py tests/shay_cli/test_process.py tests/shay_cli/test_startup_plugin_gating.py -n0 -q`
- `SHAY_HOME=$(mktemp -d) uv run shay process list`

Observed result:
- 44 targeted tests passed
- top-level `shay process` command routed correctly from the real CLI entrypoint

## Recommended next milestone

Do not jump to “instrument everything.”

The next smart step is to wire automatic emission into one or two high-value paths only:

1. one explicit orchestration path
2. one execution path

Good candidates:
- a delegated task completion path
- a kanban worker completion path
- a manual `shay goal` / long-run completion path if one exists cleanly

That gives real machine-written records from live workflows without turning the MVP into a sprawling surveillance rewrite.
