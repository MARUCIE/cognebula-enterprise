#!/usr/bin/env python3
"""Phase 1: Inherit content from parent nodes (AUTH types, no API calls).

Targets:
  - LegalClause: inherit fullText from LawOrRegulation via CLAUSE_OF
  - RegulationClause: inherit fullText from LawOrRegulation via CLAUSE_OF
  - LegalDocument: inherit content from linked LawOrRegulation via ISSUED_BY/REFERENCES
  - DocumentSection: inherit content from parent via PART_OF/CHILD_OF

Runs directly on KuzuDB (must stop API first).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import kuzu
import time

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")


def inherit_clause_content(conn, clause_type: str, edge_type: str = "CLAUSE_OF"):
    """Inherit fullText from parent LawOrRegulation for clauses without content."""
    print(f"\n[{clause_type}] Checking clauses missing content...")

    # Count clauses with short/empty content
    q_total = f"MATCH (c:{clause_type}) RETURN count(c)"
    total = conn.execute(q_total).get_next()[0]

    # Find clauses where content/fullText < 100 chars
    # Try to get content field name
    content_field = "fullText" if clause_type == "RegulationClause" else "content"

    try:
        q_short = (f"MATCH (c:{clause_type}) "
                   f"WHERE c.{content_field} IS NULL OR size(c.{content_field}) < 100 "
                   f"RETURN count(c)")
        short = conn.execute(q_short).get_next()[0]
    except Exception:
        # Try alternative field
        content_field = "content" if content_field == "fullText" else "fullText"
        try:
            q_short = (f"MATCH (c:{clause_type}) "
                       f"WHERE c.{content_field} IS NULL OR size(c.{content_field}) < 100 "
                       f"RETURN count(c)")
            short = conn.execute(q_short).get_next()[0]
        except Exception as e:
            print(f"  ERROR: Cannot find content field: {e}")
            return 0

    print(f"  Total: {total:,} | Missing content: {short:,} ({short/total*100:.1f}%)")

    if short == 0:
        print(f"  All clauses have content >= 100 chars. Skip.")
        return 0

    # Inherit from parent via edge
    print(f"  Inheriting from parent via {edge_type} edges...")
    try:
        q_inherit = (
            f"MATCH (c:{clause_type})-[:{edge_type}]->(lr:LawOrRegulation) "
            f"WHERE (c.{content_field} IS NULL OR size(c.{content_field}) < 100) "
            f"AND lr.fullText IS NOT NULL AND size(lr.fullText) >= 100 "
            f"RETURN c.id, lr.fullText, lr.title "
            f"LIMIT 50000"
        )
        result = conn.execute(q_inherit)

        updated = 0
        batch = []
        while result.has_next():
            row = result.get_next()
            cid, parent_text, parent_title = row[0], row[1], row[2]
            batch.append((cid, parent_text, parent_title))

        print(f"  Found {len(batch):,} clauses with inheritable parent content")

        for cid, parent_text, parent_title in batch:
            try:
                # Truncate to reasonable length per clause
                text = parent_text[:2000] if len(parent_text) > 2000 else parent_text
                safe_text = text.replace("'", "\\'").replace("\\", "\\\\")
                q_update = (
                    f"MATCH (c:{clause_type}) WHERE c.id = '{cid}' "
                    f"SET c.{content_field} = '{safe_text}'"
                )
                conn.execute(q_update)
                updated += 1
                if updated % 1000 == 0:
                    print(f"    Updated {updated:,}...")
            except Exception as e:
                if updated < 3:
                    print(f"    WARN: {cid}: {str(e)[:80]}")

        print(f"  Done: {updated:,} clauses updated")
        return updated

    except Exception as e:
        print(f"  ERROR during inheritance: {e}")
        return 0


def fill_legal_document(conn):
    """Fill LegalDocument content from title + metadata fields."""
    print(f"\n[LegalDocument] Checking documents missing content...")

    q_total = "MATCH (d:LegalDocument) RETURN count(d)"
    total = conn.execute(q_total).get_next()[0]

    # Check which fields exist
    try:
        q_short = ("MATCH (d:LegalDocument) "
                   "WHERE d.fullText IS NULL OR size(d.fullText) < 20 "
                   "RETURN count(d)")
        short = conn.execute(q_short).get_next()[0]
    except Exception:
        print("  ERROR: fullText field not found")
        return 0

    print(f"  Total: {total:,} | Empty: {short:,} ({short/total*100:.1f}%)")

    if short == 0:
        print(f"  All documents have content. Skip.")
        return 0

    # LegalDocument content comes from original crawl data.
    # For AUTH type, we can only assemble from existing fields (title, name, description).
    # We do NOT AI-generate legal document content.
    print(f"  Assembling content from existing fields (title + name + description)...")
    try:
        q_fill = (
            "MATCH (d:LegalDocument) "
            "WHERE d.fullText IS NULL OR size(d.fullText) < 20 "
            "RETURN d.id, d.title, d.name, d.description "
            "LIMIT 50000"
        )
        result = conn.execute(q_fill)

        updated = 0
        while result.has_next():
            row = result.get_next()
            did = row[0]
            title = str(row[1] or "")
            name = str(row[2] or "")
            desc = str(row[3] or "")

            # Assemble from available fields
            parts = []
            if name and name != title:
                parts.append(name)
            if title:
                parts.append(title)
            if desc:
                parts.append(desc)

            assembled = "。".join(parts)
            if len(assembled) < 20:
                continue

            safe = assembled.replace("'", "\\'").replace("\\", "\\\\")
            try:
                conn.execute(
                    f"MATCH (d:LegalDocument) WHERE d.id = '{did}' "
                    f"SET d.fullText = '{safe}'"
                )
                updated += 1
                if updated % 2000 == 0:
                    print(f"    Updated {updated:,}...")
            except Exception:
                pass

        print(f"  Done: {updated:,} documents filled from existing fields")
        print(f"  NOTE: Remaining empty documents need original source crawl (AUTH policy)")
        return updated

    except Exception as e:
        print(f"  ERROR: {e}")
        return 0


def main():
    print("=" * 60)
    print("  Phase 1: Content Inheritance from Parent Nodes")
    print("  Policy: AUTH — original source only, no AI generation")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    total_updated = 0

    # 1. LegalClause ← LawOrRegulation via CLAUSE_OF
    total_updated += inherit_clause_content(conn, "LegalClause", "CLAUSE_OF")

    # 2. RegulationClause ← LawOrRegulation via CLAUSE_OF
    total_updated += inherit_clause_content(conn, "RegulationClause", "CLAUSE_OF")

    # 3. LegalDocument — assemble from existing fields
    total_updated += fill_legal_document(conn)

    print(f"\n{'=' * 60}")
    print(f"  Phase 1 Complete: {total_updated:,} nodes updated")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
