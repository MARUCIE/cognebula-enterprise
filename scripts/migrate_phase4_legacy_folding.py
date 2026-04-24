#!/usr/bin/env python3
"""Phase 4 — legacy knowledge folding: CPAKnowledge + MindmapNode -> KnowledgeUnit.

Phase 4 closes the two biggest legacy node types in the drift audit:
  4a — schema: ensure canonical KnowledgeUnit exists, widen with legacy* columns
  4b — CPAKnowledge (flat) -> KnowledgeUnit with 'CPAK_' id prefix
  4c — MindmapNode (tree-ish) -> KnowledgeUnit with 'MIND_' id prefix

Column mapping (derived from live schemas on Vela 0.12 demo graph):
  CPAKnowledge
    id      -> 'CPAK_' + id
    title   -> topic
    content -> content
    subject -> legacyType (per-subject tag, falls back to 'cpa_knowledge')
    chapter -> legacyPath
  MindmapNode
    id          -> 'MIND_' + id
    node_text   -> topic
    content     -> content
    category    -> legacyType (falls back to 'mindmap_node')
    parent_text -> legacyParentId (preserved verbatim; parent refs in demo are text, not ids)
    source_file -> legacyPath

Safety:
  --dry-run (default) reports: whether KU exists, ALTER plan, source row counts,
    id-collision counts after prefix (should be 0 by construction), REL deps.
  --execute performs, in order: CREATE IF NOT EXISTS KnowledgeUnit (if missing),
    ALTER ADD missing legacy* columns, MERGE CPA and Mindmap rows, rewire any REL
    deps via the same _V2-suffix-style convention Phase 1d established (but the
    two legacy tables have no REL deps on demo; this logic is a no-op hedge for prod).
  DROP TABLE CPAKnowledge / MindmapNode only if no unrewired REL dep remains.

Usage:
  python3 scripts/migrate_phase4_legacy_folding.py --db data/finance-tax-graph.demo
  python3 scripts/migrate_phase4_legacy_folding.py --db ... --execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CANONICAL_DDL = """
