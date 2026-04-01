#!/usr/bin/env python3
"""Full rebuild of LanceDB vector index using gemini-embedding-2-preview (3072 dim).

Reads all meaningful nodes from KG API, embeds via batch API, writes to LanceDB.
Replaces the old kg_nodes table entirely.

Usage:
    python3 scripts/rebuild_embeddings.py                    # full rebuild
    python3 scripts/rebuild_embeddings.py --dim 768          # truncated 768-dim
    python3 scripts/rebuild_embeddings.py --tables TaxType,FAQEntry  # specific tables only
    python3 scripts/rebuild_embeddings.py --dry-run          # count only
"""
import argparse
import json
import logging
import os
import sys
import time

import requests as http_requests
import lancedb
import pyarrow as pa
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rebuild_embeddings")

# Config
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-embedding-2-preview"
BATCH_EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents"
KG_API = os.environ.get("KG_API", "http://localhost:8400")
LANCE_PATH = os.environ.get("LANCE_PATH", "/home/kg/data/lancedb")

# Tables to embed with their text-building logic
# Format: (table_name, text_fields_priority, category_field)
EMBED_TABLES = [
    # High-value structured data
    ("TaxType", ["name", "fullText", "title"], "category"),
    ("TaxItem", ["name", "fullText", "description"], "taxType"),
    ("TaxRate", ["name", "fullText", "description"], "category"),
    ("TaxIncentive", ["name", "fullText", "description", "eligibilityCriteria"], "incentiveType"),
    ("ComplianceRule", ["name", "fullText", "description"], "category"),
    ("RiskIndicator", ["name", "fullText", "description", "metricFormula"], "category"),
    ("AccountingStandard", ["name", "fullText", "description"], "category"),
    ("AccountingSubject", ["name", "fullText", "description"], "category"),
    ("BusinessActivity", ["name", "fullText", "description"], "category"),
    ("JournalEntryTemplate", ["name", "fullText", "description"], "category"),
    ("FilingFormField", ["name", "description"], "category"),
    ("TaxTreaty", ["name", "fullText", "description"], "category"),
    ("FinancialIndicator", ["name", "fullText", "description", "formula"], "category"),
    ("TaxCalculationRule", ["name", "fullText", "description"], "category"),
    ("SocialInsuranceRule", ["name", "fullText", "description"], "category"),
    ("InvoiceRule", ["name", "fullText", "description"], "category"),
    ("IndustryBenchmark", ["ratioName", "description"], "category"),
    ("IndustryRiskProfile", ["name", "fullText", "description"], "category"),
    ("TaxAccountingGap", ["name", "fullText", "description"], "category"),
    ("Penalty", ["name", "fullText", "description"], "category"),
    ("AuditTrigger", ["name", "fullText", "description"], "category"),
    ("DeductionRule", ["name", "fullText", "description"], "category"),
    ("ResponseStrategy", ["name", "fullText", "description"], "category"),
    ("PolicyChange", ["name", "fullText", "description"], "category"),
    # Q&A content
    ("FAQEntry", ["question", "content", "fullText"], "category"),
    # CPA knowledge
    ("CPAKnowledge", ["title", "content", "topic"], "subject"),
    # Legal documents (large tables)
    ("LawOrRegulation", ["title", "fullText"], "regulationType"),
    ("LegalDocument", ["name", "fullText", "description"], "type"),
    # Reference data
    ("TaxClassificationCode", ["item_name", "description", "code"], "category_abbr"),
    ("Classification", ["name", "fullText", "title"], "system"),
    # Knowledge
    ("KnowledgeUnit", ["content", "title", "topic"], "category"),
]


def build_text(node: dict, text_fields: list) -> str:
    """Build embedding text from node fields, prioritizing non-empty fields."""
    parts = []
    for f in text_fields:
        val = node.get(f, "") or ""
        val = str(val).strip()
        if len(val) > 5:
            parts.append(val[:2000])
    text = "\n".join(parts)[:4000]
    return text if len(text) >= 10 else ""


def fetch_nodes(table: str, limit: int = 100, offset: int = 0) -> list:
    """Fetch nodes from KG API."""
    resp = http_requests.get(
        f"{KG_API}/api/v1/nodes",
        params={"type": table, "limit": limit, "offset": offset},
        timeout=15,
    )
    return resp.json().get("results", [])


