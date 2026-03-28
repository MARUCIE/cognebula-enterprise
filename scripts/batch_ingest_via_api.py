#!/usr/bin/env python3
"""Batch ingest via HTTP API — no DB lock, no API restart needed.

Uses:
  - POST /api/v1/ingest         for new node creation
  - POST /api/v1/admin/execute-ddl  for content updates (MATCH...SET)

Run from Mac or VPS:
    python3 scripts/batch_ingest_via_api.py [--host 100.88.170.57]
"""
import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api_ingest")

# Run from VPS: files are local. Run from Mac: files via SSH.
BASE = "/home/kg/cognebula-enterprise"


def api_post(host, path, data, timeout=30):
    url = f"http://{host}:8400{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()[:200]}
    except Exception as e:
        return {"error": str(e)[:200]}


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


def escape_cypher(s):
    """Escape string for inline Cypher (single quotes)."""
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")


# ── New KU node creation via execute-ddl ─────────────────────────
def ingest_new_ku_nodes(host, items, source, batch_size=20):
    """Create new KnowledgeUnit nodes via DDL CREATE statements.

    KnowledgeUnit columns: id, title, content, source, type.
    Dedup: skip if id already exists.
    """
    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        stmts = []
        for item in batch:
            item_id = item.get("id", "")
            title = (item.get("title") or "").strip()
            content = (item.get("content") or "").strip()

            if not item_id or len(title) < 2:
                total_skipped += 1
                continue
            # Filter 502 error content
            if content[:10].startswith("502") or "Bad Gateway" in content[:50]:
                total_skipped += 1
                continue

            eid = escape_cypher(item_id)
            et = escape_cypher(title[:500])
            ec = escape_cypher(content[:5000])
            es = escape_cypher(source)
            etp = escape_cypher(item.get("type", source)[:100])

            # CREATE with dedup via MERGE-like pattern
            # Use CREATE only — dedup check separately
            stmts.append((eid, f"CREATE (k:KnowledgeUnit {{id: '{eid}', title: '{et}', content: '{ec}', source: '{es}', type: '{etp}'}})"))

        for eid, create_stmt in stmts:
            # Dedup check
            check = f"MATCH (k:KnowledgeUnit {{id: '{eid}'}}) RETURN count(k)"
            result = api_post(host, "/api/v1/admin/execute-ddl", {"statements": [check]}, timeout=10)
            # execute-ddl doesn't return query results, so just try creating
            result = api_post(host, "/api/v1/admin/execute-ddl", {"statements": [create_stmt]}, timeout=10)
            if "error" in result:
                total_errors += 1
            else:
                results = result.get("results", [{}])
                if results and results[0].get("status") == "OK":
                    total_inserted += 1
                elif "already exists" in str(results).lower() or "duplicate" in str(results).lower():
                    total_skipped += 1
                else:
                    # Might be a duplicate key error — count as skip
                    err_str = str(results)
                    if "exists" in err_str.lower() or "violat" in err_str.lower():
                        total_skipped += 1
                    else:
                        total_errors += 1
                        if total_errors <= 3:
                            log.warning("  DDL create err: %s", err_str[:150])

        if (start + batch_size) % 500 == 0 or start + batch_size >= len(items):
            log.info("  %d/%d: +%d new, %d skip, %d err",
                     min(start + batch_size, len(items)), len(items),
                     total_inserted, total_skipped, total_errors)

    return total_inserted, total_skipped, total_errors


# ── Content update via execute-ddl ───────────────────────────────
def update_content_batch(host, items, table="KnowledgeUnit"):
    """Update existing nodes' content via MATCH...SET through execute-ddl."""
    updated = 0
    failed = 0
    skipped = 0

    for i, item in enumerate(items):
        node_id = item.get("id", "")
        content = (item.get("content") or item.get("lr_content") or "").strip()

        if not node_id or len(content) < 100:
            skipped += 1
            continue

        # Truncate for Cypher inline (max 5000 chars to avoid URL length issues)
        content_escaped = escape_cypher(content[:5000])

        stmt = (
            f"MATCH (k:{table} {{id: '{escape_cypher(node_id)}'}}) "
            f"SET k.content = '{content_escaped}'"
        )

        result = api_post(host, "/api/v1/admin/execute-ddl", {"statements": [stmt]}, timeout=15)
        if "error" in result:
            failed += 1
            if failed <= 3:
                log.warning("  DDL error for %s: %s", node_id[:20], str(result)[:100])
        else:
            results = result.get("results", [{}])
            if results and results[0].get("status") == "OK":
                updated += 1
            else:
                failed += 1
                if failed <= 3:
                    log.warning("  DDL fail for %s: %s", node_id[:20], str(results)[:100])

        if (i + 1) % 500 == 0:
            log.info("  %d/%d: updated=%d failed=%d skipped=%d", i + 1, len(items), updated, failed, skipped)

    return updated, failed, skipped


