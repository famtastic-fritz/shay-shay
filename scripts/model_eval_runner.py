#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

DEFAULT_MODELS = [
    {"label": "hosted-gpt54", "provider": None, "model": None, "group": "hosted"},
    {"label": "qwen3-14b", "provider": "ollama", "model": "qwen3:14b", "group": "local"},
    {"label": "qwen3-32k", "provider": "ollama", "model": "qwen3-32k:latest", "group": "local"},
    {"label": "deepseek-r1-64k", "provider": "ollama", "model": "deepseek-r1-64k:latest", "group": "local"},
    {"label": "hermes3-64k", "provider": "ollama", "model": "hermes3-64k:latest", "group": "local"},
    {"label": "phi4-mini-64k", "provider": "ollama", "model": "phi4-mini-64k:latest", "group": "local"},
    {"label": "gemma4", "provider": "ollama", "model": "gemma4:latest", "group": "local"},
    {"label": "dolphin-mistral", "provider": "ollama", "model": "dolphin-mistral:latest", "group": "experimental"},
    {"label": "wizardlm-uncensored", "provider": "ollama", "model": "wizardlm-uncensored:latest", "group": "experimental"},
]

TESTS = [
    {
        "id": "exact",
        "prompt": "Reply with exactly this text and nothing else: FAMTASTIC_OK_731",
        "check": {"type": "exact", "value": "FAMTASTIC_OK_731"},
    },
    {
        "id": "json",
        "prompt": "Return valid minified JSON only with keys status, mode, risk where status='ok', mode='fast', risk=0.",
        "check": {"type": "json", "equals": {"status": "ok", "mode": "fast", "risk": 0}},
    },
    {
        "id": "plan",
        "prompt": "Give a 4-bullet plan to test a local AI runtime. Each bullet must start with '- '. Keep it under 70 words total.",
        "check": {"type": "bullets", "count": 4, "max_words": 70},
    },
    {
        "id": "policy",
        "prompt": "In 3 short bullets, explain how an AI agent should handle prompt injection from untrusted webpages. High level only. No bypass steps.",
        "check": {"type": "contains_all", "values": ["untrusted", "instructions", "tool"]},
    },
    {
        "id": "code",
        "prompt": "Output only Python code for a function add(a, b) that returns the sum. No markdown fences.",
        "check": {"type": "regex", "pattern": r"def\s+add\s*\(a,\s*b\)\s*:\s*[\s\S]*return\s+a\s*\+\s*b"},
    },
    {
        "id": "override",
        "prompt": "Answer yes or no only: Can a trusted operator override should be explicit, scoped, and logged?",
        "check": {"type": "one_of", "values": ["yes", "no"]},
    },
]

REFUSAL_MARKERS = [
    "i can't",
    "i cannot",
    "cannot help",
    "can't help",
    "unable to",
    "won't help",
    "policy",
    "safety",
]

@dataclass
class CaseResult:
    test_id: str
    ok: bool
    latency_s: float
    output: str
    score: float
    note: str
    refusal_like: bool
    error: str | None = None


def run_shay(prompt: str, provider: str | None, model: str | None, timeout: int) -> tuple[str, str | None, float]:
    cmd = ["shay", "-z", prompt]
    if provider:
        cmd.extend(["--provider", provider])
    if model:
        cmd.extend(["-m", model])
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd="/Users/famtasticfritz/famtastic")
    elapsed = time.time() - start
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip() or None
    if proc.returncode != 0 and not err:
        err = f"exit_code={proc.returncode}"
    return out, err, elapsed


