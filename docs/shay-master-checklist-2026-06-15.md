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

What is still not real yet:
- capability truth is still curated code, not yet auto-updated from live runtime observations
- closeout is advisory/gating output, not yet a write-back reconciler that mutates the matrix automatically
- multi-swarm research and drift archaeology artifacts are not yet collected for this pass
- the process-intelligence spine is still only partially normalized

## Master checklist

### 1) Episodic-memory complement + retrieval alignment
- [ ] verify where episodic memory truth should live versus MCP/basic-memory/shared-vault truth
- [ ] document retrieval boundaries: session recall vs durable memory vs research artifact
- [ ] map which surfaces are observation-only, interpretation-only, or mixed and split the mixed ones
- [ ] identify the minimum proof needed before memory-routing claims can be promoted from seeded to proven

### 2) Capability truth layer
- [x] make capability-matrix checking executable before task execution
- [x] make proof-aware closeout requirements executable after task execution
- [ ] add a write-back/reconciliation path so proven observations can update capability truth safely
- [ ] define when a capability status may move between seeded / implemented / partial / proven-live
- [ ] add explicit reality-class language to capability docs where the wording is still vague

### 3) Research artifact capture
- [x] keep the durable research artifact protocol as a required proof surface for research/memory tasks
- [ ] run the protocol for this broader truth-reconstruction wave and capture the resulting artifact
- [ ] ensure repo/doc archaeology and external-pattern research land in durable notes, not just terminal residue

### 4) Swarm telemetry + preflight
- [ ] identify atomic research/build lanes with minimal context packets
- [ ] route each lane by cheapest-sufficient model instead of one-size-fits-all heavy routing
- [ ] define required proof artifacts per lane before dispatch
- [ ] record swarm telemetry truth separately from self-reported child summaries

### 5) Source-of-truth rules
- [x] define three canonical truth surfaces: working tree, committed branch, live runtime
- [x] add executable preflight/closeout gate language as distinct operational truth surfaces
- [ ] document update gates for when truth can be promoted
- [ ] document startup checks and closeout enforcement as standard session control rules

### 6) Implementation slice
- [x] add `preflight` capabilities subcommand
- [x] add `closeout` capabilities subcommand
- [x] add focused tests for gate failure/pass behavior and proof-surface requirements
- [ ] add matrix write-back or ledger reconciliation as the next low-risk implementation slice

### 7) Verification + commit readiness
- [x] run focused pytest for capability gate slice
- [ ] run broader verification once the next truth/doc slice lands
- [ ] update any remaining docs that still overclaim without reality-class wording
- [ ] leave a clean commit-ready report covering proof, gaps, and next slice

## Next slice recommendation

Best next grounded slice:
1. add a low-risk write-back path that records observed proof into a capability ledger without silently promoting truth
2. require human- or verifier-backed promotion from observed artifact -> proven-live capability state
3. wire that ledger into `shay intelligence truth` so capability and intelligence truth stop drifting apart

## Resume sentence

Resume by building the smallest safe capability-truth write-back path, then run it against one real task class so the matrix learns from proof instead of staying purely curated.
