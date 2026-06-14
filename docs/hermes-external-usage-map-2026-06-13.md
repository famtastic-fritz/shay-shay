# Hermes External Usage Map

Date: 2026-06-13
Lane: Hermes-removal sandbox
Scope: read-only inspection only; no live mutation; no wrapper edits; no restarts; no deletions

## Purpose

Map the most likely external Hermes dependencies before any live forwarding, deprecation, or removal move is considered.

## Executive Summary

The live `hermes` command is still an active external dependency.

What is concretely true:
- `~/.local/bin/hermes` exists and directly execs `/Users/famtasticfritz/.shay/hermes-agent/venv/bin/hermes`.
- `~/.local/bin/shay-desktop` still shells into `hermes desktop`, making the Hermes CLI a live dependency for the Shay desktop launcher.
- `~/.zshrc` still exports `HERMES_HOME=~/.shay`, which means at least one active shell session contract still uses Hermes naming for runtime-home selection.
- No launch agent or cron entry was found invoking the `hermes` wrapper directly in this pass.
- `~/.shay/hermes-agent` and `~/.hermes` both still exist and remain remove-last surfaces.

Net: Hermes is no longer the current product identity inside the sandbox repo, but it still survives as a real external compatibility contract on this machine.

## Inspected Surfaces

### 1. `~/.local/bin/hermes`
- classification: active external dependency; command wrapper; candidate for forwarding shim
- risk: high
- path: `/Users/famtasticfritz/.local/bin/hermes`
- evidence:
  - line 1: `#!/usr/bin/env bash`
  - line 4: `exec "/Users/famtasticfritz/.shay/hermes-agent/venv/bin/hermes" "$@"`
- interpretation:
  - The current wrapper does not forward to `shay`.
  - It jumps directly into the legacy Hermes-named runtime tree under `~/.shay/hermes-agent`.
  - Any future change to that backing tree can break external callers immediately.

### 2. `~/.local/bin/shay-desktop`
- classification: command wrapper; active external dependency; candidate for later cleanup
- risk: medium
- path: `/Users/famtasticfritz/.local/bin/shay-desktop`
- evidence:
  - line 2: comment states it launches Hermes desktop wired to Shay-Shay runtime home
  - line 7: `export HERMES_HOME="/Users/famtasticfritz/.shay"`
  - line 8: `exec hermes desktop "$@"`
- interpretation:
  - Even the Shay-named desktop launcher still depends on the Hermes command existing.
  - Removing `hermes` before a safe forward/deprecation layer exists would break this launcher.

### 3. Shell startup config

#### `~/.zshrc`
- classification: compatibility shim; active external dependency
- risk: medium
- path: `/Users/famtasticfritz/.zshrc`
- evidence:
  - line 29: `# Shay / Hermes`
  - line 30: `export HERMES_HOME=~/.shay`
  - line 31-34: shell sources `$HOME/.shay/.env`
- redaction note:
  - The same file contains secret-bearing env material later in the file. That content is intentionally not reproduced here.
- interpretation:
  - The live shell contract still uses `HERMES_HOME` to point Hermes-era consumers at Shay state.
  - This is not an alias/function, but it is an active compatibility surface.

#### Included shell files
- classification: safe to ignore for Hermes mapping in this pass
- inspected includes:
  - Google Cloud SDK path/completion includes referenced from `.zshrc`
  - `$HOME/.shay/.env` include referenced from `.zshrc`
- interpretation:
  - No additional Hermes wrapper call was inspected from the Google includes.
  - `~/.shay/.env` was not expanded in this mapping pass because it is a secret-bearing boundary.

### 4. Launch agents
- classification: mostly Shay-native; safe to ignore for direct Hermes-wrapper usage
- path root: `/Users/famtasticfritz/Library/LaunchAgents`
- findings:
  - `ai.shay.gateway.plist` is Shay-native service identity and calls `shay_cli.main gateway run` directly.
  - No inspected launch agent invoked `~/.local/bin/hermes`.
  - No inspected launch agent used `hermes desktop`.
- redaction note:
  - Some launch agents contain secret-bearing environment values. Those were not copied into this report.
- interpretation:
  - Launchd is not the current reason the Hermes wrapper must stay alive.
  - Service naming already being Shay-native lowers cutover risk on that surface.

### 5. Cron
- classification: safe to ignore in this pass
- command: `crontab -l`
- result: no Hermes or Shay wrapper invocation found in the returned listing
- interpretation:
  - No cron-based Hermes dependency was evidenced in this pass.

