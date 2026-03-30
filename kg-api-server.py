#!/usr/bin/env python3
"""CogNebula KG API Server — FastAPI query service on kg-node."""
import os
import json
import hashlib

# Load env vars from .env file (POE_API_KEY, GEMINI_API_KEY, etc.)
for _env_path in ["/home/kg/.env.kg-api", os.path.join(os.path.dirname(__file__), ".env")]:
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
from typing import Optional
from pathlib import Path as _Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import kuzu
import lancedb
import numpy as np

# Config
DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
LANCE_PATH = "/home/kg/data/lancedb"
HOST = "0.0.0.0"
PORT = 8400

# ── Quality Gate Thresholds ──────────────────────────────────────────
QG_TITLE_MIN_LEN = 2          # Minimum title length (chars) — lowered for CJK (增值税=3chars is valid)
QG_CONTENT_MIN_LEN = 20       # Minimum content/fullText length
QG_TARGET_EDGE_DENSITY = 0.5  # Target edges per node
QG_TITLE_COVERAGE_TARGET = 0.95  # 95% nodes must have titles

# TaxRateMapping human-readable labels (code -> Chinese)
TRM_LABELS = {
    "TRM_TRANSPORT": "交通运输业", "TRM_FINANCE": "金融业", "TRM_TELECOM": "电信业",
    "TRM_SOFTWARE": "软件业", "TRM_AGRI": "农业", "TRM_EXPORT": "出口退税",
    "TRM_REALESTATE": "房地产业", "TRM_CONSTRUCT": "建筑业", "TRM_SERVICE": "现代服务业",
    "TRM_GOODS": "货物销售", "TRM_CATERING": "餐饮业", "TRM_CULTURE": "文化业",
    "TRM_EDUCATION": "教育", "TRM_MEDICAL": "医疗", "TRM_LOGISTICS": "物流业",
}


def _get_node_label(node_id, title=None, name=None, question=None,
                    content=None, table=None, node_text=None,
                    topic=None, item_name=None, productCategory=None):
    """Get best human-readable label for a node.

    Priority: title > name > question > node_text > topic > item_name > TRM decode > content prefix.
    Never returns raw IDs, offset tuples, or internal codes.
    """
    import re as _re
    for val in (title, name, question, node_text, topic, item_name, productCategory):
        if val and isinstance(val, str) and len(val.strip()) >= 2:
            clean = val.strip()
            # Skip raw ID leaks
            if clean.startswith("{'_id':") or clean.startswith("{'offset':"):
                continue
            # Skip pure numbers/section markers (e.g. "4.", "2.5%", "2025.5")
            if _re.match(r'^[\d\.\-%/]+$', clean):
                continue
            # Skip very short content that's just noise
            if len(clean) <= 3 and not any('\u4e00' <= c <= '\u9fff' for c in clean):
                continue
            return clean[:40]

    # TaxRateMapping code decode: "TRM_TRANSPORT_9" -> "交通运输业 9%"
    if node_id and str(node_id).startswith("TRM_"):
        nid = str(node_id)
        parts = nid.rsplit("_", 1)
        base = parts[0] if len(parts) > 1 else nid
        rate = parts[1] if len(parts) > 1 else ""
        label = TRM_LABELS.get(base, base.replace("TRM_", ""))
        return f"{label} {rate}%" if rate and rate.isdigit() else label

    # Content prefix as last resort
    if content and isinstance(content, str) and len(content.strip()) >= 5:
        return content.strip()[:35] + "..."

    # Hash ID: show only last 8 chars
    nid = str(node_id) if node_id else ""
    if len(nid) > 12:
        return f"...{nid[-8:]}"
    return nid or "未命名"


app = FastAPI(
    title="CogNebula KG API",
    version="1.0.0",
    description="Finance/Tax Knowledge Graph query service"
)

# Mount the static frontend UI
import os
if os.path.isdir("src/web"):
    app.mount("/ui", StaticFiles(directory="src/web", html=True), name="ui")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "Access-Control-Request-Private-Network"],
    expose_headers=["Access-Control-Allow-Private-Network"],
)


# Chrome Private Network Access (PNA) preflight handler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class PrivateNetworkMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(PrivateNetworkMiddleware)

# ---------------------------------------------------------------------------
# Know-Arc Expert Workbench integration (mounted at /api/v1/ka/*)
# ---------------------------------------------------------------------------
try:
    import sys
    sys.path.insert(0, "/home/kg/know-arc")
    from know_arc.api.router import create_ka_router
    ka_router = create_ka_router(
        kuzu_path="/home/kg/know-arc/data/know-arc-graph",
        sqlite_path="/home/kg/know-arc/data/know-arc.db",
        results_dir="/home/kg/know-arc/data/results",
        web_dir="/home/kg/know-arc/know_arc/web",
    )
    app.include_router(ka_router)
    _know_arc_available = True
except Exception as e:
    import logging
    logging.getLogger("kg-api").warning(f"Know-Arc integration failed: {e}")
    _know_arc_available = False

# Lazy DB connections
_kuzu_db = None
_kuzu_conn = None
_lance_db = None
_lance_table = None


def get_kuzu():
    global _kuzu_db, _kuzu_conn
    if _kuzu_conn is None:
        _kuzu_db = kuzu.Database(DB_PATH)  # auto buffer sizing
        _kuzu_conn = kuzu.Connection(_kuzu_db)
    return _kuzu_conn


def get_lance():
    global _lance_db, _lance_table
    if _lance_table is None:
        _lance_db = lancedb.connect(LANCE_PATH)
        _lance_table = _lance_db.open_table("kg_nodes")
    return _lance_table


# === Web UI ===
WEB_DIR = _Path("/home/kg/cognebula-enterprise/src/web")


@app.get("/")
def web_ui():
    html_path = WEB_DIR / "unified.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html",
                            headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return JSONResponse({"error": "Web UI not found"}, status_code=404)


@app.get("/kg_explorer.html")
def kg_explorer():
    """Serve the original KG Explorer (vis.js, embedded in unified Tab Shell via iframe)."""
    html_path = WEB_DIR / "kg_explorer.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html",
                            headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return JSONResponse({"error": "KG Explorer not found"}, status_code=404)


@app.get("/kg_explorer_v2.html")
def kg_explorer_v2():
    """Serve KG Explorer v2 (Cytoscape.js + fcose + compound nodes)."""
    html_path = WEB_DIR / "kg_explorer_v2.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html",
                            headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return JSONResponse({"error": "KG Explorer v2 not found"}, status_code=404)


# === Health ===
@app.get("/api/v1/health")
def health():
    try:
        conn = get_kuzu()
        conn.execute("RETURN 1")
        kuzu_ok = True
    except:
        kuzu_ok = False

    try:
        tbl = get_lance()
        lance_ok = tbl is not None
        lance_rows = len(tbl)
    except:
        lance_ok = False
        lance_rows = 0

    return {
        "status": "healthy" if kuzu_ok and lance_ok else "degraded",
        "kuzu": kuzu_ok,
        "lancedb": lance_ok,
        "lancedb_rows": lance_rows,
    }


# === Stats ===
@app.get("/api/v1/stats")
def stats():
    conn = get_kuzu()
    result = conn.execute("CALL show_tables() RETURN *")
    tables = []
    while result.has_next():
        tables.append(result.get_next())

    node_counts = {}
    total_nodes = 0
    for t in tables:
        if t[2] == "NODE":
            try:
                r = conn.execute(f"MATCH (n:{t[1]}) RETURN count(n)")
                if r.has_next():
                    c = r.get_next()[0]
                    node_counts[t[1]] = c
                    total_nodes += c
            except:
                node_counts[t[1]] = -1

    total_edges = 0
    edge_counts = {}
    for t in tables:
        if t[2] == "REL":
            try:
                r = conn.execute(f"MATCH ()-[e:{t[1]}]->() RETURN count(e)")
                if r.has_next():
                    c = r.get_next()[0]
                    edge_counts[t[1]] = c
                    total_edges += c
            except:
                edge_counts[t[1]] = -1

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "total_entities": total_nodes + total_edges,
        "node_tables": len(node_counts),
        "rel_tables": len(edge_counts),
        "nodes_by_type": {k: v for k, v in sorted(node_counts.items(), key=lambda x: -x[1]) if v > 0},
        "edges_by_type": {k: v for k, v in sorted(edge_counts.items(), key=lambda x: -x[1]) if v > 0},
    }


