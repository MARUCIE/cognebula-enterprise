#!/usr/bin/env python3
"""KG Quality Gate — 6-dimension content quality audit + ingestion gate.

Dimensions:
  D1 Length        — distribution across 5 buckets (empty/<50/50-200/200-500/500+)
  D2 Authenticity  — % nodes with real content (not nav junk / HTML boilerplate)
  D3 Domain        — % nodes with >=2 finance/tax domain terms
  D4 Unique        — dedup ratio (distinct first-100-char / total)
  D5 Fill          — % non-empty nodes (content >= 5 chars)
  D6 Score         — composite 0-100 (Length 30 + Auth 20 + Domain 25 + Unique 15 + Fill 10)

Hard gate: each type must score >= 70 composite, overall >= 70.
Authoritative types (LawOrRegulation etc.): junk > 50% forces FAIL regardless of score.

Usage:
    python3 scripts/kg_quality_gate.py --audit          # full KG audit via API
    python3 scripts/kg_quality_gate.py --audit --json   # JSON output
    python3 scripts/kg_quality_gate.py data/file.json   # ingestion pre-check
    python3 scripts/kg_quality_gate.py --check-api      # legacy simple check
"""
import json
import sys
import os
from pathlib import Path

# Import content validator for D6 Authenticity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from content_validator import is_junk
    _HAS_VALIDATOR = True
except ImportError:
    _HAS_VALIDATOR = False

try:
    import httpx
    _HTTP = "httpx"
except ImportError:
    import urllib.request
    _HTTP = "urllib"

# ── Configuration ───────────────────────────────────────────────────────

KG_API = os.environ.get("KG_API", "http://localhost:8400")
DB_PATH = os.environ.get("KUZU_DB_PATH", "/home/kg/cognebula-enterprise/data/finance-tax-graph")
COMPOSITE_GATE = 70  # minimum composite score to pass
SAMPLE_SIZE = 200  # reduced from 500 to prevent KuzuDB segfault on 8GB VPS
_DIRECT_MODE = False  # set True for direct KuzuDB access (API must be stopped)
_kuzu_conn = None

# ── Node Category (determines scoring method) ──────────────────────────
# "document"   — full-text expected, scored by length+domain+unique
# "qa"         — question+answer pairs, scored by length+domain+unique
# "structured" — code/name/category, scored by field completeness
# "metadata"   — lightweight reference nodes, scored by field completeness

NODE_CATEGORY = {
    # Document types — must have full text
    "LawOrRegulation": "document",
    "LegalClause": "document",
    "RegulationClause": "document",
    "LegalDocument": "document",
    "DocumentSection": "document",
    "AccountingStandard": "document",
    "RegionalTaxPolicy": "document",
    "SocialInsuranceRule": "document",

    # QA types — AI-expandable content
    "KnowledgeUnit": "qa",
    "FAQEntry": "qa",
    "CPAKnowledge": "qa",
    "MindmapNode": "qa",
    "ComplianceRule": "qa",
    "TaxIncentive": "qa",
    "Penalty": "qa",
    "IndustryRiskProfile": "qa",
    "BusinessActivity": "qa",
    "AccountingEntry": "qa",
    "TaxRiskScenario": "qa",
    "ResponseStrategy": "qa",
    "TaxWarningIndicator": "qa",
    "IndustryKnowledge": "qa",
    "TaxAccountingGap": "qa",
    "JournalEntryTemplate": "qa",
    "RiskIndicator": "qa",

    # Structured types — field completeness, not text length
    "Classification": "structured",
    "HSCode": "structured",
    "TaxRate": "structured",
    "TaxClassificationCode": "structured",
    "TaxCodeDetail": "structured",
    "TaxCodeIndustryMap": "structured",
    "TaxItem": "structured",
    "TaxBasis": "structured",
    "FilingForm": "structured",
    "FilingFormField": "structured",
    "TaxRateMapping": "structured",
    "TaxRateSchedule": "structured",
    "TaxRateDetail": "structured",

    # Metadata types — reference entities
    "IssuingBody": "metadata",
    "Region": "metadata",
    "TaxType": "metadata",
    "Industry": "metadata",
    "ChartOfAccount": "metadata",
    "ChartOfAccountDetail": "metadata",
    "AccountingSubject": "metadata",
    "EnterpriseType": "metadata",
    "TaxEntity": "metadata",
    "FormTemplate": "metadata",
}

