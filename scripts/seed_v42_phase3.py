#!/usr/bin/env python3
"""v4.2 Phase 3 Seed — P2 Operations + Data Expansion.

1. ResponseStrategy: 17 risk response strategies (core scenarios; expansion target: 40+)
2. PolicyChange: 11 recent tax policy changes 2022-2026 (expansion target: 30+)
3. IndustryBenchmark expansion: +150 (20 industries × core metrics)
4. RESPONDS_TO / TRIGGERED_BY_CHANGE / BENCHMARK_FOR edges

WARNING: Not idempotent. Re-running will fail on duplicate IDs.
See docs/KG_GOTCHAS.md #8 for details.
"""

import json
import urllib.request

API_BASE = "http://100.75.77.112:8400"


def api_ddl(statements):
    data = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/execute-ddl", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def cn(table, props):
    parts = []
    for k, v in props.items():
        if v is None: continue
        safe = str(v).replace("\\", "\\\\").replace("'", "\\'")
        parts.append(f"{k}: '{safe}'")
    return f"CREATE (n:{table} {{{', '.join(parts)}}})"


def ce(et, ft, fid, tt, tid, p=None):
    ps = ""
    if p:
        parts = [f"{k}: '{str(v).replace(chr(39), chr(92)+chr(39))}'" for k,v in p.items() if v]
        if parts: ps = " {" + ", ".join(parts) + "}"
    return f"MATCH (a:{ft}), (b:{tt}) WHERE a.id = '{fid}' AND b.id = '{tid}' CREATE (a)-[:{et}{ps}]->(b)"


def batch(stmts, label, bs=20):
    ok = err = 0
    for i in range(0, len(stmts), bs):
        r = api_ddl(stmts[i:i+bs])
        ok += r.get("ok", 0); err += r.get("errors", 0)
        for x in r.get("results", []):
            if x.get("status") == "ERROR": print(f"  ERROR: {x.get('reason','')[:120]}")
    print(f"  {label}: {ok} OK, {err} err (of {len(stmts)})")
    return ok, err


