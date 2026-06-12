# Shay-Shay canonical memory hierarchy

Status: canonical policy
Last updated: 2026-06-12
Scope: defines which memory layers are authoritative, how they are used at runtime, and which stores are legacy or manual-only.

## Purpose

This file is the canonical memory hierarchy for Shay-Shay.

If other docs describe memory behavior differently, this file wins unless live runtime code proves otherwise. Diagnostic reviews are useful, but this file defines the intended hierarchy and the canonical names for each layer.

## The hierarchy

### Layer 1 — Identity and operating voice
Source of truth:
- `~/.shay/SOUL.md`
- `~/.shay/PERSONA.md`

Role:
- Defines identity, operating philosophy, tone, voice, and behavioral framing.
- Loaded into the system prompt at session start.

Classification:
- Active
- Auto-injected
- Session-stable

Notes:
- These are not general notes. They are runtime identity files.
- They outrank downstream interpretation docs.

### Layer 2 — Bounded prompt memory
Source of truth:
- `~/.shay/memories/MEMORY.md`
- `~/.shay/memories/USER.md`

Role:
- Holds durable facts that should be available without retrieval.
- Injected into the system prompt through the built-in memory store.

Classification:
- Active
- Auto-injected
- Snapshot-based per session

Notes:
- This layer is intentionally bounded.
- It should contain compact, durable facts, not logs, progress reports, or bulky reference material.
- Mid-session writes persist to disk but are not guaranteed to become live prompt context until the next prompt rebuild/session load.

### Layer 3 — Project and repo context
Source of truth:
- repo and cwd context files such as `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `SHAY.md`, and similar prompt-context files discovered by the runtime

Role:
- Supplies project-local operating constraints and conventions.

Classification:
- Active
- Auto-injected
- Session-scoped context

Notes:
- This layer is about the current working environment, not personal memory.

### Layer 4 — Conversation recall
Source of truth:
- `~/.shay/state.db`

Role:
- Canonical store for session/message history and transcript search.
- Backing store for historical recall flows such as `session_search`.

Classification:
- Active
- Retrieval-based
- Canonical historical memory

Notes:
- This is the primary conversation recall store.
- JSON session files are not the canonical historical recall layer.

### Layer 5 — Shared knowledge vault
Source of truth:
- `~/famtastic/obsidian` accessed through enabled MCP services such as `basic-memory`, `vault-search`, and `obsidian`

Role:
- Shared structured knowledge, long-form notes, research, captures, and stream documentation.

Classification:
- Active
- Retrieval-based
- Shared knowledge substrate

Notes:
- This layer is available when tools call into it.
- It is not the same thing as prompt memory.

### Layer 6 — Private memory vault
Source of truth:
- `~/.shay/private/`

Role:
- Private notes, thinking logs, strategy, observations, and other off-prompt material.

Classification:
- Present
- Manual/private
- Not part of default shared retrieval

Notes:
- This layer is intentionally isolated from the shared vault search path.
- It is not canonical prompt memory.
- Any future retrieval path into this vault must be explicit and opt-in.

### Layer 7 — Legacy and auxiliary artifacts
Current stores:
- `~/.shay/sessions/*.json`
- `~/.shay/sessions/sessions.json`
- `~/.shay/shay.db` unless and until it is wired to a documented runtime role

Role:
- Legacy session artifacts, gateway bookkeeping, or currently unused surfaces.

Classification:
- Non-canonical
- Auxiliary or dormant

Notes:
- These files may still matter operationally for compatibility or bookkeeping.
- They do not outrank `state.db` as the source of truth for conversation recall.

## Authority order

When multiple memory surfaces appear to conflict, use this order:
1. Live runtime behavior
2. Identity files: `SOUL.md`, `PERSONA.md`
3. This hierarchy doc
4. Bounded prompt memory: `MEMORY.md`, `USER.md`
5. Canonical conversation recall: `state.db`
6. Shared vault knowledge through MCP
7. Private vault contents when explicitly consulted
8. Legacy session JSON artifacts and undocumented side stores

## Practical rule of thumb

If the question is "what shapes Shay automatically in a normal session," the answer is:
- identity files
- bounded prompt memory
- active project context files

If the question is "where should Shay look for historical or structured knowledge," the answer is:
- `state.db` for conversations
- Obsidian/MCP for structured shared knowledge
- `~/.shay/private/` only when explicitly and intentionally consulted

## Related policy docs

- `docs/shay-memory-compaction-policy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-db-status.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