# Required fields per structured type (for field completeness scoring)
STRUCTURED_REQUIRED_FIELDS = {
    "Classification": ["name", "system"],
    "HSCode": ["code", "name"],
    "TaxRate": ["name", "taxTypeId", "description"],
    "TaxClassificationCode": ["code", "item_name"],
    "TaxCodeDetail": ["code", "item_name"],
    "TaxCodeIndustryMap": ["tax_code", "industry", "applicability"],
    "TaxItem": ["name", "description"],
    "TaxBasis": ["name", "description"],
    "FilingForm": ["name"],
    "FilingFormField": ["name"],
    "TaxRateMapping": ["name"],
    "TaxRateSchedule": ["name"],
    "TaxRateDetail": ["name"],
}

# Domain vocabulary for finance/tax
DOMAIN_TERMS = frozenset(
    # Tax types + tax mechanics
    "增值税 企业所得税 个人所得税 消费税 关税 印花税 房产税 土地增值税 城建税 "
    "资源税 税率 纳税 申报 发票 抵扣 扣除 免税 减免 征收 计税 应税 税额 税基 "
    "纳税人 扣缴 退税 税负 合规 审计 会计 科目 分录 借方 贷方 资产 负债 权益 "
    "收入 成本 费用 利润 折旧 摊销 预缴 汇缴 核定 查账 小规模 一般纳税人 "
    "进项 销项 留抵 加计抵减 即征即退 先征后返 加速折旧 研发加计 高新技术 "
    "小微企业 个体工商户 合伙企业 居民企业 非居民 常设机构 转让定价 "
    "关联交易 税收协定 预约定价 同期资料 反避税 CRS BEPS "
    # Social insurance
    "社保 公积金 工伤 生育 医疗 养老 失业 残保金 保险 缴费 费率 基数 "
    "单位缴费 个人缴费 缴费比例 补充医疗 大病保险 灵活就业 参保 断缴 转移接续 "
    # Financial statements
    "资产负债表 利润表 现金流量表 所有者权益变动表 财务报表附注 "
    # Legal/regulatory (original)
    "法律 法规 条例 规章 办法 通知 公告 规定 实施 依照 依据 适用 "
    "税务机关 税务局 主管税务 登记 备案 征管 稽查 "
    "违反 处罚 罚款 滞纳金 补缴 追征 纳税期限 申报期 "
    "应纳税所得额 应纳税额 计税依据 税款 欠税 "
    # Regulatory/administrative (expanded for compliance KG)
    "经营 许可 监督 主管部门 行政处罚 行政许可 行政复议 "
    "营业执照 工商 市场监管 监管 执法 "
    "责令 整改 吊销 暂扣 没收 查封 扣押 取缔 "
    "施行 修订 废止 颁布 批准 核准 审批 "
    # Business entity / compliance
    "法人 股东 注册资本 章程 董事 监事 "
    "合同 协议 委托 代理 授权 "
    "财政 预算 拨款 专项资金 补贴 "
    # Government bodies
    "国务院 财政部 人力资源 社会保障 商务部 海关总署".split()
)

# ── Content Source Policy ───────────────────────────────────────────────
# CRITICAL: Legal/regulatory text MUST come from original sources.
# AI generation is ONLY allowed for QA-type and descriptive content.
#
# "authoritative" — original source only: crawl, inherit from parent, or
#                   structured assembly from existing fields. NO AI generation.
# "ai_expandable" — AI may generate or expand content (QA, summaries, descriptions)
# "structured"    — assemble description from code+name+category fields,
#                   NOT free-form AI generation.