# ═══════════════════════════════════════════════════════════════
# 1. ResponseStrategy — 风险应对策略
# ═══════════════════════════════════════════════════════════════
STRATEGIES = [
    # Tax burden responses
    {"id": "RS_TB_SELFCHECK", "name": "税负率偏低自查", "strategyType": "self_audit",
     "targetRisk": "RI_TB_01", "timeframe": "7天",
     "actionSteps": "1.调取12个月增值税申报表;2.计算各月税负率趋势;3.与行业均值对比;4.排查进项异常(大额/集中/跨区);5.形成自查报告",
     "preventionMeasure": "每月末监控税负率，偏离行业均值20%时预警",
     "description": "增值税税负率偏低时的标准自查流程，在税务机关检查前主动排查"},
    {"id": "RS_TB_INCOME_CHECK", "name": "收入完整性核查", "strategyType": "internal_audit",
     "targetRisk": "RI_TB_02", "timeframe": "15天",
     "actionSteps": "1.核对银行流水与收入台账;2.检查未开票收入;3.核查视同销售;4.检查关联交易定价;5.补申报",
     "description": "当所得税贡献率异常偏低时，首先核查收入是否完整记录"},
    {"id": "RS_TB_COST_REVIEW", "name": "成本费用合规审查", "strategyType": "compliance_review",
     "targetRisk": "RI_FR_01", "timeframe": "10天",
     "actionSteps": "1.审查大额费用凭证;2.检查个人消费混入;3.核查白条入账;4.审查关联交易成本;5.纳税调整",
     "description": "成本率异常时的合规审查，重点排查虚增成本"},
    # Invoice responses
    {"id": "RS_INV_COMPARE", "name": "进销项比对分析", "strategyType": "data_analysis",
     "targetRisk": "RI_INV_01", "timeframe": "5天",
     "actionSteps": "1.导出进销项明细;2.按商品编码比对;3.标记不匹配项;4.逐项核实业务实质;5.异常项处理",
     "description": "进销项品名偏差过大时的分析处理流程"},
    {"id": "RS_INV_RED_REVIEW", "name": "红字发票专项审查", "strategyType": "internal_audit",
     "targetRisk": "RI_INV_02", "timeframe": "3天",
     "actionSteps": "1.提取红字发票清单;2.逐笔核实退货/折让依据;3.检查是否有虚开后冲红;4.完善退货流程",
     "description": "红字发票占比过高的专项审查"},
    {"id": "RS_INV_CONCENTRATION", "name": "供应商集中度分散", "strategyType": "business_optimization",
     "targetRisk": "RI_INV_05", "timeframe": "长期",
     "actionSteps": "1.梳理供应商结构;2.评估关联关系;3.引入2-3家备选供应商;4.调整采购比例;5.留存比价记录",
     "description": "进项高度集中的风险应对，通过分散供应商降低关联交易嫌疑"},
    # Financial ratio responses
    {"id": "RS_FR_ENTERTAINMENT", "name": "业务招待费合规控制", "strategyType": "expense_control",
     "targetRisk": "RI_FR_04", "timeframe": "持续",
     "actionSteps": "1.设定年度招待费预算(≤收入5‰的60%);2.每笔审批;3.保留招待对象/事由记录;4.季度统计预警",
     "description": "业务招待费是最常见的纳税调增项，需要全流程控制"},
    {"id": "RS_FR_RD_ARCHIVE", "name": "研发费用归集规范", "strategyType": "compliance_setup",
     "targetRisk": "RI_FR_09", "timeframe": "30天",
     "actionSteps": "1.建立研发项目立项审批制度;2.设置研发费用辅助账;3.按6类费用归集;4.委外研发单独核算;5.留存备查资料",
     "description": "研发费用加计扣除是最大的税收优惠之一，归集规范直接决定能否享受"},
    {"id": "RS_FR_CASHFLOW", "name": "现金流与利润背离分析", "strategyType": "financial_analysis",
     "targetRisk": "RI_FR_08", "timeframe": "10天",
     "actionSteps": "1.编制间接法现金流量表;2.分析应收账款变化;3.核查大额非现金交易;4.检查票据背书;5.解释差异原因",
     "description": "有利润无现金是税务稽查的重要关注点"},
    # Banking/GT4 responses
    {"id": "RS_BK_SEPARATION", "name": "公私账户分离整改", "strategyType": "compliance_setup",
     "targetRisk": "RI_BK_01", "timeframe": "30天",
     "actionSteps": "1.清理法人/股东私户收公款情况;2.补开发票/确认收入;3.建立资金审批流程;4.设置公转私用途审查",
     "description": "金税四期银税联网后的首要合规措施"},
    {"id": "RS_BK_THREE_FLOW", "name": "三流一致核查", "strategyType": "compliance_review",
     "targetRisk": "RI_BK_03", "timeframe": "7天",
     "actionSteps": "1.逐笔核对发票/合同/付款三方;2.标记资金流向不匹配项;3.补充合同或说明;4.异常交易整改",
     "description": "资金流/发票流/货物流一致是增值税真实性的核心判断标准"},
    {"id": "RS_BK_SALARY_ALIGN", "name": "工资社保数据对齐", "strategyType": "hr_compliance",
     "targetRisk": "RI_BK_06", "timeframe": "30天",
     "actionSteps": "1.核对个税申报人数与实际用工;2.检查临时工/劳务派遣;3.核实社保缴费基数与实发工资;4.补差额",
     "description": "金税四期联网社保/公积金后最常见的风险点"},
    # Filing behavior responses
    {"id": "RS_FB_ZERO_EXIT", "name": "零申报退出计划", "strategyType": "business_decision",
     "targetRisk": "RI_FB_01", "timeframe": "30天",
     "actionSteps": "1.评估是否确实无经营;2.如有经营立即补申报;3.如无经营考虑注销;4.如保留备用做好解释材料",
     "description": "连续零申报超6个月需要决策：补申报或注销"},
    {"id": "RS_FB_FILING_SOP", "name": "申报SOP建设", "strategyType": "process_setup",
     "targetRisk": "RI_FB_02", "timeframe": "15天",
     "actionSteps": "1.建立申报日历(每月/季/年);2.设置T-3天提醒;3.指定AB角;4.建立复核机制;5.保留申报截图",
     "description": "解决频繁逾期申报的根本方案"},
    # Cross-system responses
    {"id": "RS_CS_DATA_ALIGN", "name": "多口径数据对齐", "strategyType": "data_governance",
     "targetRisk": "RI_CS_01", "timeframe": "年度",
     "actionSteps": "1.比对税务申报/统计年报/工商年报收入;2.识别口径差异;3.留存差异解释;4.统一数据源头",
     "description": "金税四期跨系统比对的预防性措施"},
    # Proactive strategies
    {"id": "RS_PROACTIVE_REVIEW", "name": "年度税务健康检查", "strategyType": "proactive_audit",
     "targetRisk": "", "timeframe": "年度",
     "actionSteps": "1.全税种税负率分析;2.发票合规检查;3.费用限额计算;4.优惠政策适用确认;5.关联交易合规;6.出具自查报告",
     "description": "年度主动自查是最佳的风险预防手段"},
    {"id": "RS_PROACTIVE_PLANNING", "name": "税收筹划方案设计", "strategyType": "tax_planning",
     "targetRisk": "", "timeframe": "年度",
     "actionSteps": "1.梳理可享受的税收优惠;2.评估业务结构优化空间;3.利用政策叠加效应;4.方案合规性审查;5.实施与跟踪",
     "description": "在合法范围内通过业务安排降低整体税负"},
]

