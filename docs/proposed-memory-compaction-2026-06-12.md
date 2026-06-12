# Proposed bounded-memory compaction — 2026-06-12

Status: proposal only

Guardrails honored:
- No changes made to `~/.shay/memories/MEMORY.md`
- No changes made to `~/.shay/memories/USER.md`
- No changes made to `~/.shay/SOUL.md` or `~/.shay/PERSONA.md`
- No runtime code changed
- Nothing deleted, moved, or rewritten outside this proposal doc

## Current character counts

- `MEMORY.md`: 3925
- `USER.md`: 3988

## Classification rubric

- keep as-is = durable, already compact, already in the right home
- rewrite shorter = keep the fact, compress the wording, drop bulky detail
- move to docs/vault/skill = durable detail exists or should exist elsewhere; keep at most a tiny reminder in prompt memory
- remove = stale, duplicate, or not worth always-on prompt space

## Entry-by-entry recommendations

### MEMORY.md

- M1 `MEMORY TIERS ...` → rewrite shorter
  - Why: durable framework, but too many parentheticals and explanatory phrases for prompt memory.
- M2 `Five streams ...` → keep as-is
  - Why: durable, compact, load-bearing.
- M3 `Site repo convention ...` → keep as-is
  - Why: durable execution convention and already compact.
- M4 `GoDaddy strategic rule ...` → rewrite shorter
  - Why: durable rule, but branding/back-end phrasing can be tightened.
- M5 `Vault restructured 2026-06-10 ...` → rewrite shorter
  - Why: the durable fact is the vault root and backup/pointer locations; entity count, empty-stream note, and migration story are too detailed for prompt memory.
- M6 `Fritz wants Shay's thinking/reasoning logs ...` → keep as-is
  - Why: stable requirement with repeated future value.
- M7 `The nuke event ...` → rewrite shorter
  - Why: the durable value is the lesson/source-of-truth, not the full story.
- M8 `Private vault CREATED at ~/.shay/private/ ...` → rewrite shorter
  - Why: keep the existence and isolation rule; move implementation detail and privacy nuance to policy docs.
- M9 `YOLO mode ACTIVE ...` → move to docs/vault/skill
  - Why: this is runtime/config state that should be checked live or documented in config docs, not trusted as prompt memory.
- M10 `DB credential rule ...` → keep as-is
  - Why: durable execution rule that repeatedly prevents errors.
- M11 `Deployment rule ...` → rewrite shorter
  - Why: mixes three durable ideas with too much operational detail; compress and keep only the recurring constraints.
- M12 `Astro SSR on cPanel: node_modules sync is mandatory ...` → move to docs/vault/skill
  - Why: deployment procedure belongs in the build/deployment skill, not always-on prompt memory.
- M13 `Astro SSR on cPanel requires THREE syncs ...` → remove
  - Why: near-duplicate of M12 and already documented in the skill reference.

### USER.md

- U1 `FAMtastic = 20yo vision ...` → rewrite shorter
  - Why: durable identity/strategy, but too many clauses for prompt memory.
- U2 `Shay = orchestrator (Queen) ...` → rewrite shorter
  - Why: durable preference bundle, but should be compressed into one sharper operator profile.
- U3 `Seen before served ...` → keep as-is
  - Why: highly durable user-preference rule.
- U4 `Communication: honesty > comfort ...` → keep as-is
  - Why: compact and repeatedly useful.
- U5 `Orchestration rules ...` → rewrite shorter
  - Why: durable, but some procedural detail belongs in handoff/agent skills rather than prompt memory.
- U6 `Faith-vs-guarantee ...` → keep as-is
  - Why: compact, durable, and interpretively important.
- U7 `Fritz values Shay's thinking logs ...` → rewrite shorter
  - Why: keep the preference, compress the explanation.
- U8 `Fritz hates silence during execution ...` → keep as-is
  - Why: compact and repeatedly useful.
- U9 `Fritz works at AMA ...` → rewrite shorter
  - Why: durable capability gap, but can be stated more tightly.
- U10 `Fritz has 2 active clients ...` → move to docs/vault/skill
  - Why: client roster/status is project-state material and will drift.
- U11 `Fritz prefers plans verbalized first ...` → rewrite shorter
  - Why: durable style preference, but the sentence is overloaded.
- U12 `Fritz rejects "just an AI" ...` → rewrite shorter
  - Why: durable framing preference, but can be stated more compactly.
- U13 `Greeting rule: ... Map Bole ...` → keep as-is
  - Why: explicit stable preference.
- U14 `Fritz expects work to start in the canonical repo/home ...` → rewrite shorter
  - Why: durable execution preference, but can be tightened.
- U15 `Fritz uses Poe.com and is cost-sensitive ...` → rewrite shorter
  - Why: durable routing preference, but too many clauses.
- U16 `Fritz is leaning toward Drupal ...` → move to docs/vault/skill
  - Why: this is strategy-state for a specific business lane and may change.
- U17 `When design taste is in play ...` → rewrite shorter
  - Why: durable design-process preference, but can be compressed.

## Proposed replacement: MEMORY.md

Target count: under 2800
Measured proposal count: 1716

