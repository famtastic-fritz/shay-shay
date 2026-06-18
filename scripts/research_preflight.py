#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

HOME = Path(os.environ.get("HOME", str(Path.home()))).expanduser()
DEFAULT_ROOT = Path(
    os.environ.get(
        "SHAY_RESEARCH_ROOT",
        str(HOME / "famtastic/obsidian/Shay-Memory/research"),
    )
).expanduser()
DEFAULT_LEDGER = Path(
    os.environ.get(
        "SHAY_RESEARCH_LEDGER",
        str(DEFAULT_ROOT / "_ledger/research-artifacts.jsonl"),
    )
).expanduser()
DEFAULT_REGISTRY = Path(
    os.environ.get(
        "SHAY_RESEARCH_REGISTRY",
        str(DEFAULT_ROOT / "_ledger/research-registry.jsonl"),
    )
).expanduser()
DEFAULT_STATE_DB = Path(
    os.environ.get(
        "SHAY_STATE_DB",
        str(HOME / ".shay/state.db"),
    )
).expanduser()

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
}


@dataclass
class MatchRecord:
    title: str
    path: str
    permalink: str
    summary: str
    question: str
    created_at: str
    tags: list[str]
    freshness: str
    verdict: str
    related_topics: list[str]
    source: str
    score: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "path": self.path,
            "permalink": self.permalink,
            "summary": self.summary,
            "question": self.question,
            "created_at": self.created_at,
            "tags": self.tags,
            "freshness": self.freshness,
            "verdict": self.verdict,
            "related_topics": self.related_topics,
            "source": self.source,
            "score": round(self.score, 4),
            "reasons": self.reasons,
        }


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "research"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def topic_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in STOP_WORDS and len(token) > 1
    ]


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = normalize_text(str(value))
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(item)
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _registry_candidates(registry_path: Path, ledger_path: Path) -> list[dict[str, Any]]:
    registry_rows = _read_jsonl(registry_path)
    if registry_rows:
        return registry_rows
    return _read_jsonl(ledger_path)


def _coerce_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return unique_strings(str(item) for item in raw)
    if isinstance(raw, str):
        return unique_strings(part for part in raw.split(","))
    return []


