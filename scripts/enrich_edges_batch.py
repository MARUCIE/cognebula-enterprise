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

ISSUING_BODY_KEYWORDS = {
    "国家税务总局": "IB_SAT",
    "财政部": "IB_MOF",
    "国务院": "IB_SC",
    "全国人民代表大会": "IB_NPC",
    "全国人大常委会": "IB_NPC_SC",
    "中国人民银行": "IB_PBC",
    "海关总署": "IB_GAC",
    "国家统计局": "IB_NBS",
    "证监会": "IB_CSRC",
    "银保监会": "IB_CBIRC",
}


def enrich_ku_about_tax(conn) -> int:
    """Create KU_ABOUT_TAX edges for new sub-clauses and QA nodes."""
    csv_path = f"{CSV_DIR}/ku_about_tax_enrich.csv"

    # Find KnowledgeUnit and LegalClause nodes without KU_ABOUT_TAX edges
    # Focus on new sub-clauses (id contains _p) and QA nodes (id starts with QA_)
    r = conn.execute("""
        MATCH (k:LegalClause)
        WHERE k.id CONTAINS '_p' AND k.content IS NOT NULL
        RETURN k.id, k.title, k.content
        LIMIT 15000
    """)

    pairs = set()
    while r.has_next():
        row = r.get_next()
        kid = str(row[0] or "")
        text = f"{row[1] or ''} {row[2] or ''}"
        for kw, tid in TAX_KEYWORDS.items():
            if kw in text:
                pairs.add((kid, tid))

    # Also do KnowledgeUnit QA nodes
    r = conn.execute("""
        MATCH (k:KnowledgeUnit)
        WHERE k.id STARTS WITH 'QA_'
        RETURN k.id, k.title, k.content
        LIMIT 50000
    """)
    while r.has_next():
        row = r.get_next()
        kid = str(row[0] or "")
        text = f"{row[1] or ''} {row[2] or ''}"
        for kw, tid in TAX_KEYWORDS.items():
            if kw in text:
                pairs.add((kid, tid))
                break  # one per KU

    if not pairs:
        return 0

    with open(csv_path, "w", newline="") as f:
        for kid, tid in pairs:
            csv.writer(f).writerow([kid, tid])

    try:
        conn.execute(f'COPY KU_ABOUT_TAX FROM "{csv_path}" (header=false)')
        return len(pairs)
    except Exception as e:
        print(f"  KU_ABOUT_TAX ERROR: {str(e)[:80]}")
        return 0


def enrich_issued_by(conn) -> int:
    """Create ISSUED_BY edges for LawOrRegulation without issuing body links."""
    csv_path = f"{CSV_DIR}/issued_by_enrich.csv"

    # Find LawOrRegulation nodes that have issuingAuthority text but no ISSUED_BY edge
    r = conn.execute("""
        MATCH (d:LawOrRegulation)
        WHERE d.issuingAuthority IS NOT NULL AND size(d.issuingAuthority) >= 2
        AND NOT EXISTS { MATCH (d)-[:ISSUED_BY]->() }
        RETURN d.id, d.issuingAuthority, d.title
        LIMIT 50000
    """)

    pairs = set()
    while r.has_next():
        row = r.get_next()
        did = str(row[0] or "")
        authority = str(row[1] or "")
        title = str(row[2] or "")
        text = f"{authority} {title}"
        for kw, bid in ISSUING_BODY_KEYWORDS.items():
            if kw in text:
                pairs.add((did, bid))
                break

    if not pairs:
        return 0

    with open(csv_path, "w", newline="") as f:
        for did, bid in pairs:
            csv.writer(f).writerow([did, bid])

    try:
        conn.execute(f'COPY ISSUED_BY FROM "{csv_path}" (header=false)')
        return len(pairs)
    except Exception as e:
        print(f"  ISSUED_BY ERROR: {str(e)[:80]}")
        return 0


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
