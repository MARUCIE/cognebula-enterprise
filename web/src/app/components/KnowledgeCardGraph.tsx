"use client";

import React, { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { NODE_COLORS, EDGE_LABELS_ZH, getNodeLayer } from "../lib/kg-api";
import { CN } from "../lib/cognebula-theme";

/* ── Type-specific field renderers ── */
const TYPE_ZH: Record<string, string> = {
  exemption: "免征", rate_reduction: "减征", refund: "退税", deduction: "扣除",
  timing: "时间性", permanent: "永久性", certification: "认证", deferral: "递延",
};

function getCardFields(data: Record<string, unknown>, type: string): [string, string][] {
  const s = (k: string) => String(data[k] || "").slice(0, 60);
  switch (type) {
    case "TaxType":
      return [["税率", s("rateRange")], ["周期", s("filingFrequency").replace("monthly", "月报").replace("quarterly", "季报")]];
    case "TaxIncentive":
      return [["类型", TYPE_ZH[s("incentiveType")] || s("incentiveType")], ["依据", s("lawReference")]];
    case "ComplianceRule":
      return [["规则", s("ruleType")], ["内容", s("fullText")]];
    case "TaxAccountingGap":
      return [["差异", TYPE_ZH[s("gapType")] || s("gapType")], ["会计", s("accountingTreatment")]];
    case "SocialInsuranceRule":
      return [["单位", s("employerRate")], ["个人", s("employeeRate")]];
    case "InvoiceRule":
      return [["类型", s("ruleType")], ["条件", s("condition")]];
    default:
      return [["说明", s("fullText") || s("description") || s("name")]];
  }
}

/* ── Knowledge Card Node Component — Heptabase-style rich card ── */
const NODE_ZH_INLINE: Record<string, string> = {
  TaxType: "税种", TaxIncentive: "税收优惠", ComplianceRule: "合规规则", TaxRate: "税率",
  TaxAccountingGap: "税会差异", SocialInsuranceRule: "社保", InvoiceRule: "发票",
  IndustryBenchmark: "基准", AuditTrigger: "审计", RiskIndicator: "风险", Penalty: "处罚",
  LegalDocument: "法规", LegalClause: "条款", IssuingBody: "机构", KnowledgeUnit: "知识",
  AccountingSubject: "科目", Classification: "分类", TaxEntity: "主体", Region: "地区",
  FilingForm: "申报", BusinessActivity: "业务",
};

// Convert a node-type accent color into a very-light tinted card background
// by appending an alpha hex. Input is "#RRGGBB" → returns "#RRGGBB0C" (≈5% tint).
function tintBackground(hex: string): string {
  return hex.length === 7 ? `${hex}0C` : CN.bgCard;
}

function KnowledgeCardNode({ data }: NodeProps) {
  const [hover, setHover] = React.useState(false);
  const nodeData = data as { label: string; nodeType: string; raw: Record<string, unknown>; onSelect?: (id: string) => void };
  const color = NODE_COLORS[nodeData.nodeType] || "#94A3B8";
  const layer = getNodeLayer(nodeData.nodeType);
  const fields = getCardFields(nodeData.raw || {}, nodeData.nodeType).filter(([, v]) => v);
  const ft = String(nodeData.raw?.fullText || nodeData.raw?.content || nodeData.raw?.description || "");
  const typeZh = NODE_ZH_INLINE[nodeData.nodeType] || layer.slice(0, 5);

  const openDetail = () => nodeData.onSelect?.(String(nodeData.raw?.id || ""));

  return (
    <div
      onClick={(e) => { if (e.detail === 2) openDetail(); }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: tintBackground(color),
        border: `1px solid ${hover ? color : CN.border}`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 8,
        padding: "12px 14px 10px",
        width: 280,
        minHeight: 110,
        cursor: "pointer",
        fontSize: 12,
        transition: "box-shadow 140ms ease, transform 140ms ease, border-color 140ms ease",
        boxShadow: hover
          ? `0 8px 22px ${color}26, 0 1px 3px rgba(15,23,42,0.06)`
          : `0 1px 3px rgba(15,23,42,0.06)`,
        transform: hover ? "translateY(-1px)" : "none",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
      title="双击查看完整详情"
    >
      <Handle type="target" position={Position.Left} style={{ background: color, width: 8, height: 8, border: "none" }} />
      <Handle type="source" position={Position.Right} style={{ background: color, width: 8, height: 8, border: "none" }} />

      {/* Top bar: type badge (like Heptabase's NOTE pill, aligned right) */}
      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
        <span style={{
          fontSize: 9,
          fontWeight: 700,
          color,
          background: CN.bg,
          border: `1px solid ${color}40`,
          padding: "2px 8px",
          borderRadius: 10,
          letterSpacing: "0.8px",
          textTransform: "uppercase",
        }}>
          {typeZh}
        </span>
      </div>

      {/* Title — always visible, up to two lines */}
      <div style={{
        fontWeight: 700,
        fontSize: 14,
        color: CN.text,
        lineHeight: 1.35,
        display: "-webkit-box",
        WebkitBoxOrient: "vertical",
        WebkitLineClamp: 2,
        overflow: "hidden",
      }}>
        {String(nodeData.label)}
      </div>

      {/* Key fields — always visible, up to 2 rows */}
      {fields.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {fields.slice(0, 2).map(([label, value]) => (
            <div key={label} style={{ display: "flex", gap: 8, fontSize: 11.5, lineHeight: 1.5 }}>
              <span style={{ color: CN.textMuted, minWidth: 36, flexShrink: 0 }}>{label}</span>
              <span style={{ color: CN.textSecondary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Full-text preview snippet — shown if the card has body text */}
      {ft && ft.length > 8 && (
        <div style={{
          fontSize: 11,
          color: CN.textMuted,
          lineHeight: 1.55,
          display: "-webkit-box",
          WebkitBoxOrient: "vertical",
          WebkitLineClamp: 2,
          overflow: "hidden",
          borderTop: `1px dashed ${CN.border}`,
          paddingTop: 6,
        }}>
          {ft.slice(0, 160)}
        </div>
      )}

      {/* Footer hint — always visible so users know double-click opens detail */}
      <div style={{
        marginTop: "auto",
        fontSize: 10,
        color: hover ? color : CN.textMuted,
        textAlign: "right",
        fontWeight: 500,
        letterSpacing: "0.3px",
        transition: "color 140ms ease",
      }}>
        双击查看完整详情 →
      </div>
    </div>
  );
}

const nodeTypes = { knowledgeCard: KnowledgeCardNode };

/* ── Props ── */
export interface CardGraphNode {
  id: string;
  label: string;
  type: string;
  raw: Record<string, unknown>;
}

export interface CardGraphEdge {
  source: string;
  target: string;
  label: string;
  edgeType: string;
}

interface Props {
  nodes: CardGraphNode[];
  edges: CardGraphEdge[];
  onNodeSelect?: (nodeId: string, nodeType: string) => void;
}

/* ── Layout: dagre auto-layout (hierarchical DAG) ── */
function layoutNodes(nodes: CardGraphNode[], edges: CardGraphEdge[]): Node[] {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Dagre = require("@dagrejs/dagre");
  const g = new Dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 36, ranksep: 160, marginx: 24, marginy: 24 });

  const CARD_W = 280;
  const CARD_H = 130;

  for (const n of nodes) {
    g.setNode(n.id, { width: CARD_W, height: CARD_H });
  }
  for (const e of edges) {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target);
    }
  }

  Dagre.layout(g);

  return nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      id: n.id,
      type: "knowledgeCard",
      position: { x: (pos?.x || 0) - CARD_W / 2, y: (pos?.y || 0) - CARD_H / 2 },
      data: { label: n.label, nodeType: n.type, raw: n.raw },
    };
  });
}

