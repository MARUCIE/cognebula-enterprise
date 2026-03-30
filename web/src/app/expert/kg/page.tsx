"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  getStats, getGraph, searchNodes, getNodeDetail, listNodes,
  NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS, LAYER_GROUPS, getNodeLayer,
  type KGStats, type KGNeighbor, type KGNodeDetail,
} from "../../lib/kg-api";
import type { GraphData, SelectedNode, CytoscapeGraphHandle } from "../../components/CytoscapeGraph";
import type { Graph3DData, Selected3DNode, ForceGraph3DHandle } from "../../components/ForceGraph3D";
import { CN, cnInput, cnBtn, cnBtnPrimary, cnBadge } from "../../lib/cognebula-theme";

const CytoscapeGraph = dynamic(() => import("../../components/CytoscapeGraph"), { ssr: false });
const ForceGraph3D = dynamic(() => import("../../components/ForceGraph3D"), { ssr: false });

const TAX_NAME_MAP: Record<string, string> = {
  "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT", "消费税": "TT_CONSUMPTION",
  "关税": "TT_TARIFF", "城建税": "TT_URBAN", "教育费附加": "TT_EDUCATION", "资源税": "TT_RESOURCE",
  "土地增值税": "TT_LAND_VAT", "房产税": "TT_PROPERTY", "印花税": "TT_STAMP", "契税": "TT_CONTRACT",
  "车船税": "TT_VEHICLE", "环保税": "TT_ENV", "烟叶税": "TT_TOBACCO",
};

/* ── Node type Chinese names + descriptions ── */
/* v4.1 Ontology — 21 node types */
const NODE_ZH: Record<string, { zh: string; desc: string }> = {
  // L1 法规层 (3)
  LegalDocument: { zh: "法律文件", desc: "法律、法规、规章、会计准则的完整文档" },
  LegalClause: { zh: "法规条款", desc: "从法律文件中提取的逐条条款" },
  IssuingBody: { zh: "发布机构", desc: "法规的颁布机关 (财政部、税务总局等)" },
  // L2 业务层 (7)
  TaxRate: { zh: "税率", desc: "各税种的适用税率及计算规则" },
  AccountingSubject: { zh: "会计科目", desc: "企业会计核算的科目体系" },
  Classification: { zh: "分类体系", desc: "HS编码/税收分类编码/行业分类" },
  TaxEntity: { zh: "纳税主体", desc: "纳税人类型 (一般纳税人/小规模等)" },
  Region: { zh: "行政区划", desc: "省/市/区/国际地区" },
  FilingForm: { zh: "申报表", desc: "纳税申报使用的表单模板" },
  BusinessActivity: { zh: "经营活动", desc: "企业经营行为分类 (销售/服务/投资等)" },
  // L3 合规层 (9)
  ComplianceRule: { zh: "合规规则", desc: "企业必须遵守的财税合规条件" },
  RiskIndicator: { zh: "风险指标", desc: "税务风险预警指标及触发阈值" },
  TaxIncentive: { zh: "税收优惠", desc: "减免税、加计扣除等优惠政策" },
  Penalty: { zh: "处罚规定", desc: "违规行为对应的罚则和处罚标准" },
  AuditTrigger: { zh: "审计触发", desc: "触发税务稽查的异常指标" },
  TaxAccountingGap: { zh: "税会差异", desc: "会计处理与税务处理的差异项 (50项)" },
  SocialInsuranceRule: { zh: "社保公积金", desc: "各城市社保/公积金费率规则" },
  InvoiceRule: { zh: "发票规则", desc: "增值税发票管理的认证/抵扣/红冲规则" },
  IndustryBenchmark: { zh: "行业基准", desc: "各行业税负率/利润率预警基准" },
  // L4 知识层 (2)
  TaxType: { zh: "税种", desc: "中国现行 18 个税种 (增值税/所得税等)" },
  KnowledgeUnit: { zh: "知识单元", desc: "从教材/指南/FAQ提取的知识点" },
};

