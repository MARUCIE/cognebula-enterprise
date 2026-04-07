#!/usr/bin/env python3
"""Phase 2: Structured data template generation (STRC types).

Assembles descriptive content from existing fields (code, name, category).
NO AI generation — only recombining data already in the database.

Targets:
  - Classification: name + category + code → description
  - HSCode: code + name + rate info → description
  - TaxRate: rate + tax type + conditions → description
  - TaxClassificationCode: code + item_name + category → description
  - TaxCodeDetail: code + name → description
  - TaxCodeIndustryMap: code + industry → description

Runs directly on KuzuDB (must stop API first).
"""
import sys
import os
import kuzu

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")


def safe_str(val) -> str:
    """Convert value to non-null string."""
    if val is None:
        return ""
    return str(val).strip()


def escape_cypher(text: str) -> str:
    """Escape text for Cypher string literal."""
    return text.replace("\\", "\\\\").replace("'", "\\'")


def fill_type(conn, type_name: str, builder_fn, content_field: str = "fullText",
              min_len: int = 50, limit: int = 60000):
    """Generic filler: query nodes missing content, build from fields, write back."""
    print(f"\n[{type_name}] Checking content...")

    try:
        total = conn.execute(f"MATCH (n:{type_name}) RETURN count(n)").get_next()[0]
    except Exception as e:
        print(f"  ERROR: Table not found: {e}")
        return 0

    # Check how many are short
    try:
        q = (f"MATCH (n:{type_name}) "
             f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_len} "
             f"RETURN count(n)")
        short = conn.execute(q).get_next()[0]
    except Exception:
        # content_field might not exist, try description
        content_field = "description"
        try:
            q = (f"MATCH (n:{type_name}) "
                 f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_len} "
                 f"RETURN count(n)")
            short = conn.execute(q).get_next()[0]
        except Exception as e:
            print(f"  ERROR: No usable content field: {e}")
            return 0

    print(f"  Total: {total:,} | Needs fill: {short:,} ({short/total*100:.1f}%)")
    if short == 0:
        print(f"  All nodes have content. Skip.")
        return 0

    # Query all short nodes with their fields
    try:
        result = builder_fn(conn, type_name, content_field, min_len, limit)
        print(f"  Done: {result:,} nodes updated")
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        return 0


def build_classification(conn, type_name, content_field, min_len, limit):
    """Build description from name + system + category fields."""
    q = (f"MATCH (n:{type_name}) "
         f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_len} "
         f"RETURN n.id, n.name, n.title, n.system, n.code "
         f"LIMIT {limit}")
    result = conn.execute(q)
    updated = 0
    while result.has_next():
        row = result.get_next()
        nid, name, title, system, code = [safe_str(x) for x in row]

        parts = []
        if code:
            parts.append(f"分类编码：{code}")
        if name:
            parts.append(f"名称：{name}")
        if title and title != name:
            parts.append(f"标题：{title}")
        if system:
            parts.append(f"分类体系：{system}")

        desc = "。".join(parts)
        if len(desc) < 20:
            continue

        try:
            conn.execute(
                f"MATCH (n:{type_name}) WHERE n.id = '{escape_cypher(nid)}' "
                f"SET n.{content_field} = '{escape_cypher(desc)}'")
            updated += 1
        except Exception:
            pass

    return updated


def build_hscode(conn, type_name, content_field, min_len, limit):
    """Build description from HS code fields."""
    q = (f"MATCH (n:{type_name}) "
         f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_len} "
         f"RETURN n.id, n.code, n.name, n.title, n.chineseName, n.unit, n.rate "
         f"LIMIT {limit}")
    result = conn.execute(q)
    updated = 0
    while result.has_next():
        row = result.get_next()
        nid = safe_str(row[0])
        code = safe_str(row[1])
        name = safe_str(row[2])
        title = safe_str(row[3])
        cn_name = safe_str(row[4])
        unit = safe_str(row[5])
        rate = safe_str(row[6])

        display_name = cn_name or name or title
        parts = []
        if code:
            parts.append(f"海关HS编码：{code}")
        if display_name:
            parts.append(f"商品名称：{display_name}")
        if unit:
            parts.append(f"计量单位：{unit}")
        if rate:
            parts.append(f"税率：{rate}")
        if len(code) >= 4:
            chapter = code[:2]
            parts.append(f"所属第{int(chapter)}类")

        desc = "。".join(parts)
        if len(desc) < 20:
            continue

        try:
            conn.execute(
                f"MATCH (n:{type_name}) WHERE n.id = '{escape_cypher(nid)}' "
                f"SET n.{content_field} = '{escape_cypher(desc)}'")
            updated += 1
        except Exception:
            pass

    return updated


