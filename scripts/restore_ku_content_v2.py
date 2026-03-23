#!/usr/bin/env python3
"""Restore KU content v2 — safe, non-destructive.

Key fix over v1: NEVER overwrite existing good content with shorter/empty content.
Only SET when new content >= 100c AND longer than existing.

Data sources (priority order):
1. backfill/lr_cleanup_content.jsonl  (18,713 items, by ID match)
2. recrawl/baike_fulltext.json        (5,000 items, by title match)
3. recrawl/ndrc_fulltext.json         (NDRC fulltext, by title match)
4. recrawl/mof_fulltext.json          (MOF fulltext, by title match)
5. backfill/cicpa_content.jsonl       (93 items, by ID match)
6. compliance-matrix/compliance_matrix_fast_all.json (20K, by ID match)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/restore_ku_content_v2.py 2>&1 | tee /tmp/restore_ku_v2.log
    sudo systemctl start kg-api
"""
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("restore_v2")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DATA_DIR = "/home/kg/cognebula-enterprise/data"
MAX_CONTENT = 3000
CHECKPOINT_EVERY = 50
RECONNECT_EVERY = 10000
MIN_CONTENT = 100  # Only write if content >= this


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
        log.info("  DB connected (total writes: %d, skipped: %d)", self.total_writes, self.skipped)

    def _reconnect(self):
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass
        del self.conn
        del self.db
        time.sleep(1)
        self._connect()

    def get_existing_content_len(self, node_id: str) -> int:
        """Get length of existing content for a KU node."""
        try:
            r = self.conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                {"id": node_id}
            )
            if r.has_next():
                return r.get_next()[0]
        except Exception:
            pass
        return -1  # Node not found

    def safe_set_content(self, node_id: str, content: str) -> bool:
        """SET content ONLY if new content >= MIN_CONTENT and longer than existing."""
        content = content[:MAX_CONTENT]
        if len(content) < MIN_CONTENT:
            self.skipped += 1
            return False

        existing_len = self.get_existing_content_len(node_id)
        if existing_len < 0:
            self.skipped += 1
            return False  # Node not found
        if existing_len >= len(content):
            self.skipped += 1
            return False  # Existing is already better

        try:
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

    def find_ku_by_title(self, title: str) -> str | None:
        """Find KU ID by title match (for sources without ID)."""
        try:
            r = self.conn.execute(
                "MATCH (k:KnowledgeUnit) WHERE k.title = $t RETURN k.id LIMIT 1",
                {"t": title}
            )
            if r.has_next():
                return str(r.get_next()[0])
        except Exception:
            pass
        return None

    def close(self):
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass
        del self.conn
        del self.db


def restore_lr_cleanup(sdb: SafeDB) -> int:
    path = os.path.join(DATA_DIR, "backfill", "lr_cleanup_content.jsonl")
    if not os.path.exists(path):
        log.warning("lr_cleanup JSONL not found")
        return 0

    updated = 0
    total = 0
    with open(path) as f:
        for line in f:
            total += 1
            try:
                item = json.loads(line)
            except Exception:
                continue
            content = item.get("content", "")
            node_id = item.get("id", "")
            if not node_id or len(content) < MIN_CONTENT:
                sdb.skipped += 1
                continue
            if sdb.safe_set_content(node_id, content):
                updated += 1
            if total % 5000 == 0:
                log.info("  lr_cleanup: %d/%d processed, %d updated", total, total, updated)

    log.info("  lr_cleanup DONE: %d updated / %d total", updated, total)
    return updated


def restore_json_by_title(sdb: SafeDB, name: str, path: str) -> int:
    if not os.path.exists(path):
        log.warning("%s not found", name)
        return 0

    with open(path) as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = list(data.values()) if not any(k in data for k in ["title", "content"]) else [data]

    updated = 0
    for i, item in enumerate(data):
        title = item.get("title", "")
        content = item.get("content", "") or item.get("fulltext", "") or item.get("text", "")
        if not title or len(content) < MIN_CONTENT:
            sdb.skipped += 1
            continue

        kid = sdb.find_ku_by_title(title)
        if kid and sdb.safe_set_content(kid, content):
            updated += 1

        if (i + 1) % 1000 == 0:
            log.info("  %s: %d/%d processed, %d updated", name, i + 1, len(data), updated)

    log.info("  %s DONE: %d updated / %d total", name, updated, len(data))
    return updated