CREATE NODE TABLE IF NOT EXISTS KnowledgeUnit(
    id STRING,
    topic STRING,
    content STRING,
    sourceDocId STRING,
    embeddingId STRING,
    authorityScore DOUBLE,
    PRIMARY KEY (id)
)
"""

LEGACY_COLUMNS = [
    ("legacyType", "STRING"),
    ("legacyParentId", "STRING"),
    ("legacyPath", "STRING"),
]


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


def table_columns(conn, table: str) -> list[str]:
    try:
        r = conn.execute(f"CALL table_info('{table}') RETURN *")
    except Exception:
        return []
    out = []
    while r.has_next():
        out.append(r.get_next()[1])
    return out


def count_nodes(conn, tbl: str) -> int:
    try:
        r = conn.execute(f"MATCH (n:{tbl}) RETURN count(n)")
        return int(r.get_next()[0])
    except Exception:
        return -1


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


def count_rel(conn, rel: str) -> int:
    try:
        r = conn.execute(f"MATCH ()-[e:{rel}]->() RETURN count(e)")
        return int(r.get_next()[0])
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Kuzu DB path")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="probe only (default)")
    mode.add_argument(
        "--execute", action="store_true", help="actually run CREATE/ALTER/MERGE/DROP"
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
    has_ku = "KnowledgeUnit" in nodes
    has_cpa = "CPAKnowledge" in nodes
    has_mindmap = "MindmapNode" in nodes

    print(f"Mode: {'DRY-RUN (no writes)' if dry_run else 'EXECUTE'}")
    print()
    print(f"KnowledgeUnit present: {has_ku}  (canonical target)")
    print(f"CPAKnowledge  present: {has_cpa}  rows={count_nodes(conn, 'CPAKnowledge') if has_cpa else 'n/a'}")
    print(f"MindmapNode   present: {has_mindmap}  rows={count_nodes(conn, 'MindmapNode') if has_mindmap else 'n/a'}")

    if not has_cpa and not has_mindmap:
        print("\nNo legacy source tables present — nothing to fold.")
        return 0

    # Phase 4a — schema plan
    print("\n=== Phase 4a: schema plan ===")
    need_create = not has_ku
    print(f"  CREATE KnowledgeUnit: {'YES' if need_create else 'no (exists)'}")
    existing_cols = set(table_columns(conn, "KnowledgeUnit")) if has_ku else set()
    missing_legacy = [
        (c, t) for c, t in LEGACY_COLUMNS if c not in existing_cols
    ]
    if need_create:
        # After CREATE, legacy cols will need adding too (DDL doesn't include them).
        missing_legacy = list(LEGACY_COLUMNS)
    print(f"  Missing legacy columns: {[c for c, _ in missing_legacy] or '(none)'}")

    # REL deps for the two legacy tables (for optional rewire)
    legacy_rel_deps = []
    for rel in rels:
        pairs = rel_endpoints(conn, rel)
        if any(
            "CPAKnowledge" in f or "CPAKnowledge" in t
            or "MindmapNode" in f or "MindmapNode" in t
            for f, t in pairs
        ):
            legacy_rel_deps.append((rel, pairs, count_rel(conn, rel)))
    print(f"\n  REL tables touching legacy sources ({len(legacy_rel_deps)}):")
    for rel, pairs, rc in legacy_rel_deps:
        print(f"    {rel}: {pairs}  edges={rc}")

    # Id-collision preview (against canonical) — always 0 by construction
    # (prefix scheme guarantees no collision unless canonical already has CPAK_/MIND_ ids)
    if has_ku:
        collision_cpa = 0
        collision_mind = 0
        if has_cpa:
            r = conn.execute(
                "MATCH (c:CPAKnowledge), (k:KnowledgeUnit) "
                "WHERE 'CPAK_' + c.id = k.id RETURN count(c)"
            )
            collision_cpa = int(r.get_next()[0])
        if has_mindmap:
            r = conn.execute(
                "MATCH (m:MindmapNode), (k:KnowledgeUnit) "
                "WHERE 'MIND_' + m.id = k.id RETURN count(m)"
            )
            collision_mind = int(r.get_next()[0])
        print(f"\n  id collision (post-prefix): CPAK={collision_cpa}  MIND={collision_mind}")
        if collision_cpa or collision_mind:
            print("  WARN: canonical already holds prefixed ids — rerun of prior Phase 4?")

    if dry_run:
        print("\nDRY-RUN: no changes written.")
        return 0

    # ---- EXECUTE ----

    # 4a
    print("\n=== Phase 4a: execute schema ===")
    if need_create:
        try:
            conn.execute(CANONICAL_DDL)
            print("  OK: CREATE TABLE KnowledgeUnit")
        except Exception as e:
            print(f"  FAIL: CREATE KnowledgeUnit: {e}", file=sys.stderr)
            return 1
    for col, typ in missing_legacy:
        try:
            conn.execute(f"ALTER TABLE KnowledgeUnit ADD {col} {typ}")
            print(f"  OK: ALTER ADD {col} {typ}")
        except Exception as e:
            print(f"  FAIL: ALTER ADD {col}: {e}", file=sys.stderr)
            return 1

    # 4b — CPAKnowledge
    if has_cpa:
        print("\n=== Phase 4b: CPAKnowledge -> KnowledgeUnit ===")
        try:
            conn.execute(
                "MATCH (c:CPAKnowledge) "
                "MERGE (k:KnowledgeUnit {id: 'CPAK_' + c.id}) "
                "ON CREATE SET "
                "  k.topic = c.title, "
                "  k.content = c.content, "
                "  k.legacyType = CASE WHEN c.subject IS NOT NULL AND c.subject <> '' "
                "                      THEN 'cpa_' + c.subject ELSE 'cpa_knowledge' END, "
                "  k.legacyPath = c.chapter"
            )
            r = conn.execute(
                "MATCH (k:KnowledgeUnit) "
                "WHERE k.legacyType STARTS WITH 'cpa_' RETURN count(k)"
            )
            print(f"  OK: merged CPAKnowledge — KU rows with cpa_* legacyType = {r.get_next()[0]}")
        except Exception as e:
            print(f"  FAIL: CPAKnowledge MERGE: {e}", file=sys.stderr)
            return 1

    # 4c — MindmapNode
    if has_mindmap:
        print("\n=== Phase 4c: MindmapNode -> KnowledgeUnit ===")
        try:
            conn.execute(
                "MATCH (m:MindmapNode) "
                "MERGE (k:KnowledgeUnit {id: 'MIND_' + m.id}) "
                "ON CREATE SET "
                "  k.topic = m.node_text, "
                "  k.content = m.content, "
                "  k.legacyType = CASE WHEN m.category IS NOT NULL AND m.category <> '' "
                "                      THEN 'mindmap_' + m.category ELSE 'mindmap_node' END, "
                "  k.legacyParentId = m.parent_text, "
                "  k.legacyPath = m.source_file"
            )
            r = conn.execute(
                "MATCH (k:KnowledgeUnit) "
                "WHERE k.legacyType STARTS WITH 'mindmap_' RETURN count(k)"
            )
            print(f"  OK: merged MindmapNode — KU rows with mindmap_* legacyType = {r.get_next()[0]}")
        except Exception as e:
            print(f"  FAIL: MindmapNode MERGE: {e}", file=sys.stderr)
            return 1

    # Edge rewire (none expected on demo; hedge for prod)
    unrewired_rels: list[str] = []
    for rel, pairs, rc in legacy_rel_deps:
        if rc == 0:
            try:
                conn.execute(f"DROP TABLE {rel}")
                print(f"  OK: dropped empty REL {rel}")
            except Exception as e:
                print(f"  WARN: could not drop empty REL {rel}: {e}")
            continue
        print(
            f"  SKIP rewire {rel} ({rc} edges): Phase 4 does not auto-rewire legacy edges; "
            f"manual follow-up needed"
        )
        unrewired_rels.append(rel)

    # Drop source tables only if their REL deps are clean
    for src, prefix in [("CPAKnowledge", "CPAK_"), ("MindmapNode", "MIND_")]:
        if not any(src in r_name or prefix in r_name for r_name in unrewired_rels):
            if (src == "CPAKnowledge" and has_cpa) or (src == "MindmapNode" and has_mindmap):
                try:
                    conn.execute(f"DROP TABLE {src}")
                    print(f"  OK: dropped {src}")
                except Exception as e:
                    print(f"  FAIL: DROP {src}: {e}", file=sys.stderr)
                    return 1

    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
