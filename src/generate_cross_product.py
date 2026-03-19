#!/usr/bin/env python3
"""Generate cross-product matrix nodes from existing graph entities.

Creates HIGH-VALUE intersection nodes that represent real business scenarios:
  Matrix 1: TaxIncentive x Industry x Region -> IncentiveApplicability guides
  Matrix 2: RiskIndicator x Industry -> RiskMonitoringCalendar guides

Output: LawOrRegulation nodes with regulationType='incentive_matrix' or 'risk_matrix'

Usage:
    python src/generate_cross_product.py --db data/finance-tax-graph [--dry-run]
"""

import argparse
import hashlib
import sys
from datetime import date, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        print(f"  WARN: {label} -- {e}")
        return False


def short_hash(text: str) -> str:
    """8-char hash for ID generation."""
    return hashlib.md5(text.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Business Rule Engine: Incentive x Industry applicability
# ---------------------------------------------------------------------------

# Beneficiary type -> applicable industry IDs
# Rules based on actual Chinese tax policy applicability
BENEFICIARY_INDUSTRY_MAP = {
    # Universal: all enterprises can claim
    "all_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_CONSTRUCTION", "IND_FINANCE", "IND_TRANSPORT", "IND_CATERING",
        "IND_REALESTATE", "IND_AGRICULTURE", "IND_HIGH_TECH", "IND_MINING",
    ],
    "all_taxpayer": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_CONSTRUCTION", "IND_FINANCE", "IND_TRANSPORT", "IND_CATERING",
        "IND_REALESTATE", "IND_AGRICULTURE",
    ],
    # Software / IT
    "software_enterprise": ["IND_SOFTWARE", "IND_HIGH_TECH"],
    "key_software_enterprise": ["IND_SOFTWARE"],
    # High-tech
    "high_tech_enterprise": [
        "IND_SOFTWARE", "IND_HIGH_TECH", "IND_MANUFACTURING",
    ],
    # Small taxpayer / micro enterprise
    "small_taxpayer": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_CONSTRUCTION", "IND_TRANSPORT", "IND_CATERING",
        "IND_AGRICULTURE", "IND_REALESTATE",
    ],
    "small_micro_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_CONSTRUCTION", "IND_TRANSPORT", "IND_CATERING",
    ],
    # Agriculture
    "agricultural_producer": ["IND_AGRICULTURE"],
    "agricultural_enterprise": ["IND_AGRICULTURE"],
    "agricultural_cooperative": ["IND_AGRICULTURE"],
    "agricultural_insurer": ["IND_AGRICULTURE", "IND_FINANCE"],
    # Export
    "export_enterprise": [
        "IND_MANUFACTURING", "IND_COMMERCE", "IND_SOFTWARE",
        "IND_EXPORT_REFUND",
    ],
    "cross_border_service": ["IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE"],
    # Real estate / construction
    "real_estate_developer": ["IND_REALESTATE", "IND_REAL_ESTATE"],
    "infrastructure_enterprise": ["IND_CONSTRUCTION"],
    "infrastructure_entity": ["IND_CONSTRUCTION", "IND_TRANSPORT"],
    # IC / semiconductor
    "ic_enterprise": ["IND_MANUFACTURING", "IND_HIGH_TECH"],
    "ic_design_enterprise": ["IND_SOFTWARE", "IND_HIGH_TECH"],
    "ic_130nm_enterprise": ["IND_MANUFACTURING", "IND_HIGH_TECH"],
    "ic_65nm_enterprise": ["IND_MANUFACTURING", "IND_HIGH_TECH"],
    "ic_28nm_enterprise": ["IND_MANUFACTURING", "IND_HIGH_TECH"],
    # Finance
    "financial_institution": ["IND_FINANCE"],
    "bond_holder": ["IND_FINANCE"],
    "venture_capital": ["IND_FINANCE"],
    "qfii_investor": ["IND_FINANCE"],
    # Employer types
    "disability_employer": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
    ],
    # Environmental
    "env_protection_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_CONSTRUCTION",
    ],
    "compliant_enterprise": ["IND_MANUFACTURING", "IND_MINING", "IND_CONSTRUCTION"],
    # Mining / resources
    "mining_enterprise": ["IND_MINING", "IND_COAL_MINING"],
    "oil_gas_enterprise": ["IND_MINING"],
    # Recycling
    "recycling_enterprise": ["IND_RECYCLING", "IND_MANUFACTURING"],
    # Welfare / nonprofit
    "welfare_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_COMMERCE",
    ],
    # Western development
    "western_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_CONSTRUCTION", "IND_TRANSPORT", "IND_AGRICULTURE", "IND_MINING",
    ],
    # Hainan
    "hainan_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_TRANSPORT", "IND_CATERING",
    ],
    # Tech advanced
    "tech_advanced_service": ["IND_SERVICE", "IND_SOFTWARE"],
    "tech_transfer_enterprise": [
        "IND_SOFTWARE", "IND_HIGH_TECH", "IND_MANUFACTURING",
    ],
    # Animation
    "animation_enterprise": ["IND_SERVICE", "IND_SOFTWARE"],
    # Ethnic
    "ethnic_autonomous_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_COMMERCE", "IND_AGRICULTURE",
    ],
    # Poverty
    "poverty_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_COMMERCE", "IND_AGRICULTURE",
    ],
    # Non-resident
    "non_resident_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_COMMERCE", "IND_FINANCE",
    ],
    "foreign_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_COMMERCE", "IND_FINANCE",
    ],
    "resident_enterprise": [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_FINANCE",
    ],
    # Pipeline gas
    "pipeline_gas_enterprise": ["IND_TRANSPORT"],
    # Education / medical / elderly
    "education_institution": ["IND_SERVICE"],
    "medical_institution": ["IND_SERVICE"],
    "elderly_care": ["IND_SERVICE"],
    "research_institution": ["IND_SERVICE", "IND_SOFTWARE", "IND_HIGH_TECH"],
    "charity_organization": ["IND_NONPROFIT"],
    "nonprofit_entity": ["IND_NONPROFIT"],
    # Government / military (skip for industry matrix -- not enterprise types)
    "government_entity": [],
    "military_entity": [],
    "municipal_entity": [],
}

