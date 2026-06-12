# Private memory retrieval design — 2026-06-12

Status: planning only
Scope: retrieval policy for `~/.shay/private/`

## Guardrails honored

- No runtime code changed
- No private-memory tool implemented
- No changes to `SOUL.md`, `PERSONA.md`, `MEMORY.md`, or `USER.md`
- No indexing of `~/.shay/private/`
- No copying or moving private notes into Obsidian
- No auto-loading of private notes into prompt context

## Files inspected

Source-of-truth docs:
- `docs/shay-memory-hierarchy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-memory-compaction-policy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-db-status.md`

Private-vault files:
- `~/.shay/private/README.md`
- `~/.shay/private/observations/why-this-vault-exists.md`
- `~/.shay/private/strategy/thinking-log-capture.md`

## What the existing policy already says

The current canonical policy is clear on the big rule:
- private memory is private-by-default
- it is not prompt memory
- it is not shared knowledge
- any retrieval path must be explicit and opt-in
- private content must not silently leak into shared retrieval surfaces

The private vault README adds an important operating reality:
- this is "casual privacy," not encryption
- other agents may have filesystem access, but should not routinely scan or index this path
- the origin purpose is preserving thinking logs, private observations, strategy, and sensitive reflection without casual exposure

## Recommendation

Recommended mode: opt-in retrieval only

Why this wins:
1. It matches the current canonical policy language exactly.
2. It preserves privacy-by-default while still allowing Fritz to intentionally consult the vault.
3. It avoids the two biggest failure modes:
   - accidental auto-injection into normal work
   - silent widening into a shared knowledge substrate
4. It leaves room for a future task-gated helper without making task gating the default policy.

## Alternatives considered

### Fully manual
Pros:
- safest in absolute privacy terms
- no runtime ambiguity

Cons:
- makes the vault practically inert
- weak fit for Fritz's stated desire to preserve and sometimes consult Shay's private thinking

Verdict:
- acceptable fallback if retrieval proves too risky, but too restrictive as the primary design

### Opt-in retrieval only
Pros:
- best match to the current policy and user intent
- simple boundary: no access unless Fritz explicitly asks
- minimizes accidental leakage

Cons:
- requires clear permission rules and audit logging

Verdict:
- recommended default

### Task-gated retrieval
Pros:
- could reduce friction when a task obviously calls for private recall
- could support structured access later

Cons:
- easy to abuse or over-broaden
- task classification can drift into implicit permission
- unsafe as a default because it weakens the bright-line privacy rule

Verdict:
- possible future implementation shape, not the default policy

### Excluded entirely from runtime
Pros:
- strongest boundary

Cons:
- contradicts the idea of a usable private vault for Fritz and Shay
- blocks intentional retrieval even when Fritz directly requests it

Verdict:
- too rigid for the intended purpose

## Safest default

Safest default: deny by default unless Fritz gives explicit permission in the current session.

Operational meaning:
- no background reads
- no indexing
- no semantic search over the private path by default
- no automatic consultation because a task "seems related"
- no carrying forward prior permission into later sessions unless Fritz explicitly renews it

## Exact access rules

1. Private memory must never be part of default prompt injection.
2. Private memory must never be indexed by shared or ambient retrieval systems.
3. Private memory may be consulted only after explicit permission from Fritz in the current session.
4. Permission must be scoped:
   - specific file
   - specific folder
   - specific topic/query
   - or one clearly bounded retrieval action
5. If the request is broad but explicit, narrow it before retrieval when possible.
   - Example: prefer `thoughts/May-29` over `read the whole private vault`.
6. Retrieval results must be treated as private-session material, not automatically promotable facts.
7. Nothing from private retrieval may be copied into:
   - `MEMORY.md`
   - `USER.md`
   - shared vault / Obsidian
   - repo docs
   - skills
   unless Fritz explicitly asks for that promotion as a separate action.
8. Private retrieval should return only the minimum material needed for the asked task.
9. If the request can be answered from non-private sources first, prefer those first unless Fritz specifically asks for the private vault.
10. Permission expires at the end of the current session/task unless Fritz explicitly says otherwise.

## Explicit permission standard

Explicit permission is the bright-line rule for any access to `~/.shay/private/`.
If permission is ambiguous, implied, stale, inherited, or inferred from task relevance, private memory must not be accessed.

### Valid permission examples

The following count as valid explicit permission because they directly name private notes, private memory, the private vault, or `~/.shay/private/`:
- "Read my private notes about X."
- "Search `~/.shay/private/strategy` for X."
- "Use my private vault for this task."
- "Look in private memory for context on X."
- "Check the private vault for this."
- "Read `~/.shay/private/thoughts/...`"
- "Look in our private notes about May 29."
- "Search the private vault for thinking-log notes on X."
- "Use private memory for this question."
- "You can consult the private vault in this session."

### Invalid permission examples

The following do not count as explicit permission:
- vague references like "you know what I mean"
- normal memory recall requests such as "remember what we said before"
- generic note requests such as "search your notes"
- project research requests that do not explicitly mention private memory
- background review tasks
- "use whatever context you have"
- "figure it out"
- subagent tasks unless private access is explicitly included in the delegated task
- a task that merely seems emotionally relevant
- old permission from a previous session

