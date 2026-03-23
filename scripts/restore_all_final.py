#!/usr/bin/env python3
"""Final comprehensive KU content restore — all sources in one pass.

CRITICAL: Run with API stopped. Do NOT restart API until this completes.
This script handles ALL sources and does its own CHECKPOINT discipline.

Sources:
1. lr_cleanup CSV (32K, inline content)
2. lr_cleanup JSONL (18K, LLM backfill)
3. compliance_matrix JSON (20K)
4. baike fulltext (5K)
5. NDRC fulltext
6. MOF fulltext
7. CICPA JSONL
8. chinatax_api variants (4.5K)
9. QA CSV (701, Q+A combined)
"""
import csv
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("final")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DATA_DIR = "/home/kg/cognebula-enterprise/data"
MAX_CONTENT = 3000
CHECKPOINT_EVERY = 50
RECONNECT_EVERY = 14000
MIN_CONTENT = 100


class SafeDB:
    def __init__(self):
        import kuzu
        self._kuzu = kuzu
        self.writes = 0
        self.total_writes = 0
        self.skipped = 0
        self.updated = 0
        self._connect()

    def _connect(self):
        self.db = self._kuzu.Database(DB_PATH)
        self.conn = self._kuzu.Connection(self.db)
        self.writes = 0
        log.info("  DB connected (total: %d writes, %d updated)", self.total_writes, self.updated)

    def _reconnect(self):
        try:
            self.conn.execute("CHECKPOINT")
        except:
            pass
        del self.conn
        del self.db
        time.sleep(2)  # Extra safety margin
        self._connect()

    def safe_set(self, node_id, content):
        content = content[:MAX_CONTENT]
        if len(content) < MIN_CONTENT:
            self.skipped += 1
            return False
        try:
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
            self.updated += 1
            if self.writes % CHECKPOINT_EVERY == 0:
                self.conn.execute("CHECKPOINT")
            if self.writes >= RECONNECT_EVERY:
                self._reconnect()
            return True
        except:
            self.skipped += 1
            return False

    def find_by_title(self, title):
        try:
            r = self.conn.execute(
                "MATCH (k:KnowledgeUnit) WHERE k.title = $t RETURN k.id LIMIT 1",
                {"t": title}
            )
            if r.has_next():
                return str(r.get_next()[0])
        except:
            pass
        return None

    def checkpoint_and_report(self, label):
        try:
            self.conn.execute("CHECKPOINT")
        except:
            pass
        r = self.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
        good = r.get_next()[0]
        r = self.conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
        total = r.get_next()[0]
        log.info("  [CHECKPOINT after %s] KU >=100c: %d/%d (%.1f%%)", label, good, total, 100*good/total)
        return good

    def close(self):
        try:
            self.conn.execute("CHECKPOINT")
        except:
            pass
        del self.conn
        del self.db


