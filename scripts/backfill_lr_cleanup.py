#!/usr/bin/env python3
"""Backfill content for lr_cleanup KU nodes via Gemini LLM.

These 32,765 nodes have titles but empty content. Titles are financial/tax
terms that serve as natural prompts for content generation.

Two modes:
  --generate: Generate content to JSON (no DB needed, can run while DB is locked)
  --ingest:   Write generated content back to KuzuDB

Run on kg-node:
    # Phase 1: Generate (parallel safe, no DB lock)
    /home/kg/kg-env/bin/python3 -u scripts/backfill_lr_cleanup.py --generate --batch-size 10 --max-batches 3300

    # Phase 2: Ingest (needs DB lock)
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/backfill_lr_cleanup.py --ingest
    sudo systemctl start kg-api
"""
import argparse
import json
import logging
import os
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backfill")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
OUTPUT_DIR = "/home/kg/cognebula-enterprise/data/backfill"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "lr_cleanup_content.jsonl")


def _load_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        for env_path in ["/home/kg/cognebula-enterprise/.env", "/home/kg/.env"]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            key = line.strip().split("=", 1)[1]
    return key


GEMINI_API_KEY = _load_api_key()  # kept for legacy reference
from llm_client import llm_generate

# Type-specific prompt templates
TYPE_PROMPTS = {
    "FAQ": "用150-400字中文回答以下财税问题。引用具体法规条款。直接回答，不加标题。\n\n问题：{title}",
    "思维导图": "用150-300字中文解释以下财税概念的核心要点（定义、关键规则、常见误区）。直接输出，不加标题。\n\n概念：{title}",
    "考试": "用200-400字中文解答以下注册会计师/税务师考试知识点。包含定义、计算公式或关键条件。直接输出。\n\n知识点：{title}",
    "百科": "用150-300字中文解释以下财务/税务/会计术语的定义和实务要点。直接输出。\n\n术语：{title}",
    "模板": "用150-300字中文说明以下财务模板/表格的用途、填写要点和注意事项。直接输出。\n\n模板：{title}",
    "知识": "用150-300字中文解释以下财税知识点的核心内容。直接输出。\n\n知识点：{title}",
    "参考": "用100-200字中文概述以下参考资料的主要内容和适用场景。直接输出。\n\n参考：{title}",
    "其他": "用150-300字中文解释以下内容。直接输出。\n\n主题：{title}",
}


def _call_gemini_batch(items: list[dict]) -> list[dict]:
    """Generate content for a batch of items in a single Gemini call."""
    lines = []
    for i, item in enumerate(items):
        tp = item.get("type", "其他")
        lines.append(f"[{i+1}] ({tp}) {item['title']}")

    prompt = f"""你是中国财税领域专家。请为以下 {len(items)} 个知识点各生成一段简明解释。

{chr(10).join(lines)}

要求：
1. 每段 150-400 字中文
2. 尽量引用具体法规或准则
3. 用 [1] [2] [3] ... 编号分隔
4. 直接输出，不加额外标题"""

    try:
        raw = llm_generate(prompt, max_tokens=8000, temperature=0.3)
        if raw.startswith("[ERROR]"):
            log.warning("LLM call failed: %s", raw)
            return []
        return _parse_batch(raw, items)
    except Exception as e:
        log.warning("LLM call failed: %s", e)
    return []


def _parse_batch(raw: str, items: list[dict]) -> list[dict]:
    """Parse numbered sections from Gemini response."""
    import re
    results = []
    sections = re.split(r'\[(\d+)\]', raw)
    for j in range(1, len(sections) - 1, 2):
        try:
            idx = int(sections[j]) - 1
            content = sections[j + 1].strip()
            if idx < len(items) and len(content) >= 80:
                results.append({
                    "id": items[idx]["id"],
                    "content": content[:5000],
                })
        except (ValueError, IndexError):
            continue
    return results


def generate(batch_size: int = 10, max_batches: int = 3300):
    """Generate content to JSONL file (no DB write)."""
    import kuzu

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load existing generated IDs to resume
    done_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
    log.info("Already generated: %d", len(done_ids))

    # Read all lr_cleanup nodes needing content
    db = kuzu.Database(DB_PATH, read_only=True)
    conn = kuzu.Connection(db)

    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.source = 'lr_cleanup' AND (k.content IS NULL OR size(k.content) < 50) "
        "RETURN k.id, k.title, k.type"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        kid = str(row[0])
        if kid not in done_ids:
            items.append({"id": kid, "title": str(row[1] or ""), "type": str(row[2] or "其他")})

    del conn
    del db
    log.info("To generate: %d items", len(items))

    # Generate in batches
    t0 = time.time()
    total_generated = 0
    outf = open(OUTPUT_FILE, "a", encoding="utf-8")

    for batch_idx in range(min(max_batches, (len(items) + batch_size - 1) // batch_size)):
        batch = items[batch_idx * batch_size: (batch_idx + 1) * batch_size]
        if not batch:
            break

        results = _call_gemini_batch(batch)
        for r in results:
            outf.write(json.dumps(r, ensure_ascii=False) + "\n")
            total_generated += 1

        if (batch_idx + 1) % 50 == 0:
            outf.flush()
            elapsed = time.time() - t0
            rate = total_generated / elapsed * 3600
            log.info("  Batch %d/%d: +%d generated (%.0f/hr)",
                     batch_idx + 1, max_batches, total_generated, rate)

        time.sleep(0.5)  # Rate limit

    outf.close()
    elapsed = time.time() - t0
    log.info("Generation done: +%d content in %.0fs", total_generated, elapsed)


def ingest():
    """Write generated content back to KuzuDB."""
    import kuzu

    if not os.path.exists(OUTPUT_FILE):
        log.error("No generated content. Run --generate first.")
        return

    items = []
    with open(OUTPUT_FILE) as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    log.info("Content to ingest: %d", len(items))

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    r = conn.execute("MATCH (n) RETURN count(n)")
    before = r.get_next()[0]

    updated = 0
    errors = 0
    for item in items:
        try:
            conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                {"id": item["id"], "c": item["content"]}
            )
            updated += 1
        except Exception:
            errors += 1

        if updated % 1000 == 0 and updated > 0:
            log.info("  Updated: %d/%d", updated, len(items))

    log.info("Ingest done: %d updated, %d errors", updated, errors)
    del conn
    del db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate content to JSONL")
    parser.add_argument("--ingest", action="store_true", help="Write content to KuzuDB")
    parser.add_argument("--batch-size", type=int, default=10, help="Items per Gemini call")
    parser.add_argument("--max-batches", type=int, default=3300, help="Max batches")
    args = parser.parse_args()

    if args.generate:
        generate(args.batch_size, args.max_batches)
    elif args.ingest:
        ingest()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
