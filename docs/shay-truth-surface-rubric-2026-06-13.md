# Shay Truth-Surface Rubric

Date: 2026-06-13
Status: control rule
Purpose: keep working-tree truth, committed-branch truth, and live-runtime truth separated

## The three truth surfaces

| surface | question it answers | proof style | common failure |
|---|---|---|---|
| working tree | Is the artifact/code present in the current checkout right now? | direct file existence, git status, local reads | overstating this as committed branch truth |
| committed branch | Is the artifact/code actually committed on the current branch? | git status clean or file tracked in commit history | treating untracked or modified work as settled canon |
| live runtime | Is the running Shay system actually using it now? | read-only CLI/runtime probes, process state, deployed paths | assuming branch code equals live behavior |

## Mandatory language

Use these phrases precisely:
- `present in the working tree`
- `committed on the branch`
- `observed in the live runtime`

Avoid vague claims like:
- `on this branch` when the file is only untracked or modified
- `live` when only code exists
- `implemented` when only docs/schema exist
- `available` when only configured inventory exists

## Related truth splits from this run

1. Runtime vs branch
- `shay status` points at `/Users/famtasticfritz/famtastic/shay-shay`
- current docs/control work is in `/Users/famtasticfritz/famtastic/shay-shay-main-sync-20260613`

2. Configured vs selected vs healthy
- provider keys/config may exist
- selected runtime provider may be different
- end-to-end health may still be unproven

3. Inventory vs proof
- enabled MCP list is not per-server health proof
- skill hub search is not local installed-skill truth
- fallback chain presence is not fallback-chain success proof

## Rule

Whenever a canon doc makes a capability claim, it should be classifiable into one of the three surfaces above.
If it cannot, the wording is too vague and should be downgraded.

## Operational gate surfaces (added 2026-06-15)

Two execution-control surfaces now sit on top of the three base truth surfaces:

1. `preflight gate`
- question answered: "Given current capability truth, should this task be treated as ready or blocked before execution?"
- proof style: matched capability truth, blocking capability states, missing prerequisites, warnings/gaps
- current CLI: `shay capabilities preflight "<task>"`
- common failure: treating a doc claim as execution readiness when the gate still shows blocked or partial truth

2. `closeout gate`
- question answered: "What proof surfaces and closeout actions are required before this task can be treated as settled?"
- proof style: required proof surfaces + required closeout actions derived from matched capabilities
- current CLI: `shay capabilities closeout "<task>"`
- common failure: calling a task complete without durable proof capture or matrix/truth-surface updates

These do NOT replace working-tree / branch / runtime truth.
They operationalize them.
A task can exist in code and still fail preflight.
A task can succeed in practice and still fail closeout if proof was not captured.
