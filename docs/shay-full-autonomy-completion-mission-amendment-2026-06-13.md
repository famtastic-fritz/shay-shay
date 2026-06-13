# Shay full autonomy completion mission amendment — 2026-06-13

Status: captain amendment
Parent authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`

## Why this exists

This amendment preserves the original mission authority while separating the later execution-control overlay that was added during the live HyperSwarm run.

Use the parent mission as scope authority.
Use this amendment as the captain control-plane addendum for the remainder of the mission.

## Mission Amendment — HyperSwarm Execution Model

Do not restart the mission. Do not duplicate completed work. Continue the current mission, but enforce this execution model from this point forward.

Execution model:
- Captain / Orchestrator owns mission coherence, bounded packets, master tracker, merge decisions, and final synthesis.
- Gatekeeper enforces forbidden and approval-gated boundaries, blocks live mutation, blocks secret capture, and blocks deletion/restart/push/merge unless explicitly allowed.
- Recorder / Ledgerer records plan/job/task/run/event lineage, tools used, files inspected, files changed, decisions, assumptions, gaps, validations, artifacts, and commits.
- Hermes Lane Worker handles Hermes removal status, wrappers, compatibility, reference inventory, and cutover/relabeling planning without touching live wrapper or deleting anything.
- Awareness Lane Worker handles capability matrix, skills matrix, MCP/model/provider matrix, Add = Audit + Prune, and HyperSwarm canonicalization while separating draft/design from live-wired behavior.
- Process Intelligence Lane Worker handles process telemetry, run/decision/tool/artifact ledgers, pattern scanner, redaction policy, after-action review, and query examples.
- Scheduler / Watcher Lane Worker handles memory-reflect, lessons-sync, dailybrief, launch agents, crontab, and watcher/cron status without enabling or creating new scheduled jobs.
- Command Surface Lane Worker maps `shay doctor`, `shay sessions`, `shay status`, `shay mcp`, `shay gateway`, `shay model` / `/model`, skills, memory/session search, config validation, and diagnostics.
- Pruner / Consolidator checks duplicate, stale, superseded, or overlapping artifacts; applies Add = Audit + Prune; recommends merge/archive/quarantine/supersede; and does not delete without approval.
- Adversarial Reviewer performs brutal QA, challenges completion claims, checks designed vs wired vs live truth, and judges whether the work is useful or just paperwork.

Parallelism rule:
- Run Hermes lane, Awareness lane, Process Intelligence lane, Scheduler/Watcher lane, Command Surface lane, and Pruner lane in parallel where safe.
- Run reviewer after lane outputs exist.

Lane packet requirement:
Every lane must emit a lane packet containing:
- lane_name
- job_id
- task_ids
- inputs
- files inspected
- files changed
- tools used
- assumptions
- decisions
- gaps opened
- gaps closed
- artifacts produced
- validation performed
- risk level
- completion state (`designed`, `sandbox_proven`, `pr_ready`, `pr_open`, `merged_to_main`, `live_wired`, `validated_live`, `blocked`, `deferred`)
- next action

Lineage requirement:
Every lane packet must use plan_id, job_id, task_id, run_id, and event_id where practical.

Loop control:
- max 2 self-repair attempts per gap
- max 3 related unresolved gaps before switching to replan/synthesis
- no infinite loops
- if stuck, produce a gap-driven next-action packet instead of silence

Final brutal QA must score the HyperSwarm itself:
- Did parallelism help?
- Did it create sprawl?
- Which lanes should have been parallel?
- Which should have been serial?
- What metadata was missing?
- What should be captured next time?
- What role definitions need improvement?

## Mission Amendment — Master Open Items And Completion Tracker

Do not restart the mission. Do not duplicate work. Do not abandon the original prompt.

Create/update:
- `docs/shay-master-open-items-and-completion-tracker-2026-06-13.md`
- `docs/shay-master-open-items-and-completion-tracker-2026-06-13.yaml`

The tracker must separate:
- designed
- sandbox_proven
- pr_ready
- pr_open
- merged_to_main
- live_wired
- validated_live
- blocked
- deferred

The tracker must cover all known open items across Hermes removal, live wrapper/forwarder, code relabeling reconstruction, PR #3 docs/control status, dirty live checkout cleanup/preservation, paused rewrite sandbox status, model-switch local stack parked status, capability awareness, ledgers, pattern scanner, scheduler/watcher audit, and command-surface map.

For each item, record:
- item_id
- title
- category
- current_state
- evidence
- related_pr
- related_branch
- related_commit
- related_docs
- owner_role
- checker_role
- next_action
- approval_needed
- blocker
- validation_required
- done_definition

Completion rule amendment:
Do not call the mission complete unless the tracker clearly states what is actually live, what is only designed, what is only PR-ready, what is blocked, and what still needs Fritz approval.