# ═══════════════════════════════════════════════════════════════
# 2. PolicyChange — 近年重要税收政策变更
# ═══════════════════════════════════════════════════════════════
POLICY_CHANGES = [
    {"id": "PC_2022_STAMP", "name": "印花税法实施", "changeType": "new_law", "effectiveDate": "2022-07-01",
     "impactScope": "all_taxpayers", "impactedTaxTypes": "STAMP",
     "previousPolicy": "1988年暂行条例", "newPolicy": "2022年印花税法",
     "transitionRule": "2022年7月1日起按新法执行",
     "description": "印花税正式立法，部分税目税率调整(买卖合同降至0.3‰)，明确不含增值税计税"},
    {"id": "PC_2022_R&D_100", "name": "研发费用加计扣除100%", "changeType": "preferential_expansion",
     "effectiveDate": "2022-10-01", "impactScope": "all_enterprises", "impactedTaxTypes": "CIT",
     "previousPolicy": "制造业100%，其他75%", "newPolicy": "所有企业统一100%",
     "description": "2022年第四季度起所有行业研发费用加计扣除统一提高至100%"},
    {"id": "PC_2023_PIT_RAISE", "name": "个税专项附加扣除标准提高", "changeType": "standard_adjustment",
     "effectiveDate": "2023-08-01", "impactScope": "individual", "impactedTaxTypes": "PIT",
     "previousPolicy": "子女教育1000/月、赡养老人2000/月、婴幼儿照护1000/月",
     "newPolicy": "子女教育2000/月、赡养老人3000/月、婴幼儿照护2000/月",
     "description": "三项专项附加扣除标准翻倍，每年可多扣2.4万元"},
    {"id": "PC_2023_STAMP_HALF", "name": "证券交易印花税减半", "changeType": "rate_reduction",
     "effectiveDate": "2023-08-28", "impactScope": "securities", "impactedTaxTypes": "STAMP",
     "previousPolicy": "证券交易印花税1‰(卖方)", "newPolicy": "减半至0.5‰",
     "description": "活跃资本市场一揽子措施之一"},
    {"id": "PC_2023_SMALL_VAT", "name": "小规模纳税人增值税优惠延续", "changeType": "preferential_extension",
     "effectiveDate": "2023-01-01", "impactScope": "small_taxpayer", "impactedTaxTypes": "VAT",
     "previousPolicy": "1%征收率(疫情临时)", "newPolicy": "月销售≤10万免征;1%征收率至2027年底",
     "description": "小规模增值税优惠从疫情临时政策转为中长期政策"},
    {"id": "PC_2023_SMALL_CIT", "name": "小微企业所得税优惠延续", "changeType": "preferential_extension",
     "effectiveDate": "2023-01-01", "impactScope": "small_enterprise", "impactedTaxTypes": "CIT",
     "previousPolicy": "所得额≤100万实际5%，100-300万实际10%",
     "newPolicy": "统一至300万以内实际5%(300万×25%×20%)",
     "description": "小型微利企业实际税负降至5%，是中小企业最重要的所得税优惠"},
    {"id": "PC_2024_DIGITAL_INVOICE", "name": "全面数字化电子发票推广", "changeType": "system_change",
     "effectiveDate": "2024-01-01", "impactScope": "all_taxpayers", "impactedTaxTypes": "VAT",
     "previousPolicy": "纸质发票+电子发票并行", "newPolicy": "全电发票全国推广",
     "description": "全面数电发票（去版式号段限制）加速推广，金税四期数据采集能力全面提升"},
    {"id": "PC_2024_GT4_BANK", "name": "金税四期银税联网深化", "changeType": "enforcement_enhancement",
     "effectiveDate": "2024-06-01", "impactScope": "all_taxpayers", "impactedTaxTypes": "ALL",
     "previousPolicy": "有限的银行数据共享", "newPolicy": "银行/不动产/市监/社保/海关全面联网",
     "description": "金税四期多部门数据共享深化，跨系统比对能力显著增强"},
    {"id": "PC_2025_CIT_PREPAY", "name": "企业所得税预缴申报表修订", "changeType": "form_change",
     "effectiveDate": "2025-01-01", "impactScope": "all_enterprises", "impactedTaxTypes": "CIT",
     "previousPolicy": "A200000旧版申报表", "newPolicy": "新版预缴申报表(增加研发费用加计扣除栏次)",
     "description": "季度预缴即可享受研发加计扣除，无需等年度汇算"},
    {"id": "PC_2025_CONSUMPTION_REFORM", "name": "消费税改革(征收环节后移)", "changeType": "structural_reform",
     "effectiveDate": "2025-07-01", "impactScope": "consumption_tax", "impactedTaxTypes": "CONSUMPTION",
     "previousPolicy": "生产/进口环节征收(多数)", "newPolicy": "部分高档消费品后移至零售环节",
     "transitionRule": "高档手表/贵重珠宝先行试点",
     "description": "消费税改革配合央地财政关系调整，征收环节从生产向零售后移"},
    {"id": "PC_2026_PROPERTY_TAX_PILOT", "name": "房产税改革试点扩大", "changeType": "pilot_expansion",
     "effectiveDate": "2026-01-01", "impactScope": "pilot_cities", "impactedTaxTypes": "PROPERTY",
     "previousPolicy": "上海/重庆试点(2011)", "newPolicy": "扩大至6个城市试点",
     "description": "房产税改革扩大试点范围，居民住房纳入征税范围"},
]

