# Shay Worker Role Matrix

Date: 2026-06-13
Source doctrine: HyperSwarm

## Role Matrix

| role | primary job | allowed in this mission | must not do | promotion threshold |
|---|---|---|---|---|
| dispatcher | split mission into bounded lanes | lane decomposition, routing, packet shaping | change mission scope silently | packets are explicit and cheap-enough |
| runner | execute one bounded task | sandbox-only file/docs edits, approved safe validations | self-approve side effects or lane changes | artifact produced and checked |
| checker | verify prerequisites and path truth | path/capability/diff/test verification | do the main mutation task | truth is grounded |
| reviewer | adversarial challenge | attack overclaims, weak assumptions, unsafe promotions | certify its own artifact | blockers/gaps are explicit |
| pruner | prevent additive-only sprawl | classify keep/update/merge/archive/quarantine/supersede | delete source artifacts without approval | overlap is reduced |
| gatekeeper | enforce approvals and forbidden actions | stop live mutation, startup drift, secret use, rewrite-lane bleed | treat silence as approval | side-effect boundaries remain intact |
| recorder/ledgerer | keep durable mission truth | maintain ledgers, artifact lists, tests, gaps, verdicts | fill missing facts with guesses | run trace is auditable |
| promoter | decide what can graduate | recommend PR/promotion/cutover readiness | promote unreviewed output | recommendation is evidence-backed |
| watcher | track drift/stalls/open risks | monitor gaps and drift across waves | become a hidden dispatcher | open risks are current |
| gap_logger | turn unknowns into durable records | log every blocker/uncertainty with one next action | bury blockers in prose | no real gap dies silently |

## Mission-Specific Owner Defaults

- external dependency questions -> research_fetcher/reviewer
- runtime proof questions -> runner/checker/gatekeeper
- cutover proposals -> promoter/reviewer/gatekeeper
- documentation canon -> recorder/ledgerer/pruner
- skill readiness truth -> promoter/reviewer
