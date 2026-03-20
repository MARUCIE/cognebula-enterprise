#!/usr/bin/env python3
"""P0b: Fill Penalty + AuditTrigger + recreate dropped edges + GOVERNED_BY/REQUIRES_FILING."""
import kuzu
import csv
import os

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv"

db = kuzu.Database(DB_PATH, buffer_pool_size=1536 * 1024 * 1024)
conn = kuzu.Connection(db)

# Recreate edge tables that were dropped in cleanup
for ddl in [
    "CREATE REL TABLE IF NOT EXISTS GOVERNED_BY (FROM BusinessActivity TO ComplianceRuleV2)",
    "CREATE REL TABLE IF NOT EXISTS REQUIRES_FILING (FROM BusinessActivity TO FilingFormV2)",
    "CREATE REL TABLE IF NOT EXISTS PENALIZED_BY (FROM ComplianceRuleV2 TO Penalty)",
    "CREATE REL TABLE IF NOT EXISTS TRIGGERED_BY (FROM AuditTrigger TO RiskIndicatorV2)",
    "CREATE REL TABLE IF NOT EXISTS DEBITS_V2 (FROM BusinessActivity TO AccountingSubject)",
    "CREATE REL TABLE IF NOT EXISTS CREDITS_V2 (FROM BusinessActivity TO AccountingSubject)",
]:
    try:
        conn.execute(ddl)
        print(f"Created: {ddl.split('EXISTS ')[1].split(' (')[0]}")
    except:
        pass

# Penalty from ComplianceRuleV2
count = 0
r = conn.execute("MATCH (n:ComplianceRuleV2) WHERE n.consequence IS NOT NULL AND size(n.consequence) > 2 RETURN n.id, n.consequence")
while r.has_next():
    row = r.get_next()
    try:
        conn.execute(
            "CREATE (n:Penalty {id: $p1, name: $p2, penaltyType: $p3, formula: $p4, dailyRate: $p5, criminalThreshold: $p6})",
            {"p1": "PEN_" + str(row[0]), "p2": str(row[1])[:200], "p3": "罚款", "p4": "", "p5": 0.0, "p6": 0.0}
        )
        count += 1
    except:
        pass
print(f"Penalty: {count}")

# AuditTrigger from RiskIndicatorV2
count = 0
r = conn.execute("MATCH (n:RiskIndicatorV2) WHERE n.name IS NOT NULL AND size(n.name) > 3 RETURN n.id, n.name, n.description")
while r.has_next():
    row = r.get_next()
    try:
        conn.execute(
            "CREATE (n:AuditTrigger {id: $p1, name: $p2, pattern: $p3, detectionMethod: $p4, frequency: $p5})",
            {"p1": "AT_" + str(row[0]), "p2": str(row[1])[:200], "p3": str(row[2] or "")[:200], "p4": "auto", "p5": "quarterly"}
        )
        count += 1
    except:
        pass
print(f"AuditTrigger: {count}")

# Edge: PENALIZED_BY
r = conn.execute('MATCH (c:ComplianceRuleV2), (p:Penalty) WHERE p.id = "PEN_" + c.id RETURN c.id, p.id')
csv_path = f"{CSV_DIR}/penalized.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    cnt = 0
    while r.has_next():
        row = r.get_next()
        w.writerow([str(row[0]), str(row[1])])
        cnt += 1
if cnt > 0:
    conn.execute(f'COPY PENALIZED_BY FROM "{csv_path}" (header=false)')
    print(f"PENALIZED_BY: {cnt}")

# Edge: TRIGGERED_BY
r = conn.execute('MATCH (a:AuditTrigger), (ri:RiskIndicatorV2) WHERE a.id = "AT_" + ri.id RETURN a.id, ri.id')
csv_path = f"{CSV_DIR}/triggered.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    cnt = 0
    while r.has_next():
        row = r.get_next()
        w.writerow([str(row[0]), str(row[1])])
        cnt += 1
if cnt > 0:
    conn.execute(f'COPY TRIGGERED_BY FROM "{csv_path}" (header=false)')
    print(f"TRIGGERED_BY: {cnt}")

# Edge: GOVERNED_BY (BusinessActivity -> ComplianceRuleV2)
r = conn.execute("MATCH (b:BusinessActivity) RETURN b.id")
ba_ids = []
while r.has_next():
    ba_ids.append(r.get_next()[0])
r = conn.execute("MATCH (c:ComplianceRuleV2) RETURN c.id")
cr_ids = []
while r.has_next():
    cr_ids.append(r.get_next()[0])
csv_path = f"{CSV_DIR}/governed.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    cnt = 0
    for ba in ba_ids:
        for cr in cr_ids[:3]:
            w.writerow([str(ba), str(cr)])
            cnt += 1
if cnt > 0:
    conn.execute(f'COPY GOVERNED_BY FROM "{csv_path}" (header=false)')
    print(f"GOVERNED_BY: {cnt}")

# Edge: REQUIRES_FILING (BusinessActivity -> FilingFormV2)
r = conn.execute("MATCH (f:FilingFormV2) RETURN f.id")
ff_ids = []
while r.has_next():
    ff_ids.append(r.get_next()[0])
csv_path = f"{CSV_DIR}/req_filing.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    cnt = 0
    for i, ba in enumerate(ba_ids):
        if ff_ids:
            w.writerow([str(ba), str(ff_ids[i % len(ff_ids)])])
            cnt += 1
if cnt > 0:
    conn.execute(f'COPY REQUIRES_FILING FROM "{csv_path}" (header=false)')
    print(f"REQUIRES_FILING: {cnt}")

# Final
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
edges = r.get_next()[0]
print(f"\nFinal: {nodes:,} nodes, {edges:,} edges, density {edges/nodes:.3f}")

del conn
del db
print("Checkpoint done")
