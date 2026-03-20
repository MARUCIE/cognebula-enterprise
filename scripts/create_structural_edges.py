#!/usr/bin/env python3
"""Create structural edges to break TaxType isolation.

Fills 8 new edge tables connecting BusinessActivity, TaxIncentive, ComplianceRule,
FilingForm, AccountingSubject, RiskIndicator, KnowledgeUnit, AuditTrigger → TaxType.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/create_structural_edges.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import os
import re

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv"
os.makedirs(CSV_DIR, exist_ok=True)

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

# Tax keyword → TaxType ID mapping
TAX_KEYWORDS = {
    "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT",
    "消费税": "TT_CONSUMPTION", "关税": "TT_TARIFF",
    "城市维护建设税": "TT_URBAN", "城建税": "TT_URBAN",
    "教育费附加": "TT_EDUCATION", "地方教育附加": "TT_LOCAL_EDU",
    "资源税": "TT_RESOURCE", "土地增值税": "TT_LAND_VAT",
    "房产税": "TT_PROPERTY", "城镇土地使用税": "TT_LAND_USE",
    "车船税": "TT_VEHICLE", "印花税": "TT_STAMP",
    "契税": "TT_CONTRACT", "耕地占用税": "TT_CULTIVATED",
    "烟叶税": "TT_TOBACCO", "船舶吨税": "TT_TONNAGE",
    "环境保护税": "TT_ENV", "环保税": "TT_ENV",
    "个税": "TT_PIT", "所得税": "TT_CIT",
}

def match_tax(text):
    """Find all TaxType IDs mentioned in text."""
    if not text:
        return set()
    matches = set()
    for kw, tid in TAX_KEYWORDS.items():
        if kw in str(text):
            matches.add(tid)
    return matches

def create_edges_by_content(source_table, source_text_field, rel_type, desc):
    """Match source nodes to TaxType by keyword in their text content."""
    csv_path = f"{CSV_DIR}/{rel_type.lower()}.csv"
    r = conn.execute(f"MATCH (n:{source_table}) RETURN n.id, n.{source_text_field}")
    pairs = []
    while r.has_next():
        row = r.get_next()
        sid = str(row[0] or "")
        text = str(row[1] or "")
        for tid in match_tax(text):
            pairs.append((sid, tid))

    if not pairs:
        # Try name field
        r = conn.execute(f"MATCH (n:{source_table}) RETURN n.id, n.name")
        while r.has_next():
            row = r.get_next()
            sid = str(row[0] or "")
            text = str(row[1] or "")
            for tid in match_tax(text):
                pairs.append((sid, tid))

    # Deduplicate
    pairs = list(set(pairs))

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        for sid, tid in pairs:
            w.writerow([sid, tid])

    if pairs:
        try:
            conn.execute(f'COPY {rel_type} FROM "{csv_path}" (header=false)')
            print(f"  {desc}: {len(pairs):,} edges")
        except Exception as e:
            print(f"  {desc}: COPY ERR: {str(e)[:60]}")
    else:
        print(f"  {desc}: 0 (no keyword matches)")
    return len(pairs)

total = 0

# 1. TRIGGERS_TAX: BusinessActivity → TaxType
print("[1/8] TRIGGERS_TAX (BusinessActivity → TaxType)")
total += create_edges_by_content("BusinessActivity", "name", "TRIGGERS_TAX", "BusinessActivity→TaxType")

# 2. INCENTIVE_FOR_TAX: TaxIncentiveV2 → TaxType
print("[2/8] INCENTIVE_FOR_TAX (TaxIncentive → TaxType)")
total += create_edges_by_content("TaxIncentiveV2", "name", "INCENTIVE_FOR_TAX", "TaxIncentive→TaxType")

# 3. RULE_FOR_TAX: ComplianceRuleV2 → TaxType
print("[3/8] RULE_FOR_TAX (ComplianceRule → TaxType)")
total += create_edges_by_content("ComplianceRuleV2", "name", "RULE_FOR_TAX", "ComplianceRule→TaxType")

# 4. FILING_FOR_TAX: FilingFormV2 → TaxType
print("[4/8] FILING_FOR_TAX (FilingForm → TaxType)")
total += create_edges_by_content("FilingFormV2", "name", "FILING_FOR_TAX", "FilingForm→TaxType")

# 5. MAPS_TO_ACCOUNT: TaxType → AccountingSubject (hardcoded domain knowledge)
print("[5/8] MAPS_TO_ACCOUNT (TaxType → AccountingSubject)")
csv_path = f"{CSV_DIR}/maps_to_account.csv"
# Find AccountingSubject nodes containing tax-related keywords
r = conn.execute("MATCH (a:AccountingSubject) RETURN a.id, a.name")
acct_pairs = []
while r.has_next():
    row = r.get_next()
    aid = str(row[0] or "")
    name = str(row[1] or "")
    for tid in match_tax(name):
        acct_pairs.append((tid, aid))  # TaxType → AccountingSubject
acct_pairs = list(set(acct_pairs))
with open(csv_path, "w", newline="") as f:
    for tid, aid in acct_pairs:
        csv.writer(f).writerow([tid, aid])
if acct_pairs:
    try:
        conn.execute(f'COPY MAPS_TO_ACCOUNT FROM "{csv_path}" (header=false)')
        print(f"  TaxType→AccountingSubject: {len(acct_pairs):,} edges")
    except Exception as e:
        print(f"  COPY ERR: {str(e)[:60]}")
    total += len(acct_pairs)
else:
    print(f"  TaxType→AccountingSubject: 0")

# 6. RISK_FOR_TAX: RiskIndicatorV2 → TaxType
print("[6/8] RISK_FOR_TAX (RiskIndicator → TaxType)")
total += create_edges_by_content("RiskIndicatorV2", "name", "RISK_FOR_TAX", "RiskIndicator→TaxType")

# 7. KU_ABOUT_TAX: KnowledgeUnit → TaxType (sample first 10K)
print("[7/8] KU_ABOUT_TAX (KnowledgeUnit → TaxType)")
csv_path = f"{CSV_DIR}/ku_about_tax.csv"
r = conn.execute("MATCH (k:KnowledgeUnit) RETURN k.id, k.title, k.content LIMIT 10000")
ku_pairs = []
while r.has_next():
    row = r.get_next()
    kid = str(row[0] or "")
    text = str(row[1] or "") + " " + str(row[2] or "")
    for tid in match_tax(text):
        ku_pairs.append((kid, tid))
ku_pairs = list(set(ku_pairs))
with open(csv_path, "w", newline="") as f:
    for kid, tid in ku_pairs:
        csv.writer(f).writerow([kid, tid])
if ku_pairs:
    try:
        conn.execute(f'COPY KU_ABOUT_TAX FROM "{csv_path}" (header=false)')
        print(f"  KnowledgeUnit→TaxType: {len(ku_pairs):,} edges")
    except Exception as e:
        print(f"  COPY ERR: {str(e)[:60]}")
    total += len(ku_pairs)

# 8. AUDIT_FOR_TAX: AuditTrigger → TaxType
print("[8/8] AUDIT_FOR_TAX (AuditTrigger → TaxType)")
total += create_edges_by_content("AuditTrigger", "name", "AUDIT_FOR_TAX", "AuditTrigger→TaxType")

# Final stats
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
edges = r.get_next()[0]
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
print(f"\n=== DONE: +{total:,} new structural edges ===")
print(f"Total: {edges:,} edges / {nodes:,} nodes = density {edges/nodes:.3f}")

del conn
del db
print("Checkpoint done")
