# Shay Prune Recommendations

Date: 2026-06-13
Status: audit + prune recommendations only
Scope: current mission artifacts in `/Users/famtasticfritz/famtastic/shay-shay-main-sync-20260613/docs`
Authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`

## Executive finding

Add = Audit + Prune was applied to the current mission artifact set without deleting anything.

Current state:
- the clean worktree contains a tight Hermes-removal doc cluster plus an older memory/process cluster
- several Hermes docs still refer to a broader 2026-06-13 awareness/control cluster that is not present in this clean worktree
- the biggest immediate consolidation risk is not duplicate files on disk; it is duplicated narrative and phantom references to deferred docs

## Audit summary by cluster

### 1. Hermes-removal evidence/control cluster
Strong keep set:
- `docs/hermes-reference-inventory-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.yaml`
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.yaml`
- `docs/hermes-live-cutover-proposal-2026-06-13.md`
- `docs/hermes-wrapper-forwarding-plan-2026-06-13.md`
- `docs/hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md`
- `docs/hermes-removal-gap-log-2026-06-13.md`
- `docs/hermes-removal-pr-readiness-check-2026-06-13.md`
- `docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md`
- `docs/hermes-removal-promotion-plan-2026-06-13.md`
- `docs/hermes-removal-brutal-qa-report-2026-06-13.md`
- `docs/hermes-removal-final-sandbox-report-2026-06-13.md`
- `docs/hermes-removal-mission-ledger-2026-06-13.md`
- `docs/hermes-awareness-docs-consolidation-plan-2026-06-13.md`

Finding:
- this cluster is mostly valid, but several files repeat the same promotion truth in different packaging
- duplication is acceptable during mission execution, but later promotion should preserve one canonical state doc plus one evidence trail, not five co-equal summaries

### 2. Workstream-control cluster
Files inspected:
- `docs/shay-workstream-control-map-2026-06-12.md`

Finding:
- already labeled stale/superseded by newer Hermes docs
- still useful as historical umbrella map
- should not be deleted now because newer docs still cite it as prior context

### 3. Memory/process cluster
Files inspected:
- `docs/shay-memory-hierarchy.md`
- `docs/shay-memory-compaction-policy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
- `docs/shay-db-audit-2026-06-12.md`
- `docs/shay-db-status.md`
- `docs/session-json-audit-2026-06-12.md`
- `docs/proposed-memory-compaction-2026-06-12.md`
- `docs/private-memory-retrieval-design-2026-06-12.md`
- `docs/private-memory-access-surface-spec-2026-06-12.md`
- `docs/memory-architecture-validation-2026-06-12.md`

Finding:
- this cluster is healthier than the Hermes cluster because it already distinguishes canonical policy from diagnostic reviews
- pruning need is mostly label discipline, not file removal
- diagnostic reviews should stay preserved as evidence, while hierarchy/policy docs remain canonical

### 4. Process-intelligence / mission-growth cluster
Files observed now in this clean worktree:
- `docs/shay-process-intelligence-architecture-2026-06-13.md`
- `docs/shay-run-ledger-schema-2026-06-13.yaml`
- `docs/shay-decision-ledger-schema-2026-06-13.yaml`
- `docs/shay-tool-agent-ledger-schema-2026-06-13.yaml`
- `docs/shay-artifact-ledger-schema-2026-06-13.yaml`
- `docs/shay-hermes-lane-packet-2026-06-13.md`
- `docs/shay-process-intelligence-review-options-2026-06-13.md`
- `docs/shay-pruner-consolidator-lane-packet-2026-06-13.md`
- `docs/shay-prune-recommendations-2026-06-13.md`

Current finding:
- the first process-intelligence cluster is now landing in this branch
- the mission still demands more adjacent docs beyond the current set
- the known risk is overlap between architecture, schemas, pilot-run docs, lane packets, tracker docs, and pattern-scanner docs

Recommendation:
- use a small canon + evidence trail model
- keep schemas and architecture as canon candidates
- treat lane packets and review notes as evidence/support material
- see `docs/shay-process-intelligence-review-options-2026-06-13.md`

## Merge candidates

1. Wrapper cluster
- `docs/hermes-wrapper-forwarding-plan-2026-06-13.md`
- `docs/hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md`
Action: merge later
Why:
- end-state plan and validation packet are distinct today
- once approved/live-wired, they should likely become one canonical wrapper-cutover doc

2. External-usage cluster
- `docs/hermes-external-compatibility-plan-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.yaml`
Action: merge later at doctrine level, keep map/schema separate
Why:
- plan explains policy; map provides evidence
- later the plan should cite the map rather than restating its content

3. Promotion-state cluster
- `docs/hermes-removal-promotion-plan-2026-06-13.md`
- `docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md`
- `docs/hermes-removal-final-sandbox-report-2026-06-13.md`
- `docs/hermes-removal-brutal-qa-report-2026-06-13.md`
Action: partial merge later
Why:
- all four carry promotion-readiness truth
- recommendation is to keep QA report as review evidence, keep manifest as execution recipe, and eventually supersede the high-level promotion plan with the tracker or final merged PR packet

4. Memory-policy cluster
- `docs/private-memory-retrieval-design-2026-06-12.md`
- `docs/private-memory-access-surface-spec-2026-06-12.md`
Action: merge later
Why:
- both cover the same future retrieval surface from different angles
- policy should stay separate; design+surface spec can become one implementation design doc later

## Archive-later candidates

1. `docs/shay-workstream-control-map-2026-06-12.md`
Action: archive later as historical umbrella map
Condition:
- only after newer tracker/process docs fully replace its coordination role

2. `docs/proposed-memory-compaction-2026-06-12.md`
Action: archive later as proposal once compaction policy is treated as the canon
Condition:
- keep now because it captures the proposed replacement text and rationale

3. `docs/hermes-removal-mission-ledger-2026-06-13.md`
Action: archive later as historical mission evidence
Condition:
- only after a master tracker and lane packets exist and point back to it

## Quarantine candidates

1. Historical phantom/deferred doc references
This section records the first clean-worktree audit state before later Title 6 completion landed. Several items from that original list have since been restored or added on this branch, including the broader awareness cluster and the Hermes lane packet.
Still treat the remaining truly deferred or secondary surfaces below as quarantine candidates unless they are explicitly promoted later:
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md`
- `docs/hyperwam-effectiveness-assessment-2026-06-13.md` (historical filename typo; HyperSwarm is the canonical name)
Action: quarantine references, not files
Why:
- some entries in this cluster were real historical references before later restoration landed
- PR-facing docs must separate present-on-branch truth from deferred or secondary surfaces

