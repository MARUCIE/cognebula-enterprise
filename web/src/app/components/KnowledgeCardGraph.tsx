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

/* ── Knowledge Card Node Component ── */
function KnowledgeCardNode({ data }: NodeProps) {
  const nodeData = data as { label: string; nodeType: string; raw: Record<string, unknown>; onSelect?: (id: string) => void };
  const color = NODE_COLORS[nodeData.nodeType] || "#94A3B8";
  const layer = getNodeLayer(nodeData.nodeType);
  const fields = getCardFields(nodeData.raw || {}, nodeData.nodeType);

  return (
    <div
      onClick={() => nodeData.onSelect?.(String(nodeData.raw?.id || ""))}
      style={{
        background: CN.bgCard,
        border: `1px solid ${CN.border}`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 6,
        padding: "10px 12px",
        minWidth: 180,
        maxWidth: 260,
        cursor: "pointer",
        fontSize: 12,
        transition: "box-shadow 0.15s",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color, width: 6, height: 6 }} />
      <Handle type="source" position={Position.Right} style={{ background: color, width: 6, height: 6 }} />

      {/* Header: type badge + title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6, marginBottom: 6 }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: CN.text, lineHeight: 1.3 }}>
          {String(nodeData.label).slice(0, 25)}
        </div>
        <span style={{
          fontSize: 9, fontWeight: 600, color, background: color + "18",
          padding: "1px 5px", borderRadius: 3, flexShrink: 0, whiteSpace: "nowrap",
        }}>
          {layer.slice(0, 5)}
        </span>
      </div>

      {/* Fields */}
      {fields.map(([label, value]) => value ? (
        <div key={label} style={{ display: "flex", gap: 6, lineHeight: 1.5, color: CN.textSecondary }}>
          <span style={{ color: CN.textMuted, minWidth: 28, flexShrink: 0 }}>{label}</span>
          <span style={{ color: CN.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</span>
        </div>
      ) : null)}
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

/* ── Layout: simple horizontal layers ── */
function layoutNodes(nodes: CardGraphNode[]): Node[] {
  // Group by layer, then spread vertically
  const layers: Record<string, CardGraphNode[]> = {};
  for (const n of nodes) {
    const layer = getNodeLayer(n.type);
    (layers[layer] ||= []).push(n);
  }

  const layerOrder = ["L4 知识层", "L3 合规层", "L2 业务层", "L1 法规层"];
  const result: Node[] = [];
  let xOffset = 0;

  for (const layerName of layerOrder) {
    const group = layers[layerName];
    if (!group?.length) continue;

    for (let i = 0; i < group.length; i++) {
      const n = group[i];
      result.push({
        id: n.id,
        type: "knowledgeCard",
        position: { x: xOffset, y: i * 100 },
        data: { label: n.label, nodeType: n.type, raw: n.raw },
      });
    }
    xOffset += 300;
  }
  return result;
}

function layoutEdges(edges: CardGraphEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `e-${i}-${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    label: e.label,
    type: "default",
    animated: false,
    style: { stroke: CN.textMuted, strokeWidth: 1.5 },
    labelStyle: { fontSize: 10, fill: CN.textMuted },
    markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color: CN.textMuted },
  }));
}

/* ── Main Component ── */
export default function KnowledgeCardGraph({ nodes: inputNodes, edges: inputEdges, onNodeSelect }: Props) {
  const initialNodes = useMemo(() => {
    const laid = layoutNodes(inputNodes);
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
