"""R8 acceptance reporter tests.

The external execution ledger is authoritative.  These tests prove that a
missing/incomplete lifecycle cannot be converted into a passing upgrade claim.
"""

from __future__ import annotations

import json
import hashlib
import os
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]


def _run(tmp_path: pathlib.Path, **extra: str) -> subprocess.CompletedProcess[str]:
    output = tmp_path / "proof.json"
    ledger = tmp_path / "execution-events.jsonl"
    ledger.write_text('{"event_type":"execution_ledger_initialized"}\n', encoding="utf-8")
    provenance = tmp_path / "provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python_executable": os.environ.get("SHAY_TEST_PYTHON", sys.executable),
                "python_version": "3.11.0",
                "reviewed_sha": "0" * 40,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    provenance.chmod(0o400)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "SHAY_UPGRADE_PROOF_OUTPUT": str(output),
        "SHAY_TEST_PYTHON": os.environ.get("SHAY_TEST_PYTHON", sys.executable),
        "SHAY_TEST_ENV_PROVENANCE": str(provenance),
        "SHAY_EXECUTION_LEDGER": str(ledger),
        "HOME": str(tmp_path / "home"),
        "SHAY_HOME": str(tmp_path / "shay-home"),
        "SHAY_PROMPT_MEMORY_VAULT": str(tmp_path / "vault"),
    }
    env.update(extra)
    return subprocess.run(
        [str(ROOT / "scripts/run_shay_upgrade_proof.sh")],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_upgrade_proof_blocks_without_external_phase_chain(tmp_path: pathlib.Path) -> None:
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "launch-blocked" in result.stderr
    evidence = json.loads((tmp_path / "proof.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "launch-blocked"
    assert evidence["checks"]["lifecycle"] is False
    assert evidence["passed_commands"] == 0
    assert evidence["validated_semantic_evidence"] < 6


def test_upgrade_proof_requires_fresh_external_output(tmp_path: pathlib.Path) -> None:
    output = tmp_path / "proof.json"
    output.write_text("immutable prior result\n", encoding="utf-8")
    result = _run(tmp_path, SHAY_UPGRADE_PROOF_OUTPUT=str(output))
    assert result.returncode != 0
    assert "already exists" in result.stderr