# === Quality Audit ===
@app.get("/api/v1/quality")
def quality_audit():
    """Audit KG data quality: title coverage, edge density, isolated nodes."""
    conn = get_kuzu()
    issues = []
    metrics = {}

    # v2.2 tables only -- legacy tables (TaxCodeDetail, AccountRuleMapping, etc.)
    # have been migrated and must NOT inflate quality audit issue counts.
    V2_TABLES = {
        "LegalDocument", "LegalClause", "TaxRate", "ComplianceRuleV2", "RiskIndicatorV2",
        "TaxIncentiveV2", "KnowledgeUnit", "Classification", "AccountingSubject",
        "TaxType", "TaxEntity", "Region", "FilingFormV2", "BusinessActivity",
        "IssuingBody", "Penalty", "AuditTrigger",
    }

    V2_EDGES = {
        "PART_OF", "CHILD_OF", "SUPERSEDES", "AMENDS", "CONFLICTS_WITH",
        "REFERENCES_CLAUSE", "BASED_ON", "INCENTIVE_BASED_ON", "ISSUED_BY",
        "APPLIES_TO_TAX", "APPLIES_TO_ENTITY", "APPLIES_IN_REGION", "APPLIES_TO_CLASS",
        "REQUIRES_FILING", "GOVERNED_BY", "DEBITS_V2", "CREDITS_V2",
        "INTERPRETS", "EXEMPLIFIED_BY", "EXPLAINS_RATE",
        "WARNS_ABOUT", "DESCRIBES_INCENTIVE", "GUIDES_FILING",
        "PENALIZED_BY", "TRIGGERED_BY",
        "CALCULATED_FROM", "SURCHARGE_OF", "RELATED_TAX",
        "TRIGGERS_TAX", "INCENTIVE_FOR_TAX", "RULE_FOR_TAX", "FILING_FOR_TAX",
        "MAPS_TO_ACCOUNT", "RISK_FOR_TAX", "KU_ABOUT_TAX", "AUDIT_FOR_TAX",
    }

    # Get all node tables
    result = conn.execute("CALL show_tables() RETURN *")
    node_tables = []
    while result.has_next():
        row = result.get_next()
        if row[2] == "NODE":
            node_tables.append(row[1])

    # Table-specific label fields for v2.2 tables
    TABLE_LABEL_FIELDS = {
        "LegalClause": ["title", "fullText"],
        "KnowledgeUnit": ["topic", "content"],
        "ComplianceRuleV2": ["name", "description"],
        "RiskIndicatorV2": ["name", "description"],
        "TaxIncentiveV2": ["name", "description"],
        "FilingFormV2": ["name", "description"],
        "AccountingSubject": ["name", "description"],
        "Penalty": ["name", "description"],
        "AuditTrigger": ["name", "description"],
    }

    # Title coverage per table
    title_stats = {}
    total_nodes = 0
    total_with_title = 0
    for tbl in node_tables:
        if tbl not in V2_TABLES:
            continue
        try:
            r = conn.execute(f"MATCH (n:{tbl}) RETURN count(n)")
            count = r.get_next()[0]
            if count == 0:
                continue
        except:
            continue

        has_title = 0
        # Check standard fields + table-specific fields
        fields_to_check = ["title", "name", "question"] + TABLE_LABEL_FIELDS.get(tbl, [])
        for field in fields_to_check:
            try:
                r = conn.execute(
                    f"MATCH (n:{tbl}) WHERE n.{field} IS NOT NULL AND size(n.{field}) >= {QG_TITLE_MIN_LEN} RETURN count(n)"
                )
                has_title = max(has_title, r.get_next()[0])
            except:
                pass

        coverage = round(has_title / count, 3) if count > 0 else 0
        title_stats[tbl] = {"total": count, "with_title": has_title, "coverage": coverage}
        total_nodes += count
        total_with_title += has_title
        if coverage < QG_TITLE_COVERAGE_TARGET:
            issues.append({
                "severity": "high" if coverage < 0.5 else "medium",
                "type": "empty_title", "table": tbl,
                "message": f"{tbl}: title coverage {coverage:.0%} ({count - has_title} missing)",
            })

    metrics["title_coverage"] = round(total_with_title / total_nodes, 3) if total_nodes > 0 else 0

    # Content coverage: nodes with fullText/content >= QG_CONTENT_MIN_LEN chars
    total_with_content = 0
    for tbl in node_tables:
        if tbl not in V2_TABLES:
            continue
        content_fields = ["fullText", "content", "description"]
        if tbl in TABLE_LABEL_FIELDS:
            content_fields.extend(TABLE_LABEL_FIELDS[tbl])
        best_count = 0
        for field in content_fields:
            try:
                r = conn.execute(
                    f"MATCH (n:{tbl}) WHERE n.{field} IS NOT NULL AND size(n.{field}) >= {QG_CONTENT_MIN_LEN} RETURN count(n)"
                )
                best_count = max(best_count, r.get_next()[0])
            except:
                pass
        total_with_content += best_count
    metrics["content_coverage"] = round(total_with_content / total_nodes, 3) if total_nodes > 0 else 0

    # Edge density (v3.1 edges only)
    total_edges = 0
    edge_debug = {}
    for edge_label in V2_EDGES:
        try:
            r = conn.execute(f"MATCH ()-[e:{edge_label}]->() RETURN count(e)")
            c = r.get_next()[0]
            total_edges += c
            edge_debug[edge_label] = c
        except Exception as e:
            edge_debug[edge_label] = f"ERROR: {str(e)[:80]}"

    density = round(total_edges / total_nodes, 3) if total_nodes > 0 else 0
    metrics["edge_density"] = density
    metrics["total_nodes"] = total_nodes
    metrics["total_edges"] = total_edges
    if density < QG_TARGET_EDGE_DENSITY:
        issues.append({
            "severity": "high", "type": "sparse_edges",
            "message": f"Edge density {density} below target {QG_TARGET_EDGE_DENSITY}",
        })

    # Edge label quality: check if MENTIONS edges point to nodes with readable labels
    unlabeled_edge_targets = 0
    try:
        # Sample MENTIONS edges and check if targets have any label field
        for src_tbl in ["DocumentSection", "LawOrRegulation", "CPAKnowledge"]:
            try:
                label_fields = TABLE_LABEL_FIELDS.get(src_tbl, [])
                all_fields = ["title", "name"] + label_fields
                # Check if target nodes of MENTIONS edges have any label
                for field in all_fields:
                    try:
                        r = conn.execute(
                            f"MATCH (d:{src_tbl})-[:MENTIONS]->(t:TaxType) "
                            f"WHERE d.{field} IS NULL OR size(d.{field}) < 5 "
                            f"RETURN count(d) LIMIT 1"
                        )
                        unlabeled_edge_targets += r.get_next()[0]
                        break  # Only count once per table
                    except:
                        continue
            except:
                pass
    except:
        pass

    if unlabeled_edge_targets > 50:
        issues.append({
            "severity": "medium", "type": "unlabeled_edge_targets",
            "message": f"{unlabeled_edge_targets} MENTIONS edges point to nodes without readable labels",
        })
    metrics["unlabeled_edge_targets"] = unlabeled_edge_targets

    # Quality score
    score = 100
    score -= max(0, (QG_TITLE_COVERAGE_TARGET - metrics["title_coverage"]) * 100)
    score -= max(0, (QG_TARGET_EDGE_DENSITY - density) * 50)
    metrics["quality_score"] = max(0, round(score))
    gate_pass = metrics["quality_score"] >= 60

    return {
        "gate": "PASS" if gate_pass else "FAIL",
        "score": metrics["quality_score"],
        "metrics": metrics,
        "title_stats": {k: v for k, v in sorted(title_stats.items(), key=lambda x: x[1]["total"], reverse=True) if v["total"] > 0},
        "issues": sorted(issues, key=lambda x: 0 if x["severity"] == "high" else 1),
        # "edge_debug": edge_debug,  # enable for diagnostics
    }


