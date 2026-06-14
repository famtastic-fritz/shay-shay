# Hermes Reference Inventory

Date: 2026-06-13
Lane: Hermes-removal sandbox
Purpose: classify every current sandbox-repo Hermes reference so current Shay identity can be separated from legacy compatibility, historical provenance, and stale residue.

Latest evidence anchor: `a644a0a docs: validate Hermes sandbox lock-dir isolation` closes the lock-dir override question only; it does not prove broad runtime independence.

Historical naming note: HyperSwarm is the canonical name. Any `HyperWAM` or `hyperwam` strings below are historical filename residue or quoted source text only.

## Summary
- Files with Hermes-family hits in the sandbox repo: 37
- Unclassified files after this pass: 0
- Active code-path Hermes references remain in a small compatibility cluster only.
- Most new Hermes mentions introduced by this mission live in control/docs artifacts where Hermes is the subject, not the product identity.

## Classification Vocabulary
- replace_with_shay_now
- compatibility_shim_keep_deprecate
- historical_reference_keep_labeled
- model_name_false_positive_keep
- external_contract_remove_last
- stale_superseded
- current_control_keep
- unknown_high_risk

## Replace With Shay Now
- No new active code-path string replacements were justified beyond comment/docstring clarification. The surviving active-code Hermes strings are all deliberate compatibility surfaces.

## Compatibility Shim / Keep-Deprecate Cluster
- `shay_cli/web_server.py` — Active Shay dashboard surface with legacy bearer/session-token compatibility for hermes-workspace.
  - sample refs: line 81:     Precedence: SHAY_DASHBOARD_TOKEN > HERMES_DASHBOARD_TOKEN. Empty values; line 82:     are treated as unset, preserving the legacy hermes-workspace compatibility
- `shay_cli/mcp_config.py` — Shay MCP serialization keeps legacy hermes-workspace JSON/mask compatibility.
  - sample refs: line 34: # Matches the legacy hermes-workspace mask sentinel so that compatibility UI; line 824:     consumed by the legacy hermes-workspace ``normalizeMcpServer`` path.
- `shay_cli/conductor_missions.py` — Shay API surface backing legacy hermes-workspace conductor probes.
  - sample refs: line 4: hermes-workspace v2.3 gateway probes to decide its ``conductor`` capability flag
- `gateway/chat_stream_routes.py` — SSE route contract preserved for legacy Hermes Workspace client bundle.
  - sample refs: line 3: This is the gateway endpoint that the legacy Hermes Workspace bundle (v2.3+)
- `gateway/platforms/api_server.py` — API server mounts legacy workspace-compatible SSE route.
  - sample refs: line 3375:             # Enhanced-chat SSE endpoint for the legacy Hermes Workspace v2.3+
- `tests/shay_cli/test_mcp_api_routes.py` — Tests prove legacy workspace token/MCP compatibility remains intentional.
  - sample refs: line 2: to the legacy hermes-workspace v2.3 MCP UI compatibility contract.; line 12: - SPA root injects __HERMES__SESSION_TOKEN__ so the legacy workspace regex matches
