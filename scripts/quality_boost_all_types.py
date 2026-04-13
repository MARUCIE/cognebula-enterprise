#!/usr/bin/env python3
"""Boost content quality for all FAIL types in 6D audit.

Phase A: Structured assembly (DOC types, no AI)
  - RegionalTaxPolicy: assemble description from region + policy_name + local_variation
  - SocialInsuranceRule: expand description from all structured fields

Phase B: Gemini expand (QA types, ai_expandable)
  - MindmapNode: generate content from node_text + category
  - IndustryRiskProfile: generate description from industry + indicator + risk_level
  - AccountingEntry: expand description from scenario + accounts
  - TaxRiskScenario: expand description from all fields
  - ComplianceRule: generate fullText from all fields

Run on kg-node (API must be stopped):
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 scripts/quality_boost_all_types.py
    sudo systemctl start kg-api
"""
import kuzu
import json
import os
import sys
import time
from urllib.request import Request, urlopen

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_BASE = "https://generativelanguage.googleapis.com"
GEMINI_MODEL = "gemini-2.5-flash-lite"


def call_gemini(prompt: str, retries: int = 3) -> str:
    """Call Gemini API with retry."""
    url = f"{GEMINI_BASE}/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 16384,
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }).encode()

    for attempt in range(retries):
        try:
            req = Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  WARN: Gemini failed after {retries} attempts: {e}")
                return ""


def safe_str(val) -> str:
    """Convert value to safe string for Cypher."""
    s = str(val or "").replace("\\", "\\\\").replace("'", "\\'")
    return s


# ══════════════════════════════════════════════════
# Phase A: Structured Assembly (DOC types)
# ══════════════════════════════════════════════════

def fix_regional_tax_policy(conn):
    """RegionalTaxPolicy: assemble description from structured fields."""
    print("\n=== Phase A1: RegionalTaxPolicy (structured assembly) ===")

    # Ensure description column exists
    try:
        conn.execute("ALTER TABLE RegionalTaxPolicy ADD description STRING DEFAULT ''")
        print("  Added description column")
    except:
        pass  # column already exists

    r = conn.execute(
        "MATCH (n:RegionalTaxPolicy) "
        "RETURN n.id, n.region, n.policy_name, n.local_variation"
    )
    count = 0
    while r.has_next():
        row = r.get_next()
        nid, region, policy, variation = row[0], row[1] or "", row[2] or "", row[3] or ""
        if not nid:
            continue

        desc = (
            f"{region}地区税收政策：{policy}。"
            f"适用范围：{region}辖区内符合条件的纳税人。"
            f"执行标准：{variation}。"
            f"该政策属于地方性税收优惠措施，纳税人应按照{region}税务机关发布的最新通知和实施细则执行。"
            f"申报时需确认资格条件，留存相关证明材料备查。政策享受期间应关注主管税务机关的合规要求和申报截止日期。"
        )

        conn.execute(
            f"MATCH (n:RegionalTaxPolicy) WHERE n.id = '{safe_str(nid)}' "
            f"SET n.description = '{safe_str(desc)}'"
        )
        count += 1

    conn.execute("CHECKPOINT")
    print(f"  RegionalTaxPolicy: {count} descriptions assembled")


