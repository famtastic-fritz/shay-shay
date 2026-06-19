Title
Shay Intelligence Control Plane

Purpose
Turn the seeded intelligence layer into a governed control plane that can route, supervise, verify, and improve work across agents, tools, models, providers, and memory systems.

Goal
Build the intelligence spine first so Shay can justify route decisions with evidence instead of relying on static roles or instinct.

Tasks
- [x] Lock the layer name as Intelligence Control Plane
- [x] Define module boundaries for memory/truth, capability registry, provider/model registry, agency, and telemetry/routing proof
- [x] Build the provider/model registry as routable truth
- [x] Add durable telemetry for routed task outcomes
- [x] Refactor static agent registry into template registry plus instantiated workers
- [x] Add evidence-backed routing and route explanation
- [x] Unify truth, research, and operational memory surfaces
- [x] Wire CLI surfaces and tests for the control-plane slice
- [x] Update truth surfaces and leave verification proof

Status
Completed for the targeted overnight slice

Started
2026-06-19

Ended
2026-06-19

Execution
Dependency-first build completed in the intended order: provider/model registry -> telemetry schema usage -> template registry -> evidence-backed routing -> memory/truth surfaces -> CLI exposure -> parent verification.

Research
Current doctrine and implementation map were used as the dependency map:
- /Users/famtasticfritz/famtastic/shay-shay/docs/shay-agency-system-doctrine-2026-06-18.md
- /Users/famtasticfritz/famtastic/shay-shay/docs/shay-agency-system-implementation-map-2026-06-18.md

Review
Parent verification completed with targeted pytest plus live CLI command runs.
Subagent reviewer lane was attempted twice and failed to produce a usable grounded review, so it counts as negative evidence for cheap-review routing, not closure proof.

Skills
- hyperswarm
- hyperparallel-swarm-orchestration
- shay-shay

Blocked By
None

Proof
Done for this slice means Shay can now expose control-plane facts through CLI surfaces and tests for:
- why this model/provider route
- which template owns the job shape
- what telemetry scorecard exists for that route
- which memory/truth surfaces feed the decision
- which module boundary owns each part of the intelligence spine