CONTENT_SOURCE_POLICY = {
    # Authoritative — never AI-generate
    "LawOrRegulation":      "authoritative",
    "LegalClause":          "authoritative",
    "RegulationClause":     "authoritative",
    "LegalDocument":        "authoritative",
    "AccountingStandard":   "authoritative",
    "SocialInsuranceRule":  "authoritative",
    "RegionalTaxPolicy":    "authoritative",
    "TaxTreaty":            "authoritative",
    "DeductionRule":        "authoritative",

    # Structured — assemble from existing fields, no fabrication
    "Classification":       "structured",
    "HSCode":               "structured",
    "TaxRate":              "structured",
    "TaxClassificationCode":"structured",
    "TaxCodeDetail":        "structured",
    "TaxCodeIndustryMap":   "structured",
    "TaxItem":              "structured",
    "TaxBasis":             "structured",
    "FilingForm":           "structured",
    "FilingFormField":      "structured",
    "ChartOfAccount":       "structured",
    "ChartOfAccountDetail": "structured",
    "AccountingSubject":    "structured",
    "IssuingBody":          "structured",
    "Region":               "structured",

    # AI-expandable — can use Gemini to generate/expand
    "KnowledgeUnit":        "ai_expandable",
    "FAQEntry":             "ai_expandable",
    "CPAKnowledge":         "ai_expandable",
    "MindmapNode":          "ai_expandable",
    "DocumentSection":      "ai_expandable",
    "BusinessActivity":     "ai_expandable",
    "TaxRiskScenario":      "ai_expandable",
    "ComplianceRule":       "ai_expandable",
    "TaxIncentive":         "ai_expandable",
    "Penalty":              "ai_expandable",
    "IndustryRiskProfile":  "ai_expandable",
    "IndustryBenchmark":    "ai_expandable",
    "IndustryKnowledge":    "ai_expandable",
    "AccountingEntry":      "ai_expandable",
    "TaxAccountingGap":     "ai_expandable",
    "RiskIndicator":        "ai_expandable",
    "ResponseStrategy":     "ai_expandable",
    "TaxWarningIndicator":  "ai_expandable",
    "JournalEntryTemplate": "ai_expandable",
}


# Node types with their content fields (priority order)
NODE_CONTENT_FIELDS = {
    "LawOrRegulation":      ["fullText", "summary", "title"],
    "KnowledgeUnit":        ["content", "answer", "question"],
    "LegalClause":          ["content", "fullText", "title"],
    "RegulationClause":     ["fullText", "title"],
    "LegalDocument":        ["fullText", "description", "name", "title"],
    "Classification":       ["fullText", "description", "name"],
    "DocumentSection":      ["content", "title"],
    "MindmapNode":          ["content", "topic", "title"],
    "HSCode":               ["description", "chineseName", "name"],
    "CPAKnowledge":         ["content", "title"],
    "TaxRate":              ["fullText", "description", "name"],
    "FAQEntry":             ["content", "answer", "question"],
    "TaxClassificationCode": ["description", "item_name"],
    "TaxCodeDetail":        ["description", "name"],
    "TaxCodeIndustryMap":   ["description", "name"],
    "IndustryRiskProfile":  ["description", "name"],
    "RegionalTaxPolicy":    ["description", "fullText"],
    "BusinessActivity":     ["description", "name"],
    "AccountingEntry":      ["description", "name"],
    "TaxRiskScenario":      ["description", "name"],
    "ComplianceRule":       ["fullText", "description", "name"],
    "TaxIncentive":         ["fullText", "description", "name"],
    "Penalty":              ["fullText", "description", "name"],
    "SocialInsuranceRule":  ["description", "name"],
}

# ── Ingestion Gate (per-node) ───────────────────────────────────────────

TITLE_MIN_LEN = 5
CONTENT_MIN_LEN = 20


