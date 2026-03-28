#!/usr/bin/env python3
"""Batch ingest for Session 10 — all completed crawl data.

Sources (in order):
1. chinatax_fulltext_v3.jsonl  — 4,966 items, upsert KU by title match + create new
2. flk_npc_laws.jsonl          — 2,901 items, metadata-only LawOrRegulation
3. mof_fulltext.json           — 926 items, KU with content (filter 502 errors)
4. ndrc_fulltext.json          — 858 items, KU with content
5. baike_fulltext.json         — 8,011 items, KU with content
6. lr_cleanup shards 0-3       — 15,781 items, update existing KU content by ID

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/batch_ingest_session10.py 2>&1 | tee /tmp/batch_ingest_s10.log
    sudo systemctl start kg-api
"""
import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch_ingest")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
BASE = "/home/kg/cognebula-enterprise"
CHECKPOINT_EVERY = 100


def load_jsonl(path):
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return items


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_db():
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    return db, conn


def graph_stats(conn):
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    return nodes, edges


def checkpoint(conn, writes):
    if writes > 0 and writes % CHECKPOINT_EVERY == 0:
        conn.execute("CHECKPOINT")


# ── 1. chinatax_fulltext_v3 ─────────────────────────────────────
def ingest_chinatax_v3(conn):
    path = f"{BASE}/data/recrawl/chinatax_fulltext_v3.jsonl"
    if not os.path.exists(path):
        log.warning("SKIP chinatax_v3: file not found")
        return
    items = load_jsonl(path)
    log.info("[chinatax_v3] Loaded %d items", len(items))

    updated = 0
    created = 0
    skipped = 0
    writes = 0

    for i, item in enumerate(items):
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        item_id = item.get("id", "")

        if len(title) < 2:
            skipped += 1
            continue

        # Try update existing KU by title match
        if len(content) >= 100:
            try:
                r = conn.execute(
                    "MATCH (k:KnowledgeUnit) WHERE k.title = $t "
                    "RETURN k.id, CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END LIMIT 1",
                    {"t": title},
                )
                if r.has_next():
                    row = r.get_next()
                    kid, existing_len = str(row[0]), row[1]
                    if existing_len < len(content):
                        conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                            {"id": kid, "c": content[:50000]},
                        )
                        updated += 1
                        writes += 1
                        checkpoint(conn, writes)
                        continue
                    else:
                        skipped += 1
                        continue
            except Exception:
                pass

        # Create new KU if not matched
        if item_id and len(title) >= 2:
            try:
                r = conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": item_id}
                )
                if r.has_next():
                    skipped += 1
                    continue
            except Exception:
                pass

            try:
                conn.execute(
                    "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, "
                    "source: $source, type: $tp})",
                    {
                        "id": item_id,
                        "title": title[:500],
                        "content": content[:50000] if content else "",
                        "source": "chinatax_fgk",
                        "tp": item.get("channel", "chinatax"),
                    },
                )
                created += 1
                writes += 1
                checkpoint(conn, writes)
            except Exception as e:
                if created < 3:
                    log.warning("  create err: %s", str(e)[:100])

        if (i + 1) % 500 == 0:
            log.info("  %d/%d: updated=%d created=%d skipped=%d", i + 1, len(items), updated, created, skipped)

    conn.execute("CHECKPOINT")
    log.info("[chinatax_v3] DONE: updated=%d created=%d skipped=%d", updated, created, skipped)


# ── 2. flk_npc (metadata-only) ──────────────────────────────────
def ingest_flk_npc(conn):
    path = f"{BASE}/data/recrawl/flk_npc_laws.jsonl"
    if not os.path.exists(path):
        log.warning("SKIP flk_npc: file not found")
        return
    items = load_jsonl(path)
    log.info("[flk_npc] Loaded %d items (metadata-only)", len(items))

    inserted = 0
    skipped = 0
    writes = 0

    for i, item in enumerate(items):
        bbbs = item.get("bbbs", "")
        title = (item.get("title") or "").strip()
        if not bbbs or len(title) < 2:
            skipped += 1
            continue

        node_id = f"FLK_{bbbs[:16]}"

        # Dedup
        try:
            r = conn.execute(
                "MATCH (n:LawOrRegulation {id: $id}) RETURN n.id", {"id": node_id}
            )
            if r.has_next():
                skipped += 1
                continue
        except Exception:
            pass

        # Also dedup by title
        try:
            r = conn.execute(
                "MATCH (n:LawOrRegulation) WHERE n.title = $t RETURN n.id LIMIT 1",
                {"t": title},
            )
            if r.has_next():
                skipped += 1
                continue
        except Exception:
            pass

        try:
            conn.execute(
                "CREATE (n:LawOrRegulation {"
                "id: $id, title: $title, fullText: $ft, "
                "sourceUrl: $url, regulationType: $rtype, "
                "issuingAuthority: $auth, status: $status})",
                {
                    "id": node_id,
                    "title": title[:500],
                    "ft": f"[{item.get('flxz', '')}] {title} ({item.get('gbrq', '')})",
                    "url": f"https://flk.npc.gov.cn/detail2.html?ZmY={bbbs}",
                    "rtype": item.get("flxz", "unknown")[:100],
                    "auth": item.get("zdjgName", "")[:200],
                    "status": "active",
                },
            )
            inserted += 1
            writes += 1
            checkpoint(conn, writes)
        except Exception as e:
            if inserted < 3:
                log.warning("  flk create err: %s", str(e)[:100])

        if (i + 1) % 500 == 0:
            log.info("  %d/%d: inserted=%d skipped=%d", i + 1, len(items), inserted, skipped)

    conn.execute("CHECKPOINT")
    log.info("[flk_npc] DONE: inserted=%d skipped=%d", inserted, skipped)


