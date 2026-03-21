#!/usr/bin/env python3
"""Generate QA pairs from LawOrRegulation articles using Gemini 2.5 Flash.

M3 L1 Deepening: Transform existing law/regulation articles into structured
KnowledgeUnit QA pairs. Each article produces 1-3 QA pairs with edge classification.

Pipeline: KuzuDB (read LR) → Gemini Flash (generate QA) → CSV → COPY FROM (write KU + edges)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/generate_lr_qa.py \
        --batch-size 100 --max-batches 10
    sudo systemctl start kg-api

Cost estimate: ~$0.30 per 1000 articles (Gemini 2.5 Flash, ~500 tokens/article)
"""
import kuzu
import csv
import json
import os
import sys
import time
import hashlib
import argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/m3_qa"

# Edge classification keywords (reuse from split_explains.py)
EDGE_CLASSIFIERS = [
    ("EXEMPLIFIED_BY", ["案例", "举例", "实例", "例如", "比如", "实务"]),
    ("WARNS_ABOUT", ["风险", "违规", "处罚", "罚款", "滞纳金", "偷税", "稽查", "违法"]),
    ("EXPLAINS_RATE", ["税率", "征收率", "计税依据", "应纳税额", "适用税率", "起征点"]),
    ("DESCRIBES_INCENTIVE", ["优惠", "减免", "即征即退", "加计扣除", "免税", "退税"]),
    ("GUIDES_FILING", ["申报", "填报", "报表", "纳税申报", "汇算清缴", "预缴"]),
]


def classify_edge(qa_text: str) -> str:
    """Classify QA text into edge type."""
    for edge_type, keywords in EDGE_CLASSIFIERS:
        for kw in keywords:
            if kw in qa_text:
                return edge_type
    return "INTERPRETS"


GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def generate_qa_batch(articles: list[dict], api_key: str) -> list[dict]:
    """Call Gemini 2.5 Flash Lite via HTTP to generate QA pairs.

    Returns list of {article_id, question, answer, edge_type}.
    """
    results = []
    for article in articles:
        aid = article["id"]
        name = article["name"] or ""
        content = article.get("content", "") or article.get("status", "") or ""

        # Skip articles with too little content
        text = f"{name} {content}".strip()
        if len(text) < 50:
            continue

        prompt = (
            "你是中国财税法规专家。根据以下法规内容，生成 1-3 个高质量问答对。\n\n"
            f"法规名称: {name}\n"
            f"法规内容: {text[:2000]}\n\n"
            "要求:\n"
            "1. 问题必须具体、可回答（不要\"什么是XX\"这种泛问）\n"
            "2. 答案要引用法规原文要点，50-200 字\n"
            "3. 输出 JSON 数组格式: [{\"q\": \"问题\", \"a\": \"答案\"}]\n"
            "4. 如果法规内容太短或太泛，只生成 1 个问答\n\n"
            "只输出 JSON 数组，不要其他文字。"
        )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": 2000,
                "temperature": 0.3,
            },
        }

        try:
            req = Request(
                f"{GEMINI_URL}?key={api_key}",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=30)
            result = json.loads(resp.read())
            raw = result["candidates"][0]["content"]["parts"][0]["text"]

            qa_pairs = json.loads(raw)
            if not isinstance(qa_pairs, list):
                qa_pairs = [qa_pairs]

            for i, qa in enumerate(qa_pairs[:3]):  # max 3 per article
                q = qa.get("q", "").strip()
                a = qa.get("a", "").strip()
                if len(q) < 10 or len(a) < 20:
                    continue

                qa_hash = hashlib.md5(f"{aid}_{i}_{q}".encode()).hexdigest()[:12]
                ku_id = f"QA_{qa_hash}"
                edge_type = classify_edge(f"{q} {a}")

                results.append({
                    "ku_id": ku_id,
                    "article_id": aid,
                    "question": q,
                    "answer": a,
                    "edge_type": edge_type,
                    "source": "gemini-qa-v3",
                })

        except json.JSONDecodeError as e:
            print(f"    JSON PARSE ERROR on {aid[:15]}: {str(e)[:60]}")
            continue
        except HTTPError as e:
            if e.code == 429:
                print(f"    Rate limited, sleeping 30s...")
                time.sleep(30)
            else:
                print(f"    HTTP {e.code} on {aid[:15]}: {str(e)[:80]}")
            continue
        except Exception as e:
            print(f"    ERROR on {aid[:15]}: {str(e)[:80]}")
            continue

        time.sleep(0.5)

    return results


