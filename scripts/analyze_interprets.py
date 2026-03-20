#!/usr/bin/env python3
"""Analyze INTERPRETS edges to find reclassification opportunities.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/analyze_interprets.py
    sudo systemctl start kg-api
"""
import kuzu
from collections import Counter

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

# 1. KU type distribution for INTERPRETS
print("=" * 60)
print("INTERPRETS Analysis: Finding reclassification opportunities")
print("=" * 60)

r = conn.execute("""
    MATCH (k:KnowledgeUnit)-[e:INTERPRETS]->(c:LegalClause)
    RETURN k.type, count(e) AS cnt
    ORDER BY cnt DESC
""")

print("\n[1] KU Type Distribution:")
type_counts = {}
while r.has_next():
    row = r.get_next()
    t = str(row[0] or "(null)")
    c = row[1]
    type_counts[t] = c
    print(f"  {t:35s}: {c:>7,}")

# 2. Keyword frequency analysis on titles
print("\n[2] Keyword Frequency in INTERPRETS KU titles (sample 50K):")
r = conn.execute("""
    MATCH (k:KnowledgeUnit)-[e:INTERPRETS]->(c:LegalClause)
    RETURN k.title
    LIMIT 50000
""")

# Extended keywords for potential reclassification
EXTENDED_KW = {
    "WARNS_ABOUT": ["违约", "失信", "黑名单", "异常", "疑点", "问题", "错误",
                     "常见问题", "注意", "防范", "合规风险", "税收风险", "涉税风险"],
    "EXPLAINS_RATE": ["计算", "公式", "算法", "计税方法", "核定征收",
                       "查账征收", "扣缴", "预扣预缴", "汇算"],
    "DESCRIBES_INCENTIVE": ["抵免", "返还", "补贴", "奖励", "扶持",
                             "高新技术", "小型微利", "研发费用", "西部大开发"],
    "GUIDES_FILING": ["备案", "登记", "注销", "变更", "迁移", "跨区域",
                       "税务登记", "发票", "电子发票", "认证", "勾选"],
    "EXEMPLIFIED_BY": ["实务操作", "操作流程", "步骤", "示例", "样例",
                        "填写说明", "图解", "解读案例"],
}

kw_hits = Counter()
titles_seen = 0
while r.has_next():
    row = r.get_next()
    title = str(row[0] or "")
    titles_seen += 1
    for edge_type, keywords in EXTENDED_KW.items():
        for kw in keywords:
            if kw in title:
                kw_hits[f"{edge_type}:{kw}"] += 1
                break  # one match per type per title

print(f"  Titles analyzed: {titles_seen:,}")
print(f"\n  Keyword hits (top 30):")
for kw, count in kw_hits.most_common(30):
    print(f"    {kw:45s}: {count:>5,}")

# 3. Estimate reclassification potential
print("\n[3] Reclassification Potential:")
total_reclassifiable = sum(kw_hits.values())
print(f"  Titles with extended keyword matches: ~{total_reclassifiable:,}")
print(f"  Current INTERPRETS: 390,756")
print(f"  Potential reduction: ~{total_reclassifiable:,} ({total_reclassifiable*100//390756}%)")
print(f"  Post-reclassification INTERPRETS: ~{390756-total_reclassifiable:,}")

del conn
del db
print("\nCheckpoint done")
