"use client";

import React, { useEffect, useRef, useCallback, useState, type ErrorInfo } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";

export interface SigmaGraphData {
  nodes: { id: string; label: string; type: string; size: number }[];
  edges: { source: string; target: string; label?: string }[];
}

interface Props {
  data: SigmaGraphData;
  highlightTypes?: string[];  // When set, only these node types are fully visible
  onNodeClick?: (nodeId: string, nodeType: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
}

/* ── Error Boundary (class component required by React) ── */
class SigmaErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[SigmaGraph] render crash:", error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
          height: "100%", background: "#0F172A", color: "#9CA3AF", padding: 40 }}>
          <div style={{ textAlign: "center", maxWidth: 400 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#E5E7EB", marginBottom: 8 }}>
              星图渲染出错
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.6 }}>
              {this.state.error.message}
            </div>
            <button onClick={() => this.setState({ error: null })}
              style={{ marginTop: 16, padding: "6px 16px", background: "#1E293B",
                color: "#E5E7EB", border: "1px solid #334155", borderRadius: 4,
                cursor: "pointer", fontSize: 12 }}>
              重试
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/* ── Sigma Renderer ── */
function SigmaRenderer({ data, highlightTypes, onNodeClick, onNodeHover }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const nodeSizesRef = useRef<Map<string, number>>(new Map());
  const hoveredRef = useRef<string | null>(null);
  const neighborsRef = useRef<Set<string>>(new Set());
  const [initError, setInitError] = useState<string | null>(null);

  const cleanup = useCallback(() => {
    try { sigmaRef.current?.kill(); } catch { /* safe cleanup */ }
    sigmaRef.current = null;
    graphRef.current = null;
    nodeSizesRef.current.clear();
    hoveredRef.current = null;
    neighborsRef.current.clear();
  }, []);

  useEffect(() => {
    if (!containerRef.current || data.nodes.length === 0) return;
    cleanup();
    setInitError(null);

    try {
      const graph = new Graph();
      const addedNodes = new Set<string>();

      // Layer filter
      const hlSet = highlightTypes && highlightTypes.length > 0
        ? new Set(highlightTypes)
        : null;

      for (const n of data.nodes) {
        if (addedNodes.has(n.id)) continue;
        addedNodes.add(n.id);
        const baseSize = n.size || 3;
        nodeSizesRef.current.set(n.id, baseSize);
        const isHL = !hlSet || hlSet.has(n.type);
        graph.addNode(n.id, {
          label: n.label,
          x: Math.random() * 1000,
          y: Math.random() * 1000,
          size: isHL ? baseSize : baseSize * 0.4,
          color: isHL ? "#C9CDD3" : "#1E293B",
          nodeType: n.type,
        });
      }

      for (const e of data.edges) {
        if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue;
        if (graph.hasEdge(e.source, e.target)) continue;
        try {
          graph.addEdge(e.source, e.target, {
            color: "#475569",   // Visible slate-600 (was #262D3A — too dark)
            size: 0.5,
            label: e.label || "",
          });
        } catch { /* skip duplicate edges */ }
      }

      graphRef.current = graph;

      // ForceAtlas2: tuned for 1000+ nodes
      const nodeCount = graph.order;
      forceAtlas2.assign(graph, {
        iterations: nodeCount > 500 ? 150 : 80,
        settings: {
          gravity: nodeCount > 500 ? 3 : 1,
          scalingRatio: nodeCount > 500 ? 20 : 10,
          barnesHutOptimize: true,
          barnesHutTheta: 0.5,
          slowDown: nodeCount > 500 ? 8 : 5,
          strongGravityMode: true,
          outboundAttractionDistribution: true,
        },
      });

      // Sigma renderer with nodeReducer/edgeReducer for hover highlighting.
      const sigma = new Sigma(graph, containerRef.current, {
        renderLabels: true,
        labelRenderedSizeThreshold: nodeCount > 500 ? 12 : nodeCount > 100 ? 5 : 3,
        labelSize: 11,
        labelColor: { color: "#E5E7EB" },
        labelFont: "'Inter', 'Noto Sans SC', system-ui, sans-serif",
        defaultNodeColor: "#C9CDD3",
        defaultEdgeColor: "#475569",
        defaultNodeType: "circle",
        defaultEdgeType: "line",
        allowInvalidContainer: true,
        nodeReducer: (node, attrs) => {
          const res = { ...attrs };
          const hov = hoveredRef.current;
          if (hov) {
            if (node === hov) {
              res.color = "#60A5FA";
              res.size = (nodeSizesRef.current.get(node) || 3) * 2.5;
              res.zIndex = 2;
            } else if (neighborsRef.current.has(node)) {
              res.color = "#93C5FD";
              res.size = (nodeSizesRef.current.get(node) || 3) * 1.5;
              res.zIndex = 1;
            } else {
              res.color = "#1E293B";
              res.size = (attrs.size || 3) * 0.4;
              res.label = "";
            }
          }
          return res;
        },
        edgeReducer: (edge, attrs) => {
          const res = { ...attrs };
          const hov = hoveredRef.current;
          if (hov) {
            const [src, tgt] = graph.extremities(edge);
            if (src === hov || tgt === hov) {
              res.color = "#60A5FA";
              res.size = 2;
            } else {
              res.color = "#111827";
              res.size = 0.1;
            }
          }
          return res;
        },
      });

      sigmaRef.current = sigma;

      // Hover: set ref + refresh (reducers handle the visuals)
      sigma.on("enterNode", ({ node }) => {
        hoveredRef.current = node;
        neighborsRef.current = new Set(graph.neighbors(node));
        onNodeHover?.(node);
        sigma.refresh();
      });

      sigma.on("leaveNode", () => {
        hoveredRef.current = null;
        neighborsRef.current.clear();
        onNodeHover?.(null);
        sigma.refresh();
      });

      sigma.on("clickNode", ({ node }) => {
        const nodeType = graph.getNodeAttribute(node, "nodeType") || "";
        onNodeClick?.(node, nodeType);
      });

    } catch (err) {
      console.error("[SigmaGraph] initialization failed:", err);
      setInitError(err instanceof Error ? err.message : String(err));
    }

    return () => { cleanup(); };
  }, [data, onNodeClick, onNodeHover, cleanup]);

  if (initError) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
        height: "100%", background: "#0F172A", color: "#9CA3AF", padding: 40 }}>
        <div style={{ textAlign: "center", maxWidth: 400 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#E5E7EB", marginBottom: 8 }}>
            星图初始化失败
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.6 }}>{initError}</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        background: "#0F172A",
      }}
    />
  );
}

/* ── Export with Error Boundary ── */
export default function SigmaGraph(props: Props) {
  return (
    <SigmaErrorBoundary>
      <SigmaRenderer {...props} />
    </SigmaErrorBoundary>
  );
}
