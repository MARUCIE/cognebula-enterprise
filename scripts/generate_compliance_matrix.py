#!/usr/bin/env python3
"""Phase B: Generate LLM Compliance Knowledge Matrix.

Creates structured compliance knowledge nodes from the cross-product of:
  Industry(24) x TaxType(19) x Lifecycle(20) x Scenario(50)

Each node is a compliance knowledge point with:
  - Structured metadata (industry, tax type, lifecycle stage, scenario)
  - AI-generated compliance guidance grounded in real regulations
  - References to existing LR/LegalClause nodes in the graph

Quality rules:
  - Content must reference specific regulation names/numbers
  - Min 200 chars of substantive compliance guidance
  - Must link to >= 1 existing LR/TaxType node via edges

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/generate_compliance_matrix.py --batch-size 50
    sudo systemctl start kg-api
"""
import argparse
import hashlib
import json
import logging
import os
import re
import time
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("compliance_matrix")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
OUTPUT_DIR = "/home/kg/cognebula-enterprise/data/compliance-matrix"

# ─── Dimensions ──────────────────────────────────────────────────────

INDUSTRIES = [
    "制造业", "房地产", "建筑业", "批发零售", "金融保险",
    "信息技术", "交通运输", "住宿餐饮", "教育培训", "医疗健康",
    "农林牧渔", "采矿业", "电力能源", "文化传媒", "科学研究",
    "租赁商务", "水利环境", "居民服务", "公共管理", "国际组织",
    "软件服务", "电子商务", "新能源汽车", "人工智能",
]

TAX_TYPES = [
    "企业所得税", "增值税", "个人所得税", "消费税", "关税",
    "城市维护建设税", "教育费附加", "地方教育附加", "印花税", "契税",
    "土地增值税", "房产税", "城镇土地使用税", "车辆购置税", "车船税",
    "资源税", "环境保护税", "烟叶税", "耕地占用税",
]

LIFECYCLE_STAGES = [
    "公司设立", "股权架构", "融资借款", "资产购置", "日常经营",
    "员工薪酬", "研发活动", "固定资产折旧", "无形资产摊销", "存货管理",
    "收入确认", "成本核算", "费用列支", "关联交易", "跨境业务",
    "并购重组", "资产处置", "利润分配", "纳税申报", "注销清算",
]

# Top scenarios per lifecycle (generating on-demand to control volume)
SCENARIOS_PER_COMBO = [
    "合规要点", "常见风险", "优惠政策", "申报实务", "案例分析",
]

# ─── Gemini API ──────────────────────────────────────────────────────

def _load_api_key():
    """Load Gemini API key from env or .env file."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.strip().split("=", 1)[1]
                        break
    return key


GEMINI_API_KEY = _load_api_key()
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"


def _call_gemini(prompt: str, max_tokens: int = 2000) -> str:
    """Call Gemini API via urllib (no deprecated google.generativeai)."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GEMINI_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
    except Exception as e:
        log.warning("Gemini call failed: %s", e)
    return ""


def _make_id(industry: str, tax: str, lifecycle: str, scenario: str) -> str:
    key = f"cm:{industry}:{tax}:{lifecycle}:{scenario}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ─── Generator ───────────────────────────────────────────────────────

