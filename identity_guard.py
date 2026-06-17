"""Identity guard for Shay-Shay runtime files.

Protects the load-bearing identity artifacts under SHAY_HOME:
- SOUL.md
- PERSONA.md
- memories/USER.md

Design goals:
- Keep an uncommitted private emergency snapshot under SHAY_HOME/private/
- Track file locations + hashes in a manifest so restores stay path-correct
- Verify required authority lines at startup
- Alert the user immediately (stderr + optional home-channel message) on drift
- Generate a concrete recovery brief that can drive an interview/repair flow
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from shay_constants import get_default_shay_root, get_shay_home


IDENTITY_GUARD_VERSION = 1
IDENTITY_MANIFEST_VERSION = 1
DEFAULT_INCIDENT_DEDUP_COOLDOWN_SECONDS = 6 * 60 * 60

_REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    "SOUL.md": (
        "Nothing supersedes Fritz.",
        "Fritz's direct message / directive right now",
        "Learn Fritz",
    ),
    "PERSONA.md": (
        "Nothing supersedes Fritz.",
        "Fritz's direct intent outranks everything.",
    ),
    "memories/USER.md": (
        "nothing supersedes Fritz or his direct directives",
        "dynamic ultra-brief responses",
    ),
}


@dataclass(frozen=True)
class IdentityFileSpec:
    relative_path: str
    emergency_name: str

    @property
    def required_snippets(self) -> tuple[str, ...]:
        return _REQUIRED_SNIPPETS.get(self.relative_path, ())


IDENTITY_SPECS: tuple[IdentityFileSpec, ...] = (
    IdentityFileSpec("SOUL.md", "SOUL.md"),
    IdentityFileSpec("PERSONA.md", "PERSONA.md"),
    IdentityFileSpec("memories/USER.md", "USER.md"),
)


@dataclass
class IdentityFinding:
    severity: str
    code: str
    path: str
    message: str
    missing_snippets: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.missing_snippets:
            data["missing_snippets"] = list(self.missing_snippets)
        return data


@dataclass
class IdentityAuditResult:
    ok: bool
    shay_home: str
    findings: list[IdentityFinding]
    manifest_path: str
    emergency_dir: str
    incident_path: Optional[str] = None
    interview_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "shay_home": self.shay_home,
            "manifest_path": self.manifest_path,
            "emergency_dir": self.emergency_dir,
            "incident_path": self.incident_path,
            "interview_path": self.interview_path,
            "findings": [f.to_dict() for f in self.findings],
        }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _root() -> Path:
    return get_default_shay_root()


def _home() -> Path:
    return get_shay_home()


def _identity_guard_dir() -> Path:
    return _root() / "private" / "identity-guard"


def _emergency_dir() -> Path:
    return _identity_guard_dir() / "emergency"


def _manifest_path() -> Path:
    return _identity_guard_dir() / "identity-manifest.json"


def _incident_dir() -> Path:
    return _identity_guard_dir() / "incidents"


def _incident_dedup_cooldown_seconds() -> int:
    raw = os.environ.get("SHAY_IDENTITY_GUARD_DEDUP_SECONDS", "").strip()
    if not raw:
        return DEFAULT_INCIDENT_DEDUP_COOLDOWN_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_INCIDENT_DEDUP_COOLDOWN_SECONDS


def _current_version_path() -> Path:
    return _identity_guard_dir() / "CURRENT_VERSION.txt"


def _spec_actual_path(spec: IdentityFileSpec) -> Path:
    return _home() / spec.relative_path


def _spec_emergency_path(spec: IdentityFileSpec) -> Path:
    return _emergency_dir() / spec.emergency_name


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _set_immutable_flag(path: Path, *, locked: bool) -> None:
    if not path.exists() or sys.platform != "darwin":
        return
    flag = "uchg" if locked else "nouchg"
    subprocess.run(["chflags", flag, str(path)], check=True, capture_output=True, text=True)


def _safe_copy_replace(src: Path, dest: Path, *, lock_after: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        _set_immutable_flag(dest, locked=False)
    shutil.copy2(src, dest)
    if lock_after:
        _set_immutable_flag(dest, locked=True)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _default_manifest() -> dict[str, Any]:
    return {
        "manifest_version": IDENTITY_MANIFEST_VERSION,
        "guard_version": IDENTITY_GUARD_VERSION,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "shay_home": str(_home()),
        "root": str(_root()),
        "current_version": 0,
        "files": {},
    }


def load_manifest() -> dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        return _default_manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_manifest()
        return data
    except Exception:
        return _default_manifest()


def save_manifest(manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = int(time.time())
    manifest["shay_home"] = str(_home())
    manifest["root"] = str(_root())
    _write_json(_manifest_path(), manifest)


def ensure_identity_snapshot(*, reason: str = "startup") -> dict[str, Any]:
    """Refresh the private emergency snapshot and version manifest.

    This is intentionally uncommitted and profile-local. It follows the active
    SHAY_HOME so restores remain path-correct when profile roots move.
    """
    guard_dir = _identity_guard_dir()
    emergency_dir = _emergency_dir()
    guard_dir.mkdir(parents=True, exist_ok=True)
    emergency_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    version = int(manifest.get("current_version") or 0) + 1
    version_dir = guard_dir / "versions" / f"v{version:05d}"
    version_dir.mkdir(parents=True, exist_ok=True)

    files_meta: dict[str, Any] = {}
    for spec in IDENTITY_SPECS:
        src = _spec_actual_path(spec)
        if not src.exists():
            continue
        dest = _spec_emergency_path(spec)
        _safe_copy_replace(src, dest, lock_after=True)

        version_dest = version_dir / spec.emergency_name
        _safe_copy_replace(src, version_dest, lock_after=True)

        content = _read_text(src)
        files_meta[spec.relative_path] = {
            "actual_path": str(src),
            "emergency_path": str(dest),
            "version_path": str(version_dest),
            "sha256": _sha256_text(content),
            "required_snippets": list(spec.required_snippets),
            "last_snapshot_reason": reason,
            "snapshot_at": int(time.time()),
        }

    manifest["current_version"] = version
    manifest["files"] = files_meta
    save_manifest(manifest)
    _current_version_path().write_text(f"v{version:05d}\n", encoding="utf-8")
    return manifest


def _findings_for_spec(spec: IdentityFileSpec, manifest_files: dict[str, Any]) -> list[IdentityFinding]:
    findings: list[IdentityFinding] = []
    actual = _spec_actual_path(spec)
    emergency = _spec_emergency_path(spec)

    if not actual.exists():
        findings.append(
            IdentityFinding(
                severity="critical",
                code="missing_file",
                path=str(actual),
                message=f"Required identity file is missing: {spec.relative_path}",
            )
        )
        if not emergency.exists():
            findings.append(
                IdentityFinding(
                    severity="critical",
                    code="missing_emergency_backup",
                    path=str(emergency),
                    message=f"Emergency backup is also missing for {spec.relative_path}",
                )
            )
        return findings

    try:
        content = _read_text(actual)
    except Exception as exc:
        findings.append(
            IdentityFinding(
                severity="critical",
                code="unreadable_file",
                path=str(actual),
                message=f"Could not read identity file {spec.relative_path}: {exc}",
            )
        )
        return findings

    missing = [snippet for snippet in spec.required_snippets if snippet not in content]
    if missing:
        findings.append(
            IdentityFinding(
                severity="critical",
                code="missing_required_snippets",
                path=str(actual),
                message=f"Identity file drifted: required authority lines missing in {spec.relative_path}",
                missing_snippets=missing,
            )
        )

    expected_hash = None
    meta = manifest_files.get(spec.relative_path)
    if isinstance(meta, dict):
        expected_hash = meta.get("sha256")
    actual_hash = _sha256_text(content)
    if expected_hash and expected_hash != actual_hash:
        findings.append(
            IdentityFinding(
                severity="warning",
                code="hash_changed",
                path=str(actual),
                message=f"Identity file changed since last protected snapshot: {spec.relative_path}",
            )
        )
    return findings


def verify_identity_files() -> IdentityAuditResult:
    manifest = load_manifest()
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    findings: list[IdentityFinding] = []
    for spec in IDENTITY_SPECS:
        findings.extend(_findings_for_spec(spec, manifest_files))
    return IdentityAuditResult(
        ok=not any(f.severity == "critical" for f in findings),
        shay_home=str(_home()),
        findings=findings,
        manifest_path=str(_manifest_path()),
        emergency_dir=str(_emergency_dir()),
    )


def restore_from_emergency(relative_path: str) -> Path:
    spec = next((s for s in IDENTITY_SPECS if s.relative_path == relative_path), None)
    if spec is None:
        raise ValueError(f"Unknown identity file: {relative_path}")
    emergency = _spec_emergency_path(spec)
    if not emergency.exists():
        raise FileNotFoundError(f"No emergency backup for {relative_path} at {emergency}")
    actual = _spec_actual_path(spec)
    actual.parent.mkdir(parents=True, exist_ok=True)
    _safe_copy_replace(emergency, actual, lock_after=False)
    return actual


def auto_restore_missing_files() -> list[str]:
    restored: list[str] = []
    for spec in IDENTITY_SPECS:
        actual = _spec_actual_path(spec)
        if actual.exists():
            continue
        emergency = _spec_emergency_path(spec)
        if not emergency.exists():
            continue
        actual.parent.mkdir(parents=True, exist_ok=True)
        _safe_copy_replace(emergency, actual, lock_after=False)
        restored.append(spec.relative_path)
    return restored


def lock_identity_backups() -> list[str]:
    locked: list[str] = []
    manifest = load_manifest()
    for meta in manifest.get("files", {}).values():
        if not isinstance(meta, dict):
            continue
        for key in ("emergency_path", "version_path"):
            raw = meta.get(key)
            if not raw:
                continue
            path = Path(str(raw))
            if not path.exists():
                continue
            _set_immutable_flag(path, locked=True)
            locked.append(str(path))
    return locked


def unlock_identity_backups() -> list[str]:
    unlocked: list[str] = []
    manifest = load_manifest()
    for meta in manifest.get("files", {}).values():
        if not isinstance(meta, dict):
            continue
        for key in ("emergency_path", "version_path"):
            raw = meta.get(key)
            if not raw:
                continue
            path = Path(str(raw))
            if not path.exists():
                continue
            _set_immutable_flag(path, locked=False)
            unlocked.append(str(path))
    return unlocked


def _recovery_interview_markdown(result: IdentityAuditResult, restored: list[str]) -> str:
    bullets = []
    for finding in result.findings:
        bullets.append(f"- [{finding.severity}] {finding.message}")
        if finding.missing_snippets:
            for snippet in finding.missing_snippets:
                bullets.append(f"  - missing: {snippet}")
    restored_line = "\n".join(f"- auto-restored: {name}" for name in restored) or "- auto-restored: none"
    return textwrap.dedent(
        f"""
        # Shay identity recovery interview

        SHAY_HOME: {result.shay_home}
        Manifest: {result.manifest_path}
        Emergency dir: {result.emergency_dir}

        Findings:
        {chr(10).join(bullets) if bullets else '- none'}

        Restore actions:
        {restored_line}

        Next-step interview with Fritz:
        1. Do we trust the current live file contents?
        2. If not, restore from emergency backup, versioned snapshot, or vault copy?
        3. Were file locations changed intentionally and should the manifest be resynced?
        4. Did authority hierarchy drift, and what exact lines must be reinstated?
        5. After repair, run a fresh protected snapshot to lock the new baseline.
        """
    ).strip() + "\n"


def _incident_signature(result: IdentityAuditResult, restored: list[str]) -> dict[str, Any]:
    findings_payload = []
    for finding in result.findings:
        findings_payload.append(
            {
                "severity": finding.severity,
                "code": finding.code,
                "path": Path(finding.path).name,
                "missing_snippets": sorted(finding.missing_snippets or []),
            }
        )
    findings_payload.sort(key=lambda item: (item["severity"], item["code"], item["path"]))
    return {
        "findings": findings_payload,
        "auto_restored": sorted(restored),
    }


def _load_latest_incident_signature() -> tuple[dict[str, Any] | None, int | None]:
    incident_dir = _incident_dir()
    if not incident_dir.exists():
        return None, None
    incident_files = sorted(incident_dir.glob("identity-incident-*.json"))
    if not incident_files:
        return None, None
    latest = incident_files[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    normalized_findings = []
    for finding in payload.get("findings", []):
        if not isinstance(finding, dict):
            continue
        normalized_findings.append(
            {
                "severity": finding.get("severity"),
                "code": finding.get("code"),
                "path": Path(str(finding.get("path", ""))).name,
                "missing_snippets": sorted(finding.get("missing_snippets") or []),
            }
        )
    normalized_findings.sort(key=lambda item: (item["severity"], item["code"], item["path"]))
    signature = {
        "findings": normalized_findings,
        "auto_restored": sorted(payload.get("auto_restored", [])),
    }
    return signature, int(latest.stat().st_mtime)


def _is_duplicate_incident(result: IdentityAuditResult, restored: list[str]) -> bool:
    cooldown = _incident_dedup_cooldown_seconds()
    if cooldown <= 0:
        return False
    latest_signature, latest_ts = _load_latest_incident_signature()
    if latest_signature is None or latest_ts is None:
        return False
    if time.time() - latest_ts > cooldown:
        return False
    return latest_signature == _incident_signature(result, restored)


def _write_incident(result: IdentityAuditResult, restored: list[str]) -> IdentityAuditResult:
    incident_dir = _incident_dir()
    incident_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    incident_path = incident_dir / f"identity-incident-{stamp}.json"
    interview_path = incident_dir / f"identity-recovery-interview-{stamp}.md"
    payload = result.to_dict()
    payload["auto_restored"] = restored
    _write_json(incident_path, payload)
    interview_path.write_text(_recovery_interview_markdown(result, restored), encoding="utf-8")
    result.incident_path = str(incident_path)
    result.interview_path = str(interview_path)
    return result


def _stderr_alert(result: IdentityAuditResult, restored: list[str]) -> None:
    lines = [
        "[shay identity guard] CRITICAL identity drift detected.",
        f"SHAY_HOME: {result.shay_home}",
    ]
    for finding in result.findings:
        lines.append(f"- {finding.severity.upper()}: {finding.message}")
    if restored:
        lines.append("- AUTO-RESTORED: " + ", ".join(restored))
    if result.interview_path:
        lines.append(f"- Recovery interview: {result.interview_path}")
    sys.stderr.write("\n".join(lines) + "\n")
    sys.stderr.flush()


def _home_target_candidates() -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    env_map = {
        "telegram": "TELEGRAM_HOME_CHANNEL",
        "discord": "DISCORD_HOME_CHANNEL",
        "slack": "SLACK_HOME_CHANNEL",
        "signal": "SIGNAL_HOME_CHANNEL",
        "matrix": "MATRIX_HOME_ROOM",
    }
    for platform, env_name in env_map.items():
        value = os.getenv(env_name, "").strip()
        if value:
            candidates.append((platform, value))
    return candidates


async def _send_home_alert_async(message: str) -> Optional[str]:
    try:
        from gateway.config import load_gateway_config, Platform
        from tools.send_message_tool import _send_to_platform
    except Exception as exc:
        return f"import failure: {exc}"

    targets = _home_target_candidates()
    if not targets:
        return "no home channel configured"

    try:
        config = load_gateway_config()
    except Exception as exc:
        return f"gateway config load failed: {exc}"

    errors: list[str] = []
    for platform_name, chat_id in targets:
        try:
            platform = Platform(platform_name)
            pconfig = config.platforms.get(platform)
            if not pconfig or not pconfig.enabled:
                errors.append(f"{platform_name}: not enabled")
                continue
            result = await _send_to_platform(platform, pconfig, chat_id, message)
            if result and result.get("error"):
                errors.append(f"{platform_name}: {result['error']}")
                continue
            return None
        except Exception as exc:
            errors.append(f"{platform_name}: {exc}")
    return "; ".join(errors) if errors else "unknown send failure"


def send_home_alert(message: str) -> Optional[str]:
    try:
        return asyncio.run(_send_home_alert_async(message))
    except RuntimeError:
        return "event loop already running"
    except Exception as exc:
        return str(exc)


def startup_identity_check(*, send_alert: bool = True, auto_restore_missing: bool = True) -> IdentityAuditResult:
    """Run at CLI/gateway startup.

    Healthy path:
    - ensure protected snapshot exists and refresh it when all files are present

    Drift path:
    - auto-restore missing files from emergency backup when possible
    - write incident + recovery interview
    - alert via stderr and optional home-channel send
    """
    _identity_guard_dir().mkdir(parents=True, exist_ok=True)
    _incident_dir().mkdir(parents=True, exist_ok=True)

    # First-run bootstrap: create snapshot if we don't have one yet and all files exist.
    manifest = load_manifest()
    if not manifest.get("files"):
        all_present = all(_spec_actual_path(spec).exists() for spec in IDENTITY_SPECS)
        if all_present:
            ensure_identity_snapshot(reason="bootstrap")

    restored = auto_restore_missing_files() if auto_restore_missing else []
    result = verify_identity_files()

    if result.ok and not restored:
        ensure_identity_snapshot(reason="startup-ok")
        return result

    if restored:
        result = verify_identity_files()

    if _is_duplicate_incident(result, restored):
        return result

    result = _write_incident(result, restored)
    _stderr_alert(result, restored)

    if send_alert:
        summary = [f"Shay identity guard tripped on {Path(result.shay_home).name}."]
        for finding in result.findings[:5]:
            summary.append(f"- {finding.severity}: {finding.code} @ {Path(finding.path).name}")
        if restored:
            summary.append("- auto-restored: " + ", ".join(restored))
        if result.interview_path:
            summary.append(f"- recovery interview: {result.interview_path}")
        send_home_alert("\n".join(summary))

    # Refresh snapshot after successful missing-file restore; do NOT bless snippet-drift automatically.
    if restored and result.ok:
        ensure_identity_snapshot(reason="startup-auto-restore")
    return result
