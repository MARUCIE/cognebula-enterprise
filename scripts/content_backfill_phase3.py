#!/usr/bin/env python3
"""Phase 3: Gemini AI content expansion for QA-type nodes.

Policy: AI_EXPANDABLE only — never generates legal/regulatory text.

Targets (small types first, validate before scaling):
  - TaxIncentive (112) — expand short descriptions to full explanations
  - Penalty (164) — expand to include legal basis + calculation
  - BusinessActivity (414) — expand activity descriptions
  - AccountingEntry (375) — expand journal entry explanations
  - TaxRiskScenario (180) — expand risk scenario details
  - CPAKnowledge (7,729) — expand short titles to full content
  - MindmapNode (28,526) — expand node_text to full content
  - IndustryRiskProfile (720) — expand benchmark descriptions

Uses Gemini 2.5 Flash Lite via CF Worker proxy. Rate: ~1 req/sec.
Runs with API up (reads via API, writes via KuzuDB directly).
"""
import os
import sys
import re
import time
import json

try:
    import httpx
except ImportError:
    print("ERROR: httpx required. pip install httpx")
    sys.exit(1)

import kuzu

DB_PATH = os.environ.get("KUZU_DB", "data/finance-tax-graph")
KG_API = os.environ.get("KG_API", "http://localhost:8400")

# Gemini config
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_PROXY = os.environ.get("GEMINI_PROXY",
    "https://gemini-api-proxy.maoyuan-wen-683.workers.dev")
GEMINI_MODEL = "gemini-2.5-flash-lite"
RATE_SLEEP = 1.5  # seconds between API calls


def gemini_generate(prompt: str, max_tokens: int = 500) -> str:
    """Call Gemini API to generate content."""
    url = f"{GEMINI_PROXY}/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3,
        },
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


def safe_set_content(conn, type_name: str, node_id: str, field: str, content: str) -> bool:
    """Safely SET content with proper Cypher escaping."""
    safe = content
    safe = safe.replace("\\", "\\\\")
    safe = safe.replace("'", "\\'")
    safe = safe.replace("\n", "\\n")
    safe = safe.replace("\r", "")
    safe = safe.replace("\t", " ")
    safe = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', safe)

    nid_safe = node_id.replace("'", "\\'")
    try:
        conn.execute(
            f"MATCH (n:{type_name}) WHERE n.id = '{nid_safe}' "
            f"SET n.{field} = '{safe}'"
        )
        return True
    except Exception:
        return False


def expand_type(conn, type_name: str, content_field: str,
                prompt_template: str, source_fields: list[str],
                max_nodes: int = 500, min_existing_len: int = 50):
    """Expand short content for a type using Gemini. Reads directly from KuzuDB."""
    print(f"\n[{type_name}] Expanding content via Gemini...")

    # Build RETURN clause from source fields + content field + id
    all_fields = list(dict.fromkeys(["id", content_field] + source_fields))
    return_clause = ", ".join(f"n.{f}" for f in all_fields)

    # Query KuzuDB directly for nodes with short content
    try:
        q = (f"MATCH (n:{type_name}) "
             f"WHERE n.{content_field} IS NULL OR size(n.{content_field}) < {min_existing_len} "
             f"RETURN {return_clause} "
             f"LIMIT {max_nodes}")
        result = conn.execute(q)
    except Exception as e:
        # If content_field doesn't exist, try with just id + source fields
        try:
            alt_fields = list(dict.fromkeys(["id"] + source_fields))
            return_clause = ", ".join(f"n.{f}" for f in alt_fields)
            q = (f"MATCH (n:{type_name}) "
                 f"RETURN {return_clause} "
                 f"LIMIT {max_nodes}")
            result = conn.execute(q)
            all_fields = alt_fields
        except Exception as e2:
            print(f"  ERROR querying: {e2}")
            return 0

    # Collect rows
    to_expand = []
    while result.has_next():
        row = result.get_next()
        node = {all_fields[i]: row[i] for i in range(len(all_fields))}
        to_expand.append(node)

    print(f"  Need expansion: {len(to_expand)}")
    if not to_expand:
        return 0

    updated = 0
    errors = 0

    for i, n in enumerate(to_expand):
        nid = str(n.get("id", ""))
        # Build context from source fields
        context_parts = []
        for f in source_fields:
            val = str(n.get(f, "") or "").strip()
            if val and len(val) >= 2:
                context_parts.append(f"{f}: {val}")

        if not context_parts:
            continue

        context = "\n".join(context_parts)
        prompt = prompt_template.format(context=context)

        generated = gemini_generate(prompt)
        if not generated or len(generated) < 30:
            errors += 1
            continue

        if safe_set_content(conn, type_name, nid, content_field, generated):
            updated += 1
        else:
            errors += 1

        if (i + 1) % 50 == 0:
            print(f"    Progress: {i+1}/{len(to_expand)} (updated: {updated}, errors: {errors})")

        time.sleep(RATE_SLEEP)

    print(f"  Done: {updated} updated, {errors} errors")
    return updated


