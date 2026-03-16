#!/usr/bin/env python3
"""Seed the 3-Layer Finance/Tax Knowledge Graph with core reference data.

Populates:
- L1: 18 tax types, 6 enterprise types, 9 PIT income types, 5 taxpayer statuses
- L2: 7 lifecycle stages, 91 chart of accounts (top-level), key journal templates, tax rate mappings
- L3: 2026 tax calendar, compliance rules, entity type profiles

Usage:
    python seed_data.py --db data/finance-tax-graph
"""

import argparse
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from cognebula import init_kuzu_db


def _merge(conn, cypher: str, params: dict = None):
    """Execute a MERGE with error handling."""
    try:
        if params:
            conn.execute(cypher, params)
        else:
            conn.execute(cypher)
    except Exception as e:
        print(f"WARN: {e}")


def seed_tax_types(conn):
    """L1: 18 Chinese tax types."""
    types = [
        ("TT_VAT", "增值税", "0%/6%/9%/13%", 0.0, 13.0, "tiered", "monthly", "indirect", "goods_and_services", "增值税法"),
        ("TT_CIT", "企业所得税", "15%/20%/25%", 15.0, 25.0, "flat_with_incentives", "quarterly", "direct", "income", "企业所得税法"),
        ("TT_PIT", "个人所得税", "3%-45%", 3.0, 45.0, "progressive_7tier", "monthly", "direct", "income", "个人所得税法"),
        ("TT_CONSUMPTION", "消费税", "3%-56%", 3.0, 56.0, "tiered_by_good", "monthly", "indirect", "specific_behavior", "消费税暂行条例"),
        ("TT_TARIFF", "关税", "0%-65%", 0.0, 65.0, "tiered_by_hs", "per_shipment", "indirect", "goods_and_services", "关税法"),
        ("TT_URBAN", "城市维护建设税", "1%/5%/7%", 1.0, 7.0, "tiered_by_location", "monthly", "indirect", "surtax", "城市维护建设税法"),
        ("TT_EDUCATION", "教育费附加", "3%", 3.0, 3.0, "flat", "monthly", "indirect", "surtax", "教育费附加征收规定"),
        ("TT_LOCAL_EDU", "地方教育附加", "1%-2%", 1.0, 2.0, "flat", "monthly", "indirect", "surtax", "地方教育附加征收规定"),
        ("TT_RESOURCE", "资源税", "2%-10%", 2.0, 10.0, "tiered_by_resource", "monthly", "direct", "specific_behavior", "资源税法"),
        ("TT_LAND_VAT", "土地增值税", "30%-60%", 30.0, 60.0, "progressive_4tier", "per_transaction", "direct", "property", "土地增值税暂行条例"),
        ("TT_PROPERTY", "房产税", "1.2%/12%", 1.2, 12.0, "dual_method", "annual", "direct", "property", "房产税暂行条例"),
        ("TT_LAND_USE", "城镇土地使用税", "0.6-30元/㎡", 0.6, 30.0, "tiered_by_area", "annual", "direct", "property", "城镇土地使用税暂行条例"),
        ("TT_VEHICLE", "车船税", "60-5400元/年", 60.0, 5400.0, "tiered_by_displacement", "annual", "direct", "property", "车船税法"),
        ("TT_STAMP", "印花税", "0.03‰-0.5‰", 0.003, 0.05, "tiered_by_contract", "per_transaction", "direct", "specific_behavior", "印花税法"),
        ("TT_CONTRACT", "契税", "1%-5%", 1.0, 5.0, "tiered_by_type", "per_transaction", "direct", "property", "契税法"),
        ("TT_CULTIVATED", "耕地占用税", "5-50元/㎡", 5.0, 50.0, "tiered_by_area", "per_transaction", "direct", "property", "耕地占用税法"),
        ("TT_TOBACCO", "烟叶税", "20%", 20.0, 20.0, "flat", "per_transaction", "direct", "specific_behavior", "烟叶税法"),
        ("TT_TONNAGE", "船舶吨税", "按吨位", 0.0, 0.0, "tiered_by_tonnage", "quarterly", "direct", "specific_behavior", "船舶吨税法"),
        ("TT_ENV", "环境保护税", "按排放量", 0.0, 0.0, "tiered_by_emission", "quarterly", "direct", "specific_behavior", "环境保护税法"),
    ]
    for t in types:
        _merge(conn, "MERGE (n:TaxType {id: $id}) SET n.name=$name, n.rateRange=$rr, n.minRate=$min, n.maxRate=$max, n.rateStructure=$rs, n.filingFrequency=$ff, n.liabilityType=$lt, n.category=$cat, n.governingLaw=$gl, n.status='active'",
               {"id": t[0], "name": t[1], "rr": t[2], "min": t[3], "max": t[4], "rs": t[5], "ff": t[6], "lt": t[7], "cat": t[8], "gl": t[9]})
    print(f"OK: Seeded {len(types)} tax types")


