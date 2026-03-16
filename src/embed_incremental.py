#!/usr/bin/env python3
"""Incremental embedding: embed new nodes without full DB rebuild.

Reads node IDs from LanceDB, compares with KuzuDB, embeds only new ones.
Does NOT lock KuzuDB for extended periods (opens/closes per batch).

M2 Principle: new nodes embed immediately, no full rebuild unless schema changes.

Usage:
    python3 src/embed_incremental.py
    python3 src/embed_incremental.py --batch-size 100
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
import kuzu
import lancedb
import pyarrow as pa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("embed_incremental")

EMBEDDING_DIM = 768
MODEL = "gemini-embedding-2-preview"
GEMINI_EMBED_BASE = os.environ.get(
    "GEMINI_EMBED_BASE",
    "https://gemini-api-proxy.maoyuan-wen-683.workers.dev"
)
EMBED_URL = f"{GEMINI_EMBED_BASE}/v1beta/models/{MODEL}:embedContent"


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for p in [Path.home() / ".openclaw" / ".env", Path(".env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found")


def embed_one(text: str, api_key: str, client: httpx.Client) -> list[float]:
    body = {
        "model": f"models/{MODEL}",
        "content": {"parts": [{"text": text[:8000]}]},
        "outputDimensionality": EMBEDDING_DIM,
    }
    for attempt in range(5):
        try:
            resp = client.post(f"{EMBED_URL}?key={api_key}", json=body, timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt + 1)
                continue
            resp.raise_for_status()
            return resp.json()["embedding"]["values"]
        except Exception as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
            else:
                log.error("Embed failed: %s", e)
                return [0.0] * EMBEDDING_DIM
    return [0.0] * EMBEDDING_DIM


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--lance", default="data/finance-tax-lance")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    api_key = get_api_key()
    log.info("API key loaded")

    # Get existing IDs from LanceDB
    lance_db = lancedb.connect(args.lance)
    try:
        tbl = lance_db.open_table("finance_tax_embeddings")
        existing_ids = set(tbl.to_pandas()["id"].tolist())
        log.info("LanceDB existing: %d vectors", len(existing_ids))
    except Exception:
        log.info("No existing LanceDB table, will create")
        existing_ids = set()

    # Get all node IDs from KuzuDB (quick read, release lock fast)
    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    new_docs = []

    # LawOrRegulation
    r = conn.execute(
        "MATCH (n:LawOrRegulation) RETURN n.id, n.title, n.regulationType, "
        "n.issuingAuthority, n.fullText"
    )
    while r.has_next():
        row = r.get_next()
        nid = row[0] or ""
        if nid in existing_ids:
            continue
        title = row[1] or ""
        text = (row[4] or "")[:1500]
        new_docs.append({
            "id": nid,
            "title": title[:200],
            "node_type": "LawOrRegulation",
            "reg_type": row[2] or "",
            "source": row[3] or "",
            "embed_text": f"{title}\n{text}"[:3000],
        })

    # RegulationClause
    r = conn.execute("MATCH (n:RegulationClause) RETURN n.id, n.title, n.fullText")
    while r.has_next():
        row = r.get_next()
        nid = row[0] or ""
        if nid in existing_ids:
            continue
        title = row[1] or ""
        text = (row[2] or "")[:1500]
        new_docs.append({
            "id": nid,
            "title": title[:200],
            "node_type": "RegulationClause",
            "reg_type": "clause",
            "source": "",
            "embed_text": f"{title}\n{text}"[:3000],
        })

    # Close DB connection to release lock
    del conn
    del db

    log.info("New documents to embed: %d", len(new_docs))
    if not new_docs:
        log.info("Nothing to embed, all up to date")
        return

    # Embed in batches
    client = httpx.Client()
    records = []
    start = time.time()

    for i, doc in enumerate(new_docs):
        vec = embed_one(doc["embed_text"], api_key, client)
        records.append({
            "id": doc["id"],
            "title": doc["title"],
            "node_type": doc["node_type"],
            "reg_type": doc["reg_type"],
            "source": doc["source"],
            "vector": vec,
        })

        if (i + 1) % args.batch_size == 0:
            # Append batch to LanceDB
            try:
                tbl = lance_db.open_table("finance_tax_embeddings")
                tbl.add(records)
                log.info("Appended %d vectors (%d/%d total)",
                         len(records), i + 1, len(new_docs))
            except Exception:
                # Table might not exist yet, create it
                tbl = lance_db.create_table("finance_tax_embeddings", records)
                log.info("Created table with %d vectors", len(records))
            records = []

        if (i + 1) % 100 == 0:
            time.sleep(0.5)  # Rate limit

    # Final batch
    if records:
        try:
            tbl = lance_db.open_table("finance_tax_embeddings")
            tbl.add(records)
        except Exception:
            tbl = lance_db.create_table("finance_tax_embeddings", records)
        log.info("Final batch: %d vectors", len(records))

    client.close()
    elapsed = time.time() - start

    # Summary
    tbl = lance_db.open_table("finance_tax_embeddings")
    log.info("Done: +%d vectors in %.1f min | Total: %d vectors",
             len(new_docs), elapsed / 60, tbl.count_rows())


if __name__ == "__main__":
    main()