# Beneficiary type -> applicable region filter
# None = all provinces; list of AR_IDs = specific regions only
WESTERN_DEV_REGIONS = [
    "AR_500000",  # Chongqing
    "AR_510000",  # Sichuan
    "AR_520000",  # Guizhou
    "AR_530000",  # Yunnan
    "AR_540000",  # Tibet
    "AR_610000",  # Shaanxi
    "AR_620000",  # Gansu
    "AR_630000",  # Qinghai
    "AR_640000",  # Ningxia
    "AR_650000",  # Xinjiang
    "AR_150000",  # Inner Mongolia
    "AR_450000",  # Guangxi
]

HAINAN_REGIONS = ["AR_460000"]  # Hainan

# Ethnic autonomous regions (have ethnic autonomy tax reduction powers)
ETHNIC_REGIONS = [
    "AR_150000",  # Inner Mongolia
    "AR_450000",  # Guangxi
    "AR_540000",  # Tibet
    "AR_640000",  # Ningxia
    "AR_650000",  # Xinjiang
]

# Economic powerhouse provinces (where most businesses actually operate)
MAJOR_ECONOMIC_REGIONS = [
    "AR_110000",  # Beijing
    "AR_120000",  # Tianjin
    "AR_310000",  # Shanghai
    "AR_320000",  # Jiangsu
    "AR_330000",  # Zhejiang
    "AR_340000",  # Anhui
    "AR_350000",  # Fujian
    "AR_370000",  # Shandong
    "AR_440000",  # Guangdong
    "AR_500000",  # Chongqing
    "AR_510000",  # Sichuan
    "AR_420000",  # Hubei
    "AR_430000",  # Hunan
    "AR_410000",  # Henan
    "AR_210000",  # Liaoning
    "AR_130000",  # Hebei
    "AR_360000",  # Jiangxi
    "AR_610000",  # Shaanxi
]

# Region filter by beneficiary type
BENEFICIARY_REGION_FILTER = {
    "western_enterprise": WESTERN_DEV_REGIONS,
    "hainan_enterprise": HAINAN_REGIONS,
    "ethnic_autonomous_enterprise": ETHNIC_REGIONS,
}


