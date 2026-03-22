#!/usr/bin/env python3
"""Create REFERENCES edges: KU content mentioning 《法规名》 → LawOrRegulation."""
import kuzu
import re
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
before = r.get_next()[0]

# Build LR title index
print("Building LR title index...")
r = conn.execute("MATCH (lr:LawOrRegulation) WHERE lr.title IS NOT NULL RETURN lr.id, lr.title")
lr_index = {}
while r.has_next():
    row = r.get_next()
    lr_id = str(row[0])
    title = str(row[1])
    if len(title) >= 4:
        lr_index[title[:15]] = lr_id
print(f"  LR index: {len(lr_index)} entries")

# Regex for regulation names
reg_pattern = re.compile(
    r'\u300a([^\u300b]{4,30}(?:\u6cd5|\u6761\u4f8b|\u529e\u6cd5|\u89c4\u5b9a|\u901a\u77e5|\u51b3\u5b9a|\u610f\u89c1|\u51c6\u5219|\u5236\u5ea6|\u89c4\u5219|\u7ec6\u5219))\u300b'
)
# Unicode: 《=\u300a 》=\u300b 法=\u6cd5 条例=\u6761\u4f8b etc.

total_edges = 0
batch_size = 1000
offset = 0

while offset < 100000:
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.content CONTAINS '\u300a' "
        f"RETURN k.id, k.content SKIP {offset} LIMIT {batch_size}"
    )
    batch = []
    while r.has_next():
        row = r.get_next()
        batch.append((str(row[0]), str(row[1] or '')))

    if not batch:
        break

    for ku_id, content in batch:
        refs = reg_pattern.findall(content)
        if not refs:
            continue
        for ref_name in set(refs[:3]):
            prefix = ref_name[:15]
            if prefix in lr_index:
                lr_id = lr_index[prefix]
                try:
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $kid}), (lr:LawOrRegulation {id: $lid}) "
                        "CREATE (k)-[:REFERENCES]->(lr)",
                        {"kid": ku_id, "lid": lr_id}
                    )
                    total_edges += 1
                except Exception:
                    pass

    offset += batch_size
    if offset % 10000 == 0:
        print(f"  Progress: {offset}, +{total_edges} edges")

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
after = r.get_next()[0]
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
print(f"\nREFERENCES edges: +{after - before:,}")
print(f"Graph: {nodes:,} nodes / {after:,} edges / density {after/nodes:.3f}")
del conn
del db
