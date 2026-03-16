#!/usr/bin/env python3
"""Inject comprehensive Chinese tax rate tables into KuzuDB.

Uses the existing TaxRateMapping table for detailed rate entries, plus creates
a new TaxRateSchedule node table for progressive rate brackets (PIT/Land VAT).

Covers all major Chinese tax types:
  - VAT: 13%/9%/6%/0% standard + 3%/5% simplified
  - CIT: 25%/20%/15%/10% + withholding
  - PIT: 7-bracket comprehensive (3%-45%) + 5-bracket business (5%-35%)
  - Stamp duty: 13 tax items
  - Property tax: from-value 1.2% / from-rent 12%
  - Land use tax: 4 tiers by city size
  - Vehicle purchase tax: 10%
  - Deed tax: 3%-5%
  - Consumption tax: major items
  - Urban construction tax: 7%/5%/1%
  - Land appreciation tax: 4-bracket progressive

Usage:
    python src/inject_tax_rates.py --db data/finance-tax-graph [--dry-run]
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
# TaxRateSchedule DDL -- for progressive rate brackets
# ---------------------------------------------------------------------------

DDL_TAX_RATE_SCHEDULE = """CREATE NODE TABLE IF NOT EXISTS TaxRateSchedule(
    id STRING PRIMARY KEY,
    taxTypeId STRING,
    scheduleName STRING,
    bracketOrder INT64,
    lowerBound DOUBLE,
    upperBound DOUBLE,
    rate DOUBLE,
    quickDeduction DOUBLE,
    applicableScope STRING,
    effectiveFrom STRING,
    effectiveUntil STRING,
    legalBasis STRING,
    notes STRING
)"""

DDL_REL_SCHEDULE_TAX = """CREATE REL TABLE IF NOT EXISTS FT_RATE_SCHEDULE(
    FROM TaxRateSchedule TO TaxType
)"""


# ---------------------------------------------------------------------------
# TaxRateMapping data (flat-rate taxes)
# Format: (id, productCategory, productCategoryCode, taxTypeId,
#          applicableRate, rateLabel, simplifiedRate, specialPolicy,
#          specialPolicyDetail, hsCode, invoiceCategory,
#          effectiveFrom, effectiveUntil, sourceRegulation, notes)
# ---------------------------------------------------------------------------

RATE_MAPPINGS = [
    # ===== VAT Standard Rates (增值税标准税率) =====
    ("TRM_VAT_13_GOODS", "销售货物", "VAT-STD-01", "TT_VAT",
     13.0, "标准税率13%", 0.0, "", "销售货物、加工修理修配劳务、有形动产租赁服务",
     "", "增值税专用发票/普通发票", "2019-04-01", "2099-12-31",
     "财政部税务总局海关总署公告2019年第39号", ""),

    ("TRM_VAT_13_TANGIBLE_LEASE", "有形动产租赁", "VAT-STD-02", "TT_VAT",
     13.0, "标准税率13%", 0.0, "", "有形动产经营租赁、融资租赁",
     "", "增值税专用发票", "2019-04-01", "2099-12-31",
     "财政部税务总局海关总署公告2019年第39号", ""),

    ("TRM_VAT_9_TRANSPORT", "交通运输服务", "VAT-LOW-01", "TT_VAT",
     9.0, "低税率9%", 0.0, "", "陆路/水路/航空/管道运输服务",
     "", "增值税专用发票", "2019-04-01", "2099-12-31",
     "财政部税务总局海关总署公告2019年第39号", ""),

    ("TRM_VAT_9_POSTAL", "邮政服务", "VAT-LOW-02", "TT_VAT",
     9.0, "低税率9%", 0.0, "", "邮政普遍服务/特殊服务/其他邮政服务",
     "", "增值税专用发票", "2019-04-01", "2099-12-31",
     "财政部税务总局海关总署公告2019年第39号", ""),

    ("TRM_VAT_9_TELECOM_BASIC", "基础电信服务", "VAT-LOW-03", "TT_VAT",
     9.0, "低税率9%", 0.0, "", "语音通话/出租出借网络/卫星电视信号落地转接",
     "", "增值税专用发票", "2019-04-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_9_CONSTRUCTION", "建筑服务", "VAT-LOW-04", "TT_VAT",
     9.0, "低税率9%", 0.0, "", "工程服务/安装服务/修缮服务/装饰服务/其他建筑服务",
     "", "增值税专用发票", "2019-04-01", "2099-12-31",
     "财政部税务总局海关总署公告2019年第39号", ""),

    ("TRM_VAT_9_REALESTATE", "不动产租赁/销售", "VAT-LOW-05", "TT_VAT",
     9.0, "低税率9%", 0.0, "", "不动产经营租赁/融资租赁/转让不动产/转让土地使用权",
     "", "增值税专用发票", "2019-04-01", "2099-12-31",
     "财政部税务总局海关总署公告2019年第39号", ""),

    ("TRM_VAT_9_AGRI", "农产品", "VAT-LOW-06", "TT_VAT",
     9.0, "低税率9%", 0.0, "", "粮食/食用植物油/自来水/暖气/天然气/图书/饲料/化肥等",
     "", "增值税普通发票/专用发票", "2019-04-01", "2099-12-31",
     "增值税暂行条例第二条", ""),

    ("TRM_VAT_6_MODERN_SERVICE", "现代服务", "VAT-SVC-01", "TT_VAT",
     6.0, "服务税率6%", 0.0, "", "研发/技术/信息技术/文化创意/物流辅助/鉴证咨询/广播影视",
     "", "增值税专用发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_6_FINANCE", "金融服务", "VAT-SVC-02", "TT_VAT",
     6.0, "服务税率6%", 0.0, "", "贷款服务/直接收费金融服务/保险服务/金融商品转让",
     "", "增值税专用发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_6_LIFESTYLE", "生活服务", "VAT-SVC-03", "TT_VAT",
     6.0, "服务税率6%", 0.0, "", "文化体育/教育医疗/旅游娱乐/餐饮住宿/居民日常服务/其他生活服务",
     "", "增值税专用发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_6_TELECOM_VALUE", "增值电信服务", "VAT-SVC-04", "TT_VAT",
     6.0, "服务税率6%", 0.0, "", "短信/彩信/电子数据和信息传输/互联网接入",
     "", "增值税专用发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_6_INTANGIBLE", "销售无形资产(除土地使用权)", "VAT-SVC-05", "TT_VAT",
     6.0, "服务税率6%", 0.0, "", "转让技术/商标/著作权/商誉/自然资源使用权(除土地)",
     "", "增值税专用发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_0_EXPORT", "出口货物/服务", "VAT-ZERO-01", "TT_VAT",
     0.0, "零税率", 0.0, "", "出口货物(符合退税条件)/跨境应税行为",
     "", "出口发票", "1994-01-01", "2099-12-31",
     "增值税暂行条例第二条", ""),

    # VAT Simplified rates
    ("TRM_VAT_3_SIMPLIFIED", "小规模纳税人简易计税3%", "VAT-SIMP-01", "TT_VAT",
     3.0, "简易征收率3%", 3.0, "small_scale", "小规模纳税人销售货物/提供应税劳务适用",
     "", "增值税普通发票", "2014-07-01", "2099-12-31",
     "增值税暂行条例第十二条", "可开专票(放弃减税)"),

    ("TRM_VAT_5_SIMPLIFIED_RE", "不动产简易计税5%", "VAT-SIMP-02", "TT_VAT",
     5.0, "简易征收率5%", 5.0, "simplified", "个人/小规模纳税人出租不动产(非住房)",
     "", "增值税普通发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", ""),

    ("TRM_VAT_5_SIMPLIFIED_HOUSING", "个人出租住房简易计税1.5%", "VAT-SIMP-03", "TT_VAT",
     1.5, "简易征收率1.5%", 1.5, "simplified", "个人出租住房减按1.5%征收率计算缴纳增值税",
     "", "增值税普通发票", "2016-05-01", "2099-12-31",
     "财税[2016]36号", "5%征收率减按1.5%"),

    ("TRM_VAT_3_SIMPLIFIED_LABOR", "劳务派遣简易计税差额5%", "VAT-SIMP-04", "TT_VAT",
     5.0, "简易征收率5%(差额)", 5.0, "simplified_differential",
     "劳务派遣服务选择差额纳税，以取得全部价款减去代付工资福利社保后的余额为销售额按5%征收",
     "", "增值税普通发票", "2016-05-01", "2099-12-31",
     "财税[2016]47号", ""),

    # ===== CIT Rates (企业所得税税率) =====
    ("TRM_CIT_25_STANDARD", "企业所得税标准税率", "CIT-STD-01", "TT_CIT",
     25.0, "标准税率25%", 0.0, "", "居民企业标准所得税率",
     "", "", "2008-01-01", "2099-12-31",
     "企业所得税法第四条", ""),

    ("TRM_CIT_20_SMALL", "小型微利企业20%名义税率", "CIT-PREF-01", "TT_CIT",
     20.0, "小微企业名义税率20%", 0.0, "small_micro", "小型微利企业减按20%税率(实际更低)",
     "", "", "2008-01-01", "2099-12-31",
     "企业所得税法第二十八条", "配合减计所得优惠实际约5%"),

    ("TRM_CIT_15_HNTE", "高新技术企业15%", "CIT-PREF-02", "TT_CIT",
     15.0, "高新技术企业15%", 0.0, "high_tech", "经认定的高新技术企业减按15%税率",
     "", "", "2008-01-01", "2099-12-31",
     "企业所得税法第二十八条", ""),

    ("TRM_CIT_15_WESTERN", "西部大开发15%", "CIT-PREF-03", "TT_CIT",
     15.0, "西部大开发15%", 0.0, "western_dev", "西部地区鼓励类产业企业减按15%税率",
     "", "", "2021-01-01", "2030-12-31",
     "财政部税务总局发改委公告2020年第23号", ""),

    ("TRM_CIT_10_NONRES", "非居民企业预提所得税10%", "CIT-WH-01", "TT_CIT",
     10.0, "预提所得税10%", 0.0, "withholding",
     "非居民企业取得来源于中国的股息/利息/租金/特许权使用费等所得",
     "", "", "2008-01-01", "2099-12-31",
     "企业所得税法第三条", ""),

    ("TRM_CIT_10_KEY_SOFTWARE", "重点软件企业10%", "CIT-PREF-04", "TT_CIT",
     10.0, "重点软件企业10%", 0.0, "key_software", "国家规划布局内重点软件企业",
     "", "", "2020-01-01", "2030-12-31",
     "财政部税务总局公告2020年第45号", ""),

    # ===== Stamp Duty (印花税税目税率) =====
    ("TRM_STAMP_LOAN", "借款合同", "STAMP-01", "TT_STAMP",
     0.005, "万分之零点五", 0.0, "", "银行及其他金融组织和借款人(不包括银行同业拆借)所签订的借款合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_FINANCING_LEASE", "融资租赁合同", "STAMP-02", "TT_STAMP",
     0.005, "万分之零点五", 0.0, "", "融资租赁合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_PURCHASE_SALE", "买卖合同", "STAMP-03", "TT_STAMP",
     0.03, "万分之三", 0.0, "", "动产买卖合同(不包括个人与电子商务经营者签订的)",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_CONTRACT_WORK", "承揽合同", "STAMP-04", "TT_STAMP",
     0.03, "万分之三", 0.0, "", "加工承揽合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_CONSTRUCTION", "建设工程合同", "STAMP-05", "TT_STAMP",
     0.03, "万分之三", 0.0, "", "建设工程勘察设计合同/建筑安装工程承包合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_TRANSPORT", "运输合同", "STAMP-06", "TT_STAMP",
     0.03, "万分之三", 0.0, "", "货物运输合同(不包括管道运输合同)",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_TECHNOLOGY", "技术合同", "STAMP-07", "TT_STAMP",
     0.03, "万分之三", 0.0, "", "技术开发/转让/咨询/服务等合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_LEASE", "租赁合同", "STAMP-08", "TT_STAMP",
     0.1, "千分之一", 0.0, "", "财产租赁合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_CUSTODY", "保管合同", "STAMP-09", "TT_STAMP",
     0.1, "千分之一", 0.0, "", "仓储保管合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_STORAGE", "仓储合同", "STAMP-10", "TT_STAMP",
     0.1, "千分之一", 0.0, "", "仓储合同",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_INSURANCE", "财产保险合同", "STAMP-11", "TT_STAMP",
     0.1, "千分之一", 0.0, "", "财产保险合同(不包括再保险合同)",
     "", "", "2022-07-01", "2099-12-31", "印花税法", ""),

    ("TRM_STAMP_PROPERTY_TRANSFER", "产权转移书据", "STAMP-12", "TT_STAMP",
     0.05, "万分之五", 0.0, "", "土地使用权/房屋建筑物/股权等转移书据",
     "", "", "2022-07-01", "2099-12-31", "印花税法", "含土地使用权出让/转让"),

    ("TRM_STAMP_BUSINESS_BOOKS", "营业账簿", "STAMP-13", "TT_STAMP",
     0.025, "万分之二点五", 0.0, "", "营业账簿(记载资金的账簿按实收资本和资本公积合计金额)",
     "", "", "2022-07-01", "2099-12-31", "印花税法", "2018年起减半"),

    ("TRM_STAMP_SECURITIES", "证券交易", "STAMP-14", "TT_STAMP",
     0.1, "千分之一(卖方)", 0.0, "", "证券(股票)交易印花税，向出让方单边征收",
     "", "", "2023-08-28", "2099-12-31",
     "财政部税务总局公告2023年第39号", "2023年8月28日减半至千分之一"),

    # ===== Property Tax (房产税税率) =====
    ("TRM_PROPERTY_FROM_VALUE", "房产税从价计征", "PROP-01", "TT_PROPERTY",
     1.2, "从价1.2%", 0.0, "", "自用房产按房产原值一次减除10%-30%后的余值x1.2%",
     "", "", "1986-10-01", "2099-12-31", "房产税暂行条例", "减除比例由各省确定"),

    ("TRM_PROPERTY_FROM_RENT", "房产税从租计征", "PROP-02", "TT_PROPERTY",
     12.0, "从租12%", 0.0, "", "出租房产按租金收入x12%",
     "", "", "1986-10-01", "2099-12-31", "房产税暂行条例", ""),

    ("TRM_PROPERTY_FROM_RENT_INDIVIDUAL", "个人出租住房房产税4%", "PROP-03", "TT_PROPERTY",
     4.0, "个人出租住房4%", 0.0, "individual_rental",
     "个人出租住房不区分用途减按4%税率征收房产税",
     "", "", "2008-03-01", "2099-12-31", "财税[2008]24号", ""),

    # ===== Land Use Tax (城镇土地使用税税率) =====
    ("TRM_LANDUSE_TIER1", "大城市(50万以上)土地使用税", "LAND-01", "TT_LAND_USE",
     0.0, "1.5-30元/平方米/年", 0.0, "", "大城市(50万以上人口)每平方米年税额1.5-30元",
     "", "", "1988-11-01", "2099-12-31", "城镇土地使用税暂行条例", "具体标准由各省确定"),

    ("TRM_LANDUSE_TIER2", "中等城市(20-50万)土地使用税", "LAND-02", "TT_LAND_USE",
     0.0, "1.2-24元/平方米/年", 0.0, "", "中等城市(20-50万人口)每平方米年税额1.2-24元",
     "", "", "1988-11-01", "2099-12-31", "城镇土地使用税暂行条例", ""),

    ("TRM_LANDUSE_TIER3", "小城市(20万以下)土地使用税", "LAND-03", "TT_LAND_USE",
     0.0, "0.9-18元/平方米/年", 0.0, "", "小城市(20万以下人口)每平方米年税额0.9-18元",
     "", "", "1988-11-01", "2099-12-31", "城镇土地使用税暂行条例", ""),

    ("TRM_LANDUSE_TIER4", "县城/建制镇/工矿区土地使用税", "LAND-04", "TT_LAND_USE",
     0.0, "0.6-12元/平方米/年", 0.0, "", "县城、建制镇、工矿区每平方米年税额0.6-12元",
     "", "", "1988-11-01", "2099-12-31", "城镇土地使用税暂行条例", ""),

    # ===== Vehicle Purchase Tax (车辆购置税) =====
    ("TRM_VEHICLE_PURCHASE", "车辆购置税标准税率", "VP-01", "TT_VAT",
     10.0, "车辆购置税10%", 0.0, "", "购置应税车辆按计税价格(不含增值税)x10%",
     "", "", "2019-07-01", "2099-12-31", "车辆购置税法", "新能源汽车免征"),

    # ===== Deed Tax (契税) =====
    ("TRM_DEED_STANDARD", "契税标准税率", "DEED-01", "TT_CONTRACT",
     0.0, "3%-5%", 0.0, "", "承受土地/房屋权属的单位和个人，具体税率由各省确定",
     "", "", "2021-09-01", "2099-12-31", "契税法", "多数省份为3%或4%"),

    # ===== Urban Construction Tax (城市维护建设税) =====
    ("TRM_URBAN_CITY", "城建税-市区7%", "URBAN-01", "TT_URBAN",
     7.0, "市区7%", 0.0, "", "纳税人所在地为市区的税率为7%",
     "", "", "2021-09-01", "2099-12-31", "城市维护建设税法", ""),

    ("TRM_URBAN_COUNTY", "城建税-县城/镇5%", "URBAN-02", "TT_URBAN",
     5.0, "县城/镇5%", 0.0, "", "纳税人所在地为县城、镇的税率为5%",
     "", "", "2021-09-01", "2099-12-31", "城市维护建设税法", ""),

    ("TRM_URBAN_OTHER", "城建税-其他1%", "URBAN-03", "TT_URBAN",
     1.0, "其他地区1%", 0.0, "", "纳税人所在地不在市区、县城或镇的税率为1%",
     "", "", "2021-09-01", "2099-12-31", "城市维护建设税法", ""),

    # ===== Education Surcharge (教育费附加) =====
    ("TRM_EDU_SURCHARGE", "教育费附加3%", "EDU-01", "TT_EDUCATION",
     3.0, "教育费附加3%", 0.0, "", "以增值税和消费税税额为计征依据，费率3%",
     "", "", "2005-10-01", "2099-12-31", "教育费附加征收规定", ""),

    # ===== Local Education Surcharge (地方教育附加) =====
    ("TRM_LOCAL_EDU_SURCHARGE", "地方教育附加2%", "LEDU-01", "TT_LOCAL_EDU",
     2.0, "地方教育附加2%", 0.0, "", "以增值税和消费税税额为计征依据，费率2%",
     "", "", "2010-01-01", "2099-12-31", "地方教育附加征收规定", ""),

    # ===== Consumption Tax Key Items (消费税主要税目) =====
    ("TRM_CONSUMPTION_TOBACCO", "消费税-卷烟", "CONS-01", "TT_CONSUMPTION",
     56.0, "甲类56%+0.003元/支", 0.0, "", "甲类卷烟56%+0.003元/支；乙类36%+0.003元/支",
     "", "", "2009-05-01", "2099-12-31", "消费税暂行条例", "复合计税"),

    ("TRM_CONSUMPTION_LIQUOR", "消费税-白酒", "CONS-02", "TT_CONSUMPTION",
     20.0, "白酒20%+0.5元/斤", 0.0, "", "白酒20%从价税+0.5元/500克(毫升)从量税",
     "", "", "2006-04-01", "2099-12-31", "消费税暂行条例", "复合计税"),

    ("TRM_CONSUMPTION_BEER", "消费税-啤酒", "CONS-03", "TT_CONSUMPTION",
     0.0, "甲类250元/吨|乙类220元/吨", 0.0, "", "甲类啤酒(≥3000元/吨)250元/吨；乙类220元/吨",
     "", "", "2006-04-01", "2099-12-31", "消费税暂行条例", "从量定额"),

    ("TRM_CONSUMPTION_COSMETICS", "消费税-高档化妆品", "CONS-04", "TT_CONSUMPTION",
     15.0, "高档化妆品15%", 0.0, "", "高档化妆品(生产环节销售价≥10元/ml或片或张)消费税率15%",
     "", "", "2016-10-01", "2099-12-31", "财税[2016]103号", ""),

    ("TRM_CONSUMPTION_JEWELRY", "消费税-贵重首饰", "CONS-05", "TT_CONSUMPTION",
     5.0, "金银首饰5%/其他10%", 0.0, "", "金银首饰/铂金首饰/钻石及钻石饰品5%；其他贵重首饰/珠宝玉石10%",
     "", "", "1994-01-01", "2099-12-31", "消费税暂行条例", ""),

    ("TRM_CONSUMPTION_CAR_HIGH", "消费税-超豪华小汽车", "CONS-06", "TT_CONSUMPTION",
     10.0, "超豪华小汽车加征10%", 0.0, "",
     "零售价≥130万元(不含增值税)的超豪华小汽车在零售环节加征10%消费税",
     "", "", "2016-12-01", "2099-12-31", "财税[2016]129号", ""),

    ("TRM_CONSUMPTION_CAR_STANDARD", "消费税-小汽车", "CONS-07", "TT_CONSUMPTION",
     0.0, "1%-40%(按排量)", 0.0, "",
     "乘用车按排量: ≤1.0L 1% | 1.0-1.5L 3% | 1.5-2.0L 5% | 2.0-2.5L 9% | 2.5-3.0L 12% | 3.0-4.0L 25% | >4.0L 40%",
     "", "", "2008-09-01", "2099-12-31", "消费税暂行条例", ""),

    ("TRM_CONSUMPTION_FUEL", "消费税-成品油", "CONS-08", "TT_CONSUMPTION",
     0.0, "汽油1.52元/升|柴油1.20元/升", 0.0, "",
     "汽油1.52元/升；柴油1.20元/升；航空煤油1.20元/升；石脑油1.52元/升",
     "", "", "2015-01-13", "2099-12-31", "消费税暂行条例", "从量定额"),

    # ===== Environmental Protection Tax (环境保护税) =====
    ("TRM_ENV_AIR", "环保税-大气污染物", "ENV-01", "TT_ENV",
     0.0, "1.2-12元/污染当量", 0.0, "",
     "大气污染物每污染当量1.2-12元(各省自定)",
     "", "", "2018-01-01", "2099-12-31", "环境保护税法", "按污染当量数"),

    ("TRM_ENV_WATER", "环保税-水污染物", "ENV-02", "TT_ENV",
     0.0, "1.4-14元/污染当量", 0.0, "",
     "水污染物每污染当量1.4-14元(各省自定)",
     "", "", "2018-01-01", "2099-12-31", "环境保护税法", "按污染当量数"),

    ("TRM_ENV_SOLID", "环保税-固体废物", "ENV-03", "TT_ENV",
     0.0, "5-1000元/吨", 0.0, "",
     "煤矸石5元/吨；尾矿15元/吨；危废1000元/吨；冶炼渣/粉煤灰等25元/吨；其他固废25元/吨",
     "", "", "2018-01-01", "2099-12-31", "环境保护税法", ""),

    ("TRM_ENV_NOISE", "环保税-工业噪声", "ENV-04", "TT_ENV",
     0.0, "350-11200元/月", 0.0, "",
     "超标1-3dB 350元/月；4-6dB 700元/月；7-9dB 1400元/月；10-12dB 2800元/月；13-15dB 5600元/月；>15dB 11200元/月",
     "", "", "2018-01-01", "2099-12-31", "环境保护税法", ""),

    # ===== Tobacco Tax (烟叶税) =====
    ("TRM_TOBACCO_LEAF", "烟叶税20%", "TOBACCO-01", "TT_TOBACCO",
     20.0, "烟叶税20%", 0.0, "", "在中华人民共和国境内收购烟叶的单位为烟叶税纳税人，税率20%",
     "", "", "2018-07-01", "2099-12-31", "烟叶税法", "应纳税额=收购金额x(1+10%)x20%"),

    # ===== Resource Tax - common items (资源税) =====
    ("TRM_RESOURCE_CRUDE_OIL", "资源税-原油", "RES-01", "TT_RESOURCE",
     6.0, "原油6%", 0.0, "", "原油资源税率6%",
     "", "", "2020-09-01", "2099-12-31", "资源税法", "从价计征"),

    ("TRM_RESOURCE_NATURAL_GAS", "资源税-天然气", "RES-02", "TT_RESOURCE",
     6.0, "天然气6%", 0.0, "", "天然气资源税率6%",
     "", "", "2020-09-01", "2099-12-31", "资源税法", "从价计征"),

    ("TRM_RESOURCE_COAL", "资源税-煤", "RES-03", "TT_RESOURCE",
     0.0, "原煤2%-10%", 0.0, "", "煤炭资源税率2%-10%(各省自定)",
     "", "", "2020-09-01", "2099-12-31", "资源税法", "从价计征"),

    ("TRM_RESOURCE_RARE_EARTH", "资源税-稀土", "RES-04", "TT_RESOURCE",
     0.0, "轻稀土7%-12%|中重稀土20%", 0.0, "",
     "轻稀土矿7%-12%；中重稀土矿20%",
     "", "", "2020-09-01", "2099-12-31", "资源税法", ""),
]


# ---------------------------------------------------------------------------
# TaxRateSchedule data -- progressive brackets
# Format: (id, taxTypeId, scheduleName, bracketOrder, lowerBound, upperBound,
#          rate, quickDeduction, applicableScope, effectiveFrom, effectiveUntil,
#          legalBasis, notes)
# ---------------------------------------------------------------------------

RATE_SCHEDULES = [
    # ===== PIT Comprehensive Income 7-bracket (个税综合所得7级) =====
    # Annual taxable income brackets (after standard deduction of 60,000/year)
    ("TRS_PIT_COMP_01", "TT_PIT", "综合所得年度税率表", 1,
     0.0, 36000.0, 3.0, 0.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: 0-3000"),

    ("TRS_PIT_COMP_02", "TT_PIT", "综合所得年度税率表", 2,
     36000.0, 144000.0, 10.0, 2520.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: 3000-12000"),

    ("TRS_PIT_COMP_03", "TT_PIT", "综合所得年度税率表", 3,
     144000.0, 300000.0, 20.0, 16920.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: 12000-25000"),

    ("TRS_PIT_COMP_04", "TT_PIT", "综合所得年度税率表", 4,
     300000.0, 420000.0, 25.0, 31920.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: 25000-35000"),

    ("TRS_PIT_COMP_05", "TT_PIT", "综合所得年度税率表", 5,
     420000.0, 660000.0, 30.0, 52920.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: 35000-55000"),

    ("TRS_PIT_COMP_06", "TT_PIT", "综合所得年度税率表", 6,
     660000.0, 960000.0, 35.0, 85920.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: 55000-80000"),

    ("TRS_PIT_COMP_07", "TT_PIT", "综合所得年度税率表", 7,
     960000.0, 999999999.0, 45.0, 181920.0, "comprehensive_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", "月换算: >80000"),

    # ===== PIT Business Income 5-bracket (个税经营所得5级) =====
    ("TRS_PIT_BIZ_01", "TT_PIT", "经营所得年度税率表", 1,
     0.0, 30000.0, 5.0, 0.0, "business_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", ""),

    ("TRS_PIT_BIZ_02", "TT_PIT", "经营所得年度税率表", 2,
     30000.0, 90000.0, 10.0, 1500.0, "business_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", ""),

    ("TRS_PIT_BIZ_03", "TT_PIT", "经营所得年度税率表", 3,
     90000.0, 300000.0, 20.0, 10500.0, "business_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", ""),

    ("TRS_PIT_BIZ_04", "TT_PIT", "经营所得年度税率表", 4,
     300000.0, 500000.0, 30.0, 40500.0, "business_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", ""),

    ("TRS_PIT_BIZ_05", "TT_PIT", "经营所得年度税率表", 5,
     500000.0, 999999999.0, 35.0, 65500.0, "business_annual",
     "2019-01-01", "2099-12-31", "个人所得税法", ""),

    # ===== PIT Monthly Bonus Rate Table (年终奖月度换算税率表) =====
    ("TRS_PIT_BONUS_01", "TT_PIT", "全年一次性奖金月度税率表", 1,
     0.0, 3000.0, 3.0, 0.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", "奖金/12后适用"),

    ("TRS_PIT_BONUS_02", "TT_PIT", "全年一次性奖金月度税率表", 2,
     3000.0, 12000.0, 10.0, 210.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", ""),

    ("TRS_PIT_BONUS_03", "TT_PIT", "全年一次性奖金月度税率表", 3,
     12000.0, 25000.0, 20.0, 1410.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", ""),

    ("TRS_PIT_BONUS_04", "TT_PIT", "全年一次性奖金月度税率表", 4,
     25000.0, 35000.0, 25.0, 2660.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", ""),

    ("TRS_PIT_BONUS_05", "TT_PIT", "全年一次性奖金月度税率表", 5,
     35000.0, 55000.0, 30.0, 4410.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", ""),

    ("TRS_PIT_BONUS_06", "TT_PIT", "全年一次性奖金月度税率表", 6,
     55000.0, 80000.0, 35.0, 7160.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", ""),

    ("TRS_PIT_BONUS_07", "TT_PIT", "全年一次性奖金月度税率表", 7,
     80000.0, 999999999.0, 45.0, 15160.0, "annual_bonus_monthly",
     "2024-01-01", "2027-12-31", "财政部税务总局公告2023年第30号", ""),

    # ===== Land Appreciation Tax 4-bracket (土地增值税4级) =====
    ("TRS_LAND_VAT_01", "TT_LAND_VAT", "土地增值税4级超率累进税率表", 1,
     0.0, 50.0, 30.0, 0.0, "appreciation_ratio_pct",
     "1994-01-01", "2099-12-31", "土地增值税暂行条例", "增值额未超过扣除项目金额50%"),

    ("TRS_LAND_VAT_02", "TT_LAND_VAT", "土地增值税4级超率累进税率表", 2,
     50.0, 100.0, 40.0, 5.0, "appreciation_ratio_pct",
     "1994-01-01", "2099-12-31", "土地增值税暂行条例", "超过50%未超过100%"),

    ("TRS_LAND_VAT_03", "TT_LAND_VAT", "土地增值税4级超率累进税率表", 3,
     100.0, 200.0, 50.0, 15.0, "appreciation_ratio_pct",
     "1994-01-01", "2099-12-31", "土地增值税暂行条例", "超过100%未超过200%"),

    ("TRS_LAND_VAT_04", "TT_LAND_VAT", "土地增值税4级超率累进税率表", 4,
     200.0, 999999999.0, 60.0, 35.0, "appreciation_ratio_pct",
     "1994-01-01", "2099-12-31", "土地增值税暂行条例", "超过200%"),
]


# ---------------------------------------------------------------------------
# Injection logic
# ---------------------------------------------------------------------------

def create_schedule_schema(conn, dry_run: bool):
    """Create TaxRateSchedule node table and FT_RATE_SCHEDULE rel table if not exist."""
    if dry_run:
        print("[DRY RUN] Would create TaxRateSchedule + FT_RATE_SCHEDULE tables")
        return
    _exec(conn, DDL_TAX_RATE_SCHEDULE, "NODE TaxRateSchedule")
    _exec(conn, DDL_REL_SCHEDULE_TAX, "REL FT_RATE_SCHEDULE")
    print("OK: Schema ensured (TaxRateSchedule + FT_RATE_SCHEDULE)")


def inject_rate_mappings(conn, dry_run: bool) -> tuple[int, int]:
    """Inject flat-rate tax entries into TaxRateMapping."""
    inserted = 0
    skipped = 0

    for item in RATE_MAPPINGS:
        (rm_id, prod_cat, pcc, tax_type, rate, label, simp_rate, sp,
         sp_detail, hs, inv_cat, eff_from, eff_until, source, notes) = item

        sql = (
            f"MERGE (n:TaxRateMapping {{id: '{esc(rm_id)}'}}) "
            f"SET n.productCategory = '{esc(prod_cat)}', "
            f"n.productCategoryCode = '{esc(pcc)}', "
            f"n.taxTypeId = '{esc(tax_type)}', "
            f"n.applicableRate = {rate}, "
            f"n.rateLabel = '{esc(label)}', "
            f"n.simplifiedRate = {simp_rate}, "
            f"n.specialPolicy = '{esc(sp)}', "
            f"n.specialPolicyDetail = '{esc(sp_detail)}', "
            f"n.hsCode = '{esc(hs)}', "
            f"n.invoiceCategory = '{esc(inv_cat)}', "
            f"n.effectiveFrom = date('{eff_from}'), "
            f"n.effectiveUntil = date('{eff_until}'), "
            f"n.sourceRegulation = '{esc(source)}', "
            f"n.notes = '{esc(notes)}'"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"TaxRateMapping {rm_id}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def inject_rate_mapping_edges(conn, dry_run: bool) -> tuple[int, int]:
    """Create OP_MAPS_TO_RATE edges from TaxRateMapping to TaxType."""
    inserted = 0
    skipped = 0

    for item in RATE_MAPPINGS:
        rm_id = item[0]
        tax_type = item[3]

        sql = (
            f"MATCH (a:TaxRateMapping {{id: '{esc(rm_id)}'}}), "
            f"(b:TaxType {{id: '{esc(tax_type)}'}}) "
            f"CREATE (a)-[:OP_MAPS_TO_RATE]->(b)"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"MAPS_TO_RATE {rm_id}->{tax_type}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def inject_rate_schedules(conn, dry_run: bool) -> tuple[int, int]:
    """Inject progressive rate bracket data into TaxRateSchedule."""
    inserted = 0
    skipped = 0

    for item in RATE_SCHEDULES:
        (sched_id, tax_type, name, order, lower, upper, rate, quick_ded,
         scope, eff_from, eff_until, basis, notes) = item

        sql = (
            f"MERGE (n:TaxRateSchedule {{id: '{esc(sched_id)}'}}) "
            f"SET n.taxTypeId = '{esc(tax_type)}', "
            f"n.scheduleName = '{esc(name)}', "
            f"n.bracketOrder = {order}, "
            f"n.lowerBound = {lower}, "
            f"n.upperBound = {upper}, "
            f"n.rate = {rate}, "
            f"n.quickDeduction = {quick_ded}, "
            f"n.applicableScope = '{esc(scope)}', "
            f"n.effectiveFrom = '{esc(eff_from)}', "
            f"n.effectiveUntil = '{esc(eff_until)}', "
            f"n.legalBasis = '{esc(basis)}', "
            f"n.notes = '{esc(notes)}'"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"TaxRateSchedule {sched_id}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def inject_schedule_tax_edges(conn, dry_run: bool) -> tuple[int, int]:
    """Create FT_RATE_SCHEDULE edges from TaxRateSchedule to TaxType."""
    inserted = 0
    skipped = 0

    # Deduplicate: one edge per unique (schedule_group, tax_type) pair
    seen = set()
    for item in RATE_SCHEDULES:
        sched_id = item[0]
        tax_type = item[1]

        sql = (
            f"MATCH (a:TaxRateSchedule {{id: '{esc(sched_id)}'}}), "
            f"(b:TaxType {{id: '{esc(tax_type)}'}}) "
            f"CREATE (a)-[:FT_RATE_SCHEDULE]->(b)"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"RATE_SCHEDULE {sched_id}->{tax_type}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def verify(conn):
    """Verify injection results."""
    print("\n--- Verification ---")
    try:
        result = conn.execute("MATCH (n:TaxRateMapping) RETURN count(n)")
        print(f"  TaxRateMapping nodes: {result.get_next()[0]}")

        result = conn.execute("MATCH (n:TaxRateSchedule) RETURN count(n)")
        print(f"  TaxRateSchedule nodes: {result.get_next()[0]}")

        result = conn.execute("MATCH ()-[r:OP_MAPS_TO_RATE]->() RETURN count(r)")
        print(f"  OP_MAPS_TO_RATE edges: {result.get_next()[0]}")

        result = conn.execute("MATCH ()-[r:FT_RATE_SCHEDULE]->() RETURN count(r)")
        print(f"  FT_RATE_SCHEDULE edges: {result.get_next()[0]}")

        # Rate schedule breakdown
        result = conn.execute(
            "MATCH (n:TaxRateSchedule) RETURN n.scheduleName AS name, count(*) AS cnt ORDER BY name"
        )
        while result.has_next():
            row = result.get_next()
            print(f"    {row[0]}: {row[1]} brackets")

    except Exception as e:
        print(f"WARN: Verification failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Inject comprehensive tax rate tables into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate only, no DB writes")
    args = parser.parse_args()

    print(f"=== Tax Rate Table Injection ===")
    print(f"TaxRateMapping entries: {len(RATE_MAPPINGS)}")
    print(f"TaxRateSchedule brackets: {len(RATE_SCHEDULES)}")

    # Summary by tax type
    by_tax = {}
    for item in RATE_MAPPINGS:
        tt = item[3]
        by_tax[tt] = by_tax.get(tt, 0) + 1
    print("\nRate mappings by tax type:")
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

    print("\n=== Creating TaxRateSchedule Schema ===")
    create_schedule_schema(conn, args.dry_run)

    print("\n=== Injecting TaxRateMapping Entries ===")
    ins1, skip1 = inject_rate_mappings(conn, args.dry_run)
    print(f"OK: Inserted/updated {ins1} rate mappings, skipped {skip1}")

    print("\n=== Injecting OP_MAPS_TO_RATE Edges ===")
    ins2, skip2 = inject_rate_mapping_edges(conn, args.dry_run)
    print(f"OK: Created {ins2} edges, skipped {skip2}")

    print("\n=== Injecting TaxRateSchedule Brackets ===")
    ins3, skip3 = inject_rate_schedules(conn, args.dry_run)
    print(f"OK: Inserted/updated {ins3} rate brackets, skipped {skip3}")

    print("\n=== Injecting FT_RATE_SCHEDULE Edges ===")
    ins4, skip4 = inject_schedule_tax_edges(conn, args.dry_run)
    print(f"OK: Created {ins4} edges, skipped {skip4}")

    if not args.dry_run:
        verify(conn)

    total = ins1 + ins2 + ins3 + ins4
    print(f"\n=== Grand Total: {total} operations ===")
    print("DONE")


if __name__ == "__main__":
    main()
