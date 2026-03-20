"""CogNebula Finance/Tax Knowledge Graph API + Web UI.

Single-process FastAPI service exposing KuzuDB graph queries and
LanceDB vector search. Handles KuzuDB single-process lock gracefully.

Usage:
    uvicorn src.api.kg_api:app --host 0.0.0.0 --port 8400
"""
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

import httpx
import kuzu
import lancedb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kg_api")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GRAPH_PATH = PROJECT_ROOT / "data" / "finance-tax-graph"
LANCE_PATH = PROJECT_ROOT / "data" / "finance-tax-lance"
WEB_DIR = PROJECT_ROOT / "src" / "web"

# All known node tables (from cognebula.py schema)
NODE_TABLES = [
    "LawOrRegulation", "RegulationClause", "TaxType", "TaxpayerStatus",
    "EnterpriseType", "PersonalIncomeType", "AccountingStandard", "TaxIncentive",
    "FTIndustry", "AdministrativeRegion", "SpecialZone", "TaxAuthority",
    "FilingObligation", "TaxRateVersion", "HSCode",
    "AccountEntry", "ChartOfAccount", "JournalTemplate", "FinancialStatement",
    "FilingForm", "TaxRateMapping", "IndustryBookkeeping", "LifecycleStage",
    "LifecycleActivity", "ComplianceRule", "RiskIndicator", "AuditTrigger",
    "Penalty", "ComplianceChecklist", "TaxCalendar", "TaxPlanningStrategy",
    "EntityTypeProfile", "AdminRegion",
    # Additional tables discovered in stats
    "DocumentSection", "MindmapNode", "CPAKnowledge", "TaxClassificationCode",
    "TaxCodeDetail", "TaxCodeRegionRate", "TaxCodeIndustryMap", "FAQEntry",
    "IndustryRiskProfile", "RegionalTaxPolicy", "AccountingEntry",
    "SpreadsheetEntry", "AccountRuleMapping", "TaxRiskScenario",
    "ChartOfAccountDetail", "IndustryKnowledge", "TaxCreditIndicator",
    "Region", "Industry", "TaxPolicy", "TaxRateDetail", "TaxWarningIndicator",
]

# TaxRateMapping human-readable labels (code -> Chinese)
TRM_LABELS = {
    "TRM_TRANSPORT": "交通运输业", "TRM_FINANCE": "金融业", "TRM_TELECOM": "电信业",
    "TRM_SOFTWARE": "软件业", "TRM_AGRI": "农业", "TRM_EXPORT": "出口",
    "TRM_REALESTATE": "房地产业", "TRM_CONSTRUCT": "建筑业", "TRM_SERVICE": "现代服务业",
    "TRM_GOODS": "货物销售", "TRM_CATERING": "餐饮业", "TRM_CULTURE": "文化业",
    "TRM_EDUCATION": "教育", "TRM_MEDICAL": "医疗", "TRM_LOGISTICS": "物流业",
    "TRM_ENERGY": "能源业", "TRM_MINING": "采矿业", "TRM_RETAIL": "零售业",
}

# Node type colors for vis.js
NODE_COLORS = {
    "LawOrRegulation": "#e74c3c",
    "RegulationClause": "#e67e22",
    "TaxType": "#3498db",
    "FTIndustry": "#2ecc71",
    "HSCode": "#9b59b6",
    "TaxIncentive": "#1abc9c",
    "AccountingStandard": "#f39c12",
    "AdminRegion": "#34495e",
    "AdministrativeRegion": "#34495e",
    "ComplianceRule": "#e91e63",
    "AccountEntry": "#00bcd4",
    "ChartOfAccount": "#8bc34a",
}
DEFAULT_COLOR = "#95a5a6"

