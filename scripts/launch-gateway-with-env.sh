#!/bin/bash
set -euo pipefail

SHAY_HOME="${SHAY_HOME:-$HOME/.shay}"
ENV_EXPORTS="$SHAY_HOME/.env.launchctl.exports"

python3 - <<'PY' > "$ENV_EXPORTS"
from pathlib import Path
import shlex
import os

home = Path(os.environ.get('SHAY_HOME', str(Path.home() / '.shay')))
for name in ['.env', '.env.local']:
    path = home / name
    if not path.exists():
        continue
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        print(f'export {key}={shlex.quote(value)}')
PY

# shellcheck disable=SC1090
source "$ENV_EXPORTS"
rm -f "$ENV_EXPORTS"

cd /Users/famtasticfritz/famtastic/shay-shay
exec /Users/famtasticfritz/famtastic/shay-shay/.venv/bin/python -m shay_cli.main gateway run --replace
