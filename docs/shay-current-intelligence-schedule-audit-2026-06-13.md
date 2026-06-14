# Shay current intelligence schedule audit — 2026-06-13

Scope: read-only audit of current automatic intelligence/scheduler surfaces for the HyperSwarm mission. No launchd, cron, or live config changes were made.

## Executive read

Current automatic intelligence is split across two families:

1. Shay/phone/memory automation
   - `ai.shay.memory-reflect`
   - `com.famtastic.shay-lessons-sync`
   - `com.shay.dailybrief`
2. Legacy/general intelligence cron
   - `scripts/intelligence-loop`
   - `research/repo-intelligence/run-analysis.sh`

Net result:
- Reflection is active and appears healthy.
- Lessons sync is active and high-frequency; it mirrors knowledge but does not analyze patterns.
- Daily brief is configured but currently unhealthy/safe-disabled in practice; last launchd exit code is `7` and its last log update is `2026-06-10 08:00:01`.
- Shay internal cron registry exists at `~/.shay/cron/jobs.json`, but all 10 recorded jobs are currently `enabled: false`.
- There is no watcher-state directory at `~/.shay/watcher-state`, so there is no evidence of a currently deployed process watcher/pattern scanner control plane.

## Evidence inspected

- Mission authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`
- User launch agents:
  - `~/Library/LaunchAgents/ai.shay.memory-reflect.plist`
  - `~/Library/LaunchAgents/com.famtastic.shay-lessons-sync.plist`
  - `~/Library/LaunchAgents/com.shay.dailybrief.plist`
- Launchd runtime state via `launchctl print gui/$(id -u)/...`
- User crontab via `crontab -l`
- Shay config: `~/.shay/config.yaml`
- Shay cron registry: `~/.shay/cron/jobs.json`
- Runtime artifacts/logs:
  - `/tmp/shay-memory-reflect.log`
  - `/tmp/shay-lessons-sync.log`
  - `/tmp/shay-dailybrief.log`
  - `~/.shay/events.jsonl`
  - `~/famtastic/shay-phone/asks/`
- Source implementations:
  - `~/famtastic/obsidian/Shay-Memory/_system/reflect.py`
  - `~/famtastic/shay-agent-os/sync_lessons_to_shay.py`
  - `~/famtastic/shay-phone/server.py`
  - `scripts/intelligence-loop`
  - `research/repo-intelligence/run-analysis.sh`
  - `research/repo-intelligence/analyze_repo.py`

## Current automatic schedules

| Surface | Auto-runs now | Cadence | Active state | Writes to | Safe? | Captures process metadata? | Analyzes patterns? | Notes |
|---|---|---:|---|---|---|---|---|---|
| `ai.shay.memory-reflect` | yes | daily at 03:00 | loaded; last exit `0`; not currently running | `Shay-Memory/reflections/episodic/YYYY-MM-DD.md`, `semantic/YYYY-MM-DD.md`, `reflective/YYYY-MM-DD.md`; log `/tmp/shay-memory-reflect.log` | mostly yes | not process metadata; reflects notes | weakly; reflective synthesis over notes, not process telemetry | latest log mtime `2026-06-13T03:00:05` |
| `com.famtastic.shay-lessons-sync` | yes | every 1800s, RunAtLoad true | loaded; last exit `0`; not currently running between intervals | `Shay-Memory/lessons-mirror/*`; log `/tmp/shay-lessons-sync.log` | yes, but chatty/high-frequency | no | no | mirrors `.wolf`/repo docs into indexed vault |
| `com.shay.dailybrief` | configured yes | daily at 08:00 | loaded; last exit `7`; not currently running | phone asks, `~/.shay/events.jsonl`, `/tmp/shay-dailybrief.log` | currently not safe enough for autonomy | yes; agent status + PIDs in brief payload | no | repeated ask creation behavior observed in events log |
| Shay internal cron registry | not running now | n/a | 10 jobs recorded, all disabled | `~/.shay/cron/jobs.json` | yes, because disabled | mixed, depends on job | mixed | no active internal jobs |
| crontab: `scripts/intelligence-loop` | yes | Mon/Wed/Fri 09:00 | active by crontab; latest log mtime `2026-06-12T09:00:00` | `~/PENDING-REVIEW.md`, `~/.famtastic-intel-loop.log` | mostly yes | no | yes, cross-site finding aggregation | not Shay-native but part of current auto intelligence estate |
| crontab: `repo-intelligence/run-analysis.sh` | yes | hourly | active by crontab; output log path currently missing | `research/repo-intelligence/completed/*.json`, `reports/batch_*.md`, pending batch mutation | mostly yes | repo metadata, not local process metadata | yes, keyword/score-based tech-stack analysis | external GitHub/repo intelligence loop |

## Launch agent details

### `ai.shay.memory-reflect`
- Label: `ai.shay.memory-reflect`
- Schedule: `StartCalendarInterval { Hour: 3, Minute: 0 }`
- Program: `/usr/bin/python3 ~/famtastic/obsidian/Shay-Memory/_system/reflect.py`
- Runtime state: `state = not running`, `last exit code = 0`
- Log evidence shows successful daily writes through `2026-06-13`.

What it writes:
- Daily L1/L2/L3 reflection notes under `~/famtastic/obsidian/Shay-Memory/reflections/`
- Example destinations from the live log:
  - `reflections/episodic/2026-06-13.md`
  - `reflections/semantic/2026-06-13.md`
  - `reflections/reflective/2026-06-13.md`

Safety assessment:
- Safe as batch note synthesis.
- It reads the vault broadly and can include large recent note sets (`263 source note(s)` on `2026-06-12`), but does not mutate system state outside the vault/log.

Metadata/pattern assessment:
- Does not inspect live processes.
- Performs memory-layer summarization and reflective synthesis over note content, so it is a content-reflection mechanism, not a process watcher.

### `com.famtastic.shay-lessons-sync`
- Label: `com.famtastic.shay-lessons-sync`
- Schedule: `StartInterval 1800`, `RunAtLoad true`
- Program: `/usr/bin/python3 ~/famtastic/shay-agent-os/sync_lessons_to_shay.py`
- Runtime state: `state = not running`, `last exit code = 0`
- Latest log mtime: `2026-06-13T11:46:13`

What it writes:
- `~/famtastic/obsidian/Shay-Memory/lessons-mirror/cerebrum-mirror.md`
- `~/famtastic/obsidian/Shay-Memory/lessons-mirror/buglog-mirror.md`
- mirrored repo docs into the same vault area

Safety assessment:
- Safe mirroring job.
- No evidence of command execution against arbitrary targets; it copies known local knowledge sources into the Shay vault.

Metadata/pattern assessment:
- No local process metadata capture.
- No pattern analysis; this is sync/index hydration only.
- Risk is drift/noise, not autonomy overreach.

### `com.shay.dailybrief`
- Label: `com.shay.dailybrief`
- Schedule: `StartCalendarInterval { Hour: 8, Minute: 0 }`
- Program: `/bin/sh -c curl -s -H "X-Shay-Token: $(cat ~/famtastic/shay-phone/.token)" http://localhost:8787/api/daily-brief`
- Runtime state: `state = not running`, `last exit code = 7`
- Latest log mtime: `2026-06-10T08:00:01`

What it writes:
- phone ask JSON files under `~/famtastic/shay-phone/asks/`
- command events in `~/.shay/events.jsonl`
- log at `/tmp/shay-dailybrief.log`

Observed behavior and risk:
- `server.py` shows `create_ask()` writes JSON ask files and emits events.
- Live ask directory currently contains 491 JSON files.
- `~/.shay/events.jsonl` shows repeated `kind: daily_brief` ask creation events within short windows, indicating historical ask-storm behavior.
- `/tmp/shay-dailybrief.log` includes agent labels/statuses and PIDs in the brief payload.

Safety assessment:
- Not safe enough to expand as-is for HyperSwarm autonomy.
- It is not just informative; it creates approval artifacts and can spam asks/events when the surrounding phone service path is unhealthy or looped.

Metadata/pattern assessment:
- Yes, it captures process metadata in the brief payload: agent status and PID snapshots.
- No durable pattern analysis; it snapshots status and generates asks, but does not score trends or gate on repeated anomalies.

## Shay config and scheduler posture

From `~/.shay/config.yaml`:
- `memory.memory_enabled: true`
- `memory.user_profile_enabled: true`
- `context.engine: compressor`
- `curator.enabled: true`
- `curator.interval_hours: 168`
- `approvals.cron_mode: deny`
- `cron.wrap_response: true`
- `delegation.orchestrator_enabled: true`
- `delegation.subagent_auto_approve: false`

Interpretation:
- Memory and context compression are enabled.
- Weekly curation exists conceptually, but this audit did not find a corresponding live watcher control plane for process intelligence.
- Cron-triggered approval posture is conservative (`deny`), which is good for safety.
- Orchestrator/delegation is enabled, but autonomous scheduling is not equivalent to autonomous approval.

## Shay internal cron registry

`~/.shay/cron/jobs.json` contains 10 jobs, but all are `enabled: false`.
Examples include:
- `seed-research-rotation`
- `Honcho decision brief`
- `API Usage Watchdog`
- `3AM Repo Evaluation & Install`
- `poe-scrape`
- `poe-daily-summary`
- `hosting-facelift-heartbeat`

Assessment:
- There is scheduler inventory, but no active Shay-native recurring jobs at this moment.
- This is good for the current mission because it means watcher design can be specified cleanly without live scheduler entanglement.

## Existing docs / memory reflection / session summaries / run logs

Found live evidence of:
- daily reflection notes under `Shay-Memory/reflections/{episodic,semantic,reflective}/`
- session summaries under `Shay-Memory/reflections/episodic/sessions/`
- mirrored lessons under `Shay-Memory/lessons-mirror/`
- runtime event log `~/.shay/events.jsonl`

Important distinction:
- Session memos do capture some runtime metadata, but only at session/document boundary. Example live session memo frontmatter includes:
  - `session_id`
  - `started_at`
  - `ended_at`
  - `project`
  - `model`
  - `memo_schema: handoff-v1`
- That is useful provenance, but it is not a continuously running watcher or run ledger.

## What currently runs automatically

Definitely active on the machine today:
- memory reflection at 03:00 daily
- lessons sync every 30 minutes and at load
- legacy FAMtastic intelligence loop Mon/Wed/Fri at 09:00
- hourly repo-intelligence analysis cron

Configured but unhealthy / not producing healthy autonomous behavior:
- daily brief at 08:00

Configured inventory but not active:
- all jobs in `~/.shay/cron/jobs.json`

## What is missing

1. No watcher control plane
- No `~/.shay/watcher-state/` directory
- No observed watcher checkpoints, leases, suppression windows, or review queue artifacts

2. No process-intelligence ledger
- No durable run ledger linking watcher observations to reviews, asks, escalations, and resolved outcomes

3. No pattern scanner with safety gates
- Nothing currently scores repeated failures, ask storms, stale jobs, or abnormal churn before escalating

4. No dedupe / cooldown around daily brief asks
- Live event history shows repeated daily-brief ask creation without visible throttling

5. No clear separation between observation and action
- Current automation either mirrors content, reflects content, or directly creates asks; there is no middle layer that observes/processes patterns without activating downstream effects

6. No HyperSwarm watcher controls document
- Needed: enablement gates, write scope, suppression, escalation policy, and human-review boundary

## Audit conclusion

Current estate is strong on memory reflection and knowledge mirroring, weak on safe watcher autonomy.

If HyperSwarm needs process intelligence without enabling anything yet, the immediate design target should be:
- read-only watcher signals
- append-only ledgers
- deduped review packet generation
- zero direct launchctl/cron/job mutation from the watcher itself
- explicit human-controlled promotion path from observe -> review -> approved automation