def get_applicable_regions(beneficiary_type: str, all_provinces: list) -> list:
    """Return list of (region_id, region_name) tuples for this beneficiary type."""
    if beneficiary_type in BENEFICIARY_REGION_FILTER:
        allowed = set(BENEFICIARY_REGION_FILTER[beneficiary_type])
        return [(r_id, r_name) for r_id, r_name in all_provinces if r_id in allowed]

    # For universal / broad incentives, use major economic regions only
    # to avoid combinatorial explosion while keeping practical value
    if beneficiary_type in (
        "all_enterprise", "all_taxpayer", "small_taxpayer",
        "small_micro_enterprise",
    ):
        allowed = set(MAJOR_ECONOMIC_REGIONS)
        return [(r_id, r_name) for r_id, r_name in all_provinces if r_id in allowed]

    # For industry-specific incentives, use top economic regions
    top_regions = set(MAJOR_ECONOMIC_REGIONS[:10])  # Top 10 only
    return [(r_id, r_name) for r_id, r_name in all_provinces if r_id in top_regions]


# ---------------------------------------------------------------------------
# Industry-specific Chinese names (for readable titles)
# ---------------------------------------------------------------------------

INDUSTRY_NAMES = {
    "IND_MANUFACTURING": "制造业",
    "IND_SERVICE": "现代服务业",
    "IND_SOFTWARE": "软件和信息技术服务业",
    "IND_COMMERCE": "商贸业",
    "IND_CONSTRUCTION": "建筑业",
    "IND_FINANCE": "金融业",
    "IND_TRANSPORT": "交通运输业",
    "IND_CATERING": "住宿餐饮业",
    "IND_REALESTATE": "房地产业",
    "IND_REAL_ESTATE": "房地产业",
    "IND_AGRICULTURE": "农林牧渔业",
    "IND_HIGH_TECH": "高新技术企业",
    "IND_MINING": "采矿业",
    "IND_COAL_MINING": "煤炭开采和洗选",
    "IND_RECYCLING": "再生资源",
    "IND_EXPORT_REFUND": "出口退税企业",
    "IND_NONPROFIT": "民间非营利组织",
    "IND_GENERAL": "通用",
}


# ---------------------------------------------------------------------------
# Content generators
# ---------------------------------------------------------------------------

def generate_incentive_content(
    incentive_name: str,
    incentive_type: str,
    value: float,
    value_basis: str,
    eligibility: str,
    law_ref: str,
    industry_name: str,
    region_name: str,
    combinable: bool,
) -> str:
    """Generate Chinese-language practical guide content."""
    type_labels = {
        "exemption": "免税",
        "rate_reduction": "税率优惠",
        "refund": "即征即退/退税",
        "super_deduction": "加计扣除",
        "deduction": "税前扣除",
        "deferral": "递延纳税",
        "credit": "税额抵免",
    }
    type_label = type_labels.get(incentive_type, incentive_type)

    value_desc = ""
    if value > 0:
        if value_basis == "flat_rate":
            value_desc = f"优惠税率{value}%"
        elif value_basis == "effective_rate":
            value_desc = f"实际税率{value}%"
        elif value_basis == "reduced_rate":
            value_desc = f"减按{value}%征收"
        elif value_basis == "percentage_extra":
            value_desc = f"加计扣除{value}%"
        elif value_basis == "effective_rate_cap":
            value_desc = f"实际税负超过{value}%部分即征即退"
        elif value_basis == "max_refund_rate":
            value_desc = f"最高退税率{value}%"
        else:
            value_desc = f"优惠幅度{value}"

    combinable_text = "可与其他优惠叠加享受" if combinable else "不可与同类优惠叠加，需择优选择"

    content = f"""【适用指南】{incentive_name} -- {industry_name} -- {region_name}

一、政策概述
优惠类型：{type_label}
{f'优惠力度：{value_desc}' if value_desc else ''}
适用条件：{eligibility}
法规依据：{law_ref}

二、{industry_name}企业适用要点
1. {industry_name}企业在{region_name}申请该优惠，需满足以下条件：
   - 企业注册地在{region_name}辖区内
   - 符合{industry_name}行业分类标准（参照《国民经济行业分类》GB/T 4754）
   - {eligibility}
2. 申报时需准备的行业特定材料：
   - 行业经营资质证明
   - 近期纳税申报表
   - 相关审批/认定文件

三、叠加政策说明
{combinable_text}。
建议结合{region_name}地方性税收优惠政策综合筹划。

四、风险提示
- 确保业务实质符合政策要求，避免形式合规实质不符
- 关注政策有效期，及时跟踪延续或调整公告
- 留存完整的备查资料，应对可能的税务稽查"""

    return content