# ── FLK NPC (metadata-only LawOrRegulation) via DDL ──────────────
def ingest_flk_npc(host, items):
    """Create FLK NPC laws as LawOrRegulation nodes via DDL CREATE."""
    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    for i, item in enumerate(items):
        bbbs = item.get("bbbs", "")
        title = (item.get("title") or "").strip()
        if not bbbs or len(title) < 2:
            total_skipped += 1
            continue

        node_id = f"FLK_{bbbs[:16]}"
        eid = escape_cypher(node_id)
        et = escape_cypher(title[:500])
        ft = escape_cypher(f"[{item.get('flxz', '')}] {title} ({item.get('gbrq', '')})")
        eurl = escape_cypher(f"https://flk.npc.gov.cn/detail2.html?ZmY={bbbs}")
        ertype = escape_cypher(item.get("flxz", "unknown")[:100])
        eauth = escape_cypher(item.get("zdjgName", "")[:200])

        stmt = (
            f"CREATE (n:LawOrRegulation {{id: '{eid}', title: '{et}', "
            f"fullText: '{ft}', sourceUrl: '{eurl}', "
            f"regulationType: '{ertype}', issuingAuthority: '{eauth}', status: 'active'}})"
        )

        result = api_post(host, "/api/v1/admin/execute-ddl", {"statements": [stmt]}, timeout=10)
        if "error" in result:
            total_errors += 1
        else:
            results = result.get("results", [{}])
            if results and results[0].get("status") == "OK":
                total_inserted += 1
            else:
                err_str = str(results)
                if "exists" in err_str.lower() or "duplicate" in err_str.lower() or "violat" in err_str.lower():
                    total_skipped += 1
                else:
                    total_errors += 1
                    if total_errors <= 3:
                        log.warning("  flk DDL err: %s", err_str[:150])

        if (i + 1) % 300 == 0:
            log.info("  flk %d/%d: +%d new, %d skip, %d err",
                     i + 1, len(items), total_inserted, total_skipped, total_errors)

    return total_inserted, total_skipped, total_errors


