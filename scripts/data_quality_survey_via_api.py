#!/usr/bin/env python3
"""Run the existing data_quality_survey against PROD via /api/v1/nodes.

The native CLI `scripts/data_quality_survey.py` opens a direct kuzu.Database
which fails against the uvicorn-locked PROD instance. This wrapper re-uses
the pure analysis half (`survey_type` from `src/audit/data_quality_survey.py`)
by feeding it samples fetched via the read-only nodes endpoint.

Honest scope of this run:
  * Only canonical-coverage scope: parse_canonical_schema() yields ~31 types.
  * Per-type sample = first N rows from `/api/v1/nodes?type=T&limit=N`.
  * No mutation, no admin endpoint usage.
  * Verdict per existing target_defect_rate=0.10 (override via --target).

Usage:
    python scripts/data_quality_survey_via_api.py
    python scripts/data_quality_survey_via_api.py --sample 200
    python scripts/data_quality_survey_via_api.py --api-url https://ops.hegui.org \
        --output outputs/reports/data-quality-audit/2026-04-27-prod-survey.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.audit.data_quality_survey import (  # noqa: E402
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_STALE_YEARS,
    DEFAULT_TARGET_DEFECT_RATE,
    survey_type,
)
from src.audit.ontology_conformance import parse_canonical_schema  # noqa: E402


def _fetch_sample(api_url: str, type_name: str, limit: int, timeout: int = 30) -> list[dict]:
    """Fetch first `limit` rows of canonical type via /api/v1/nodes."""
    qs = urllib.parse.urlencode({"type": type_name, "limit": limit})
    url = f"{api_url.rstrip('/')}/api/v1/nodes?{qs}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        return []
    return data.get("results", []) or []


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-url", default="https://ops.hegui.org")
    p.add_argument("--sample", type=int, default=DEFAULT_SAMPLE_SIZE,
                   help=f"per-type sample size (default {DEFAULT_SAMPLE_SIZE})")
    p.add_argument("--target", type=float, default=DEFAULT_TARGET_DEFECT_RATE,
                   help="defect rate target for PASS/FAIL verdict")
    p.add_argument("--stale-years", type=int, default=DEFAULT_STALE_YEARS)
    p.add_argument("--output", help="write full JSON report here")
    p.add_argument("--schema",
                   default=str(PROJECT_ROOT / "schemas" / "ontology_v4.2.cypher"))
    args = p.parse_args(argv)

    schema_path = Path(args.schema)
    canonical_types = sorted(parse_canonical_schema(schema_path))
    print(f"=== data_quality_survey_via_api ===")
    print(f"  api_url={args.api_url}")
    print(f"  canonical_types={len(canonical_types)}")
    print(f"  per-type sample={args.sample} target_defect_rate={args.target}")
    print(f"  stale_years={args.stale_years}")
    print()

    today = date.today()
    per_type: dict = {}
    total_sampled = 0
    total_defects = 0
    fetch_misses: list[str] = []

    t0 = time.time()
    for i, t in enumerate(canonical_types, start=1):
        rows = _fetch_sample(args.api_url, t, args.sample)
        if not rows:
            fetch_misses.append(t)
        report = survey_type(rows, today=today, stale_years=args.stale_years)
        per_type[t] = report
        total_sampled += report["sampled"]
        total_defects += report["defects_total"]
        # Brief per-type line
        print(f"  [{i:2d}/{len(canonical_types)}] {t:<30s} "
              f"sampled={report['sampled']:>4d}  defects={report['defects_total']:>4d}  "
              f"rate={report['defect_rate']:.4f}")

    elapsed = time.time() - t0
    overall_defect_rate = (
        round(total_defects / total_sampled, 4) if total_sampled else 0.0
    )
    verdict = "PASS" if overall_defect_rate <= args.target else "FAIL"

    report = {
        "api_url": args.api_url,
        "schema": str(schema_path),
        "sample_size": args.sample,
        "stale_years": args.stale_years,
        "elapsed_s": round(elapsed, 2),
        "fetch_misses": fetch_misses,
        "per_type": per_type,
        "overall": {
            "canonical_types_surveyed": len(canonical_types),
            "total_sampled": total_sampled,
            "total_defects": total_defects,
            "defect_rate": overall_defect_rate,
            "verdict": verdict,
            "target_defect_rate": args.target,
        },
    }

    print()
    print(f"=== OVERALL ===")
    print(f"  types_surveyed={len(canonical_types)}  sampled={total_sampled}  "
          f"defects={total_defects}")
    print(f"  defect_rate={overall_defect_rate:.4f}  target={args.target:.4f}  "
          f"verdict={verdict}  elapsed={elapsed:.1f}s")
    if fetch_misses:
        print(f"  fetch_misses ({len(fetch_misses)}): {fetch_misses[:5]}"
              f"{'…' if len(fetch_misses) > 5 else ''}")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        print(f"  written: {out_path}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