- `tests/shay_cli/test_dashboard_bearer_auth.py` — Tests prove HERMES_DASHBOARD_TOKEN fallback remains a deliberate external contract.
  - sample refs: line 3: Covers the SHAY_DASHBOARD_TOKEN / HERMES_DASHBOARD_TOKEN env-var bearer; line 4: compatibility contract that lets legacy external clients (hermes-workspace
- `tests/shay_cli/test_conductor_missions.py` — Tests prove legacy workspace conductor probe support.
  - sample refs: line 3: This endpoint backs the legacy hermes-workspace v2.3 Conductor capability. The

## Stale / Superseded Candidates
- `docs/shay-workstream-control-map-2026-06-12.md` — Broad umbrella control map superseded by narrower packet/matrix/gap docs; keep labeled historical until pruned.
- `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md` — Plan doc superseded by a644a0a lock-dir validation result.
- `docs/hyperwam-effectiveness-assessment-2026-06-13.md` — One-off assessment under a historical filename typo (`hyperwam`); keep or merge lessons into canonical HyperSwarm orchestration docs.

## Inventory Table
| path | classification | why |
|---|---|---|
| `REBRAND-REPORT-2026-05-19.md` | `historical_reference_keep_labeled` | Migration record documenting Hermes-to-Shay rebrand history. |
| `SOUL.md` | `historical_reference_keep_labeled` | Hermes refers to upstream skeleton/provenance, not current product identity. |
| `archive/wip-2026-06-01/AGENT-OS-SDD.md` | `historical_reference_keep_labeled` | Archived design residue; not current runtime truth. |
| `docs/hermes-external-compatibility-plan-2026-06-13.md` | `current_control_keep` | Current compatibility planning doc for external Hermes surfaces. |
| `docs/hermes-live-cutover-proposal-2026-06-13.md` | `current_control_keep` | Current proposal-only live cutover packet. |
| `docs/hermes-reference-inventory-2026-06-13.md` | `current_control_keep` | Current canonical inventory report for Hermes references. |
| `docs/hermes-reference-inventory-2026-06-13.yaml` | `current_control_keep` | Current canonical structured inventory for Hermes references. |
| `docs/hermes-removal-brutal-qa-report-2026-06-13.md` | `current_control_keep` | Current brutal QA report for the Hermes-removal lane. |
| `docs/hermes-removal-capability-control-packet-2026-06-13.md` | `current_control_keep` | Current Hermes-removal control packet; Hermes references are lane/control subjects, not product branding residue. |
| `docs/hermes-removal-capability-matrix-2026-06-13.yaml` | `current_control_keep` | Current lane capability truth; Hermes references describe protected legacy surfaces/gaps. |
| `docs/hermes-removal-final-sandbox-report-2026-06-13.md` | `current_control_keep` | Current final sandbox report for the Hermes-removal lane. |
| `docs/hermes-removal-gap-log-2026-06-13.md` | `current_control_keep` | Current Hermes-removal gap ledger. |
| `docs/hermes-removal-mission-ledger-2026-06-13.md` | `current_control_keep` | Current mission ledger tracking protected Hermes surfaces and decisions. |
| `docs/hermes-removal-next-lockdir-validation-plan-2026-06-13.md` | `stale_superseded` | Plan doc superseded by a644a0a lock-dir validation result. |
| `docs/hermes-removal-preflight-checklist-2026-06-13.md` | `current_control_keep` | Current preflight gate that must keep explicit Hermes protected-surface references. |
| `docs/hermes-removal-promotion-plan-2026-06-13.md` | `current_control_keep` | Current promotion-plan packet for the Hermes-removal lane. |
| `docs/hyperwam-effectiveness-assessment-2026-06-13.md` | `stale_superseded` | One-off assessment under a historical filename typo (`hyperwam`); keep or merge lessons into canonical HyperSwarm orchestration docs. |
| `docs/plans/2026-05-19-media-studio-solutions-backlog.md` | `historical_reference_keep_labeled` | Unrelated plan residue mentioning Hermes historically. |
| `docs/shay-add-audit-prune-rule-2026-06-13.md` | `current_control_keep` | Current additive-control rule referencing Hermes-removal examples. |
| `docs/shay-adoption-backlog-2026-06-13.md` | `current_control_keep` | Current adoption backlog seeded from Hermes-removal gaps. |
| `docs/shay-capability-research-cron-design-2026-06-13.md` | `current_control_keep` | Current cron design uses Hermes lane as prototype. |
| `docs/shay-gap-lifecycle-policy-2026-06-13.md` | `current_control_keep` | Current lifecycle policy mentions Hermes gaps as examples. |
| `docs/shay-gap-log-schema-2026-06-13.yaml` | `current_control_keep` | Current gap log schema mentions Hermes-lane examples. |
| `docs/shay-gap-resolution-workflow-2026-06-13.md` | `current_control_keep` | Current resolution workflow mentions Hermes gaps as examples. |
| `docs/shay-global-capability-matrix-draft-2026-06-13.md` | `current_control_keep` | Current global capability draft built from the Hermes-removal lane. |
| `docs/shay-global-capability-matrix-draft-2026-06-13.yaml` | `current_control_keep` | Current structured capability draft built from the Hermes-removal lane. |
| `docs/shay-research-fetcher-role-2026-06-13.md` | `current_control_keep` | Current role design uses Hermes lane as prototype. |
| `docs/shay-workstream-control-map-2026-06-12.md` | `stale_superseded` | Broad umbrella control map superseded by narrower packet/matrix/gap docs; keep labeled historical until pruned. |
| `docs/upstream/hermes-v2026.5.16-delta-report.md` | `historical_reference_keep_labeled` | Upstream Hermes lineage/delta report; preserve as historical evidence. |
| `gateway/chat_stream_routes.py` | `compatibility_shim_keep_deprecate` | SSE route contract preserved for legacy Hermes Workspace client bundle. |
| `gateway/platforms/api_server.py` | `compatibility_shim_keep_deprecate` | API server mounts legacy workspace-compatible SSE route. |
| `shay_cli/conductor_missions.py` | `compatibility_shim_keep_deprecate` | Shay API surface backing legacy hermes-workspace conductor probes. |
| `shay_cli/mcp_config.py` | `compatibility_shim_keep_deprecate` | Shay MCP serialization keeps legacy hermes-workspace JSON/mask compatibility. |
| `shay_cli/web_server.py` | `compatibility_shim_keep_deprecate` | Active Shay dashboard surface with legacy bearer/session-token compatibility for hermes-workspace. |
| `tests/shay_cli/test_conductor_missions.py` | `compatibility_shim_keep_deprecate` | Tests prove legacy workspace conductor probe support. |
| `tests/shay_cli/test_dashboard_bearer_auth.py` | `compatibility_shim_keep_deprecate` | Tests prove HERMES_DASHBOARD_TOKEN fallback remains a deliberate external contract. |
| `tests/shay_cli/test_mcp_api_routes.py` | `compatibility_shim_keep_deprecate` | Tests prove legacy workspace token/MCP compatibility remains intentional. |
