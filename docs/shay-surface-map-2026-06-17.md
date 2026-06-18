# Shay Surface Map

Date: 2026-06-17
Status: live cutover truth

## Canonical local surfaces

### 1. Shay Desktop
- App path: `/Applications/Shay Desktop.app`
- Desktop shortcut: `/Users/famtasticfritz/Desktop/Shay Desktop.app`
- Runtime home: `/Users/famtasticfritz/.shay`
- CLI bridge: `/Users/famtasticfritz/.local/bin/shay`
- Runtime source root: `/Users/famtasticfritz/famtastic/shay-shay`
- Embedded dashboard URL: `http://127.0.0.1:9120`
- Dashboard auth: `X-Hermes-Session-Token` using the fixed local token carried by the app bundle for Workspace integration

### 2. Shay Workspace
- App path: `/Users/famtasticfritz/Desktop/Shay Workspace.app`
- Runtime home: `/Users/famtasticfritz/.shay`
- Gateway health URL: `http://127.0.0.1:8642/health`
- Dashboard URL: `http://127.0.0.1:9120/api/status`
- Behavior: optional companion surface; consumes the Desktop-hosted dashboard plus the shared gateway runtime

### 3. Standalone browser dashboard
- Command: `shay dashboard`
- Default URL: `http://127.0.0.1:9119`
- Status: keep as an optional lightweight browser-only surface, not the primary local app surface

## What changed in this cutover
- Shay Desktop now prefers a fixed local port when available and can honor an injected dashboard session token instead of generating a random one every launch.
- Desktop and desktop shortcut were both replaced from the freshly rebuilt app bundle so the icon-launch path matches the live runtime.
- Shay Workspace was rewired to the shared Shay runtime and patched to read dashboard URL/token from environment so it can attach to the Desktop-hosted dashboard.
- Workspace health checks now send the dashboard session token when probing the Desktop-hosted dashboard on port 9120.

## Live proof captured
- Desktop launched from `/Users/famtasticfritz/Desktop/Shay Desktop.app` and `.shay/logs/desktop.log` reported `Hermes Web UI → http://127.0.0.1:9120`.
- Dashboard status returned HTTP 200 at `http://127.0.0.1:9120/api/status`.
- Shared gateway health returned HTTP 200 at `http://127.0.0.1:8642/health`.
- Shay Workspace advanced past the onboarding prompt into the main application shell after the dashboard token/header patch.

## Known gaps
- The visible product strings inside the desktop/workspace shells still say `Hermes` in multiple places. Runtime wiring is cut over; brand text cleanup is still separate.
- The standalone `shay dashboard` docs still describe 9119 as the single local dashboard unless updated to mention the Desktop-hosted 9120 surface.
- Workspace changes were patched directly in the local app bundle. If that app is rebuilt from its own source later, the same environment-aware dashboard URL/token logic must exist there too.