# Read-only safety: block write queries
EMBEDDING_DIM = 768
EMBED_MODEL = "gemini-embedding-2-preview"
GEMINI_EMBED_BASE = os.environ.get(
    "GEMINI_EMBED_BASE",
    "https://gemini-api-proxy.maoyuan-wen-683.workers.dev"
)
EMBED_URL = f"{GEMINI_EMBED_BASE}/v1beta/models/{EMBED_MODEL}:embedContent"

_http_client: Optional[httpx.Client] = None


def _get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for p in [Path.home() / ".openclaw" / ".env", Path(".env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def _embed_text(text: str) -> list:
    """Embed text using Gemini Embedding API."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client()
    api_key = _get_api_key()
    if not api_key:
        return None
    body = {
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text[:2000]}]},
        "outputDimensionality": EMBEDDING_DIM,
    }
    try:
        resp = _http_client.post(f"{EMBED_URL}?key={api_key}", json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()["embedding"]["values"]
    except Exception as e:
        log.warning("Embed failed: %s", e)
        return None


WRITE_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|DETACH|CREATE|ALTER|COPY|SET|MERGE|REMOVE)\b", re.IGNORECASE
)

# ── Singleton DB connections ──────────────────────────────────────────
_db_lock = threading.Lock()
_kuzu_db: Optional[kuzu.Database] = None
_kuzu_conn: Optional[kuzu.Connection] = None
_lance_db = None
_degraded = False
_start_time = time.time()


def _init_kuzu(retries=3, delay=2.0):
    global _kuzu_db, _kuzu_conn, _degraded
    for attempt in range(retries):
        try:
            _kuzu_db = kuzu.Database(str(GRAPH_PATH))
            _kuzu_conn = kuzu.Connection(_kuzu_db)
            _degraded = False
            log.info("KuzuDB connected: %s", GRAPH_PATH)
            return
        except Exception as e:
            log.warning("KuzuDB connect attempt %d failed: %s", attempt + 1, e)
            if attempt < retries - 1:
                time.sleep(delay)
    _degraded = True
    log.warning("KuzuDB unavailable, starting in degraded mode")


def _init_lance():
    global _lance_db
    try:
        _lance_db = lancedb.connect(str(LANCE_PATH))
        log.info("LanceDB connected: %s", LANCE_PATH)
    except Exception as e:
        log.warning("LanceDB connect failed: %s", e)


def _execute_cypher(query: str, params: dict = None):
    """Thread-safe Cypher execution with lock handling."""
    global _degraded
    with _db_lock:
        if _degraded or _kuzu_conn is None:
            # Try reconnect
            try:
                _init_kuzu(retries=1, delay=0.5)
            except:
                pass
            if _degraded:
                raise HTTPException(503, detail="图数据库被占用，请稍后重试")
        try:
            return _kuzu_conn.execute(query, params or {})
        except Exception as e:
            if "lock" in str(e).lower() or "busy" in str(e).lower():
                _degraded = True
                raise HTTPException(503, detail="图数据库被占用，请稍后重试")
            raise


# ── Pydantic models ───────────────────────────────────────────────────
class CypherQuery(BaseModel):
    cypher: str
    params: dict = {}
    limit: int = 100


class SearchQuery(BaseModel):
    query: str
    limit: int = 10


# ── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(
    title="CogNebula 业财税知识图谱 API",
    version="1.0.0",
    description="Chinese Finance/Tax Knowledge Graph — Query & Explore",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    _init_kuzu()
    _init_lance()


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "degraded" if _degraded else "ok",
        "kuzu": not _degraded and _kuzu_conn is not None,
        "lance": _lance_db is not None,
        "uptime_s": int(time.time() - _start_time),
    }


@app.get("/api/stats")
def stats():
    # Try KuzuDB
    if not _degraded and _kuzu_conn is not None:
        try:
            tables = []
            total_nodes = 0
            for tbl in NODE_TABLES:
                try:
                    r = _execute_cypher(f"MATCH (n:{tbl}) RETURN count(n)")
                    cnt = r.get_next()[0]
                    if cnt > 0:
                        tables.append({"name": tbl, "count": cnt})
                        total_nodes += cnt
                except:
                    pass

            r = _execute_cypher("MATCH ()-[e]->() RETURN count(e)")
            total_edges = r.get_next()[0]

            return {
                "nodes_total": total_nodes,
                "edges_total": total_edges,
                "total_nodes": total_nodes,  # alias for pipeline scripts
                "total_edges": total_edges,  # alias for pipeline scripts
                "density": round(total_edges / total_nodes, 2) if total_nodes else 0,
                "tables": sorted(tables, key=lambda x: -x["count"]),
            }
        except HTTPException:
            pass  # Fall through to LanceDB stats

    # Fallback: LanceDB stats + cached KuzuDB stats
    if _lance_db is not None:
        try:
            tbl = _lance_db.open_table("finance_tax_embeddings")
            vec_count = tbl.count_rows()
            # Approximate from last known state
            return {
                "nodes_total": 251000,
                "edges_total": 270000,
                "density": 1.08,
                "tables": [
                    {"name": "LawOrRegulation (approx)", "count": 170000},
                    {"name": "RegulationClause (approx)", "count": 42600},
                    {"name": "HSCode (approx)", "count": 23300},
                    {"name": "LanceDB vectors", "count": vec_count},
                ],
                "source": "cached_estimate",
                "note": "图数据库被占用，显示估算统计 + 向量库实际计数",
            }
        except:
            pass

    raise HTTPException(503, detail="数据库不可用")


# ── Quality Audit API ────────────────────────────────────────────────

# Quality gate thresholds
QG_TITLE_MIN_LEN = 5          # Minimum title length (chars)
QG_CONTENT_MIN_LEN = 20       # Minimum content/fullText length
QG_TARGET_EDGE_DENSITY = 0.5  # Target edges per node
QG_TITLE_COVERAGE_TARGET = 0.95  # 95% nodes must have titles


@app.get("/api/v1/quality")
def quality_audit():
    """Audit KG data quality. Returns metrics and issues.

    Checks: title coverage, edge density, isolated nodes, label quality.
    """
    if _degraded or _kuzu_conn is None:
        raise HTTPException(503, detail="图数据库不可用")

    issues = []
    metrics = {}

    # 1. Title coverage per table
    title_stats = {}
    total_nodes = 0
    total_with_title = 0
    for tbl in NODE_TABLES:
        try:
            r = _execute_cypher(f"MATCH (n:{tbl}) RETURN count(n)")
            count = r.get_next()[0]
            if count == 0:
                continue
        except:
            continue

        # Count nodes with non-empty title
        has_title = 0
        try:
            r = _execute_cypher(
                f"MATCH (n:{tbl}) WHERE n.title IS NOT NULL AND size(n.title) >= {QG_TITLE_MIN_LEN} RETURN count(n)"
            )
            has_title = r.get_next()[0]
        except:
            # Table might not have title field — try name
            try:
                r = _execute_cypher(
                    f"MATCH (n:{tbl}) WHERE n.name IS NOT NULL AND size(n.name) >= 2 RETURN count(n)"
                )
                has_title = r.get_next()[0]
            except:
                pass

        coverage = round(has_title / count, 3) if count > 0 else 0
        title_stats[tbl] = {"total": count, "with_title": has_title, "coverage": coverage}
        total_nodes += count
        total_with_title += has_title
        if coverage < QG_TITLE_COVERAGE_TARGET:
            issues.append({
                "severity": "high" if coverage < 0.5 else "medium",
                "type": "empty_title",
                "table": tbl,
                "message": f"{tbl}: title coverage {coverage:.0%} ({count - has_title} nodes missing title)",
            })

    metrics["title_coverage"] = round(total_with_title / total_nodes, 3) if total_nodes > 0 else 0

    # 2. Edge density
    try:
        r = _execute_cypher("MATCH ()-[e]->() RETURN count(e)")
        total_edges = r.get_next()[0]
    except:
        total_edges = 0

    density = round(total_edges / total_nodes, 3) if total_nodes > 0 else 0
    metrics["edge_density"] = density
    metrics["total_nodes"] = total_nodes
    metrics["total_edges"] = total_edges
    if density < QG_TARGET_EDGE_DENSITY:
        issues.append({
            "severity": "high",
            "type": "sparse_edges",
            "message": f"Edge density {density} below target {QG_TARGET_EDGE_DENSITY} ({total_edges} edges / {total_nodes} nodes)",
        })

    # 3. Isolated nodes (nodes with 0 edges)
    isolated = 0
    for tbl in ["TaxType", "DocumentSection", "MindmapNode", "CPAKnowledge", "FAQEntry"]:
        try:
            r = _execute_cypher(f"""
                MATCH (n:{tbl})
                WHERE NOT exists {{ (n)-[]-() }}
                RETURN count(n)
            """)
            cnt = r.get_next()[0]
            if cnt > 0:
                isolated += cnt
                issues.append({
                    "severity": "medium",
                    "type": "isolated_nodes",
                    "table": tbl,
                    "message": f"{tbl}: {cnt} nodes with zero edges",
                })
        except:
            pass
    metrics["isolated_nodes"] = isolated

    # 4. Overall quality score (0-100)
    score = 100
    # Deduct for low title coverage
    score -= max(0, (QG_TITLE_COVERAGE_TARGET - metrics["title_coverage"]) * 100)
    # Deduct for low edge density
    score -= max(0, (QG_TARGET_EDGE_DENSITY - density) * 50)
    # Deduct for isolated nodes (cap at 20 points)
    if total_nodes > 0:
        score -= min(20, (isolated / total_nodes) * 200)
    metrics["quality_score"] = max(0, round(score))

    # Gate verdict
    gate_pass = metrics["quality_score"] >= 60 and len([i for i in issues if i["severity"] == "high"]) == 0

    return {
        "gate": "PASS" if gate_pass else "FAIL",
        "score": metrics["quality_score"],
        "metrics": metrics,
        "title_stats": title_stats,
        "issues": sorted(issues, key=lambda x: 0 if x["severity"] == "high" else 1),
        "thresholds": {
            "title_min_len": QG_TITLE_MIN_LEN,
            "content_min_len": QG_CONTENT_MIN_LEN,
            "edge_density_target": QG_TARGET_EDGE_DENSITY,
            "title_coverage_target": QG_TITLE_COVERAGE_TARGET,
        },
    }


# ── Ingest API ───────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    table: str = "LawOrRegulation"
    nodes: list[dict]


@app.post("/api/v1/ingest")
def ingest(req: IngestRequest):
    """Batch-ingest nodes into KuzuDB with quality gate enforcement.

    Quality gate checks per node:
    - id: required, non-empty
    - title: required, >= QG_TITLE_MIN_LEN chars (default 5)
    - content (fullText/content): >= QG_CONTENT_MIN_LEN chars (default 20)
    - Rejects nodes that would degrade graph quality

    Returns rejected nodes with reasons for upstream correction.
    """
    table = req.table
    if table not in NODE_TABLES and not table.isidentifier():
        raise HTTPException(400, detail=f"Unknown table: {table}")

    if not req.nodes:
        return {"inserted": 0, "errors": 0, "skipped": 0, "rejected": []}

    inserted = 0
    errors = 0
    skipped = 0
    rejected = []

    # Pre-validate all nodes before touching DB
    valid_nodes = []
    for i, node in enumerate(req.nodes):
        nid = node.get("id", "").strip()
        title = (node.get("title") or "").strip()
        content = (node.get("fullText") or node.get("content") or "").strip()

        # Gate 1: ID required
        if not nid:
            rejected.append({"index": i, "reason": "missing_id"})
            continue

        # Gate 2: Title required and meaningful
        if len(title) < QG_TITLE_MIN_LEN:
            rejected.append({"index": i, "id": nid, "reason": f"title_too_short ({len(title)} < {QG_TITLE_MIN_LEN})"})
            continue

        # Gate 3: Content minimum (warn but allow for some table types)
        if len(content) < QG_CONTENT_MIN_LEN and table not in ("TaxType", "Region", "Industry", "TaxCalendar"):
            rejected.append({"index": i, "id": nid, "reason": f"content_too_short ({len(content)} < {QG_CONTENT_MIN_LEN})"})
            continue

        # Gate 4: No raw ID/offset leak in title
        if title.startswith("{'_id':") or title.startswith("{'offset':") or title.startswith("TRM_"):
            rejected.append({"index": i, "id": nid, "reason": f"title_is_raw_id ({title[:30]})"})
            continue

        valid_nodes.append(node)

    if not valid_nodes:
        return {"inserted": 0, "errors": 0, "skipped": 0, "rejected": rejected}

    with _db_lock:
        if _degraded or _kuzu_conn is None:
            raise HTTPException(503, detail="图数据库不可用")

        # Ensure table exists
        try:
            _kuzu_conn.execute(f"MATCH (n:{table}) RETURN count(n) LIMIT 1")
        except Exception:
            log.info("Creating node table: %s", table)
            try:
                _kuzu_conn.execute(f"""
                    CREATE NODE TABLE IF NOT EXISTS {table} (
                        id STRING PRIMARY KEY,
                        title STRING,
                        fullText STRING,
                        sourceUrl STRING,
                        regulationNumber STRING,
                        effectiveDate STRING,
                        hierarchyLevel STRING,
                        regulationType STRING,
                        createdAt STRING DEFAULT ''
                    )
                """)
            except Exception as e:
                log.error("Failed to create table %s: %s", table, e)
                raise HTTPException(500, detail=f"Table creation failed: {e}")

        # Insert validated nodes
        for node in valid_nodes:
            nid = node.get("id")
            title = node.get("title", "")
            if not nid or len(title) < 3:
                skipped += 1
                continue

            # Dedup: skip if already exists
            try:
                r = _kuzu_conn.execute(
                    f"MATCH (n:{table}) WHERE n.id = $nid RETURN count(n)",
                    {"nid": nid},
                )
                if r.get_next()[0] > 0:
                    skipped += 1
                    continue
            except Exception:
                pass  # If check fails, try insert anyway

            try:
                _kuzu_conn.execute(
                    f"""CREATE (n:{table} {{
                        id: $id, title: $title, fullText: $fullText,
                        sourceUrl: $sourceUrl, regulationNumber: $regNum,
                        effectiveDate: $effDate, hierarchyLevel: $hierLevel,
                        regulationType: $regType, createdAt: $createdAt
                    }})""",
                    {
                        "id": nid,
                        "title": (title or "")[:500],
                        "fullText": (node.get("fullText") or "")[:5000],
                        "sourceUrl": (node.get("sourceUrl") or "")[:500],
                        "regNum": (node.get("regulationNumber") or "")[:200],
                        "effDate": (node.get("effectiveDate") or "")[:20],
                        "hierLevel": (node.get("hierarchyLevel") or "")[:100],
                        "regType": (node.get("regulationType") or "")[:100],
                        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                )
                inserted += 1
            except Exception as e:
                log.warning("Insert failed for %s: %s", nid, str(e)[:100])
                errors += 1

    log.info("Ingest %s: inserted=%d, skipped=%d, errors=%d, rejected=%d",
             table, inserted, skipped, errors, len(rejected))
    result = {"inserted": inserted, "errors": errors, "skipped": skipped, "table": table}
    if rejected:
        result["rejected"] = rejected[:50]  # Cap to avoid huge responses
        result["rejected_count"] = len(rejected)
    return result


@app.post("/api/query")
def query(q: CypherQuery):
    # Safety: block write operations
    if WRITE_KEYWORDS.search(q.cypher):
        raise HTTPException(400, detail="只读服务，不允许写入操作")

    # Inject LIMIT if missing
    cypher = q.cypher.strip().rstrip(";")
    if "LIMIT" not in cypher.upper():
        cypher += f" LIMIT {q.limit}"

    t0 = time.time()
    try:
        result = _execute_cypher(cypher, q.params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, detail=f"查询错误: {str(e)[:200]}")

    columns = result.get_column_names()
    rows = []
    while result.has_next():
        row = result.get_next()
        rows.append([_serialize(v) for v in row])
        if len(rows) >= q.limit:
            break

    elapsed = int((time.time() - t0) * 1000)
    return {"columns": columns, "rows": rows, "count": len(rows), "elapsed_ms": elapsed}


@app.post("/api/search")
def search(q: SearchQuery):
    if _lance_db is None:
        raise HTTPException(503, detail="向量数据库不可用")

    try:
        # Embed query text via Gemini API
        vec = _embed_text(q.query)
        if vec is None:
            raise HTTPException(500, detail="嵌入生成失败")

        tbl = _lance_db.open_table("finance_tax_embeddings")
        results = tbl.search(vec).limit(q.limit).to_list()
        items = []
        for r in results:
            items.append({
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "node_type": r.get("node_type", ""),
                "score": round(r.get("_distance", 0), 4),
            })
        return {"results": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"搜索错误: {str(e)[:200]}")


@app.get("/api/node/{node_id}")
def get_node(node_id: str):
    # Try KuzuDB first
    if not _degraded and _kuzu_conn is not None:
        for tbl in NODE_TABLES:
            try:
                r = _execute_cypher(
                    f"MATCH (n:{tbl}) WHERE n.id = $id RETURN n.*",
                    {"id": node_id}
                )
                if r.has_next():
                    row = r.get_next()
                    cols = r.get_column_names()
                    props = {}
                    for c, v in zip(cols, row):
                        key = c.replace("n.", "")
                        props[key] = _serialize(v)
                    return {"table": tbl, "id": node_id, "properties": props}
            except HTTPException as he:
                if he.status_code == 503:
                    break  # DB locked, fall through to LanceDB
                raise
            except:
                continue

    # Fallback: lookup in LanceDB metadata via SQL filter
    if _lance_db is not None:
        try:
            tbl = _lance_db.open_table("finance_tax_embeddings")
            results = tbl.search().where(f"id = '{node_id}'", prefilter=True).limit(1).to_arrow().to_pylist()
            if results:
                row = results[0]
                props = {
                    "id": row.get("id", node_id),
                    "title": row.get("title", ""),
                    "node_type": row.get("node_type", ""),
                    "reg_type": row.get("reg_type", ""),
                    "source": row.get("source", ""),
                }
                return {
                    "table": row.get("node_type", "LawOrRegulation"),
                    "id": node_id,
                    "properties": {k: v for k, v in props.items() if v},
                    "source": "lancedb_fallback",
                }
        except Exception as e:
            log.warning("LanceDB fallback failed: %s", e)

    raise HTTPException(404, detail=f"节点 {node_id} 未找到")


@app.get("/api/neighbors/{node_id}")
def get_neighbors(node_id: str, limit: int = Query(default=50, le=200)):
    # Find the node first
    node = None
    node_table = None
    for tbl in NODE_TABLES:
        try:
            r = _execute_cypher(
                f"MATCH (n:{tbl}) WHERE n.id = $id RETURN n.id, n.title, n.name",
                {"id": node_id}
            )
            if r.has_next():
                row = r.get_next()
                node = {"id": row[0], "label": row[1] or row[2] or node_id, "table": tbl}
                node_table = tbl
                break
        except:
            continue

    if not node:
        raise HTTPException(404, detail=f"节点 {node_id} 未找到")

    # Get outgoing and incoming neighbors
    neighbors = []
    edges = []

    # Outgoing
    try:
        r = _execute_cypher(f"""
            MATCH (a:{node_table} {{id: $id}})-[r]->(b)
            RETURN label(b) as tbl, b.id, b.title, b.name, type(r) as rel
            LIMIT {limit}
        """, {"id": node_id})
        while r.has_next():
            row = r.get_next()
            nid = _serialize(row[1])
            neighbors.append({
                "id": nid,
                "label": _serialize(row[2]) or _serialize(row[3]) or nid,
                "table": _serialize(row[0]),
            })
            edges.append({
                "from": node_id, "to": nid,
                "label": _serialize(row[4]),
            })
    except:
        pass

    # Incoming
    try:
        r = _execute_cypher(f"""
            MATCH (b)-[r]->(a:{node_table} {{id: $id}})
            RETURN label(b) as tbl, b.id, b.title, b.name, type(r) as rel
            LIMIT {limit}
        """, {"id": node_id})
        while r.has_next():
            row = r.get_next()
            nid = _serialize(row[1])
            neighbors.append({
                "id": nid,
                "label": _serialize(row[2]) or _serialize(row[3]) or nid,
                "table": _serialize(row[0]),
            })
            edges.append({
                "from": nid, "to": node_id,
                "label": _serialize(row[4]),
            })
    except:
        pass

    return {
        "node": node,
        "neighbors": neighbors,
        "edges": edges,
        "count": len(neighbors),
    }


@app.get("/api/tables")
def list_tables():
    active = []
    for tbl in NODE_TABLES:
        try:
            r = _execute_cypher(f"MATCH (n:{tbl}) RETURN count(n)")
            cnt = r.get_next()[0]
            if cnt > 0:
                active.append({"name": tbl, "count": cnt, "color": NODE_COLORS.get(tbl, DEFAULT_COLOR)})
        except:
            pass
    return {"tables": sorted(active, key=lambda x: -x["count"])}


@app.get("/api/sample")
def sample_graph(table: str = "TaxType", limit: int = Query(default=20, le=100)):
    """Get a sample subgraph for initial visualization.

    Returns nodes with human-readable labels (never raw IDs/offsets).
    """
    nodes = []
    edges = []
    seen = set()

    # Sanitize table name
    if not table.isidentifier():
        raise HTTPException(400, detail=f"Invalid table name: {table}")

    # Get seed nodes with all possible label fields
    try:
        r = _execute_cypher(f"""
            MATCH (n:{table})
            RETURN n.id, n.title, n.name, n.question, n.content
            LIMIT {limit}
        """)
        while r.has_next():
            row = r.get_next()
            nid = _serialize(row[0])
            if not nid or nid in seen:
                continue
            seen.add(nid)
            label = _get_node_label(
                nid, title=_serialize(row[1]), name=_serialize(row[2]),
                question=_serialize(row[3]), content=_serialize(row[4]),
                table=table,
            )
            nodes.append({
                "id": nid, "label": label, "table": table,
                "color": NODE_COLORS.get(table, DEFAULT_COLOR),
            })
    except Exception as e:
        log.warning("Sample seed query failed for %s: %s", table, e)

    # Get their neighbors (1-hop) — outgoing
    for node in list(nodes):
        try:
            r = _execute_cypher(f"""
                MATCH (a:{table} {{id: $id}})-[r]->(b)
                RETURN label(b), b.id, b.title, b.name, b.question, b.content, type(r)
                LIMIT 5
            """, {"id": node["id"]})
            while r.has_next():
                row = r.get_next()
                nid = _serialize(row[1])
                tbl = _serialize(row[0])
                if not nid or nid in seen:
                    edges.append({"from": node["id"], "to": nid, "label": _serialize(row[6])})
                    continue
                seen.add(nid)
                label = _get_node_label(
                    nid, title=_serialize(row[2]), name=_serialize(row[3]),
                    question=_serialize(row[4]), content=_serialize(row[5]),
                    table=tbl,
                )
                nodes.append({
                    "id": nid, "label": label, "table": tbl,
                    "color": NODE_COLORS.get(tbl, DEFAULT_COLOR),
                })
                edges.append({"from": node["id"], "to": nid, "label": _serialize(row[6])})
        except:
            pass

        # Incoming edges
        try:
            r = _execute_cypher(f"""
                MATCH (b)-[r]->(a:{table} {{id: $id}})
                RETURN label(b), b.id, b.title, b.name, b.question, b.content, type(r)
                LIMIT 5
            """, {"id": node["id"]})
            while r.has_next():
                row = r.get_next()
                nid = _serialize(row[1])
                tbl = _serialize(row[0])
                if not nid or nid in seen:
                    edges.append({"from": nid, "to": node["id"], "label": _serialize(row[6])})
                    continue
                seen.add(nid)
                label = _get_node_label(
                    nid, title=_serialize(row[2]), name=_serialize(row[3]),
                    question=_serialize(row[4]), content=_serialize(row[5]),
                    table=tbl,
                )
                nodes.append({
                    "id": nid, "label": label, "table": tbl,
                    "color": NODE_COLORS.get(tbl, DEFAULT_COLOR),
                })
                edges.append({"from": nid, "to": node["id"], "label": _serialize(row[6])})
        except:
            pass

    return {"nodes": nodes, "edges": edges}


@app.get("/")
def web_ui():
    html_path = WEB_DIR / "kg_explorer.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    return JSONResponse({"error": "Web UI not found"}, status_code=404)


def _serialize(v):
    """Convert KuzuDB value to JSON-safe type.

    Handles KuzuDB internal types (node IDs, offset tuples) gracefully
    instead of leaking raw repr like {'_id': ('offset': 38977, 'tab...}.
    """
    if v is None:
        return None
    if isinstance(v, (int, float, str, bool)):
        return v
    # KuzuDB dict-like node values — extract meaningful fields
    if isinstance(v, dict):
        # Try common label fields in priority order
        for key in ("title", "name", "question", "label"):
            if key in v and v[key]:
                return str(v[key])[:200]
        # Fall back to id if present
        if "id" in v and isinstance(v["id"], str):
            return v["id"]
        # Internal _id with offset — return empty (not the ugly repr)
        if "_id" in v:
            return None
    # For any other complex type, try str but cap length
    s = str(v)
    # Detect KuzuDB offset tuple leaks
    if s.startswith("{'_id':") or s.startswith("{'offset':"):
        return None
    return s[:200]


def _get_node_label(node_id: str, title=None, name=None, question=None,
                    content=None, table=None):
    """Get best human-readable label for a node.

    Priority: title > name > question > TRM decode > content prefix > id suffix.
    """
    # Try direct fields
    for val in (title, name, question):
        if val and isinstance(val, str) and len(val.strip()) >= 2:
            return val.strip()[:40]

    # TaxRateMapping code decode: "TRM_TRANSPORT_9" -> "交通运输业 9%"
    if node_id and node_id.startswith("TRM_"):
        parts = node_id.rsplit("_", 1)
        base = parts[0] if len(parts) > 1 else node_id
        rate = parts[1] if len(parts) > 1 else ""
        label = TRM_LABELS.get(base, base.replace("TRM_", ""))
        if rate and rate.isdigit():
            return f"{label} {rate}%"
        return label

    # Content prefix as last resort
    if content and isinstance(content, str) and len(content.strip()) >= 5:
        return content.strip()[:35] + "..."

    # Hash ID: show only last 8 chars
    if node_id and len(node_id) > 12:
        return f"...{node_id[-8:]}"

    return node_id or "未命名"
