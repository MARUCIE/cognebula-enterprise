#!/usr/bin/env python3
"""Ingest 12366 hotspot FAQ data as KnowledgeUnit nodes.

Source: data/raw/20260315-12366-full/20260315-12366/12366_hotspot.json
Target: KnowledgeUnit table with source=12366_hotspot

Each item has: id, title, question, answer, content, category, url, date
Content = Q + A combined; title = question.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/ingest_12366_hotspot.py 2>&1 | tee /tmp/ingest_12366.log
    sudo systemctl start kg-api
"""
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ingest_12366")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DATA_PATH = "/home/kg/cognebula-enterprise/data/raw/20260315-12366-full/20260315-12366/12366_hotspot.json"
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

    def _post_write(self):
        self.writes += 1
        self.total_writes += 1
        if self.writes % CHECKPOINT_EVERY == 0:
            self.conn.execute("CHECKPOINT")
        if self.writes >= RECONNECT_EVERY:
            self._reconnect()

    def close(self):
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass
        del self.conn
        del self.db


def main():
    t0 = time.time()

    with open(DATA_PATH) as f:
        data = json.load(f)
    log.info("Loaded %d items from 12366_hotspot.json", len(data))

    sdb = SafeDB()

    # Check existing 12366 KU count
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.source = '12366_hotspot' RETURN count(k)")
    existing = r.get_next()[0]
    log.info("Existing 12366_hotspot KU: %d", existing)

    # Build set of existing IDs
    existing_ids = set()
    if existing > 0:
        r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.source = '12366_hotspot' RETURN k.id")
        while r.has_next():
            existing_ids.add(str(r.get_next()[0]))
    log.info("Existing IDs loaded: %d", len(existing_ids))

    created = 0
    updated = 0
    skipped = 0

    for i, item in enumerate(data):
        node_id = f"KU_12366_{item.get('id', '')}"
        title = (item.get("question", "") or item.get("title", ""))[:200]
        answer = item.get("answer", "") or ""
        content = item.get("content", "") or f"Q: {title}\nA: {answer}"
        content = content[:MAX_CONTENT]
        category = item.get("category", "")
        source_url = item.get("url", "")
        date_str = item.get("date", "")

        if len(title) < 5 or len(content) < MIN_CONTENT:
            skipped += 1
            continue

        if node_id in existing_ids:
            # Update content if better
            try:
                r = sdb.conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                    {"id": node_id}
                )
                if r.has_next() and r.get_next()[0] < len(content):
                    sdb.conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                        {"id": node_id, "c": content}
                    )
                    sdb._post_write()
                    updated += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
        else:
            # Create new node (only use columns that exist in KnowledgeUnit table)
            try:
                sdb.conn.execute(
                    "CREATE (k:KnowledgeUnit {id: $id, title: $t, content: $c, source: $s})",
                    {"id": node_id, "t": title, "c": content, "s": "12366_hotspot"}
                )
                sdb._post_write()
                created += 1
            except Exception as e:
                if created == 0 and skipped < 3:
                    log.warning("  CREATE failed: %s", str(e)[:200])
                skipped += 1

        if (i + 1) % 1000 == 0:
            log.info("  Progress: %d/%d, created=%d, updated=%d, skipped=%d",
                     i + 1, len(data), created, updated, skipped)

    # Create tax edges for new KU
    if created > 0:
        log.info("\nCreating KU_ABOUT_TAX edges for new nodes...")
        tax_keywords = {
            "增值税": None, "企业所得税": None, "个人所得税": None,
            "消费税": None, "关税": None, "房产税": None, "印花税": None,
            "土地增值税": None, "契税": None, "车辆购置税": None,
            "车船税": None, "资源税": None, "环境保护税": None,
            "城市维护建设税": None, "教育费附加": None,
            "耕地占用税": None, "城镇土地使用税": None,
        }
        # Map keywords to TaxType IDs
        r = sdb.conn.execute("MATCH (t:TaxType) RETURN t.id, t.name")
        while r.has_next():
            row = r.get_next()
            tid, tname = str(row[0]), str(row[1])
            for kw in tax_keywords:
                if kw in tname or tname in kw:
                    tax_keywords[kw] = tid

        edge_count = 0
        for item in data:
            node_id = f"KU_12366_{item.get('id', '')}"
            content = item.get("content", "") or item.get("answer", "") or ""
            title = item.get("question", "") or item.get("title", "") or ""
            text = title + " " + content

            for kw, tid in tax_keywords.items():
                if tid and kw in text:
                    try:
                        # Check if edge exists
                        r = sdb.conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $kid})-[:KU_ABOUT_TAX]->(t:TaxType {id: $tid}) RETURN count(*)",
                            {"kid": node_id, "tid": tid}
                        )
                        if r.has_next() and r.get_next()[0] == 0:
                            sdb.conn.execute(
                                "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType {id: $tid}) CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                                {"kid": node_id, "tid": tid}
                            )
                            sdb._post_write()
                            edge_count += 1
                    except Exception:
                        pass

        log.info("  Created %d KU_ABOUT_TAX edges", edge_count)

    # Final
    sdb.conn.execute("CHECKPOINT")

    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    ku_good = r.get_next()[0]
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    ku_total = r.get_next()[0]

    elapsed = time.time() - t0
    log.info("\n" + "=" * 60)
    log.info("12366 Ingest complete (%.0fs)", elapsed)
    log.info("  Created: %d | Updated: %d | Skipped: %d", created, updated, skipped)
    log.info("  KU coverage: %d/%d (%.1f%%)", ku_good, ku_total, 100 * ku_good / ku_total)

    sdb.close()


if __name__ == "__main__":
    main()