# === Constellation (single-call graph data for Sigma.js) ===
@app.get("/api/v1/constellation")
def constellation(limit: int = Query(500, ge=10, le=2000)):
    """Return dense graph data for Sigma.js constellation visualization.

    Strategy:
    1. Aggressive node sampling (all small tables, subset of large ones)
    2. Iterate ALL backbone edge tables to discover connections between sampled nodes
    3. Python-filter: keep only edges where both endpoints are sampled
    """
    conn = get_kuzu()
    nodes = []
    edges = []
    added_ids = set()

    # v4.1 types: (table, sample_limit, node_size, label_field)
    # KuzuDB is schema-based: must use correct column names per table.
    # Small tables (< 200): sample ALL for maximum density.
    TYPES = [
        ("TaxType", 19, 10, "name"),
        ("TaxIncentive", 109, 5, "name"),
        ("ComplianceRule", 84, 5, "name"),
        ("TaxRate", 80, 4, "name"),
        ("TaxAccountingGap", 50, 4, "name"),
        ("SocialInsuranceRule", 138, 4, "name"),
        ("InvoiceRule", 40, 4, "name"),
        ("IndustryBenchmark", 45, 4, "ratioName"),  # No `name` column
        ("AuditTrigger", 100, 4, "name"),
        ("Penalty", 127, 4, "name"),
        ("TaxEntity", 34, 5, "name"),
        ("BusinessActivity", 60, 4, "name"),
        ("AccountingSubject", 80, 4, "name"),
        ("FilingForm", 60, 4, "name"),
        ("Region", 31, 5, "name"),
        ("IssuingBody", 60, 4, "name"),
        ("RiskIndicator", 100, 4, "name"),
        ("LegalDocument", 40, 3, "name"),
        ("LegalClause", 30, 2.5, "title"),         # Uses `title` not `name`
        ("KnowledgeUnit", 20, 2.5, "topic"),        # Uses `topic`
        ("FAQEntry", 20, 2.5, "question"),           # Uses `question`
        ("Classification", 40, 3, "name"),
    ]

    for table, sample, size, label_field in TYPES:
        try:
            r = conn.execute(f"MATCH (n:{table}) RETURN n.id, n.{label_field} LIMIT {sample}")
            while r.has_next():
                row = r.get_next()
                nid = str(row[0]) if row[0] else ""
                if not nid or nid in added_ids:
                    continue
                name = str(row[1] or "")[:30]
                if not name or name.startswith("...") or len(name) < 2:
                    continue
                added_ids.add(nid)
                nodes.append({"id": nid, "label": name, "type": table, "size": size})
        except Exception:
            continue

    # ── Edge discovery: iterate ALL known backbone edge tables ──
    # For each edge table, query a batch and keep only edges between sampled nodes.
    # This is O(E) queries where E = number of edge tables (~45), each LIMIT 500.
    # Comprehensive edge table list — includes all known tables from the running DB.
    # Non-existent tables are silently skipped (try/except per table).
    ALL_EDGE_TABLES = [
        # Structural (hierarchy, authorship)
        "PART_OF", "CHILD_OF", "ISSUED_BY", "SUPERSEDES", "AMENDS",
        "PARENT_CLAUSE", "PARENT_SUBJECT",
        # Core backbone (verified in DB: TT_VAT has these)
        "CLASSIFIED_UNDER_TAX", "FT_INCENTIVE_TAX", "FT_APPLIES_TO", "FT_GOVERNED_BY",
        "APPLIES_TO_TAX", "CALCULATED_FROM", "SURCHARGE_OF", "RELATED_TAX",
        "ENTITY_FOR_TAX",
        # Backbone (may exist from build_backbone_edges.py)
        "INCENTIVE_FOR_TAX", "RULE_FOR_TAX", "GAP_FOR_TAX",
        "INVOICE_FOR_TAX", "AUDIT_FOR_TAX", "RISK_FOR_TAX", "FILING_FOR_TAX",
        "BENCHMARK_FOR", "TRIGGERS_TAX", "KU_ABOUT_TAX",
        # Cross-type semantic
        "BASED_ON", "REFERENCES_CLAUSE", "GOVERNED_BY",
        "INTERPRETS", "DESCRIBES_INCENTIVE", "EXPLAINS_RATE",
        "WARNS_ABOUT", "GUIDES_FILING", "EXEMPLIFIED_BY",
        # Compliance
        "STACKS_WITH", "EXCLUDES", "CREATES_GAP", "HAS_GAP",
        "INSURANCE_IN_REGION", "AUDIT_TRIGGERS", "OVERRIDES_IN",
        "PENALIZED_BY", "TRIGGERED_BY", "RELATED_PARTY",
        # Mapping
        "MAPS_TO_SUBJECT", "MAPS_TO_ACCOUNT", "HAS_RATE",
        # Legacy/extended
        "APPLIES_TO_ENTITY", "APPLIES_IN_REGION", "APPLIES_TO_CLASS",
        "REQUIRES_FILING", "RULE_FOR_INDUSTRY",
        "INCENTIVE_BASED_ON",
        # V2 edges
        "DEBITS_V2", "CREDITS_V2",
        # FT (FinancialTax) prefix edges
        "FT_QUALIFIES_FOR",
    ]

    for edge_table in ALL_EDGE_TABLES:
        try:
            r = conn.execute(
                f"MATCH (a)-[e:{edge_table}]->(b) RETURN a.id, b.id LIMIT 1000"
            )
            while r.has_next():
                row = r.get_next()
                src = str(row[0] or "")
                tgt = str(row[1] or "")
                if src in added_ids and tgt in added_ids and src != tgt:
                    edges.append({"source": src, "target": tgt, "type": edge_table})
        except Exception:
            continue

    # ── Fallback: generic expansion for any isolated nodes ──
    # If some nodes have zero edges after edge-table scan, expand them generically
    nodes_with_edges = set()
    for e in edges:
        nodes_with_edges.add(e["source"])
        nodes_with_edges.add(e["target"])
    isolated = [n for n in nodes if n["id"] not in nodes_with_edges]
    for iso_node in isolated[:50]:  # Cap to avoid too many queries
        safe_id = iso_node["id"].replace("'", "\\'")
        safe_type = iso_node["type"]
        try:
            r = conn.execute(
                f"MATCH (n:{safe_type})-[e]->(m) WHERE n.id = '{safe_id}' "
                f"RETURN n.id, label(e), m.id LIMIT 5"
            )
            while r.has_next():
                row = r.get_next()
                tgt = str(row[2] or "")
                if tgt in added_ids and tgt != iso_node["id"]:
                    edges.append({"source": str(row[0]), "target": tgt, "type": str(row[1])})
        except Exception:
            pass

    # Deduplicate edges
    seen_edges = set()
    unique_edges = []
    for e in edges:
        key = f"{e['source']}-{e['target']}-{e['type']}"
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    return {"nodes": nodes, "edges": unique_edges, "total_nodes": len(nodes), "total_edges": len(unique_edges)}


