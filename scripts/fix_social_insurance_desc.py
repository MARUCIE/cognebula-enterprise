#!/usr/bin/env python3
"""Fix SocialInsuranceRule description — assemble from structured fields.

Authoritative type: NO AI generation. Assemble from existing fields only.
Fields: name, insuranceType, regionId, employerRate, employeeRate,
        baseCeiling, baseFloor, effectiveDate, adjustmentMonth.

Run with API stopped (KuzuDB direct access).
"""
import kuzu
import os
import re

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")


def safe_set(conn, node_id, content):
    safe = content.replace("\\", "\\\\").replace("'", "\\'")
    safe = safe.replace("\n", "\\n").replace("\r", "").replace("\t", " ")
    safe = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', safe)
    nid = node_id.replace("'", "\\'")
    try:
        conn.execute(
            f"MATCH (n:SocialInsuranceRule) WHERE n.id = '{nid}' "
            f"SET n.description = '{safe}'"
        )
        return True
    except Exception:
        return False


def build_description(n):
    """Build rich description from structured fields."""
    parts = []

    name = n.get("name", "")
    ins_type = n.get("insuranceType", "")
    region = n.get("regionId", "")

    # Header
    if name:
        parts.append(f"{name}。")

    # Insurance type and region
    if ins_type and region:
        parts.append(f"险种类型：{ins_type}保险，适用地区：{region}。")
    elif ins_type:
        parts.append(f"险种类型：{ins_type}保险。")

    # Rates
    employer = n.get("employerRate", "")
    employee = n.get("employeeRate", "")
    if employer or employee:
        rate_parts = []
        if employer:
            rate_parts.append(f"单位缴费比例{employer}")
        if employee:
            rate_parts.append(f"个人缴费比例{employee}")
        parts.append(f"缴费费率：{'，'.join(rate_parts)}。")

    # Base
    ceiling = n.get("baseCeiling", "")
    floor = n.get("baseFloor", "")
    if ceiling or floor:
        base_parts = []
        if ceiling:
            base_parts.append(f"缴费基数上限为{ceiling}")
        if floor:
            base_parts.append(f"下限为{floor}")
        parts.append(f"缴费基数：{'，'.join(base_parts)}。")

    # Dates
    eff = n.get("effectiveDate", "")
    adj = n.get("adjustmentMonth", "")
    if eff:
        parts.append(f"生效日期：{eff}。")
    if adj:
        parts.append(f"年度调整月份：{adj}。")

    return "".join(parts)


def main():
    print("=" * 60)
    print("  SocialInsuranceRule Description Fix — Field Assembly")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    q = ("MATCH (n:SocialInsuranceRule) "
         "RETURN n.id, n.name, n.insuranceType, n.regionId, "
         "n.employerRate, n.employeeRate, "
         "n.baseCeiling, n.baseFloor, "
         "n.effectiveDate, n.adjustmentMonth, n.description "
         "LIMIT 1000")
    result = conn.execute(q)

    nodes = []
    fields = ["id", "name", "insuranceType", "regionId",
              "employerRate", "employeeRate",
              "baseCeiling", "baseFloor",
              "effectiveDate", "adjustmentMonth", "description"]
    while result.has_next():
        row = result.get_next()
        nodes.append({fields[i]: str(row[i] or "") for i in range(len(fields))})

    # Only fix nodes with short descriptions
    to_fix = [n for n in nodes if len(n.get("description", "")) < 200]
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Need expansion: {len(to_fix)}")

    if not to_fix:
        print("  All descriptions are adequate")
        return

    updated = 0
    errors = 0

    for n in to_fix:
        desc = build_description(n)
        if len(desc) < 30:
            errors += 1
            continue

        if safe_set(conn, n["id"], desc):
            updated += 1
        else:
            errors += 1

    print(f"  Done: {updated} updated, {errors} errors")

    # Sample output
    if updated > 0:
        sample = build_description(to_fix[0])
        print(f"\n  Sample: {sample[:200]}")

    print("=" * 60)


if __name__ == "__main__":
    main()
