# Private memory access surface spec — 2026-06-12

Status: planning only
Scope: minimal explicit-access runtime surface for `~/.shay/private/`
Phase: 4B planning spec only

## Guardrails honored

- No runtime code changed
- No runtime code was modified
- No changes to `SOUL.md`, `PERSONA.md`, `MEMORY.md`, or `USER.md`
- No indexing of `~/.shay/private/`
- No copying private notes into Obsidian
- No auto-loading of private notes into prompt context
- No vector store for private memory
- No background ingestion
- Design is limited to explicit, opt-in retrieval only

## Source-of-truth docs used

- `docs/shay-memory-hierarchy.md`
- `docs/shay-private-memory-policy.md`
- `docs/private-memory-retrieval-design-2026-06-12.md`

## Design objective

Create the smallest possible runtime surface that lets Fritz intentionally consult `~/.shay/private/` without turning private memory into ambient memory.

This spec assumes the approved policy remains unchanged:
- private memory is private-by-default
- private memory is not prompt memory
- private memory is not shared knowledge
- access requires explicit permission in the current task/session
- access must be narrow, visible, auditable, and deny-by-default

## Decision summary

Recommended Phase 4C shape:
1. Add one dedicated tool for private retrieval.
2. Keep it out of the default/core toolset.
3. Make it deny by default unless explicit permission exists in the current task/session.
4. Support only narrow filesystem-style retrieval actions.
5. Emit an audit record on every attempt, including denials.
6. Force visible disclosure in the user-facing response whenever private memory was consulted.
7. Block cron/background/delegated/subagent use by default.

## Proposed interface

Preferred implementation surface: one built-in tool named `private_memory_access`.

Why one tool:
- keeps the surface small
- fits Shay's existing tool-calling model
- avoids adding a broad new command family too early
- makes allow/deny logic centralized

Phase 4C should not add semantic search, retrieval plugins, indexing, or prompt-builder hooks.

### Tool name

`private_memory_access`

### Tool schema

```json
{
  "name": "private_memory_access",
  "description": "Explicit, opt-in access to ~/.shay/private/ for narrow private retrieval only.",
  "parameters": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["read_file", "list_dir", "search_filenames", "search_content"]
      },
      "scope": {
        "type": "string",
        "description": "File or directory scope under ~/.shay/private/. Must stay inside the private root."
      },
      "query": {
        "type": "string",
        "description": "Required for search_filenames and search_content. Omit for read_file and list_dir."
      },
      "permission_basis": {
        "type": "string",
        "description": "Exact or near-exact user language from the current task/session that explicitly authorizes private access."
      },
      "limit": {
        "type": "integer",
        "description": "Optional result cap for list/search actions.",
        "minimum": 1,
        "maximum": 50,
        "default": 10
      },
      "offset": {
        "type": "integer",
        "description": "Optional pagination offset for list/search actions.",
        "minimum": 0,
        "default": 0
      },
      "line_start": {
        "type": "integer",
        "description": "Optional 1-based starting line for read_file.",
        "minimum": 1
      },
      "line_count": {
        "type": "integer",
        "description": "Optional max lines for read_file.",
        "minimum": 1,
        "maximum": 400,
        "default": 120
      }
    },
    "required": ["action", "scope", "permission_basis"],
    "additionalProperties": false
  }
}
```

### Response shape

The tool should return a structured result, not raw uncontrolled text.

```json
{
  "status": "granted | denied | error",
  "consulted_private_memory": true,
  "action": "read_file | list_dir | search_filenames | search_content",
  "scope": "~/.shay/private/...",
  "permission_basis": "quoted or normalized authorization text",
  "results": [],
  "summary": "brief private-session summary",
  "disclosure": {
    "private_memory_consulted": true,
    "scope": "~/.shay/private/...",
    "action": "...",
    "permission_basis": "..."
  }
}
```

On denial, `consulted_private_memory` must be `false` and `results` must be empty.

## Allowed actions

### 1. `read_file`
Purpose:
- read one file under `~/.shay/private/`

