#!/usr/bin/env python3
"""Fixture for Phase 1d migration test — clone demo DB and inject TaxIncentiveV2.

Why this fixture:
  The demo graph ships only canonical `TaxIncentive` (no V2). The prod shape
  has both canonical + V2 coexisting (109 V2 rows per Session 43 drift audit).
  Without a V2 fixture, the Phase 1d --dry-run reports 'nothing to merge' —
  a false-positive green light. This script injects a minimal V2 + V2-rel
  slice so the migration logic exercises real conflict-detection + edge-rewire
  code paths.

Shape injected:
  TaxIncentiveV2 node table (same schema as canonical)
    - 2 rows with ids colliding with canonical (triggers SKIP path)
    - 3 rows with new ids (triggers MERGE success path)
  FT_INCENTIVE_TAX_V2 rel (TaxIncentiveV2 -> TaxType)
    - 2 edges (needs rewire to canonical FT_INCENTIVE_TAX)

Usage:
  python3 scripts/fixture_phase1d_test.py --src data/finance-tax-graph.demo \
      --dst data/finance-tax-graph.phase1d-test
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Source demo DB (read-only, copied)")
    ap.add_argument("--dst", required=True, help="Destination test DB (overwritten)")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    if not src.exists():
        print(f"ERROR: {src} missing", file=sys.stderr)
        return 2

    # Kuzu DB is a single file (as of 0.12/Vela); copy is safe.
    if dst.exists():
        dst.unlink()
    shutil.copy2(src, dst)
    print(f"OK: copied {src} -> {dst}")

    import kuzu  # noqa: WPS433

    db = kuzu.Database(str(dst))
    conn = kuzu.Connection(db)

    # Drop V2 if a previous fixture run left it behind
    try:
        conn.execute("DROP TABLE FT_INCENTIVE_TAX_V2")
    except Exception:
        pass
    try:
        conn.execute("DROP TABLE TaxIncentiveV2")
    except Exception:
        pass

    # 1) Create V2 node table mirroring canonical schema
    conn.execute(
        """
        CREATE NODE TABLE TaxIncentiveV2 (
            id STRING,
            name STRING,
            incentiveType STRING,
            value DOUBLE,
            valueBasis STRING,
            beneficiaryType STRING,
            eligibilityCriteria STRING,
            combinable BOOL,
            maxAnnualBenefit DOUBLE,
            effectiveFrom DATE,
            effectiveUntil DATE,
            lawReference STRING,
            PRIMARY KEY (id)
        )
        """
    )
    print("OK: created TaxIncentiveV2 table")

    # 2) Pick 2 existing canonical ids (for conflict path)
    r = conn.execute("MATCH (n:TaxIncentive) RETURN n.id ORDER BY n.id LIMIT 2")
    conflict_ids = []
    while r.has_next():
        conflict_ids.append(r.get_next()[0])
    if len(conflict_ids) < 2:
        print("ERROR: canonical TaxIncentive has <2 rows; cannot seed conflicts", file=sys.stderr)
        return 2
    print(f"OK: will seed conflicts on canonical ids: {conflict_ids}")

    # 3) Insert 2 conflict rows (reuse canonical ids) + 3 fresh rows
    rows = [
        (conflict_ids[0], "CONFLICT-A", "reduction", 0.05, "rate", "smallBusiness",
         "legacy V2 eligibility A", True, 100000.0, "2024-01-01", "2025-12-31", "V2-LAW-A"),
        (conflict_ids[1], "CONFLICT-B", "exemption", 0.0, "rate", "startup",
         "legacy V2 eligibility B", False, 50000.0, "2024-01-01", "2026-06-30", "V2-LAW-B"),
        ("V2_FRESH_001", "FRESH-001", "reduction", 0.10, "rate", "hightech",
         "V2-only fresh row 1", True, 200000.0, "2024-07-01", "2026-12-31", "V2-LAW-C"),
        ("V2_FRESH_002", "FRESH-002", "deduction", 0.15, "basis", "manufacturing",
         "V2-only fresh row 2", True, 300000.0, "2025-01-01", "2026-12-31", "V2-LAW-D"),
        ("V2_FRESH_003", "FRESH-003", "credit", 50000.0, "amount", "exporter",
         "V2-only fresh row 3", False, 50000.0, "2025-06-01", "2026-12-31", "V2-LAW-E"),
    ]
    insert_cypher = (
        "CREATE (n:TaxIncentiveV2 {"
        "id: $id, name: $name, incentiveType: $incentiveType, value: $value, "
        "valueBasis: $valueBasis, beneficiaryType: $beneficiaryType, "
        "eligibilityCriteria: $eligibilityCriteria, combinable: $combinable, "
        "maxAnnualBenefit: $maxAnnualBenefit, effectiveFrom: date($effectiveFrom), "
        "effectiveUntil: date($effectiveUntil), lawReference: $lawReference"
        "})"
    )
    for row in rows:
        conn.execute(
            insert_cypher,
            {
                "id": row[0], "name": row[1], "incentiveType": row[2], "value": row[3],
                "valueBasis": row[4], "beneficiaryType": row[5],
                "eligibilityCriteria": row[6], "combinable": row[7],
                "maxAnnualBenefit": row[8], "effectiveFrom": row[9],
                "effectiveUntil": row[10], "lawReference": row[11],
            },
        )
    print(f"OK: inserted {len(rows)} V2 rows (2 conflict + 3 fresh)")

    # 4) Create V2 rel mirroring canonical FT_INCENTIVE_TAX (TaxIncentive -> TaxType)
    conn.execute(
        "CREATE REL TABLE FT_INCENTIVE_TAX_V2 (FROM TaxIncentiveV2 TO TaxType)"
    )
    print("OK: created FT_INCENTIVE_TAX_V2 rel table")

    # 5) Pick 2 TaxType ids to connect to
    r = conn.execute("MATCH (n:TaxType) RETURN n.id ORDER BY n.id LIMIT 2")
    tt_ids = []
    while r.has_next():
        tt_ids.append(r.get_next()[0])
    if len(tt_ids) < 2:
        print("WARN: <2 TaxType rows; skipping V2 rel edges", file=sys.stderr)
    else:
        # Edge from a FRESH V2 row and from a CONFLICT V2 row
        for v2_id, tt_id in [("V2_FRESH_001", tt_ids[0]), (conflict_ids[0], tt_ids[1])]:
            conn.execute(
                "MATCH (v:TaxIncentiveV2 {id: $v_id}), (t:TaxType {id: $t_id}) "
                "CREATE (v)-[:FT_INCENTIVE_TAX_V2]->(t)",
                {"v_id": v2_id, "t_id": tt_id},
            )
        print(f"OK: inserted 2 FT_INCENTIVE_TAX_V2 edges (to {tt_ids})")

    # Summary
    r = conn.execute("MATCH (n:TaxIncentiveV2) RETURN count(n)")
    print(f"\nFixture end state: TaxIncentiveV2 rows = {r.get_next()[0]}")
    r = conn.execute("MATCH ()-[e:FT_INCENTIVE_TAX_V2]->() RETURN count(e)")
    print(f"                   FT_INCENTIVE_TAX_V2 edges = {r.get_next()[0]}")
    r = conn.execute(
        "MATCH (v:TaxIncentiveV2), (t:TaxIncentive) WHERE v.id = t.id RETURN count(v)"
    )
    print(f"                   expected id conflicts    = {r.get_next()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
