Title
Shay Intelligence Control Plane

Goal
Build the intelligence spine first so Shay can justify route decisions with evidence instead of relying on static roles or instinct.

Tasks
- [x] Lock module boundaries and shared schemas
- [x] Build provider/model registry
- [x] Add telemetry schema + storage
- [x] Refactor agent registry into templates + worker instances
- [x] Add evidence-backed routing + route explanation
- [x] Unify memory/truth surfaces
- [x] Update truth-surface docs
- [x] Run verification and leave clean proof

Status
Completed for overnight slice

Started
2026-06-19

Ended
2026-06-19

Execution
Implemented the control-plane slice in repo code, exposed it via CLI, extended telemetry fields, added tests, ran targeted pytest, and ran live CLI verification commands.

Research
Used the doctrine brief plus the two 2026-06-18 agency/control-plane docs as the dependency map.

Review
Parent verification passed. Cheap reviewer lane failed to return grounded output twice, so parent review remained the deciding gate.

Skills
- hyperswarm
- hyperparallel-swarm-orchestration
- shay-shay

Proof
- `python -m pytest tests/test_intelligence_layer.py tests/agent/test_process_intelligence.py -o addopts=''`
- `python -m shay_cli.main intelligence control-plane modules`
- `python -m shay_cli.main intelligence control-plane providers`
- `python -m shay_cli.main intelligence control-plane explain implement routing evidence`