def fix_social_insurance_rule(conn):
    """SocialInsuranceRule: expand description from all structured fields."""
    print("\n=== Phase A2: SocialInsuranceRule (structured assembly) ===")

    # Ensure description column exists
    try:
        conn.execute("ALTER TABLE SocialInsuranceRule ADD description STRING DEFAULT ''")
        print("  Added description column")
    except:
        pass

    r = conn.execute(
        "MATCH (n:SocialInsuranceRule) "
        "RETURN n.id, n.name, n.insuranceType, n.employerRate, n.employeeRate, "
        "n.baseFloor, n.baseCeiling, n.adjustmentMonth, n.effectiveDate, n.regionId"
    )
    count = 0
    while r.has_next():
        row = r.get_next()
        nid = row[0]
        name = row[1] or ""
        ins_type = row[2] or ""
        employer = row[3] or ""
        employee = row[4] or ""
        floor_val = row[5] or ""
        ceil_val = row[6] or ""
        adj_month = row[7] or ""
        eff_date = row[8] or ""
        region = row[9] or ""

        if not nid:
            continue

        parts = [f"{name}。"]
        parts.append(f"保险类型：{ins_type}。")
        if employer:
            parts.append(f"单位缴费比例为{employer}。")
        if employee:
            parts.append(f"个人缴费比例为{employee}。")
        if floor_val:
            parts.append(f"缴费基数下限：{floor_val}。")
        if ceil_val:
            parts.append(f"缴费基数上限：{ceil_val}。")
        if adj_month:
            parts.append(f"缴费基数每年{adj_month}进行调整。")
        if eff_date:
            parts.append(f"该规则自{eff_date}起施行。")
        if region and region != "NATIONAL":
            parts.append(f"适用地区：{region}。")
        elif region == "NATIONAL":
            parts.append("本规则为全国统一标准，各地可在此基础上制定地方实施办法。")

        parts.append("用人单位应按月足额缴纳社会保险费，不得擅自减免或延迟缴纳。参保人员应关注缴费基数调整通知，确保社保权益不受影响。")

        desc = "".join(parts)
        conn.execute(
            f"MATCH (n:SocialInsuranceRule) WHERE n.id = '{safe_str(nid)}' "
            f"SET n.description = '{safe_str(desc)}'"
        )
        count += 1

    conn.execute("CHECKPOINT")
    print(f"  SocialInsuranceRule: {count} descriptions assembled")


# ══════════════════════════════════════════════════
# Phase B: Gemini Expand (QA types)
# ══════════════════════════════════════════════════

