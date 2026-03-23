#!/usr/bin/env python3
"""Restore KU content from the original lr_cleanup CSV source.

The CSV (ku_from_lr_v2.csv) has 32,841 entries with 19,948 having content >= 100c.
The JSONL backfill only covered 18,626. This script fills the gap from CSV directly.

Also processes: mindmap all_mindmap_nodes.json, 12366 hotspot data.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/restore_ku_from_csv.py 2>&1 | tee /tmp/restore_csv.log
    sudo systemctl start kg-api
"""
import csv
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("restore_csv")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DATA_DIR = "/home/kg/cognebula-enterprise/data"
MAX_CONTENT = 3000
CHECKPOINT_EVERY = 50
RECONNECT_EVERY = 10000
MIN_CONTENT = 100


class SafeDB:
    def __init__(self):
        import kuzu
        self._kuzu = kuzu
        self.writes = 0
        self.total_writes = 0
        self.skipped = 0
        self._connect()

    def _connect(self):
        self.db = self._kuzu.Database(DB_PATH)
        self.conn = self._kuzu.Connection(self.db)
        self.writes = 0
        log.info("  DB connected (total writes: %d)", self.total_writes)

    def _reconnect(self):
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass
        del self.conn
        del self.db
        time.sleep(1)
        self._connect()

    def safe_set_content(self, node_id, content):
        content = content[:MAX_CONTENT]
        if len(content) < MIN_CONTENT:
            self.skipped += 1
            return False
        try:
            # Check existing
            r = self.conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                {"id": node_id}
            )
            if not r.has_next():
                self.skipped += 1
                return False
            existing = r.get_next()[0]
            if existing >= len(content):
                self.skipped += 1
                return False

            self.conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                {"id": node_id, "c": content}
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


def restore_from_csv(sdb):
    """Restore from the original lr_cleanup CSV which has inline content."""
    path = os.path.join(DATA_DIR, "edge_csv", "m3_lr_cleanup", "ku_from_lr_v2.csv")
    if not os.path.exists(path):
        log.warning("CSV not found")
        return 0

    updated = 0
    total = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            total += 1
            if len(row) < 4:
                continue
            node_id = row[0].strip().strip('"')
            content = row[3].strip().strip('"')
            if sdb.safe_set_content(node_id, content):
                updated += 1
            if total % 5000 == 0:
                log.info("  CSV: %d processed, %d updated", total, updated)

    log.info("  CSV DONE: %d updated / %d total", updated, total)
    return updated


def restore_mindmap(sdb):
    """Restore from mindmap extracted JSON files."""
    base = os.path.join(DATA_DIR, "extracted", "mindmap")
    if not os.path.isdir(base):
        return 0

    updated = 0
    for fname in os.listdir(base):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(base, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue
            for item in data:
                content = item.get("content", "") or item.get("text", "") or ""
                node_id = item.get("id", "")
                if node_id and sdb.safe_set_content(node_id, content):
                    updated += 1
        except Exception:
            pass

    log.info("  mindmap DONE: %d updated", updated)
    return updated


def restore_mindmap_fixes(sdb):
    """Restore from mindmap_fixes directory."""
    base = os.path.join(DATA_DIR, "extracted", "mindmap_fixes")
    if not os.path.isdir(base):
        return 0

    updated = 0
    total = 0
    for fname in os.listdir(base):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(base, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue
            for item in data:
                total += 1
                content = item.get("content", "") or item.get("text", "") or ""
                title = item.get("title", "") or item.get("topic", "")
                node_id = item.get("id", "")
                if not node_id and title:
                    # Try title match
                    try:
                        r = sdb.conn.execute(
                            "MATCH (m:MindmapNode) WHERE m.title = $t OR m.topic = $t RETURN m.id LIMIT 1",
                            {"t": title}
                        )
                        if r.has_next():
                            node_id = str(r.get_next()[0])
                    except Exception:
                        pass
                if node_id and len(content) >= 50:
                    # MindmapNode has different table, need different SET
                    try:
                        r = sdb.conn.execute(
                            "MATCH (m:MindmapNode {id: $id}) RETURN CASE WHEN m.content IS NOT NULL THEN size(m.content) ELSE 0 END",
                            {"id": node_id}
                        )
                        if r.has_next():
                            existing = r.get_next()[0]
                            if existing < len(content[:MAX_CONTENT]):
                                sdb.conn.execute(
                                    "MATCH (m:MindmapNode {id: $id}) SET m.content = $c",
                                    {"id": node_id, "c": content[:MAX_CONTENT]}
                                )
                                sdb.writes += 1
                                sdb.total_writes += 1
                                if sdb.writes % CHECKPOINT_EVERY == 0:
                                    sdb.conn.execute("CHECKPOINT")
                                if sdb.writes >= RECONNECT_EVERY:
                                    sdb._reconnect()
                                updated += 1
                    except Exception:
                        pass

            if total % 10000 == 0:
                log.info("  mindmap_fixes: %d processed, %d updated", total, updated)
        except Exception as e:
            log.warning("  Error reading %s: %s", fname, e)

    log.info("  mindmap_fixes DONE: %d updated / %d total", updated, total)
    return updated


def main():
    t0 = time.time()
    sdb = SafeDB()

    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    before = r.get_next()[0]
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    total_ku = r.get_next()[0]
    log.info("BEFORE: %d/%d KU with content >=100c (%.1f%%)", before, total_ku, 100 * before / total_ku)

    results = {}

    log.info("\n[1/3] lr_cleanup CSV (original source)...")
    results["csv"] = restore_from_csv(sdb)

    log.info("\n[2/3] mindmap extracted JSON...")
    results["mindmap"] = restore_mindmap(sdb)

    log.info("\n[3/3] mindmap_fixes JSON...")
    results["mindmap_fixes"] = restore_mindmap_fixes(sdb)

    # Final
    sdb.conn.execute("CHECKPOINT")
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    after = r.get_next()[0]

    elapsed = time.time() - t0
    log.info("\n" + "=" * 60)
    log.info("Restore CSV complete (%.0fs)", elapsed)
    for source, count in results.items():
        log.info("  %s: +%d", source, count)
    log.info("  Total writes: %d, skipped: %d", sdb.total_writes, sdb.skipped)
    log.info("  KU coverage: %d/%d (%.1f%%) — was %.1f%%",
             after, total_ku, 100 * after / total_ku, 100 * before / total_ku)
    log.info("  Delta: %+d KU with content", after - before)

    sdb.close()


if __name__ == "__main__":
    main()
