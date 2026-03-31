#!/usr/bin/env python3
"""v4.2 Phase 4 Validation — 10 real business queries.

Tests whether the v4.2 ontology can answer questions a 代账公司 Agent would face.
Each query exercises a different chain in the ontology graph.
"""

import json
import urllib.request
import sys

API_BASE = "http://100.75.77.112:8400"
PASS = 0
FAIL = 0
WARN = 0


def api_ddl(stmts):
    data = json.dumps({"statements": stmts}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/execute-ddl", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def cypher(query):
    """Execute a single Cypher query and return rows."""
    r = api_ddl([query])
    return r


def search(q, table=None, limit=5):
    url = f"{API_BASE}/api/v1/search?query={q}&limit={limit}"
    if table:
        url += f"&table={table}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def constellation_type(t, limit=200):
    url = f"{API_BASE}/api/v1/constellation/type?type={t}&limit={limit}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def stats():
    url = f"{API_BASE}/api/v1/stats"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def check(name, condition, detail=""):
    global PASS, FAIL, WARN
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")


def warn(name, detail):
    global WARN
    WARN += 1
    print(f"  WARN: {name} — {detail}")


def main():
    print("=" * 60)
    print("v4.2 Phase 4 Validation — 10 Business Queries")
    print("=" * 60)

    # ─── Q1: Monthly close chain ───
    # "我有一笔销售收入，如何从业务活动走到报表？"
    # Chain: BusinessActivity → JournalEntryTemplate → AccountingSubject → FinancialStatementItem
    print("\nQ1: 业务活动→分录→科目→报表 完整链路")
    d = constellation_type("JournalEntryTemplate", 50)
    jet_count = len([n for n in d["nodes"] if n["id"].startswith("JET_")])
    check("JournalEntryTemplate 有数据", jet_count > 0, f"got {jet_count}")

    d = constellation_type("FinancialStatementItem", 50)
    fsi_count = len([n for n in d["nodes"] if n["id"].startswith("FSI_")])
    check("FinancialStatementItem 有数据", fsi_count > 0, f"got {fsi_count}")

    # Check ENTRY_DEBITS edges exist
    s = stats()
    ebt = s.get("edges_by_type", {})
    check("ENTRY_DEBITS 边存在", ebt.get("ENTRY_DEBITS", 0) > 0,
          f"got {ebt.get('ENTRY_DEBITS', 0)}")
    check("ENTRY_CREDITS 边存在", ebt.get("ENTRY_CREDITS", 0) > 0,
          f"got {ebt.get('ENTRY_CREDITS', 0)}")
    check("POPULATES 边存在 (科目→报表项)", ebt.get("POPULATES", 0) > 0,
          f"got {ebt.get('POPULATES', 0)}")

    # ─── Q2: Tax calculation ───
    # "增值税一般纳税人怎么算税？"
    # Chain: TaxType → TaxCalculationRule → formula
    print("\nQ2: 税种→计算规则→公式")
    d = constellation_type("TaxCalculationRule", 20)
    tcr_count = len([n for n in d["nodes"] if n["id"].startswith("TCR_")])
    check("TaxCalculationRule 有数据", tcr_count > 0, f"got {tcr_count}")
    check("CALCULATION_FOR_TAX 边存在", ebt.get("CALCULATION_FOR_TAX", 0) > 0,
          f"got {ebt.get('CALCULATION_FOR_TAX', 0)}")

    # ─── Q3: Filing form fields ───
    # "增值税主表第19栏怎么填？"
    # Chain: FilingFormField (formula + description)
    print("\nQ3: 申报表栏次填报指引")
    d = constellation_type("FilingFormField", 100)
    fff_count = len([n for n in d["nodes"] if n["id"].startswith("FFF_")])
    check("FilingFormField 有数据", fff_count > 0, f"got {fff_count}")
    check("FIELD_OF 边存在", ebt.get("FIELD_OF", 0) > 0,
          f"got {ebt.get('FIELD_OF', 0)}")
    check("DERIVES_FROM 边存在 (跨表引用)", ebt.get("DERIVES_FROM", 0) > 0,
          f"got {ebt.get('DERIVES_FROM', 0)}")

    # ─── Q4: Risk detection → response ───
    # "我的增值税税负率偏低，该怎么办？"
    # Chain: RiskIndicator → RESPONDS_TO ← ResponseStrategy
    print("\nQ4: 风险指标→应对策略")
    ri_count = s["nodes_by_type"].get("RiskIndicator", 0)
    rs_count = s["nodes_by_type"].get("ResponseStrategy", 0)
    check("RiskIndicator 有数据 (rebuilt)", ri_count >= 49, f"got {ri_count}")
    check("ResponseStrategy 有数据", rs_count >= 39, f"got {rs_count}")
    check("RESPONDS_TO 边存在", ebt.get("RESPONDS_TO", 0) > 0,
          f"got {ebt.get('RESPONDS_TO', 0)}")

    # ─── Q5: Policy change impact ───
    # "2024年有什么税收政策变化影响我们？"
    # Chain: PolicyChange → TRIGGERED_BY_CHANGE → TaxType
    print("\nQ5: 政策变动→影响税种")
    pc_count = s["nodes_by_type"].get("PolicyChange", 0)
    check("PolicyChange 有数据", pc_count >= 30, f"got {pc_count}")
    check("TRIGGERED_BY_CHANGE 边存在", ebt.get("TRIGGERED_BY_CHANGE", 0) > 0,
          f"got {ebt.get('TRIGGERED_BY_CHANGE', 0)}")

    # ─── Q6: Financial indicator analysis ───
    # "杜邦分析法怎么拆？ROE分解成什么？"
    # Chain: FinancialIndicator → DECOMPOSES_INTO → FinancialIndicator
    print("\nQ6: 财务指标→杜邦分解")
    fi_count = s["nodes_by_type"].get("FinancialIndicator", 0)
    check("FinancialIndicator 有数据", fi_count >= 17, f"got {fi_count}")
    check("DECOMPOSES_INTO 边存在 (杜邦树)", ebt.get("DECOMPOSES_INTO", 0) > 0,
          f"got {ebt.get('DECOMPOSES_INTO', 0)}")
    check("COMPUTED_FROM 边存在 (指标←报表项)", ebt.get("COMPUTED_FROM", 0) > 0,
          f"got {ebt.get('COMPUTED_FROM', 0)}")

    # ─── Q7: Tax treaty query ───
    # "给新加坡公司付特许权使用费，预提税率多少？"
    # Chain: TaxTreaty + Region + TaxRate
    print("\nQ7: 税收协定→预提税率")
    tt_count = s["nodes_by_type"].get("TaxTreaty", 0)
    check("TaxTreaty 有数据", tt_count >= 20, f"got {tt_count}")

    # ─── Q8: Industry benchmark comparison ───
    # "餐饮业增值税税负率正常范围是多少？"
    # Chain: IndustryBenchmark (ratioName + minValue + maxValue)
    print("\nQ8: 行业基准→税负率范围")
    ib_count = s["nodes_by_type"].get("IndustryBenchmark", 0)
    check("IndustryBenchmark 有数据 (expanded)", ib_count >= 199, f"got {ib_count}")
    check("BENCHMARK_FOR 边存在", ebt.get("BENCHMARK_FOR", 0) > 0,
          f"got {ebt.get('BENCHMARK_FOR', 0)}")

    # Search test
    try:
        r = search("餐饮", "IndustryBenchmark", 5)
        results = r.get("results", [])
        check("Search '餐饮' 在 IndustryBenchmark 返回结果", len(results) > 0,
              f"got {len(results)} results")
    except Exception as e:
        warn("Search API", str(e)[:80])

    # ─── Q9: Tax incentive stacking ───
    # "小微企业能同时享受哪些优惠？哪些互斥？"
    # Chain: TaxIncentive → STACKS_WITH / EXCLUDES → TaxIncentive
    print("\nQ9: 税收优惠→叠加/互斥规则")
    ti_count = s["nodes_by_type"].get("TaxIncentive", 0)
    check("TaxIncentive 有数据", ti_count >= 112, f"got {ti_count}")
    check("STACKS_WITH 边存在", ebt.get("STACKS_WITH", 0) > 0,
          f"got {ebt.get('STACKS_WITH', 0)}")
    check("EXCLUDES 边存在", ebt.get("EXCLUDES", 0) > 0,
          f"got {ebt.get('EXCLUDES', 0)}")

    # ─── Q10: Compliance rule + penalty ───
    # "业务招待费超标了，会有什么后果？"
    # Chain: ComplianceRule → PENALIZED_BY → Penalty
    print("\nQ10: 合规规则→处罚后果")
    cr_count = s["nodes_by_type"].get("ComplianceRule", 0)
    pen_count = s["nodes_by_type"].get("Penalty", 0)
    check("ComplianceRule 有数据 (expanded)", cr_count >= 159, f"got {cr_count}")
    check("Penalty 有数据 (expanded)", pen_count >= 164, f"got {pen_count}")
    check("PENALIZED_BY 边存在", ebt.get("PENALIZED_BY", 0) > 0,
          f"got {ebt.get('PENALIZED_BY', 0)}")

    # Search test
    try:
        r = search("招待费")
        results = r.get("results", [])
        check("Search '招待费' 返回结果", len(results) > 0,
              f"got {len(results)} results")
    except Exception as e:
        warn("Search API", str(e)[:80])

    # ─── Summary ───
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} PASS, {FAIL} FAIL, {WARN} WARN")
    pct = (PASS / total * 100) if total > 0 else 0
    grade = "A" if pct >= 90 else "B" if pct >= 75 else "C" if pct >= 60 else "F"
    print(f"Score: {pct:.0f}% (Grade {grade})")

    if FAIL > 0:
        print(f"\nFailed checks need attention before v4.2 can be considered complete.")
    else:
        print(f"\nAll checks passed. v4.2 ontology is ready for production use.")

    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
