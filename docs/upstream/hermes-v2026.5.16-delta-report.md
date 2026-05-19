# Hermes upstream delta report — v2026.5.7 to v2026.5.16

Date: 2026-05-19
Shay baseline: `v0.13.0-shay.1` / `4e0207f`
Hermes base release: `v2026.5.7` / Hermes Agent v0.13.0
Hermes target release: `v2026.5.16` / Hermes Agent v0.14.0
Target tag commit: `8487dfb57d2f2f7b310a2b3eb692b32674af22cd`
Current Hermes `main` at investigation time: `39c41d0f23a35fdecc143e3cc5ffb2b4dbd3e25d`

## Executive take

Do not merge Hermes `v2026.5.16` directly into Shay-Shay `main`.

The release is valuable, but it is too broad and too Hermes-branded to import blindly. The delta touches the exact files that define Shay's rebrand boundary: `pyproject.toml`, `cli.py`, `hermes_cli/*`, `hermes_constants.py`, `hermes_state.py`, `hermes_bootstrap.py`, `agent/display.py`, `agent/prompt_builder.py`, gateway config/session files, installer/update scripts, docs, and runtime-path logic.

Recommended path: selective porting in waves, not a single upstream merge.

Priority order:
1. Security/dependency fixes.
2. Provider/model updates that matter to Shay.
3. Runtime reliability and performance fixes.
4. Gateway/platform fixes already useful to Fritz's workflow.
5. Tooling improvements.
6. Optional new surfaces only after Shay's product direction says they belong.

## Raw delta

From a clean clone of `https://github.com/NousResearch/hermes-agent.git`:

```text
git diff --shortstat v2026.5.7..v2026.5.16
1395 files changed, 165539 insertions(+), 29113 deletions(-)

git rev-list --count v2026.5.7..v2026.5.16
847 commits
```

Release metadata from GitHub:

```text
v2026.5.7  — Hermes Agent v0.13.0 (2026.5.7) — The Tenacity Release
published 2026-05-07T16:23:08Z

v2026.5.16 — Hermes Agent v0.14.0 (2026.5.16)
published 2026-05-16T09:59:15Z
```

Hermes release notes claim v0.14.0 includes 808 commits, 633 merged PRs, 1,393 files changed, 165,061 insertions, 545 issues closed, and 215 community contributors. Local git counted 847 commits and 1,395 changed files in the tag-to-tag diff; the difference is likely release-note filtering versus raw graph/diff accounting.

## File-area impact

Top changed areas by first path component:

```text
377 tests
263 website
138 optional-skills
 85 skills
 74 plugins
 71 tools
 67 hermes_cli
 59 ui-tui
 57 agent
 41 environments
 39 gateway
 35 web
 16 locales
 14 scripts
 10 acp_adapter
  8 .github
```

Highest-churn files include:

```text
gateway/run.py                                  +2430/-768
website/src/data/userStories.json              +2252/-734
run_agent.py                                   +2075/-315
cli.py                                         +1882/-290
hermes_cli/main.py                             +1769/-293
plugins/platforms/line/adapter.py              +1638/-0
tests/hermes_cli/test_auth_xai_oauth_provider.py +1605/-0
gateway/platforms/telegram.py                  +1277/-186
agent/plugin_llm.py                            +1046/-0
agent/lsp/servers.py                           +1040/-0
hermes_cli/auth.py                              +989/-32
agent/auxiliary_client.py                       +821/-98
scripts/install.ps1                             +775/-85
plugins/web/firecrawl/provider.py               +773/-0
hermes_cli/tools_config.py                      +734/-140
```

## Change categories

Heuristic commit-subject classification from the tag-to-tag log:

```text
docs/tests/CI:             186 commits
gateway/messaging:         137 commits
providers/models:          114 commits
CLI/TUI/dashboard:         112 commits
tools/capabilities:         88 commits
install/distribution:       87 commits
cron/kanban/goals:          86 commits
skills/plugins:             71 commits
Windows:                    50 commits
performance:                30 commits
security:                   21 commits
other/uncategorized:       118 commits
```

Important caveat: categories overlap. Example: an xAI provider fix can also be a security/auth fix and a docs/test change.

## Release highlights worth considering

Hermes v0.14.0's major release-note highlights:

