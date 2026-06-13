# Shay telemetry redaction policy — 2026-06-13

Status: draft policy
Scope: process intelligence telemetry, ledgers, reviews, reports, and future watcher outputs
Authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`

## Policy statement

Telemetry is redaction-first by default. If material might contain secrets, private content, or sensitive runtime data, the system must summarize or hash it before persistence.

## Primary rule

Never store these in process telemetry by default:
- raw API keys
- bearer tokens
- passwords
- cookies
- OAuth codes
- private vault content
- full environment dumps
- full private session transcripts
- unfiltered command output that may contain secrets

## Allowed replacements

Use one or more of these instead:
- `[REDACTED:secret-type]`
- path only
- protected pointer
- content hash
- structured summary
- count/size metadata
- abstract risk statement

## Classification levels

### Level 0 — safe operational metadata
Examples:
- plan_id
- run_id
- timestamps
- branch name
- file paths inside repo
- outcome status

Handling:
- may be stored directly

### Level 1 — limited internal metadata
Examples:
- command summaries
- model/provider names
- non-sensitive validation results
- artifact summaries

Handling:
- may be stored with light summarization
- avoid unnecessary payload capture

### Level 2 — sensitive metadata
Examples:
- runtime logs that may echo config fragments
- shell output near credentialed commands
- audit findings involving possible secret exposure
- failure traces that may include environment references

Handling:
- summarize or hash before storage
- strip values
- store protected pointer only if deeper inspection is required

### Level 3 — prohibited raw payloads
Examples:
- actual credentials
- raw private content
- copied session transcript with secrets
- full env dump

Handling:
- do not persist in ledgers or reports
- stop, redact, and escalate if encountered unexpectedly

## Redaction workflow

1. classify the payload before writing telemetry
2. if level 2 or 3, prevent raw persistence
3. replace payload with summary/hash/pointer
4. record that redaction happened
5. if exposure was unexpected, create safety event and gap record

## Command capture rule

For shell and tool activity:
- store command intent summary by default
- store exact command text only when demonstrably non-sensitive
- strip inline tokens, passwords, and secret-looking arguments before any persistence

Examples:
- acceptable: `git branch/status inspection`
- acceptable: `repository doc inventory search`
- not acceptable: full command line containing auth headers or credentials

## Transcript capture rule

Do not store full private session transcripts in process ledgers.
Instead store:
- instruction summary
- instruction hash
- decision summary
- evidence pointers

## Audit-risk handling rule

This mission discovered a secret-exposure risk during audit.
That finding must be handled as follows:
- record only the abstract fact that a workflow surface could expose secret material
- do not retain the secret values
- do not retain the vulnerable payload shape if it increases replay risk
- open a gap for filter hardening or approval-gate tightening

Approved abstract phrasing example:
- `Audit identified secret-exposure risk in a workflow surface; values were not retained.`

## Evidence storage rule

If deeper evidence is required for a human reviewer:
- place it in a protected store outside the routine process ledger path
- reference it with a protected pointer or controlled-access evidence ID
- do not inline it into markdown reports or YAML ledgers

## Watcher and automation rule

No watcher or scanner may be enabled unless it proves:
- redaction happens before persistence
- logs are filtered for secret-like patterns
- retention is bounded
- review path exists for safety exceptions

## Validation checks

Before a ledger write is accepted, validate:
- no secret-like strings remain
- no prohibited raw payload classes are present
- redaction notes exist when summaries replace payloads
- safety event is emitted if unexpected sensitive material was detected

## Retention guidance

Retain:
- lineage metadata
- summaries
- decisions
- artifact paths
- validation outcomes
- lessons learned

Do not retain by default:
- raw runtime logs
- raw command output from sensitive contexts
- full transcripts
- secret-bearing payloads

## Operator responsibilities

Operators and future automation authors must:
- assume telemetry may become searchable later
- redact before convenience logging
- prefer structured summaries over pasted payloads
- treat audit-discovered secret risks as safety findings, not documentation opportunities

## Acceptance bar

The policy is satisfied only if all process intelligence docs, schemas, pilot examples, and future implementations:
- preserve lineage
- preserve explainability
- never preserve raw secrets
- document redactions explicitly when evidence is transformed