def generate_risk_content(
    indicator_name: str,
    indicator_code: str,
    metric_name: str,
    metric_formula: str,
    threshold_low: float,
    threshold_high: float,
    industry_benchmark: float,
    severity: str,
    monitoring_freq: str,
    trigger_condition: str,
    detection_method: str,
    recommended_action: str,
    industry_name: str,
) -> str:
    """Generate Chinese-language risk monitoring guide content."""
    severity_labels = {"high": "高", "medium": "中", "low": "低"}
    sev = severity_labels.get(severity, severity)

    freq_labels = {
        "monthly": "每月",
        "quarterly": "每季度",
        "annual": "每年",
        "daily": "每日",
    }
    freq = freq_labels.get(monitoring_freq, monitoring_freq)

    threshold_desc = ""
    if threshold_low > 0 or threshold_high > 0:
        if threshold_low > 0 and threshold_high > 0:
            threshold_desc = f"预警区间：{threshold_low} ~ {threshold_high}"
        elif threshold_low > 0:
            threshold_desc = f"下限阈值：{threshold_low}"
        elif threshold_high > 0:
            threshold_desc = f"上限阈值：{threshold_high}"

    benchmark_desc = f"行业基准值：{industry_benchmark}" if industry_benchmark > 0 else ""

    content = f"""【风险监控日历】{indicator_name} -- {industry_name}

一、指标概览
指标编号：{indicator_code}
监控指标：{metric_name}
{f'计算公式：{metric_formula}' if metric_formula else ''}
风险等级：{sev}
监控频率：{freq}

二、{industry_name}行业阈值
{threshold_desc}
{benchmark_desc}
触发条件：{trigger_condition}

三、{industry_name}行业特殊考虑
1. {industry_name}企业在该指标上的行业特征：
   - 受行业经营周期、季节性波动影响
   - 需结合{industry_name}行业平均水平综合判断
   - 关注上下游产业链关联影响
2. 常见误报场景：
   - 行业政策调整导致的阶段性波动
   - 企业经营模式转型期的正常偏离
   - 季节性因素导致的短期异常

四、监控与应对
{f'检测方法：{detection_method}' if detection_method else ''}
{f'建议措施：{recommended_action}' if recommended_action else ''}
- 建立{freq}自查机制
- 异常时及时准备说明材料
- 保留完整的业务凭证和合同备查"""

    return content


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_entities(conn):
    """Load all needed entities from KuzuDB."""
    # TaxIncentive
    incentives = []
    result = conn.execute(
        "MATCH (n:TaxIncentive) RETURN n.id, n.name, n.incentiveType, n.value, "
        "n.valueBasis, n.beneficiaryType, n.eligibilityCriteria, n.combinable, "
        "n.lawReference ORDER BY n.id"
    )
    while result.has_next():
        row = result.get_next()
        incentives.append({
            "id": row[0], "name": row[1], "incentiveType": row[2],
            "value": row[3], "valueBasis": row[4], "beneficiaryType": row[5],
            "eligibility": row[6], "combinable": row[7], "lawRef": row[8],
        })
    print(f"  Loaded {len(incentives)} TaxIncentive nodes")

    # FTIndustry (level1 + level2 only for meaningful combinations)
    industries = []
    result = conn.execute(
        "MATCH (n:FTIndustry) RETURN n.id, n.name, n.classificationLevel "
        "ORDER BY n.id"
    )
    while result.has_next():
        row = result.get_next()
        industries.append({"id": row[0], "name": row[1], "level": row[2]})
    print(f"  Loaded {len(industries)} FTIndustry nodes")

    # AdministrativeRegion (province level only)
    provinces = []
    result = conn.execute(
        "MATCH (n:AdministrativeRegion) WHERE n.level = 1 "
        "RETURN n.id, n.name ORDER BY n.id"
    )
    while result.has_next():
        row = result.get_next()
        # Skip duplicates (AR_BEIJING vs AR_110000 etc), SAR, and Taiwan
        rid = row[0] or ""
        if rid.startswith("AR_") and len(rid) == 9 and rid[3:].isdigit():
            code = int(rid[3:])
            if code < 700000:  # Exclude Taiwan, HK, Macau
                provinces.append((rid, row[1]))
    print(f"  Loaded {len(provinces)} province-level regions")

    # RiskIndicator (well-structured ones only)
    risk_indicators = []
    result = conn.execute(
        "MATCH (n:RiskIndicator) WHERE n.indicatorCode <> '' "
        "RETURN n.id, n.name, n.indicatorCode, n.metricName, n.metricFormula, "
        "n.thresholdLow, n.thresholdHigh, n.industryBenchmark, n.industryId, "
        "n.severity, n.monitoringFrequency, n.triggerCondition, "
        "n.detectionMethod, n.recommendedAction ORDER BY n.indicatorCode"
    )
    while result.has_next():
        row = result.get_next()
        risk_indicators.append({
            "id": row[0], "name": row[1], "code": row[2],
            "metricName": row[3], "metricFormula": row[4],
            "thresholdLow": row[5], "thresholdHigh": row[6],
            "industryBenchmark": row[7], "industryId": row[8],
            "severity": row[9], "monitoringFrequency": row[10],
            "triggerCondition": row[11], "detectionMethod": row[12],
            "recommendedAction": row[13],
        })
    print(f"  Loaded {len(risk_indicators)} structured RiskIndicator nodes")

    return incentives, industries, provinces, risk_indicators


