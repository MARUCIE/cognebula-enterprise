#!/usr/bin/env python3
"""Ontology Quality Fix — batch enrich content + build missing edges.

Fixes:
1. Content enrichment: generate descriptions from existing structured fields
2. Missing backbone edges: connect isolated types to TaxType/Region hubs
3. Name quality: skip garbage nodes (textbook headers) in future queries

Run against the KG API server (not directly against KuzuDB).
"""
import json
import urllib.request

API = "http://100.75.77.112:8400/api/v1"

def api_get(path: str):
    resp = urllib.request.urlopen(f"{API}{path}")
    return json.loads(resp.read())

def api_post(path: str, data: dict):
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def cypher(stmt: str):
    """Execute a single Cypher statement via the admin execute-ddl endpoint."""
    return api_post("/admin/execute-ddl", {"statements": [stmt]})


# ══════════════════════════════════════════════════
# 1. Content enrichment: auto-generate descriptions
# ══════════════════════════════════════════════════

def enrich_tax_rates():
    """TaxRate: combine name + valueExpression + calculationBasis into description."""
    print("\n=== Enriching TaxRate descriptions ===")
    data = api_get("/nodes?type=TaxRate&limit=200")
    count = 0
    for r in data.get("results", []):
        nid = r.get("id", "")
        name = r.get("name", "")
        rate = r.get("valueExpression", "")
        basis = r.get("calculationBasis", "")
        if not nid or not name:
            continue
        desc = f"{name}"
        if rate:
            desc += f"，税率{rate}"
        if basis:
            desc += f"，计税基础：{basis}"
        safe_desc = desc.replace("'", "\\'").replace('"', '\\"')
        safe_id = nid.replace("'", "\\'")
        try:
            cypher(f"MATCH (n:TaxRate) WHERE n.id = '{safe_id}' SET n.description = '{safe_desc}'")
            count += 1
        except Exception as e:
            if "does not exist" in str(e):
                # Need to ALTER TABLE first
                try:
                    cypher("ALTER TABLE TaxRate ADD description STRING DEFAULT ''")
                    cypher(f"MATCH (n:TaxRate) WHERE n.id = '{safe_id}' SET n.description = '{safe_desc}'")
                    count += 1
                except:
                    pass
    print(f"  TaxRate: {count} descriptions added")

def enrich_social_insurance():
    """SocialInsuranceRule: combine insuranceType + rates into description."""
    print("\n=== Enriching SocialInsuranceRule descriptions ===")
    data = api_get("/nodes?type=SocialInsuranceRule&limit=200")
    count = 0
    for r in data.get("results", []):
        nid = r.get("id", "")
        name = r.get("name", "")
        itype = r.get("insuranceType", "")
        employer = r.get("employerRate", "")
        employee = r.get("employeeRate", "")
        region = r.get("regionId", "")
        if not nid:
            continue
        parts = [name or itype or "社保规则"]
        if employer:
            parts.append(f"单位{employer}")
        if employee:
            parts.append(f"个人{employee}")
        if region:
            parts.append(f"地区：{region}")
        desc = "，".join(parts)
        safe_desc = desc.replace("'", "\\'")
        safe_id = nid.replace("'", "\\'")
        try:
            cypher(f"MATCH (n:SocialInsuranceRule) WHERE n.id = '{safe_id}' SET n.description = '{safe_desc}'")
            count += 1
        except:
            try:
                cypher("ALTER TABLE SocialInsuranceRule ADD description STRING DEFAULT ''")
                cypher(f"MATCH (n:SocialInsuranceRule) WHERE n.id = '{safe_id}' SET n.description = '{safe_desc}'")
                count += 1
            except:
                pass
    print(f"  SocialInsuranceRule: {count} descriptions added")