# === Query nodes ===
@app.get("/api/v1/nodes")
def query_nodes(
    type: str = Query(..., description="Node table name, e.g. FAQEntry"),
    q: Optional[str] = Query(None, description="Filter by text match"),
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = get_kuzu()

    # Validate table exists
    result = conn.execute("CALL show_tables() RETURN *")
    valid_tables = set()
    while result.has_next():
        row = result.get_next()
        if row[2] == "NODE":
            valid_tables.add(row[1])

    if type not in valid_tables:
        raise HTTPException(404, f"Table '{type}' not found. Valid: {sorted(valid_tables)}")

    # Build query with optional text filter (column-safe: tries name+title+fullText, falls back)
    if q:
        safe_q = q.replace("\\", "\\\\").replace("'", "\\'")
        try:
            cypher = (
                f"MATCH (n:{type}) "
                f"WHERE n.name CONTAINS '{safe_q}' OR n.title CONTAINS '{safe_q}' "
                f"OR (n.fullText IS NOT NULL AND n.fullText CONTAINS '{safe_q}') "
                f"RETURN n SKIP {offset} LIMIT {limit}"
            )
            result = conn.execute(cypher)
        except Exception:
            # Fallback: table may lack title or fullText columns
            cypher = f"MATCH (n:{type}) WHERE n.name CONTAINS '{safe_q}' RETURN n SKIP {offset} LIMIT {limit}"
            result = conn.execute(cypher)
    else:
        # For LegalDocument: prioritize policy content over kuaiji textbook
        if type == "LegalDocument":
            try:
                cypher = (
                    f"MATCH (n:{type}) "
                    f"WITH n, CASE "
                    f"WHEN n.type STARTS WITH 'policy' THEN 1 "
                    f"WHEN n.type STARTS WITH 'provincial' THEN 2 "
                    f"WHEN n.type STARTS WITH '12366' THEN 3 "
                    f"WHEN n.type STARTS WITH 'compliance' THEN 4 "
                    f"WHEN n.type = 'kuaiji' THEN 8 "
                    f"WHEN n.type STARTS WITH 'pdf_cpa' THEN 9 "
                    f"ELSE 5 END AS priority "
                    f"RETURN n ORDER BY priority SKIP {offset} LIMIT {limit}"
                )
                result = conn.execute(cypher)
            except Exception:
                cypher = f"MATCH (n:{type}) RETURN n SKIP {offset} LIMIT {limit}"
                result = conn.execute(cypher)
        else:
            cypher = f"MATCH (n:{type}) RETURN n SKIP {offset} LIMIT {limit}"
            result = conn.execute(cypher)
    rows = []
    while result.has_next():
        row = result.get_next()
        if row and row[0]:
            d = dict(row[0]) if hasattr(row[0], '__iter__') and not isinstance(row[0], str) else {"value": str(row[0])}
            # Dynamic label injection: add _display_label from best available field
            d["_display_label"] = _get_node_label(
                d.get("id"), title=d.get("title"), name=d.get("name"),
                question=d.get("question"), content=d.get("content") or d.get("fullText"),
                table=type, node_text=d.get("node_text"), topic=d.get("topic"),
                item_name=d.get("item_name"), productCategory=d.get("productCategory"),
            )
            rows.append(d)

    return {"type": type, "count": len(rows), "offset": offset, "results": rows}


# === Text-based KG Search (Cypher CONTAINS) ===
def _cypher_text_search(conn, query: str, limit: int = 10, table_filter: str = None) -> list:
    """Search KuzuDB using CONTAINS across v4.1 node tables.

    Returns ranked results: exact name match > name contains > title > fullText.
    Falls back gracefully if a table lacks certain columns.
    """
    safe_q = query.replace("\\", "\\\\").replace("'", "\\'")

    SEARCH_TABLES = [
        # v4.1 core (high priority — structured domain data)
        "TaxType", "TaxRate", "TaxIncentive", "ComplianceRule", "RiskIndicator",
        "TaxAccountingGap", "SocialInsuranceRule", "InvoiceRule", "IndustryBenchmark",
        "AuditTrigger", "Penalty", "FilingForm", "TaxEntity", "BusinessActivity",
        "AccountingSubject", "Classification", "Region", "IssuingBody",
        # Large content tables
        "LegalDocument", "LegalClause", "KnowledgeUnit",
        # Legacy tables with rich Q&A content
        "FAQEntry", "CPAKnowledge",
    ]

    if table_filter:
        SEARCH_TABLES = [t for t in SEARCH_TABLES if t == table_filter]

    results = []
    per_table = max(5, limit)

    for table in SEARCH_TABLES:
        if len(results) >= limit * 5:
            break
        try:
            # Primary: search across name, title, fullText
            cypher = (
                f"MATCH (n:{table}) "
                f"WHERE n.name CONTAINS '{safe_q}' OR n.title CONTAINS '{safe_q}' "
                f"OR (n.fullText IS NOT NULL AND n.fullText CONTAINS '{safe_q}') "
                f"RETURN n.id, n.name, n.title, "
                f"CASE WHEN n.fullText IS NOT NULL AND n.fullText <> '' "
                f"THEN substring(n.fullText, 0, 500) ELSE '' END "
                f"LIMIT {per_table}"
            )
            r = conn.execute(cypher)
            while r.has_next():
                row = r.get_next()
                nid = str(row[0]) if row[0] is not None else ""
                name = str(row[1]) if row[1] is not None else ""
                title = str(row[2]) if row[2] is not None else ""
                ft = str(row[3]) if row[3] is not None else ""
                # Relevance scoring
                score = 40
                if name == query:
                    score = 100
                elif query in name:
                    score = 80
                elif title and query in title:
                    score = 60
                display = ft if ft else (title if title else name)
                results.append({
                    "id": nid, "text": display[:500], "table": table,
                    "title": title or name, "name": name, "score": score,
                })
        except Exception:
            # Fallback: table might lack title or fullText columns
            try:
                cypher2 = (
                    f"MATCH (n:{table}) "
                    f"WHERE n.name CONTAINS '{safe_q}' "
                    f"RETURN n.id, n.name LIMIT {per_table}"
                )
                r = conn.execute(cypher2)
                while r.has_next():
                    row = r.get_next()
                    nid = str(row[0]) if row[0] is not None else ""
                    name = str(row[1]) if row[1] is not None else ""
                    results.append({
                        "id": nid, "text": name[:500], "table": table,
                        "title": name, "name": name,
                        "score": 80 if query in name else 40,
                    })
            except Exception:
                continue

    # If full-phrase search returned too few, try domain-aware term extraction
    DOMAIN_TERMS = [
        "小规模纳税人", "一般纳税人", "增值税", "企业所得税", "个人所得税", "消费税",
        "土地增值税", "房产税", "印花税", "契税", "关税", "车船税", "资源税",
        "城建税", "教育费附加", "税收优惠", "减免税", "加计扣除", "即征即退",
        "纳税申报", "汇算清缴", "税务登记", "发票管理", "进项税额", "销项税额",
        "小微企业", "高新技术", "研发费用", "社保", "公积金",
        "税会差异", "纳税调整", "视同销售", "税前扣除", "合规", "风险", "稽查",
        # High-frequency 2-char terms (prevent bigram stride misalignment)
        "发票", "认证", "申报", "退税", "免税", "抵扣", "征收", "缴纳",
        "税率", "税种", "税负", "税额", "纳税", "减税", "优惠", "罚款",
        "审计", "处罚", "滞纳", "行业", "基准", "预警", "科目", "会计",
    ]
    if len(results) < limit and len(query) > 3:
        import re as _re_split
        # First: extract known domain terms
        subterms = []
        for dt in DOMAIN_TERMS:
            if dt in query and dt not in subterms:
                subterms.append(dt)
        # Second: split on particles, keep 2-4 char chunks (no overlapping bigrams)
        raw = _re_split.split(
            r'[，。？！、的了在是有和与或及其对于关于如何什么哪些可以怎么为被将把各多少几个 ]',
            query,
        )
        for t in raw:
            t = t.strip()
            if 2 <= len(t) <= 4 and t not in subterms:
                subterms.append(t)
            elif len(t) > 4:
                for i in range(0, len(t) - 1, 2):
                    bi = t[i:i+2]
                    if bi not in subterms and len(bi) == 2:
                        subterms.append(bi)
        # Filter out subterms that are substrings of domain terms
        found_domain = [t for t in subterms if t in DOMAIN_TERMS]
        if found_domain:
            subterms = [t for t in subterms if t in DOMAIN_TERMS or not any(t in dt for dt in found_domain)]
        existing_ids = {r["id"] for r in results}
        for st in subterms[:4]:
            if st == query:
                continue
            safe_st = st.replace("\\", "\\\\").replace("'", "\\'")
            for table in SEARCH_TABLES:
                if table_filter and table != table_filter:
                    continue
                if len(results) >= limit * 3:
                    break
                try:
                    cypher = (
                        f"MATCH (n:{table}) "
                        f"WHERE n.name CONTAINS '{safe_st}' OR n.title CONTAINS '{safe_st}' "
                        f"RETURN n.id, n.name, n.title, '' LIMIT 5"
                    )
                    r = conn.execute(cypher)
                    while r.has_next():
                        row = r.get_next()
                        nid = str(row[0]) if row[0] is not None else ""
                        if nid in existing_ids:
                            continue
                        name = str(row[1]) if row[1] is not None else ""
                        title = str(row[2]) if row[2] is not None else ""
                        results.append({
                            "id": nid, "text": (title or name)[:500], "table": table,
                            "title": title or name, "name": name,
                            "score": 60 if st in name else 40,
                        })
                        existing_ids.add(nid)
                except Exception:
                    continue

    results.sort(key=lambda x: -x["score"])
    return results[:limit]


# === Search (Cypher text + optional LanceDB vector boost) ===
@app.get("/api/v1/search")
def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    table_filter: Optional[str] = Query(None, description="Filter by source table"),
):
    conn = get_kuzu()
    results = _cypher_text_search(conn, q, limit, table_filter)

    # Optional: boost with LanceDB vector results if embedding succeeds
    try:
        import urllib.request as _urlreq
        _api_key = os.environ.get("GEMINI_API_KEY", "")
        if _api_key:
            _url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:embedContent?key={_api_key}"
            _payload = json.dumps({"model": "models/gemini-embedding-2-preview", "content": {"parts": [{"text": q[:2048]}]}, "taskType": "RETRIEVAL_QUERY", "outputDimensionality": 768}).encode()
            _req = _urlreq.Request(_url, data=_payload, headers={"Content-Type": "application/json"})
            with _urlreq.urlopen(_req, timeout=5) as _resp:
                query_vec = json.loads(_resp.read())["embedding"]["values"]
            tbl = get_lance()
            vec_results = tbl.search(query_vec).limit(limit).to_list()
            existing_ids = {r["id"] for r in results}
            for vr in vec_results:
                vid = vr.get("id", "")
                if vid and vid not in existing_ids:
                    results.append({
                        "id": vid,
                        "text": (vr.get("text", "") or "")[:500],
                        "table": vr.get("table", ""),
                        "title": "",
                        "name": "",
                        "score": max(0, 50 - float(vr.get("_distance", 50))),
                    })
                    existing_ids.add(vid)
    except Exception:
        pass  # Vector boost is optional; Cypher text search is the primary

    results.sort(key=lambda x: -x["score"])
    results = results[:limit]

    return {
        "query": q,
        "count": len(results),
        "results": [
            {
                "id": r["id"],
                "text": r["text"][:300],
                "table": r["table"],
                "title": r.get("title", ""),
                "name": r.get("name", ""),
                "score": r["score"],
            }
            for r in results
        ],
    }


# === Graph traversal ===
@app.get("/api/v1/graph")
def graph_traverse(
    table: str = Query(..., description="Node table name"),
    id_field: str = Query("id", description="ID field name"),
    id_value: str = Query(..., description="Node ID value"),
    depth: int = Query(1, ge=1, le=3),
):
    conn = get_kuzu()
    safe_val = id_value.replace("'", "''")
    safe_field = id_field.replace("'", "")
    safe_table = table.replace("'", "")
    try:
        result = conn.execute(f"MATCH (n:{safe_table}) WHERE n.{safe_field} = '{safe_val}' RETURN n")
        node = None
        node_dict = None
        if result.has_next():
            row = result.get_next()
            raw = row[0] if row else None
            if isinstance(raw, dict):
                node_dict = raw
                # Return clean version with label (10K limit for full-text display)
                node = {k: str(v)[:10000] if v is not None else None for k, v in raw.items()}
                node["_label"] = _get_node_label(
                    node.get("id"), title=node.get("title"),
                    name=node.get("name"), question=node.get("question"),
                    content=node.get("content") or node.get("fullText"),
                    table=safe_table,
                )
            else:
                node = str(raw) if raw else None
        neighbors = []

        def _parse_neighbor(row, direction):
            """Extract clean neighbor info from KuzuDB row [edge_label, node_label, node_obj]."""
            edge_type = str(row[0])
            target_type = str(row[1])
            raw_node = row[2]
            # Extract fields from the KuzuDB node object
            if isinstance(raw_node, dict):
                nid = raw_node.get("id", "")
                label = _get_node_label(
                    nid, title=raw_node.get("title"), name=raw_node.get("name"),
                    question=raw_node.get("question"),
                    content=raw_node.get("content") or raw_node.get("fullText"),
                    table=target_type, node_text=raw_node.get("node_text"),
                    topic=raw_node.get("topic"), item_name=raw_node.get("item_name"),
                    productCategory=raw_node.get("productCategory"),
                )
                return {
                    "edge_type": edge_type, "target_type": target_type,
                    "target_id": str(nid), "target_label": label,
                    "target": f"id: {nid}, title: {label}",
                    "direction": direction,
                }
            else:
                # Fallback for non-dict nodes
                s = str(raw_node)[:10000]
                # Try to extract id from string repr
                import re
                id_match = re.search(r"id:\s*([^,}]+)", s)
                nid = id_match.group(1).strip() if id_match else s[:30]
                return {
                    "edge_type": edge_type, "target_type": target_type,
                    "target_id": nid, "target_label": _get_node_label(nid, table=target_type),
                    "target": s,
                    "direction": direction,
                }

        try:
            result = conn.execute(f"MATCH (n:{safe_table})-[e]->(m) WHERE n.{safe_field} = '{safe_val}' RETURN label(e), label(m), m LIMIT 100")
            while result.has_next():
                neighbors.append(_parse_neighbor(result.get_next(), "outgoing"))
        except Exception as _ge:
            import sys; print(f"GRAPH_ERR: {_ge}", file=sys.stderr)
        try:
            result = conn.execute(f"MATCH (m)-[e]->(n:{safe_table}) WHERE n.{safe_field} = '{safe_val}' RETURN label(e), label(m), m LIMIT 100")
            while result.has_next():
                neighbors.append(_parse_neighbor(result.get_next(), "incoming"))
        except Exception as _ge:
            import sys; print(f"GRAPH_ERR: {_ge}", file=sys.stderr)

        # Sort: backbone ontology edges first, bulk/legacy edges last
        BACKBONE_EDGES = {
            "INCENTIVE_FOR_TAX", "RULE_FOR_TAX", "APPLIES_TO_TAX", "GAP_FOR_TAX",
            "INVOICE_FOR_TAX", "AUDIT_FOR_TAX", "RISK_FOR_TAX", "FILING_FOR_TAX",
            "TRIGGERS_TAX", "STACKS_WITH", "EXCLUDES", "CREATES_GAP",
            "HAS_GAP", "INSURANCE_IN_REGION", "BENCHMARK_FOR", "AUDIT_TRIGGERS",
            "OVERRIDES_IN", "PENALIZED_BY", "TRIGGERED_BY", "GOVERNED_BY",
            "CALCULATED_FROM", "SURCHARGE_OF", "RELATED_TAX",
            "PARENT_SUBJECT", "PARENT_CLAUSE", "MAPS_TO_SUBJECT",
            "PART_OF", "CHILD_OF", "ISSUED_BY", "SUPERSEDES", "AMENDS",
        }
        neighbors.sort(key=lambda n: (0 if n.get("edge_type") in BACKBONE_EDGES else 1, n.get("edge_type", "")))
        return {"node": node, "neighbors": neighbors[:100], "depth": depth}
    except Exception as e:
        raise HTTPException(400, str(e))


