#!/usr/bin/env python3
"""Re-ingest extracted nodes from doctax_extracted.json into KG API.

Run this after KuzuDB lock is released.
Usage: .venv/bin/python3 scripts/reingest_extracted.py
"""
import json
import urllib.request
from pathlib import Path

KG_API = "http://100.75.77.112:8400"
DATA_FILE = Path(__file__).parent.parent / "data" / "extracted" / "doctax_extracted.json"
BATCH_SIZE = 30


def ingest_batch(table, nodes):
    inserted = errors = 0
    for i in range(0, len(nodes), BATCH_SIZE):
        batch = nodes[i:i + BATCH_SIZE]
        payload = json.dumps({"table": table, "nodes": batch}).encode()
        req = urllib.request.Request(
            f"{KG_API}/api/v1/ingest",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                r = json.loads(resp.read())
                inserted += r.get("inserted", 0)
                errors += r.get("errors", 0)
        except Exception as e:
            errors += len(batch)
    return inserted, errors


def main():
    # Check health first
    try:
        with urllib.request.urlopen(f"{KG_API}/api/v1/health", timeout=5) as resp:
            health = json.loads(resp.read())
            if not health.get("kuzu"):
                print("ERROR: KuzuDB is still locked/degraded. Wait and retry.")
                return
    except:
        print("ERROR: KG API unreachable")
        return

    with open(DATA_FILE) as f:
        data = json.load(f)
    print(f"Loaded {len(data)} extracted nodes from {DATA_FILE}")

    # Map to DocumentSection schema
    nodes = []
    for n in data:
        nodes.append({
            "id": n.get("id", ""),
            "title": (n.get("title") or "")[:500],
            "content": (n.get("content") or "")[:3000],
            "source": (n.get("category") or n.get("source_file") or "")[:200],
        })

    print(f"Ingesting {len(nodes)} nodes as DocumentSection...")
    ins, err = ingest_batch("DocumentSection", nodes)
    print(f"Inserted: {ins}, Errors: {err} (errors are likely duplicates)")

    # Final stats
    try:
        with urllib.request.urlopen(f"{KG_API}/api/v1/stats", timeout=10) as resp:
            stats = json.loads(resp.read())
            print(f"KG: {stats['total_nodes']:,} nodes, {stats['total_edges']:,} edges")
    except:
        pass


if __name__ == "__main__":
    main()
