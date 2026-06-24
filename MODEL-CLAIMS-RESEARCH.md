# Model Claims Research

Generated: 2026-06-24

Purpose: build a better truth layer for dynamic worker-pool routing.

## What I researched

I pulled claims from three layers:

1. Local Shay truth
   - current live overrides inside this repo
2. models.dev normalized catalog
   - machine-readable claims for tools / vision / reasoning / context
3. provider docs
   - general capability surfaces and model-family docs

## The important finding

We have a truth conflict.

### Conflict: GLM family
- Fritz's observed reality / suspicion:
  - glm-5.2 is text-only
  - glm-5.1 and possibly the other non-vision GLM variants may also be text-only in practice
- models.dev currently claims:
  - glm-5.2 tool_call=true, reasoning=true
  - glm-5.1 tool_call=true, reasoning=true
  - glm-5 tool_call=true, reasoning=true
  - glm-4.7 tool_call=true, reasoning=true
  - only glm-5v-turbo is explicitly multimodal/vision

That means catalog truth alone is not safe enough to drive worker-pool routing.

## What this means architecturally

For worker-pool creation, we need a layered truth model, not a single matrix.

### Recommended truth hierarchy
1. Fritz live directive / verified runtime probe
2. live provider probe results captured by Shay
3. local manual override file in repo
4. models.dev catalog claims
5. provider marketing/docs language

If 2 and 3 say a model cannot really do tools, that must beat 4.

## Billing classes in this environment

### Subscription
- openai-codex
  - gpt-5.5
  - gpt-5.4
  - gpt-5.3-codex
  - gpt-5.2-codex

### Metered
- zai / glm
- anthropic

### Metered or free-tier depending account/project
- gemini

## What we should build next

### 1. A live capability probe command
Something like:
- `shay intelligence control-plane probe-model zai glm-5.1`
- `shay intelligence control-plane probe-model zai glm-5.2`

It should test separately:
- plain text completion
- tool-call compliance
- image/attachment acceptance
- structured output compliance
- long-context acceptance

### 2. A persistent capability registry
A file like:
- `runtime/model_capability_registry.json`

Per model store:
- catalog claims
- live probe results
- last verified timestamp
- billing type
- lane fit
- confidence score
- override reason if manually pinned

### 3. Dynamic worker-pool routing should use fit scores, not just labels
Per worker packet score models on:
- tools required?
- vision required?
- reasoning depth needed?
- context size needed?
- billing sensitivity?
- subscription-protected lane?
- proven reliability for this task family?

## Best current practical rule set

Until live probes exist:
- trust glm-5v-turbo for multimodal GLM work
- treat glm-5.2 as text-only because we explicitly overrode it
- treat glm-5.1 / glm-5 / glm-4.7 as disputed for tool use until probed live
- do not let disputed models become automatic worker defaults for tool-heavy jobs
- use gemini/anthropic/openai-codex lanes where catalog + ecosystem behavior are less ambiguous

## Files created
- `/Users/famtasticfritz/famtastic/shay-shay/MODEL-CLAIMS-RESEARCH.json`
- `/Users/famtasticfritz/famtastic/shay-shay/MODEL-CLAIMS-RESEARCH.md`

## Source URLs used
- https://models.dev/api.json
- https://docs.z.ai/api-reference/llm/chat-completion
- https://docs.z.ai/guides/llm/glm-4.5
- https://ai.google.dev/gemini-api/docs/models
- https://docs.anthropic.com/en/docs/about-claude/models/overview
