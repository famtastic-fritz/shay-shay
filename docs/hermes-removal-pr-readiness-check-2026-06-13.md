# Hermes Removal PR Readiness Check

Date: 2026-06-13
Lane: Hermes-removal sandbox
Scope: read-only Git ancestry and transplant-readiness inspection only

## Question

Is the sandbox branch actually PR-clean against current `origin/main`?

Short answer: no.

Final verdict:
- PR-ready only after clean cherry-pick branch

## Branch / Base Truth

Sandbox worktree:
- path: `/Users/famtasticfritz/famtastic/shay-shay-hermes-removal-sandbox-20260613`
- branch: `sandbox/hermes-removal-backup-of-now-20260613`
- HEAD: `f748523a598e31401aaa6d9399aab67d9b4c88f0`

Clean origin/main evidence lane:
- path: `/Users/famtasticfritz/famtastic/shay-shay-main-sync-20260613`
- branch: `sync/workstream-control-map-20260613`
- HEAD: `20dd4b1ad239a8ddcb560afc2fc26cb5d21fcb66`

Merge-base:
- `70db100f6f67b07bcd359b516a02b38056702fec`

Interpretation:
- the sandbox does not descend from current `origin/main`
- it forked before the current `origin/main` head
- it carries a large amount of local-only history from the live checkout lane

## Ahead / Behind Shape

`git rev-list --left-right --count origin/main...HEAD` returned:
- left-only (`origin/main` only): 2 commits
- right-only (sandbox only): 55 commits

Meaning:
- the sandbox is missing 2 commits that exist on current `origin/main`
- the sandbox also contains 55 commits not on `origin/main`

This is not a narrow PR shape.

## Sandbox Commits Ahead of `origin/main`

The visible ahead range starts with:
- `f748523 docs: add Hermes removal inventory and QA control packet`
- `e58f8f9 refactor: label legacy Hermes compatibility surfaces`
- `7ea3d9d docs: add capability gap lifecycle and research watcher design`
- `e6d7c6a docs: add capability gap lifecycle and research watcher design`
- `a644a0a docs: validate Hermes sandbox lock-dir isolation`
- `b6ac858 docs: add HyperWAM skill and lock-dir validation plan`
- `a8e5f7a docs: record sandbox gateway validation result`
- `38a35b6 docs: add Hermes sandbox startup approval packet`
- `c4eebbe docs: validate Hermes sandbox help path`
- `e566282 docs: refine hermes removal sandbox controls`
- `1a21046 docs: add Hermes removal capability controls`
- `5c3cbb2 docs: add Shay workstream control map`
- plus many older non-Hermes mission commits below that point

Interpretation:
- the branch includes the Hermes-removal workstream
- but it also includes unrelated local-only feature and docs history that is not cleanly aligned to current `origin/main`

## File Diff Shape vs `origin/main`

`git diff --stat origin/main...HEAD` returned:
- 125 files changed
- 21,848 insertions
- 2,234 deletions

This is far too broad to describe as a clean Hermes-removal PR as-is.

The diff includes:
- Hermes-removal docs/control artifacts
- HyperSwarm/capability-awareness drafts
- many unrelated code, tests, gateway, memory, dashboard, model, kanban, and web changes inherited from local live-checkout history

## Can the Two Latest Mission Commits Be Cherry-Picked Cleanly Onto `origin/main`?

Checked read-only with patch-apply tests against the clean main-sync lane.

### Commit `e58f8f9`
Result: not cleanly transplantable as-is

Observed failures included:
- `gateway/chat_stream_routes.py: No such file or directory`
- `shay_cli/conductor_missions.py: No such file or directory`
- `tests/shay_cli/test_conductor_missions.py: No such file or directory`
- `tests/shay_cli/test_dashboard_bearer_auth.py: No such file or directory`
- `tests/shay_cli/test_mcp_api_routes.py: No such file or directory`
- context mismatches in `gateway/platforms/api_server.py`, `shay_cli/mcp_config.py`, and `shay_cli/web_server.py`

Interpretation:
- this commit depends on local-only prerequisite history absent from `origin/main`
- it cannot be advertised as a clean cherry-pick candidate onto main as-is

### Commit `f748523`
Result: not independently proven cherry-pick-clean in this pass

Reason:
- the first commit check failed hard enough to show the pair is not a clean standalone stack onto current `origin/main`
- `f748523` is docs-only, but its surrounding PR shape still sits on a branch with unrelated local-only ancestry drift
- if promoted later, this docs material should be manually restaged or transplanted on a clean branch rather than trusted as an as-is stack continuation

## Unrelated Local History Risk

Risk level: high

Why:
- sandbox merge-base predates current `origin/main`
- sandbox is missing mainline commits
- sandbox carries 55 right-only commits
- as-is PR would mix Hermes-removal work with unrelated inherited history

## Exact Promotion Method Recommended

Do not open a PR from the current sandbox branch.

Use this later approved method instead:
1. start a fresh PR branch from clean `origin/main` / main-sync truth
2. manually transplant only the Hermes-removal artifacts that still matter
3. treat `e58f8f9` as a reconstruction candidate, not a guaranteed cherry-pick
4. restage docs/control artifacts explicitly from the sandbox
5. keep global awareness drafts optional/draft-only unless separately approved
6. run final targeted validation on the clean PR branch
7. open the narrow PR from that clean branch only

## Recommended PR Scope on the Future Clean Branch

Likely include later:
- `docs/hermes-reference-inventory-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.yaml`
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.yaml`
- `docs/hermes-wrapper-forwarding-plan-2026-06-13.md`
- `docs/hermes-live-cutover-proposal-2026-06-13.md`
- `docs/hermes-removal-gap-log-2026-06-13.md`
- `docs/hermes-removal-brutal-qa-report-2026-06-13.md`
- `docs/hermes-removal-final-sandbox-report-2026-06-13.md`
- `docs/hermes-removal-promotion-plan-2026-06-13.md`
- `docs/hermes-removal-pr-readiness-check-2026-06-13.md`
- `docs/hermes-removal-mission-ledger-2026-06-13.md`

Maybe include later, but only after separate judgment:
- `e58f8f9`-equivalent code/test relabeling changes reconstructed cleanly against current `origin/main`

Keep draft/control only for now:
- `docs/shay-global-capability-matrix-draft-2026-06-13.*`
- `docs/shay-adoption-backlog*`
- other broad awareness/control drafts unless a consolidation pass explicitly promotes them

## Final Verdict

PR verdict:
- PR-ready only after clean cherry-pick branch

Why this exact verdict instead of `not PR-ready: unrelated local history`:
- the Hermes-removal work itself looks promotable
- the current branch shape is the problem
- the right answer is not to discard the wave; it is to re-home it onto a clean branch later

## Bottom Line

The sandbox lane produced useful truth.
It did not produce a branch you should open as a PR directly against `origin/main`.
The honest promotion path is a fresh clean branch plus selective transplant/reconstruction.