# Shay runtime surface audit — 2026-06-17

## Observation
- `/Applications/Shay Desktop.app` exists and is a small wrapper-style app bundle (`Contents/MacOS/Shay Desktop` is 52,800 bytes).
- `/Applications/ShayDesktop.app` also exists and is a separate Electron bundle whose `Info.plist` still points at `CFBundleExecutable=HermesDesktop` and version `0.8.1`.
- `~/.local/bin/shay-desktop` is a shell wrapper that exports `HERMES_HOME=/Users/famtasticfritz/.shay` and then executes `hermes desktop`.
- The canonical upstream desktop source is present locally at `/Users/famtasticfritz/.hermes/hermes-agent/apps/desktop/` on commit `59510d7b4`.
- Upstream Hermes desktop already supports sharing a single runtime root via `HERMES_HOME` and launches the backend with `hermes dashboard --no-open --tui --host 127.0.0.1 --port <port>` from `apps/desktop/electron/main.cjs`.
- `shay-workspace/.env` and `shay-web/.env` are already pointed at `HERMES_HOME=/Users/famtasticfritz/.shay`, so the common runtime root is aligned there already.
- Workspace currently targets Shay services directly: gateway `127.0.0.1:8642`, dashboard `127.0.0.1:9119`, token `shay-workspace-local-dev-token`.
- Shay Web currently targets the same `~/.shay` root and gateway `127.0.0.1:8642`.

## Interpretation
- The cleanest cutover path is to stop relying on the tiny wrapper-style Shay Desktop app and instead build a rebranded app directly from the local `NousResearch/hermes-agent` desktop source, with the runtime pointed at `~/.shay`.
- Workspace and Web do not need a runtime-home rewrite first; they need validation and, if necessary, a lighter wiring cleanup after desktop is stabilized.
- There is naming drift across installed surfaces (`Shay Desktop.app` vs `ShayDesktop.app` vs wrapper scripts) that should be collapsed into one canonical desktop surface.
