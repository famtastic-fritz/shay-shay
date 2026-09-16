"""Hermetic baseline envelopes used by ``scripts/run_tests.sh --e2e``."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import pwd
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_OWNER_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
_OWNER_PROFILE = _OWNER_HOME / ".shay"
_PROFILE_SCRIPT = r'''
import json
import os
from pathlib import Path

root = Path(os.environ["PROFILE_ROOT"]).resolve()
other = Path(os.environ["OTHER_ROOT"]).resolve()
repo = Path(os.environ["REPO_ROOT"]).resolve()
owner_profile = Path(os.environ["OWNER_PROFILE"]).resolve()
home = Path(os.environ["HOME"]).resolve()
shay_home = Path(os.environ["SHAY_HOME"]).resolve()
vault = Path(os.environ["SHAY_PROMPT_MEMORY_VAULT"]).resolve()
assert home.parent == root and shay_home.parent == root and vault.parent == root
assert len({home, shay_home, vault}) == 3
for path in (home, shay_home, vault):
    assert path.is_relative_to(root)
    assert not path.is_relative_to(repo)
    assert not path.is_relative_to(owner_profile)
for name in ("SHAY_KANBAN_HOME", "SHAY_KANBAN_DB", "SHAY_KANBAN_WORKSPACES_ROOT", "SHAY_KANBAN_BOARD", "SHAY_KANBAN_LOGS_ROOT"):
    assert name not in os.environ

from shay_cli import kanban_db as kb

db_path = kb.init_db()
assert db_path.resolve() == shay_home / "kanban.db"
with kb.connect() as conn:
    task_id = kb.create_task(
        conn,
        title=os.environ["PROFILE_NAME"],
        idempotency_key="baseline:" + os.environ["PROFILE_NAME"],
    )
    row = kb.get_task(conn, task_id)
    assert row is not None and row.title == os.environ["PROFILE_NAME"]

vault.joinpath("memory.json").write_text(json.dumps({"profile": os.environ["PROFILE_NAME"]}))
cache = Path(os.environ["XDG_CACHE_HOME"])
cache.mkdir(parents=True, exist_ok=True)
cache.joinpath("marker").write_text(os.environ["PROFILE_NAME"])
log = shay_home / "kanban" / "logs" / "baseline.log"
log.parent.mkdir(parents=True, exist_ok=True)
log.write_text(task_id + "\n")
for path in (Path(os.environ["TMPDIR"]), cache, Path(os.environ["PIP_CACHE_DIR"]), Path(os.environ["UV_CACHE_DIR"]), Path(os.environ["COVERAGE_FILE"]).parent, log):
    assert path.resolve().is_relative_to(root)
    assert not path.resolve().is_relative_to(repo)
    assert not path.resolve().is_relative_to(owner_profile)

# The other profile's files may exist on disk, but no implicit Shay path may
# resolve to them; this process only ever opened its own roots above.
assert db_path.resolve() != (other / "shay-home" / "kanban.db").resolve()
assert not db_path.resolve().is_relative_to(other)
print(json.dumps({"db": str(db_path.resolve()), "task_id": task_id, "profile": os.environ["PROFILE_NAME"]}))
'''


def _run_profile(root: Path, other: Path, name: str) -> dict:
    home = root / "home"
    shay_home = root / "shay-home"
    vault = root / "prompt-memory-vault"
    for path in (home, shay_home, vault):
        path.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(home),
        "SHAY_HOME": str(shay_home),
        "SHAY_PROMPT_MEMORY_VAULT": str(vault),
        "PYTHONPATH": str(_REPO_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "PIP_CACHE_DIR": str(root / "pip-cache"),
        "UV_CACHE_DIR": str(root / "uv-cache"),
        "COVERAGE_FILE": str(root / "coverage" / ".coverage"),
        "PROFILE_ROOT": str(root),
        "OTHER_ROOT": str(other),
        "REPO_ROOT": str(_REPO_ROOT),
        "OWNER_PROFILE": str(_OWNER_PROFILE),
        "PROFILE_NAME": name,
    }
    subprocess_env = dict(env)
    result = subprocess.run(
        [sys.executable, "-c", _PROFILE_SCRIPT],
        cwd=_REPO_ROOT,
        env=subprocess_env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_two_profile_envelopes_are_isolated(tmp_path: Path) -> None:
    first = tmp_path / "profile-a"
    second = tmp_path / "profile-b"
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
        results = list(
            workers.map(
                lambda args: _run_profile(*args),
                ((first, second, "profile-a"), (second, first, "profile-b")),
            )
        )

    assert {Path(result["db"]) for result in results} == {
        (first / "shay-home" / "kanban.db").resolve(),
        (second / "shay-home" / "kanban.db").resolve(),
    }
    assert (first / "prompt-memory-vault" / "memory.json").read_text()
    assert (second / "prompt-memory-vault" / "memory.json").read_text()
    assert json.loads((first / "prompt-memory-vault" / "memory.json").read_text())["profile"] == "profile-a"
    assert json.loads((second / "prompt-memory-vault" / "memory.json").read_text())["profile"] == "profile-b"
    assert (first / "cache" / "marker").read_text() == "profile-a"
    assert (second / "cache" / "marker").read_text() == "profile-b"
    assert (first / "shay-home" / "kanban" / "logs" / "baseline.log").read_text().strip() == results[0]["task_id"]
    assert (second / "shay-home" / "kanban" / "logs" / "baseline.log").read_text().strip() == results[1]["task_id"]
    with sqlite3.connect(first / "shay-home" / "kanban.db") as conn:
        assert {row[0] for row in conn.execute("SELECT title FROM tasks")} == {"profile-a"}
    with sqlite3.connect(second / "shay-home" / "kanban.db") as conn:
        assert {row[0] for row in conn.execute("SELECT title FROM tasks")} == {"profile-b"}


def _portable_test_provenance(tmp_path: Path) -> Path:
    """Create a caller-supplied marker for runner preflight tests."""
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    reviewed = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True
    ).strip()
    marker = tmp_path / "provenance.json"
    payload = {
        "dependency_lock_hashes": {"uv.lock": digest(_REPO_ROOT / "uv.lock")},
        "environment_kind": "immutable_local",
        "install_command": "python -m pip install -e '.[all,dev]'",
        "pip_check_exit_code": 0,
        "pyproject_sha256": digest(_REPO_ROOT / "pyproject.toml"),
        "python_executable": sys.executable,
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "repository": str(_REPO_ROOT),
        "reviewed_sha": reviewed,
        "schema_version": 1,
    }
    marker.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    marker.chmod(0o400)
    return marker


@pytest.mark.parametrize("symlinked", ["HOME", "SHAY_HOME", "SHAY_PROMPT_MEMORY_VAULT"])
def test_runner_rejects_symlinked_e2e_envelope_paths(
    tmp_path: Path, symlinked: str
) -> None:
    """The E2E wrapper must fail before following an envelope symlink."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    paths = {
        "HOME": run_root / "home",
        "SHAY_HOME": run_root / "shay-home",
        "SHAY_PROMPT_MEMORY_VAULT": run_root / "prompt-memory-vault",
    }
    target = outside / symlinked.lower().replace("_", "-")
    target.mkdir()
    paths[symlinked].symlink_to(target, target_is_directory=True)
    marker = _portable_test_provenance(tmp_path)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(paths["HOME"]),
        "SHAY_HOME": str(paths["SHAY_HOME"]),
        "SHAY_PROMPT_MEMORY_VAULT": str(paths["SHAY_PROMPT_MEMORY_VAULT"]),
        "SHAY_TEST_PYTHON": sys.executable,
        "SHAY_TEST_ENV_PROVENANCE": str(marker),
        "SHAY_TEST_WORKERS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [str(_REPO_ROOT / "scripts" / "run_tests.sh"), "--e2e"],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0
    assert "symlink" in (result.stdout + result.stderr).lower()
    assert not (outside / "tmp").exists()
