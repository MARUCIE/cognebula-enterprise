"use client";

import React, { useEffect, useRef, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import Forceatlas2Layout from "graphology-layout-forceatlas2/worker";
import { CN } from "../lib/cognebula-theme";

export interface SigmaGraphData {
  nodes: { id: string; label: string; type: string; size: number }[];
  edges: { source: string; target: string; label?: string }[];
}

interface Props {
  data: SigmaGraphData;
  onNodeClick?: (nodeId: string, nodeType: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
}

export default function SigmaGraph({ data, onNodeClick, onNodeHover }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const layoutRef = useRef<Forceatlas2Layout | null>(null);

  const cleanup = useCallback(() => {
    layoutRef.current?.kill();
    layoutRef.current = null;
    sigmaRef.current?.kill();
    sigmaRef.current = null;
    graphRef.current = null;
  }, []);

  useEffect(() => {
    if (!containerRef.current || data.nodes.length === 0) return;
    cleanup();

    // Build graphology graph
    const graph = new Graph();
    const addedNodes = new Set<string>();

    for (const n of data.nodes) {
      if (addedNodes.has(n.id)) continue;
      addedNodes.add(n.id);
      // Random initial positions for force layout
      graph.addNode(n.id, {
        label: n.label,
        x: Math.random() * 1000,
        y: Math.random() * 1000,
        size: n.size || 3,
        color: "#D1D5DB",  // Monochrome gray (Obsidian style)
        type: n.type,
        nodeType: n.type,
      });
    }

    for (const e of data.edges) {
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue;
      if (graph.hasEdge(e.source, e.target)) continue;
      try {
        graph.addEdge(e.source, e.target, {
          color: "#374151",  // Dark gray edges
          size: 0.5,
          label: e.label || "",
        });
      } catch { /* skip duplicate edges */ }
    }

    graphRef.current = graph;

    // Create Sigma renderer
    const sigma = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      labelRenderedSizeThreshold: 8,   // Only show labels when node rendered > 8px
      labelSize: 11,
      labelColor: { color: "#E5E7EB" },
      labelFont: "'Inter', 'Noto Sans SC', system-ui, sans-serif",
      defaultNodeColor: "#D1D5DB",
      defaultEdgeColor: "#374151",
      defaultNodeType: "circle",
      defaultEdgeType: "line",
      allowInvalidContainer: true,
      // Hover highlighting
      nodeReducer: (node, data) => {
        const res = { ...data };
        if (sigmaRef.current) {
          const hoveredNode = sigmaRef.current.getCustomBBox();
          // Default: all nodes same monochrome style
        }
        return res;
      },
    });

    sigmaRef.current = sigma;

    // Hover events
    sigma.on("enterNode", ({ node }) => {
      onNodeHover?.(node);
      // Highlight hovered node
      graph.setNodeAttribute(node, "color", "#60A5FA");
      graph.setNodeAttribute(node, "size", (graph.getNodeAttribute(node, "size") || 3) * 2);
      sigma.refresh();
    });

    sigma.on("leaveNode", ({ node }) => {
      onNodeHover?.(null);
      graph.setNodeAttribute(node, "color", "#D1D5DB");
      graph.setNodeAttribute(node, "size", (graph.getNodeAttribute(node, "size") || 6) / 2);
      sigma.refresh();
    });

    // Click events
    sigma.on("clickNode", ({ node }) => {
      const nodeType = graph.getNodeAttribute(node, "nodeType") || "";
      onNodeClick?.(node, nodeType);
    });

    // Start ForceAtlas2 layout
    const layout = new Forceatlas2Layout(graph, {
      settings: {
        gravity: 1,
        scalingRatio: 10,
        barnesHutOptimize: true,
        barnesHutTheta: 0.5,
        slowDown: 5,
        strongGravityMode: false,
        outboundAttractionDistribution: true,
      },
    });
    layout.start();
    layoutRef.current = layout;

    // Stop layout after convergence (~5 seconds)
    const stopTimer = setTimeout(() => {
      layout.stop();
    }, 5000);

    return () => {
      clearTimeout(stopTimer);
      cleanup();
    };
  }, [data, onNodeClick, onNodeHover, cleanup]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        background: "#0F172A",  // Very dark blue-gray (Obsidian style)
      }}
    />
  );
}
