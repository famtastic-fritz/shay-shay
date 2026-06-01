"""Build Coordinator — safe concurrent multi-build governance.

The layer ABOVE the orchestrators. The run-router (``shay_cli/run_router.py``)
decides HOW one build runs (ralph/swarm + executor). This coordinator governs
HOW MULTIPLE concurrent builds COEXIST without clobbering each other.

It provides:

1. A persisted **active-build registry** (JSON under ``$SHAY_HOME``) that
   survives restart. Each build = ``{id, orchestrator, repo, file_set,
   worktree_path, status, started_at, ...}``.
2. ``admit(build)`` — creates a fresh ``git worktree`` of the build's repo
   under ``$SHAY_HOME/worktrees/<build-id>`` so the build runs THERE, never
   the live tree. Applies overlap-aware admission:
       - file_set DISJOINT from every active build  -> admitted (parallel)
       - file_set OVERLAPS an active build           -> queued (serialize)
       - file_set unknown                            -> serialize per-repo
   Also honors a global concurrent-worker budget (``max_concurrent`` from
   run-policy.yaml) and a low-funds signal.
3. ``reconcile(build, *, green)`` — on GREEN, merges the worktree back to the
   live repo; on conflict, escalates (no silent clobber). On FAIL, discards
   the worktree. Removes the worktree either way, then promotes queued builds
   whose blockers have cleared.
4. A vault mirror of live state at
   ``obsidian/Shay-Memory/_system/coordinator-state.md``.

Worktree isolation is REAL from day one (the actual safety). File-set overlap
is coarse/advisory: an empty/None file_set is treated as "touches the whole
repo" and serialized per-repo. Fine-grained intra-repo parallelism is a later
enhancement (pairs with the anti-drift trace graph).

Source spec: obsidian/Shay-Memory/research/build-coordinator-design-2026-06-01.md
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Build",
    "BuildCoordinator",
    "AdmitResult",
    "default_registry_path",
    "worktrees_root",
]

# Build status lifecycle.
STATUS_ADMITTED = "admitted"   # has a worktree, running
STATUS_QUEUED = "queued"       # blocked behind an overlapping/repo-locked build
STATUS_GREEN = "green"         # gates passed, merged back, terminal
STATUS_FAILED = "failed"       # gates failed / discarded, terminal
STATUS_CONFLICT = "conflict"   # merge conflict on reconcile, escalated

TERMINAL_STATUSES = frozenset({STATUS_GREEN, STATUS_FAILED})
ACTIVE_STATUSES = frozenset({STATUS_ADMITTED, STATUS_QUEUED, STATUS_CONFLICT})


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def _shay_home() -> Path:
    """Resolve SHAY_HOME without a hard import dependency at module load."""
    val = os.environ.get("SHAY_HOME", "").strip()
    if val:
        return Path(val)
    try:  # prefer the canonical resolver when importable
        from shay_constants import get_shay_home  # type: ignore

        return get_shay_home()
    except Exception:
        return Path.home() / ".shay"


def default_registry_path() -> Path:
    """Where the active-build registry JSON lives."""
    return _shay_home() / "build-coordinator.json"


def worktrees_root() -> Path:
    """Parent dir under which per-build worktrees are created."""
    return _shay_home() / "worktrees"


def _default_vault_mirror() -> Path | None:
    """Best-effort path to the vault mirror; None if the vault is absent."""
    candidate = (
        Path.home()
        / "famtastic"
        / "obsidian"
        / "Shay-Memory"
        / "_system"
        / "coordinator-state.md"
    )
    return candidate


# --------------------------------------------------------------------------- #
# Build record
# --------------------------------------------------------------------------- #
@dataclass
class Build:
    """One concurrent build tracked by the coordinator."""

    repo: str
    orchestrator: str = "interactive"
    file_set: list[str] = field(default_factory=list)
    id: str = ""
    worktree_path: str | None = None
    status: str = STATUS_QUEUED
    started_at: float = 0.0
    workers: int = 1
    blocked_by: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"b-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        if not self.started_at:
            self.started_at = time.time()
        # Normalize repo to an absolute string path.
        self.repo = str(Path(self.repo).expanduser())

    @property
    def normalized_files(self) -> set[str]:
        """File set as a set of normalized relative-ish paths (may be empty)."""
        return {f.strip() for f in (self.file_set or []) if f and f.strip()}

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdmitResult:
    """Outcome of an ``admit`` call."""

    build: Build
    admitted: bool
    queued: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "build_id": self.build.id,
            "status": self.build.status,
            "admitted": self.admitted,
            "queued": self.queued,
            "worktree_path": self.build.worktree_path,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------- #
# Git helpers (isolated so tests can run against a real temp repo)
# --------------------------------------------------------------------------- #
def _git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _current_branch(repo: str) -> str:
    try:
        out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        return out or "HEAD"
    except subprocess.CalledProcessError:
        return "HEAD"


# --------------------------------------------------------------------------- #
# Coordinator
# --------------------------------------------------------------------------- #
class BuildCoordinator:
    """Persisted, overlap-aware, worktree-isolating multi-build governor."""

    def __init__(
        self,
        registry_path: Path | str | None = None,
        worktrees_dir: Path | str | None = None,
        *,
        max_concurrent: int | None = None,
        vault_mirror: Path | str | None = None,
        low_funds: bool = False,
    ) -> None:
        self.registry_path = Path(registry_path) if registry_path else default_registry_path()
        self.worktrees_dir = Path(worktrees_dir) if worktrees_dir else worktrees_root()
        self.vault_mirror = (
            Path(vault_mirror) if vault_mirror is not None else _default_vault_mirror()
        )
        self.low_funds = low_funds
        self._max_concurrent = max_concurrent
        self.builds: dict[str, Build] = {}
        self._load()

    # ----- persistence ---------------------------------------------------- #
    def _load(self) -> None:
        if not self.registry_path.exists():
            self.builds = {}
            return
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.builds = {}
            return
        self.builds = {}
        for rec in data.get("builds", []):
            try:
                self.builds[rec["id"]] = Build(**rec)
            except TypeError:
                # Tolerate forward/backward schema drift — keep known fields.
                known = {k: v for k, v in rec.items() if k in Build.__dataclass_fields__}
                b = Build(**known)
                self.builds[b.id] = b

    def _save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": time.time(),
            "builds": [b.as_dict() for b in self.builds.values()],
        }
        tmp = self.registry_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.registry_path)
        self._mirror_to_vault()

    # ----- budget --------------------------------------------------------- #
    def max_concurrent(self) -> int:
        """Global cap on concurrent workers across all builds.

        Reads the swarm orchestrator's ``max_concurrent`` from run-policy.yaml
        unless explicitly overridden in the constructor.
        """
        if self._max_concurrent is not None:
            return self._max_concurrent
        try:
            from shay_cli import run_router

            policy = run_router.load_policy()
            cap = (
                (policy.get("orchestrators", {}) or {})
                .get("swarm", {})
                .get("max_concurrent")
            )
            if isinstance(cap, int) and cap > 0:
                return cap
        except Exception:
            pass
        return 4

    def workers_in_use(self) -> int:
        return sum(
            b.workers for b in self.builds.values() if b.status == STATUS_ADMITTED
        )

    def budget_available(self, need: int) -> bool:
        if self.low_funds:
            # Low funds: only allow a build through if nothing else is running.
            return self.workers_in_use() == 0 and need <= self.max_concurrent()
        return (self.workers_in_use() + need) <= self.max_concurrent()

    # ----- overlap logic -------------------------------------------------- #
    def active_builds(self) -> list[Build]:
        return [b for b in self.builds.values() if b.status in ACTIVE_STATUSES]

    def running_builds(self) -> list[Build]:
        return [b for b in self.builds.values() if b.status == STATUS_ADMITTED]

    def queued_builds(self) -> list[Build]:
        return [b for b in self.builds.values() if b.status == STATUS_QUEUED]

    def _overlapping_blocker(self, build: Build) -> Build | None:
        """Return a running build that this build must serialize behind.

        - unknown file_set (empty) -> serialize per-repo: blocked by any
          running build in the same repo.
        - known file_set -> blocked only by a running build whose file_set
          intersects (or is itself unknown) within the same repo.
        """
        mine = build.normalized_files
        for other in self.running_builds():
            if other.id == build.id:
                continue
            if Path(other.repo) != Path(build.repo):
                continue
            theirs = other.normalized_files
            if not mine or not theirs:
                # Either side unknown -> conservatively serialize per-repo.
                return other
            if mine & theirs:
                return other
        return None

    # ----- worktree ------------------------------------------------------- #
    def _worktree_path_for(self, build: Build) -> Path:
        return self.worktrees_dir / build.id

    def _create_worktree(self, build: Build) -> Path:
        """`git worktree add` a fresh isolated tree for the build."""
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        wt = self._worktree_path_for(build)
        if wt.exists():
            # Stale leftover — reclaim it before re-adding.
            self._remove_worktree(build, path=wt)
        base = _current_branch(build.repo)
        branch = f"coord/{build.id}"
        _git(build.repo, "worktree", "add", "-b", branch, str(wt), base)
        return wt

    def _remove_worktree(self, build: Build, path: Path | None = None) -> None:
        wt = path or (Path(build.worktree_path) if build.worktree_path else None)
        if not wt:
            return
        # Remove the worktree, then prune the branch we created for it.
        _git(build.repo, "worktree", "remove", "--force", str(wt), check=False)
        _git(build.repo, "worktree", "prune", check=False)
        _git(build.repo, "branch", "-D", f"coord/{build.id}", check=False)

    # ----- public API ----------------------------------------------------- #
    def admit(self, build: Build) -> AdmitResult:
        """Register a build, create its worktree, and decide parallel vs queued."""
        self.builds[build.id] = build

        blocker = self._overlapping_blocker(build)
        if blocker is not None:
            build.status = STATUS_QUEUED
            build.blocked_by = blocker.id
            self._save()
            return AdmitResult(
                build=build,
                admitted=False,
                queued=True,
                reason=(
                    f"file_set overlaps (or unknown vs) running build {blocker.id} "
                    f"in {build.repo} — serialized behind it"
                ),
            )

        if not self.budget_available(build.workers):
            build.status = STATUS_QUEUED
            build.blocked_by = None
            self._save()
            return AdmitResult(
                build=build,
                admitted=False,
                queued=True,
                reason=(
                    f"worker budget exhausted "
                    f"({self.workers_in_use()}/{self.max_concurrent()} in use"
                    f"{'; low-funds' if self.low_funds else ''}) — queued"
                ),
            )

        # Admit: real worktree isolation.
        wt = self._create_worktree(build)
        build.worktree_path = str(wt)
        build.status = STATUS_ADMITTED
        build.blocked_by = None
        self._save()
        return AdmitResult(
            build=build,
            admitted=True,
            queued=False,
            reason=f"file_set disjoint + budget ok — admitted in worktree {wt}",
        )

    def reconcile(self, build: Build | str, *, green: bool) -> dict[str, Any]:
        """Finish a build: merge-back on GREEN, discard on FAIL.

        Always removes the worktree, then promotes any queued builds whose
        blockers have cleared.
        """
        bid = build.id if isinstance(build, Build) else build
        rec = self.builds.get(bid)
        if rec is None:
            return {"build_id": bid, "status": "unknown", "reason": "not in registry"}

        result: dict[str, Any] = {"build_id": rec.id, "repo": rec.repo}

        if green:
            merged = self._merge_back(rec)
            result.update(merged)
            rec.status = merged["status"]
        else:
            rec.status = STATUS_FAILED
            result.update({"status": STATUS_FAILED, "reason": "gates failed — worktree discarded"})

        # Remove worktree either way (conflict keeps the branch for inspection).
        if rec.status != STATUS_CONFLICT:
            self._remove_worktree(rec)
            rec.worktree_path = None

        self._save()
        promoted = self._promote_queued()
        result["promoted"] = [p.id for p in promoted]
        return result

    def _merge_back(self, build: Build) -> dict[str, Any]:
        """Merge the build's worktree branch into the live repo's branch."""
        if not build.worktree_path:
            return {"status": STATUS_GREEN, "reason": "no worktree to merge (nothing to do)"}
        branch = f"coord/{build.id}"
        proc = _git(build.repo, "merge", "--no-ff", "-m", f"coordinator: merge {build.id}", branch, check=False)
        if proc.returncode == 0:
            return {"status": STATUS_GREEN, "reason": f"merged {branch} into live tree"}
        # Conflict / failure: abort the merge so the live tree stays clean.
        _git(build.repo, "merge", "--abort", check=False)
        return {
            "status": STATUS_CONFLICT,
            "reason": (
                f"merge of {branch} conflicted — live tree left untouched, "
                f"branch retained for escalation. git said: {proc.stderr.strip()[:300]}"
            ),
        }

    def _promote_queued(self) -> list[Build]:
        """Admit queued builds that are now unblocked (in FIFO order)."""
        promoted: list[Build] = []
        # Process oldest-queued first for fairness.
        for b in sorted(self.queued_builds(), key=lambda x: x.started_at):
            blocker = self._overlapping_blocker(b)
            if blocker is not None:
                b.blocked_by = blocker.id
                continue
            if not self.budget_available(b.workers):
                continue
            try:
                wt = self._create_worktree(b)
            except subprocess.CalledProcessError:
                continue
            b.worktree_path = str(wt)
            b.status = STATUS_ADMITTED
            b.blocked_by = None
            promoted.append(b)
        if promoted:
            self._save()
        return promoted

    def prune_terminal(self) -> int:
        """Drop terminal builds from the registry. Returns count removed."""
        before = len(self.builds)
        self.builds = {
            bid: b for bid, b in self.builds.items() if b.status not in TERMINAL_STATUSES
        }
        removed = before - len(self.builds)
        if removed:
            self._save()
        return removed

    # ----- reporting ------------------------------------------------------ #
    def status_dict(self) -> dict[str, Any]:
        return {
            "registry": str(self.registry_path),
            "worktrees_dir": str(self.worktrees_dir),
            "max_concurrent": self.max_concurrent(),
            "workers_in_use": self.workers_in_use(),
            "low_funds": self.low_funds,
            "active": [b.as_dict() for b in self.active_builds()],
            "running": [b.id for b in self.running_builds()],
            "queued": [b.id for b in self.queued_builds()],
        }

    def render_status(self) -> str:
        lines: list[str] = []
        lines.append("Build Coordinator — active builds")
        lines.append("=" * 60)
        lines.append(f"  registry:      {self.registry_path}")
        lines.append(f"  worktrees:     {self.worktrees_dir}")
        cap = self.max_concurrent()
        used = self.workers_in_use()
        funds = " (LOW FUNDS)" if self.low_funds else ""
        lines.append(f"  budget:        {used}/{cap} workers in use{funds}")
        lines.append("")

        active = self.active_builds()
        if not active:
            lines.append("  (no active builds — registry empty)")
            return "\n".join(lines)

        for b in sorted(active, key=lambda x: x.started_at):
            fs = ", ".join(sorted(b.normalized_files)) or "<unknown — repo-locked>"
            wt = b.worktree_path or "-"
            blocked = f"  blocked-by={b.blocked_by}" if b.blocked_by else ""
            lines.append(f"  [{b.status:<9}] {b.id}")
            lines.append(f"      orchestrator: {b.orchestrator}   repo: {b.repo}")
            lines.append(f"      file_set:     {fs}")
            lines.append(f"      worktree:     {wt}{blocked}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _mirror_to_vault(self) -> None:
        """Write a human-browsable mirror of live state to the vault."""
        if not self.vault_mirror:
            return
        try:
            self.vault_mirror.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return  # vault not present on this machine — silently skip
        body = [
            "---",
            "title: coordinator-state",
            "type: note",
            "tags: [coordinator, worktree, concurrency, run-model]",
            "---",
            "",
            "# Build Coordinator — live state",
            "",
            f"_Auto-generated mirror. Updated {time.strftime('%Y-%m-%d %H:%M:%S')}._",
            "",
            f"- registry: `{self.registry_path}`",
            f"- worktrees: `{self.worktrees_dir}`",
            f"- budget: {self.workers_in_use()}/{self.max_concurrent()} workers in use"
            + (" (LOW FUNDS)" if self.low_funds else ""),
            "",
        ]
        active = self.active_builds()
        if not active:
            body.append("_No active builds._")
        else:
            body.append("| build | status | orchestrator | repo | file_set | worktree |")
            body.append("|---|---|---|---|---|---|")
            for b in sorted(active, key=lambda x: x.started_at):
                fs = ", ".join(sorted(b.normalized_files)) or "_unknown (repo-locked)_"
                body.append(
                    f"| {b.id} | {b.status} | {b.orchestrator} | "
                    f"`{b.repo}` | {fs} | `{b.worktree_path or '-'}` |"
                )
        try:
            self.vault_mirror.write_text("\n".join(body) + "\n", encoding="utf-8")
        except OSError:
            pass
