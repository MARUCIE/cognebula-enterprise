#!/usr/bin/env python3
"""Ingest STARD statute dataset (55K articles) into KuzuDB.

Source: https://github.com/oneal2000/STARD
Format: JSONL, each line: {"id": N, "name": "法律名第X条", "content": "条文内容"}

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/ingest_stard.py
    sudo systemctl start kg-api
"""
import hashlib
import json
import logging
import time
import kuzu

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("stard")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
STARD_PATH = "/tmp/STARD/data/corpus.jsonl"

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

r = conn.execute("MATCH (n) RETURN count(n)")
before_nodes = r.get_next()[0]
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
before_edges = r.get_next()[0]
log.info("Before: %s nodes / %s edges", f"{before_nodes:,}", f"{before_edges:,}")

inserted = 0
skipped = 0
t0 = time.time()

with open(STARD_PATH) as f:
    for i, line in enumerate(f):
        d = json.loads(line)
        name = d.get("name", "")
        content = d.get("content", "").strip()
        if len(content) < 10:
            continue

        doc_id = hashlib.sha256(f"stard:{d['id']}:{name}".encode()).hexdigest()[:16]

        try:
            r = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": doc_id})
            if r.has_next():
                skipped += 1
                continue
            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, source: $source, type: $tp})",
                {"id": doc_id, "title": name[:500], "content": content[:50000],
                 "source": "stard_statute", "tp": "statute_article"}
            )
            inserted += 1
        except Exception as e:
            if inserted < 3:
                log.warning("ERR: %s", str(e)[:80])

        if (i + 1) % 10000 == 0:
            log.info("  Progress: %d, +%d new, %d skipped", i + 1, inserted, skipped)

elapsed = time.time() - t0

r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
edges = r.get_next()[0]
log.info("STARD ingest: +%d new, %d skipped (%.0fs)", inserted, skipped, elapsed)
log.info("Graph: %s nodes / %s edges / density %.3f", f"{nodes:,}", f"{edges:,}", edges / nodes)

del conn; del db
