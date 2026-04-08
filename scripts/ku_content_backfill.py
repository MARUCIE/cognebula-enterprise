#!/usr/bin/env python3
"""Backfill empty KnowledgeUnit content using Gemini 2.5 Flash Lite.

M3 L1 Deepening: For KU nodes that have a title but empty/short content,
generate meaningful content using LLM based on the title + context.

Pipeline: KuzuDB (read empty KU) → Gemini Flash Lite (generate content) → KuzuDB (UPDATE)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/ku_content_backfill.py \
        --batch-size 20 --max-batches 500
    sudo systemctl start kg-api

Cost estimate: ~$0.10 per 1000 KU (Gemini 2.5 Flash Lite, ~200 tokens/KU)
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
from llm_client import llm_generate, llm_generate_json

TAX_KEYWORDS = {
    "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT",
    "消费税": "TT_CONSUMPTION", "关税": "TT_TARIFF",
    "城市维护建设税": "TT_URBAN", "城建税": "TT_URBAN",
    "教育费附加": "TT_EDUCATION", "地方教育附加": "TT_LOCAL_EDU",
    "资源税": "TT_RESOURCE", "土地增值税": "TT_LAND_VAT",
    "房产税": "TT_PROPERTY", "城镇土地使用税": "TT_LAND_USE",
    "车船税": "TT_VEHICLE", "印花税": "TT_STAMP",
    "契税": "TT_CONTRACT", "耕地占用税": "TT_CULTIVATED",
    "烟叶税": "TT_TOBACCO", "环境保护税": "TT_ENV",
    "个税": "TT_PIT", "所得税": "TT_CIT",
}


def call_gemini(titles: list[str], api_key: str = "") -> list[str]:
    """Generate content for a batch of KU titles via Poe API."""
    prompt = (
        "你是中国财税知识专家。对以下每个标题，写一段200-400字的中文详细说明。"
        "包含：概念定义、关键要点、适用场景、注意事项。使用专业准确的表述。"
        "返回一个JSON数组，每个元素是对应标题的说明文字，保持顺序一致。\n\n"
        "标题列表:\n"
    )
    for i, t in enumerate(titles):
        prompt += f"{i+1}. {t}\n"

    result = llm_generate_json(prompt, temperature=0.3, max_tokens=8192)
    if isinstance(result, list):
        return result
    return []


def main():
    parser = argparse.ArgumentParser(description="Backfill empty KU content via Gemini")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--max-batches", type=int, default=500)
    parser.add_argument("--min-content-len", type=int, default=20,
                        help="Minimum content length to consider 'filled'")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    print("=" * 60)
    print(f"M3 KU Content Backfill ({args.max_batches} batches x {args.batch_size} = {args.max_batches * args.batch_size} max)")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Count empty KU with titles
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.title IS NOT NULL AND size(k.title) >= 5 "
        "AND (k.content IS NULL OR size(k.content) < 20) "
        "RETURN count(k)"
    )
    empty_count = r.get_next()[0]
    print(f"Empty KU with titles: {empty_count:,}")

    to_process = min(empty_count, args.max_batches * args.batch_size)
    print(f"Will process: {to_process:,}")

    total_updated = 0
    total_errors = 0
    total_tax_edges = 0
    start_time = time.time()

    for batch_num in range(args.max_batches):
        # Fetch batch of empty KU
        r = conn.execute(
            f"MATCH (k:KnowledgeUnit) "
            f"WHERE k.title IS NOT NULL AND size(k.title) >= 5 "
            f"AND (k.content IS NULL OR size(k.content) < {args.min_content_len}) "
            f"RETURN k.id, k.title "
            f"LIMIT {args.batch_size}"
        )
        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({"id": str(row[0]), "title": str(row[1])})

        if not batch:
            print(f"  No more empty KU to process")
            break

        titles = [item["title"] for item in batch]

        try:
            contents = call_gemini(titles, api_key)
        except HTTPError as e:
            total_errors += 1
            print(f"  Gemini error: {e}")
            time.sleep(5)
            continue
        except Exception as e:
            total_errors += 1
            print(f"  Error: {e}")
            time.sleep(2)
            continue

        if len(contents) != len(batch):
            # Partial result — use what we got
            contents = contents[:len(batch)]

        # Update each KU
        batch_updated = 0
        for item, content in zip(batch, contents):
            if not content or len(str(content)) < 10:
                continue
            content_str = str(content).replace("'", "\\'").replace('"', '\\"')
            try:
                conn.execute(
                    f'MATCH (k:KnowledgeUnit) WHERE k.id = "{item["id"]}" '
                    f"SET k.content = '{content_str}'"
                )
                batch_updated += 1

                # Create KU_ABOUT_TAX edge if tax keyword found
                text = f"{item['title']} {content_str}"
                for kw, tid in TAX_KEYWORDS.items():
                    if kw in text:
                        try:
                            conn.execute(
                                f'MATCH (k:KnowledgeUnit), (t:TaxType) '
                                f'WHERE k.id = "{item["id"]}" AND t.id = "{tid}" '
                                f'CREATE (k)-[:KU_ABOUT_TAX]->(t)'
                            )
                            total_tax_edges += 1
                        except Exception:
                            pass  # duplicate edge or schema issue
                        break
            except Exception as e:
                total_errors += 1

        total_updated += batch_updated

        # Progress report every 10 batches
        if (batch_num + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (batch_num + 1) / (elapsed / 60) if elapsed > 0 else 0
            remaining = (args.max_batches - batch_num - 1) / rate if rate > 0 else 0
            print(
                f"  Batch {batch_num + 1}/{args.max_batches}: "
                f"+{total_updated} updated, {total_errors} errors, "
                f"{rate:.1f} batches/min, ETA {remaining:.0f}min"
            )

        # Rate limit
        time.sleep(0.5)

    # Create additional KU_ABOUT_TAX edges from content
    print(f"\nCreating KU_ABOUT_TAX edges from extracted tax types...")
    print(f"  KU_ABOUT_TAX: +{total_tax_edges}")

    # Checkpoint
    elapsed = time.time() - start_time

    # Final stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.content IS NOT NULL AND size(k.content) >= 20 "
        "RETURN count(k)"
    )
    filled = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    ku_total = r.get_next()[0]

    print(f"\n{'='*60}")
    print(f"KU Content Backfill Done ({elapsed:.0f}s)")
    print(f"  Updated: {total_updated:,} KU nodes")
    print(f"  New edges: +{total_tax_edges}")
    print(f"  KU with content: {filled:,}/{ku_total:,} ({filled/ku_total*100:.0f}%)")
    print(f"  Graph: {nodes:,} nodes / {edges:,} edges / density {edges/nodes:.3f}")
    print("Checkpoint done")

    del conn
    del db


if __name__ == "__main__":
    main()
