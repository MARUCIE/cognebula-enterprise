"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  chatRAG, getGraph, searchNodes,
  NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS, LAYER_GROUPS, getNodeLayer,
  type ChatResponse, type ChatSource, type KGNeighbor,
} from "../../lib/kg-api";
import type { GraphData, SelectedNode, CytoscapeGraphHandle } from "../../components/CytoscapeGraph";
import { CN, cnCard, cnInput, cnBtnPrimary, cnBadge } from "../../lib/cognebula-theme";

const CytoscapeGraph = dynamic(() => import("../../components/CytoscapeGraph"), { ssr: false });

interface QAEntry {
  id: string;
  question: string;
  answer: string;
  sources: ChatSource[];
  html?: string;
  graphData: GraphData;
  timestamp: string;
}

/* Format RAG fallback answer: tags → badges, --- → dividers, indent → blocks */
function formatRAGAnswer(text: string): React.ReactNode {
  if (!text) return null;
  const lines = text.split("\n");
  return lines.map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={i} style={{ height: 8 }} />;
    // Section header: "--- 税种数据 ---"
    if (trimmed.startsWith("---") && trimmed.endsWith("---")) {
      const title = trimmed.replace(/^-+\s*/, "").replace(/\s*-+$/, "");
      return (
        <div key={i} style={{ margin: "12px 0 6px", padding: "6px 0", borderTop: `1px solid ${CN.border}`, fontSize: 12, fontWeight: 700, color: CN.blue, letterSpacing: "0.5px" }}>
          {title}
        </div>
      );
    }
    // Tag line: "[税率] 小规模纳税人..." or "[社保规则] ..."
    const tagMatch = trimmed.match(/^\[([^\]]+)\]\s*(.*)/);
    if (tagMatch) {
      return (
        <div key={i} style={{ display: "flex", gap: 8, alignItems: "baseline", padding: "3px 0" }}>
          <span style={{ fontSize: 10, fontWeight: 600, color: CN.blue, background: CN.blueBg, padding: "2px 6px", borderRadius: 3, flexShrink: 0 }}>{tagMatch[1]}</span>
          <span>{tagMatch[2]}</span>
        </div>
      );
    }
    // Indented structured data: "  增值税 (0.0, 13.0, 分级税率, 月报)"
    if (line.startsWith("  ") && trimmed.includes("(")) {
      const parts = trimmed.match(/^(.+?)\s*\((.+)\)$/);
      if (parts) {
        return (
          <div key={i} style={{ display: "flex", gap: 8, padding: "2px 0 2px 16px", fontSize: 13 }}>
            <span style={{ fontWeight: 600, minWidth: 100 }}>{parts[1]}</span>
            <span style={{ color: CN.textMuted }}>{parts[2]}</span>
          </div>
        );
      }
    }
    // Indented line
    if (line.startsWith("  ")) {
      return <div key={i} style={{ paddingLeft: 16, padding: "2px 0 2px 16px", fontSize: 13 }}>{trimmed}</div>;
    }
    // Normal line
    return <div key={i} style={{ padding: "2px 0" }}>{trimmed}</div>;
  });
}

function extractGenUI(answer: string): { text: string; html: string | null } {
  const marker = "<!--GENUI-->";
  const endMarker = "<!--/GENUI-->";
  const start = answer.indexOf(marker);
  if (start === -1) return { text: answer, html: null };
  const end = answer.indexOf(endMarker, start);
  const htmlContent = end !== -1
    ? answer.slice(start + marker.length, end).trim()
    : answer.slice(start + marker.length).trim();
  const text = answer.slice(0, start).trim();
  return { text, html: htmlContent };
}