# ═══════════════════════════════════════════════════════════════
# 3. IndustryBenchmark expansion — 20 industries × 8 metrics
# ═══════════════════════════════════════════════════════════════
INDUSTRIES = [
    ("MFG_GENERAL", "制造业(一般)", "C"),
    ("MFG_ELEC", "电子制造", "C39"),
    ("MFG_AUTO", "汽车制造", "C36"),
    ("MFG_FOOD", "食品制造", "C14"),
    ("MFG_PHARMA", "医药制造", "C27"),
    ("MFG_TEXTILE", "纺织业", "C17"),
    ("RETAIL_GENERAL", "批发零售(一般)", "F"),
    ("RETAIL_ECOMMERCE", "电子商务", "F_EC"),
    ("CONSTRUCTION", "建筑业", "E"),
    ("REAL_ESTATE", "房地产业", "K"),
    ("TECH_SOFTWARE", "软件信息技术", "I65"),
    ("TECH_CONSULTING", "信息技术咨询", "I64"),
    ("LOGISTICS", "交通运输物流", "G"),
    ("HOTEL_CATERING", "住宿餐饮", "H"),
    ("FINANCE_BANKING", "金融(银行)", "J66"),
    ("FINANCE_INSURANCE", "金融(保险)", "J68"),
    ("EDUCATION", "教育", "P"),
    ("HEALTHCARE", "卫生", "Q"),
    ("AGRICULTURE", "农林牧渔", "A"),
    ("MINING", "采矿业", "B"),
]

METRICS = [
    ("VAT_BURDEN", "增值税税负率", "%", "tax_burden"),
    ("CIT_RATE", "所得税贡献率", "%", "tax_burden"),
    ("GROSS_MARGIN", "毛利率", "%", "profitability"),
    ("COST_RATIO", "收入成本率", "%", "cost"),
    ("EXPENSE_RATIO", "期间费用率", "%", "cost"),
    ("AR_DAYS", "应收账款周转天数", "天", "efficiency"),
    ("INV_DAYS", "存货周转天数", "天", "efficiency"),
    ("CASH_PROFIT", "经营现金流/净利润", "倍", "cashflow"),
]

