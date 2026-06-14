# Shay Pattern Scanner Autonomy Policy

Date: 2026-06-13
Status: policy / design only
Authority:
- `docs/shay-pattern-scanner-design-2026-06-13.md`
- `docs/shay-process-intelligence-watcher-design-2026-06-13.md`
- `docs/shay-telemetry-redaction-policy-2026-06-13.md`
- Fritz source architecture packet sections 17, 18, 22, and 23

## Purpose

The pattern scanner should not just notice patterns.
It must also know what it is allowed to do with them.
This policy defines those autonomy boundaries.

## Scanner outputs

The scanner may emit:
- pattern records
- repeated-gap recommendations
- backlog recommendations
- prune candidates
- disabled draft watcher/cron configs
- requests for human review

The scanner may not treat an observation as a permission slip.

## Autonomy zones

### Green zone — auto-allowed
The scanner may autonomously:
- update safe metadata
- open draft gap recommendations
- open draft backlog recommendations
- open draft prune candidates
- generate disabled draft watcher/cron configs
- classify repeated overclaim, repeated docs sprawl, repeated skill/tool mismatch, repeated provider-health unknowns, repeated approval bottlenecks

Required conditions:
- no live mutation
- no secret-bearing capture
- no paid checks
- outputs are reversible and reviewable

### Yellow zone — approval packet or bounded proof only
The scanner may prepare, but not execute:
- sandbox-local `.venv` enablement recommendations
- bounded sandbox runtime startup proofs
- synthetic config proofs beyond read-only status
- branch push / PR-open recommendations
- new skill adoption recommendations
- watcher activation recommendations
- provider health checks that might cost money or touch external services

Yellow-zone output must include:
- exact proposed action
- why approval is needed
- expected value
- risk
- stop/abort rules
- safe fallback

### Red zone — stop and ask Fritz
The scanner must stop and escalate before any of these:
- live deletion
- live wrapper edit
- live launchd edit
- live service restart
- force push
- merge to main
- secret/private data access
- live provider/model config change

### Forbidden
The scanner must never:
- capture raw secrets
- capture raw private-vault contents
- read/copy API keys, tokens, cookies, or secret env values
- store unredacted env dumps
- mutate private/session/state stores outside approved bounded flows
- treat missing evidence as healthy status

## Severity routing

| severity | default route |
|---|---|
| low | record pattern and propose a draft recommendation |
| medium | draft recommendation plus human-visible review note |
| high | open review packet and block any related unsafe follow-on automation |
| critical | immediate stop/escalation; no autonomous follow-on action |

## Review boundary

A pattern is not a fix.
Before implementation, the scanner output should route through one of:
- gap logger
- pruner
- promoter
- gatekeeper
- Fritz approval

## Dedupe and cooldown rule

The scanner must suppress repeated identical findings within a bounded window.
If the same pattern repeats without new evidence, update frequency and last-seen metadata instead of spamming new outputs.

## Privacy / redaction rule

Pattern evidence should prefer:
- IDs
- hashes
- paths
- redacted summaries
- category labels

Pattern evidence must avoid:
- raw secret values
- raw private notes
- raw session dumps when a structured pointer is enough

## Promotion path

Allowed progression:
- observe pattern
- record pattern
- review pattern
- classify autonomy zone
- either implement green-zone metadata update or create approval packet
- measure later whether the recommendation improved outcomes

This policy does not itself enable automation.
It defines what the scanner is and is not allowed to do when automation arrives.
