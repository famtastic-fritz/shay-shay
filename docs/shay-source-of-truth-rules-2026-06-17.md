# Shay source-of-truth rules

Date: 2026-06-17
Status: active control rule
Purpose: define what counts as truth, what can be promoted, what must be verified by the parent lane, and what gates must pass before Shay claims completion.

## Source priority order

When sources conflict, resolve them in this order:
1. Fritz's direct instruction right now
2. Live system reality actually observed now
3. Current runtime/CLI probe output
4. Current working-tree artifact contents
5. Committed-branch history/state
6. Shared truth surfaces intentionally updated from proof
7. Older docs, summaries, or seeded structures

If a lower layer disagrees with a higher layer, the lower layer is historical context, not current truth.

## Reality classes

Use one of these labels for every truth-bearing surface:
- proven_live: observed in the live runtime or validated by a direct parent-level check
- implemented_unverified: present in code/docs/config but not yet verified in the live path being claimed
- observed_artifact: a durable artifact exists and was read, but no promotion decision has been made yet
- partial: some portion works or is present, but the whole claim is not true yet
- seeded: declared, planned, or curated structure that may be useful but is not proof
- stale: once useful, now superseded by newer reality or explicitly called stale
- deprecated: intentionally retained only for historical/reference use
- unknown: not yet checked

## Truth surfaces

Base truth surfaces:
1. working tree
   - Answers: is the artifact present in the checkout right now?
   - Proof: file read, git status, local file existence
2. committed branch
   - Answers: is it actually committed on the current branch?
   - Proof: git history/status
3. live runtime
   - Answers: is the running Shay system actually using it now?
   - Proof: direct runtime probe, exact command output, observed live state

Operational gate surfaces:
4. preflight gate
   - Answers: should this task be treated as execution-ready before work starts?
   - Proof: matched capabilities, blockers, prerequisites, warnings, required proof surfaces
5. closeout gate
   - Answers: what must be captured before the task can be treated as settled?
   - Proof: required proof surfaces, required write-backs, required closeout actions

Parent validation surface:
6. parent verification
   - Answers: did the claimed outcome actually happen in the repo/runtime/tracker truth?
   - Proof: direct parent reads, audit commands, tests, regenerated artifacts, branch-state checks

## Evidence vs proof

Use this language precisely:
- self-report only: not proof
- artifact exists but was not reopened: weak evidence
- artifact reopened and matches the claim: evidence
- artifact plus validation plus parent verification: proof

Child/delegate/subagent summaries are never final proof by themselves.
They can generate leads, draft artifacts, or narrow the search space.
Final closure requires parent verification against the actual truth surface being claimed.

## Promotion rules

Truth may be promoted only under these gates:
1. seeded -> observed_artifact
   - requires a durable artifact created and reopened by the parent lane
2. observed_artifact -> implemented_unverified
   - requires the artifact to map to a real code/doc/config/runtime surface that now exists
3. implemented_unverified -> partial or proven_live
   - requires the exact validation path for the claim being made
   - failure-only evidence promotes to `partial` with a repair-first posture
   - mixed success/failure evidence promotes only to `partial` until the failures are explained or cleared
   - repeated verifier-backed success across multiple runs can mark the capability as `proven_live`-eligible, but curated status still remains review-gated
   - single observed success without repeated verifier-backed proof stays `implemented_unverified`
4. partial -> proven_live
   - requires the missing gaps to be closed and revalidated
5. any class -> stale/deprecated
   - requires explicit supersession or removal from current active use

No automatic promotion from seeded to proven_live.
No promotion from child summary alone.
No promotion from doc wording alone.
No curated status flip from ledger evidence alone; automatic evaluation may recommend promotion, but the final truth write-back is still intentionally review-gated.

## Startup checks

Before non-trivial work:
- verify repo/worktree/branch truth
- verify whether the target is live-runtime work, branch work, or docs/control work
- identify the canonical artifact for the current mission
- classify the target surfaces by reality class
- identify proof targets before changing files
- confirm whether the run is planning-only, read-only, or real execution

## Preflight checks

Before launch or fan-out:
- each task must have a bounded objective
- each lane must have a minimal context packet
- each lane must have an output contract
- each lane must have artifact destinations
- each lane must have a stop rule and reviewer path
- each lane must know whether it is allowed to mutate anything
- no lane may self-certify final completion

## Closeout enforcement

Before claiming completion:
- reopen all changed control artifacts
- verify required proof surfaces directly
- rerun the exact relevant validation commands where applicable
- update truth surfaces to reflect reality, not aspiration
- classify unresolved gaps honestly
- state branch truth precisely: modified, committed local, pushed, merged
- do not collapse working-tree truth, branch truth, and runtime truth into one blob

## Standard blocker classes

Block only for real blockers:
- no trustworthy current canonical artifact exists
- branch/worktree truth is ambiguous
- proof target cannot be validated from the available parent-level surfaces
- required authority belongs to Fritz
- live/runtime claim cannot be checked safely

## Mandatory language

Say:
- present in the working tree
- committed on the branch
- observed in the live runtime
- evidence only
- parent-verified proof

Do not say:
- done
- live
- implemented
- available
- running
unless the exact truth surface for that claim was verified.