def batch_embed(texts: list, api_key: str, dim: int) -> list:
    """Embed a batch of texts using batchEmbedContents API."""
    requests_body = []
    for text in texts:
        req = {
            "model": f"models/{MODEL}",
            "content": {"parts": [{"text": text[:8000]}]},
        }
        if dim < 3072:
            req["outputDimensionality"] = dim
        requests_body.append(req)

    for attempt in range(5):
        try:
            resp = http_requests.post(
                f"{BATCH_EMBED_URL}?key={api_key}",
                json={"requests": requests_body},
                timeout=60,
            )
            if resp.status_code == 429:
                wait = 2 ** attempt + 1
                log.warning("Rate limited, waiting %ds", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return [e["values"] for e in data["embeddings"]]
        except Exception as e:
            if attempt < 4:
                log.warning("Batch embed attempt %d failed: %s", attempt + 1, e)
                time.sleep(2 ** attempt)
            else:
                log.error("Batch embed failed after 5 attempts: %s", e)
                return [[0.0] * dim] * len(texts)
    return [[0.0] * dim] * len(texts)


def main():
    parser = argparse.ArgumentParser(description="Rebuild LanceDB embeddings")
    parser.add_argument("--dim", type=int, default=3072, help="Embedding dimension (768 or 3072)")
    parser.add_argument("--batch-size", type=int, default=80, help="Texts per embed API call (max 100)")
    parser.add_argument("--tables", type=str, default="", help="Comma-separated table names (empty=all)")
    parser.add_argument("--dry-run", action="store_true", help="Count nodes only")
    parser.add_argument("--lance-path", default=LANCE_PATH)
    args = parser.parse_args()

    global GEMINI_KEY
    if not GEMINI_KEY:
        # Try loading from .env
        for p in ["/home/kg/.env.kg-api", ".env"]:
            if os.path.exists(p):
                for line in open(p):
                    if line.startswith("GEMINI_API_KEY="):
                        GEMINI_KEY = line.split("=", 1)[1].strip()
                        break
    if not GEMINI_KEY:
        log.error("GEMINI_API_KEY not set")
        sys.exit(1)

    # Filter tables if specified
    tables = EMBED_TABLES
    if args.tables:
        selected = set(args.tables.split(","))
        tables = [t for t in tables if t[0] in selected]
        log.info("Selected tables: %s", [t[0] for t in tables])

    # Phase 1: Collect all texts to embed
    log.info("Phase 1: Collecting texts from %d tables...", len(tables))
    all_records = []  # (id, text, table, category)

    for table_name, text_fields, cat_field in tables:
        count = 0
        for offset in range(0, 200_000, 100):
            nodes = fetch_nodes(table_name, limit=100, offset=offset)
            if not nodes:
                break
            for n in nodes:
                text = build_text(n, text_fields)
                if not text:
                    continue
                nid = n.get("id", "")
                cat = n.get(cat_field, "") or ""
                all_records.append((nid, text, table_name, cat))
                count += 1
        log.info("  %s: %d texts", table_name, count)

    log.info("Total texts to embed: %d", len(all_records))

    if args.dry_run:
        log.info("[DRY RUN] Would embed %d texts at %d dim", len(all_records), args.dim)
        return

    # Phase 2+3: Batch embed + incremental write to LanceDB
    log.info("Phase 2: Embedding %d texts (dim=%d, batch=%d) with incremental LanceDB writes...",
             len(all_records), args.dim, args.batch_size)

    db = lancedb.connect(args.lance_path)

    # Drop old table if exists
    try:
        db.drop_table("kg_nodes")
        log.info("Dropped old kg_nodes table")
    except Exception:
        pass

    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("table", pa.string()),
        pa.field("category", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), args.dim)),
    ])

    tbl = None
    flush_buffer = []
    FLUSH_SIZE = 5000  # Write to LanceDB every 5K vectors (keep memory ~75MB)
    start = time.time()
    total_written = 0

    for i in range(0, len(all_records), args.batch_size):
        batch = all_records[i:i + args.batch_size]
        texts = [r[1] for r in batch]
        vectors = batch_embed(texts, GEMINI_KEY, args.dim)

        for (nid, text, table, cat), vec in zip(batch, vectors):
            flush_buffer.append({
                "id": nid,
                "text": text[:500],
                "table": table,
                "category": cat[:100],
                "vector": vec,
            })

        # Flush to LanceDB periodically
        if len(flush_buffer) >= FLUSH_SIZE:
            if tbl is None:
                tbl = db.create_table("kg_nodes", flush_buffer, schema=schema)
            else:
                tbl.add(flush_buffer)
            total_written += len(flush_buffer)
            flush_buffer = []

        done = min(i + args.batch_size, len(all_records))
        if done % 5000 < args.batch_size:
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(all_records) - done) / rate if rate > 0 else 0
            log.info("  %d/%d (%.0f/sec, ETA %.0f min, written: %d)",
                     done, len(all_records), rate, eta / 60, total_written)

        time.sleep(0.1)

    # Final flush
    if flush_buffer:
        if tbl is None:
            tbl = db.create_table("kg_nodes", flush_buffer, schema=schema)
        else:
            tbl.add(flush_buffer)
        total_written += len(flush_buffer)

    elapsed = time.time() - start
    log.info("Embedding complete: %d vectors written in %.1f min", total_written, elapsed / 60)

    # Create IVF_PQ index for fast search
    log.info("Creating vector index...")
    try:
        tbl.create_index(
            metric="cosine",
            num_partitions=min(256, max(1, len(embedded) // 1000)),
            num_sub_vectors=min(96, args.dim // 32),
        )
        log.info("Index created")
    except Exception as e:
        log.warning("Index creation failed (will use brute force): %s", e)

    log.info("=== DONE: %d vectors, %d dim, %.1f min ===", len(embedded), args.dim, elapsed / 60)


if __name__ == "__main__":
    main()
