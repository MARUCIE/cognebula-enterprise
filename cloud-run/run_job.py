#!/usr/bin/env python3
"""Cloud Run Job: KuzuDB heavy operations with 16GB RAM.

Flow:
1. Download DB snapshot from GCS
2. Run the specified operation (matrix expansion, content restore, etc.)
3. Upload updated DB back to GCS
4. Upload results (JSONL) to GCS

Environment variables:
  OPERATION: matrix_expand | restore_lr | build_edges | ingest_all
  GCS_BUCKET: cognebula-kg-data
  DB_ARCHIVE: finance-tax-graph.tar.gz
"""
import gc
import json
import logging
import os
import subprocess
import sys
import tarfile
import time

from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("cloud-job")

GCS_BUCKET = os.environ.get("GCS_BUCKET", "cognebula-kg-data")
DB_ARCHIVE = os.environ.get("DB_ARCHIVE", "finance-tax-graph.tar.gz")
OPERATION = os.environ.get("OPERATION", "status")
LOCAL_DB = "/tmp/finance-tax-graph"
LOCAL_TAR = "/tmp/finance-tax-graph.tar.gz"


def download_db():
    """Download DB from GCS, extract, delete tar to free space."""
    log.info("Downloading from gs://%s/%s...", GCS_BUCKET, DB_ARCHIVE)
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(DB_ARCHIVE)
    blob.download_to_filename(LOCAL_TAR)
    size_mb = os.path.getsize(LOCAL_TAR) / 1024 / 1024
    log.info("Downloaded: %.1f MB", size_mb)

    log.info("Extracting (filter=data)...")
    with tarfile.open(LOCAL_TAR, "r:gz") as tar:
        tar.extractall("/tmp", filter="data")

    # Delete tar immediately to free memory (tmpfs)
    os.remove(LOCAL_TAR)
    gc.collect()
    log.info("DB ready at %s (tar deleted to free RAM)", LOCAL_DB)


def upload_db():
    """Compress and upload DB back to GCS."""
    log.info("Compressing DB...")
    with tarfile.open(LOCAL_TAR, "w:gz") as tar:
        tar.add(LOCAL_DB, arcname="finance-tax-graph")
    size_mb = os.path.getsize(LOCAL_TAR) / 1024 / 1024
    log.info("Compressed: %.1f MB", size_mb)

    log.info("Uploading to gs://%s/%s...", GCS_BUCKET, DB_ARCHIVE)
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(DB_ARCHIVE)
    blob.upload_from_filename(LOCAL_TAR)
    log.info("Upload done.")
    os.remove(LOCAL_TAR)


def upload_file(local_path, gcs_path):
    """Upload a single file to GCS."""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    log.info("Uploaded %s to gs://%s/%s", local_path, GCS_BUCKET, gcs_path)


def op_status():
    """Just check DB stats."""
    import kuzu
    db = kuzu.Database(LOCAL_DB)
    conn = kuzu.Connection(db)

    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    ku = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content) >= 100 RETURN count(k)")
    ku_good = r.get_next()[0]

    log.info("Nodes: %d | Edges: %d | Density: %.2f", nodes, edges, edges / nodes)
    log.info("KU: %d total, %d with content (%.1f%%)", ku, ku_good, 100 * ku_good / ku)

    del conn, db
    return {"nodes": nodes, "edges": edges, "ku": ku, "ku_good": ku_good}


def op_restore_lr():
    """Restore lr_cleanup content without reconnect (16GB safe)."""
    import csv
    import kuzu

    db = kuzu.Database(LOCAL_DB)
    conn = kuzu.Connection(db)
    writes = 0

    # Load content from CSV + JSONL into memory
    content_map = {}

    csv_path = "/tmp/data/edge_csv/m3_lr_cleanup/ku_from_lr_v2.csv"
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    nid = row[0].strip().strip('"')
                    content = row[3].strip().strip('"')[:3000]
                    if len(content) >= 100:
                        content_map[nid] = content
        log.info("CSV: %d IDs with content>=100c", len(content_map))

    jsonl_path = "/tmp/data/backfill/lr_cleanup_content.jsonl"
    if os.path.exists(jsonl_path):
        added = 0
        with open(jsonl_path) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    nid = item["id"]
                    content = item.get("content", "")[:3000]
                    if len(content) >= 100 and (nid not in content_map or len(content) > len(content_map[nid])):
                        content_map[nid] = content
                        added += 1
                except:
                    pass
        log.info("JSONL added: %d (total: %d)", added, len(content_map))

    # Write to DB
    items = list(content_map.items())
    del content_map
    gc.collect()

    updated = 0
    for i, (nid, content) in enumerate(items):
        try:
            r = conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                {"id": nid}
            )
            if r.has_next() and r.get_next()[0] < len(content):
                conn.execute("MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c", {"id": nid, "c": content})
                writes += 1
                updated += 1
                if writes % 50 == 0:
                    conn.execute("CHECKPOINT")
        except:
            pass

        if (i + 1) % 5000 == 0:
            conn.execute("CHECKPOINT")
            log.info("  %d/%d: updated=%d", i + 1, len(items), updated)

    conn.execute("CHECKPOINT")
    log.info("LR restore done: %d updated / %d items", updated, len(items))

    del conn, db
    return {"updated": updated, "total": len(items)}