function buildSourceGraph(sources: ChatSource[]): GraphData {
  const groups: GraphData["groups"] = [];
  const nodes: GraphData["nodes"] = [];
  const edges: GraphData["edges"] = [];
  const addedGroups = new Set<string>();
  const addedNodes = new Set<string>();

  // Center node: the answer
  nodes.push({
    id: "__answer__",
    label: "AI 回答",
    type: "Answer",
    color: "#2563EB",
    size: 40,
    parent: undefined,
  });

  for (const src of sources) {
    if (!src.id || addedNodes.has(src.id)) continue;
    addedNodes.add(src.id);

    const nodeType = src.table || "Unknown";
    const layer = getNodeLayer(nodeType);
    if (!addedGroups.has(layer)) {
      addedGroups.add(layer);
      groups.push({ id: layer, label: layer });
    }

    const label = (src.text || src.id).slice(0, 35);
    nodes.push({
      id: src.id,
      label,
      type: nodeType,
      color: NODE_COLORS[nodeType] || "#94A3B8",
      size: 20,
      parent: layer,
    });

    edges.push({
      id: `${src.id}-__answer__`,
      source: src.id,
      target: "__answer__",
      label: "支撑",
      color: "#60A5FA",
    });
  }

  return { nodes, edges, groups };
}

