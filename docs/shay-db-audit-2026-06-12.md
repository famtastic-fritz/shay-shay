# Shay-Shay `shay.db` audit

Status: Phase 6 audit/decision only
Date: 2026-06-12
Scope: read-only inspection of `~/.shay/shay.db` plus repo/doc reference audit for `shay.db`, `state.db`, `DEFAULT_DB_PATH`, and `SessionDB`
Implementation status: audit/report only; no delete, move, rename, schema change, config change, migration, or runtime behavior change performed

## Explicit safety boundary

Phase 6 does not:
- delete `~/.shay/shay.db`
- move `~/.shay/shay.db`
- rename `~/.shay/shay.db`
- modify `~/.shay/state.db`
- modify `~/.shay/sessions/`
- modify SOUL.md
- modify PERSONA.md
- modify MEMORY.md
- modify USER.md
- change runtime behavior
- change SQL, migrations, config behavior, or persistence logic

## Executive summary

Observed result:
- `~/.shay/shay.db` exists
- current size: 0 bytes
- SQLite can open it read-only
- integrity check returns `ok`
- no tables, indexes, views, or triggers were present
- no active runtime Python code reference to `shay.db` was found in the repo outside the new audit script and earlier audit/report artifacts

Decision:
- Recommendation: preserve and document as dormant

Why:
- `shay.db` currently presents as an empty placeholder/dormant side store, not an active runtime database
- the active runtime conversation database is clearly `state.db`
- removing or renaming `shay.db` now would create more uncertainty than value, while preserving it costs essentially nothing at 0 bytes

## Source-of-truth docs reviewed

- `docs/shay-memory-hierarchy.md`
- `docs/shay-db-status.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`

## Read-only runtime audit

Audit script:
- `scripts/audit_shay_db.py`

Audit timestamp:
- 2026-06-12T19:06:39+00:00

Observed `shay.db` status:
- path: `/Users/famtasticfritz/.shay/shay.db`
- exists: yes
- size_bytes: 0
- sha256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- SQLite open (read-only): yes
- integrity check: `ok`
- tables: none
- schema objects: none
- classification from audit script: `dormant_empty_placeholder`

Interpretation:
- This file is empty on disk, readable by SQLite, and contains no schema objects.
- That is consistent with a dormant placeholder or abandoned/unused DB path.
- It is not consistent with an active session store, memory store, or feature DB in the current runtime.

## Distinction between `state.db` and `shay.db`

Current observed `state.db` status at audit time:
- path: `/Users/famtasticfritz/.shay/state.db`
- exists: yes
- size_bytes: 247,791,616
- tables include: `sessions`, `messages`, `messages_fts`, `messages_fts_trigram`, `schema_version`, `state_meta`, and related FTS backing tables
- session rows: 476
- message rows: 15,193

Operational distinction:
- `state.db` is the active structured runtime store for conversation/session history
- `shay.db` is empty, non-structured, and currently dormant

Practical operator rule:
- for conversation/session recall, diagnostics, and persistence questions, check `state.db`
- do not treat `shay.db` as authoritative unless future runtime wiring gives it a real role

## Repo references found

### `shay.db`

Runtime code references found in Python modules:
- none found outside audit artifacts

Audit/doc references found:
- `docs/shay-db-status.md:17` — says `shay.db` does not appear to be an active canonical runtime store
- `docs/shay-db-status.md:33-36` — says docs should describe it as present on disk, not observed as an active memory source, and not a substitute for `state.db`
- `docs/shay-memory-hierarchy.md:117-132` — classifies `~/.shay/shay.db` under legacy/auxiliary artifacts unless wired to a documented runtime role
- `docs/shay-memory-architecture-review-2026-06-12.md:66` — records `~/.shay/shay.db` as size 0 with no tables
- `docs/shay-memory-architecture-review-2026-06-12.md:75` — says `shay.db` is effectively unused in the current wiring
- `docs/shay-memory-architecture-review-2026-06-12.md:362` — calls for either removing `shay.db` from the mental map or wiring it to a real purpose later

### `state.db`

Key runtime references showing active use:
- `shay_state.py:34` — `DEFAULT_DB_PATH = get_shay_home() / "state.db"`
- `shay_state.py:333` — `SessionDB` defaults to `DEFAULT_DB_PATH`
- `gateway/session.py:430-431` — comments explicitly say canonical conversation history lives in `state.db`
- `shay_cli/doctor.py:798-811` — health checks inspect `~/.shay/state.db`, not `shay.db`
- `run_agent.py:2446-2448` — recall path lazily creates `SessionDB()`
- `mcp_serve.py:72-75` — event bridge gets a `SessionDB` for canonical message history
- `gateway/platforms/api_server.py:783-784` — says sessions are persisted to `state.db`

### `DEFAULT_DB_PATH`

