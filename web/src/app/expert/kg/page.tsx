"use client";

import React, { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  getStats, getGraph, searchNodes, getNodeDetail, listNodes, getConstellation, getConstellationByType,
  NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS, LAYER_GROUPS,
  type KGStats, type KGNeighbor, type KGNodeDetail,
} from "../../lib/kg-api";
import { CN, cnInput, cnBtn, cnBtnPrimary, cnBadge } from "../../lib/cognebula-theme";
const KnowledgeCardGraph = dynamic(() => import("../../components/KnowledgeCardGraph"), { ssr: false });
const SigmaGraph = dynamic(() => import("../../components/SigmaGraph"), { ssr: false });
import type { CardGraphNode, CardGraphEdge } from "../../components/KnowledgeCardGraph";
import type { SigmaGraphData } from "../../components/SigmaGraph";

const TAX_NAME_MAP: Record<string, string> = {
  "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT", "消费税": "TT_CONSUMPTION",
  "关税": "TT_TARIFF", "城建税": "TT_URBAN", "教育费附加": "TT_EDUCATION", "资源税": "TT_RESOURCE",
  "土地增值税": "TT_LAND_VAT", "房产税": "TT_PROPERTY", "印花税": "TT_STAMP", "契税": "TT_CONTRACT",
  "车船税": "TT_VEHICLE", "环保税": "TT_ENV", "烟叶税": "TT_TOBACCO",
};

/* ── Node type Chinese names + descriptions ── */
/* v4.1 Ontology — 21 node types */
const NODE_ZH: Record<string, { zh: string; desc: string }> = {
  // L1 法规层 (5)
  LegalDocument: { zh: "法律文件", desc: "法律、法规、规章、会计准则的完整文档" },
  LegalClause: { zh: "法规条款", desc: "从法律文件中提取的逐条条款" },
  IssuingBody: { zh: "发布机构", desc: "法规的颁布机关 (财政部、税务总局等)" },
  AccountingStandard: { zh: "会计准则", desc: "CAS 1-42 企业会计准则体系" },
  TaxTreaty: { zh: "税收协定", desc: "中国与20+国家/地区的双边税收协定" },
  // L2 业务层 (14)
  TaxRate: { zh: "税率", desc: "各税种的适用税率及计算规则" },
  AccountingSubject: { zh: "会计科目", desc: "企业会计核算的科目体系 (284个)" },
  Classification: { zh: "分类体系", desc: "HS编码/税收分类编码/行业分类" },
  TaxEntity: { zh: "纳税主体", desc: "纳税人类型 (一般纳税人/小规模等)" },
  Region: { zh: "行政区划", desc: "省/市/区/国际地区" },
  FilingForm: { zh: "申报表", desc: "纳税申报使用的表单模板" },
  BusinessActivity: { zh: "经营活动", desc: "企业经营行为分类 (销售/服务/投资等)" },
  JournalEntryTemplate: { zh: "分录模板", desc: "常见业务的标准会计分录 (30个)" },
  FinancialStatementItem: { zh: "报表项目", desc: "资产负债表/利润表/现金流量表项目" },
  FilingFormField: { zh: "申报栏次", desc: "申报表具体栏次的填报规则和公式" },
  TaxItem: { zh: "税目", desc: "消费税15目/印花税17目等税种细分" },
  TaxBasis: { zh: "计税依据", desc: "从价/从量/复合/收入型等计税方式" },
  TaxLiabilityTrigger: { zh: "纳税义务时点", desc: "增值税9项/所得税/个税等纳税义务发生时间" },
  TaxMilestoneEvent: { zh: "生命周期事件", desc: "企业设立→经营→并购→清算的税务节点" },
  // L3 合规层 (14)
  ComplianceRule: { zh: "合规规则", desc: "企业必须遵守的财税合规条件" },
  RiskIndicator: { zh: "风险指标", desc: "金税四期6模块49项风险监控指标" },
  TaxIncentive: { zh: "税收优惠", desc: "减免税、加计扣除等优惠政策" },
  Penalty: { zh: "处罚规定", desc: "违规行为对应的罚则和处罚标准" },
  AuditTrigger: { zh: "审计触发", desc: "3级20项税务稽查触发条件" },
  TaxAccountingGap: { zh: "税会差异", desc: "会计处理与税务处理的差异项 (50项)" },
  SocialInsuranceRule: { zh: "社保公积金", desc: "各城市社保/公积金费率规则" },
  InvoiceRule: { zh: "发票规则", desc: "增值税发票管理的认证/抵扣/红冲规则" },
  IndustryBenchmark: { zh: "行业基准", desc: "各行业税负率/利润率预警基准" },
  TaxCalculationRule: { zh: "计算规则", desc: "增值税/所得税/个税等税额计算公式" },
  FinancialIndicator: { zh: "财务指标", desc: "杜邦分析+流动性+偿债+效率+税负指标" },
  DeductionRule: { zh: "扣除限额", desc: "企业所得税/个税各项扣除标准" },
  ResponseStrategy: { zh: "应对策略", desc: "风险预警触发后的标准化应对方案" },
  PolicyChange: { zh: "政策变动", desc: "2022-2026年重大税收政策变更事件" },
  // L4 知识层 (2)
  TaxType: { zh: "税种", desc: "中国现行 18 个税种 (增值税/所得税等)" },
  KnowledgeUnit: { zh: "知识单元", desc: "从教材/指南/FAQ提取的知识点" },
};

