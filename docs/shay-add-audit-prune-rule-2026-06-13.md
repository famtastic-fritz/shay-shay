# Shay Add = Audit + Prune Rule

Date: 2026-06-13

## Rule

Before adding any new skill, doc, matrix, backlog item, workflow, role, config rule, or capability record:
1. inspect related existing artifacts first
2. classify them as one of:
   - keep
   - update
   - merge
   - archive
   - quarantine
   - supersede
   - remove after backup
   - reject
   - needs Fritz approval
3. only then add the new artifact if the existing set still has a real gap

## Why

Without this rule, capability-awareness becomes additive paperwork instead of sharper truth.

## Hermes-Removal Examples

- `docs/shay-workstream-control-map-2026-06-12.md` -> supersede later
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md` -> archive later
- `docs/shay-capability-research-cron-design-2026-06-13.md` + `docs/shay-research-fetcher-role-2026-06-13.md` -> merge-overlap review later
- `docs/hermes-wrapper-forwarding-plan-2026-06-13.md` + `docs/hermes-live-wrapper-forwarder-validation-packet-2026-06-13.md` -> keep both now, merge later if wrapper work is promoted beyond proposal stage
- `docs/hermes-removal-promotion-plan-2026-06-13.md` + `docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md` -> promotion-plan summary plus exact manifest now; later collapse once the clean branch exists
- first clean PR scope -> docs/control only; code relabeling deferred until reconstruction is proven clean
- `skills/red-teaming/godmode/SKILL.md` -> quarantine by default in readiness routing
