"use client";

import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from "react";
import type { KGNeighbor } from "../lib/kg-api";

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
    cyRef.current?.fit(undefined, 50);
  }, []);

  const runLayout = useCallback((name = "fcose") => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.layout({
      name,
      animate: true,
      animationDuration: 600,
      animationEasing: "ease-out",
      quality: "default",
      nodeSeparation: 100,
      idealEdgeLength: 150,
      nodeRepulsion: 12000,
      gravity: 0.25,
      gravityRange: 250,
      nestingFactor: 0.12,
      componentSpacing: 80,
      tile: true,
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
        style: [  // shadow-* properties are valid Cytoscape CSS but missing from @types/cytoscape
          /* ── Compound (Group) Nodes ── */
          {
            selector: "node.group",
            style: {
              "shape": "round-rectangle",
              "background-color": "#161B22",
              "background-opacity": 0.6,
              "border-width": 1,
              "border-color": "#30363D",
              "border-opacity": 0.8,
              "label": "data(label)",
              "text-valign": "top",
              "text-halign": "center",
              "font-size": 11,
              "font-weight": 700,
              "font-family": "'Inter', 'Noto Sans SC', system-ui, sans-serif",
              "color": "#8B949E",
              "text-margin-y": 8,
              "padding": "28px",
            },
          },
          /* ── Entity Nodes ── */
          {
            selector: "node.entity",
            style: {
              "background-color": "data(color)",
              "background-opacity": 0.85,
              "label": "data(label)",
              "width": "mapData(size, 1, 100, 20, 60)",
              "height": "mapData(size, 1, 100, 20, 60)",
              "border-width": 2,
              "border-color": "data(color)",
              "border-opacity": 0.4,
              "font-size": 11,
              "font-family": "'Inter', 'Noto Sans SC', system-ui, sans-serif",
              "font-weight": 500,
              "color": "#E6EDF3",
              "text-outline-width": 2.5,
              "text-outline-color": "#0D1117",
              "text-outline-opacity": 0.9,
              "text-max-width": "100px",
              "text-wrap": "ellipsis",
              "text-margin-y": 4,
              "overlay-padding": 6,
            },
          },
          /* ── Large center nodes (size >= 30) ── */
          {
            selector: "node.entity[size >= 30]",
            style: {
              "font-size": 12,
              "font-weight": 700,
              "shadow-blur": 20,
              "shadow-opacity": 0.5,
              "border-width": 3,
            },
          },
          /* ── Hover state ── */
          {
            selector: "node.entity.hover",
            style: {
              "border-width": 3,
              "border-color": "#58A6FF",
              "border-opacity": 1,
              "shadow-blur": 25,
              "shadow-color": "#58A6FF",
              "shadow-opacity": 0.6,
              "background-opacity": 1,
              "z-index": 999,
            },
          },
          /* ── Dimmed (neighbors not highlighted) ── */
          {
            selector: "node.entity.dimmed",
            style: {
              "background-opacity": 0.15,
              "border-opacity": 0.1,
              "shadow-opacity": 0,
              "color": "#484F58",
              "text-outline-opacity": 0.3,
            },
          },
          /* ── Selected state ── */
          {
            selector: "node:selected",
            style: {
              "border-width": 3,
              "border-color": "#58A6FF",
              "border-opacity": 1,
              "background-opacity": 1,
              "shadow-blur": 30,
              "shadow-color": "#58A6FF",
              "shadow-opacity": 0.7,
            },
          },
          /* ── Edges ── */
          {
            selector: "edge",
            style: {
              "width": 1.5,
              "line-color": "data(color)",
              "line-opacity": 0.5,
              "target-arrow-color": "data(color)",
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.8,
              "label": "data(label)",
              "font-size": 9,
              "font-family": "'Inter', 'Noto Sans SC', system-ui, sans-serif",
              "font-weight": 500,
              "color": "#6B7280",
              "text-outline-width": 2,
              "text-outline-color": "#0D1117",
              "text-outline-opacity": 0.8,
              "text-rotation": "autorotate",
              "curve-style": "bezier",
              "text-background-color": "#0D1117",
              "text-background-opacity": 0.7,
              "text-background-padding": "2px",
            },
          },
          /* ── Highlighted edges ── */
          {
            selector: "edge.highlighted",
            style: {
              "width": 2.5,
              "line-opacity": 1,
              "line-color": "#58A6FF",
              "target-arrow-color": "#58A6FF",
              "color": "#A5D6FF",
              "z-index": 999,
            },
          },
          /* ── Dimmed edges ── */
          {
            selector: "edge.dimmed",
            style: {
              "line-opacity": 0.08,
              "color": "#30363D",
              "text-outline-opacity": 0,
              "text-background-opacity": 0,
            },
          },
          /* ── Selected edge ── */
          {
            selector: "edge:selected",
            style: {
              "width": 3,
              "line-color": "#58A6FF",
              "target-arrow-color": "#58A6FF",
              "line-opacity": 1,
              "color": "#A5D6FF",
            },
          },
        ] as any,  // shadow-* props are valid runtime CSS but missing from @types/cytoscape
        layout: { name: "preset" },
        wheelSensitivity: 0.3,
        minZoom: 0.15,
        maxZoom: 4,
      });

      cyRef.current = cy;

      /* ── Hover: highlight node + connected edges + neighbors ── */
      cy.on("mouseover", "node.entity", (evt) => {
        const node = evt.target;
        const neighborhood = node.closedNeighborhood();
        cy.elements().not(neighborhood).addClass("dimmed");
        node.addClass("hover");
        node.connectedEdges().addClass("highlighted");
      });

      cy.on("mouseout", "node.entity", () => {
        cy.elements().removeClass("dimmed hover highlighted");
      });

      /* ── Click: select node ── */
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
        background: "radial-gradient(ellipse at center, #161B22 0%, #0D1117 70%)",
        backgroundImage: `
          radial-gradient(ellipse at center, #161B22 0%, #0D1117 70%),
          linear-gradient(rgba(88,166,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(88,166,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: "100% 100%, 40px 40px, 40px 40px",
      }}
    />
  );
});

export default CytoscapeGraph;