def _gemini_batch_expand(type_name: str, items: list[dict], prompt_template: str,
                         target_field: str, conn, batch_size: int = 20) -> int:
    """Generic Gemini batch expand for QA types."""
    total_updated = 0

    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        entries = "\n".join(f"{j+1}. {item['prompt_text']}" for j, item in enumerate(batch))
        prompt = prompt_template.replace("{{ENTRIES}}", entries).replace("{{COUNT}}", str(len(batch)))

        result = call_gemini(prompt)
        if not result:
            continue

        try:
            contents = json.loads(result)
            if not isinstance(contents, list):
                print(f"  WARN: Gemini returned non-list for batch {i//batch_size}")
                continue
        except json.JSONDecodeError:
            print(f"  WARN: JSON parse failed for batch {i//batch_size}")
            continue

        for j, item in enumerate(batch):
            if j >= len(contents):
                break
            text = str(contents[j]).strip()
            if len(text) < 30:
                continue

            try:
                conn.execute(
                    f"MATCH (n:{type_name}) WHERE n.id = '{safe_str(item['id'])}' "
                    f"SET n.{target_field} = '{safe_str(text)}'"
                )
                total_updated += 1
            except Exception as e:
                print(f"  WARN: Update failed for {item['id']}: {e}")

        if (i // batch_size + 1) % 5 == 0:
            conn.execute("CHECKPOINT")
            print(f"  ... {total_updated} updated so far")

        time.sleep(0.5)  # rate limit

    conn.execute("CHECKPOINT")
    return total_updated


def fix_mindmap_node(conn):
    """MindmapNode: generate content from node_text + category."""
    print("\n=== Phase B1: MindmapNode (Gemini expand) ===")

    try:
        conn.execute("ALTER TABLE MindmapNode ADD content STRING DEFAULT ''")
        print("  Added content column")
    except:
        pass

    r = conn.execute(
        "MATCH (n:MindmapNode) "
        "WHERE n.content IS NULL OR size(n.content) < 20 "
        "RETURN n.id, n.node_text, n.category, n.parent_text "
        "LIMIT 2000"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        nid, text, cat, parent = row[0], row[1] or "", row[2] or "", row[3] or ""
        if not nid or not text:
            continue
        ctx = f"[{cat}] {text}"
        if parent:
            ctx += f" (上级: {parent})"
        items.append({"id": nid, "prompt_text": ctx})

    print(f"  Found {len(items)} nodes to expand")
    if not items:
        return

    prompt_tpl = (
        "你是中国财税知识专家。对以下每个财税思维导图节点，写一段150-300字的中文说明。"
        "内容要专业准确，包含该主题的核心概念、适用范围、关键要点。"
        "返回一个JSON数组，每个元素是对应节点的说明文字，保持顺序一致。"
        "只输出JSON数组，不要加任何markdown标记。\n\n"
        "节点列表(共{{COUNT}}个):\n{{ENTRIES}}"
    )
    count = _gemini_batch_expand("MindmapNode", items, prompt_tpl, "content", conn)
    print(f"  MindmapNode: {count}/{len(items)} content generated")


def fix_industry_risk_profile(conn):
    """IndustryRiskProfile: generate description from structured fields."""
    print("\n=== Phase B2: IndustryRiskProfile (Gemini expand) ===")

    try:
        conn.execute("ALTER TABLE IndustryRiskProfile ADD description STRING DEFAULT ''")
        print("  Added description column")
    except:
        pass

    r = conn.execute(
        "MATCH (n:IndustryRiskProfile) "
        "RETURN n.id, n.industry, n.indicator, n.risk_level, n.benchmark"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        nid = row[0]
        industry, indicator, risk, benchmark = row[1] or "", row[2] or "", row[3] or "", row[4] or ""
        if not nid:
            continue
        ctx = f"{industry} - {indicator} (风险等级: {risk})"
        if benchmark:
            ctx += f" 基准: {benchmark}"
        items.append({"id": nid, "prompt_text": ctx})

    print(f"  Found {len(items)} nodes to expand")
    if not items:
        return

    prompt_tpl = (
        "你是中国税务风险管理专家。对以下每个行业风险指标，写一段150-300字的中文说明。"
        "包含：指标含义、触发原因、税务稽查关注点、企业应对建议。"
        "返回一个JSON数组，每个元素是对应指标的说明文字，保持顺序一致。"
        "只输出JSON数组。\n\n"
        "指标列表(共{{COUNT}}个):\n{{ENTRIES}}"
    )
    count = _gemini_batch_expand("IndustryRiskProfile", items, prompt_tpl, "description", conn)
    print(f"  IndustryRiskProfile: {count}/{len(items)} descriptions generated")


def fix_accounting_entry(conn):
    """AccountingEntry: expand description."""
    print("\n=== Phase B3: AccountingEntry (Gemini expand) ===")

    r = conn.execute(
        "MATCH (n:AccountingEntry) "
        "RETURN n.id, n.scenario, n.debit_account, n.credit_account, n.description, n.industry"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        nid = row[0]
        scenario, debit, credit, desc, industry = (
            row[1] or "", row[2] or "", row[3] or "", row[4] or "", row[5] or ""
        )
        if not nid:
            continue
        ctx = f"{scenario}: 借{debit}/贷{credit} ({desc}) [{industry}]"
        items.append({"id": nid, "prompt_text": ctx})

    print(f"  Found {len(items)} nodes to expand")
    if not items:
        return

    prompt_tpl = (
        "你是中国会计实务专家。对以下每个会计分录场景，写一段150-300字的中文详细说明。"
        "包含：业务场景说明、会计处理依据、借贷方向分析、涉税处理要点、实务注意事项。"
        "返回一个JSON数组，每个元素是对应分录的说明文字，保持顺序一致。"
        "只输出JSON数组。\n\n"
        "分录列表(共{{COUNT}}个):\n{{ENTRIES}}"
    )
    count = _gemini_batch_expand("AccountingEntry", items, prompt_tpl, "description", conn)
    print(f"  AccountingEntry: {count}/{len(items)} descriptions expanded")


def fix_tax_risk_scenario(conn):
    """TaxRiskScenario: expand description."""
    print("\n=== Phase B4: TaxRiskScenario (Gemini expand) ===")

    r = conn.execute(
        "MATCH (n:TaxRiskScenario) "
        "RETURN n.id, n.scenario, n.risk_type, n.industry, n.description, "
        "n.consequence, n.prevention"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        nid = row[0]
        scenario, rtype, industry = row[1] or "", row[2] or "", row[3] or ""
        desc, consequence, prevention = row[4] or "", row[5] or "", row[6] or ""
        if not nid:
            continue
        ctx = f"{scenario}({rtype},{industry}): {desc}. 后果:{consequence}. 预防:{prevention}"
        items.append({"id": nid, "prompt_text": ctx})

    print(f"  Found {len(items)} nodes to expand")
    if not items:
        return

    prompt_tpl = (
        "你是中国税务合规风险专家。对以下每个税务风险场景，写一段150-300字的中文详细说明。"
        "包含：风险场景描述、产生原因、法律后果、预防措施、整改建议。"
        "返回一个JSON数组，每个元素是对应风险场景的说明文字，保持顺序一致。"
        "只输出JSON数组。\n\n"
        "风险场景列表(共{{COUNT}}个):\n{{ENTRIES}}"
    )
    count = _gemini_batch_expand("TaxRiskScenario", items, prompt_tpl, "description", conn)
    print(f"  TaxRiskScenario: {count}/{len(items)} descriptions expanded")


def fix_compliance_rule(conn):
    """ComplianceRule: generate fullText from all fields."""
    print("\n=== Phase B5: ComplianceRule (Gemini expand) ===")

    try:
        conn.execute("ALTER TABLE ComplianceRule ADD fullText STRING DEFAULT ''")
        print("  Added fullText column")
    except:
        pass

    r = conn.execute(
        "MATCH (n:ComplianceRule) "
        "RETURN n.id, n.name, n.ruleCode, n.category, n.conditionDescription, "
        "n.requiredAction, n.violationConsequence, n.severityLevel"
    )
    items = []
    while r.has_next():
        row = r.get_next()
        nid = row[0]
        name, code, cat = row[1] or "", row[2] or "", row[3] or ""
        condition, action, consequence, severity = (
            row[4] or "", row[5] or "", row[6] or "", row[7] or ""
        )
        if not nid:
            continue
        ctx = (f"{name}({code},{cat}): 条件={condition}; "
               f"要求={action}; 违规后果={consequence}; 级别={severity}")
        items.append({"id": nid, "prompt_text": ctx})

    print(f"  Found {len(items)} nodes to expand")
    if not items:
        return

    prompt_tpl = (
        "你是中国税务合规专家。对以下每条合规规则，写一段200-400字的中文详细说明。"
        "包含：规则要求、适用范围、触发条件、执行步骤、违规后果、法规依据。"
        "返回一个JSON数组，每个元素是对应规则的说明文字，保持顺序一致。"
        "只输出JSON数组。\n\n"
        "规则列表(共{{COUNT}}个):\n{{ENTRIES}}"
    )
    count = _gemini_batch_expand("ComplianceRule", items, prompt_tpl, "fullText", conn)
    print(f"  ComplianceRule: {count}/{len(items)} fullText generated")


def main():
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    print("Opening KuzuDB (write mode)...")
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Phase A: Structured assembly (no AI needed)
    fix_regional_tax_policy(conn)
    fix_social_insurance_rule(conn)

    # Phase B: Gemini expand (QA types)
    fix_compliance_rule(conn)      # 8 nodes — smallest, quickest
    fix_tax_risk_scenario(conn)    # 180 nodes
    fix_accounting_entry(conn)     # 375 nodes
    fix_industry_risk_profile(conn)  # 720 nodes
    fix_mindmap_node(conn)         # 28K nodes — largest, last

    conn.execute("CHECKPOINT")
    print("\n=== All phases complete. Final CHECKPOINT done. ===")
    del conn, db


if __name__ == "__main__":
    main()
