# Hermes-Removal Mission Ledger

Date: 2026-06-13
Lane: sandbox
Primary sandbox worktree: `/Users/famtasticfritz/famtastic/shay-shay-hermes-removal-sandbox-20260613`
Sandbox branch: `sandbox/hermes-removal-backup-of-now-20260613`
Sandbox home: `/Users/famtasticfritz/.shay-hermes-removal-sandbox`
Live checkout protected: `/Users/famtasticfritz/famtastic/shay-shay`
Paused rewrite sandbox protected: `/Users/famtasticfritz/famtastic/shay-shay-build`
Mission doctrine: current app/runtime/product identity becomes Shay; historical provenance, compatibility contracts, migration records, and model identifiers remain Hermes when appropriate and must be labeled clearly.

## Assignment

Note: earlier sandbox notes used the name "HyperWAM"; HyperSwarm is the canonical name. Historical commit-message quotes below keep the original wording when needed.

Run the complete Hermes-removal + capability-awareness stress test to completion inside the Hermes-removal sandbox only, using HyperSwarm role discipline and producing final QA, gap analysis, and promotion/cutover recommendation artifacts.

## Preflight Identity

- path: `/Users/famtasticfritz/famtastic/shay-shay-hermes-removal-sandbox-20260613`
- branch: `sandbox/hermes-removal-backup-of-now-20260613`
- head at mission start: `7ea3d9d`
- git status at mission start: clean
- latest commits at mission start:
  - `7ea3d9d docs: add capability gap lifecycle and research watcher design`
  - `e6d7c6a docs: add capability gap lifecycle and research watcher design`
  - `a644a0a docs: validate Hermes sandbox lock-dir isolation`
  - `b6ac858 docs: add HyperWAM skill and lock-dir validation plan`
  - `a8e5f7a docs: record sandbox gateway validation result`

## Live Protection Checks

Observed only; no live mutations performed.

- live checkout exists: yes
- paused rewrite sandbox exists: yes
- protected external Hermes paths present and untouched within inspected scope:
  - `/Users/famtasticfritz/.local/bin/hermes`
  - `/Users/famtasticfritz/.shay/hermes-agent`
  - `/Users/famtasticfritz/.hermes`
- protected private/live state paths treated as off-limits:
  - `/Users/famtasticfritz/.shay/private`
  - `/Users/famtasticfritz/.shay/sessions`
  - `/Users/famtasticfritz/.shay/state.db`

## HyperSwarm Lane Plan Used

- Dispatcher: split work into preflight, inventory, replacements, compatibility, awareness, validation, QA, and promotion lanes
- Runner: execute bounded sandbox-only file and validation tasks
- Checker: verify paths, diffs, and safety boundaries before mutations/claims
- Reviewer: adversarially challenge overclaims, weak assumptions, and cutover risk
- Pruner: classify stale/duplicate/superseded artifacts before adding new ones
- Gatekeeper: block live mutations, secret usage, runtime startup drift, and approval-gated actions
- Recorder/Ledgerer: maintain this ledger plus file/test/gap/decision records
- Promoter: decide what is ready for PR/promotion vs hold/defer
- Watcher: track open gaps/drift during the run
- Gap Logger: convert uncertainty into durable gap/backlog items with one next action

## Add = Audit + Prune Rule Applied

Before adding new lifecycle/awareness artifacts, related existing docs were audited and classified. Current classifications surfaced in this mission:
- keep: capability control packet, capability matrix, preflight checklist, lifecycle docs, HyperSwarm skill
- update: gap log, mission ledger, compatibility labeling comments/docstrings, current control docs
- merge later: research cron design + research fetcher role overlap
- archive later: `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md`
- supersede later: `docs/shay-workstream-control-map-2026-06-12.md`
- quarantine by default in routing: `skills/red-teaming/godmode/SKILL.md`
- remove after backup: none in this sandbox mission
- needs Fritz approval: any live wrapper/home deletion or command replacement

## Tools Used

- `skill_view`
- `read_file`
- `search_files`
- `terminal`
- `patch`
- `write_file`
- `execute_code`
- `delegate_task`
- `todo`

## Files Inspected

