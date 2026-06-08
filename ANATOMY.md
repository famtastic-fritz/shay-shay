# Shay Anatomy — Biological Model Mapping

Shay is organized as a living system with distinct organs, each with its own responsibility. This document maps each package to its biological role.

## The System Architecture

| Package | Anatomy Role | Description | Phase | Status |
|---------|------|-------------|-------|--------|
| `@shay/core` | Spine | Central nervous system kernel. Holds config loading, schema registry, event bus, credential vault. Routes all startup signals. | 0 | Skeleton |
| `@shay/memory` | Nervous System | Distributed memory fabric. Semantic search, context window management, session persistence, recall chains. | 1 | Stub |
| `@shay/brain` | Brain | Reasoning router and anticipation cross-cutting. Routes reasoning chains, manages thought traces, coordinates multi-agent flows. Not a package yet (lives in @shay/brain as a future concern). | 2 | Stub |
| `@shay/ingestion` | Digestive System | Ingestion protocol, data normalization, vectorization, message canonicalization. Converts raw input into system-native types. | 2 | Stub |
| `@shay/doctor` | Immune System | Self-diagnostic, verification gate, health checks. The `verify()` function. Runs before every major decision. Stub gate pattern in Ph0. | 0 | Working Stub |
| `@shay/capabilities` | Organs | Capability registry, skill loader, tool resolver. Declares what the system can do. Loaded at startup. | 1 | Stub |
| `@shay/bridge` | External Organs | MCP integration, A2A (agent-to-agent), OASF (Open Agent Service Framework). Connects to outside systems. | 1 | Stub |
| `@shay/surfaces` | Skin | Thin clients — REPL, web chat, CLI. Interfaces between user and core. Stateless. | 1 | Stub |

## The Heart

The Heart (Authority) is NOT a Ph0 concern. It will govern all consensus-based decisions and protocol versioning in later phases. For now, @shay/core is the spine only.

## Cross-Cutting Concerns

- **Anticipation** lives in @shay/brain, not as a separate package. It is a cross-cutting capability that routes reasoning proactively.
- **Conversation Continuity** is built into @shay/memory via session persistence and recall chains.
- **Error Recovery** is the job of @shay/doctor's verification gate.

## Ph0 Status

- **@shay/core** → skeleton config + schema registry + event bus. NOT full bootstrap yet; startup sequence still needs work.
- **@shay/doctor** → working stub. Has the `verify()` gate interface; returns boolean. Full diagnostics deferred to Ph1.
- **All others** → stub packages. Exports exist, TypeScript compiles, but behavior is minimal or empty.
