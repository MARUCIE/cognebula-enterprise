#!/usr/bin/env python3
"""Fix RegionalTaxPolicy description — assemble from structured fields.

Authoritative type: NO AI generation. Assemble from existing fields only.
Fields: policy_name, region, local_variation, title.

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
            f"MATCH (n:RegionalTaxPolicy) WHERE n.id = '{nid}' "
            f"SET n.description = '{safe}'"
        )
        return True
    except Exception:
        return False


def build_description(n):
    """Build description from available fields."""
    parts = []
    name = n.get("policy_name", "") or n.get("title", "")
    region = n.get("region", "")
    variation = n.get("local_variation", "")

    if name and region:
        parts.append(f"地方税收政策：{name}，适用地区：{region}。")
    elif name:
        parts.append(f"地方税收政策：{name}。")

    if variation and "按" in variation:
        parts.append(f"执行标准：{variation}。")

    if region:
        parts.append(f"该政策为{region}地方性税收优惠或征管规定，"
                     f"具体执行细则以{region}税务局最新公告为准。")

    return "".join(parts)


def main():
    print("=" * 60)
    print("  RegionalTaxPolicy Description Fix — Field Assembly")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Check if description field exists
    try:
        conn.execute("MATCH (n:RegionalTaxPolicy) WHERE n.description IS NOT NULL RETURN count(n)")
    except Exception:
        print("  Adding description field via ALTER TABLE...")
        try:
            conn.execute('ALTER TABLE RegionalTaxPolicy ADD description STRING DEFAULT ""')
            print("  OK: description field added")
        except Exception as e:
            print(f"  ERROR: {e}")
            return

    q = ("MATCH (n:RegionalTaxPolicy) "
         "RETURN n.id, n.policy_name, n.region, n.local_variation, n.title "
         "LIMIT 1000")
    result = conn.execute(q)

    nodes = []
    fields = ["id", "policy_name", "region", "local_variation", "title"]
    while result.has_next():
        row = result.get_next()
        nodes.append({fields[i]: str(row[i] or "") for i in range(len(fields))})

    to_fix = [n for n in nodes]
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Processing: {len(to_fix)}")

    updated = 0
    errors = 0

    for n in to_fix:
        desc = build_description(n)
        if len(desc) < 10:
            errors += 1
            continue
        if safe_set(conn, n["id"], desc):
            updated += 1
        else:
            errors += 1

    print(f"  Done: {updated} updated, {errors} errors")

    if updated > 0:
        sample = build_description(to_fix[0])
        print(f"\n  Sample ({len(sample)} chars): {sample[:200]}")

    print("=" * 60)


if __name__ == "__main__":
    main()
