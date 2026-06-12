# Session JSON audit — 2026-06-12

Status: Phase 5 audit only
Scope: read-only inspection of legacy session JSON artifacts under `~/.shay/sessions/` plus read-only comparison against `~/.shay/state.db`
Implementation status: audit/report only; no archive, prune, move, rename, delete, or runtime behavior change performed

## Guardrails honored

- No files were deleted.
- No files were moved.
- No files were renamed.
- Nothing under `~/.shay/sessions/` was modified.
- `~/.shay/state.db` was opened read-only via SQLite URI mode (`file:...?...mode=ro`).
- `~/.shay/shay.db` was not modified.
- No runtime code path was changed.
- No session artifact was rewritten in place.

## Files created for this audit

- `scripts/audit_sessions_json.py` — read-only audit script
- `docs/session-json-audit-2026-06-12.md` — this report

## Runtime seam confirmed

The current runtime still treats `sessions.json` as active bookkeeping rather than dead residue.

Relevant code evidence:
- `gateway/session.py:427-431` — `SessionEntry` is described as the gateway session index and explicitly says canonical conversation history lives in `state.db`.
- `gateway/session.py:475-476` — notes that expiry-finalization state is persisted to `sessions.json` across gateway restarts.
- `mcp_serve.py:81-96` — `_load_sessions_index()` directly loads `sessions.json` and describes it as the gateway bookkeeping index.

Conclusion:
- `sessions.json` is active bookkeeping.
- `state.db` is the canonical conversation history store.
- Many legacy `session_*.json`, `*.jsonl`, and `request_dump_*.json` artifacts appear to be secondary artifacts rather than the primary runtime source of truth.

## Audit method

The audit script inspects:
- `~/.shay/sessions/*.json`
- `~/.shay/sessions/*.jsonl`
- `~/.shay/sessions/sessions.json`
- `~/.shay/state.db`

The script classifies artifacts into these buckets:
- active bookkeeping candidate
- raw archive candidate
- migration candidate
- summarize-then-archive candidate
- prune candidate
- corrupt/unreadable candidate
- duplicate candidate
- unknown / needs manual review

Classification heuristics used:
- `sessions.json` → active bookkeeping candidate if it matches the gateway index shape.
- `session_*.json` → duplicate candidate when the session ID is already present in `state.db`; otherwise migration candidate.
- `request_dump_*.json` → summarize-then-archive candidate because these appear to be diagnostic payload captures, not canonical recall data.
- `*.jsonl` → raw archive candidate when they look like legacy transcript fragments already represented elsewhere.
- unreadable artifacts → corrupt/unreadable candidate.

## Point-in-time result

Audit run timestamp:
- `2026-06-12T19:00:58+00:00`

Important live-system note:
- The file count changed during the audit window (an earlier read saw 641 artifacts; the final run saw 642).
- That means the directory is still live and mutable while Shay is operating.
- Any future archive/prune phase must treat counts as point-in-time, not fixed forever.

## Summary totals

Total files found under `~/.shay/sessions/`:
- 642

Counts by extension:
- `.json`: 639
- `.jsonl`: 3

`state.db` status:
- exists: yes
- schema usable: yes
- session rows: 475
- message rows: 15,079

## Classification counts

- active bookkeeping candidate: 1
- raw archive candidate: 3
- migration candidate: 189
- summarize-then-archive candidate: 54
- prune candidate: 0
- corrupt/unreadable candidate: 0
- duplicate candidate: 395
- unknown / needs manual review: 0

Counts by artifact kind:
- `sessions_index`: 1
- `session_snapshot_json`: 584
- `request_dump_json`: 54
- `jsonl_fragment`: 3

## sessions.json assessment

Does `sessions.json` appear to be active bookkeeping?
- Yes.

Why:
- It is shaped as a dictionary keyed by `session_key` with per-session routing metadata.
- Runtime code still loads it directly.
- Runtime comments explicitly distinguish it from `state.db`, which is described as the canonical recall/history store.

Entry count observed in `sessions.json` during audit:
- 1

## Sampled session JSON representation in state.db

A spread sample of 10 `session_*.json` artifacts was compared against `state.db`.

Result:
- 8 of 10 sampled session JSON files appear represented in `state.db`
- 2 of 10 sampled session JSON files did not appear represented in `state.db`

Sample rows:

| File | Session ID | Represented in state.db | state.db message count | Classification |
|---|---|---:|---:|---|
| `session_20260603_171158_4e105e.json` | `20260603_171158_4e105e` | no | - | migration candidate |
| `session_20260605_124822_588641.json` | `20260605_124822_588641` | yes | 10 | duplicate candidate |
| `session_20260607_045304_d8256b.json` | `20260607_045304_d8256b` | yes | 28 | duplicate candidate |
| `session_20260609_153754_8ed19a.json` | `20260609_153754_8ed19a` | yes | 44 | duplicate candidate |
| `session_20260609_215427_ebf37e.json` | `20260609_215427_ebf37e` | no | - | migration candidate |
| `session_20260610_125206_f245c2.json` | `20260610_125206_f245c2` | yes | 31 | duplicate candidate |
| `session_20260611_113209_b5968e.json` | `20260611_113209_b5968e` | yes | 1 | duplicate candidate |
| `session_20260612_001058_4b4516.json` | `20260612_001058_4b4516` | yes | 48 | duplicate candidate |
| `session_20260612_144548_f41319.json` | `20260612_144548_f41319` | yes | 60 | duplicate candidate |
| `session_cron_dd3146e4e2f3_20260610_223236.json` | `cron_dd3146e4e2f3_20260610_223236` | yes | 2 | duplicate candidate |

