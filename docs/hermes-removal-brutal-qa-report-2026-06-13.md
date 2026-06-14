# Hermes Removal Brutal QA Report

Date: 2026-06-13
Lane: Hermes-removal sandbox
Method: HyperSwarm + adversarial review
Note: earlier sandbox notes used the name "HyperWAM"; HyperSwarm is the canonical name.

## Executive Verdict

- current product-identity cleanup in active code/comments/tests: PASS
- sandbox-only documentation/control expansion: PASS WITH WARNINGS
- capability-awareness usefulness: WARNING
- PR readiness: READY FOR PR WITH WARNINGS
- live cutover readiness: NEEDS FRITZ APPROVAL / UNSAFE TO EXECUTE NOW

## What Is Actually Done

- Active code/comment/test references that still use Hermes for current behavior were reviewed.
- Safe replacements were applied only where Hermes was clearly acting as unlabeled compatibility residue in comments/docstrings.
- Compatibility-critical strings and env/token surfaces were preserved intentionally.
- A full sandbox-repo Hermes reference inventory was generated and classified.
- External Hermes surfaces were mapped into a proposal-only compatibility/cutover packet.
- The Hermes lane was expanded into a broader capability-awareness prototype: global capability matrix draft, worker-role matrix, skills readiness matrix, skills gap log, adoption backlog, and add=audit+prune rule.
- Gap records were normalized into explicit fields with one next action each.
- Targeted validation passed:
  - repo re-scan: 34 Hermes-hit files, 0 unclassified
  - `py_compile` on touched Python/test files: passed
  - targeted pytest on touched tests: `48 passed`

## What Is Not Done

- Hermes is not removed from live external surfaces.
- External callers/readers of `hermes`, `~/.shay/hermes-agent`, and `~/.hermes` are not fully mapped.
- Sandbox execution is not self-contained; it still depends on the live checkout `.venv` path for execution-grade proof.
- No live wrapper forwarding was implemented.
- No live cutover was attempted.
- No proof was produced that every broader capability draft should become canon as-is.

## What Is Still Unsafe

- Deleting or replacing `~/.local/bin/hermes`
- Deleting `~/.shay/hermes-agent`
- Deleting `~/.hermes`
- Editing live launch agents
- Restarting live services
- Claiming sandbox self-sufficiency
- Claiming live cutover readiness

## What Is Only Partially Proven

- Sandbox runtime independence: partial only
- MCP sandbox independence: unproven
- Provider/model readiness: passive only
- Skill readiness beyond discovery: conditional and lane-dependent
- HyperSwarm canon readiness: useful, but still prone to paperwork sprawl

## Weak Assumptions That Must Stay Labeled Weak

- Passing targeted tests using the live checkout `.venv` does not equal sandbox-local runtime readiness.
- A compatibility shim comment/docstring update does not prove full Hermes removal.
- A capability matrix draft does not automatically become a trustworthy operating system.
- Skill presence does not equal host readiness.
- Inventory completeness for the repo does not equal live cutover readiness.

## What Could Break Live Shay

- Premature wrapper replacement if hidden external callers still expect `hermes`
- Premature deletion of `~/.shay/hermes-agent`
- Premature deletion of `~/.hermes`
- Any unapproved live launchd edit or restart

## What Could Break Human Habits / Scripts

- Removing the `hermes` command before forwarding/deprecation guidance exists
- Changing docs/mental models faster than shell habits are mapped
- Treating historical Hermes references as branding bugs when they are actually provenance or compatibility evidence

## What Still Depends On Shared Live `.venv`

- `py_compile` sanity check for touched Python/test files in this mission
- targeted pytest execution for touched tests in this mission
- any future execution-grade proof unless a sandbox-local `.venv` is created or another approved path is chosen

## What Still Needs Fritz Approval

- creating a sandbox-local `.venv` if the next wave should remove shared-venv coupling
- any live wrapper replacement or forwarding rollout
- any live deletion of Hermes surfaces
- any live launchd edit or service restart
- any cron/watcher implementation with real side effects
- any push

## Open Gaps

Open / active:
- `sandbox-no-local-venv`
- `sandbox-home-not-yet-startup-validated`
- `hermes-external-client-usage-unknown`
- `provider-health-partial-only`
- `mcp-sandbox-independence-unproven`
- `skill-presence-not-equal-host-readiness`
- `legacy-hermes-home-sensitive`
- `sandbox-tests-share-live-venv`
- `delegation-must-be-read-only-scoped`

Closed / accepted-risk / constrained:
- `gateway-lock-dir-default-outside-shay-home` -> closed for the narrow override question
- `path-missing-python-pytest-pip` -> accepted-risk / non-blocking host-path caveat

## What Should Be Pruned

Candidates to merge/archive/supersede later:
- `docs/shay-workstream-control-map-2026-06-12.md` -> supersede later
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md` -> archive later
- overlap review later between:
  - `docs/shay-capability-research-cron-design-2026-06-13.md`
  - `docs/shay-research-fetcher-role-2026-06-13.md`
- future catalog-prune review for skills that remain candidate/blocked/quarantine only

## What Should Be Promoted

Strongest promotable artifacts from this wave:
- `docs/hermes-reference-inventory-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.yaml`
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
- `docs/hermes-live-cutover-proposal-2026-06-13.md`
- `docs/hermes-removal-gap-log-2026-06-13.md`
- targeted compatibility-labeling comment/docstring/test changes in active code

## What Should Be Rejected

Reject these overclaims:
- “Hermes is fully removed.”
- “Sandbox runtime is self-contained.”
- “Live cutover is ready now.”
- “Every capability-awareness artifact here is canonical without further pruning.”

## Is The Capability-Awareness System Useful Or Just Paperwork?

Verdict: WARNING

It is useful because it forced:
- lane discipline
- explicit approval gates
- gap normalization
- separation of compatibility vs identity residue
- separation of helper proof vs runtime proof

It becomes paperwork when:
- too many overlapping artifacts accumulate without consolidation
- ledgers drift out of date
- drafts are mistaken for readiness

Current judgment: useful prototype, not yet clean canon.

## Did HyperSwarm Help Or Add Friction?

Verdict: PASS WITH FRICTION

Helped:
- stronger dispatcher/runner/checker/reviewer separation
- better safety discipline
- better adversarial framing
- better gap logging

Added friction:
- artifact sprawl risk
- overhead if the recorder/pruner discipline slips

Bottom line: HyperSwarm improved truthfulness and safety, but needs aggressive prune discipline to stay FAMtastic instead of bureaucratic.

## Hermes End-State Recommendation

- in repo active identity: Hermes is reduced to deliberate compatibility/historical/control references only
- external command/home surfaces: Hermes must remain temporarily, preferably as forward/remove-last candidates
- live cutover: not yet

## Final QA Verdict Matrix

- inventory classification: PASS
- code sanity: PASS
- state isolation proof: WARNING
- capability controls: PASS WITH WARNINGS
- skill matrix honesty: PASS WITH WARNINGS
- docs consistency: WARNING
- live cutover readiness: NEEDS FRITZ APPROVAL / UNSAFE NOW
- overall: READY FOR PR WITH WARNINGS