# === Ingest ===


@app.post("/api/v1/admin/migrate-table")
def migrate_table(payload: dict):
    """Migrate data from old table to new v2.2 table in-process.

    Runs entirely within the API process (no SSH needed).
    Uses Cypher MATCH -> CREATE in batches to avoid OOM.

    Payload: {"source": "LawOrRegulation", "target": "LegalDocument", "batch_size": 500,
              "field_map": {"id": "id", "name": "title", "type": "'规范性文件'", ...}}
    """
    conn = get_kuzu()
    source = payload.get("source", "")
    target = payload.get("target", "")
    field_map = payload.get("field_map", {})
    batch_size = payload.get("batch_size", 500)
    offset = payload.get("offset", 0)

    if not source or not target or not field_map:
        raise HTTPException(400, "source, target, field_map required")

    # Build SELECT clause from field_map
    # field_map: {new_field: "n.old_field" or "'literal'"}
    # Each column gets an alias to avoid KuzuDB "duplicate column name" error
    return_cols = []
    for i, (new_field, expr) in enumerate(field_map.items()):
        if expr.startswith("'") and expr.endswith("'"):
            return_cols.append(f"{expr} AS col_{i}")
        else:
            return_cols.append(f"n.{expr} AS col_{i}")

    query = f"MATCH (n:{source}) RETURN {', '.join(return_cols)} SKIP {offset} LIMIT {batch_size}"

    try:
        r = conn.execute(query)
    except Exception as e:
        raise HTTPException(400, f"Source query failed: {str(e)[:200]}")

    inserted = 0
    errors = 0
    new_fields = list(field_map.keys())

    # Detect INT64/DOUBLE fields from target table schema
    int_fields = set()
    double_fields = set()
    try:
        schema_r = conn.execute(f"CALL table_info('{target}') RETURN *")
        while schema_r.has_next():
            sr = schema_r.get_next()
            col_name = sr[1] if len(sr) > 1 else ""
            col_type = str(sr[2]).upper() if len(sr) > 2 else ""
            if "INT" in col_type:
                int_fields.add(col_name)
            elif "DOUBLE" in col_type or "FLOAT" in col_type:
                double_fields.add(col_name)
    except:
        pass

    while r.has_next():
        row = r.get_next()
        props = {}
        for i, field in enumerate(new_fields):
            val = row[i]
            # Type-aware conversion
            if field in int_fields:
                try:
                    props[field] = int(val) if val is not None else 0
                except (ValueError, TypeError):
                    props[field] = 0
            elif field in double_fields:
                try:
                    props[field] = float(val) if val is not None else 0.0
                except (ValueError, TypeError):
                    props[field] = 0.0
            elif val is None:
                props[field] = ""
            elif isinstance(val, (int, float)):
                props[field] = val
            else:
                props[field] = str(val)[:500]

        # Build parameterized CREATE
        param_names = [f"p{i}" for i in range(len(new_fields))]
        prop_str = ", ".join(f"{f}: ${p}" for f, p in zip(new_fields, param_names))
        params = {p: props[f] for p, f in zip(param_names, new_fields)}

        try:
            conn.execute(f"CREATE (n:{target} {{{prop_str}}})", params)
            inserted += 1
        except Exception as e:
            err = str(e)
            if "duplicate" not in err.lower() and "primary key" not in err.lower():
                errors += 1
            # Skip duplicates silently

    return {
        "source": source, "target": target,
        "inserted": inserted, "errors": errors,
        "offset": offset, "batch_size": batch_size,
    }


@app.post("/api/v1/admin/execute-ddl")
def execute_ddl(payload: dict):
    """Execute schema DDL statements (CREATE/DROP TABLE).

    Used by migration scripts. Only allows CREATE/DROP NODE/REL TABLE.
    """
    conn = get_kuzu()
    statements = payload.get("statements", [])
    if isinstance(statements, str):
        statements = [statements]

    results = []
    for stmt in statements:
        stmt = stmt.strip().rstrip(";")
        # Safety: allow CREATE/DROP TABLE + CREATE node/edge + MATCH SET for migration
        upper = stmt.upper()
        ALLOWED_PREFIXES = (
            "CREATE NODE TABLE", "CREATE REL TABLE", "DROP TABLE",
            "CREATE (", "MATCH (", "CREATE REL TABLE IF NOT EXISTS",
            "CREATE NODE TABLE IF NOT EXISTS", "DROP TABLE IF EXISTS",
            "ALTER TABLE",
        )
        if not any(upper.startswith(p) for p in ALLOWED_PREFIXES):
            results.append({"statement": stmt[:80], "status": "REJECTED", "reason": "Not in allowed prefix list"})
            continue
        try:
            conn.execute(stmt)
            results.append({"statement": stmt[:80], "status": "OK"})
        except Exception as e:
            err = str(e)
            if "already exists" in err.lower() or "exist" in err.lower():
                results.append({"statement": stmt[:80], "status": "SKIP", "reason": "already exists"})
            else:
                results.append({"statement": stmt[:80], "status": "ERROR", "reason": err[:200]})

    ok = sum(1 for r in results if r["status"] == "OK")
    skip = sum(1 for r in results if r["status"] == "SKIP")
    err = sum(1 for r in results if r["status"] == "ERROR")
    return {"total": len(results), "ok": ok, "skipped": skip, "errors": err, "results": results}


@app.post("/api/v1/admin/alter-table")
def alter_table(payload: dict):
    """Add missing columns to a node table."""
    conn = get_kuzu()
    table = payload.get("table", "LawOrRegulation")

    # Full expected schema
    expected_cols = {
        "title": "STRING",
        "fullText": "STRING",
        "sourceUrl": "STRING",
        "regulationNumber": "STRING",
        "effectiveDate": "STRING",
        "hierarchyLevel": "STRING",
        "regulationType": "STRING",
        "createdAt": "STRING",
    }

    added = []
    errors = []
    for col, dtype in expected_cols.items():
        try:
            conn.execute("ALTER TABLE " + table + " ADD " + col + " " + dtype + " DEFAULT ''")
            added.append(col)
        except Exception as e:
            err_str = str(e)
            if "already exists" in err_str.lower() or "exist" in err_str.lower():
                pass  # Column already exists, fine
            else:
                errors.append(f"{col}: {err_str[:100]}")

    # Verify schema
    try:
        r = conn.execute("CALL table_info('" + table + "') RETURN *")
        cols_found = []
        while r.has_next():
            row = r.get_next()
            cols_found.append(row[1] if len(row) > 1 else str(row))
    except:
        cols_found = ["(could not read)"]

    return {"table": table, "added": added, "errors": errors, "current_columns": cols_found}