Required arguments:
- `action`
- `scope` pointing to one file
- `permission_basis`

Optional arguments:
- `line_start`
- `line_count`

Allowed output:
- bounded file content
- line-limited reads only

### 2. `list_dir`
Purpose:
- list one folder under `~/.shay/private/`

Required arguments:
- `action`
- `scope` pointing to one directory
- `permission_basis`

Optional arguments:
- `limit`
- `offset`

Allowed output:
- child filenames/directories only
- no recursive crawl by default

### 3. `search_filenames`
Purpose:
- search filenames within a scoped directory under `~/.shay/private/`

Required arguments:
- `action`
- `scope` pointing to a directory
- `query`
- `permission_basis`

Optional arguments:
- `limit`
- `offset`

Allowed output:
- matching filenames/paths only
- no file contents

### 4. `search_content`
Purpose:
- search file contents within a scoped directory under `~/.shay/private/`

Required arguments:
- `action`
- `scope` pointing to a directory or bounded file set
- `query`
- `permission_basis`

Optional arguments:
- `limit`
- `offset`

Allowed output:
- bounded matching snippets only
- no whole-vault search by default
- no semantic/vector retrieval

## Rejection behavior

The tool must reject access instead of trying to be helpful when any rule fails.

### Mandatory rejection cases

1. No explicit permission in the current task/session.
2. `permission_basis` does not clearly reference private notes, private memory, private vault, or `~/.shay/private/`.
3. Permission is stale, inherited, implied, or from a previous session.
4. `scope` escapes the private root or uses traversal patterns.
5. `scope` is broader than the permission reasonably supports.
6. The tool is called from a subagent, cron job, background review, or delegated task without explicit private authorization for that exact execution path.
7. `action=search_content` is requested against the entire vault root without stronger explicit wording.
8. Required arguments are missing.
9. The tool is asked to promote, export, rewrite, or copy private material anywhere else.
10. The tool is invoked as an ambient recall substitute for normal memory.

### Rejection response shape

```json
{
  "status": "denied",
  "consulted_private_memory": false,
  "action": "...",
  "scope": "requested scope",
  "permission_basis": "submitted basis",
  "reason": "clear policy reason",
  "results": []
}
```

### Example denial reasons

- `explicit_permission_required`
- `permission_not_private_specific`
- `permission_not_current_session`
- `scope_outside_private_root`
- `scope_too_broad`
- `delegated_access_not_authorized`
- `cron_access_not_allowed`
- `background_access_not_allowed`
- `missing_query`
- `promotion_not_allowed`

## Permission handling standard

Phase 4C should treat `permission_basis` as a claimed authorization string, not proof by itself.

The runtime should verify all of the following before allowing access:
1. the current task/session includes explicit private-memory permission
2. the permission language is private-specific
3. the requested scope is consistent with that permission
4. the current execution surface is allowed

Recommended model:
- the tool call includes `permission_basis`
- runtime validation checks that it matches a current-session private authorization record or current-turn explicit request context
- if validation fails, deny

This avoids trusting the model to invent permission after the fact.

## Visible disclosure standard

If private memory was actually consulted, the final user-facing answer must visibly disclose that fact.

Required disclosure block:

```text
Private memory consulted: yes
Action: <action>
Scope: <resolved scope>
Permission basis: <explicit authorization text or normalized summary>
```

Disclosure rules:
1. Must appear in the final answer whenever private memory was consulted.
2. Must appear even if the result was empty.
3. Must not be hidden only inside logs.
4. Must not be silently merged into a normal answer with no boundary marker.
5. If access was denied, the answer should say private memory was not consulted and why.

Recommended answer behavior:
- prepend or append the disclosure block in a consistent format
- then provide the actual answer
- do not imply the information came from default memory

## Audit-log schema

Every private-memory access attempt must create an audit record, including denials.

### Storage location

Preferred location:
- `~/.shay/private/audit/private-memory-access.jsonl`

Optional future refinement:
- daily roll files under `~/.shay/private/audit/YYYY-MM-DD.jsonl`

