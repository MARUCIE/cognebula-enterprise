#!/usr/bin/env python3
"""Phase 1d migration — merge TaxIncentiveV2 rows into canonical TaxIncentive.

Why this needs its own script (not Phase 1b ALTER RENAME):
  TaxIncentiveV2 (109 rows, live) coexists with TaxIncentive (already populated).
  Same canonical target, two sources. Straight RENAME would collide.
  This script does row-level MERGE by id, then rewires REL edges, then drops V2.

Safety:
  - --dry-run (default) only reports: conflict count, orphan-edge count,
    schema diff between V2 and canonical.
  - --execute requires both tables present and will:
      1. MATCH (v:TaxIncentiveV2), MERGE (t:TaxIncentive {id: v.id}),
         ON CREATE SET t = v  (keeps existing canonical rows untouched)
      2. For each REL table referencing TaxIncentiveV2 as endpoint:
           - empty: DROP TABLE immediately
           - convention-rewirable (V2 suffix + canonical twin + endpoint shape
             matches after V2->canonical swap): MATCH edge, CREATE equivalent
             edge on canonical rel, DELETE V2 edge, DROP V2 rel
           - otherwise: log as unrewired; V2 rel + TaxIncentiveV2 stay behind
             for manual follow-up
      3. DROP TABLE TaxIncentiveV2 only if every V2 REL dep was resolved

Conflict policy:
  - If TaxIncentive already has a row with the same id as V2: SKIP (keep canonical).
  - If there's a schema mismatch (V2 has columns canonical lacks): log + skip that column.
  - Merge strategy is conservative; no destructive overwrites.

Usage:
  python3 scripts/migrate_phase1d_taxincentive_merge.py --db data/finance-tax-graph.demo
  python3 scripts/migrate_phase1d_taxincentive_merge.py --db ... --execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def show_tables(conn):
    r = conn.execute("CALL show_tables() RETURN *")
    nodes, rels = [], []
    while r.has_next():
        row = r.get_next()
        if row[2] == "NODE":
            nodes.append(row[1])
        elif row[2] == "REL":
            rels.append(row[1])
    return nodes, rels


def table_props(conn, table: str) -> list[tuple[str, str]]:
    """Return [(name, type), ...] for a node table."""
    try:
        r = conn.execute(f"CALL table_info('{table}') RETURN *")
    except Exception:
        return []
    out = []
    while r.has_next():
        row = r.get_next()
        # row[0]=propertyId, row[1]=name, row[2]=type
        out.append((row[1], row[2]))
    return out


def rel_endpoints(conn, rel: str) -> list[tuple[str, str]]:
    try:
        rr = conn.execute(f"CALL show_connection('{rel}') RETURN *")
    except Exception:
        return []
    pairs = []
    while rr.has_next():
        row = rr.get_next()
        pairs.append((row[0], row[1]))
    return pairs


def count_nodes(conn, tbl: str) -> int:
    try:
        r = conn.execute(f"MATCH (n:{tbl}) RETURN count(n)")
        return int(r.get_next()[0])
    except Exception:
        return -1


def count_rel(conn, rel: str) -> int:
    try:
        r = conn.execute(f"MATCH ()-[e:{rel}]->() RETURN count(e)")
        return int(r.get_next()[0])
    except Exception:
        return -1


def count_conflicts(conn) -> int:
    """Rows in both V2 and canonical sharing an id."""
    try:
        r = conn.execute(
            "MATCH (v:TaxIncentiveV2), (t:TaxIncentive) WHERE v.id = t.id RETURN count(v)"
        )
        return int(r.get_next()[0])
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Kuzu DB path")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="probe only (default)")
    mode.add_argument(
        "--execute", action="store_true", help="actually run MERGE + DROP"
    )
    args = ap.parse_args()

    dry_run = not args.execute

    import kuzu  # noqa: WPS433

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"ERROR: {db_path} does not exist", file=sys.stderr)
        return 2

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    nodes, rels = show_tables(conn)
    has_v2 = "TaxIncentiveV2" in nodes
    has_canonical = "TaxIncentive" in nodes

    print(f"Mode: {'DRY-RUN (no writes)' if dry_run else 'EXECUTE'}")
    print()
    print(f"TaxIncentiveV2 present:   {has_v2}")
    print(f"TaxIncentive  present:    {has_canonical}")

    if not has_v2:
        print("\nNo TaxIncentiveV2 table — nothing to merge.")
        return 0

    v2_rows = count_nodes(conn, "TaxIncentiveV2")
    canonical_rows = count_nodes(conn, "TaxIncentive") if has_canonical else 0
    print(f"TaxIncentiveV2 rows:      {v2_rows}")
    print(f"TaxIncentive   rows:      {canonical_rows}")

    if has_canonical:
        conflicts = count_conflicts(conn)
        print(f"id conflicts (both):      {conflicts}")
    else:
        conflicts = 0

    v2_props = table_props(conn, "TaxIncentiveV2")
    canonical_props = table_props(conn, "TaxIncentive") if has_canonical else []
    v2_cols = {n for n, _ in v2_props}
    canonical_cols = {n for n, _ in canonical_props}
    v2_only = v2_cols - canonical_cols
    canonical_only = canonical_cols - v2_cols
    print("\nSchema diff:")
    print(f"  V2-only columns       : {sorted(v2_only) or '(none)'}")
    print(f"  canonical-only columns: {sorted(canonical_only) or '(none)'}")

    # Edge dependencies on V2
    v2_rel_deps = []
    for rel in rels:
        pairs = rel_endpoints(conn, rel)
        if any(f == "TaxIncentiveV2" or t == "TaxIncentiveV2" for f, t in pairs):
            v2_rel_deps.append((rel, pairs, count_rel(conn, rel)))

    print(f"\nREL tables touching TaxIncentiveV2 ({len(v2_rel_deps)}):")
    for rel, pairs, rc in v2_rel_deps:
        print(f"  {rel}: {pairs}  edges={rc}")

    if dry_run:
        print("\nDRY-RUN: no changes written.")
        print(
            "\nNext: if schema diff is empty and conflicts are acceptable, re-run with --execute."
        )
        return 0

    # Execute
    if not has_canonical:
        print(
            "\nERROR: TaxIncentive (canonical target) missing. Create it first via schemas/ontology_v4.2.cypher.",
            file=sys.stderr,
        )
        return 2

    if v2_only:
        print(
            f"\nERROR: TaxIncentiveV2 has columns not in canonical ({sorted(v2_only)}). "
            f"Widen canonical schema first or drop extra columns before merge.",
            file=sys.stderr,
        )
        return 2

    print("\n=== Executing MERGE ===")
    shared_cols = sorted(v2_cols & canonical_cols - {"id"})
    set_clause = ", ".join(f"t.{c} = v.{c}" for c in shared_cols) if shared_cols else ""
    merge_cypher = "MATCH (v:TaxIncentiveV2) " "MERGE (t:TaxIncentive {id: v.id}) " + (
        f"ON CREATE SET {set_clause}" if set_clause else ""
    )
    try:
        conn.execute(merge_cypher)
        print(f"  OK: merged {v2_rows} V2 rows into canonical")
    except Exception as e:
        print(f"  FAIL: MERGE: {e}", file=sys.stderr)
        return 1

    # Edge rewire — per REL dep, attempt convention-based rewire, then drop V2 rel.
    # Convention: a V2 rel named FOO_V2 with endpoints swapping TaxIncentiveV2<->TaxIncentive
    # against its canonical twin FOO is auto-rewirable. Mismatches are logged and skipped
    # (user must author a manual rewire rule). Conflict-row edges are rewired too — the
    # canonical row with the same id absorbs them.
    unrewired_rels: list[str] = []
    for rel, pairs, rc in v2_rel_deps:
        if rc == 0:
            try:
                conn.execute(f"DROP TABLE {rel}")
                print(f"  OK: dropped empty REL {rel}")
            except Exception as e:
                print(f"  WARN: could not drop empty REL {rel}: {e}")
            continue
        if not rel.endswith("_V2"):
            print(f"  SKIP {rel}: no `_V2` suffix convention; rewire manually")
            unrewired_rels.append(rel)
            continue
        canonical_rel = rel[:-3]
        if canonical_rel not in rels:
            print(f"  SKIP {rel}: canonical twin `{canonical_rel}` not found")
            unrewired_rels.append(rel)
            continue
        canonical_pairs = rel_endpoints(conn, canonical_rel)
        expected_pairs = [
            (
                f if f != "TaxIncentiveV2" else "TaxIncentive",
                t if t != "TaxIncentiveV2" else "TaxIncentive",
            )
            for f, t in pairs
        ]
        if sorted(canonical_pairs) != sorted(expected_pairs):
            print(
                f"  SKIP {rel}: endpoint shape mismatch "
                f"(V2={pairs} vs canonical={canonical_pairs})"
            )
            unrewired_rels.append(rel)
            continue
        rewire_ok = True
        for from_t, to_t in pairs:
            if from_t == "TaxIncentiveV2":
                cypher = (
                    f"MATCH (v:TaxIncentiveV2)-[e:{rel}]->(x:{to_t}), "
                    f"(c:TaxIncentive {{id: v.id}}) "
                    f"CREATE (c)-[:{canonical_rel}]->(x) "
                    f"DELETE e"
                )
            else:
                cypher = (
                    f"MATCH (x:{from_t})-[e:{rel}]->(v:TaxIncentiveV2), "
                    f"(c:TaxIncentive {{id: v.id}}) "
                    f"CREATE (x)-[:{canonical_rel}]->(c) "
                    f"DELETE e"
                )
            try:
                conn.execute(cypher)
                print(f"  OK: rewired {rel}[{from_t}->{to_t}] into {canonical_rel}")
            except Exception as e:
                print(f"  FAIL rewire {rel}[{from_t}->{to_t}]: {e}", file=sys.stderr)
                rewire_ok = False
                break
        if not rewire_ok:
            unrewired_rels.append(rel)
            continue
        try:
            conn.execute(f"DROP TABLE {rel}")
            print(f"  OK: dropped {rel} after rewire")
        except Exception as e:
            print(f"  WARN: rewired but could not drop {rel}: {e}")
            unrewired_rels.append(rel)

    try:
        if not unrewired_rels:
            conn.execute("DROP TABLE TaxIncentiveV2")
            print("  OK: dropped TaxIncentiveV2")
        else:
            print(
                f"  SKIP DROP TaxIncentiveV2 — unrewired REL dep(s): {unrewired_rels}"
            )
    except Exception as e:
        print(f"  FAIL: DROP TaxIncentiveV2: {e}", file=sys.stderr)
        return 1

    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
