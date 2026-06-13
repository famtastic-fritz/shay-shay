# Hermes Removal Promotion Plan

Date: 2026-06-13
Status: proposal only

## Promotion Target

Promote the Hermes-removal sandbox work as a narrow PR that tightens current Shay identity labeling, preserves necessary compatibility shims, and ships the strongest evidence/control docs without pretending live cutover is ready.

## Recommended PR Scope

### First Clean PR Only

Docs/control only:
- `docs/hermes-reference-inventory-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.yaml`
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.yaml`
- `docs/hermes-live-cutover-proposal-2026-06-13.md`
- `docs/hermes-wrapper-forwarding-plan-2026-06-13.md`
- `docs/hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md`
- `docs/hermes-removal-gap-log-2026-06-13.md`
- `docs/hermes-removal-brutal-qa-report-2026-06-13.md`
- `docs/hermes-removal-final-sandbox-report-2026-06-13.md`
- `docs/hermes-removal-pr-readiness-check-2026-06-13.md`
- `docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md`
- `docs/hermes-awareness-docs-consolidation-plan-2026-06-13.md`
- `docs/hermes-removal-promotion-plan-2026-06-13.md`
- `docs/hermes-removal-mission-ledger-2026-06-13.md`

### Explicitly Deferred From First Clean PR

Code / tests:
- `shay_cli/web_server.py`
- `shay_cli/mcp_config.py`
- `shay_cli/conductor_missions.py`
- `gateway/chat_stream_routes.py`
- `gateway/platforms/api_server.py`
- `tests/shay_cli/test_mcp_api_routes.py`
- `tests/shay_cli/test_dashboard_bearer_auth.py`
- `tests/shay_cli/test_conductor_missions.py`

Reason:
- the code/test relabeling stack was not proven cleanly transplantable onto current `origin/main`
- first PR should establish clean docs/control truth, not stretch into reconstruction

### Keep As Draft / Secondary Control Material Unless Later Promoted

- `docs/shay-global-capability-matrix-draft-2026-06-13.md`
- `docs/shay-global-capability-matrix-draft-2026-06-13.yaml`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-adoption-backlog-2026-06-13.md`
- `docs/shay-adoption-backlog-schema-2026-06-13.yaml`
- `docs/shay-adoption-backlog-policy-2026-06-13.md`
- `docs/shay-add-audit-prune-rule-2026-06-13.md`
- `docs/shay-gap-log-schema-2026-06-13.yaml`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-research-fetcher-role-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`
- `docs/hermes-removal-capability-control-packet-2026-06-13.md`
- `docs/hermes-removal-capability-matrix-2026-06-13.yaml`
- `docs/hermes-removal-preflight-checklist-2026-06-13.md`
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md`
- `docs/hyperwam-effectiveness-assessment-2026-06-13.md`

Reason: useful, but wider than the first clean docs/control PR and still candidates for later consolidation.

## Promotion Gates

Must be true before PR:
- inventory remains at 0 unclassified repo hits
- code sanity stays green
- targeted tests stay green
- final reports do not overclaim sandbox self-sufficiency or live cutover readiness
- commit history clearly separates code/test changes from docs/control changes
- promotion branch is rebuilt from current `origin/main` or otherwise proven clean against it

## Cutover Gates (Not For This PR)

Must be true before any live cutover:
- external Hermes callers/readers are mapped
- Fritz approves live wrapper strategy
- wrapper forwarding packet is explicit
- any deletion of Hermes surfaces is separately approved
- launchd/service edits are separately approved

## Recommended Commit Split

1. first clean docs/control commit
   - scope: Hermes-removal evidence, gap, QA, wrapper-planning, PR-readiness, and promotion-control docs only
2. later code/test reconstruction commit
   - scope: `e58f8f9`-style relabeling only after clean reconstruction against current `origin/main`

## Promotion Verdict

- PR promotion from current sandbox branch: NOT READY AS-IS
- PR promotion after fresh clean branch from current `origin/main`: READY WITH WARNINGS
- live cutover promotion: NOT READY: LIVE CUTOVER NEEDS APPROVAL

## Immediate Next Move After Commit

Do not open a PR from this sandbox branch.
Instead:
1. use the clean PR transplant manifest to prepare a fresh docs/control-only branch from current `origin/main` later, when Fritz explicitly approves branch creation
2. keep code relabeling deferred to a later reconstruction PR
3. keep live wrapper replacement proposal-only until Fritz separately approves the validation packet
