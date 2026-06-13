# Hermes Wrapper Forwarding Plan

Date: 2026-06-13
Status: proposal only; do not install from this doc
Scope: `~/.local/bin/hermes` end-state recommendation only

## Executive Recommendation

Recommended end state right now:
- Option 4 wins: replace `~/.local/bin/hermes` with a deprecation-warning forwarder to `shay`
- But not yet. First approval should cover the wrapper change itself.

Why Option 4 wins:
- Option 1 `remove entirely` is too aggressive because live external dependencies still exist.
- Option 2 `keep temporarily as compatibility wrapper` is safer than removal, but preserves direct coupling to the legacy `~/.shay/hermes-agent` tree.
- Option 3 `replace with forwarding shim to shay` is directionally right, but too silent; Fritz should get a clean transition signal.
- Option 5 `keep indefinitely as compatibility sugar` is too permissive and risks freezing Hermes naming forever.

So the safest honest target is:
1. keep the wrapper for compatibility
2. stop pointing it at `~/.shay/hermes-agent/venv/bin/hermes`
3. forward into `shay`
4. print a short deprecation notice on stderr
5. preserve exit codes and passthrough args

## Current State

Current wrapper content:
- `#!/usr/bin/env bash`
- `unset PYTHONPATH`
- `unset PYTHONHOME`
- `exec "/Users/famtasticfritz/.shay/hermes-agent/venv/bin/hermes" "$@"`

Current risk:
- the wrapper is tied directly to a legacy backing tree
- it bypasses the Shay CLI entrypoint entirely
- any future removal or restructuring of `~/.shay/hermes-agent` can break callers immediately

## Recommended Wrapper Behavior

Behavior requirements:
- keep command name `hermes` available for now
- print a one-line deprecation warning to stderr
- prefer `shay` as the canonical target
- preserve existing args exactly
- preserve exit status from `shay`
- fail clearly if `shay` is not available on PATH
- remain shell-simple for rollback

Recommended runtime behavior:
1. unset `PYTHONPATH` and `PYTHONHOME` like the current wrapper does
2. verify `shay` is on PATH
3. print: `hermes is deprecated; forwarding to shay` to stderr
4. `exec shay "$@"`

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

## Why This Shape Is Safest

- It removes direct dependence on `~/.shay/hermes-agent/venv/bin/hermes`.
- It keeps the user habit and automation entrypoint alive during transition.
- It keeps `shay` as the canonical executable without deleting Hermes prematurely.
- It gives a visible signal without being noisy or interactive.
- It is fully reversible with one file restore.

## Known Constraints / Caveats

- `~/.local/bin/shay-desktop` currently runs `exec hermes desktop "$@"` and exports `HERMES_HOME=~/.shay`.
  - This is okay if `hermes` forwards cleanly to `shay` and `shay desktop` is valid.
  - It is not okay if `shay desktop` is unsupported or semantically different.
- This wave did not execute `shay desktop` for behavioral proof because runtime mutation/execution beyond read-only inspection was out of scope.
- If `shay` and `hermes` currently parse subcommands differently for some edge cases, the wrapper must be tested before live installation.

## Rollback Plan

If a future approved live wrapper change causes any regression:
1. restore the previous wrapper file content exactly
2. confirm `hermes --help` works again
3. confirm any known consumer such as `shay-desktop` works again
4. defer further changes until the mismatched command behavior is mapped

Rollback target content:
```bash
#!/usr/bin/env bash
unset PYTHONPATH
unset PYTHONHOME
exec "/Users/famtasticfritz/.shay/hermes-agent/venv/bin/hermes" "$@"
```

## Validation Checklist

Before installing a live forwarder, validate:
- [ ] `command -v shay` resolves in the same runtime context used by the wrapper
- [ ] `shay --help` succeeds
- [ ] `hermes --help` through the new wrapper succeeds
- [ ] `hermes gateway status` preserves expected behavior, if that command is still relied on
- [ ] `hermes desktop` behaves acceptably or a compensating `shay-desktop` update is prepared
- [ ] no launch agent or automation still relies on legacy direct-path behavior
- [ ] rollback content is saved before replacement

## Approval Question

Approve later live change to `~/.local/bin/hermes` from a direct legacy-binary exec to a deprecation-warning forwarding shim into `shay`?

Recommended answer: yes, but only after a narrow live validation packet is approved.

## Bottom Line

Do not remove `hermes`.
Do not keep the current direct legacy target forever.
When approved, convert it into a deprecation-warning forwarder to `shay` and let that bridge the transition.