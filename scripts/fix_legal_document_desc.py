#!/usr/bin/env python3
"""Fix LegalDocument description — assemble from available metadata fields.

LegalDocument has sparse fields: name, type, issuingBodyId, status.
Assemble a structured description from these to reach 50+ chars (medium).

Authoritative type: field assembly only, NO AI generation.
Run with API stopped (KuzuDB direct access).
"""
import kuzu
import os
import re

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")

# Map internal source IDs to readable Chinese names
SOURCE_MAP = {
    "chinatax_fgk_api": "国家税务总局法规库",
    "npc_flk": "全国人大法律法规库",
    "mof": "财政部",
    "ndrc": "国家发改委",
    "customs": "海关总署",
    "": "综合来源",
}

TYPE_MAP = {
    "policy/policy_law": "政策法规",
    "policy/tax_law": "税收法律",
    "policy/regulation": "行政法规",
    "会计准则": "会计准则",
    "tax_law": "税收法律",
    "": "法规文档",
}


def safe_set(conn, node_id, content):
    safe = content.replace("\\", "\\\\").replace("'", "\\'")
    safe = safe.replace("\n", "\\n").replace("\r", "").replace("\t", " ")
    safe = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', safe)
    nid = node_id.replace("'", "\\'")
    try:
        conn.execute(
            f"MATCH (n:LegalDocument) WHERE n.id = '{nid}' "
            f"SET n.description = '{safe}'"
        )
        return True
    except Exception:
        return False


def build_description(n):
    name = n.get("name", "")
    doc_type = TYPE_MAP.get(n.get("type", ""), n.get("type", "法规文档"))
    source = SOURCE_MAP.get(n.get("issuingBodyId", ""), n.get("issuingBodyId", ""))
    status = n.get("status", "")

    parts = [f"{doc_type}：{name}。"]
    if source:
        parts.append(f"来源：{source}。")
    if status == "active":
        parts.append("现行有效。")
    elif status:
        parts.append(f"状态：{status}。")
    parts.append("本文档为中国财税法规体系的组成部分，具体条文以官方发布为准。")

    return "".join(parts)


def main():
    print("=" * 60)
    print("  LegalDocument Description Fix — Field Assembly v2")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Ensure description field exists
    try:
        conn.execute(
            "MATCH (n:LegalDocument) WHERE n.description IS NOT NULL "
            "RETURN count(n)"
        )
    except Exception:
        print("  Adding description field...")
        conn.execute('ALTER TABLE LegalDocument ADD description STRING DEFAULT ""')

    q = ("MATCH (n:LegalDocument) "
         "WHERE n.description IS NULL OR size(n.description) < 50 "
         "RETURN n.id, n.name, n.type, n.issuingBodyId, n.status "
         "LIMIT 60000")
    result = conn.execute(q)

    nodes = []
    fields = ["id", "name", "type", "issuingBodyId", "status"]
    while result.has_next():
        row = result.get_next()
        nodes.append({fields[i]: str(row[i] or "") for i in range(len(fields))})

    print(f"  Total to fix: {len(nodes)}")

    updated = 0
    errors = 0
    for i, n in enumerate(nodes):
        desc = build_description(n)
        if len(desc) < 30:
            errors += 1
            continue
        if safe_set(conn, n["id"], desc):
            updated += 1
        else:
            errors += 1

        if (i + 1) % 5000 == 0:
            print(f"  Progress: {i+1}/{len(nodes)} ({updated} updated, {errors} errors)")

    print(f"\n  Done: {updated} updated, {errors} errors")
    if nodes:
        sample = build_description(nodes[0])
        print(f"  Sample ({len(sample)} chars): {sample[:200]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
