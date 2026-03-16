#!/usr/bin/env python3
"""Finance/Tax Hybrid RAG -- LanceDB Semantic + KuzuDB Structural

This module provides the Hybrid RAG pipeline for finance/tax queries:
1. LanceDB vector search -> top-K semantically similar regulations
2. KuzuDB graph traversal -> expand to related tax types, incentives, authorities
3. Tiered context assembly -> full text (D0), titles (D1), names only (D2)
4. Token budget enforcement -> truncate to target token count

Usage:
    from finance_tax_rag import hybrid_rag_query
    result = hybrid_rag_query(conn, query="软件企业增值税优惠", limit=5)
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

try:
    import lancedb
    LANCE_AVAILABLE = True
except ImportError:
    LANCE_AVAILABLE = False


def _lance_search(db_path: Path, query: str, limit: int = 5) -> list[dict]:
    """Search LanceDB for semantically similar regulations."""
    if not LANCE_AVAILABLE:
        return []
    lance_path = db_path.parent / "finance-tax-lance"
    if not lance_path.exists():
        return []
    try:
        db = lancedb.connect(str(lance_path))
        if "finance_tax_embeddings" not in db.table_names():
            return []
        table = db.open_table("finance_tax_embeddings")
        # Full-text search fallback (no embedding model in this process)
        results = table.search(query).limit(limit).to_list()
        return [{"id": r.get("id", ""), "title": r.get("title", ""),
                 "score": r.get("_distance", 0)} for r in results]
    except Exception:
        return []


def _kuzu_text_search(conn: Any, query: str, limit: int = 5) -> list[dict]:
    """Fallback: search KuzuDB by title/fullText keyword match."""
    results = []
    try:
        r = conn.execute(
            "MATCH (n:LawOrRegulation) "
            "WHERE n.title CONTAINS $kw OR n.fullText CONTAINS $kw "
            "RETURN n.id, n.title, n.regulationNumber, n.effectiveDate, "
            "n.hierarchyLevel, n.sourceUrl, n.fullText "
            "ORDER BY n.hierarchyLevel ASC LIMIT $lim",
            {"kw": query, "lim": limit}
        )
        while r.has_next():
            row = r.get_next()
            results.append({
                "id": row[0], "title": row[1], "reg_number": row[2],
                "effective_date": str(row[3]) if row[3] else None,
                "hierarchy": row[4], "url": row[5],
                "full_text": (row[6] or "")[:2000],
            })
    except Exception:
        pass
    return results


def _expand_graph(conn: Any, law_ids: list[str]) -> dict:
    """Expand from law nodes via graph traversal to related entities."""
    tax_types = []
    incentives = []
    authorities = []

    for lid in law_ids[:5]:
        # Tax types governed by this law
        try:
            r = conn.execute(
                "MATCH (tax:TaxType)-[:FT_GOVERNED_BY]->(law:LawOrRegulation {id: $lid}) "
                "RETURN DISTINCT tax.name, tax.rateRange, tax.filingFrequency",
                {"lid": lid}
            )
            while r.has_next():
                row = r.get_next()
                tax_types.append({"name": row[0], "rates": row[1], "frequency": row[2]})
        except Exception:
            pass

        # Incentives linked to these tax types
        try:
            r = conn.execute(
                "MATCH (tax:TaxType)-[:FT_GOVERNED_BY]->(law:LawOrRegulation {id: $lid}), "
                "(inc:TaxIncentive)-[:FT_INCENTIVE_TAX]->(tax) "
                "RETURN DISTINCT inc.name, inc.incentiveType, inc.value, inc.valueBasis",
                {"lid": lid}
            )
            while r.has_next():
                row = r.get_next()
                incentives.append({"name": row[0], "type": row[1], "value": row[2], "basis": row[3]})
        except Exception:
            pass

    return {"tax_types": tax_types, "incentives": incentives, "authorities": authorities}


def _assemble_context(laws: list[dict], graph: dict, token_budget: int = 4000) -> str:
    """Assemble markdown context with tiered detail degradation."""
    lines = []
    approx_tokens = 0

    # Depth 0: Full regulation text for top results
    for i, law in enumerate(laws[:3]):
        if approx_tokens > token_budget * 0.7:
            break
        lines.append(f"### {law['title']}")
        if law.get("reg_number"):
            lines.append(f"**文号**: {law['reg_number']} (层级: {law.get('hierarchy', 'N/A')})")
        if law.get("effective_date"):
            lines.append(f"**生效日期**: {law['effective_date']}")
        if law.get("url"):
            lines.append(f"**来源**: {law['url']}")
        text = law.get("full_text", "")
        if text:
            lines.append(f"\n{text}\n")
            approx_tokens += len(text) // 2  # rough CJK token estimate

    # Depth 1: Related tax types (names + rates only)
    if graph["tax_types"]:
        lines.append("\n### 相关税种")
        for tt in graph["tax_types"]:
            lines.append(f"- **{tt['name']}**: {tt.get('rates', 'N/A')} (申报频率: {tt.get('frequency', 'N/A')})")
            approx_tokens += 20

    # Depth 1: Incentives (names only)
    if graph["incentives"] and approx_tokens < token_budget:
        lines.append("\n### 适用优惠政策")
        for inc in graph["incentives"]:
            lines.append(f"- {inc['name']} ({inc.get('type', '')}): {inc.get('value', '')} {inc.get('basis', '')}")
            approx_tokens += 15

    # Depth 2: Remaining laws (titles only, if budget allows)
    if len(laws) > 3 and approx_tokens < token_budget:
        lines.append("\n### 其他相关法规")
        for law in laws[3:]:
            lines.append(f"- [{law.get('reg_number', '')}] {law['title']}")
            approx_tokens += 10

    return "\n".join(lines)


def hybrid_rag_query(conn: Any, db_path: Path, query: str,
                     limit: int = 5, token_budget: int = 4000) -> dict:
    """Execute Hybrid RAG: LanceDB semantic + KuzuDB structural.

    Returns:
        dict with keys: context (markdown), entry_points, tokens_approx, method
    """
    # Step 1: Semantic search (LanceDB) with text search fallback (KuzuDB)
    lance_results = _lance_search(db_path, query, limit)
    if lance_results:
        method = "LanceDB Semantic + KuzuDB Structural"
        law_ids = [r["id"] for r in lance_results]
        # Fetch full data from KuzuDB for these IDs
        laws = []
        for lid in law_ids:
            try:
                r = conn.execute(
                    "MATCH (n:LawOrRegulation {id: $lid}) "
                    "RETURN n.id, n.title, n.regulationNumber, n.effectiveDate, "
                    "n.hierarchyLevel, n.sourceUrl, n.fullText",
                    {"lid": lid}
                )
                if r.has_next():
                    row = r.get_next()
                    laws.append({
                        "id": row[0], "title": row[1], "reg_number": row[2],
                        "effective_date": str(row[3]) if row[3] else None,
                        "hierarchy": row[4], "url": row[5],
                        "full_text": (row[6] or "")[:2000],
                    })
            except Exception:
                pass
    else:
        method = "KuzuDB Text Search + Structural"
        laws = _kuzu_text_search(conn, query, limit)

    if not laws:
        return {"context": f"未找到与 '{query}' 相关的法规", "entry_points": [],
                "tokens_approx": 0, "method": method}

    # Step 2: Graph expansion
    law_ids = [l["id"] for l in laws]
    graph = _expand_graph(conn, law_ids)

    # Step 3: Assemble tiered context
    context = _assemble_context(laws, graph, token_budget)
    tokens_approx = len(context) // 2  # rough CJK estimate

    return {
        "context": context,
        "entry_points": [l["title"] for l in laws[:3]],
        "tokens_approx": tokens_approx,
        "method": method,
        "regulations_found": len(laws),
        "tax_types_found": len(graph["tax_types"]),
        "incentives_found": len(graph["incentives"]),
    }
