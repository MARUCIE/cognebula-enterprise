#!/usr/bin/env python3
"""Create REFERENCES edges: per-KU row insert approach."""
import kuzu
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
before = r.get_next()[0]
print(f"Before: {before:,} edges")

MAJOR_LAWS = [
    "企业所得税法", "增值税暂行条例", "个人所得税法",
    "税收征收管理法", "发票管理办法", "会计法",
    "企业所得税法实施条例", "个人所得税法实施条例",
    "土地增值税暂行条例", "印花税法", "契税法",
    "资源税法", "环境保护税法", "消费税暂行条例", "关税法",
    "企业会计准则", "公司法", "劳动合同法", "民法典",
]

total_edges = 0
t0 = time.time()

for law_name in MAJOR_LAWS:
    # Find LR id
    r = conn.execute(
        "MATCH (lr:LawOrRegulation) WHERE lr.title CONTAINS $name RETURN lr.id LIMIT 1",
        {"name": law_name}
    )
    if not r.has_next():
        print(f"  SKIP {law_name}: no LR found")
        continue
    lr_id = str(r.get_next()[0])

    # Find KU ids that mention this law (batch query)
    r = conn.execute(
        f"MATCH (k:KnowledgeUnit) WHERE k.content CONTAINS '{law_name}' RETURN k.id"
    )
    ku_ids = []
    while r.has_next():
        ku_ids.append(str(r.get_next()[0]))

    if not ku_ids:
        continue

    # Create edges one by one
    created = 0
    for ku_id in ku_ids:
        try:
            conn.execute(
                "MATCH (k:KnowledgeUnit {id: $kid}), (lr:LawOrRegulation {id: $lid}) "
                "CREATE (k)-[:REFERENCES]->(lr)",
                {"kid": ku_id, "lid": lr_id}
            )
            created += 1
        except Exception:
            pass

    total_edges += created
    print(f"  {law_name}: {len(ku_ids)} KU matched, +{created} edges")

elapsed = time.time() - t0
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
after = r.get_next()[0]
r = conn.execute("MATCH (n) RETURN count(n)")
nodes = r.get_next()[0]
print(f"\nREFERENCES: +{after - before:,} edges ({elapsed:.0f}s)")
print(f"Graph: {nodes:,} nodes / {after:,} edges / density {after/nodes:.3f}")
del conn; del db
