# Process Intelligence MVP — Brutal QA

This document answers the question that actually matters:

Did we build a real capability, or did we just add code-shaped hope?

## Verdict

This is a real MVP.

But it is only partially live-wired.

The command surface is live.
The storage is live.
The redaction boundary is live.
The after-action summary path is live.

Universal automatic runtime capture is NOT live yet.

That distinction matters.

## What is actually live-wired

1. `shay process` is a real top-level command in `shay_cli/main.py`.
2. `shay process log` writes real records to disk.
3. `shay process list` reads them back.
4. `shay process show` returns the full normalized record.
5. `shay process summary` returns a compact after-action report.
6. The command works from the real CLI entrypoint, not only from isolated unit imports.

Proof run:

`SHAY_HOME=$(mktemp -d) uv run shay process list`

Observed result:

`No process runs logged yet.`

That means the main parser route is real.

## What is only code-present, not broadly wired

1. Chat sessions do not automatically emit process records yet.
2. Generic tool executions do not automatically emit process records yet.
3. Cron runs do not automatically emit process records yet.
4. Delegate/subagent completions do not automatically emit process records yet.
5. Kanban or other orchestrators do not automatically emit process records yet.

So no, this is not “Shay now remembers every process automatically.”

That would be a lie.

## Can Shay answer the target questions now?

Yes, if the run is logged.

The record model is sufficient to answer:
- what happened
- how long it took
- what tools were used
- what commands were run
- what files were inspected/changed
- what decisions were made
- what gaps were opened/closed
- what validation happened
- what should happen next

No, if the run was never logged.

This MVP does not magically reconstruct missing process history.

## Safety check

### Good

- raw instruction text is not stored by default
- `instruction_text` is hash-only input
- `full_instruction_stored` is forced false in MVP
- secret-bearing strings are redacted before write
- env-like containers are not captured raw
- transcript/body/messages/system_prompt style content is replaced with sentinel placeholders

### Still worth watching

- summaries and decisions are still human/machine supplied text fields, so they can be vague even when safe
- the ledger depends on callers providing enough metadata to be useful
- redaction coverage is regex-plus-policy driven, which is good, but not infinite

## Reliability check

### Good

- each run gets its own JSON file
- the index is updated atomically
- sparse payloads do not crash the schema because required fields are normalized into existence
- list/show/latest all work against stored records

### Weak spots

- there is no file locking for concurrent writers yet
- repeated writes for the same `run_id` will create multiple index entries and rely on latest-wins behavior
- this is still filesystem-backed MVP storage, not a query-optimized long-term analytics store

## Validation proof from this branch

Targeted test run:

`uv run --extra dev pytest tests/agent/test_process_intelligence.py tests/shay_cli/test_process.py tests/shay_cli/test_startup_plugin_gating.py -n0 -q`

Observed result:

`44 passed`

Meaning:
- new core tests passed
- new CLI tests passed
- existing startup plugin gating test still passed

That is the right proof for MVP quality here.

## Failure modes if we shipped this and pretended it was complete

1. Somebody assumes every Shay action is now automatically logged.
   False.

2. Somebody assumes this stores enough to reconstruct raw reasoning.
   False.

3. Somebody assumes concurrency is hardened.
   Not yet.

4. Somebody assumes this replaces session memory.
   It does not.

5. Somebody assumes it is impossible to log unhelpful metadata.
   Also false. Safe does not equal insightful.

## What the next milestone should be

One or two automatic emitters. Not ten.

Best next move:
- choose one orchestration completion path
- choose one execution completion path
- emit this schema automatically there
- validate the summaries against real work, not synthetic JSON payloads only

That is how this becomes process intelligence instead of a nice manual ledger.

## Bottom line

This branch adds a real, test-backed process-intelligence MVP.

It is not fake.
It is not complete.
It is not universal.

It is the right size.
