# QA skill map — product app flow + proof discipline

Date: 2026-06-26
Repo: shay-shay
Status: planning artifact for future skill build

## Purpose
Define what a reusable QA skill needs in order to evaluate product apps like FAMtastic By the Numbers without drifting into shallow "looks good" reviews.

## Core thesis
This QA skill should not behave like a generic UI once-over.
It should act like a conversion + trust + proof checker across:
- activation flow
- premium flow
- mobile flow
- browser behavior
- product-truth alignment

## Inputs the skill should require
- canonical app path
- canonical brief / product promise if one exists
- target environment (local/staging/live)
- payment mode truth (mock/live)
- persistence mode truth (local/mysql/etc.)
- specific screens or flows under review
- known gaps / current concerns
- proof expectation (screenshots, console, network, pass-fail ledger)

## Mandatory audit lanes

### 1. Landing / promise lane
Check:
- does the hero explain the payoff fast?
- is the language trust-building instead of vague mysticism?
- are the first CTAs obvious?
- does the page communicate what is free vs paid?

### 2. Intake friction lane
Check:
- are we asking for too much before value?
- are required fields justified?
- do optional fields stay optional?
- do mobile inputs feel clean and tappable?

### 3. First-result activation lane
Check:
- does the first result feel meaningful?
- is one signal visually dominant?
- is the value obvious before the upsell?
- is the math visible enough to create trust?

### 4. Full-chart comprehension lane
Check:
- does the result hierarchy guide the eye?
- are cards/panels scannable?
- does the reading read like a story, not a stats dump?
- are interpretation claims proportional to the underlying model?

### 5. Premium conversion lane
Check:
- does premium deepen rather than rescue the experience?
- are locked vs unlocked states clear?
- is the CTA honest about what unlocks?
- do purchase/restore/reload flows work end to end?

### 6. Compatibility lane
Check:
- does compatibility stay separate enough from core activation?
- does the scoring/summary feel earned?
- are partner fields and empty states clear?
- does premium compatibility promise stay aligned to actual engine depth?

### 7. Mobile layout lane
Check:
- hero overlap/collision
- card overflow
- text density
- button spacing / tap targets
- scroll rhythm and section sequencing

### 8. Trust / compliance lane
Check:
- disclaimer present and positioned well
- privacy language present where needed
- no overclaiming
- observation vs interpretation separation when relevant
- support/restore language clear

## Product-specific logic checks
- master numbers preserved correctly where intended
- reduction math displayed correctly
- invalid inputs handled cleanly
- method/lineage named correctly
- partner/compatibility edge cases handled honestly
- pricing/config-driven CTA matches runtime truth

## Proof rules
- browser-driven verification only for UX claims
- no shortcut-only proof for user-facing flows
- capture evidence by screen/state
- produce explicit pass/fail ledger
- log reproducible gaps with steps
- separate observed fact from interpretation/recommendation

## Suggested output shape
1. Executive verdict
2. What passed
3. What broke
4. UX friction
5. Trust/compliance issues
6. Mobile issues
7. Monetization/premium issues
8. Exact reproduction steps
9. Proof references
10. Priority order: fix now / future / ignore

## Suggested reusable checklist by screen
- Landing / hero
- Intake
- Free result
- Full chart
- Math transparency
- Compatibility
- Premium locked state
- Premium unlocked state
- Save locally
- Restore purchase
- Reload persistence
- Mobile narrow view
- Payment return lane

## Tool expectations
Primary:
- browser
- vision
- file
- terminal
Optional:
- computer_use for desktop-only states

## Artifact expectations
The finished skill should eventually include:
- SKILL.md
- one checklist template for product apps
- one issue-ledger template
- one proof-report template
- pitfalls section for false-positive QA claims

## Why this matters
Without this skill, QA drifts into generic comments like "looks clean" or "responsive enough."
That is weak.
The skill needs to judge whether the product:
- earns trust
- delivers first-session value fast
- keeps premium honest
- survives mobile reality
- and produces proof Fritz can believe