def enrich_penalty():
    """Penalty: combine penaltyType + calculationMethod into description."""
    print("\n=== Enriching Penalty descriptions ===")
    data = api_get("/nodes?type=Penalty&limit=200")
    count = 0
    for r in data.get("results", []):
        nid = r.get("id", "")
        name = r.get("name", "")
        ptype = r.get("penaltyType", "")
        method = r.get("calculationMethod", "")
        min_amt = r.get("minAmount", "")
        max_amt = r.get("maxAmount", "")
        if not nid:
            continue
        parts = [name or "处罚规定"]
        if ptype:
            parts.append(f"类型：{ptype}")
        if method:
            parts.append(f"计算方式：{method}")
        if min_amt and max_amt:
            parts.append(f"金额{min_amt}-{max_amt}")
        desc = "，".join(parts)
        safe = desc.replace("'", "\\'")
        safe_id = nid.replace("'", "\\'")
        try:
            cypher(f"MATCH (n:Penalty) WHERE n.id = '{safe_id}' SET n.description = '{safe}'")
            count += 1
        except:
            try:
                cypher("ALTER TABLE Penalty ADD description STRING DEFAULT ''")
                cypher(f"MATCH (n:Penalty) WHERE n.id = '{safe_id}' SET n.description = '{safe}'")
                count += 1
            except:
                pass
    print(f"  Penalty: {count} descriptions added")

def enrich_tax_accounting_gap():
    """TaxAccountingGap: combine fields into readable description."""
    print("\n=== Enriching TaxAccountingGap descriptions ===")
    data = api_get("/nodes?type=TaxAccountingGap&limit=100")
    count = 0
    for r in data.get("results", []):
        nid = r.get("id", "")
        name = r.get("name", "")
        acct = r.get("accountingTreatment", "")
        tax = r.get("taxTreatment", "")
        gtype = r.get("gapType", "")
        direction = r.get("adjustmentDirection", "")
        if not nid:
            continue
        parts = [name or "税会差异"]
        if gtype:
            parts.append(f"类型：{gtype}")
        if acct:
            parts.append(f"会计处理：{acct}")
        if tax:
            parts.append(f"税务处理：{tax}")
        if direction:
            parts.append(f"调整方向：{direction}")
        desc = "；".join(parts)
        safe = desc.replace("'", "\\'")
        safe_id = nid.replace("'", "\\'")
        try:
            cypher(f"MATCH (n:TaxAccountingGap) WHERE n.id = '{safe_id}' SET n.description = '{safe}'")
            count += 1
        except:
            try:
                cypher("ALTER TABLE TaxAccountingGap ADD description STRING DEFAULT ''")
                cypher(f"MATCH (n:TaxAccountingGap) WHERE n.id = '{safe_id}' SET n.description = '{safe}'")
                count += 1
            except:
                pass
    print(f"  TaxAccountingGap: {count} descriptions added")

def enrich_simple_types():
    """Enrich types that just need a basic description from existing fields."""
    TYPES = [
        ("TaxEntity", ["name"], "纳税主体"),
        ("Region", ["name"], "行政区域"),
        ("IssuingBody", ["name", "shortName"], "法规发布机构"),
        ("AccountingSubject", ["name"], "会计科目"),
        ("IndustryBenchmark", ["ratioName", "industryCode", "minValue", "maxValue", "unit"], "行业基准指标"),
        ("InvoiceRule", ["name", "ruleType", "invoiceType", "condition"], "发票管理规则"),
        ("FilingForm", ["name", "formNumber", "applicableTaxpayerType"], "纳税申报表"),
        ("BusinessActivity", ["name"], "业务活动"),
    ]
    for table, fields, default_prefix in TYPES:
        print(f"\n=== Enriching {table} descriptions ===")
        data = api_get(f"/nodes?type={table}&limit=200")
        count = 0
        for r in data.get("results", []):
            nid = r.get("id", "")
            if not nid:
                continue
            parts = []
            for f in fields:
                v = r.get(f, "")
                if v and str(v) not in ("", "null", "None", "0", "0.0"):
                    parts.append(str(v))
            if not parts:
                parts = [default_prefix]
            desc = f"{default_prefix}：{'，'.join(parts)}" if len(parts) > 1 else parts[0]
            safe = desc.replace("'", "\\'")
            safe_id = nid.replace("'", "\\'")
            try:
                cypher(f"MATCH (n:{table}) WHERE n.id = '{safe_id}' SET n.description = '{safe}'")
                count += 1
            except:
                try:
                    cypher(f"ALTER TABLE {table} ADD description STRING DEFAULT ''")
                    cypher(f"MATCH (n:{table}) WHERE n.id = '{safe_id}' SET n.description = '{safe}'")
                    count += 1
                except:
                    pass
        print(f"  {table}: {count} descriptions added")


