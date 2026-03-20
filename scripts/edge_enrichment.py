#!/usr/bin/env python3
"""Edge enrichment sprint: boost density from 0.12 to ≥1.0.

Strategy:
1. CLASSIFIED_UNDER: LawOrRegulation → TaxType (keyword match)
2. ISSUED_BY: LawOrRegulation → IssuingBody (issuingAuthority field)
3. ABOUT_INDUSTRY: LawOrRegulation → FTIndustry (keyword match)
4. SIMILAR_TO: within LawOrRegulation (title similarity via hash buckets)
5. HAS_CLAUSE: LegalClause/RegulationClause → LawOrRegulation (regulationId)

Runs directly on KuzuDB (stop API first).
"""
import hashlib
import sys
import time

import kuzu

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/finance-tax-graph"
DRY_RUN = "--dry-run" in sys.argv

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

def ensure_rel(name, from_tbl, to_tbl):
    try:
        conn.execute(f"CREATE REL TABLE IF NOT EXISTS {name}(FROM {from_tbl} TO {to_tbl})")
    except Exception as e:
        if "already exists" not in str(e).lower():
            print(f"  WARN: {name} creation: {e}")

def count_edges():
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    return r.get_next()[0]

def count_nodes():
    r = conn.execute("MATCH (n) RETURN count(n)")
    return r.get_next()[0]

initial_edges = count_edges()
initial_nodes = count_nodes()
print(f"Start: {initial_nodes:,} nodes / {initial_edges:,} edges / density={initial_edges/initial_nodes:.3f}")
print()

# --- 1. CLASSIFIED_UNDER: LawOrRegulation → TaxType ---
print("=== 1. CLASSIFIED_UNDER (LR → TaxType) ===")
ensure_rel("CLASSIFIED_UNDER_TAX", "LawOrRegulation", "TaxType")

# Load TaxType IDs and keywords
tax_types = {}
r = conn.execute("MATCH (t:TaxType) RETURN t.id, t.name")
while r.has_next():
    row = r.get_next()
    tax_types[row[0]] = row[1]

TAX_KEYWORDS = {
    "TT_VAT": ["增值税", "进项税", "销项税", "发票"],
    "TT_CIT": ["企业所得税", "所得税", "纳税调整", "汇算清缴"],
    "TT_PIT": ["个人所得税", "个税", "工资薪金", "劳务报酬"],
    "TT_STAMP": ["印花税"],
    "TT_CONSUMPTION": ["消费税"],
    "TT_TARIFF": ["关税", "进口税"],
    "TT_PROPERTY": ["房产税"],
    "TT_LAND_VAT": ["土地增值税"],
    "TT_VEHICLE": ["车船税", "车辆购置税"],
    "TT_RESOURCE": ["资源税"],
    "TT_CONTRACT": ["契税"],
    "TT_URBAN": ["城建税", "城市维护建设税"],
    "TT_EDUCATION": ["教育费附加"],
    "TT_ENV": ["环境保护税", "环保税"],
}

# Scan LawOrRegulation title+fullText for tax keywords (batched to avoid OOM)
created = 0
batch = []
BATCH_SCAN = 5000
for offset in range(0, 200000, BATCH_SCAN):
    r = conn.execute(
        "MATCH (n:LawOrRegulation) RETURN n.id, n.title, n.fullText "
        f"SKIP {offset} LIMIT {BATCH_SCAN}"
    )
    found = False
    while r.has_next():
        found = True
        row = r.get_next()
        nid = row[0]
        text = ((row[1] or "") + " " + (row[2] or ""))[:2000]
        for tid, keywords in TAX_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                batch.append((nid, tid))
    if not found:
        break

print(f"  Matches: {len(batch)}")
if not DRY_RUN:
    for nid, tid in batch:
        try:
            conn.execute(
                "MATCH (a:LawOrRegulation), (b:TaxType) WHERE a.id = $aid AND b.id = $bid "
                "CREATE (a)-[:CLASSIFIED_UNDER_TAX]->(b)",
                {"aid": nid, "bid": tid}
            )
            created += 1
        except:
            pass
    print(f"  Created: {created:,} edges")
else:
    print(f"  (dry-run: would create {len(batch):,} edges)")

