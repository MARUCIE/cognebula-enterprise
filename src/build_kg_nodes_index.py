#!/usr/bin/env python3
"""Build LanceDB kg_nodes vector index aligned with kg-api-server.py.

Fixes 3 mismatches from original build_vector_index.py:
  1. Dimension: 768 (not 3072) — matches _embed_query() in kg-api-server
  2. Table name: kg_nodes (not finance_tax_embeddings) — matches get_lance()
  3. Node types: includes KnowledgeUnit (67K+ with content)

Embeds: LawOrRegulation + KnowledgeUnit + FAQEntry + small reference tables
Model: gemini-embedding-2-preview, 768D, via CF Worker proxy

Run on VPS (needs kuzu access, kg-api must be stopped):
    systemctl stop kg-api
    /home/kg-env/bin/python3 src/build_kg_nodes_index.py \
        --db /home/kg/cognebula-enterprise/data/finance-tax-graph \
        --lance /home/kg/data/lancedb
    systemctl start kg-api
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_index")

EMBEDDING_DIM = 768
MODEL = "gemini-embedding-2-preview"
GEMINI_EMBED_BASE = os.environ.get(
    "GEMINI_EMBED_BASE",
    "https://gemini-api-proxy.maoyuan-wen-683.workers.dev"
)
EMBED_URL = f"{GEMINI_EMBED_BASE}/v1beta/models/{MODEL}:embedContent"
TABLE_NAME = "kg_nodes"  # must match kg-api-server.py get_lance()
MIN_CONTENT_LEN = 50  # skip nodes with trivial content


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for p in ["/home/kg/.env.kg-api", str(Path.home() / ".openclaw" / ".env"), ".env"]:
        if os.path.exists(p):
            for line in open(p):
                if line.strip().startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1]
    raise RuntimeError("GEMINI_API_KEY not found")


def embed_one(text, api_key, client):
    import httpx
    body = {
        "model": f"models/{MODEL}",
        "content": {"parts": [{"text": text[:8000]}]},
        "taskType": "RETRIEVAL_DOCUMENT",
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


def load_nodes(db_path):
    import kuzu
    db = kuzu.Database(db_path, read_only=True)
    conn = kuzu.Connection(db)
    docs = []

    # 1. LawOrRegulation
    r = conn.execute(
        "MATCH (n:LawOrRegulation) "
        "RETURN n.id, n.title, n.regulationType, n.issuingAuthority, n.fullText"
    )
    lr_count = 0
    while r.has_next():
        row = r.get_next()
        title = row[1] or ""
        text = (row[4] or "")[:1500]
        if len(title) + len(text) < MIN_CONTENT_LEN:
            continue
        docs.append({
            "id": row[0], "title": title[:200], "node_type": "LawOrRegulation",
            "source": row[3] or "", "embed_text": f"{title}\n{row[2] or ''}\n{text}"[:3000],
        })
        lr_count += 1
    log.info("LawOrRegulation: %d nodes", lr_count)

    # 2. KnowledgeUnit (with content)
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.content IS NOT NULL AND size(k.content) >= 50 "
        "RETURN k.id, k.title, k.type, k.source, k.content"
    )
    ku_count = 0
    while r.has_next():
        row = r.get_next()
        title = row[1] or ""
        content = (row[4] or "")[:1500]
        docs.append({
            "id": row[0], "title": title[:200], "node_type": "KnowledgeUnit",
            "source": row[3] or "", "embed_text": f"{title}\n{content}"[:3000],
        })
        ku_count += 1
    log.info("KnowledgeUnit (content>=50): %d nodes", ku_count)

    # 3. FAQEntry
    try:
        r = conn.execute(
            "MATCH (f:FAQEntry) RETURN f.id, f.question, f.answer"
        )
        faq_count = 0
        while r.has_next():
            row = r.get_next()
            q = row[1] or ""
            a = (row[2] or "")[:1000]
            if len(q) + len(a) < MIN_CONTENT_LEN:
                continue
            docs.append({
                "id": row[0], "title": q[:200], "node_type": "FAQEntry",
                "source": "faq", "embed_text": f"Q: {q}\nA: {a}"[:3000],
            })
            faq_count += 1
        log.info("FAQEntry: %d nodes", faq_count)
    except Exception:
        pass

    # 4. Small reference tables
    for tbl, query, nt in [
        ("TaxType", "MATCH (n:TaxType) RETURN n.id, n.name, n.code", "TaxType"),
        ("AccountingStandard", "MATCH (n:AccountingStandard) RETURN n.id, n.name, n.standardNumber", "AccountingStandard"),
        ("TaxIncentive", "MATCH (n:TaxIncentive) RETURN n.id, n.name, n.description", "TaxIncentive"),
    ]:
        try:
            r = conn.execute(query)
            t_count = 0
            while r.has_next():
                row = r.get_next()
                text = " ".join(str(x) for x in row if x)
                docs.append({
                    "id": row[0], "title": f"[{nt}] {row[1] or ''}"[:200],
                    "node_type": nt, "source": nt,
                    "embed_text": text[:3000],
                })
                t_count += 1
            if t_count:
                log.info("%s: %d nodes", tbl, t_count)
        except Exception:
            pass

    del conn, db
    return docs


def main():
    import httpx
    import lancedb

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="/home/kg/cognebula-enterprise/data/finance-tax-graph")
    parser.add_argument("--lance", default="/home/kg/data/lancedb")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    api_key = get_api_key()
    log.info("API key loaded")

    docs = load_nodes(args.db)
    if args.limit:
        docs = docs[:args.limit]
    log.info("Total: %d nodes to embed", len(docs))

    if not docs:
        return

    # Embed
    client = httpx.Client()
    records = []
    t0 = time.time()

    for i, doc in enumerate(docs):
        vec = embed_one(doc["embed_text"], api_key, client)
        records.append({
            "id": doc["id"],
            "title": doc["title"],
            "node_type": doc["node_type"],
            "source": doc["source"],
            "vector": vec,
        })

        if (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(docs) - i - 1) / rate / 60 if rate > 0 else 0
            log.info("Embedded %d/%d (%.1f/s, ETA %.0f min)", i + 1, len(docs), rate, eta)

        if (i + 1) % 100 == 0:
            time.sleep(0.5)

    client.close()

    # Build LanceDB
    lance_dir = Path(args.lance)
    lance_dir.mkdir(parents=True, exist_ok=True)
    lance_db = lancedb.connect(str(lance_dir))

    try:
        lance_db.drop_table(TABLE_NAME)
        log.info("Dropped existing %s table", TABLE_NAME)
    except Exception:
        pass

    table = lance_db.create_table(TABLE_NAME, records)
    elapsed = time.time() - t0

    log.info("=" * 60)
    log.info("DONE: %d vectors, %dD, table=%s", len(records), EMBEDDING_DIM, TABLE_NAME)
    log.info("Time: %.1f min (%.1f vectors/sec)", elapsed / 60, len(records) / elapsed)
    log.info("Path: %s", args.lance)

    # Verify
    sample = table.search(records[0]["vector"]).limit(3).to_list()
    log.info("Verify: top-3 = %s", [s["title"][:30] for s in sample])

    print(json.dumps({
        "status": "ok", "count": len(records),
        "dimensions": EMBEDDING_DIM, "table": TABLE_NAME,
    }))


if __name__ == "__main__":
    main()