The audit location must remain inside the private root or another private-only local path.
It must not write into Obsidian, shared memory, or repo docs.

### Audit record schema

```json
{
  "timestamp": "ISO-8601",
  "request_id": "uuid-or-session-scoped-id",
  "session_id": "current session id if available",
  "platform": "cli | telegram | discord | ...",
  "actor_type": "primary_agent | subagent | cron | background_job",
  "actor_id": "agent/session identifier if available",
  "requester": "Fritz or current user identity label",
  "status": "granted | denied | aborted | error",
  "action": "read_file | list_dir | search_filenames | search_content",
  "scope_requested": "raw requested scope",
  "scope_resolved": "normalized in-root scope if granted",
  "query_present": true,
  "query_hash": "optional hash of query text",
  "permission_basis": "explicit user authorization text or normalized summary",
  "permission_source": "current_turn | current_session_flag | delegated_packet",
  "delegated": false,
  "parent_session_id": "if delegated",
  "tool_name": "private_memory_access",
  "result_count": 0,
  "promotion_requested": false,
  "denial_reason": null,
  "notes": "optional non-sensitive metadata"
}
```

### Audit rules

1. Do not log full private file contents by default.
2. Do not log full search snippets by default.
3. Log metadata, scope, and decision basis.
4. Record denials as well as grants.
5. Audit data is private-session infrastructure, not shared knowledge.
6. Query hashing is preferred over raw query storage when the query itself may be sensitive.

## Safeguards by execution surface

### Primary interactive session
Allowed:
- yes, if explicit permission exists in the current task/session
- only with narrow scope
- only through the dedicated tool

### Subagents
Default:
- denied

Allow only if all are true:
1. Fritz explicitly authorized private access for the delegated task
2. the delegation packet includes the exact permission basis
3. the packet includes an explicit private scope
4. the child is marked as allowed for private access
5. audit records preserve parent/child linkage

If any of the above is missing, deny.

### Delegated tasks
Default:
- denied

Rule:
- delegated work must not inherit private access implicitly from the parent conversation
- authorization must be included explicitly in the delegated task payload

### Cron jobs
Phase 4C default:
- denied entirely

Reason:
- cron runs without a live user present
- current-session explicit permission cannot be freshly established at execution time

Future reconsideration would require a separate policy, not this minimal v1 surface.

### Background reviews / watchers / autonomous scans
Default:
- denied entirely

Reason:
- they violate the bright-line rule against ambient scanning and background retrieval

### Prompt building / memory injection
Default:
- never allowed

Rule:
- private memory must not be added to prompt assembly, compaction, memory hydration, or shared retrieval pipelines

## Candidate runtime files for future Phase 4C

These are candidate implementation files only. This spec does not authorize changing them now.

### Likely new file
- `tools/private_memory_access.py`
  - new dedicated tool implementation
  - path normalization, action dispatch, bounded reads/searches, structured result payload, audit writes

### Likely touched existing files
- `toolsets.py`
  - add a dedicated private-memory toolset or keep the tool outside default/core sets
  - ensure it is not enabled by default

- `model_tools.py`
  - expose the new tool schema to the runtime
  - enforce any global registration/dispatch wiring required by the tool system

- `run_agent.py`
  - ensure final response assembly can include mandatory visible disclosure after private retrieval
  - carry task/session permission context if needed

- `agent/tool_guardrails.py`
  - centralize deny-by-default enforcement for disallowed surfaces such as cron, background reviews, and unauthorized delegation

- `gateway/session.py`
  - carry current-session metadata needed to validate explicit permission across gateway conversations

- `shay_constants.py`
  - define a canonical helper/path for the private audit location if the project prefers path helpers over inline strings

- `cli.py`
  - optional only if the CLI needs explicit rendering support for the disclosure block or admin-facing handling

- `shay_cli/commands.py`
  - optional only if a dedicated slash command or admin command is added later; not required for the minimal tool-first design

