# Shay master checklist

Date: 2026-06-15
Status: active working checklist
Purpose: one resumable control document spanning truth reconstruction, capability enforcement, research capture, swarm preflight, and verification.

## Current reality

What is real now:
- `shay intelligence truth` exists and exposes a curated truth registry with explicit reality classes.
- `shay capabilities preflight "<task>"` now evaluates matched capability truth, blocking capability states, missing prerequisites, warnings/gaps, required proof surfaces, and closeout actions.
- `shay capabilities closeout "<task>"` now renders proof-aware closeout requirements from the same capability truth layer.
- Focused verification passed for the new capability gate slice: `.venv/bin/python -m pytest -q tests/test_capabilities_cmd.py -o addopts=''`.
- The flat-file plan/control plane in the sibling `~/famtastic` repo can now prove zero active-plan drift after backfilling task-ledger rows and closeout packets; `node scripts/plans/audit.js` reports zero drift, zero conflicts, zero missing active plan files, and zero orphan tasks.
- Canonical doctrine and reconstruction artifacts now exist for this pass:
  - `docs/shay-source-of-truth-rules-2026-06-17.md`
  - `docs/shay-swarm-preflight-packet-2026-06-17.md`
  - `~/famtastic/obsidian/Shay-Memory/research/2026-06-17-shay-truth-reconstruction.md`

What is still not real yet:
- capability truth now evaluates verifier-backed promotion eligibility from live runtime observations, but curated matrix status still does not auto-flip from ledger evidence alone
- closeout is still advisory/gating output, not yet a write-back reconciler that mutates the matrix automatically
- broad external pattern research is still intentionally shallow for this pass; the durable internal reconstruction/drift artifact now exists
- delegate/swarm child summaries still cannot be trusted as proof by themselves; parent-level verification against the actual filesystem/runtime remains required

## Master checklist

### 1) Episodic-memory complement + retrieval alignment
- [x] verify where episodic memory truth should live versus MCP/basic-memory/shared-vault truth
- [x] document retrieval boundaries: session recall vs durable memory vs research artifact
- [x] map which surfaces are observation-only, interpretation-only, or mixed and split the mixed ones
- [x] identify the minimum proof needed before memory-routing claims can be promoted from seeded to proven

### 2) Capability truth layer
- [x] make capability-matrix checking executable before task execution
- [x] make proof-aware closeout requirements executable after task execution
- [x] add a write-back/reconciliation path so proven observations can update capability truth safely
- [x] define when a capability status may move between seeded / implemented / partial / proven-live
- [x] add explicit reality-class language to capability docs where the wording is still vague

### 3) Research artifact capture
- [x] keep the durable research artifact protocol as a required proof surface for research/memory tasks
- [x] run the protocol for this broader truth-reconstruction wave and capture the resulting artifact
- [x] ensure repo/doc archaeology and external-pattern research land in durable notes, not just terminal residue

### 4) Swarm telemetry + preflight
- [x] identify atomic research/build lanes with minimal context packets
- [x] route each lane by cheapest-sufficient model instead of one-size-fits-all heavy routing
- [x] define required proof artifacts per lane before dispatch
- [x] record swarm telemetry truth separately from self-reported child summaries

Current verified lesson:
- A read-only delegate wave was useful for rough drift hunting, but its self-reports were too mushy to count as proof. The parent lane had to verify with direct repo reads plus `node ~/famtastic/scripts/plans/audit.js` before any “clean” claim was real.
- A later delegate/subagent pressure test in this run reinforced the same point: two child summaries failed to ground on the requested files and returned unusable narrative. Negative proof still counts — child output may help generate leads, but closure remains parent-only.

### 5) Source-of-truth rules
- [x] define three canonical truth surfaces: working tree, committed branch, live runtime
- [x] add executable preflight/closeout gate language as distinct operational truth surfaces
- [x] document update gates for when truth can be promoted
- [x] document startup checks and closeout enforcement as standard session control rules

### 6) Implementation slice
- [x] add `preflight` capabilities subcommand
- [x] add `closeout` capabilities subcommand
- [x] add focused tests for gate failure/pass behavior and proof-surface requirements
- [x] add matrix write-back or ledger reconciliation as the next low-risk implementation slice

### 7) Verification + commit readiness
- [x] run focused pytest for capability gate slice
- [x] run broader verification once the next truth/doc slice lands
- [x] update any remaining docs that still overclaim without reality-class wording
- [x] leave a clean commit-ready report covering proof, gaps, and next slice

Latest proof artifact:
- `~/famtastic/tasks/tasks.jsonl` + six `plans/<id>/closeouts/2026-06-16-needs_tasking.json` packets repaired the flat-file control-plane drift, and `~/famtastic/command-center/{briefing.md,index.html,state.json}` was regenerated from the repaired ledgers.
- `~/famtastic/obsidian/Shay-Memory/research/2026-06-17-shay-truth-reconstruction.md` now captures the current truth-surface classification, drift archaeology, and source ledger for this pass.

## Done conditions for this wave

This wave counts as done only if:
1. the master checklist is the canonical resumable control artifact
2. source-of-truth rules are explicit and linked
3. swarm preflight exists with lane packets, proof targets, and reviewer boundaries
4. truth-surface reconstruction exists as a durable research artifact
5. child self-report is explicitly downgraded to evidence-only unless the parent verifies it
6. final closeout states which gaps remain open and what the next grounded implementation slice is

## Commit-readiness report

Current branch truth:
- branch: `main`
- modified tracked files:
  - `docs/learning-loop-verification-run-2026-06-15.md`
  - `docs/shay-master-checklist-2026-06-15.md`
- new untracked files:
  - `docs/shay-source-of-truth-rules-2026-06-17.md`
  - `docs/shay-swarm-preflight-packet-2026-06-17.md`

Proof carried by this wave:
- parent reopened all changed/new doctrine artifacts
- parent verified branch state directly with `git -C /Users/famtasticfritz/famtastic/shay-shay status --short --branch`
- durable research artifact exists at `~/famtastic/obsidian/Shay-Memory/research/2026-06-17-shay-truth-reconstruction.md`

Open gaps carried forward honestly:
1. verifier-backed promotion rules for moving capability status between seeded / implemented / partial / proven-live are still not implemented
2. broader capability-matrix reality-class cleanup beyond the CLI wording pass is still incomplete
3. process-intelligence normalization is still incomplete

Commit readiness verdict:
- docs/control packet is ready to commit as a truthful doctrine/reconstruction slice
- not a full learning-loop implementation closeout

## Next slice recommendation

Best next grounded slice:
1. add a low-risk write-back path that records observed proof into a capability ledger without silently promoting truth
2. require human- or verifier-backed promotion from observed artifact -> proven-live capability state
3. wire that ledger into `shay intelligence truth` so capability and intelligence truth stop drifting apart

## Resume sentence

Resume by building the smallest safe capability-truth write-back path, then run it against one real task class so the matrix learns from proof instead of staying purely curated.
