#!/usr/bin/env python3
"""Create v2.2 edges via CSV export + COPY FROM.

This is the FAST path for bulk edge creation.
Runs offline on kg-node (stop API first).

    sudo systemctl stop kg-api
    pkill -9 uvicorn; pkill -9 python3; sleep 5
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/create_edges_csv.py
    sudo systemctl start kg-api
"""
import csv
import kuzu
import os
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv"
os.makedirs(CSV_DIR, exist_ok=True)

print("Connecting to KuzuDB...")
db = kuzu.Database(DB_PATH, buffer_pool_size=1536 * 1024 * 1024)  # 1.5GB
conn = kuzu.Connection(db)
print("Connected\n")


def export_edge_csv(query, csv_name, from_col="from", to_col="to"):
    """Export edge pairs to CSV, then COPY FROM."""
    csv_path = os.path.join(CSV_DIR, csv_name)
    t0 = time.time()

    print(f"  Exporting {csv_name}...", end=" ", flush=True)
    count = 0
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([from_col, to_col])
        r = conn.execute(query)
        while r.has_next():
            row = r.get_next()
            if row[0] and row[1]:
                writer.writerow([str(row[0]), str(row[1])])
                count += 1
    elapsed = time.time() - t0
    print(f"{count:,} pairs ({elapsed:.1f}s)")
    return csv_path, count


total = 0

# 1. PART_OF: LegalClause.documentId -> LegalDocument.id
print("[1/4] PART_OF (LegalClause -> LegalDocument)")
csv_path, count = export_edge_csv(
    "MATCH (c:LegalClause), (d:LegalDocument) WHERE c.documentId = d.id RETURN c.id, d.id",
    "part_of.csv"
)
if count > 0:
    try:
        conn.execute(f'COPY PART_OF FROM "{csv_path}"')
        print(f"  COPY OK: {count:,} edges")
        total += count
    except Exception as e:
        print(f"  COPY ERROR: {str(e)[:100]}")

# 2. CHILD_OF: Classification hierarchy (parent_code from TaxCodeDetail)
print("\n[2/4] CHILD_OF (Classification -> Classification)")
# TaxCodeDetail has parent_code - map to Classification IDs
csv_path, count = export_edge_csv(
    "MATCH (c:Classification), (p:Classification) "
    "WHERE EXISTS { MATCH (td:TaxCodeDetail) WHERE td.id = c.id AND td.parent_code = p.id } "
    "RETURN c.id, p.id",
    "child_of.csv"
)
if count > 0:
    try:
        conn.execute(f'COPY CHILD_OF FROM "{csv_path}"')
        print(f"  COPY OK: {count:,} edges")
        total += count
    except Exception as e:
        print(f"  COPY ERROR: {str(e)[:100]}")
else:
    # Alternative: use HSCode parent hierarchy if available
    print("  Trying HS_PARENT_OF mapping...")
    csv_path2, count2 = export_edge_csv(
        "MATCH (a:HSCode)-[:HS_PARENT_OF]->(b:HSCode), "
        "(ca:Classification {id: a.id}), (cb:Classification {id: b.id}) "
        "RETURN ca.id, cb.id",
        "child_of_hs.csv"
    )
    if count2 > 0:
        try:
            conn.execute(f'COPY CHILD_OF FROM "{csv_path2}"')
            print(f"  COPY OK: {count2:,} HS hierarchy edges")
            total += count2
        except Exception as e:
            print(f"  COPY ERROR: {str(e)[:100]}")

# 3. EXPLAINS: KnowledgeUnit -> LegalClause (via shared source/documentId)
print("\n[3/4] EXPLAINS (KnowledgeUnit -> LegalClause)")
# Match by source field
csv_path, count = export_edge_csv(
    "MATCH (k:KnowledgeUnit), (c:LegalClause) "
    "WHERE k.source IS NOT NULL AND c.documentId IS NOT NULL AND k.source = c.documentId "
    "RETURN k.id, c.id LIMIT 50000",
    "explains.csv"
)
if count > 0:
    try:
        conn.execute(f'COPY EXPLAINS FROM "{csv_path}"')
        print(f"  COPY OK: {count:,} edges")
        total += count
    except Exception as e:
        print(f"  COPY ERROR: {str(e)[:100]}")

# 4. APPLIES_TO_TAX: need to map Classification codes to TaxType
# VAT items start with '10', CIT with '20', etc. — this needs domain knowledge
print("\n[4/4] Stats")
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
print(f"Total edges in DB: {r.get_next()[0]:,}")
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
edges = r.get_next()[0]
print(f"Density: {edges/nodes:.3f}")

print(f"\n=== DONE: +{total:,} new edges ===")

del conn
del db
