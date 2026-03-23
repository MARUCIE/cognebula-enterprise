#!/usr/bin/env python3
"""Wave 3 KU content restore — chinatax + doc-tax + remaining sources.

Sources:
1. chinatax_api.json variants (4,580 unique items with content>=100c)
   - Match by title to existing KU nodes
2. all_mindmap_nodes.json (14K items) — update KU by title if sourced from mindmap
3. doc-tax PDF extracts — check for usable content

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/restore_ku_wave3.py 2>&1 | tee /tmp/restore_wave3.log
    sudo systemctl start kg-api
"""
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("wave3")

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

    def _post_write(self):
        self.writes += 1
        self.total_writes += 1
        if self.writes % CHECKPOINT_EVERY == 0:
            self.conn.execute("CHECKPOINT")
        if self.writes >= RECONNECT_EVERY:
            self._reconnect()

    def safe_set_ku_content(self, node_id, content):
        """SET content on KU only if new content > existing."""
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
            self._post_write()
            return True
        except Exception:
            self.skipped += 1
            return False

    def find_ku_by_title(self, title):
        """Find KU node ID by exact title match."""
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

    def find_ku_by_title_contains(self, title_fragment):
        """Find KU by title CONTAINS (for partial matches)."""
        try:
            r = self.conn.execute(
                "MATCH (k:KnowledgeUnit) WHERE contains(k.title, $t) RETURN k.id LIMIT 1",
                {"t": title_fragment}
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


def restore_chinatax(sdb):
    """Restore chinatax content by matching title to existing KU."""
    # Merge all chinatax files, keep longest content per ID
    files = [
        os.path.join(DATA_DIR, "raw/chinatax-full/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/20260315-fgk-deep/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/2026-03-15-fgk-10k/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/2026-03-15-fgk-extra/chinatax_api.json"),
    ]

    # Deduplicate by title, keep longest content
    by_title = {}
    for fpath in files:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)
        for item in data:
            title = (item.get("title", "") or "").strip()
            content = item.get("content", "") or ""
            if len(title) >= 5 and len(content) >= MIN_CONTENT:
                if title not in by_title or len(content) > len(by_title[title]):
                    by_title[title] = content

    log.info("  Unique chinatax titles with content>=100c: %d", len(by_title))

    updated = 0
    not_found = 0
    for i, (title, content) in enumerate(by_title.items()):
        kid = sdb.find_ku_by_title(title)
        if kid:
            if sdb.safe_set_ku_content(kid, content):
                updated += 1
        else:
            not_found += 1

        if (i + 1) % 1000 == 0:
            log.info("  chinatax: %d/%d processed, %d updated, %d not found",
                     i + 1, len(by_title), updated, not_found)

    log.info("  chinatax DONE: %d updated, %d not found, %d skipped",
             updated, not_found, sdb.skipped)
    return updated


def restore_chinatax_by_id(sdb):
    """Also try matching by original chinatax ID embedded in KU id."""
    files = [
        os.path.join(DATA_DIR, "raw/chinatax-full/chinatax_api.json"),
    ]

    by_id = {}
    for fpath in files:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)
        for item in data:
            iid = item.get("id", "")
            content = item.get("content", "") or ""
            if iid and len(content) >= MIN_CONTENT:
                # Try multiple ID formats
                for prefix in ["KU_chinatax_", "KU_fgk_", "chinatax_"]:
                    by_id[prefix + iid] = content

    updated = 0
    for i, (node_id, content) in enumerate(by_id.items()):
        if sdb.safe_set_ku_content(node_id, content):
            updated += 1
        if (i + 1) % 5000 == 0:
            log.info("  chinatax-by-id: %d/%d processed, %d updated",
                     i + 1, len(by_id), updated)

    log.info("  chinatax-by-id DONE: %d updated / %d tried", updated, len(by_id))
    return updated


def restore_extracted_json(sdb):
    """Try to restore from other extracted JSON files."""
    extracted_dir = os.path.join(DATA_DIR, "extracted")
    if not os.path.isdir(extracted_dir):
        return 0

    updated = 0
    for root, dirs, files in os.walk(extracted_dir):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            if "mindmap" in root:
                continue  # Already handled

            fpath = os.path.join(root, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    continue
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title", "") or item.get("name", "") or ""
                    content = item.get("content", "") or item.get("description", "") or item.get("text", "") or ""
                    node_id = item.get("id", "")

                    if len(content) < MIN_CONTENT:
                        continue

                    if node_id:
                        if sdb.safe_set_ku_content(node_id, content):
                            updated += 1
                    elif len(title) >= 5:
                        kid = sdb.find_ku_by_title(title)
                        if kid and sdb.safe_set_ku_content(kid, content):
                            updated += 1
            except Exception:
                pass

    log.info("  extracted DONE: %d updated", updated)
    return updated


def restore_cctaa(sdb):
    """Restore from CCTAA (Chinese CPA association) data if available."""
    path = os.path.join(DATA_DIR, "raw", "20260315-cctaa", "cctaa_standards.json")
    if not os.path.exists(path):
        # Try alternative paths
        for alt in ["cctaa_all.json", "cctaa.json"]:
            alt_path = os.path.join(DATA_DIR, "raw", "20260315-cctaa", alt)
            if os.path.exists(alt_path):
                path = alt_path
                break
        else:
            log.info("  cctaa: no data file found")
            return 0

    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        return 0

    updated = 0
    for item in data:
        title = item.get("title", "") or ""
        content = item.get("content", "") or item.get("fullText", "") or ""
        if len(content) < MIN_CONTENT or len(title) < 5:
            continue
        kid = sdb.find_ku_by_title(title)
        if kid and sdb.safe_set_ku_content(kid, content):
            updated += 1

    log.info("  cctaa DONE: %d updated / %d items", updated, len(data))
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

    log.info("\n[1/4] chinatax by title match...")
    sdb.skipped = 0
    results["chinatax_title"] = restore_chinatax(sdb)

    log.info("\n[2/4] chinatax by ID match...")
    sdb.skipped = 0
    results["chinatax_id"] = restore_chinatax_by_id(sdb)

    log.info("\n[3/4] extracted JSON files...")
    sdb.skipped = 0
    results["extracted"] = restore_extracted_json(sdb)

    log.info("\n[4/4] CCTAA data...")
    sdb.skipped = 0
    results["cctaa"] = restore_cctaa(sdb)

    # Final
    sdb.conn.execute("CHECKPOINT")
    r = sdb.conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    after = r.get_next()[0]

    elapsed = time.time() - t0
    log.info("\n" + "=" * 60)
    log.info("Wave 3 complete (%.0fs)", elapsed)
    for source, count in results.items():
        log.info("  %s: +%d", source, count)
    log.info("  Total writes: %d", sdb.total_writes)
    log.info("  KU coverage: %d/%d (%.1f%%) — was %.1f%%",
             after, total_ku, 100 * after / total_ku, 100 * before / total_ku)
    log.info("  Delta: %+d KU with content", after - before)

    sdb.close()


if __name__ == "__main__":
    main()
