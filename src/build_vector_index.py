#!/usr/bin/env python3
"""Build LanceDB vector index from KuzuDB LawOrRegulation nodes.

Uses Gemini Embedding 2 Preview (768d) to embed regulation titles + content,
then stores vectors in LanceDB for fast ANN search.

Usage:
    python build_vector_index.py --db data/finance-tax-graph --lance data/finance-tax-lance
    python build_vector_index.py --db data/finance-tax-graph --lance data/finance-tax-lance --batch-size 20
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import httpx
import kuzu
import lancedb
import pyarrow as pa

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_vector_index")

EMBEDDING_MODEL = os.environ.get("EMBED_MODEL", "gemini-embedding-2-preview")
EMBEDDING_DIM = 3072  # gemini-embedding-2-preview default dimension
# Support proxied endpoint via GEMINI_EMBED_BASE env var (for geo-restricted VPS)
_DEFAULT_BASE = "https://generativelanguage.googleapis.com"
GEMINI_EMBED_BASE = os.environ.get("GEMINI_EMBED_BASE", _DEFAULT_BASE)
GEMINI_API_URL = f"{GEMINI_EMBED_BASE}/v1beta/models/{{model}}:embedContent"


def _get_api_key() -> str:
    """Get Gemini API key from environment or .env files."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for env_path in [Path.home() / ".openclaw" / ".env", Path(".env")]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found in environment or .env files")


