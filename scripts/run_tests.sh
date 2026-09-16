#!/usr/bin/env bash
# Canonical test runner for shay-shay. Run this instead of calling
# `pytest` directly to guarantee your local run matches CI behavior.
#
# What this script enforces:
#   * -n 4 xdist workers (CI has 4 cores; -n auto diverges locally)
#   * TZ=UTC, LANG=C.UTF-8, PYTHONHASHSEED=0 (deterministic)
#   * Credential env vars blanked (conftest.py also does this, but this
#     is belt-and-suspenders for anyone running `pytest` outside of
#     our conftest path — e.g. calling pytest on a single file)
#   * Proper venv activation
#
# Usage:
#   scripts/run_tests.sh                     # full suite
#   scripts/run_tests.sh tests/agent/        # one directory
#   scripts/run_tests.sh tests/agent/test_foo.py::TestClass::test_method
#   scripts/run_tests.sh --tb=long -v        # pass-through pytest args

set -euo pipefail

E2E_MODE=0
if [ "${1:-}" = "--e2e" ]; then
  E2E_MODE=1
  shift
fi

die() {
  echo "error: $*" >&2
  exit 1
}

# ── Locate repo root ────────────────────────────────────────────────────────
# Works whether this is the main checkout or a worktree.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OWNER_HOME="$(python3 -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
OWNER_PROFILE="$OWNER_HOME/.shay"

# ── Resolve and validate the Python environment ────────────────────────────
# An explicit pair is mandatory for E2E and is also honored in default mode.
# With no pair, retain ordinary developer venv discovery.
if [ -n "${SHAY_TEST_PYTHON:-}" ] || [ -n "${SHAY_TEST_ENV_PROVENANCE:-}" ]; then
  [ -n "${SHAY_TEST_PYTHON:-}" ] && [ -n "${SHAY_TEST_ENV_PROVENANCE:-}" ] \
    || die "SHAY_TEST_PYTHON and SHAY_TEST_ENV_PROVENANCE must be supplied together"
  PYTHON="$SHAY_TEST_PYTHON"
  PROVENANCE="$SHAY_TEST_ENV_PROVENANCE"
  REQUIRE_PY311=1
elif [ "$E2E_MODE" -eq 1 ]; then
  die "--e2e requires absolute SHAY_TEST_PYTHON and SHAY_TEST_ENV_PROVENANCE"
else
  REQUIRE_PY311=0
  VENV=""
  for candidate in "$REPO_ROOT/.venv" "$REPO_ROOT/venv" "$HOME/.shay/shay-shay/venv"; do
    if [ -f "$candidate/bin/activate" ]; then
      VENV="$candidate"
      break
    fi
  done
  [ -n "$VENV" ] || die "no virtualenv found in $REPO_ROOT/.venv or $REPO_ROOT/venv"
  PYTHON="$VENV/bin/python"
fi

