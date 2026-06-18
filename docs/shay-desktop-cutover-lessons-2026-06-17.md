# Shay Desktop cutover lessons — 2026-06-17

Status: durable recovery note

## Observation
- The runtime/gateway/dashboard plumbing could be made partially healthy while the actual desktop product remained broken.
- `/Applications/Shay Desktop.app` behaved like a wrapper-style surface, while `/Applications/ShayDesktop.app` appeared to be the heavier existing Electron bundle lineage.
- The upstream desktop source already existed locally at `/Users/famtasticfritz/.hermes/hermes-agent/apps/desktop/`.
- Workspace and dashboard surfaces were rewired before the canonical desktop base was conclusively identified and validated as a working product.
- End-to-end verification exposed the truth: port health and API health passed, but the desktop shell still failed and Workspace still had contract mismatches.

## Interpretation
- Plumbing proof is not product proof.
- In a multi-surface app family, the first move must be to identify the canonical working surface before attempting any runtime cutover or rebrand.
- Wrapper apps, alias apps, shortcuts, and app-bundle copies must not be treated as equally authoritative. One canonical source app and one canonical source tree must be named first.
- Source-level rebuilds beat local app-bundle surgery. Bundle patching is acceptable only as a short-lived diagnostic move, not as the primary cutover strategy.

## New cutover rule
Before any future Shay/Desktop/Workspace/Web cutover:

1. Identify every installed surface.
   - Example: `Shay Desktop.app`, `ShayDesktop.app`, `Hermes.app`, Workspace bundle, shell wrappers, symlinks.
2. Classify each surface.
   - wrapper / shortcut
   - real Electron bundle
   - source tree build artifact
   - local patched copy
3. Name the canonical base.
   - one installed app
   - one source tree
4. Verify the canonical base works as a product before rewiring anything else.
   - launch
   - key screens render
   - critical functions work
   - logs are clean enough
5. Only then do rebrand/cutover work.
   - runtime root
   - env wiring
   - dashboard/gateway URLs
   - token/auth contract
6. Verify at product level, not just infra level.
   - icon launch
   - shell readiness
   - feature flows
   - companion surfaces

## Anti-repeat checklist
- Do not treat HTTP 200 as success if the app shell is broken.
- Do not patch multiple app bundles before choosing a canonical app.
- Do not let Workspace/Web drive the desktop decision; desktop base comes first.
- Do not report cutover success until both infra proof and visible product proof pass.
- Distinguish clearly between:
  - observation: what was verified live
  - interpretation: what we think it means

## Operational change
For Shay surface work, future reports must include a dedicated section:
- Canonical base app
- Canonical source tree
- Wrapper/alias surfaces ignored or retired
- Product-level proof
- Remaining gaps

## Current honest takeaway
This pass proved pieces of the runtime contract, but it did not prove a working Shay Desktop product. The correct recovery path is to return to canonical-surface identification, choose the real Electron base, and rebuild/rebrand from source instead of continuing bundle-level patch stacking.