def generate_matrix1(incentives, industries, provinces, dry_run=False):
    """Matrix 1: TaxIncentive x Industry x Region -> IncentiveApplicability nodes."""
    nodes = []
    industry_map = {ind["id"]: ind for ind in industries}
    today = date.today().isoformat()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # PIT incentives are individual-level, skip for enterprise matrix
    pit_beneficiaries = {
        "all_employee", "individual_with_children", "individual_student",
        "individual_with_elderly", "individual_homeowner", "individual_renter",
        "individual_patient", "individual_with_infant", "individual_pension_participant",
        "annuity_participant", "employee_with_equity", "insurance_beneficiary",
        "military_personnel", "terminated_employee", "award_recipient",
        "diplomat", "individual_first_home", "individual_second_home",
        "individual_owner", "new_energy_vehicle_buyer", "new_energy_vehicle_owner",
        "energy_saving_vehicle_owner",
    }

    for inc in incentives:
        bt = inc["beneficiaryType"]

        # Skip PIT / individual-level incentives
        if bt in pit_beneficiaries:
            continue

        # Get applicable industries
        applicable_industries = BENEFICIARY_INDUSTRY_MAP.get(bt, [])
        if not applicable_industries:
            continue

        # Get applicable regions
        applicable_regions = get_applicable_regions(bt, provinces)
        if not applicable_regions:
            continue

        for ind_id in applicable_industries:
            if ind_id not in industry_map:
                continue
            ind_name = INDUSTRY_NAMES.get(ind_id, industry_map[ind_id]["name"])

            for region_id, region_name in applicable_regions:
                node_id = f"XP_IM_{short_hash(f'{inc['id']}_{ind_id}_{region_id}')}"
                title = f"[适用指南] {inc['name']} -- {ind_name} -- {region_name}"
                content = generate_incentive_content(
                    inc["name"], inc["incentiveType"], inc["value"],
                    inc["valueBasis"], inc["eligibility"], inc["lawRef"],
                    ind_name, region_name, inc["combinable"],
                )
                nodes.append({
                    "id": node_id,
                    "title": title,
                    "regulationType": "incentive_matrix",
                    "content": content,
                    "issuingAuthority": "AI-Fleet CogNebula Cross-Product Engine",
                    "regulationNumber": f"XP-IM-{inc['id']}-{ind_id}-{region_id}",
                    "status": "active",
                    "hierarchyLevel": 99,  # synthetic, lowest priority
                    "today": today,
                    "now_ts": now_ts,
                    # Metadata for edges
                    "_incentive_id": inc["id"],
                    "_industry_id": ind_id,
                    "_region_id": region_id,
                })

    print(f"  Matrix 1 generated: {len(nodes)} IncentiveApplicability nodes")
    return nodes