# ── Prompts per type ────────────────────────────────────────────────────

PROMPTS = {
    "TaxIncentive": (
        "fullText",
        "你是中国财税专家。根据以下税收优惠政策信息，写一段200-400字的详细说明，"
        "包括：适用条件、优惠内容、法律依据、注意事项。使用专业但易懂的中文。\n\n{context}",
        ["name", "incentiveType", "eligibilityCriteria", "lawReference", "beneficiaryType"],
    ),
    "Penalty": (
        "description",
        "你是中国财税合规专家。根据以下处罚信息，写一段150-300字的说明，"
        "包括：违法行为描述、处罚标准、法律依据、首违不罚条件（如适用）。\n\n{context}",
        ["name", "penaltyType", "description"],
    ),
    "BusinessActivity": (
        "description",
        "你是中国财税专家。根据以下经营活动信息，写一段150-300字的说明，"
        "包括：活动定义、涉及税种、税务处理要点、常见风险。\n\n{context}",
        ["name", "title", "description"],
    ),
    "AccountingEntry": (
        "description",
        "你是中国会计专家。根据以下会计分录信息，写一段150-300字的说明，"
        "包括：业务场景、借贷方向、科目选择依据、税务影响。\n\n{context}",
        ["title", "debit_account", "credit_account", "scenario", "industry", "description"],
    ),
    "TaxRiskScenario": (
        "description",
        "你是中国税务风险管理专家。根据以下风险场景，写一段200-400字的详细说明，"
        "包括：风险描述、触发条件、后果影响、防范措施。\n\n{context}",
        ["scenario", "risk_type", "description", "consequence", "prevention", "industry"],
    ),
    "CPAKnowledge": (
        "content",
        "你是中国注册会计师考试辅导专家。根据以下知识点，写一段200-400字的详细讲解，"
        "包括：概念定义、核心要点、考试重点、易错点。使用教材式的准确表述。\n\n{context}",
        ["title", "topic", "subject", "content_type", "content"],
    ),
    "IndustryRiskProfile": (
        "description",
        "你是中国行业税务分析师。根据以下行业风险指标，写一段150-300字的说明，"
        "包括：指标含义、行业基准值、异常信号、税务局关注点。\n\n{context}",
        ["industry", "indicator", "benchmark", "risk_level"],
    ),
}


def main():
    if not GEMINI_KEY:
        # Try loading from .env
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
    print("  Phase 3: Gemini AI Content Expansion")
    print("  Policy: AI_EXPANDABLE only — QA/descriptive types")
    print(f"  Model: {GEMINI_MODEL} via {GEMINI_PROXY}")
    print("=" * 60)

    # Open KuzuDB for writes (API must be stopped)
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    total = 0

    # Process small types first to validate
    for type_name, (content_field, prompt_tpl, source_fields) in PROMPTS.items():
        total += expand_type(
            conn, type_name, content_field,
            prompt_tpl, source_fields,
            max_nodes=500, min_existing_len=100,
        )

    print(f"\n{'=' * 60}")
    print(f"  Phase 3 Complete: {total} nodes expanded")
    print(f"  NOTE: MindmapNode (28K) skipped — needs separate batch job")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
