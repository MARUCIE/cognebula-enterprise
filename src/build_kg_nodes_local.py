#!/usr/bin/env python3
"""Build LanceDB kg_nodes index locally from exported JSONL.

Reads: data/kg_embed_export.jsonl (exported from VPS kuzu)
Writes: data/lancedb-build/kg_nodes (LanceDB table, sync to VPS after)

Uses local Gemini API key (Mac, not VPS — VPS key is rate limited).

Usage:
    python3 src/build_kg_nodes_local.py
    python3 src/build_kg_nodes_local.py --limit 100
"""
import json, logging, os, sys, time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_local")

EMBEDDING_DIM = 768
MODEL = "gemini-embedding-2-preview"
TABLE_NAME = "kg_nodes"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "data", "kg_embed_export.jsonl")
LANCE_DIR = os.path.join(BASE, "data", "lancedb-build")
CHECKPOINT = os.path.join(BASE, "data", "embed_checkpoint.json")


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
    return {"embedded_count": 0, "done_ids": []}


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

    # Load export
    docs = []
    with open(INPUT) as f:
        for line in f:
            docs.append(json.loads(line))
    log.info("Loaded %d docs from export", len(docs))

    # Resume from checkpoint
    ckpt = load_checkpoint()
    done_ids = set(ckpt.get("done_ids", []))
    log.info("Checkpoint: %d already embedded", len(done_ids))

    pending = [d for d in docs if d["id"] not in done_ids]
    if limit:
        pending = pending[:limit]
    log.info("Pending: %d docs to embed", len(pending))

    if not pending:
        log.info("All done!")
        return

    # Load existing LanceDB if any
    lance_dir = Path(LANCE_DIR)
    lance_dir.mkdir(parents=True, exist_ok=True)
    lance_db = lancedb.connect(str(lance_dir))

    client = httpx.Client()
    records = []
    t0 = time.time()
    batch_size = 500
    failed = 0

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

        # Flush batch to LanceDB
        if len(records) >= batch_size:
            try:
                tbl = lance_db.open_table(TABLE_NAME)
                tbl.add(records)
            except Exception:
                tbl = lance_db.create_table(TABLE_NAME, records)
            save_checkpoint({"embedded_count": len(done_ids), "done_ids": list(done_ids)})
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(pending) - i - 1) / rate / 60 if rate > 0 else 0
            log.info("Batch %d: +%d vectors (total %d, %.1f/s, ETA %.0f min, %d failed)",
                     (i + 1) // batch_size, len(records), len(done_ids), rate, eta, failed)
            records = []

        # Rate limit: Gemini embedding free tier = 1500 RPM (25 RPS)
        # At ~2 RPS actual throughput, no extra sleep needed
        pass

    # Final batch
    if records:
        try:
            tbl = lance_db.open_table(TABLE_NAME)
            tbl.add(records)
        except Exception:
            tbl = lance_db.create_table(TABLE_NAME, records)
        save_checkpoint({"embedded_count": len(done_ids), "done_ids": list(done_ids)})

    client.close()
    elapsed = time.time() - t0

    tbl = lance_db.open_table(TABLE_NAME)
    log.info("=" * 60)
    log.info("DONE: %d vectors in %.1f min (%.1f/s)", len(done_ids), elapsed / 60, len(done_ids) / elapsed if elapsed > 0 else 0)
    log.info("Total in LanceDB: %d vectors", tbl.count_rows())
    log.info("Failed: %d", failed)
    log.info("Output: %s", LANCE_DIR)
    log.info("Next: rsync %s to VPS /home/kg/data/lancedb/", LANCE_DIR)


if __name__ == "__main__":
    main()
