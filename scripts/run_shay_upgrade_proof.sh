#!/usr/bin/env bash
set -euo pipefail

# R8's common proof is deliberately a fail-closed reporter.  The repository
# contains the reporter and its schema, but the external execution ledger is
# the authority for reviews, CI, completion, and finalization.  It must be
# supplied by the orchestrator; this script never invents those facts.

die() {
  echo "error: $*" >&2
  exit 2
}

repo_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
: "${SHAY_UPGRADE_PROOF_OUTPUT:?SHAY_UPGRADE_PROOF_OUTPUT is required}"
: "${SHAY_TEST_PYTHON:?SHAY_TEST_PYTHON is required}"
: "${SHAY_TEST_ENV_PROVENANCE:?SHAY_TEST_ENV_PROVENANCE is required}"
: "${SHAY_EXECUTION_LEDGER:?SHAY_EXECUTION_LEDGER is required; R8 authority is external}"

case "$SHAY_UPGRADE_PROOF_OUTPUT" in /*) ;; *) die "proof output must be absolute" ;; esac
case "$SHAY_TEST_PYTHON" in /*) ;; *) die "SHAY_TEST_PYTHON must be absolute" ;; esac
case "$SHAY_TEST_ENV_PROVENANCE" in /*) ;; *) die "SHAY_TEST_ENV_PROVENANCE must be absolute" ;; esac
case "$SHAY_EXECUTION_LEDGER" in /*) ;; *) die "SHAY_EXECUTION_LEDGER must be absolute" ;; esac
[ ! -e "$SHAY_UPGRADE_PROOF_OUTPUT" ] || die "proof output already exists; choose a fresh external path"
[ -x "$SHAY_TEST_PYTHON" ] || die "test interpreter is not executable"
[ -f "$SHAY_TEST_ENV_PROVENANCE" ] || die "environment provenance is missing"
[ -f "$SHAY_EXECUTION_LEDGER" ] || die "external execution ledger is missing"
[ -d "$(dirname -- "$SHAY_UPGRADE_PROOF_OUTPUT")" ] || die "proof output parent must already exist"

exec "$SHAY_TEST_PYTHON" - "$repo_root" "$SHAY_UPGRADE_PROOF_OUTPUT" "$SHAY_EXECUTION_LEDGER" "$SHAY_TEST_ENV_PROVENANCE" <<'PY'
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

repo, output, ledger, provenance = map(pathlib.Path, sys.argv[1:])

def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

started = now()
try:
    provenance_obj = json.loads(provenance.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"invalid environment provenance: {exc}")
if not isinstance(provenance_obj, dict) or provenance_obj.get("schema_version") not in {1, 2}:
    raise SystemExit("unsupported environment provenance schema")
if provenance_obj.get("python_executable") != str(pathlib.Path(sys.executable)):
    raise SystemExit("environment provenance interpreter mismatch")
if not isinstance(provenance_obj.get("python_version"), str) or not provenance_obj["python_version"].startswith("3.11."):
    raise SystemExit("environment provenance Python version mismatch")
if not isinstance(provenance_obj.get("reviewed_sha"), str) or len(provenance_obj["reviewed_sha"]) != 40:
    raise SystemExit("environment provenance reviewed SHA mismatch")
branch = subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"], text=True).strip()
head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
status = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"], text=True)

required = [
    ".github/workflows/tests.yml",
    "scripts/run_shay_upgrade_proof.sh",
    "tests/e2e/test_shay_upgrade_proof.py",
    "docs/architecture/evidence/shay-agent-r8-events.jsonl",
    "docs/architecture/evidence/shay-agent-upgrade-evidence.json",
    "docs/architecture/shay-agent-enhancement-trace.jsonl",
    "docs/architecture/shay-current-state-diagrams.md",
    "docs/status/shay-agent-enhancement-status.md",
    "docs/status/shay-agent-enhancement-final-checklist.md",
]
present = {p: (repo / p).is_file() for p in required}

phase_rows = []
ledger_error = None
try:
    raw = ledger.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("ledger is missing its final newline")
    for line_no, line in enumerate(raw.splitlines(), 1):
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"ledger line {line_no} is not an object")
        phase_rows.append(row)
except Exception as exc:
    ledger_error = str(exc)

complete = {}
for row in phase_rows:
    req = row.get("requirement_id")
    if isinstance(req, str) and req.startswith("SHAY-AGENT-R"):
        complete.setdefault(req, []).append(row)

prior_phases = {}
for n in range(1, 8):
    req = f"SHAY-AGENT-R{n}"
    rows = complete.get(req, [])
    prior_phases[req] = {
        "ledger_rows": len(rows),
        "kanban_completed": any(r.get("event_type") == "kanban_completed" and r.get("outcome") == "completed" for r in rows),
        "remote_ci_verified": any(r.get("event_type") == "feature_branch_push_verified" and r.get("outcome") == "pushed" for r in rows),
        "reviews_complete": sum(1 for r in rows if r.get("event_type") in {"verification_review", "anti_pattern_review", "quality_review"} and r.get("outcome") == "passed") >= 3,
    }

all_prior_complete = bool(not ledger_error and prior_phases and all(
    v["kanban_completed"] and v["remote_ci_verified"] and v["reviews_complete"]
    for v in prior_phases.values()
))
checks = {
    "baseline": all(present.values()),
    "lifecycle": all_prior_complete,
    "safety": bool(os.environ.get("SHAY_PROFILE_SAFETY_RECEIPT")),
    "memory": bool(os.environ.get("SHAY_MEMORY_PROVENANCE_RECEIPT")),
    "protocol": bool(os.environ.get("SHAY_PROTOCOL_RECEIPT")),
    "CLI journey": bool(os.environ.get("SHAY_CLI_JOURNEY_RECEIPT")),
}
all_passed = not ledger_error and all(checks.values()) and bool(branch == "codex/shay-agent-phase8-acceptance") and not status
failure_reasons = []
if ledger_error:
    failure_reasons.append(ledger_error)
if not all_prior_complete:
    failure_reasons.append("R1-R7 external review/CI/kanban completion chain is incomplete")
for label, ok in checks.items():
    if not ok:
        failure_reasons.append(f"semantic gate unavailable: {label}")
if branch != "codex/shay-agent-phase8-acceptance":
    failure_reasons.append("unexpected feature branch")
if status:
    failure_reasons.append("candidate worktree is dirty")

payload = {
    "schema_version": 1,
    "format": "shay-agent-upgrade-evidence-v1",
    "requirement_id": "SHAY-AGENT-R8",
    "candidate": {"branch": branch, "head": head, "tree": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()},
    "cutoff": {"execution_ledger": str(ledger), "execution_ledger_sha256": sha(ledger), "provenance": str(provenance), "provenance_sha256": sha(provenance)},
    "prior_phases": prior_phases,
    "checks": checks,
    "markers": [f"PASS: {name}" for name, ok in checks.items() if ok],
    "executed_commands": 1,
    "passed_commands": 1 if all_passed else 0,
    "validated_semantic_evidence": sum(1 for ok in checks.values() if ok),
    "rollback_results": [],
    "status": "passed" if all_passed else "launch-blocked",
    "failure_reasons": failure_reasons,
    "started_at": started,
    "ended_at": now(),
}
canonical = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
if not output.parent.is_dir():
    raise SystemExit("proof output parent must already exist")
fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
try:
    os.write(fd, canonical)
    os.fsync(fd)
finally:
    os.close(fd)
if not all_passed:
    print("R8 upgrade proof: launch-blocked", file=sys.stderr)
    for reason in failure_reasons:
        print(f"  - {reason}", file=sys.stderr)
    raise SystemExit(1)
for marker in ("baseline", "lifecycle", "safety", "memory", "protocol", "CLI journey"):
    print(f"PASS: {marker}")
PY
