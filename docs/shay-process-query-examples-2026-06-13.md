# Shay Process Query Examples

Date: 2026-06-13
Status: query contract / acceptance surface
Authority:
- `docs/shay-process-intelligence-architecture-2026-06-13.md`
- `docs/shay-run-ledger-schema-2026-06-13.yaml`
- `docs/shay-decision-ledger-schema-2026-06-13.yaml`
- `docs/shay-tool-agent-ledger-schema-2026-06-13.yaml`
- `docs/shay-artifact-ledger-schema-2026-06-13.yaml`
- Fritz source architecture packet sections 15, 16, and 28

## Purpose

These are the questions the process-intelligence layer should be able to answer.
Each question maps to ledger fields so the system is judged by answerability, not by how impressive the architecture sounds.

## Query groups

### A. Run envelope

| question | primary ledger | key fields | answerability target |
|---|---|---|---|
| How long did the last task take? | run ledger | `run_id`, `started_at`, `ended_at`, `duration_seconds` | must-answer |
| What plan/job/task/run did this work belong to? | run ledger | `plan_id`, `job_id`, `task_id`, `run_id`, `parent_job_id` | must-answer |
| What instruction triggered this run? | run ledger | `initiating_instruction_summary`, `instruction_source`, `instruction_hash`, `full_instruction_stored` | must-answer |
| What constraints governed this run? | run ledger | `constraints`, `allowed_actions`, `forbidden_actions`, `approval_gates` | must-answer |

### B. Tools, roles, and execution

| question | primary ledger | key fields | answerability target |
|---|---|---|---|
| Which tools did Shay use? | tool-agent ledger | `tool_or_skill_used`, `agent_or_role`, `why_chosen` | must-answer |
| Which roles were dispatched? | tool-agent ledger | `agent_or_role`, `allowed_actions`, `forbidden_actions` | must-answer |
| Which commands were run? | run ledger | `commands_run` | must-answer |
| Which files were inspected or changed? | run/artifact ledger | `files_inspected`, `files_changed`, `path_or_url`, `artifact_type` | must-answer |

### C. Decisions and assumptions

| question | primary ledger | key fields | answerability target |
|---|---|---|---|
| What decisions were made? | decision ledger | `decision`, `chosen_option`, `why`, `evidence`, `outcome` | must-answer |
| What alternatives were considered? | decision ledger | `alternatives_considered`, `chosen_option` | should-answer |
| What assumptions were made? | run/decision ledger | `assumptions_made`, `assumption_level`, `confidence` | must-answer |
| Which approvals were needed? | decision/run ledger | `approval_needed`, `approval_gates` | must-answer |

### D. Gaps, blockers, and rework

| question | primary ledger | key fields | answerability target |
|---|---|---|---|
| Which gaps were opened during the run? | run ledger + gap system | `gaps_opened`, `blockers`, `next_actions` | must-answer |
| Which gaps repeated across runs? | run ledger + pattern scanner | `gaps_opened`, `pattern_id`, `frequency` | should-answer |
| Which tasks caused rework? | tool-agent/run ledger | `caused_rework`, `rework_loops`, `validation_result` | should-answer |
| Which approval gates slowed us down? | run/decision ledger | `approval_gates`, `blockers`, `outcome` | should-answer |

### E. Validation and safety

| question | primary ledger | key fields | answerability target |
|---|---|---|---|
| What validation happened? | run ledger | `validations_run`, `validation_results` | must-answer |
| What safety events occurred? | run ledger | `safety_events`, `blockers` | must-answer |
| What redactions were applied? | run/artifact ledger | `privacy_redactions`, `validation_status`, `retention_class` | must-answer |
| Which artifacts lack validation? | artifact ledger | `validation_status`, `artifact_type`, `path_or_url` | should-answer |

### F. Improvement and automation

| question | primary ledger | key fields | answerability target |
|---|---|---|---|
| What should improve next time? | run ledger + after-action review | `lessons_learned`, `next_actions` | must-answer |
| What should be automated next? | pattern scanner + backlog | `recommendation`, `next_action`, `backlog_id` | should-answer |
| What should be pruned next? | artifact/pattern scanner | `retention_class`, `supersedes`, `pattern_id`, `recommendation` | should-answer |

## Current truth on this branch

Today this branch can answer some of these questions only partially.
The strongest current evidence surfaces are:
- process-intelligence architecture doc
- ledger schema docs
- current intelligence schedule audit
- command-surface map
- branch-local runtime recorder slice

It cannot yet honestly claim a live operator-grade query surface for all of the questions above.

## Failure modes

If a query cannot be answered, the system should say why:
- ledger field missing
- event never captured
- answer exists only in a doc summary, not structured telemetry
- query is cross-run but only single-run evidence exists
- answer would require secret-bearing raw capture, which is forbidden

## Acceptance rule

The process-intelligence layer is only as real as the questions it can answer from structured evidence.
If a question above cannot be answered from ledgers, the right conclusion is not “good enough.”
The right conclusion is “capture is incomplete.”
