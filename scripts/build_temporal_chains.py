#!/usr/bin/env python3
"""Build temporal version chains between LegalDocuments.

M3 Phase 1 L1: Auto-discover SUPERSEDES and AMENDS relationships
based on document numbering patterns and dates.

Chinese tax law numbering: e.g., "国家税务总局公告2024年第X号" supersedes "...2023年第X号"
Same title prefix + different year = version chain candidate.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/build_temporal_chains.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import os
import re
import hashlib
from collections import defaultdict

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv/m3_temporal"
os.makedirs(CSV_DIR, exist_ok=True)

# Year extraction pattern
YEAR_PATTERN = re.compile(r'(\d{4})年')
# Doc number pattern: 第X号
DOC_NUM_PATTERN = re.compile(r'第(\d+)号')
# Normalization: remove year and number to get "base title"
NORMALIZE_PATTERNS = [
    (re.compile(r'\d{4}年'), ''),
    (re.compile(r'第\d+号'), ''),
    (re.compile(r'\s+'), ' '),
]


def normalize_title(title: str) -> str:
    """Remove year and doc number to get base title for matching."""
    result = title
    for pattern, replacement in NORMALIZE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result.strip()


def extract_year(title: str, date_str: str) -> int:
    """Extract year from title or date string."""
    m = YEAR_PATTERN.search(title)
    if m:
        return int(m.group(1))
    if date_str:
        m = YEAR_PATTERN.search(date_str)
        if m:
            return int(m.group(1))
        # Try YYYY-MM-DD format
        if len(date_str) >= 4 and date_str[:4].isdigit():
            return int(date_str[:4])
    return 0


def main():
    print("=" * 60)
    print("Temporal Version Chain Builder")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Get all LegalDocuments/LawOrRegulation with titles containing year info
    r = conn.execute("""
        MATCH (d:LawOrRegulation)
        WHERE d.title IS NOT NULL AND size(d.title) >= 10
        RETURN d.id, d.title, d.issuedDate
    """)

    docs = []
    while r.has_next():
        row = r.get_next()
        did = str(row[0] or "")
        title = str(row[1] or "")
        date = str(row[2] or "")
        year = extract_year(title, date)
        if year >= 1990:
            base = normalize_title(title)
            if len(base) >= 5:  # meaningful base title
                docs.append({"id": did, "title": title, "base": base, "year": year, "date": date})

    print(f"\nDocuments with year info: {len(docs):,}")

    # Group by base title
    groups = defaultdict(list)
    for d in docs:
        groups[d["base"]].append(d)

    # Find chains (same base title, different years)
    chains = []
    for base, group in groups.items():
        if len(group) < 2:
            continue
        # Sort by year descending
        group.sort(key=lambda x: x["year"], reverse=True)
        for i in range(len(group) - 1):
            newer = group[i]
            older = group[i + 1]
            if newer["year"] > older["year"]:
                chains.append((newer["id"], older["id"], newer["year"], older["year"], base))

    print(f"Version chains found: {len(chains):,}")
    if chains:
        print(f"\nSample chains:")
        for newer_id, older_id, ny, oy, base in chains[:10]:
            print(f"  [{ny}] → [{oy}] {base[:50]}")

    if not chains:
        print("No temporal chains found.")
        del conn; del db
        return

    # Also check for existing SUPERSEDES edges to avoid duplicates
    existing = set()
    try:
        r = conn.execute("MATCH (a)-[e:SUPERSEDES]->(b) RETURN a.id, b.id")
        while r.has_next():
            row = r.get_next()
            existing.add((str(row[0]), str(row[1])))
    except:
        pass

    new_chains = [(n, o, ny, oy, b) for n, o, ny, oy, b in chains if (n, o) not in existing]
    print(f"New chains (excluding existing): {len(new_chains):,}")

    if not new_chains:
        print("All chains already exist.")
        del conn; del db
        return

    # Write CSV
    csv_path = f"{CSV_DIR}/supersedes_temporal.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        for newer_id, older_id, _, _, _ in new_chains:
            w.writerow([newer_id, older_id])

    # COPY FROM
    print(f"\n[Loading {len(new_chains):,} SUPERSEDES edges]")
    try:
        conn.execute(f'COPY SUPERSEDES FROM "{csv_path}" (header=false)')
        print(f"  SUPERSEDES: +{len(new_chains):,} temporal edges")
    except Exception as e:
        print(f"  SUPERSEDES COPY ERROR: {str(e)[:80]}")

    # Stats
    r = conn.execute("MATCH ()-[e:SUPERSEDES]->() RETURN count(e)")
    total_sup = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    total_edges = r.get_next()[0]
    r = conn.execute("MATCH (n) RETURN count(n)")
    total_nodes = r.get_next()[0]

    print(f"\nTotal SUPERSEDES: {total_sup:,}")
    print(f"Total: {total_edges:,} edges / {total_nodes:,} nodes / density {total_edges/total_nodes:.3f}")

    del conn
    del db
    print("Checkpoint done")


if __name__ == "__main__":
    main()
