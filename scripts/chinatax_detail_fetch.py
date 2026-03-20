#!/usr/bin/env python3
"""Fetch full text for ChinaTax FGK documents that only have snippets.

M3 Phase 1: Upgrade 57K policy documents from search snippets (3000 chars)
to full article text. Uses fleet-page-fetch VPS proxy for JS-rendered pages.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/chinatax_detail_fetch.py \
        --batch-size 100 --max-batches 50
    sudo systemctl start kg-api
"""
import kuzu
import csv
import json
import os
import sys
import time
import re
import argparse
import hashlib

import httpx

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/m3_detail"
os.makedirs(CSV_DIR, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
]


def fetch_article_text(client: httpx.Client, url: str) -> str:
    """Fetch full article text from a ChinaTax URL."""
    import random
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = client.get(url, headers=headers, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            return ""

        html = resp.text
        # Extract main content from common ChinaTax page structures
        # Pattern 1: <div class="main_content"> or <div id="fontzoom">
        patterns = [
            r'<div[^>]*(?:class="main_content"|id="fontzoom")[^>]*>(.*?)</div>',
            r'<div[^>]*class="TRS_Editor"[^>]*>(.*?)</div>',
            r'<div[^>]*class="pages_content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                # Strip HTML tags
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
                if len(content) >= 100:
                    return content[:10000]  # Cap at 10K chars

        # Fallback: extract all text between <body> tags
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = re.sub(r'<script[^>]*>.*?</script>', '', body_match.group(1), flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'\s+', ' ', content).strip()
            if len(content) >= 100:
                return content[:10000]

    except Exception:
        pass
    return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch full text for ChinaTax documents")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("ChinaTax Detail Fetch: snippet → full text")
    print(f"Batch: {args.batch_size}, Max: {args.max_batches}")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Find LawOrRegulation nodes with short content (snippet-only)
    r = conn.execute("""
        MATCH (n:LawOrRegulation)
        WHERE n.sourceUrl IS NOT NULL AND n.sourceUrl STARTS WITH 'http'
          AND (n.fullText IS NULL OR size(n.fullText) < 200)
          AND n.title IS NOT NULL AND size(n.title) >= 5
        RETURN n.id, n.title, n.sourceUrl, size(n.fullText)
        LIMIT 50000
    """)

    candidates = []
    while r.has_next():
        row = r.get_next()
        candidates.append({
            "id": str(row[0]),
            "title": str(row[1] or ""),
            "url": str(row[2] or ""),
            "current_len": row[3] or 0,
        })

    print(f"\nCandidates for detail fetch: {len(candidates):,}")

    if args.dry_run:
        print(f"[DRY RUN] Would fetch full text for {min(len(candidates), args.batch_size * args.max_batches):,} documents")
        for c in candidates[:5]:
            print(f"  {c['id'][:15]} | {c['title'][:40]} | current: {c['current_len']} chars | {c['url'][:50]}")
        del conn; del db
        return

    if not candidates:
        print("No candidates found.")
        del conn; del db
        return

    # Fetch full text in batches
    updated = 0
    failed = 0
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        total = min(len(candidates), args.batch_size * args.max_batches)
        for i, doc in enumerate(candidates[:total]):
            if i > 0 and i % args.batch_size == 0:
                print(f"  ... {i:,} / {total:,} ({updated} updated, {failed} failed)")

            full_text = fetch_article_text(client, doc["url"])
            if full_text and len(full_text) > doc["current_len"]:
                # Update node in KuzuDB
                try:
                    safe_text = full_text.replace("'", "''")[:10000]
                    conn.execute(
                        f"MATCH (n:LawOrRegulation) WHERE n.id = $id SET n.fullText = $text",
                        parameters={"id": doc["id"], "text": safe_text},
                    )
                    updated += 1
                except Exception:
                    failed += 1
            else:
                failed += 1

            # Polite delay
            time.sleep(3)

    print(f"\n{'='*60}")
    print(f"Detail fetch DONE: {updated:,} updated, {failed:,} failed out of {total:,}")

    del conn
    del db
    print("Checkpoint done")


if __name__ == "__main__":
    main()
