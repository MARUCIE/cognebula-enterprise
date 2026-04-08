#!/usr/bin/env python3
"""Fix TaxRate description — assemble from name + valueExpression + calculationBasis.

STRC type, "structured" policy — no AI generation, just field assembly.
Matches existing description format: "{name}，税率{rate}，计税基础：{basis}"

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
            f"MATCH (n:TaxRate) WHERE n.id = '{nid}' SET n.description = '{safe}'"
        )
        return True
    except Exception:
        return False


def main():
    print("=" * 60)
    print("  TaxRate Description Fix — Field Assembly")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Find TaxRate nodes without description
    q = ("MATCH (n:TaxRate) "
         "WHERE n.description IS NULL OR size(n.description) < 5 "
         "RETURN n.id, n.name, n.valueExpression, n.calculationBasis "
         "LIMIT 10000")
    result = conn.execute(q)

    to_fix = []
    while result.has_next():
        row = result.get_next()
        to_fix.append({
            "id": str(row[0] or ""),
            "name": str(row[1] or ""),
            "rate": str(row[2] or ""),
            "basis": str(row[3] or ""),
        })

    print(f"  Need fix: {len(to_fix)}")
    if not to_fix:
        print("  All TaxRate nodes have descriptions")
        return

    updated = 0
    errors = 0

    for n in to_fix:
        parts = []
        if n["name"]:
            parts.append(n["name"])
        if n["rate"]:
            parts.append(f"税率{n['rate']}")
        if n["basis"]:
            parts.append(f"计税基础：{n['basis']}")

        desc = "，".join(parts) if parts else ""
        if len(desc) < 5:
            errors += 1
            continue

        if safe_set(conn, n["id"], desc):
            updated += 1
        else:
            errors += 1

    print(f"  Done: {updated} updated, {errors} errors")
    print("=" * 60)


if __name__ == "__main__":
    main()
