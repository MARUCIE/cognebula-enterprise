#!/usr/bin/env python3
"""Ingest crawled data from JSON files into KuzuDB.

Use when crawl scripts saved JSON but ingest failed (schema mismatch etc).

Usage:
    /home/kg/kg-env/bin/python3 -u scripts/ingest_from_json.py data/recrawl/baike_fulltext.json --source baike_kuaiji
    /home/kg/kg-env/bin/python3 -u scripts/ingest_from_json.py data/compliance-matrix/compliance_matrix_all.json --source compliance_matrix
"""
import argparse
import json
import logging
import kuzu

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ingest")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"


def ingest(json_path: str, source: str):
    with open(json_path) as f:
        items = json.load(f)
    log.info("Loaded %d items from %s", len(items), json_path)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    inserted = 0
    skipped = 0
    for item in items:
        item_id = item.get("id", "")
        if not item_id:
            continue
        content = item.get("content", "")
        if len(content) < 50:
            continue

        try:
            r = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": item_id})
            if r.has_next():
                # Update if existing has short content
                conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) "
                    "WHERE k.content IS NULL OR size(k.content) < size($content) "
                    "SET k.content = $content",
                    {"id": item_id, "content": content[:50000]}
                )
                skipped += 1
                continue

            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, source: $source, type: $tp})",
                {
                    "id": item_id,
                    "title": item.get("title", "")[:500],
                    "content": content[:50000],
                    "source": source,
                    "tp": item.get("type", item.get("taxType", source)),
                }
            )
            inserted += 1
        except Exception as e:
            if inserted < 3:
                log.warning("Ingest failed: %s", str(e)[:100])

    log.info("Ingest %s: +%d new, %d updated/skipped", source, inserted, skipped)

    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    log.info("Graph: %s nodes / %s edges / density %.3f", f"{nodes:,}", f"{edges:,}", edges / nodes)

    del conn
    del db


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", help="Path to JSON file")
    parser.add_argument("--source", required=True, help="Source name for KU nodes")
    args = parser.parse_args()
    ingest(args.json_path, args.source)