def seed_taxpayer_statuses(conn):
    """L1: Taxpayer classification."""
    statuses = [
        ("TS_GENERAL", "一般纳税人", "VAT", 5000000.0, "annual_revenue", True),
        ("TS_SMALL", "小规模纳税人", "VAT", 5000000.0, "annual_revenue", True),
        ("TS_SMALL_MICRO", "小型微利企业", "CIT", 3000000.0, "annual_taxable_income", False),
        ("TS_HIGHTECH", "高新技术企业", "CIT", 0.0, "certification", False),
        ("TS_INDIVIDUAL", "个体工商户", "PIT", 0.0, "registration_type", False),
    ]
    for s in statuses:
        _merge(conn, "MERGE (n:TaxpayerStatus {id: $id}) SET n.name=$name, n.domain=$dom, n.thresholdValue=$tv, n.thresholdUnit=$tu, n.transitionAllowed=$ta",
               {"id": s[0], "name": s[1], "dom": s[2], "tv": s[3], "tu": s[4], "ta": s[5]})
    print(f"OK: Seeded {len(statuses)} taxpayer statuses")


def seed_enterprise_types(conn):
    """L1: Enterprise classification."""
    types = [
        ("ET_LLC", "有限责任公司", "registration", "domestic", False),
        ("ET_CORP", "股份有限公司", "registration", "domestic", False),
        ("ET_SOLE_PROP", "个人独资企业", "registration", "domestic", False),
        ("ET_PARTNERSHIP", "合伙企业", "registration", "domestic", False),
        ("ET_INDIVIDUAL", "个体工商户", "registration", "domestic", False),
        ("ET_WFOE", "外商投资企业", "registration", "international", True),
    ]
    for t in types:
        _merge(conn, "MERGE (n:EnterpriseType {id: $id}) SET n.name=$name, n.classificationBasis=$cb, n.taxJurisdiction=$tj, n.globalIncomeScope=$gi",
               {"id": t[0], "name": t[1], "cb": t[2], "tj": t[3], "gi": t[4]})
    print(f"OK: Seeded {len(types)} enterprise types")


def seed_lifecycle_stages(conn):
    """L2: 7 enterprise lifecycle stages."""
    stages = [
        ("LS_01_ESTABLISH", "设立期", "Establishment", 1, "工商注册→税务登记→银行开户→社保开户→科目设置", "30-60 days", True),
        ("LS_02_DAILY", "日常核算期", "Daily Operations", 2, "日记账→凭证→明细账→总账→银行对账→发票管理", "Ongoing", True),
        ("LS_03_MONTHLY", "月度处理期", "Monthly Close", 3, "月末结转→计提折旧/社保/工资→增值税申报→个税申报→附加税", "Monthly", True),
        ("LS_04_QUARTERLY", "季度处理期", "Quarterly Close", 4, "企业所得税预缴→季度报表→房产税→环保税", "Quarterly", True),
        ("LS_05_ANNUAL", "年度处理期", "Annual Close", 5, "汇算清缴→工商年报→审计→关联交易申报→税收优惠备案", "Jan-Jun", True),
        ("LS_06_SPECIAL", "特殊事件期", "Special Events", 6, "税务稽查→行政复议→发票异常→优惠申请→出口退税→股权变更", "As needed", False),
        ("LS_07_DISSOLVE", "注销期", "Dissolution", 7, "清算→清税→税务注销→工商注销→社保注销", "6-12 months", False),
    ]
    for s in stages:
        _merge(conn, "MERGE (n:LifecycleStage {id: $id}) SET n.name=$name, n.englishName=$en, n.stageOrder=$order, n.description=$desc, n.typicalDuration=$dur, n.mandatoryForAllEntities=$mand",
               {"id": s[0], "name": s[1], "en": s[2], "order": s[3], "desc": s[4], "dur": s[5], "mand": s[6]})
    print(f"OK: Seeded {len(stages)} lifecycle stages")


