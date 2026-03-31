#!/usr/bin/env python3
"""v4.2 Phase 5 — Expand ResponseStrategy (17→40) and PolicyChange (11→30).

Only adds NEW records. Existing IDs are skipped by design (CREATE will fail on dup).
See docs/KG_GOTCHAS.md #8.
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
# New ResponseStrategy (23 additional, IDs RS_NEW_*)
# Covers: invoice forensics, industry-specific, GT4 advanced,
# tax incentive management, international, digital economy
# ═══════════════════════════════════════════════════════════════
NEW_STRATEGIES = [
    # Invoice advanced
    {"id": "RS_INV_VOID_AUDIT", "name": "作废发票专项审查", "strategyType": "internal_audit",
     "targetRisk": "RI_INV_03", "timeframe": "5天",
     "actionSteps": "1.提取12个月作废发票清单;2.分析作废原因分布;3.核查开具后24小时内作废;4.排查虚开后作废模式;5.建立作废审批流程",
     "description": "作废率超标的专项审查，重点排查虚开后作废的掩饰行为"},
    {"id": "RS_INV_TOPLINE", "name": "顶额开票整改", "strategyType": "process_optimization",
     "targetRisk": "RI_INV_04", "timeframe": "持续",
     "actionSteps": "1.统计各票种顶额开票率;2.评估是否需要提升发票限额;3.申请提升限额;4.优化开票流程避免分拆;5.留存业务解释材料",
     "description": "顶额开票率过高时的合规整改方案"},
    {"id": "RS_INV_CROSS_REGION", "name": "跨区域发票合规检查", "strategyType": "compliance_review",
     "targetRisk": "RI_INV_08", "timeframe": "15天",
     "actionSteps": "1.统计跨区域发票占比;2.核实异地经营资质;3.检查是否需要外出经营管理证明;4.确认预缴义务;5.整理分支机构清单",
     "description": "大量跨区域开票需要确认异地经营合规性"},
    {"id": "RS_INV_MONTH_END", "name": "月末集中开票均衡化", "strategyType": "process_optimization",
     "targetRisk": "RI_INV_09", "timeframe": "持续",
     "actionSteps": "1.分析开票时间分布;2.设置每旬开票额度;3.与业务部门协调发货节奏;4.建立预开票机制;5.监控月均衡指数",
     "description": "将月末集中开票分散到全月，降低异常预警"},
    {"id": "RS_INV_ZERO_RATE", "name": "零税率发票合规梳理", "strategyType": "compliance_review",
     "targetRisk": "RI_INV_10", "timeframe": "10天",
     "actionSteps": "1.区分免税/零税率/不征税;2.核查出口业务单证;3.验证零税率资格;4.纠正错误开票;5.补缴差额税款",
     "description": "非出口企业零税率发票异常高时的合规梳理"},

    # Financial ratio advanced
    {"id": "RS_FR_RECEIVABLE", "name": "应收账款异常核查", "strategyType": "financial_analysis",
     "targetRisk": "RI_FR_06", "timeframe": "15天",
     "actionSteps": "1.账龄分析;2.核查大额应收交易对手;3.评估坏账准备计提;4.检查关联方应收;5.与客户对账确认",
     "description": "应收账款周转异常慢可能隐含虚构收入或关联交易"},
    {"id": "RS_FR_INVENTORY", "name": "存货异常处理", "strategyType": "financial_analysis",
     "targetRisk": "RI_FR_07", "timeframe": "15天",
     "actionSteps": "1.存货盘点;2.计算各类存货周转率;3.评估跌价准备;4.核查异常入库/出库;5.清理滞销存货",
     "description": "存货周转异常时的综合处理方案"},
    {"id": "RS_FR_DEBT_RATIO", "name": "高负债风险应对", "strategyType": "financial_restructuring",
     "targetRisk": "RI_FR_10", "timeframe": "长期",
     "actionSteps": "1.分析负债结构;2.评估偿债能力;3.检查隐性担保;4.制定还款计划;5.必要时增资或引入投资",
     "description": "资不抵债且仍持续经营需要合理解释和财务重组"},
    {"id": "RS_FR_TRANSFER_PRICE", "name": "关联交易定价调整", "strategyType": "transfer_pricing",
     "targetRisk": "RI_FR_11", "timeframe": "年度",
     "actionSteps": "1.识别关联方;2.编制同期资料;3.可比性分析;4.利润水平测试;5.必要时调整定价或准备特殊事项说明",
     "description": "关联交易占比高且利润率偏低时的转让定价合规"},
    {"id": "RS_FR_OTHER_RECEIVABLE", "name": "其他应收款清理", "strategyType": "financial_cleanup",
     "targetRisk": "RI_FR_12", "timeframe": "30天",
     "actionSteps": "1.逐笔核实其他应收明细;2.清理股东借款(超年度视同分红);3.催收逾期款项;4.核销坏账;5.规范借支流程",
     "description": "其他应收款膨胀是股东抽资和体外循环的常见信号"},
    {"id": "RS_FR_EXPENSE_RATIO", "name": "期间费用合规审查", "strategyType": "compliance_review",
     "targetRisk": "RI_FR_03", "timeframe": "15天",
     "actionSteps": "1.按费用科目明细分析;2.检查大额异常支出;3.核查咨询费/培训费真实性;4.验证费用分摊合理性;5.纳税调增处理",
     "description": "期间费用率远超行业均值时的费用合规审查"},

    # Tax incentive management
    {"id": "RS_INCENTIVE_HNTE", "name": "高新技术企业维护", "strategyType": "incentive_management",
     "targetRisk": "", "timeframe": "持续",
     "actionSteps": "1.监控研发费用占比(≥3/4/5%);2.科技人员占比(≥10%);3.高新收入占比(≥60%);4.知识产权更新;5.三年重新认定准备",
     "description": "15%优惠税率的维护管理，研发费用占比和人员占比是最常失败的指标"},
    {"id": "RS_INCENTIVE_SMALL", "name": "小微企业资格监控", "strategyType": "incentive_management",
     "targetRisk": "", "timeframe": "季度",
     "actionSteps": "1.监控年应纳税所得额(≤300万);2.从业人数(≤300人);3.资产总额(≤5000万);4.季度预缴时确认资格;5.临界值预警",
     "description": "小微企业实际税率5%，超过任一指标即失去资格"},
    {"id": "RS_INCENTIVE_RD_EXTRA", "name": "研发加计扣除最大化", "strategyType": "tax_optimization",
     "targetRisk": "", "timeframe": "年度",
     "actionSteps": "1.梳理所有研发项目;2.六类费用归集最大化;3.委托研发80%可加计;4.集团分摊合理化;5.季度预缴提前享受",
     "description": "100%加计扣除是最大的税收优惠，归集范围直接决定节税金额"},

    # Industry-specific
    {"id": "RS_IND_CONSTRUCTION", "name": "建筑业异地预缴合规", "strategyType": "industry_compliance",
     "targetRisk": "", "timeframe": "持续",
     "actionSteps": "1.项目台账建立;2.异地预缴增值税(2%/3%);3.企业所得税1/15预缴;4.跨区域涉税事项报告;5.分包差额计算",
     "description": "建筑业跨区域经营的增值税和所得税预缴是最复杂的行业规则"},
    {"id": "RS_IND_ECOMMERCE", "name": "电商平台税务合规", "strategyType": "industry_compliance",
     "targetRisk": "", "timeframe": "持续",
     "actionSteps": "1.平台佣金/推广费进项抵扣;2.刷单退货红字处理;3.促销折扣的发票开具;4.直播带货佣金个税;5.跨境电商综合税",
     "description": "电商特有的促销/退货/佣金等税务处理规则"},
    {"id": "RS_IND_REALESTATE", "name": "房地产土增税清算", "strategyType": "industry_compliance",
     "targetRisk": "", "timeframe": "项目结束",
     "actionSteps": "1.项目清算条件判断;2.土地成本分摊;3.开发成本归集;4.扣除项目加计20%;5.四级超率累进税率计算",
     "description": "土地增值税清算是房地产企业最大的税务风险环节"},

    # Digital economy & GT4 advanced
    {"id": "RS_GT4_BANK_MONITOR", "name": "银行流水异常监控", "strategyType": "data_monitoring",
     "targetRisk": "RI_BK_01", "timeframe": "持续",
     "actionSteps": "1.设置大额交易预警(≥5万个人/≥20万对公);2.监控公转私频率;3.检查账户余额与报表现金匹配;4.可疑交易自查;5.银行对账单归档",
     "description": "金税四期银税联网后银行流水监控的标准化方案"},
    {"id": "RS_GT4_SOCIAL_MATCH", "name": "社保公积金数据匹配", "strategyType": "hr_compliance",
     "targetRisk": "RI_BK_06", "timeframe": "年度",
     "actionSteps": "1.个税申报人数vs社保参保人数比对;2.检查应参未参人员;3.核实缴费基数与实际工资;4.灵活用工合规处理;5.劳务派遣合规确认",
     "description": "社保入税后个税与社保人数/基数必须一致的合规要求"},

    # International tax
    {"id": "RS_INTL_WITHHOLDING", "name": "非居民企业代扣代缴", "strategyType": "international_tax",
     "targetRisk": "", "timeframe": "每次付汇",
     "actionSteps": "1.判断付款是否构成来源于中国的所得;2.确认税收协定适用;3.计算代扣税额(10%或协定税率);4.税务备案;5.付汇前完税",
     "description": "向境外支付特许权使用费/股息/利息的代扣代缴义务"},
    {"id": "RS_INTL_TREATY_APPLY", "name": "税收协定待遇申请", "strategyType": "international_tax",
     "targetRisk": "", "timeframe": "按交易",
     "actionSteps": "1.确认受益所有人身份;2.收集税收居民身份证明;3.判断LOB条款适用;4.备案或审批;5.追溯适用(3年内可补)",
     "description": "通过税收协定降低股息/利息/特许权使用费预提税率"},

    # Proactive governance
    {"id": "RS_GOV_TAX_ARCHIVE", "name": "税务档案数字化", "strategyType": "data_governance",
     "targetRisk": "", "timeframe": "持续",
     "actionSteps": "1.申报表+完税证明电子归档;2.发票台账月度备份;3.合同/协议关联归档;4.税务检查资料专档;5.保存期限≥10年",
     "description": "完整的税务档案是应对稽查和争议的基础"},
]


# ═══════════════════════════════════════════════════════════════
# New PolicyChange (19 additional)
# Covers: 2022-2026 major tax policy updates
# ═══════════════════════════════════════════════════════════════
NEW_POLICY_CHANGES = [
    {"id": "PC_2022_RD_100", "name": "研发费用100%加计扣除", "changeType": "incentive_expansion",
     "effectiveDate": "2022-10-01", "impactScope": "all_enterprises",
     "impactedTaxTypes": "CIT",
     "previousPolicy": "75%加计扣除(制造业100%)", "newPolicy": "所有企业统一100%加计扣除",
     "transitionRule": "2022年10月1日起至2027年12月31日",
     "description": "研发费用加计扣除从75%提升到100%，覆盖所有企业，是最大的普惠性税收优惠"},
    {"id": "PC_2023_500W_EQUIP", "name": "设备器具一次性扣除延续", "changeType": "incentive_extension",
     "effectiveDate": "2023-01-01", "impactScope": "all_enterprises",
     "impactedTaxTypes": "CIT",
     "previousPolicy": "500万以下设备一次性扣除(到期)", "newPolicy": "延续至2027年12月31日",
     "transitionRule": "单位价值≤500万的设备器具可选择一次性税前扣除",
     "description": "固定资产加速折旧政策延续，对制造业和技术企业影响重大"},
    {"id": "PC_2023_INDIVIDUAL_PENSION", "name": "个人养老金税前扣除", "changeType": "new_deduction",
     "effectiveDate": "2023-01-01", "impactScope": "individual_taxpayers",
     "impactedTaxTypes": "PIT",
     "previousPolicy": "无个人养老金扣除", "newPolicy": "年度限额12000元税前扣除",
     "transitionRule": "缴存到个人养老金账户即可享受",
     "description": "个人养老金制度配套的税收优惠，实际递延纳税"},
    {"id": "PC_2024_SMALL_VAT_EXTEND", "name": "小规模纳税人减免增值税延续", "changeType": "incentive_extension",
     "effectiveDate": "2024-01-01", "impactScope": "small_taxpayers",
     "impactedTaxTypes": "VAT",
     "previousPolicy": "月销售额≤10万免征(到期)", "newPolicy": "延续至2027年12月31日",
     "transitionRule": "月销售额≤10万(季度≤30万)免征增值税",
     "description": "小规模纳税人增值税减免是个体户和小微企业的核心政策"},
    {"id": "PC_2024_STAMP_HALF_EXTEND", "name": "印花税减半延续", "changeType": "incentive_extension",
     "effectiveDate": "2024-01-01", "impactScope": "small_enterprises",
     "impactedTaxTypes": "STAMP",
     "previousPolicy": "小规模纳税人印花税减半(到期)", "newPolicy": "延续至2027年12月31日",
     "transitionRule": "增值税小规模纳税人适用50%减征",
     "description": "六税两费减半政策延续，含印花税/房产税/城镇土地使用税等"},
    {"id": "PC_2024_CIT_QUARTERLY_ENJOY", "name": "季度预缴可享受优惠", "changeType": "procedure_simplification",
     "effectiveDate": "2024-01-01", "impactScope": "all_enterprises",
     "impactedTaxTypes": "CIT",
     "previousPolicy": "部分优惠需年度汇算才能享受", "newPolicy": "小微企业/研发加计等可在季度预缴时享受",
     "transitionRule": "无需等待年度汇算",
     "description": "提前享受税收优惠，改善企业现金流"},
    {"id": "PC_2024_EZONE_HAINAN", "name": "海南自贸港企业所得税", "changeType": "regional_incentive",
     "effectiveDate": "2024-01-01", "impactScope": "hainan_enterprises",
     "impactedTaxTypes": "CIT",
     "previousPolicy": "鼓励类产业企业15%(试行)", "newPolicy": "15%税率正式确定+新增实质性运营要求",
     "transitionRule": "需满足实质性运营条件(人员/资产/收入)",
     "description": "海南自贸港15%企业所得税优惠从试行转为正式，强化反避税"},
    {"id": "PC_2025_DIGITAL_ECONOMY_TAX", "name": "数字经济税收指引", "changeType": "new_guidance",
     "effectiveDate": "2025-01-01", "impactScope": "digital_enterprises",
     "impactedTaxTypes": "CIT,VAT",
     "previousPolicy": "无专门指引", "newPolicy": "明确数据交易/算法授权/SaaS服务的增值税和所得税处理",
     "transitionRule": "按新指引执行，存量业务给予6个月过渡期",
     "description": "首次明确数字经济核心业务的税务处理规则"},
    {"id": "PC_2025_GLOBAL_MINIMUM_TAX", "name": "全球最低税率实施", "changeType": "international_reform",
     "effectiveDate": "2025-01-01", "impactScope": "mnc_enterprises",
     "impactedTaxTypes": "CIT",
     "previousPolicy": "无全球最低税", "newPolicy": "年收入≥7.5亿欧元的跨国集团适用15%全球最低税",
     "transitionRule": "OECD Pillar Two框架，中国IIR规则2025年起生效",
     "description": "OECD双支柱方案落地，影响在华跨国企业的整体税负"},
    {"id": "PC_2025_INVOICE_FULL_DIGITAL", "name": "全面数电票推广", "changeType": "digitalization",
     "effectiveDate": "2025-07-01", "impactScope": "all_taxpayers",
     "impactedTaxTypes": "VAT",
     "previousPolicy": "数电票试点(部分地区)", "newPolicy": "全国全面推行数电票，纸质发票逐步退出",
     "transitionRule": "新办纳税人默认数电票，存量企业2025年底前切换",
     "description": "发票全面数字化是金税四期的基础设施"},
    {"id": "PC_2025_EQUITY_TRANSFER", "name": "股权转让个税核定征收收紧", "changeType": "anti_avoidance",
     "effectiveDate": "2025-01-01", "impactScope": "individual_taxpayers",
     "impactedTaxTypes": "PIT",
     "previousPolicy": "核定征收可适用于股权转让", "newPolicy": "股权转让收入明显偏低需提供合理理由，否则按净资产核定",
     "transitionRule": "存量股权转让适用新规",
     "description": "堵住通过核定征收降低股权转让个税的避税通道"},
    {"id": "PC_2025_VAT_CREDIT_REFUND", "name": "增量留抵退税常态化", "changeType": "procedure_improvement",
     "effectiveDate": "2025-01-01", "impactScope": "all_taxpayers",
     "impactedTaxTypes": "VAT",
     "previousPolicy": "阶段性大规模留抵退税", "newPolicy": "增量留抵退税常态化，存量退税按行业分批",
     "transitionRule": "符合条件的纳税人按月申请增量退税",
     "description": "留抵退税从应急政策转为常态机制"},
    {"id": "PC_2026_ESG_TAX_INCENTIVE", "name": "绿色税收优惠扩围", "changeType": "incentive_expansion",
     "effectiveDate": "2026-01-01", "impactScope": "green_enterprises",
     "impactedTaxTypes": "CIT,VAT",
     "previousPolicy": "节能环保设备抵免/即征即退", "newPolicy": "碳减排投资额外加计扣除+新能源设备增值税即征即退扩围",
     "transitionRule": "需取得绿色认证",
     "description": "双碳目标下的税收激励扩围"},
    {"id": "PC_2026_SMART_AUDIT", "name": "金税四期智能稽查升级", "changeType": "enforcement_upgrade",
     "effectiveDate": "2026-01-01", "impactScope": "all_taxpayers",
     "impactedTaxTypes": "ALL",
     "previousPolicy": "金税四期初期(银税联网+发票比对)", "newPolicy": "AI辅助稽查+跨部门数据共享(市监/海关/外汇/社保)+行为分析",
     "transitionRule": "全国统一推行",
     "description": "金税四期从数据联网升级到AI驱动的智能稽查"},
    {"id": "PC_2024_INHERITANCE_TAX_DISCUSSION", "name": "遗产税立法讨论", "changeType": "legislation_signal",
     "effectiveDate": "2024-03-01", "impactScope": "high_net_worth",
     "impactedTaxTypes": "PIT",
     "previousPolicy": "无遗产税", "newPolicy": "全国人大财经委建议研究开征遗产税(非正式立法)",
     "transitionRule": "仅为立法信号，尚未进入正式立法程序",
     "description": "遗产税讨论虽非正式立法，但对高净值客户资产配置有重大影响"},
    {"id": "PC_2025_LAND_VALUE_REFORM", "name": "土地增值税立法", "changeType": "legislation",
     "effectiveDate": "2025-06-01", "impactScope": "real_estate",
     "impactedTaxTypes": "PROPERTY",
     "previousPolicy": "1993年暂行条例", "newPolicy": "土地增值税法(征求意见稿)",
     "transitionRule": "征求意见阶段，预计2026年正式实施",
     "description": "土地增值税从暂行条例升级为法律，税率结构可能调整"},
    {"id": "PC_2025_CROSS_BORDER_ECOMMERCE", "name": "跨境电商税收新规", "changeType": "new_regulation",
     "effectiveDate": "2025-04-01", "impactScope": "cross_border_ecommerce",
     "impactedTaxTypes": "VAT,CIT",
     "previousPolicy": "试行综合税率", "newPolicy": "跨境电商零售进口增值税/消费税免税限额提升+出口退税简化",
     "transitionRule": "单次交易限值5000元，年度限值26000元提升至36000元",
     "description": "跨境电商税收政策进一步放宽，促进进出口"},
    {"id": "PC_2023_CIT_CHARITABLE", "name": "公益性捐赠税前扣除扩围", "changeType": "incentive_expansion",
     "effectiveDate": "2023-01-01", "impactScope": "all_enterprises",
     "impactedTaxTypes": "CIT",
     "previousPolicy": "年度利润12%限额扣除", "newPolicy": "扶贫/乡村振兴捐赠可全额扣除+一般捐赠12%限额3年结转",
     "transitionRule": "需通过公益性社会组织或政府部门",
     "description": "公益捐赠税前扣除优惠扩围，鼓励企业社会责任"},
    {"id": "PC_2024_CONSUMPTION_EV", "name": "新能源汽车购置税延续", "changeType": "incentive_extension",
     "effectiveDate": "2024-01-01", "impactScope": "vehicle_buyers",
     "impactedTaxTypes": "CONSUMPTION",
     "previousPolicy": "新能源汽车免征购置税(到期)", "newPolicy": "2024-2025免征，2026-2027减半征收",
     "transitionRule": "免税限额3万元/辆",
     "description": "新能源汽车购置税分阶段退坡"},
]


# TaxType ID mapping for edges
TT_MAP = {
    "STAMP": "TT_STAMP", "CIT": "TT_CIT", "PIT": "TT_PIT", "VAT": "TT_VAT",
    "CONSUMPTION": "TT_CONSUMPTION", "PROPERTY": "TT_PROPERTY", "ALL": "TT_VAT",
}


def main():
    print("=== v4.2 Phase 5: ResponseStrategy & PolicyChange Expansion ===\n")

    # 1. ResponseStrategy
    print("--- ResponseStrategy (23 new) ---")
    create_stmts = []
    set_stmts = []
    for rs in NEW_STRATEGIES:
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

    # 2. PolicyChange
    print("\n--- PolicyChange (19 new) ---")
    create_stmts = []
    set_stmts = []
    for pc in NEW_POLICY_CHANGES:
        create_stmts.append(cn("PolicyChange", {
            "id": pc["id"], "name": pc["name"], "chineseName": pc["name"],
            "changeType": pc["changeType"], "impactScope": pc["impactScope"],
            "impactedTaxTypes": pc["impactedTaxTypes"],
            "previousPolicy": pc.get("previousPolicy", ""),
            "newPolicy": pc.get("newPolicy", ""),
            "transitionRule": pc.get("transitionRule", ""),
        }))
        ft = (
            f"【{pc['name']}】类型：{pc['changeType']}。{pc['description']}。"
            f"旧政策：{pc.get('previousPolicy', '')}。新政策：{pc.get('newPolicy', '')}"
        )
        safe_ft = ft.replace("'", "\\'")
        safe_desc = pc["description"].replace("'", "\\'")
        set_stmts.append(
            f"MATCH (n:PolicyChange) WHERE n.id = '{pc['id']}' "
            f"SET n.fullText = '{safe_ft}', n.description = '{safe_desc}'"
        )
    batch(create_stmts, "PolicyChange CREATE")
    batch(set_stmts, "PolicyChange SET")

    # 3. Edges
    print("\n--- Edges ---")
    edge_stmts = []

    # RESPONDS_TO: ResponseStrategy → RiskIndicator
    for rs in NEW_STRATEGIES:
        if rs.get("targetRisk"):
            edge_stmts.append(ce("RESPONDS_TO", "ResponseStrategy", rs["id"],
                                 "RiskIndicator", rs["targetRisk"],
                                 {"description": rs["name"]}))

    # TRIGGERED_BY_CHANGE: PolicyChange → TaxType
    for pc in NEW_POLICY_CHANGES:
        for tax in pc["impactedTaxTypes"].split(","):
            tax = tax.strip()
            tt_id = TT_MAP.get(tax)
            if tt_id:
                edge_stmts.append(ce("TRIGGERED_BY_CHANGE", "PolicyChange", pc["id"],
                                     "TaxType", tt_id,
                                     {"description": pc["name"], "impactLevel": pc["changeType"]}))

    batch(edge_stmts, "Edges")

    print(f"\n=== Summary ===")
    print(f"New ResponseStrategy: {len(NEW_STRATEGIES)} (total: 17 + {len(NEW_STRATEGIES)} = {17 + len(NEW_STRATEGIES)})")
    print(f"New PolicyChange: {len(NEW_POLICY_CHANGES)} (total: 11 + {len(NEW_POLICY_CHANGES)} = {11 + len(NEW_POLICY_CHANGES)})")
    print(f"New edges: {len(edge_stmts)}")


if __name__ == "__main__":
    main()
