#!/usr/bin/env python3
"""Phase 3b: Remaining QA types — MindmapNode + IndustryRiskProfile.

MindmapNode (28K): expand node_text + parent_text into full content.
  - Only first 500 batch; integrate into M3 for daily processing.
IndustryRiskProfile (720): expand benchmark+indicator into description.
  - ALTER TABLE already applied (description STRING).

Runs with API stopped (KuzuDB direct access).
"""
import os
import sys
import re
import time
import json

try:
    import httpx
except ImportError:
    print("ERROR: httpx required")
    sys.exit(1)

import kuzu

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_PROXY = os.environ.get("GEMINI_PROXY",
    "https://gemini-api-proxy.maoyuan-wen-683.workers.dev")
GEMINI_MODEL = "gemini-2.5-flash-lite"
RATE_SLEEP = 1.5


def gemini_generate(prompt: str, max_tokens: int = 500) -> str:
    url = f"{GEMINI_PROXY}/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }
    try:
        r = httpx.post(f"{url}?key={GEMINI_KEY}", json=payload, timeout=30)
        if r.status_code != 200:
            return ""
        data = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0].get("text", "").strip() if parts else ""
    except Exception:
        return ""


def safe_set(conn, type_name, node_id, field, content):
    safe = content.replace("\\", "\\\\").replace("'", "\\'")
    safe = safe.replace("\n", "\\n").replace("\r", "").replace("\t", " ")
    safe = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', safe)
    nid = node_id.replace("'", "\\'")
    try:
        conn.execute(f"MATCH (n:{type_name}) WHERE n.id = '{nid}' SET n.{field} = '{safe}'")
        return True
    except:
        return False


def expand_mindmap(conn, batch_size=500):
    """Expand MindmapNode — needs ALTER TABLE first to add content field."""
    print("\n[MindmapNode] Checking if content field exists...")

    # First check if we need to add a content field
    try:
        conn.execute("MATCH (n:MindmapNode) WHERE n.content IS NOT NULL RETURN count(n)")
        print("  content field exists")
        content_field = "content"
    except:
        print("  Adding content field via ALTER TABLE...")
        try:
            conn.execute('ALTER TABLE MindmapNode ADD content STRING DEFAULT ""')
            print("  OK: content field added")
            content_field = "content"
        except Exception as e:
            print(f"  ERROR adding field: {e}")
            return 0

    # Query nodes with short content
    q = (f"MATCH (n:MindmapNode) "
         f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < 50 "
         f"RETURN n.id, n.node_text, n.parent_text, n.category, n.depth "
         f"LIMIT {batch_size}")
    result = conn.execute(q)

    to_expand = []
    while result.has_next():
        row = result.get_next()
        to_expand.append({
            "id": str(row[0] or ""),
            "node_text": str(row[1] or ""),
            "parent_text": str(row[2] or ""),
            "category": str(row[3] or ""),
            "depth": str(row[4] or ""),
        })

    print(f"  Need expansion: {len(to_expand)}")
    if not to_expand:
        return 0

    updated = 0
    errors = 0

    for i, n in enumerate(to_expand):
        context = f"主题: {n['node_text']}"
        if n['parent_text']:
            context += f"\n上级主题: {n['parent_text']}"
        if n['category']:
            context += f"\n分类: {n['category']}"

        prompt = (
            "你是中国财税知识专家。根据以下知识导图节点信息，"
            "写一段150-300字的详细说明，解释这个概念的含义、"
            "适用场景、关键要点。使用专业准确的中文。\n\n" + context
        )

        generated = gemini_generate(prompt)
        if generated and len(generated) >= 30:
            if safe_set(conn, "MindmapNode", n["id"], content_field, generated):
                updated += 1
            else:
                errors += 1
        else:
            errors += 1

        if (i + 1) % 50 == 0:
            print(f"    Progress: {i+1}/{len(to_expand)} (updated: {updated}, errors: {errors})")
        time.sleep(RATE_SLEEP)

    print(f"  Done: {updated} updated, {errors} errors")
    return updated


def expand_industry_risk(conn):
    """Expand IndustryRiskProfile descriptions."""
    print("\n[IndustryRiskProfile] Expanding descriptions...")

    q = ("MATCH (n:IndustryRiskProfile) "
         "WHERE n.description IS NULL OR size(n.description) < 50 "
         "RETURN n.id, n.industry, n.indicator, n.benchmark, n.risk_level "
         "LIMIT 720")
    result = conn.execute(q)

    to_expand = []
    while result.has_next():
        row = result.get_next()
        to_expand.append({
            "id": str(row[0] or ""),
            "industry": str(row[1] or ""),
            "indicator": str(row[2] or ""),
            "benchmark": str(row[3] or ""),
            "risk_level": str(row[4] or ""),
        })

    print(f"  Need expansion: {len(to_expand)}")
    if not to_expand:
        return 0

    updated = 0
    errors = 0

    for i, n in enumerate(to_expand):
        context = "\n".join(f"{k}: {v}" for k, v in n.items() if k != "id" and v)
        prompt = (
            "你是中国行业税务分析师。根据以下行业风险指标，写一段150-300字的说明，"
            "包括：指标含义、行业基准值、异常信号、税务局关注点。\n\n" + context
        )

        generated = gemini_generate(prompt)
        if generated and len(generated) >= 30:
            if safe_set(conn, "IndustryRiskProfile", n["id"], "description", generated):
                updated += 1
            else:
                errors += 1
        else:
            errors += 1

        if (i + 1) % 50 == 0:
            print(f"    Progress: {i+1}/{len(to_expand)} (updated: {updated}, errors: {errors})")
        time.sleep(RATE_SLEEP)

    print(f"  Done: {updated} updated, {errors} errors")
    return updated


def main():
    if not GEMINI_KEY:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip()
                        globals()["GEMINI_KEY"] = os.environ["GEMINI_API_KEY"]
                        break

    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    print("=" * 60)
    print("  Phase 3b: Remaining QA Types")
    print(f"  Model: {GEMINI_MODEL}")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    total = 0
    total += expand_mindmap(conn, batch_size=500)
    total += expand_industry_risk(conn)

    print(f"\n{'=' * 60}")
    print(f"  Phase 3b Complete: {total} nodes expanded")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