Representative inspected files/artifacts:
- `skills/orchestration/hyperwam/SKILL.md`
- `skills/autonomous-ai-agents/shay-shay/SKILL.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-gap-log-schema-2026-06-13.yaml`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`
- `docs/shay-research-fetcher-role-2026-06-13.md`
- `docs/hermes-removal-gap-log-2026-06-13.md`
- `docs/hermes-removal-capability-matrix-2026-06-13.yaml`
- `shay_cli/web_server.py`
- `shay_cli/mcp_config.py`
- `shay_cli/conductor_missions.py`
- `gateway/chat_stream_routes.py`
- `gateway/platforms/api_server.py`
- `tests/shay_cli/test_mcp_api_routes.py`
- `tests/shay_cli/test_dashboard_bearer_auth.py`
- `tests/shay_cli/test_conductor_missions.py`

## Files Changed

Code / tests:
- `shay_cli/web_server.py`
- `shay_cli/mcp_config.py`
- `shay_cli/conductor_missions.py`
- `gateway/chat_stream_routes.py`
- `gateway/platforms/api_server.py`
- `tests/shay_cli/test_mcp_api_routes.py`
- `tests/shay_cli/test_dashboard_bearer_auth.py`
- `tests/shay_cli/test_conductor_missions.py`

Docs / control artifacts:
- `docs/hermes-removal-gap-log-2026-06-13.md`
- `docs/hermes-removal-mission-ledger-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.yaml`
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
- `docs/hermes-live-cutover-proposal-2026-06-13.md`
- `docs/shay-global-capability-matrix-draft-2026-06-13.md`
- `docs/shay-global-capability-matrix-draft-2026-06-13.yaml`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-adoption-backlog-2026-06-13.md`
- `docs/shay-adoption-backlog-schema-2026-06-13.yaml`
- `docs/shay-adoption-backlog-policy-2026-06-13.md`
- `docs/shay-add-audit-prune-rule-2026-06-13.md`

## Tests / Probes Run

- preflight git identity check
- protected-path presence check
- Hermes reference repo scan + reclassification pass
- unclassified-reference verification pass: 0 unclassified files after final inventory regeneration
- `py_compile` on all touched Python/test files using shared live-checkout venv path with sandbox `SHAY_HOME`
- targeted pytest using shared live-checkout venv path with sandbox `SHAY_HOME`:
  - `tests/shay_cli/test_dashboard_bearer_auth.py`
  - `tests/shay_cli/test_mcp_api_routes.py`
  - `tests/shay_cli/test_conductor_missions.py`
  - result: `48 passed`

## Gaps Found / Reconciled

Added or expanded in `docs/hermes-removal-gap-log-2026-06-13.md`:
- `sandbox-no-local-venv`
- `path-missing-python-pytest-pip`
- `sandbox-home-not-yet-startup-validated`
- `gateway-lock-dir-default-outside-shay-home`
- `hermes-external-client-usage-unknown`
- `provider-health-partial-only`
- `mcp-sandbox-independence-unproven`
- `skill-presence-not-equal-host-readiness`
- `legacy-hermes-home-sensitive`
- `sandbox-tests-share-live-venv`
- `delegation-must-be-read-only-scoped`

## Decisions Made

- Keep surviving active-code Hermes strings only where they are proven compatibility surfaces.
- Convert ambiguous active-code Hermes comments/docstrings into explicit legacy-compatibility language rather than deleting needed shims.
- Treat external Hermes surfaces as remove-last, not cleanup-first.
- Expand capability awareness using the Hermes lane as the prototype, but keep claims conservative where runtime proof is partial.
- Count targeted pytest/compile success as code sanity proof only, not as proof of sandbox self-sufficiency, because execution still uses the live checkout `.venv` path.
- Use HyperSwarm, but call out paperwork-sprawl risk explicitly in final QA.

## Approval Gates

Still blocked unless Fritz explicitly approves later:
- creating a sandbox-local `.venv` if he wants the next wave to resolve shared-venv coupling
- live `hermes` command replacement/forwarding
- live wrapper deletion
- live `~/.hermes` deletion or migration steps
- live launchd edits
- live service restarts
- real token/platform enablement
- destructive cleanup outside sandbox
- any push

## Verdicts So Far

- preflight verdict: PASS
- live-protection verdict: PASS
- inventory-classification verdict: PASS after final regeneration (`34` files with hits, `0` unclassified)
- code-comment compatibility cleanup verdict: PASS
- targeted code sanity verdict: PASS with warning-level shared-venv coupling
- mission status: IN PROGRESS until brutal QA, final report, promotion plan, and commits are complete

## Next Steps

1. Produce the brutal QA report with adversarial verdicts and prune/promote/reject recommendations.
2. Produce the final sandbox report and promotion/cutover plan.
3. Re-run final git status / validation summary and separate code commits from docs/control commits.
4. Leave all live actions as proposal-only questions for Fritz.
