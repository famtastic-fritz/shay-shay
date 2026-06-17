from __future__ import annotations

import json
from pathlib import Path

from identity_guard import (
    IDENTITY_SPECS,
    _identity_guard_mode,
    ensure_identity_snapshot,
    load_manifest,
    lock_identity_backups,
    restore_from_emergency,
    unlock_identity_backups,
    verify_identity_files,
)


def _display_name(relative_path: str) -> str:
    if relative_path == "memories/USER.md":
        return "USER.md"
    return Path(relative_path).name


def _status_payload() -> dict:
    manifest = load_manifest()
    audit = verify_identity_files()
    files = []
    meta_map = manifest.get("files", {}) if isinstance(manifest.get("files"), dict) else {}
    for spec in IDENTITY_SPECS:
        actual = Path(audit.shay_home) / spec.relative_path
        meta = meta_map.get(spec.relative_path, {}) if isinstance(meta_map.get(spec.relative_path), dict) else {}
        emergency = Path(str(meta.get("emergency_path", ""))) if meta.get("emergency_path") else None
        version = Path(str(meta.get("version_path", ""))) if meta.get("version_path") else None
        files.append(
            {
                "relative_path": spec.relative_path,
                "display_name": _display_name(spec.relative_path),
                "actual_path": str(actual),
                "actual_exists": actual.exists(),
                "emergency_path": str(emergency) if emergency else None,
                "emergency_exists": emergency.exists() if emergency else False,
                "version_path": str(version) if version else None,
                "version_exists": version.exists() if version else False,
            }
        )
    return {
        "ok": audit.ok,
        "mode": _identity_guard_mode(),
        "shay_home": audit.shay_home,
        "manifest_path": audit.manifest_path,
        "emergency_dir": audit.emergency_dir,
        "current_version": manifest.get("current_version"),
        "findings": [finding.to_dict() for finding in audit.findings],
        "files": files,
    }


def _print_status(payload: dict) -> None:
    if payload["ok"] and payload["findings"]:
        status = "WARN"
    else:
        status = "OK" if payload["ok"] else "DRIFT"
    print(f"Identity status: {status}")
    print(f"Mode: {payload['mode']}")
    print(f"SHAY_HOME: {payload['shay_home']}")
    print(f"Manifest: {payload['manifest_path']}")
    print(f"Emergency dir: {payload['emergency_dir']}")
    print(f"Current version: v{int(payload['current_version'] or 0):05d}")
    print("")
    for item in payload["files"]:
        print(f"- {item['display_name']}: live={'yes' if item['actual_exists'] else 'no'}, emergency={'yes' if item['emergency_exists'] else 'no'}, version={'yes' if item['version_exists'] else 'no'}")
    if payload["findings"]:
        print("")
        print("Findings:")
        for finding in payload["findings"]:
            print(f"- {finding['severity']}: {finding['code']} :: {finding['message']}")
            for snippet in finding.get("missing_snippets", []) or []:
                print(f"  missing: {snippet}")


def cmd_identity(args) -> int:
    command = getattr(args, "identity_command", None) or "status"

    if command == "status":
        payload = _status_payload()
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            _print_status(payload)
        return 0 if payload["ok"] else 1

    if command == "snapshot":
        manifest = ensure_identity_snapshot(reason=getattr(args, "reason", None) or "manual")
        print(f"Identity snapshot saved: v{int(manifest.get('current_version') or 0):05d}")
        print(f"Manifest: {Path.home() / '.shay' / 'private' / 'identity-guard' / 'identity-manifest.json'}")
        return 0

    if command == "restore":
        target = getattr(args, "target", None)
        restored = restore_from_emergency(target)
        print(f"Restored {target} -> {restored}")
        return 0

    if command == "lock":
        locked = lock_identity_backups()
        print(f"Locked {len(locked)} identity backup files.")
        for path in locked:
            print(f"- {path}")
        return 0

    if command == "unlock":
        unlocked = unlock_identity_backups()
        print(f"Unlocked {len(unlocked)} identity backup files.")
        for path in unlocked:
            print(f"- {path}")
        return 0

    raise SystemExit(f"Unknown identity command: {command}")