@app.post("/api/v1/admin/fix-titles")
def fix_titles(payload: dict):
    """Batch-fix empty titles by copying from alternative fields.

    For each table, maps a source field to the title field.
    This handles KuzuDB's single-process lock by running inside the API process.
    """
    conn = get_kuzu()
    dry_run = payload.get("dry_run", True)

    # Table -> (title_target, source_fields_in_priority_order)
    FIELD_MAP = {
        "MindmapNode": ("node_text", []),  # node_text IS the label; no title field to fix
        "RegulationClause": ("title", ["fullText"]),
        "CPAKnowledge": ("title", ["topic", "content"]),
        "TaxRateMapping": ("title", ["productCategory", "rateLabel"]),
        "TaxType": ("title", ["name"]),
        "TaxCodeRegionRate": ("title", ["item_name"]),
        "TaxClassificationCode": ("title", ["name", "code"]),
        "TaxCodeDetail": ("title", ["name", "description"]),
        "TaxCodeIndustryMap": ("title", ["name", "industry_name"]),
        "IndustryRiskProfile": ("title", ["name", "industry"]),
        "RegionalTaxPolicy": ("title", ["name", "policy_name"]),
        "AccountingEntry": ("title", ["name", "description", "scenario"]),
        "AccountRuleMapping": ("title", ["name", "rule_name"]),
        "TaxRiskScenario": ("title", ["name", "scenario"]),
        "IndustryKnowledge": ("title", ["name", "topic"]),
        "TaxCreditIndicator": ("title", ["name", "indicator"]),
        "TaxRateDetail": ("title", ["name", "description"]),
        "TaxRateSchedule": ("title", ["name", "description"]),
        "TaxPolicy": ("title", ["name", "policy_name"]),
        "AccountingStandard": ("title", ["name", "casNumber"]),
        "Industry": ("title", ["name", "gbCode"]),
        "Region": ("title", ["name", "regionType"]),
        "FTIndustry": ("title", ["name", "gbCode"]),
        "IndustryBookkeeping": ("title", ["name", "method"]),
    }

    results = {}
    total_fixed = 0

    for tbl, (title_field, sources) in FIELD_MAP.items():
        # Check if table has the title field
        has_title_field = True
        try:
            conn.execute(f"MATCH (n:{tbl}) RETURN n.{title_field} LIMIT 1")
        except:
            has_title_field = False

        if not has_title_field:
            # Table doesn't have title field — try to add it
            try:
                conn.execute(f"ALTER TABLE {tbl} ADD title STRING DEFAULT ''")
            except:
                pass  # Already exists or can't add

        fixed = 0
        for src_field in sources:
            if fixed > 0:
                break  # Already found a working source
            try:
                # Count nodes needing fix
                r = conn.execute(
                    f"MATCH (n:{tbl}) WHERE (n.{title_field} IS NULL OR size(n.{title_field}) < 5) "
                    f"AND n.{src_field} IS NOT NULL AND size(n.{src_field}) >= 5 "
                    f"RETURN count(n)"
                )
                count = r.get_next()[0]
                if count == 0:
                    continue

                if dry_run:
                    fixed = count
                    continue

                # Apply fix: fetch IDs + source values, then update one by one
                # KuzuDB SET with function expressions can be unreliable,
                # so we do it row-by-row for safety
                r2 = conn.execute(
                    f"MATCH (n:{tbl}) WHERE (n.{title_field} IS NULL OR size(n.{title_field}) < 5) "
                    f"AND n.{src_field} IS NOT NULL AND size(n.{src_field}) >= 5 "
                    f"RETURN n.id, n.{src_field} LIMIT 1000"
                )
                batch_fixed = 0
                while r2.has_next():
                    row = r2.get_next()
                    nid = row[0]
                    src_val = str(row[1] or "")[:80]
                    if len(src_val) < 5:
                        continue
                    try:
                        conn.execute(
                            f"MATCH (n:{tbl}) WHERE n.id = $nid SET n.{title_field} = $val",
                            {"nid": nid, "val": src_val}
                        )
                        batch_fixed += 1
                    except:
                        pass
                fixed = batch_fixed
            except Exception as e:
                # Field doesn't exist or other error — try next source
                continue

        if fixed > 0:
            results[tbl] = {"fixed": fixed, "source": sources[0] if sources else "N/A"}
            total_fixed += fixed

    return {
        "dry_run": dry_run,
        "total_fixed": total_fixed,
        "details": results,
    }


@app.post("/api/v1/admin/enrich-edges")
def enrich_edges(payload: dict):
    """Create MENTIONS edges between content nodes and TaxType based on keyword matching.

    Fixes the isolated TaxType problem by finding content that mentions each tax.
    """
    conn = get_kuzu()
    dry_run = payload.get("dry_run", True)

    # Auto-discover TaxType IDs and match to Chinese keywords
    # IDs must match actual DB data (verified via /api/v1/nodes?type=TaxType)
    TAX_KEYWORDS = {
        "TT_VAT": ["增值税"],
        "TT_CIT": ["企业所得税"],
        "TT_PIT": ["个人所得税", "个税"],
        "TT_CONSUMPTION": ["消费税"],
        "TT_RESOURCE": ["资源税"],
        "TT_PROPERTY": ["房产税"],
        "TT_VEHICLE": ["车船税"],
        "TT_CONTRACT": ["契税"],           # was TT_DEED
        "TT_STAMP": ["印花税"],
        "TT_TARIFF": ["关税"],             # was TT_CUSTOMS
        "TT_URBAN": ["城市维护建设税", "城建税"],  # was TT_URBAN_MAINTENANCE
        "TT_CULTIVATED": ["耕地占用税"],    # was TT_FARMLAND
        "TT_TOBACCO": ["烟叶税"],
        "TT_LAND_VAT": ["土地增值税"],
        "TT_LAND_USE": ["城镇土地使用税"],  # was TT_URBAN_LAND
        "TT_ENV": ["环境保护税", "环保税"],
        "TT_EDUCATION": ["教育费附加"],
        "TT_LOCAL_EDU": ["地方教育附加"],
        "TT_TONNAGE": ["船舶吨税"],
    }

    # Content tables and their text fields
    CONTENT_SOURCES = [
        ("DocumentSection", "content"),
        ("LawOrRegulation", "title"),
        ("CPAKnowledge", "content"),
    ]

    results = {}
    total_created = 0

    # Ensure MENTIONS edge tables exist
    for src_tbl, _ in CONTENT_SOURCES:
        try:
            conn.execute(f"MATCH ()-[r:MENTIONS]->() RETURN count(r) LIMIT 1")
        except:
            try:
                conn.execute(f"CREATE REL TABLE IF NOT EXISTS MENTIONS (FROM {src_tbl} TO TaxType)")
            except:
                pass

    for tax_id, keywords in TAX_KEYWORDS.items():
        tax_total = 0
        for src_tbl, text_field in CONTENT_SOURCES:
            for kw in keywords:
                try:
                    r = conn.execute(
                        f"MATCH (d:{src_tbl}) WHERE d.{text_field} CONTAINS $kw "
                        f"RETURN count(d)",
                        {"kw": kw}
                    )
                    match_count = min(r.get_next()[0], 50)  # Cap at 50 per keyword
                    if match_count == 0:
                        continue

                    if not dry_run:
                        # Create edges (limited batch)
                        try:
                            conn.execute(
                                f"MATCH (d:{src_tbl}), (t:TaxType {{id: $tid}}) "
                                f"WHERE d.{text_field} CONTAINS $kw "
                                f"CREATE (d)-[:MENTIONS]->(t)",
                                {"kw": kw, "tid": tax_id}
                            )
                        except:
                            pass

                    tax_total += match_count
                except:
                    continue

        if tax_total > 0:
            results[tax_id] = {"keyword": keywords[0], "edges": tax_total}
            total_created += tax_total

    return {
        "dry_run": dry_run,
        "total_edges_created": total_created,
        "details": results,
    }


@app.post("/api/v1/admin/reset-table")
def reset_table(payload: dict):
    """Drop and recreate a node table with full schema. Use with caution."""
    conn = get_kuzu()
    table = payload.get("table", "LawOrRegulation")

    # Drop if exists
    try:
        conn.execute("DROP TABLE IF EXISTS " + table)
    except Exception as e:
        pass  # Table may not exist

    # Create with full schema
    create_sql = (
        "CREATE NODE TABLE IF NOT EXISTS " + table + " ("
        "id STRING PRIMARY KEY, "
        "title STRING, "
        "fullText STRING, "
        "sourceUrl STRING, "
        "regulationNumber STRING, "
        "effectiveDate STRING, "
        "hierarchyLevel STRING, "
        "regulationType STRING, "
        "createdAt STRING DEFAULT ''"
        ")"
    )
    conn.execute(create_sql)

    # Verify
    r = conn.execute("MATCH (n:" + table + ") RETURN count(n)")
    count = r.get_next()[0]
    return {"status": "ok", "table": table, "count": count}


@app.post("/api/v1/ingest")
def ingest(payload: dict):
    """Batch-ingest nodes with quality gate enforcement.

    Gate checks: title >= 5 chars, content >= 20 chars, no raw ID leaks.
    Returns rejected nodes with reasons for upstream correction.
    """
    conn = get_kuzu()
    table = payload.get("table", "LawOrRegulation")
    nodes = payload.get("nodes", [])

    if not nodes:
        return {"table": table, "inserted": 0, "errors": 0, "skipped": 0, "rejected": []}

    # Pre-validate all nodes
    valid_nodes = []
    rejected = []
    # Tables exempt from content length check (metadata-only tables)
    metadata_tables = {
        "TaxType", "Region", "Industry", "TaxCalendar", "TaxpayerStatus",
        # v2.2 metadata tables (seed data, short content is expected)
        "TaxEntity", "IssuingBody", "FilingFormV2", "BusinessActivity",
        "ComplianceRuleV2", "RiskIndicatorV2", "Penalty", "AuditTrigger",
        "AccountingSubject", "Classification",
    }

    for i, node in enumerate(nodes):
        nid = (node.get("id") or "").strip()
        title = (node.get("title") or "").strip()
        content = (node.get("fullText") or node.get("content") or "").strip()

        if not nid:
            rejected.append({"index": i, "reason": "missing_id"})
            continue
        if len(title) < QG_TITLE_MIN_LEN:
            rejected.append({"index": i, "id": nid, "reason": f"title_too_short ({len(title)}<{QG_TITLE_MIN_LEN})"})
            continue
        if len(content) < QG_CONTENT_MIN_LEN and table not in metadata_tables:
            rejected.append({"index": i, "id": nid, "reason": f"content_too_short ({len(content)}<{QG_CONTENT_MIN_LEN})"})
            continue
        if title.startswith("{'_id':") or title.startswith("{'offset':"):
            rejected.append({"index": i, "id": nid, "reason": "title_is_raw_id"})
            continue

        valid_nodes.append(node)

    inserted = 0
    errors = 0
    skipped = 0
    first_error = None
    for node in valid_nodes:
        nid = node.get("id", "")
        title = node.get("title", "")
        if not nid or len(title) < 3:
            skipped += 1
            continue

        # Dedup check
        try:
            r = conn.execute(
                "MATCH (n:" + table + ") WHERE n.id = $nid RETURN count(n)",
                {"nid": nid},
            )
            if r.get_next()[0] > 0:
                skipped += 1
                continue
        except:
            pass

        try:
            # Only set STRING columns to avoid DATE/INT64/TIMESTAMP type errors
            conn.execute(
                "CREATE (n:" + table + " {"
                "id: $id, "
                "title: $title, "
                "fullText: $fullText, "
                "sourceUrl: $sourceUrl, "
                "regulationNumber: $regulationNumber, "
                "regulationType: $regulationType, "
                "issuingAuthority: $issuingAuthority, "
                "status: $status"
                "})",
                {
                    "id": nid,
                    "title": (title or "")[:500],
                    "fullText": (node.get("fullText") or node.get("content") or "")[:5000],
                    "sourceUrl": (node.get("sourceUrl") or node.get("url") or "")[:500],
                    "regulationNumber": (node.get("regulationNumber") or node.get("doc_num") or "")[:200],
                    "regulationType": (node.get("regulationType") or node.get("type") or "crawl")[:100],
                    "issuingAuthority": (node.get("issuingAuthority") or node.get("source") or "")[:200],
                    "status": (node.get("status") or "active")[:50],
                },
            )
            inserted += 1
        except Exception as e:
            errors += 1
            if first_error is None:
                first_error = str(e)[:200]

    result = {"table": table, "inserted": inserted, "errors": errors, "skipped": skipped}
    if first_error:
        result["first_error"] = first_error
    if rejected:
        result["rejected"] = rejected[:50]
        result["rejected_count"] = len(rejected)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)