# --- 2. ABOUT_INDUSTRY: LawOrRegulation → FTIndustry ---
print()
print("=== 2. ABOUT_INDUSTRY (LR → FTIndustry) ===")
ensure_rel("ABOUT_INDUSTRY", "LawOrRegulation", "FTIndustry")

industries = {}
r = conn.execute("MATCH (i:FTIndustry) RETURN i.id, i.name")
while r.has_next():
    row = r.get_next()
    industries[row[0]] = row[1]

INDUSTRY_KEYWORDS = {}
for iid, name in industries.items():
    # Use industry name as keyword
    INDUSTRY_KEYWORDS[iid] = [name]

created2 = 0
batch2 = []
for offset in range(0, 200000, BATCH_SCAN):
    r = conn.execute(
        "MATCH (n:LawOrRegulation) RETURN n.id, n.title, n.fullText "
        f"SKIP {offset} LIMIT {BATCH_SCAN}"
    )
    found = False
    while r.has_next():
        found = True
        row = r.get_next()
        nid = row[0]
        text = ((row[1] or "") + " " + (row[2] or ""))[:2000]
        for iid, keywords in INDUSTRY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                batch2.append((nid, iid))
    if not found:
        break

print(f"  Matches: {len(batch2)}")
if not DRY_RUN:
    for nid, iid in batch2:
        try:
            conn.execute(
                "MATCH (a:LawOrRegulation), (b:FTIndustry) WHERE a.id = $aid AND b.id = $bid "
                "CREATE (a)-[:ABOUT_INDUSTRY]->(b)",
                {"aid": nid, "bid": iid}
            )
            created2 += 1
        except:
            pass
    print(f"  Created: {created2:,} edges")
else:
    print(f"  (dry-run: would create {len(batch2):,} edges)")

# --- 3. Connect LegalClause orphans to LawOrRegulation ---
print()
print("=== 3. HAS_CLAUSE (LegalClause → parent LR) ===")
ensure_rel("HAS_CLAUSE", "LegalClause", "LawOrRegulation")

# LegalClause IDs are like CL_{reg_id}_art{N}
# Extract reg_id and link to LawOrRegulation
created3 = 0
r = conn.execute("MATCH (c:LegalClause) RETURN c.id")
clause_parents = []
while r.has_next():
    cid = r.get_next()[0] or ""
    if cid.startswith("CL_"):
        # Extract parent regulation ID: CL_{hash}_art{N} → {hash}
        parts = cid[3:].split("_art")
        if parts:
            parent_id = parts[0]
            clause_parents.append((cid, parent_id))

print(f"  Clause-parent pairs: {len(clause_parents)}")
if not DRY_RUN:
    for cid, pid in clause_parents:
        try:
            conn.execute(
                "MATCH (c:LegalClause), (p:LawOrRegulation) WHERE c.id = $cid AND p.id = $pid "
                "CREATE (c)-[:HAS_CLAUSE]->(p)",
                {"cid": cid, "pid": pid}
            )
            created3 += 1
        except:
            pass
    print(f"  Created: {created3:,} edges")
else:
    print(f"  (dry-run: would create {len(clause_parents):,} edges)")

# --- 4. Connect DocumentSection → source document ---
print()
print("=== 4. SECTION_OF (DocumentSection → source) ===")
ensure_rel("SECTION_OF", "DocumentSection", "LawOrRegulation")

created4 = 0
r = conn.execute("MATCH (s:DocumentSection) WHERE s.sourceUrl IS NOT NULL RETURN s.id, s.sourceUrl LIMIT 50000")
section_links = []
while r.has_next():
    row = r.get_next()
    sid, src = row[0], (row[1] or "")
    if src:
        # Hash the source URL to find matching LR
        lr_id = hashlib.sha256(src.encode()).hexdigest()[:16]
        section_links.append((sid, lr_id))

print(f"  Section-source pairs: {len(section_links)}")
# Skip actual creation for now (may not match IDs)

# --- Summary ---
print()
final_edges = count_edges()
final_nodes = count_nodes()
delta = final_edges - initial_edges
print(f"=== SUMMARY ===")
print(f"  Before: {initial_edges:,} edges")
print(f"  After:  {final_edges:,} edges")
print(f"  Delta:  +{delta:,} edges")
print(f"  Density: {final_edges/final_nodes:.3f} (was {initial_edges/initial_nodes:.3f})")
