#!/usr/bin/env python3
"""Restore lr_cleanup KU content WITHOUT reconnect.

The 8GB VPS KuzuDB reconnect bug causes previously-checkpointed data to be lost.
This script avoids reconnect entirely by:
1. Processing in smaller chunks with frequent CHECKPOINT
2. Never closing/reopening the DB connection
3. Using explicit memory management (gc.collect between chunks)

Target: ~14K lr_cleanup KU nodes that lost content due to reconnect

Run on kg-node (after QA gen completes):
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/restore_lr_no_reconnect.py 2>&1 | tee /tmp/restore_lr_norec.log
    sudo systemctl start kg-api
"""
import csv
import gc
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("lr_norec")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_PATH = "/home/kg/cognebula-enterprise/data/edge_csv/m3_lr_cleanup/ku_from_lr_v2.csv"
JSONL_PATH = "/home/kg/cognebula-enterprise/data/backfill/lr_cleanup_content.jsonl"
MAX_CONTENT = 3000
CHECKPOINT_EVERY = 30  # More frequent checkpoint (was 50)


def main():
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    writes = 0

    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    before = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    total_ku = r.get_next()[0]
    log.info("BEFORE: %d/%d (%.1f%%)", before, total_ku, 100 * before / total_ku)

    # Phase 1: Load all content from CSV + JSONL into memory, pick longest per ID
    log.info("\nLoading content sources into memory...")
    content_map = {}  # id -> content

    # CSV source
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                nid = row[0].strip().strip('"')
                content = row[3].strip().strip('"')[:MAX_CONTENT]
                if len(content) >= 100:
                    if nid not in content_map or len(content) > len(content_map[nid]):
                        content_map[nid] = content

    log.info("  CSV: %d IDs with content>=100c", len(content_map))

    # JSONL source (may have longer content for same IDs)
    jsonl_added = 0
    with open(JSONL_PATH) as f:
        for line in f:
            try:
                item = json.loads(line)
                nid = item["id"]
                content = item.get("content", "")[:MAX_CONTENT]
                if len(content) >= 100:
                    if nid not in content_map or len(content) > len(content_map[nid]):
                        content_map[nid] = content
                        jsonl_added += 1
            except:
                pass

    log.info("  JSONL added/replaced: %d (total unique: %d)", jsonl_added, len(content_map))

    # Phase 2: Write to DB without reconnect
    log.info("\nWriting to DB (no reconnect)...")
    updated = 0
    skipped = 0
    items = list(content_map.items())
    del content_map  # Free memory
    gc.collect()

    for i, (nid, content) in enumerate(items):
        try:
            r = conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                {"id": nid}
            )
            if not r.has_next():
                skipped += 1
                continue
            existing = r.get_next()[0]
            if existing >= len(content):
                skipped += 1
                continue

            conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                {"id": nid, "c": content}
            )
            writes += 1
            updated += 1

            if writes % CHECKPOINT_EVERY == 0:
                conn.execute("CHECKPOINT")

            # Periodic GC to reduce memory pressure
            if writes % 1000 == 0:
                gc.collect()

        except Exception:
            skipped += 1

        if (i + 1) % 5000 == 0:
            conn.execute("CHECKPOINT")
            r2 = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
            current = r2.get_next()[0]
            log.info("  %d/%d: updated=%d, skipped=%d, current coverage=%d (%.1f%%)",
                     i + 1, len(items), updated, skipped, current, 100 * current / total_ku)

    # Final
    conn.execute("CHECKPOINT")
    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    after = r.get_next()[0]

    log.info("\n" + "=" * 60)
    log.info("lr_cleanup restore (no reconnect) complete")
    log.info("  Updated: %d | Skipped: %d | Writes: %d", updated, skipped, writes)
    log.info("  KU coverage: %d -> %d (%+d), %.1f%%", before, after, after - before, 100 * after / total_ku)

    del conn, db


if __name__ == "__main__":
    main()
