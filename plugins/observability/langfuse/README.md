# Langfuse Observability Plugin

This plugin ships bundled with Shay-Shay but is **opt-in** — it only loads when
you explicitly enable it.

## Enable

Pick one:

```bash
# Interactive: walks you through credentials + SDK install + enable
shay tools  # → Langfuse Observability

# Manual
pip install langfuse
shay plugins enable observability/langfuse
```

## Required credentials

Set these in `~/.shay/.env` (or via `shay tools`):

```bash
SHAY_LANGFUSE_PUBLIC_KEY=pk-lf-...
SHAY_LANGFUSE_SECRET_KEY=sk-lf-...
SHAY_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

Without the SDK or credentials the hooks no-op silently — the plugin fails
open.

## Verify

```bash
shay plugins list                 # observability/langfuse should show "enabled"
shay chat -q "hello"              # then check Langfuse for a "Shay-Shay turn" trace
```

## Optional tuning

```bash
SHAY_LANGFUSE_ENV=production       # environment tag
SHAY_LANGFUSE_RELEASE=v1.0.0       # release tag
SHAY_LANGFUSE_SAMPLE_RATE=0.5      # sample 50% of traces
SHAY_LANGFUSE_MAX_CHARS=12000      # max chars per field (default: 12000)
SHAY_LANGFUSE_DEBUG=true           # verbose plugin logging
```

## Disable

```bash
shay plugins disable observability/langfuse
```