### 6. `~/.shay/hermes-agent`
- classification: active external dependency; candidate for forwarding-shim support; candidate for later removal
- risk: high
- path: `/Users/famtasticfritz/.shay/hermes-agent`
- evidence:
  - wrapper target from `~/.local/bin/hermes` points here directly
  - top-level structure still contains an agent checkout and `venv/`
- interpretation:
  - This is not just historical residue. It is the current backing target of the live `hermes` wrapper.
  - Deleting or repointing it without first changing the wrapper strategy is unsafe.

### 7. `~/.hermes`
- classification: unknown/high-risk; active external dependency; candidate for later removal
- risk: high
- path: `/Users/famtasticfritz/.hermes`
- evidence:
  - top-level entries include `.env`, `config.yaml`, `state.db`, `sessions/`, `skills/`, `logs/`, `gateway_state.json`, and nested `hermes-agent/`
- interpretation:
  - This path still looks like a real legacy state home, not empty residue.
  - Because it contains live-looking state artifacts, this remains a remove-last surface.
  - This mapping pass did not inspect secrets or internal data content.

## Project / Repo / Runbook References

### Active or operationally relevant
1. `_docs/SHAY-DESKTOP-WIRE-BRAND-PHASE1-DISCOVERY.md`
   - classification: docs/runbook reference; active external dependency signal
   - evidence: documents `~/.hermes` fallback behavior and `HERMES_HOME` reliance in the desktop path layer
2. `_docs/SHAY-DESKTOP-WIRE-BRAND-PHASE1-STATUS.md`
   - classification: docs/runbook reference; active external dependency signal
   - evidence: records that `getHermesRoot()` still defaults to `~/.hermes`
3. sandbox docs under `docs/hermes-*2026-06-13*`
   - classification: docs/runbook reference
   - interpretation: these are current control artifacts, not external callers

### Historical / reference-only / safe to ignore for live-wrapper decisions
1. `_refs/hermes-webui-v0.51/**`
   - classification: historical reference
   - interpretation: extensive Hermes references exist, but this tree is a reference copy and not evidence that the local live wrapper is currently called from there
2. `tools/graphify/docs/translations/**`
   - classification: docs/runbook reference; model-name/platform-name false positive for this task
   - interpretation: generic platform support docs, not local runtime callers
3. `repos/OBLITERATUS/README.md`
   - classification: historical reference / model-name false positive
4. `CHANGELOG.md` and older narrative docs
   - classification: historical reference unless paired with a current executable surface

## Planning-Doc Audit (Add = Audit + Prune)

The new findings sharpen the status of the earlier Hermes planning docs:

- `docs/hermes-external-compatibility-plan-2026-06-13.md`
  - classification: still relevant, but now partially superseded by this evidence-backed usage map
- `docs/hermes-live-cutover-proposal-2026-06-13.md`
  - classification: still relevant, but still proposal-only and too high-level without this machine-level usage map
- `docs/hermes-removal-promotion-plan-2026-06-13.md`
  - classification: still relevant, but PR guidance must now acknowledge ancestry drift from `origin/main`
- global awareness drafts (`docs/shay-*2026-06-13*`)
  - classification: draft/control only; do not promote yet

No docs were deleted in this wave.

## Reference Classification Table

| surface | classification | risk | action posture |
|---|---|---:|---|
| `~/.local/bin/hermes` | active external dependency; command wrapper; candidate for forwarding shim | high | preserve until approved forwarder exists |
| `~/.local/bin/shay-desktop` | command wrapper; active dependency on `hermes` | medium | preserve; later retarget after wrapper policy |
| `~/.zshrc` `HERMES_HOME=~/.shay` | compatibility shim | medium | preserve until rename strategy is approved |
| launch agents | safe to ignore for direct Hermes-wrapper dependency | low | no action from this pass |
| crontab | safe to ignore in this pass | low | no action |
| `~/.shay/hermes-agent` | active external dependency; candidate for later removal | high | remove last |
| `~/.hermes` | unknown/high-risk; candidate for later removal | high | remove last; no guessing |
| `_refs/hermes-webui-v0.51/**` | historical reference | low | ignore for live cutover unless separately activated |
| desktop wire-brand docs | docs/runbook reference with active dependency signal | medium | keep as evidence |

## Bottom Line

The Hermes wrapper is still load-bearing.

Not because Hermes is still the product.
Because live external surfaces still route through Hermes-named contracts:
- command entrypoint
- desktop launcher dependency
- shell runtime-home compatibility variable
- legacy runtime/state trees

That means the safe next move is forward-and-deprecate planning, not removal.