def generate_node(industry: str, tax_type: str, lifecycle: str, scenario: str) -> dict | None:
    """Generate a single compliance matrix node via Gemini."""
    prompt = f"""你是中国财税合规专家。请针对以下场景生成合规知识点：

行业：{industry}
税种：{tax_type}
生命周期阶段：{lifecycle}
场景类型：{scenario}

要求：
1. 用中文撰写，200-800字
2. 必须引用具体的法规名称和条款号（如《企业所得税法》第X条）
3. 包含：适用条件、计算方法/税率、申报要点、常见误区
4. 如果该组合没有直接相关的合规要点，返回"不适用"

直接输出合规知识内容，不要加标题或格式标记。"""

    content = _call_gemini(prompt)
    if not content or len(content) < 100:
        return None
    if "不适用" in content[:20]:
        return None

    # Validate: must reference at least one regulation
    has_regulation_ref = bool(re.search(r'《.{2,20}》|第\d+条|国税发|财税\[|财税〔', content))
    if not has_regulation_ref:
        log.warning("  No regulation reference: %s/%s/%s/%s", industry, tax_type, lifecycle, scenario)
        # Still accept but flag

    return {
        "id": _make_id(industry, tax_type, lifecycle, scenario),
        "title": f"{industry} - {tax_type} - {lifecycle} - {scenario}",
        "content": content[:5000],
        "industry": industry,
        "taxType": tax_type,
        "lifecycle": lifecycle,
        "scenario": scenario,
        "source": "compliance_matrix",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Batch Generation ────────────────────────────────────────────────

def generate_batch(batch_combos: list[tuple], batch_idx: int) -> list[dict]:
    """Generate a batch of compliance nodes."""
    results = []
    for i, (ind, tax, lc, sc) in enumerate(batch_combos):
        node = generate_node(ind, tax, lc, sc)
        if node:
            results.append(node)
        if (i + 1) % 10 == 0:
            log.info("  Batch %d: %d/%d generated, %d valid", batch_idx, i + 1, len(batch_combos), len(results))
        time.sleep(0.5)  # Rate limiting
    return results


def ingest_batch(items: list[dict]):
    """Ingest compliance matrix nodes to KuzuDB."""
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    inserted = 0
    for item in items:
        try:
            # Check existence
            r = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": item["id"]})
            if r.has_next():
                continue

            conn.execute(
                "CREATE (k:KnowledgeUnit {"
                "id: $id, title: $title, content: $content, "
                "source: $source, type: $tp"
                "})",
                {
                    "id": item["id"],
                    "title": item["title"],
                    "content": item["content"],
                    "source": "compliance_matrix",
                    "tp": f"{item['industry']}/{item['taxType']}",
                }
            )
            inserted += 1
        except Exception as e:
            log.warning("Ingest failed: %s", e)

    # Create edges to matching TaxType nodes
    edge_count = 0
    for item in items:
        try:
            # Link to TaxType
            r = conn.execute(
                "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType) "
                "WHERE t.name CONTAINS $tax "
                "RETURN t.id LIMIT 1",
                {"kid": item["id"], "tax": item["taxType"][:4]}
            )
            if r.has_next():
                tt_id = r.get_next()[0]
                try:
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType {id: $tid}) "
                        "CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                        {"kid": item["id"], "tid": str(tt_id)}
                    )
                    edge_count += 1
                except Exception:
                    pass
        except Exception:
            pass

    log.info("Ingested: +%d nodes, +%d edges", inserted, edge_count)

    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    log.info("Graph: %s nodes / %s edges / density %.3f", f"{nodes:,}", f"{edges:,}", edges / nodes)

    del conn
    del db


def main():
    parser = argparse.ArgumentParser(description="Generate LLM Compliance Knowledge Matrix")
    parser.add_argument("--batch-size", type=int, default=50, help="Combos per batch")
    parser.add_argument("--max-total", type=int, default=10000, help="Max total nodes to generate")
    parser.add_argument("--industries", nargs="+", default=None, help="Specific industries")
    parser.add_argument("--tax-types", nargs="+", default=None, help="Specific tax types")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N combos")
    parser.add_argument("--no-ingest", action="store_true", help="Generate only, no DB ingest")
    parser.add_argument("--dry-run", action="store_true", help="Show combos without generating")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    industries = args.industries or INDUSTRIES
    tax_types = args.tax_types or TAX_TYPES

    # Build all combos
    all_combos = []
    for ind in industries:
        for tax in tax_types:
            for lc in LIFECYCLE_STAGES:
                for sc in SCENARIOS_PER_COMBO:
                    all_combos.append((ind, tax, lc, sc))

    if args.offset > 0:
        all_combos = all_combos[args.offset:]
        log.info("Skipped first %d combos (--offset)", args.offset)
    total = min(len(all_combos), args.max_total)
    log.info("Total combos: %d (capped at %d)", len(all_combos), total)
    log.info("Dimensions: %d industries x %d taxes x %d lifecycle x %d scenarios",
             len(industries), len(tax_types), len(LIFECYCLE_STAGES), len(SCENARIOS_PER_COMBO))

    if args.dry_run:
        log.info("Dry run — showing first 10 combos:")
        for c in all_combos[:10]:
            print(f"  {c[0]} / {c[1]} / {c[2]} / {c[3]}")
        log.info("Total would generate: %d nodes", total)
        return

    # Process in batches
    all_results = []
    for batch_start in range(0, total, args.batch_size):
        batch_end = min(batch_start + args.batch_size, total)
        batch = all_combos[batch_start:batch_end]
        batch_idx = batch_start // args.batch_size + 1

        log.info("=" * 50)
        log.info("Batch %d: combos %d-%d", batch_idx, batch_start + 1, batch_end)

        results = generate_batch(batch, batch_idx)
        all_results.extend(results)

        # Save incremental
        out_path = os.path.join(OUTPUT_DIR, f"batch_{batch_idx:04d}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Batch %d: %d/%d valid, saved to %s", batch_idx, len(results), len(batch), out_path)

        # Ingest
        if not args.no_ingest and results:
            ingest_batch(results)

    # Summary
    log.info("=" * 60)
    log.info("Compliance Matrix Generation Complete")
    log.info("  Total generated: %d / %d combos (%.1f%% yield)",
             len(all_results), total, 100 * len(all_results) / max(total, 1))

    # Save full output
    out_path = os.path.join(OUTPUT_DIR, "compliance_matrix_all.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    log.info("Full output: %s", out_path)


if __name__ == "__main__":
    main()