2. Any future process-intelligence pilot-run doc that copies schema definitions inline
Action: quarantine from canon
Why:
- evidence docs should cite schemas, not become competing schema sources

## Supersede candidates

1. `docs/shay-workstream-control-map-2026-06-12.md`
Superseded by:
- Hermes-removal consolidation/pr-readiness/promotion docs
- upcoming master open-items tracker

2. High-level promotion prose in `docs/hermes-removal-promotion-plan-2026-06-13.md`
Supersede later with:
- the actual master open-items/completion tracker
- the actual clean PR packet once created

3. Diagnostic wording in `docs/shay-memory-architecture-review-2026-06-12.md`
Supersede where necessary with:
- canonical policy docs already in place
Why:
- the review should remain preserved, but not outrank the hierarchy/policy set

## What must not be deleted

Do not delete now:
- `docs/shay-full-autonomy-completion-mission-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.md`
- `docs/hermes-reference-inventory-2026-06-13.yaml`
- `docs/hermes-external-usage-map-2026-06-13.md`
- `docs/hermes-external-usage-map-2026-06-13.yaml`
- `docs/hermes-removal-gap-log-2026-06-13.md`
- `docs/hermes-removal-pr-readiness-check-2026-06-13.md`
- `docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md`
- `docs/hermes-removal-brutal-qa-report-2026-06-13.md`
- `docs/shay-memory-hierarchy.md`
- `docs/shay-memory-compaction-policy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-db-audit-2026-06-12.md`
- `docs/session-json-audit-2026-06-12.md`
- any upcoming master tracker, command map, or process-intelligence schema files

Reason:
- these are mission authority, canonical policy, schema/evidence roots, or primary proof artifacts

## Major risks

1. Narrative duplication risk
- multiple Hermes docs currently summarize the same readiness state

2. Phantom reference risk
- deferred or secondary surfaces can still be named repeatedly in current docs if labels slip

3. Canon-vs-evidence drift risk
- without labels, reports and policies can be mistaken as equal truth sources

4. Incoming process-intelligence sprawl risk
- mission amendments will generate many adjacent docs unless small-canon discipline holds

## Recommended next consolidation policy

1. Preserve all current evidence docs.
2. Add explicit labels later: canonical, evidence, draft, historical, superseded, quarantine.
3. Treat deferred or secondary referenced docs as quarantined until they are explicitly promoted into this branch's canon.
4. Promote one current-state tracker over multiple overlapping summary docs.
5. Keep YAML schemas as the machine-readable source whenever they exist.

## Bottom line

No deletion is justified.
The main prune win is classification:
- merge later: wrapper, external-usage, promotion-state, and private-memory design pairs
- archive later: older umbrella/proposal/history docs
- quarantine: references to deferred or missing broader awareness docs
- supersede: older umbrella maps and high-level summaries once tracker-based truth exists