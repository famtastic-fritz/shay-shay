#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

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


@dataclass
class SourceRecord:
    label: str
    location: str
    kind: str
    note: str = ""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "research-artifact"


def normalize_bullets(items: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        if item.startswith("- "):
            normalized.append(item[2:].strip())
        else:
            normalized.append(item)
    return normalized


def unique_strings(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


def parse_source(raw: str) -> SourceRecord:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 3:
        raise ValueError(
            "source must be 'label|location|kind' or 'label|location|kind|note'"
        )
    label, location, kind = parts[:3]
    note = parts[3] if len(parts) > 3 else ""
    if not label or not location or not kind:
        raise ValueError("source fields label, location, and kind must be non-empty")
    return SourceRecord(label=label, location=location, kind=kind, note=note)


def render_markdown(
    *,
    title: str,
    slug: str,
    created_at: str,
    summary: str,
    question: str,
    observations: list[str],
    interpretations: list[str],
    capabilities: list[str],
    sources: list[SourceRecord],
    next_actions: list[str],
    resume_sentence: str,
    tags: list[str],
    freshness: str,
    verdict: str,
    related_topics: list[str],
) -> str:
    source_lines = []
    for src in sources:
        suffix = f" — {src.note}" if src.note else ""
        source_lines.append(f"- {src.label} [{src.kind}] — {src.location}{suffix}")

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- none captured"

    tag_list = ", ".join(f'"{tag}"' for tag in tags)
    related_list = ", ".join(f'"{topic}"' for topic in related_topics)

    return f"""---
title: {title}
type: note
permalink: shay-memory/research/{slug}
created_at: {created_at}
summary: {summary}
question: {question}
resume_sentence: {resume_sentence}
freshness: {freshness}
verdict: {verdict}
related_topics: [{related_list}]
tags: [{tag_list}]
artifact_type: research-capture
---

# {title}

## Summary
{summary}

## Research question
{question}

## Reuse status
- freshness: {freshness}
- verdict: {verdict}
- related topics: {', '.join(related_topics) if related_topics else 'none captured'}

## Observations
{bullets(observations)}

## Interpretations
{bullets(interpretations)}

## Capability notes
{bullets(capabilities)}

## Sources
{chr(10).join(source_lines) if source_lines else '- none captured'}

## Next actions
{bullets(next_actions)}

## Resume prompt
{resume_sentence}
"""


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Create a durable research artifact with observation vs interpretation separation."
    )
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--observation", action="append", default=[])
    ap.add_argument("--interpretation", action="append", default=[])
    ap.add_argument("--capability", action="append", default=[])
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--next-action", action="append", default=[])
    ap.add_argument("--resume-sentence", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--related-topic", action="append", default=[])
    ap.add_argument("--freshness", default="current")
    ap.add_argument("--verdict", default="captured")
    ap.add_argument("--output-dir", default=str(DEFAULT_ROOT))
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    args = ap.parse_args()

    if not args.observation:
        print("at least one --observation is required", file=sys.stderr)
        return 2
    if not args.interpretation:
        print("at least one --interpretation is required", file=sys.stderr)
        return 2

    created = datetime.now(timezone.utc)
    created_at = created.isoformat()
    date_slug = created.strftime("%Y-%m-%d")
    base_slug = args.slug.strip() or slugify(args.title)
    slug = f"{base_slug}-{date_slug}"
    resume_sentence = (
        args.resume_sentence.strip()
        or f"Open shay-memory/research/{slug} and continue from the observations, capability notes, and next actions."
    )

    observations = normalize_bullets(args.observation)
    interpretations = normalize_bullets(args.interpretation)
    capabilities = normalize_bullets(args.capability)
    next_actions = normalize_bullets(args.next_action)
    sources = [parse_source(raw) for raw in args.source]
    tags = sorted(
        {
            "research",
            "shay-memory",
            "observation-vs-interpretation",
            *(slugify(tag) for tag in args.tag if tag.strip()),
        }
    )
    related_topics = unique_strings(args.related_topic)
    freshness = args.freshness.strip() or "current"
    verdict = args.verdict.strip() or "captured"

    md = render_markdown(
        title=args.title.strip(),
        slug=slug,
        created_at=created_at,
        summary=args.summary.strip(),
        question=args.question.strip(),
        observations=observations,
        interpretations=interpretations,
        capabilities=capabilities,
        sources=sources,
        next_actions=next_actions,
        resume_sentence=resume_sentence,
        tags=tags,
        freshness=freshness,
        verdict=verdict,
        related_topics=related_topics,
    )

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}.md"
    output_path.write_text(md, encoding="utf-8")

    ledger_payload = {
        "created_at": created_at,
        "title": args.title.strip(),
        "slug": slug,
        "summary": args.summary.strip(),
        "question": args.question.strip(),
        "path": str(output_path),
        "permalink": f"shay-memory/research/{slug}",
        "observations": observations,
        "interpretations": interpretations,
        "capabilities": capabilities,
        "sources": [src.__dict__ for src in sources],
        "tags": tags,
        "next_actions": next_actions,
        "resume_sentence": resume_sentence,
        "freshness": freshness,
        "verdict": verdict,
        "related_topics": related_topics,
    }
    registry_payload = {
        "created_at": created_at,
        "topic_key": base_slug,
        "title": args.title.strip(),
        "summary": args.summary.strip(),
        "question": args.question.strip(),
        "path": str(output_path),
        "permalink": f"shay-memory/research/{slug}",
        "tags": tags,
        "freshness": freshness,
        "verdict": verdict,
        "related_topics": related_topics,
        "resume_sentence": resume_sentence,
    }
    append_jsonl(Path(args.ledger).expanduser(), ledger_payload)
    append_jsonl(Path(args.registry).expanduser(), registry_payload)

    print(str(output_path))
    print(str(Path(args.ledger).expanduser()))
    print(str(Path(args.registry).expanduser()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
