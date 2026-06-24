# Model Capability + Billing Matrix

Generated: 2026-06-24
Repo: /Users/famtasticfritz/famtastic/shay-shay

This is the practical matrix for Fritz's current Shay environment — not a generic vendor brochure.

## Billing types used here

- subscription = authenticated account/subscription lane (OAuth-style account access)
- metered = API-key lane where usage can directly incur per-use/token cost
- metered/free-tier = API-key lane that may have free quota, but should still be treated as a metered API surface unless proven otherwise

## Currently active / configured provider surfaces

| Provider lane | Auth state | Billing type | Notes |
|---|---|---:|---|
| Z.AI / GLM | configured | metered | Current default runtime in this environment |
| Google / Gemini | configured | metered/free-tier | API-key lane; may have free quota depending on account/project |
| Anthropic | configured | metered | Native API-key lane |
| OpenAI Codex | logged in | subscription | OAuth/login lane; treat as subscription-backed access |
| OpenAI API | not set | n/a | No direct OpenAI API key configured |
| OpenRouter | not set | n/a | Not configured |
| xAI / Grok | not set | n/a | Not configured |
| Kimi | not set | n/a | Not configured |
| MiniMax | not set | n/a | Not configured |
| StepFun | not set | n/a | Not configured |

## Model capability matrix

| Provider | Model | Tools | Vision | Reasoning | Billing type | Recommended use |
|---|---|---:|---:|---:|---|---|
| Z.AI | glm-5.2 | no | no | no* | metered | pure text-only lane, drafting, simple transforms, no tool workflows |
| Z.AI | glm-5.1 | yes | no | yes | metered | cheap default orchestration / cron / tool-driving work |
| Z.AI | glm-5 | yes | no | yes | metered | general text/tool lane |
| Z.AI | glm-5v-turbo | yes | yes | yes | metered | multimodal GLM lane |
| Z.AI | glm-4.7 | yes | no | yes | metered | fallback older coding lane |
| Gemini | gemini-3.1-pro-preview | yes | yes | yes | metered/free-tier | stronger multimodal/reasoning lane |
| Gemini | gemini-3-pro-preview | yes | yes | yes | metered/free-tier | strong multimodal/reasoning lane |
| Gemini | gemini-3-flash-preview | yes | yes | yes | metered/free-tier | cheaper/faster multimodal lane |
| Gemini | gemini-3.1-flash-lite-preview | yes | yes | yes | metered/free-tier | lowest-cost Gemini lane |
| Anthropic | claude-haiku-4-5 | yes | yes | yes | metered | cheap Anthropic orchestration lane |
| Anthropic | claude-sonnet-4-6 | yes | yes | yes | metered | build/debug/reasoning lane |
| Anthropic | claude-opus-4-7 | yes | yes | yes | metered | premium review / adversarial lane |
| OpenAI Codex | gpt-5.5 | yes | yes | yes | subscription | premium subscription lane |
| OpenAI Codex | gpt-5.4 | yes | yes | yes | subscription | premium subscription lane |
| OpenAI Codex | gpt-5.3-codex | yes | yes | yes | subscription | codex-oriented coding lane |
| OpenAI Codex | gpt-5.2-codex | yes | yes | yes | subscription | codex-oriented coding lane |

\* glm-5.2 is manually pinned in Shay truth as text-only / no-tools / no-vision for safety in this environment.

## Operational doctrine from this matrix

### Safe default lanes
- Default tool-driving brain: `zai / glm-5.1`
- Cheap text-only lane: `zai / glm-5.2`
- Vision-capable cheap-ish lane: `gemini-3-flash-preview` or `gemini-3.1-flash-lite-preview`

### Premium / protected lanes
- Subscription lane that can drain if inherited: `openai-codex`
- Premium metered review lane: `anthropic claude-opus-4-7`

### Hard rule
- Do not route tool-required work to `glm-5.2`
- Do not let cron jobs inherit `openai-codex` by default
- Pin agent cron jobs explicitly when cost matters

## Missing but useful next surfaces
- Explicit router rule: auto-block tool-required tasks from `glm-5.2`
- First-class `shay capabilities` or `shay intelligence` command that prints this matrix live
- Billing classifier in status output: `subscription` vs `metered` vs `free-tier` vs `unconfigured`

## Source of truth used for this matrix
- `shay status`
- auth/config surfaces in current runtime
- `agent.models_dev.get_model_capabilities(...)`
- local Shay capability overrides for `glm-5.2`