function layoutEdges(edges: CardGraphEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `e-${i}-${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    label: e.label,
    type: "smoothstep",
    animated: false,
    // Dashed connector, Heptabase-reference style
    style: { stroke: "#94A3B8", strokeWidth: 1.5, strokeDasharray: "4 4" },
    labelStyle: { fontSize: 11, fill: "#475569", fontWeight: 600 },
    labelBgStyle: { fill: "#F8FAFC", fillOpacity: 0.95, stroke: "#CBD5E1", strokeWidth: 0.5 },
    labelBgPadding: [6, 4] as [number, number],
    labelBgBorderRadius: 6,
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "#94A3B8" },
  }));
}

/* ── Main Component ── */
export default function KnowledgeCardGraph({ nodes: inputNodes, edges: inputEdges, onNodeSelect }: Props) {
  const initialNodes = useMemo(() => {
    const laid = layoutNodes(inputNodes, inputEdges);
    return laid.map(n => ({
      ...n,
      data: { ...n.data, onSelect: (id: string) => {
        const found = inputNodes.find(nn => nn.id === id);
        if (found && onNodeSelect) onNodeSelect(id, found.type);
      }},
    }));
  }, [inputNodes, onNodeSelect]);

  const initialEdges = useMemo(() => layoutEdges(inputEdges), [inputEdges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={3}
        proOptions={{ hideAttribution: true }}
      >
        <Background color={CN.border} gap={40} />
        <Controls position="bottom-right" />
        <MiniMap
          nodeColor={(n) => NODE_COLORS[n.data?.nodeType as string] || "#94A3B8"}
          style={{ background: CN.bgCard, border: `1px solid ${CN.border}` }}
        />
      </ReactFlow>
    </div>
  );
}
