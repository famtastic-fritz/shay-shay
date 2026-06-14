# Shay Global Capability Matrix Draft

Date: 2026-06-13
Status: draft built from the Hermes-removal lane prototype

## Purpose

Turn the Hermes-removal lane into a reusable global capability-awareness system so Shay can distinguish documented capability, sandbox-safe capability, live-read-only capability, approval-gated capability, and forbidden actions.

## Surface Summary

| surface | current status | lane | fallback | key gaps |
|---|---|---|---|---|
| sandbox repo inspection | healthy | sandbox | direct file/git inspection | none |
| sandbox execution runtime | warning | sandbox | explicit shared interpreter path only as labeled coupling | sandbox-no-local-venv, sandbox-tests-share-live-venv |
| sandbox startup isolation | warning | sandbox-runtime | prior narrow proofs + approval-gated startup tests | sandbox-home-not-yet-startup-validated |
| gateway lock-dir override | healthy_for_narrow_scope | sandbox-runtime | explicit `SHAY_GATEWAY_LOCK_DIR` | gateway-lock-dir-default-outside-shay-home |
| live gateway inspection | healthy | live-read-only | passive status/plist inspection | none |
| live mutation surfaces | forbidden | live | proposal-only | hermes-external-client-usage-unknown |
| external compatibility surfaces | warning | external-read-only | preserve and forward later | hermes-external-client-usage-unknown, legacy-hermes-home-sensitive |
| skills discovery | healthy | session-read-only | skills tree inspection | skill-presence-not-equal-host-readiness |
| skills host readiness | warning | global | matrix + preflight checks | skill-presence-not-equal-host-readiness |
| MCP visibility | warning | passive | config/listing only | mcp-sandbox-independence-unproven |
| provider health | warning | passive | passive status/docs | provider-health-partial-only |
| delegation/orchestration | warning | session-orchestration | tightly scoped read-only delegation | delegation-must-be-read-only-scoped |
| git commit in sandbox | approval-gated but in-scope when explicitly requested | sandbox-write | leave uncommitted diff | none |
| git push | forbidden | any | none | none |

## Canonical Rules

- documented != executable
- skill exists != host ready
- helper/unit proof != runtime proof
- watch/research != implementation
- accepted risk != silence
- add = audit + prune before new artifacts
