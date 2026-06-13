# Hermes Awareness Docs Consolidation Plan

Date: 2026-06-13
Status: prune/consolidation proposal only
Scope: Hermes-removal sandbox docs created during the 2026-06-13 mission waves

## Canonical vs Temporary vs Draft

Canonical Hermes-removal docs for first clean docs PR:
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

Temporary control material:
- `docs/hermes-removal-capability-control-packet-2026-06-13.md`
- `docs/hermes-removal-capability-matrix-2026-06-13.yaml`
- `docs/hermes-removal-preflight-checklist-2026-06-13.md`
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md`
- `docs/hyperwam-effectiveness-assessment-2026-06-13.md` (historical typo in filename; HyperSwarm is the canonical name)

Draft global awareness material:
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
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-research-fetcher-role-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`

## Full Inventory Classification

| file | mission role | first classification | prune action | notes |
|---|---|---|---|---|
| hermes-reference-inventory-2026-06-13.md | repo inventory evidence | promote in first clean docs PR | keep | core proof |
| hermes-reference-inventory-2026-06-13.yaml | machine-readable inventory | promote in first clean docs PR | keep | pair with md |
| hermes-external-compatibility-plan-2026-06-13.md | cutover doctrine | promote in first clean docs PR | keep | still useful after usage map |
| hermes-external-usage-map-2026-06-13.md | machine-specific external caller map | promote in first clean docs PR | keep | strongest new external truth |
| hermes-external-usage-map-2026-06-13.yaml | structured external usage map | promote in first clean docs PR | keep | pair with md |
| hermes-live-cutover-proposal-2026-06-13.md | live cutover sequence proposal | promote in first clean docs PR | keep | still proposal-only |
| hermes-wrapper-forwarding-plan-2026-06-13.md | wrapper end-state recommendation | promote in first clean docs PR | keep now / merge later | later merge with validation packet possible |
| hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md | live validation proposal | promote in first clean docs PR | keep now / merge later | approval-gated operational packet |
| hermes-removal-gap-log-2026-06-13.md | source of gaps | promote in first clean docs PR | keep | canonical gap truth |
| hermes-removal-brutal-qa-report-2026-06-13.md | quality verdict | promote in first clean docs PR | keep | reviewer-facing truth |
| hermes-removal-final-sandbox-report-2026-06-13.md | summary verdict | promote in first clean docs PR | keep | needs wording aligned to docs-only PR shape |
| hermes-removal-pr-readiness-check-2026-06-13.md | ancestry truth | promote in first clean docs PR | keep | blocks false PR claims |
| hermes-removal-clean-pr-transplant-manifest-2026-06-13.md | exact clean PR map | promote in first clean docs PR | keep | new canonical promotion map |
| hermes-awareness-docs-consolidation-plan-2026-06-13.md | doc taxonomy/prune plan | promote in first clean docs PR | keep | new prune truth |
| hermes-removal-promotion-plan-2026-06-13.md | high-level promotion posture | promote in first clean docs PR | keep now / consolidate later | now points to docs-only first PR |
| hermes-removal-mission-ledger-2026-06-13.md | mission chronology | promote in first clean docs PR | keep | useful historical control artifact |
| hermes-removal-capability-control-packet-2026-06-13.md | sandbox approval/control packet | keep sandbox-only | defer | narrow process artifact |
| hermes-removal-capability-matrix-2026-06-13.yaml | sandbox capability matrix | keep sandbox-only | defer | prototype control matrix |
| hermes-removal-preflight-checklist-2026-06-13.md | sandbox preflight | keep sandbox-only | defer | process-local |
| hermes-removal-next-lockdir-validation-plan-2026-06-13.md | next sandbox validation | superseded for first PR scope | archive | still useful historically, not first PR canon |
| hyperwam-effectiveness-assessment-2026-06-13.md | orchestration retro | defer to later awareness PR | defer | historical filename typo; HyperSwarm is the canonical name; not needed for first Hermes docs PR |
| shay-global-capability-matrix-draft-2026-06-13.md | global awareness narrative | defer to later awareness PR | defer | broad, still draft |
| shay-global-capability-matrix-draft-2026-06-13.yaml | global awareness structure | defer to later awareness PR | defer | pair with md |
| shay-adoption-backlog-2026-06-13.md | candidate adoption list | defer to later awareness PR | defer | useful but broad |
| shay-adoption-backlog-policy-2026-06-13.md | backlog policy | defer to later awareness PR | merge later | can later fold into a global control handbook |
| shay-adoption-backlog-schema-2026-06-13.yaml | backlog schema | defer to later awareness PR | merge later | pair with backlog system |
| shay-add-audit-prune-rule-2026-06-13.md | meta rule | defer to later awareness PR | merge later | likely fold into a broader global policy doc |
| shay-skills-gap-log-2026-06-13.md | skills-specific gap list | defer to later awareness PR | merge later | overlaps with larger gap system |
| shay-skills-readiness-matrix-2026-06-13.yaml | skills readiness data | defer to later awareness PR | keep draft | useful when policy matures |
| shay-worker-role-matrix-2026-06-13.md | worker-role control draft | defer to later awareness PR | keep draft | useful pattern, not first PR scope |
| shay-gap-log-schema-2026-06-13.yaml | generic gap schema | defer to later awareness PR | keep draft | broader than Hermes PR |
| shay-gap-resolution-workflow-2026-06-13.md | generic workflow | defer to later awareness PR | merge later | later combine with lifecycle policy |
| shay-gap-lifecycle-policy-2026-06-13.md | generic policy | defer to later awareness PR | merge later | later combine with workflow |
| shay-research-fetcher-role-2026-06-13.md | generic role doc | defer to later awareness PR | merge later | overlaps with workflow/cron docs |
| shay-capability-research-cron-design-2026-06-13.md | cron design | defer to later awareness PR | merge later | approval-gated and not first PR scope |