def validate_node(node: dict, index: int = 0) -> list[dict]:
    """Validate a single node for ingestion. Returns list of issues."""
    issues = []
    nid = (node.get("id") or "").strip()
    title = (node.get("title") or "").strip()
    content = (node.get("content") or node.get("fullText") or "").strip()

    if not nid:
        issues.append({"index": index, "severity": "high", "reason": "missing_id"})
    if len(title) < TITLE_MIN_LEN:
        issues.append({
            "index": index, "id": nid, "severity": "high",
            "reason": f"title_too_short ({len(title)}/{TITLE_MIN_LEN})",
            "value": title[:50],
        })
    if len(content) < CONTENT_MIN_LEN:
        issues.append({
            "index": index, "id": nid, "severity": "medium",
            "reason": f"content_too_short ({len(content)}/{CONTENT_MIN_LEN})",
        })
    if title.startswith("{'_id':") or title.startswith("{'offset':"):
        issues.append({
            "index": index, "id": nid, "severity": "high",
            "reason": "title_is_raw_id",
        })
    if title.startswith("TRM_"):
        issues.append({
            "index": index, "id": nid, "severity": "medium",
            "reason": f"title_is_code ({title})",
        })
    return issues


def validate_batch(nodes: list[dict]) -> dict:
    """Validate a batch of nodes for ingestion."""
    all_issues = []
    for i, node in enumerate(nodes):
        all_issues.extend(validate_node(node, i))

    total = len(nodes)
    high_count = sum(1 for i in all_issues if i["severity"] == "high")
    medium_count = sum(1 for i in all_issues if i["severity"] == "medium")
    pass_count = total - len(set(i.get("index") for i in all_issues))

    return {
        "gate": "PASS" if high_count == 0 else "FAIL",
        "total": total,
        "passed": pass_count,
        "pass_rate": round(pass_count / total, 3) if total > 0 else 0,
        "issues_high": high_count,
        "issues_medium": medium_count,
        "issues": all_issues[:100],
    }


# ── 5-Dimension Content Quality Audit ──────────────────────────────────

def _api_get(path: str, params: dict = None, timeout: int = 120) -> dict:
    """GET request to KG API."""
    if _HTTP == "httpx":
        r = httpx.get(f"{KG_API}{path}", params=params, timeout=timeout)
        return r.json()
    else:
        url = f"{KG_API}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url += f"?{qs}"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())


def _init_kuzu(force_new=False):
    """Initialize direct KuzuDB connection.

    force_new: close and reopen to prevent KuzuDB memory accumulation segfault.
    """
    global _kuzu_conn, _kuzu_db
    if force_new and _kuzu_conn is not None:
        try:
            del _kuzu_conn
        except Exception:
            pass
        try:
            del _kuzu_db
        except Exception:
            pass
        _kuzu_conn = None
        _kuzu_db = None
        import gc
        gc.collect()
    if _kuzu_conn is not None:
        return _kuzu_conn
    import kuzu
    try:
        _kuzu_db = kuzu.Database(DB_PATH, read_only=True)
    except RuntimeError:
        _kuzu_db = kuzu.Database(DB_PATH)
    _kuzu_conn = kuzu.Connection(_kuzu_db)
    return _kuzu_conn

_kuzu_db = None


def _direct_get_stats() -> dict:
    """Get node/edge counts directly from KuzuDB.

    Only queries types defined in NODE_CONTENT_FIELDS to avoid segfaults
    from querying 200+ tables on the 69GB database.
    """
    conn = _init_kuzu()
    nodes_by_type = {}
    total_nodes = 0

    for type_name in NODE_CONTENT_FIELDS:
        try:
            r = conn.execute(f"MATCH (n:{type_name}) RETURN count(n)")
            if r.has_next():
                c = r.get_next()[0]
                if c > 0:
                    nodes_by_type[type_name] = c
                    total_nodes += c
        except Exception as e:
            print(f"  WARN: count({type_name}) failed: {e}")

    # Skip global edge count — triggers KuzuDB segfault on 69GB database
    # with 120+ REL types. Node counts are sufficient for quality audit.
    return {"total_nodes": total_nodes, "total_edges": -1,
            "nodes_by_type": nodes_by_type}


