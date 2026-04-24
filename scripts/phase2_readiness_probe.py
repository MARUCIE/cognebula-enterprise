#!/usr/bin/env python3
"""Phase 2 readiness probe — read-only report for duplicate cluster collapse.

Why this exists:
  The `phase2_duplicate_cluster_collapse.cypher` scaffold says "REWRITE with
  actual column names post-dry-run" — meaning real column discovery is a
  prerequisite. Demo graph only covers 2/5 or 2/6 of each cluster's sources
  (see Session 73 note), so demo cannot end-to-end validate Phase 2 the way
  it did Phase 1d (Session 71) and Phase 4 (Session 72). This script is
  HITL-safe: read-only, no mutations, safe to run against production to
  harvest the real schemas + counts + collision signals that Phase 2 MERGE
  blocks need.

Output sections per cluster:
  - Target canonical: present/absent, row count
  - Sources: present/absent, row count each, column schema each
  - Id overlap probes (source ∩ target) — helps decide conflict strategy

Usage:
  python3 scripts/phase2_readiness_probe.py --db data/finance-tax-graph.demo
  python3 scripts/phase2_readiness_probe.py --db /home/kg/.../finance-tax-graph

No --execute flag — this script never writes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CLUSTERS = {
    "2A policy": {
        "target": "TaxIncentive",
        "sources": ["TaxPolicy", "RegionalTaxPolicy", "TaxExemptionThreshold"],
    },
    "2B industry": {
        "target": "IndustryBenchmark",
        "sources": [
            "Industry", "FTIndustry", "IndustryKnowledge",
            "IndustryBookkeeping", "IndustryRiskProfile",
        ],
    },
    "2C accounting (RISKIEST per scaffold)": {
        "target": "AccountingSubject",
        "sources": [
            "AccountEntry", "AccountingEntry", "AccountRuleMapping",
            "ChartOfAccount", "ChartOfAccountDetail", "DepreciationRule",
        ],
    },
    "2D tax_rate": {
        "target": "TaxRate",
        "sources": [
            "TaxRateMapping", "TaxRateDetail", "TaxRateSchedule",
            "TaxCalculationRule", "TaxpayerRatePolicy", "TaxCodeIndustryMap",
        ],
    },
}


def list_tables(conn) -> set[str]:
    r = conn.execute("CALL show_tables() RETURN *")
    out = set()
    while r.has_next():
        row = r.get_next()
        if row[2] == "NODE":
            out.add(row[1])
    return out


def count_rows(conn, tbl: str) -> int:
    try:
        r = conn.execute(f"MATCH (n:{tbl}) RETURN count(n)")
        return int(r.get_next()[0])
    except Exception:
        return -1


def columns(conn, tbl: str) -> list[tuple[str, str]]:
    try:
        r = conn.execute(f"CALL table_info('{tbl}') RETURN *")
    except Exception:
        return []
    out = []
    while r.has_next():
        row = r.get_next()
        out.append((row[1], row[2]))
    return out


def id_overlap(conn, src: str, tgt: str) -> int:
    try:
        r = conn.execute(
            f"MATCH (a:{src}), (b:{tgt}) WHERE a.id = b.id RETURN count(a)"
        )
        return int(r.get_next()[0])
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Kuzu DB path (read-only)")
    args = ap.parse_args()

    import kuzu  # noqa: WPS433

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"ERROR: {db_path} does not exist", file=sys.stderr)
        return 2

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    present = list_tables(conn)

    for label, cluster in CLUSTERS.items():
        target = cluster["target"]
        srcs = cluster["sources"]
        print(f"\n==== {label} ====")
        tgt_present = target in present
        tgt_rows = count_rows(conn, target) if tgt_present else -1
        print(f"  Target `{target}`: {'PRESENT' if tgt_present else 'ABSENT'}  rows={tgt_rows}")
        if tgt_present:
            cols = columns(conn, target)
            print(f"    columns: {[c for c, _ in cols]}")

        present_srcs = 0
        print(f"  Sources ({len(srcs)}):")
        for src in srcs:
            if src not in present:
                print(f"    {src}: ABSENT")
                continue
            present_srcs += 1
            rows = count_rows(conn, src)
            cols = columns(conn, src)
            print(f"    {src}: PRESENT  rows={rows}")
            print(f"      columns: {[c for c, _ in cols]}")
            if tgt_present and rows > 0:
                overlap = id_overlap(conn, src, target)
                print(f"      id-overlap with {target}: {overlap}")
        coverage = f"{present_srcs}/{len(srcs)} sources"
        coverage += f" + {'1' if tgt_present else '0'}/1 target"
        print(f"  Coverage: {coverage}")

    print("\n==== Summary guidance ====")
    print("  Clusters with full source coverage can go straight to fixture+merge (Phase 1d/4 pattern).")
    print("  Partial coverage: probe prod for missing sources' schemas, then author MERGE blocks from real columns.")
    print("  Zero source coverage (e.g., demo for 2A): wait for prod probe run to harvest schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
