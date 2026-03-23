#!/usr/bin/env python3
"""Ingest chinatax fulltext crawl results into KU nodes.

Reads: data/recrawl/chinatax_fulltext.jsonl
Updates: KnowledgeUnit nodes where source contains 'chinatax'

Match strategy: title exact match → title contains match

Run on kg-node (after QA gen completes):
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/ingest_chinatax_fulltext.py 2>&1 | tee /tmp/ingest_chinatax.log
    sudo systemctl start kg-api
"""
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ct_ingest")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
JSONL_PATH = "/home/kg/cognebula-enterprise/data/recrawl/chinatax_fulltext.jsonl"
CHECKPOINT_EVERY = 30


def main():
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Load JSONL
    items = []
    with open(JSONL_PATH) as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except:
                pass
    log.info("Loaded %d items from JSONL", len(items))

    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    before = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    total_ku = r.get_next()[0]
    log.info("Before: %d/%d (%.1f%%)", before, total_ku, 100 * before / total_ku)

    writes = 0
    updated = 0
    not_found = 0

    for i, item in enumerate(items):
        title = item.get("title", "").strip()
        content = item.get("content", "")[:3000]
        if len(content) < 100 or len(title) < 5:
            continue

        # Try exact title match
        kid = None
        try:
            r = conn.execute(
                "MATCH (k:KnowledgeUnit) WHERE k.title = $t RETURN k.id, CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END LIMIT 1",
                {"t": title}
            )
            if r.has_next():
                row = r.get_next()
                kid = str(row[0])
                existing_len = row[1]
        except:
            pass

        # Fallback: contains match
        if not kid:
            short = title[:25]
            try:
                r = conn.execute(
                    "MATCH (k:KnowledgeUnit) WHERE contains(k.title, $t) RETURN k.id, CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END LIMIT 1",
                    {"t": short}
                )
                if r.has_next():
                    row = r.get_next()
                    kid = str(row[0])
                    existing_len = row[1]
            except:
                pass

        if kid and existing_len < len(content):
            try:
                conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                    {"id": kid, "c": content}
                )
                writes += 1
                updated += 1
                if writes % CHECKPOINT_EVERY == 0:
                    conn.execute("CHECKPOINT")
            except:
                pass
        elif not kid:
            not_found += 1

        if (i + 1) % 100 == 0:
            log.info("  %d/%d: updated=%d, not_found=%d", i + 1, len(items), updated, not_found)

    conn.execute("CHECKPOINT")

    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    after = r.get_next()[0]

    log.info("\n=== DONE ===")
    log.info("Updated: %d | Not found: %d | Writes: %d", updated, not_found, writes)
    log.info("KU coverage: %d -> %d (%+d), %.1f%%", before, after, after - before, 100 * after / total_ku)

    del conn, db


if __name__ == "__main__":
    main()