## Which Docs Are Canonical

Canonical right now:
- Hermes evidence and promotion docs listed in the first section above
- especially inventory, usage map, gap log, PR-readiness check, promotion plan, transplant manifest

## Which Docs Are Temporary Control Material

Temporary control material:
- capability control packet
- capability matrix
- preflight checklist
- next lock-dir validation plan
- HyperSwarm effectiveness assessment (historical filename typo uses `hyperwam`)

These are useful because they explain how the sandbox was safely run.
They are not the cleanest first PR story.

## Which Docs Are Draft Global Awareness Material

Draft-only for now:
- all `docs/shay-*2026-06-13*` awareness/control docs except where individual Hermes docs cite them as references

## Which Docs Should Become Global Shay Docs Later

Good later candidates:
- `shay-global-capability-matrix-draft-2026-06-13.*`
- `shay-add-audit-prune-rule-2026-06-13.md`
- `shay-adoption-backlog*`
- `shay-skills-readiness-matrix-2026-06-13.yaml`
- `shay-gap-lifecycle-policy-2026-06-13.md`
- `shay-gap-resolution-workflow-2026-06-13.md`
- `shay-gap-log-schema-2026-06-13.yaml`

## Which Docs Should Remain Hermes-Specific

Remain Hermes-specific:
- all `hermes-*2026-06-13*` docs tied to wrapper strategy, external usage, inventory, cutover order, PR readiness, and mission evidence

## Which Docs Should Be Merged Before Promotion

None are mandatory to merge before the first clean docs PR.

Recommended later merges:
- wrapper forwarding plan + live wrapper validation packet
- gap lifecycle policy + gap resolution workflow
- adoption backlog policy + add-audit-prune rule
- research fetcher role + capability research cron design

## Which Docs Should Not Be Promoted In First PR

Do not promote in first PR:
- generic `shay-*` awareness/control docs
- lock-dir next-step plan
- HyperSwarm retro doc (historical filename uses `hyperwam`)
- sandbox capability-control packet/matrix/checklist set

## Add = Audit + Prune Outcome

Keep:
- first clean docs PR Hermes evidence/control set

Merge later:
- wrapper docs pair
- lifecycle/workflow/policy clusters

Archive later:
- lock-dir next-step plan after that line of work is either done or replaced

Defer:
- broad Shay awareness/control cluster

Supersede later:
- older high-level promotion wording once the clean branch actually exists

## Bottom Line

The first clean PR should carry the tight Hermes-removal evidence story.
The broader Shay awareness system is real, but it belongs in a later awareness PR after consolidation.