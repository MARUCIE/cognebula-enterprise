#!/usr/bin/env python3
"""Fix and migrate the 3 remaining seed tables into v2.2.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/migrate_remaining_seed.py
    sudo systemctl start kg-api
"""
import kuzu

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

db = kuzu.Database(DB_PATH, buffer_pool_size=1024 * 1024 * 1024)
conn = kuzu.Connection(db)
print("KuzuDB connected")

# 1. TaxIncentiveV2 (from TaxIncentive: 109 nodes)
# Fields: id, name, incentiveType, eligibilityCriteria, effectiveFrom, effectiveUntil
count = 0
r = conn.execute("MATCH (n:TaxIncentive) RETURN n.id, n.name, n.incentiveType, n.eligibilityCriteria, n.effectiveFrom, n.effectiveUntil")
while r.has_next():
    row = r.get_next()
    try:
        conn.execute(
            "CREATE (n:TaxIncentiveV2 {id: $p1, name: $p2, type: $p3, description: $p4, effectiveDate: $p5, expiryDate: $p6})",
            {"p1": str(row[0] or ""), "p2": str(row[1] or ""), "p3": str(row[2] or "exemption"),
             "p4": str(row[3] or ""), "p5": str(row[4] or ""), "p6": str(row[5] or "")}
        )
        count += 1
    except Exception as e:
        if count == 0:
            print(f"  TaxIncentiveV2 first error: {e}")
print(f"TaxIncentiveV2: {count}")

# 2. ComplianceRuleV2 (from ComplianceRule: 84 nodes)
# Fields: id, name, conditionDescription, category, violationConsequence
# NOTE: KuzuDB 'description' may be reserved, use $p params to avoid issues
count = 0
r = conn.execute("MATCH (n:ComplianceRule) RETURN n.id, n.name, n.conditionDescription, n.category, n.violationConsequence")
while r.has_next():
    row = r.get_next()
    try:
        conn.execute(
            "CREATE (n:ComplianceRuleV2 {id: $p1, name: $p2, description: $p3, category: $p4, consequence: $p5, effectiveDate: $p6, expiryDate: $p7})",
            {"p1": str(row[0] or ""), "p2": str(row[1] or ""), "p3": str(row[2] or ""),
             "p4": str(row[3] or ""), "p5": str(row[4] or ""), "p6": "", "p7": ""}
        )
        count += 1
    except Exception as e:
        if count == 0:
            print(f"  ComplianceRuleV2 first error: {e}")
print(f"ComplianceRuleV2: {count}")

# 3. RiskIndicatorV2 (from RiskIndicator + TaxWarningIndicator + TaxCreditIndicator)
count = 0

# RiskIndicator: id, name, indicatorCode, triggerCondition, severity
try:
    r = conn.execute("MATCH (n:RiskIndicator) RETURN n.id, n.name, n.triggerCondition, n.severity")
    while r.has_next():
        row = r.get_next()
        try:
            conn.execute(
                "CREATE (n:RiskIndicatorV2 {id: $p1, name: $p2, description: $p3, indicatorType: $p4, threshold: $p5, severity: $p6})",
                {"p1": str(row[0] or ""), "p2": str(row[1] or ""), "p3": str(row[2] or ""),
                 "p4": "risk", "p5": 0.0, "p6": str(row[3] or "medium")}
            )
            count += 1
        except:
            pass
except Exception as e:
    print(f"  RiskIndicator: {e}")

# TaxWarningIndicator: id, name, formula, threshold
try:
    r = conn.execute("MATCH (n:TaxWarningIndicator) RETURN n.id, n.name, n.formula, n.threshold")
    while r.has_next():
        row = r.get_next()
        try:
            thresh = float(row[3]) if row[3] else 0.0
        except:
            thresh = 0.0
        try:
            conn.execute(
                "CREATE (n:RiskIndicatorV2 {id: $p1, name: $p2, description: $p3, indicatorType: $p4, threshold: $p5, severity: $p6})",
                {"p1": "WI_" + str(row[0] or ""), "p2": str(row[1] or ""), "p3": str(row[2] or ""),
                 "p4": "warning", "p5": thresh, "p6": "medium"}
            )
            count += 1
        except:
            pass
except Exception as e:
    print(f"  TaxWarningIndicator: {e}")

# TaxCreditIndicator: id, name, score, category
try:
    r = conn.execute("MATCH (n:TaxCreditIndicator) RETURN n.id, n.name, n.score, n.category")
    while r.has_next():
        row = r.get_next()
        try:
            score = float(row[2]) if row[2] else 0.0
        except:
            score = 0.0
        try:
            conn.execute(
                "CREATE (n:RiskIndicatorV2 {id: $p1, name: $p2, description: $p3, indicatorType: $p4, threshold: $p5, severity: $p6})",
                {"p1": "CI_" + str(row[0] or ""), "p2": str(row[1] or row[0] or ""), "p3": str(row[3] or ""),
                 "p4": "credit", "p5": score, "p6": "low"}
            )
            count += 1
        except:
            pass
except Exception as e:
    print(f"  TaxCreditIndicator: {e}")

print(f"RiskIndicatorV2: {count}")
print(f"\nDone!")
