#!/usr/bin/env python3
"""CogNebula MCP Server — Domain knowledge graph for AI agents.

Exposes a finance/tax knowledge graph (620K+ nodes, 1M+ edges) as MCP tools.
Proxies to kg-api-server on VPS via REST API.

Usage:
    # stdio mode (for Claude Code, LangGraph, etc.)
    python cognebula_mcp.py

    # Test with MCP inspector
    mcp dev cognebula_mcp.py
"""
import json
import os
import urllib.request
import urllib.error
from mcp.server.fastmcp import FastMCP

# API base URL — Tailscale IP or override via env
API_BASE = os.environ.get("COGNEBULA_API_URL", "http://100.75.77.112:8400")
API_KEY = os.environ.get("COGNEBULA_API_KEY", "")

mcp = FastMCP(
    "CogNebula",
    instructions="Finance/tax knowledge graph with 800K+ nodes and 720K+ edges. "
    "Hybrid search (text + vector + graph), RAG chat, traverse relationships.",
)


def _api_get(path: str, params: dict | None = None) -> dict:
    """Call CogNebula REST API."""
    url = f"{API_BASE}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:500]}
    except Exception as e:
        return {"error": str(e)}


def _api_post(path: str, body: dict) -> dict:
    """POST to CogNebula REST API."""
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:500]}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search(query: str, limit: int = 10, table_filter: str | None = None) -> str:
    """Search the finance/tax knowledge graph for regulations, laws, and compliance rules.

    Use when: answering tax questions, finding applicable regulations, looking up tax rates.
    Returns: matching nodes with title, content excerpt, source table, and relevance score.

    Args:
        query: Search text (Chinese or English). Examples: "增值税税率", "小规模纳税人", "企业所得税优惠"
        limit: Max results (1-100, default 10)
        table_filter: Optional node type filter (e.g. "LawOrRegulation", "TaxRate", "KnowledgeUnit")
    """
    params = {"q": query, "limit": limit}
    if table_filter:
        params["table_filter"] = table_filter
    data = _api_get("/api/v1/search", params)
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    results = data.get("results", [])
    if not results:
        return f"No results found for '{query}'. Try broader keywords."

    lines = [f"Found {data.get('count', 0)} results for '{query}':\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title") or r.get("name") or r.get("id", "")
        lines.append(f"{i}. [{r.get('table', '')}] {title}")
        if r.get("text"):
            lines.append(f"   {r['text'][:200]}")
        lines.append(f"   ID: {r.get('id', '')} | Score: {r.get('score', 0):.1f}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def hybrid_search(query: str, limit: int = 10, expand: bool = True) -> str:
    """Search the knowledge graph using hybrid retrieval (text + vector + graph).

    Use when: you need the most accurate and comprehensive search results.
    Combines keyword matching, semantic vector similarity, and graph traversal.
    Better than basic search for nuanced or multi-concept queries.

    Args:
        query: Search text (Chinese). Examples: "小规模纳税人增值税免征条件", "研发费用加计扣除比例"
        limit: Max results (1-100, default 10)
        expand: Whether to include 1-hop graph neighbors of top results (default True)
    """
    params = {"q": query, "limit": limit, "expand": str(expand).lower()}
    data = _api_get("/api/v1/hybrid-search", params)
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    results = data.get("results", [])
    graph = data.get("graph_expansion", [])

    lines = [
        f"Hybrid search: {data.get('count', 0)} results "
        f"(text: {data.get('text_hits', 0)}, vector: {data.get('vector_hits', 0)})\n"
    ]
    for i, r in enumerate(results, 1):
        title = r.get("title") or r.get("name") or r.get("id", "")
        lines.append(f"{i}. [{r.get('table', '')}] {title}")
        if r.get("text"):
            lines.append(f"   {r['text'][:200]}")
        lines.append(f"   ID: {r.get('id', '')} | RRF: {r.get('rrf_score', 0):.4f}")
        lines.append("")

    if graph:
        lines.append(f"Graph expansion ({len(graph)} connected nodes):")
        for g in graph[:10]:
            lines.append(f"  {g.get('from', '')} --[{g.get('rel', '')}]--> [{g.get('type', '')}] {g.get('name', g.get('id', ''))}")

    return "\n".join(lines)


@mcp.tool()
def traverse(table: str, node_id: str, depth: int = 1) -> str:
    """Traverse the knowledge graph from a specific node to find related regulations.

    Use when: understanding regulation relationships, finding superseding laws,
    tracing clause dependencies, exploring tax type connections.

    Args:
        table: Node type (e.g. "LawOrRegulation", "RegulationClause", "TaxType", "KnowledgeUnit")
        node_id: Node ID from a previous search result
        depth: Traversal depth 1-3 (default 1). Higher = more connections but slower
    """
    data = _api_get("/api/v1/graph", {
        "table": table, "id_field": "id", "id_value": node_id, "depth": depth,
    })
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    node = data.get("node")
    neighbors = data.get("neighbors", [])

    lines = []
    if node:
        label = node.get("_label") or node.get("title") or node.get("name") or node_id
        lines.append(f"Node: {label}")
        lines.append(f"Type: {table} | ID: {node_id}")
        # Show key fields
        for field in ["title", "content", "description", "fullText", "name"]:
            val = node.get(field)
            if val and field != "_label":
                lines.append(f"{field}: {str(val)[:300]}")
        lines.append("")

    if neighbors:
        lines.append(f"Connected nodes ({len(neighbors)}):")
        # Group by edge type
        by_edge: dict[str, list] = {}
        for n in neighbors:
            edge = n.get("edge_type", "UNKNOWN")
            by_edge.setdefault(edge, []).append(n)
        for edge_type, nodes in by_edge.items():
            lines.append(f"\n  --[{edge_type}]-->")
            for n in nodes[:5]:
                label = n.get("label") or n.get("id", "")
                lines.append(f"    {n.get('type', '')}: {label}")
            if len(nodes) > 5:
                lines.append(f"    ... and {len(nodes) - 5} more")
    else:
        lines.append("No connected nodes found.")

    return "\n".join(lines)


@mcp.tool()
def chat(question: str, mode: str = "rag") -> str:
    """Ask a question about Chinese finance/tax regulations using RAG or Cypher.

    Use when: the user needs a synthesized answer (not just search results).
    The RAG mode searches the knowledge graph, assembles context, and generates an answer.
    The Cypher mode translates the question to a graph query.

    Args:
        question: Natural language question in Chinese. Example: "小微企业的企业所得税优惠政策有哪些？"
        mode: "rag" (default, recommended) or "cypher" (for structured queries)
    """
    data = _api_post("/api/v1/chat", {"question": question, "mode": mode, "limit": 8})
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    answer = data.get("answer", "")
    sources = data.get("sources", [])
    cypher = data.get("cypher", "")

    lines = [answer]
    if cypher:
        lines.append(f"\nCypher: {cypher}")
    if sources:
        lines.append(f"\nSources ({len(sources)} retrieved):")
        for s in sources[:5]:
            if isinstance(s, dict):
                lines.append(f"  - {s.get('title', s.get('id', 'unknown'))}")
    return "\n".join(lines)


@mcp.tool()
def stats() -> str:
    """Get knowledge graph statistics: node counts, edge counts, table breakdown.

    Use when: understanding the scope and coverage of the knowledge graph.
    """
    data = _api_get("/api/v1/stats")
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    lines = [
        f"CogNebula Knowledge Graph Statistics",
        f"Nodes: {data.get('total_nodes', 0):,} ({data.get('node_tables', 0)} types)",
        f"Edges: {data.get('total_edges', 0):,} ({data.get('rel_tables', 0)} types)",
        "",
        "Top node types:",
    ]
    for k, v in list(data.get("nodes_by_type", {}).items())[:10]:
        lines.append(f"  {k}: {v:,}")
    lines.append("\nEdge types:")
    for k, v in list(data.get("edges_by_type", {}).items())[:10]:
        lines.append(f"  {k}: {v:,}")
    return "\n".join(lines)


@mcp.tool()
def quality() -> str:
    """Check knowledge graph data quality: completeness, content coverage, edge density.

    Use when: assessing whether the knowledge graph is reliable for a given query domain.
    """
    data = _api_get("/api/v1/quality")
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    score = data.get("score", 0)
    gate = "PASS" if score >= 70 else "FAIL"
    metrics = data.get("metrics", {})

    lines = [
        f"Quality Gate: {score}/100 ({gate})",
        f"Nodes: {metrics.get('total_nodes', 0):,}",
        f"Edges: {metrics.get('total_edges', 0):,}",
        f"Edge density: {metrics.get('edge_density', 0):.3f}",
    ]
    details = data.get("details", {})
    if details:
        lines.append("\nPer-type scores:")
        for k, v in details.items():
            if isinstance(v, dict):
                s = v.get("score", "N/A")
                g = "PASS" if isinstance(s, (int, float)) and s >= 50 else "FAIL"
                lines.append(f"  {k}: {s} ({g})")
    return "\n".join(lines)


@mcp.tool()
def lookup_nodes(
    node_type: str,
    query: str | None = None,
    limit: int = 10,
) -> str:
    """Look up nodes by type and optional text filter.

    Use when: browsing a specific category of knowledge (e.g. all TaxRate nodes,
    or all LawOrRegulation nodes matching a keyword).

    Args:
        node_type: Node table name. Common types: LawOrRegulation, RegulationClause,
            KnowledgeUnit, TaxRate, TaxIncentive, ComplianceRule, FAQEntry, TaxType
        query: Optional text filter to match against node content
        limit: Max results (1-500, default 10)
    """
    params = {"type": node_type, "limit": limit}
    if query:
        params["q"] = query
    data = _api_get("/api/v1/nodes", params)
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)

    nodes = data.get("results", data.get("nodes", []))
    if not nodes:
        return f"No {node_type} nodes found" + (f" matching '{query}'" if query else "") + "."

    lines = [f"{node_type} nodes ({len(nodes)} results):\n"]
    for n in nodes:
        label = n.get("_display_label") or n.get("title") or n.get("name") or n.get("id", "")
        lines.append(f"- {label}")
        lines.append(f"  ID: {n.get('id', '')}")
        content = n.get("content") or n.get("description") or n.get("fullText") or ""
        if content:
            lines.append(f"  {str(content)[:150]}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
