#!/usr/bin/env python3
"""Split LegalClause into sub-clauses (条→款→项).

M3 Phase 1 L1: Deep split existing clauses for finer granularity.
Chinese law structure: 条(Article) → 款(Paragraph) → 项(Item) → 目(Sub-item)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/split_clauses_v2.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import os
import re
import hashlib
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/m3_clause_split"
os.makedirs(CSV_DIR, exist_ok=True)

# Chinese legal numbering patterns
# 款 (paragraph): （一）（二）... or 一、二、... or 1. 2. 3.
PARAGRAPH_PATTERNS = [
    r'（[一二三四五六七八九十]+）',   # （一）（二）
    r'[一二三四五六七八九十]+、',      # 一、二、
    r'\d+\.\s',                        # 1. 2. 3.
]

# 项 (item): （1）（2）... or (1)(2)... or ①②③
ITEM_PATTERNS = [
    r'（\d+）',                        # （1）（2）
    r'\(\d+\)',                        # (1)(2)
    r'[①②③④⑤⑥⑦⑧⑨⑩]',            # circled numbers
]


def split_content(content: str) -> list[dict]:
    """Split a clause's content into sub-clauses (款/项)."""
    if not content or len(content) < 100:
        return []

    sub_clauses = []

    # Try paragraph-level split first
    for pattern in PARAGRAPH_PATTERNS:
        parts = re.split(f'({pattern})', content)
        if len(parts) >= 3:  # At least one split happened
            current_num = ""
            current_text = parts[0].strip()  # preamble
            for part in parts[1:]:
                if re.match(pattern, part):
                    if current_text and len(current_text) >= 20:
                        sub_clauses.append({
                            "type": "paragraph",
                            "number": current_num,
                            "content": current_text.strip(),
                        })
                    current_num = part.strip()
                    current_text = ""
                else:
                    current_text += part

            # Last paragraph
            if current_text and len(current_text) >= 20:
                sub_clauses.append({
                    "type": "paragraph",
                    "number": current_num,
                    "content": current_text.strip(),
                })

            if len(sub_clauses) >= 2:
                return sub_clauses

    return []


def main():
    print("=" * 60)
    print("LegalClause Split v2: 条 → 款 → 项")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Count eligible clauses (content >= 200 chars, likely splittable)
    r = conn.execute("""
        MATCH (c:LegalClause)
        WHERE c.content IS NOT NULL AND size(c.content) >= 200
        RETURN count(c)
    """)
    eligible = r.get_next()[0]
    print(f"\nEligible clauses (content >= 200 chars): {eligible:,}")

    # Process in batches
    BATCH = 5000
    total_split = 0
    total_sub = 0
    all_nodes = []
    all_edges = []  # PART_OF edges: sub-clause → parent clause

    for offset in range(0, eligible, BATCH):
        r = conn.execute(f"""
            MATCH (c:LegalClause)
            WHERE c.content IS NOT NULL AND size(c.content) >= 200
            RETURN c.id, c.documentId, c.clauseNumber, c.title, c.content
            SKIP {offset} LIMIT {BATCH}
        """)

        batch_split = 0
        while r.has_next():
            row = r.get_next()
            clause_id = str(row[0] or "")
            doc_id = str(row[1] or "")
            clause_num = str(row[2] or "")
            clause_title = str(row[3] or "")
            content = str(row[4] or "")

            subs = split_content(content)
            if len(subs) >= 2:
                batch_split += 1
                for i, sub in enumerate(subs):
                    sub_id = f"{clause_id}_p{i+1}"
                    sub_title = f"{clause_title} {sub['number']}".strip() if clause_title else f"第{clause_num}条 {sub['number']}".strip()
                    all_nodes.append({
                        "id": sub_id,
                        "documentId": doc_id,
                        "clauseNumber": f"{clause_num}.{i+1}",
                        "title": sub_title[:200],
                        "content": sub["content"][:5000],
                        "keywords": "",
                    })
                    all_edges.append((sub_id, doc_id))  # PART_OF: sub-clause → LegalDocument
                    total_sub += 1

        total_split += batch_split
        print(f"  Batch {offset//BATCH + 1}: {batch_split} clauses split → {total_sub} sub-clauses total")

    print(f"\nTotal: {total_split:,} clauses split → {total_sub:,} sub-clauses")

    if total_sub == 0:
        print("No sub-clauses generated.")
        del conn; del db
        return

    # Write CSV files
    nodes_csv = f"{CSV_DIR}/sub_clause_nodes.csv"
    edges_csv = f"{CSV_DIR}/sub_clause_part_of.csv"

    with open(nodes_csv, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for n in all_nodes:
            # Sanitize content: remove newlines and extra whitespace
            content = n["content"].replace("\n", " ").replace("\r", " ").replace('"', "'")
            title = n["title"].replace('"', "'")
            w.writerow([n["id"], n["documentId"], n["clauseNumber"], title, content, n["keywords"]])

    with open(edges_csv, "w", newline="") as f:
        w = csv.writer(f)
        for sub_id, parent_id in all_edges:
            w.writerow([sub_id, parent_id])

    print(f"\nCSV: {nodes_csv} ({total_sub} rows)")
    print(f"CSV: {edges_csv} ({len(all_edges)} rows)")

    # COPY FROM
    print("\n[Loading into KuzuDB]")
    try:
        conn.execute(f'COPY LegalClause FROM "{nodes_csv}" (header=false, parallel=false)')
        print(f"  LegalClause: +{total_sub:,} sub-clause nodes")
    except Exception as e:
        print(f"  LegalClause COPY ERROR: {str(e)[:80]}")

    try:
        conn.execute(f'COPY PART_OF FROM "{edges_csv}" (header=false)')
        print(f"  PART_OF: +{len(all_edges):,} edges")
    except Exception as e:
        print(f"  PART_OF COPY ERROR: {str(e)[:80]}")

    # Stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    print(f"\nTotal: {nodes:,} nodes / {edges:,} edges / density {edges/nodes:.3f}")

    del conn
    del db
    print("Checkpoint done")


if __name__ == "__main__":
    main()
