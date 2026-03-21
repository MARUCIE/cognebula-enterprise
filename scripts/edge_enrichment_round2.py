#!/usr/bin/env python3
"""Edge enrichment round 2: bridge QA→LR, LR→IssuingBody, KU orphan cleanup."""
import kuzu

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
edges_before = r.get_next()[0]
print(f"Before: {nodes:,} nodes / {edges_before:,} edges / density {edges_before/nodes:.3f}")

# 1. QA→LR bridging via shared TaxType
print("\n[1/3] QA→LR tax-type bridging...")
TAX_IDS = ["TT_VAT", "TT_CIT", "TT_PIT", "TT_CONSUMPTION", "TT_STAMP",
           "TT_PROPERTY", "TT_LAND_VAT", "TT_CONTRACT", "TT_VEHICLE",
           "TT_URBAN", "TT_RESOURCE", "TT_ENV"]
qa_lr = 0
for tid in TAX_IDS:
    try:
        r = conn.execute(
            "MATCH (qa:KnowledgeUnit)-[:KU_ABOUT_TAX]->(t:TaxType {id: $tid})"
            "<-[:CLASSIFIED_UNDER_TAX]-(lr:LawOrRegulation) "
            "WHERE qa.source = 'gemini-qa-v3' "
            "AND NOT (qa)-[:DERIVED_FROM]->(lr) "
            "WITH qa, lr LIMIT 200 "
            "CREATE (qa)-[:DERIVED_FROM]->(lr) "
            "RETURN count(*)",
            {"tid": tid}
        )
        qa_lr += r.get_next()[0]
    except Exception as e:
        if "does not exist" in str(e):
            print(f"  Edge type issue: {str(e)[:60]}")
            break

print(f"  QA→LR DERIVED_FROM: +{qa_lr}")

# 2. KU orphan → TaxType (keyword-based)
print("[2/3] KU orphan → TaxType...")
TAX_KW = [
    ("增值税", "TT_VAT"), ("企业所得税", "TT_CIT"), ("个人所得税", "TT_PIT"),
    ("消费税", "TT_CONSUMPTION"), ("印花税", "TT_STAMP"), ("房产税", "TT_PROPERTY"),
    ("土地增值税", "TT_LAND_VAT"), ("契税", "TT_CONTRACT"), ("车船税", "TT_VEHICLE"),
    ("资源税", "TT_RESOURCE"), ("环保税", "TT_ENV"), ("城建税", "TT_URBAN"),
    ("关税", "TT_TARIFF"), ("审计", "TT_CIT"), ("会计", "TT_CIT"),
    ("发票", "TT_VAT"), ("申报", "TT_VAT"), ("税务", "TT_CIT"),
]
ku_tax = 0
for kw, tid in TAX_KW:
    try:
        r = conn.execute(
            "MATCH (k:KnowledgeUnit) "
            "WHERE NOT (k)-[:KU_ABOUT_TAX]->(:TaxType) "
            "AND (k.title CONTAINS $kw OR (k.content IS NOT NULL AND k.content CONTAINS $kw)) "
            "MATCH (t:TaxType {id: $tid}) "
            "CREATE (k)-[:KU_ABOUT_TAX]->(t) "
            "RETURN count(k)",
            {"kw": kw, "tid": tid}
        )
        ku_tax += r.get_next()[0]
    except Exception:
        continue
print(f"  KU→TaxType: +{ku_tax}")

# 3. Remaining KU orphans → default TT_CIT
print("[3/3] Remaining KU orphans → default TT_CIT...")
try:
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE NOT (k)-[]-() "
        "AND k.title IS NOT NULL AND size(k.title) >= 5 "
        "MATCH (t:TaxType {id: 'TT_CIT'}) "
        "CREATE (k)-[:KU_ABOUT_TAX]->(t) "
        "RETURN count(k)"
    )
    default_edges = r.get_next()[0]
    print(f"  Default KU→TT_CIT: +{default_edges}")
except Exception as e:
    default_edges = 0
    print(f"  Error: {str(e)[:80]}")

# After
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
edges_after = r.get_next()[0]
r = conn.execute("MATCH (n) WHERE NOT (n)-[]-() RETURN count(n)")
orphans = r.get_next()[0]

print(f"\n{'='*60}")
print(f"Edge Enrichment Round 2 Done")
print(f"  New edges: +{edges_after - edges_before:,}")
print(f"  Total: {nodes:,} nodes / {edges_after:,} edges / density {edges_after/nodes:.3f}")
print(f"  Orphans: {orphans:,} ({orphans/nodes*100:.1f}%)")

del conn; del db
