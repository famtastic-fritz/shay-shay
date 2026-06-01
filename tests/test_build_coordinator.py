"""Tests for the Build Coordinator (shay_cli/build_coordinator.py).

These exercise the real safety guarantees against a genuine temp git repo:
  - disjoint file_sets admit in parallel (both get worktrees)
  - overlapping file_sets serialize (the second is queued)
  - unknown file_set serializes per-repo (conservative)
  - a worktree is created on admit and removed on reconcile / fail
  - a GREEN build merges its worktree branch back into the live repo
  - a FAILED build discards its worktree with no live-tree impact
  - registry persists across coordinator restarts
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from shay_cli.build_coordinator import (
    STATUS_ADMITTED,
    STATUS_FAILED,
    STATUS_GREEN,
    STATUS_QUEUED,
    Build,
    BuildCoordinator,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A real git repo with one commit so worktree add works."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@t.test")
    _git(r, "config", "user.name", "Test")
    (r / "README.md").write_text("seed\n")
    _git(r, "add", "README.md")
    _git(r, "commit", "-m", "seed")
    return r


@pytest.fixture()
def coord(tmp_path: Path) -> BuildCoordinator:
    return BuildCoordinator(
        registry_path=tmp_path / "registry.json",
        worktrees_dir=tmp_path / "wt",
        max_concurrent=4,
        vault_mirror=tmp_path / "vault" / "coordinator-state.md",
    )


def test_status_runs_on_empty_registry(coord: BuildCoordinator):
    out = coord.render_status()
    assert "no active builds" in out.lower()
    assert coord.status_dict()["active"] == []


def test_disjoint_builds_admit_parallel(coord: BuildCoordinator, repo: Path):
    a = coord.admit(Build(repo=str(repo), file_set=["a.py"], orchestrator="swarm"))
    b = coord.admit(Build(repo=str(repo), file_set=["b.py"], orchestrator="swarm"))

    assert a.admitted and not a.queued
    assert b.admitted and not b.queued
    assert a.build.status == STATUS_ADMITTED
    assert b.build.status == STATUS_ADMITTED
    # Both got real, distinct worktrees on disk.
    assert Path(a.build.worktree_path).is_dir()
    assert Path(b.build.worktree_path).is_dir()
    assert a.build.worktree_path != b.build.worktree_path


def test_overlapping_builds_serialize(coord: BuildCoordinator, repo: Path):
    a = coord.admit(Build(repo=str(repo), file_set=["shared.py", "a.py"]))
    b = coord.admit(Build(repo=str(repo), file_set=["shared.py", "b.py"]))

    assert a.admitted
    assert b.queued and not b.admitted
    assert b.build.status == STATUS_QUEUED
    assert b.build.blocked_by == a.build.id
    assert b.build.worktree_path is None  # no worktree while queued


def test_unknown_file_set_serializes_per_repo(coord: BuildCoordinator, repo: Path):
    a = coord.admit(Build(repo=str(repo), file_set=["a.py"]))
    # Unknown file_set -> conservatively serialize behind any running build.
    b = coord.admit(Build(repo=str(repo), file_set=[]))
    assert a.admitted
    assert b.queued
    assert b.build.blocked_by == a.build.id


def test_worktree_created_on_admit_and_removed_on_reconcile(
    coord: BuildCoordinator, repo: Path
):
    res = coord.admit(Build(repo=str(repo), file_set=["x.py"]))
    wt = Path(res.build.worktree_path)
    assert wt.is_dir()

    coord.reconcile(res.build, green=True)
    assert not wt.exists()  # worktree removed after reconcile
    assert coord.builds[res.build.id].status == STATUS_GREEN
    assert coord.builds[res.build.id].worktree_path is None


def test_green_build_merges_back(coord: BuildCoordinator, repo: Path):
    res = coord.admit(Build(repo=str(repo), file_set=["feature.txt"]))
    wt = Path(res.build.worktree_path)

    # Do real work in the isolated worktree and commit it there.
    (wt / "feature.txt").write_text("hello from worktree\n")
    _git(wt, "add", "feature.txt")
    _git(wt, "commit", "-m", "add feature")

    result = coord.reconcile(res.build, green=True)
    assert result["status"] == STATUS_GREEN
    # The file now exists in the LIVE tree — merge-back happened.
    assert (repo / "feature.txt").read_text() == "hello from worktree\n"


def test_failed_build_discards_worktree_no_live_impact(
    coord: BuildCoordinator, repo: Path
):
    res = coord.admit(Build(repo=str(repo), file_set=["junk.txt"]))
    wt = Path(res.build.worktree_path)
    (wt / "junk.txt").write_text("should never reach live\n")
    _git(wt, "add", "junk.txt")
    _git(wt, "commit", "-m", "junk")

    result = coord.reconcile(res.build, green=False)
    assert result["status"] == STATUS_FAILED
    assert not wt.exists()
    # Live tree untouched.
    assert not (repo / "junk.txt").exists()


def test_queued_build_promoted_after_blocker_reconciles(
    coord: BuildCoordinator, repo: Path
):
    a = coord.admit(Build(repo=str(repo), file_set=["shared.py"]))
    b = coord.admit(Build(repo=str(repo), file_set=["shared.py"]))
    assert b.queued

    coord.reconcile(a.build, green=True)
    # b should now be promoted to admitted with a fresh worktree.
    promoted = coord.builds[b.build.id]
    assert promoted.status == STATUS_ADMITTED
    assert promoted.worktree_path and Path(promoted.worktree_path).is_dir()


def test_budget_cap_queues_excess(repo: Path, tmp_path: Path):
    c = BuildCoordinator(
        registry_path=tmp_path / "r.json",
        worktrees_dir=tmp_path / "wt",
        max_concurrent=1,
        vault_mirror=tmp_path / "v.md",
    )
    a = c.admit(Build(repo=str(repo), file_set=["a.py"]))
    b = c.admit(Build(repo=str(repo), file_set=["b.py"]))  # disjoint but over budget
    assert a.admitted
    assert b.queued and "budget" in b.reason.lower()


def test_registry_persists_across_restart(repo: Path, tmp_path: Path):
    reg = tmp_path / "r.json"
    wt = tmp_path / "wt"
    c1 = BuildCoordinator(registry_path=reg, worktrees_dir=wt, vault_mirror=tmp_path / "v.md")
    res = c1.admit(Build(repo=str(repo), file_set=["p.py"]))

    c2 = BuildCoordinator(registry_path=reg, worktrees_dir=wt, vault_mirror=tmp_path / "v.md")
    assert res.build.id in c2.builds
    assert c2.builds[res.build.id].status == STATUS_ADMITTED


def test_vault_mirror_written(coord: BuildCoordinator, repo: Path):
    coord.admit(Build(repo=str(repo), file_set=["m.py"]))
    assert coord.vault_mirror.exists()
    text = coord.vault_mirror.read_text()
    assert "Build Coordinator" in text