def restore_cicpa(sdb: SafeDB) -> int:
    path = os.path.join(DATA_DIR, "backfill", "cicpa_content.jsonl")
    if not os.path.exists(path):
        log.warning("cicpa JSONL not found")
        return 0

    updated = 0
    total = 0
    with open(path) as f:
        for line in f:
            total += 1
            try:
                item = json.loads(line)
            except Exception:
                continue
            content = item.get("content", "")
            node_id = item.get("id", "")
            if not node_id or len(content) < MIN_CONTENT:
                sdb.skipped += 1
                continue
            if sdb.safe_set_content(node_id, content):
                updated += 1

    log.info("  cicpa DONE: %d updated / %d total", updated, total)
    return updated


def restore_compliance_matrix(sdb: SafeDB) -> int:
    path = os.path.join(DATA_DIR, "compliance-matrix", "compliance_matrix_fast_all.json")
    if not os.path.exists(path):
        log.warning("compliance_matrix JSON not found")
        return 0

    import hashlib
    with open(path) as f:
        data = json.load(f)

    updated = 0
    for i, item in enumerate(data):
        content = item.get("content", "") or item.get("analysis", "") or ""
        if len(content) < MIN_CONTENT:
            sdb.skipped += 1
            continue

        node_id = item.get("id", "")
        if not node_id:
            key = f"cm:{item.get('tax_type', '')}:{item.get('business_activity', '')}:{item.get('scenario', '')}"
            node_id = hashlib.sha256(key.encode()).hexdigest()[:16]

        if sdb.safe_set_content(node_id, content):
            updated += 1

        if (i + 1) % 5000 == 0:
            log.info("  compliance_matrix: %d/%d processed, %d updated", i + 1, len(data), updated)

    log.info("  compliance_matrix DONE: %d updated / %d total", updated, len(data))
    return updated


def main():
    t0 = time.time()
    sdb = SafeDB()

    # Pre-flight
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    before = r.get_next()[0]
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    total = r.get_next()[0]
    log.info("BEFORE: %d/%d KU with content >=100c (%.1f%%)", before, total, 100 * before / total)

    results = {}

    log.info("\n[1/6] lr_cleanup (by ID)...")
    results["lr_cleanup"] = restore_lr_cleanup(sdb)

    log.info("\n[2/6] baike (by title)...")
    results["baike"] = restore_json_by_title(
        sdb, "baike", os.path.join(DATA_DIR, "recrawl", "baike_fulltext.json"))

    log.info("\n[3/6] NDRC (by title)...")
    results["ndrc"] = restore_json_by_title(
        sdb, "ndrc", os.path.join(DATA_DIR, "recrawl", "ndrc_fulltext.json"))

    log.info("\n[4/6] MOF (by title)...")
    results["mof"] = restore_json_by_title(
        sdb, "mof", os.path.join(DATA_DIR, "recrawl", "mof_fulltext.json"))

    log.info("\n[5/6] CICPA (by ID)...")
    results["cicpa"] = restore_cicpa(sdb)

    log.info("\n[6/6] compliance_matrix (by ID)...")
    results["compliance_matrix"] = restore_compliance_matrix(sdb)

    # Final checkpoint and stats
    sdb.conn.execute("CHECKPOINT")
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    after = r.get_next()[0]

    elapsed = time.time() - t0
    log.info("\n" + "=" * 60)
    log.info("Restore v2 complete (%.0fs)", elapsed)
    for source, count in results.items():
        log.info("  %s: +%d", source, count)
    log.info("  Total writes: %d", sdb.total_writes)
    log.info("  Total skipped: %d", sdb.skipped)
    log.info("  KU coverage: %d/%d (%.1f%%) — was %.1f%%",
             after, total, 100 * after / total, 100 * before / total)
    log.info("  Delta: %+d KU with content", after - before)

    sdb.close()


if __name__ == "__main__":
    main()