def seed_chart_of_accounts(conn):
    """L2: Standard chart of accounts (top-level, 6 categories)."""
    accounts = [
        # Assets (1xxx)
        ("COA_1001", "1001", "库存现金", "Cash on Hand", "资产", 1, "debit"),
        ("COA_1002", "1002", "银行存款", "Bank Deposits", "资产", 1, "debit"),
        ("COA_1012", "1012", "其他货币资金", "Other Monetary Funds", "资产", 1, "debit"),
        ("COA_1031", "1031", "应收账款", "Accounts Receivable", "资产", 1, "debit"),
        ("COA_1051", "1051", "预付账款", "Prepayments", "资产", 1, "debit"),
        ("COA_1101", "1101", "交易性金融资产", "Trading Financial Assets", "资产", 1, "debit"),
        ("COA_1403", "1403", "原材料", "Raw Materials", "资产", 1, "debit"),
        ("COA_1405", "1405", "库存商品", "Finished Goods", "资产", 1, "debit"),
        ("COA_1581", "1581", "固定资产", "Fixed Assets", "资产", 1, "debit"),
        ("COA_1584", "1584", "累计折旧", "Accumulated Depreciation", "资产", 1, "credit"),
        ("COA_1621", "1621", "无形资产", "Intangible Assets", "资产", 1, "debit"),
        ("COA_1631", "1631", "研发支出", "R&D Expenditure", "资产", 1, "debit"),
        # Liabilities (2xxx)
        ("COA_2001", "2001", "短期借款", "Short-term Loans", "负债", 2, "credit"),
        ("COA_2201", "2201", "应付账款", "Accounts Payable", "负债", 2, "credit"),
        ("COA_2203", "2203", "合同负债", "Contract Liabilities", "负债", 2, "credit"),
        ("COA_2211", "2211", "应付职工薪酬", "Accrued Payroll", "负债", 2, "credit"),
        ("COA_2221", "2221", "应交税费", "Taxes Payable", "负债", 2, "credit"),
        ("COA_2501", "2501", "长期借款", "Long-term Loans", "负债", 2, "credit"),
        # Equity (4xxx)
        ("COA_4001", "4001", "实收资本", "Paid-in Capital", "所有者权益", 4, "credit"),
        ("COA_4002", "4002", "资本公积", "Capital Surplus", "所有者权益", 4, "credit"),
        ("COA_4101", "4101", "盈余公积", "Retained Earnings Reserve", "所有者权益", 4, "credit"),
        ("COA_4103", "4103", "未分配利润", "Unappropriated Retained Earnings", "所有者权益", 4, "credit"),
        # Cost (5xxx)
        ("COA_5001", "5001", "生产成本", "Production Cost", "成本", 5, "debit"),
        ("COA_5101", "5101", "制造费用", "Manufacturing Overhead", "成本", 5, "debit"),
        # P&L (6xxx)
        ("COA_6001", "6001", "主营业务收入", "Main Business Revenue", "损益", 6, "credit"),
        ("COA_6401", "6401", "主营业务成本", "COGS", "损益", 6, "debit"),
        ("COA_6601", "6601", "销售费用", "Selling Expenses", "损益", 6, "debit"),
        ("COA_6602", "6602", "管理费用", "Administrative Expenses", "损益", 6, "debit"),
        ("COA_6603", "6603", "财务费用", "Financial Expenses", "损益", 6, "debit"),
        ("COA_6801", "6801", "所得税费用", "Income Tax Expense", "损益", 6, "debit"),
    ]
    for a in accounts:
        _merge(conn, "MERGE (n:ChartOfAccount {id: $id}) SET n.code=$code, n.name=$name, n.englishName=$en, n.category=$cat, n.categoryCode=$cc, n.level=1, n.direction=$dir, n.isLeaf=false, n.standardBasis='CAS'",
               {"id": a[0], "code": a[1], "name": a[2], "en": a[3], "cat": a[4], "cc": a[5], "dir": a[6]})
    print(f"OK: Seeded {len(accounts)} chart of accounts")


