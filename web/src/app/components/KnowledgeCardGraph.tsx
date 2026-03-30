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

/* ── Knowledge Card Node Component (compact ↔ expanded) ── */
function KnowledgeCardNode({ data }: NodeProps) {
  const [expanded, setExpanded] = React.useState(false);
  const nodeData = data as { label: string; nodeType: string; raw: Record<string, unknown>; onSelect?: (id: string) => void };
  const color = NODE_COLORS[nodeData.nodeType] || "#94A3B8";
  const layer = getNodeLayer(nodeData.nodeType);
  const fields = getCardFields(nodeData.raw || {}, nodeData.nodeType);
  const ft = String(nodeData.raw?.fullText || nodeData.raw?.content || nodeData.raw?.description || "");
  const NODE_ZH_INLINE: Record<string, string> = {
    TaxType: "税种", TaxIncentive: "税收优惠", ComplianceRule: "合规规则", TaxRate: "税率",
    TaxAccountingGap: "税会差异", SocialInsuranceRule: "社保", InvoiceRule: "发票",
    IndustryBenchmark: "基准", AuditTrigger: "审计", RiskIndicator: "风险", Penalty: "处罚",
    LegalDocument: "法规", LegalClause: "条款", IssuingBody: "机构", KnowledgeUnit: "知识",
    AccountingSubject: "科目", Classification: "分类", TaxEntity: "主体", Region: "地区",
    FilingForm: "申报", BusinessActivity: "业务",
  };

  return (
    <div
      onClick={(e) => {
        if (e.detail === 2) {
          // Double click → open detail panel
          nodeData.onSelect?.(String(nodeData.raw?.id || ""));
        } else {
          // Single click → toggle expand
          setExpanded(!expanded);
        }
      }}
      style={{
        background: CN.bgCard,
        border: `1px solid ${expanded ? color : CN.border}`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 6,
        padding: expanded ? "12px 14px" : "6px 10px",
        width: expanded ? 300 : 180,
        cursor: "pointer",
        fontSize: 12,
        transition: "all 0.2s ease",
        boxShadow: expanded ? `0 4px 16px ${color}22` : "none",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color, width: 6, height: 6 }} />
      <Handle type="source" position={Position.Right} style={{ background: color, width: 6, height: 6 }} />

      {/* Header: always visible */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6 }}>
        <div style={{ fontWeight: 700, fontSize: expanded ? 14 : 12, color: CN.text, lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: expanded ? "normal" : "nowrap" }}>
          {String(nodeData.label).slice(0, expanded ? 60 : 20)}
        </div>
        <span style={{
          fontSize: 9, fontWeight: 600, color, background: color + "18",
          padding: "1px 5px", borderRadius: 3, flexShrink: 0, whiteSpace: "nowrap",
        }}>
          {NODE_ZH_INLINE[nodeData.nodeType] || layer.slice(0, 5)}
        </span>
      </div>

      {/* Expanded: show all fields + fullText */}
      {expanded && (
        <div style={{ marginTop: 8, borderTop: `1px solid ${CN.border}`, paddingTop: 6 }}>
          {fields.map(([label, value]) => value ? (
            <div key={label} style={{ display: "flex", gap: 6, lineHeight: 1.6, color: CN.textSecondary }}>
              <span style={{ color: CN.textMuted, minWidth: 32, flexShrink: 0, fontSize: 11 }}>{label}</span>
              <span style={{ color: CN.text }}>{value}</span>
            </div>
          ) : null)}
          {ft && ft.length > 5 && (
            <div style={{ marginTop: 6, fontSize: 11, color: CN.textMuted, lineHeight: 1.5, borderTop: `1px solid ${CN.bgElevated}`, paddingTop: 6, maxHeight: 120, overflowY: "auto" }}>
              {ft.slice(0, 300)}{ft.length > 300 ? "..." : ""}
            </div>
          )}
          <div style={{ marginTop: 4, fontSize: 9, color: CN.textMuted, textAlign: "right" }}>双击查看完整详情</div>
        </div>
      )}
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
  g.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 200, marginx: 30, marginy: 30 });

  const CARD_W = 220;
  const CARD_H = 90;

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
    style: { stroke: CN.textMuted, strokeWidth: 1.2 },
    labelStyle: { fontSize: 9, fill: CN.textMuted },
    labelBgStyle: { fill: CN.bg, fillOpacity: 0.8 },
    labelBgPadding: [4, 2] as [number, number],
    labelBgBorderRadius: 3,
    markerEnd: { type: MarkerType.ArrowClosed, width: 10, height: 10, color: CN.textMuted },
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
