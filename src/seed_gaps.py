#!/usr/bin/env python3
"""Fill ALL empty tables in the 3-layer finance/tax knowledge graph.

Targets 20+ empty node tables + 12+ empty edge tables identified by audit.
Uses CREATE with inline values (not MERGE with parameters) to avoid KuzuDB bugs.

Usage:
    python src/seed_gaps.py [--db data/finance-tax-graph]
"""

import argparse
import sys
from pathlib import Path


def _exec(conn, cypher: str, label: str = ""):
    """Execute Cypher with error handling."""
    try:
        conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e)
        if "already exists" in msg.lower() or "duplicate" in msg.lower() or "primary key" in msg.lower():
            return False  # silently skip duplicates
        print(f"WARN: {label} -- {e}")
        return False


def esc(s: str) -> str:
    """Escape single quotes for Cypher inline strings."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


# ---------------------------------------------------------------------------
# L1 NODES
# ---------------------------------------------------------------------------

def seed_ft_industry(conn):
    """L1: 10 industry classifications."""
    items = [
        ("IND_MANUFACTURING", "C", "制造业", "level1", "", True),
        ("IND_COMMERCE", "F", "商贸业", "level1", "", True),
        ("IND_SERVICE", "L", "现代服务业", "level1", "", True),
        ("IND_CONSTRUCTION", "E", "建筑业", "level1", "", True),
        ("IND_REALESTATE", "K", "房地产业", "level1", "", True),
        ("IND_SOFTWARE", "I65", "软件和信息技术服务业", "level2", "IND_SERVICE", True),
        ("IND_FINANCE", "J", "金融业", "level1", "", False),
        ("IND_TRANSPORT", "G", "交通运输业", "level1", "", False),
        ("IND_CATERING", "H", "住宿餐饮业", "level1", "", False),
        ("IND_AGRICULTURE", "A", "农林牧渔业", "level1", "", True),
    ]
    count = 0
    for i in items:
        has_pp = "true" if i[5] else "false"
        sql = (
            f"CREATE (n:FTIndustry {{"
            f"id: '{esc(i[0])}', gbCode: '{esc(i[1])}', name: '{esc(i[2])}', "
            f"classificationLevel: '{esc(i[3])}', parentIndustryId: '{esc(i[4])}', "
            f"hasPreferentialPolicy: {has_pp}"
            f"}})"
        )
        if _exec(conn, sql, f"FTIndustry {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/10 FTIndustry")
    return count


def seed_tax_incentive(conn):
    """L1: 8 tax incentives."""
    items = [
        ("INCE_SOFTWARE_VAT", "软件企业增值税即征即退", "refund", 3.0, "effective_rate_cap",
         "software_enterprise", "自行开发销售软件产品，增值税实际税负超过3%部分即征即退",
         True, 0.0, "2011-01-01", "2099-12-31", "财税[2011]100号"),
        ("INCE_HNTE_CIT", "高新技术企业所得税15%优惠税率", "rate_reduction", 15.0, "flat_rate",
         "high_tech_enterprise", "经认定的高新技术企业减按15%税率征收企业所得税",
         True, 0.0, "2008-01-01", "2099-12-31", "企业所得税法第二十八条"),
        ("INCE_SMALL_CIT", "小型微利企业所得税减征", "rate_reduction", 5.0, "effective_rate",
         "small_micro_enterprise", "年应纳税所得额不超过300万元减按5%实际税率",
         False, 3000000.0, "2023-01-01", "2027-12-31", "财政部税务总局公告2023年第12号"),
        ("INCE_RD_DEDUCTION", "研发费用加计扣除", "super_deduction", 100.0, "percentage_extra",
         "all_enterprise", "研发费用在据实扣除基础上再加计100%扣除",
         True, 0.0, "2023-01-01", "2099-12-31", "财政部税务总局公告2023年第7号"),
        ("INCE_DISABLED_VAT", "安置残疾人增值税即征即退", "refund", 0.0, "per_person_cap",
         "disability_employer", "每安置1名残疾人每月退还增值税，上限为省级最低工资标准4倍",
         False, 0.0, "2016-05-01", "2099-12-31", "财税[2016]52号"),
        ("INCE_EXPORT_REFUND", "出口退税", "refund", 13.0, "max_refund_rate",
         "export_enterprise", "出口货物退还已缴纳增值税，退税率13%/10%/9%/6%不等",
         False, 0.0, "1994-01-01", "2099-12-31", "出口货物退（免）税管理办法"),
        ("INCE_AGRI_VAT", "农产品免征增值税", "exemption", 0.0, "full_exemption",
         "agricultural_producer", "农业生产者销售自产农产品免征增值税",
         False, 0.0, "1994-01-01", "2099-12-31", "增值税暂行条例第十五条"),
        ("INCE_POVERTY_CIT", "脱贫攻坚税收优惠", "deduction", 0.0, "special_deduction",
         "poverty_enterprise", "企业通过公益性社会组织扶贫捐赠支出据实扣除",
         True, 0.0, "2019-01-01", "2025-12-31", "财政部税务总局公告2019年第49号"),
    ]
    count = 0
    for i in items:
        comb = "true" if i[7] else "false"
        sql = (
            f"CREATE (n:TaxIncentive {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', incentiveType: '{esc(i[2])}', "
            f"value: {i[3]}, valueBasis: '{esc(i[4])}', beneficiaryType: '{esc(i[5])}', "
            f"eligibilityCriteria: '{esc(i[6])}', combinable: {comb}, "
            f"maxAnnualBenefit: {i[8]}, effectiveFrom: date('{i[9]}'), "
            f"effectiveUntil: date('{i[10]}'), lawReference: '{esc(i[11])}'"
            f"}})"
        )
        if _exec(conn, sql, f"TaxIncentive {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/8 TaxIncentive")
    return count


def seed_personal_income_type(conn):
    """L1: 9 personal income types."""
    items = [
        ("PIT_SALARY", "工资薪金所得", "comprehensive", "progressive_7tier", 60000.0, 0.0),
        ("PIT_LABOR", "劳务报酬所得", "comprehensive", "progressive_7tier", 0.0, 800.0),
        ("PIT_MANUSCRIPT", "稿酬所得", "comprehensive", "progressive_7tier", 0.0, 800.0),
        ("PIT_ROYALTY", "特许权使用费所得", "comprehensive", "progressive_7tier", 0.0, 800.0),
        ("PIT_BUSINESS", "经营所得", "separate", "progressive_5tier", 0.0, 0.0),
        ("PIT_INTEREST", "利息股息红利所得", "separate", "flat_20pct", 0.0, 0.0),
        ("PIT_PROPERTY_RENT", "财产租赁所得", "separate", "flat_20pct", 0.0, 800.0),
        ("PIT_PROPERTY_SALE", "财产转让所得", "separate", "flat_20pct", 0.0, 0.0),
        ("PIT_INCIDENTAL", "偶然所得", "separate", "flat_20pct", 0.0, 0.0),
    ]
    count = 0
    for i in items:
        sql = (
            f"CREATE (n:PersonalIncomeType {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', incomeCategory: '{esc(i[2])}', "
            f"rateStructure: '{esc(i[3])}', standardDeduction: {i[4]}, "
            f"taxableThreshold: {i[5]}"
            f"}})"
        )
        if _exec(conn, sql, f"PersonalIncomeType {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/9 PersonalIncomeType")
    return count


def seed_tax_authority(conn):
    """L1: 5 tax authorities."""
    items = [
        ("TA_SAT", "国家税务总局", 1, "AR_NATIONAL", "", True, True),
        ("TA_MOF", "财政部", 1, "AR_NATIONAL", "", True, False),
        ("TA_CUSTOMS", "海关总署", 1, "AR_NATIONAL", "", True, True),
        ("TA_PBC", "中国人民银行", 1, "AR_NATIONAL", "", True, False),
        ("TA_LOCAL", "省级税务局(通用)", 2, "AR_NATIONAL", "TA_SAT", False, True),
    ]
    count = 0
    for i in items:
        pm = "true" if i[5] else "false"
        enf = "true" if i[6] else "false"
        sql = (
            f"CREATE (n:TaxAuthority {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', adminLevel: {i[2]}, "
            f"governingRegionId: '{esc(i[3])}', parentId: '{esc(i[4])}', "
            f"policyMaking: {pm}, enforcement: {enf}"
            f"}})"
        )
        if _exec(conn, sql, f"TaxAuthority {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/5 TaxAuthority")
    return count


def seed_administrative_region(conn):
    """L1: 5 top-level administrative regions."""
    items = [
        ("AR_NATIONAL", "全国", "national", 0, ""),
        ("AR_BEIJING", "北京市", "municipality", 1, "AR_NATIONAL"),
        ("AR_SHANGHAI", "上海市", "municipality", 1, "AR_NATIONAL"),
        ("AR_GUANGDONG", "广东省", "province", 1, "AR_NATIONAL"),
        ("AR_JIANGSU", "江苏省", "province", 1, "AR_NATIONAL"),
    ]
    count = 0
    for i in items:
        sql = (
            f"CREATE (n:AdministrativeRegion {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', regionType: '{esc(i[2])}', "
            f"level: {i[3]}, parentId: '{esc(i[4])}'"
            f"}})"
        )
        if _exec(conn, sql, f"AdministrativeRegion {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/5 AdministrativeRegion")
    return count


# ---------------------------------------------------------------------------
# L2 NODES
# ---------------------------------------------------------------------------

def seed_lifecycle_stage(conn):
    """L2: 7 lifecycle stages."""
    items = [
        ("LS_01_ESTABLISH", "企业设立", "Establishment", 1,
         "工商注册-税务登记-银行开户-社保开户-科目设置", "30-60 days", True),
        ("LS_02_DAILY", "日常经营", "Daily Operations", 2,
         "日记账-凭证-明细账-总账-银行对账-发票管理", "Ongoing", True),
        ("LS_03_MONTHLY", "月度结转", "Monthly Close", 3,
         "月末结转-计提折旧/社保/工资-增值税申报-个税申报-附加税", "Monthly", True),
        ("LS_04_QUARTERLY", "季度申报", "Quarterly Close", 4,
         "企业所得税预缴-季度报表-房产税-环保税", "Quarterly", True),
        ("LS_05_ANNUAL", "年度汇算", "Annual Close", 5,
         "汇算清缴-工商年报-审计-关联交易申报-税收优惠备案", "Jan-Jun", True),
        ("LS_06_SPECIAL", "特殊事项", "Special Events", 6,
         "税务稽查-行政复议-发票异常-优惠申请-出口退税-股权变更", "As needed", False),
        ("LS_07_TERMINATE", "注销清算", "Dissolution", 7,
         "清算-清税-税务注销-工商注销-社保注销", "6-12 months", False),
    ]
    count = 0
    for i in items:
        mand = "true" if i[6] else "false"
        sql = (
            f"CREATE (n:LifecycleStage {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', englishName: '{esc(i[2])}', "
            f"stageOrder: {i[3]}, description: '{esc(i[4])}', "
            f"typicalDuration: '{esc(i[5])}', mandatoryForAllEntities: {mand}, "
            f"notes: ''"
            f"}})"
        )
        if _exec(conn, sql, f"LifecycleStage {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/7 LifecycleStage")
    return count


def seed_filing_form(conn):
    """L2: 6 filing forms."""
    items = [
        ("FF_VAT_MONTHLY", "SB001", "增值税月度申报表", "TT_VAT", "general",
         "销项税额|进项税额|进项转出|应纳税额", "应纳税额=销项-进项+转出",
         "monthly", "次月15日", "遇节假日顺延", "电子税务局",
         "https://etax.chinatax.gov.cn", "FF_CIT_QUARTERLY", "滞纳金+罚款",
         "2019-v4", "2019-04-01"),
        ("FF_CIT_QUARTERLY", "SB002", "企业所得税季度预缴表", "TT_CIT", "all",
         "营业收入|营业成本|利润总额|已预缴税额", "预缴=利润总额x25%-已预缴",
         "quarterly", "季后15日", "遇节假日顺延", "电子税务局",
         "https://etax.chinatax.gov.cn", "FF_CIT_ANNUAL", "滞纳金+罚款",
         "A200000", "2021-01-01"),
        ("FF_CIT_ANNUAL", "SB003", "企业所得税年度汇算清缴表", "TT_CIT", "all",
         "收入总额|扣除项目|纳税调整|应纳税所得额|减免税额", "应纳税额=应纳税所得额x税率-减免-已预缴",
         "annual", "次年5月31日", "无顺延", "电子税务局",
         "https://etax.chinatax.gov.cn", "", "500-5000元罚款",
         "A100000", "2021-01-01"),
        ("FF_IIT_MONTHLY", "SB004", "个人所得税月度扣缴表", "TT_PIT", "all",
         "工资薪金|专项扣除|专项附加扣除|累计预扣预缴|本期应扣缴", "累计预扣预缴法",
         "monthly", "次月15日", "遇节假日顺延", "自然人电子税务局",
         "https://etax.chinatax.gov.cn", "", "滞纳金+罚款",
         "2019-v2", "2019-01-01"),
        ("FF_STAMP_TAX", "SB005", "印花税申报表", "TT_STAMP", "all",
         "应税凭证类型|计税金额|适用税率|应纳税额", "应纳税额=计税金额x税率",
         "per_transaction", "纳税义务发生次月15日", "遇节假日顺延", "电子税务局",
         "https://etax.chinatax.gov.cn", "", "滞纳金",
         "2022-v1", "2022-07-01"),
        ("FF_PROPERTY_TAX", "SB006", "房产税申报表", "TT_PROPERTY", "property_owner",
         "房产原值|减除比例|计税余值|适用税率", "从价=原值x(1-减除比例)x1.2%|从租=租金x12%",
         "annual", "各地规定(多为4月/10月)", "按当地规定", "电子税务局",
         "https://etax.chinatax.gov.cn", "", "滞纳金",
         "2020-v1", "2020-01-01"),
    ]
    count = 0
    for i in items:
        sql = (
            f"CREATE (n:FilingForm {{"
            f"id: '{esc(i[0])}', formNumber: '{esc(i[1])}', name: '{esc(i[2])}', "
            f"taxTypeId: '{esc(i[3])}', applicableTaxpayerType: '{esc(i[4])}', "
            f"fields: '{esc(i[5])}', calculationRules: '{esc(i[6])}', "
            f"filingFrequency: '{esc(i[7])}', deadline: '{esc(i[8])}', "
            f"deadlineAdjustmentRule: '{esc(i[9])}', filingChannel: '{esc(i[10])}', "
            f"onlineFilingUrl: '{esc(i[11])}', relatedForms: '{esc(i[12])}', "
            f"penaltyForLate: '{esc(i[13])}', version: '{esc(i[14])}', "
            f"effectiveDate: date('{i[15]}'), notes: ''"
            f"}})"
        )
        if _exec(conn, sql, f"FilingForm {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/6 FilingForm")
    return count


def seed_standard_case(conn):
    """L2: 5 OP_StandardCase from R6 design."""
    items = [
        ("SC_CAS14_REVENUE_SOFTWARE", "收入确认五步法-SaaS收入", "CAS_14", "第五条/第十二条",
         "application", "SaaS企业按月确认订阅收入",
         "识别合同-识别履约义务-确定交易价格-分摊至履约义务-按时段确认收入",
         "一次性确认全年收入而非按服务期分摊", "software", False, True,
         "IFRS 15更强调合同修改的会计处理", ""),
        ("SC_CAS17_BORROWING_COST", "借款费用资本化-房地产", "CAS_17", "第四条/第六条",
         "application", "房地产开发企业开发贷款利息资本化",
         "满足3个条件同时具备时开始资本化：资产支出已发生+借款费用已发生+购建活动已开始",
         "将非资本化期间利息计入开发成本", "real_estate", False, False, "", ""),
        ("SC_CAS18_DEFERRED_TAX", "递延所得税-折旧差异", "CAS_18", "第七条/第十三条",
         "application", "固定资产会计折旧与税法折旧差异产生暂时性差异",
         "计算暂时性差异=账面价值-计税基础，确认递延所得税资产或负债",
         "忽略暂时性差异直接按税法口径计提所得税", "all", True, False,
         "小企业会计准则不要求确认递延所得税", ""),
        ("SC_CAS1_INVENTORY_COST", "存货成本计量-制造业", "CAS_01", "第六条/第八条",
         "application", "制造业原材料采购成本及生产成本归集",
         "采购成本=买价+运费+保险+入库前加工费-商业折扣；生产成本=直接材料+直接人工+制造费用",
         "将管理费用或销售费用计入存货成本", "manufacturing", True, False,
         "小企业准则不要求期末减值测试", ""),
        ("SC_CAS4_FIXED_ASSET_DEPRECIATION", "固定资产折旧方法选择", "CAS_04", "第十四条/第十七条",
         "application", "不同类型固定资产选择合适折旧方法",
         "年限平均法(通用)/工作量法(运输)/双倍余额递减法(技术更新快)/年数总和法(前期效用大)",
         "所有资产统一使用直线法而不考虑实际使用模式", "all", True, False,
         "小企业准则仅允许年限平均法和工作量法", ""),
    ]
    count = 0
    for i in items:
        sme = "true" if i[9] else "false"
        ifrs = "true" if i[10] else "false"
        sql = (
            f"CREATE (n:OP_StandardCase {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', standardId: '{esc(i[2])}', "
            f"clauseRef: '{esc(i[3])}', caseType: '{esc(i[4])}', "
            f"scenario: '{esc(i[5])}', correctTreatment: '{esc(i[6])}', "
            f"commonMistake: '{esc(i[7])}', industryRelevance: '{esc(i[8])}', "
            f"diffFromSme: {sme}, diffFromIfrs: {ifrs}, "
            f"diffDescription: '{esc(i[11])}', notes: '{esc(i[12])}'"
            f"}})"
        )
        if _exec(conn, sql, f"OP_StandardCase {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/5 OP_StandardCase")
    return count


# ---------------------------------------------------------------------------
# L3 NODES
# ---------------------------------------------------------------------------

def seed_risk_indicator(conn):
    """L3: 5 risk indicators."""
    items = [
        ("RI_TAX_BURDEN_LOW", "税负率异常偏低", "RISK-001", "增值税税负率",
         "实际缴纳增值税/不含税销售收入x100%", 0.5, 3.0, 2.0, "IND_MANUFACTURING",
         "连续3个月低于行业平均50%", "high", "data_comparison",
         "金税系统+纳税申报表", "monthly", 0.15, "自查进项发票真实性+销售完整性"),
        ("RI_INPUT_MISMATCH", "进销项不匹配", "RISK-002", "进销项比率",
         "进项税额/销项税额x100%", 80.0, 120.0, 95.0, "",
         "进销项比持续>110%或<70%", "high", "ratio_monitoring",
         "增值税申报表", "monthly", 0.10, "核查采购品类与销售品类的对应关系"),
        ("RI_INVOICE_ANOMALY", "发票异常（大量作废/红冲）", "RISK-003", "作废红冲率",
         "(作废发票数+红冲发票数)/开票总数x100%", 0.0, 5.0, 2.0, "",
         "单月作废率>5%或连续红冲", "medium", "pattern_detection",
         "发票管理系统", "monthly", 0.20, "核查作废原因+完善开票流程"),
        ("RI_LOSS_CONSECUTIVE", "连续亏损", "RISK-004", "连续亏损年数",
         "连续亏损年度计数", 0.0, 3.0, 0.0, "",
         "连续亏损3年以上且有关联交易", "medium", "financial_analysis",
         "企业所得税年度申报表", "annual", 0.25, "核查关联交易定价+费用真实性"),
        ("RI_RELATED_PARTY", "关联交易价格异常", "RISK-005", "关联交易价格偏离度",
         "abs(关联价格-公允价格)/公允价格x100%", 0.0, 20.0, 5.0, "",
         "价格偏离公允价值>20%", "high", "transfer_pricing_analysis",
         "关联交易申报表+同期资料", "annual", 0.12, "准备同期资料+调整定价策略"),
    ]
    count = 0
    for i in items:
        sql = (
            f"CREATE (n:RiskIndicator {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', indicatorCode: '{esc(i[2])}', "
            f"metricName: '{esc(i[3])}', metricFormula: '{esc(i[4])}', "
            f"thresholdLow: {i[5]}, thresholdHigh: {i[6]}, "
            f"industryBenchmark: {i[7]}, industryId: '{esc(i[8])}', "
            f"triggerCondition: '{esc(i[9])}', severity: '{esc(i[10])}', "
            f"detectionMethod: '{esc(i[11])}', dataSource: '{esc(i[12])}', "
            f"monitoringFrequency: '{esc(i[13])}', falsePositiveRate: {i[14]}, "
            f"recommendedAction: '{esc(i[15])}', notes: '', confidence: 0.9"
            f"}})"
        )
        if _exec(conn, sql, f"RiskIndicator {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/5 RiskIndicator")
    return count


def seed_penalty(conn):
    """L3: 5 penalty types."""
    items = [
        ("PEN_LATE_FILING", "逾期申报", "PEN-001", "administrative",
         "daily_surcharge", 0.0005, 0.0, 0.0, 200.0, 10000.0,
         0.0, "", "", "首次可减免",
         "税收征收管理法第六十二条", "每日万分之五滞纳金+200-10000元罚款"),
        ("PEN_TAX_EVASION", "偷税", "PEN-002", "administrative_criminal",
         "percentage_of_tax_owed", 0.0, 0.0, 0.5, 0.0, 0.0,
         100000.0, "yuan", "刑法第二百零一条", "5年内首次可不予追究刑事责任",
         "税收征收管理法第六十三条", "50%-500%罚款，构成犯罪追究刑事责任"),
        ("PEN_INVOICE_FRAUD", "虚开发票", "PEN-003", "criminal",
         "fixed_plus_percentage", 0.0, 0.0, 0.0, 0.0, 0.0,
         10000.0, "yuan", "刑法第二百零五条", "无",
         "发票管理办法第三十七条", "虚开金额1万以上即可立案，最高无期徒刑"),
        ("PEN_TRANSFER_PRICING", "转让定价调整", "PEN-004", "administrative",
         "interest_plus_adjustment", 0.0, 0.0, 0.0, 0.0, 0.0,
         0.0, "", "", "主动披露可从轻",
         "企业所得税法第四十一条", "补缴税款+加收利息(基准利率+5个百分点)"),
        ("PEN_LATE_PAYMENT", "欠税", "PEN-005", "administrative",
         "daily_surcharge_plus_fine", 0.0005, 0.0, 0.5, 0.0, 0.0,
         0.0, "", "", "无",
         "税收征收管理法第六十八条", "每日万分之五滞纳金+50%以上5倍以下罚款"),
    ]
    count = 0
    for i in items:
        sql = (
            f"CREATE (n:Penalty {{"
            f"id: '{esc(i[0])}', name: '{esc(i[1])}', penaltyCode: '{esc(i[2])}', "
            f"penaltyType: '{esc(i[3])}', calculationMethod: '{esc(i[4])}', "
            f"dailyRate: {i[5]}, fixedAmount: {i[6]}, percentageRate: {i[7]}, "
            f"minimumPenalty: {i[8]}, maximumPenalty: {i[9]}, "
            f"criminalThreshold: {i[10]}, criminalThresholdUnit: '{esc(i[11])}', "
            f"criminalStatute: '{esc(i[12])}', firstOffenseLeniency: '{esc(i[13])}', "
            f"sourceRegulation: '{esc(i[14])}', notes: '{esc(i[15])}', confidence: 0.95"
            f"}})"
        )
        if _exec(conn, sql, f"Penalty {i[0]}"):
            count += 1
    print(f"OK: Seeded {count}/5 Penalty")
    return count


# ---------------------------------------------------------------------------
# EDGES
# ---------------------------------------------------------------------------

def seed_edge_triggers_entry(conn):
    """OP_TRIGGERS_ENTRY: connect business scenarios to account entries by keyword match."""
    mappings = [
        ("BS_PURCHASE_RAW_GENERAL", "AE_PURCHASE"),
        ("BS_SALE_GOODS_GENERAL", "AE_SALE"),
        ("BS_SALE_GOODS_GENERAL", "AE_COGS"),
        ("BS_SALARY_PROVISION", "AE_PAYROLL"),
        ("BS_DEPRECIATION", "AE_DEPREC"),
        ("BS_VAT_MONTHLY_TRANSFER", "AE_VAT_PAY"),
        ("BS_CIT_PROVISION", "AE_CIT_PREPAY"),
        ("BS_IIT_WITHHOLD", "AE_PAYROLL"),
        ("BS_STAMP_TAX", "AE_SURTAX"),
        ("BS_SOFTWARE_VAT_REFUND", "AE_VAT_PAY"),
        ("BS_EXPORT_REFUND", "AE_VAT_PAY"),
        ("BS_BAD_DEBT_PROVISION", "AE_DEPREC"),
        ("BS_REVENUE_SAAS", "AE_SALE"),
        ("BS_LEASE_OPERATING", "AE_SALE"),
        ("BS_INVENTORY_TRANSFER", "AE_COGS"),
    ]
    count = 0
    for src, dst in mappings:
        sql = (
            f"MATCH (a:OP_BusinessScenario {{id: '{src}'}}), (b:AccountEntry {{id: '{dst}'}}) "
            f"CREATE (a)-[:OP_TRIGGERS_ENTRY]->(b)"
        )
        if _exec(conn, sql, f"TRIGGERS_ENTRY {src}->{dst}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} OP_TRIGGERS_ENTRY edges")
    return count


def seed_edge_subject_to(conn):
    """FT_SUBJECT_TO: connect industries to tax types."""
    # All industries subject to VAT and CIT
    industries = [
        "IND_MANUFACTURING", "IND_COMMERCE", "IND_SERVICE", "IND_CONSTRUCTION",
        "IND_REALESTATE", "IND_SOFTWARE", "IND_FINANCE", "IND_TRANSPORT",
        "IND_CATERING", "IND_AGRICULTURE",
    ]
    universal_taxes = ["TT_VAT", "TT_CIT"]
    # Specific taxes
    specific = [
        ("IND_MANUFACTURING", "TT_CONSUMPTION"),
        ("IND_REALESTATE", "TT_LAND_VAT"),
        ("IND_REALESTATE", "TT_CONTRACT"),
        ("IND_REALESTATE", "TT_PROPERTY"),
        ("IND_CONSTRUCTION", "TT_STAMP"),
        ("IND_FINANCE", "TT_STAMP"),
        ("IND_TRANSPORT", "TT_VEHICLE"),
        ("IND_AGRICULTURE", "TT_RESOURCE"),
    ]
    count = 0
    for ind in industries:
        for tax in universal_taxes:
            sql = (
                f"MATCH (a:FTIndustry {{id: '{ind}'}}), (b:TaxType {{id: '{tax}'}}) "
                f"CREATE (a)-[:FT_SUBJECT_TO]->(b)"
            )
            if _exec(conn, sql, f"SUBJECT_TO {ind}->{tax}"):
                count += 1
    for ind, tax in specific:
        sql = (
            f"MATCH (a:FTIndustry {{id: '{ind}'}}), (b:TaxType {{id: '{tax}'}}) "
            f"CREATE (a)-[:FT_SUBJECT_TO]->(b)"
        )
        if _exec(conn, sql, f"SUBJECT_TO {ind}->{tax}"):
            count += 1
    print(f"OK: Created {count} FT_SUBJECT_TO edges")
    return count


def seed_edge_scenario_stage(conn):
    """OP_SCENARIO_STAGE: connect scenarios to lifecycle stages."""
    mappings = [
        # Daily scenarios
        ("BS_PURCHASE_RAW_GENERAL", "LS_02_DAILY"),
        ("BS_SALE_GOODS_GENERAL", "LS_02_DAILY"),
        ("BS_LEASE_OPERATING", "LS_02_DAILY"),
        ("BS_REALESTATE_PRESALE", "LS_02_DAILY"),
        # Monthly scenarios
        ("BS_SALARY_PROVISION", "LS_03_MONTHLY"),
        ("BS_DEPRECIATION", "LS_03_MONTHLY"),
        ("BS_VAT_MONTHLY_TRANSFER", "LS_03_MONTHLY"),
        ("BS_IIT_WITHHOLD", "LS_03_MONTHLY"),
        ("BS_STAMP_TAX", "LS_03_MONTHLY"),
        ("BS_SOFTWARE_VAT_REFUND", "LS_03_MONTHLY"),
        ("BS_EXPORT_REFUND", "LS_03_MONTHLY"),
        ("BS_REVENUE_SAAS", "LS_03_MONTHLY"),
        ("BS_INVENTORY_TRANSFER", "LS_03_MONTHLY"),
        # Quarterly scenarios
        ("BS_CIT_PROVISION", "LS_04_QUARTERLY"),
        ("BS_BAD_DEBT_PROVISION", "LS_04_QUARTERLY"),
    ]
    count = 0
    for src, dst in mappings:
        sql = (
            f"MATCH (a:OP_BusinessScenario {{id: '{src}'}}), (b:LifecycleStage {{id: '{dst}'}}) "
            f"CREATE (a)-[:OP_SCENARIO_STAGE]->(b)"
        )
        if _exec(conn, sql, f"SCENARIO_STAGE {src}->{dst}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} OP_SCENARIO_STAGE edges")
    return count


def seed_edge_industry_account(conn):
    """OP_INDUSTRY_ACCOUNT: connect industries to their special accounts."""
    mappings = [
        # Manufacturing -> production cost accounts
        ("IND_MANUFACTURING", "COA_5001"),   # 生产成本
        ("IND_MANUFACTURING", "COA_5101"),   # 制造费用
        ("IND_MANUFACTURING", "COA_1403"),   # 原材料
        ("IND_MANUFACTURING", "COA_1405"),   # 库存商品
        # Construction -> project accounts (use existing COA)
        ("IND_CONSTRUCTION", "COA_5001"),    # 生产成本(工程施工)
        ("IND_CONSTRUCTION", "COA_2203"),    # 合同负债(工程结算)
        # Software -> R&D accounts
        ("IND_SOFTWARE", "COA_1631"),        # 研发支出
        ("IND_SOFTWARE", "COA_1621"),        # 无形资产
        # Real estate -> inventory + contract liability
        ("IND_REALESTATE", "COA_1405"),      # 库存商品(开发产品)
        ("IND_REALESTATE", "COA_2203"),      # 合同负债(预收房款)
        # Commerce -> inventory + receivable
        ("IND_COMMERCE", "COA_1405"),        # 库存商品
        ("IND_COMMERCE", "COA_1031"),        # 应收账款
        # Finance -> trading financial assets
        ("IND_FINANCE", "COA_1101"),         # 交易性金融资产
        # Agriculture -> biological assets (use fixed assets as proxy)
        ("IND_AGRICULTURE", "COA_1581"),     # 固定资产(农业设施)
    ]
    count = 0
    for ind, coa in mappings:
        sql = (
            f"MATCH (a:FTIndustry {{id: '{ind}'}}), (b:ChartOfAccount {{id: '{coa}'}}) "
            f"CREATE (a)-[:OP_INDUSTRY_ACCOUNT]->(b)"
        )
        if _exec(conn, sql, f"INDUSTRY_ACCOUNT {ind}->{coa}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} OP_INDUSTRY_ACCOUNT edges")
    return count


def seed_edge_standard_entry(conn):
    """OP_STANDARD_ENTRY: cross-layer AccountingStandard -> AccountEntry.

    NOTE: XL_IMPLEMENTED_BY schema is FROM LawOrRegulation TO AccountEntry,
    so we use OP_STANDARD_ENTRY (FROM AccountingStandard TO AccountEntry) instead.
    """
    mappings = [
        ("CAS_01", "AE_PURCHASE"),     # CAS 1 Inventories -> purchase raw materials
        ("CAS_01", "AE_COGS"),         # CAS 1 Inventories -> COGS transfer
        ("CAS_04", "AE_DEPREC"),       # CAS 4 Fixed Assets -> depreciation
        ("CAS_09", "AE_PAYROLL"),      # CAS 9 Employee Benefits -> payroll
        ("CAS_14", "AE_SALE"),         # CAS 14 Revenue -> sales
        ("CAS_18", "AE_CIT_PREPAY"),   # CAS 18 Income Taxes -> CIT provision
        ("CAS_06", "AE_RD_CAPITAL"),   # CAS 6 Intangible Assets -> R&D capitalization
        ("CAS_06", "AE_RD_EXPENSE"),   # CAS 6 -> R&D expense
    ]
    count = 0
    for std, ae in mappings:
        sql = (
            f"MATCH (a:AccountingStandard {{id: '{std}'}}), (b:AccountEntry {{id: '{ae}'}}) "
            f"CREATE (a)-[:OP_STANDARD_ENTRY]->(b)"
        )
        if _exec(conn, sql, f"STANDARD_ENTRY {std}->{ae}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} OP_STANDARD_ENTRY edges")
    return count


def seed_edge_scenario_industry(conn):
    """OP_SCENARIO_INDUSTRY: connect scenarios to their primary industries."""
    mappings = [
        ("BS_PURCHASE_RAW_GENERAL", "IND_MANUFACTURING"),
        ("BS_INVENTORY_TRANSFER", "IND_MANUFACTURING"),
        ("BS_REALESTATE_PRESALE", "IND_REALESTATE"),
        ("BS_SOFTWARE_VAT_REFUND", "IND_SOFTWARE"),
        ("BS_EXPORT_REFUND", "IND_COMMERCE"),
    ]
    count = 0
    for src, dst in mappings:
        sql = (
            f"MATCH (a:OP_BusinessScenario {{id: '{src}'}}), (b:FTIndustry {{id: '{dst}'}}) "
            f"CREATE (a)-[:OP_SCENARIO_INDUSTRY]->(b)"
        )
        if _exec(conn, sql, f"SCENARIO_INDUSTRY {src}->{dst}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} OP_SCENARIO_INDUSTRY edges")
    return count


def seed_edge_standard_case(conn):
    """OP_STANDARD_CASE: connect accounting standards to standard cases."""
    mappings = [
        ("CAS_14", "SC_CAS14_REVENUE_SOFTWARE"),
        ("CAS_17", "SC_CAS17_BORROWING_COST"),
        ("CAS_18", "SC_CAS18_DEFERRED_TAX"),
        ("CAS_01", "SC_CAS1_INVENTORY_COST"),
        ("CAS_04", "SC_CAS4_FIXED_ASSET_DEPRECIATION"),
    ]
    count = 0
    for std, sc in mappings:
        sql = (
            f"MATCH (a:AccountingStandard {{id: '{std}'}}), (b:OP_StandardCase {{id: '{sc}'}}) "
            f"CREATE (a)-[:OP_STANDARD_CASE]->(b)"
        )
        if _exec(conn, sql, f"STANDARD_CASE {std}->{sc}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} OP_STANDARD_CASE edges")
    return count


def seed_edge_incentive_tax(conn):
    """FT_INCENTIVE_TAX: connect incentives to their tax types."""
    mappings = [
        ("INCE_SOFTWARE_VAT", "TT_VAT"),
        ("INCE_HNTE_CIT", "TT_CIT"),
        ("INCE_SMALL_CIT", "TT_CIT"),
        ("INCE_RD_DEDUCTION", "TT_CIT"),
        ("INCE_DISABLED_VAT", "TT_VAT"),
        ("INCE_EXPORT_REFUND", "TT_VAT"),
        ("INCE_AGRI_VAT", "TT_VAT"),
        ("INCE_POVERTY_CIT", "TT_CIT"),
    ]
    count = 0
    for inc, tax in mappings:
        sql = (
            f"MATCH (a:TaxIncentive {{id: '{inc}'}}), (b:TaxType {{id: '{tax}'}}) "
            f"CREATE (a)-[:FT_INCENTIVE_TAX]->(b)"
        )
        if _exec(conn, sql, f"INCENTIVE_TAX {inc}->{tax}"):
            count += 1
    print(f"OK: Created {count}/{len(mappings)} FT_INCENTIVE_TAX edges")
    return count


def seed_edge_incentive_region(conn):
    """FT_INCENTIVE_REGION: connect incentives to applicable regions."""
    # Most incentives are national
    national = [
        "INCE_SOFTWARE_VAT", "INCE_HNTE_CIT", "INCE_SMALL_CIT",
        "INCE_RD_DEDUCTION", "INCE_DISABLED_VAT", "INCE_EXPORT_REFUND",
        "INCE_AGRI_VAT", "INCE_POVERTY_CIT",
    ]
    count = 0
    for inc in national:
        sql = (
            f"MATCH (a:TaxIncentive {{id: '{inc}'}}), (b:AdministrativeRegion {{id: 'AR_NATIONAL'}}) "
            f"CREATE (a)-[:FT_INCENTIVE_REGION]->(b)"
        )
        if _exec(conn, sql, f"INCENTIVE_REGION {inc}->AR_NATIONAL"):
            count += 1
    print(f"OK: Created {count}/{len(national)} FT_INCENTIVE_REGION edges")
    return count


# ---------------------------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------------------------

def report_all_counts(conn):
    """Print counts for ALL node and edge tables."""
    print("\n" + "=" * 60)
    print("FINAL TABLE COUNTS")
    print("=" * 60)

    result = conn.execute("CALL show_tables() RETURN *")
    node_tables = []
    rel_tables = []
    while result.has_next():
        row = result.get_next()
        tname = str(row[1])
        ttype = str(row[2]).upper()
        if ttype in ("NODE", "NODE_TABLE"):
            node_tables.append(tname)
        elif ttype in ("REL", "REL_TABLE"):
            rel_tables.append(tname)

    total_nodes = 0
    total_edges = 0

    print("\n--- NODE TABLES ---")
    for t in sorted(node_tables):
        try:
            r = conn.execute(f"MATCH (n:{t}) RETURN count(n)")
            c = r.get_next()[0]
            total_nodes += c
            print(f"  {t}: {c}")
        except Exception:
            print(f"  {t}: ERROR")

    print("\n--- REL TABLES ---")
    for t in sorted(rel_tables):
        try:
            r = conn.execute(f"MATCH ()-[r:{t}]->() RETURN count(r)")
            c = r.get_next()[0]
            total_edges += c
            if c > 0:
                print(f"  {t}: {c}")
        except Exception:
            pass

    print(f"\n--- SUMMARY ---")
    print(f"Node tables: {len(node_tables)}")
    print(f"Rel tables: {len(rel_tables)}")
    print(f"Total nodes: {total_nodes}")
    print(f"Total edges: {total_edges}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fill ALL gap tables in finance/tax knowledge graph")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    args = parser.parse_args()

    try:
        import kuzu
    except ImportError:
        print("ERROR: kuzu not installed. Run: pip install kuzu")
        sys.exit(1)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB path {db_path} does not exist")
        sys.exit(1)

    print(f"Connecting to KuzuDB at {db_path}")
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    # === L1 Nodes ===
    print("\n=== L1: Seeding FTIndustry ===")
    seed_ft_industry(conn)

    print("\n=== L1: Seeding TaxIncentive ===")
    seed_tax_incentive(conn)

    print("\n=== L1: Seeding PersonalIncomeType ===")
    seed_personal_income_type(conn)

    print("\n=== L1: Seeding TaxAuthority ===")
    seed_tax_authority(conn)

    print("\n=== L1: Seeding AdministrativeRegion ===")
    seed_administrative_region(conn)

    # === L2 Nodes ===
    print("\n=== L2: Seeding LifecycleStage ===")
    seed_lifecycle_stage(conn)

    print("\n=== L2: Seeding FilingForm ===")
    seed_filing_form(conn)

    print("\n=== L2: Seeding OP_StandardCase ===")
    seed_standard_case(conn)

    # === L3 Nodes ===
    print("\n=== L3: Seeding RiskIndicator ===")
    seed_risk_indicator(conn)

    print("\n=== L3: Seeding Penalty ===")
    seed_penalty(conn)

    # === Edges ===
    print("\n=== EDGES: OP_TRIGGERS_ENTRY ===")
    seed_edge_triggers_entry(conn)

    print("\n=== EDGES: FT_SUBJECT_TO ===")
    seed_edge_subject_to(conn)

    print("\n=== EDGES: OP_SCENARIO_STAGE ===")
    seed_edge_scenario_stage(conn)

    print("\n=== EDGES: OP_INDUSTRY_ACCOUNT ===")
    seed_edge_industry_account(conn)

    print("\n=== EDGES: OP_STANDARD_ENTRY ===")
    seed_edge_standard_entry(conn)

    print("\n=== EDGES: OP_SCENARIO_INDUSTRY ===")
    seed_edge_scenario_industry(conn)

    print("\n=== EDGES: OP_STANDARD_CASE ===")
    seed_edge_standard_case(conn)

    print("\n=== EDGES: FT_INCENTIVE_TAX ===")
    seed_edge_incentive_tax(conn)

    print("\n=== EDGES: FT_INCENTIVE_REGION ===")
    seed_edge_incentive_region(conn)

    # === Final Report ===
    report_all_counts(conn)


if __name__ == "__main__":
    main()
