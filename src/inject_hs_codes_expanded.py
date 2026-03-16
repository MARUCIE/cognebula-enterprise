#!/usr/bin/env python3
"""Inject expanded HS codes (crawled from hsbianma.com) into KuzuDB.

Reads data from data/raw/20260315-hs-codes/hs-codes-for-inject.json
and inserts into existing HSCode table + HS_PARENT_OF edges.

Skips existing seed nodes (366 already in DB).

Usage:
    python src/inject_hs_codes_expanded.py --db data/finance-tax-graph
    python src/inject_hs_codes_expanded.py --db data/finance-tax-graph --dry-run
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import kuzu
except ImportError:
    print("ERROR: kuzu not installed. Run: pip install kuzu")
    sys.exit(1)


BATCH_SIZE = 200
DATA_FILE = Path(__file__).parent.parent / "data" / "raw" / "20260315-hs-codes" / "hs-codes-for-inject.json"


def _exec(conn, cypher: str, params: dict = None, label: str = ""):
    """Execute Cypher with idempotent error handling."""
    try:
        if params:
            conn.execute(cypher, params)
        else:
            conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg or "primary key" in msg:
            return True  # idempotent
        if "violates" in msg and "constraint" in msg:
            return True  # duplicate key
        print(f"  WARN: {label} -- {e}")
        return False


def get_existing_codes(conn):
    """Get set of existing HSCode IDs."""
    existing = set()
    try:
        result = conn.execute("MATCH (h:HSCode) RETURN h.id")
        while result.has_next():
            row = result.get_next()
            existing.add(row[0])
    except Exception as e:
        print(f"WARN: Could not query existing codes: {e}")
    return existing


def main():
    parser = argparse.ArgumentParser(description="Inject expanded HS codes into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph",
                       help="Path to KuzuDB database")
    parser.add_argument("--data", default=str(DATA_FILE),
                       help="Path to injection JSON file")
    parser.add_argument("--dry-run", action="store_true",
                       help="Print what would be done without writing")
    args = parser.parse_args()

    # Load data
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print("Run fetch_hs_codes.py first to crawl data.")
        sys.exit(1)

    with open(data_path, encoding="utf-8") as f:
        codes = json.load(f)
    print(f"Loaded {len(codes)} HS codes from {data_path}")

    if args.dry_run:
        # Count by level
        from collections import Counter
        levels = Counter(c["level"] for c in codes)
        for lvl in sorted(levels):
            print(f"  Level {lvl}: {levels[lvl]} codes")
        print(f"  TOTAL: {len(codes)}")
        print("DRY RUN: No changes written.")
        return

    # Connect to DB
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    # Ensure schema exists
    _exec(conn, """CREATE NODE TABLE IF NOT EXISTS HSCode(
        id STRING PRIMARY KEY,
        code STRING,
        name STRING,
        level INT64,
        parentCode STRING,
        section STRING,
        vatRate STRING,
        consumptionTaxRate STRING,
        exportRefundRate STRING,
        seedStatus STRING
    )""", label="SCHEMA HSCode")

    _exec(conn, """CREATE REL TABLE IF NOT EXISTS HS_PARENT_OF(
        FROM HSCode TO HSCode
    )""", label="SCHEMA HS_PARENT_OF")

    # Get existing codes to skip
    existing = get_existing_codes(conn)
    print(f"Found {len(existing)} existing HSCode nodes (will skip)")

    # Insert new nodes
    inserted = 0
    skipped = 0
    errors = 0

    for i, code_info in enumerate(codes):
        code = code_info["code"]
        node_id = f"hs-{code}"

        if node_id in existing:
            skipped += 1
            continue

        name = code_info.get("name_cn", "") or f"HS {code}"
        level = code_info.get("level", len(code))
        parent_code = code_info.get("parent_code", "")
        section = code_info.get("section", "")
        vat_rate = code_info.get("vat_rate", "")
        consumption_tax = code_info.get("consumption_tax", "")
        export_refund = code_info.get("export_refund_rate", "")

        ok = _exec(conn,
            "CREATE (n:HSCode {id: $id, code: $code, name: $name, level: $lvl, "
            "parentCode: $pc, section: $sec, vatRate: $vat, consumptionTaxRate: $ct, "
            "exportRefundRate: $er, seedStatus: $ss})",
            {
                "id": node_id,
                "code": code,
                "name": name,
                "lvl": level,
                "pc": parent_code,
                "sec": section,
                "vat": vat_rate,
                "ct": consumption_tax,
                "er": export_refund,
                "ss": "crawled",
            },
            label=f"INSERT {node_id}",
        )
        if ok:
            inserted += 1
            existing.add(node_id)
        else:
            errors += 1

        if (i + 1) % 500 == 0:
            print(f"  Progress: {i+1}/{len(codes)} (inserted: {inserted}, skipped: {skipped})")

    print(f"\nNodes: inserted={inserted}, skipped={skipped}, errors={errors}")

    # Create HS_PARENT_OF edges
    print("\nCreating HS_PARENT_OF edges...")
    edges_created = 0
    edges_skipped = 0

    for code_info in codes:
        code = code_info["code"]
        parent_code = code_info.get("parent_code", "")
        if not parent_code or len(parent_code) < 2:
            continue

        child_id = f"hs-{code}"
        parent_id = f"hs-{parent_code}"

        # Only create edge if both nodes exist
        if child_id not in existing or parent_id not in existing:
            edges_skipped += 1
            continue

        ok = _exec(conn,
            "MATCH (c:HSCode {id: $cid}), (p:HSCode {id: $pid}) "
            "CREATE (p)-[:HS_PARENT_OF]->(c)",
            {"cid": child_id, "pid": parent_id},
            label=f"EDGE {parent_id}->{child_id}",
        )
        if ok:
            edges_created += 1
        else:
            edges_skipped += 1

        if (edges_created + edges_skipped) % 500 == 0:
            print(f"  Edges progress: created={edges_created}, skipped={edges_skipped}")

    print(f"\nEdges: created={edges_created}, skipped={edges_skipped}")

    # Final count
    result = conn.execute("MATCH (h:HSCode) RETURN count(h)")
    while result.has_next():
        print(f"\nFinal HSCode count: {result.get_next()[0]}")

    result = conn.execute("MATCH ()-[r:HS_PARENT_OF]->() RETURN count(r)")
    while result.has_next():
        print(f"Final HS_PARENT_OF edge count: {result.get_next()[0]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
