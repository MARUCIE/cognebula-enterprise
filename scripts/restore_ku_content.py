#!/usr/bin/env python3
"""Restore KU content from source JSON/CSV files after WAL deletion.

KuzuDB WAL OOM caused content regression. This script restores content
from original data files with safe CHECKPOINT discipline.

CRITICAL RULES (8GB VPS):
- CHECKPOINT every 50 writes
- Restart DB connection every 10,000 writes
- Truncate content to 3000c to reduce buffer pressure
- Log progress for resume capability

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/restore_ku_content.py 2>&1 | tee /tmp/restore_ku_content.log
    sudo systemctl start kg-api
"""
import csv
import hashlib
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("restore")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DATA_DIR = "/home/kg/cognebula-enterprise/data"
MAX_CONTENT = 3000  # Truncate to prevent buffer OOM
CHECKPOINT_EVERY = 50
RECONNECT_EVERY = 10000


class SafeDB:
    """KuzuDB wrapper with auto-checkpoint and reconnect."""

    def __init__(self):
        import kuzu
        self._kuzu = kuzu
        self.writes = 0
        self.total_writes = 0
        self._connect()

    def _connect(self):
        self.db = self._kuzu.Database(DB_PATH)
        self.conn = self._kuzu.Connection(self.db)
        self.writes = 0
        log.info("  DB connected (total writes so far: %d)", self.total_writes)

    def _reconnect(self):
        """Checkpoint + close + reopen to release buffer pool."""
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass
        del self.conn
        del self.db
        time.sleep(1)
        self._connect()

    def execute(self, query, params=None):
        if params:
            self.conn.execute(query, params)
        else:
            self.conn.execute(query)

    def set_content(self, node_id: str, content: str) -> bool:
        """SET content on a KU node with checkpoint discipline."""
        try:
            self.conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                {"id": node_id, "c": content[:MAX_CONTENT]}
            )
            self.writes += 1
            self.total_writes += 1

            if self.writes % CHECKPOINT_EVERY == 0:
                self.conn.execute("CHECKPOINT")

            if self.writes >= RECONNECT_EVERY:
                self._reconnect()

            return True
        except Exception:
            return False

    def close(self):
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass
        del self.conn
        del self.db


def restore_compliance_matrix(sdb: SafeDB) -> int:
    """Restore compliance_matrix KU content from JSON."""
    path = os.path.join(DATA_DIR, "compliance-matrix", "compliance_matrix_fast_all.json")
    if not os.path.exists(path):
        log.warning("compliance_matrix JSON not found")
        return 0

    with open(path) as f:
        data = json.load(f)

    updated = 0
    for i, item in enumerate(data):
        content = item.get("content", "") or item.get("analysis", "") or ""
        if len(content) < 50:
            continue
        node_id = item.get("id", "")
        if not node_id:
            # Reconstruct ID from fields
            key = f"cm:{item.get('tax_type','')}:{item.get('business_activity','')}:{item.get('scenario','')}"
            node_id = hashlib.sha256(key.encode()).hexdigest()[:16]

        if sdb.set_content(node_id, content):
            updated += 1

        if (i + 1) % 5000 == 0:
            log.info("  compliance_matrix: %d/%d processed, %d updated", i + 1, len(data), updated)

    return updated


def restore_baike(sdb: SafeDB) -> int:
    """Restore baike KU content from fulltext JSON."""
    path = os.path.join(DATA_DIR, "recrawl", "baike_fulltext.json")
    if not os.path.exists(path):
        return 0

    with open(path) as f:
        data = json.load(f)

    updated = 0
    for item in data:
        title = item.get("title", "")
        content = item.get("content", "")
        if len(content) < 50 or not title:
            continue

        # Try to find KU by title match
        try:
            r = sdb.conn.execute(
                "MATCH (k:KnowledgeUnit) WHERE k.title = $t AND (k.content IS NULL OR size(k.content) < 50) RETURN k.id LIMIT 1",
                {"t": title}
            )
            if r.has_next():
                kid = str(r.get_next()[0])
                if sdb.set_content(kid, content):
                    updated += 1
        except Exception:
            pass

    return updated


def restore_ndrc(sdb: SafeDB) -> int:
    """Restore NDRC fulltext."""
    path = os.path.join(DATA_DIR, "recrawl", "ndrc_fulltext.json")
    if not os.path.exists(path):
        return 0

    with open(path) as f:
        data = json.load(f)

    updated = 0
    for item in data:
        title = item.get("title", "")
        content = item.get("content", "")
        if len(content) < 50:
            continue
        try:
            r = sdb.conn.execute(
                "MATCH (k:KnowledgeUnit) WHERE k.title = $t AND (k.content IS NULL OR size(k.content) < 50) RETURN k.id LIMIT 1",
                {"t": title}
            )
            if r.has_next():
                kid = str(r.get_next()[0])
                if sdb.set_content(kid, content):
                    updated += 1
        except Exception:
            pass

    return updated


def restore_lr_cleanup(sdb: SafeDB) -> int:
    """Restore lr_cleanup content from backfill JSONL."""
    path = os.path.join(DATA_DIR, "backfill", "lr_cleanup_content.jsonl")
    if not os.path.exists(path):
        return 0

    items = []
    with open(path) as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except Exception:
                pass

    updated = 0
    for i, item in enumerate(items):
        if sdb.set_content(item["id"], item["content"]):
            updated += 1
        if (i + 1) % 5000 == 0:
            log.info("  lr_cleanup: %d/%d processed, %d updated", i + 1, len(items), updated)

    return updated


def restore_mindmap(sdb: SafeDB) -> int:
    """Restore mindmap content from extracted JSON."""
    path = os.path.join(DATA_DIR, "extracted", "mindmap", "all_mindmap_nodes.json")
    if not os.path.exists(path):
        return 0

    with open(path) as f:
        data = json.load(f)

    updated = 0
    for item in data:
        content = item.get("content", "") or item.get("text", "")
        node_id = item.get("id", "")
        if len(content) < 20 or not node_id:
            continue
        if sdb.set_content(node_id, content):
            updated += 1

    return updated


def main():
    t0 = time.time()
    sdb = SafeDB()

    # Pre-flight
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    before = r.get_next()[0]
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    total = r.get_next()[0]
    log.info("Before: %d/%d KU with content >=100c (%.1f%%)", before, total, 100 * before / total)

    # Restore in priority order
    results = {}

    log.info("\n[1/5] Restoring lr_cleanup...")
    results["lr_cleanup"] = restore_lr_cleanup(sdb)

    log.info("\n[2/5] Restoring compliance_matrix...")
    results["compliance_matrix"] = restore_compliance_matrix(sdb)

    log.info("\n[3/5] Restoring baike...")
    results["baike"] = restore_baike(sdb)

    log.info("\n[4/5] Restoring NDRC...")
    results["ndrc"] = restore_ndrc(sdb)

    log.info("\n[5/5] Restoring mindmap...")
    results["mindmap"] = restore_mindmap(sdb)

    # Final stats
    sdb.conn.execute("CHECKPOINT")
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    after = r.get_next()[0]

    elapsed = time.time() - t0
    log.info("\n" + "=" * 60)
    log.info("Restore complete (%.0fs)", elapsed)
    for source, count in results.items():
        log.info("  %s: +%d", source, count)
    log.info("  Total writes: %d", sdb.total_writes)
    log.info("  KU coverage: %d/%d (%.1f%%) — was %.1f%%", after, total, 100 * after / total, 100 * before / total)
    log.info("  Delta: +%d KU with content", after - before)

    sdb.close()


if __name__ == "__main__":
    main()
