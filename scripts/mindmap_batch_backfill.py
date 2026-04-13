#!/usr/bin/env python3
"""Batch backfill MindmapNode content using Gemini 2.5 Flash Lite.

Processes 2000 nodes per run. Designed to be called in a loop with process
restart between runs to prevent Python heap growth.

Run on kg-node (API must be stopped):
    sudo systemctl stop kg-api
    for run in $(seq 1 13); do
        echo "=== Run $run ==="
        /home/kg/kg-env/bin/python3 scripts/mindmap_batch_backfill.py
    done
    sudo systemctl start kg-api
"""
import kuzu
import json
import os
import sys
import time
from urllib.request import Request, urlopen

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
BATCH_SIZE = 20
LIMIT = 2000


def call_gemini(prompt: str) -> str:
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 16384,
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }).encode()
    for attempt in range(3):
        try:
            req = Request(GEMINI_URL, data=payload,
                          headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                print(f"  WARN: Gemini failed: {e}")
                return ""


def safe_str(val) -> str:
    return str(val or "").replace("\\", "\\\\").replace("'", "\\'")


def main():
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    r = conn.execute(
        "MATCH (n:MindmapNode) "
        "WHERE n.content IS NULL OR size(n.content) < 20 "
        "RETURN n.id, n.node_text, n.category, n.parent_text "
        f"LIMIT {LIMIT}"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        nid, text, cat, parent = row[0], row[1] or "", row[2] or "", row[3] or ""
        if nid and text:
            ctx = f"[{cat}] {text}"
            if parent:
                ctx += f" (上级: {parent})"
            items.append({"id": nid, "prompt_text": ctx})

    print(f"  Found {len(items)} remaining nodes")
    if len(items) == 0:
        print("  All done!")
        del conn, db
        sys.exit(0)

    prompt_tpl = (
        "你是中国财税知识专家。对以下每个财税思维导图节点，写一段150-300字的中文说明。"
        "内容要专业准确，包含该主题的核心概念、适用范围、关键要点。"
        "返回一个JSON数组，每个元素是对应节点的说明文字，保持顺序一致。"
        "只输出JSON数组，不要加任何markdown标记。\n\n"
        "节点列表(共{count}个):\n{entries}"
    )

    count = 0
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        entries = "\n".join(
            f"{j+1}. {item['prompt_text']}" for j, item in enumerate(batch)
        )
        prompt = prompt_tpl.format(count=len(batch), entries=entries)
        result = call_gemini(prompt)
        if not result:
            continue
        try:
            contents = json.loads(result)
            if not isinstance(contents, list):
                continue
        except json.JSONDecodeError:
            continue

        for j, item in enumerate(batch):
            if j >= len(contents):
                break
            text = str(contents[j]).strip()
            if len(text) < 30:
                continue
            try:
                conn.execute(
                    f"MATCH (n:MindmapNode) WHERE n.id = '{safe_str(item['id'])}' "
                    f"SET n.content = '{safe_str(text)}'"
                )
                count += 1
            except Exception as e:
                print(f"  WARN: {e}")

        if (i // BATCH_SIZE + 1) % 5 == 0:
            conn.execute("CHECKPOINT")
            print(f"  ... {count} updated so far")

        time.sleep(0.5)

    conn.execute("CHECKPOINT")
    print(f"  Updated {count}/{len(items)} nodes")
    del conn, db


if __name__ == "__main__":
    main()