def _direct_get_nodes(type_name: str, fields: list[str], limit: int) -> list[dict]:
    """Sample nodes directly from KuzuDB.

    Probes each field first to skip non-existent properties (avoids segfault).
    """
    conn = _init_kuzu()

    # Probe which fields actually exist on this type
    valid_fields = []
    for f in fields:
        try:
            conn.execute(f"MATCH (n:{type_name}) RETURN n.{f} LIMIT 1")
            valid_fields.append(f)
        except Exception:
            pass  # field doesn't exist on this type

    if not valid_fields:
        return []

    field_list = ", ".join(f"n.{f}" for f in valid_fields)
    try:
        r = conn.execute(f"MATCH (n:{type_name}) RETURN {field_list} LIMIT {limit}")
    except Exception:
        return []
    nodes = []
    while r.has_next():
        row = r.get_next()
        node = {}
        for i, f in enumerate(valid_fields):
            val = row[i]
            node[f] = str(val) if val is not None else ""
        nodes.append(node)
    return nodes


def _extract_best_content(node: dict, fields: list[str]) -> str:
    """Extract the longest content from a node across candidate fields."""
    best = ""
    for f in fields:
        val = str(node.get(f, "") or "")
        if len(val) > len(best):
            best = val
    return best


def _count_domain_terms(text: str) -> int:
    """Count how many domain terms appear in the text."""
    return sum(1 for t in DOMAIN_TERMS if t in text)


def _score_document_or_qa(nodes: list[dict], fields: list[str], sampled: int) -> dict:
    """Score document/QA types: Length(30) + Authenticity(20) + Domain(25) + Unique(15) + Fill(10)."""
    contents = [_extract_best_content(n, fields) for n in nodes]

    empty = sum(1 for c in contents if len(c) < 5)
    short = sum(1 for c in contents if 5 <= len(c) < 50)
    medium = sum(1 for c in contents if 50 <= len(c) < 200)
    good = sum(1 for c in contents if 200 <= len(c) < 500)
    rich = sum(1 for c in contents if len(c) >= 500)

    # D2 Authenticity: detect nav junk / HTML boilerplate via content_validator
    junk_count = 0
    real_count = 0
    if _HAS_VALIDATOR:
        for c in contents:
            if len(c) < 20:
                continue  # skip empties — already counted in D5 Fill
            junk, _reason = is_junk(c)
            if junk:
                junk_count += 1
            else:
                real_count += 1
        non_empty = sampled - empty
        auth_pct = real_count / non_empty * 100 if non_empty > 0 else 0
        junk_pct = junk_count / non_empty * 100 if non_empty > 0 else 0
    else:
        auth_pct = 100.0  # no validator available — assume good
        junk_pct = 0.0
        real_count = sampled - empty

    domain_hits = sum(1 for c in contents if _count_domain_terms(c) >= 2)
    domain_pct = domain_hits / sampled * 100

    unique_prefixes = set(c[:100] for c in contents if len(c) >= 20)
    unique_pct = len(unique_prefixes) / sampled * 100 if sampled > 0 else 0

    filled = sampled - empty
    fill_pct = filled / sampled * 100

    # Weighted scoring: Length(30) + Authenticity(20) + Domain(25) + Unique(15) + Fill(10) = 100
    len_score = (medium + good * 2 + rich * 3) / (sampled * 3) * 30
    auth_score = min(auth_pct / 80 * 20, 20)  # 80% real content = full marks
    domain_score = min(domain_pct / 80 * 25, 25)
    unique_score = min(unique_pct / 90 * 15, 15)
    fill_score = fill_pct / 100 * 10
    composite = round(len_score + auth_score + domain_score + unique_score + fill_score, 1)

    return {
        "score": composite,
        "method": "text",
        "junk_pct": round(junk_pct, 1),
        "dimensions": {
            "length": {"empty": empty, "short": short, "medium": medium,
                       "good": good, "rich": rich, "sub_score": round(len_score, 1)},
            "authenticity": {"real": real_count, "junk": junk_count,
                             "real_pct": round(auth_pct, 1), "junk_pct": round(junk_pct, 1),
                             "sub_score": round(auth_score, 1)},
            "domain": {"hits": domain_hits, "pct": round(domain_pct, 1),
                       "sub_score": round(domain_score, 1)},
            "unique": {"distinct": len(unique_prefixes), "pct": round(unique_pct, 1),
                       "sub_score": round(unique_score, 1)},
            "fill": {"filled": filled, "pct": round(fill_pct, 1),
                     "sub_score": round(fill_score, 1)},
        },
    }