# Industry-specific benchmark ranges (min, max)
BENCHMARK_DATA = {
    "MFG_GENERAL":    [(2.5,4.0),(1.0,3.0),(15,30),(70,85),(8,15),(45,90),(30,60),(0.6,1.2)],
    "MFG_ELEC":       [(2.0,3.5),(1.5,4.0),(18,35),(65,82),(10,18),(50,80),(25,50),(0.5,1.0)],
    "MFG_AUTO":       [(2.0,3.0),(1.0,2.5),(12,22),(78,88),(6,12),(60,120),(40,80),(0.6,1.1)],
    "MFG_FOOD":       [(3.0,5.0),(1.0,3.0),(20,40),(60,80),(10,20),(30,60),(15,40),(0.8,1.5)],
    "MFG_PHARMA":     [(4.0,8.0),(2.0,6.0),(50,75),(25,50),(25,45),(60,120),(40,90),(0.5,0.9)],
    "MFG_TEXTILE":    [(2.0,3.5),(0.8,2.0),(10,20),(80,90),(5,12),(50,90),(30,60),(0.5,1.0)],
    "RETAIL_GENERAL": [(1.0,2.5),(0.5,2.0),(5,15),(85,95),(3,8),(30,60),(20,45),(0.6,1.2)],
    "RETAIL_ECOMMERCE":[(0.8,2.0),(0.5,1.5),(3,12),(88,97),(5,15),(15,40),(10,30),(0.4,0.8)],
    "CONSTRUCTION":   [(2.0,3.5),(1.0,2.5),(8,18),(82,92),(4,10),(90,180),(15,40),(0.3,0.8)],
    "REAL_ESTATE":    [(3.0,5.0),(2.0,5.0),(20,40),(60,80),(5,12),(180,365),(180,720),(0.2,0.6)],
    "TECH_SOFTWARE":  [(3.0,6.0),(2.0,5.0),(50,80),(20,50),(20,40),(60,120),(5,15),(0.7,1.3)],
    "TECH_CONSULTING":[(3.0,5.0),(2.0,4.0),(40,65),(35,60),(15,30),(45,90),(0,5),(0.8,1.4)],
    "LOGISTICS":      [(2.0,4.0),(1.0,2.5),(10,20),(80,90),(5,10),(30,60),(5,15),(0.7,1.2)],
    "HOTEL_CATERING": [(2.0,4.0),(0.5,2.0),(30,55),(45,70),(15,25),(10,30),(5,15),(0.8,1.5)],
    "FINANCE_BANKING":[(0,0),(5.0,15.0),(30,50),(0,0),(15,30),(0,0),(0,0),(0,0)],
    "FINANCE_INSURANCE":[(3.0,6.0),(2.0,5.0),(25,45),(55,75),(10,20),(30,60),(0,0),(0.5,1.0)],
    "EDUCATION":      [(1.0,3.0),(0.5,2.0),(30,60),(40,70),(15,30),(30,60),(0,5),(0.6,1.0)],
    "HEALTHCARE":     [(2.0,4.0),(1.0,3.0),(20,40),(60,80),(10,20),(30,60),(10,30),(0.6,1.1)],
    "AGRICULTURE":    [(0,1.0),(0.3,1.0),(8,20),(80,92),(3,8),(30,90),(30,90),(0.5,1.0)],
    "MINING":         [(3.0,6.0),(2.0,5.0),(25,45),(55,75),(5,12),(30,60),(20,50),(0.7,1.3)],
}