def main():
    parser = argparse.ArgumentParser(description="Generate QA from LawOrRegulation")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0, help="Skip first N articles")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source-table", default="LawOrRegulation",
                        help="Source table (LawOrRegulation or LegalDocument)")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    os.makedirs(CSV_DIR, exist_ok=True)

    print("=" * 60)
    print(f"M3 L1: LR Article QA Generation (Gemini 2.5 Flash)")
    print(f"Source: {args.source_table}, Batch: {args.batch_size}, Max: {args.max_batches}")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Count available articles
    r = conn.execute(f"MATCH (n:{args.source_table}) RETURN count(n)")
    total = r.get_next()[0]
    print(f"\nTotal {args.source_table}: {total:,}")

    # Check existing QA nodes to avoid duplicates
    try:
        r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.id STARTS WITH 'QA_' RETURN count(k)")
        existing_qa = r.get_next()[0]
    except:
        existing_qa = 0
    print(f"Existing QA nodes: {existing_qa:,}")

    total_generated = 0
    all_qa = []

    for batch_num in range(args.max_batches):
        offset = args.offset + batch_num * args.batch_size
        if offset >= total:
            break

        # Fetch batch of articles
        # LawOrRegulation uses title/fullText; LegalDocument uses name/status
        # Only select articles with substantial content (>= 100 chars)
        if args.source_table == "LawOrRegulation":
            query = f"""
                MATCH (n:{args.source_table})
                WHERE n.fullText IS NOT NULL AND size(n.fullText) >= 100
                RETURN n.id, n.title, n.fullText
                SKIP {offset} LIMIT {args.batch_size}
            """
        else:
            query = f"""
                MATCH (n:{args.source_table})
                WHERE n.name IS NOT NULL AND size(n.name) >= 10
                RETURN n.id, n.name, n.status
                SKIP {offset} LIMIT {args.batch_size}
            """
        r = conn.execute(query)
        articles = []
        while r.has_next():
            row = r.get_next()
            articles.append({
                "id": str(row[0] or ""),
                "name": str(row[1] or ""),
                "content": str(row[2] or ""),
            })

        if not articles:
            break

        print(f"\n[Batch {batch_num + 1}/{args.max_batches}] {len(articles)} articles (offset {offset})")

        if args.dry_run:
            print(f"  DRY RUN: would process {len(articles)} articles")
            total_generated += len(articles) * 2  # estimate 2 QA per article
            continue

        # Generate QA
        qa_results = generate_qa_batch(articles, api_key)
        all_qa.extend(qa_results)
        total_generated += len(qa_results)

        # Edge type distribution
        from collections import Counter
        dist = Counter(qa["edge_type"] for qa in qa_results)
        print(f"  Generated: {len(qa_results)} QA pairs")
        for et, count in dist.most_common():
            print(f"    {et}: {count}")

    if args.dry_run:
        print(f"\n[DRY RUN] Estimated: ~{total_generated:,} QA pairs from {args.max_batches * args.batch_size} articles")
        del conn
        del db
        return

    if not all_qa:
        print("\nNo QA generated. Check API key and article content.")
        del conn
        del db
        return

    # Write CSV files
    print(f"\n[Writing CSVs] {len(all_qa):,} QA pairs")

    # Nodes CSV: KnowledgeUnit
    nodes_csv = f"{CSV_DIR}/qa_nodes.csv"
    with open(nodes_csv, "w", newline="") as f:
        w = csv.writer(f)
        for qa in all_qa:
            w.writerow([qa["ku_id"], "FAQ", qa["question"], qa["answer"], qa["source"]])

    # Create KU_ABOUT_TAX edges via keyword matching (same as structural edges)
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

    # KU_ABOUT_TAX edges CSV
    tax_edges_csv = f"{CSV_DIR}/qa_ku_about_tax.csv"
    tax_edge_count = 0
    with open(tax_edges_csv, "w", newline="") as f:
        w = csv.writer(f)
        for qa in all_qa:
            text = f"{qa['question']} {qa['answer']}"
            for kw, tid in TAX_KEYWORDS.items():
                if kw in text:
                    w.writerow([qa["ku_id"], tid])
                    tax_edge_count += 1
                    break  # one tax per QA

    # COPY FROM
    print(f"\n[Loading into KuzuDB]")

    # First: KU nodes
    try:
        conn.execute(f'COPY KnowledgeUnit FROM "{nodes_csv}" (header=false)')
        print(f"  KnowledgeUnit: +{len(all_qa):,} nodes")
    except Exception as e:
        print(f"  KnowledgeUnit COPY ERROR: {str(e)[:80]}")

    # Then: KU_ABOUT_TAX edges
    if tax_edge_count > 0:
        try:
            conn.execute(f'COPY KU_ABOUT_TAX FROM "{tax_edges_csv}" (header=false)')
            print(f"  KU_ABOUT_TAX: +{tax_edge_count:,} edges")
        except Exception as e:
            print(f"  KU_ABOUT_TAX COPY ERROR: {str(e)[:80]}")

    # Final stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    print(f"\n{'='*60}")
    print(f"DONE: +{len(all_qa):,} QA pairs generated and loaded")
    print(f"Total: {nodes:,} nodes / {edges:,} edges / density {edges/nodes:.3f}")

    del conn
    del db
    print("Checkpoint done")


if __name__ == "__main__":
    main()
