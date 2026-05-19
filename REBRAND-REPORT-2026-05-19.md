# Shay-Shay rebrand handoff — 2026-05-19

## Summary
The Hermes Agent codebase was copied into a new standalone home at `~/famtastic/shay-shay` and rebranded into Shay-Shay without modifying the running Hermes installation. The new `shay` console entry point builds in its own Python 3.13 virtualenv, displays Shay-Shay version/help text, renders a SHAY-SHAY banner with the FAMtastic red/deep-blue palette, and uses `~/.shay` / `SHAY_*` runtime naming. Hermes state was copied into `~/.shay`, including skills, memories, sessions/history, cron/config/state files, auth/config files, API-key `.env` content, gateway/channel state, logs, caches, and history. `SOUL.md` in the repo is intentionally left as Fritz's placeholder drop target.

## Changes made
- Created `~/famtastic/shay-shay` from the current Hermes source in a new directory.
- Rebranded the CLI/package surface from Hermes to Shay-Shay, including `shay` console script, `shay-shay` package name, `SHAY_*` env vars, and `~/.shay` runtime home.
- Replaced the terminal wordmark with a SHAY-SHAY ASCII banner and changed the default theme to FAMtastic night colors: primary `#FF3366`, deep blue `#2C5F8D`, black/night status background.
- Updated startup/help/version/status user-facing strings to Shay-Shay naming; final smoke-test output has no lowercase `hermes` leftovers.
- Created `~/famtastic/shay-shay/SOUL.md` with the exact placeholder content requested.
- Copied Hermes state from `~/.hermes` into `~/.shay`, including skills (652 files), sessions (117 files), cron (1 files), memories/memory files, config, auth files, `.env` secrets, gateway/channel state, logs, caches, and history.
- Created `~/.config/shay` from `~/.config/hermes` when present and adjusted copied text config/state files from Hermes paths/env names to Shay paths/env names.
- Preserved active Telegram integration secrets in `~/.shay/.env` for Shay while keeping token values out of this report.
- Built and installed Shay-Shay editable into `~/famtastic/shay-shay/.venv` and added `~/.local/bin/shay` symlink to the venv entry point.
- Initialized a fresh local git repo with no inherited history and committed the scaffold at `5d423c6`. No remote is configured.

## Files left alone
- `LICENSE` was retained so the MIT license remains intact.
- Attribution/lineage references to Nous Research, the MIT license, and underlying Hermes research/model references were deliberately not treated as product-brand leftovers.
- Some internal implementation names remain where changing them would risk unnecessary breakage; the user-facing CLI/help/version/status surfaces are Shay-Shay.
- The current running Hermes installation under `~/.hermes/hermes-agent` was not edited. Only backups, `~/famtastic/shay-shay`, `~/.shay`, `~/.config/shay`, and the `~/.local/bin/shay` shim were created/updated.
- No GitHub remote was added and nothing was pushed.

## TODOs for Fritz
- Drop the real identity brief into `~/famtastic/shay-shay/SOUL.md`, replacing the placeholder.
- Start Shay for her first wake with `shay` when ready.
- Review `~/.shay/.env` and `~/.shay/config.yaml` if you want to prune inherited Hermes-only settings.
- Set up the GitHub remote manually, e.g. `famtastic-fritz/shay-shay`, then push when you decide.
- Optional: run `shay doctor --fix` later if you want Shay to auto-address non-critical environment warnings; I did not run it because it can make extra changes.

## Smoke test results

