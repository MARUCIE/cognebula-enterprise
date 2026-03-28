"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  getStats, getGraph, searchNodes,
  NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS, LAYER_GROUPS, getNodeLayer,
  type KGStats, type KGNeighbor,
} from "../../lib/kg-api";
import type { GraphData, SelectedNode, CytoscapeGraphHandle } from "../../components/CytoscapeGraph";

const CytoscapeGraph = dynamic(() => import("../../components/CytoscapeGraph"), { ssr: false });

/* TAX_NAME_MAP for direct lookup */
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
  const graphRef = useRef<CytoscapeGraphHandle>(null);

  /* Load stats on mount */
  useEffect(() => {
    getStats().then(setStats).catch(() => setError("无法连接 KG 服务"));
  }, []);

  /* Build graph data from API response */
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

      /* Center node */
      const centerLayer = ensureGroup(centerTable);
      addedNodes.add(centerId);
      nodes.push({
        id: centerId,
        label: centerLabel.slice(0, 30),
        type: centerTable,
        color: NODE_COLORS[centerTable] || "#8B5CF6",
        size: 45,
        parent: centerLayer,
      });

      /* Neighbors */
      for (const nb of neighbors.slice(0, 30)) {
        if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
        addedNodes.add(nb.target_id);
        const nbLayer = ensureGroup(nb.target_type);
        nodes.push({
          id: nb.target_id,
          label: (nb.target_label || nb.target_id).slice(0, 30),
          type: nb.target_type,
          color: NODE_COLORS[nb.target_type] || "#94A3B8",
          size: 15,
          parent: nbLayer,
        });
        const edgeType = nb.edge_type;
        const src = nb.direction === "incoming" ? nb.target_id : centerId;
        const tgt = nb.direction === "incoming" ? centerId : nb.target_id;
        edges.push({
          id: `${src}-${tgt}-${edgeType}`,
          source: src,
          target: tgt,
          label: EDGE_LABELS_ZH[edgeType] || edgeType.slice(0, 12),
          color: EDGE_COLORS[edgeType] || "#4B5563",
        });
      }

      return { nodes, edges, groups };
    },
    []
  );

  /* Search handler */
  const handleSearch = useCallback(async () => {
    const q = searchQuery.trim();
    if (!q) return;
    setLoading(true);
    setError(null);

    try {
      /* Direct TaxType lookup */
      if (TAX_NAME_MAP[q] || q.startsWith("TT_")) {
        const id = TAX_NAME_MAP[q] || q;
        const result = await getGraph("TaxType", id);
        if (result.node) {
          const data = buildGraphFromTraversal("TaxType", id, result.node._label || id, result.neighbors);
          setGraphData(data);
        }
        setLoading(false);
        return;
      }

      /* Vector search */
      const searchResult = await searchNodes(q, 10);
      const results = searchResult.results || [];
      if (!results.length) {
        setError(`未找到: ${q}`);
        setLoading(false);
        return;
      }

      const addedGroups = new Set<string>();
      const addedNodes = new Set<string>();
      const groups: GraphData["groups"] = [];
      const allNodes: GraphData["nodes"] = [];
      const allEdges: GraphData["edges"] = [];

      function ensureGroup(type: string) {
        const layer = getNodeLayer(type);
        if (!addedGroups.has(layer)) {
          addedGroups.add(layer);
          groups.push({ id: layer, label: layer });
        }
        return layer;
      }

      for (const item of results) {
        const nodeId = item.id || item.node_id || "";
        const nodeTable = item.table || item.source_table || "";
        const nodeLabel = item.text || item.title || item.name || nodeId;
        if (!nodeId || addedNodes.has(nodeId)) continue;
        addedNodes.add(nodeId);

        const layer = ensureGroup(nodeTable);
        allNodes.push({
          id: nodeId,
          label: nodeLabel.slice(0, 30),
          type: nodeTable,
          color: NODE_COLORS[nodeTable] || "#94A3B8",
          size: 25,
          parent: layer,
        });

        /* Fetch neighbors for each result */
        try {
          const graphResult = await getGraph(nodeTable, nodeId);
          for (const nb of (graphResult.neighbors || []).slice(0, 8)) {
            if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
            addedNodes.add(nb.target_id);
            const nbLayer = ensureGroup(nb.target_type);
            allNodes.push({
              id: nb.target_id,
              label: (nb.target_label || nb.target_id).slice(0, 30),
              type: nb.target_type,
              color: NODE_COLORS[nb.target_type] || "#94A3B8",
              size: 12,
              parent: nbLayer,
            });
            const edgeType = nb.edge_type;
            const src = nb.direction === "incoming" ? nb.target_id : nodeId;
            const tgt = nb.direction === "incoming" ? nodeId : nb.target_id;
            allEdges.push({
              id: `${src}-${tgt}-${edgeType}`,
              source: src,
              target: tgt,
              label: EDGE_LABELS_ZH[edgeType] || edgeType.slice(0, 12),
              color: EDGE_COLORS[edgeType] || "#4B5563",
            });
          }
        } catch {
          /* neighbor fetch failed, skip */
        }
      }

      setGraphData({ nodes: allNodes, edges: allEdges, groups });
    } catch (e) {
      setError(e instanceof Error ? e.message : "搜索失败");
    }
    setLoading(false);
  }, [searchQuery, buildGraphFromTraversal]);

  /* Double-click node: expand from that node */
  const handleNodeDblClick = useCallback(async (nodeId: string, nodeType: string) => {
    setLoading(true);
    try {
      const result = await getGraph(nodeType, nodeId);
      if (result.node) {
        const data = buildGraphFromTraversal(nodeType, nodeId, result.node._label || nodeId, result.neighbors);
        setGraphData(data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "展开失败");
    }
    setLoading(false);
  }, [buildGraphFromTraversal]);

  const toggleLayout = useCallback(() => {
    const layouts = ["fcose", "cose", "circle", "grid"];
    const idx = layouts.indexOf(currentLayout);
    const next = layouts[(idx + 1) % layouts.length];
    setCurrentLayout(next);
    graphRef.current?.runLayout(next);
  }, [currentLayout]);

  /* Top node types for sidebar */
  const topTypes = stats
    ? Object.entries(stats.nodes_by_type)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 12)
    : [];

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - var(--topbar-height))" }}>
      {/* Toolbar */}
      <div
        className="flex items-center gap-3 shrink-0"
        style={{
          padding: "8px 16px",
          background: "var(--color-surface-container-lowest)",
          borderBottom: "1px solid var(--color-surface-container)",
        }}
      >
        <input
          type="text"
          placeholder="搜索实体 (如: 增值税、企业所得税法、TT_VAT)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          style={{
            flex: 1,
            maxWidth: 420,
            padding: "7px 14px",
            border: "1px solid var(--color-surface-container)",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-surface-container-low)",
            color: "var(--color-text-primary)",
            fontSize: 13,
            outline: "none",
          }}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            padding: "7px 18px",
            borderRadius: "var(--radius-sm)",
            background: loading ? "var(--color-surface-container)" : "var(--color-primary)",
            color: "var(--color-on-primary)",
            fontSize: 13,
            fontWeight: 600,
            border: "none",
            cursor: loading ? "wait" : "pointer",
          }}
        >
          {loading ? "加载中..." : "搜索"}
        </button>
        <button onClick={() => graphRef.current?.fit()} style={toolbarBtnStyle}>
          重置视图
        </button>
        <button onClick={toggleLayout} style={toolbarBtnStyle}>
          布局: {currentLayout}
        </button>

        {/* Live stats */}
        <div className="flex items-center gap-4 ml-auto" style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
          <span>图内节点: <strong style={{ color: "var(--color-primary)" }}>{graphData.nodes.length}</strong></span>
          <span>图内边: <strong style={{ color: "var(--color-primary)" }}>{graphData.edges.length}</strong></span>
          {stats && (
            <span>KG 总量: <strong style={{ color: "var(--color-secondary-dim)" }}>{(stats.total_nodes / 1000).toFixed(0)}K</strong> / <strong style={{ color: "var(--color-secondary-dim)" }}>{(stats.total_edges / 1000).toFixed(0)}K</strong></span>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: "8px 16px", background: "color-mix(in srgb, var(--color-danger) 8%, var(--color-surface))", color: "var(--color-danger)", fontSize: 13, borderBottom: "1px solid var(--color-surface-container)" }}>
          {error}
        </div>
      )}

      {/* Main content: sidebar + graph + detail */}
      <div className="flex flex-1 min-h-0">
        {/* Left sidebar: node types */}
        <div
          className="shrink-0 overflow-y-auto"
          style={{
            width: 200,
            background: "var(--color-surface-container-lowest)",
            borderRight: "1px solid var(--color-surface-container)",
            padding: "12px 0",
          }}
        >
          <div style={{ padding: "0 12px 8px", fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
            节点类型 TOP-12
          </div>
          {topTypes.map(([type, count]) => (
            <button
              key={type}
              onClick={() => {
                setSearchQuery(type);
                handleNodeDblClick(type, type);
              }}
              className="flex items-center justify-between w-full text-left"
              style={{
                padding: "6px 12px",
                fontSize: 11,
                color: "var(--color-text-primary)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-surface-container-low)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span className="flex items-center gap-2">
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: NODE_COLORS[type] || "#94A3B8", flexShrink: 0 }} />
                <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 110 }}>{type}</span>
              </span>
              <span style={{ color: "var(--color-text-tertiary)", fontSize: 10 }}>{count > 999 ? `${(count / 1000).toFixed(1)}K` : count}</span>
            </button>
          ))}

          {/* Layer legend */}
          <div style={{ padding: "16px 12px 8px", fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.1em", borderTop: "1px solid var(--color-surface-container)", marginTop: 8 }}>
            层级分组
          </div>
          {Object.entries(LAYER_GROUPS).map(([name, info]) => (
            <div key={name} className="flex items-center gap-2" style={{ padding: "4px 12px", fontSize: 11, color: "var(--color-text-secondary)" }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: info.color, flexShrink: 0 }} />
              <span>{name}</span>
              <span style={{ fontSize: 9, color: "var(--color-text-tertiary)" }}>({info.nodes.length})</span>
            </div>
          ))}
        </div>

        {/* Center: Cytoscape graph — DARK CANVAS (intentional) */}
        <div className="flex-1 relative min-w-0">
          {graphData.nodes.length === 0 && !loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ color: "#6B7280", zIndex: 2 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 12, opacity: 0.4 }}>
                <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="5" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="19" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="5" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="19" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                <path d="M7 6.5L9.5 10M14.5 10L17 6.5M9.5 14L7 17.5M14.5 14L17 17.5" stroke="currentColor" strokeWidth="1" />
              </svg>
              <span style={{ fontSize: 14 }}>搜索实体开始探索知识图谱</span>
              <span style={{ fontSize: 12, marginTop: 4 }}>双击节点可展开关联</span>
            </div>
          )}
          <CytoscapeGraph
            ref={graphRef}
            data={graphData}
            onNodeSelect={setSelectedNode}
            onNodeDblClick={handleNodeDblClick}
          />
        </div>

        {/* Right panel: node detail */}
        {selectedNode && (
          <div
            className="shrink-0 overflow-y-auto"
            style={{
              width: 300,
              background: "var(--color-surface-container-lowest)",
              borderLeft: "1px solid var(--color-surface-container)",
              padding: 16,
            }}
          >
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>
                {selectedNode.label}
              </h3>
              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: "none", border: "none", color: "var(--color-text-tertiary)", cursor: "pointer", fontSize: 16 }}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>类型</div>
              <div className="flex items-center gap-2" style={{ marginTop: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: NODE_COLORS[selectedNode.type] || "#94A3B8" }} />
                <span style={{ fontSize: 13, color: "var(--color-text-primary)" }}>{selectedNode.type}</span>
              </div>
            </div>

            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>ID</div>
              <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: 2, wordBreak: "break-all" }}>
                {selectedNode.id}
              </div>
            </div>

            <div style={{ marginTop: 16, borderTop: "1px solid var(--color-surface-container)", paddingTop: 12 }}>
              <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                关联 ({selectedNode.neighbors.length})
              </div>
              {selectedNode.neighbors.map((nb, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between"
                  style={{ padding: "6px 0", borderBottom: "1px solid var(--color-surface-container-low)", fontSize: 12 }}
                >
                  <span style={{ color: "var(--color-text-primary)", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {nb.direction === "incoming" ? "← " : "→ "}{nb.target_label}
                  </span>
                  <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 6px", borderRadius: 3, background: "var(--color-surface-container-low)", color: EDGE_COLORS[nb.edge_type] || "var(--color-text-tertiary)", whiteSpace: "nowrap" }}>
                    {EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type}
                  </span>
                </div>
              ))}
            </div>

            <button
              onClick={() => handleNodeDblClick(selectedNode.id, selectedNode.type)}
              style={{
                width: "100%",
                marginTop: 16,
                padding: "8px 0",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-surface-container-low)",
                border: "1px solid var(--color-surface-container)",
                color: "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              以此节点为中心展开
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

const toolbarBtnStyle: React.CSSProperties = {
  padding: "7px 14px",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-surface-container-low)",
  color: "var(--color-text-secondary)",
  fontSize: 12,
  fontWeight: 500,
  border: "1px solid var(--color-surface-container)",
  cursor: "pointer",
};