def main():
    print("=== v4.2 Phase 3: P2 Operations + Expansion ===\n")

    # 1. ResponseStrategy — CREATE then SET (ALTER-added columns workaround)
    create_stmts = []
    set_stmts = []
    for rs in STRATEGIES:
        create_stmts.append(cn("ResponseStrategy", {
            "id": rs["id"], "name": rs["name"], "chineseName": rs["name"],
            "strategyType": rs["strategyType"], "targetRisk": rs.get("targetRisk", ""),
            "actionSteps": rs["actionSteps"], "preventionMeasure": rs.get("preventionMeasure", ""),
            "timeframe": rs.get("timeframe", ""),
        }))
        ft = f"【{rs['name']}】类型：{rs['strategyType']}。步骤：{rs['actionSteps']}。{rs['description']}"
        safe_ft = ft.replace("'", "\\'")
        safe_desc = rs["description"].replace("'", "\\'")
        set_stmts.append(
            f"MATCH (n:ResponseStrategy) WHERE n.id = '{rs['id']}' "
            f"SET n.fullText = '{safe_ft}', n.description = '{safe_desc}'"
        )
    batch(create_stmts, "ResponseStrategy CREATE")
    batch(set_stmts, "ResponseStrategy SET")

    # 2. PolicyChange — CREATE then SET
    create_stmts = []
    set_stmts = []
    for pc in POLICY_CHANGES:
        create_stmts.append(cn("PolicyChange", {
            "id": pc["id"], "name": pc["name"], "chineseName": pc["name"],
            "changeType": pc["changeType"], "impactScope": pc["impactScope"],
            "impactedTaxTypes": pc["impactedTaxTypes"],
            "previousPolicy": pc.get("previousPolicy", ""),
            "newPolicy": pc.get("newPolicy", ""),
            "transitionRule": pc.get("transitionRule", ""),
        }))
        ft = f"【{pc['name']}】类型：{pc['changeType']}。{pc['description']}。旧政策：{pc.get('previousPolicy','')}。新政策：{pc.get('newPolicy','')}"
        safe_ft = ft.replace("'", "\\'")
        safe_desc = pc["description"].replace("'", "\\'")
        set_stmts.append(
            f"MATCH (n:PolicyChange) WHERE n.id = '{pc['id']}' "
            f"SET n.fullText = '{safe_ft}', n.description = '{safe_desc}'"
        )
    batch(create_stmts, "PolicyChange CREATE")
    batch(set_stmts, "PolicyChange SET")

    # 3. IndustryBenchmark expansion
    # Check existing IDs pattern first
    ib_stmts = []
    for ind_code, ind_name, nbs_code in INDUSTRIES:
        data = BENCHMARK_DATA.get(ind_code, [])
        for j, (met_code, met_name, unit, cat) in enumerate(METRICS):
            if j >= len(data): continue
            lo, hi = data[j]
            if lo == 0 and hi == 0: continue  # skip inapplicable
            ib_id = f"IB_{ind_code}_{met_code}"
            ib_stmts.append(cn("IndustryBenchmark", {
                "id": ib_id,
                "ratioName": f"{ind_name}-{met_name}",
                "industryCode": nbs_code,
                "minValue": str(lo),
                "maxValue": str(hi),
                "unit": unit,
                "name": f"{ind_name} {met_name} ({lo}-{hi}{unit})",
                "description": f"{ind_name}行业{met_name}正常范围{lo}-{hi}{unit}",
            }))
    batch(ib_stmts, "IndustryBenchmark expansion")

    # ═══════════════════════════════════════════════════════════════
    # Edges
    # ═══════════════════════════════════════════════════════════════
    print("\n=== P2 Edges ===\n")
    edge_stmts = []

    # RESPONDS_TO: ResponseStrategy → RiskIndicator
    for rs in STRATEGIES:
        if rs.get("targetRisk"):
            edge_stmts.append(ce("RESPONDS_TO", "ResponseStrategy", rs["id"],
                                 "RiskIndicator", rs["targetRisk"],
                                 {"description": rs["name"]}))

    # TRIGGERED_BY_CHANGE: PolicyChange → TaxType
    tt_map = {"STAMP": "TT_STAMP", "CIT": "TT_CIT", "PIT": "TT_PIT", "VAT": "TT_VAT",
              "CONSUMPTION": "TT_CONSUMPTION", "PROPERTY": "TT_PROPERTY", "ALL": "TT_VAT"}
    for pc in POLICY_CHANGES:
        for tax in pc["impactedTaxTypes"].split(","):
            tax = tax.strip()
            tt_id = tt_map.get(tax)
            if tt_id:
                edge_stmts.append(ce("TRIGGERED_BY_CHANGE", "PolicyChange", pc["id"],
                                     "TaxType", tt_id,
                                     {"description": pc["name"], "impactLevel": pc["changeType"]}))

    # BENCHMARK_FOR: IndustryBenchmark → TaxType (for tax_burden metrics)
    for ind_code, _, _ in INDUSTRIES:
        data = BENCHMARK_DATA.get(ind_code, [])
        for j, (met_code, _, _, cat) in enumerate(METRICS):
            if j >= len(data): continue
            lo, hi = data[j]
            if lo == 0 and hi == 0: continue
            ib_id = f"IB_{ind_code}_{met_code}"
            if met_code == "VAT_BURDEN":
                edge_stmts.append(ce("BENCHMARK_FOR", "IndustryBenchmark", ib_id,
                                     "TaxType", "TT_VAT", {"description": f"增值税税负基准"}))
            elif met_code == "CIT_RATE":
                edge_stmts.append(ce("BENCHMARK_FOR", "IndustryBenchmark", ib_id,
                                     "TaxType", "TT_CIT", {"description": f"所得税贡献基准"}))

    batch(edge_stmts, "P2 Edges")

    print(f"\n=== Phase 3 Summary ===")
    print(f"ResponseStrategy: {len(STRATEGIES)}")
    print(f"PolicyChange: {len(POLICY_CHANGES)}")
    print(f"IndustryBenchmark expansion: {len(ib_stmts)}")
    print(f"Edges: {len(edge_stmts)}")


if __name__ == "__main__":
    main()
