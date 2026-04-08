#!/usr/bin/env python3
"""Fix LegalDocument — inherit fullText from LawOrRegulation.

LegalDocument was created from LawOrRegulation during v4.1 migration,
but fullText was not copied. Both share the same ID. This script copies
fullText from LawOrRegulation to LegalDocument.description.

Authoritative type: content inherited from source, NOT AI-generated.

Run with API stopped (KuzuDB direct access).
"""
import kuzu
import os
import re
import time

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")


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


def main():
    print("=" * 60)
    print("  LegalDocument Fix — Inherit fullText from LawOrRegulation")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Check if description field exists on LegalDocument
    try:
        conn.execute(
            "MATCH (n:LegalDocument) WHERE n.description IS NOT NULL "
            "RETURN count(n)"
        )
    except Exception:
        print("  Adding description field via ALTER TABLE...")
        try:
            conn.execute(
                'ALTER TABLE LegalDocument ADD description STRING DEFAULT ""'
            )
            print("  OK: description field added")
        except Exception as e:
            print(f"  ERROR: {e}")
            return

    # Count LegalDocument with empty description
    r = conn.execute(
        "MATCH (n:LegalDocument) "
        "WHERE n.description IS NULL OR size(n.description) < 20 "
        "RETURN count(n)"
    )
    empty_count = r.get_next()[0]
    print(f"  LegalDocument with empty description: {empty_count:,}")

    # Count LawOrRegulation with fullText
    r = conn.execute(
        "MATCH (n:LawOrRegulation) "
        "WHERE n.fullText IS NOT NULL AND size(n.fullText) >= 50 "
        "RETURN count(n)"
    )
    lr_with_text = r.get_next()[0]
    print(f"  LawOrRegulation with fullText: {lr_with_text:,}")

    # Process in batches to avoid OOM (83K JOINs failed before with 8GB RAM)
    BATCH_SIZE = 200
    total_updated = 0
    total_errors = 0
    total_skipped = 0
    offset = 0

    while True:
        # Fetch batch of LegalDocument IDs with empty description
        q = (
            "MATCH (ld:LegalDocument) "
            "WHERE ld.description IS NULL OR size(ld.description) < 20 "
            f"RETURN ld.id SKIP {offset} LIMIT {BATCH_SIZE}"
        )
        result = conn.execute(q)

        ld_ids = []
        while result.has_next():
            row = result.get_next()
            ld_ids.append(str(row[0] or ""))

        if not ld_ids:
            break

        # For each LegalDocument, look up matching LawOrRegulation
        batch_updated = 0
        for ld_id in ld_ids:
            if not ld_id:
                continue

            safe_id = ld_id.replace("'", "\\'")
            try:
                r = conn.execute(
                    f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{safe_id}' "
                    f"RETURN lr.fullText, lr.title, lr.summary"
                )
                if not r.has_next():
                    total_skipped += 1
                    continue

                row = r.get_next()
                fulltext = str(row[0] or "")
                title = str(row[1] or "")
                summary = str(row[2] or "")

                # Use the longest available content
                content = fulltext if len(fulltext) > len(summary) else summary
                if len(content) < 20 and title:
                    content = title
                if len(content) < 10:
                    total_skipped += 1
                    continue

                if safe_set(conn, ld_id, content):
                    batch_updated += 1
                else:
                    total_errors += 1

            except Exception:
                total_errors += 1

        total_updated += batch_updated

        if (offset + BATCH_SIZE) % 2000 == 0 or not ld_ids:
            print(
                f"  Progress: {offset + len(ld_ids):,} processed | "
                f"{total_updated:,} updated | {total_skipped:,} skipped | "
                f"{total_errors:,} errors"
            )

        offset += BATCH_SIZE

        # Brief pause every 1000 nodes to avoid DB pressure
        if offset % 1000 == 0:
            time.sleep(0.5)

    print(f"\n  Done: {total_updated:,} updated, "
          f"{total_skipped:,} skipped (no LR match), "
          f"{total_errors:,} errors")
    print("=" * 60)


if __name__ == "__main__":
    main()