# ── Main ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="100.88.170.57", help="KG API host")
    parser.add_argument("--skip-lr", action="store_true", help="Skip LR shard updates")
    parser.add_argument("--only", choices=["chinatax", "flk", "mof", "ndrc", "baike", "lr"], help="Only run one source")
    args = parser.parse_args()
    host = args.host

    # Health check
    log.info("=" * 60)
    log.info("Session 10 Batch Ingest via API — %s", host)
    log.info("=" * 60)

    result = api_post(host, "/api/v1/quality", {})
    if "error" in result:
        # Try GET
        try:
            url = f"http://{host}:8400/api/v1/quality"
            with urllib.request.urlopen(url, timeout=10) as resp:
                result = json.loads(resp.read())
        except Exception:
            log.error("API not reachable at %s:8400", host)
            sys.exit(1)

    metrics = result.get("metrics", {})
    log.info("BEFORE: %s nodes / %s edges / score %s",
             f"{metrics.get('total_nodes', '?'):,}" if isinstance(metrics.get('total_nodes'), int) else metrics.get('total_nodes', '?'),
             f"{metrics.get('total_edges', '?'):,}" if isinstance(metrics.get('total_edges'), int) else metrics.get('total_edges', '?'),
             metrics.get("quality_score", "?"))

    t0 = time.time()
    sources_done = []

    # 1. chinatax_fulltext_v3
    if not args.only or args.only == "chinatax":
        path = f"{BASE}/data/recrawl/chinatax_fulltext_v3.jsonl"
        if os.path.exists(path):
            items = load_jsonl(path)
            log.info("[chinatax_v3] %d items — creating new KnowledgeUnit nodes", len(items))
            ins, skip, err = ingest_new_ku_nodes(host, items, "chinatax_fgk")
            log.info("[chinatax_v3] DONE: +%d new, %d skipped, %d errors", ins, skip, err)
            sources_done.append(f"chinatax_v3: +{ins}")

    # 2. flk_npc (metadata-only)
    if not args.only or args.only == "flk":
        path = f"{BASE}/data/recrawl/flk_npc_laws.jsonl"
        if os.path.exists(path):
            items = load_jsonl(path)
            log.info("[flk_npc] %d items — creating LawOrRegulation nodes (metadata)", len(items))
            ins, skip, err = ingest_flk_npc(host, items)
            log.info("[flk_npc] DONE: +%d new, %d skipped, %d errors", ins, skip, err)
            sources_done.append(f"flk_npc: +{ins}")

    # 3. mof
    if not args.only or args.only == "mof":
        path = f"{BASE}/data/recrawl/mof_fulltext.json"
        if os.path.exists(path):
            items = load_json(path)
            log.info("[mof] %d items — creating new KnowledgeUnit nodes", len(items))
            ins, skip, err = ingest_new_ku_nodes(host, items, "mof")
            log.info("[mof] DONE: +%d new, %d skipped, %d errors", ins, skip, err)
            sources_done.append(f"mof: +{ins}")

    # 4. ndrc
    if not args.only or args.only == "ndrc":
        path = f"{BASE}/data/recrawl/ndrc_fulltext.json"
        if os.path.exists(path):
            items = load_json(path)
            log.info("[ndrc] %d items — creating new KnowledgeUnit nodes", len(items))
            ins, skip, err = ingest_new_ku_nodes(host, items, "ndrc")
            log.info("[ndrc] DONE: +%d new, %d skipped, %d errors", ins, skip, err)
            sources_done.append(f"ndrc: +{ins}")

    # 5. baike
    if not args.only or args.only == "baike":
        path = f"{BASE}/data/recrawl/baike_fulltext.json"
        if os.path.exists(path):
            items = load_json(path)
            log.info("[baike] %d items — creating new KnowledgeUnit nodes", len(items))
            ins, skip, err = ingest_new_ku_nodes(host, items, "baike_kuaiji")
            log.info("[baike] DONE: +%d new, %d skipped, %d errors", ins, skip, err)
            sources_done.append(f"baike: +{ins}")

    # 6. LR shards (content update)
    if not args.skip_lr and (not args.only or args.only == "lr"):
        total_updated = 0
        total_failed = 0
        total_skipped = 0
        for shard in range(4):
            path = f"{BASE}/data/backfill/lr_cleanup_content_shard{shard}.jsonl"
            if not os.path.exists(path):
                log.warning("SKIP lr_shard%d: not found", shard)
                continue
            items = load_jsonl(path)
            log.info("[lr_shard%d] %d items — updating KU content via DDL", shard, len(items))
            upd, fail, skip = update_content_batch(host, items)
            log.info("[lr_shard%d] DONE: updated=%d failed=%d skipped=%d", shard, upd, fail, skip)
            total_updated += upd
            total_failed += fail
            total_skipped += skip
        sources_done.append(f"lr_shards: +{total_updated} updated")

    elapsed = time.time() - t0

    # Final stats
    log.info("=" * 60)
    try:
        url = f"http://{host}:8400/api/v1/quality"
        with urllib.request.urlopen(url, timeout=10) as resp:
            result = json.loads(resp.read())
        metrics = result.get("metrics", {})
        log.info("AFTER: %s nodes / %s edges / score %s",
                 f"{metrics.get('total_nodes', '?'):,}" if isinstance(metrics.get('total_nodes'), int) else metrics.get('total_nodes', '?'),
                 f"{metrics.get('total_edges', '?'):,}" if isinstance(metrics.get('total_edges'), int) else metrics.get('total_edges', '?'),
                 metrics.get("quality_score", "?"))
    except Exception:
        log.warning("Could not fetch final stats")
    log.info("Sources: %s", " | ".join(sources_done))
    log.info("Elapsed: %.0fs", elapsed)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