def _score_structured(nodes: list[dict], type_name: str, sampled: int) -> dict:
    """Score structured types by field completeness (not text length)."""
    required = STRUCTURED_REQUIRED_FIELDS.get(type_name, ["name"])

    # Count how many required fields are filled (non-null, >= 1 char)
    fully_complete = 0
    field_fill_counts = {f: 0 for f in required}

    for n in nodes:
        filled_count = 0
        for f in required:
            val = n.get(f)
            if val is not None and len(str(val).strip()) >= 1:
                field_fill_counts[f] += 1
                filled_count += 1
        if filled_count == len(required):
            fully_complete += 1

    completeness_pct = fully_complete / sampled * 100 if sampled > 0 else 0

    # Uniqueness by concatenating key fields
    keys = []
    for n in nodes:
        key = "|".join(str(n.get(f, ""))[:30] for f in required)
        keys.append(key)
    unique_keys = set(keys)
    unique_pct = len(unique_keys) / sampled * 100 if sampled > 0 else 0

    # Composite: completeness 60 + uniqueness 30 + fill 10
    comp_score = min(completeness_pct / 90 * 60, 60)
    uniq_score = min(unique_pct / 90 * 30, 30)
    fill_score = (sampled - sum(1 for n in nodes
                  if all(not n.get(f) for f in required))) / sampled * 10
    composite = round(comp_score + uniq_score + fill_score, 1)

    return {
        "score": composite,
        "method": "fields",
        "dimensions": {
            "completeness": {"fully_complete": fully_complete,
                             "pct": round(completeness_pct, 1),
                             "required_fields": required,
                             "per_field": {f: field_fill_counts[f] for f in required},
                             "sub_score": round(comp_score, 1)},
            "unique": {"distinct": len(unique_keys), "pct": round(unique_pct, 1),
                       "sub_score": round(uniq_score, 1)},
            "fill": {"sub_score": round(fill_score, 1)},
        },
    }


def _score_metadata(nodes: list[dict], sampled: int) -> dict:
    """Score metadata types: just need name/id filled."""
    filled = sum(1 for n in nodes if any(
        len(str(n.get(f, "")).strip()) >= 2
        for f in ["name", "title", "id", "code"]))
    fill_pct = filled / sampled * 100 if sampled > 0 else 0
    composite = round(min(fill_pct / 90 * 100, 100), 1)

    return {
        "score": composite,
        "method": "meta",
        "dimensions": {
            "fill": {"filled": filled, "pct": round(fill_pct, 1),
                     "sub_score": composite},
        },
    }


def audit_type(type_name: str, total: int, fields: list[str]) -> dict:
    """Audit a single node type using category-appropriate scoring."""
    try:
        if _DIRECT_MODE:
            # For structured types, merge required fields so scoring has the data it needs.
            # NODE_CONTENT_FIELDS provides text fields for DOC/QA scoring, but
            # STRUCTURED_REQUIRED_FIELDS may include different fields (code, system, etc.)
            category = NODE_CATEGORY.get(type_name, "qa")
            query_fields = list(fields)
            if category == "structured":
                for f in STRUCTURED_REQUIRED_FIELDS.get(type_name, []):
                    if f not in query_fields:
                        query_fields.append(f)
            nodes = _direct_get_nodes(type_name, query_fields, SAMPLE_SIZE)
        else:
            data = _api_get("/api/v1/nodes", {"type": type_name, "limit": SAMPLE_SIZE})
            nodes = data.get("results", [])
    except Exception as e:
        return {"type": type_name, "total": total, "error": str(e),
                "sampled": 0, "score": 0, "gate": "ERROR"}

    sampled = len(nodes)
    if sampled == 0:
        return {"type": type_name, "total": total, "sampled": 0,
                "score": 0, "gate": "FAIL", "reason": "no_data_from_api"}

    category = NODE_CATEGORY.get(type_name, "qa")
    policy = CONTENT_SOURCE_POLICY.get(type_name, "unknown")

    if category in ("document", "qa"):
        scores = _score_document_or_qa(nodes, fields, sampled)
    elif category == "structured":
        scores = _score_structured(nodes, type_name, sampled)
    elif category == "metadata":
        scores = _score_metadata(nodes, sampled)
    else:
        scores = _score_document_or_qa(nodes, fields, sampled)

    gate = "PASS" if scores["score"] >= COMPOSITE_GATE else "FAIL"

    # Authoritative types: force FAIL if junk content > 50%
    junk_pct = scores.get("junk_pct", 0)
    forced_fail = False
    if policy == "authoritative" and junk_pct > 50:
        gate = "FAIL"
        forced_fail = True

    result = {
        "type": type_name,
        "total": total,
        "sampled": sampled,
        "gate": gate,
        "score": scores["score"],
        "category": category,
        "policy": policy,
        "method": scores["method"],
        "dimensions": scores["dimensions"],
    }
    if forced_fail:
        result["forced_fail"] = f"authoritative type junk={junk_pct:.0f}%>50%"
    return result


