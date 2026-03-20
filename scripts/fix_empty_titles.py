#!/usr/bin/env python3
"""Fix nodes with empty/missing titles by extracting from content.

Connects to KuzuDB directly and patches title fields.
Run on kg-node: python3 scripts/fix_empty_titles.py [--dry-run]

Strategy:
1. Find nodes where title is NULL or too short (< 5 chars)
2. Extract title from content: first sentence or first 50 chars
3. UPDATE the node's title field
"""
import json
import sys
import time

DRY_RUN = "--dry-run" in sys.argv

# Tables to check (ordered by expected issue count)
TARGET_TABLES = [
    ("DocumentSection", "title", "content"),
    ("MindmapNode", "title", "content"),
    ("CPAKnowledge", "title", "content"),
    ("FAQEntry", "title", "content"),  # FAQEntry might use 'question' field
    ("LawOrRegulation", "title", "fullText"),
    ("RegulationClause", "title", "fullText"),
]

TITLE_MIN_LEN = 5


def extract_title(content: str) -> str:
    """Extract a meaningful title from content text.

    Strategy: first sentence, capped at 80 chars, cleaned.
    """
    if not content or len(content.strip()) < 5:
        return ""

    text = content.strip()

    # Try first sentence (Chinese period, newline, or English period)
    for sep in ["。", "\n", "；", ". ", "：", ":", "—"]:
        idx = text.find(sep)
        if 5 <= idx <= 80:
            return text[:idx].strip()

    # Fall back to first 50 chars
    return text[:50].strip()


def fix_table(conn, table: str, title_field: str, content_field: str) -> tuple[int, int]:
    """Fix empty titles in a single table. Returns (fixed, total_empty)."""
    # Count empty titles
    try:
        r = conn.execute(
            f"MATCH (n:{table}) WHERE n.{title_field} IS NULL OR size(n.{title_field}) < {TITLE_MIN_LEN} "
            f"RETURN count(n)"
        )
        total_empty = r.get_next()[0]
    except Exception as e:
        print(f"  WARN: Cannot query {table}.{title_field}: {e}")
        return 0, 0

    if total_empty == 0:
        print(f"  {table}: all titles OK")
        return 0, 0

    print(f"  {table}: {total_empty} nodes with empty/short title")

    # Fetch nodes needing fix (batch of 500)
    fixed = 0
    try:
        r = conn.execute(
            f"MATCH (n:{table}) WHERE n.{title_field} IS NULL OR size(n.{title_field}) < {TITLE_MIN_LEN} "
            f"RETURN n.id, n.{content_field} LIMIT 5000"
        )
        while r.has_next():
            row = r.get_next()
            nid = row[0]
            content = row[1] or ""

            new_title = extract_title(content)
            if len(new_title) < TITLE_MIN_LEN:
                continue

            if DRY_RUN:
                if fixed < 3:
                    print(f"    [DRY] {nid}: '{new_title}'")
                fixed += 1
                continue

            try:
                conn.execute(
                    f"MATCH (n:{table}) WHERE n.id = $id SET n.{title_field} = $title",
                    {"id": nid, "title": new_title},
                )
                fixed += 1
            except Exception as e:
                if fixed == 0:
                    print(f"    ERROR updating {nid}: {e}")
    except Exception as e:
        print(f"  ERROR fetching from {table}: {e}")

    print(f"  {table}: fixed {fixed}/{total_empty}")
    return fixed, total_empty


def main():
    try:
        import kuzu
    except ImportError:
        print("ERROR: kuzu not installed. Run: pip install kuzu")
        sys.exit(1)

    db_path = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
    print(f"=== Fix Empty Titles {'(DRY RUN)' if DRY_RUN else ''} ===")
    print(f"DB: {db_path}")
    print()

    try:
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)
    except Exception as e:
        print(f"ERROR: Cannot connect to KuzuDB: {e}")
        sys.exit(1)

    total_fixed = 0
    total_empty = 0

    for table, title_field, content_field in TARGET_TABLES:
        f, e = fix_table(conn, table, title_field, content_field)
        total_fixed += f
        total_empty += e

    # Also try FAQEntry with 'question' field as fallback
    try:
        r = conn.execute(
            "MATCH (n:FAQEntry) WHERE (n.title IS NULL OR size(n.title) < 5) AND n.question IS NOT NULL "
            "RETURN n.id, n.question LIMIT 5000"
        )
        faq_fixed = 0
        while r.has_next():
            row = r.get_next()
            nid, question = row[0], (row[1] or "")
            if len(question) >= 5:
                if not DRY_RUN:
                    try:
                        conn.execute(
                            "MATCH (n:FAQEntry) WHERE n.id = $id SET n.title = $title",
                            {"id": nid, "title": question[:80]},
                        )
                    except:
                        pass
                faq_fixed += 1
        if faq_fixed:
            total_fixed += faq_fixed
            print(f"  FAQEntry (question->title): fixed {faq_fixed}")
    except:
        pass

    print()
    print(f"=== DONE: Fixed {total_fixed}/{total_empty} empty titles ===")
    if DRY_RUN:
        print("(Dry run — no changes written. Remove --dry-run to apply.)")


if __name__ == "__main__":
    main()
