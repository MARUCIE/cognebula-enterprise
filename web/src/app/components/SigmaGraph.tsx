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
  const [initError, setInitError] = useState<string | null>(null);

  const cleanup = useCallback(() => {
    try { sigmaRef.current?.kill(); } catch { /* safe cleanup */ }
    sigmaRef.current = null;
    graphRef.current = null;
    nodeSizesRef.current.clear();
  }, []);

  useEffect(() => {
    if (!containerRef.current || data.nodes.length === 0) return;
    cleanup();
    setInitError(null);

    try {
      // Build graphology graph
      const graph = new Graph();
      const addedNodes = new Set<string>();

      // Layer filter: determine which nodes are highlighted
      const hlSet = highlightTypes && highlightTypes.length > 0
        ? new Set(highlightTypes)
        : null;

      for (const n of data.nodes) {
        if (addedNodes.has(n.id)) continue;
        addedNodes.add(n.id);
        const baseSize = n.size || 3;
        nodeSizesRef.current.set(n.id, baseSize);
        const isHighlighted = !hlSet || hlSet.has(n.type);
        graph.addNode(n.id, {
          label: n.label,
          x: Math.random() * 1000,
          y: Math.random() * 1000,
          size: isHighlighted ? baseSize : baseSize * 0.4,
          color: isHighlighted ? "#D1D5DB" : "#1E293B",
          nodeType: n.type,
        });
      }

      for (const e of data.edges) {
        if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue;
        if (graph.hasEdge(e.source, e.target)) continue;
        try {
          graph.addEdge(e.source, e.target, {
            color: "#262D3A",
            size: 0.3,
            label: e.label || "",
          });
        } catch { /* skip duplicate edges */ }
      }

      graphRef.current = graph;

      // ForceAtlas2: tuned for 1000+ nodes — more iterations, stronger gravity
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

      // Create Sigma renderer — label threshold higher for dense graphs
      const sigma = new Sigma(graph, containerRef.current, {
        renderLabels: true,
        labelRenderedSizeThreshold: nodeCount > 500 ? 12 : 8,
        labelSize: 11,
        labelColor: { color: "#E5E7EB" },
        labelFont: "'Inter', 'Noto Sans SC', system-ui, sans-serif",
        defaultNodeColor: "#D1D5DB",
        defaultEdgeColor: "#262D3A",
        defaultNodeType: "circle",
        defaultEdgeType: "line",
        allowInvalidContainer: true,
      });

      sigmaRef.current = sigma;

      // Hover: highlight with stable size (no cumulative drift)
      sigma.on("enterNode", ({ node }) => {
        onNodeHover?.(node);
        const base = nodeSizesRef.current.get(node) || 3;
        graph.setNodeAttribute(node, "color", "#60A5FA");
        graph.setNodeAttribute(node, "size", base * 2);
        sigma.refresh();
      });

      sigma.on("leaveNode", ({ node }) => {
        onNodeHover?.(null);
        const base = nodeSizesRef.current.get(node) || 3;
        graph.setNodeAttribute(node, "color", "#D1D5DB");
        graph.setNodeAttribute(node, "size", base);
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