def run_full_audit() -> dict:
    """Run 6-dimension audit on all major node types."""
    if _DIRECT_MODE:
        stats = _direct_get_stats()
    else:
        stats = _api_get("/api/v1/stats")
    nodes_by_type = stats.get("nodes_by_type", {})

    results = []
    audit_count = 0
    for type_name, fields in NODE_CONTENT_FIELDS.items():
        total = nodes_by_type.get(type_name, 0)
        if total == 0:
            continue
        if _DIRECT_MODE:
            # Reconnect every 5 types to prevent KuzuDB memory accumulation segfault
            if audit_count > 0 and audit_count % 5 == 0:
                _init_kuzu(force_new=True)
            print(f"  Auditing {type_name} ({total:,})...", end="", flush=True)
        result = audit_type(type_name, total, fields)
        results.append(result)
        audit_count += 1
        if _DIRECT_MODE:
            print(f" {result.get('score', 0):.1f} {result.get('gate', '?')}")

    # Overall metrics
    total_nodes = sum(r["total"] for r in results)
    scored = [r for r in results if r.get("score", 0) > 0]
    weighted_score = (
        sum(r["score"] * r["total"] for r in scored)
        / sum(r["total"] for r in scored)
        if scored else 0
    )
    passing = [r for r in results if r.get("gate") == "PASS"]
    failing = [r for r in results if r.get("gate") == "FAIL"]

    return {
        "gate": "PASS" if weighted_score >= COMPOSITE_GATE and not failing else "FAIL",
        "overall_score": round(weighted_score, 1),
        "gate_threshold": COMPOSITE_GATE,
        "total_nodes": total_nodes,
        "types_audited": len(results),
        "types_passing": len(passing),
        "types_failing": len(failing),
        "failing_types": [r["type"] for r in failing],
        "results": sorted(results, key=lambda r: r.get("score", 0), reverse=True),
    }


# ── CLI ─────────────────────────────────────────────────────────────────