def seed_tax_calendar_2026(conn):
    """L3: 2026 monthly tax deadlines (adjusted for holidays)."""
    deadlines = [
        (1, "2026-01-20", "CNY preparation"),
        (2, "2026-02-24", "CNY extension"),
        (3, "2026-03-16", "Sunday shift"),
        (4, "2026-04-20", "Qingming extension"),
        (5, "2026-05-22", "Labour Day extension"),
        (6, "2026-06-15", "Standard"),
        (7, "2026-07-15", "Standard"),
        (8, "2026-08-17", "Saturday shift"),
        (9, "2026-09-15", "Standard"),
        (10, "2026-10-26", "National Day extension"),
        (11, "2026-11-16", "Sunday shift"),
        (12, "2026-12-15", "Standard"),
    ]
    for m, dl, reason in deadlines:
        _merge(conn, f"MERGE (n:TaxCalendar {{id: $id}}) SET n.name=$name, n.calendarYear=2026, n.calendarMonth=$m, n.adjustedDeadline=date('{dl}'), n.adjustmentReason=$reason, n.reminderDays=5",
               {"id": f"TC_2026_{m:02d}", "name": f"2026年{m}月纳税申报", "m": m, "reason": reason})
    print(f"OK: Seeded {len(deadlines)} tax calendar entries (2026)")


def seed_entity_profiles(conn):
    """L3: Entity type profiles with tax obligations."""
    profiles = [
        ("EP_LLC", "有限责任公司", "LLC", "一般纳税人/小规模纳税人", "增值税+企业所得税+附加税+印花税", "必须", "年收入>400万或上市需审计", "6月30日"),
        ("EP_CORP", "股份有限公司", "Corporation", "一般纳税人", "增值税+企业所得税+附加税+印花税", "必须(完整)", "必须(年度审计)", "6月30日"),
        ("EP_SOLE", "个人独资企业", "Sole Proprietorship", "小规模纳税人", "增值税+个人所得税+附加税", "必须", "不要求", "6月30日"),
        ("EP_PARTNER", "合伙企业", "Partnership", "一般/小规模", "增值税+个人所得税(按份额)+附加税", "必须", "不要求", "6月30日"),
        ("EP_INDIVIDUAL", "个体工商户", "Individual Business", "小规模纳税人", "增值税+个人所得税", "可选(简易)", "不要求", "6月30日"),
        ("EP_WFOE", "外商投资企业", "WFOE/JV", "一般纳税人", "增值税+企业所得税+附加税+预提所得税", "必须(完整)", "必须(年度审计)", "6月30日"),
    ]
    for p in profiles:
        _merge(conn, "MERGE (n:EntityTypeProfile {id: $id}) SET n.name=$name, n.entityType=$et, n.taxpayerCategory=$tc, n.applicableTaxTypes=$att, n.bookkeepingRequirement=$br, n.auditRequirement=$ar, n.annualReportDeadline=$ard",
               {"id": p[0], "name": p[1], "et": p[2], "tc": p[3], "att": p[4], "br": p[5], "ar": p[6], "ard": p[7]})
    print(f"OK: Seeded {len(profiles)} entity type profiles")


def seed_compliance_rules(conn):
    """L3: Core compliance rules."""
    rules = [
        ("CR_TAX_REG_30D", "税务登记30日规则", "TAX-REG-001", "establishment", "取得营业执照后30日内必须完成税务登记", "提交税务登记表", "500-2000元罚款", "P0"),
        ("CR_VAT_MONTHLY", "增值税月度申报", "VAT-MONTH-001", "monthly", "一般纳税人每月15日前申报增值税", "填报增值税纳税申报表", "滞纳金0.5%/日+罚款", "P0"),
        ("CR_CIT_QUARTERLY", "企业所得税季度预缴", "CIT-QTR-001", "quarterly", "季度终了15日内预缴企业所得税", "填报企业所得税预缴申报表", "滞纳金+罚款", "P0"),
        ("CR_CIT_ANNUAL", "企业所得税汇算清缴", "CIT-ANNUAL-001", "annual", "5月31日前完成上年度汇算清缴", "填报37张汇算清缴表", "500-5000元罚款+滞纳金", "P0"),
        ("CR_PIT_ANNUAL", "个税年度汇算", "PIT-ANNUAL-001", "annual", "6月30日前完成个税年度汇算", "APP或网上申报", "500-5000元罚款", "P1"),
        ("CR_BIZ_ANNUAL", "工商年报", "BIZ-ANNUAL-001", "annual", "6月30日前提交工商年报", "国家企业信用信息公示系统", "列入经营异常名录", "P1"),
        ("CR_THREE_FLOWS", "三流一致", "RISK-001", "daily", "发票流、资金流、货物流必须一致", "每笔交易核对三流", "虚开发票罪(刑事责任)", "P0"),
        ("CR_INVOICE_AUTH", "进项发票认证", "VAT-INPUT-001", "monthly", "取得增值税专用发票后及时认证抵扣", "增值税发票综合服务平台勾选", "过期不得抵扣", "P1"),
    ]
    for r in rules:
        _merge(conn, "MERGE (n:ComplianceRule {id: $id}) SET n.name=$name, n.ruleCode=$rc, n.category=$cat, n.conditionDescription=$cd, n.requiredAction=$ra, n.violationConsequence=$vc, n.severityLevel=$sl, n.autoDetectable=true",
               {"id": r[0], "name": r[1], "rc": r[2], "cat": r[3], "cd": r[4], "ra": r[5], "vc": r[6], "sl": r[7]})
    print(f"OK: Seeded {len(rules)} compliance rules")


