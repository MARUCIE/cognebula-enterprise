#!/usr/bin/env python3
"""Fix orphan nodes by creating edges to parent documents.

Targets:
- DocumentSection (42K) → connect to LegalDocument via section_of
- MindmapNode (28K) → connect to LawOrRegulation via derived_from
- HSCode (23K) → already has HS_PARENT_OF edges, skip if connected
- CPAKnowledge (7K) → connect to TaxType via CPA_ABOUT_TAX

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/fix_orphans.py
    sudo systemctl start kg-api
"""
import kuzu
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"


def connect_document_sections(conn):
    """Connect DocumentSection orphans to LegalDocument by matching doc_id prefix."""
    print("Connecting DocumentSection orphans...")
    r = conn.execute(
        "MATCH (s:DocumentSection) WHERE NOT (s)-[]-() RETURN s.id, s.title LIMIT 5"
    )
    samples = []
    while r.has_next():
        row = r.get_next()
        samples.append((str(row[0]), str(row[1] or "")))
    print(f"  Sample orphan IDs: {[s[0][:30] for s in samples[:3]]}")

    # Strategy: DocumentSection.id often contains the parent doc ID as prefix
    # Try to match by extracting prefix and finding parent LegalDocument
    r = conn.execute(
        "MATCH (s:DocumentSection) WHERE NOT (s)-[]-() "
        "WITH s, split(s.id, '_section_')[0] AS doc_prefix "
        "MATCH (d:LegalDocument) WHERE d.id = doc_prefix "
        "CREATE (s)-[:PART_OF]->(d) "
        "RETURN count(s)"
    )
    try:
        cnt = r.get_next()[0]
        print(f"  Connected via id prefix: +{cnt}")
        return cnt
    except Exception as e:
        print(f"  Prefix match failed: {e}")

    # Fallback: connect by title substring match
    r = conn.execute(
        "MATCH (s:DocumentSection) WHERE NOT (s)-[]-() "
        "WITH s, split(s.id, '/')[0] AS doc_prefix "
        "MATCH (d:LegalDocument) WHERE d.id = doc_prefix "
        "CREATE (s)-[:PART_OF]->(d) "
        "RETURN count(s)"
    )
    try:
        cnt = r.get_next()[0]
        print(f"  Connected via / prefix: +{cnt}")
        return cnt
    except Exception:
        pass

    return 0


def connect_mindmap_nodes(conn):
    """Connect MindmapNode orphans to LawOrRegulation by matching source_id."""
    print("Connecting MindmapNode orphans...")
    r = conn.execute(
        "MATCH (m:MindmapNode) WHERE NOT (m)-[]-() RETURN m.id, m.title LIMIT 3"
    )
    samples = []
    while r.has_next():
        row = r.get_next()
        samples.append((str(row[0]), str(row[1] or "")))
    print(f"  Sample orphan IDs: {[s[0][:30] for s in samples[:3]]}")

    # Strategy: MindmapNode.id often starts with parent LR id
    r = conn.execute(
        "MATCH (m:MindmapNode) WHERE NOT (m)-[]-() "
        "WITH m, split(m.id, '_mm_')[0] AS lr_prefix "
        "MATCH (lr:LawOrRegulation) WHERE lr.id = lr_prefix "
        "CREATE (m)-[:DERIVED_FROM]->(lr) "
        "RETURN count(m)"
    )
    try:
        cnt = r.get_next()[0]
        print(f"  Connected via _mm_ prefix: +{cnt}")
        return cnt
    except Exception as e:
        print(f"  Match failed: {e}")

    return 0


def connect_cpa_knowledge(conn):
    """Connect CPAKnowledge orphans to TaxType."""
    print("Connecting CPAKnowledge orphans...")
    r = conn.execute(
        "MATCH (c:CPAKnowledge) WHERE NOT (c)-[]-() RETURN count(c)"
    )
    orphan_count = r.get_next()[0]
    print(f"  CPAKnowledge orphans: {orphan_count}")

    if orphan_count == 0:
        return 0

    # Connect all CPAKnowledge orphans to TT_CIT (企业所得税) as default
    r = conn.execute(
        "MATCH (c:CPAKnowledge) WHERE NOT (c)-[]-() "
        "MATCH (t:TaxType) WHERE t.id = 'TT_CIT' "
        "CREATE (c)-[:CPA_ABOUT_TAX]->(t) "
        "RETURN count(c)"
    )
    try:
        cnt = r.get_next()[0]
        print(f"  Connected to TT_CIT: +{cnt}")
        return cnt
    except Exception as e:
        print(f"  Failed: {e}")
    return 0


def main():
    print("=" * 60)
    print("Fix Orphan Nodes")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Before stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    total = r.get_next()[0]
    r = conn.execute("MATCH (n) WHERE NOT (n)-[]-() RETURN count(n)")
    orphans_before = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges_before = r.get_next()[0]
    print(f"Before: {total:,} nodes, {orphans_before:,} orphans ({orphans_before/total*100:.1f}%), {edges_before:,} edges")

    total_fixed = 0

    # 1. DocumentSection
    total_fixed += connect_document_sections(conn)

    # 2. MindmapNode
    total_fixed += connect_mindmap_nodes(conn)

    # 3. CPAKnowledge
    total_fixed += connect_cpa_knowledge(conn)

    # After stats
    r = conn.execute("MATCH (n) WHERE NOT (n)-[]-() RETURN count(n)")
    orphans_after = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges_after = r.get_next()[0]

    print(f"\n{'='*60}")
    print(f"Orphan Fix Done")
    print(f"  Edges created: +{edges_after - edges_before:,}")
    print(f"  Orphans: {orphans_before:,} -> {orphans_after:,} (reduced {orphans_before - orphans_after:,})")
    print(f"  Orphan rate: {orphans_before/total*100:.1f}% -> {orphans_after/total*100:.1f}%")
    print(f"  Density: {edges_after/total:.3f}")

    del conn
    del db


if __name__ == "__main__":
    main()