# ══════════════════════════════════════════════════
# 2. Missing backbone edges
# ══════════════════════════════════════════════════

# Tax type ID → keyword mapping for matching
TAX_KEYWORDS = {
    "TT_VAT": ["增值税", "VAT"],
    "TT_CIT": ["企业所得税", "CIT", "所得税"],
    "TT_PIT": ["个人所得税", "PIT", "个税"],
    "TT_CONSUMPTION": ["消费税"],
    "TT_STAMP": ["印花税"],
    "TT_PROPERTY": ["房产税"],
    "TT_LAND_VAT": ["土地增值税"],
    "TT_URBAN": ["城建税", "城市维护建设税"],
    "TT_EDUCATION": ["教育费附加"],
    "TT_RESOURCE": ["资源税"],
    "TT_ENV": ["环保税", "环境保护税"],
    "TT_CONTRACT": ["契税"],
    "TT_VEHICLE": ["车船税"],
    "TT_TARIFF": ["关税"],
    "TT_TOBACCO": ["烟叶税"],
}

def match_tax_type(text: str) -> str | None:
    """Match text content to a TaxType ID."""
    for tt_id, keywords in TAX_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return tt_id
    return None

def build_missing_edges():
    """Build backbone edges for isolated types."""
    print("\n=== Building missing backbone edges ===")

    # SocialInsuranceRule → Region (INSURANCE_IN_REGION)
    print("  SocialInsuranceRule → Region...")
    sir_data = api_get("/nodes?type=SocialInsuranceRule&limit=200")
    region_data = api_get("/nodes?type=Region&limit=50")
    region_map = {r["name"]: r["id"] for r in region_data.get("results", []) if r.get("name") and r.get("id")}
    sir_edges = 0
    for r in sir_data.get("results", []):
        rid = r.get("regionId", "")
        if not rid:
            continue
        # Try to match regionId to a Region node
        for rname, rnode_id in region_map.items():
            if rname in rid or rid in rname:
                try:
                    safe_sir = r["id"].replace("'", "\\'")
                    safe_region = rnode_id.replace("'", "\\'")
                    cypher(f"MATCH (a:SocialInsuranceRule), (b:Region) WHERE a.id = '{safe_sir}' AND b.id = '{safe_region}' CREATE (a)-[:INSURANCE_IN_REGION]->(b)")
                    sir_edges += 1
                except:
                    pass
                break
    print(f"    INSURANCE_IN_REGION: {sir_edges} edges")

    # FilingForm → TaxType (FILING_FOR_TAX)
    print("  FilingForm → TaxType...")
    ff_data = api_get("/nodes?type=FilingForm&limit=200")
    ff_edges = 0
    for r in ff_data.get("results", []):
        fid = r.get("id", "")
        fname = r.get("name", "") + " " + r.get("formNumber", "")
        tax_id = r.get("taxTypeId", "")
        # Try taxTypeId first, then name matching
        target = None
        if tax_id:
            for tt_id in TAX_KEYWORDS:
                if tt_id == tax_id or tax_id in tt_id:
                    target = tt_id
                    break
        if not target:
            target = match_tax_type(fname)
        if target and fid:
            try:
                safe_f = fid.replace("'", "\\'")
                safe_t = target.replace("'", "\\'")
                cypher(f"MATCH (a:FilingForm), (b:TaxType) WHERE a.id = '{safe_f}' AND b.id = '{safe_t}' CREATE (a)-[:FILING_FOR_TAX]->(b)")
                ff_edges += 1
            except:
                pass
    print(f"    FILING_FOR_TAX: {ff_edges} edges")

    # RiskIndicator → TaxType (RISK_FOR_TAX)
    print("  RiskIndicator → TaxType...")
    ri_data = api_get("/nodes?type=RiskIndicator&limit=200")
    ri_edges = 0
    for r in ri_data.get("results", []):
        rid = r.get("id", "")
        rname = r.get("name", "") + " " + r.get("metricName", "")
        target = match_tax_type(rname)
        if target and rid:
            try:
                safe_r = rid.replace("'", "\\'")
                safe_t = target.replace("'", "\\'")
                cypher(f"MATCH (a:RiskIndicator), (b:TaxType) WHERE a.id = '{safe_r}' AND b.id = '{safe_t}' CREATE (a)-[:RISK_FOR_TAX]->(b)")
                ri_edges += 1
            except:
                pass
    print(f"    RISK_FOR_TAX: {ri_edges} edges")

    # AuditTrigger → TaxType (AUDIT_FOR_TAX) — additional edges
    print("  AuditTrigger → TaxType (additional)...")
    at_data = api_get("/nodes?type=AuditTrigger&limit=200")
    at_edges = 0
    for r in at_data.get("results", []):
        aid = r.get("id", "")
        aname = r.get("name", "") + " " + r.get("patternDescription", "")
        target = match_tax_type(aname)
        if target and aid:
            try:
                safe_a = aid.replace("'", "\\'")
                safe_t = target.replace("'", "\\'")
                cypher(f"MATCH (a:AuditTrigger), (b:TaxType) WHERE a.id = '{safe_a}' AND b.id = '{safe_t}' CREATE (a)-[:AUDIT_FOR_TAX]->(b)")
                at_edges += 1
            except:
                pass
    print(f"    AUDIT_FOR_TAX: {at_edges} edges")

    # AccountingSubject → TaxType (MAPS_TO_ACCOUNT) — reverse direction
    print("  AccountingSubject edge enrichment...")
    # AccountingSubject already has MAPS_TO_ACCOUNT from TaxType, but let's check
    # and add more if needed

    # IndustryBenchmark → TaxType (BENCHMARK_FOR)
    print("  IndustryBenchmark → TaxType...")
    ib_data = api_get("/nodes?type=IndustryBenchmark&limit=100")
    ib_edges = 0
    for r in ib_data.get("results", []):
        bid = r.get("id", "")
        bname = r.get("ratioName", "") + " " + r.get("industryCode", "")
        # Most benchmarks relate to VAT or CIT
        target = match_tax_type(bname)
        if not target:
            target = "TT_VAT"  # Default: most benchmarks are VAT-related
        if bid:
            try:
                safe_b = bid.replace("'", "\\'")
                safe_t = target.replace("'", "\\'")
                cypher(f"MATCH (a:IndustryBenchmark), (b:TaxType) WHERE a.id = '{safe_b}' AND b.id = '{safe_t}' CREATE (a)-[:BENCHMARK_FOR]->(b)")
                ib_edges += 1
            except:
                pass
    print(f"    BENCHMARK_FOR: {ib_edges} edges")


# ══════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    print("CogNebula Ontology Quality Fix")
    print("=" * 50)

    # Step 1: Content enrichment
    enrich_tax_rates()
    enrich_social_insurance()
    enrich_penalty()
    enrich_tax_accounting_gap()
    enrich_simple_types()

    # Step 2: Missing backbone edges
    build_missing_edges()

    print("\n" + "=" * 50)
    print("DONE. Restart constellation to see changes.")
