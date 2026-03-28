#!/usr/bin/env python3
"""Backfill empty LawOrRegulation fullText using Gemini 2.5 Flash Lite.

For LR nodes that have a title but empty/short fullText (e.g. anti-bot blocked pages),
generate authoritative content based on the title + regulation metadata.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/lr_content_backfill.py --max-batches 200
    sudo systemctl start kg-api
"""
import kuzu
import os
import sys
import time
import json
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
from llm_client import llm_generate_json


def call_gemini(titles_and_meta: list[dict], api_key: str = "") -> list[str]:
    """Generate authoritative content for a batch of LR titles via Poe API."""
    items = "\n".join([
        f"{i+1}. {d['title']} (发文机关: {d['authority']}, 类型: {d['type']})"
        for i, d in enumerate(titles_and_meta)
    ])
    prompt = (
        "你是中国财税法规专家。为以下法规文件生成权威摘要（每条 100-300 字）。\n"
        "内容要求：核心要点、适用范围、关键条款、实务影响。\n"
        "返回 JSON 数组，每个元素为一段摘要文本。\n\n"
        f"{items}"
    )

    result = llm_generate_json(prompt, temperature=0.3, max_tokens=4096)
    if isinstance(result, list):
        return [str(c) for c in result]
    return []


def main():
    parser = argparse.ArgumentParser(description="Backfill empty LR fullText via Gemini")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-batches", type=int, default=200)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    print("=" * 60)
    print(f"LR Content Backfill ({args.max_batches} batches x {args.batch_size})")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    r = conn.execute(
        "MATCH (n:LawOrRegulation) "
        "WHERE n.title IS NOT NULL AND size(n.title) >= 5 "
        "AND (n.fullText IS NULL OR size(n.fullText) < 200) "
        "RETURN count(n)"
    )
    empty_count = r.get_next()[0]
    print(f"LR needing content: {empty_count:,}")

    total_updated = 0
    total_errors = 0
    start_time = time.time()

    for batch_num in range(args.max_batches):
        r = conn.execute(
            "MATCH (n:LawOrRegulation) "
            "WHERE n.title IS NOT NULL AND size(n.title) >= 5 "
            "AND (n.fullText IS NULL OR size(n.fullText) < 200) "
            "RETURN n.id, n.title, n.issuingAuthority, n.regulationType "
            f"LIMIT {args.batch_size}"
        )
        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({
                "id": str(row[0]),
                "title": str(row[1]),
                "authority": str(row[2] or ""),
                "type": str(row[3] or ""),
            })

        if not batch:
            print("  No more empty LR to process")
            break

        try:
            contents = call_gemini(batch, api_key)
        except HTTPError as e:
            total_errors += 1
            if e.code == 429:
                print("  Rate limited, sleeping 30s...")
                time.sleep(30)
            continue
        except Exception as e:
            total_errors += 1
            print(f"  Error: {str(e)[:80]}")
            time.sleep(2)
            continue

        for item, content in zip(batch, contents[:len(batch)]):
            if not content or len(content) < 50:
                continue
            try:
                conn.execute(
                    "MATCH (n:LawOrRegulation) WHERE n.id = $id SET n.fullText = $text",
                    {"id": item["id"], "text": content}
                )
                total_updated += 1
            except Exception:
                total_errors += 1

        if (batch_num + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (batch_num + 1) / (elapsed / 60) if elapsed > 0 else 0
            remaining = (args.max_batches - batch_num - 1) / rate if rate > 0 else 0
            print(
                f"  Batch {batch_num + 1}/{args.max_batches}: "
                f"+{total_updated} updated, {total_errors} errors, "
                f"{rate:.1f} batches/min, ETA {remaining:.0f}min"
            )

        time.sleep(0.5)

    elapsed = time.time() - start_time
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]

    print(f"\n{'='*60}")
    print(f"LR Content Backfill Done ({elapsed:.0f}s)")
    print(f"  Updated: {total_updated:,}")
    print(f"  Errors: {total_errors:,}")
    print(f"  Graph: {nodes:,} nodes / {edges:,} edges / density {edges/nodes:.3f}")

    del conn; del db


if __name__ == "__main__":
    main()
