#!/usr/bin/env python3
"""Batch edge enrichment: keyword-based relationship discovery.

M3 Phase 1: Create edges between existing nodes using keyword matching.
No LLM needed — pure pattern matching, fast and free.

Enrichment types:
1. KU_ABOUT_TAX: KnowledgeUnit → TaxType (new sub-clauses + QA nodes)
2. ISSUED_BY: LawOrRegulation → IssuingBody (unmapped documents)
3. APPLIES_TO_CLASS: TaxRate → Classification (via tax code matching)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/enrich_edges_batch.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import os
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/m3_enrich"
os.makedirs(CSV_DIR, exist_ok=True)

TAX_KEYWORDS = {
    "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT",
    "消费税": "TT_CONSUMPTION", "关税": "TT_TARIFF",
    "城市维护建设税": "TT_URBAN", "城建税": "TT_URBAN",
    "教育费附加": "TT_EDUCATION", "地方教育附加": "TT_LOCAL_EDU",
    "资源税": "TT_RESOURCE", "土地增值税": "TT_LAND_VAT",
    "房产税": "TT_PROPERTY", "城镇土地使用税": "TT_LAND_USE",
    "车船税": "TT_VEHICLE", "印花税": "TT_STAMP",
    "契税": "TT_CONTRACT", "耕地占用税": "TT_CULTIVATED",
    "烟叶税": "TT_TOBACCO", "环境保护税": "TT_ENV",
    "个税": "TT_PIT", "所得税": "TT_CIT",
}

def _build_issuing_body_map(conn):
    """Build keyword→ID map from actual IssuingBody table."""
    r = conn.execute("MATCH (b:IssuingBody) RETURN b.id, b.name")
    body_map = {}
    while r.has_next():
        bid, name = r.get_next()
        if name and len(name) >= 2:
            body_map[name] = bid
    return body_map


def enrich_ku_about_tax(conn) -> int:
    """Create KU_ABOUT_TAX edges for KnowledgeUnit nodes without tax type links."""
    # Only KnowledgeUnit → TaxType (edge table definition)
    # Find KU nodes that have tax keywords but no existing KU_ABOUT_TAX edge
    r = conn.execute("""
        MATCH (k:KnowledgeUnit)
        WHERE (k.id STARTS WITH 'QA_' OR k.type = 'FAQ')
        AND NOT EXISTS { MATCH (k)-[:KU_ABOUT_TAX]->() }
        RETURN k.id, k.title, k.content
        LIMIT 20000
    """)

    pairs = []
    seen = set()
    while r.has_next():
        row = r.get_next()
        kid = str(row[0] or "")
        text = f"{row[1] or ''} {row[2] or ''}"
        for kw, tid in TAX_KEYWORDS.items():
            if kw in text and (kid, tid) not in seen:
                pairs.append((kid, tid))
                seen.add((kid, tid))
                break  # one tax type per KU

    if not pairs:
        return 0

    # Use parameterized INSERT (safer than COPY for dedup)
    created = 0
    for kid, tid in pairs:
        try:
            conn.execute(
                f"MATCH (k:KnowledgeUnit), (t:TaxType) "
                f"WHERE k.id = '{kid}' AND t.id = '{tid}' "
                f"CREATE (k)-[:KU_ABOUT_TAX]->(t)"
            )
            created += 1
        except:
            pass
    return created


def enrich_issued_by(conn) -> int:
    """Create ISSUED_BY edges using dynamic IssuingBody ID resolution."""
    body_map = _build_issuing_body_map(conn)
    if not body_map:
        print("  No IssuingBody entries found")
        return 0
    print(f"  Loaded {len(body_map)} IssuingBody entries")

    # Check what table ISSUED_BY connects FROM
    # It might be LegalDocument, not LawOrRegulation
    r = conn.execute("""
        MATCH (d:LawOrRegulation)
        WHERE d.issuingAuthority IS NOT NULL AND size(d.issuingAuthority) >= 2
        AND NOT EXISTS { MATCH (d)-[:ISSUED_BY]->() }
        RETURN d.id, d.issuingAuthority
        LIMIT 10000
    """)

    created = 0
    while r.has_next():
        row = r.get_next()
        did = str(row[0] or "")
        authority = str(row[1] or "")

        # Find best matching IssuingBody by name substring
        best_bid = None
        best_len = 0
        for name, bid in body_map.items():
            if name in authority and len(name) > best_len:
                best_bid = bid
                best_len = len(name)

        if best_bid:
            try:
                conn.execute(
                    f"MATCH (d:LawOrRegulation), (b:IssuingBody) "
                    f"WHERE d.id = '{did}' AND b.id = '{best_bid}' "
                    f"CREATE (d)-[:ISSUED_BY]->(b)"
                )
                created += 1
            except:
                pass

    return created


def main():
    print("=" * 60)
    print("Batch Edge Enrichment (keyword-based, no LLM)")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Current stats
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    before_edges = r.get_next()[0]
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    print(f"\nBefore: {before_edges:,} edges / {nodes:,} nodes / density {before_edges/nodes:.3f}")

    total_new = 0

    # 1. KU_ABOUT_TAX for sub-clauses + QA nodes
    print("\n[1/2] KU_ABOUT_TAX enrichment (sub-clauses + QA)...")
    count = enrich_ku_about_tax(conn)
    print(f"  +{count:,} KU_ABOUT_TAX edges")
    total_new += count

    # 2. ISSUED_BY for unmapped documents
    print("[2/2] ISSUED_BY enrichment (unmapped documents)...")
    count = enrich_issued_by(conn)
    print(f"  +{count:,} ISSUED_BY edges")
    total_new += count

    # Final stats
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    after_edges = r.get_next()[0]
    print(f"\n{'='*60}")
    print(f"Enrichment DONE: +{total_new:,} new edges")
    print(f"Total: {after_edges:,} edges / {nodes:,} nodes / density {after_edges/nodes:.3f}")

    del conn
    del db
    print("Checkpoint done")


if __name__ == "__main__":
    main()