export default function KGExplorerPage() {
  const [selectedNode, setSelectedNode] = useState<{ id: string; label: string; type: string; neighbors: KGNeighbor[] } | null>(null);
  const [stats, setStats] = useState<KGStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(true);
  const [nodeDetail, setNodeDetail] = useState<KGNodeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set(["L1 法规层", "L3 合规层"]));
  const [viewMode, setViewMode] = useState<"sigma" | "cards">("sigma");
  const [sigmaData, setSigmaData] = useState<SigmaGraphData>({ nodes: [], edges: [] });
  const [sigmaLoading, setSigmaLoading] = useState(false);
  const [sigmaHighlightTypes, setSigmaHighlightTypes] = useState<string[]>([]);
  const [cardType, setCardType] = useState("TaxType");
  const [cardNodes, setCardNodes] = useState<Record<string, unknown>[]>([]);
  const [cardGraphNodes, setCardGraphNodes] = useState<CardGraphNode[]>([]);
  const [cardGraphEdges, setCardGraphEdges] = useState<CardGraphEdge[]>([]);
  const [cardLoading, setCardLoading] = useState(false);
  const [cardPage, setCardPage] = useState(0);
  const CARD_PAGE_SIZE = 12;

  useEffect(() => {
    getStats().then(setStats).catch(() => setError("KG API 无法连接"));
  }, []);

  // Card view: load nodes + edges for card graph
  const loadCards = useCallback(async (type: string, page: number) => {
    setCardLoading(true);
    try {
      const res = await listNodes(type, CARD_PAGE_SIZE, page * CARD_PAGE_SIZE);
      const results = res.results || [];
      setCardNodes(results);

      // Build card graph: load neighbors for first N nodes to create edges
      const gNodes: CardGraphNode[] = [];
      const gEdges: CardGraphEdge[] = [];
      const addedIds = new Set<string>();

      for (const n of results) {
        const nid = String(n.id || "");
        if (!nid) continue;
        gNodes.push({ id: nid, label: String(n.name || n.title || n._display_label || ""), type, raw: n });
        addedIds.add(nid);
      }

      // Fetch edges for first 5 nodes (keep graph clean)
      for (const n of results.slice(0, 5)) {
        const nid = String(n.id || "");
        if (!nid) continue;
        try {
          const gr = await getGraph(type, nid);
          for (const nb of (gr.neighbors || []).slice(0, 3)) {
            if (!nb.target_id) continue;
            // Add neighbor as card if not already present
            if (!addedIds.has(nb.target_id)) {
              addedIds.add(nb.target_id);
              gNodes.push({ id: nb.target_id, label: nb.target_label || nb.target_id, type: nb.target_type, raw: {} });
            }
            const src = nb.direction === "incoming" ? nb.target_id : nid;
            const tgt = nb.direction === "incoming" ? nid : nb.target_id;
            gEdges.push({ source: src, target: tgt, label: EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type.slice(0, 8), edgeType: nb.edge_type });
          }
        } catch { /* skip */ }
      }
      setCardGraphNodes(gNodes);
      setCardGraphEdges(gEdges);
    } catch { setCardNodes([]); setCardGraphNodes([]); setCardGraphEdges([]); }
    setCardLoading(false);
  }, []);

  useEffect(() => {
    if (viewMode === "cards") loadCards(cardType, cardPage);
  }, [viewMode, cardType, cardPage, loadCards]);

  // Sigma: single API call for constellation data
  useEffect(() => {
    if (viewMode !== "sigma" || sigmaData.nodes.length > 0) return;
    setSigmaLoading(true);
    getConstellation(600)
      .then((data) => {
        setSigmaData({
          nodes: data.nodes,
          edges: data.edges.map((e) => ({ source: e.source, target: e.target, label: EDGE_LABELS_ZH[e.type] || "" })),
        });
      })
      .catch(() => {})
      .finally(() => setSigmaLoading(false));
  }, [viewMode, sigmaData.nodes.length]);

  // Card type-specific field renderer
  const renderCardFields = (n: Record<string, unknown>, type: string) => {
    const s = (k: string) => String(n[k] || "");
    const TYPE_ZH: Record<string, string> = { exemption: "免征", rate_reduction: "减征", refund: "退税", deduction: "扣除", deferral: "递延", credit: "抵免", timing: "时间性", permanent: "永久性" };
    switch (type) {
      case "TaxType":
        return [["税率范围", s("rateRange")], ["申报周期", s("filingFrequency").replace("monthly","月报").replace("quarterly","季报").replace("annual","年报")], ["适用法律", s("governingLaw")]];
      case "TaxIncentive":
        return [["优惠类型", TYPE_ZH[s("incentiveType")] || s("incentiveType")], ["适用条件", s("eligibilityCriteria")], ["法律依据", s("lawReference")]];
      case "ComplianceRule":
        return [["规则类型", s("ruleType")], ["内容", s("fullText").slice(0, 80)]];
      case "TaxAccountingGap":
        return [["差异类型", TYPE_ZH[s("gapType")] || s("gapType")], ["会计处理", s("accountingTreatment").slice(0, 60)], ["税务处理", s("taxTreatment").slice(0, 60)]];
      case "SocialInsuranceRule":
        return [["险种", s("insuranceType")], ["单位费率", s("employerRate")], ["个人费率", s("employeeRate")]];
      case "InvoiceRule":
        return [["规则类型", s("ruleType")], ["适用条件", s("condition").slice(0, 60)]];
      case "IndustryBenchmark":
        return [["行业代码", s("industryCode")], ["范围", `${s("minValue")}~${s("maxValue")} ${s("unit")}`]];
      case "TaxRate":
        return [["税率", s("rateValue") || s("rate") || ""], ["适用范围", s("applicableScope") || s("name")]];
      case "Penalty":
        return [["处罚类型", s("penaltyType") || ""], ["说明", s("name")]];
      default:
        return [["类型", type], ["说明", s("fullText").slice(0, 80) || s("title") || s("name")]];
    }
  };

  // Fetch full node detail when a node is selected
  useEffect(() => {
    if (!selectedNode) { setNodeDetail(null); return; }
    setDetailLoading(true);
    getNodeDetail(selectedNode.type, selectedNode.id)
      .then((d) => setNodeDetail(d))
      .catch(() => setNodeDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedNode?.id, selectedNode?.type]);

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
          setSelectedNode({ id, label: result.node._label || id, type: "TaxType", neighbors: result.neighbors });
        }
        setLoading(false);
        return;
      }

      const searchResult = await searchNodes(q, 10);
      const results = searchResult.results || [];
      if (!results.length) { setError(`未找到: ${q}`); setLoading(false); return; }

      // Select the first result and show its detail
      const first = results[0];
      const nodeId = first.id || first.node_id || "";
      const nodeTable = first.table || first.source_table || "";
      const nodeLabel = first.text || first.title || first.name || nodeId;
      if (nodeId) {
        try {
          const gr = await getGraph(nodeTable, nodeId);
          setSelectedNode({ id: nodeId, label: nodeLabel, type: nodeTable, neighbors: gr.neighbors || [] });
        } catch {
          setSelectedNode({ id: nodeId, label: nodeLabel, type: nodeTable, neighbors: [] });
        }
      }
    } catch (e) { setError(e instanceof Error ? e.message : "搜索失败"); }
    setLoading(false);
  }, [searchQuery]);

  // Browse a node type: switch card type or highlight in sigma
  const [sigmaFocusType, setSigmaFocusType] = useState<string | null>(null);

  const handleBrowseType = useCallback(async (nodeType: string) => {
    if (viewMode === "cards") {
      setCardType(nodeType);
      setCardPage(0);
      return;
    }
    // Sigma mode: load type-focused subgraph (toggle: click same type to return to overview)
    if (sigmaFocusType === nodeType) {
      // Return to global constellation
      setSigmaFocusType(null);
      setSigmaLoading(true);
      setSigmaHighlightTypes([]);
      try {
        const c = await getConstellation(500);
        setSigmaData({ nodes: c.nodes, edges: c.edges.map(e => ({ ...e, label: EDGE_LABELS_ZH[e.type] || "" })) });
      } catch { /* keep current */ }
      setSigmaLoading(false);
      return;
    }
    // Load focused subgraph for this type
    setSigmaFocusType(nodeType);
    setSigmaLoading(true);
    setSigmaHighlightTypes([]);
    try {
      const c = await getConstellationByType(nodeType, 300);
      setSigmaData({
        nodes: c.nodes,
        edges: c.edges.map(e => ({ ...e, label: EDGE_LABELS_ZH[e.type] || "" })),
      });
    } catch (e) { setError(e instanceof Error ? e.message : "加载子图失败"); }
    setSigmaLoading(false);
  }, [viewMode, sigmaFocusType]);

  // Select a node and load its neighbors for the detail panel
  const handleNodeSelect = useCallback(async (nodeId: string, nodeType: string) => {
    setLoading(true);
    try {
      const result = await getGraph(nodeType, nodeId);
      const label = result.node?._label || nodeId;
      setSelectedNode({ id: nodeId, label, type: nodeType, neighbors: result.neighbors || [] });
    } catch (e) { setError(e instanceof Error ? e.message : "展开失败"); }
    setLoading(false);
  }, []);

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
        {/* View mode switcher: 星图 / 卡片 */}
        <div style={{ display: "flex", gap: 0, border: `1px solid ${CN.border}`, borderRadius: 4, overflow: "hidden" }}>
          {(["sigma", "cards"] as const).map((m) => (
            <button key={m} onClick={() => setViewMode(m)}
              style={{ padding: "4px 10px", fontSize: 11, fontWeight: 600, border: "none", cursor: "pointer",
                background: viewMode === m ? CN.blue : "transparent", color: viewMode === m ? "#fff" : CN.textSecondary }}>
              {m === "sigma" ? "星图" : "卡片"}
            </button>
          ))}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 16, fontSize: 12, color: CN.textMuted }}>
          {viewMode === "sigma" ? (
            <span>
              {sigmaFocusType ? (
                <>{NODE_ZH[sigmaFocusType]?.zh || sigmaFocusType}: <strong style={{ color: CN.blue }}>{sigmaData.nodes.length}</strong> 节点 / <strong>{sigmaData.edges.length}</strong> 边 <button onClick={() => handleBrowseType(sigmaFocusType)} style={{ background: "none", border: "none", color: CN.blue, cursor: "pointer", fontSize: 11, textDecoration: "underline" }}>返回全局</button></>
              ) : (
                <>星图: <strong style={{ color: CN.blue }}>{sigmaData.nodes.length}</strong> 节点 / <strong>{sigmaData.edges.length}</strong> 边{sigmaHighlightTypes.length > 0 && <span style={{ color: CN.amber }}> -- 过滤中 <button onClick={() => setSigmaHighlightTypes([])} style={{ background: "none", border: "none", color: CN.blue, cursor: "pointer", fontSize: 11, textDecoration: "underline" }}>清除</button></span>}</>
              )}
            </span>
          ) : (
            <span>{NODE_ZH[cardType]?.zh || cardType}: <strong style={{ color: CN.blue }}>{cardNodes.length}</strong> 条</span>
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
                // In sigma mode: highlight all types in this layer
                if (viewMode === "sigma") {
                  const layerTypeNames = layerInfo.nodes;
                  setSigmaHighlightTypes(prev => {
                    const isSame = prev.length === layerTypeNames.length && prev.every(t => layerTypeNames.includes(t));
                    return isSame ? [] : layerTypeNames;
                  });
                }
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

        {/* Center: Sigma / Cards */}
        <div style={{ flex: 1, position: "relative", minWidth: 0, background: viewMode === "sigma" ? "#0F172A" : CN.bg, overflowY: viewMode === "cards" ? "auto" : "hidden" }}>
          {viewMode === "sigma" ? (
            /* ── Sigma Constellation View (Obsidian-style) ── */
            sigmaLoading ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#E5E7EB" }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>构建星图...</div>
                  <div style={{ fontSize: 12, color: "#6B7280" }}>加载 {sigmaData.nodes.length} / ~1300 节点</div>
                </div>
              </div>
            ) : sigmaData.nodes.length > 0 ? (
              <SigmaGraph
                data={sigmaData}
                highlightTypes={sigmaHighlightTypes.length > 0 ? sigmaHighlightTypes : undefined}
                onNodeClick={async (nodeId, nodeType) => {
                  const label = sigmaData.nodes.find(n => n.id === nodeId)?.label || nodeId;
                  setSelectedNode({ id: nodeId, label, type: nodeType, neighbors: [] });
                  // Drill-down: fetch neighbors and merge into constellation
                  try {
                    const gr = await getGraph(nodeType, nodeId);
                    if (!gr.neighbors || gr.neighbors.length === 0) return;
                    const existingIds = new Set(sigmaData.nodes.map(n => n.id));
                    const newNodes = [...sigmaData.nodes];
                    const newEdges = [...sigmaData.edges];
                    let added = 0;
                    for (const nb of gr.neighbors.slice(0, 20)) {
                      if (!nb.target_id || existingIds.has(nb.target_id)) {
                        // Edge to existing node — just add the edge
                        if (nb.target_id && existingIds.has(nb.target_id)) {
                          const src = nb.direction === "outgoing" ? nodeId : nb.target_id;
                          const tgt = nb.direction === "outgoing" ? nb.target_id : nodeId;
                          if (!newEdges.some(e => e.source === src && e.target === tgt)) {
                            newEdges.push({ source: src, target: tgt, label: nb.edge_type });
                          }
                        }
                        continue;
                      }
                      existingIds.add(nb.target_id);
                      newNodes.push({
                        id: nb.target_id,
                        label: (nb.target_label || nb.target_id).slice(0, 30),
                        type: nb.target_type,
                        size: 4,
                      });
                      const src = nb.direction === "outgoing" ? nodeId : nb.target_id;
                      const tgt = nb.direction === "outgoing" ? nb.target_id : nodeId;
                      newEdges.push({ source: src, target: tgt, label: nb.edge_type });
                      added++;
                    }
                    if (added > 0 || newEdges.length > sigmaData.edges.length) {
                      setSigmaData({ nodes: newNodes, edges: newEdges });
                    }
                  } catch { /* silent — detail panel still works */ }
                }}
              />
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#6B7280" }}>
                星图数据加载失败，请切换到卡片视图
              </div>
            )
          ) : (
            /* ── Knowledge Cards View ── */
            <div style={{ padding: 20 }}>
              {/* Type selector pills */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
                {Object.entries(LAYER_GROUPS).map(([layerName, layerInfo]) =>
                  layerInfo.nodes.filter(t => (stats?.nodes_by_type?.[t] || 0) > 0).map(type => (
                    <button key={type} onClick={() => { setCardType(type); setCardPage(0); }}
                      style={{
                        padding: "4px 10px", fontSize: 11, fontWeight: 600, borderRadius: 12, cursor: "pointer",
                        border: cardType === type ? `2px solid ${NODE_COLORS[type]}` : `1px solid ${CN.border}`,
                        background: cardType === type ? NODE_COLORS[type] + "18" : "transparent",
                        color: cardType === type ? NODE_COLORS[type] : CN.textSecondary,
                      }}>
                      {NODE_ZH[type]?.zh || type} <span style={{ opacity: 0.6 }}>{stats?.nodes_by_type?.[type] || 0}</span>
                    </button>
                  ))
                )}
              </div>

              {/* Card Graph: cards connected by edges, zoomable canvas */}
              {cardLoading ? (
                <div style={{ textAlign: "center", padding: 40, color: CN.textMuted }}>加载中...</div>
              ) : cardGraphNodes.length > 0 ? (
                <div style={{ height: "calc(100vh - 180px)", border: `1px solid ${CN.border}`, borderRadius: 6, overflow: "hidden" }}>
                  <KnowledgeCardGraph
                    nodes={cardGraphNodes}
                    edges={cardGraphEdges}
                    onNodeSelect={(nodeId, nodeType) => {
                      const name = cardGraphNodes.find(n => n.id === nodeId)?.label || nodeId;
                      setSelectedNode({ id: nodeId, label: name, type: nodeType, neighbors: [] });
                    }}
                  />
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: 40, color: CN.textMuted }}>暂无数据</div>
              )}

              {/* Pagination */}
              {cardNodes.length >= CARD_PAGE_SIZE && (
                <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 12 }}>
                  <button disabled={cardPage === 0} onClick={() => setCardPage(p => p - 1)}
                    style={{ ...cnBtn, padding: "4px 12px", opacity: cardPage === 0 ? 0.3 : 1 }}>&lt; 上一页</button>
                  <span style={{ fontSize: 12, color: CN.textMuted, padding: "4px 8px" }}>第 {cardPage + 1} 页</span>
                  <button onClick={() => setCardPage(p => p + 1)}
                    style={{ ...cnBtn, padding: "4px 12px" }}>下一页 &gt;</button>
                </div>
              )}
            </div>
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
                {/* Title / Name (only if different from panel header) */}
                {(nodeDetail.title || nodeDetail.name) && (nodeDetail.title || nodeDetail.name) !== selectedNode.label && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: CN.textMuted, letterSpacing: "1px", marginBottom: 4 }}>标题</div>
                    <div style={{ fontSize: 13, color: CN.text, lineHeight: 1.6 }}>
                      {nodeDetail.title || nodeDetail.name}
                    </div>
                  </div>
                )}

                {/* Full Text / Content / Description */}
                {(nodeDetail.fullText || nodeDetail.content || nodeDetail.description) && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: CN.textMuted, letterSpacing: "1px", marginBottom: 4 }}>
                      {nodeDetail.fullText ? "全文内容" : nodeDetail.content ? "内容" : "描述"}
                    </div>
                    <div style={{
                      fontSize: 12, color: CN.textSecondary, lineHeight: 1.8,
                      padding: "10px 12px", background: CN.bg, border: `1px solid ${CN.border}`,
                      borderRadius: 4, whiteSpace: "pre-wrap",
                    }}>
                      {nodeDetail.fullText || nodeDetail.content || nodeDetail.description}
                    </div>
                  </div>
                )}

                {/* Unified properties — Chinese field names, hide internal metadata */}
                {(() => {
                  // Internal/display fields to always hide
                  const HIDE = new Set(["_id", "_label", "_display_label", "id", "title", "name",
                    "fullText", "content", "description", "createdAt"]);
                  // v4.1 ontology field → Chinese label mapping
                  const FIELD_ZH: Record<string, string> = {
                    // Shared
                    regulationNumber: "文号", effectiveDate: "生效日期", hierarchyLevel: "层级",
                    regulationType: "法规类型", status: "状态", sourceUrl: "来源",
                    // TaxType
                    rateRange: "税率范围", filingFrequency: "申报周期", taxCategory: "税种分类",
                    // TaxRate
                    taxTypeId: "适用税种", valueExpression: "税率", calculationBasis: "计税基础",
                    rateType: "税率类型", applicableCondition: "适用条件",
                    // TaxIncentive
                    incentiveType: "优惠类型", value: "优惠值", valueBasis: "优惠基础",
                    beneficiaryType: "受益人类型", eligibilityCriteria: "适用条件",
                    combinable: "可叠加", maxAnnualBenefit: "年最大收益", lawReference: "法律依据",
                    // ComplianceRule
                    ruleCode: "规则编号", category: "分类", conditionDescription: "条件描述",
                    conditionFormula: "条件公式", consequence: "后果", severity: "严重程度",
                    // TaxAccountingGap
                    accountingTreatment: "会计处理", taxTreatment: "税务处理",
                    gapType: "差异类型", adjustmentDirection: "调整方向",
                    // SocialInsuranceRule
                    insuranceType: "险种", employerRate: "单位费率", employeeRate: "个人费率",
                    baseFloor: "缴费基数下限", baseCeiling: "缴费基数上限", regionId: "适用地区",
                    // InvoiceRule
                    invoiceType: "发票类型", condition: "适用条件", procedure: "操作流程",
                    ruleType: "规则类型",
                    // IndustryBenchmark
                    industryCode: "行业代码", ratioName: "指标名称",
                    minValue: "下限", maxValue: "上限", unit: "单位",
                    // AuditTrigger
                    triggerCode: "触发编号", patternDescription: "模式描述",
                    detectionMethod: "检测方法", historicalFrequency: "历史频率",
                    // Penalty
                    penaltyCode: "处罚编号", penaltyType: "处罚类型",
                    calculationMethod: "计算方式", dailyRate: "日利率",
                    minAmount: "最低金额", maxAmount: "最高金额",
                    // RiskIndicator
                    indicatorCode: "指标编号", metricName: "指标名称",
                    metricFormula: "计算公式", thresholdLow: "低阈值", thresholdHigh: "高阈值",
                    // Entity/Region/Filing
                    formNumber: "表单编号", applicableTaxpayerType: "适用纳税人",
                    fields: "字段", shortName: "简称",
                    // LegalDocument
                    level: "层级", issuingBodyId: "发布机构", issueDate: "发布日期",
                    type: "类型", abolishDate: "废止日期",
                    // LegalClause / KnowledgeUnit
                    topic: "主题", question: "问题", answer: "回答",
                    // v4.2 — JournalEntryTemplate
                    chineseName: "中文名", businessActivity: "触发业务",
                    debitAccounts: "借方科目", creditAccounts: "贷方科目",
                    frequency: "频率", example: "示例",
                    // v4.2 — FinancialStatementItem
                    statementType: "报表类型", itemCode: "行次编号", parentItem: "上级项目",
                    calculationFormula: "计算公式", direction: "方向", isSubtotal: "是否小计",
                    reportingStandard: "准则",
                    // v4.2 — TaxCalculationRule
                    formula: "公式", formulaSteps: "计算步骤", inputFields: "输入字段",
                    outputField: "输出字段", applicableScenario: "适用场景",
                    exampleCalculation: "计算示例",
                    // v4.2 — FilingFormField
                    formId: "表单ID", fieldNumber: "栏次号", fieldType: "字段类型",
                    dataSource: "数据来源", derivesFrom: "来源于", validationRule: "校验规则",
                    isMandatory: "是否必填",
                    // v4.2 — FinancialIndicator
                    indicatorType: "指标类型", decomposesInto: "分解为",
                    normalRange: "正常范围", warningThreshold: "预警阈值",
                    benchmarkIndustry: "基准行业",
                    // v4.2 — TaxTreaty
                    treatyPartner: "缔约方", signDate: "签署日期",
                    dividendRate: "股息预提税率", interestRate: "利息预提税率",
                    royaltyRate: "特许权使用费率", capitalGainsRule: "资本利得规则",
                    permanentEstablishmentDays: "常设机构天数",
                    tieBreaker: "居民判定规则", beneficialOwnerTest: "受益所有人测试",
                    // v4.2 — AccountingStandard
                    casNumber: "准则编号", ifrsEquivalent: "IFRS对应",
                    scope: "适用范围", differenceFromIfrs: "与IFRS差异",
                    // AccountingSubject hierarchy
                    parentCode: "上级科目", balanceDirection: "余额方向",
                    isLeaf: "是否末级", monetaryType: "货币类型", standardSource: "准则来源",
                    // TaxIncentive stacking
                    stackingGroup: "叠加分组", effectiveFrom: "生效起", effectiveUntil: "生效止",
                    expiryDate: "到期日",
                    // v4.2 P1 — TaxItem (parentItem already defined in P0)
                    taxBasis: "计税依据", exemptions: "免税情形",
                    // v4.2 P1 — TaxBasis
                    basisType: "计税方式", applicableTaxType: "适用税种",
                    adjustmentRules: "调整规则",
                    // v4.2 P1 — TaxLiabilityTrigger
                    triggerEvent: "触发事件", triggerCondition: "触发条件",
                    liabilityDate: "纳税义务日期", documentBasis: "文件依据",
                    // v4.2 P1 — DeductionRule (ruleType already defined)
                    deductionType: "扣除类型", limitAmount: "限额金额",
                    carryForward: "结转规则", documentRequirement: "凭证要求", applicableEntity: "适用主体",
                    // v4.2 P1 — TaxMilestoneEvent
                    eventType: "事件类型", lifecycle: "生命周期阶段",
                    taxImplications: "税务影响", requiredActions: "必须动作",
                    deadline: "截止日", penalties: "逾期处罚",
                    // v4.2 P1 — RiskIndicator (rebuilt)
                    module: "监控模块", warningRule: "预警规则",
                    monitoringFrequency: "监控频率", falsePositiveRate: "误报率",
                    recommendedAction: "建议措施", confidence: "置信度",
                    // v4.2 P1 — AuditTrigger (rebuilt)
                    auditType: "审计类型", typicalOutcome: "典型结果",
                    preventionMeasure: "预防措施", lookbackPeriodMonths: "追溯月数",
                    // v4.2 P2 — ResponseStrategy
                    strategyType: "策略类型", targetRisk: "目标风险",
                    actionSteps: "操作步骤", estimatedCost: "预估成本",
                    timeframe: "时间周期", effectivenessScore: "有效性评分",
                    // v4.2 P2 — PolicyChange
                    changeType: "变更类型", previousPolicy: "旧政策", newPolicy: "新政策",
                    impactScope: "影响范围", impactedTaxTypes: "影响税种", transitionRule: "过渡规则",
                  };

                  const props = Object.entries(nodeDetail)
                    .filter(([k, v]) => !HIDE.has(k) && v != null && v !== "" && String(v) !== "null" && String(v) !== "undefined"
                      && !(typeof v === "object" && "offset" in (v as Record<string,unknown>)))  // Hide KuzuDB _id-like objects
                    .map(([k, v]) => [FIELD_ZH[k] || k, String(v)] as [string, string]);
                  if (props.length === 0) return null;
                  return (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 10, color: CN.textMuted, letterSpacing: "1px", marginBottom: 6 }}>属性</div>
                      <div style={{ fontSize: 12, lineHeight: 1.7 }}>
                        {props.map(([label, val]) => (
                          <div key={label} style={{ display: "flex", gap: 8, padding: "3px 0", borderBottom: `1px solid ${CN.bgElevated}` }}>
                            <span style={{ color: CN.textMuted, minWidth: 80, flexShrink: 0, fontSize: 11, fontWeight: 600 }}>{label}</span>
                            {val.startsWith("http") ? (
                              <a href={val} target="_blank" rel="noopener noreferrer"
                                style={{ color: CN.blue, textDecoration: "none", wordBreak: "break-all" }}>
                                {val.slice(0, 80)}
                              </a>
                            ) : (
                              <span style={{ color: CN.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{val}</span>
                            )}
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
                  onClick={() => handleNodeSelect(nb.target_id, nb.target_type)}
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
              onClick={() => handleNodeSelect(selectedNode.id, selectedNode.type)}
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
