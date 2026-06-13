# Hermes Removal Clean PR Transplant Manifest

Date: 2026-06-13
Status: proposal only
Scope: first clean PR from fresh current `origin/main` branch

## PR Intent

The first clean PR should be docs/control only.

It should not attempt to carry code relabeling or reconstruction work from `e58f8f9`.
It should not be opened from the current sandbox branch.
It should be rebuilt manually from a fresh branch off current `origin/main`.

## Files To Include In First Clean PR

Promote in first clean docs PR:
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

Why these belong:
- they document the real Hermes-removal truth discovered in the sandbox
- they define safe promotion shape
- they preserve evidence for later wrapper and cutover approval
- they do not require the missing local-only code history to make sense

## Files To Exclude From First Clean PR

Exclude for now:
- `docs/shay-global-capability-matrix-draft-2026-06-13.md`
- `docs/shay-global-capability-matrix-draft-2026-06-13.yaml`
- `docs/shay-adoption-backlog-2026-06-13.md`
- `docs/shay-adoption-backlog-policy-2026-06-13.md`
- `docs/shay-adoption-backlog-schema-2026-06-13.yaml`
- `docs/shay-add-audit-prune-rule-2026-06-13.md`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/shay-gap-log-schema-2026-06-13.yaml`
- `docs/shay-research-fetcher-role-2026-06-13.md`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`
- `docs/hermes-removal-capability-control-packet-2026-06-13.md`
- `docs/hermes-removal-capability-matrix-2026-06-13.yaml`
- `docs/hermes-removal-preflight-checklist-2026-06-13.md`
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md`
- `docs/hyperwam-effectiveness-assessment-2026-06-13.md`

Why these are excluded:
- they are valuable but broader than the first Hermes docs/control PR
- several are prototype awareness/control docs that still need consolidation
- some are narrow sandbox process records rather than first-PR canon
- they would widen the PR beyond the cleanest narrative

## Files To Defer

### Defer to later awareness PR
- `docs/shay-global-capability-matrix-draft-2026-06-13.*`
- `docs/shay-adoption-backlog*`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/shay-gap-log-schema-2026-06-13.yaml`
- `docs/shay-research-fetcher-role-2026-06-13.md`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`
- `docs/shay-add-audit-prune-rule-2026-06-13.md`

### Defer as sandbox-only process artifacts for now
- `docs/hermes-removal-capability-control-packet-2026-06-13.md`
- `docs/hermes-removal-capability-matrix-2026-06-13.yaml`
- `docs/hermes-removal-preflight-checklist-2026-06-13.md`
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md`
- `docs/hyperwam-effectiveness-assessment-2026-06-13.md`

## Code Changes To Defer

Defer all code/test relabeling and reconstruction from the first clean PR.

Explicitly deferred:
- `shay_cli/web_server.py`
- `shay_cli/mcp_config.py`
- `shay_cli/conductor_missions.py`
- `gateway/chat_stream_routes.py`
- `gateway/platforms/api_server.py`
- `tests/shay_cli/test_mcp_api_routes.py`
- `tests/shay_cli/test_dashboard_bearer_auth.py`
- `tests/shay_cli/test_conductor_missions.py`

Reason:
- `e58f8f9` did not apply cleanly onto current `origin/main`
- first PR should prove promotion shape, not stretch into reconstruction

## Docs To Merge / Consolidate

Merge or consolidate later:
- `docs/hermes-wrapper-forwarding-plan-2026-06-13.md`
  + `docs/hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md`
  - keep both for now; later merge into one canonical wrapper cutover doc if promoted beyond proposal stage
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
  + `docs/hermes-external-usage-map-2026-06-13.md`
  - keep both for first PR; later compatibility plan can cite map rather than restate it
- `docs/hermes-removal-promotion-plan-2026-06-13.md`
  + `docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md`
  - keep both for now; later the manifest can be archived after the clean PR is created

## Exact Transplant Method

When approved later:
1. go to the clean evidence lane rooted at current `origin/main`
2. create a fresh branch from current `origin/main`
3. copy only the approved docs/control files from this sandbox into that clean branch
4. review each file against the consolidation plan before staging
5. run validation commands
6. commit docs only
7. open PR only after Fritz approves that next step

Recommended shell shape later:
```bash
cd /Users/famtasticfritz/famtastic/shay-shay-main-sync-20260613
git checkout -b pr/hermes-removal-docs-control-20260613 origin/main
# copy approved files from sandbox path into this branch
# review diffs
# run validation
# commit docs only
```

## Validation Commands

Run later on the clean PR branch:
```bash
git status --short
git diff --stat origin/main...
git diff --name-only origin/main...
```

Required truth checks:
```bash
rg -n "READY FOR PR WITH WARNINGS|open a narrow PR from this sandbox|code/test cleanup commit" docs
rg -n "docs/control only|defer|origin/main|fresh branch" docs/hermes-removal-*.md docs/hermes-awareness-*.md
```

Optional sanity checks:
```bash
python3 - <<'PY'
from pathlib import Path
approved = [
    'docs/hermes-reference-inventory-2026-06-13.md',
    'docs/hermes-reference-inventory-2026-06-13.yaml',
    'docs/hermes-external-compatibility-plan-2026-06-13.md',
    'docs/hermes-external-usage-map-2026-06-13.md',
    'docs/hermes-external-usage-map-2026-06-13.yaml',
    'docs/hermes-live-cutover-proposal-2026-06-13.md',
    'docs/hermes-wrapper-forwarding-plan-2026-06-13.md',
    'docs/hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md',
    'docs/hermes-removal-gap-log-2026-06-13.md',
    'docs/hermes-removal-brutal-qa-report-2026-06-13.md',
    'docs/hermes-removal-final-sandbox-report-2026-06-13.md',
    'docs/hermes-removal-pr-readiness-check-2026-06-13.md',
    'docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md',
    'docs/hermes-awareness-docs-consolidation-plan-2026-06-13.md',
    'docs/hermes-removal-promotion-plan-2026-06-13.md',
    'docs/hermes-removal-mission-ledger-2026-06-13.md',
]
for rel in approved:
    print('OK', rel, Path(rel).exists())
PY
```

## Expected PR Title

`docs: preserve Hermes removal evidence and promotion controls`

## Expected PR Body

Suggested body shape:
- documents the Hermes-removal sandbox findings without pretending the sandbox branch is PR-clean
- preserves inventory, compatibility, external-usage, wrapper-planning, gap, QA, and promotion-control artifacts
- records that live cutover and wrapper replacement are still approval-gated
- defers code relabeling/reconstruction to a later PR because the prior commit stack is not cleanly transplantable onto current `origin/main`

## Risks

- over-promoting draft awareness docs would widen the first PR and muddy the story
- under-promoting key Hermes evidence docs would force later retelling of already-proven truth
- leaving stale wording in `hermes-removal-final-sandbox-report` or `hermes-removal-promotion-plan` would create internal contradiction
- the wrapper-validation packet must stay proposal-only until live approval exists

## Reviewer Checklist

- [ ] branch starts from current `origin/main`
- [ ] PR contains docs/control files only
- [ ] no code or test file is staged
- [ ] no live cutover claim is made
- [ ] no wrapper replacement claim is made
- [ ] final sandbox report and promotion plan agree on docs-only first PR
- [ ] deferred code relabeling is called out explicitly
- [ ] excluded awareness/control docs are intentionally absent

## Bottom Line

First clean PR: docs/control only.
Code relabeling: later.
Live wrapper change: later and approval-gated.