def generate_matrix2(risk_indicators, industries, dry_run=False):
    """Matrix 2: RiskIndicator x Industry -> RiskMonitoringCalendar nodes."""
    nodes = []
    industry_map = {ind["id"]: ind for ind in industries}
    today = date.today().isoformat()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Core level-1 industries for risk monitoring
    core_industries = [
        "IND_MANUFACTURING", "IND_SERVICE", "IND_SOFTWARE", "IND_COMMERCE",
        "IND_CONSTRUCTION", "IND_FINANCE", "IND_TRANSPORT", "IND_CATERING",
        "IND_REALESTATE", "IND_AGRICULTURE",
    ]

    # Generic risk indicators (no specific industry) apply to all core industries
    # Industry-specific ones only apply to their own + closely related industries
    RELATED_INDUSTRIES = {
        "IND_MANUFACTURING": ["IND_MANUFACTURING", "IND_HIGH_TECH", "IND_RECYCLING"],
        "IND_SERVICE": ["IND_SERVICE", "IND_SOFTWARE", "IND_HR_SERVICES"],
        "IND_COMMERCE": ["IND_COMMERCE", "IND_GOLD_RETAIL"],
        "IND_CONSTRUCTION": ["IND_CONSTRUCTION", "IND_CONCRETE", "IND_PROPERTY_MGMT"],
        "IND_FINANCE": ["IND_FINANCE"],
        "IND_REALESTATE": ["IND_REALESTATE", "IND_REAL_ESTATE"],
        "IND_MINING": ["IND_MINING", "IND_COAL_MINING"],
    }

    # Build reverse map: specific industry -> which core industries it relates to
    specific_to_core = {}
    for core, related in RELATED_INDUSTRIES.items():
        for r in related:
            specific_to_core.setdefault(r, set()).add(core)

    for ri in risk_indicators:
        ri_industry = ri["industryId"]

        if not ri_industry or ri_industry == "IND_GENERAL":
            # Generic indicator: apply to all core industries
            target_industries = core_industries
        elif ri_industry in [ind["id"] for ind in industries]:
            # Has a specific industry -- apply to that + related core industries
            target_ids = specific_to_core.get(ri_industry, set())
            target_ids.add(ri_industry)
            target_industries = [i for i in target_ids if i in industry_map]
        else:
            # Industry ID is a hash (auto-generated sub-industry), skip cross-product
            # but still generate for the indicator itself with generic industry mapping
            # Map BURDEN indicators to closest core industry
            if ri["code"].startswith("BURDEN-"):
                # Tax burden benchmarks -- create 1 node for the indicator's own industry
                target_industries = []
            else:
                target_industries = []

        if not target_industries:
            continue

        for ind_id in target_industries:
            if ind_id not in industry_map:
                continue
            ind_name = INDUSTRY_NAMES.get(ind_id, industry_map[ind_id]["name"])

            # Skip if indicator already has this exact industry (would be redundant)
            if ri_industry == ind_id and len(target_industries) == 1:
                # Still generate -- adds the calendar/guide format
                pass

            node_id = f"XP_RM_{short_hash(f'{ri['id']}_{ind_id}')}"
            title = f"[风险监控日历] {ri['name']} -- {ind_name}"
            content = generate_risk_content(
                ri["name"], ri["code"], ri["metricName"],
                ri["metricFormula"], ri["thresholdLow"], ri["thresholdHigh"],
                ri["industryBenchmark"], ri["severity"],
                ri["monitoringFrequency"], ri["triggerCondition"],
                ri["detectionMethod"], ri["recommendedAction"],
                ind_name,
            )
            nodes.append({
                "id": node_id,
                "title": title,
                "regulationType": "risk_matrix",
                "content": content,
                "issuingAuthority": "AI-Fleet CogNebula Cross-Product Engine",
                "regulationNumber": f"XP-RM-{ri['id']}-{ind_id}",
                "status": "active",
                "hierarchyLevel": 99,
                "today": today,
                "now_ts": now_ts,
                # Metadata for edges
                "_risk_id": ri["id"],
                "_industry_id": ind_id,
            })

    print(f"  Matrix 2 generated: {len(nodes)} RiskMonitoringCalendar nodes")
    return nodes