def op_ingest_all():
    """Run all pending ingest scripts in sequence."""
    import kuzu

    db = kuzu.Database(LOCAL_DB)
    conn = kuzu.Connection(db)
    writes = 0
    results = {}

    # Download data files from GCS
    log.info("Downloading data files from GCS...")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    data_files = [
        "backfill/qa_answers.jsonl",
        "backfill/lr_cleanup_content.jsonl",
        "recrawl/chinatax_fulltext.jsonl",
    ]

    for f in data_files:
        blob = bucket.blob(f"data/{f}")
        local = f"/tmp/data/{f}"
        os.makedirs(os.path.dirname(local), exist_ok=True)
        if blob.exists():
            blob.download_to_filename(local)
            log.info("  Downloaded %s", f)

    # Ingest QA answers
    qa_path = "/tmp/data/backfill/qa_answers.jsonl"
    if os.path.exists(qa_path):
        log.info("\nIngesting QA answers...")
        qa_updated = 0
        with open(qa_path) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    nid = item["id"]
                    content = f"Q: {item['question']}\nA: {item['answer']}"[:3000]
                    if len(content) >= 100:
                        r = conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END",
                            {"id": nid}
                        )
                        if r.has_next() and r.get_next()[0] < len(content):
                            conn.execute("MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c", {"id": nid, "c": content})
                            writes += 1
                            qa_updated += 1
                            if writes % 50 == 0:
                                conn.execute("CHECKPOINT")
                except:
                    pass
        conn.execute("CHECKPOINT")
        results["qa"] = qa_updated
        log.info("  QA: +%d", qa_updated)

    # Ingest chinatax fulltext
    ct_path = "/tmp/data/recrawl/chinatax_fulltext.jsonl"
    if os.path.exists(ct_path):
        log.info("\nIngesting chinatax fulltext...")
        ct_updated = 0
        with open(ct_path) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    title = item.get("title", "").strip()
                    content = item.get("content", "")[:3000]
                    if len(content) >= 100 and title:
                        r = conn.execute(
                            "MATCH (k:KnowledgeUnit) WHERE k.title = $t RETURN k.id, CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END LIMIT 1",
                            {"t": title}
                        )
                        if r.has_next():
                            row = r.get_next()
                            if row[1] < len(content):
                                conn.execute("MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c", {"id": str(row[0]), "c": content})
                                writes += 1
                                ct_updated += 1
                                if writes % 50 == 0:
                                    conn.execute("CHECKPOINT")
                except:
                    pass
        conn.execute("CHECKPOINT")
        results["chinatax"] = ct_updated
        log.info("  chinatax: +%d", ct_updated)

    del conn, db
    results["total_writes"] = writes
    return results


def main():
    t0 = time.time()
    log.info("=== Cloud Run Job: %s ===", OPERATION)
    log.info("RAM: %.1f GB available", os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1024**3)

    # Step 1: Download DB
    download_db()

    # Step 2: Run operation
    if OPERATION == "status":
        result = op_status()
    elif OPERATION == "restore_lr":
        result = op_restore_lr()
    elif OPERATION == "ingest_all":
        result = op_ingest_all()
    else:
        log.error("Unknown operation: %s", OPERATION)
        sys.exit(1)

    # Step 3: Upload DB (if modified)
    if OPERATION != "status":
        upload_db()

    elapsed = time.time() - t0
    log.info("\n=== Done in %.0fs ===", elapsed)
    log.info("Result: %s", json.dumps(result))


if __name__ == "__main__":
    main()