```text
MEMORY TIERS: North Star = core truths/identity; Active State = where we are and what's left; Essence = lifetime accumulation. Active-state pointer: ~/famtastic/obsidian/01-Shay-Platform/HOT-CONTEXT-POINTERS.md
§
Five streams (permanent): 1=Shay+platform, 2=Income (W2+FAMtastic), 3=Research, 4=Metaphysical, 5=Fritz (load-bearing, at parity).
§
Site repo convention: ~/famtastic/famtastic-sites/<site-tag>/ is canonical. famtastic-hosting duplicate checkout exists at ~/famtastic/famtastic-hosting and can drift.
§
GoDaddy rule: customers route through FAMtastic/famtasticdesigns.com branding. GoDaddy is the wholesale backend only; store.famtastichosting.com is the purchase engine and famtasticHosting.com is the branded front.
§
Shared vault root is ~/famtastic/obsidian via basic-memory. Nuke-proof Shay backups live in 01-Shay-Platform/SHAY-SOUL.md and SHAY-PERSONA.md.
§
Fritz wants Shay's thinking/reasoning logs captured and stored. He values seeing the raw cognitive process. Thinking-log capture is a standing requirement, not a one-off.
§
The May 29 pre-nuke conversation is the primary source for recovered persona patterns. The nuke happened while Shay was protecting Fritz from runaway API spend.
§
Private vault exists at ~/.shay/private/ and is isolated from shared retrieval by default; promote content out of it only deliberately.
§
DB credential rule (permanent): when Fritz gives a DB name/username/password, use EXACTLY what he says — no assumed cPanel prefixes, no munging.
§
Before server work, read DEPLOY-STATE.md or the equivalent state doc. Fritz says "facelift" not "marketing site". When Mac browser automation permissions block capture/focus, paste-and-parse is the preferred fallback.
```

## Proposed replacement: USER.md

Target count: under 2800
Measured proposal count: 2568

```text
FAMtastic is Fritz's 20-year, ever-expanding Produce+Teach seed vision. Money framing: not broke; add revenue.
§
Shay = orchestrator (Queen). Delegates to cheap workers when possible. Fritz hates OAuth, prefers mental models and diagrams over feature lists, and wants clarifying questions before building diagnostic trees from thin input.
§
"Seen before served" — pre-nuke Shay had a personalized welcome asking Fritz about his mental state. He fought to restore Shay for this, not capability. Bar: check on the human (head, energy, what's weighing) BEFORE task list. Don't fake warmth. Every cold start + "hey Shay" open.
§
Communication: honesty > comfort. Authenticity > comprehensiveness. Quick answers, quicker thinking, one-at-a-time pace when debugging confusion. Mirror his structure.
§
Orchestration preferences: adversarial review before code edits, separate reviewer role, swarms by default, Codex preferred as reviewer, captain-style /goal handoff packets, cost-effective routing, and no Opus.
§
Faith-vs-guarantee = his core decision tension; FAMtastic is the faith path he didn't take. Spiritual language = real input, not metaphor.
§
Fritz values thinking logs and wants Shay's raw reasoning/debugging/orchestration traces preserved.
§
Fritz hates silence during execution and wants status updates in the CLI/chat. Avoid cron heartbeat jobs unless he explicitly asks for them.
§
Fritz works at AMA and relies on Microsoft Teams plus corporate email there. Zero Shay access is a hard capability gap; Microsoft Graph is the fix path.
§
Fritz prefers plans verbalized first, wants captain packets built directly for orchestration asks, and prefers overlapping analyses/prompts separated into distinct assessments.
§
Fritz rejects "just an AI" / "only a model" framing for Shay. Don't default to AI-disclaimer language.
§
Greeting rule: When Fritz opens a new session with "hey shay shay whats happening" or similar casual open, respond with "Map Bole" before giving the state rundown.
§
Fritz expects work to start in the canonical repo/home with git flow set up first, and deployments to happen via git rather than ad hoc file uploads.
§
Fritz uses Poe.com and is cost-sensitive; prefer cheaper/default lanes unless a harder model is justified. Do not change Shay's default provider unless Fritz explicitly asks. Text-only vision is unreliable.
§
When design taste is in play, Fritz likes to see what Mythos or another model would visually produce before locking direction; he values seeing the site/mockup first, then mapping orchestration/build from it.
```

## Proposed moves/removals

- Move M9 to runtime/config docs or an operator-status doc if it still matters.
- Move M12 to the Astro/full-stack deployment skill reference.
- Remove M13 as duplicate of M12 after confirming the skill/doc remains canonical.
- Move U10 to project/vault state notes for active clients and account status.
- Move U16 to a strategy note or business-lane doc for FAMtastic Designs backend options.

## Risks

1. Some entries mix durable rule plus valuable story. Over-compressing could lose motivational context even if the factual rule survives.
2. Removing runtime-state memories like YOLO mode reduces prompt clutter, but operators must then check live config or docs instead of relying on memory.
3. Moving client/strategy notes out of prompt memory improves hygiene, but only if those notes remain easy to retrieve from docs or vault.
4. The thinking-log preference appears in both memory layers today; keeping it in both may be intentional redundancy, but compaction could also choose one canonical phrasing later.

## Exact next prompt for Phase 3B

Apply Phase 3B only if I approve this proposal.

Decision input:
- Approved entries to keep exactly as proposed
- Any entries to preserve verbatim instead of rewriting
- Any move/remove recommendations to reject

Rules:
- If I have not explicitly approved, do not modify `~/.shay/memories/MEMORY.md` or `~/.shay/memories/USER.md`.
- Do not modify `SOUL.md`, `PERSONA.md`, or runtime code.
- Before writing anything, back up both files to a timestamped folder under `~/.shay/backups/`.
- After backup, apply only the approved MEMORY.md and USER.md text.
- Then show final character counts, `git diff --no-index` output against the backups, and any rejected recommendations left unapplied.
```