def insert_nodes(conn, nodes, dry_run=False):
    """Insert LawOrRegulation nodes into KuzuDB."""
    if dry_run:
        print(f"  DRY RUN: would insert {len(nodes)} nodes")
        # Show 5 sample titles
        for n in nodes[:5]:
            print(f"    - {n['title'][:80]}")
        print(f"    ... ({len(nodes) - 5} more)")
        return 0

    inserted = 0
    skipped = 0
    for i, n in enumerate(nodes):
        cypher = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(n['id'])}', "
            f"regulationNumber: '{esc(n['regulationNumber'])}', "
            f"title: '{esc(n['title'])}', "
            f"issuingAuthority: '{esc(n['issuingAuthority'])}', "
            f"regulationType: '{esc(n['regulationType'])}', "
            f"issuedDate: date('{n['today']}'), "
            f"effectiveDate: date('{n['today']}'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: '{n['status']}', "
            f"hierarchyLevel: {n['hierarchyLevel']}, "
            f"sourceUrl: '', "
            f"contentHash: '{short_hash(n['content'])}', "
            f"fullText: '{esc(n['content'])}', "
            f"validTimeStart: timestamp('{n['now_ts']}'), "
            f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
            f"txTimeCreated: timestamp('{n['now_ts']}'), "
            f"txTimeUpdated: timestamp('{n['now_ts']}')"
            f"}})"
        )
        ok = _exec(conn, cypher, n["id"])
        if ok:
            inserted += 1
        else:
            skipped += 1

        if (i + 1) % 500 == 0:
            print(f"    Progress: {i + 1}/{len(nodes)} (inserted={inserted}, skipped={skipped})")

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Generate cross-product matrix nodes")
    parser.add_argument("--db", required=True, help="Path to KuzuDB directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report expected counts without inserting")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB path not found: {db_path}")
        sys.exit(1)

    import kuzu

    if args.dry_run:
        print("NOTE: Opening DB in read-only mode (dry run)")
        db = kuzu.Database(str(db_path), read_only=True)
    else:
        db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    print("=== Loading entities from KuzuDB ===")
    incentives, industries, provinces, risk_indicators = load_entities(conn)

    print()
    print("=== Matrix 1: TaxIncentive x Industry x Region ===")
    m1_nodes = generate_matrix1(incentives, industries, provinces, args.dry_run)

    print()
    print("=== Matrix 2: RiskIndicator x Industry ===")
    m2_nodes = generate_matrix2(risk_indicators, industries, args.dry_run)

    all_nodes = m1_nodes + m2_nodes
    print()
    print(f"=== Total: {len(all_nodes)} cross-product nodes ===")

    if args.dry_run:
        print()
        print("--- Matrix 1 breakdown ---")
        m1_by_type = {}
        for n in m1_nodes:
            reg = n["regulationNumber"].split("-")[2]  # incentive ID part
            m1_by_type[reg] = m1_by_type.get(reg, 0) + 1
        for k, v in sorted(m1_by_type.items(), key=lambda x: -x[1])[:20]:
            print(f"  {k}: {v} nodes")
        print(f"  ... ({len(m1_by_type)} distinct incentives)")

        print()
        print("--- Matrix 2 breakdown ---")
        m2_by_ind = {}
        for n in m2_nodes:
            ind = n["_industry_id"]
            m2_by_ind[ind] = m2_by_ind.get(ind, 0) + 1
        for k, v in sorted(m2_by_ind.items(), key=lambda x: -x[1]):
            print(f"  {INDUSTRY_NAMES.get(k, k)}: {v} nodes")

        print()
        print("--- Sample titles ---")
        print("Matrix 1:")
        for n in m1_nodes[:5]:
            print(f"  {n['title']}")
        print("Matrix 2:")
        for n in m2_nodes[:5]:
            print(f"  {n['title']}")
    else:
        print()
        print("=== Inserting Matrix 1 nodes ===")
        m1_count = insert_nodes(conn, m1_nodes)
        print(f"  Inserted: {m1_count}")

        print()
        print("=== Inserting Matrix 2 nodes ===")
        m2_count = insert_nodes(conn, m2_nodes)
        print(f"  Inserted: {m2_count}")

        print()
        total = m1_count + m2_count
        print(f"=== DONE: {total} new LawOrRegulation nodes created ===")

        # Verify
        result = conn.execute(
            "MATCH (n:LawOrRegulation) WHERE n.regulationType = 'incentive_matrix' "
            "RETURN count(n)"
        )
        im_count = result.get_next()[0]
        result = conn.execute(
            "MATCH (n:LawOrRegulation) WHERE n.regulationType = 'risk_matrix' "
            "RETURN count(n)"
        )
        rm_count = result.get_next()[0]
        print(f"  Verification: incentive_matrix={im_count}, risk_matrix={rm_count}")


if __name__ == "__main__":
    main()
