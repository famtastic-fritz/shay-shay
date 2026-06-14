# Shay Process Intelligence Watcher Design

Date: 2026-06-13
Status: design only; no watcher enablement performed
Authority:
- `docs/shay-current-intelligence-schedule-audit-2026-06-13.md`
- `docs/shay-process-intelligence-architecture-2026-06-13.md`
- Fritz source architecture packet section 15

## Purpose

Define the watcher layer that keeps process intelligence alive after a run finishes.
This doc does not enable anything.
It defines the contracts watchers must satisfy before activation is even considered.

## Current automatic surfaces to respect

Already running or historically configured surfaces must be audited, not blindly reused:
- `ai.shay.memory-reflect`
- `com.famtastic.shay-lessons-sync`
- `com.shay.dailybrief`
- launch agents
- crontab
- Shay config for reflection / lessons / daily brief

Current design posture:
- no new watcher is enabled by this doc
- dailybrief is not reused as a delivery path for watcher spam
- no watcher may mutate live config or runtime without approval

## Required watcher schema

Every watcher must define:
- `watcher`
- `cadence`
- `inputs`
- `outputs`
- `allowed_actions`
- `forbidden_actions`
- `approval_needed`
- `storage_location`
- `failure_mode`

## Watcher set

### 1. After-run review watcher
- watcher: `after-run-review`
- cadence: after every meaningful run
- inputs: run ledger, decision ledger, tool-agent ledger, artifact ledger
- outputs: after-action packet, one recommended improvement, gap/backlog updates if warranted
- allowed_actions: read structured ledgers, write review packet, open recommendation draft
- forbidden_actions: enabling automation, changing live config, auto-closing high-risk gaps without review
- approval_needed: no
- storage_location: process-intelligence review store
- failure_mode: if run metadata is incomplete, emit an incomplete-capture finding instead of a fake review

### 2. Nightly pattern scan watcher
- watcher: `nightly-pattern-scan`
- cadence: nightly
- inputs: recent run ledgers, decisions, artifacts, gap log, adoption backlog
- outputs: pattern candidates, repeated-blocker report, one bounded recommendation
- allowed_actions: read metadata, open pattern recommendation draft, mark duplicate candidate patterns
- forbidden_actions: enabling new jobs, changing routing, performing paid checks by default
- approval_needed: no
- storage_location: pattern scanner draft store
- failure_mode: if data volume is too thin, produce “insufficient evidence” rather than invented trends

### 3. Weekly pruning review watcher
- watcher: `weekly-prune-review`
- cadence: weekly
- inputs: artifact ledger, docs inventories, skill readiness matrix, backlog, gap history
- outputs: keep/update/merge/archive/quarantine recommendations
- allowed_actions: create prune recommendation packet, flag duplicates/superseded items
- forbidden_actions: deleting or archiving live artifacts automatically
- approval_needed: no
- storage_location: prune-review store
- failure_mode: if relationships are unclear, quarantine recommendation only

### 4. Provider health watcher
- watcher: `provider-health-watch`
- cadence: weekly or on-demand before provider-sensitive work
- inputs: passive provider config/status surfaces, recent provider failures, approved health signals
- outputs: provider health classification update
- allowed_actions: passive checks, status classification, recommendation draft
- forbidden_actions: expensive live checks by default, provider swaps, live config edits
- approval_needed: yes for active/paid checks or config mutation
- storage_location: provider-health store
- failure_mode: remain `unknown` or `warning`; do not fake healthy status

### 5. Skill readiness watcher
- watcher: `skill-readiness-watch`
- cadence: weekly or after notable environment/tool changes
- inputs: skill catalog, readiness matrix, gap log, tool inventory
- outputs: readiness changes, stale/block/duplicate flags, quarantine candidates
- allowed_actions: metadata updates, recommendation drafts
- forbidden_actions: silently promoting risky skills to ready, changing tool installs
- approval_needed: yes for installs or broad catalog policy changes
- storage_location: skills-readiness store
- failure_mode: leave skill at `warning` or `blocked` if host proof is absent

### 6. Gap stale-check watcher
- watcher: `gap-stale-check`
- cadence: weekly
- inputs: gap log, last_checked timestamps, watch cadence, backlog links
- outputs: stale-gap reminders, reopen prompts, close/defer candidates
- allowed_actions: update stale-review packet, flag neglected gaps
- forbidden_actions: auto-close unresolved material gaps
- approval_needed: no
- storage_location: gap-review store
- failure_mode: if timestamps are missing, emit ledger hygiene gap instead of guessing

### 7. Adoption backlog review watcher
- watcher: `adoption-backlog-review`
- cadence: weekly or after new candidate fixes are discovered
- inputs: adoption backlog, recent research, recent gap changes, tool/provider readiness
- outputs: promote/defer/reject/supersede recommendations
- allowed_actions: backlog recommendation drafts, duplicate detection, priority suggestions
- forbidden_actions: installing/adopting tools, enabling workflows, changing live systems
- approval_needed: yes for adoption with side effects
- storage_location: adoption-review store
- failure_mode: if candidate value is unproven, keep item at researching/candidate_found

## Control-plane requirements before activation

No watcher should be enabled until these exist:
- a durable watcher state store
- dedupe / cooldown / suppression rules
- explicit human-review routing for yellow/red findings
- failure visibility
- branch/runtime boundary labeling
- safe write targets

## Delivery rules

Watchers should prefer:
- structured draft outputs
- backlog/gap recommendation packets
- low-noise summaries

Watchers must avoid:
- daily brief spam
- repeated identical alerts
- direct live mutation
- silent failure

## Activation boundary

Activation is approval-gated when it would:
- schedule a real job
- modify live config
- send recurring user-facing notifications
- perform paid or secret-bearing checks

Until then, this is design truth only.
