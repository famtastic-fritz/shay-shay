#!/usr/bin/env python3
"""Read-only audit of ~/.shay/shay.db.

Inspects:
- whether ~/.shay/shay.db exists
- file size and basic metadata
- whether SQLite can open it read-only
- table/object list and schema, if any
- whether it appears empty, corrupt, dormant, or active

This script never writes to ~/.shay/shay.db, ~/.shay/state.db, or ~/.shay/sessions/.
It prints a JSON summary to stdout.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def classify_status(exists: bool, size_bytes: int | None, sqlite_open: bool, sqlite_error: str | None, objects: list[dict[str, Any]]) -> str:
    if not exists:
        return "missing"
    if sqlite_error:
        return "corrupt_or_not_sqlite"
    if sqlite_open and size_bytes == 0 and not objects:
        return "dormant_empty_placeholder"
    if sqlite_open and not objects:
        return "empty_sqlite_db"
    if sqlite_open and objects:
        return "active_or_structured_db"
    return "unknown"


def main() -> None:
    shay_db_path = Path.home() / ".shay" / "shay.db"
    result: dict[str, Any] = {
        "audit_timestamp": utc_now_iso(),
        "path": str(shay_db_path),
        "exists": shay_db_path.exists(),
        "size_bytes": None,
        "sha256": None,
        "sqlite_open": False,
        "sqlite_error": None,
        "integrity_check": None,
        "objects": [],
        "table_names": [],
        "schema_sql": {},
        "classification": None,
        "notes": [],
    }

    if not shay_db_path.exists():
        result["classification"] = "missing"
        result["notes"].append("shay.db does not exist at audit time")
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    stat = shay_db_path.stat()
    result["size_bytes"] = stat.st_size
    result["sha256"] = sha256_file(shay_db_path)

    try:
        conn = sqlite3.connect(f"file:{shay_db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        result["sqlite_open"] = True

        try:
            cur.execute("PRAGMA integrity_check;")
            row = cur.fetchone()
            result["integrity_check"] = row[0] if row else None
        except Exception as exc:
            result["integrity_check"] = f"error: {exc}"

        rows = cur.execute(
            """
            SELECT name, type, tbl_name, sql
            FROM sqlite_master
            WHERE type IN ('table', 'index', 'view', 'trigger')
            ORDER BY type, name
            """
        ).fetchall()

        objects = []
        schema_sql: dict[str, str | None] = {}
        table_names: list[str] = []
        for name, obj_type, tbl_name, sql in rows:
            objects.append(
                {
                    "name": name,
                    "type": obj_type,
                    "table_name": tbl_name,
                    "has_sql": sql is not None,
                }
            )
            schema_sql[name] = sql
            if obj_type == "table":
                table_names.append(name)

        result["objects"] = objects
        result["table_names"] = table_names
        result["schema_sql"] = schema_sql
        conn.close()
    except Exception as exc:
        result["sqlite_error"] = repr(exc)

    result["classification"] = classify_status(
        exists=result["exists"],
        size_bytes=result["size_bytes"],
        sqlite_open=result["sqlite_open"],
        sqlite_error=result["sqlite_error"],
        objects=result["objects"],
    )

    if result["classification"] == "dormant_empty_placeholder":
        result["notes"].append("File exists, opens in SQLite read-only mode, contains no objects, and has 0 bytes")
        result["notes"].append("This shape is consistent with a dormant placeholder rather than an active runtime database")
    elif result["classification"] == "empty_sqlite_db":
        result["notes"].append("File opens in SQLite read-only mode but currently has no schema objects")
    elif result["classification"] == "active_or_structured_db":
        result["notes"].append("Database contains schema objects and may have a runtime role")
    elif result["classification"] == "corrupt_or_not_sqlite":
        result["notes"].append("File exists but could not be opened as a read-only SQLite database")

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
