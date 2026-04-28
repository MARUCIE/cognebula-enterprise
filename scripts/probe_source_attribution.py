#!/usr/bin/env python3
"""probe_source_attribution.py — read-only probe of source-attribution feasibility.

Why this exists
---------------
B4 design (`outputs/audits/2026-04-28-prod-kg-source-schema-draft.md`) classified
each fact-bearing table by source-attribution backfill cost (LOW / MEDIUM / HIGH)
based on declared schema. But declared ≠ populated. This probe measures actual
per-table populated-rate of source-attribution fields against prod, and surfaces
which Phase-1-LOW assumptions are real and which are fabricated.

Methodology
-----------
For each candidate fact-bearing table, sample 200-500 rows via
`/api/v1/nodes?type=<X>&limit=500` and:

1. Inventory schema fields present (column declared).
2. Measure populated rate per field (non-empty fraction).
3. Classify each field as ID-prefix-pattern (e.g. `CL_*`), `source_doc_id`,
   `sourceUrl`, or `extracted_by` to assess Phase-1 candidate paths.
4. Aggregate distinct-source-count per table for the populated paths.

Output
------
CSV stdout: one row per (table, attribution_path, status). Stderr: human summary.

Audit ref
---------
- §20 Phase B4 (Source schema declaration)
- outputs/audits/2026-04-28-prod-kg-source-schema-draft.md (B4 design)
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "_lib"))
import prod_kg_client as kg  # noqa: E402


# Phase 1 LOW-cost candidates per B4 design.
# (table, claimed_path, expected_phase1_cost) — empirical results may falsify these.
PHASE1_CANDIDATES = (
    ("LegalClause",      "id-prefix CL_*",      "LOW"),
    ("KnowledgeUnit",    "source_doc_id",       "LOW"),
    ("LegalDocument",    "source_doc_id",       "LOW"),
    ("ComplianceRuleV2", "sourceUrl",           "LOW"),
    ("FilingFormV2",     "sourceUrl",           "LOW"),
    ("TaxIncentiveV2",   "sourceUrl",           "LOW"),
    ("RiskIndicatorV2",  "sourceUrl",           "LOW"),
)


def probe_id_prefix(rows: list[dict], expected_prefix: str) -> dict:
    """Test how many rows' id starts with the expected prefix."""
    matches = 0
    distinct_keys: Counter = Counter()
    for r in rows:
        rid = (r.get("id") or "").strip()
        if rid.startswith(expected_prefix):
            matches += 1
            tail = rid[len(expected_prefix):]
            # First underscore-delimited token ≈ source-doc bucket
            key = tail.split("_", 1)[0] if "_" in tail else tail[:8]
            distinct_keys[key] += 1
    return {
        "matched": matches,
        "sampled": len(rows),
        "distinct_groups_in_sample": len(distinct_keys),
        "top5": distinct_keys.most_common(5),
    }


def probe_field_populated(rows: list[dict], field: str) -> dict:
    """Test how many rows have `field` non-empty + how many distinct values."""
    populated = 0
    distinct_vals: Counter = Counter()
    for r in rows:
        v = r.get(field)
        if v not in (None, "", 0, [], "0"):
            populated += 1
            distinct_vals[str(v)[:80]] += 1
    return {
        "populated": populated,
        "sampled": len(rows),
        "distinct_in_sample": len(distinct_vals),
        "top5": distinct_vals.most_common(5),
    }