```text
$ shay --version
Shay-Shay v0.13.0 (2026.5.7)
Project: /Users/famtasticfritz/famtastic/shay-shay
Python: 3.13.12
OpenAI SDK: 2.37.0
__EXIT__:0
$ shay --help
usage: shay [-h] [--version] [-z PROMPT] [-m MODEL] [--provider PROVIDER] [-t TOOLSETS] [--resume SESSION] [--continue [SESSION_NAME]]
            [--worktree] [--accept-hooks] [--skills SKILLS] [--yolo] [--pass-session-id] [--ignore-user-config] [--ignore-rules] [--tui]
            [--dev]
            {chat,model,fallback,gateway,setup,whatsapp,slack,login,logout,auth,status,cron,webhook,kanban,hooks,doctor,dump,debug,backup,checkpoints,import,config,pairing,skills,plugins,curator,memory,tools,computer-use,mcp,sessions,insights,claw,version,update,uninstall,acp,profile,completion,dashboard,logs} ...

Shay-Shay - AI assistant with tool-calling capabilities

positional arguments:
  {chat,model,fallback,gateway,setup,whatsapp,slack,login,logout,auth,status,cron,webhook,kanban,hooks,doctor,dump,debug,backup,checkpoints,import,config,pairing,skills,plugins,curator,memory,tools,computer-use,mcp,sessions,insights,claw,version,update,uninstall,acp,profile,completion,dashboard,logs}
                        Command to run
    chat                Interactive chat with the agent
    model               Select default model and provider
    fallback            Manage fallback providers (tried when the primary model fails)
    gateway             Messaging gateway management
    setup               Interactive setup wizard
    whatsapp            Set up WhatsApp integration
    slack               Slack integration helpers (manifest generation, etc.)
    login               Authenticate with an inference provider
    logout              Clear authentication for an inference provider
    auth                Manage pooled provider credentials
    status              Show status of all components
    cron                Cron job management
    webhook             Manage dynamic webhook subscriptions
    kanban              Multi-profile collaboration board (tasks, links, comments)
    hooks               Inspect and manage shell-script hooks
    doctor              Check configuration and dependencies
    dump                Dump setup summary for support/debugging
    debug               Debug tools — upload logs and system info for support
    backup              Back up Shay-Shay home directory to a zip file
    checkpoints         Inspect / prune / clear ~/.shay/checkpoints/
    import              Restore a Shay-Shay backup from a zip file
    config              View and edit configuration
    pairing             Manage DM pairing codes for user authorization
    skills              Search, install, configure, and manage skills
    plugins             Manage plugins — install, update, remove, list
    curator             Background skill maintenance (curator) — status, run, pause, pin
    memory              Configure external memory provider
    tools               Configure which tools are enabled per platform
    computer-use        Manage the Computer Use (cua-driver) backend (macOS)
    mcp                 Manage MCP servers and run Shay-Shay as an MCP server
    sessions            Manage session history (list, rename, export, prune, delete)
    insights            Show usage insights and analytics
    claw                OpenClaw migration tools
    version             Show version information
    update              Update Shay-Shay to the latest version
    uninstall           Uninstall Shay-Shay
    acp                 Run Shay-Shay as an ACP (Agent Client Protocol) server
    profile             Manage profiles — multiple isolated Shay-Shay instances
    completion          Print shell completion script (bash, zsh, or fish)
    dashboard           Start the web UI dashboard
    logs                View and filter Shay-Shay log files

options:
  -h, --help            show this help message and exit
  --version, -V         Show version and exit
  -z, --oneshot PROMPT  One-shot mode: send a single prompt and print ONLY the final response text to stdout. No banner, no spinner, no
                        tool previews, no session_id line. Tools, memory, rules, and AGENTS.md in the CWD are loaded as normal; approvals
                        are auto-bypassed. Intended for scripts / pipes.
  -m, --model MODEL     Model override for this invocation (e.g. anthropic/claude-sonnet-4.6). Applies to -z/--oneshot and --tui. Also
                        settable via SHAY_INFERENCE_MODEL env var.
  --provider PROVIDER   Provider override for this invocation (e.g. openrouter, anthropic). Applies to -z/--oneshot and --tui. Also
                        settable via SHAY_INFERENCE_PROVIDER env var.
  -t, --toolsets TOOLSETS
                        Comma-separated toolsets to enable for this invocation. Applies to -z/--oneshot and --tui.
  --resume, -r SESSION  Resume a previous session by ID or title
  --continue, -c [SESSION_NAME]
                        Resume a session by name, or the most recent if no name given
  --worktree, -w        Run in an isolated git worktree (for parallel agents)
  --accept-hooks        Auto-approve any unseen shell hooks declared in config.yaml without a TTY prompt. Equivalent to
                        SHAY_ACCEPT_HOOKS=1 or hooks_auto_accept: true in config.yaml. Use on CI / headless runs that can't prompt.
  --skills, -s SKILLS   Preload one or more skills for the session (repeat flag or comma-separate)
  --yolo                Bypass all dangerous command approval prompts (use at your own risk)
  --pass-session-id     Include the session ID in the agent's system prompt
  --ignore-user-config  Ignore ~/.shay/config.yaml and fall back to built-in defaults (credentials in .env are still loaded)
  --ignore-rules        Skip auto-injection of AGENTS.md, SOUL.md, .cursorrules, memory, and preloaded skills
  --tui                 Launch the modern TUI instead of the classic REPL
  --dev                 With --tui: run TypeScript sources via tsx (skip dist build)

Examples:
    shay                        Start interactive chat
    shay chat -q "Hello"        Single query mode
    shay -c                     Resume the most recent session
    shay -c "my project"        Resume a session by name (latest in lineage)
    shay --resume <session_id>  Resume a specific session by ID
    shay setup                  Run setup wizard
    shay logout                 Clear stored authentication
    shay auth add <provider>    Add a pooled credential
    shay auth list              List pooled credentials
    shay auth remove <p> <t>    Remove pooled credential by index, id, or label
    shay auth reset <provider>  Clear exhaustion status for a provider
    shay model                  Select default model
    shay fallback [list]        Show fallback provider chain
    shay fallback add           Add a fallback provider (same picker as `shay model`)
    shay fallback remove        Remove a fallback provider from the chain
    shay config                 View configuration
    shay config edit            Edit config in $EDITOR
    shay config set model gpt-4 Set a config value
    shay gateway                Run messaging gateway
    shay -s shay-shay-dev,github-auth
    shay -w                     Start in isolated git worktree
    shay gateway install        Install gateway background service
    shay sessions list          List past sessions
    shay sessions browse        Interactive session picker
    shay sessions rename ID T   Rename/title a session
    shay logs                   View agent.log (last 50 lines)
    shay logs -f                Follow agent.log in real time
    shay logs errors            View errors.log
    shay logs --since 1h        Lines from the last hour
    shay debug share             Upload debug report for support
    shay update                 Update to latest version
    shay dashboard              Start web UI dashboard (port 9119)
    shay dashboard --stop       Stop running dashboard processes
    shay dashboard --status     List running dashboard processes

For more help on a command:
    shay <command> --help
__EXIT__:0
$ shay doctor

┌─────────────────────────────────────────────────────────┐
│                 🩺 Shay-Shay Doctor                        │
└─────────────────────────────────────────────────────────┘

◆ Python Environment
  ✓ Python 3.13.12
  ✓ Virtual environment active

◆ Required Packages
  ✓ OpenAI SDK
  ✓ Rich (terminal UI)
  ✓ python-dotenv
  ✓ PyYAML
  ✓ HTTPX
  ✓ Croniter (cron expressions) (optional)
  ✓ python-telegram-bot (optional)
  ✓ discord.py (optional)

◆ Configuration Files
  ✓ ~/.shay/.env file exists
  ✓ API key or custom endpoint configured
  ✓ ~/.shay/config.yaml exists
  ✓ Config version up to date (v23)

◆ Auth Providers
  ⚠ Nous Portal auth (not logged in)
  ✓ OpenAI Codex auth (logged in)
  ⚠ Google Gemini OAuth (not logged in)
  ⚠ MiniMax OAuth (not logged in)
  ✓ codex CLI

◆ Directory Structure
  ✓ ~/.shay directory exists
  ✓ ~/.shay/cron/ exists
  ✓ ~/.shay/sessions/ exists
  ✓ ~/.shay/logs/ exists
  ✓ ~/.shay/skills/ exists
  ✓ ~/.shay/memories/ exists
  ✓ ~/.shay/SOUL.md exists (persona configured)
  ✓ ~/.shay/memories/ directory exists
  ✓ MEMORY.md exists (2139 chars)
  ✓ USER.md exists (1375 chars)
  ✓ ~/.shay/state.db exists (62 sessions)

◆ Command Installation
  ✓ Venv entry point exists (.venv/bin/shay)
  ✓ ~/.local/bin/shay → correct target

◆ External Tools
  ✓ git
  ✓ ripgrep (rg) (faster file search)
  ⚠ docker not found (optional)
  ✓ Node.js
  ✓ agent-browser (Node.js) (browser automation)
  ✓ Playwright Chromium (browser engine)
  ✓ Browser tools (agent-browser) deps (1 moderate vulnerability)

◆ API Connectivity
  Running 25 connectivity checks in parallel…
                                                                      
  ✓ OpenRouter API

◆ Submodules
  ⚠ tinker-atropos not found (run: git submodule update --init --recursive)

◆ Tool Availability
  ✓ browser
  ✓ clarify
  ✓ code_execution
  ✓ cronjob
  ✓ terminal
  ✓ delegation
  ✓ file
  ✓ image_gen
  ✓ memory
  ✓ moa
  ✓ session_search
  ✓ skills
  ✓ todo
  ✓ tts
  ✓ vision
  ✓ video
  ✓ kanban (runtime-gated; loaded only for dispatcher-spawned workers)
  ⚠ browser-cdp (system dependency not met)
  ⚠ computer_use (system dependency not met)
  ⚠ discord (missing DISCORD_BOT_TOKEN)
  ⚠ discord_admin (missing DISCORD_BOT_TOKEN)
  ⚠ feishu_doc (system dependency not met)
  ⚠ feishu_drive (system dependency not met)
  ⚠ homeassistant (system dependency not met)
  ⚠ rl (missing TINKER_API_KEY, WANDB_API_KEY)
  ⚠ messaging (system dependency not met)
  ⚠ web (missing EXA_API_KEY, PARALLEL_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY, FIRECRAWL_API_URL, FIRECRAWL_GATEWAY_URL, TOOL_GATEWAY_DOMAIN, TOOL_GATEWAY_SCHEME, TOOL_GATEWAY_USER_TOKEN)
  ⚠ shay-yuanbao (system dependency not met)
  ⚠ spotify (system dependency not met)

◆ Skills Hub
  ⚠ Skills Hub directory not initialized (run: shay skills list)
  ⚠ No GITHUB_TOKEN (60 req/hr rate limit — set in ~/.shay/.env for better rates)

◆ Memory Provider
  ✓ Built-in memory active (no external provider configured — this is fine)

────────────────────────────────────────────────────────────
  Found 1 issue(s) to address:

  1. Run 'shay setup' to configure missing API keys for full tool access

  Tip: run 'shay doctor --fix' to auto-fix what's possible.

__EXIT__:0
```

## Verification notes
- `SOUL.md` placeholder exact match: yes.
- `git remote -v` output: empty / no remote configured.
- `git status --short` before this report rewrite was: clean.
- Telegram bot token is present in inherited config, but no Telegram home channel or recent bot chat was discoverable from local state/getUpdates during notification setup; the completion notice is therefore delivered in the active conversation, and the report records the Telegram delivery limitation honestly.

## Next step for Fritz
Drop `SHAY-IDENTITY-2026-05-19.md` into `~/famtastic/shay-shay/SOUL.md`, then run `shay` for her first wake.