Interpretation:
- Most sampled legacy session JSON snapshots look redundant with `state.db`.
- Not all are redundant.
- That means a future cleanup phase cannot safely bulk-delete all `session_*.json` files without an explicit migration/coverage plan.

## Representative examples by class

Active bookkeeping candidate:
- `sessions.json`

Raw archive candidates:
- `20260605_020207_5978b002.jsonl`
- `20260606_065928_e7209d13.jsonl`
- `20260610_202325_28af71bf.jsonl`

Summarize-then-archive candidates:
- `request_dump_20260604_123337_322b5c_20260604_123449_434629.json`
- `request_dump_20260604_204934_91c1a0_20260604_205019_359926.json`
- `request_dump_20260605_000503_f45b38_20260605_000719_247400.json`

Migration candidates:
- `session_20260603_171158_4e105e.json`
- `session_20260604_120101_fb7404.json`
- `session_20260604_175707_3b43cf.json`

Duplicate candidates:
- `session_20260604_123337_322b5c.json`
- `session_20260604_172544_ae858f.json`
- `session_20260604_203301_20fdbc.json`

## Recommended next action

Do not delete anything yet.

Recommended Phase 5B planning target:
1. Preserve `sessions.json` as active bookkeeping unless and until runtime is changed to remove that dependency.
2. Treat `state.db` as the canonical baseline for coverage checks.
3. Split legacy artifacts into three planning lanes:
   - duplicate lane: likely archive/prune after verification
   - migration lane: verify whether content missing from `state.db` must be migrated or intentionally preserved as raw archive
   - request-dump lane: summarize sensitive/debug payload captures before deciding archive/prune policy
4. Add an explicit “live system mutation” note to any cleanup plan because the artifact set is still changing while Shay runs.
5. Plan archive/prune only after defining exact verification rules, dry-run outputs, and rollback posture.

## Risks

1. False safety from partial coverage
- 395 artifacts look duplicate relative to `state.db`, but 189 look like migration candidates.
- Bulk cleanup without per-file verification could drop content not represented in the canonical store.

2. Live directory churn
- The count changed during the audit window.
- A plan that assumes a static directory will drift immediately.

3. Sensitive diagnostic payloads
- `request_dump_*.json` files may contain request payload fragments, headers, prompt text, or error details.
- These should not be blindly copied, exposed, or deleted without a deliberate policy.

4. Mixed artifact semantics
- Not every JSON file under `~/.shay/sessions/` means the same thing.
- `sessions.json` is active bookkeeping; `session_*.json` snapshots are different; request dumps are different again.

5. Cron/session edge cases
- At least one sampled artifact used a cron-shaped session ID and was represented in `state.db`.
- Any future planner must account for non-human session naming patterns.

## Explicit deletion warning

WARNING:
This audit does NOT authorize deletion, movement, renaming, migration, compaction, or rewriting of any artifact under `~/.shay/sessions/`.

The presence of “duplicate candidate,” “raw archive candidate,” “summarize-then-archive candidate,” or “prune candidate” in this report is classification only.
It is not execution approval.
Any destructive or reorganizing step requires a separate Phase 5B planning pass and a later explicitly authorized implementation phase.

## Exact Phase 5B prompt for archive/prune planning only

Implement Phase 5B planning only.

Goal:
Create a design-level archive/prune plan for legacy session JSON artifacts under `~/.shay/sessions/` using the completed audit report, without deleting, moving, renaming, or modifying any runtime data.

Source-of-truth docs:
- `docs/shay-memory-hierarchy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
- `docs/session-json-audit-2026-06-12.md`

Rules:
- Do not delete anything.
- Do not move anything.
- Do not rename anything.
- Do not modify `~/.shay/sessions/`.
- Do not modify `~/.shay/state.db`.
- Do not modify `~/.shay/shay.db`.
- Do not modify SOUL.md.
- Do not modify PERSONA.md.
- Do not modify MEMORY.md.
- Do not modify USER.md.
- Do not change runtime behavior.
- Planning only.

Tasks:
1. Define exact verification rules for when a `session_*.json` artifact can be considered safely represented in `state.db`.
2. Define a dry-run archive/prune workflow that produces reviewable manifests before any destructive step.
3. Define separate policies for:
   - `sessions.json`
   - `session_*.json`
   - `request_dump_*.json`
   - `*.jsonl`
4. Define rollback and recovery requirements.
5. Define how to handle live-directory churn while Shay is still running.
6. Produce a planning doc only; do not implement archive/prune behavior.

Afterward show:
1. files created/changed
2. archive/prune decision framework
3. verification rules
4. risks
5. open questions requiring explicit approval

Do not continue into implementation.
