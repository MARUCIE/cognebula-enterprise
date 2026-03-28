#!/usr/bin/env python3
"""M3 Edge Engine: Use Gemini to discover relationships between existing nodes.

Meadows insight: L3 should generate EDGES, not nodes.
Density 6.0 needs 6M edges for 1M nodes. Current 860K. Gap: 5.14M.

Pipeline: Sample node pairs → Gemini classifies relationship → CSV → COPY FROM

Edge types discovered:
- SUPERSEDES (法规替代): LegalDocument → LegalDocument
- CONFLICTS_WITH (冲突): LegalClause → LegalClause
- APPLIES_TO_ENTITY (适用主体): TaxRate → TaxEntity
- APPLIES_IN_REGION (适用地区): TaxRate → Region
- RELATED_TAX (关联税种): TaxType → TaxType

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/generate_edges_ai.py \
        --batch-size 50 --max-batches 20
    sudo systemctl start kg-api
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
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/m3_edges"
os.makedirs(CSV_DIR, exist_ok=True)


from llm_client import llm_generate


def _strip_markdown(text: str) -> str:
    """Strip markdown code block wrappers from LLM response."""
    import re
    # Remove ```json ... ``` or ``` ... ```
    m = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _call_gemini(prompt: str, api_key: str = "") -> str:
    """Call LLM via Poe API and return response text (markdown stripped)."""
    raw = llm_generate(prompt, temperature=0.1, max_tokens=2000)
    return _strip_markdown(raw)


def discover_supersedes(conn, api_key: str, batch_size: int = 50, max_batches: int = 20) -> int:
    """Find SUPERSEDES relationships between LegalDocuments using title similarity."""
    TAX_KEYWORDS = ["增值税", "企业所得税", "个人所得税", "消费税", "土地增值税",
                     "房产税", "印花税", "车船税", "契税", "资源税", "环保税",
                     "城建税", "教育费附加", "关税"]

    total_edges = 0
    csv_path = f"{CSV_DIR}/supersedes.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)

        for kw in TAX_KEYWORDS:
            r = conn.execute(f"""
                MATCH (d:LawOrRegulation)
                WHERE d.title CONTAINS '{kw}' AND d.issuedDate IS NOT NULL
                RETURN d.id, d.title, d.issuedDate
                ORDER BY d.issuedDate DESC
                LIMIT 100
            """)
            docs = []
            while r.has_next():
                row = r.get_next()
                docs.append({"id": str(row[0]), "title": str(row[1] or ""), "date": str(row[2] or "")})

            if len(docs) < 2:
                continue

            for i in range(0, min(len(docs) - 1, batch_size), 5):
                batch = docs[i:i+10]
                if len(batch) < 2:
                    break

                doc_list = "\n".join([f"- [{d['date']}] {d['title']} (ID: {d['id']})" for d in batch])
                prompt = (
                    f'以下是关于"{kw}"的中国税法文件列表（按时间排序）：\n\n'
                    f'{doc_list}\n\n'
                    '请判断哪些较新的文件替代（SUPERSEDES）了较旧的文件。\n'
                    '只输出确定的替代关系，格式为 JSON 数组：\n'
                    '[{"newer_id": "xxx", "older_id": "yyy", "reason": "简短原因"}]\n\n'
                    '如果没有确定的替代关系，输出空数组 []。'
                )

                try:
                    raw = _call_gemini(prompt, api_key)
                    pairs = json.loads(raw)
                    if not isinstance(pairs, list):
                        pairs = []

                    for p in pairs:
                        newer = p.get("newer_id", "")
                        older = p.get("older_id", "")
                        if newer and older and newer != older:
                            writer.writerow([newer, older])
                            total_edges += 1

                except (json.JSONDecodeError, KeyError):
                    continue
                except HTTPError as e:
                    if e.code == 429:
                        time.sleep(30)
                    continue
                except Exception:
                    continue

                time.sleep(0.5)

    return total_edges, csv_path


def discover_cross_references(conn, api_key: str) -> int:
    """Find cross-reference edges between LegalClauses and LegalDocuments."""
    # Use keyword matching (no LLM needed) — find clauses that mention other documents
    csv_path = f"{CSV_DIR}/references_clause_new.csv"
    total = 0

    # Get all LegalDocument titles (for matching)
    r = conn.execute("MATCH (d:LawOrRegulation) WHERE d.title IS NOT NULL AND size(d.title) >= 8 RETURN d.id, d.title LIMIT 5000")
    doc_titles = {}
    while r.has_next():
        row = r.get_next()
        doc_titles[str(row[0])] = str(row[1])

    # Sample clauses with content
    r = conn.execute("""
        MATCH (c:LegalClause)
        WHERE c.content IS NOT NULL AND size(c.content) >= 50
        RETURN c.id, c.content
        LIMIT 10000
    """)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        while r.has_next():
            row = r.get_next()
            clause_id = str(row[0])
            content = str(row[1] or "")

            # Check if this clause mentions any known document title
            for doc_id, doc_title in doc_titles.items():
                # Only match substantial title fragments (>= 8 chars)
                if len(doc_title) >= 8 and doc_title in content:
                    writer.writerow([clause_id, doc_id])
                    total += 1
                    break  # one ref per clause to avoid explosion

    return total, csv_path


def main():
    parser = argparse.ArgumentParser(description="M3 Edge Engine")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-batches", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # LLM calls now go through llm_client.py (Poe API), no separate key needed
    api_key = os.environ.get("POE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    if not api_key and not args.dry_run:
        print("ERROR: POE_API_KEY not set (check .env.kg-api)")
        sys.exit(1)

    print("=" * 60)
    print("M3 Edge Engine: Discover relationships between existing nodes")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Current stats
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    current_edges = r.get_next()[0]
    r = conn.execute("MATCH (n) RETURN count(n)")
    current_nodes = r.get_next()[0]
    print(f"\nCurrent: {current_edges:,} edges / {current_nodes:,} nodes / density {current_edges/current_nodes:.3f}")
    print(f"Target: density 6.0 = {current_nodes * 6:,} edges needed")
    print(f"Gap: {current_nodes * 6 - current_edges:,} edges\n")

    if args.dry_run:
        print("[DRY RUN] Would discover: SUPERSEDES + cross-references")
        del conn; del db
        return

    total_new = 0

    # 1. AI-powered SUPERSEDES discovery
    print("[1/2] Discovering SUPERSEDES relationships (Gemini AI)...")
    count, csv_path = discover_supersedes(conn, api_key, args.batch_size, args.max_batches)
    if count > 0:
        try:
            conn.execute(f'COPY SUPERSEDES FROM "{csv_path}" (header=false)')
            print(f"  SUPERSEDES: +{count:,} edges loaded via COPY")
            total_new += count
        except Exception as e:
            # COPY failed (missing PKs) — fallback to row-by-row MATCH+CREATE
            print(f"  SUPERSEDES COPY failed: {str(e)[:60]}, trying row-by-row...")
            loaded = 0
            with open(csv_path) as cf:
                for row in csv.reader(cf):
                    if len(row) >= 2:
                        try:
                            conn.execute(
                                f"MATCH (a:LawOrRegulation {{id: '{row[0]}'}}), "
                                f"(b:LawOrRegulation {{id: '{row[1]}'}}) "
                                f"CREATE (a)-[:SUPERSEDES]->(b)"
                            )
                            loaded += 1
                        except Exception:
                            pass
            print(f"  SUPERSEDES: +{loaded} edges (row-by-row)")
            total_new += loaded
    else:
        print(f"  SUPERSEDES: 0 new (no confident pairs found)")

    # 2. Keyword-based cross-references (free, fast)
    print("[2/2] Discovering cross-references (keyword matching)...")
    count, csv_path = discover_cross_references(conn, api_key)
    if count > 0:
        try:
            conn.execute(f'COPY REFERENCES_CLAUSE FROM "{csv_path}" (header=false)')
            print(f"  REFERENCES_CLAUSE: +{count:,} edges loaded via COPY")
            total_new += count
        except Exception as e:
            # COPY failed — fallback to row-by-row
            print(f"  REFERENCES_CLAUSE COPY failed: {str(e)[:60]}, trying row-by-row...")
            loaded = 0
            with open(csv_path) as cf:
                for row in csv.reader(cf):
                    if len(row) >= 2:
                        try:
                            conn.execute(
                                f"MATCH (c:LegalClause {{id: '{row[0]}'}}), "
                                f"(d:LawOrRegulation {{id: '{row[1]}'}}) "
                                f"CREATE (c)-[:REFERENCES_CLAUSE]->(d)"
                            )
                            loaded += 1
                        except Exception:
                            pass
            print(f"  REFERENCES_CLAUSE: +{loaded} edges (row-by-row)")
            total_new += loaded
    else:
        print(f"  REFERENCES_CLAUSE: 0 new")

    # Final stats
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    new_total = r.get_next()[0]
    print(f"\n{'='*60}")
    print(f"Edge Engine DONE: +{total_new:,} new edges")
    print(f"Total: {new_total:,} edges / {current_nodes:,} nodes / density {new_total/current_nodes:.3f}")

    del conn
    del db
    print("Checkpoint done")


if __name__ == "__main__":
    main()
