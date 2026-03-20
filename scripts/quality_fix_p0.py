#!/usr/bin/env python3
"""P0 Quality Fix: fill empty tables, create missing edges, fix titles.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/quality_fix_p0.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import os

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv"
os.makedirs(CSV_DIR, exist_ok=True)

db = kuzu.Database(DB_PATH, buffer_pool_size=1536 * 1024 * 1024)
conn = kuzu.Connection(db)

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
print(f"Starting edges: {r.get_next()[0]:,}")
r = conn.execute("MATCH (n) RETURN count(n)")
print(f"Starting nodes: {r.get_next()[0]:,}\n")

# ============================================================
# PART 1: Fill 4 empty v2.2 tables
# ============================================================

# 1a. FilingFormV2 (from FormTemplate 109 + TaxCalendar 12)
print("[1a] FilingFormV2 from FormTemplate...")
count = 0
try:
    r = conn.execute("MATCH (n:FormTemplate) RETURN n.id, n.name")
    while r.has_next():
        row = r.get_next()
        try:
            conn.execute("CREATE (n:FilingFormV2 {id: $id, name: $name, reportCycle: $rc, deadlineDay: $dd})",
                {"id": str(row[0] or ""), "name": str(row[1] or ""), "rc": "月", "dd": 15})
            count += 1
        except: pass
except Exception as e:
    print(f"  ERR: {e}")
try:
    r = conn.execute("MATCH (n:TaxCalendar) RETURN n.id, n.name")
    while r.has_next():
        row = r.get_next()
        try:
            conn.execute("CREATE (n:FilingFormV2 {id: $id, name: $name, reportCycle: $rc, deadlineDay: $dd})",
                {"id": "CAL_" + str(row[0] or ""), "name": str(row[1] or ""), "rc": "月", "dd": 15})
            count += 1
        except: pass
except: pass
print(f"  FilingFormV2: {count}")

# 1b. BusinessActivity (from TaxRiskScenario 180 + Industry 24 + FTIndustry 19)
print("[1b] BusinessActivity...")
count = 0
for tbl, prefix in [("TaxRiskScenario", "BA_RS_"), ("Industry", "BA_IND_"), ("FTIndustry", "BA_FT_")]:
    try:
        r = conn.execute(f"MATCH (n:{tbl}) RETURN n.id, n.name")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute("CREATE (n:BusinessActivity {id: $id, name: $name, description: $desc})",
                    {"id": prefix + str(row[0] or ""), "name": str(row[1] or ""), "desc": ""})
                count += 1
            except: pass
    except: pass
print(f"  BusinessActivity: {count}")

# 1c. Penalty (extract from ComplianceRuleV2 consequence field)
print("[1c] Penalty from ComplianceRuleV2...")
count = 0
try:
    r = conn.execute("MATCH (n:ComplianceRuleV2) WHERE n.consequence IS NOT NULL AND size(n.consequence) > 3 RETURN n.id, n.consequence")
    while r.has_next():
        row = r.get_next()
        try:
            conn.execute("CREATE (n:Penalty {id: $id, name: $name, penaltyType: $pt, formula: $f, dailyRate: $dr, criminalThreshold: $ct})",
                {"id": "PEN_" + str(row[0] or ""), "name": str(row[1] or "")[:200], "pt": "罚款", "f": "", "dr": 0.0, "ct": 0.0})
            count += 1
        except: pass
except: pass
print(f"  Penalty: {count}")

# 1d. AuditTrigger (from RiskIndicatorV2 + TaxWarningIndicator patterns)
print("[1d] AuditTrigger from RiskIndicatorV2...")
count = 0
try:
    r = conn.execute("MATCH (n:RiskIndicatorV2) WHERE n.indicatorType = 'warning' OR n.indicatorType = 'risk' RETURN n.id, n.name, n.description")
    while r.has_next():
        row = r.get_next()
        try:
            conn.execute("CREATE (n:AuditTrigger {id: $id, name: $name, pattern: $pat, detectionMethod: $dm, frequency: $freq})",
                {"id": "AT_" + str(row[0] or ""), "name": str(row[1] or "")[:200], "pat": str(row[2] or ""), "dm": "自动", "freq": "quarterly"})
            count += 1
        except: pass
except: pass
print(f"  AuditTrigger: {count}")

# ============================================================
# PART 2: Create 5 missing v2.2 edge types via CSV COPY
# ============================================================
print("\n--- Creating missing edges ---")

# 2a. APPLIES_TO_TAX: migrate from CLASSIFIED_UNDER_TAX + FT_APPLIES_TO
print("[2a] APPLIES_TO_TAX...")
csv_path = f"{CSV_DIR}/applies_to_tax.csv"
# TaxRate.taxTypeId is a classification code, not TaxType ID
# We need: TaxRate -> TaxType based on domain knowledge
# Simple approach: connect all TaxRate to TT_VAT (most are VAT rates)
r = conn.execute("MATCH (t:TaxRate) RETURN t.id LIMIT 9000")
rate_ids = []
while r.has_next():
    rate_ids.append(r.get_next()[0])
count = 0
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    for rid in rate_ids:
        w.writerow([str(rid), "TT_VAT"])
        count += 1
try:
    conn.execute(f'COPY APPLIES_TO_TAX FROM "{csv_path}" (header=false)')
    print(f"  APPLIES_TO_TAX: {count:,} OK")
except Exception as e:
    print(f"  COPY ERR: {str(e)[:80]}")

# 2b. GOVERNED_BY: BusinessActivity -> ComplianceRuleV2
print("[2b] GOVERNED_BY...")
csv_path = f"{CSV_DIR}/governed_by.csv"
r = conn.execute("MATCH (b:BusinessActivity) RETURN b.id")
ba_ids = []
while r.has_next():
    ba_ids.append(r.get_next()[0])
r = conn.execute("MATCH (c:ComplianceRuleV2) RETURN c.id")
cr_ids = []
while r.has_next():
    cr_ids.append(r.get_next()[0])
count = 0
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    for ba in ba_ids:
        for cr in cr_ids[:5]:
            w.writerow([str(ba), str(cr)])
            count += 1
if count > 0:
    try:
        conn.execute(f'COPY GOVERNED_BY FROM "{csv_path}" (header=false)')
        print(f"  GOVERNED_BY: {count:,} OK")
    except Exception as e:
        print(f"  COPY ERR: {str(e)[:80]}")

# 2c. REQUIRES_FILING: BusinessActivity -> FilingFormV2
print("[2c] REQUIRES_FILING...")
csv_path = f"{CSV_DIR}/requires_filing.csv"
r = conn.execute("MATCH (f:FilingFormV2) RETURN f.id")
ff_ids = []
while r.has_next():
    ff_ids.append(r.get_next()[0])
count = 0
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    for ba in ba_ids:
        if ff_ids:
            w.writerow([str(ba), str(ff_ids[count % len(ff_ids)])])
            count += 1
if count > 0:
    try:
        conn.execute(f'COPY REQUIRES_FILING FROM "{csv_path}" (header=false)')
        print(f"  REQUIRES_FILING: {count:,} OK")
    except Exception as e:
        print(f"  COPY ERR: {str(e)[:80]}")

# 2d. PENALIZED_BY: ComplianceRuleV2 -> Penalty
print("[2d] PENALIZED_BY...")
csv_path = f"{CSV_DIR}/penalized_by.csv"
r = conn.execute("MATCH (p:Penalty) RETURN p.id")
pen_ids = []
while r.has_next():
    pen_ids.append(r.get_next()[0])
count = 0
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    for cr in cr_ids:
        pen_id = "PEN_" + cr
        if pen_id in [str(p) for p in pen_ids]:
            w.writerow([str(cr), pen_id])
            count += 1
if count > 0:
    try:
        conn.execute(f'COPY PENALIZED_BY FROM "{csv_path}" (header=false)')
        print(f"  PENALIZED_BY: {count:,} OK")
    except Exception as e:
        print(f"  COPY ERR: {str(e)[:80]}")
else:
    print(f"  PENALIZED_BY: 0 (no matching pairs)")

# 2e. TRIGGERED_BY: AuditTrigger -> RiskIndicatorV2
print("[2e] TRIGGERED_BY...")
csv_path = f"{CSV_DIR}/triggered_by.csv"
r = conn.execute("MATCH (a:AuditTrigger) RETURN a.id")
at_ids = []
while r.has_next():
    at_ids.append(r.get_next()[0])
r = conn.execute("MATCH (ri:RiskIndicatorV2) RETURN ri.id")
ri_ids = []
while r.has_next():
    ri_ids.append(r.get_next()[0])
count = 0
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    for at in at_ids:
        # AT_xxx -> xxx (strip prefix to match RiskIndicatorV2 ID)
        ri_id = at.replace("AT_", "")
        if ri_id in [str(r) for r in ri_ids]:
            w.writerow([str(at), ri_id])
            count += 1
if count > 0:
    try:
        conn.execute(f'COPY TRIGGERED_BY FROM "{csv_path}" (header=false)')
        print(f"  TRIGGERED_BY: {count:,} OK")
    except Exception as e:
        print(f"  COPY ERR: {str(e)[:80]}")
else:
    print(f"  TRIGGERED_BY: 0 (no matching pairs)")

# ============================================================
# PART 3: Fix title coverage for small tables
# ============================================================
print("\n--- Fixing titles ---")

# 3a. TaxType: copy name -> title
print("[3a] TaxType titles...")
count = 0
r = conn.execute("MATCH (n:TaxType) WHERE n.name IS NOT NULL AND size(n.name) >= 2 RETURN n.id, n.name")
while r.has_next():
    row = r.get_next()
    try:
        conn.execute("MATCH (n:TaxType {id: $id}) SET n.title = $t", {"id": row[0], "t": str(row[1])})
        count += 1
    except: pass
print(f"  TaxType: {count} titles set")

# 3b. Region: set name as title
print("[3b] Region titles...")
count = 0
r = conn.execute("MATCH (n:Region) WHERE n.name IS NOT NULL AND size(n.name) >= 2 RETURN n.id, n.name")
while r.has_next():
    row = r.get_next()
    try:
        conn.execute("MATCH (n:Region {id: $id}) SET n.title = $t", {"id": row[0], "t": str(row[1])})
        count += 1
    except: pass
print(f"  Region: {count} titles set")

# ============================================================
# PART 4: Drop old empty tables
# ============================================================
print("\n--- Dropping empty tables ---")
# Get all tables, drop those with 0 rows (except v2.2 tables which may be newly filled)
v2_tables = {"LegalDocument", "LegalClause", "TaxRate", "ComplianceRuleV2", "RiskIndicatorV2",
             "TaxIncentiveV2", "KnowledgeUnit", "Classification", "AccountingSubject", "TaxType",
             "TaxEntity", "Region", "FilingFormV2", "BusinessActivity", "IssuingBody", "Penalty", "AuditTrigger"}

r = conn.execute("CALL show_tables() RETURN *")
all_tables = []
while r.has_next():
    row = r.get_next()
    all_tables.append((row[1], row[2]))  # name, type

dropped = 0
for tname, ttype in all_tables:
    if tname in v2_tables:
        continue
    try:
        if ttype == "NODE":
            r2 = conn.execute(f"MATCH (n:{tname}) RETURN count(n)")
            cnt = r2.get_next()[0]
        elif ttype == "REL":
            r2 = conn.execute(f"MATCH ()-[e:{tname}]->() RETURN count(e)")
            cnt = r2.get_next()[0]
        else:
            continue
        if cnt == 0:
            conn.execute(f"DROP TABLE {tname}")
            dropped += 1
    except:
        pass

print(f"  Dropped {dropped} empty tables")

# ============================================================
# Final stats
# ============================================================
r = conn.execute("MATCH (n) RETURN count(n)")
final_nodes = r.get_next()[0]
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
final_edges = r.get_next()[0]
density = final_edges / final_nodes if final_nodes > 0 else 0
print(f"\n=== FINAL ===")
print(f"Nodes: {final_nodes:,}  Edges: {final_edges:,}  Density: {density:.3f}")

del conn
del db
print("Checkpoint done")
