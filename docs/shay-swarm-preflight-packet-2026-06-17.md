# Shay swarm preflight packet

Date: 2026-06-17
Status: active preflight packet
Purpose: define the autonomous-safe lane map for Shay truth reconstruction work before any real fan-out or closeout claim.

## Goal
Make Shay's truth system autonomous-safe so truth reconstruction, doctrine repair, and verification can run to completion without narrative drift or self-certifying swarm claims.

## Launch rule
This packet is preflight only until every lane below has:
- a bounded mission
- minimal context
- artifact destination
- proof target
- reviewer path

No lane is considered complete from its own summary.
Captain/parent verification closes the run.

## Dependency order
1. source-of-truth doctrine lane
2. master-checklist lane
3. truth-reconstruction lanes
4. research/drift lanes only for unresolved gaps
5. captain synthesis lane
6. parent verification lane

## Routing policy
- cheap/default lane: doc reads, artifact classification, inventory, archaeology
- mid lane: synthesis, checklist normalization, truth-surface mapping
- premium lane: adversarial review, ambiguity collapse, promotion decisions

## Lane packets

### lane-01: source-of-truth doctrine
- mission: lock the control rules for reality classes, source priority, promotion gates, preflight checks, and closeout enforcement
- inputs: existing rubric, current checklist, learning-loop verification run doc
- must ignore: speculative future implementation beyond control doctrine
- output: source-of-truth rules doc
- artifact: `docs/shay-source-of-truth-rules-2026-06-17.md`
- proof target: file written, reopened, and reflected in checklist
- reviewer: captain

### lane-02: master checklist normalization
- mission: turn the checklist into the canonical resumable control artifact with explicit done conditions and linkouts to doctrine/proof surfaces
- inputs: current checklist, doctrine doc, verification doc
- must ignore: code implementation expansion not needed for control readiness
- output: updated master checklist
- artifact: `docs/shay-master-checklist-2026-06-15.md`
- proof target: reopened checklist shows grounded statuses and next gates
- reviewer: captain

### lane-03: truth surface reconstruction
- mission: classify the live Shay surfaces by reality class, upstream source, update gate, and proof rule
- inputs: capabilities cmd, intelligence cmd, process_intelligence, curator, capability matrix, shared docs
- must ignore: any claim that cannot be tied to a direct file or runtime surface
- output: durable research/reconstruction artifact
- artifact: `~/famtastic/obsidian/Shay-Memory/research/2026-06-17-shay-truth-reconstruction.md`
- proof target: artifact written and reopened; classifications grounded in file reads
- reviewer: captain

### lane-04: drift archaeology and adversarial review
- mission: identify where narrative drift is most likely to recur and pressure-test the doctrine against self-report failure modes
- inputs: checklist, verification doc, truth reconstruction artifact, sibling control-plane lesson
- must ignore: implementation rabbit holes not required for this decision
- output: additions folded back into the reconstruction artifact/checklist
- artifact: same reconstruction artifact plus checklist deltas
- proof target: explicit drift patterns and countermeasures captured durably
- reviewer: premium/adversarial pass or captain if kept single-lane

### lane-05: captain synthesis
- mission: merge doctrine, checklist, reconstruction, and drift findings into one truthful closeout state
- inputs: all prior lane artifacts
- output: updated verification run doc and checklist state
- artifacts:
  - `docs/learning-loop-verification-run-2026-06-15.md`
  - `docs/shay-master-checklist-2026-06-15.md`
- proof target: reopened docs reflect actual finished/pending states
- reviewer: parent verification lane

### lane-06: parent verification
- mission: verify all closure claims from the actual filesystem, branch state, and validation commands
- inputs: changed docs, git state, exact validation commands
- output: final proof-ready closeout state
- artifacts: verified docs + git status + validation output
- proof target: parent can point to exact files/commands for every material claim
- reviewer: parent only

## Safety boundaries
- no live runtime edits
- no persona/root-truth edits
- no uncontrolled real HyperSwarm launch
- no broad implementation expansion unless doctrine requires it
- no self-certifying child closure

## Completion test
The packet becomes autonomous-ready only when:
- doctrine is explicit
- checklist is canonical
- truth surfaces are classified
- unresolved gaps are bounded
- final verification is parent-level