def build_taxrate(conn, type_name, content_field, min_len, limit):
    """Build description from tax rate fields."""
    q = (f"MATCH (n:{type_name}) "
         f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_len} "
         f"RETURN n.id, n.name, n.title, n.description, n.rate, n.category "
         f"LIMIT {limit}")
    result = conn.execute(q)
    updated = 0
    while result.has_next():
        row = result.get_next()
        nid = safe_str(row[0])
        name = safe_str(row[1])
        title = safe_str(row[2])
        desc = safe_str(row[3])
        rate = safe_str(row[4])
        cat = safe_str(row[5])

        display = name or title
        parts = []
        if display:
            parts.append(f"税率项目：{display}")
        if rate:
            parts.append(f"适用税率：{rate}")
        if cat:
            parts.append(f"税种类别：{cat}")
        if desc and len(desc) >= 10:
            parts.append(desc)

        assembled = "。".join(parts)
        if len(assembled) < 20:
            continue

        try:
            conn.execute(
                f"MATCH (n:{type_name}) WHERE n.id = '{escape_cypher(nid)}' "
                f"SET n.{content_field} = '{escape_cypher(assembled)}'")
            updated += 1
        except Exception:
            pass

    return updated


def build_taxcode(conn, type_name, content_field, min_len, limit):
    """Build description from tax classification code fields."""
    # Try multiple field combinations
    fields_to_try = [
        "n.id, n.item_name, n.code, n.category_abbr, n.description, n.tax_rate",
        "n.id, n.name, n.code, n.category, n.description, n.rate",
    ]

    for fields in fields_to_try:
        try:
            q = (f"MATCH (n:{type_name}) "
                 f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_len} "
                 f"RETURN {fields} "
                 f"LIMIT {limit}")
            result = conn.execute(q)
            break
        except Exception:
            continue
    else:
        print(f"  WARN: No matching field combination for {type_name}")
        return 0

    updated = 0
    while result.has_next():
        row = result.get_next()
        nid = safe_str(row[0])
        name = safe_str(row[1])
        code = safe_str(row[2])
        cat = safe_str(row[3])
        desc = safe_str(row[4])
        rate = safe_str(row[5])

        parts = []
        if code:
            parts.append(f"税收分类编码：{code}")
        if name:
            parts.append(f"商品/服务名称：{name}")
        if cat:
            parts.append(f"类别简称：{cat}")
        if rate:
            parts.append(f"适用税率：{rate}")
        if desc and len(desc) >= 5:
            parts.append(desc)

        assembled = "。".join(parts)
        if len(assembled) < 20:
            continue

        try:
            conn.execute(
                f"MATCH (n:{type_name}) WHERE n.id = '{escape_cypher(nid)}' "
                f"SET n.{content_field} = '{escape_cypher(assembled)}'")
            updated += 1
        except Exception:
            pass

    return updated


def main():
    print("=" * 60)
    print("  Phase 2: Structured Data Template Generation")
    print("  Policy: STRC — assemble from existing fields only")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    total = 0
    total += fill_type(conn, "Classification", build_classification, "fullText")
    total += fill_type(conn, "HSCode", build_hscode, "description")
    total += fill_type(conn, "TaxRate", build_taxrate, "fullText")
    total += fill_type(conn, "TaxClassificationCode", build_taxcode, "description")
    total += fill_type(conn, "TaxCodeDetail", build_taxcode, "description")
    total += fill_type(conn, "TaxCodeIndustryMap", build_taxcode, "description")

    print(f"\n{'=' * 60}")
    print(f"  Phase 2 Complete: {total:,} nodes updated")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
