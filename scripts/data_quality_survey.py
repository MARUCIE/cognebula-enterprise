#!/usr/bin/env python3
"""Data-quality survey CLI — answer the real question "is the data any good?".

Complements `scripts/coverage_report.py` (which asks "does the Schema have
the columns?"). This script asks: "of the rows that exist, how many have
defects we can mechanically detect?"

Closes the audit 2026-04-21 next-cycle inversion test — run this BEFORE any
new Schema work.

Usage:

    ./.venv/bin/python scripts/data_quality_survey.py \\
        --db /path/to/prod.kuzu \\
        --sample-size 100 \\
        --target-defect-rate 0.10 \\
        --output outputs/reports/data-quality-survey/$(date +%F)-baseline.json

Exit codes:
    0  PASS (defect_rate <= target_defect_rate)
    1  FAIL (defect_rate > target_defect_rate)
    2  argparse / missing DB / runtime error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.audit.data_quality_survey import (  # noqa: E402
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_STALE_YEARS,
    DEFAULT_TARGET_DEFECT_RATE,
    survey,
)


def render_summary(report: dict) -> str:
    """Short human-readable summary for operator console."""
    overall = report["overall"]
    lines = [
        f"sampled            {overall['total_sampled']:>8}",
        f"types surveyed     {overall['canonical_types_surveyed']:>8}",
        f"defects total      {overall['total_defects']:>8}",
        f"defect rate        {overall['defect_rate']:>8.2%}",
        f"target defect rate {overall['target_defect_rate']:>8.2%}",
        f"VERDICT            {overall['verdict']:>8}",
    ]
    lines.append("")
    lines.append("Top defect contributors:")
    per_type = report["per_type"]
    ranked = sorted(
        per_type.items(),
        key=lambda kv: kv[1]["defect_rate"],
        reverse=True,
    )
    for t, r in ranked[:10]:
        if r["sampled"] == 0:
            continue
        lines.append(
            f"  {t:<28} rate={r['defect_rate']:.2%} "
            f"(dup={r['duplicate_id_count']} stale={r['stale_count']} "
            f"integrity={r['integrity_violations']} jur={r['jurisdiction_mismatches']} "
            f"prohibited={r.get('prohibited_role_count', 0)} "
            f"badchain={r.get('invalid_chain_count', 0)} "
            f"badscope={r.get('inconsistent_scope_count', 0)})"
        )
    return "\n".join(lines)


def _connect(db_path: str):  # pragma: no cover — live-DB path
    try:
        import kuzu
    except ImportError as e:
        raise RuntimeError("kuzu not installed — run: pip install kuzu") from e
    db = kuzu.Database(db_path)
    return kuzu.Connection(db)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help="Path to Kuzu database directory")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Nodes sampled per canonical type (default {DEFAULT_SAMPLE_SIZE})",
    )
    parser.add_argument(
        "--target-defect-rate",
        type=float,
        default=DEFAULT_TARGET_DEFECT_RATE,
        help=f"Max defect_rate for PASS (default {DEFAULT_TARGET_DEFECT_RATE})",
    )
    parser.add_argument(
        "--stale-years",
        type=int,
        default=DEFAULT_STALE_YEARS,
        help=f"effective_from older than this = stale (default {DEFAULT_STALE_YEARS}y)",
    )
    parser.add_argument("--output", help="Write JSON report to this file")
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress human summary; JSON only"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: db path does not exist: {db_path}", file=sys.stderr)
        return 2

    try:
        conn = _connect(str(db_path))
        report = survey(
            conn,
            sample_size=args.sample_size,
            target_defect_rate=args.target_defect_rate,
            stale_years=args.stale_years,
        )
    except Exception as e:  # pragma: no cover
        print(f"ERROR: survey failed: {e}", file=sys.stderr)
        return 2

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, default=str))

    if not args.quiet:
        print(render_summary(report))

    return 0 if report["overall"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