def _embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed a batch of texts using Gemini Embedding API (one at a time, batched for rate limit)."""
    vectors = []
    url = GEMINI_API_URL.format(model=EMBEDDING_MODEL)
    with httpx.Client(timeout=30) as client:
        for text in texts:
            truncated = text[:2000]  # Gemini has token limits
            payload = {
                "model": f"models/{EMBEDDING_MODEL}",
                "content": {"parts": [{"text": truncated}]},
                "taskType": "RETRIEVAL_DOCUMENT",
            }
            try:
                resp = client.post(
                    f"{url}?key={api_key}",
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    vec = data.get("embedding", {}).get("values", [])
                    if len(vec) == EMBEDDING_DIM:
                        vectors.append(vec)
                    else:
                        log.warning("Unexpected embedding dim %d, padding", len(vec))
                        vectors.append(vec + [0.0] * (EMBEDDING_DIM - len(vec)))
                elif resp.status_code == 429:
                    log.warning("Rate limited, waiting 10s")
                    time.sleep(10)
                    # Retry once
                    resp2 = client.post(f"{url}?key={api_key}", json=payload)
                    if resp2.status_code == 200:
                        vec = resp2.json().get("embedding", {}).get("values", [])
                        vectors.append(vec if len(vec) == EMBEDDING_DIM else [0.0] * EMBEDDING_DIM)
                    else:
                        vectors.append([0.0] * EMBEDDING_DIM)
                else:
                    log.warning("Embedding failed (%d): %s", resp.status_code, resp.text[:200])
                    vectors.append([0.0] * EMBEDDING_DIM)
            except Exception as e:
                log.warning("Embedding error: %s", e)
                vectors.append([0.0] * EMBEDDING_DIM)
            time.sleep(0.1)  # Rate limit: 1500 RPM = 25 RPS
    return vectors


def build_index(db_path: str, lance_path: str, batch_size: int = 20) -> dict:
    """Build LanceDB vector index from KuzuDB."""
    api_key = _get_api_key()
    log.info("API key loaded (prefix: %s...)", api_key[:10])

    # Read ALL node types for comprehensive embedding
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    docs = []

    # 1. LawOrRegulation (bulk)
    r = conn.execute(
        "MATCH (n:LawOrRegulation) "
        "RETURN n.id, n.title, n.regulationNumber, n.issuingAuthority, "
        "n.sourceUrl, n.fullText, n.status"
    )
    while r.has_next():
        row = r.get_next()
        docs.append({
            "id": row[0],
            "title": row[1] or "",
            "reg_number": row[2] or "",
            "source": row[3] or "",
            "url": row[4] or "",
            "text": (row[5] or "")[:2000],
            "status": row[6] or "active",
            "node_type": "LawOrRegulation",
        })
    log.info("Loaded %d LawOrRegulation nodes", len(docs))

    # 2. RiskIndicator
    try:
        r = conn.execute(
            "MATCH (n:RiskIndicator) "
            "RETURN n.id, n.name, n.metricName, n.metricFormula, "
            "n.triggerCondition, n.industryId, n.notes"
        )
        ri_count = 0
        while r.has_next():
            row = r.get_next()
            docs.append({
                "id": row[0],
                "title": f"[RiskIndicator] {row[1] or ''}",
                "reg_number": "",
                "source": row[5] or "",
                "url": "",
                "text": f"{row[2] or ''} {row[3] or ''} {row[4] or ''} {row[6] or ''}",
                "status": "active",
                "node_type": "RiskIndicator",
            })
            ri_count += 1
        log.info("Loaded %d RiskIndicator nodes", ri_count)
    except Exception as e:
        log.warning("RiskIndicator query failed: %s", e)

    # 3. OP_BusinessScenario
    try:
        r = conn.execute(
            "MATCH (n:OP_BusinessScenario) "
            "RETURN n.id, n.name, n.category, n.industry, n.description, n.notes"
        )
        bs_count = 0
        while r.has_next():
            row = r.get_next()
            docs.append({
                "id": row[0],
                "title": f"[BusinessScenario] {row[1] or ''}",
                "reg_number": "",
                "source": row[3] or "",
                "url": "",
                "text": f"{row[2] or ''} {row[4] or ''} {row[5] or ''}",
                "status": "active",
                "node_type": "OP_BusinessScenario",
            })
            bs_count += 1
        log.info("Loaded %d OP_BusinessScenario nodes", bs_count)
    except Exception as e:
        log.warning("OP_BusinessScenario query failed: %s", e)

    # 4. OP_StandardCase
    try:
        r = conn.execute(
            "MATCH (n:OP_StandardCase) "
            "RETURN n.id, n.name, n.scenario, n.correctTreatment, n.industryRelevance, n.notes"
        )
        sc_count = 0
        while r.has_next():
            row = r.get_next()
            docs.append({
                "id": row[0],
                "title": f"[StandardCase] {row[1] or ''}",
                "reg_number": "",
                "source": row[4] or "",
                "url": "",
                "text": f"{row[2] or ''} {row[3] or ''} {row[5] or ''}",
                "status": "active",
                "node_type": "OP_StandardCase",
            })
            sc_count += 1
        log.info("Loaded %d OP_StandardCase nodes", sc_count)
    except Exception as e:
        log.warning("OP_StandardCase query failed: %s", e)

    # 5. Other small tables (FTIndustry, TaxType, AccountingStandard, etc.)
    for tbl, fields in [
        ("FTIndustry", "n.id, n.name, n.gbCode"),
        ("TaxType", "n.id, n.name, n.code"),
        ("AccountingStandard", "n.id, n.name, n.standardNumber"),
        ("TaxIncentive", "n.id, n.name, n.description"),
    ]:
        try:
            r = conn.execute(f"MATCH (n:{tbl}) RETURN {fields}")
            t_count = 0
            while r.has_next():
                row = r.get_next()
                docs.append({
                    "id": row[0],
                    "title": f"[{tbl}] {row[1] or ''}",
                    "reg_number": row[2] if len(row) > 2 else "",
                    "source": tbl,
                    "url": "",
                    "text": " ".join(str(x) for x in row if x),
                    "status": "active",
                    "node_type": tbl,
                })
                t_count += 1
            if t_count > 0:
                log.info("Loaded %d %s nodes", t_count, tbl)
        except Exception:
            pass

    log.info("Total: %d nodes to embed across all types", len(docs))

    if not docs:
        return {"status": "empty", "count": 0}

    # Generate embeddings in batches
    all_vectors = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        texts = [f"{d['title']} {d['reg_number']} {d['text'][:500]}" for d in batch]
        log.info("Embedding batch %d-%d / %d", i + 1, min(i + batch_size, len(docs)), len(docs))
        vectors = _embed_batch(texts, api_key)
        all_vectors.extend(vectors)

    # Build LanceDB table
    lance_dir = Path(lance_path)
    lance_dir.mkdir(parents=True, exist_ok=True)
    lance_db = lancedb.connect(str(lance_dir))

    records = []
    for doc, vec in zip(docs, all_vectors):
        records.append({
            "id": doc["id"],
            "title": doc["title"],
            "reg_number": doc["reg_number"],
            "source": doc["source"],
            "url": doc["url"],
            "text": doc["text"][:1000],
            "status": doc["status"],
            "vector": vec,
        })

    # Create or overwrite table
    try:
        lance_db.drop_table("finance_tax_embeddings")
        log.info("Dropped existing table")
    except Exception:
        pass

    table = lance_db.create_table("finance_tax_embeddings", records)
    log.info("Created LanceDB table with %d rows, %d dimensions", len(records), EMBEDDING_DIM)

    # Verify
    sample = table.search(all_vectors[0]).limit(3).to_list()
    log.info("Verification: top-3 for first doc = %s", [s["title"][:30] for s in sample])

    return {
        "status": "ok",
        "count": len(records),
        "dimensions": EMBEDDING_DIM,
        "model": EMBEDDING_MODEL,
        "lance_path": str(lance_dir),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build LanceDB vector index")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--lance", default="data/finance-tax-lance", help="LanceDB output path")
    parser.add_argument("--batch-size", type=int, default=20, help="Embedding batch size")
    args = parser.parse_args()
    result = build_index(args.db, args.lance, args.batch_size)
    print(json.dumps(result, indent=2))