# ═══════════════════════════════════════════════════════════════════
# AI Chat Endpoint — Gemini RAG (Vector Search → Context → Answer)
# ═══════════════════════════════════════════════════════════════════
from pydantic import BaseModel as _BaseModel


class ChatRequest(_BaseModel):
    question: str
    mode: str = "rag"  # rag | cypher
    limit: int = 8


class ChatResponse(_BaseModel):
    answer: str
    sources: list = []
    cypher: str = ""
    html: str = ""
    mode: str = "rag"
    tokens_used: int = 0


def _gemini_generate(prompt: str, system: str = "", model: str = "gemini-2.5-flash") -> str:
    """Call LLM via Poe API (OpenAI-compatible) for text generation.

    Falls back to Google Gemini API if POE_API_KEY is not set.
    """
    import urllib.request as _urlreq
    import urllib.error as _urlerr

    poe_key = os.environ.get("POE_API_KEY", "")
    if poe_key:
        # Poe API path (OpenAI-compatible)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }).encode()
        req = _urlreq.Request(
            "https://api.poe.com/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {poe_key}"},
        )
        try:
            with _urlreq.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[ERROR] Poe API failed: {str(e)[:200]}"

    # Fallback: Google Gemini API
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "[ERROR] Neither POE_API_KEY nor GEMINI_API_KEY set"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"[System Instructions]\n{system}"}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    payload = json.dumps({
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }).encode()
    req = _urlreq.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[ERROR] Gemini generation failed: {str(e)[:200]}"


def _embed_query(text: str) -> list:
    """Generate embedding vector for query text."""
    import urllib.request as _urlreq
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:embedContent?key={api_key}"
    payload = json.dumps({
        "model": "models/gemini-embedding-2-preview",
        "content": {"parts": [{"text": text[:2048]}]},
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": 768,
    }).encode()
    req = _urlreq.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["embedding"]["values"]
    except:
        return None


def _rag_search_context(question: str, limit: int = 8) -> tuple:
    """Search KuzuDB text + structured data to build RAG context."""
    import re as _re_rag
    conn = get_kuzu()
    sources = []
    context_parts = []

    # Step 1: Cypher text search (primary — replaces broken vector search)
    search_results = _cypher_text_search(conn, question, limit * 2)
    for r in search_results[:limit]:
        src = {"id": r["id"], "text": r["text"], "table": r["table"], "score": r["score"]}
        sources.append(src)
        context_parts.append(f"[{r['table']}] {r['id']}: {r.get('title', '')} — {r['text']}")

    # Step 1.5: Domain-aware keyword extraction for broader coverage
    # Uses a dictionary of known tax/finance terms to avoid naive bigram pollution
    # (e.g., "小规模纳税人" should NOT be split into "小规" which matches "小规格木材")
    DOMAIN_TERMS = [
        "小规模纳税人", "一般纳税人", "增值税", "企业所得税", "个人所得税", "消费税",
        "土地增值税", "房产税", "印花税", "契税", "关税", "车船税", "资源税", "环保税",
        "城建税", "教育费附加", "税收优惠", "减免税", "加计扣除", "即征即退",
        "纳税申报", "汇算清缴", "税务登记", "发票管理", "进项税额", "销项税额",
        "小微企业", "高新技术", "研发费用", "固定资产", "无形资产",
        "社保", "公积金", "养老保险", "医疗保险", "失业保险", "工伤保险",
        "税会差异", "纳税调整", "视同销售", "税前扣除", "税收征管",
        "合规", "风险", "稽查", "处罚", "罚款", "滞纳金",
    ]
    if len(question) > 2:
        # First: extract known domain terms from question
        terms = []
        for dt in DOMAIN_TERMS:
            if dt in question and dt not in terms:
                terms.append(dt)
        # Second: split remainder on particles, keep 2-4 char chunks
        raw_terms = _re_rag.split(
            r'[，。？！、的了在是有和与或及其对于关于如何什么哪些可以怎么为被将把各多少几个 ]',
            question,
        )
        for t in raw_terms:
            t = t.strip()
            if 2 <= len(t) <= 4 and t not in terms:
                terms.append(t)
            elif len(t) > 4 and t not in terms:
                # Non-overlapping 2-char split (NOT overlapping bigrams)
                for i in range(0, len(t) - 1, 2):
                    bi = t[i:i+2]
                    if bi not in terms and len(bi) == 2:
                        terms.append(bi)
        # Filter out subterms that are substrings of already-found domain terms
        # e.g., "小规" is a substring of "小规模纳税人" → remove to avoid "小规格木材" pollution
        found_domain = [t for t in terms if t in DOMAIN_TERMS]
        if found_domain:
            terms = [t for t in terms if t in DOMAIN_TERMS or not any(t in dt for dt in found_domain)]
        seen_ids = {s["id"] for s in sources}
        for term in terms[:5]:
            if term == question:
                continue
            extra = _cypher_text_search(conn, term, 5)
            for r in extra:
                if r["id"] not in seen_ids:
                    sources.append({"id": r["id"], "text": r["text"], "table": r["table"], "score": r["score"],
                                    "title": r.get("title", "")})
                    context_parts.append(f"[{r['table']}] {r['id']}: {r.get('title', '')} — {r['text']}")
                    seen_ids.add(r["id"])

    # Step 2: Structured KuzuDB queries for common domain patterns
    keywords = question.lower()
    struct_queries = [
        ("TaxType",
         "MATCH (t:TaxType) RETURN t.name, t.code, t.minRate, t.maxRate, t.rateStructure, t.filingFrequency LIMIT 25",
         ["税", "税率", "税种", "增值税", "所得税", "对比"]),
        ("TaxIncentive",
         "MATCH (i:TaxIncentive) RETURN i.name, i.incentiveType, i.value, i.eligibilityCriteria LIMIT 15",
         ["优惠", "减免", "incentive", "减税", "退税", "免征"]),
        ("TaxAccountingGap",
         "MATCH (g:TaxAccountingGap) RETURN g.name, g.gapType, g.accountingTreatment, g.taxTreatment LIMIT 15",
         ["税会差异", "差异", "会计处理", "纳税调整"]),
        ("SocialInsuranceRule",
         "MATCH (s:SocialInsuranceRule) RETURN s.name, s.insuranceType, s.regionId, s.employerRate, s.employeeRate LIMIT 20",
         ["社保", "公积金", "保险", "养老", "医疗", "失业", "工伤", "生育", "缴纳"]),
        ("InvoiceRule",
         "MATCH (v:InvoiceRule) RETURN v.name, v.ruleType, v.condition LIMIT 15",
         ["发票", "开票", "电子发票", "专票", "普票"]),
        ("IndustryBenchmark",
         "MATCH (b:IndustryBenchmark) RETURN b.ratioName, b.industryCode, b.minValue, b.maxValue, b.unit LIMIT 15",
         ["行业", "基准", "税负率", "预警"]),
        ("AccountingStandard",
         "MATCH (a:AccountingStandard) RETURN a.name, a.casNumber, a.scope LIMIT 15",
         ["准则", "会计", "accounting"]),
    ]
    for tbl_name, cypher, triggers in struct_queries:
        if any(k in keywords for k in triggers):
            try:
                r = conn.execute(cypher)
                cols = r.get_column_names()
                rows = []
                while r.has_next():
                    row = r.get_next()
                    rows.append([str(v) if v is not None else "" for v in row])
                if rows:
                    header = " | ".join(cols)
                    context_parts.append(f"[Structured {tbl_name}] {header}")
                    for row in rows:
                        context_parts.append(" | ".join(row))
            except Exception:
                pass

    # Step 3: Graph expansion for top results
    for src in sources[:3]:
        if not src["id"]:
            continue
        safe_id = src["id"].replace("'", "\\'")
        for tbl_name in ["TaxType", "TaxIncentive", "ComplianceRule", "TaxRate",
                         "LegalClause", "RiskIndicator", "SocialInsuranceRule"]:
            try:
                r = conn.execute(
                    f"MATCH (n:{tbl_name})-[e]->(m) WHERE n.id = '{safe_id}' "
                    f"RETURN label(e) AS rel, label(m) AS tgt_type, m.id AS tgt_id, m.name AS tgt_name LIMIT 5"
                )
                while r.has_next():
                    row = r.get_next()
                    context_parts.append(f"  -> [{row[0]}] {row[1]}: {row[2]} ({row[3] or ''})")
            except Exception:
                continue

    context = "\n".join(context_parts[:40])  # Cap at 40 entries (up from 30)
    return context, sources, context_parts


