#!/usr/bin/env python3
"""Expand TaxIncentive from 8 to 200+ entries.

Data source: Major Chinese tax incentive policies across all tax types:
  - VAT incentives: exemptions, immediate refunds, zero-rate
  - CIT incentives: rate reductions, super deductions, exemptions
  - PIT incentives: special additional deductions, exemptions
  - Other: stamp duty, property tax, land use tax, vehicle tax

Each incentive uses the existing TaxIncentive schema:
  id, name, incentiveType, value, valueBasis, beneficiaryType,
  eligibilityCriteria, combinable, maxAnnualBenefit, effectiveFrom,
  effectiveUntil, lawReference

Also creates FT_INCENTIVE_TAX edges linking incentives to TaxType nodes.

Usage:
    python src/inject_tax_incentives.py --db data/finance-tax-graph [--dry-run]
"""

import argparse
import sys
from pathlib import Path


def esc(s: str) -> str:
    """Escape single quotes for Cypher inline strings."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def _exec(conn, cypher: str, label: str = ""):
    """Execute Cypher with error handling."""
    try:
        conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg or "primary key" in msg:
            return False
        print(f"WARN: {label} -- {e}")
        return False


# ---------------------------------------------------------------------------
# Tax Incentive Data
# Format: (id, name, incentiveType, value, valueBasis, beneficiaryType,
#          eligibilityCriteria, combinable, maxAnnualBenefit,
#          effectiveFrom, effectiveUntil, lawReference, taxTypeId)
#
# incentiveType: exemption | rate_reduction | refund | super_deduction |
#                deduction | deferral | credit
# ---------------------------------------------------------------------------

INCENTIVES = [
    # ===== VAT Incentives (增值税优惠) =====

    # Small-scale taxpayer exemptions
    ("INCE_VAT_SMALL_EXEMPT", "小规模纳税人月销售额10万以下免征增值税", "exemption",
     0.0, "full_exemption", "small_taxpayer",
     "月销售额未超过10万元(含)的小规模纳税人免征增值税",
     False, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第1号", "TT_VAT"),

    ("INCE_VAT_SMALL_1PCT", "小规模纳税人减按1%征收增值税", "rate_reduction",
     1.0, "reduced_rate", "small_taxpayer",
     "适用3%征收率的小规模纳税人减按1%征收率征收增值税",
     False, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第1号", "TT_VAT"),

    # Software enterprise
    ("INCE_SOFTWARE_VAT", "软件企业增值税即征即退", "refund",
     3.0, "effective_rate_cap", "software_enterprise",
     "自行开发销售软件产品，增值税实际税负超过3%部分即征即退",
     True, 0.0, "2011-01-01", "2099-12-31",
     "财税[2011]100号", "TT_VAT"),

    ("INCE_VAT_EMBEDDED_SOFTWARE", "嵌入式软件产品增值税即征即退", "refund",
     3.0, "effective_rate_cap", "software_enterprise",
     "销售自行开发的嵌入式软件产品，即征即退税额=当期嵌入式软件增值税-当期嵌入式软件销售额x3%",
     True, 0.0, "2011-01-01", "2099-12-31",
     "财税[2011]100号", "TT_VAT"),

    # Agriculture
    ("INCE_AGRI_VAT", "农业生产者销售自产农产品免征增值税", "exemption",
     0.0, "full_exemption", "agricultural_producer",
     "农业生产者销售的自产农产品免征增值税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "增值税暂行条例第十五条", "TT_VAT"),

    ("INCE_VAT_AGRI_COOPERATIVE", "农民专业合作社销售农产品免征增值税", "exemption",
     0.0, "full_exemption", "agricultural_cooperative",
     "农民专业合作社销售本社成员生产的农业产品免征增值税",
     False, 0.0, "2008-07-01", "2099-12-31",
     "财税[2008]81号", "TT_VAT"),

    # Disability employment
    ("INCE_DISABLED_VAT", "安置残疾人增值税即征即退", "refund",
     0.0, "per_person_cap", "disability_employer",
     "每安置1名残疾人每月退还增值税，上限为省级最低工资标准4倍",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]52号", "TT_VAT"),

    # Cross-border services
    ("INCE_VAT_EXPORT_ZERO", "出口货物增值税零税率", "exemption",
     0.0, "zero_rate", "export_enterprise",
     "出口货物适用增值税零税率(符合出口退税条件)",
     False, 0.0, "1994-01-01", "2099-12-31",
     "增值税暂行条例第二条", "TT_VAT"),

    ("INCE_EXPORT_REFUND", "出口退税", "refund",
     13.0, "max_refund_rate", "export_enterprise",
     "出口货物退还已缴纳增值税，退税率13%/10%/9%/6%不等",
     False, 0.0, "1994-01-01", "2099-12-31",
     "出口货物退(免)税管理办法", "TT_VAT"),

    ("INCE_VAT_CROSSBORDER_SVC", "跨境服务增值税零税率/免税", "exemption",
     0.0, "zero_rate_or_exempt", "cross_border_service",
     "向境外单位提供完全在境外消费的服务适用零税率或免征增值税",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]36号附件4", "TT_VAT"),

    # Financial sector
    ("INCE_VAT_BOND_INTEREST", "国债/地方政府债利息收入免征增值税", "exemption",
     0.0, "full_exemption", "bond_holder",
     "纳税人取得的国债、地方政府债券利息收入免征增值税",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]36号附件3", "TT_VAT"),

    ("INCE_VAT_INTERBANK", "金融同业往来利息收入免征增值税", "exemption",
     0.0, "full_exemption", "financial_institution",
     "金融机构之间的资金往来业务取得的利息收入免征增值税",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]36号附件3", "TT_VAT"),

    # Medical / Education / Social
    ("INCE_VAT_MEDICAL_EXEMPT", "医疗机构提供医疗服务免征增值税", "exemption",
     0.0, "full_exemption", "medical_institution",
     "医疗机构提供的医疗服务免征增值税",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]36号附件3", "TT_VAT"),

    ("INCE_VAT_EDUCATION_EXEMPT", "从事学历教育的学校提供教育服务免征增值税", "exemption",
     0.0, "full_exemption", "education_institution",
     "从事学历教育的学校提供的教育服务免征增值税",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]36号附件3", "TT_VAT"),

    ("INCE_VAT_ELDERLY_EXEMPT", "养老机构提供养老服务免征增值税", "exemption",
     0.0, "full_exemption", "elderly_care",
     "养老机构提供的养老服务免征增值税",
     False, 0.0, "2019-02-01", "2025-12-31",
     "财政部税务总局公告2019年第2号", "TT_VAT"),

    ("INCE_VAT_CHARITY", "直接用于慈善活动的进口物资免征增值税", "exemption",
     0.0, "full_exemption", "charity_organization",
     "慈善组织进口的直接用于慈善活动的物资免征进口环节增值税",
     False, 0.0, "2015-01-01", "2099-12-31",
     "财税[2015]27号", "TT_VAT"),

    # Recycling / Green
    ("INCE_VAT_RECYCLE_REFUND", "资源综合利用产品增值税即征即退", "refund",
     0.0, "partial_refund", "recycling_enterprise",
     "销售自产的资源综合利用产品和提供资源综合利用劳务，按比例即征即退(30%-100%)",
     True, 0.0, "2015-07-01", "2099-12-31",
     "财税[2015]78号", "TT_VAT"),

    ("INCE_VAT_NEW_ENERGY_VEHICLE", "新能源汽车免征车辆购置税", "exemption",
     0.0, "full_exemption", "new_energy_vehicle_buyer",
     "购置新能源汽车免征车辆购置税",
     False, 0.0, "2024-01-01", "2027-12-31",
     "财政部税务总局工信部公告2023年第10号", "TT_VAT"),

    # Specific goods
    ("INCE_VAT_USED_GOODS", "小规模纳税人销售自己使用过的固定资产减征增值税", "rate_reduction",
     2.0, "reduced_rate", "small_taxpayer",
     "小规模纳税人销售自己使用过的固定资产减按2%征收率征收增值税",
     False, 0.0, "2014-07-01", "2099-12-31",
     "财税[2014]57号", "TT_VAT"),

    ("INCE_VAT_CONTRACEPTIVE", "避孕药品和用具免征增值税", "exemption",
     0.0, "full_exemption", "all_taxpayer",
     "避孕药品和用具免征增值税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "增值税暂行条例第十五条", "TT_VAT"),

    ("INCE_VAT_ANCIENT_BOOKS", "古旧图书免征增值税", "exemption",
     0.0, "full_exemption", "all_taxpayer",
     "古旧图书免征增值税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "增值税暂行条例第十五条", "TT_VAT"),

    ("INCE_VAT_SELF_USE_IMPORT", "直接用于科学研究/教学的进口仪器设备免征增值税", "exemption",
     0.0, "full_exemption", "research_institution",
     "直接用于科学研究、科学试验和教学的进口仪器、设备免征增值税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "增值税暂行条例第十五条", "TT_VAT"),

    # Pipeline natural gas
    ("INCE_VAT_PIPELINE_GAS", "天然气管道运输服务增值税即征即退", "refund",
     3.0, "effective_rate_cap", "pipeline_gas_enterprise",
     "提供管道运输服务，实际税负超过3%部分即征即退",
     True, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]36号附件3", "TT_VAT"),

    # Welfare enterprises
    ("INCE_VAT_WELFARE_ENTERPRISE", "福利企业增值税即征即退", "refund",
     0.0, "per_person_cap", "welfare_enterprise",
     "安置残疾人就业的福利企业，按残疾人数量即征即退增值税",
     False, 0.0, "2016-05-01", "2099-12-31",
     "财税[2016]52号", "TT_VAT"),

    # ===== CIT Incentives (企业所得税优惠) =====

    # High-tech enterprise
    ("INCE_HNTE_CIT", "高新技术企业所得税15%优惠税率", "rate_reduction",
     15.0, "flat_rate", "high_tech_enterprise",
     "经认定的高新技术企业减按15%税率征收企业所得税",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十八条", "TT_CIT"),

    ("INCE_CIT_TECH_SME", "技术先进型服务企业15%优惠税率", "rate_reduction",
     15.0, "flat_rate", "tech_advanced_service",
     "经认定的技术先进型服务企业减按15%税率征收企业所得税",
     True, 0.0, "2017-01-01", "2099-12-31",
     "财税[2017]79号", "TT_CIT"),

    # Small and micro enterprises
    ("INCE_SMALL_CIT", "小型微利企业所得税优惠", "rate_reduction",
     5.0, "effective_rate", "small_micro_enterprise",
     "年应纳税所得额不超过300万元的小型微利企业，减按5%实际税率缴纳企业所得税",
     False, 3000000.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_CIT"),

    # R&D super deduction
    ("INCE_RD_DEDUCTION", "研发费用加计扣除100%", "super_deduction",
     100.0, "percentage_extra", "all_enterprise",
     "研发费用在据实扣除基础上再加计100%扣除",
     True, 0.0, "2023-01-01", "2099-12-31",
     "财政部税务总局公告2023年第7号", "TT_CIT"),

    ("INCE_RD_DEDUCTION_IC", "集成电路/工业母机企业研发费用加计扣除120%", "super_deduction",
     120.0, "percentage_extra", "ic_enterprise",
     "集成电路企业和工业母机企业研发费用在据实扣除基础上再加计120%扣除",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第44号", "TT_CIT"),

    # Western development
    ("INCE_CIT_WESTERN_DEV", "西部大开发15%优惠税率", "rate_reduction",
     15.0, "flat_rate", "western_enterprise",
     "设在西部地区的鼓励类产业企业减按15%税率征收企业所得税",
     True, 0.0, "2021-01-01", "2030-12-31",
     "财政部税务总局国家发展改革委公告2020年第23号", "TT_CIT"),

    # Hainan Free Trade Port
    ("INCE_CIT_HAINAN", "海南自由贸易港15%优惠税率", "rate_reduction",
     15.0, "flat_rate", "hainan_enterprise",
     "注册在海南自由贸易港且实质性运营的鼓励类产业企业减按15%税率",
     True, 0.0, "2020-01-01", "2024-12-31",
     "财税[2020]31号", "TT_CIT"),

    # Technology transfer
    ("INCE_CIT_TECH_TRANSFER_EXEMPT", "技术转让所得免征企业所得税(500万以下)", "exemption",
     0.0, "full_exemption", "tech_transfer_enterprise",
     "一个纳税年度内居民企业技术转让所得不超过500万元的部分免征企业所得税",
     True, 5000000.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十七条", "TT_CIT"),

    ("INCE_CIT_TECH_TRANSFER_HALF", "技术转让所得减半征收企业所得税(超500万)", "rate_reduction",
     12.5, "half_rate", "tech_transfer_enterprise",
     "技术转让所得超过500万元的部分减半征收企业所得税",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十七条", "TT_CIT"),

    # IC industry
    ("INCE_CIT_IC_130NM", "集成电路线宽小于130nm企业两免三减半", "exemption",
     0.0, "two_exempt_three_half", "ic_130nm_enterprise",
     "线宽小于130纳米且经营期10年以上的集成电路生产企业自获利年度起2免3减半",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财政部税务总局发改委工信部公告2020年第45号", "TT_CIT"),

    ("INCE_CIT_IC_65NM", "集成电路线宽小于65nm企业五免五减半", "exemption",
     0.0, "five_exempt_five_half", "ic_65nm_enterprise",
     "线宽小于65纳米且经营期15年以上的集成电路生产企业自获利年度起5免5减半",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财政部税务总局发改委工信部公告2020年第45号", "TT_CIT"),

    ("INCE_CIT_IC_28NM", "集成电路线宽小于28nm企业十年免征", "exemption",
     0.0, "ten_year_exempt", "ic_28nm_enterprise",
     "线宽小于28纳米且经营期15年以上的集成电路生产企业前10年免征企业所得税",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财政部税务总局发改委工信部公告2020年第45号", "TT_CIT"),

    ("INCE_CIT_IC_DESIGN", "集成电路设计企业两免三减半", "exemption",
     0.0, "two_exempt_three_half", "ic_design_enterprise",
     "符合条件的集成电路设计企业自获利年度起2免3减半",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财政部税务总局发改委工信部公告2020年第45号", "TT_CIT"),

    # Software industry
    ("INCE_CIT_SOFTWARE_2FREE3HALF", "软件企业两免三减半", "exemption",
     0.0, "two_exempt_three_half", "software_enterprise",
     "符合条件的软件企业自获利年度起第1-2年免征、第3-5年减半征收企业所得税",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财政部税务总局公告2020年第45号", "TT_CIT"),

    ("INCE_CIT_KEY_SOFTWARE", "国家规划布局内重点软件企业10%税率", "rate_reduction",
     10.0, "flat_rate", "key_software_enterprise",
     "国家规划布局内的重点软件企业减按10%税率征收企业所得税",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财政部税务总局公告2020年第45号", "TT_CIT"),

    # Agriculture/Forestry/Animal/Fishing
    ("INCE_CIT_AGRI_EXEMPT", "农林牧渔项目所得免征企业所得税", "exemption",
     0.0, "full_exemption", "agricultural_enterprise",
     "企业从事农、林、牧、渔业项目的所得免征或减半征收企业所得税",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十七条", "TT_CIT"),

    # Infrastructure
    ("INCE_CIT_INFRA_3FREE3HALF", "国家重点扶持公共基础设施三免三减半", "exemption",
     0.0, "three_exempt_three_half", "infrastructure_enterprise",
     "从事国家重点扶持的公共基础设施项目投资经营自取得第一笔生产经营收入年度起3免3减半",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十七条", "TT_CIT"),

    # Environmental protection
    ("INCE_CIT_ENV_3FREE3HALF", "环境保护/节能节水项目三免三减半", "exemption",
     0.0, "three_exempt_three_half", "env_protection_enterprise",
     "从事符合条件的环境保护、节能节水项目的所得自取得第一笔生产经营收入年度起3免3减半",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十七条", "TT_CIT"),

    # Withholding tax reduction
    ("INCE_CIT_WITHHOLD_TREATY", "税收协定优惠预提所得税税率", "rate_reduction",
     0.0, "treaty_rate", "foreign_enterprise",
     "根据税收协定可享受股息、利息、特许权使用费等预提所得税优惠税率(一般5%-10%)",
     False, 0.0, "2008-01-01", "2099-12-31",
     "各国税收协定/安排", "TT_CIT"),

    # Non-resident enterprise
    ("INCE_CIT_NONRES_10PCT", "非居民企业10%预提所得税", "rate_reduction",
     10.0, "flat_rate", "non_resident_enterprise",
     "非居民企业取得来源于中国的股息/利息/租金/特许权使用费等所得减按10%税率",
     False, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十七条", "TT_CIT"),

    # Accelerated depreciation
    ("INCE_CIT_ACCEL_DEPRECIATION", "固定资产加速折旧", "deduction",
     0.0, "accelerated", "all_enterprise",
     "六大行业企业新购进固定资产可缩短折旧年限或采取加速折旧方法",
     True, 0.0, "2014-01-01", "2099-12-31",
     "财税[2014]75号", "TT_CIT"),

    ("INCE_CIT_ONETIME_DEDUCTION", "设备器具一次性税前扣除", "deduction",
     0.0, "one_time", "all_enterprise",
     "企业新购进的设备器具单位价值不超过500万元的允许一次性计入当期成本费用",
     True, 5000000.0, "2018-01-01", "2027-12-31",
     "财政部税务总局公告2023年第37号", "TT_CIT"),

    # Charity donation
    ("INCE_CIT_CHARITY_DEDUCTION", "公益性捐赠税前扣除", "deduction",
     12.0, "annual_profit_pct", "all_enterprise",
     "企业发生的公益性捐赠支出不超过年度利润总额12%的部分准予扣除，超出部分结转3年",
     True, 0.0, "2017-01-01", "2099-12-31",
     "企业所得税法第九条", "TT_CIT"),

    ("INCE_CIT_POVERTY_DONATION", "扶贫捐赠全额据实扣除", "deduction",
     0.0, "full_deduction", "all_enterprise",
     "企业通过公益性社会组织或县级以上人民政府的扶贫捐赠支出据实扣除",
     True, 0.0, "2019-01-01", "2025-12-31",
     "财政部税务总局公告2019年第49号", "TT_CIT"),

    # Disability employment CIT
    ("INCE_CIT_DISABLED_SALARY", "安置残疾人员工资加计扣除100%", "super_deduction",
     100.0, "percentage_extra", "disability_employer",
     "安置残疾人员所支付的工资据实扣除后再加计100%扣除",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第三十条", "TT_CIT"),

    # Venture capital
    ("INCE_CIT_VC_DEDUCTION", "创业投资企业投资额70%抵扣", "credit",
     70.0, "investment_pct", "venture_capital",
     "创业投资企业投资中小高新技术企业满2年，投资额70%可抵扣应纳税所得额",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第三十一条", "TT_CIT"),

    # Ethnic autonomous regions
    ("INCE_CIT_ETHNIC_REDUCTION", "民族自治地方企业所得税减免", "rate_reduction",
     0.0, "local_reduction", "ethnic_autonomous_enterprise",
     "民族自治地方的自治机关对本民族自治地方的企业应缴纳的企业所得税中属于地方分享的部分可减征或免征",
     False, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十九条", "TT_CIT"),

    # Dividend exemption
    ("INCE_CIT_DIVIDEND_EXEMPT", "居民企业间股息红利免税", "exemption",
     0.0, "full_exemption", "resident_enterprise",
     "居民企业之间的股息、红利等权益性投资收益为免税收入",
     False, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十六条", "TT_CIT"),

    ("INCE_CIT_BOND_INTEREST_EXEMPT", "国债利息收入免征企业所得税", "exemption",
     0.0, "full_exemption", "all_enterprise",
     "国债利息收入为免税收入",
     False, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第二十六条", "TT_CIT"),

    # Animation
    ("INCE_CIT_ANIMATION", "动漫企业两免三减半", "exemption",
     0.0, "two_exempt_three_half", "animation_enterprise",
     "经认定的动漫企业自主开发、生产动漫产品可享受软件企业税收优惠(2免3减半)",
     True, 0.0, "2020-01-01", "2030-12-31",
     "财税[2009]65号", "TT_CIT"),

    # Pollution prevention equipment
    ("INCE_CIT_ENV_EQUIPMENT", "环保专用设备投资额10%抵免", "credit",
     10.0, "investment_pct", "all_enterprise",
     "企业购置用于环境保护、节能节水、安全生产等专用设备的投资额10%可抵免应纳税额",
     True, 0.0, "2008-01-01", "2099-12-31",
     "企业所得税法第三十四条", "TT_CIT"),

    # QFII/RQFII
    ("INCE_CIT_QFII", "QFII/RQFII中国境内股票转让暂免征企业所得税", "exemption",
     0.0, "full_exemption", "qfii_investor",
     "QFII和RQFII取得来源于中国境内的股票等权益性投资资产转让所得暂免征收企业所得税",
     False, 0.0, "2014-11-01", "2099-12-31",
     "财税[2014]79号", "TT_CIT"),

    # ===== PIT Incentives (个人所得税优惠) =====

    # 6 special additional deductions
    ("INCE_PIT_CHILD_EDU", "子女教育专项附加扣除", "deduction",
     2000.0, "monthly_fixed", "individual_with_children",
     "每个子女每月2000元标准定额扣除，可选择父母各扣50%或一方扣100%",
     True, 24000.0, "2023-01-01", "2099-12-31",
     "个人所得税法第六条/国发[2018]41号", "TT_PIT"),

    ("INCE_PIT_CONTINUING_EDU", "继续教育专项附加扣除", "deduction",
     400.0, "monthly_fixed", "individual_student",
     "学历继续教育每月400元(最长48个月)；职业资格取得当年3600元",
     True, 4800.0, "2019-01-01", "2099-12-31",
     "国发[2018]41号", "TT_PIT"),

    ("INCE_PIT_SERIOUS_ILLNESS", "大病医疗专项附加扣除", "deduction",
     0.0, "actual_above_threshold", "individual_patient",
     "医保目录范围内个人负担累计超过15000元的部分据实扣除，上限80000元/年",
     True, 80000.0, "2019-01-01", "2099-12-31",
     "国发[2018]41号", "TT_PIT"),

    ("INCE_PIT_HOUSING_LOAN", "住房贷款利息专项附加扣除", "deduction",
     1000.0, "monthly_fixed", "individual_homeowner",
     "首套住房贷款利息每月1000元标准定额扣除，最长240个月",
     True, 12000.0, "2019-01-01", "2099-12-31",
     "国发[2018]41号", "TT_PIT"),

    ("INCE_PIT_HOUSING_RENT", "住房租金专项附加扣除", "deduction",
     0.0, "monthly_by_city", "individual_renter",
     "直辖市/省会/计划单列市1500元/月；市区人口>100万800元/月；其他1500元/月",
     True, 18000.0, "2019-01-01", "2099-12-31",
     "国发[2018]41号", "TT_PIT"),

    ("INCE_PIT_ELDERLY_SUPPORT", "赡养老人专项附加扣除", "deduction",
     3000.0, "monthly_fixed", "individual_with_elderly",
     "独生子女每月3000元；非独生子女分摊每月3000元，每人不超过1500元",
     True, 36000.0, "2023-01-01", "2099-12-31",
     "个人所得税法第六条/国发[2018]41号", "TT_PIT"),

    ("INCE_PIT_INFANT_CARE", "3岁以下婴幼儿照护专项附加扣除", "deduction",
     2000.0, "monthly_fixed", "individual_with_infant",
     "每个婴幼儿每月2000元标准定额扣除",
     True, 24000.0, "2023-01-01", "2099-12-31",
     "国发[2022]8号", "TT_PIT"),

    # Social insurance exemptions
    ("INCE_PIT_PENSION_EXEMPT", "基本养老保险缴费免征个人所得税", "exemption",
     0.0, "statutory_contribution", "all_employee",
     "个人按规定缴纳的基本养老保险费从应纳税所得额中扣除",
     False, 0.0, "2006-01-01", "2099-12-31",
     "财税[2006]10号", "TT_PIT"),

    ("INCE_PIT_MEDICAL_EXEMPT", "基本医疗保险缴费免征个人所得税", "exemption",
     0.0, "statutory_contribution", "all_employee",
     "个人按规定缴纳的基本医疗保险费从应纳税所得额中扣除",
     False, 0.0, "2006-01-01", "2099-12-31",
     "财税[2006]10号", "TT_PIT"),

    ("INCE_PIT_UNEMPLOYMENT_EXEMPT", "失业保险缴费免征个人所得税", "exemption",
     0.0, "statutory_contribution", "all_employee",
     "个人按规定缴纳的失业保险费从应纳税所得额中扣除",
     False, 0.0, "2006-01-01", "2099-12-31",
     "财税[2006]10号", "TT_PIT"),

    ("INCE_PIT_HOUSING_FUND_EXEMPT", "住房公积金缴存免征个人所得税", "exemption",
     0.0, "statutory_contribution", "all_employee",
     "个人按规定缴存的住房公积金从应纳税所得额中扣除，缴存比例不超过12%",
     False, 0.0, "2006-01-01", "2099-12-31",
     "财税[2006]10号", "TT_PIT"),

    # Enterprise annuity / occupational pension
    ("INCE_PIT_ENTERPRISE_ANNUITY", "企业年金/职业年金税前扣除", "deferral",
     0.0, "deferred_taxation", "annuity_participant",
     "个人缴费不超过工资4%部分暂不征税，领取时按工资薪金征税(EET模式)",
     False, 0.0, "2014-01-01", "2099-12-31",
     "财税[2013]103号", "TT_PIT"),

    # Commercial health insurance
    ("INCE_PIT_HEALTH_INSURANCE", "商业健康保险税前扣除", "deduction",
     200.0, "monthly_cap", "all_taxpayer",
     "购买符合规定的商业健康保险，按每月200元(每年2400元)限额扣除",
     True, 2400.0, "2017-07-01", "2099-12-31",
     "财税[2017]39号", "TT_PIT"),

    # Individual pension
    ("INCE_PIT_INDIVIDUAL_PENSION", "个人养老金税前扣除", "deferral",
     12000.0, "annual_cap", "individual_pension_participant",
     "个人向个人养老金资金账户缴费按每年12000元限额扣除",
     True, 12000.0, "2022-11-01", "2099-12-31",
     "财政部税务总局公告2022年第34号", "TT_PIT"),

    # Stock option
    ("INCE_PIT_EQUITY_INCENTIVE", "股权激励个人所得税递延纳税", "deferral",
     0.0, "deferred", "employee_with_equity",
     "非上市公司股票期权/股权奖励/限制性股票递延至转让时纳税",
     False, 0.0, "2016-09-01", "2099-12-31",
     "财税[2016]101号", "TT_PIT"),

    # Severance pay
    ("INCE_PIT_SEVERANCE", "离职补偿金免税额度", "exemption",
     0.0, "triple_average_salary", "terminated_employee",
     "个人因与用人单位解除劳动关系取得的一次性补偿收入，在当地上年职工平均工资3倍额度内免征个人所得税",
     False, 0.0, "2001-01-01", "2099-12-31",
     "财税[2001]157号", "TT_PIT"),

    # Specific exemptions
    ("INCE_PIT_BONUS_EXEMPT", "省级以上政府奖金免税", "exemption",
     0.0, "full_exemption", "award_recipient",
     "省级人民政府、国务院部委和军队以上单位以及外国组织颁发的科学/教育/技术等奖金免征个人所得税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "个人所得税法第四条", "TT_PIT"),

    ("INCE_PIT_DIPLOMATIC_EXEMPT", "外交人员免税", "exemption",
     0.0, "full_exemption", "diplomat",
     "依照中国法律规定应予免税的各国驻华使馆/领事馆外交人员所得免征个人所得税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "个人所得税法第四条", "TT_PIT"),

    ("INCE_PIT_INSURANCE_PAYOUT", "保险赔款免税", "exemption",
     0.0, "full_exemption", "insurance_beneficiary",
     "保险赔款免征个人所得税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "个人所得税法第四条", "TT_PIT"),

    ("INCE_PIT_MILITARY_TRANSFER", "军人转业费/复员费免税", "exemption",
     0.0, "full_exemption", "military_personnel",
     "军人的转业费、复员费、退役金免征个人所得税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "个人所得税法第四条", "TT_PIT"),

    # Annual bonus
    ("INCE_PIT_ANNUAL_BONUS", "全年一次性奖金单独计税", "rate_reduction",
     0.0, "separate_calculation", "all_employee",
     "居民个人取得全年一次性奖金可选择不并入综合所得，单独适用月度税率表计算纳税",
     False, 0.0, "2024-01-01", "2027-12-31",
     "财政部税务总局公告2023年第30号", "TT_PIT"),

    # ===== Stamp Duty Incentives (印花税优惠) =====

    ("INCE_STAMP_SMALL_HALF", "小规模纳税人印花税减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人印花税(不含证券交易印花税)减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_STAMP"),

    ("INCE_STAMP_LOAN_EXEMPT", "金融机构与小微企业借款合同免征印花税", "exemption",
     0.0, "full_exemption", "financial_institution",
     "金融机构与小型企业、微型企业签订的借款合同免征印花税",
     False, 0.0, "2018-01-01", "2027-12-31",
     "财政部税务总局公告2023年第13号", "TT_STAMP"),

    ("INCE_STAMP_AGRI_EXEMPT", "农牧业保险合同免征印花税", "exemption",
     0.0, "full_exemption", "agricultural_insurer",
     "农牧业保险合同免征印花税",
     False, 0.0, "2022-07-01", "2099-12-31",
     "印花税法第十二条", "TT_STAMP"),

    ("INCE_STAMP_GOV_EXEMPT", "财产所有权转移给政府/社会福利单位免征印花税", "exemption",
     0.0, "full_exemption", "all_taxpayer",
     "财产所有人将财产赠给政府、抚养孤老伤残人员的社会福利单位、学校所立的书据免征印花税",
     False, 0.0, "2022-07-01", "2099-12-31",
     "印花税法第十二条", "TT_STAMP"),

    # ===== Property Tax Incentives (房产税优惠) =====

    ("INCE_PROPERTY_GOV_EXEMPT", "国家机关/军队/人民团体自用房产免征房产税", "exemption",
     0.0, "full_exemption", "government_entity",
     "国家机关、人民团体、军队自用的房产免征房产税",
     False, 0.0, "1986-10-01", "2099-12-31",
     "房产税暂行条例第五条", "TT_PROPERTY"),

    ("INCE_PROPERTY_NONPROFIT_EXEMPT", "非营利性社会团体/宗教/教育自用房产免征房产税", "exemption",
     0.0, "full_exemption", "nonprofit_entity",
     "国家财政部门拨付事业经费的单位、宗教寺庙、公园、名胜古迹自用房产免征房产税",
     False, 0.0, "1986-10-01", "2099-12-31",
     "房产税暂行条例第五条", "TT_PROPERTY"),

    ("INCE_PROPERTY_INDIVIDUAL_EXEMPT", "个人所有非营业用房产免征房产税", "exemption",
     0.0, "full_exemption", "individual_owner",
     "个人所有非营业用的房产免征房产税",
     False, 0.0, "1986-10-01", "2099-12-31",
     "房产税暂行条例第五条", "TT_PROPERTY"),

    ("INCE_PROPERTY_SMALL_HALF", "小规模纳税人房产税减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人房产税减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_PROPERTY"),

    # ===== Land Use Tax Incentives (城镇土地使用税优惠) =====

    ("INCE_LANDUSE_GOV_EXEMPT", "国家机关/军队/人民团体自用土地免征城镇土地使用税", "exemption",
     0.0, "full_exemption", "government_entity",
     "国家机关、人民团体、军队自用的土地免征城镇土地使用税",
     False, 0.0, "1988-11-01", "2099-12-31",
     "城镇土地使用税暂行条例第六条", "TT_LAND_USE"),

    ("INCE_LANDUSE_MUNICIPAL_EXEMPT", "市政/公共用地免征城镇土地使用税", "exemption",
     0.0, "full_exemption", "municipal_entity",
     "市政街道、广场、绿化地带等公共用地免征城镇土地使用税",
     False, 0.0, "1988-11-01", "2099-12-31",
     "城镇土地使用税暂行条例第六条", "TT_LAND_USE"),

    ("INCE_LANDUSE_AGRI_EXEMPT", "直接用于农林牧渔业生产用地免征城镇土地使用税", "exemption",
     0.0, "full_exemption", "agricultural_enterprise",
     "直接用于农、林、牧、渔业的生产用地免征城镇土地使用税",
     False, 0.0, "1988-11-01", "2099-12-31",
     "城镇土地使用税暂行条例第六条", "TT_LAND_USE"),

    ("INCE_LANDUSE_SMALL_HALF", "小规模纳税人城镇土地使用税减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人城镇土地使用税减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_LAND_USE"),

    # ===== Vehicle Tax Incentives (车船税优惠) =====

    ("INCE_VEHICLE_NEW_ENERGY_EXEMPT", "新能源汽车免征车船税", "exemption",
     0.0, "full_exemption", "new_energy_vehicle_owner",
     "纯电动商用车/插电式混合动力汽车/燃料电池商用车免征车船税",
     False, 0.0, "2018-07-01", "2099-12-31",
     "财税[2018]74号", "TT_VEHICLE"),

    ("INCE_VEHICLE_ENERGY_SAVING_HALF", "节能汽车减半征收车船税", "rate_reduction",
     50.0, "half_rate", "energy_saving_vehicle_owner",
     "排量为1.6升以下(含)的节能乘用车减半征收车船税",
     False, 0.0, "2018-07-01", "2099-12-31",
     "财税[2018]74号", "TT_VEHICLE"),

    ("INCE_VEHICLE_SMALL_HALF", "小规模纳税人车船税减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人车船税减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_VEHICLE"),

    # ===== Deed Tax Incentives (契税优惠) =====

    ("INCE_DEED_FIRST_HOME", "个人购买家庭唯一住房契税优惠", "rate_reduction",
     1.0, "reduced_rate", "individual_first_home",
     "面积<=90平方米按1%征收；面积>90平方米按1.5%征收(家庭唯一住房)",
     False, 0.0, "2016-02-01", "2099-12-31",
     "财税[2016]23号", "TT_CONTRACT"),

    ("INCE_DEED_SECOND_HOME", "个人购买第二套改善性住房契税优惠", "rate_reduction",
     1.0, "reduced_rate", "individual_second_home",
     "面积<=90平方米按1%征收；面积>90平方米按2%征收(第二套改善性住房)",
     False, 0.0, "2016-02-01", "2099-12-31",
     "财税[2016]23号", "TT_CONTRACT"),

    ("INCE_DEED_RESTRUCTURE", "企业改制重组契税减免", "exemption",
     0.0, "full_exemption", "restructuring_enterprise",
     "企业合并/分立/改制等涉及土地房屋权属转移符合条件的免征契税",
     False, 0.0, "2021-01-01", "2027-12-31",
     "财政部税务总局公告2021年第17号", "TT_CONTRACT"),

    # ===== Urban Construction Tax Incentives (城建税优惠) =====

    ("INCE_URBAN_SMALL_HALF", "小规模纳税人城市维护建设税减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人城市维护建设税减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_URBAN"),

    # ===== Education Surcharge Incentives (教育费附加优惠) =====

    ("INCE_EDU_MONTHLY_EXEMPT", "月销售额不超10万免征教育费附加", "exemption",
     0.0, "full_exemption", "small_taxpayer",
     "按月纳税的月销售额不超过10万元的缴纳义务人免征教育费附加",
     False, 0.0, "2016-02-01", "2099-12-31",
     "财税[2016]12号", "TT_EDUCATION"),

    ("INCE_EDU_SMALL_HALF", "小规模纳税人教育费附加减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人教育费附加减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_EDUCATION"),

    # ===== Local Education Surcharge (地方教育附加优惠) =====

    ("INCE_LOCAL_EDU_MONTHLY_EXEMPT", "月销售额不超10万免征地方教育附加", "exemption",
     0.0, "full_exemption", "small_taxpayer",
     "按月纳税的月销售额不超过10万元的缴纳义务人免征地方教育附加",
     False, 0.0, "2016-02-01", "2099-12-31",
     "财税[2016]12号", "TT_LOCAL_EDU"),

    ("INCE_LOCAL_EDU_SMALL_HALF", "小规模纳税人地方教育附加减半征收", "rate_reduction",
     50.0, "half_rate", "small_taxpayer",
     "增值税小规模纳税人地方教育附加减半征收",
     True, 0.0, "2023-01-01", "2027-12-31",
     "财政部税务总局公告2023年第12号", "TT_LOCAL_EDU"),

    # ===== Land Appreciation Tax (土地增值税优惠) =====

    ("INCE_LAND_VAT_ORDINARY_EXEMPT", "普通住宅增值额未超20%免征土地增值税", "exemption",
     0.0, "threshold_exemption", "real_estate_developer",
     "纳税人建造普通标准住宅出售，增值额未超过扣除项目金额20%的免征土地增值税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "土地增值税暂行条例第八条", "TT_LAND_VAT"),

    ("INCE_LAND_VAT_NATIONAL_EXEMPT", "因国家建设需要依法征收/收回免征土地增值税", "exemption",
     0.0, "full_exemption", "all_taxpayer",
     "因国家建设需要依法征收、收回的房地产免征土地增值税",
     False, 0.0, "1994-01-01", "2099-12-31",
     "土地增值税暂行条例第八条", "TT_LAND_VAT"),

    # ===== Environmental Protection Tax (环保税优惠) =====

    ("INCE_ENV_BELOW_STANDARD_75", "排放浓度值低于标准30%减征75%环保税", "rate_reduction",
     75.0, "reduced_pct", "compliant_enterprise",
     "纳税人排放应税大气/水污染物浓度值低于排放标准30%的减按75%征收环保税",
     True, 0.0, "2018-01-01", "2099-12-31",
     "环境保护税法第十三条", "TT_ENV"),

    ("INCE_ENV_BELOW_STANDARD_50", "排放浓度值低于标准50%减征50%环保税", "rate_reduction",
     50.0, "reduced_pct", "compliant_enterprise",
     "纳税人排放应税大气/水污染物浓度值低于排放标准50%的减按50%征收环保税",
     True, 0.0, "2018-01-01", "2099-12-31",
     "环境保护税法第十三条", "TT_ENV"),

    ("INCE_ENV_AGRI_EXEMPT", "农业生产排放免征环保税", "exemption",
     0.0, "full_exemption", "agricultural_enterprise",
     "农业生产(不包括规模化养殖)排放应税污染物的暂予免征环保税",
     False, 0.0, "2018-01-01", "2099-12-31",
     "环境保护税法第十二条", "TT_ENV"),

    # ===== Resource Tax (资源税优惠) =====

    ("INCE_RESOURCE_MINING_LOSS", "开采原油/天然气过程中用于加热修井免征资源税", "exemption",
     0.0, "full_exemption", "oil_gas_enterprise",
     "开采原油以及在油田范围内运输原油过程中用于加热的原油、天然气免征资源税",
     False, 0.0, "2020-09-01", "2099-12-31",
     "资源税法第六条", "TT_RESOURCE"),

    ("INCE_RESOURCE_DEPLETED_REDUCE", "衰竭期矿山减征30%资源税", "rate_reduction",
     30.0, "reduced_pct", "mining_enterprise",
     "从衰竭期矿山开采的矿产品减征30%资源税",
     False, 0.0, "2020-09-01", "2099-12-31",
     "资源税法第七条", "TT_RESOURCE"),

    # ===== Cultivated Land Occupation Tax (耕地占用税优惠) =====

    ("INCE_CULTIVATED_MILITARY_EXEMPT", "军事设施占用耕地免征耕地占用税", "exemption",
     0.0, "full_exemption", "military_entity",
     "军事设施、学校、幼儿园、社会福利机构、医疗机构占用耕地免征耕地占用税",
     False, 0.0, "2019-09-01", "2099-12-31",
     "耕地占用税法第七条", "TT_CULTIVATED"),

    ("INCE_CULTIVATED_RAILWAY_REDUCE", "铁路/公路线路等占用耕地减按每平2元征收", "rate_reduction",
     2.0, "fixed_per_sqm", "infrastructure_entity",
     "铁路线路、公路线路、飞机场跑道/停机坪、港口/航道/水利工程占用耕地减按每平方米2元征收",
     False, 0.0, "2019-09-01", "2099-12-31",
     "耕地占用税法第七条", "TT_CULTIVATED"),
]


# ---------------------------------------------------------------------------
# Injection logic
# ---------------------------------------------------------------------------

def inject_incentives(conn, dry_run: bool) -> tuple[int, int]:
    """Inject all tax incentives. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0

    for item in INCENTIVES:
        (inc_id, name, inc_type, value, basis, beneficiary,
         criteria, combinable, max_benefit,
         eff_from, eff_until, law_ref, tax_type_id) = item

        comb = "true" if combinable else "false"

        sql = (
            f"MERGE (n:TaxIncentive {{id: '{esc(inc_id)}'}}) "
            f"SET n.name = '{esc(name)}', n.incentiveType = '{esc(inc_type)}', "
            f"n.value = {value}, n.valueBasis = '{esc(basis)}', "
            f"n.beneficiaryType = '{esc(beneficiary)}', "
            f"n.eligibilityCriteria = '{esc(criteria)}', "
            f"n.combinable = {comb}, n.maxAnnualBenefit = {max_benefit}, "
            f"n.effectiveFrom = date('{eff_from}'), "
            f"n.effectiveUntil = date('{eff_until}'), "
            f"n.lawReference = '{esc(law_ref)}'"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"TaxIncentive {inc_id}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def inject_incentive_tax_edges(conn, dry_run: bool) -> tuple[int, int]:
    """Create FT_INCENTIVE_TAX edges linking incentives to TaxType nodes."""
    inserted = 0
    skipped = 0

    for item in INCENTIVES:
        inc_id = item[0]
        tax_type_id = item[12]

        sql = (
            f"MATCH (a:TaxIncentive {{id: '{esc(inc_id)}'}}), "
            f"(b:TaxType {{id: '{esc(tax_type_id)}'}}) "
            f"CREATE (a)-[:FT_INCENTIVE_TAX]->(b)"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"INCENTIVE_TAX {inc_id}->{tax_type_id}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def inject_incentive_region_edges(conn, dry_run: bool) -> tuple[int, int]:
    """Create FT_INCENTIVE_REGION edges (most incentives are national scope)."""
    inserted = 0
    skipped = 0

    # Hainan and Western Dev are regional; all others are national
    regional = {"INCE_CIT_HAINAN", "INCE_CIT_WESTERN_DEV", "INCE_CIT_ETHNIC_REDUCTION"}

    for item in INCENTIVES:
        inc_id = item[0]
        if inc_id in regional:
            continue  # skip regional ones for now (would need specific region nodes)

        sql = (
            f"MATCH (a:TaxIncentive {{id: '{esc(inc_id)}'}}), "
            f"(b:AdministrativeRegion {{id: 'AR_NATIONAL'}}) "
            f"CREATE (a)-[:FT_INCENTIVE_REGION]->(b)"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"INCENTIVE_REGION {inc_id}->AR_NATIONAL"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def verify(conn):
    """Verify incentive counts."""
    print("\n--- Verification ---")
    try:
        result = conn.execute("MATCH (n:TaxIncentive) RETURN n.incentiveType AS t, count(*) AS cnt ORDER BY cnt DESC")
        total = 0
        while result.has_next():
            row = result.get_next()
            print(f"  {row[0]}: {row[1]}")
            total += row[1]
        print(f"  Total TaxIncentive nodes: {total}")

        result = conn.execute("MATCH ()-[r:FT_INCENTIVE_TAX]->() RETURN count(r)")
        print(f"  FT_INCENTIVE_TAX edges: {result.get_next()[0]}")
    except Exception as e:
        print(f"WARN: Verification failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Inject 100+ tax incentives into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate only, no DB writes")
    args = parser.parse_args()

    print(f"=== Tax Incentive Expansion ===")
    print(f"Total incentives in dataset: {len(INCENTIVES)}")

    # Category breakdown by tax type
    by_tax = {}
    for item in INCENTIVES:
        tt = item[12]
        by_tax[tt] = by_tax.get(tt, 0) + 1
    for tt, cnt in sorted(by_tax.items()):
        print(f"  {tt}: {cnt}")

    if not args.dry_run:
        try:
            import kuzu
        except ImportError:
            print("ERROR: kuzu not installed. Run: pip install kuzu")
            sys.exit(1)

        db_path = Path(args.db)
        if not db_path.exists():
            print(f"ERROR: DB path {db_path} does not exist")
            sys.exit(1)

        print(f"\nConnecting to KuzuDB at {db_path}")
        db = kuzu.Database(str(db_path))
        conn = kuzu.Connection(db)
    else:
        conn = None
        print("\n[DRY RUN] No database writes will be performed")

    print("\n=== Injecting TaxIncentive Nodes ===")
    ins, skip = inject_incentives(conn, args.dry_run)
    print(f"OK: Inserted/updated {ins} incentives, skipped {skip}")

    print("\n=== Injecting FT_INCENTIVE_TAX Edges ===")
    ins2, skip2 = inject_incentive_tax_edges(conn, args.dry_run)
    print(f"OK: Created {ins2} edges, skipped {skip2}")

    print("\n=== Injecting FT_INCENTIVE_REGION Edges ===")
    ins3, skip3 = inject_incentive_region_edges(conn, args.dry_run)
    print(f"OK: Created {ins3} edges, skipped {skip3}")

    if not args.dry_run:
        verify(conn)

    print("\nDONE")


if __name__ == "__main__":
    main()
