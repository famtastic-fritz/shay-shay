# ADR: Shay durable task/run ownership

Status: proposed for the R3 feature-flagged rollout

## Decision

`SessionDB` remains the owner of conversations and messages. The Kanban ledger
(`tasks`, `task_runs`, and `task_events`) is the sole durable owner of tasks,
runs, claims, retry lineage, approvals-waiting state, cancellation, and
terminal lifecycle events. `task_events.id` is the replay cursor.

Cron owns schedules and dispatch requests, not task truth. `ProcessRegistry`
owns live process handles and exit observation, not durable completion truth.
Batch checkpoints remain batch-specific. CLI, TUI, ACP, and the gateway API
are adapters over the Kanban domain state; none creates a parallel task
database.

The API adapter is feature-flagged (`durable_runs` or `SHAY_DURABLE_RUNS`) so
the legacy process-memory reader remains available during one compatibility
window. External API run ids are bound in `kanban_run_bindings`. Reconnects
replay `task_events` strictly after `Last-Event-ID` and terminal transitions
are single-writer/idempotent. A gateway restart closes an active run as
`interrupted` with `retry_required=true`; it never infers completion.

## Consequences

- A cancelled or interrupted run cannot be completed by a later stale worker.
- Historical active idempotency-key duplicates are retained as task rows,
  reconciled deterministically, and recorded in
  `task_idempotency_reconciliations` before the unique active-key index is
  enabled.
- External side effects are not claimed exactly-once by R3; R4/R8 effect
  interception and composed proof remain required for that stronger claim.
- Disabling the feature flag changes the API adapter only; it does not delete
  or downgrade Kanban ledger records.

## Alternatives rejected

- A second API-specific SQLite database: duplicates lifecycle authority.
- Replacing Kanban with an external agent framework: overwrites Shay's custom
  runtime and breaks the preservation contract.
- Marking interrupted work as completed on process restart: falsifies operator
  state and may cause duplicate external effects.