SYSTEM_PROMPT_RAG = """你是 CogNebula 业财税知识图谱的 AI 助手。你基于知识图谱中的真实数据回答问题。

## 核心规则
1. 只根据提供的上下文回答，不编造信息
2. 引用具体法规文号、条款编号
3. 回答使用中文，专业术语保持准确
4. 结构化输出：先给结论，再展开细节

## Generative UI 输出规则（重要）
当回答涉及以下场景时，你必须在普通文字回答之后，额外输出一个 `<!--GENUI-->` 标记包裹的自包含 HTML 代码块，用于前端渲染为交互式可视化：

**必须生成 HTML 的场景：**
- 税率对比（用柱状图/表格）
- 时间线（法规生效/废止时间线用 SVG）
- 流程图（申报流程、合规检查流程）
- 数据汇总（多税种/多行业对比表格）
- 关系图解（实体之间的关系用 SVG 连线图）

**HTML 生成规范：**
```
<!--GENUI-->
<!DOCTYPE html>
<html>
<head><style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; padding: 20px; color: var(--text, #1F2937); background: var(--bg, #FFFFFF); }
  /* 你的样式 */
</style></head>
<body>
  <!-- 你的可视化内容 -->
  <script>
    // 可选的交互脚本
    // 发送高度给父窗口
    new ResizeObserver(() => {
      parent.postMessage({type:'resize', height: document.body.scrollHeight}, '*');
    }).observe(document.body);
  </script>
</body>
</html>
<!--/GENUI-->
```

**HTML 质量要求：**
- 完全自包含（不引用外部 CDN）
- 使用 CSS 变量 `var(--text)` `var(--bg)` `var(--primary)` `var(--border)` 适配明暗主题
- SVG 图表优先（轻量、矢量、不依赖库）
- 数据直接内联（不从外部 fetch）
- 最后一行必须有 ResizeObserver 脚本发送高度
- 表格必须有 hover 效果和斑马纹
- 图表必须有标签和图例
- 颜色使用语义化：红=税务风险/法律、蓝=税种、绿=优惠/收益、紫=会计准则"""


SYSTEM_PROMPT_CYPHER = """你是 CogNebula 知识图谱的 Cypher 查询生成器。用户用自然语言提问，你生成 KuzuDB Cypher 查询。

图谱中的主要节点类型：
- TaxType (id, name, code, minRate, maxRate, rateStructure, filingFrequency)
- LawOrRegulation (id, title, regulationNumber, effectiveDate, fullText, hierarchyLevel)
- FAQEntry (id, question, answer, category, source)
- CPAKnowledge (id, title, content, chapter, subject)
- AccountingStandard (id, name, casNumber, scope, effectiveDate)
- TaxIncentive (id, name, incentiveType, value, eligibilityCriteria)
- ComplianceRule (id, name, ruleCode, category, conditionFormula)
- DocumentSection (id, title, content, sectionNumber)
- Region (id, name, regionType)
- Industry (id, name, gbCode)
- ChartOfAccount (id, code, name, category, direction)

主要关系类型：
- FT_GOVERNED_BY, FT_APPLIES_TO, FT_QUALIFIES_FOR, FT_INCENTIVE_TAX
- FT_SUBJECT_TO, FT_MAPS_TO, FT_REFERENCES, FT_AFFECTS
- OP_DEBITS, OP_CREDITS, CO_VIOLATES, CO_PENALIZED_BY

规则：
1. 只生成 READ 查询（MATCH/RETURN/WHERE），禁止 CREATE/DELETE/DROP
2. 始终加 LIMIT（默认 20）
3. 输出格式：先输出 Cypher 查询（用 ```cypher 包裹），再用一句话解释查询意图
4. 如果用户问题不适合 Cypher 查询，说明原因"""


@app.post("/api/v1/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question is required")

    if req.mode == "cypher":
        # Generate Cypher query from natural language
        answer = _gemini_generate(
            prompt=f"用户问题：{question}\n\n请生成对应的 Cypher 查询。",
            system=SYSTEM_PROMPT_CYPHER,
        )
        # Try to extract and execute the Cypher
        import re as _re
        cypher_match = _re.search(r"```cypher\s*(.*?)\s*```", answer, _re.DOTALL)
        cypher = cypher_match.group(1).strip() if cypher_match else ""

        sources = []
        if cypher:
            try:
                conn = get_kuzu()
                result = conn.execute(cypher)
                rows = []
                cols = result.get_column_names()
                while result.has_next() and len(rows) < 20:
                    row = result.get_next()
                    rows.append([str(v)[:200] if v is not None else None for v in row])
                sources = [{"columns": cols, "rows": rows, "count": len(rows)}]
            except Exception as e:
                answer += f"\n\n[Query execution error: {str(e)[:200]}]"

        return ChatResponse(
            answer=answer,
            sources=sources,
            cypher=cypher,
            mode="cypher",
        )

    else:
        # RAG mode: search → context → generate
        context, sources, context_parts = _rag_search_context(question, req.limit)

        if not context.strip():
            return ChatResponse(
                answer="未找到与您问题相关的知识图谱数据。请尝试更具体的关键词，例如：增值税税率、小规模纳税人、企业所得税优惠等。",
                sources=[],
                mode="rag",
            )

        prompt = f"""基于以下知识图谱上下文回答用户的问题。

## 知识图谱上下文
{context}

## 用户问题
{question}

请给出准确、结构化的回答。"""

        answer = _gemini_generate(prompt=prompt, system=SYSTEM_PROMPT_RAG)

        # Fallback: if LLM fails (429/error), build readable structured answer
        if answer.startswith("[ERROR]"):
            # Table name → Chinese label mapping
            TABLE_ZH = {
                "TaxType": "税种", "TaxRate": "税率", "TaxIncentive": "税收优惠",
                "ComplianceRule": "合规规则", "RiskIndicator": "风险指标",
                "TaxAccountingGap": "税会差异", "SocialInsuranceRule": "社保规则",
                "InvoiceRule": "发票规则", "IndustryBenchmark": "行业基准",
                "AuditTrigger": "审计触发", "Penalty": "处罚", "FilingForm": "申报表",
                "TaxEntity": "纳税主体", "BusinessActivity": "业务活动",
                "AccountingSubject": "会计科目", "LegalDocument": "法规文件",
                "LegalClause": "法规条款", "KnowledgeUnit": "知识",
                "FAQEntry": "问答", "CPAKnowledge": "CPA知识",
                "Classification": "分类", "Region": "地区", "IssuingBody": "发布机构",
            }
            fallback_lines = [f"以下是知识图谱中与「{question}」相关的数据：\n"]
            seen_names = set()
            # Include search results (deduplicated by name)
            for _src in sources[:8]:
                _title = _src.get("title", _src.get("text", "")[:60])
                if _title in seen_names:
                    continue
                seen_names.add(_title)
                _table = _src.get("table", "")
                _label = TABLE_ZH.get(_table, _table)
                _text = _src.get("text", "")
                if _text and _text != _title and len(_text) > 10:
                    fallback_lines.append(f"[{_label}] {_title}\n  {_text[:200]}\n")
                else:
                    fallback_lines.append(f"[{_label}] {_title}")
            # Include structured query data in readable format (not raw pipes)
            for _cp in context_parts:
                if _cp.startswith("[Structured "):
                    # Extract table name and format as section header
                    import re as _re_fb
                    _m = _re_fb.match(r'\[Structured (\w+)\] (.*)', _cp)
                    if _m:
                        _tbl = _m.group(1)
                        _label = TABLE_ZH.get(_tbl, _tbl)
                        fallback_lines.append(f"\n--- {_label}数据 ---")
                elif " | " in _cp and not _cp.startswith("["):
                    # Data row: convert pipe format to readable Chinese text
                    FIELD_ZH = {
                        "tiered": "分级税率", "flat": "固定费率", "progressive_7tier": "7级累进",
                        "progressive_4tier": "4级超率累进", "flat_with_incentives": "固定+优惠",
                        "tiered_by_good": "按商品分级", "tiered_by_hs": "按HS编码",
                        "tiered_by_location": "按地区", "tiered_by_resource": "按资源",
                        "tiered_by_area": "按面积", "tiered_by_displacement": "按排量",
                        "tiered_by_contract": "按合同", "dual_method": "从价从量复合",
                        "monthly": "月报", "quarterly": "季报", "annual": "年报",
                        "per_shipment": "逐票", "per_transaction": "逐笔",
                        "NATIONAL": "全国", "exemption": "免征", "rate_reduction": "减征",
                        "refund": "退税", "deduction": "扣除", "timing": "时间性差异",
                        "permanent": "永久性差异",
                    }
                    fields = [f.strip() for f in _cp.split("|")]
                    if fields and fields[0]:
                        readable = fields[0]
                        details = []
                        for f in fields[1:]:
                            f = f.strip()
                            if f and f != "None" and f != "":
                                details.append(FIELD_ZH.get(f, f))
                        if details:
                            readable += " (" + ", ".join(details[:4]) + ")"
                        if readable not in seen_names:
                            fallback_lines.append(f"  {readable}")
                            seen_names.add(readable)
            if len(fallback_lines) > 1:
                answer = "\n".join(fallback_lines)
            else:
                answer = "暂时无法生成 AI 回答（LLM 服务繁忙），但已在知识图谱中找到相关数据。请查看下方来源。"

        # Extract GENUI HTML if present
        import re as _re2
        genui_match = _re2.search(r"<!--GENUI-->(.*?)<!--/GENUI-->", answer, _re2.DOTALL)
        genui_html = ""
        clean_answer = answer
        if genui_match:
            genui_html = genui_match.group(1).strip()
            clean_answer = answer[:genui_match.start()].strip()

        return ChatResponse(
            answer=clean_answer,
            sources=[{"id": s["id"], "table": s["table"], "score": s.get("score", 0)} for s in sources[:5]],
            html=genui_html,
            mode="rag",
        )