case "$PYTHON" in /*) ;; *) die "SHAY_TEST_PYTHON must be an absolute path" ;; esac
[ -f "$PYTHON" ] || die "Python interpreter does not exist: $PYTHON"
[ -x "$PYTHON" ] || die "Python interpreter is not executable: $PYTHON"
PYTHON_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$PYTHON")"
case "$PYTHON_REAL" in
  "$REPO_ROOT"/*|"$OWNER_PROFILE"/*|"$OWNER_HOME/.local/share/shay-agent-enhancement-2026-09-13/python311"/*|"$OWNER_HOME/Documents/Codex/2026-09-12/shay-assistant-read-only-review/test-envs/python311"/*)
    die "Python interpreter is in a forbidden path: $PYTHON_REAL" ;;
esac
PYTHON_VERSION="$("$PYTHON" -c 'import platform; print(platform.python_version())')"
if [ "$REQUIRE_PY311" -eq 1 ]; then
  case "$PYTHON_VERSION" in 3.11.*) ;; *) die "Python 3.11 is required (got $PYTHON_VERSION)" ;; esac
fi

if [ -n "${PROVENANCE:-}" ]; then
  case "$PROVENANCE" in /*) ;; *) die "SHAY_TEST_ENV_PROVENANCE must be an absolute path" ;; esac
  [ -f "$PROVENANCE" ] || die "provenance file does not exist: $PROVENANCE"
  PROVENANCE_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$PROVENANCE")"
  case "$PROVENANCE_REAL" in
    "$REPO_ROOT"/*|"$OWNER_PROFILE"/*|"$OWNER_HOME/.local/share/shay-agent-enhancement-2026-09-13/python311"/*|"$OWNER_HOME/Documents/Codex/2026-09-12/shay-assistant-read-only-review/test-envs/python311"/*)
      die "provenance file is in a forbidden path: $PROVENANCE_REAL" ;;
  esac
  "$PYTHON" - "$REPO_ROOT" "$PYTHON" "$PROVENANCE" <<'PY'
import hashlib, json, os, pathlib, re, stat, subprocess, sys
repo, interpreter, marker = map(pathlib.Path, sys.argv[1:])
st = os.lstat(marker)
if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or
        st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o400):
    raise SystemExit("provenance must be a mode-0400 regular file owned by the effective user")
def pairs(items):
    d = {}
    for key, value in items:
        if key in d:
            raise ValueError("duplicate key: " + key)
        d[key] = value
    return d
try:
    raw = marker.read_bytes()
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
except Exception as exc:
    raise SystemExit(f"invalid provenance JSON: {exc}")
v4 = {"base_python_executable","base_python_sha256","install_command","pip_check_exit_code","pip_freeze_sha256","pyproject_sha256","python_executable","python_version","repository","reviewed_sha","schema_version"}
portable = {"dependency_lock_hashes","environment_kind","install_command","pip_check_exit_code","pyproject_sha256","python_executable","python_version","repository","reviewed_sha","schema_version"}
if not isinstance(obj, dict):
    raise SystemExit("provenance must be an object")
if type(obj.get("schema_version")) is int and obj["schema_version"] == 2 and set(obj) == v4:
    kind = "v4"
elif type(obj.get("schema_version")) is int and obj["schema_version"] == 1 and set(obj) == portable:
    kind = "portable"
else:
    raise SystemExit("unsupported provenance schema or additional/missing keys")
canonical = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()
if raw != canonical:
    raise SystemExit("provenance is not canonical JSON")
source_repository = "/Users/famtastic-fritz/Development/FAMtastic/shay-shay"
if obj["repository"] not in {str(repo), source_repository}:
    raise SystemExit("provenance repository mismatch")
if obj["python_executable"] != str(interpreter):
    raise SystemExit("provenance interpreter mismatch")
if not isinstance(obj["python_version"], str) or not re.fullmatch(r"3\.11\.\d+", obj["python_version"]):
    raise SystemExit("provenance Python version mismatch")
install_commands = {
    "python -m pip install -e '.[all,dev]'",
    "uv export --locked --all-extras --dev --format requirements.txt --no-emit-project --no-annotate && uv pip install --python \"$RUNNER_TEMP/shay-python/bin/python\" -e \".[all,dev]\" --constraint \"$RUNNER_TEMP/shay-constraints.txt\"",
}
if obj["install_command"] not in install_commands or type(obj["pip_check_exit_code"]) is not int or obj["pip_check_exit_code"] != 0:
    raise SystemExit("provenance install/dependency check mismatch")
digest = lambda b: hashlib.sha256(b).hexdigest()
for key in ("pyproject_sha256",):
    if not isinstance(obj[key], str) or not re.fullmatch(r"[0-9a-f]{64}", obj[key]):
        raise SystemExit("provenance digest is not canonical: " + key)
if not isinstance(obj["reviewed_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", obj["reviewed_sha"]):
    raise SystemExit("provenance reviewed SHA is invalid")
if digest((repo / "pyproject.toml").read_bytes()) != obj["pyproject_sha256"]:
    raise SystemExit("pyproject.toml differs from provenance")
reviewed = subprocess.check_output(["git", "-C", str(repo), "show", f"{obj['reviewed_sha']}:pyproject.toml"])
if digest(reviewed) != obj["pyproject_sha256"]:
    raise SystemExit("reviewed pyproject.toml differs from provenance")
if kind == "portable":
    if obj["environment_kind"] not in {"immutable_local", "ephemeral_ci"} or not isinstance(obj["dependency_lock_hashes"], dict) or not obj["dependency_lock_hashes"]:
        raise SystemExit("portable provenance lock/environment fields are invalid")
    for name, expected in obj["dependency_lock_hashes"].items():
        if not isinstance(name, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise SystemExit("portable provenance lock digest is invalid")
        path = pathlib.PurePosixPath(name)
        current = repo / path
        if path.is_absolute() or ".." in path.parts or not current.is_file() or current.is_symlink() or repo not in current.resolve().parents:
            raise SystemExit("dependency lock path escapes repository")
        if digest(current.read_bytes()) != expected:
            raise SystemExit("dependency lock differs from provenance: " + name)
        prior = subprocess.check_output(["git", "-C", str(repo), "show", f"{obj['reviewed_sha']}:{name}"])
        if digest(prior) != expected:
            raise SystemExit("reviewed dependency lock differs from provenance: " + name)
else:
    if not isinstance(obj["base_python_executable"], str):
        raise SystemExit("v4 base interpreter binding mismatch")
    base = pathlib.Path(obj["base_python_executable"])
    if not base.is_absolute() or not base.is_file() or base.is_symlink() or not isinstance(obj["base_python_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", obj["base_python_sha256"]) or digest(base.read_bytes()) != obj["base_python_sha256"]:
        raise SystemExit("v4 base interpreter binding mismatch")
    selected_target = pathlib.Path(os.path.realpath(interpreter))
    if not selected_target.is_file() or digest(selected_target.read_bytes()) != obj["base_python_sha256"]:
        raise SystemExit("v4 selected interpreter target mismatch")
    if subprocess.call([str(interpreter), "-m", "pip", "check"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        raise SystemExit("pip check failed")
    freeze = subprocess.check_output([str(interpreter), "-m", "pip", "freeze", "--all"], env={**os.environ, "LC_ALL":"C"})
    if digest(b"".join(sorted(freeze.splitlines(keepends=True)))) != obj["pip_freeze_sha256"]:
        raise SystemExit("pip freeze --all hash mismatch")
PY
fi

if [ "$E2E_MODE" -eq 1 ]; then
  # E2E callers must establish the disposable envelope before this script
  # starts pytest, imports Shay, or probes a live-profile plugin. Never
  # replace a missing or malformed path with a fallback that could hide an
  # isolation mistake.
  [ -n "${HOME:-}" ] && [ -n "${SHAY_HOME:-}" ] && \
    [ -n "${SHAY_PROMPT_MEMORY_VAULT:-}" ] || \
    die "--e2e requires HOME, SHAY_HOME, and SHAY_PROMPT_MEMORY_VAULT"
  [[ "$HOME" == /* ]] && [[ "$SHAY_HOME" == /* ]] && \
    [[ "$SHAY_PROMPT_MEMORY_VAULT" == /* ]] || \
    die "--e2e HOME, SHAY_HOME, and SHAY_PROMPT_MEMORY_VAULT must be absolute"
  # Resolve every envelope path and create it through held directory
  # descriptors.  Lexical prefix checks plus mkdir -p are insufficient: an
  # existing symlink (or a concurrent replacement) can redirect a supposedly
  # disposable run into the owner profile.  The helper rejects every existing
  # symlink component before mkdir and uses O_NOFOLLOW while walking/creating
  # each component, so the pathname cannot be redirected during setup.
  E2E_PATHS="$("$PYTHON" - "$HOME" "$SHAY_HOME" "$SHAY_PROMPT_MEMORY_VAULT" \
    "$REPO_ROOT" "$OWNER_PROFILE" "$OWNER_HOME" <<'PY'
import os
import pathlib
import stat
import sys

raw_home, raw_shay_home, raw_vault, raw_repo, raw_owner_profile, raw_owner_home = sys.argv[1:]

def fail(message: str):
    raise SystemExit("--e2e " + message)

def parse(raw: str, label: str) -> pathlib.Path:
    if not raw or not raw.startswith("/"):
        fail(f"{label} must be an absolute path")
    if any(char in raw for char in ("\x00", "\n", "|")):
        fail(f"{label} contains an unsupported control/delimiter character")
    path = pathlib.Path(raw)
    if ".." in path.parts:
        fail(f"{label} must not contain '..' path components")
    current = pathlib.Path(path.anchor)
    # Existing components are checked before any directory is created.  Once
    # an absent component is reached there can be no existing descendant
    # symlink; ensure_dir() below closes the remaining race with O_NOFOLLOW.
    for part in path.parts[1:]:
        current /= part
        try:
            entry = os.lstat(current)
        except FileNotFoundError:
            break
        except OSError as exc:
            fail(f"cannot inspect {label}: {exc}")
        if stat.S_ISLNK(entry.st_mode):
            fail(f"{label} contains a symlink component: {current}")
    try:
        resolved = path.resolve(strict=False)
    except OSError as exc:
        fail(f"cannot resolve {label}: {exc}")
    if resolved != path:
        fail(f"{label} resolves differently from its supplied path")
    return resolved

home = parse(raw_home, "HOME")
shay_home = parse(raw_shay_home, "SHAY_HOME")
vault = parse(raw_vault, "SHAY_PROMPT_MEMORY_VAULT")
repo = pathlib.Path(raw_repo).resolve()
owner_profile = pathlib.Path(raw_owner_profile).resolve()
owner_home = pathlib.Path(raw_owner_home).resolve()
run_root = home.parent

if run_root == pathlib.Path("/"):
    fail("run root may not be filesystem root")
if home.parent != run_root:
    fail("HOME must be a direct child of the run root")
for label, path in (("SHAY_HOME", shay_home), ("SHAY_PROMPT_MEMORY_VAULT", vault)):
    try:
        path.relative_to(run_root)
    except ValueError:
        fail(f"{label} must be below the HOME run root")
if len({home, shay_home, vault}) != 3:
    fail("HOME, SHAY_HOME, and SHAY_PROMPT_MEMORY_VAULT must be distinct")

for forbidden in (
    repo,
    owner_profile,
    owner_home / ".local" / "share" / "shay-agent-enhancement-2026-09-13",
    owner_home / "Documents" / "Codex" / "2026-09-12" / "shay-assistant-read-only-review" / "test-envs",
):
    if run_root == forbidden or forbidden in run_root.parents:
        fail(f"E2E run root is in a forbidden path: {run_root}")

def ensure_dir(path: pathlib.Path) -> None:
    """Create/open *path* without following symlinks in any component."""
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=fd,
                )
            except OSError as exc:
                fail(f"E2E path component is not a real directory: {path}: {exc}")
            os.close(fd)
            fd = child
    finally:
        os.close(fd)

for directory in (
    run_root,
    home,
    shay_home,
    vault,
    run_root / "tmp",
    run_root / "xdg-cache",
    run_root / "pip-cache",
    run_root / "uv-cache",
    run_root / "coverage",
    run_root / "logs",
):
    ensure_dir(directory)

print("|".join(str(path) for path in (run_root, home, shay_home, vault)))
PY
  )" || die "unable to establish a symlink-safe E2E envelope"
  IFS='|' read -r RUN_ROOT HOME SHAY_HOME SHAY_PROMPT_MEMORY_VAULT <<< "$E2E_PATHS"
  [ -n "$RUN_ROOT" ] && [ -n "$HOME" ] && [ -n "$SHAY_HOME" ] && \
    [ -n "$SHAY_PROMPT_MEMORY_VAULT" ] || \
    die "E2E envelope resolver returned incomplete paths"
  export TMPDIR="$RUN_ROOT/tmp"
  export XDG_CACHE_HOME="$RUN_ROOT/xdg-cache"
  export PIP_CACHE_DIR="$RUN_ROOT/pip-cache"
  export UV_CACHE_DIR="$RUN_ROOT/uv-cache"
  export COVERAGE_FILE="$RUN_ROOT/coverage/.coverage"
  unset SHAY_KANBAN_HOME SHAY_KANBAN_DB SHAY_KANBAN_WORKSPACES_ROOT \
    SHAY_KANBAN_BOARD SHAY_KANBAN_LOGS_ROOT
  export PYTHONDONTWRITEBYTECODE=1
fi

# Missing test dependencies are a preflight failure; the wrapper never installs.
"$PYTHON" - <<'PY'
import importlib.util
missing = [name for name in ("pytest", "xdist", "pytest_split") if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit("missing required test dependencies: " + ", ".join(missing))
PY

# ── Hermetic environment ────────────────────────────────────────────────────
# Mirror what CI does in .github/workflows/tests.yml + what conftest.py does.
# Unset every credential-shaped var currently in the environment.
while IFS='=' read -r name _; do
  case "$name" in
    *_API_KEY|*_TOKEN|*_SECRET|*_PASSWORD|*_CREDENTIALS|*_ACCESS_KEY| \
    *_SECRET_ACCESS_KEY|*_PRIVATE_KEY|*_OAUTH_TOKEN|*_WEBHOOK_SECRET| \
    *_ENCRYPT_KEY|*_APP_SECRET|*_CLIENT_SECRET|*_CORP_SECRET|*_AES_KEY| \
    AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|FAL_KEY| \
    GH_TOKEN|GITHUB_TOKEN)
      unset "$name"
      ;;
  esac
done < <(env)

# Unset SHAY_* behavioral vars too.
unset SHAY_YOLO_MODE SHAY_INTERACTIVE SHAY_QUIET SHAY_TOOL_PROGRESS \
      SHAY_TOOL_PROGRESS_MODE SHAY_MAX_ITERATIONS SHAY_SESSION_PLATFORM \
      SHAY_SESSION_CHAT_ID SHAY_SESSION_CHAT_NAME SHAY_SESSION_THREAD_ID \
      SHAY_SESSION_SOURCE SHAY_SESSION_KEY SHAY_GATEWAY_SESSION \
      SHAY_CRON_SESSION \
      SHAY_PLATFORM SHAY_INFERENCE_PROVIDER SHAY_MANAGED SHAY_DEV \
      SHAY_CONTAINER SHAY_EPHEMERAL_SYSTEM_PROMPT SHAY_TIMEZONE \
      SHAY_REDACT_SECRETS SHAY_BACKGROUND_NOTIFICATIONS SHAY_EXEC_ASK \
      SHAY_HOME_MODE 2>/dev/null || true

# Pin deterministic runtime.
export TZ=UTC
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONHASHSEED=0

# ── Live-gateway test guard (developer machines) ────────────────────────────
# If a system-wide shay pytest_live_guard plugin is installed at
# $HOME/.shay/pytest_live_guard.py, force-load it here so every test run
# from this script gets the protection regardless of which worktree is
# checked out (in-tree tests/conftest.py guard may be missing on stale
# branches). Harmless on CI / fresh machines that don't have the file.
if [ -f "$HOME/.shay/pytest_live_guard.py" ]; then
  case ":${PYTHONPATH:-}:" in
    *":$HOME/.shay:"*) ;;
    *) export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$HOME/.shay" ;;
  esac
  if [[ ",${PYTEST_PLUGINS:-}," != *,pytest_live_guard,* ]]; then
    export PYTEST_PLUGINS="${PYTEST_PLUGINS:+$PYTEST_PLUGINS,}pytest_live_guard"
  fi
fi

# The marker's successful dependency-check claim is independently re-run for
# both schemas before pytest or Shay imports occur.
"$PYTHON" -m pip check >/dev/null

# ── Worker count ────────────────────────────────────────────────────────────
# CI uses `-n auto` on ubuntu-latest which gives 4 workers. A 20-core
# workstation with `-n auto` gets 20 workers and exposes test-ordering
# flakes that CI will never see. Pin to 4 so local matches CI.
WORKERS="${SHAY_TEST_WORKERS:-4}"

# ── Run pytest ──────────────────────────────────────────────────────────────
cd "$REPO_ROOT"

if [ "$E2E_MODE" -eq 1 ]; then
  echo "▶ running baseline E2E pytest gate with $WORKERS workers, hermetic env, in $REPO_ROOT"
  "$PYTHON" -m pytest -o "addopts=" -p no:cacheprovider -n "$WORKERS" \
    tests/e2e/test_shay_baseline_e2e.py "$@"
  for stress in tests/stress/test_concurrency.py \
                tests/stress/test_subprocess_e2e.py \
                tests/stress/test_atypical_scenarios.py; do
    echo "▶ running standalone stress program: $stress"
    "$PYTHON" "$stress"
  done
  exit 0
fi

# If the first argument starts with `-` treat all args as pytest flags;
# otherwise treat them as test paths.
ARGS=()
if [ "$#" -gt 0 ]; then
  ARGS=("$@")
fi

echo "▶ running pytest with $WORKERS workers, hermetic env, in $REPO_ROOT"
echo "  (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0; all credential env vars unset)"

# -o "addopts=" clears pyproject.toml's `-n auto` so our -n wins.
if [ "$#" -gt 0 ]; then
  exec "$PYTHON" -m pytest \
    -o "addopts=" \
    -n "$WORKERS" \
    --ignore=tests/integration \
    --ignore=tests/e2e \
    -m "not integration" \
    "${ARGS[@]}"
else
  exec "$PYTHON" -m pytest \
    -o "addopts=" \
    -n "$WORKERS" \
    --ignore=tests/integration \
    --ignore=tests/e2e \
    -m "not integration"
fi
