#!/usr/bin/env python3
"""LegalBench-Tax v0 evaluation runner — Stage 0 (validate) + Stage 1 (score).

Reads `eval_legalbench_tax_v0.jsonl` and either:

- **Stage 0 (default `--mode validate`)**: distribution + schema validation only
  (no API calls). Same as the original stub. Safe for CI / pre-commit.

- **Stage 1 dry-run (`--mode dry-run`)**: prints the request body that would be
  sent to the KG API for each case, without actually sending. Lets you inspect
  the wire shape before burning tokens. No external dependencies.

- **Stage 1 live (`--mode live`)**: POSTs each case's `question` to
  `${COGNEBULA_API_URL}/api/v1/chat` (default `http://localhost:8400`) with
  `mode: "rag"`, then scores the response on three deterministic dimensions:

    1. anchor_recall  — fraction of `reasoning_anchors` whose target-id
       substring appears in returned `sources` rows
    2. keyword_overlap — fraction of Chinese keywords from `expected_answer`
       found in returned `answer`
    3. source_citation — fraction of statutory `sources` (e.g. "CIT 法 §27")
       whose tokens appear in returned `answer`

  Composite score = arithmetic mean of the three dimensions. Outputs a JSON
  results file per case + per-domain + overall aggregates.

Stage 2 (Day 75 SOTA): replace deterministic scoring with LLM judge for
fuzzy semantic equivalence; diff vs Claude Opus 4.7 baseline (70.3% on
VALS.ai LegalBench-Tax leaderboard).

Usage:
    python benchmark/run_legalbench_tax.py                          # validate
    python benchmark/run_legalbench_tax.py --mode dry-run            # preview
    python benchmark/run_legalbench_tax.py --mode live --output r.json
    COGNEBULA_API_URL=http://localhost:8400 KG_API_KEY=... \
        python benchmark/run_legalbench_tax.py --mode live --limit 5

SOTA gap doc cross-ref: §Day 61-75 — "Build private 100-case Chinese tax
eval set". Status 2026-04-26: 100/100 cases authored (CIT 30 / VAT 30 /
IIT 20 / MISC 20). Stage 1 runner ready; --live requires user trigger.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
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
ALLOWED_MODES = {"validate", "dry-run", "live"}

TARGET_DISTRIBUTION = {"CIT": 30, "VAT": 30, "IIT": 20, "MISC": 20}

API_BASE_DEFAULT = os.environ.get("COGNEBULA_API_URL", "http://localhost:8400")
API_KEY = os.environ.get("KG_API_KEY", "")

# ---------------------------------------------------------------------------
# Stage 0 — validation
# ---------------------------------------------------------------------------


def validate_record(rec: dict, lineno: int) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(rec.keys())
    if missing:
        errors.append(f"line {lineno}: missing fields {missing}")
    if rec.get("domain") not in ALLOWED_DOMAINS:
        errors.append(f"line {lineno}: domain={rec.get('domain')!r} not in {ALLOWED_DOMAINS}")
    if rec.get("difficulty") not in ALLOWED_DIFFICULTY:
        errors.append(f"line {lineno}: difficulty={rec.get('difficulty')!r} not in {ALLOWED_DIFFICULTY}")
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


# ---------------------------------------------------------------------------
# Stage 1 — scoring helpers
# ---------------------------------------------------------------------------


# Chinese keyword extractor: 2+ char runs of CJK or alphanumeric tokens
# Filters single-char particles (的, 是, 等) which are noise.
_CJK_RE = re.compile(r"[一-鿿]{2,}|[A-Za-z][A-Za-z0-9_]+|\d+%?")
_NOISE_TOKENS = {
    "应纳", "应当", "可以", "不得", "如下", "本例", "来源", "因此", "其中",
    "包括", "适用", "按照", "实际", "符合", "规定", "情况",
}


def _extract_keywords(text: str, max_kw: int = 30) -> list[str]:
    """Extract content keywords from Chinese answer text."""
    if not text:
        return []
    raw = _CJK_RE.findall(text)
    kept: list[str] = []
    seen = set()
    for tok in raw:
        if tok in _NOISE_TOKENS or tok in seen:
            continue
        seen.add(tok)
        kept.append(tok)
        if len(kept) >= max_kw:
            break
    return kept


def _flatten_sources(api_sources: list) -> set[str]:
    """Collect all string values from API response `sources`."""
    out: set[str] = set()
    for src in api_sources:
        if not isinstance(src, dict):
            continue
        for row in src.get("rows", []):
            if not isinstance(row, list):
                continue
            for v in row:
                if isinstance(v, str):
                    out.add(v)
    return out


def score_case(case: dict, response: dict) -> dict:
    """Score a single case response. Returns dict with 4 metrics + matched lists."""
    answer = response.get("answer") or ""
    api_source_strings = _flatten_sources(response.get("sources") or [])

    # Dim 1: anchor_recall — anchor format "Type:id_or_name"
    anchors = case.get("reasoning_anchors", []) or []
    matched_anchors: list[str] = []
    for anchor in anchors:
        anchor_id = anchor.split(":", 1)[-1] if ":" in anchor else anchor
        if any(anchor_id in s for s in api_source_strings) or anchor_id in answer:
            matched_anchors.append(anchor)
    anchor_recall = len(matched_anchors) / max(len(anchors), 1)

    # Dim 2: keyword_overlap vs expected_answer
    keywords = _extract_keywords(case.get("expected_answer", ""))
    matched_kw = [k for k in keywords if k in answer]
    keyword_overlap = len(matched_kw) / max(len(keywords), 1)

    # Dim 3: source_citation — statutory tokens (法/条例/号) appear in answer
    expected_sources = case.get("sources", []) or []
    matched_sources: list[str] = []
    for src in expected_sources:
        # Token-split by space + punctuation; require >=1 informative token in answer
        tokens = [t for t in re.split(r"[\s§【】\[\]()（）]+", src) if len(t) >= 2]
        if any(t in answer for t in tokens):
            matched_sources.append(src)
    source_citation = len(matched_sources) / max(len(expected_sources), 1)

    composite = round((anchor_recall + keyword_overlap + source_citation) / 3, 4)

    return {
        "anchor_recall": round(anchor_recall, 4),
        "keyword_overlap": round(keyword_overlap, 4),
        "source_citation": round(source_citation, 4),
        "composite": composite,
        "matched_anchors": matched_anchors,
        "matched_keywords_count": len(matched_kw),
        "expected_keywords_count": len(keywords),
        "matched_sources": matched_sources,
    }


# ---------------------------------------------------------------------------
# Stage 1 — API call (live mode)
# ---------------------------------------------------------------------------


def _headers(extra: dict | None = None) -> dict:
    h = {"Accept": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    if extra:
        h.update(extra)
    return h


def chat_request_body(case: dict, limit: int) -> dict:
    """Build the /api/v1/chat POST body for a case. Used by both dry-run and live."""
    return {
        "question": case["question"],
        "mode": "rag",
        "limit": limit,
    }


def call_chat(api_base: str, body: dict, timeout: int = 60) -> dict:
    """POST to /api/v1/chat. Returns dict with `answer` + `sources` or `error`."""
    url = f"{api_base.rstrip('/')}/api/v1/chat"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers=_headers({"Content-Type": "application/json"}),
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
            payload["_elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
            return payload
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode(errors="ignore")[:500]}
    except urllib.error.URLError as e:
        return {"error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


# ---------------------------------------------------------------------------
# Stage 1 — orchestration
# ---------------------------------------------------------------------------


def run_dry_run(records: list[dict], limit: int, max_preview: int) -> dict:
    """Print request bodies that would be sent. No API calls."""
    previewed = []
    for case in records[:max_preview]:
        body = chat_request_body(case, limit)
        previewed.append({"id": case["id"], "domain": case["domain"], "request_body": body})
    return {
        "mode": "dry-run",
        "total_cases": len(records),
        "previewed_count": len(previewed),
        "api_base_target": API_BASE_DEFAULT,
        "would_send_to": f"{API_BASE_DEFAULT}/api/v1/chat",
        "auth_header_set": bool(API_KEY),
        "preview": previewed,
        "note": "No API calls made. Use --mode live to actually score.",
    }


def run_live(records: list[dict], api_base: str, limit: int, sleep_s: float) -> dict:
    """POST each case to /api/v1/chat, score, aggregate."""
    per_case: list[dict] = []
    api_errors = 0

    for i, case in enumerate(records, 1):
        body = chat_request_body(case, limit)
        response = call_chat(api_base, body)
        if "error" in response:
            api_errors += 1
            per_case.append({
                "id": case["id"],
                "domain": case["domain"],
                "error": response["error"],
                "detail": response.get("detail", "")[:200],
            })
        else:
            scored = score_case(case, response)
            per_case.append({
                "id": case["id"],
                "domain": case["domain"],
                "sub_task": case.get("sub_task"),
                "difficulty": case.get("difficulty"),
                "elapsed_ms": response.get("_elapsed_ms"),
                **scored,
            })
        # Brief progress indicator every 10 cases
        if i % 10 == 0:
            print(f"  ... {i}/{len(records)} cases done", file=sys.stderr)
        if sleep_s > 0 and i < len(records):
            time.sleep(sleep_s)

    # Aggregate
    by_domain_scores: dict[str, list[float]] = {d: [] for d in ALLOWED_DOMAINS}
    by_difficulty_scores: dict[str, list[float]] = {d: [] for d in ALLOWED_DIFFICULTY}
    overall_scores: list[float] = []
    for r in per_case:
        if "composite" not in r:
            continue
        overall_scores.append(r["composite"])
        by_domain_scores[r["domain"]].append(r["composite"])
        if r.get("difficulty") in by_difficulty_scores:
            by_difficulty_scores[r["difficulty"]].append(r["composite"])

    def _avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    return {
        "mode": "live",
        "api_base": api_base,
        "total_cases": len(records),
        "api_errors": api_errors,
        "scored_cases": sum(1 for r in per_case if "composite" in r),
        "overall_composite_avg": _avg(overall_scores),
        "by_domain_avg": {d: _avg(by_domain_scores[d]) for d in ALLOWED_DOMAINS},
        "by_difficulty_avg": {d: _avg(by_difficulty_scores[d]) for d in ALLOWED_DIFFICULTY},
        "per_case": per_case,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="benchmark/eval_legalbench_tax_v0.jsonl",
                        help="JSONL eval file path")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="validate",
                        help="validate (Stage 0) | dry-run (preview) | live (Stage 1 score)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero on validation errors")
    parser.add_argument("--api-base", default=API_BASE_DEFAULT,
                        help=f"KG API base URL (default: {API_BASE_DEFAULT})")
    parser.add_argument("--limit", type=int, default=10,
                        help="Per-question retrieval limit passed to /api/v1/chat (default 10)")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="Seconds to sleep between live API calls (rate limit, default 0)")
    parser.add_argument("--max-preview", type=int, default=3,
                        help="Cases to print in dry-run (default 3)")
    parser.add_argument("--output", help="Write JSON results to this path (live mode)")
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

    if args.mode == "validate":
        summary = report(records)
        print("=== LegalBench-Tax v0 distribution ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if args.mode == "dry-run":
        result = run_dry_run(records, args.limit, args.max_preview)
        print("=== LegalBench-Tax v0 dry-run preview ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    # live
    print(f"=== LegalBench-Tax v0 live scoring against {args.api_base} ===", file=sys.stderr)
    if not API_KEY:
        print("[warn] KG_API_KEY env var not set; calls will be unauthenticated",
              file=sys.stderr)
    result = run_live(records, args.api_base, args.limit, args.sleep)
    summary_only = {k: v for k, v in result.items() if k != "per_case"}
    print("=== LegalBench-Tax v0 live aggregate ===")
    print(json.dumps(summary_only, indent=2, ensure_ascii=False))

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[written] full per-case results -> {out_path}", file=sys.stderr)

    return 0 if result["api_errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
