# Hermes Live Wrapper Forwarder Validation Packet

Date: 2026-06-13
Status: proposal only — do not execute without Fritz approval
Scope: narrow live wrapper validation and rollback packet for `~/.local/bin/hermes`

## Purpose

Define the exact future live validation steps for replacing the current direct legacy Hermes wrapper target with a deprecation-warning forwarder to `shay`.

This packet does not authorize the change.
It only prepares the validation shape.

## Current Wrapper Behavior

Current live wrapper behavior:
- file: `~/.local/bin/hermes`
- current content shape:
  - `#!/usr/bin/env bash`
  - `unset PYTHONPATH`
  - `unset PYTHONHOME`
  - `exec "/Users/famtasticfritz/.shay/hermes-agent/venv/bin/hermes" "$@"`

Current operational meaning:
- the wrapper bypasses the `shay` entrypoint entirely
- the wrapper is directly coupled to the legacy `~/.shay/hermes-agent` backing tree
- any later deletion or retargeting of that tree is unsafe until the wrapper strategy is changed

## Proposed Future Behavior

Future wrapper should:
- print a one-line deprecation warning to stderr
- `exec shay "$@"`
- preserve args exactly
- preserve exit code from `shay`
- fail clearly if `shay` is missing from PATH
- keep `unset PYTHONPATH` and `unset PYTHONHOME`

Recommended warning text:
- `hermes is deprecated; forwarding to shay`

## Exact Proposed Wrapper Content

```bash
#!/usr/bin/env bash
set -euo pipefail
unset PYTHONPATH
unset PYTHONHOME

if ! command -v shay >/dev/null 2>&1; then
  echo "hermes compatibility wrapper: 'shay' not found on PATH" >&2
  exit 127
fi

echo "hermes is deprecated; forwarding to shay" >&2
exec shay "$@"
```

## Backup Command

Before any future approved replacement:
```bash
cp ~/.local/bin/hermes ~/.local/bin/hermes.backup-2026-06-13
chmod +x ~/.local/bin/hermes.backup-2026-06-13
```

## Validation Checks

Minimum checks for a future approved live run:

1. PATH / target truth
```bash
command -v shay
command -v hermes
```

2. Canonical entrypoint sanity
```bash
shay --help >/tmp/shay-help.out 2>/tmp/shay-help.err
```

3. Backed-up wrapper exists
```bash
test -x ~/.local/bin/hermes.backup-2026-06-13
```

4. New wrapper help path
```bash
hermes --help >/tmp/hermes-help.out 2>/tmp/hermes-help.err
```
Expected:
- stderr contains deprecation warning
- command exits successfully

5. Exit-code preservation check
```bash
hermes --definitely-not-a-real-flag >/tmp/hermes-badflag.out 2>/tmp/hermes-badflag.err; echo $?
shay --definitely-not-a-real-flag >/tmp/shay-badflag.out 2>/tmp/shay-badflag.err; echo $?
```
Expected:
- failure class matches
- exit status is effectively preserved

6. Known subcommand sanity
```bash
hermes gateway --help >/tmp/hermes-gateway-help.out 2>/tmp/hermes-gateway-help.err
shay gateway --help >/tmp/shay-gateway-help.out 2>/tmp/shay-gateway-help.err
```
Expected:
- both succeed or fail in matching ways that do not indicate wrapper regression

7. Desktop dependency sanity
```bash
shay desktop --help >/tmp/shay-desktop-help.out 2>/tmp/shay-desktop-help.err
hermes desktop --help >/tmp/hermes-desktop-help.out 2>/tmp/hermes-desktop-help.err
```
Expected:
- if `shay desktop` is valid, `hermes desktop` should mirror it through the wrapper
- if invalid, stop and roll back

## Rollback Command

If any future approved live validation fails:
```bash
cp ~/.local/bin/hermes.backup-2026-06-13 ~/.local/bin/hermes
chmod +x ~/.local/bin/hermes
```

## Risks

- `shay desktop` may not be semantically equivalent to `hermes desktop`
- human habit or ad hoc scripts may rely on legacy behavior not yet captured in automation
- PATH differences between interactive and service-like contexts could make `shay` resolution inconsistent
- wrapper stderr warning could affect brittle scripts that parse stderr too aggressively

## Approval Question

Approve a future narrow live validation packet for replacing `~/.local/bin/hermes` with a deprecation-warning forwarder to `shay`?

Recommended answer:
- yes, but only as a separate live-approved step after the first clean docs PR path is settled

## Bottom Line

This is a safety packet, not an execution packet.
The wrapper stays untouched until Fritz says yes.