### Likely test files
- `tests/tools/test_private_memory_access.py`
- `tests/test_toolsets.py`
- `tests/test_model_tools.py`
- `tests/run_agent/test_private_memory_disclosure.py`
- `tests/gateway/test_session.py`
- `tests/agent/test_tool_guardrails.py`

## Risks

1. Scope creep: a narrow tool slowly becomes broad ambient retrieval.
2. Permission laundering: model-generated `permission_basis` strings that do not reflect real user authorization.
3. Delegation leakage: parent permission accidentally flowing into subagents or background jobs.
4. Audit leakage: storing too much sensitive text in logs.
5. Surface drift: CLI/gateway behavior diverging so one surface is stricter than another.
6. Root-scope abuse: content searches against all of `~/.shay/private/` becoming de facto indexing.
7. Disclosure failure: private notes influencing the answer without visible attribution.
8. Promotion creep: private material being copied into shared stores without a separate explicit step.

## Non-goals for Phase 4C

- no semantic search
- no embeddings
- no vector database
- no MCP exposure of `~/.shay/private/`
- no prompt-builder integration
- no memory auto-promotion
- no background indexing
- no cron-based retrieval
- no bulk export or sync to Obsidian

## Implementation order for future Phase 4C

1. Define the permission-validation contract.
   - Decide how current-session explicit permission is recorded and verified.
   - Do this before writing the tool so the tool does not trust model claims blindly.

2. Add canonical private audit path handling.
   - Introduce a single audit destination helper/path convention.

3. Implement the dedicated tool.
   - Add `read_file`, `list_dir`, `search_filenames`, and `search_content` only.
   - Enforce in-root path normalization and bounded output.

4. Add rejection plumbing and denial codes.
   - Ensure denials are structured, explicit, and audited.

5. Add visible disclosure plumbing.
   - Ensure final answers visibly disclose private consultation.

6. Add execution-surface guardrails.
   - Block cron, background reviews, and unauthorized delegation/subagents.

7. Add focused tests.
   - grant path
   - deny path
   - path traversal denial
   - broad-scope denial
   - disclosure presence
   - audit logging
   - subagent/cron/background denial

8. Update docs after implementation.
   - reflect actual runtime behavior, not intended behavior
   - update policy docs only if implementation required a clarified boundary

## Exact Phase 4C prompt

Implement Phase 4C only.

Goal:
Add a minimal runtime private-memory access surface for `~/.shay/private/` that follows the approved private-memory policy and explicit permission standard.

Source-of-truth docs:
- `docs/shay-memory-hierarchy.md`
- `docs/shay-private-memory-policy.md`
- `docs/private-memory-retrieval-design-2026-06-12.md`
- `docs/private-memory-access-surface-spec-2026-06-12.md`

Rules:
- Implement runtime code for the minimal access surface only.
- Do not modify `SOUL.md`, `PERSONA.md`, `MEMORY.md`, or `USER.md`.
- Do not index `~/.shay/private/`.
- Do not copy private notes into Obsidian.
- Do not auto-load private notes into prompt context.
- Do not create a vector store.
- Do not add background ingestion.
- Do not expose private memory through MCP or shared retrieval.
- Keep the surface limited to explicit, opt-in retrieval only.

Required implementation:
1. Add a dedicated built-in tool named `private_memory_access`.
2. Support only these actions:
   - `read_file`
   - `list_dir`
   - `search_filenames`
   - `search_content`
3. Enforce in-root scope under `~/.shay/private/` only.
4. Enforce deny-by-default behavior when explicit permission is missing, stale, ambiguous, delegated without authorization, or too broad.
5. Write an audit record for every attempt, including denials.
6. Ensure final answers visibly disclose when private memory was consulted.
7. Block cron jobs, background reviews, and unauthorized subagent/delegated use.
8. Add focused tests for grants, denials, traversal protection, disclosure, and audit logging.

Afterward show:
1. files changed
2. tests added/updated
3. permission validation behavior
4. disclosure behavior
5. audit path/schema used
6. known limitations

Do not implement anything beyond this minimal Phase 4C surface.
