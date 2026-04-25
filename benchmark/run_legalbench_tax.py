#!/usr/bin/env python3
"""LegalBench-Tax v0 evaluation runner stub.

Reads `eval_legalbench_tax_v0.jsonl` and reports the case distribution by
domain (CIT / VAT / IIT / MISC) plus sub-task breakdown. Designed to grow
into a full scorer that submits each `question` to the KG/MCP retrieval +
LLM answer pipeline and grades against `expected_answer` + `reasoning_anchors`.

Stage 0 (this file): distribution + schema validation only.
Stage 1 (next session): wire to /api/v1/query + LLM judge.
Stage 2 (Day 75): score + diff vs Claude Opus 4.7 baseline (70.3% on VALS.ai).

Usage:
    python benchmark/run_legalbench_tax.py
    python benchmark/run_legalbench_tax.py --file benchmark/eval_legalbench_tax_v0.jsonl

SOTA gap doc cross-ref: §Day 61-75 — "Build private 100-case Chinese tax
eval set (CIT 30 / VAT 30 / IIT 20 / 小税种 20)". v0 ships 20 cases (5 per
domain) as the structural framework; domain expert extends to 100.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED_FIELDS = {
    "id",
    "domain",
    "sub_task",
    "difficulty",
    "question",
    "expected_answer",
    "reasoning_anchors",
    "sources",
    "author",
    "authored_at",
}

ALLOWED_DOMAINS = {"CIT", "VAT", "IIT", "MISC"}
ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}

TARGET_DISTRIBUTION = {"CIT": 30, "VAT": 30, "IIT": 20, "MISC": 20}


def validate_record(rec: dict, lineno: int) -> list[str]:
    """Return list of validation errors for a single record."""
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(rec.keys())
    if missing:
        errors.append(f"line {lineno}: missing fields {missing}")
    if rec.get("domain") not in ALLOWED_DOMAINS:
        errors.append(
            f"line {lineno}: domain={rec.get('domain')!r} not in {ALLOWED_DOMAINS}"
        )
    if rec.get("difficulty") not in ALLOWED_DIFFICULTY:
        errors.append(
            f"line {lineno}: difficulty={rec.get('difficulty')!r} not in {ALLOWED_DIFFICULTY}"
        )
    if not isinstance(rec.get("reasoning_anchors"), list):
        errors.append(f"line {lineno}: reasoning_anchors must be list")
    if not isinstance(rec.get("sources"), list):
        errors.append(f"line {lineno}: sources must be list")
    return errors


def load_eval(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {lineno}: invalid JSON: {exc}")
                continue
            errors.extend(validate_record(rec, lineno))
            records.append(rec)
    return records, errors


def report(records: list[dict]) -> dict:
    by_domain = Counter(r.get("domain") for r in records)
    by_difficulty = Counter(r.get("difficulty") for r in records)
    by_sub_task = Counter(r.get("sub_task") for r in records)
    coverage_pct = {
        d: round(by_domain.get(d, 0) / TARGET_DISTRIBUTION[d] * 100, 1)
        for d in ALLOWED_DOMAINS
    }
    return {
        "total_cases": len(records),
        "by_domain": dict(by_domain),
        "by_difficulty": dict(by_difficulty),
        "top_sub_tasks": dict(by_sub_task.most_common(10)),
        "target_distribution": TARGET_DISTRIBUTION,
        "coverage_pct_vs_target": coverage_pct,
        "remaining_to_target": {
            d: TARGET_DISTRIBUTION[d] - by_domain.get(d, 0) for d in ALLOWED_DOMAINS
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        default="benchmark/eval_legalbench_tax_v0.jsonl",
        help="JSONL eval file path",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on validation errors")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"[error] eval file not found: {path}", file=sys.stderr)
        return 2

    records, errors = load_eval(path)

    if errors:
        print(f"=== Validation errors ({len(errors)}) ===")
        for e in errors:
            print(f"  {e}")
        if args.strict:
            return 1

    summary = report(records)
    print("=== LegalBench-Tax v0 distribution ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