function getNodeZh(type: string): string {
  return NODE_ZH[type]?.zh || type;
}

export default function KGExplorerPage() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [], groups: [] });
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);
  const [stats, setStats] = useState<KGStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentLayout, setCurrentLayout] = useState("fcose");
  const [leftOpen, setLeftOpen] = useState(true);
  const [nodeDetail, setNodeDetail] = useState<KGNodeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set(["L1 法规层", "L3 合规层"]));
  const [viewMode, setViewMode] = useState<"3d" | "2d">("3d");
  const [graph3DData, setGraph3DData] = useState<Graph3DData>({ nodes: [], links: [] });
  const [drillLayer, setDrillLayer] = useState<string | null>(null);
  const graphRef = useRef<CytoscapeGraphHandle>(null);
  const graph3DRef = useRef<ForceGraph3DHandle>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setError("KG API 无法连接"));
  }, []);

  // Build 3D overview: load 200+ real nodes across all types for dense sphere
  useEffect(() => {
    if (!stats) return;
    if (drillLayer) return;

    async function loadOverviewSphere() {
      setLoading(true);
      const nodes: Graph3DData["nodes"] = [];
      const links: Graph3DData["links"] = [];
      const addedNodes = new Set<string>();

      // Curated v4.1 types with meaningful labels (not bulk legacy tables)
      const OVERVIEW_TYPES: [string, number][] = [
        // v4.1 core types with rich names — show more of these
        ["TaxType", 19], ["TaxIncentive", 15], ["ComplianceRule", 12],
        ["TaxRate", 10], ["TaxAccountingGap", 10], ["SocialInsuranceRule", 10],
        ["InvoiceRule", 8], ["IndustryBenchmark", 8], ["AuditTrigger", 8],
        ["Penalty", 8], ["TaxEntity", 8], ["BusinessActivity", 8],
        ["AccountingSubject", 8], ["FilingForm", 8], ["Region", 8],
        ["IssuingBody", 8], ["RiskIndicator", 8],
        // Bulk tables: tiny sample only
        ["LegalDocument", 5], ["LegalClause", 5], ["KnowledgeUnit", 3],
        ["FAQEntry", 5],
      ];

      for (const [type, sampleSize] of OVERVIEW_TYPES) {
        if (!stats!.nodes_by_type[type]) continue;
        const count = stats!.nodes_by_type[type] || 0;
        try {
          const res = await listNodes(type, sampleSize);
          for (const item of (res.results || [])) {
            const nodeId = String(item.id || "");
            if (!nodeId || addedNodes.has(nodeId)) continue;
            const nodeLabel = String(item.title || item.name || item._display_label || item.topic || "").slice(0, 20);
            // Skip nodes with meaningless labels (numbers, hashes, codes)
            if (!nodeLabel || nodeLabel.startsWith("...") || /^[\d.\-/%]+$/.test(nodeLabel) || /^0\d章/.test(nodeLabel)) continue;
            addedNodes.add(nodeId);
            nodes.push({
              id: nodeId,
              label: nodeLabel,
              type,
              color: NODE_COLORS[type] || "#94A3B8",
              size: Math.max(2, 3 + Math.log10(count + 1) * 1.5),
              group: getNodeLayer(type),
            });
          }
        } catch { /* skip */ }
      }

      // Fetch edges for more nodes to create dense web of connections
      const nodesToExpand = nodes.slice(0, 50);
      for (const node of nodesToExpand) {
        try {
          const gr = await getGraph(node.type, node.id);
          for (const nb of (gr.neighbors || []).slice(0, 6)) {
            if (!nb.target_id) continue;
            // Link to existing node if present
            if (addedNodes.has(nb.target_id)) {
              links.push({
                source: node.id, target: nb.target_id,
                label: EDGE_LABELS_ZH[nb.edge_type] || "",
                color: EDGE_COLORS[nb.edge_type] || "#30363D",
              });
            } else if (nodes.length < 350) {
              // Add neighbor as new node (skip meaningless labels)
              const nbLabel = (nb.target_label || "").slice(0, 20);
              if (!nbLabel || nbLabel.startsWith("...") || /^[\d.\-/%]+$/.test(nbLabel)) continue;
              addedNodes.add(nb.target_id);
              nodes.push({
                id: nb.target_id,
                label: nbLabel,
                type: nb.target_type,
                color: NODE_COLORS[nb.target_type] || "#94A3B8",
                size: 2,
                group: getNodeLayer(nb.target_type),
              });
              links.push({
                source: node.id, target: nb.target_id,
                label: "",
                color: EDGE_COLORS[nb.edge_type] || "#30363D",
              });
            }
          }
        } catch { /* skip */ }
      }

      setGraph3DData({ nodes, links });
      setLoading(false);
    }

    loadOverviewSphere();
  }, [stats, drillLayer]);

  // ── Drill-down navigation stack ──
  const [drillStack, setDrillStack] = useState<{ id: string; label: string; type: string }[]>([]);

  // Single click: show detail panel
  const handle3DNodeClick = useCallback((node: Selected3DNode) => {
    setSelectedNode({
      id: node.id, label: node.label, type: node.type, neighbors: node.neighbors,
    });
  }, []);

  // Double click: drill into node (load its neighbors as new sphere)
  const handle3DDrillDown = useCallback(async (nodeId: string, nodeType: string) => {
    if (loading) return;
    const nodeLabel = graph3DData.nodes.find((n) => n.id === nodeId)?.label || nodeId;

    setLoading(true);
    setDrillStack((prev) => [...prev, { id: nodeId, label: nodeLabel, type: nodeType }]);

    const nodes: Graph3DData["nodes"] = [];
    const links: Graph3DData["links"] = [];
    const addedNodes = new Set<string>();

    // Center node (the one we drilled into)
    addedNodes.add(nodeId);
    nodes.push({
      id: nodeId,
      label: nodeLabel.slice(0, 20),
      type: nodeType,
      color: NODE_COLORS[nodeType] || "#58A6FF",
      size: 20, // large center
    });

    // Load its neighbors (depth 1)
    try {
      const gr = await getGraph(nodeType, nodeId);
      for (const nb of (gr.neighbors || []).slice(0, 30)) {
        if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
        addedNodes.add(nb.target_id);
        nodes.push({
          id: nb.target_id,
          label: (nb.target_label || "").slice(0, 18),
          type: nb.target_type,
          color: NODE_COLORS[nb.target_type] || "#94A3B8",
          size: 8,
        });
        links.push({
          source: nodeId, target: nb.target_id,
          label: EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type.slice(0, 10),
          color: EDGE_COLORS[nb.edge_type] || "#4B5563",
        });
      }

      // Depth 2: expand top neighbors to find cross-links
      const depth2Nodes = nodes.filter((n) => n.id !== nodeId).slice(0, 10);
      for (const d2 of depth2Nodes) {
        try {
          const gr2 = await getGraph(d2.type, d2.id);
          for (const nb of (gr2.neighbors || []).slice(0, 4)) {
            if (!nb.target_id) continue;
            if (addedNodes.has(nb.target_id)) {
              // Cross-link between existing nodes
              links.push({
                source: d2.id, target: nb.target_id,
                label: EDGE_LABELS_ZH[nb.edge_type] || "",
                color: EDGE_COLORS[nb.edge_type] || "#30363D",
              });
            } else if (nodes.length < 150) {
              addedNodes.add(nb.target_id);
              nodes.push({
                id: nb.target_id,
                label: (nb.target_label || "").slice(0, 18),
                type: nb.target_type,
                color: NODE_COLORS[nb.target_type] || "#94A3B8",
                size: 4,
              });
              links.push({
                source: d2.id, target: nb.target_id,
                label: "",
                color: EDGE_COLORS[nb.edge_type] || "#30363D",
              });
            }
          }
        } catch { /* skip */ }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "下钻失败");
    }

    setGraph3DData({ nodes, links });
    setDrillLayer(nodeId); // mark as drilled
    setLoading(false);
  }, [loading, graph3DData]);

  // Go back one level in drill stack
  const handleDrillBack = useCallback(() => {
    setDrillStack((prev) => {
      const next = prev.slice(0, -1);
      if (next.length === 0) {
        // Back to overview
        setDrillLayer(null);
      } else {
        // Re-drill into parent
        const parent = next[next.length - 1];
        // Trigger re-drill by temporarily clearing
        setDrillLayer(null);
        setTimeout(() => {
          handle3DDrillDown(parent.id, parent.type);
          setDrillStack(next);
        }, 100);
      }
      return next.length === 0 ? [] : next;
    });
  }, [handle3DDrillDown]);

  // Legacy: drill into a layer (kept for sidebar click)
  const drillIntoLayerTypes = useCallback(async (types: string[]) => {
    setLoading(true);
    const nodes: Graph3DData["nodes"] = [];
    const links: Graph3DData["links"] = [];
    const addedNodes = new Set<string>();

    for (const type of types.slice(0, 6)) {
      try {
        const res = await listNodes(type, 5);
        for (const item of (res.results || [])) {
          const nodeId = String(item.id || "");
          const nodeLabel = String(item.title || item.name || item._display_label || nodeId);
          if (!nodeId || addedNodes.has(nodeId)) continue;
          addedNodes.add(nodeId);
          nodes.push({
            id: nodeId,
            label: nodeLabel.slice(0, 25),
            type,
            color: NODE_COLORS[type] || "#94A3B8",
            size: 15,
          });

          try {
            const gr = await getGraph(type, nodeId);
            for (const nb of (gr.neighbors || []).slice(0, 3)) {
              if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
              addedNodes.add(nb.target_id);
              nodes.push({
                id: nb.target_id,
                label: (nb.target_label || nb.target_id).slice(0, 25),
                type: nb.target_type,
                color: NODE_COLORS[nb.target_type] || "#94A3B8",
                size: 8,
              });
              links.push({
                source: nodeId, target: nb.target_id,
                label: EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type.slice(0, 10),
                color: EDGE_COLORS[nb.edge_type] || "#4B5563",
              });
            }
          } catch { /* skip */ }
        }
      } catch { /* skip */ }
    }
    setGraph3DData({ nodes, links });
    setLoading(false);
  }, []);

  // Fetch full node detail when a node is selected
  useEffect(() => {
    if (!selectedNode) { setNodeDetail(null); return; }
    setDetailLoading(true);
    getNodeDetail(selectedNode.type, selectedNode.id)
      .then((d) => setNodeDetail(d))
      .catch(() => setNodeDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedNode?.id, selectedNode?.type]);

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

      // Cap per edge type to prevent any single type from dominating (e.g., MAPS_TO_ACCOUNT 43)
      const edgeTypeCounts: Record<string, number> = {};
      const MAX_PER_EDGE_TYPE = 8;
      const MAX_TOTAL = 40;
      let totalAdded = 0;
      for (const nb of neighbors) {
        if (totalAdded >= MAX_TOTAL) break;
        if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
        const etCount = edgeTypeCounts[nb.edge_type] || 0;
        if (etCount >= MAX_PER_EDGE_TYPE) continue;
        edgeTypeCounts[nb.edge_type] = etCount + 1;
        totalAdded++;
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
      if (!results.length) { setError(`未找到: ${q}`); setLoading(false); return; }

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
    } catch (e) { setError(e instanceof Error ? e.message : "搜索失败"); }
    setLoading(false);
  }, [searchQuery, buildGraphFromTraversal]);

  // Browse a node type: load sample nodes and build graph
  const handleBrowseType = useCallback(async (nodeType: string) => {
    setLoading(true);
    setError(null);
    setSearchQuery(getNodeZh(nodeType));
    try {
      const res = await listNodes(nodeType, 8);
      const results = res.results || [];
      if (!results.length) { setError(`${getNodeZh(nodeType)} 暂无数据`); setLoading(false); return; }

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
        const nodeId = String(item.id || "");
        const nodeLabel = String(item.title || item.name || item._display_label || item.topic || nodeId);
        if (!nodeId || addedNodes.has(nodeId)) continue;
        addedNodes.add(nodeId);
        const layer = ensureGroup(nodeType);
        allNodes.push({ id: nodeId, label: nodeLabel.slice(0, 30), type: nodeType, color: NODE_COLORS[nodeType] || "#94A3B8", size: 25, parent: layer });

        try {
          const graphResult = await getGraph(nodeType, nodeId);
          for (const nb of (graphResult.neighbors || []).slice(0, 5)) {
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
    } catch (e) { setError(e instanceof Error ? e.message : "浏览失败"); }
    setLoading(false);
  }, [buildGraphFromTraversal]);

  const handleNodeDblClick = useCallback(async (nodeId: string, nodeType: string) => {
    setLoading(true);
    try {
      const result = await getGraph(nodeType, nodeId);
      if (result.node) setGraphData(buildGraphFromTraversal(nodeType, nodeId, result.node._label || nodeId, result.neighbors));
    } catch (e) { setError(e instanceof Error ? e.message : "展开失败"); }
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
      {/* Toolbar — light background */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 32px", flexShrink: 0,
        background: CN.bg, borderBottom: `1px solid ${CN.border}`,
      }}>
        <button onClick={() => setLeftOpen(!leftOpen)} style={{ ...cnBtn, padding: "7px 10px", fontSize: 14 }}>
          {leftOpen ? "\u25C0" : "\u25B6"}
        </button>
        <input
          type="text"
          placeholder="搜索实体 (如: 增值税, TT_VAT, 企业所得税法)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          style={{ ...cnInput, flex: 1, maxWidth: 480 }}
        />
        <button onClick={handleSearch} disabled={loading}
          style={{ ...cnBtnPrimary, opacity: loading ? 0.5 : 1, cursor: loading ? "wait" : "pointer" }}>
          {loading ? "..." : "搜索"}
        </button>
        {viewMode === "2d" && <button onClick={() => graphRef.current?.fit()} style={cnBtn}>重置</button>}
        {viewMode === "2d" && <button onClick={toggleLayout} style={cnBtn}>布局: {currentLayout}</button>}
        {drillStack.length > 0 && viewMode === "3d" && (
          <button onClick={handleDrillBack} style={{ ...cnBtn, color: CN.blue, borderColor: CN.blue }}>
            &larr; 返回
          </button>
        )}
        {/* Breadcrumb */}
        {drillStack.length > 0 && viewMode === "3d" && (
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: CN.textMuted }}>
            <span style={{ cursor: "pointer", color: CN.blue }} onClick={() => { setDrillStack([]); setDrillLayer(null); }}>总览</span>
            {drillStack.map((item, i) => (
              <span key={i}>
                <span style={{ color: CN.textMuted, margin: "0 2px" }}>/</span>
                <span style={{ color: i === drillStack.length - 1 ? CN.text : CN.blue, fontWeight: i === drillStack.length - 1 ? 600 : 400 }}>
                  {(NODE_ZH[item.type]?.zh ? `${item.label}` : item.label).slice(0, 15)}
                </span>
              </span>
            ))}
          </div>
        )}
        <button
          onClick={() => setViewMode(viewMode === "3d" ? "2d" : "3d")}
          style={{ ...cnBtn, color: viewMode === "3d" ? CN.blue : CN.textSecondary, borderColor: viewMode === "3d" ? CN.blue : CN.border }}
        >
          {viewMode === "3d" ? "3D" : "2D"}
        </button>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 16, fontSize: 12, color: CN.textMuted }}>
          {viewMode === "3d" ? (
            <span>3D: <strong style={{ color: CN.blue }}>{graph3DData.nodes.length}</strong> 节点{drillLayer && ` -- ${drillLayer}`}</span>
          ) : (
            <>
              <span>图谱: <strong style={{ color: CN.blue }}>{graphData.nodes.length}</strong> 节点</span>
              <span><strong style={{ color: CN.blue }}>{graphData.edges.length}</strong> 边</span>
            </>
          )}
          {stats && (
            <span>KG: <strong style={{ color: CN.green }}>{(stats.total_nodes / 1000).toFixed(0)}K</strong> / <strong style={{ color: CN.green }}>{(stats.total_edges / 1000).toFixed(0)}K</strong></span>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: "8px 32px", background: CN.redBg, color: CN.red, fontSize: 13, borderBottom: `1px solid ${CN.border}` }}>
          {error}
        </div>
      )}

      {/* 3-Panel Layout */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* Left Sidebar: Node Types grouped by layer, collapsible, Chinese names */}
        {leftOpen && (
          <div style={{
            width: 240, flexShrink: 0, overflowY: "auto",
            background: CN.bgCard, borderRight: `1px solid ${CN.border}`,
          }}>
            {Object.entries(LAYER_GROUPS).map(([layerName, layerInfo]) => {
              const isExpanded = expandedLayers.has(layerName);
              const toggleLayer = () => {
                setExpandedLayers((prev) => {
                  const next = new Set(prev);
                  if (next.has(layerName)) next.delete(layerName);
                  else next.add(layerName);
                  return next;
                });
              };
              // Get node types in this layer that exist in stats
              const layerNodes = layerInfo.nodes
                .map((type) => ({ type, count: stats?.nodes_by_type?.[type] || 0 }))
                .filter((n) => n.count > 0)
                .sort((a, b) => b.count - a.count);
              const layerTotal = layerNodes.reduce((s, n) => s + n.count, 0);

              return (
                <div key={layerName}>
                  {/* Layer header — clickable to expand/collapse */}
                  <button
                    onClick={toggleLayer}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      width: "100%", padding: "10px 12px", fontSize: 11, fontWeight: 700,
                      color: CN.textSecondary, background: CN.bgElevated,
                      border: "none", borderBottom: `1px solid ${CN.border}`,
                      cursor: "pointer", textAlign: "left", letterSpacing: "0.5px",
                    }}
                  >
                    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 10, height: 10, background: layerInfo.color, borderRadius: 2, flexShrink: 0, border: `1px solid ${layerInfo.darkColor}` }} />
                      <span>{isExpanded ? "v" : ">"} {layerName}</span>
                    </span>
                    <span style={{ fontSize: 10, color: CN.textMuted, fontVariantNumeric: "tabular-nums" }}>
                      {layerTotal > 999 ? `${(layerTotal / 1000).toFixed(1)}K` : layerTotal}
                    </span>
                  </button>

                  {/* Expanded: list node types in this layer */}
                  {isExpanded && layerNodes.map(({ type, count }) => {
                    const info = NODE_ZH[type];
                    const zhName = info?.zh || type;
                    const desc = info?.desc || "";
                    return (
                      <button key={type}
                        onClick={() => handleBrowseType(type)}
                        title={`${type}: ${desc}`}
                        style={{
                          display: "flex", alignItems: "center", justifyContent: "space-between",
                          width: "100%", padding: "6px 12px 6px 24px", fontSize: 12, color: CN.text,
                          background: "transparent", border: "none", cursor: "pointer", textAlign: "left",
                          borderBottom: `1px solid ${CN.bgElevated}`,
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = CN.bgElevated)}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <span style={{ display: "flex", flexDirection: "column", gap: 1, minWidth: 0 }}>
                          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ width: 6, height: 6, borderRadius: "50%", background: NODE_COLORS[type] || "#94A3B8", flexShrink: 0 }} />
                            <span style={{ fontWeight: 600 }}>{zhName}</span>
                          </span>
                          <span style={{ fontSize: 10, color: CN.textMuted, paddingLeft: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {desc}
                          </span>
                        </span>
                        <span style={{ color: CN.textMuted, fontSize: 10, fontVariantNumeric: "tabular-nums", flexShrink: 0, marginLeft: 8 }}>
                          {count > 999 ? `${(count / 1000).toFixed(1)}K` : count}
                        </span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}

        {/* Center: Graph Canvas */}
        <div style={{ flex: 1, position: "relative", minWidth: 0, background: CN.bgCanvas }}>
          {viewMode === "3d" ? (
            /* ── 3D Force Graph ── */
            <>
              {graph3DData.nodes.length === 0 && !loading && (
                <div style={{
                  position: "absolute", inset: 0, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", color: "#8B949E", zIndex: 2,
                }}>
                  <span style={{ fontSize: 15, color: "#E6EDF3" }}>加载 3D 图谱...</span>
                </div>
              )}
              <ForceGraph3D
                ref={graph3DRef}
                data={graph3DData}
                onNodeSelect={handle3DNodeClick as any}
                onNodeDblClick={(id, type) => handle3DDrillDown(id, type)}
              />
              {/* Loading overlay */}
              {loading && (
                <div style={{
                  position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                  background: "rgba(8,12,20,0.6)", zIndex: 20,
                }}>
                  <div style={{ color: "#58A6FF", fontSize: 14, fontWeight: 600 }}>
                    加载知识图谱...
                  </div>
                </div>
              )}
              {/* 3D hint overlay */}
              {graph3DData.nodes.length > 0 && !loading && (
                <div style={{
                  position: "absolute", bottom: 16, left: "50%", transform: "translateX(-50%)",
                  background: "rgba(13,17,23,0.85)", padding: "8px 20px", borderRadius: 8,
                  fontSize: 12, color: "#8B949E", zIndex: 10, whiteSpace: "nowrap",
                }}>
                  单击查看详情 | 双击下钻进入 | 鼠标拖拽旋转 | 滚轮缩放
                </div>
              )}
            </>
          ) : (
            /* ── 2D Cytoscape Graph ── */
            <>
              {graphData.nodes.length === 0 && !loading && (
                <div style={{
                  position: "absolute", inset: 0, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", color: "#8B949E", zIndex: 2,
                }}>
                  <svg width="56" height="56" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 16, opacity: 0.3 }}>
                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="5" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="19" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="5" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="19" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M7 6.5L9.5 10M14.5 10L17 6.5M9.5 14L7 17.5M14.5 14L17 17.5" stroke="currentColor" strokeWidth="1" />
                  </svg>
                  <span style={{ fontSize: 15, color: "#E6EDF3" }}>搜索实体开始探索知识图谱</span>
                  <span style={{ fontSize: 12, marginTop: 6, color: "#8B949E" }}>双击节点可展开关联</span>
                </div>
              )}
              <CytoscapeGraph ref={graphRef} data={graphData} onNodeSelect={setSelectedNode} onNodeDblClick={handleNodeDblClick} />
            </>
          )}
        </div>

        {/* Right Panel: Node Detail — light panel with full content */}
        {selectedNode && (
          <div style={{
            width: 340, flexShrink: 0, overflowY: "auto",
            background: CN.bgCard, borderLeft: `1px solid ${CN.border}`, padding: 16,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: CN.text, margin: 0, maxWidth: 260 }}>
                {selectedNode.label}
              </h3>
              <button onClick={() => { setSelectedNode(null); setNodeDetail(null); }}
                style={{ background: "none", border: "none", color: CN.textMuted, cursor: "pointer", fontSize: 18 }}>
                x
              </button>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>类型</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: NODE_COLORS[selectedNode.type] || "#94A3B8" }} />
                <span style={{ fontSize: 13, color: CN.text }}>{selectedNode.type}</span>
              </div>
            </div>

            {/* Full Content Section */}
            {detailLoading && (
              <div style={{ padding: 8, color: CN.textMuted, fontSize: 12 }}>加载详情...</div>
            )}

            {nodeDetail && (
              <>
                {/* Title / Name */}
                {(nodeDetail.title || nodeDetail.name) && (nodeDetail.title || nodeDetail.name) !== selectedNode.label && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>标题</div>
                    <div style={{ fontSize: 13, color: CN.text, lineHeight: 1.6 }}>
                      {nodeDetail.title || nodeDetail.name}
                    </div>
                  </div>
                )}

                {/* Full Text / Content / Description */}
                {(nodeDetail.fullText || nodeDetail.content || nodeDetail.description) && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>
                      {nodeDetail.fullText ? "全文内容" : nodeDetail.content ? "内容" : "描述"}
                    </div>
                    <div style={{
                      fontSize: 12, color: CN.textSecondary, lineHeight: 1.8,
                      maxHeight: 300, overflowY: "auto",
                      padding: "10px 12px", background: CN.bg, border: `1px solid ${CN.border}`,
                      borderRadius: 4, whiteSpace: "pre-wrap",
                    }}>
                      {nodeDetail.fullText || nodeDetail.content || nodeDetail.description}
                    </div>
                  </div>
                )}

                {/* Metadata fields */}
                {(() => {
                  const metaFields: [string, string, unknown][] = [
                    ["文号", "regulationNumber", nodeDetail.regulationNumber],
                    ["生效日期", "effectiveDate", nodeDetail.effectiveDate],
                    ["层级", "hierarchyLevel", nodeDetail.hierarchyLevel],
                    ["类型", "regulationType", nodeDetail.regulationType],
                    ["状态", "status", nodeDetail.status],
                    ["来源", "sourceUrl", nodeDetail.sourceUrl],
                  ];
                  const visible = metaFields.filter(([, , v]) => v && String(v).length > 0 && String(v) !== "undefined" && String(v) !== "null");
                  if (visible.length === 0) return null;
                  return (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>属性</div>
                      <div style={{ display: "grid", gridTemplateColumns: "80px 1fr", gap: "4px 8px", fontSize: 12 }}>
                        {visible.map(([label, , value]) => (
                          <React.Fragment key={label}>
                            <span style={{ color: CN.textMuted, fontWeight: 600 }}>{label}</span>
                            {String(value).startsWith("http") ? (
                              <a href={String(value)} target="_blank" rel="noopener noreferrer"
                                style={{ color: CN.blue, textDecoration: "none", wordBreak: "break-all" }}>
                                {String(value).slice(0, 60)}...
                              </a>
                            ) : (
                              <span style={{ color: CN.text, wordBreak: "break-all" }}>{String(value)}</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  );
                })()}

                {/* Extra KG properties (dynamic) */}
                {(() => {
                  const knownFields = new Set(["id", "title", "name", "fullText", "content", "description",
                    "regulationNumber", "effectiveDate", "hierarchyLevel", "regulationType", "status",
                    "sourceUrl", "_display_label", "_label", "createdAt"]);
                  const extra = Object.entries(nodeDetail).filter(
                    ([k, v]) => !knownFields.has(k) && v !== null && v !== undefined && String(v).length > 0 && String(v) !== "undefined"
                  );
                  if (extra.length === 0) return null;
                  return (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>其他属性</div>
                      <div style={{ fontSize: 11, lineHeight: 1.7 }}>
                        {extra.slice(0, 12).map(([k, v]) => (
                          <div key={k} style={{ display: "flex", gap: 8, marginBottom: 2 }}>
                            <span style={{ color: CN.textMuted, fontWeight: 600, minWidth: 80, flexShrink: 0 }}>{k}</span>
                            <span style={{ color: CN.textSecondary, wordBreak: "break-all" }}>{String(v).slice(0, 200)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </>
            )}

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>ID</div>
              <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2, wordBreak: "break-all", fontFamily: "monospace" }}>
                {selectedNode.id}
              </div>
            </div>

            <div style={{ borderTop: `1px solid ${CN.border}`, paddingTop: 12, marginTop: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>
                关联 ({selectedNode.neighbors.length})
              </div>
              {selectedNode.neighbors.map((nb, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "5px 0", borderBottom: `1px solid ${CN.bgElevated}`, fontSize: 12,
                  cursor: "pointer",
                }}
                  onClick={() => handleNodeDblClick(nb.target_id, nb.target_type)}
                >
                  <span style={{ color: CN.text, maxWidth: 170, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
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
                borderRadius: 6,
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
