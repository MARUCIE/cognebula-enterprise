"use client";

import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from "react";
import type { KGNeighbor } from "../lib/kg-api";

/* Cytoscape requires DOM — import dynamically inside useEffect */
type CyInstance = import("cytoscape").Core;

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  size: number;
  parent?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  color: string;
}

export interface GraphGroup {
  id: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  groups: GraphGroup[];
}

export interface SelectedNode {
  id: string;
  label: string;
  type: string;
  neighbors: KGNeighbor[];
}

export interface CytoscapeGraphHandle {
  fit: () => void;
  runLayout: (name?: string) => void;
}

interface Props {
  data: GraphData;
  onNodeSelect?: (node: SelectedNode | null) => void;
  onNodeDblClick?: (nodeId: string, nodeType: string) => void;
}

const CytoscapeGraph = forwardRef<CytoscapeGraphHandle, Props>(function CytoscapeGraph(
  { data, onNodeSelect, onNodeDblClick },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<CyInstance | null>(null);

  const fitGraph = useCallback(() => {
    cyRef.current?.fit(undefined, 40);
  }, []);

  const runLayout = useCallback((name = "fcose") => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.layout({
      name,
      animate: true,
      animationDuration: 500,
      quality: "default",
      nodeSeparation: 80,
      idealEdgeLength: 120,
      nodeRepulsion: 8000,
      gravity: 0.3,
      gravityRange: 200,
      nestingFactor: 0.15,
      componentSpacing: 60,
    } as unknown as cytoscape.LayoutOptions).run();
  }, []);

  useImperativeHandle(ref, () => ({ fit: fitGraph, runLayout }), [fitGraph, runLayout]);

  useEffect(() => {
    let mounted = true;

    async function init() {
      const cytoscape = (await import("cytoscape")).default;
      const fcose = (await import("cytoscape-fcose")).default;
      cytoscape.use(fcose);

      if (!mounted || !containerRef.current) return;

      const cy = cytoscape({
        container: containerRef.current,
        style: [
          {
            selector: "node.group",
            style: {
              "shape": "round-rectangle",
              "background-opacity": 0.12,
              "border-width": 1,
              "border-color": "#374151",
              "border-opacity": 0.3,
              "label": "data(label)",
              "text-valign": "top",
              "text-halign": "center",
              "font-size": 13,
              "font-weight": 700,
              "color": "#9CA3AF",
              "padding": "20px",
            },
          },
          {
            selector: "node.entity",
            style: {
              "background-color": "data(color)",
              "label": "data(label)",
              "width": "mapData(size, 1, 100, 18, 56)",
              "height": "mapData(size, 1, 100, 18, 56)",
              "font-size": 10,
              "font-family": "'SF Mono', 'Fira Code', 'JetBrains Mono', monospace",
              "color": "#D1D5DB",
              "text-outline-width": 2,
              "text-outline-color": "#0D1117",
              "text-max-width": "80px",
              "text-wrap": "ellipsis",
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-width": 3,
              "border-color": "#58A6FF",
              "background-color": "#58A6FF",
            },
          },
          {
            selector: "edge",
            style: {
              "width": 1.2,
              "line-color": "data(color)",
              "target-arrow-color": "data(color)",
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.7,
              "label": "data(label)",
              "font-size": 8,
              "font-family": "'SF Mono', monospace",
              "color": "#6B7280",
              "text-rotation": "autorotate",
              "curve-style": "bezier",
              "opacity": 0.7,
            },
          },
          {
            selector: "edge:selected",
            style: { "width": 2.5, "line-color": "#58A6FF", "target-arrow-color": "#58A6FF", "opacity": 1 },
          },
        ],
        layout: { name: "preset" },
        wheelSensitivity: 0.3,
      });

      cyRef.current = cy;

      cy.on("tap", "node.entity", (evt) => {
        const node = evt.target;
        const edges = node.connectedEdges();
        const neighbors: KGNeighbor[] = edges.map((e: cytoscape.EdgeSingular) => {
          const isSource = e.source().id() === node.id();
          const other = isSource ? e.target() : e.source();
          return {
            edge_type: e.data("rawType") || e.data("label"),
            target_type: other.data("type") || "",
            target_id: other.id(),
            target_label: other.data("label") || other.id(),
            direction: isSource ? "outgoing" as const : "incoming" as const,
          };
        });
        onNodeSelect?.({
          id: node.id(),
          label: node.data("label"),
          type: node.data("type"),
          neighbors,
        });
      });

      cy.on("tap", (evt) => {
        if (evt.target === cy) onNodeSelect?.(null);
      });

      cy.on("dbltap", "node.entity", (evt) => {
        const node = evt.target;
        onNodeDblClick?.(node.id(), node.data("type"));
      });
    }

    init();
    return () => {
      mounted = false;
      cyRef.current?.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Update graph data when props change */
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.elements().remove();

    const elements: cytoscape.ElementDefinition[] = [];

    for (const g of data.groups) {
      elements.push({ group: "nodes", data: { id: g.id, label: g.label }, classes: "group" });
    }
    for (const n of data.nodes) {
      elements.push({
        group: "nodes",
        data: { id: n.id, label: n.label, type: n.type, color: n.color, size: n.size, parent: n.parent },
        classes: "entity",
      });
    }
    for (const e of data.edges) {
      elements.push({
        group: "edges",
        data: { id: e.id, source: e.source, target: e.target, label: e.label, color: e.color, rawType: e.label },
      });
    }

    cy.add(elements);
    runLayout();
  }, [data, runLayout]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        background: "#0D1117",
      }}
    />
  );
});

export default CytoscapeGraph;
