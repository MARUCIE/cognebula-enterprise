#!/usr/bin/env python3
"""Fast Compliance Matrix: batch 5 nodes per Gemini call.

5x faster than single-node generation. Same quality.
Uses JSON output mode for structured parsing.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/generate_compliance_matrix_fast.py --max-total 10000 --offset 10000
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
log = logging.getLogger("cm_fast")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
OUTPUT_DIR = "/home/kg/cognebula-enterprise/data/compliance-matrix"

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

SCENARIOS = [
    "合规要点", "常见风险", "优惠政策", "申报实务", "案例分析",
    "税务筹划", "风险防控", "政策变化", "争议处理", "跨区域差异",
    "特殊情形", "减免条件", "计税基础", "扣除标准", "申报期限",
]


def _load_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.strip().split("=", 1)[1]
    return key


GEMINI_API_KEY = _load_api_key()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"


def _call_gemini(prompt: str, max_tokens: int = 8000) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(GEMINI_URL, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
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
    return hashlib.sha256(f"cm:{industry}:{tax}:{lifecycle}:{scenario}".encode()).hexdigest()[:16]


def generate_batch_5(combos: list[tuple]) -> list[dict]:
    """Generate 5 nodes in a single Gemini call."""
    lines = []
    for i, (ind, tax, lc, sc) in enumerate(combos):
        lines.append(f"[{i+1}] 行业={ind}, 税种={tax}, 阶段={lc}, 场景={sc}")

    prompt = f"""你是中国财税合规专家。请一次性为以下 {len(combos)} 个场景各生成一段合规知识点。

{chr(10).join(lines)}

要求：
1. 每段 200-600 字中文
2. 必须引用具体法规（如《企业所得税法》第X条）
3. 包含：适用条件、税率/计算、申报要点
4. 如果不适用，写"不适用"
5. 用 [1] [2] [3] [4] [5] 编号分隔各段

直接输出，不加标题。"""

    raw = _call_gemini(prompt, max_tokens=8000)
    if not raw:
        return []

    # Parse numbered sections
    results = []
    sections = re.split(r'\[(\d+)\]', raw)
    # sections = ['', '1', 'content1', '2', 'content2', ...]
    for j in range(1, len(sections) - 1, 2):
        try:
            idx = int(sections[j]) - 1
            content = sections[j + 1].strip()
            if idx < len(combos) and len(content) >= 100 and "不适用" not in content[:20]:
                ind, tax, lc, sc = combos[idx]
                results.append({
                    "id": _make_id(ind, tax, lc, sc),
                    "title": f"{ind} - {tax} - {lc} - {sc}",
                    "content": content[:5000],
                    "industry": ind, "taxType": tax,
                    "lifecycle": lc, "scenario": sc,
                    "source": "compliance_matrix",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                })
        except (ValueError, IndexError):
            continue

    return results


def ingest_batch(items: list[dict]):
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    inserted = 0
    for item in items:
        try:
            r = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": item["id"]})
            if r.has_next():
                continue
            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, source: $source, type: $tp})",
                {"id": item["id"], "title": item["title"], "content": item["content"],
                 "source": "compliance_matrix", "tp": f"{item['industry']}/{item['taxType']}"}
            )
            inserted += 1
        except Exception:
            pass

    # Edges
    edge_count = 0
    for item in items:
        try:
            r = conn.execute(
                "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType) WHERE t.name CONTAINS $tax RETURN t.id LIMIT 1",
                {"kid": item["id"], "tax": item["taxType"][:4]}
            )
            if r.has_next():
                tt_id = str(r.get_next()[0])
                try:
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType {id: $tid}) CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                        {"kid": item["id"], "tid": tt_id}
                    )
                    edge_count += 1
                except Exception:
                    pass
        except Exception:
            pass

    log.info("Ingested: +%d nodes, +%d edges", inserted, edge_count)
    del conn; del db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-total", type=int, default=10000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--no-ingest", action="store_true")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_combos = []
    for ind in INDUSTRIES:
        for tax in TAX_TYPES:
            for lc in LIFECYCLE_STAGES:
                for sc in SCENARIOS:
                    all_combos.append((ind, tax, lc, sc))

    if args.offset > 0:
        all_combos = all_combos[args.offset:]
    total = min(len(all_combos), args.max_total)
    log.info("Combos: %d total, offset %d, generating %d", len(all_combos) + args.offset, args.offset, total)
    log.info("Scenarios: %d (expanded from 5 to 15)", len(SCENARIOS))

    all_results = []
    batch_idx = 0
    t0 = time.time()

    for i in range(0, total, 5):
        chunk = all_combos[i:i+5]
        results = generate_batch_5(chunk)
        all_results.extend(results)

        batch_idx += 1
        if batch_idx % 20 == 0:  # Every 100 combos
            elapsed = time.time() - t0
            rate = len(all_results) / max(elapsed, 1) * 3600
            log.info("  %d/%d combos, %d valid (%.0f nodes/hr)", i + 5, total, len(all_results), rate)

            # Save + ingest every 100 combos
            if not args.no_ingest and all_results:
                out_path = os.path.join(OUTPUT_DIR, f"fast_batch_{batch_idx//20:04d}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(all_results[-100:], f, ensure_ascii=False, indent=2)
                ingest_batch(all_results[-100:])
                all_results_to_ingest = []

        time.sleep(0.3)

    # Final ingest
    if not args.no_ingest and all_results:
        ingest_batch(all_results)

    elapsed = time.time() - t0
    log.info("=" * 60)
    log.info("Fast Matrix Done (%d combos, %.0fs, %.0f nodes/hr)",
             total, elapsed, len(all_results) / max(elapsed, 1) * 3600)
    log.info("Generated: %d / %d (%.1f%% yield)", len(all_results), total,
             100 * len(all_results) / max(total, 1))

    out_path = os.path.join(OUTPUT_DIR, "compliance_matrix_fast_all.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