- xAI Grok via SuperGrok OAuth; grok-4.3 context moved to 1M.
- OpenAI-compatible local proxy for OAuth providers.
- `x_search` tool for X/Twitter search.
- Microsoft Teams / Graph stack wired end-to-end.
- Lazy dependency/debloating wave.
- Official PyPI package path: `pip install hermes-agent`.
- Cross-session one-hour Claude prompt caching.
- Faster browser console evaluations via persistent CDP connection.
- Cold-start performance wave, roughly 19 seconds off Hermes launch.
- New LINE and SimpleX Chat messaging platforms.
- Live `/handoff` session transfer.
- Native button UI for `clarify` on Telegram/Discord.
- Discord channel history backfill.
- `vision_analyze` passes pixels to vision-capable models.
- Per-turn file mutation verifier footer.
- LSP semantic diagnostics on write.
- Unified pluggable `video_generate`.
- `computer_use` cua-driver backend for non-Anthropic models.
- Zed ACP Registry integration via `uvx`.
- OpenRouter Pareto Code router.
- NovitaAI provider.
- Codex app-server runtime for OpenAI/Codex models.
- `huggingface/skills` trusted default tap.
- Nine new optional skills.
- Brave Search and DDGS search providers.
- Native Windows support marked early beta.

## Rebrand risk assessment

Risk level: high for a direct merge.

Reasons:

1. Upstream still uses Hermes naming, package layout, CLI commands, environment variables, and runtime paths.
2. The update touches core identity files and runtime naming files.
3. The update includes install/update/PyPI work that is explicitly Hermes-packaged and likely conflicts with Shay's `shay-shay` package name and `shay` entrypoint.
4. The update touches gateway/session/config behavior, where `~/.shay` and copied runtime state must not be regressed to `~/.hermes`.
5. The update touches skill discovery and built-in skill paths, where Shay needs to preserve its FAMtastic skill/personality direction.

Rebrand-sensitive files changed upstream include at least these areas:

```text
pyproject.toml
README.md
README.zh-CN.md
cli.py
hermes_bootstrap.py
hermes_constants.py
hermes_state.py
hermes_time.py
hermes_cli/*
agent/display.py
agent/prompt_builder.py
agent/skill_commands.py
agent/transports/hermes_tools_mcp_server.py
gateway/*
scripts/install.ps1
setup-hermes.sh
acp_registry/agent.json
website/*
```

A raw grep at the target tag found hundreds of Hermes references in active source/docs paths. That is expected upstream, but it means a mechanical merge would reintroduce Hermes vocabulary unless followed by a deliberate rebrand pass.

## Must-port candidates

These should be ported first because they improve safety or prevent avoidable failures.

### Security and dependency fixes

Representative commits:

```text
fcd9011f fix(security): separate OAuth PKCE state from code_verifier
72f94f4a test(security): regression guard for OAuth PKCE state/verifier separation
d725407c security(deps): bump aiohttp, anthropic, cryptography to CVE-fixed versions (#26830)
6ba35ec3 tighten dangerous-command detection (#26829)
627f8a5f security: sanitize tool error strings before injecting into model context (#26823)
6af99423 fix(url-safety): allow only http and https schemes
04b1fdae security(deps): add upper bounds to 5 loose deps + document supply chain policy (#24226)
d6c9711b fix(security): reduce unnecessary shell=True in subprocess calls
c1eb2dcd feat(security): supply-chain advisory checker + lazy-install framework + tiered install fallback (#24220)
f6736ced fix(security): sanitize env and redact output in quick commands
0c5c4d1b fix(skills-hub): cover remaining SSRF fetch paths after #10029
9bbad3cc fix(security): drop caller-controlled author override in kanban_comment
c3864000 fix(security): honor relay-declared sender_type in Google Chat adapter to prevent BOT filter bypass
```

Porting note: these should be cherry-picked or manually applied by file, then adapted from `HERMES_*` / `hermes_*` to `SHAY_*` / `shay_*` before commit.

### Runtime reliability fixes

Worth reviewing early:

- async bridge cleanup and unscheduled coroutine fixes.
- context compression JSON/error handling fixes.
- fallback/provider retry fixes.
- memory Windows file-lock TOCTOU fix.
- gateway platform circuit breaker so one broken adapter does not kill the gateway.
- process registry orphan cleanup.
- SQLite fallback to `journal_mode=DELETE` on NFS/SMB/FUSE.

These are likely useful to Shay because they harden the agent kernel rather than changing product identity.

## Should-port candidates

### Provider/model capabilities

- xAI OAuth / SuperGrok provider.
- Grok 1M context metadata.
- DeepSeek thinking/reasoning mapping.
- OpenRouter Pareto Code router.
- NovitaAI provider.
- Codex app-server runtime.
- Copilot ACP deprecation and GitHub Models 413 hints.

Porting note: high value, but auth/provider code often touches config, credential pools, env var naming, and docs. Needs targeted ports plus smoke tests for model selection and provider auth display.

### Performance

- Cold-start deferrals.
- Lazy platform imports.
- Fast browser CDP console calls.
- Prompt caching improvements.
- Model catalog disk-cache-first lookup.

Porting note: high value for daily use. Most performance changes should be portable, but lazy dependency work is tied to installer/package behavior and should be split from the broader PyPI/debloat migration.