Relevant findings:
- `shay_state.py:34` defines `DEFAULT_DB_PATH` as `state.db`
- `tools/session_search_tool.py:548-549` imports `DEFAULT_DB_PATH` and checks its parent for session-search readiness
- test files monkeypatch `DEFAULT_DB_PATH` to alternate `state.db` paths for isolation

Interpretation:
- the named default DB path in runtime code is `state.db`, not `shay.db`

### `SessionDB`

Relevant findings:
- `SessionDB` is the active SQLite session/message abstraction used across runtime surfaces
- references were found in `run_agent.py`, `gateway/run.py`, `gateway/session.py`, `gateway/platforms/api_server.py`, `mcp_serve.py`, `cron/scheduler.py`, and many tests
- no evidence was found that `SessionDB` points at `shay.db`

## Does any config or doc imply `shay.db` is active?

Config implication:
- no active config path was found that points runtime persistence at `shay.db`

Doc implication:
- the current docs do not imply `shay.db` is active
- the current docs consistently describe `shay.db` as dormant, non-canonical, or effectively unused

Conclusion:
- the repo/docs currently reinforce `state.db` as active and `shay.db` as dormant

## Risk of deleting `shay.db`

Current risk level:
- low technical blast radius based on current evidence, but non-zero uncertainty remains

Why the risk is not zero:
1. Empty files can still function as sentinels/placeholders
- even a 0-byte file may be created/checked by some abandoned or edge path not surfaced in normal code search

2. Runtime/home churn risk
- deleting it changes the shape of `~/.shay/` and can muddy future debugging if some latent path expects the file to exist or recreates it silently

3. Evidence standard
- we do not yet have a controlled rename/remove validation run proving no runtime path notices its absence

Bottom line:
- deletion is not justified by this phase alone

## Risk of leaving `shay.db`

Current risk level:
- very low

Why:
1. Storage cost is effectively zero
- the file is 0 bytes

2. No observed active runtime role
- it is not competing with `state.db` in code wiring

3. Main downside is operator confusion
- the name `shay.db` invites wrong assumptions if it is not documented clearly

Bottom line:
- the real risk is misunderstanding, not operational harm

## Recommended next action

Chosen recommendation:
- preserve and document as dormant

Reasoning:
- This is the cleanest move that matches current evidence.
- It avoids premature deletion.
- It sharpens the mental model now: `state.db` is active, `shay.db` is dormant.
- If later validation proves the file is truly irrelevant, a future archive/remove phase can happen with confidence.

What this recommendation means:
- keep `~/.shay/shay.db` in place for now
- continue documenting it as dormant/non-canonical
- do not wire new features to it casually
- only consider archive/remove after a future validation phase explicitly proves no runtime dependency exists

## Exact validation steps for a future rename/archive test

This phase does not perform these steps. These are the exact checks a future validation phase should require before any rename/archive/remove decision.

1. Capture baseline before touching anything
- record `ls -l ~/.shay/shay.db`
- record `stat ~/.shay/shay.db`
- record SHA-256 hash
- record whether current runtime has recreated or modified the file recently
- record `shay doctor` output related to DB/runtime health

2. Verify baseline runtime behavior with file present
- start CLI session
- send at least one normal prompt
- verify history/session persistence still lands in `state.db`
- exercise `session_search`
- if gateway is running, verify gateway resume/session mapping paths still behave normally
- if API server is enabled, verify a basic conversation still persists to `state.db`

3. Perform a controlled rename only
- rename `~/.shay/shay.db` to a quarantine path such as `~/.shay/shay.db.phase6b.bak`
- do not delete it
- do not touch `state.db`
- do not touch `sessions/`

4. Re-run the same baseline runtime checks
- CLI prompt round-trip
- `session_search`
- gateway startup, if in use
- API server/session continuity, if in use
- `shay doctor`
- inspect logs for any mention of `shay.db`, SQLite open failures, missing-file warnings, or fallback paths

5. Observe file recreation behavior
- check whether a new `~/.shay/shay.db` gets auto-created
- if recreated, record size, timestamp, and whether it remains empty
- if not recreated, record that absence caused no observable runtime issue during the test window

6. Rollback requirement
- if any warning, error, recreation anomaly, or behavior change appears, restore the original filename immediately
- confirm post-rollback behavior matches baseline

7. Archive/remove decision gate
- only after a clean rename test with no runtime dependency evidence should archive/remove be considered
- even then, archive first before any permanent deletion

## Final decision statement

Phase 6 decision:
- `shay.db` should currently be preserved and documented as dormant
- it should not currently be removed, repurposed, or wired to a real function based on the evidence from this audit alone

## Files produced by this phase

- `scripts/audit_shay_db.py`
- `docs/shay-db-audit-2026-06-12.md`
