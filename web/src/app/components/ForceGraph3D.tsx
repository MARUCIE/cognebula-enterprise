"use client";

import { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from "react";
import type { KGNeighbor } from "../lib/kg-api";

export interface Graph3DNode {
  id: string;
  label: string;
  type: string;
  color: string;
  size: number;
  group?: string;
}

export interface Graph3DEdge {
  source: string;
  target: string;
  label: string;
  color: string;
}

export interface Graph3DData {
  nodes: Graph3DNode[];
  links: Graph3DEdge[];
}

export interface Selected3DNode {
  id: string;
  label: string;
  type: string;
  neighbors: KGNeighbor[];
}

export interface ForceGraph3DHandle {
  zoomToFit: () => void;
}

interface Props {
  data: Graph3DData;
  onNodeSelect?: (node: Selected3DNode | null) => void;
  onNodeDblClick?: (nodeId: string, nodeType: string) => void;
}

const ForceGraph3DComponent = forwardRef<ForceGraph3DHandle, Props>(function ForceGraph3DComponent(
  { data, onNodeSelect, onNodeDblClick },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [mounted, setMounted] = useState(false);
  const [GraphComp, setGraphComp] = useState<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useImperativeHandle(ref, () => ({
    zoomToFit: () => graphRef.current?.zoomToFit(800, 60),
  }), []);

  // Dynamic import
  useEffect(() => {
    import("react-force-graph-3d").then((mod) => {
      setGraphComp(() => mod.default);
      setMounted(true);
    });
  }, []);

  // Track container size
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    ro.observe(el);
    setDimensions({ width: el.clientWidth, height: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  // Configure forces for sphere shape + auto-rotate
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg || data.nodes.length === 0) return;

    // Dense sphere forces — tight Obsidian-style globe
    const d3 = require("d3-force-3d");
    const nodeCount = data.nodes.length;

    // Very weak repulsion for tight packing
    fg.d3Force("charge", d3.forceManyBody().strength(-8));
    // Strong center gravity
    fg.d3Force("center", d3.forceCenter(0, 0, 0).strength(0.15));

    // Very tight radial constraint — force all nodes onto sphere shell
    const radius = Math.max(40, Math.pow(nodeCount, 0.35) * 9);
    fg.d3Force("radial", d3.forceRadial(radius, 0, 0, 0).strength(0.95));

    // Short link distance for web density
    fg.d3Force("link")?.distance(15).strength(0.4);

    // Collision to prevent overlap
    fg.d3Force("collision", d3.forceCollide().radius((n: any) => Math.max(2, (n.size || 3) * 0.4)).strength(0.6));

    // Auto-rotate (slow orbit)
    let angle = 0;
    const rotate = () => {
      if (!graphRef.current) return;
      angle += 0.0015;
      const dist = radius * 3.2;
      graphRef.current.cameraPosition({
        x: dist * Math.sin(angle),
        y: dist * 0.2 * Math.sin(angle * 0.3),
        z: dist * Math.cos(angle),
      });
    };
    const interval = setInterval(rotate, 30);

    // Initial zoom
    setTimeout(() => fg.zoomToFit(1000, 80), 800);

    return () => clearInterval(interval);
  }, [data, mounted]);

  // Double-click detection via timer
  const lastClickRef = useRef<{ id: string; time: number }>({ id: "", time: 0 });

  const handleNodeClick = useCallback((node: any, event: MouseEvent) => {
    event.stopPropagation();

    // Double-click detection (< 400ms between clicks on same node)
    const now = Date.now();
    const last = lastClickRef.current;
    if (last.id === node.id && now - last.time < 400) {
      // Double click → drill down
      lastClickRef.current = { id: "", time: 0 };
      onNodeDblClick?.(node.id, node.type || "");
      return;
    }
    lastClickRef.current = { id: node.id, time: now };

    // Single click: zoom to node + show detail
    const fg = graphRef.current;
    if (fg) {
      const dist = 80;
      fg.cameraPosition(
        { x: (node.x || 0) + dist, y: (node.y || 0) + dist * 0.2, z: (node.z || 0) + dist },
        node, 800
      );
    }

    const neighbors: KGNeighbor[] = data.links
      .filter((l: any) => {
        const s = typeof l.source === "object" ? l.source.id : l.source;
        const t = typeof l.target === "object" ? l.target.id : l.target;
        return s === node.id || t === node.id;
      })
      .map((l: any) => {
        const s = typeof l.source === "object" ? l.source.id : l.source;
        const t = typeof l.target === "object" ? l.target.id : l.target;
        const isSource = s === node.id;
        const otherId = isSource ? t : s;
        const other = data.nodes.find((n) => n.id === otherId);
        return {
          edge_type: l.label || "",
          target_type: other?.type || "",
          target_id: otherId,
          target_label: other?.label || otherId,
          direction: isSource ? "outgoing" as const : "incoming" as const,
        };
      });

    onNodeSelect?.({ id: node.id, label: node.label || node.id, type: node.type || "", neighbors });
  }, [data, onNodeSelect]);

  const handleNodeDblClick = useCallback((node: any) => {
    onNodeDblClick?.(node.id, node.type || "");
  }, [onNodeDblClick]);

  if (!mounted || !GraphComp) {
    return (
      <div ref={containerRef} style={{
        width: "100%", height: "100%",
        background: "radial-gradient(ellipse at center, #0F1923 0%, #080C14 100%)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#4A5568", fontSize: 13,
      }}>
        Loading 3D Engine...
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%", position: "relative" }}>
      <GraphComp
        ref={graphRef}
        graphData={data}
        width={dimensions.width}
        height={dimensions.height}
        nodeId="id"
        nodeLabel={(node: any) => `${node.label}\n[${node.type}]`}
        nodeColor={(node: any) => node.color || "#58A6FF"}
        nodeVal={(node: any) => Math.max(1, (node.size || 5) * 0.6)}
        nodeOpacity={0.95}
        nodeResolution={20}
        linkSource="source"
        linkTarget="target"
        linkColor={(link: any) => link.color ? `${link.color}50` : "#30363D40"}
        linkWidth={0.3}
        linkOpacity={0.25}
        linkDirectionalParticles={1}
        linkDirectionalParticleWidth={0.8}
        linkDirectionalParticleSpeed={0.003}
        linkDirectionalParticleColor={(link: any) => link.color || "#58A6FF"}
        linkCurvature={0}
        backgroundColor="rgba(0,0,0,0)"
        showNavInfo={false}
        onNodeClick={handleNodeClick}
        onBackgroundClick={() => onNodeSelect?.(null)}
        warmupTicks={80}
        cooldownTicks={200}
        enableNodeDrag={true}
        enableNavigationControls={true}
        nodeThreeObject={(node: any) => {
          const THREE = require("three");
          const group = new THREE.Group();
          const size = Math.max(1.5, (node.size || 5) * 0.35);
          const isLayer = node.type === "__layer__";

          // Main sphere with emissive glow
          const geo = new THREE.SphereGeometry(size, isLayer ? 32 : 16, isLayer ? 32 : 16);
          const color = new THREE.Color(node.color || "#58A6FF");
          const mat = new THREE.MeshStandardMaterial({
            color,
            emissive: color,
            emissiveIntensity: isLayer ? 0.4 : 0.2,
            metalness: 0.3,
            roughness: 0.4,
            transparent: true,
            opacity: isLayer ? 0.95 : 0.85,
          });
          group.add(new THREE.Mesh(geo, mat));

          // Outer glow shell — all nodes get a subtle aura
          const glowGeo = new THREE.SphereGeometry(size * (isLayer ? 2.0 : 1.6), 12, 12);
          const glowMat = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: isLayer ? 0.1 : 0.05,
            depthWrite: false,
          });
          group.add(new THREE.Mesh(glowGeo, glowMat));

          // Label sprite — visible at all zoom levels
          const text = (node.label || "").slice(0, 18);
          if (text) {
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d")!;
            const fontSize = isLayer ? 64 : 40;
            canvas.width = 512;
            canvas.height = 80;
            ctx.clearRect(0, 0, 512, 80);
            ctx.font = `600 ${fontSize}px "Inter", "Noto Sans SC", system-ui, sans-serif`;
            ctx.fillStyle = "#E6EDF3";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.shadowColor = "#000000";
            ctx.shadowBlur = 12;
            ctx.shadowOffsetY = 2;
            ctx.fillText(text, 256, 40);
            const tex = new THREE.CanvasTexture(canvas);
            const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85, depthTest: false });
            const sprite = new THREE.Sprite(spriteMat);
            const scale = isLayer ? size * 7 : Math.max(15, size * 5);
            sprite.scale.set(scale, scale * 80 / 512, 1);
            sprite.position.set(0, size * 1.1 + 2.5, 0);
            sprite.renderOrder = 999;
            group.add(sprite);
          }

          return group;
        }}
      />

      {/* Ambient background gradient overlay */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: "radial-gradient(ellipse at center, transparent 40%, #080C14 100%)",
        zIndex: 1,
      }} />
    </div>
  );
});

export default ForceGraph3DComponent;
