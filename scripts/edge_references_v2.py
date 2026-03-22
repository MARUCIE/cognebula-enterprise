#!/usr/bin/env python3
"""Create REFERENCES edges v2: wider matching, Cypher-level search."""
import kuzu
import re
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
before = r.get_next()[0]
print(f"Before: {before:,} edges")

# Pattern: match anything inside 《》 that's 4-40 chars
ref_pattern = re.compile(r'\u300a([^\u300b]{4,40})\u300b')
left_b = "\u300a"

# Process compliance_matrix KU first (they have the most refs)
total_edges = 0
batch_size = 500
offset = 0

print("\nProcessing KU with content references...")
t0 = time.time()

while offset < 200000:
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.content IS NOT NULL AND size(k.content) > 100 "
        f"AND k.content CONTAINS '{left_b}' "
        f"RETURN k.id, k.content SKIP {offset} LIMIT {batch_size}"
    )
    batch = []
    while r.has_next():
        row = r.get_next()
        batch.append((str(row[0]), str(row[1] or '')))

    if not batch:
        break

    for ku_id, content in batch:
        refs = ref_pattern.findall(content)
        if not refs:
            continue

        for ref_name in set(refs[:5]):
            # Use first 10 chars as search fragment
            frag = ref_name[:10]
            if len(frag) < 4:
                continue
            try:
                r2 = conn.execute(
                    "MATCH (lr:LawOrRegulation) "
                    "WHERE lr.title CONTAINS $frag "
                    "RETURN lr.id LIMIT 1",
                    {"frag": frag}
                )
                if r2.has_next():
                    lr_id = str(r2.get_next()[0])
                    try:
                        conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $kid}), (lr:LawOrRegulation {id: $lid}) "
                            "CREATE (k)-[:REFERENCES]->(lr)",
                            {"kid": ku_id, "lid": lr_id}
                        )
                        total_edges += 1
                    except Exception:
                        pass
            except Exception:
                pass

    offset += batch_size
    if offset % 5000 == 0:
        elapsed = time.time() - t0
        print(f"  Progress: {offset}, +{total_edges} edges ({elapsed:.0f}s)")

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
after = r.get_next()[0]
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
print(f"\nREFERENCES v2: +{after - before:,} edges ({time.time()-t0:.0f}s)")
print(f"Graph: {nodes:,} nodes / {after:,} edges / density {after/nodes:.3f}")
del conn; del db
