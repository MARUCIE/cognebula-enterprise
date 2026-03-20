#!/usr/bin/env python3
"""Migrate seed data into v2.2 tables directly on kg-node.

Run on kg-node AFTER stopping kg-api:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/migrate_seed_data.py
    sudo systemctl start kg-api
"""
import kuzu
import sys

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DRY_RUN = "--dry-run" in sys.argv


def safe_str(v, maxlen=200):
    if v is None:
        return ""
    return str(v)[:maxlen]


def migrate(conn):
    results = {}

    # 1. TaxEntity (from EnterpriseType + TaxpayerStatus + EntityTypeProfile)
    count = 0
    # EnterpriseType: id, name, classificationBasis, taxJurisdiction
    try:
        r = conn.execute("MATCH (n:EnterpriseType) RETURN n.id, n.name")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:TaxEntity {id: $id, name: $name, type: $type, taxpayerStatus: $status})",
                    {"id": f"TE_{row[0]}", "name": safe_str(row[1]), "type": "企业", "status": ""}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  EnterpriseType: {e}")

    # TaxpayerStatus: id, name, domain, thresholdValue
    try:
        r = conn.execute("MATCH (n:TaxpayerStatus) RETURN n.id, n.name")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:TaxEntity {id: $id, name: $name, type: $type, taxpayerStatus: $status})",
                    {"id": f"TE_{row[0]}", "name": safe_str(row[1]), "type": "身份", "status": safe_str(row[1])}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  TaxpayerStatus: {e}")

    # EntityTypeProfile: id, name, entityType, taxpayerCategory
    try:
        r = conn.execute("MATCH (n:EntityTypeProfile) RETURN n.id, n.name, n.taxpayerCategory")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:TaxEntity {id: $id, name: $name, type: $type, taxpayerStatus: $status})",
                    {"id": f"TE_{row[0]}", "name": safe_str(row[1]), "type": "画像", "status": safe_str(row[2])}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  EntityTypeProfile: {e}")
    results["TaxEntity"] = count

    # 2. TaxIncentiveV2 (from TaxIncentive)
    count = 0
    try:
        r = conn.execute("MATCH (n:TaxIncentive) RETURN n.id, n.name, n.incentiveType, n.eligibilityCriteria, n.effectiveFrom, n.effectiveUntil")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:TaxIncentiveV2 {id: $id, name: $name, type: $type, description: $desc, effectiveDate: $ed, expiryDate: $ex})",
                    {"id": safe_str(row[0]), "name": safe_str(row[1]), "type": safe_str(row[2]) or "减免",
                     "desc": safe_str(row[3]), "ed": safe_str(row[4]), "ex": safe_str(row[5])}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  TaxIncentive: {e}")
    results["TaxIncentiveV2"] = count

    # 3. ComplianceRuleV2 (from ComplianceRule)
    count = 0
    try:
        r = conn.execute("MATCH (n:ComplianceRule) RETURN n.id, n.name, n.conditionDescription, n.category, n.violationConsequence, n.effectiveFrom, n.effectiveUntil")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:ComplianceRuleV2 {id: $id, name: $name, description: $desc, category: $cat, consequence: $con, effectiveDate: $ed, expiryDate: $ex})",
                    {"id": safe_str(row[0]), "name": safe_str(row[1]), "desc": safe_str(row[2]),
                     "cat": safe_str(row[3]), "con": safe_str(row[4]), "ed": safe_str(row[5]), "ex": safe_str(row[6])}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  ComplianceRule: {e}")
    results["ComplianceRuleV2"] = count

    # 4. RiskIndicatorV2 (from RiskIndicator + TaxCreditIndicator + TaxWarningIndicator)
    count = 0
    # RiskIndicator: id, name, severity, triggerCondition, metricFormula
    try:
        r = conn.execute("MATCH (n:RiskIndicator) RETURN n.id, n.name, n.triggerCondition, n.severity")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:RiskIndicatorV2 {id: $id, name: $name, description: $desc, indicatorType: $type, threshold: $thresh, severity: $sev})",
                    {"id": safe_str(row[0]), "name": safe_str(row[1]), "desc": safe_str(row[2]),
                     "type": "风险指标", "thresh": 0.0, "sev": safe_str(row[3]) or "中"}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  RiskIndicator: {e}")

    # TaxWarningIndicator: id, name, formula, threshold, tax_type
    try:
        r = conn.execute("MATCH (n:TaxWarningIndicator) RETURN n.id, n.name, n.formula, n.threshold")
        while r.has_next():
            row = r.get_next()
            try:
                conn.execute(
                    "CREATE (n:RiskIndicatorV2 {id: $id, name: $name, description: $desc, indicatorType: $type, threshold: $thresh, severity: $sev})",
                    {"id": f"WI_{safe_str(row[0])}", "name": safe_str(row[1]), "desc": safe_str(row[2]),
                     "type": "预警指标", "thresh": float(row[3]) if row[3] else 0.0, "sev": "中"}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  TaxWarningIndicator: {e}")

    # TaxCreditIndicator: id, name, score, category
    try:
        r = conn.execute("MATCH (n:TaxCreditIndicator) RETURN n.id, n.name, n.score, n.category")
        while r.has_next():
            row = r.get_next()
            name = safe_str(row[1]) or safe_str(row[0])
            try:
                conn.execute(
                    "CREATE (n:RiskIndicatorV2 {id: $id, name: $name, description: $desc, indicatorType: $type, threshold: $thresh, severity: $sev})",
                    {"id": f"CI_{safe_str(row[0])}", "name": name, "desc": safe_str(row[3]),
                     "type": "信用指标", "thresh": float(row[2]) if row[2] else 0.0, "sev": "低"}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  TaxCreditIndicator: {e}")
    results["RiskIndicatorV2"] = count

    # 5. AccountingSubject (from ChartOfAccount + ChartOfAccountDetail)
    count = 0
    try:
        r = conn.execute("MATCH (n:ChartOfAccount) RETURN n.id, n.code, n.name, n.category, n.direction")
        while r.has_next():
            row = r.get_next()
            code = safe_str(row[1]) or safe_str(row[0])
            try:
                conn.execute(
                    "CREATE (n:AccountingSubject {id: $id, name: $name, category: $cat, balanceDirection: $dir})",
                    {"id": code, "name": safe_str(row[2]), "cat": safe_str(row[3]), "dir": safe_str(row[4])}
                )
                count += 1
            except: pass
    except Exception as e:
        print(f"  ChartOfAccount: {e}")
    results["AccountingSubject"] = count

    return results


def main():
    print(f"=== Migrate Seed Data v2 {'(DRY RUN)' if DRY_RUN else ''} ===")
    try:
        db = kuzu.Database(DB_PATH, buffer_pool_size=1024 * 1024 * 1024)
        conn = kuzu.Connection(db)
        print("KuzuDB connected\n")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    results = migrate(conn)

    print("\n=== Results ===")
    total = 0
    for table, count in results.items():
        print(f"  {table}: {count} nodes")
        total += count
    print(f"\nTotal: {total} nodes migrated")


if __name__ == "__main__":
    main()