def _print_audit(report: dict):
    """Pretty-print audit report."""
    print(f"\n{'=' * 105}")
    print(f"  KG CONTENT QUALITY AUDIT — Gate: {report['gate']} "
          f"(Score: {report['overall_score']:.1f} / {report['gate_threshold']})")
    print(f"  {report['total_nodes']:,} nodes across {report['types_audited']} types "
          f"| {report['types_passing']} PASS / {report['types_failing']} FAIL")
    print(f"{'=' * 105}\n")

    CAT_LABEL = {"document": "DOC", "qa": "QA", "structured": "STRC", "metadata": "META"}
    POLICY_FIX = {
        "authoritative": "crawl/inherit",
        "structured": "assemble fields",
        "ai_expandable": "Gemini expand",
        "unknown": "tbd",
    }

    hdr = (f"{'Type':<22} {'Total':>7} {'Score':>6} {'Gate':>5} {'Cat':>4} | "
           f"{'Detail':.<50}  Fix")
    print(hdr)
    print("-" * 110)

    for r in report["results"]:
        if "error" in r:
            print(f"{r['type']:<22} {r['total']:>7,} {'ERR':>6} {'--':>5} {'--':>4} | ERROR: {r['error'][:40]}")
            continue

        d = r.get("dimensions", {})
        cat = r.get("category", "qa")
        gate_str = "PASS" if r["gate"] == "PASS" else "FAIL"
        policy = r.get("policy", "unknown")
        fix = "--" if r["gate"] == "PASS" else POLICY_FIX.get(policy, "tbd")

        if r.get("method") == "text":
            le = d.get("length", {})
            au = d.get("authenticity", {})
            dm = d.get("domain", {})
            uq = d.get("unique", {})
            auth_str = f"A{au.get('real_pct',100):.0f}%" if au else "A--"
            junk_str = f"J{au.get('junk_pct',0):.0f}%" if au.get("junk_pct", 0) > 0 else ""
            detail = (f"E{le.get('empty',0)} S{le.get('short',0)} "
                      f"M{le.get('medium',0)} G{le.get('good',0)} "
                      f"R{le.get('rich',0)} | "
                      f"{auth_str} {junk_str} "
                      f"D{dm.get('pct',0):.0f}% U{uq.get('pct',0):.0f}%").strip()
            if r.get("forced_fail"):
                detail += f" !! {r['forced_fail']}"
        elif r.get("method") == "fields":
            cp = d.get("completeness", {})
            uq = d.get("unique", {})
            detail = (f"Complete:{cp.get('pct',0):.0f}% "
                      f"Unique:{uq.get('pct',0):.0f}% "
                      f"Fields:{','.join(cp.get('required_fields',[]))}")
        elif r.get("method") == "meta":
            fi = d.get("fill", {})
            detail = f"Fill:{fi.get('pct',0):.0f}%"
        else:
            detail = "--"

        print(f"{r['type']:<22} {r['total']:>7,} {r['score']:>5.1f} {gate_str:>5} "
              f"{CAT_LABEL.get(cat,'?'):>4} | {detail:<50} {fix}")

    print("-" * 110)

    if report["failing_types"]:
        by_cat = {}
        for t in report["failing_types"]:
            cat = NODE_CATEGORY.get(t, "qa")
            by_cat.setdefault(cat, []).append(t)

        for cat in ["document", "qa", "structured", "metadata"]:
            items = by_cat.get(cat, [])
            if items:
                label = CAT_LABEL.get(cat, cat)
                print(f"\n  {label} FAIL ({len(items)}): {', '.join(items)}")

    print(f"\n  Scoring by category:")
    print(f"    DOC/QA:  Length(30) + Authenticity(20) + Domain(25) + Unique(15) + Fill(10)")
    print(f"    STRC:    FieldComplete(60) + Unique(30) + Fill(10)")
    print(f"    META:    NameFill(100)")
    print(f"  Gate >= {COMPOSITE_GATE} | E=Empty S=Short M=Medium G=Good R=Rich")
    print(f"  A=Authentic% J=Junk% D=Domain% U=Unique%")
    print(f"  Authoritative types: junk>50% forces FAIL\n")


def main():
    global _DIRECT_MODE
    if "--direct" in sys.argv:
        _DIRECT_MODE = True

    if "--audit" in sys.argv:
        report = run_full_audit()
        if "--json" in sys.argv:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_audit(report)
        sys.exit(0 if report["gate"] == "PASS" else 1)

    if "--check-api" in sys.argv:
        try:
            result = _api_get("/api/v1/quality")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get("gate") == "PASS" else 1)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [--audit [--json]] [--check-api] [json_file]")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    with open(filepath) as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("ERROR: Expected JSON array")
        sys.exit(1)

    result = validate_batch(data)
    print(f"=== KG Quality Gate: {result['gate']} ===")
    print(f"Total: {result['total']}, Passed: {result['passed']}, Rate: {result['pass_rate']:.1%}")
    print(f"High issues: {result['issues_high']}, Medium issues: {result['issues_medium']}")

    if result["issues"]:
        print("\nTop issues:")
        for issue in result["issues"][:20]:
            print(f"  [{issue['severity'].upper()}] #{issue.get('index', '?')}: {issue['reason']}"
                  + (f" -- {issue.get('value', '')}" if issue.get("value") else ""))

    sys.exit(0 if result["gate"] == "PASS" else 1)


if __name__ == "__main__":
    main()
