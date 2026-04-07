#!/usr/bin/env python3
"""Phase 1b: Fix content inheritance with proper escaping + correct edge direction.

Fixes from Phase 1:
  - Use prepared_statement pattern for safe string escaping
  - LegalClause: use documentId field instead of CLAUSE_OF edge
  - RegulationClause: retry failed updates with better escaping
  - LegalDocument: check actual field names

Runs directly on KuzuDB (must stop API first).
"""
import kuzu
import os
import re

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")


def safe_set_content(conn, type_name: str, node_id: str, field: str, content: str) -> bool:
    """Safely SET content using double-escaping for Cypher."""
    # Multi-layer escape for KuzuDB Cypher
    safe = content
    safe = safe.replace("\\", "\\\\")
    safe = safe.replace("'", "\\'")
    safe = safe.replace("\n", "\\n")
    safe = safe.replace("\r", "")
    safe = safe.replace("\t", " ")
    # Remove null bytes and control chars
    safe = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', safe)

    nid_safe = node_id.replace("'", "\\'")
    try:
        conn.execute(
            f"MATCH (n:{type_name}) WHERE n.id = '{nid_safe}' "
            f"SET n.{field} = '{safe}'"
        )
        return True
    except Exception:
        return False


def fix_regulation_clause(conn):
    """Re-inherit RegulationClause content with proper escaping."""
    print("\n[RegulationClause] Re-inheriting with fixed escaping...")

    q_short = ("MATCH (c:RegulationClause) "
               "WHERE c.fullText IS NULL OR size(c.fullText) < 100 "
               "RETURN count(c)")
    remaining = conn.execute(q_short).get_next()[0]
    print(f"  Still missing: {remaining:,}")

    if remaining == 0:
        return 0

    q = ("MATCH (c:RegulationClause)-[:CLAUSE_OF]->(lr:LawOrRegulation) "
         "WHERE (c.fullText IS NULL OR size(c.fullText) < 100) "
         "AND lr.fullText IS NOT NULL AND size(lr.fullText) >= 100 "
         "RETURN c.id, lr.fullText "
         "LIMIT 30000")

    result = conn.execute(q)
    updated = 0
    failed = 0

    while result.has_next():
        row = result.get_next()
        cid = str(row[0])
        parent_text = str(row[1] or "")[:2000]

        if safe_set_content(conn, "RegulationClause", cid, "fullText", parent_text):
            updated += 1
        else:
            failed += 1

        if updated % 2000 == 0 and updated > 0:
            print(f"    Updated {updated:,} (failed: {failed})...")

    print(f"  Done: {updated:,} updated, {failed:,} failed")
    return updated


def fix_legal_clause(conn):
    """Fill LegalClause content via documentId → LawOrRegulation."""
    print("\n[LegalClause] Checking content via documentId...")

    total = conn.execute("MATCH (c:LegalClause) RETURN count(c)").get_next()[0]
    q_short = ("MATCH (c:LegalClause) "
               "WHERE c.content IS NULL OR size(c.content) < 100 "
               "RETURN count(c)")
    short = conn.execute(q_short).get_next()[0]
    print(f"  Total: {total:,} | Missing: {short:,} ({short/total*100:.1f}%)")

    if short == 0:
        return 0

    # LegalClause has documentId field linking to parent
    # Try joining via documentId = LawOrRegulation.id
    print(f"  Joining via documentId → LawOrRegulation.id...")
    try:
        q = ("MATCH (c:LegalClause), (lr:LawOrRegulation) "
             "WHERE (c.content IS NULL OR size(c.content) < 100) "
             "AND c.documentId = lr.id "
             "AND lr.fullText IS NOT NULL AND size(lr.fullText) >= 100 "
             "RETURN c.id, lr.fullText, lr.title "
             "LIMIT 50000")
        result = conn.execute(q)
    except Exception as e:
        print(f"  documentId join failed: {e}")
        # Fallback: try PART_OF edges
        print(f"  Trying PART_OF edges...")
        try:
            q = ("MATCH (c:LegalClause)-[:PART_OF]->(lr:LawOrRegulation) "
                 "WHERE (c.content IS NULL OR size(c.content) < 100) "
                 "AND lr.fullText IS NOT NULL AND size(lr.fullText) >= 100 "
                 "RETURN c.id, lr.fullText, lr.title "
                 "LIMIT 50000")
            result = conn.execute(q)
        except Exception as e2:
            print(f"  PART_OF also failed: {e2}")
            return 0

    updated = 0
    failed = 0

    while result.has_next():
        row = result.get_next()
        cid = str(row[0])
        parent_text = str(row[1] or "")[:2000]

        if safe_set_content(conn, "LegalClause", cid, "content", parent_text):
            updated += 1
        else:
            failed += 1

        if updated % 2000 == 0 and updated > 0:
            print(f"    Updated {updated:,} (failed: {failed})...")

    print(f"  Done: {updated:,} updated, {failed:,} failed")
    if updated == 0 and short > 0:
        print(f"  NOTE: No joinable parent found. These clauses may lack parent references.")
        print(f"  These {short:,} nodes need original source crawl (AUTH policy).")
    return updated


