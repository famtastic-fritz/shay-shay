# Hermes Removal Final Sandbox Report

Date: 2026-06-13
Branch: `sandbox/hermes-removal-backup-of-now-20260613`
Lane: Hermes-removal sandbox

## 1. Is Hermes removed from sandbox current-product identity?

Mostly yes inside the sandbox repo’s active current-product identity surfaces.

After this wave, the surviving active-code Hermes references are deliberate compatibility shims or labeled historical/control references rather than unlabeled current-product identity.

## 2. What Hermes references remain and why?

Remaining categories:
- compatibility shims kept intentionally:
  - `HERMES_DASHBOARD_TOKEN`
  - `__HERMES__SESSION_TOKEN__`
  - `hermes-workspace` compatibility comments/tests/contracts
- historical provenance / migration evidence:
  - `SOUL.md`
  - `REBRAND-REPORT-2026-05-19.md`
  - `docs/upstream/hermes-v2026.5.16-delta-report.md`
- control/workstream docs where Hermes is the subject of the mission:
  - inventory, gap, compatibility, cutover, capability docs
- external remove-last surfaces outside the sandbox repo:
  - `~/.local/bin/hermes`
  - `~/.shay/hermes-agent`
  - `~/.hermes`

## 3. What should become Shay?

Already treated as Shay-native or clarified to be Shay-native:
- current dashboard/app/runtime identity
- current docs that describe present behavior
- current sandbox product-facing comments/docstrings when they were unlabeled compatibility residue
- canonical command/doc direction going forward

## 4. What should remain compatibility?

For now:
- `HERMES_DASHBOARD_TOKEN`
- `__HERMES__SESSION_TOKEN__`
- `hermes-workspace` compatibility contracts and associated tests/comments
- live `hermes` external surface as a future forwarder/remove-last contract until usage is mapped

## 5. What should remain historical?

- migration reports
- upstream Hermes delta/provenance docs
- archived design residue
- persona/SOUL references that discuss Hermes as the skeleton/provenance layer

## 6. What should be removed later?

Later, only after mapping and approval:
- direct live dependence on `hermes` command where forwarding can replace it
- `~/.shay/hermes-agent` if no longer needed
- `~/.hermes` after consumer-risk validation and explicit cutover approval
- superseded/stale planning docs after historical preservation is sufficient

## 7. What should be forwarded from `hermes` to `shay`?

Recommended future live behavior:
- `hermes` should forward to `shay`
- ideally with deprecation guidance, not silent disappearance
- do not remove the wrapper before external usage mapping closes the risk

## 8. Is sandbox safe enough for PR/promotion?

Yes, but only through a fresh clean docs/control PR branch.

Truthful verdict:
- current sandbox branch: NOT PR-CLEAN
- first clean PR shape: READY FOR CLEAN DOCS PR
- live cutover: NOT READY

Why not a cleaner or broader PASS:
- targeted test/compile validation still uses the live checkout `.venv` path
- capability-awareness docs still need pruning/consolidation
- the current sandbox branch carries inherited local-only history
- code relabeling/reconstruction was not proven cleanly transplantable onto current `origin/main`

## 9. What exact live actions require Fritz approval?

- create a sandbox-local `.venv` if he wants the next wave to remove shared-venv coupling
- replace or forward the live `hermes` shim
- delete `~/.local/bin/hermes`
- delete `~/.shay/hermes-agent`
- delete `~/.hermes`
- edit any live launch agent
- restart live services
- enable real tokens/platforms in validation
- push any branch

## 10. What gaps remain?

Primary open gaps:
- `sandbox-no-local-venv`
- `sandbox-home-not-yet-startup-validated`
- `hermes-external-client-usage-unknown`
- `provider-health-partial-only`
- `mcp-sandbox-independence-unproven`
- `skill-presence-not-equal-host-readiness`
- `legacy-hermes-home-sensitive`
- `sandbox-tests-share-live-venv`
- `delegation-must-be-read-only-scoped`

Closed / constrained:
- `gateway-lock-dir-default-outside-shay-home`
- `path-missing-python-pytest-pip`

## 11. What did the awareness matrix add?

It added a reusable truth model:
- what is healthy vs warning vs forbidden
- what is passive-only vs execution-grade
- what needs approval
- what is a skill-presence illusion vs host-ready capability
- what fallbacks exist when proof is partial

That is real value. It stops fake closure.

## 12. What did HyperSwarm add?

Note: earlier sandbox notes called this "HyperWAM"; HyperSwarm is the canonical name.

It added:
- better lane discipline
- stronger safety boundaries
- adversarial review framing
- explicit owner/checker/gap roles

It also added paperwork risk. The fix is prune discipline, not throwing HyperSwarm away.

## 13. What is the recommended next move?

Recommended next move:
1. prepare a fresh docs/control-only PR branch from current `origin/main` later, using the clean transplant manifest
2. keep broader capability-awareness artifacts as draft/control material unless or until they are pruned into a tighter canon
3. keep code relabeling/reconstruction deferred to a later PR
4. keep the live wrapper change proposal-only until the validation packet is separately approved

## Final Sandbox Verdict

READY FOR CLEAN DOCS PR

Not ready for live cutover.
Not ready for code relabeling PR from the current sandbox branch.
