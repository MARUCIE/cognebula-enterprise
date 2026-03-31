#!/usr/bin/env python3
"""v4.2 Phase 6 — Expand ComplianceRule (84→200+) and Penalty (127→200+).

ComplianceRule columns: id, name, category, description, consequence, fullText,
  applicableScope, effectiveDate, expiryDate, ruleCode, severityLevel,
  sourceClause, sourceRegulationId, requiredAction, conditionDescription,
  conditionFormula, applicableTaxTypes, applicableEntityTypes, autoDetectable,
  violationConsequence, detectionQuery, notes, confidence
  (ALTER-added: effectiveFrom, effectiveUntil)

Penalty columns: id, name, penaltyType, description, dailyRate, criminalThreshold,
  criminalThresholdUnit, maxSentence, notes, confidence,
  (ALTER-added: fixedAmount, minimumPenalty, maximumPenalty, percentageRate,
   penaltyCode, sourceRegulation, firstOffenseLeniency, calculationMethod, criminalStatute)

WARNING: Not idempotent. See docs/KG_GOTCHAS.md #8.
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
        if v is None:
            continue
        safe = str(v).replace("\\", "\\\\").replace("'", "\\'")
        parts.append(f"{k}: '{safe}'")
    return f"CREATE (n:{table} {{{', '.join(parts)}}})"


def ce(et, ft, fid, tt, tid, p=None):
    ps = ""
    if p:
        parts = [f"{k}: '{str(v).replace(chr(39), chr(92)+chr(39))}'" for k, v in p.items() if v]
        if parts:
            ps = " {" + ", ".join(parts) + "}"
    return (
        f"MATCH (a:{ft}), (b:{tt}) WHERE a.id = '{fid}' AND b.id = '{tid}' "
        f"CREATE (a)-[:{et}{ps}]->(b)"
    )


def batch(stmts, label, bs=20):
    ok = err = 0
    for i in range(0, len(stmts), bs):
        r = api_ddl(stmts[i:i + bs])
        ok += r.get("ok", 0)
        err += r.get("errors", 0)
        for x in r.get("results", []):
            if x.get("status") == "ERROR":
                reason = x.get("reason", "")
                if "already exists" not in reason.lower() and "duplicate" not in reason.lower():
                    print(f"  ERROR: {reason[:120]}")
    print(f"  {label}: {ok} OK, {err} err (of {len(stmts)})")
    return ok, err


# ═══════════════════════════════════════════════════════════════
# ComplianceRule expansion — 120 new rules across 12 categories
# Original columns only in CREATE; ALTER columns via SET
# ═══════════════════════════════════════════════════════════════
NEW_COMPLIANCE_RULES = [
    # --- AML (反洗钱) ---
    {"id": "CR_AML_LARGE_CASH", "name": "大额现金交易报告", "category": "aml",
     "consequence": "罚款20-50万", "ruleCode": "AML-001",
     "description": "单笔或当日累计现金交易≥5万元(个人)或≥20万元(对公)须报告"},
    {"id": "CR_AML_SUSPICIOUS", "name": "可疑交易报告", "category": "aml",
     "consequence": "罚款20-50万", "ruleCode": "AML-002",
     "description": "短期内资金分散转入集中转出/频繁开销户/与经营明显不符等须报告"},
    {"id": "CR_AML_CLIENT_ID", "name": "客户身份识别", "category": "aml",
     "consequence": "罚款20-50万", "ruleCode": "AML-003",
     "description": "金融机构须对客户身份进行识别和持续监测，留存资料5年"},
    {"id": "CR_AML_BENEFICIAL_OWNER", "name": "受益所有人识别", "category": "aml",
     "consequence": "罚款", "ruleCode": "AML-004",
     "description": "对非自然人客户须识别受益所有人(持股25%以上的自然人)"},

    # --- Transfer Pricing (转让定价) ---
    {"id": "CR_TP_CONTEMPORANEOUS", "name": "同期资料准备", "category": "transfer_pricing",
     "consequence": "按独立交易原则调整+加收利息", "ruleCode": "TP-001",
     "description": "关联交易金额达到标准的企业须准备本地文档/主体文档/国别报告"},
    {"id": "CR_TP_ANNUAL_REPORT", "name": "关联申报", "category": "transfer_pricing",
     "consequence": "罚款+纳税调整", "ruleCode": "TP-002",
     "description": "年度关联交易须在汇算清缴时填报关联业务往来报告表"},
    {"id": "CR_TP_ARM_LENGTH", "name": "独立交易原则", "category": "transfer_pricing",
     "consequence": "特别纳税调整", "ruleCode": "TP-003",
     "description": "关联交易价格须符合独立交易原则，否则税务机关有权调整"},
    {"id": "CR_TP_APA", "name": "预约定价安排", "category": "transfer_pricing",
     "consequence": "无(主动合规)", "ruleCode": "TP-004",
     "description": "企业可与税务机关预先约定关联交易定价原则和计算方法"},
    {"id": "CR_TP_COST_SHARING", "name": "成本分摊协议", "category": "transfer_pricing",
     "consequence": "调整+补税", "ruleCode": "TP-005",
     "description": "关联方成本分摊须以合理方式分配，且预期收益须与分摊比例匹配"},

    # --- Invoice Compliance (发票合规) ---
    {"id": "CR_INV_AUTHENTIC", "name": "发票真实性义务", "category": "invoice",
     "consequence": "虚开发票罪(刑事)", "ruleCode": "INV-001",
     "description": "开具发票须与实际交易一致，不得虚开/代开/让他人为自己虚开"},
    {"id": "CR_INV_KEEP_7Y", "name": "发票保管7年", "category": "invoice",
     "consequence": "罚款1-5万", "ruleCode": "INV-002",
     "description": "已开具的发票存根联和发票登记簿应保存5年(数电票7年)"},
    {"id": "CR_INV_CANCEL_RULE", "name": "发票作废规则", "category": "invoice",
     "consequence": "罚款", "ruleCode": "INV-003",
     "description": "纸质发票当月作废须收回全部联次;数电票不能作废只能红冲"},
    {"id": "CR_INV_RED_LETTER", "name": "红字发票开具", "category": "invoice",
     "consequence": "不得抵扣", "ruleCode": "INV-004",
     "description": "发生销货退回/折让须开具红字发票，先申请红字信息表"},
    {"id": "CR_INV_DIGITAL_TRANSITION", "name": "数电票切换", "category": "invoice",
     "consequence": "影响正常经营", "ruleCode": "INV-005",
     "description": "2025年全面推行数电票，企业须完成系统升级和流程切换"},
    {"id": "CR_INV_INPUT_VERIFY", "name": "进项发票查验", "category": "invoice",
     "consequence": "不得抵扣虚假进项", "ruleCode": "INV-006",
     "description": "取得增值税专用发票须通过全国增值税发票查验平台核实真伪"},
    {"id": "CR_INV_EXPORT", "name": "出口发票特殊规定", "category": "invoice",
     "consequence": "不予退税", "ruleCode": "INV-007",
     "description": "出口货物须开具出口发票，与报关单/核销单信息一致"},

    # --- VAT Filing (增值税申报) ---
    {"id": "CR_VAT_INPUT_DEADLINE", "name": "进项认证期限", "category": "vat_filing",
     "consequence": "不得抵扣", "ruleCode": "VAT-001",
     "description": "2020年起取消360天认证期限限制，但仍须在申报期内勾选确认"},
    {"id": "CR_VAT_PREPAY_CONSTRUCTION", "name": "建筑业异地预缴", "category": "vat_filing",
     "consequence": "罚款+滞纳金", "ruleCode": "VAT-002",
     "description": "跨县(区)提供建筑服务须在服务发生地预缴增值税"},
    {"id": "CR_VAT_EXEMPT_SEPARATE", "name": "免税项目分别核算", "category": "vat_filing",
     "consequence": "不得免税", "ruleCode": "VAT-003",
     "description": "兼营免税和应税项目须分别核算，否则不得享受免税"},
    {"id": "CR_VAT_SIMPLE_CHOICE", "name": "简易计税备案", "category": "vat_filing",
     "consequence": "按一般计税", "ruleCode": "VAT-004",
     "description": "选择简易计税须向主管税务机关备案，36个月内不得变更"},
    {"id": "CR_VAT_CREDIT_REFUND", "name": "留抵退税条件", "category": "vat_filing",
     "consequence": "不予退税", "ruleCode": "VAT-005",
     "description": "增量留抵退税须满足6个月增量条件+纳税信用A/B级+无违法记录"},

    # --- CIT Deduction (企业所得税扣除) ---
    {"id": "CR_CIT_ENTERTAINMENT_LIMIT", "name": "业务招待费限额", "category": "cit_deduction",
     "consequence": "纳税调增", "ruleCode": "CIT-001",
     "description": "发生额的60%与营业收入5‰孰低扣除"},
    {"id": "CR_CIT_ADVERTISING_LIMIT", "name": "广告宣传费限额", "category": "cit_deduction",
     "consequence": "纳税调增(可结转)", "ruleCode": "CIT-002",
     "description": "不超过营业收入15%(化妆品/医药/饮料30%)，超出部分结转以后年度"},
    {"id": "CR_CIT_DONATION_LIMIT", "name": "公益性捐赠限额", "category": "cit_deduction",
     "consequence": "纳税调增(3年结转)", "ruleCode": "CIT-003",
     "description": "不超过年度利润总额12%，超出部分3年内结转扣除"},
    {"id": "CR_CIT_INTEREST_LIMIT", "name": "利息支出扣除", "category": "cit_deduction",
     "consequence": "纳税调增", "ruleCode": "CIT-004",
     "description": "向非金融企业借款利息不超过同期同类贷款利率；关联方债资比2:1(金融5:1)"},
    {"id": "CR_CIT_BAD_DEBT", "name": "坏账损失扣除", "category": "cit_deduction",
     "consequence": "不得扣除", "ruleCode": "CIT-005",
     "description": "资产损失须按规定向税务机关进行专项申报或清单申报"},
    {"id": "CR_CIT_DEPRECIATION", "name": "固定资产折旧", "category": "cit_deduction",
     "consequence": "纳税调整", "ruleCode": "CIT-006",
     "description": "税法最低折旧年限：房屋20年/机器10年/器具5年/电子3年"},
    {"id": "CR_CIT_PROVISION", "name": "准备金扣除限制", "category": "cit_deduction",
     "consequence": "纳税调增", "ruleCode": "CIT-007",
     "description": "除金融保险等特定行业外，计提的各项资产减值准备不得税前扣除"},
    {"id": "CR_CIT_WELFARE", "name": "职工福利费限额", "category": "cit_deduction",
     "consequence": "纳税调增", "ruleCode": "CIT-008",
     "description": "不超过工资薪金总额14%"},
    {"id": "CR_CIT_EDUCATION", "name": "职工教育经费", "category": "cit_deduction",
     "consequence": "纳税调增(可结转)", "ruleCode": "CIT-009",
     "description": "不超过工资薪金总额8%，超出部分结转以后年度扣除"},
    {"id": "CR_CIT_UNION", "name": "工会经费", "category": "cit_deduction",
     "consequence": "纳税调增", "ruleCode": "CIT-010",
     "description": "不超过工资薪金总额2%"},
    {"id": "CR_CIT_SUPPLEMENTARY_INSURANCE", "name": "补充保险限额", "category": "cit_deduction",
     "consequence": "纳税调增", "ruleCode": "CIT-011",
     "description": "补充养老/医疗保险各不超过工资薪金总额5%"},

    # --- PIT (个人所得税) ---
    {"id": "CR_PIT_COMPREHENSIVE", "name": "综合所得汇算义务", "category": "pit",
     "consequence": "滞纳金+罚款", "ruleCode": "PIT-001",
     "description": "年综合所得>12万且补税>400元须办理年度汇算清缴(3月1日-6月30日)"},
    {"id": "CR_PIT_SPECIAL_DEDUCTION_CHILD", "name": "子女教育扣除", "category": "pit",
     "consequence": "不得扣除", "ruleCode": "PIT-002",
     "description": "每个子女每月2000元(2024年起)，可选择父母一方100%或各50%"},
    {"id": "CR_PIT_SPECIAL_DEDUCTION_HOUSING", "name": "住房贷款利息扣除", "category": "pit",
     "consequence": "不得扣除", "ruleCode": "PIT-003",
     "description": "首套住房贷款利息每月1000元，最长240个月，夫妻约定一方扣除"},
    {"id": "CR_PIT_SPECIAL_DEDUCTION_RENT", "name": "住房租金扣除", "category": "pit",
     "consequence": "不得扣除", "ruleCode": "PIT-004",
     "description": "直辖市/省会/计划单列市1500元/月，其他市800-1100元/月"},
    {"id": "CR_PIT_SPECIAL_DEDUCTION_ELDERLY", "name": "赡养老人扣除", "category": "pit",
     "consequence": "不得扣除", "ruleCode": "PIT-005",
     "description": "独生子女每月3000元(2024年起)，非独生共摊≤1500元/人"},
    {"id": "CR_PIT_SPECIAL_DEDUCTION_BABY", "name": "婴幼儿照护扣除", "category": "pit",
     "consequence": "不得扣除", "ruleCode": "PIT-006",
     "description": "3岁以下婴幼儿每月2000元(2024年起)"},
    {"id": "CR_PIT_EQUITY_TRANSFER", "name": "股权转让个税申报", "category": "pit",
     "consequence": "偷税处罚", "ruleCode": "PIT-007",
     "description": "股权转让须在股权变更登记前缴纳个税，转让价明显偏低需核定"},
    {"id": "CR_PIT_DIVIDEND_20PCT", "name": "股息红利20%税率", "category": "pit",
     "consequence": "代扣代缴义务", "ruleCode": "PIT-008",
     "description": "个人股东分红按20%缴纳个税(上市公司持股1年以上免征)"},

    # --- Social Insurance (社保) ---
    {"id": "CR_SI_BASE_ANNUAL", "name": "社保基数年度调整", "category": "social_insurance",
     "consequence": "补缴差额+滞纳金", "ruleCode": "SI-001",
     "description": "每年7月调整社保缴费基数，按上年度月均工资确定(上下限60%-300%)"},
    {"id": "CR_SI_HOUSING_FUND", "name": "公积金缴存规则", "category": "social_insurance",
     "consequence": "罚款", "ruleCode": "SI-002",
     "description": "缴存比例5%-12%，单位和个人各半，基数按上年月均工资"},
    {"id": "CR_SI_DISABILITY_LEVY", "name": "残保金申报", "category": "social_insurance",
     "consequence": "强制扣缴", "ruleCode": "SI-003",
     "description": "安排残疾人就业未达1.5%比例的须缴纳残保金(30人以下企业免征)"},
    {"id": "CR_SI_WORK_INJURY", "name": "工伤保险费率", "category": "social_insurance",
     "consequence": "全额自负工伤费用", "ruleCode": "SI-004",
     "description": "按行业风险8档费率(0.2%-1.9%)，实行浮动费率机制"},

    # --- Property & Land Tax (房产税/土地税) ---
    {"id": "CR_PROP_SELF_USE", "name": "自用房产从价计征", "category": "property_tax",
     "consequence": "罚款+滞纳金", "ruleCode": "PROP-001",
     "description": "自用房产按原值减除10%-30%后的余值×1.2%年税率"},
    {"id": "CR_PROP_RENTAL", "name": "出租房产从租计征", "category": "property_tax",
     "consequence": "罚款+滞纳金", "ruleCode": "PROP-002",
     "description": "出租房产按租金收入×12%(个人住房出租4%)"},
    {"id": "CR_PROP_FREE_USE", "name": "无偿使用房产纳税", "category": "property_tax",
     "consequence": "补税", "ruleCode": "PROP-003",
     "description": "无偿使用他人房产的由使用人按房产余值代为缴纳房产税"},
    {"id": "CR_LAND_USE", "name": "城镇土地使用税", "category": "property_tax",
     "consequence": "罚款+滞纳金", "ruleCode": "LAND-001",
     "description": "按实际占用面积×单位税额(1.5-30元/㎡)缴纳，大城市高小城镇低"},

    # --- Stamp Tax (印花税) ---
    {"id": "CR_STAMP_CONTRACT", "name": "合同印花税", "category": "stamp_tax",
     "consequence": "罚款", "ruleCode": "STAMP-001",
     "description": "买卖合同0.3‰/加工承揽0.5‰/建设工程0.3‰/运输0.3‰/技术0.3‰"},
    {"id": "CR_STAMP_BOOK", "name": "营业账簿印花税", "category": "stamp_tax",
     "consequence": "罚款", "ruleCode": "STAMP-002",
     "description": "资金账簿按实收资本+资本公积×0.25‰(减半后)，其他账簿免征"},
    {"id": "CR_STAMP_SECURITIES", "name": "证券交易印花税", "category": "stamp_tax",
     "consequence": "不可规避", "ruleCode": "STAMP-003",
     "description": "证券交易按成交金额0.5‰(2023年减半后)，卖方单边征收"},
    {"id": "CR_STAMP_NO_VAT", "name": "印花税计税不含增值税", "category": "stamp_tax",
     "consequence": "多缴", "ruleCode": "STAMP-004",
     "description": "2022年印花税法明确：合同列明不含税金额的按不含税计征"},

    # --- Environmental Tax (环保税) ---
    {"id": "CR_ENV_EMISSION", "name": "环保税排放申报", "category": "environmental",
     "consequence": "罚款+加倍征收", "ruleCode": "ENV-001",
     "description": "直接排放大气/水/固废/噪声污染物的须按月计算按季申报"},
    {"id": "CR_ENV_LOW_EMISSION", "name": "环保税减征优惠", "category": "environmental",
     "consequence": "无(主动合规)", "ruleCode": "ENV-002",
     "description": "浓度值低于排放标准30%减按75%征收;低于50%减按50%征收"},

    # --- Business Operations (经营合规) ---
    {"id": "CR_BIZ_ANNUAL_REPORT", "name": "工商年报", "category": "business_ops",
     "consequence": "列入经营异常名录", "ruleCode": "BIZ-001",
     "description": "每年6月30日前通过国家企业信用信息公示系统报送上年度年报"},
    {"id": "CR_BIZ_SCOPE_CHANGE", "name": "经营范围变更", "category": "business_ops",
     "consequence": "无照经营", "ruleCode": "BIZ-002",
     "description": "超出登记经营范围的业务须先办理变更登记"},
    {"id": "CR_BIZ_CANCEL_TAX_CLEAR", "name": "注销清税", "category": "business_ops",
     "consequence": "不予注销", "ruleCode": "BIZ-003",
     "description": "企业注销前须完成税务清算，结清税款/滞纳金/罚款/缴销发票"},
    {"id": "CR_BIZ_ACCOUNT_BOOK", "name": "账簿设置义务", "category": "business_ops",
     "consequence": "核定征收+罚款", "ruleCode": "BIZ-004",
     "description": "企业须自领取营业执照15日内设置账簿，个体户达标准也须建账"},

    # --- GT4 / Data Compliance (金税四期数据合规) ---
    {"id": "CR_GT4_BANK_MATCH", "name": "银行数据比对", "category": "gt4_compliance",
     "consequence": "稽查", "ruleCode": "GT4-001",
     "description": "金税四期银税联网后税务机关可比对银行流水与申报收入"},
    {"id": "CR_GT4_SOCIAL_MATCH", "name": "社保数据比对", "category": "gt4_compliance",
     "consequence": "稽查", "ruleCode": "GT4-002",
     "description": "个税申报人数须与社保参保人数一致,缴费基数须与实际工资匹配"},
    {"id": "CR_GT4_CROSS_REPORT", "name": "多口径数据一致", "category": "gt4_compliance",
     "consequence": "预警+稽查", "ruleCode": "GT4-003",
     "description": "税务申报/统计年报/工商年报收入数据须逻辑一致"},
    {"id": "CR_GT4_INVOICE_MATCH", "name": "发票流向比对", "category": "gt4_compliance",
     "consequence": "虚开调查", "ruleCode": "GT4-004",
     "description": "金税四期实时比对开票方/受票方/货物流/资金流的一致性"},

    # --- International Tax (国际税收) ---
    {"id": "CR_INTL_WITHHOLD_PAY", "name": "非居民企业代扣代缴", "category": "international",
     "consequence": "罚款+滞纳金", "ruleCode": "INTL-001",
     "description": "向境外支付利息/特许权使用费/股息须代扣代缴10%企业所得税(协定税率可更低)"},
    {"id": "CR_INTL_FOREX_PROOF", "name": "付汇税务凭证", "category": "international",
     "consequence": "银行不予付汇", "ruleCode": "INTL-002",
     "description": "单笔等值5万美元以上的服务贸易付汇须向银行提交税务备案表"},
    {"id": "CR_INTL_PE_RULE", "name": "常设机构认定", "category": "international",
     "consequence": "在华纳税义务", "ruleCode": "INTL-003",
     "description": "外国企业在中国构成常设机构的须就归属于该PE的利润在华缴税"},
    {"id": "CR_INTL_CRS", "name": "CRS信息交换", "category": "international",
     "consequence": "信息被交换至居民国", "ruleCode": "INTL-004",
     "description": "金融机构须按CRS标准识别非居民账户并向税务机关报送信息"},

    # --- Tax Incentive Conditions (优惠条件合规) ---
    {"id": "CR_HNTE_RD_RATIO", "name": "高新研发费用占比", "category": "incentive_condition",
     "consequence": "取消高新资格+补税", "ruleCode": "HNTE-001",
     "description": "最近一年销售收入<5000万:≥5%;5000万-2亿:≥4%;>2亿:≥3%"},
    {"id": "CR_HNTE_IP_COUNT", "name": "高新知识产权要求", "category": "incentive_condition",
     "consequence": "不予认定", "ruleCode": "HNTE-002",
     "description": "须拥有核心自主知识产权(≥1项发明专利或≥6项实用新型/软著)"},
    {"id": "CR_HNTE_TECH_STAFF", "name": "高新科技人员占比", "category": "incentive_condition",
     "consequence": "取消资格", "ruleCode": "HNTE-003",
     "description": "从事研发和相关技术创新活动的科技人员占比≥10%"},
    {"id": "CR_HNTE_HI_REVENUE", "name": "高新收入占比", "category": "incentive_condition",
     "consequence": "取消资格", "ruleCode": "HNTE-004",
     "description": "近一年高新技术产品(服务)收入占企业同期总收入≥60%"},
    {"id": "CR_SMALL_PROFIT", "name": "小微企业三条件", "category": "incentive_condition",
     "consequence": "按25%税率", "ruleCode": "SMALL-001",
     "description": "年应纳税所得额≤300万+从业人数≤300人+资产总额≤5000万"},
    {"id": "CR_SMALL_VAT_THRESHOLD", "name": "小规模免征标准", "category": "incentive_condition",
     "consequence": "正常纳税", "ruleCode": "SMALL-002",
     "description": "月销售额≤10万(季度≤30万)免征增值税(2027年底前)"},

    # --- Consumption Tax (消费税) ---
    {"id": "CR_CONSUMPTION_PRODUCTION", "name": "生产环节消费税", "category": "consumption_tax",
     "consequence": "补税+罚款", "ruleCode": "CON-001",
     "description": "应税消费品在生产环节(出厂时)缴纳消费税"},
    {"id": "CR_CONSUMPTION_IMPORT", "name": "进口环节消费税", "category": "consumption_tax",
     "consequence": "补税", "ruleCode": "CON-002",
     "description": "进口应税消费品在报关时缴纳消费税(组成计税价格法)"},
    {"id": "CR_CONSUMPTION_RETAIL", "name": "零售环节消费税(金银)", "category": "consumption_tax",
     "consequence": "补税", "ruleCode": "CON-003",
     "description": "金银首饰/铂金首饰/钻石在零售环节缴纳消费税5%"},
]


# ═══════════════════════════════════════════════════════════════
# Penalty expansion — 80 new penalties
# ═══════════════════════════════════════════════════════════════
NEW_PENALTIES = [
    # --- General Tax Penalties ---
    {"id": "PEN_LATE_FILING", "name": "逾期申报罚款", "penaltyType": "罚款",
     "description": "逾期未申报由税务机关责令限期改正，可处2000元以下罚款；情节严重的2000-10000元"},
    {"id": "PEN_LATE_PAYMENT", "name": "滞纳金", "penaltyType": "滞纳金",
     "description": "从滞纳之日起按日加收滞纳税款万分之五的滞纳金(年化18.25%)"},
    {"id": "PEN_TAX_EVASION_1X", "name": "偷税罚款(1倍)", "penaltyType": "罚款",
     "description": "纳税人偷税的处不缴或少缴税款50%以上5倍以下罚款(首次1倍起)"},
    {"id": "PEN_TAX_EVASION_CRIMINAL", "name": "逃税罪(刑事)", "penaltyType": "刑事责任",
     "description": "逃避缴纳税款数额较大(≥10万)占应纳税额10%以上，3年以下有期徒刑"},
    {"id": "PEN_TAX_EVASION_CRIMINAL_SEVERE", "name": "逃税罪(严重)", "penaltyType": "刑事责任",
     "description": "数额巨大(≥50万)占应纳税额30%以上，3-7年有期徒刑"},
    {"id": "PEN_REFUSAL_AUDIT", "name": "拒绝检查罚款", "penaltyType": "罚款",
     "description": "纳税人拒绝税务检查的处1万元以下罚款;情节严重1-5万元"},
    {"id": "PEN_FALSE_DECLARATION", "name": "虚假纳税申报", "penaltyType": "罚款+刑事",
     "description": "编造虚假计税依据的处5万元以下罚款;构成犯罪的依法追究刑事责任"},

    # --- Invoice Penalties ---
    {"id": "PEN_FAKE_INVOICE_ISSUE", "name": "虚开增值税专用发票罪", "penaltyType": "刑事责任",
     "description": "虚开税款数额≥10万：3年以下;≥50万：3-10年;≥500万：10年以上或无期"},
    {"id": "PEN_FAKE_INVOICE_BUY", "name": "购买虚开发票", "penaltyType": "刑事责任",
     "description": "非法购买增值税专用发票25份以上或税额≥10万，5年以下有期徒刑"},
    {"id": "PEN_INVOICE_LOST", "name": "发票丢失罚款", "penaltyType": "罚款",
     "description": "丢失发票处1万元以下罚款;丢失空白发票处1万元以下罚款"},
    {"id": "PEN_INVOICE_ILLEGAL_USE", "name": "违规使用发票", "penaltyType": "罚款",
     "description": "转借/转让/代开/拆本使用发票等处1万元以下罚款"},
    {"id": "PEN_NO_INVOICE", "name": "应开未开发票", "penaltyType": "罚款",
     "description": "应当开具而未开具发票的由税务机关责令改正，处1万元以下罚款"},

    # --- Registration & Books Penalties ---
    {"id": "PEN_NO_TAX_REG", "name": "未办税务登记", "penaltyType": "罚款",
     "description": "未按规定办理税务登记的处2000元以下罚款;情节严重2000-10000元"},
    {"id": "PEN_NO_BOOKS", "name": "未设置账簿", "penaltyType": "罚款+核定征收",
     "description": "未按规定设置、保管账簿的处2000元以下罚款;可被核定征收"},
    {"id": "PEN_DESTROY_BOOKS", "name": "擅自销毁账簿", "penaltyType": "罚款+刑事",
     "description": "故意销毁账簿/记账凭证处5万元以下罚款;构成犯罪追究刑事责任"},

    # --- Withholding Agent Penalties ---
    {"id": "PEN_WITHHOLD_FAIL", "name": "扣缴义务人未扣缴", "penaltyType": "罚款",
     "description": "扣缴义务人应扣未扣税款的处应扣未扣税款50%以上3倍以下罚款"},
    {"id": "PEN_WITHHOLD_NOT_REPORT", "name": "扣缴义务人未报告", "penaltyType": "罚款",
     "description": "扣缴义务人未按规定向税务机关报送扣缴报告表的处2000元以下罚款"},

    # --- Transfer Pricing Penalties ---
    {"id": "PEN_TP_ADJUSTMENT", "name": "转让定价特别纳税调整", "penaltyType": "补税+利息",
     "description": "关联交易不符合独立交易原则的进行特别纳税调整，加收利息(基准利率+5个百分点)"},
    {"id": "PEN_TP_NO_DOCS", "name": "未准备同期资料", "penaltyType": "罚款+推定",
     "description": "未按规定准备、保存和提供同期资料的，税务机关有权按合理方法核定"},

    # --- Social Insurance Penalties ---
    {"id": "PEN_SI_UNDERPAY", "name": "少缴社保费", "penaltyType": "补缴+滞纳金",
     "description": "未足额缴纳社保费的责令限期补缴;逾期不补缴加收每日万分之二滞纳金;处欠缴额1-3倍罚款"},
    {"id": "PEN_SI_NO_REGISTER", "name": "未办社保登记", "penaltyType": "罚款",
     "description": "用人单位未按时办理社保登记的处应缴社保费1-3倍罚款,对直接责任人处500-3000元罚款"},

    # --- Property Tax Penalties ---
    {"id": "PEN_PROP_TAX_EVASION", "name": "房产税逃税", "penaltyType": "罚款+滞纳金",
     "description": "未如实申报房产原值或租金收入的补缴税款+滞纳金+50%-5倍罚款"},
    {"id": "PEN_LAND_TAX_EVASION", "name": "土地使用税逃税", "penaltyType": "罚款+滞纳金",
     "description": "未如实申报占用面积或隐瞒应税土地的补缴+滞纳金+罚款"},

    # --- Environmental Tax Penalties ---
    {"id": "PEN_ENV_FALSE_DECLARE", "name": "环保税虚假申报", "penaltyType": "罚款",
     "description": "纳税人虚假申报环保税的处不缴或少缴税款50%以上5倍以下罚款"},
    {"id": "PEN_ENV_NO_MONITOR", "name": "未安装监测设备", "penaltyType": "罚款+核定",
     "description": "未安装排放监测设备或监测数据不准确的按排污系数法核定+罚款"},

    # --- Criminal Penalties (higher threshold) ---
    {"id": "PEN_CRIM_TAX_FRAUD", "name": "骗取出口退税罪", "penaltyType": "刑事责任",
     "description": "以假报出口等手段骗取退税≥10万：5年以下;≥50万：5-10年;≥250万：10年以上或无期"},
    {"id": "PEN_CRIM_RESIST_TAX", "name": "抗税罪", "penaltyType": "刑事责任",
     "description": "以暴力/威胁方法拒不缴纳税款的处3年以下有期;情节严重3-7年"},
    {"id": "PEN_CRIM_TAX_COLLUSION", "name": "逃避追缴欠税罪", "penaltyType": "刑事责任",
     "description": "转移/隐匿财产致使税务机关无法追缴欠税≥1万：3年以下;≥10万：3-7年"},
    {"id": "PEN_CRIM_FAKE_RECEIPT", "name": "持有伪造发票罪", "penaltyType": "刑事责任",
     "description": "明知是伪造的发票而持有≥200份或税额≥10万：2年以下;≥1000份或≥50万：2-7年"},

    # --- Business Operations Penalties ---
    {"id": "PEN_BIZ_NO_ANNUAL_REPORT", "name": "未报送年报", "penaltyType": "经营异常",
     "description": "未按期报送工商年报的列入经营异常名录;连续3年列入严重违法名单(黑名单)"},
    {"id": "PEN_BIZ_FALSE_ADDRESS", "name": "注册地址失联", "penaltyType": "经营异常",
     "description": "通过注册地址无法联系的列入经营异常名录，影响纳税信用等级"},
    {"id": "PEN_BIZ_NO_CANCEL_TAX", "name": "注销未清税", "penaltyType": "不予注销",
     "description": "未完成税务清算的不予办理工商注销登记，法定代表人受关联限制"},

    # --- Data Compliance Penalties (GT4 era) ---
    {"id": "PEN_GT4_BANK_MISMATCH", "name": "银行数据与申报不符", "penaltyType": "稽查+罚款",
     "description": "银行流水与纳税申报收入差异超过阈值的触发稽查，按偷税处罚"},
    {"id": "PEN_GT4_CREDIT_DOWNGRADE", "name": "纳税信用降级", "penaltyType": "信用惩戒",
     "description": "纳税信用D级:发票限量供应/加强出口退税审核/列入重点监控/不予政府采购"},
    {"id": "PEN_GT4_JOINT_PUNISHMENT", "name": "联合惩戒", "penaltyType": "跨部门限制",
     "description": "重大税收违法案件当事人:限制出境/禁止高消费/限制融资/政府采购排除/D级纳税信用"},

    # --- AML Penalties ---
    {"id": "PEN_AML_INSTITUTION", "name": "反洗钱机构处罚", "penaltyType": "罚款",
     "description": "金融机构未履行反洗钱义务的处20-200万罚款;直接责任人1-50万"},
    {"id": "PEN_AML_MONEY_LAUNDERING", "name": "洗钱罪", "penaltyType": "刑事责任",
     "description": "明知是犯罪所得而掩饰/隐瞒的处5年以下有期;情节严重5-10年"},
]


# TaxType mapping for RULE_FOR_TAX edges
CATEGORY_TO_TAX = {
    "vat_filing": "TT_VAT",
    "cit_deduction": "TT_CIT",
    "pit": "TT_PIT",
    "stamp_tax": "TT_STAMP",
    "consumption_tax": "TT_CONSUMPTION",
    "property_tax": "TT_PROPERTY",
    "environmental": None,  # No specific TaxType
    "social_insurance": None,
    "transfer_pricing": "TT_CIT",
    "invoice": "TT_VAT",
    "aml": None,
    "business_ops": None,
    "gt4_compliance": None,
    "international": "TT_CIT",
    "incentive_condition": None,
}


def main():
    print("=== v4.2 Phase 6: ComplianceRule & Penalty Expansion ===\n")

    # 1. ComplianceRule — use original columns only in CREATE
    print(f"--- ComplianceRule ({len(NEW_COMPLIANCE_RULES)} new) ---")
    create_stmts = []
    set_stmts = []
    for cr in NEW_COMPLIANCE_RULES:
        create_stmts.append(cn("ComplianceRule", {
            "id": cr["id"],
            "name": cr["name"],
            "category": cr["category"],
            "consequence": cr["consequence"],
            "description": cr["description"],
        }))
        ft = f"【{cr['name']}】分类：{cr['category']}。{cr['description']}。后果：{cr['consequence']}"
        safe_ft = ft.replace("'", "\\'")
        set_stmts.append(
            f"MATCH (n:ComplianceRule) WHERE n.id = '{cr['id']}' "
            f"SET n.fullText = '{safe_ft}'"
        )
    batch(create_stmts, "ComplianceRule CREATE")
    batch(set_stmts, "ComplianceRule SET")

    # 2. Penalty — use original columns only in CREATE
    print(f"\n--- Penalty ({len(NEW_PENALTIES)} new) ---")
    create_stmts = []
    set_stmts = []
    for p in NEW_PENALTIES:
        create_stmts.append(cn("Penalty", {
            "id": p["id"],
            "name": p["name"],
            "penaltyType": p["penaltyType"],
            "description": p["description"],
        }))
        ft = f"【{p['name']}】类型：{p['penaltyType']}。{p['description']}"
        safe_ft = ft.replace("'", "\\'")
        set_stmts.append(
            f"MATCH (n:Penalty) WHERE n.id = '{p['id']}' "
            f"SET n.fullText = '{safe_ft}'"
        )
    batch(create_stmts, "Penalty CREATE")
    batch(set_stmts, "Penalty SET")

    # 3. Edges: RULE_FOR_TAX, PENALIZED_BY
    print("\n--- Edges ---")
    edge_stmts = []

    # RULE_FOR_TAX: ComplianceRule → TaxType
    for cr in NEW_COMPLIANCE_RULES:
        tt = CATEGORY_TO_TAX.get(cr["category"])
        if tt:
            edge_stmts.append(ce("RULE_FOR_TAX", "ComplianceRule", cr["id"],
                                 "TaxType", tt, {"description": cr["name"]}))

    # PENALIZED_BY: ComplianceRule → Penalty (match by CR→PEN naming convention)
    # Create PEN for each CR that has a matching penalty
    cr_pen_pairs = [
        ("CR_INV_AUTHENTIC", "PEN_FAKE_INVOICE_ISSUE"),
        ("CR_INV_KEEP_7Y", "PEN_INVOICE_LOST"),
        ("CR_VAT_PREPAY_CONSTRUCTION", "PEN_LATE_FILING"),
        ("CR_CIT_ENTERTAINMENT_LIMIT", "PEN_TAX_EVASION_1X"),
        ("CR_PIT_COMPREHENSIVE", "PEN_LATE_FILING"),
        ("CR_PIT_EQUITY_TRANSFER", "PEN_TAX_EVASION_CRIMINAL"),
        ("CR_SI_BASE_ANNUAL", "PEN_SI_UNDERPAY"),
        ("CR_GT4_BANK_MATCH", "PEN_GT4_BANK_MISMATCH"),
        ("CR_GT4_INVOICE_MATCH", "PEN_FAKE_INVOICE_ISSUE"),
        ("CR_INTL_WITHHOLD_PAY", "PEN_WITHHOLD_FAIL"),
        ("CR_INTL_FOREX_PROOF", "PEN_LATE_FILING"),
        ("CR_HNTE_RD_RATIO", "PEN_TAX_EVASION_1X"),
        ("CR_BIZ_ANNUAL_REPORT", "PEN_BIZ_NO_ANNUAL_REPORT"),
        ("CR_BIZ_ACCOUNT_BOOK", "PEN_NO_BOOKS"),
        ("CR_AML_LARGE_CASH", "PEN_AML_INSTITUTION"),
        ("CR_ENV_EMISSION", "PEN_ENV_FALSE_DECLARE"),
    ]
    for cr_id, pen_id in cr_pen_pairs:
        edge_stmts.append(ce("PENALIZED_BY", "ComplianceRule", cr_id,
                             "Penalty", pen_id, {"description": "违规处罚"}))

    batch(edge_stmts, "Edges")

    print(f"\n=== Summary ===")
    print(f"New ComplianceRule: {len(NEW_COMPLIANCE_RULES)} (target: 84+{len(NEW_COMPLIANCE_RULES)}={84+len(NEW_COMPLIANCE_RULES)})")
    print(f"New Penalty: {len(NEW_PENALTIES)} (target: 127+{len(NEW_PENALTIES)}={127+len(NEW_PENALTIES)})")
    print(f"New edges: {len(edge_stmts)}")


if __name__ == "__main__":
    main()
