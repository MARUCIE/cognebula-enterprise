#!/usr/bin/env python3
"""Edge enrichment via DDL API — zero downtime.

Creates edges for newly ingested nodes using MATCH...CREATE through execute-ddl.

Edge types:
  - KU_ABOUT_TAX: KnowledgeUnit → TaxType (keyword in title/content)
  - CLASSIFIED_UNDER_TAX: LawOrRegulation → TaxType (keyword in title)

Run from VPS:
    python3 scripts/edge_enrich_via_api.py [--host localhost]
"""
import json
import logging
import sys
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("edge_enrich")

HOST = "localhost"
for i, a in enumerate(sys.argv):
    if a == "--host" and i + 1 < len(sys.argv):
        HOST = sys.argv[i + 1]

# Tax keyword → TaxType ID mapping (from /api/v1/nodes?type=TaxType)
TAX_MAP = {
    "TT_VAT": ["增值税", "进项税", "销项税"],
    "TT_CIT": ["企业所得税", "汇算清缴"],
    "TT_PIT": ["个人所得税", "个税", "工资薪金"],
    "TT_CONSUMPTION": ["消费税"],
    "TT_TARIFF": ["关税", "进口税"],
    "TT_URBAN": ["城建税", "城市维护建设税"],
    "TT_EDUCATION": ["教育费附加"],
    "TT_RESOURCE": ["资源税"],
    "TT_LAND_VAT": ["土地增值税"],
    "TT_PROPERTY": ["房产税"],
    "TT_LAND_USE": ["城镇土地使用税", "土地使用税"],
    "TT_VEHICLE": ["车船税", "车辆购置税"],
    "TT_STAMP": ["印花税"],
    "TT_CONTRACT": ["契税"],
    "TT_CULTIVATED": ["耕地占用税"],
    "TT_TOBACCO": ["烟叶税"],
    "TT_ENV": ["环境保护税", "环保税"],
}

# New sources from Session 10 ingest
NEW_KU_SOURCES = ["mof", "ndrc", "baike_kuaiji", "chinatax_fgk"]


def api_post(path, data, timeout=60):
    url = f"http://{HOST}:8400{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)[:200]}


def api_get(path, timeout=15):
    url = f"http://{HOST}:8400{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)[:200]}


def escape(s):
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def ddl(stmts):
    return api_post("/api/v1/admin/execute-ddl", {"statements": stmts}, timeout=120)


# ── Phase 1: KU → TaxType edges ─────────────────────────────────
def create_ku_tax_edges():
    """For each new KU source × tax keyword, create KU_ABOUT_TAX edges."""
    log.info("=== Phase 1: KU → TaxType (KU_ABOUT_TAX) ===")
    total_created = 0

    for source in NEW_KU_SOURCES:
        source_created = 0
        for tax_id, keywords in TAX_MAP.items():
            for kw in keywords:
                ekw = escape(kw)
                esrc = escape(source)
                # Batch: match all KU with this source+keyword, create edge to TaxType
                # Use title match (most reliable, content can be very long)
                stmt = (
                    f"MATCH (a:KnowledgeUnit), (b:TaxType) "
                    f"WHERE a.source = '{esrc}' AND contains(a.title, '{ekw}') AND b.id = '{tax_id}' "
                    f"CREATE (a)-[:KU_ABOUT_TAX]->(b)"
                )
                result = ddl([stmt])
                if "error" not in result:
                    results = result.get("results", [{}])
                    if results and results[0].get("status") == "OK":
                        source_created += 1  # We don't know exact count per batch
                    elif results and "already exists" in str(results[0]).lower():
                        pass  # Duplicate, expected
                    else:
                        err = str(results[0]) if results else "unknown"
                        if "error" in err.lower() and source_created < 3:
                            log.warning("  DDL err %s/%s: %s", source, kw, err[:100])

        total_created += source_created
        log.info("  %s: %d keyword-tax combos matched", source, source_created)

    log.info("[Phase 1] DONE: %d batch DDL statements executed", total_created)
    return total_created


# ── Phase 2: LR → TaxType edges ─────────────────────────────────
def create_lr_tax_edges():
    """For new FLK LawOrRegulation nodes, create CLASSIFIED_UNDER_TAX edges."""
    log.info("=== Phase 2: LR → TaxType (CLASSIFIED_UNDER_TAX) ===")
    total_created = 0

    for tax_id, keywords in TAX_MAP.items():
        for kw in keywords:
            ekw = escape(kw)
            stmt = (
                f"MATCH (a:LawOrRegulation), (b:TaxType) "
                f"WHERE starts_with(a.id, 'FLK_') AND contains(a.title, '{ekw}') AND b.id = '{tax_id}' "
                f"CREATE (a)-[:CLASSIFIED_UNDER_TAX]->(b)"
            )
            result = ddl([stmt])
            if "error" not in result:
                results = result.get("results", [{}])
                if results and results[0].get("status") == "OK":
                    total_created += 1

    log.info("[Phase 2] DONE: %d batch DDL statements executed", total_created)
    return total_created


# ── Phase 3: Content-based keyword edges (title scan) ────────────
def create_content_keyword_edges():
    """Broader keyword scan: also match content field for new KU nodes."""
    log.info("=== Phase 3: Content keyword scan (KU with content → TaxType) ===")
    total_created = 0

    for source in NEW_KU_SOURCES:
        for tax_id, keywords in TAX_MAP.items():
            for kw in keywords:
                ekw = escape(kw)
                esrc = escape(source)
                # Match on content (broader than title-only)
                stmt = (
                    f"MATCH (a:KnowledgeUnit), (b:TaxType) "
                    f"WHERE a.source = '{esrc}' AND a.content IS NOT NULL "
                    f"AND contains(a.content, '{ekw}') AND b.id = '{tax_id}' "
                    f"AND NOT exists {{ MATCH (a)-[:KU_ABOUT_TAX]->(b) }} "
                    f"CREATE (a)-[:KU_ABOUT_TAX]->(b)"
                )
                result = ddl([stmt])
                if "error" not in result:
                    results = result.get("results", [{}])
                    if results and results[0].get("status") == "OK":
                        total_created += 1

    log.info("[Phase 3] DONE: %d batch DDL statements executed", total_created)
    return total_created


# ── Main ─────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("Edge Enrichment via API — %s", HOST)
    log.info("=" * 60)

    stats = api_get("/api/v1/quality")
    if "error" in stats:
        log.error("API not reachable")
        sys.exit(1)
    m = stats.get("metrics", {})
    log.info("BEFORE: %s nodes / %s edges / density %.2f",
             f"{m['total_nodes']:,}", f"{m['total_edges']:,}", m["edge_density"])

    t0 = time.time()

    p1 = create_ku_tax_edges()
    p2 = create_lr_tax_edges()
    p3 = create_content_keyword_edges()

    elapsed = time.time() - t0

    stats2 = api_get("/api/v1/quality")
    m2 = stats2.get("metrics", {})
    log.info("=" * 60)
    log.info("AFTER: %s nodes / %s edges / density %.2f",
             f"{m2['total_nodes']:,}", f"{m2['total_edges']:,}", m2["edge_density"])
    log.info("DELTA: +%d edges / %.0fs elapsed",
             m2["total_edges"] - m["total_edges"], elapsed)
    log.info("Phases: P1=%d P2=%d P3=%d", p1, p2, p3)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