### Scope rules

1. Permission applies only to the current task and current session unless Fritz explicitly renews or restates it.
2. Permission must name private notes, private memory, private vault, or `~/.shay/private/`.
3. Access must be limited to the smallest folder, file, or query scope needed for the task.
4. If a request is explicit but broad, narrow it before retrieval when possible.
   - Example: prefer `~/.shay/private/strategy/` or one named file over the whole vault.
5. Broad access requires stronger wording from Fritz.
   - Example: "Use my private vault for this task" is explicit, but `read the whole private vault` should still be narrowed unless Fritz clearly insists on broad review.
6. Permission does not automatically transfer to subagents, background jobs, cron jobs, or later follow-up tasks.

### Required disclosure

1. Shay must say when private memory was consulted.
2. Shay must state the scope used.
3. Shay must state the permission basis in plain language when relevant.
4. Shay must not silently blend private notes into normal answers as if they came from default memory or shared context.
5. If private retrieval materially informed the answer, the response should make that boundary visible.

### Deny-by-default rule

If permission is ambiguous, do not access private memory.
Ask for clearer authorization or proceed without private memory.

## Logging and audit requirements

Any future retrieval mechanism should produce a lightweight audit trail outside shared prompt memory.

Minimum audit fields:
- timestamp
- session identifier if available
- actor/surface (`cli`, `telegram`, etc.)
- requester (`Fritz` / current user)
- permission text that authorized access
- scope accessed (file, folder, or query)
- tool or mechanism used
- whether content was read, searched, or summarized
- whether any promotion/export was requested
- result status (`granted`, `denied`, `aborted`, `error`)

Audit design rules:
1. Audit logs must not dump full private content by default.
2. Logs should record metadata and scope, not the sensitive text itself.
3. If snippets are ever logged for debugging, that must be an additional opt-in layer, not the default.
4. Audit logs must not be written into shared vault surfaces.
5. Audit review should make it possible to answer: who accessed private memory, when, why, and how broadly.

Preferred audit home if implemented later:
- `~/.shay/private/audit/` or another private-only local path

## What must never happen

1. No auto-loading of private notes into normal prompt context.
2. No background indexing of `~/.shay/private/`.
3. No silent semantic search over private files.
4. No automatic promotion from private memory into shared vault, docs, skills, `MEMORY.md`, or `USER.md`.
5. No delegation of private-memory retrieval to subagents by default.
6. No quoting private notes into public/shared outputs unless Fritz explicitly asks.
7. No treating private notes as canonical truth over live runtime facts, `SOUL.md`, `PERSONA.md`, or approved system docs.
8. No persistent standing permission that silently survives forever.
9. No access based solely on model inference that "this would probably help."
10. No conflation of private reasoning logs with stable prompt memory.

## Proposed future implementation shape

If Phase 4B is approved later, the safest shape is a tiny explicit-access surface, not a broad search system.

Recommended shape:
1. A narrowly scoped tool or command for private retrieval only.
2. Default mode: off unless Fritz invokes it directly.
3. Support these actions only:
   - read one file
   - list a folder
   - search filenames
   - optionally search contents within a user-specified subfolder
4. Require an explicit `scope` argument.
5. Emit an audit record on every call.
6. Return a visible boundary marker in the response such as:
   - "Private vault consulted: yes"
   - scope consulted
   - permission basis
7. No semantic indexing, no vector DB, no background ingestion.
8. No automatic use by subagents unless Fritz explicitly authorizes delegated access for that task.

## Risk notes

1. The biggest risk is scope creep: a narrow retrieval feature quietly becoming ambient memory.
2. Task-gated access sounds convenient but weakens the explicit-permission line.
3. Audit logs can themselves become a privacy leak if they store content instead of metadata.
4. Because the vault is not encrypted, policy must not overclaim its privacy level.
5. If later implementations allow search across all private content at once, accidental overexposure becomes much more likely.

## Decision

Adopt: opt-in retrieval only
Default stance: deny unless Fritz explicitly authorizes private retrieval in the current session

## Exact Phase 4B prompt

Implement Phase 4B only.

Goal:
Create a design-level spec for a minimal private-memory access surface for `~/.shay/private/` that follows the approved retrieval policy.

Rules:
- Do not implement runtime code yet.
- Do not index `~/.shay/private/`.
- Do not copy anything into Obsidian.
- Do not modify `SOUL.md`, `PERSONA.md`, `MEMORY.md`, or `USER.md`.
- Do not auto-load private notes into prompt context.
- Keep the design limited to explicit, opt-in retrieval only.

Tasks:
1. Propose the exact command/tool interface for private retrieval.
2. Define allowed actions, required arguments, and rejection behavior.
3. Define audit-log schema and storage location.
4. Define how the UI/response must visibly mark private retrieval.
5. Define safeguards for subagents, cron jobs, and background tasks.
6. Identify candidate runtime files that would eventually need changes, but do not change them.
7. Produce a planning/spec document only.

Afterward show:
1. proposed interface
2. candidate files
3. audit schema
4. safeguards
5. risks
6. implementation order

Do not implement Phase 4B.
