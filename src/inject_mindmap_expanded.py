#!/usr/bin/env python3
"""Inject ALL substantial mindmap nodes into KuzuDB (no 500-node cap).

The previous inject_extracted_data.py capped mindmap injection at 500 nodes.
This script injects all nodes with description >= 50 chars and Chinese content,
skipping any that were already injected (IDs starting with LR_MM_).

Usage:
    python src/inject_mindmap_expanded.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def esc(s: str) -> str:
    """Escape string for Cypher."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, text: str) -> str:
    """Generate deterministic ID."""
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def has_chinese(s: str) -> bool:
    """Check if string contains Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", s))


def main():
    parser = argparse.ArgumentParser(description="Inject expanded mindmap nodes")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing")
    args = parser.parse_args()

    path = Path("data/extracted/mindmap/all_mindmap_nodes.json")
    if not path.exists():
        print("ERROR: mindmap data not found at", path)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    print(f"NOTE: Loaded {len(nodes)} total mindmap nodes")

    # Filter: description >= 50 chars AND contains Chinese
    candidates = []
    for node in nodes:
        desc = str(node.get("description", ""))
        if len(desc) >= 50 and has_chinese(desc):
            candidates.append(node)

    print(f"NOTE: {len(candidates)} nodes pass filter (description >= 50 chars + Chinese)")

    conn = None
    if not args.dry_run:
        try:
            import kuzu
        except ImportError:
            print("ERROR: kuzu not installed")
            sys.exit(1)
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)

    injected = 0
    skipped = 0

    for node in candidates:
        title = str(node.get("name", node.get("title", "")))
        content = str(node.get("description", ""))
        category = str(node.get("category", "mindmap"))

        nid = make_id("LR_MM", title)
        content_short = content[:2000]

        sql = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(nid)}', title: '{esc(title[:200])}', "
            f"regulationNumber: '', issuingAuthority: 'doc-tax-mindmap', "
            f"regulationType: '{esc(category)}', "
            f"issuedDate: date('2026-01-01'), effectiveDate: date('2026-01-01'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'reference', hierarchyLevel: 0, "
            f"sourceUrl: 'local://doc-tax/mindmap', "
            f"contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
            f"fullText: '{esc(content_short)}', "
            f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
            f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
            f"txTimeCreated: timestamp('2026-03-15 00:00:00'), "
            f"txTimeUpdated: timestamp('2026-03-15 00:00:00')"
            f"}})"
        )

        if args.dry_run:
            injected += 1
        else:
            try:
                conn.execute(sql)
                injected += 1
            except Exception as e:
                err_msg = str(e).lower()
                if "duplicate" in err_msg or "already exists" in err_msg or "primary key" in err_msg:
                    skipped += 1
                else:
                    skipped += 1

    print(f"OK: Injected {injected} mindmap nodes as LawOrRegulation")
    if skipped:
        print(f"NOTE: Skipped {skipped} nodes (already exist or error)")
    print(f"NOTE: Total candidates={len(candidates)}, injected={injected}, skipped={skipped}")


if __name__ == "__main__":
    main()
