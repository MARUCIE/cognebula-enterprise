"use client";

import React, { useEffect, useState } from "react";
import { getReasoningChain, EDGE_LABELS_ZH, EDGE_COLORS, type ReasoningChain, type ReasoningEdge } from "../lib/kg-api";
import { CN, cnBadge } from "../lib/cognebula-theme";

export interface ReasoningChainPanelProps {
  nodeId: string;
  onNavigate?: (targetId: string, targetType: string | null) => void;
}

/* Compact, on-demand reasoning-chain viewer. Mounts when a node is selected,
   loads /api/v1/reasoning-chain, renders grouped direct evidence (with v4.2
   provenance: effective_at / superseded_at / source_clause_id) and an
   optional 2-hop ripple. Uses the same theme tokens as the parent KG page. */
export default function ReasoningChainPanel({ nodeId, onNavigate }: ReasoningChainPanelProps) {
  const [chain, setChain] = useState<ReasoningChain | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [include2Hop, setInclude2Hop] = useState(false);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    setError(null);
    getReasoningChain(nodeId, include2Hop)
      .then((c) => { if (!cancel) setChain(c); })
      .catch((e: Error) => { if (!cancel) setError(e.message); })
      .finally(() => { if (!cancel) setLoading(false); });
    return () => { cancel = true; };
  }, [nodeId, include2Hop]);

  if (loading) {
    return <div style={{ padding: "8px 0", color: CN.textMuted, fontSize: 12 }}>加载溯源链...</div>;
  }
  if (error) {
    return <div style={{ padding: "8px 0", color: CN.textMuted, fontSize: 12 }}>溯源链加载失败：{error}</div>;
  }
  if (!chain || !chain.trace.node_resolved) {
    return <div style={{ padding: "8px 0", color: CN.textMuted, fontSize: 12 }}>图谱中未找到该节点</div>;
  }

  return (
    <div style={{ borderTop: `1px solid ${CN.border}`, paddingTop: 12, marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>
          溯源链 · 直接证据 ({chain.direct_evidence.length})
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: CN.textMuted, cursor: "pointer" }}>
          <input type="checkbox" checked={include2Hop} onChange={(e) => setInclude2Hop(e.target.checked)}
            style={{ cursor: "pointer" }} />
          含 2-hop 扩散
        </label>
      </div>

      {chain.direct_evidence.length === 0 && (
        <div style={{ fontSize: 11, color: CN.textMuted, padding: "4px 0" }}>该节点没有直接边证据</div>
      )}

      {chain.direct_evidence.map((e, i) => (
        <EdgeRow key={`d${i}`} edge={e} onNavigate={onNavigate} />
      ))}

      {include2Hop && chain.related_2hop.length > 0 && (
        <>
          <div style={{
            fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px",
            marginTop: 12, marginBottom: 8,
          }}>
            2-hop 扩散 ({chain.related_2hop.length})
          </div>
          {chain.related_2hop.map((e, i) => (
            <EdgeRow key={`r${i}`} edge={e} hop={2} onNavigate={onNavigate} />
          ))}
        </>
      )}

      <div style={{ marginTop: 8, fontSize: 10, color: CN.textMuted, fontFamily: "monospace" }}>
        扫描 {chain.trace.rel_types_scanned} REL · {chain.trace.queries_run} 次查询
      </div>
    </div>
  );
}

function EdgeRow({
  edge, hop = 1, onNavigate,
}: { edge: ReasoningEdge; hop?: 1 | 2; onNavigate?: (id: string, type: string | null) => void }) {
  const arrow = edge.direction === "in" ? "\u2190" : "\u2192";
  const zhEdge = EDGE_LABELS_ZH[edge.edge_type] || edge.edge_type;
  const color = EDGE_COLORS[edge.edge_type] || CN.textMuted;
  const hasProvenance = edge.source_clause_id || edge.effective_at || edge.superseded_at;

  return (
    <div style={{
      padding: "6px 0", borderBottom: `1px solid ${CN.bgElevated}`, fontSize: 12,
      opacity: hop === 2 ? 0.85 : 1,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
        <span
          onClick={() => edge.target.id && onNavigate?.(edge.target.id, edge.target.type)}
          style={{
            color: CN.text, cursor: onNavigate ? "pointer" : "default",
            maxWidth: 190, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}
          title={edge.target.label || edge.target.id}
        >
          {arrow} {edge.target.label || edge.target.id}
        </span>
        <span style={cnBadge(color, CN.bgElevated)}>{zhEdge}</span>
      </div>
      {edge.via && (
        <div style={{ fontSize: 10, color: CN.textMuted, marginTop: 2, paddingLeft: 14 }}>
          经由 {edge.via.id} ({edge.via.edge})
        </div>
      )}
      {hasProvenance && (
        <div style={{
          fontSize: 10, color: CN.textMuted, marginTop: 4, paddingLeft: 14,
          display: "flex", flexWrap: "wrap", gap: "2px 10px",
        }}>
          {edge.source_clause_id && <span>条款：{edge.source_clause_id}</span>}
          {edge.effective_at && <span>生效：{edge.effective_at}</span>}
          {edge.superseded_at && <span>废止：{edge.superseded_at}</span>}
        </div>
      )}
    </div>
  );
}