### Gateway improvements

- Platform circuit breaker.
- Telegram topic/thread fixes.
- Telegram notification controls.
- Discord history backfill and auth/slash fixes.
- WhatsApp send failure timeout.
- Slack whitespace command guard.
- Gateway drain/resume fixes.

Porting note: useful because Shay is expected to be always-on and mobile-pushing. Must preserve `~/.shay` state and gateway session mappings.

## Optional or defer

### New platforms

- LINE.
- SimpleX Chat.
- Microsoft Teams.

These are impressive, but they expand surface area. Defer unless Fritz has an immediate workflow need or they unlock FAMtastic collaboration.

### PyPI/distribution work

- Official `pip install hermes-agent` path.
- `hermes postinstall`.
- pip-aware update command.
- wheel/TUI bundle work.

Do not port as-is. This work must be redesigned for `shay-shay`, `shay`, `~/.shay`, and the FAMtastic distribution story. High future value, high rebrand conflict.

### Windows early beta

High value for cross-platform future, but Fritz's current host is macOS and Shay's runtime target is a Hetzner box. Port only security/reliability pieces now; defer installer polish unless Windows becomes an active target.

### Website/docs bulk

Do not bulk-import. Upstream docs are Hermes-branded and would be wrong for Shay. Extract only technical facts needed for adapted Shay docs.

### Optional skills bulk

Review selectively. Some optional skills are valuable (`watchers`, OSINT, Notion update), but bulk importing can clutter Shay's skill inventory and dilute the FAMtastic direction.

## Skip for now

- Large upstream website user-story/docs sweeps.
- Hermes-specific branding/docs release material.
- Hermes PyPI/package metadata without a Shay distribution design.
- Atropos/RL environment removals/additions unless we decide RL environments matter to Shay.
- New platform adapters with no immediate FAMtastic use case.

## Proposed integration plan

### Phase 0 — Prepare safety rails

1. Keep `v0.13.0-shay.1` as rollback point.
2. Create branch: `chore/hermes-v2026.5.16-delta`.
3. Add upstream remote only if needed:
   `git remote add hermes https://github.com/NousResearch/hermes-agent.git`
4. Fetch tags: `git fetch hermes --tags`.
5. Create a rebrand audit script before porting anything.

Minimum rebrand audit checks:

```text
No accidental active runtime references to ~/.hermes where ~/.shay is required.
No active env var fallbacks that switch Shay back to HERMES_HOME unexpectedly.
No console entrypoint regression from shay to hermes.
No package-name regression from shay-shay to hermes-agent.
No banner/help/version regression to Hermes.
No docs claiming Shay is Hermes except lineage notes.
```

### Phase 1 — Security patch wave

Manual/cherry-pick targeted security fixes. Commit separately:

```text
fix: port upstream security hardening
```

Run compile/smoke tests and rebrand audit.

### Phase 2 — Kernel reliability/performance wave

Port agent-loop, async, compression, fallback, prompt caching, model metadata/cache, browser CDP performance where clean.

Commit separately:

```text
perf: port upstream runtime reliability updates
```

### Phase 3 — Provider wave

Port provider/model improvements that matter now:

- xAI OAuth if Fritz wants SuperGrok available inside Shay.
- DeepSeek reasoning mapping.
- OpenRouter Pareto Code router.
- Codex/Copilot fixes.

Commit separately:

```text
feat: port upstream provider updates
```

### Phase 4 — Gateway wave

Port always-on/mobile-relevant gateway fixes.

Commit separately:

```text
fix: port upstream gateway reliability fixes
```

### Phase 5 — Distribution/design decision

Only after the above: decide whether Shay wants a PyPI/package/update story. This should be a Shay product design, not a Hermes import.

## Test plan for any port wave

Run at minimum:

```text
python -m compileall -q cli.py run_agent.py model_tools.py shay_cli agent tools gateway cron
shay --version
shay --help
shay status --all
shay tools list
shay config path
```

When pytest exists in the venv, add targeted tests around touched areas:

```text
python -m pytest tests/agent tests/tools tests/shay_cli tests/gateway -q -o 'addopts='
```

Current local note: this repo's `.venv` does not currently have pytest installed, so previous validation used compile checks and CLI smoke tests.

## Final recommendation

Proceed, but do not merge upstream wholesale.

The release is worth mining. The first integration should be a small, high-confidence security/reliability wave. If that goes cleanly, follow with provider and gateway waves. Keep distribution/PyPI, Windows installer polish, new platforms, and docs bulk as separate decisions.

Shay's rule: Hermes is the upstream kernel, not the product identity. Every imported change must be adapted to Shay's name, paths, runtime, memory, and FAMtastic role before it lands.
