#!/usr/bin/env python3
"""Inject 4,205 tax classification codes into KuzuDB.

Reads data/extracted/tax_classification_codes.json and creates:
- TaxClassificationCode node table (if not exists)
- TC_PARENT_OF relationship table (if not exists)
- All 4,205 nodes + parent-child edges

Usage:
    python src/inject_tax_codes.py --db data/finance-tax-graph
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


BATCH_SIZE = 500


def _exec(conn, cypher: str, params: dict = None, label: str = ""):
    """Execute Cypher with error handling."""
    try:
        if params:
            conn.execute(cypher, params)
        else:
            conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg:
            return True  # idempotent
        print(f"WARN: {label} -- {e}")
        return False


def derive_parent_code(code: str, code_segments: list[str], level: int) -> str | None:
    """Derive parent code by zeroing out the current level's segment.

    Code structure: 19-digit string built from 10 segments.
    Segment widths: [1, 2, 2, 2, 2, 2, 2, 2, 2, 2] = 19 chars total.
    Level N uses segment index N-1. Parent = set segment N-1 to zeros.
    """
    if level <= 1:
        return None

    # Rebuild parent by zeroing the segment at index (level - 1)
    segment_widths = [1, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    parent_segments = list(code_segments)
    parent_segments[level - 1] = "0" * segment_widths[level - 1]

    # Also zero all segments below current level
    for i in range(level, len(parent_segments)):
        parent_segments[i] = "0" * segment_widths[i]

    return "".join(parent_segments)


def create_schema(conn):
    """Create TaxClassificationCode node table and TC_PARENT_OF rel table."""
    _exec(conn, """CREATE NODE TABLE IF NOT EXISTS TaxClassificationCode(
        id STRING PRIMARY KEY,
        code STRING,
        name STRING,
        level INT64,
        categoryAbbr STRING,
        descText STRING,
        parentCode STRING
    )""", label="NODE TaxClassificationCode")

    _exec(conn, """CREATE REL TABLE IF NOT EXISTS TC_PARENT_OF(
        FROM TaxClassificationCode TO TaxClassificationCode
    )""", label="REL TC_PARENT_OF")

    print("OK: Schema ensured (TaxClassificationCode + TC_PARENT_OF)")


def inject_nodes(conn, codes: list[dict]):
    """Insert all classification code nodes in batches."""
    total = len(codes)
    inserted = 0
    skipped = 0
    t0 = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = codes[i:i + BATCH_SIZE]
        for c in batch:
            parent_code = derive_parent_code(
                c["code"], c["code_segments"], c["level"]
            )
            ok = _exec(
                conn,
                "CREATE (n:TaxClassificationCode {id: $id, code: $code, name: $name, level: $level, categoryAbbr: $cat, descText: $dtxt, parentCode: $parent})",
                {
                    "id": f"TC_{c['code']}",
                    "code": c["code"],
                    "name": c["item_name"],
                    "level": c["level"],
                    "cat": c["category_abbr"],
                    "dtxt": c.get("description") or "",
                    "parent": parent_code or "",
                },
                label=f"node {c['code']}",
            )
            if ok:
                inserted += 1
            else:
                skipped += 1

        elapsed = time.time() - t0
        done = min(i + BATCH_SIZE, total)
        print(f"  ... {done}/{total} nodes ({elapsed:.1f}s)")

    print(f"OK: Inserted {inserted} nodes, skipped {skipped} ({time.time() - t0:.1f}s)")
    return inserted


def inject_edges(conn, codes: list[dict]):
    """Create parent-child relationships."""
    total_edges = 0
    skipped = 0
    t0 = time.time()

    # Build code -> id lookup
    code_set = {c["code"] for c in codes}

    for c in codes:
        if c["level"] <= 1:
            continue

        parent_code = derive_parent_code(
            c["code"], c["code_segments"], c["level"]
        )
        if not parent_code or parent_code not in code_set:
            continue

        ok = _exec(
            conn,
            """MATCH (parent:TaxClassificationCode {id: $pid}),
                     (child:TaxClassificationCode {id: $cid})
               CREATE (parent)-[:TC_PARENT_OF]->(child)""",
            {"pid": f"TC_{parent_code}", "cid": f"TC_{c['code']}"},
            label=f"edge {parent_code}->{c['code']}",
        )
        if ok:
            total_edges += 1
        else:
            skipped += 1

    elapsed = time.time() - t0
    print(f"OK: Created {total_edges} edges, skipped {skipped} ({elapsed:.1f}s)")
    return total_edges


def verify(conn):
    """Count nodes and edges for verification."""
    result = conn.execute(
        "MATCH (n:TaxClassificationCode) RETURN count(n) AS cnt"
    )
    row = result.get_next()
    node_count = row[0]

    result = conn.execute(
        "MATCH ()-[r:TC_PARENT_OF]->() RETURN count(r) AS cnt"
    )
    row = result.get_next()
    edge_count = row[0]

    # Level distribution
    result = conn.execute(
        "MATCH (n:TaxClassificationCode) RETURN n.level AS lv, count(*) AS cnt ORDER BY lv"
    )
    levels = {}
    while result.has_next():
        r = result.get_next()
        levels[r[0]] = r[1]

    print(f"\n=== Verification ===")
    print(f"Total nodes: {node_count}")
    print(f"Total edges: {edge_count}")
    print(f"Level distribution: {levels}")
    return node_count


def main():
    parser = argparse.ArgumentParser(description="Inject tax classification codes")
    parser.add_argument("--db", default="data/finance-tax-graph",
                        help="Path to KuzuDB database")
    parser.add_argument("--json", default="data/extracted/tax_classification_codes.json",
                        help="Path to JSON file")
    parser.add_argument("--skip-edges", action="store_true",
                        help="Skip edge creation (nodes only)")
    args = parser.parse_args()

    # Load JSON
    json_path = Path(args.json)
    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}")
        sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)
    codes = data["codes"]
    print(f"OK: Loaded {len(codes)} tax classification codes from {json_path.name}")

    # Open DB
    db_path = Path(args.db)
    print(f"OK: Opening KuzuDB at {db_path}")
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    # Execute
    create_schema(conn)
    inject_nodes(conn, codes)

    if not args.skip_edges:
        inject_edges(conn, codes)

    verify(conn)
    print("\nDONE")


if __name__ == "__main__":
    main()