def probe_table(table: str, claimed_path: str, expected_cost: str, sample_size: int) -> dict:
    """Run all relevant probes on one (table, claimed_path) pair."""
    try:
        rows = kg.nodes(table, limit=sample_size)
    except Exception as e:
        return {
            "table": table, "claimed_path": claimed_path, "expected_cost": expected_cost,
            "actual_cost": "ERROR", "reason": str(e)[:200], "sampled": 0,
        }

    if not rows:
        return {
            "table": table, "claimed_path": claimed_path, "expected_cost": expected_cost,
            "actual_cost": "EMPTY-TABLE", "reason": "no rows in sample", "sampled": 0,
        }

    if claimed_path.startswith("id-prefix "):
        prefix = claimed_path.split(" ", 1)[1].rstrip("*")
        result = probe_id_prefix(rows, prefix)
        match_rate = result["matched"] / result["sampled"] if result["sampled"] else 0
        if match_rate < 0.05:
            actual = "FABRICATED"
            reason = f"only {result['matched']}/{result['sampled']} rows match '{prefix}*'"
        elif match_rate >= 0.90:
            actual = "LOW"
            reason = f"{result['matched']}/{result['sampled']} rows match prefix; {result['distinct_groups_in_sample']} distinct groups"
        else:
            actual = "MEDIUM"
            reason = f"{int(match_rate*100)}% match rate; partial coverage"
        return {
            "table": table, "claimed_path": claimed_path, "expected_cost": expected_cost,
            "actual_cost": actual, "reason": reason, "sampled": result["sampled"],
            "populated_rate": match_rate, "distinct_in_sample": result["distinct_groups_in_sample"],
        }

    # Field-name path
    field = claimed_path
    result = probe_field_populated(rows, field)
    rate = result["populated"] / result["sampled"] if result["sampled"] else 0
    if rate < 0.05:
        actual = "EMPTY-FIELD"
        reason = f"only {result['populated']}/{result['sampled']} rows have populated '{field}'"
    elif rate >= 0.95:
        actual = "LOW"
        reason = f"{result['populated']}/{result['sampled']} rows populated; {result['distinct_in_sample']} distinct values"
    else:
        actual = "MEDIUM"
        reason = f"{int(rate*100)}% populated; partial coverage"
    return {
        "table": table, "claimed_path": claimed_path, "expected_cost": expected_cost,
        "actual_cost": actual, "reason": reason, "sampled": result["sampled"],
        "populated_rate": rate, "distinct_in_sample": result["distinct_in_sample"],
    }


def render_csv(reports: list[dict]) -> str:
    lines = ["table,claimed_path,expected_cost,actual_cost,populated_rate,sampled,distinct_in_sample,reason"]
    for r in reports:
        rate = r.get("populated_rate", 0.0)
        distinct = r.get("distinct_in_sample", 0)
        reason = (r.get("reason") or "").replace(",", ";")
        lines.append(
            f"{r['table']},{r['claimed_path']},{r['expected_cost']},{r['actual_cost']},"
            f"{rate:.3f},{r['sampled']},{distinct},{reason}"
        )
    return "\n".join(lines)


def render_summary(reports: list[dict]) -> str:
    out = ["", "=" * 78, "B4 PHASE 1 BACKFILL FEASIBILITY — empirical falsification", "=" * 78]
    out.append(f"{'TABLE':<22s} {'CLAIMED PATH':<22s} {'EXPECTED':<10s} {'ACTUAL':<14s} {'RATE':>7s}")
    out.append("-" * 78)
    falsified = 0
    confirmed = 0
    for r in reports:
        rate = r.get("populated_rate", 0.0)
        out.append(
            f"{r['table']:<22s} {r['claimed_path']:<22s} {r['expected_cost']:<10s} "
            f"{r['actual_cost']:<14s} {rate*100:6.1f}%"
        )
        if r.get("actual_cost") in ("FABRICATED", "EMPTY-FIELD", "EMPTY-TABLE"):
            falsified += 1
        elif r.get("actual_cost") == "LOW":
            confirmed += 1
    out.append("-" * 78)
    out.append(f"CONFIRMED LOW: {confirmed}/{len(reports)}     FALSIFIED: {falsified}/{len(reports)}")
    out.append("=" * 78)
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only probe of source-attribution feasibility (B4 Phase 1)")
    parser.add_argument("--sample-size", type=int, default=200, help="Rows to sample per table (default 200)")
    parser.add_argument("--csv-only", action="store_true", help="Emit CSV only (suppress summary)")
    args = parser.parse_args()

    try:
        h = kg.health()
        if h.get("status") != "healthy":
            print(f"ERROR: kg-api unhealthy: {h}", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"ERROR: kg-api unreachable: {e}", file=sys.stderr)
        return 2

    reports = []
    for table, path, cost in PHASE1_CANDIDATES:
        print(f"# probing {table} via {path} ...", file=sys.stderr)
        reports.append(probe_table(table, path, cost, args.sample_size))

    print(render_csv(reports))
    if not args.csv_only:
        print(render_summary(reports), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