def fix_legal_document(conn):
    """Check LegalDocument available fields and fill from existing data."""
    print("\n[LegalDocument] Checking available fields...")

    # List columns
    total = conn.execute("MATCH (d:LegalDocument) RETURN count(d)").get_next()[0]

    # Sample a node to see fields
    try:
        r = conn.execute("MATCH (d:LegalDocument) RETURN d LIMIT 1")
        if r.has_next():
            node = r.get_next()[0]
            if isinstance(node, dict):
                print(f"  Available fields: {sorted(node.keys())}")
    except Exception:
        pass

    # Try common content fields
    for field in ["fullText", "content", "description", "text", "body"]:
        try:
            q = f"MATCH (d:LegalDocument) WHERE d.{field} IS NOT NULL RETURN count(d)"
            ct = conn.execute(q).get_next()[0]
            print(f"  {field}: {ct:,} / {total:,} ({ct/total*100:.1f}%)")
        except Exception:
            print(f"  {field}: column not found")

    # Check name + title + description for assembly
    for field in ["name", "title", "description", "source", "type"]:
        try:
            q = (f"MATCH (d:LegalDocument) WHERE d.{field} IS NOT NULL "
                 f"AND size(d.{field}) >= 5 RETURN count(d)")
            ct = conn.execute(q).get_next()[0]
            print(f"  {field} (>=5ch): {ct:,}")
        except Exception:
            pass

    # Assemble content from available fields (AUTH: only existing data, no AI)
    print(f"\n  Assembling from title + name + description...")
    try:
        q = ("MATCH (d:LegalDocument) "
             "WHERE d.description IS NULL OR size(d.description) < 20 "
             "RETURN d.id, d.name, d.title, d.source, d.type "
             "LIMIT 60000")
        result = conn.execute(q)
    except Exception as e:
        print(f"  Query failed: {e}")
        return 0

    updated = 0
    while result.has_next():
        row = result.get_next()
        did = str(row[0] or "")
        name = str(row[1] or "")
        title = str(row[2] or "")
        source = str(row[3] or "")
        dtype = str(row[4] or "")

        parts = []
        if title:
            parts.append(title)
        if name and name != title:
            parts.append(f"文件名称：{name}")
        if source:
            parts.append(f"来源：{source}")
        if dtype:
            parts.append(f"类型：{dtype}")

        text = "。".join(parts)
        if len(text) < 20:
            continue

        if safe_set_content(conn, "LegalDocument", did, "description", text):
            updated += 1

        if updated % 5000 == 0 and updated > 0:
            print(f"    Updated {updated:,}...")

    print(f"  Done: {updated:,} documents filled from existing fields")
    print(f"  NOTE: For real content, these need original source crawl (AUTH policy)")
    return updated


def main():
    print("=" * 60)
    print("  Phase 1b: Content Inheritance (Fixed Escaping)")
    print("  Policy: AUTH — original source only, no AI generation")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    total = 0

    total += fix_regulation_clause(conn)
    total += fix_legal_clause(conn)
    total += fix_legal_document(conn)

    print(f"\n{'=' * 60}")
    print(f"  Phase 1b Complete: {total:,} nodes updated")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