def _coerce_topics(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return unique_strings(str(item) for item in raw)
    if isinstance(raw, str):
        return unique_strings(part for part in raw.split(","))
    return []


def _build_match(record: dict[str, Any], source: str, score: float, reasons: list[str]) -> MatchRecord:
    return MatchRecord(
        title=normalize_text(record.get("title", "")),
        path=str(record.get("path", "")),
        permalink=str(record.get("permalink", "")),
        summary=normalize_text(record.get("summary", "")),
        question=normalize_text(record.get("question", "")),
        created_at=str(record.get("created_at", "")),
        tags=_coerce_tags(record.get("tags", [])),
        freshness=normalize_text(record.get("freshness", "unknown")) or "unknown",
        verdict=normalize_text(record.get("verdict", "unknown")) or "unknown",
        related_topics=_coerce_topics(record.get("related_topics", [])),
        source=source,
        score=score,
        reasons=unique_strings(reasons),
    )


def _score_record(topic: str, topic_key: str, topic_terms: list[str], record: dict[str, Any], source: str) -> MatchRecord | None:
    title = normalize_text(record.get("title", ""))
    summary = normalize_text(record.get("summary", ""))
    question = normalize_text(record.get("question", ""))
    tags = _coerce_tags(record.get("tags", []))
    related_topics = _coerce_topics(record.get("related_topics", []))
    haystacks = [title, summary, question, " ".join(tags), " ".join(related_topics)]
    searchable = " ".join(haystacks).lower()
    reasons: list[str] = []
    score = 0.0

    lowered_topic = topic.lower()
    lowered_key = topic_key.lower()
    if lowered_topic and lowered_topic in searchable:
        score += 6.0
        reasons.append("exact topic phrase found")
    elif lowered_key and lowered_key.replace("-", " ") in searchable:
        score += 5.0
        reasons.append("normalized topic phrase found")

    matched_terms = [term for term in topic_terms if term in searchable]
    if matched_terms:
        score += min(4.0, len(matched_terms) * 1.25)
        reasons.append(f"shared terms: {', '.join(matched_terms[:6])}")

    for tag in tags:
        tag_key = slugify(tag)
        if tag_key == topic_key or tag.lower() == lowered_topic:
            score += 2.0
            reasons.append(f"tag match: {tag}")
            break

    for related in related_topics:
        related_key = slugify(related)
        if related_key == topic_key or related.lower() == lowered_topic:
            score += 1.5
            reasons.append(f"related topic match: {related}")
            break

    if score <= 0:
        return None
    return _build_match(record, source, score, reasons)


def _search_registry(topic: str, limit: int, registry_path: Path, ledger_path: Path) -> list[MatchRecord]:
    topic_key = slugify(topic)
    terms = topic_tokens(topic)
    matches: list[MatchRecord] = []
    for record in _registry_candidates(registry_path, ledger_path):
        match = _score_record(topic, topic_key, terms, record, source="registry")
        if match is not None:
            matches.append(match)
    matches.sort(key=lambda item: (-item.score, item.created_at), reverse=False)
    matches.sort(key=lambda item: item.score, reverse=True)
    return matches[:limit]


def _search_notes(topic: str, limit: int, root: Path, seen_paths: set[str]) -> list[MatchRecord]:
    topic_key = slugify(topic)
    terms = topic_tokens(topic)
    matches: list[MatchRecord] = []
    if not root.exists():
        return matches
    for path in root.glob("*.md"):
        if str(path) in seen_paths:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        title_match = re.search(r"^title:\s*(.+)$", text, flags=re.MULTILINE)
        summary_match = re.search(r"^summary:\s*(.+)$", text, flags=re.MULTILINE)
        question_match = re.search(r"^question:\s*(.+)$", text, flags=re.MULTILINE)
        permalink_match = re.search(r"^permalink:\s*(.+)$", text, flags=re.MULTILINE)
        created_match = re.search(r"^created_at:\s*(.+)$", text, flags=re.MULTILINE)
        record = {
            "title": title_match.group(1).strip() if title_match else path.stem,
            "summary": summary_match.group(1).strip() if summary_match else "",
            "question": question_match.group(1).strip() if question_match else "",
            "permalink": permalink_match.group(1).strip() if permalink_match else "",
            "path": str(path),
            "created_at": created_match.group(1).strip() if created_match else "",
        }
        match = _score_record(topic, topic_key, terms, record, source="note-scan")
        if match is not None:
            matches.append(match)
    matches.sort(key=lambda item: item.score, reverse=True)
    return matches[:limit]


def _search_state_db(topic: str, limit: int, state_db_path: Path) -> list[dict[str, Any]]:
    if not state_db_path.exists():
        return []
    query = " OR ".join(unique_strings(topic_tokens(topic))) or topic.strip()
    if not query:
        return []
    sql = """
        SELECT m.session_id,
               s.title,
               s.source,
               s.started_at,
               substr(COALESCE(m.content, ''), 1, 240) AS preview
        FROM messages_fts f
        JOIN messages m ON m.id = f.rowid
        JOIN sessions s ON s.id = m.session_id
        WHERE messages_fts MATCH ?
        ORDER BY bm25(messages_fts), m.timestamp DESC
        LIMIT ?
    """
    try:
        conn = sqlite3.connect(str(state_db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, (query, limit)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        session_id = str(row["session_id"])
        if session_id in seen:
            continue
        seen.add(session_id)
        results.append(
            {
                "session_id": session_id,
                "title": row["title"] or "",
                "source": row["source"] or "",
                "started_at": row["started_at"] or "",
                "preview": normalize_text(row["preview"] or ""),
            }
        )
    return results


def _compute_verdict(matches: list[MatchRecord]) -> str:
    if not matches:
        return "new topic"
    top = matches[0]
    if top.score >= 6.0:
        return "already researched"
    return "partially researched"


def _compute_recommendation(verdict: str, session_hits: list[dict[str, Any]]) -> str:
    if verdict == "already researched":
        return "Open the strongest existing artifact first. Only do net-new research if the stored freshness/verdict is stale or incomplete."
    if verdict == "partially researched":
        if session_hits:
            return "Review the prior artifacts and matching sessions, then continue only on the uncovered delta."
        return "Review the prior artifacts, then continue research only on the missing slice."
    return "No strong prior research artifact found. Proceed with net-new research and capture it before finalizing."


def main() -> int:
    ap = argparse.ArgumentParser(description="Research preflight: check prior artifacts before starting new research.")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--research-root", default=str(DEFAULT_ROOT))
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args()

    root = Path(args.research_root).expanduser()
    ledger = Path(args.ledger).expanduser()
    registry = Path(args.registry).expanduser()
    state_db = Path(args.state_db).expanduser()
    limit = max(1, min(int(args.limit), 20))

    artifact_matches = _search_registry(args.topic, limit, registry, ledger)
    seen_paths = {match.path for match in artifact_matches if match.path}
    note_matches = _search_notes(args.topic, limit, root, seen_paths)
    all_matches = sorted(artifact_matches + note_matches, key=lambda item: item.score, reverse=True)[:limit]
    verdict = _compute_verdict(all_matches)
    session_hits = _search_state_db(args.topic, limit, state_db)

    payload = {
        "topic": args.topic,
        "verdict": verdict,
        "recommendation": _compute_recommendation(verdict, session_hits),
        "artifact_matches": [match.to_dict() for match in all_matches],
        "session_hits": session_hits,
        "paths_checked": {
            "research_root": str(root),
            "ledger": str(ledger),
            "registry": str(registry),
            "state_db": str(state_db),
        },
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Topic: {args.topic}")
    print(f"Verdict: {verdict}")
    print(f"Recommendation: {payload['recommendation']}")
    print("")
    print("Artifact matches:")
    if all_matches:
        for match in all_matches:
            print(f"- {match.title or '(untitled)'}")
            print(f"  path: {match.path or 'unknown'}")
            print(f"  score: {match.score:.2f}")
            print(f"  freshness: {match.freshness}")
            print(f"  verdict: {match.verdict}")
            print(f"  reasons: {', '.join(match.reasons) if match.reasons else 'none'}")
    else:
        print("- none")
    print("")
    print("Session hits:")
    if session_hits:
        for hit in session_hits:
            label = hit['title'] or hit['session_id']
            print(f"- {label} [{hit['source'] or 'unknown'}] — {hit['preview']}")
    else:
        print("- none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
