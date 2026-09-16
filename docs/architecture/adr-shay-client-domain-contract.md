# ADR: Shay client domain contract

Status: accepted for the Phase 6 feature branch

## Decision

`shay_cli/domain_contract.py` is the single adapter-neutral public service seam
for task lifecycle inspection and recovery. It projects the existing Kanban
task, run, and event rows into a versioned JSON-compatible contract. CLI, TUI
JSON-RPC, gateway API, and ACP keep their existing transports and map their
wire envelopes to this seam; none gets a second lifecycle store or command
registry.

The initial protocol is `shay.client.v1`. The five lifecycle operations are
`inspect_task`, `list_task_events`, `cancel_task`, `retry_task`, and
`resume_task`. All identifiers come from Kanban (`task_id`, `run_id`, and
monotonic event `id`); the service never manufactures a client-local id.

## Compatibility

Readers ignore additive unknown fields. Writers emit the required fields and
the protocol version. A missing or incompatible major version fails closed
with the stable `incompatible_version` error; a minor version may be read when
the reader advertises that version. Event replay is strictly after the
numeric `after_event_id` cursor, ordered by ascending ledger id, and a client
must retain its cursor to deduplicate reconnects.

Task and run terminal states are explicit (`completed`, `failed`, `blocked`,
`cancelled`, `interrupted`, and `archived` where applicable). `waiting_for_approval`
is non-terminal. Cancellation is durable and idempotent through Kanban;
retry/resume are operator requests that return the resulting authoritative
snapshot, not a claim that a worker has already started.

## Authority map

| Field or object | Authority | Notes |
| --- | --- | --- |
| task/run/event identifiers and statuses | Kanban SQLite | authoritative |
| timestamps, output, error, usage | Kanban rows/event payloads | authoritative when present |
| capability availability | adapter runtime | derived; unavailable is explicit |
| session/client transport metadata | caller adapter | client-local, never lifecycle authority |
| effect and memory provenance | R4/R5 projections | optional; absence means unavailable |

The optional `effect` and `memory_provenance` projections are typed and require
an authority reference when populated. They are not inferred from empty values.

## Preservation and scope

This is an additive mapping layer. Existing CLI vocabulary, TUI embedding,
gateway routes, ACP methods, approvals, and Shay custom/persona/voice/live
files remain untouched. This ADR does not authorize mobile clients, voice/STT/
TTS changes, publishing, credentials, or production enablement.