export default function ReasoningPage() {
  const [entries, setEntries] = useState<QAEntry[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);
  const [expandedSources, setExpandedSources] = useState(false);
  const graphRef = useRef<CytoscapeGraphHandle>(null);
  const answerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const currentEntry = entries.find((e) => e.id === selectedEntry) || entries[0] || null;

  const handleAsk = useCallback(async () => {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);

    try {
      const resp = await chatRAG(q);
      const { text, html } = extractGenUI(resp.answer);

      // Build graph from sources
      let graphData = buildSourceGraph(resp.sources || []);

      // Try to expand top sources with graph neighbors for richer visualization
      if (resp.sources && resp.sources.length > 0) {
        const addedNodes = new Set(graphData.nodes.map((n) => n.id));
        const addedGroups = new Set(graphData.groups.map((g) => g.id));
        const extraNodes = [...graphData.nodes];
        const extraEdges = [...graphData.edges];
        const extraGroups = [...graphData.groups];

        for (const src of resp.sources.slice(0, 3)) {
          if (!src.id || !src.table) continue;
          try {
            const gr = await getGraph(src.table, src.id);
            for (const nb of (gr.neighbors || []).slice(0, 5)) {
              if (!nb.target_id || addedNodes.has(nb.target_id)) continue;
              addedNodes.add(nb.target_id);
              const layer = getNodeLayer(nb.target_type);
              if (!addedGroups.has(layer)) {
                addedGroups.add(layer);
                extraGroups.push({ id: layer, label: layer });
              }
              extraNodes.push({
                id: nb.target_id,
                label: (nb.target_label || nb.target_id).slice(0, 30),
                type: nb.target_type,
                color: NODE_COLORS[nb.target_type] || "#94A3B8",
                size: 12,
                parent: layer,
              });
              const s = nb.direction === "incoming" ? nb.target_id : src.id;
              const t = nb.direction === "incoming" ? src.id : nb.target_id;
              extraEdges.push({
                id: `${s}-${t}-${nb.edge_type}`,
                source: s, target: t,
                label: EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type.slice(0, 12),
                color: EDGE_COLORS[nb.edge_type] || "#4B5563",
              });
            }
          } catch { /* skip */ }
        }
        graphData = { nodes: extraNodes, edges: extraEdges, groups: extraGroups };
      }

      const entry: QAEntry = {
        id: `qa-${Date.now()}`,
        question: q,
        answer: text,
        sources: resp.sources || [],
        html: html || resp.html || undefined,
        graphData,
        timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
      };

      setEntries((prev) => [entry, ...prev]);
      setSelectedEntry(entry.id);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "查询失败");
    }
    setLoading(false);
  }, [question, loading]);

  // Resize iframe for GenUI content
  useEffect(() => {
    const handler = (ev: MessageEvent) => {
      if (ev.data?.type === "resize" && iframeRef.current) {
        iframeRef.current.style.height = `${ev.data.height + 20}px`;
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 49px)" }}>
      {/* Top: Question Input */}
      <div style={{
        padding: "12px 32px", background: CN.bg, borderBottom: `1px solid ${CN.border}`,
        display: "flex", alignItems: "center", gap: 12, flexShrink: 0,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: CN.blue, whiteSpace: "nowrap" }}>
          知识问答
        </div>
        <input
          type="text"
          placeholder="输入业财税问题 (如: 增值税小规模纳税人优惠政策有哪些?)"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          style={{ ...cnInput, flex: 1 }}
        />
        <button onClick={handleAsk} disabled={loading}
          style={{ ...cnBtnPrimary, opacity: loading ? 0.5 : 1, cursor: loading ? "wait" : "pointer", whiteSpace: "nowrap" }}>
          {loading ? "查询中..." : "提问"}
        </button>
      </div>

      {error && (
        <div style={{ padding: "8px 32px", background: CN.redBg, color: CN.red, fontSize: 13, borderBottom: `1px solid ${CN.border}` }}>
          {error}
        </div>
      )}

      {/* Main: 3-Panel Layout */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* Left: Q&A History */}
        <div style={{
          width: 280, flexShrink: 0, overflowY: "auto",
          background: CN.bgCard, borderRight: `1px solid ${CN.border}`,
        }}>
          <div style={{ padding: "12px 16px", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px", borderBottom: `1px solid ${CN.border}` }}>
            问答记录 ({entries.length})
          </div>
          {entries.length === 0 ? (
            <div style={{ padding: 20, textAlign: "center", color: CN.textMuted, fontSize: 12 }}>
              输入问题开始知识问答
            </div>
          ) : entries.map((entry) => (
            <button key={entry.id}
              onClick={() => setSelectedEntry(entry.id)}
              style={{
                display: "block", width: "100%", padding: "12px 16px", textAlign: "left",
                background: entry.id === selectedEntry ? CN.blueBg : "transparent",
                border: "none",
                borderLeft: `2px solid ${entry.id === selectedEntry ? CN.blue : "transparent"}`,
                borderBottom: `1px solid ${CN.border}`,
                cursor: "pointer",
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: CN.text, marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {entry.question}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 10, color: CN.textMuted }}>{entry.timestamp}</span>
                <span style={cnBadge(CN.green, CN.greenBg)}>
                  {entry.sources.length} 源
                </span>
              </div>
            </button>
          ))}
        </div>

        {/* Center: Answer + Graph */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {!currentEntry ? (
            <div style={{
              flex: 1, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", color: CN.textMuted,
            }}>
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 16, opacity: 0.3 }}>
                <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="5" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="19" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="5" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="19" cy="19" r="2" stroke="currentColor" strokeWidth="1.5" />
                <path d="M7 6.5L9.5 10M14.5 10L17 6.5M9.5 14L7 17.5M14.5 14L17 17.5" stroke="currentColor" strokeWidth="1" />
              </svg>
              <span style={{ fontSize: 15, color: CN.text }}>基于知识图谱的智能问答</span>
              <span style={{ fontSize: 12, marginTop: 6 }}>输入业财税问题，AI 结合 KG 实时检索回答</span>
            </div>
          ) : (
            <>
              {/* Answer Section */}
              <div ref={answerRef} style={{
                padding: "20px 28px", overflowY: "auto",
                borderBottom: `1px solid ${CN.border}`,
                maxHeight: currentEntry.html ? "35vh" : "45vh",
              }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: CN.blue, marginBottom: 8 }}>
                  Q: {currentEntry.question}
                </div>
                <div style={{ fontSize: 14, color: CN.text, lineHeight: 1.8 }}>
                  {formatRAGAnswer(currentEntry.answer)}
                </div>

                {/* GenUI HTML iframe */}
                {currentEntry.html && (
                  <div style={{ marginTop: 16, border: `1px solid ${CN.border}`, borderRadius: 6, overflow: "hidden" }}>
                    <div style={{ padding: "6px 12px", background: CN.bgElevated, fontSize: 10, fontWeight: 700, color: CN.textMuted, letterSpacing: "1px" }}>
                      INTERACTIVE VISUALIZATION
                    </div>
                    <iframe
                      ref={iframeRef}
                      srcDoc={currentEntry.html}
                      style={{ width: "100%", minHeight: 200, border: "none", background: "#fff" }}
                      sandbox="allow-scripts"
                    />
                  </div>
                )}

                {/* Sources list */}
                {currentEntry.sources.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <button
                      onClick={() => setExpandedSources(!expandedSources)}
                      style={{ background: "none", border: "none", cursor: "pointer", fontSize: 11, fontWeight: 700, color: CN.textMuted, letterSpacing: "1px", padding: 0 }}
                    >
                      {expandedSources ? "v" : ">"} 知识来源 ({currentEntry.sources.length})
                    </button>
                    {expandedSources && (
                      <div style={{ marginTop: 8 }}>
                        {currentEntry.sources.map((src, i) => (
                          <div key={i} style={{
                            padding: "8px 12px", marginBottom: 4,
                            background: CN.bgElevated, borderRadius: 4, border: `1px solid ${CN.border}`,
                          }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                              <span style={cnBadge(NODE_COLORS[src.table] || CN.textMuted, CN.bgCard)}>
                                {src.table}
                              </span>
                              {src.score !== undefined && (
                                <span style={{ fontSize: 10, color: CN.textMuted, fontFamily: "monospace" }}>
                                  score: {src.score.toFixed(4)}
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 12, color: CN.textSecondary, lineHeight: 1.6 }}>
                              {src.text?.slice(0, 200) || src.id}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Knowledge Graph Visualization */}
              <div style={{ flex: 1, position: "relative", minHeight: 200, background: CN.bgCanvas }}>
                <div style={{
                  position: "absolute", top: 8, left: 12, zIndex: 10,
                  fontSize: 10, fontWeight: 700, color: "#8B949E", letterSpacing: "1px",
                  background: "rgba(13,17,23,0.8)", padding: "4px 10px", borderRadius: 4,
                }}>
                  KNOWLEDGE GRAPH -- {currentEntry.graphData.nodes.length} 节点 / {currentEntry.graphData.edges.length} 边
                </div>
                <CytoscapeGraph
                  ref={graphRef}
                  data={currentEntry.graphData}
                  onNodeSelect={setSelectedNode}
                  onNodeDblClick={() => {}}
                />
              </div>
            </>
          )}
        </div>

        {/* Right: Selected Node Detail */}
        {selectedNode && currentEntry && (
          <div style={{
            width: 280, flexShrink: 0, overflowY: "auto",
            background: CN.bgCard, borderLeft: `1px solid ${CN.border}`, padding: 16,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: CN.text, margin: 0 }}>
                {selectedNode.label}
              </h3>
              <button onClick={() => setSelectedNode(null)}
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

            {/* Show full source text if available */}
            {(() => {
              const src = currentEntry.sources.find((s) => s.id === selectedNode.id);
              if (src?.text) {
                return (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>内容</div>
                    <div style={{ fontSize: 12, color: CN.textSecondary, lineHeight: 1.7, maxHeight: 200, overflowY: "auto" }}>
                      {src.text}
                    </div>
                  </div>
                );
              }
              return null;
            })()}

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>ID</div>
              <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2, wordBreak: "break-all", fontFamily: "monospace" }}>
                {selectedNode.id}
              </div>
            </div>

            {selectedNode.neighbors.length > 0 && (
              <div style={{ borderTop: `1px solid ${CN.border}`, paddingTop: 12 }}>
                <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>
                  关联 ({selectedNode.neighbors.length})
                </div>
                {selectedNode.neighbors.map((nb, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "5px 0", borderBottom: `1px solid ${CN.bgElevated}`, fontSize: 12,
                  }}>
                    <span style={{ color: CN.text, maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {nb.direction === "incoming" ? "\u2190 " : "\u2192 "}{nb.target_label}
                    </span>
                    <span style={cnBadge(EDGE_COLORS[nb.edge_type] || CN.textMuted, CN.bgElevated)}>
                      {EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
