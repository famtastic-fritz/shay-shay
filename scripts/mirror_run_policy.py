#!/usr/bin/env python3
"""Mirror the resolved run-policy to the Obsidian vault.

Regenerates ``Shay-Memory/_system/run-policy.resolved.md`` from the live
policy the router reads, so the browsable view always reflects real routing
behavior. Run from the repo root with the project venv:

    .venv/bin/python scripts/mirror_run_policy.py
"""

from __future__ import annotations

import datetime
import pathlib
import sys

# Ensure repo root on path when invoked directly.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shay_cli import run_router  # noqa: E402

SAMPLES = [
    "build these 10 screens",
    "swarm 10 research tasks",
    "fix the login bug",
    "update these 3 docs",
]

VAULT_DEST = (
    pathlib.Path.home()
    / "famtastic/obsidian/Shay-Memory/_system/run-policy.resolved.md"
)


def build_doc() -> str:
    src = run_router.policy_path()
    policy = run_router.load_policy(src)
    raw = pathlib.Path(src).read_text()

    blocks = [
        run_router.render_plan(
            run_router.select_run(s, policy=policy), policy_src=src.name
        )
        for s in SAMPLES
    ]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    samples_text = ("\n" + "-" * 60 + "\n").join(blocks)
    return f"""---
title: run-policy.resolved
type: note
permalink: shay-memory/_system/run-policy-resolved
tags: [run-model, run-policy, resolved, generated]
---

# Run Policy (resolved) — browsable mirror

> GENERATED — do not hand-edit. Mirrors the machine source-of-truth
> `run-policy.yaml` that the router (`shay_cli/run_router.py`) actually reads,
> so the Obsidian view always reflects live routing behavior.
>
> Regenerate: `cd ~/famtastic/shay-shay && .venv/bin/python scripts/mirror_run_policy.py`
> Canonical model: [[run-model|RUN-MODEL]]

- Resolved from: `{src}`
- Router mode: **{policy.get('mode')}** (advisory — recommends, never hijacks an explicit request)
- Generated: {now}

## Sample routing decisions (what `shay run-plan` prints)

These are produced by feeding the policy through the router — proof the
definitions drive behavior, not just describe it.

```
{samples_text}
```

## Active policy (verbatim run-policy.yaml)

```yaml
{raw.rstrip()}
```
"""


def main() -> int:
    doc = build_doc()
    VAULT_DEST.parent.mkdir(parents=True, exist_ok=True)
    VAULT_DEST.write_text(doc)
    print(f"wrote {VAULT_DEST} ({len(doc)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