def main():
    t0 = time.time()
    sdb = SafeDB()

    before = sdb.checkpoint_and_report("start")

    # === 1. lr_cleanup CSV (biggest source, 32K with 20K having content) ===
    log.info("\n[1/9] lr_cleanup CSV...")
    csv_path = os.path.join(DATA_DIR, "edge_csv/m3_lr_cleanup/ku_from_lr_v2.csv")
    count = 0
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    node_id = row[0].strip().strip('"')
                    content = row[3].strip().strip('"')
                    if sdb.safe_set(node_id, content):
                        count += 1
        log.info("  lr_cleanup CSV: +%d", count)
    sdb.checkpoint_and_report("lr_csv")

    # === 2. lr_cleanup JSONL (LLM backfill, may have content CSV doesn't) ===
    log.info("\n[2/9] lr_cleanup JSONL...")
    jsonl_path = os.path.join(DATA_DIR, "backfill/lr_cleanup_content.jsonl")
    count = 0
    if os.path.exists(jsonl_path):
        with open(jsonl_path) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    if sdb.safe_set(item["id"], item.get("content", "")):
                        count += 1
                except:
                    pass
        log.info("  lr_cleanup JSONL: +%d", count)
    sdb.checkpoint_and_report("lr_jsonl")

    # === 3. compliance_matrix ===
    log.info("\n[3/9] compliance_matrix...")
    import hashlib
    cm_path = os.path.join(DATA_DIR, "compliance-matrix/compliance_matrix_fast_all.json")
    count = 0
    if os.path.exists(cm_path):
        with open(cm_path) as f:
            data = json.load(f)
        for item in data:
            content = item.get("content", "") or item.get("analysis", "") or ""
            node_id = item.get("id", "")
            if not node_id:
                key = f"cm:{item.get('tax_type','')}:{item.get('business_activity','')}:{item.get('scenario','')}"
                node_id = hashlib.sha256(key.encode()).hexdigest()[:16]
            if sdb.safe_set(node_id, content):
                count += 1
        log.info("  compliance_matrix: +%d", count)
    sdb.checkpoint_and_report("compliance")

    # === 4. baike fulltext ===
    log.info("\n[4/9] baike fulltext...")
    count = 0
    baike_path = os.path.join(DATA_DIR, "recrawl/baike_fulltext.json")
    if os.path.exists(baike_path):
        with open(baike_path) as f:
            data = json.load(f)
        for item in data:
            title = item.get("title", "")
            content = item.get("content", "")
            if len(content) >= MIN_CONTENT and title:
                kid = sdb.find_by_title(title)
                if kid and sdb.safe_set(kid, content):
                    count += 1
        log.info("  baike: +%d", count)
    sdb.checkpoint_and_report("baike")

    # === 5. NDRC fulltext ===
    log.info("\n[5/9] NDRC fulltext...")
    count = 0
    ndrc_path = os.path.join(DATA_DIR, "recrawl/ndrc_fulltext.json")
    if os.path.exists(ndrc_path):
        with open(ndrc_path) as f:
            data = json.load(f)
        for item in data:
            title = item.get("title", "")
            content = item.get("content", "")
            if len(content) >= MIN_CONTENT and title:
                kid = sdb.find_by_title(title)
                if kid and sdb.safe_set(kid, content):
                    count += 1
        log.info("  NDRC: +%d", count)

    # === 6. MOF fulltext ===
    log.info("\n[6/9] MOF fulltext...")
    count = 0
    mof_path = os.path.join(DATA_DIR, "recrawl/mof_fulltext.json")
    if os.path.exists(mof_path):
        with open(mof_path) as f:
            data = json.load(f)
        for item in data:
            title = item.get("title", "")
            content = item.get("content", "")
            if len(content) >= MIN_CONTENT and title:
                kid = sdb.find_by_title(title)
                if kid and sdb.safe_set(kid, content):
                    count += 1
        log.info("  MOF: +%d", count)

    # === 7. CICPA JSONL ===
    log.info("\n[7/9] CICPA JSONL...")
    count = 0
    cicpa_path = os.path.join(DATA_DIR, "backfill/cicpa_content.jsonl")
    if os.path.exists(cicpa_path):
        with open(cicpa_path) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    if sdb.safe_set(item["id"], item.get("content", "")):
                        count += 1
                except:
                    pass
        log.info("  CICPA: +%d", count)
    sdb.checkpoint_and_report("cicpa")

    # === 8. chinatax by title ===
    log.info("\n[8/9] chinatax by title...")
    count = 0
    for fname in ["raw/chinatax-full/chinatax_api.json", "raw/20260315-fgk-deep/chinatax_api.json",
                   "raw/2026-03-15-fgk-extra/chinatax_api.json"]:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)
        for item in data:
            title = (item.get("title", "") or "").strip()
            content = item.get("content", "") or ""
            if len(content) >= MIN_CONTENT and len(title) >= 5:
                kid = sdb.find_by_title(title)
                if kid and sdb.safe_set(kid, content):
                    count += 1
    log.info("  chinatax: +%d", count)
    sdb.checkpoint_and_report("chinatax")

    # === 9. QA CSV (answers) ===
    log.info("\n[9/9] QA CSV answers...")
    count = 0
    qa_path = os.path.join(DATA_DIR, "edge_csv/m3_qa/qa_nodes.csv")
    if os.path.exists(qa_path):
        with open(qa_path) as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    node_id = row[0]
                    question = row[2]
                    answer = row[3]
                    content = f"Q: {question}\nA: {answer}"
                    if sdb.safe_set(node_id, content):
                        count += 1
        log.info("  QA CSV: +%d", count)

    # === FINAL ===
    after = sdb.checkpoint_and_report("FINAL")

    elapsed = time.time() - t0
    log.info("\n" + "=" * 60)
    log.info("Final restore complete (%.0fs)", elapsed)
    log.info("  Total writes: %d | Updated: %d | Skipped: %d",
             sdb.total_writes, sdb.updated, sdb.skipped)
    log.info("  KU >=100c: %d -> %d (%+d)", before, after, after - before)

    sdb.close()


if __name__ == "__main__":
    main()
