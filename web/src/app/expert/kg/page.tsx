"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  getStats, getGraph, searchNodes,
  NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS, LAYER_GROUPS, getNodeLayer,
  type KGStats, type KGNeighbor,
} from "../../lib/kg-api";
import type { GraphData, SelectedNode, CytoscapeGraphHandle } from "../../components/CytoscapeGraph";
import { CN, cnInput, cnBtn, cnBtnPrimary, cnBadge } from "../../lib/cognebula-theme";

const CytoscapeGraph = dynamic(() => import("../../components/CytoscapeGraph"), { ssr: false });

const TAX_NAME_MAP: Record<string, string> = {
  "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT", "消费税": "TT_CONSUMPTION",
  "关税": "TT_TARIFF", "城建税": "TT_URBAN", "教育费附加": "TT_EDUCATION", "资源税": "TT_RESOURCE",
  "土地增值税": "TT_LAND_VAT", "房产税": "TT_PROPERTY", "印花税": "TT_STAMP", "契税": "TT_CONTRACT",
  "车船税": "TT_VEHICLE", "环保税": "TT_ENV", "烟叶税": "TT_TOBACCO",
};

export default function KGExplorerPage() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [], groups: [] });
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);
  const [stats, setStats] = useState<KGStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentLayout, setCurrentLayout] = useState("fcose");
  const [leftOpen, setLeftOpen] = useState(true);
  const graphRef = useRef<CytoscapeGraphHandle>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setError("KG API unreachable"));
  }, []);

  const buildGraphFromTraversal = useCallback(
    (centerTable: string, centerId: string, centerLabel: string, neighbors: KGNeighbor[]) => {
      const addedGroups = new Set<string>();
      const addedNodes = new Set<string>();
      const groups: GraphData["groups"] = [];
      const nodes: GraphData["nodes"] = [];
      const edges: GraphData["edges"] = [];

      function ensureGroup(type: string) {
        const layer = getNodeLayer(type);
        if (!addedGroups.has(layer)) {
          addedGroups.add(layer);
          groups.push({ id: layer, label: layer });
        }
        return layer;
      }

      const centerLayer = ensureGroup(centerTable);
      addedNodes.add(centerId);
      nodes.push({
        id: centerId, label: centerLabel.slice(0, 30), type: centerTable,
        color: NODE_COLORS[centerTable] || "#8B5CF6", size: 45, parent: centerLayer,
      });

      for (const nb of neighbors.slice(0, 30)) {
        if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
        addedNodes.add(nb.target_id);
        const nbLayer = ensureGroup(nb.target_type);
        nodes.push({
          id: nb.target_id, label: (nb.target_label || nb.target_id).slice(0, 30),
          type: nb.target_type, color: NODE_COLORS[nb.target_type] || "#94A3B8",
          size: 15, parent: nbLayer,
        });
        const src = nb.direction === "incoming" ? nb.target_id : centerId;
        const tgt = nb.direction === "incoming" ? centerId : nb.target_id;
        edges.push({
          id: `${src}-${tgt}-${nb.edge_type}`, source: src, target: tgt,
          label: EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type.slice(0, 12),
          color: EDGE_COLORS[nb.edge_type] || "#4B5563",
        });
      }
      return { nodes, edges, groups };
    }, []
  );

  const handleSearch = useCallback(async () => {
    const q = searchQuery.trim();
    if (!q) return;
    setLoading(true);
    setError(null);

    try {
      if (TAX_NAME_MAP[q] || q.startsWith("TT_")) {
        const id = TAX_NAME_MAP[q] || q;
        const result = await getGraph("TaxType", id);
        if (result.node) {
          setGraphData(buildGraphFromTraversal("TaxType", id, result.node._label || id, result.neighbors));
        }
        setLoading(false);
        return;
      }

      const searchResult = await searchNodes(q, 10);
      const results = searchResult.results || [];
      if (!results.length) { setError(`Not found: ${q}`); setLoading(false); return; }

      const addedGroups = new Set<string>();
      const addedNodes = new Set<string>();
      const groups: GraphData["groups"] = [];
      const allNodes: GraphData["nodes"] = [];
      const allEdges: GraphData["edges"] = [];

      function ensureGroup(type: string) {
        const layer = getNodeLayer(type);
        if (!addedGroups.has(layer)) { addedGroups.add(layer); groups.push({ id: layer, label: layer }); }
        return layer;
      }

      for (const item of results) {
        const nodeId = item.id || item.node_id || "";
        const nodeTable = item.table || item.source_table || "";
        const nodeLabel = item.text || item.title || item.name || nodeId;
        if (!nodeId || addedNodes.has(nodeId)) continue;
        addedNodes.add(nodeId);
        const layer = ensureGroup(nodeTable);
        allNodes.push({ id: nodeId, label: nodeLabel.slice(0, 30), type: nodeTable, color: NODE_COLORS[nodeTable] || "#94A3B8", size: 25, parent: layer });

        try {
          const graphResult = await getGraph(nodeTable, nodeId);
          for (const nb of (graphResult.neighbors || []).slice(0, 8)) {
            if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
            addedNodes.add(nb.target_id);
            const nbLayer = ensureGroup(nb.target_type);
            allNodes.push({ id: nb.target_id, label: (nb.target_label || nb.target_id).slice(0, 30), type: nb.target_type, color: NODE_COLORS[nb.target_type] || "#94A3B8", size: 12, parent: nbLayer });
            const src = nb.direction === "incoming" ? nb.target_id : nodeId;
            const tgt = nb.direction === "incoming" ? nodeId : nb.target_id;
            allEdges.push({ id: `${src}-${tgt}-${nb.edge_type}`, source: src, target: tgt, label: EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type.slice(0, 12), color: EDGE_COLORS[nb.edge_type] || "#4B5563" });
          }
        } catch { /* skip */ }
      }
      setGraphData({ nodes: allNodes, edges: allEdges, groups });
    } catch (e) { setError(e instanceof Error ? e.message : "Search failed"); }
    setLoading(false);
  }, [searchQuery, buildGraphFromTraversal]);

  const handleNodeDblClick = useCallback(async (nodeId: string, nodeType: string) => {
    setLoading(true);
    try {
      const result = await getGraph(nodeType, nodeId);
      if (result.node) setGraphData(buildGraphFromTraversal(nodeType, nodeId, result.node._label || nodeId, result.neighbors));
    } catch (e) { setError(e instanceof Error ? e.message : "Expand failed"); }
    setLoading(false);
  }, [buildGraphFromTraversal]);

  const toggleLayout = useCallback(() => {
    const layouts = ["fcose", "cose", "circle", "grid"];
    const idx = layouts.indexOf(currentLayout);
    const next = layouts[(idx + 1) % layouts.length];
    setCurrentLayout(next);
    graphRef.current?.runLayout(next);
  }, [currentLayout]);

  const topTypes = stats
    ? Object.entries(stats.nodes_by_type).sort((a, b) => b[1] - a[1]).slice(0, 12)
    : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 49px)" }}>
      {/* Toolbar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 32px", flexShrink: 0,
        background: CN.bgCard, borderBottom: `1px solid ${CN.border}`,
      }}>
        <button onClick={() => setLeftOpen(!leftOpen)} style={{ ...cnBtn, padding: "7px 10px", fontSize: 14 }}>
          {leftOpen ? "\u25C0" : "\u25B6"}
        </button>
        <input
          type="text"
          placeholder="Search entities (e.g. 增值税, TT_VAT, 企业所得税法)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          style={{ ...cnInput, flex: 1, maxWidth: 480 }}
        />
        <button onClick={handleSearch} disabled={loading}
          style={{ ...cnBtnPrimary, opacity: loading ? 0.5 : 1, cursor: loading ? "wait" : "pointer" }}>
          {loading ? "..." : "Search"}
        </button>
        <button onClick={() => graphRef.current?.fit()} style={cnBtn}>Reset</button>
        <button onClick={toggleLayout} style={cnBtn}>Layout: {currentLayout}</button>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 16, fontSize: 12, color: CN.textMuted }}>
          <span>Graph: <strong style={{ color: CN.blue }}>{graphData.nodes.length}</strong> nodes</span>
          <span><strong style={{ color: CN.blue }}>{graphData.edges.length}</strong> edges</span>
          {stats && (
            <span>KG: <strong style={{ color: CN.green }}>{(stats.total_nodes / 1000).toFixed(0)}K</strong> / <strong style={{ color: CN.green }}>{(stats.total_edges / 1000).toFixed(0)}K</strong></span>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: "8px 16px", background: CN.redBg, color: CN.red, fontSize: 13, borderBottom: `1px solid ${CN.border}` }}>
          {error}
        </div>
      )}

      {/* 3-Panel Layout */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* Left Sidebar: Node Types */}
        {leftOpen && (
          <div style={{
            width: 200, flexShrink: 0, overflowY: "auto",
            background: CN.bgCard, borderRight: `1px solid ${CN.border}`, padding: "12px 0",
          }}>
            <div style={{ padding: "0 12px 8px", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px" }}>
              NODE TYPES
            </div>
            {topTypes.map(([type, count]) => (
              <button key={type}
                onClick={() => { setSearchQuery(type); handleNodeDblClick(type, type); }}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  width: "100%", padding: "5px 12px", fontSize: 11, color: CN.text,
                  background: "transparent", border: "none", cursor: "pointer", textAlign: "left",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = CN.bgElevated)}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: NODE_COLORS[type] || "#94A3B8", flexShrink: 0 }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 110 }}>{type}</span>
                </span>
                <span style={{ color: CN.textMuted, fontSize: 10, fontVariantNumeric: "tabular-nums" }}>
                  {count > 999 ? `${(count / 1000).toFixed(1)}K` : count}
                </span>
              </button>
            ))}

            <div style={{ padding: "16px 12px 8px", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px", borderTop: `1px solid ${CN.border}`, marginTop: 8 }}>
              LAYER GROUPS
            </div>
            {Object.entries(LAYER_GROUPS).map(([name, info]) => (
              <div key={name} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 12px", fontSize: 11, color: CN.textSecondary }}>
                <span style={{ width: 10, height: 10, background: info.color, flexShrink: 0 }} />
                <span>{name}</span>
                <span style={{ fontSize: 9, color: CN.textMuted }}>({info.nodes.length})</span>
              </div>
            ))}
          </div>
        )}

        {/* Center: Graph Canvas — takes ALL remaining width */}
        <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
          {graphData.nodes.length === 0 && !loading && (
            <div style={{
              position: "absolute", inset: 0, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", color: CN.textMuted, zIndex: 2,
            }}>
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 16, opacity: 0.3 }}>
                <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="5" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="19" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="5" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="19" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                <path d="M7 6.5L9.5 10M14.5 10L17 6.5M9.5 14L7 17.5M14.5 14L17 17.5" stroke="currentColor" strokeWidth="1" />
              </svg>
              <span style={{ fontSize: 15, color: CN.textSecondary }}>Search to explore the Knowledge Graph</span>
              <span style={{ fontSize: 12, marginTop: 6, color: CN.textMuted }}>Double-click nodes to expand connections</span>
            </div>
          )}
          <CytoscapeGraph ref={graphRef} data={graphData} onNodeSelect={setSelectedNode} onNodeDblClick={handleNodeDblClick} />
        </div>

        {/* Right Panel: Node Detail */}
        {selectedNode && (
          <div style={{
            width: 300, flexShrink: 0, overflowY: "auto",
            background: CN.bgCard, borderLeft: `1px solid ${CN.border}`, padding: 16,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: CN.text, margin: 0 }}>
                {selectedNode.label}
              </h3>
              <button onClick={() => setSelectedNode(null)}
                style={{ background: "none", border: "none", color: CN.textMuted, cursor: "pointer", fontSize: 18 }}>
                x
              </button>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>Type</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: NODE_COLORS[selectedNode.type] || "#94A3B8" }} />
                <span style={{ fontSize: 13, color: CN.text }}>{selectedNode.type}</span>
              </div>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>ID</div>
              <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2, wordBreak: "break-all", fontFamily: "monospace" }}>
                {selectedNode.id}
              </div>
            </div>

            <div style={{ borderTop: `1px solid ${CN.border}`, paddingTop: 12, marginTop: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>
                Connections ({selectedNode.neighbors.length})
              </div>
              {selectedNode.neighbors.map((nb, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "5px 0", borderBottom: `1px solid ${CN.bgElevated}`, fontSize: 12,
                }}>
                  <span style={{ color: CN.text, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {nb.direction === "incoming" ? "\u2190 " : "\u2192 "}{nb.target_label}
                  </span>
                  <span style={cnBadge(EDGE_COLORS[nb.edge_type] || CN.textMuted, CN.bgElevated)}>
                    {EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type}
                  </span>
                </div>
              ))}
            </div>

            <button
              onClick={() => handleNodeDblClick(selectedNode.id, selectedNode.type)}
              style={{
                width: "100%", marginTop: 16, padding: "8px 0",
                background: CN.blueBg, border: `1px solid ${CN.border}`,
                color: CN.blue, fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              Expand from this node
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