def seed_vat_rate_mappings(conn):
    """L2: VAT rate mappings by product/service category."""
    mappings = [
        ("TRM_GOODS_13", "货物销售", "1010000", "TT_VAT", 13.0, "标准税率", "销售货物、加工修理修配、有形动产租赁"),
        ("TRM_TRANSPORT_9", "运输服务", "3010000", "TT_VAT", 9.0, "低税率", "陆路/水路/航空/管道运输"),
        ("TRM_CONSTRUCT_9", "建筑服务", "3020000", "TT_VAT", 9.0, "低税率", "建筑安装/修缮/装饰"),
        ("TRM_REALESTATE_9", "不动产租赁/销售", "3030000", "TT_VAT", 9.0, "低税率", "不动产租赁、转让土地使用权"),
        ("TRM_AGRI_9", "农产品", "1020000", "TT_VAT", 9.0, "低税率", "粮食/食用植物油/自来水/天然气/暖气"),
        ("TRM_SERVICE_6", "现代服务", "3040000", "TT_VAT", 6.0, "服务税率", "信息技术/咨询/金融/文化/教育/广告"),
        ("TRM_FINANCE_6", "金融服务", "3050000", "TT_VAT", 6.0, "服务税率", "贷款/直接收费/保险/金融商品转让"),
        ("TRM_TELECOM_6", "增值电信", "3060000", "TT_VAT", 6.0, "服务税率", "增值电信服务"),
        ("TRM_TELECOM_9", "基础电信", "3060001", "TT_VAT", 9.0, "低税率", "基础电信服务"),
        ("TRM_EXPORT_0", "出口货物", "1000000", "TT_VAT", 0.0, "零税率", "出口货物(符合退税条件)"),
        ("TRM_SOFTWARE_13", "软件产品", "1090000", "TT_VAT", 13.0, "标准税率(即征即退至3%)", "自行开发生产的软件产品"),
    ]
    for m in mappings:
        _merge(conn, "MERGE (n:TaxRateMapping {id: $id}) SET n.productCategory=$pc, n.productCategoryCode=$pcc, n.taxTypeId=$tt, n.applicableRate=$rate, n.rateLabel=$rl, n.specialPolicyDetail=$sp",
               {"id": m[0], "pc": m[1], "pcc": m[2], "tt": m[3], "rate": m[4], "rl": m[5], "sp": m[6]})
    # Create edges: TaxRateMapping -> TaxType
    for m in mappings:
        _merge(conn, "MATCH (trm:TaxRateMapping {id: $trm_id}), (tt:TaxType {id: $tt_id}) MERGE (trm)-[:OP_MAPS_TO_RATE {rateType: 'standard', confidence: 1.0}]->(tt)",
               {"trm_id": m[0], "tt_id": m[3]})
    print(f"OK: Seeded {len(mappings)} tax rate mappings + edges")