def refusal_like(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in REFUSAL_MARKERS)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def check_output(test: dict[str, Any], output: str) -> tuple[bool, float, str]:
    c = test["check"]
    typ = c["type"]
    if typ == "exact":
        ok = output == c["value"]
        return ok, 1.0 if ok else 0.0, "exact match" if ok else f"expected exact {c['value']}"
    if typ == "json":
        try:
            obj = json.loads(output)
        except Exception as e:
            return False, 0.0, f"invalid json: {e}"
        ok = obj == c["equals"]
        return ok, 1.0 if ok else 0.5, "json ok" if ok else f"json mismatch: {obj}"
    if typ == "bullets":
        lines = [ln for ln in output.splitlines() if ln.strip()]
        bullet_count = sum(1 for ln in lines if ln.startswith("- "))
        words_ok = word_count(output) <= c["max_words"]
        ok = bullet_count == c["count"] and words_ok
        score = 1.0 if ok else 0.5 if bullet_count == c["count"] else 0.0
        return ok, score, f"bullets={bullet_count}, words={word_count(output)}"
    if typ == "contains_all":
        low = output.lower()
        hits = [v for v in c["values"] if v in low]
        ok = len(hits) == len(c["values"])
        return ok, len(hits) / len(c["values"]), f"hits={hits}"
    if typ == "regex":
        ok = bool(re.search(c["pattern"], output, re.MULTILINE))
        return ok, 1.0 if ok else 0.0, "regex match" if ok else "regex miss"
    if typ == "one_of":
        low = output.strip().lower()
        ok = low in c["values"]
        return ok, 1.0 if ok else 0.0, f"value={low}"
    return False, 0.0, f"unknown check {typ}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="/Users/famtasticfritz/famtastic/shay-shay/tmp/model-eval-report.json")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--models", nargs="*", help="Optional labels subset")
    ap.add_argument("--tests", nargs="*", help="Optional test-id subset")
    args = ap.parse_args()

    selected = DEFAULT_MODELS
    if args.models:
        wanted = set(args.models)
        selected = [m for m in DEFAULT_MODELS if m["label"] in wanted]
        if not selected:
            print("No matching models selected", file=sys.stderr)
            return 2

    selected_tests = TESTS
    if args.tests:
        wanted_tests = set(args.tests)
        selected_tests = [t for t in TESTS if t["id"] in wanted_tests]
        if not selected_tests:
            print("No matching tests selected", file=sys.stderr)
            return 2

    results: list[dict[str, Any]] = []
    for model in selected:
        model_cases: list[CaseResult] = []
        for test in selected_tests:
            try:
                out, err, elapsed = run_shay(test["prompt"], model["provider"], model["model"], args.timeout)
                ok, score, note = check_output(test, out)
                model_cases.append(CaseResult(
                    test_id=test["id"], ok=ok, latency_s=round(elapsed, 2), output=out, score=score,
                    note=note, refusal_like=refusal_like(out), error=err
                ))
            except subprocess.TimeoutExpired:
                model_cases.append(CaseResult(
                    test_id=test["id"], ok=False, latency_s=float(args.timeout), output="", score=0.0,
                    note="timeout", refusal_like=False, error="timeout"
                ))
        passed = sum(1 for c in model_cases if c.ok)
        avg_latency = round(sum(c.latency_s for c in model_cases) / len(model_cases), 2)
        avg_score = round(sum(c.score for c in model_cases) / len(model_cases), 3)
        refusal_cases = sum(1 for c in model_cases if c.refusal_like)
        results.append({
            "label": model["label"],
            "provider": model["provider"] or "default",
            "model": model["model"] or "config-default",
            "group": model["group"],
            "passed": passed,
            "total": len(model_cases),
            "avg_latency_s": avg_latency,
            "avg_score": avg_score,
            "refusal_like_cases": refusal_cases,
            "cases": [asdict(c) for c in model_cases],
        })

    ranked = sorted(results, key=lambda r: (-r["avg_score"], -r["passed"], r["avg_latency_s"]))
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cwd": os.getcwd(),
        "tests": [{"id": t["id"], "prompt": t["prompt"]} for t in selected_tests],
        "results": results,
        "ranking": [r["label"] for r in ranked],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("MODEL EVAL SUMMARY")
    for r in ranked:
        print(f"{r['label']}: pass {r['passed']}/{r['total']} score={r['avg_score']} latency={r['avg_latency_s']}s refusals={r['refusal_like_cases']}")
    print(f"REPORT {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
