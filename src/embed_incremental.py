#!/usr/bin/env python3
"""Incremental embedding: add new KU nodes to existing LanceDB index.

Reads: data/ku_embed_incremental.jsonl (exported from VPS)
Writes: data/lancedb-build/kg_nodes (appends to existing table)

Skips IDs already in the LanceDB table. Uses local Gemini API key.

Usage:
    python3 src/embed_incremental.py
    python3 src/embed_incremental.py --limit 500
"""
import json, logging, os, sys, time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("embed_incr")

EMBEDDING_DIM = 768
MODEL = "gemini-embedding-2-preview"
TABLE_NAME = "kg_nodes"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "data", "ku_embed_incremental.jsonl")
LANCE_DIR = os.path.join(BASE, "data", "lancedb-build")
CHECKPOINT = os.path.join(BASE, "data", "embed_incr_checkpoint.json")


def get_api_key():
    for p in [os.path.expanduser("~/.openclaw/.env"), ".env"]:
        if os.path.exists(p):
            for line in open(p):
                if line.strip().startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1]
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    raise RuntimeError("GEMINI_API_KEY not found")


def embed_one(text, api_key, client):
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:embedContent"
    body = {
        "model": f"models/{MODEL}",
        "content": {"parts": [{"text": text[:8000]}]},
        "taskType": "RETRIEVAL_DOCUMENT",
        "outputDimensionality": EMBEDDING_DIM,
    }
    for attempt in range(5):
        try:
            resp = client.post(f"{url}?key={api_key}", json=body, timeout=30)
            if resp.status_code == 429:
                wait = min(2 ** attempt + 1, 30)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["embedding"]["values"]
        except Exception as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
            else:
                log.error("Embed failed: %s", str(e)[:80])
                return None
    return None


def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {"done_ids": [], "count": 0}


def save_checkpoint(state):
    with open(CHECKPOINT, "w") as f:
        json.dump(state, f)


def main():
    import httpx
    import lancedb

    limit = None
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    api_key = get_api_key()
    log.info("API key: %s...", api_key[:15])

    docs = []
    with open(INPUT) as f:
        for line in f:
            docs.append(json.loads(line))
    log.info("Loaded %d docs from incremental export", len(docs))

    lance_db = lancedb.connect(LANCE_DIR)
    tbl = lance_db.open_table(TABLE_NAME)
    existing_count = tbl.count_rows()
    log.info("Existing LanceDB: %d rows", existing_count)

    existing_ids = set(tbl.to_arrow().column("id").to_pylist())
    log.info("Existing IDs: %d", len(existing_ids))

    ckpt = load_checkpoint()
    done_ids = set(ckpt.get("done_ids", []))
    log.info("Checkpoint: %d already done this run", len(done_ids))

    pending = [d for d in docs if d["id"] not in existing_ids and d["id"] not in done_ids]
    if limit:
        pending = pending[:limit]
    log.info("Pending: %d new docs to embed", len(pending))

    if not pending:
        log.info("Nothing new to embed!")
        return

    client = httpx.Client()
    records = []
    t0 = time.time()
    batch_size = 500
    failed = 0
    embedded = 0

    for i, doc in enumerate(pending):
        vec = embed_one(doc["embed_text"], api_key, client)
        if vec is None:
            failed += 1
            if failed > 50:
                log.error("Too many failures (%d), stopping", failed)
                break
            continue

        records.append({
            "id": doc["id"],
            "title": doc["title"],
            "node_type": doc["node_type"],
            "source": doc["source"],
            "vector": vec,
        })
        done_ids.add(doc["id"])
        embedded += 1

        if len(records) >= batch_size:
            tbl.add(records)
            save_checkpoint({"done_ids": list(done_ids), "count": embedded + ckpt.get("count", 0)})
            elapsed = time.time() - t0
            rate = embedded / elapsed
            eta = (len(pending) - i - 1) / rate / 60 if rate > 0 else 0
            log.info("Batch: +%d vectors (total %d, %.1f/s, ETA %.0f min, %d failed)",
                     len(records), embedded, rate, eta, failed)
            records = []

    if records:
        tbl.add(records)
        save_checkpoint({"done_ids": list(done_ids), "count": embedded + ckpt.get("count", 0)})

    client.close()
    elapsed = time.time() - t0

    final_count = tbl.count_rows()
    log.info("=" * 60)
    log.info("DONE: +%d vectors in %.1f min (%.1f/s)", embedded, elapsed / 60, embedded / elapsed if elapsed > 0 else 0)
    log.info("Total in LanceDB: %d vectors", final_count)
    log.info("Failed: %d", failed)
    log.info("Next: bash scripts/sync_lancedb_to_vps.sh")


if __name__ == "__main__":
    main()