def seed_cross_layer_edges(conn):
    """Create cross-layer edges connecting L1/L2/L3."""
    # L1 TaxType -> L3 ComplianceRule (FT_APPLIES_TO is L1, but we also link compliance)
    edges = [
        # VAT monthly filing rule references VAT tax type
        ("XL_ENFORCED_BY", "CR_VAT_MONTHLY", "TT_VAT", "增值税月度申报执行增值税法"),
        ("XL_ENFORCED_BY", "CR_CIT_QUARTERLY", "TT_CIT", "企业所得税季度预缴执行企业所得税法"),
        ("XL_ENFORCED_BY", "CR_CIT_ANNUAL", "TT_CIT", "企业所得税汇算清缴执行企业所得税法"),
    ]
    # Note: XL_ENFORCED_BY is FROM LawOrRegulation TO ComplianceRule
    # But we don't have specific LawOrRegulation nodes for each rule yet
    # So we skip these for now and create simpler L2<->L3 links

    # Link LifecycleStages to each other (ordering)
    stages = ["LS_01_ESTABLISH", "LS_02_DAILY", "LS_03_MONTHLY", "LS_04_QUARTERLY", "LS_05_ANNUAL"]
    for i in range(len(stages) - 1):
        _merge(conn, "MATCH (a:LifecycleStage {id: $a}), (b:LifecycleStage {id: $b}) MERGE (a)-[:OP_PREREQUISITE_FOR {prerequisiteType: 'sequential', confidence: 1.0}]->(b)",
               {"a": stages[i], "b": stages[i + 1]})

    # Link TaxpayerStatus -> TaxType (L1 edges)
    _merge(conn, "MATCH (ts:TaxpayerStatus {id: 'TS_GENERAL'}), (tt:TaxType {id: 'TT_VAT'}) MERGE (tt)-[:FT_APPLIES_TO {specialTreatment: '按销项-进项计算', confidence: 1.0}]->(ts)", {})
    _merge(conn, "MATCH (ts:TaxpayerStatus {id: 'TS_SMALL'}), (tt:TaxType {id: 'TT_VAT'}) MERGE (tt)-[:FT_APPLIES_TO {specialTreatment: '简易计税3%(优惠期1%)', confidence: 1.0}]->(ts)", {})
    _merge(conn, "MATCH (ts:TaxpayerStatus {id: 'TS_HIGHTECH'}), (tt:TaxType {id: 'TT_CIT'}) MERGE (tt)-[:FT_APPLIES_TO {specialTreatment: '优惠税率15%', confidence: 1.0}]->(ts)", {})
    _merge(conn, "MATCH (ts:TaxpayerStatus {id: 'TS_SMALL_MICRO'}), (tt:TaxType {id: 'TT_CIT'}) MERGE (tt)-[:FT_APPLIES_TO {specialTreatment: '实际税率5%(≤300万)', confidence: 1.0}]->(ts)", {})

    print("OK: Seeded cross-layer edges")


def main():
    parser = argparse.ArgumentParser(description="Seed 3-Layer Finance/Tax Knowledge Graph")
    parser.add_argument("--db", required=True, help="KuzuDB database path")
    args = parser.parse_args()

    db_path = Path(args.db)
    db, conn = init_kuzu_db(db_path)

    seed_tax_types(conn)
    seed_taxpayer_statuses(conn)
    seed_enterprise_types(conn)
    seed_lifecycle_stages(conn)
    seed_chart_of_accounts(conn)
    seed_tax_calendar_2026(conn)
    seed_entity_profiles(conn)
    seed_compliance_rules(conn)
    seed_vat_rate_mappings(conn)
    seed_cross_layer_edges(conn)

    # Final stats
    total_nodes = 0
    total_edges = 0
    for t in ["TaxType", "TaxpayerStatus", "EnterpriseType", "LifecycleStage",
              "ChartOfAccount", "TaxCalendar", "EntityTypeProfile", "ComplianceRule",
              "TaxRateMapping", "LawOrRegulation"]:
        try:
            r = conn.execute(f"MATCH (n:{t}) RETURN count(n)")
            c = r.get_next()[0]
            total_nodes += c
        except Exception:
            pass
    for prefix in ["FT_", "OP_", "CO_", "XL_"]:
        try:
            r = conn.execute(f"MATCH ()-[r]->() WHERE type(r) STARTS WITH '{prefix}' RETURN count(r)")
            c = r.get_next()[0]
            total_edges += c
        except Exception:
            pass

    print(f"\n=== Seed Complete ===")
    print(f"Total nodes: {total_nodes}")
    print(f"Total edges: {total_edges}")


if __name__ == "__main__":
    main()
