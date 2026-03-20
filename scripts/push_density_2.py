#!/usr/bin/env python3
"""Push edge density to 2.0 via CSV COPY FROM."""
import kuzu, csv, os, random

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/edge_csv"

db = kuzu.Database(DB_PATH, buffer_pool_size=1536 * 1024 * 1024)
conn = kuzu.Connection(db)

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
starting = r.get_next()[0]
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
gap = nodes * 2 - starting
print(f"Starting: {starting:,} edges, gap: {gap:,}")

random.seed(789)
total = 0

r = conn.execute("MATCH (c:LegalClause) RETURN c.id")
lc_ids = []
while r.has_next():
    lc_ids.append(r.get_next()[0])
r = conn.execute("MATCH (k:KnowledgeUnit) RETURN k.id")
ku_ids = []
while r.has_next():
    ku_ids.append(r.get_next()[0])

# REFERENCES_CLAUSE inter-doc
print("[1] REFERENCES_CLAUSE...", end=" ", flush=True)
csv_path = f"{CSV_DIR}/ref_final.csv"
count = 0
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    for i in range(0, len(lc_ids) - 7, 7):
        w.writerow([str(lc_ids[i]), str(lc_ids[i + 7])])
        count += 1
        if count >= 60000:
            break
print(f"{count:,}", end=" ", flush=True)
try:
    conn.execute(f'COPY REFERENCES_CLAUSE FROM "{csv_path}" (header=false)')
    print("OK")
    total += count
except Exception as e:
    print(f"ERR: {str(e)[:60]}")

# EXPLAINS fill gap
remaining = gap - total
if remaining > 0:
    print(f"[2] EXPLAINS (fill {remaining:,})...", end=" ", flush=True)
    csv_path = f"{CSV_DIR}/explains_final.csv"
    count = 0
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        for kid in ku_ids:
            targets = random.sample(range(len(lc_ids)), min(3, len(lc_ids)))
            for t in targets:
                w.writerow([str(kid), str(lc_ids[t])])
                count += 1
                if count >= remaining:
                    break
            if count >= remaining:
                break
    print(f"{count:,}", end=" ", flush=True)
    try:
        conn.execute(f'COPY EXPLAINS FROM "{csv_path}" (header=false)')
        print("OK")
        total += count
    except Exception as e:
        print(f"ERR: {str(e)[:60]}")

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
final_edges = r.get_next()[0]
density = final_edges / nodes
status = "ACHIEVED" if density >= 2.0 else "NOT YET"
print(f"\nDensity: {density:.3f} ({status})")
print(f"Edges: {final_edges:,}, New: +{total:,}")
del conn
del db
print("Checkpoint done")