# ── 3/4/5. Generic JSON ingest (mof, ndrc, baike) ───────────────
def ingest_json_source(conn, json_path, source_name, min_content=50):
    if not os.path.exists(json_path):
        log.warning("SKIP %s: file not found", source_name)
        return
    items = load_json(json_path)
    log.info("[%s] Loaded %d items", source_name, len(items))

    inserted = 0
    updated = 0
    skipped = 0
    writes = 0

    for i, item in enumerate(items):
        item_id = item.get("id", "")
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()

        if not item_id or len(title) < 2:
            skipped += 1
            continue

        # Filter 502/error content
        if content[:10].startswith("502") or "Bad Gateway" in content[:50]:
            skipped += 1
            continue

        if len(content) < min_content:
            skipped += 1
            continue

        # Check existing
        try:
            r = conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id, "
                "CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                {"id": item_id},
            )
            if r.has_next():
                row = r.get_next()
                existing_len = row[1]
                if existing_len < len(content):
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                        {"id": item_id, "c": content[:50000]},
                    )
                    updated += 1
                    writes += 1
                    checkpoint(conn, writes)
                else:
                    skipped += 1
                continue
        except Exception:
            pass

        # Create new
        try:
            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, "
                "source: $source, type: $tp})",
                {
                    "id": item_id,
                    "title": title[:500],
                    "content": content[:50000],
                    "source": source_name,
                    "tp": item.get("type", source_name),
                },
            )
            inserted += 1
            writes += 1
            checkpoint(conn, writes)
        except Exception as e:
            if inserted < 3:
                log.warning("  %s create err: %s", source_name, str(e)[:100])

        if (i + 1) % 500 == 0:
            log.info("  %d/%d: inserted=%d updated=%d skipped=%d", i + 1, len(items), inserted, updated, skipped)

    conn.execute("CHECKPOINT")
    log.info("[%s] DONE: inserted=%d updated=%d skipped=%d", source_name, inserted, updated, skipped)


# ── 6. LR cleanup shards (update existing KU content by ID) ─────
def ingest_lr_shards(conn):
    updated = 0
    not_found = 0
    skipped = 0
    writes = 0
    total = 0

    for shard in range(4):
        path = f"{BASE}/data/backfill/lr_cleanup_content_shard{shard}.jsonl"
        if not os.path.exists(path):
            log.warning("SKIP lr_shard%d: file not found", shard)
            continue
        items = load_jsonl(path)
        log.info("[lr_shard%d] Loaded %d items", shard, len(items))

        for i, item in enumerate(items):
            total += 1
            ku_id = item.get("id", "")
            content = (item.get("content") or item.get("lr_content") or "").strip()

            if not ku_id or len(content) < 100:
                skipped += 1
                continue

            try:
                r = conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) "
                    "RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                    {"id": ku_id},
                )
                if r.has_next():
                    existing_len = r.get_next()[0]
                    if existing_len < len(content):
                        conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                            {"id": ku_id, "c": content[:50000]},
                        )
                        updated += 1
                        writes += 1
                        checkpoint(conn, writes)
                    else:
                        skipped += 1
                else:
                    not_found += 1
            except Exception as e:
                if updated < 3:
                    log.warning("  lr update err: %s", str(e)[:100])

            if total % 1000 == 0:
                log.info("  lr total %d: updated=%d not_found=%d skipped=%d", total, updated, not_found, skipped)

        conn.execute("CHECKPOINT")

    log.info("[lr_shards] DONE: total=%d updated=%d not_found=%d skipped=%d", total, updated, not_found, skipped)


# ── Main ─────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("Session 10 Batch Ingest — starting")
    log.info("=" * 60)

    db, conn = get_db()
    nodes_before, edges_before = graph_stats(conn)
    log.info("BEFORE: %s nodes / %s edges / density %.3f",
             f"{nodes_before:,}", f"{edges_before:,}", edges_before / nodes_before)

    t0 = time.time()

    # 1. chinatax fulltext v3
    ingest_chinatax_v3(conn)

    # 2. flk_npc (metadata-only laws)
    ingest_flk_npc(conn)

    # 3. mof
    ingest_json_source(conn, f"{BASE}/data/recrawl/mof_fulltext.json", "mof")

    # 4. ndrc
    ingest_json_source(conn, f"{BASE}/data/recrawl/ndrc_fulltext.json", "ndrc")

    # 5. baike
    ingest_json_source(conn, f"{BASE}/data/recrawl/baike_fulltext.json", "baike_kuaiji")

    # 6. LR cleanup shards
    ingest_lr_shards(conn)

    nodes_after, edges_after = graph_stats(conn)
    elapsed = time.time() - t0

    log.info("=" * 60)
    log.info("AFTER: %s nodes / %s edges / density %.3f",
             f"{nodes_after:,}", f"{edges_after:,}", edges_after / nodes_after)
    log.info("DELTA: +%d nodes / +%d edges / %.0fs elapsed",
             nodes_after - nodes_before, edges_after - edges_before, elapsed)
    log.info("=" * 60)

    del conn
    del db


if __name__ == "__main__":
    main()
