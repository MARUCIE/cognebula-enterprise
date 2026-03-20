#!/usr/bin/env python3
"""Split EXPLAINS edges into 6 precise relationship types.

P0 task: EXPLAINS (475K, 55% of all edges) is a semantic black hole.
Split into: INTERPRETS, EXEMPLIFIED_BY, EXPLAINS_RATE, WARNS_ABOUT,
            DESCRIBES_INCENTIVE, GUIDES_FILING.

Classification: keyword-based on KnowledgeUnit type + title + content.
Execution: CSV COPY FROM (API row-by-row causes OOM on 8GB server).

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/split_explains.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import os
import re
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/explains_split"
os.makedirs(CSV_DIR, exist_ok=True)

# Classification keywords (order matters: first match wins, INTERPRETS is default)
CLASSIFIERS = [
    ("EXEMPLIFIED_BY", {
        "type_match": ["案例解析", "案例"],
        "keywords": ["案例", "举例", "实例", "例如", "比如", "实务", "实操案例",
                      "典型案例", "案例分析", "情景", "场景举例"]
    }),
    ("WARNS_ABOUT", {
        "type_match": ["风险提示", "预警"],
        "keywords": ["风险", "违规", "处罚", "罚款", "滞纳金", "偷税", "逃税",
                      "虚开", "骗税", "违法", "违反", "注意事项", "常见错误",
                      "税务稽查", "稽查", "追缴", "补税"]
    }),
    ("EXPLAINS_RATE", {
        "type_match": [],
        "keywords": ["税率", "征收率", "计税依据", "应纳税额", "计算公式",
                      "适用税率", "预征率", "扣除率", "抵扣率", "退税率",
                      "起征点", "免征额", "速算扣除", "累进税率", "比例税率"]
    }),
    ("DESCRIBES_INCENTIVE", {
        "type_match": [],
        "keywords": ["优惠", "减免", "即征即退", "加计扣除", "免税", "退税",
                      "先征后返", "税额抵免", "减半征收", "免征", "零税率",
                      "税收优惠", "优惠政策", "减税", "小微企业优惠"]
    }),
    ("GUIDES_FILING", {
        "type_match": [],
        "keywords": ["申报", "填报", "报表", "纳税申报", "申报表", "附表",
                      "申报期限", "申报流程", "电子税务局", "征期", "报税",
                      "汇算清缴", "预缴申报", "年度申报", "季度申报"]
    }),
]


def classify(ku_type, title, content):
    """Classify a KnowledgeUnit->LegalClause edge into a specific type."""
    text = f"{title or ''} {content or ''}"
    ku_type_str = str(ku_type or "")

    for edge_type, rules in CLASSIFIERS:
        # Check type match first (strongest signal)
        for tm in rules["type_match"]:
            if tm in ku_type_str:
                return edge_type
        # Check keywords in title+content
        for kw in rules["keywords"]:
            if kw in text:
                return edge_type

    return "INTERPRETS"  # default


def main():
    print("=" * 60)
    print("EXPLAINS Split: 475K -> 6 precise relationship types")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Step 1: Create new edge tables
    print("\n[1/4] Creating 6 new edge tables...")
    new_tables = [
        "INTERPRETS", "EXEMPLIFIED_BY", "EXPLAINS_RATE",
        "WARNS_ABOUT", "DESCRIBES_INCENTIVE", "GUIDES_FILING"
    ]
    for t in new_tables:
        try:
            conn.execute(f"CREATE REL TABLE IF NOT EXISTS {t} (FROM KnowledgeUnit TO LegalClause)")
            print(f"  OK: {t}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  EXISTS: {t}")
            else:
                print(f"  ERROR: {t}: {e}")

    # Step 2: Query all EXPLAINS edges with KU metadata
    print("\n[2/4] Querying EXPLAINS edges + KU metadata...")
    t0 = time.time()

    # Query in batches to avoid OOM
    # First get total count
    r = conn.execute("MATCH ()-[e:EXPLAINS]->() RETURN count(e)")
    total = r.get_next()[0]
    print(f"  Total EXPLAINS edges: {total:,}")

    # Query all edges with KU data
    query = """
    MATCH (k:KnowledgeUnit)-[e:EXPLAINS]->(c:LegalClause)
    RETURN k.id, k.type, k.title, k.content, c.id
    """
    r = conn.execute(query)

    # Step 3: Classify and write CSVs
    print("\n[3/4] Classifying edges...")
    csv_files = {t: open(f"{CSV_DIR}/{t.lower()}.csv", "w", newline="") for t in new_tables}
    csv_writers = {t: csv.writer(f) for t, f in csv_files.items()}
    counts = {t: 0 for t in new_tables}

    processed = 0
    while r.has_next():
        row = r.get_next()
        ku_id = str(row[0] or "")
        ku_type = str(row[1] or "")
        ku_title = str(row[2] or "")
        ku_content = str(row[3] or "")[:500]  # truncate for efficiency
        clause_id = str(row[4] or "")

        edge_type = classify(ku_type, ku_title, ku_content)
        csv_writers[edge_type].writerow([ku_id, clause_id])
        counts[edge_type] += 1
        processed += 1

        if processed % 50000 == 0:
            print(f"  ... {processed:,} / {total:,} ({processed*100//total}%)")

    for f in csv_files.values():
        f.close()

    t1 = time.time()
    print(f"\n  Classification complete in {t1-t0:.1f}s")
    print(f"  Distribution:")
    for t in new_tables:
        pct = counts[t] * 100 / max(processed, 1)
        print(f"    {t:25s}: {counts[t]:>7,} ({pct:5.1f}%)")

    # Step 4: COPY FROM CSV
    print("\n[4/4] Loading edges via CSV COPY FROM...")
    loaded_total = 0
    for t in new_tables:
        csv_path = f"{CSV_DIR}/{t.lower()}.csv"
        if counts[t] == 0:
            print(f"  SKIP: {t} (0 edges)")
            continue
        try:
            conn.execute(f'COPY {t} FROM "{csv_path}" (header=false)')
            print(f"  OK: {t} ({counts[t]:,} edges)")
            loaded_total += counts[t]
        except Exception as e:
            print(f"  ERROR: {t}: {str(e)[:80]}")

    # Final stats
    print("\n" + "=" * 60)
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    total_edges = r.get_next()[0]
    r = conn.execute("MATCH (n) RETURN count(n)")
    total_nodes = r.get_next()[0]

    print(f"NEW edges loaded: +{loaded_total:,}")
    print(f"Total: {total_edges:,} edges / {total_nodes:,} nodes")
    print(f"Density: {total_edges/total_nodes:.3f}")

    # Verify new edge counts
    print("\nVerification:")
    for t in new_tables:
        try:
            r = conn.execute(f"MATCH ()-[e:{t}]->() RETURN count(e)")
            c = r.get_next()[0]
            print(f"  {t:25s}: {c:>7,}")
        except:
            print(f"  {t:25s}: QUERY ERROR")

    # Check if EXPLAINS still exists (original edges preserved)
    r = conn.execute("MATCH ()-[e:EXPLAINS]->() RETURN count(e)")
    explains_remaining = r.get_next()[0]
    print(f"\n  EXPLAINS (original):     {explains_remaining:>7,}")
    print(f"  NOTE: Original EXPLAINS edges preserved for safety.")
    print(f"        Drop with: DROP TABLE EXPLAINS (after verification)")

    # Checkpoint
    del conn
    del db
    print("\nCheckpoint done. EXPLAINS split complete.")


if __name__ == "__main__":
    main()
