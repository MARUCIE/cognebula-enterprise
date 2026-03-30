#!/usr/bin/env python3
"""Build v4.1 ontology backbone edges.

Connects the 19 TaxType hub nodes to all other v4.1 types through
semantically correct ontology edges. Domain knowledge encoded as rules.

Run: python3 scripts/build_backbone_edges.py
"""
import json
import urllib.request

API = "http://100.75.77.112:8400/api/v1"


def execute(statements: list[str]) -> dict:
    payload = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(
        f"{API}/admin/execute-ddl", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_nodes(table: str, limit: int = 200) -> list[dict]:
    url = f"{API}/nodes?type={table}&limit={limit}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read()).get("results", [])


def safe(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


# ═══════════════════════════════════════════════════
# Tax type → keyword mapping (for matching node IDs/names to tax types)
# ═══════════════════════════════════════════════════
TAX_KEYWORDS = {
    "TT_VAT": ["增值税", "VAT", "vat", "_VAT_", "进项", "销项"],
    "TT_CIT": ["企业所得税", "CIT", "cit", "_CIT_", "HNTE", "hnte", "小微", "小型微利", "research_deduction"],
    "TT_PIT": ["个人所得税", "PIT", "pit", "_PIT_", "综合所得", "工资薪金"],
    "TT_CONSUMPTION": ["消费税", "CONSUMPTION", "consumption", "卷烟", "白酒", "啤酒", "化妆品", "成品油"],
    "TT_TARIFF": ["关税", "TARIFF", "tariff", "进口", "HS编码"],
    "TT_URBAN": ["城建税", "城市维护建设税", "URBAN", "urban"],
    "TT_EDUCATION": ["教育费附加", "education"],
    "TT_LOCAL_EDU": ["地方教育附加", "local_edu"],
    "TT_RESOURCE": ["资源税", "RESOURCE", "resource", "原油", "天然气", "煤", "稀土"],
    "TT_LAND_VAT": ["土地增值税", "LAND_VAT", "land_vat"],
    "TT_PROPERTY": ["房产税", "PROPERTY", "property"],
    "TT_LAND_USE": ["土地使用税", "LANDUSE", "landuse"],
    "TT_VEHICLE": ["车船税", "VEHICLE", "vehicle", "车辆购置税"],
    "TT_STAMP": ["印花税", "STAMP", "stamp"],
    "TT_CONTRACT": ["契税", "DEED", "deed", "CONTRACT"],
    "TT_CULTIVATED": ["耕地占用税", "CULTIVATED", "cultivated"],
    "TT_TOBACCO": ["烟叶税", "TOBACCO", "tobacco"],
    "TT_TONNAGE": ["船舶吨税", "TONNAGE", "tonnage"],
    "TT_ENV": ["环保税", "环境保护税", "ENV", "env"],
}


def match_tax_type(node_id: str, name: str) -> list[str]:
    """Return list of matching TaxType IDs for a given node."""
    matches = []
    combined = f"{node_id} {name}"
    for tt_id, keywords in TAX_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            matches.append(tt_id)
    return matches


def build_edge(from_table: str, from_id: str, edge_type: str, to_table: str, to_id: str) -> str:
    """Build a CREATE edge Cypher statement."""
    return (
        f"MATCH (a:{from_table}), (b:{to_table}) "
        f"WHERE a.id = '{safe(from_id)}' AND b.id = '{safe(to_id)}' "
        f"CREATE (a)-[:{edge_type}]->(b)"
    )


# ═══════════════════════════════════════════════════
# Edge generators
# ═══════════════════════════════════════════════════

def gen_incentive_to_taxtype():
    """TaxIncentive -[INCENTIVE_FOR_TAX]-> TaxType."""
    print("=== TaxIncentive → TaxType (INCENTIVE_FOR_TAX) ===")
    nodes = fetch_nodes("TaxIncentive", 120)
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        matches = match_tax_type(nid, name)
        if not matches:
            if "所得" in name:
                matches = ["TT_CIT"]
            elif "购置税" in name:
                matches = ["TT_VEHICLE"]
            else:
                matches = ["TT_VAT"]
        for tt in matches:
            stmts.append(build_edge("TaxIncentive", nid, "INCENTIVE_FOR_TAX", "TaxType", tt))
    return stmts


def gen_compliance_to_taxtype():
    """ComplianceRule -[RULE_FOR_TAX]-> TaxType."""
    print("=== ComplianceRule → TaxType (RULE_FOR_TAX) ===")
    rules = {
        "CR_TAX_REG_30D": ["TT_VAT", "TT_CIT"],
        "CR_VAT_MONTHLY": ["TT_VAT"],
        "CR_CIT_QUARTERLY": ["TT_CIT"],
        "CR_CIT_ANNUAL": ["TT_CIT"],
        "CR_PIT_ANNUAL": ["TT_PIT"],
        "CR_THREE_FLOWS": ["TT_VAT"],
        "CR_INVOICE_AUTH": ["TT_VAT"],
    }
    stmts = []
    for cr_id, tt_ids in rules.items():
        for tt in tt_ids:
            stmts.append(build_edge("ComplianceRule", cr_id, "RULE_FOR_TAX", "TaxType", tt))
    return stmts


def gen_rate_to_taxtype():
    """TaxRate -[APPLIES_TO_TAX]-> TaxType."""
    print("=== TaxRate → TaxType (APPLIES_TO_TAX) ===")
    url = f"{API}/nodes?type=TaxRate&limit=100&q=%E7%A8%8E"
    with urllib.request.urlopen(url, timeout=15) as resp:
        nodes = json.loads(resp.read()).get("results", [])
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        matches = match_tax_type(nid, name)
        for tt in matches:
            stmts.append(build_edge("TaxRate", nid, "APPLIES_TO_TAX", "TaxType", tt))
    return stmts


def gen_gap_to_taxtype():
    """TaxAccountingGap -[GAP_FOR_TAX]-> TaxType."""
    print("=== TaxAccountingGap → TaxType (GAP_FOR_TAX) ===")
    nodes = fetch_nodes("TaxAccountingGap", 60)
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        if "增值税" in name or "视同销售" in name or "进项" in name:
            stmts.append(build_edge("TaxAccountingGap", nid, "GAP_FOR_TAX", "TaxType", "TT_VAT"))
        stmts.append(build_edge("TaxAccountingGap", nid, "GAP_FOR_TAX", "TaxType", "TT_CIT"))
    return stmts


def gen_invoice_to_taxtype():
    """InvoiceRule -[INVOICE_FOR_TAX]-> TaxType."""
    print("=== InvoiceRule → TaxType (INVOICE_FOR_TAX) ===")
    nodes = fetch_nodes("InvoiceRule", 50)
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        stmts.append(build_edge("InvoiceRule", nid, "INVOICE_FOR_TAX", "TaxType", "TT_VAT"))
    return stmts


def gen_audit_to_taxtype():
    """AuditTrigger -[AUDIT_FOR_TAX]-> TaxType."""
    print("=== AuditTrigger → TaxType (AUDIT_FOR_TAX) ===")
    nodes = fetch_nodes("AuditTrigger", 50)
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        matches = match_tax_type(nid, name)
        if not matches:
            matches = ["TT_VAT", "TT_CIT"]
        for tt in matches:
            stmts.append(build_edge("AuditTrigger", nid, "AUDIT_FOR_TAX", "TaxType", tt))
    return stmts


def gen_risk_to_taxtype():
    """RiskIndicator -[RISK_FOR_TAX]-> TaxType."""
    print("=== RiskIndicator → TaxType (RISK_FOR_TAX) ===")
    nodes = fetch_nodes("RiskIndicator", 50)
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        matches = match_tax_type(nid, name)
        if not matches:
            matches = ["TT_VAT", "TT_CIT"]
        for tt in matches:
            stmts.append(build_edge("RiskIndicator", nid, "RISK_FOR_TAX", "TaxType", tt))
    return stmts


def gen_filing_to_taxtype():
    """FilingForm -[FILING_FOR_TAX]-> TaxType."""
    print("=== FilingForm → TaxType (FILING_FOR_TAX) ===")
    nodes = fetch_nodes("FilingForm", 50)
    stmts = []
    for n in nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        matches = match_tax_type(nid, name)
        if not matches:
            matches = ["TT_VAT"]
        for tt in matches:
            stmts.append(build_edge("FilingForm", nid, "FILING_FOR_TAX", "TaxType", tt))
    return stmts


def gen_incentive_stacking():
    """TaxIncentive -[STACKS_WITH]-> TaxIncentive (known stackable pairs)."""
    print("=== TaxIncentive ↔ TaxIncentive (STACKS_WITH) ===")
    STACKABLE_PAIRS = [
        ("INCE_HNTE_CIT", "INCE_RD_SUPER_DEDUCT"),       # 高新+研发加计可叠加
        ("INCE_HNTE_CIT", "INCE_CIT_TECH_TRANSFER"),     # 高新+技术转让可叠加
        ("INCE_SMALL_PROFIT_CIT", "INCE_RD_SUPER_DEDUCT"),  # 小微+研发加计
        ("INCE_VAT_SMALL_EXEMPT", "INCE_VAT_SMALL_1PCT"),   # 免征和1%不叠加但替代
        ("INCE_HNTE_CIT", "INCE_CIT_DISABLED_SALARY"),   # 高新+残疾人工资加计
        ("INCE_SOFTWARE_VAT", "INCE_CIT_SOFTWARE_EXEMPT"),  # 软件VAT退+CIT免
    ]
    stmts = []
    for a, b in STACKABLE_PAIRS:
        stmts.append(build_edge("TaxIncentive", a, "STACKS_WITH", "TaxIncentive", b))
    return stmts


def gen_incentive_excludes():
    """TaxIncentive -[EXCLUDES]-> TaxIncentive (mutually exclusive pairs)."""
    print("=== TaxIncentive ↔ TaxIncentive (EXCLUDES) ===")
    EXCLUSIVE_PAIRS = [
        ("INCE_HNTE_CIT", "INCE_CIT_WEST_DEV"),          # 高新15%和西部15%不叠加
        ("INCE_HNTE_CIT", "INCE_CIT_HAINAN"),            # 高新15%和海南15%不叠加
        ("INCE_SMALL_PROFIT_CIT", "INCE_HNTE_CIT"),      # 小微和高新不叠加
        ("INCE_VAT_SMALL_EXEMPT", "INCE_VAT_SMALL_1PCT"),  # 免征和1%二选一
    ]
    stmts = []
    for a, b in EXCLUSIVE_PAIRS:
        stmts.append(build_edge("TaxIncentive", a, "EXCLUDES", "TaxIncentive", b))
    return stmts


# ═══════════════════════════════════════════════════
# Execute all generators
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    generators = [
        gen_incentive_to_taxtype,   # TaxIncentive → TaxType (INCENTIVE_FOR_TAX)
        gen_compliance_to_taxtype,  # ComplianceRule → TaxType (RULE_FOR_TAX)
        gen_rate_to_taxtype,        # TaxRate → TaxType (APPLIES_TO_TAX)
        gen_gap_to_taxtype,         # TaxAccountingGap → TaxType (GAP_FOR_TAX)
        gen_invoice_to_taxtype,     # InvoiceRule → TaxType (INVOICE_FOR_TAX)
        gen_audit_to_taxtype,       # AuditTrigger → TaxType (AUDIT_FOR_TAX)
        gen_risk_to_taxtype,        # RiskIndicator → TaxType (RISK_FOR_TAX)
        gen_filing_to_taxtype,      # FilingForm → TaxType (FILING_FOR_TAX)
        gen_incentive_stacking,     # TaxIncentive ↔ TaxIncentive (STACKS_WITH)
        gen_incentive_excludes,     # TaxIncentive ↔ TaxIncentive (EXCLUDES)
    ]

    total_ok = 0
    total_err = 0
    total_skip = 0

    for gen in generators:
        stmts = gen()
        if not stmts:
            print(f"  (no statements)")
            continue
        # Execute in batches of 20
        for i in range(0, len(stmts), 20):
            batch = stmts[i:i+20]
            result = execute(batch)
            ok = result.get("ok", 0)
            skip = result.get("skipped", 0)
            err = result.get("errors", 0)
            total_ok += ok
            total_err += err
            total_skip += skip
            if err:
                for r in result.get("results", []):
                    if r["status"] == "ERROR":
                        print(f"    ERROR: {r['reason'][:80]}")
        print(f"  Generated: {len(stmts)} statements")

    print(f"\n=== TOTAL: {total_ok} OK, {total_skip} skipped, {total_err} errors ===")
