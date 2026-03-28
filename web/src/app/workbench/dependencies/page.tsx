"use client";

/* Dependency Graph — 依赖图
   Architecture ref: NEXT_GEN_WORKBENCH_DESIGN.md Section 4
   Interactive DAG: 41 tasks as nodes, dependencies as edges
   Uses Cytoscape.js (dynamic import, SSR-safe) */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  TASK_INSTANCES,
  TIME_WINDOWS,
  STATUS_STYLES,
  AGENT_MAP,
  type TaskInstance,
} from "../../lib/workbench-data";

// Per-enterprise dependencies (task B depends on task A for same enterprise)
// Batch-level dependencies marked with _batch suffix
const DEPENDENCY_EDGES: [number, number, "pe" | "batch"][] = [
  // W1: collection → bookkeeping → QC → adjust → close → tax prep
  [1, 4, "pe"], [2, 4, "pe"], [3, 4, "pe"], [8, 4, "pe"],
  [4, 5, "pe"], [5, 6, "pe"], [6, 7, "pe"],
  [7, 9, "pe"], [8, 9, "pe"],
  [9, 10, "pe"], [9, 11, "pe"],
  // W2: tax bookkeeping → close → filings (parallel) → audit → feedback
  [9, 13, "pe"], [13, 14, "pe"],
  [14, 15, "pe"], [14, 16, "pe"], [7, 17, "pe"], [14, 17, "pe"],
  [14, 18, "pe"], [14, 19, "pe"], [14, 20, "pe"], [14, 21, "pe"], [14, 22, "pe"],
  // Batch-level: all filings must complete for all enterprises before audit
  [15, 23, "batch"], [16, 23, "batch"], [17, 23, "batch"], [18, 23, "batch"],
  [19, 23, "batch"], [20, 23, "batch"], [21, 23, "batch"], [22, 23, "batch"],
  [23, 24, "pe"], [24, 25, "pe"],
  // W3: quality audit chain
  [26, 27, "pe"], [27, 28, "pe"], [28, 29, "pe"], [29, 30, "pe"],
  [30, 31, "pe"], [31, 32, "pe"], [31, 33, "pe"],
  // W4: prep chain
  [35, 37, "pe"], [36, 37, "pe"], [37, 38, "pe"], [37, 39, "pe"],
];

const WINDOW_COLORS: Record<string, string> = {
  W1: "#003A70",
  W2: "#C4281C",
  W3: "#1B7F4B",
  W4: "#5A5A72",
};

const STATUS_NODE_COLORS: Record<string, string> = {
  completed: "#1B7F4B",
  processing: "#003A70",
  ready: "#C5913E",
  pending: "#C3C6D1",
  blocked: "#C4281C",
};

export default function DependenciesPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const [selectedTask, setSelectedTask] = useState<TaskInstance | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function init() {
      const cytoscape = (await import("cytoscape")).default;
      const fcose = (await import("cytoscape-fcose")).default;
      cytoscape.use(fcose);

      if (!mounted || !containerRef.current) return;

      // Build nodes
      const nodes = TASK_INSTANCES.map((t) => ({
        data: {
          id: `t${t.id}`,
          label: `T${t.id}\n${t.name}`,
          window: t.window,
          status: t.status,
          color: STATUS_NODE_COLORS[t.status],
          borderColor: WINDOW_COLORS[t.window],
          size: Math.max(30, Math.min(60, t.enterpriseCount / 20)),
        },
      }));

      // Build edges
      const edges = DEPENDENCY_EDGES.map(([src, tgt, type]) => ({
        data: {
          id: `e${src}-${tgt}`,
          source: `t${src}`,
          target: `t${tgt}`,
          depType: type,
        },
      }));

      const cy = cytoscape({
        container: containerRef.current,
        elements: [...nodes, ...edges],
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)" as any,
              "text-wrap": "wrap" as any,
              "text-max-width": "80px" as any,
              "font-size": "9px" as any,
              "font-family": "Inter, Noto Sans SC, sans-serif" as any,
              "font-weight": 600 as any,
              "text-valign": "center" as any,
              "text-halign": "center" as any,
              "background-color": "data(color)" as any,
              "border-width": 2 as any,
              "border-color": "data(borderColor)" as any,
              color: "#fff" as any,
              "text-outline-color": "data(color)" as any,
              "text-outline-width": 1 as any,
              width: "data(size)" as any,
              height: "data(size)" as any,
              shape: "rectangle" as any,
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.5 as any,
              "line-color": "#C3C6D1" as any,
              "target-arrow-color": "#C3C6D1" as any,
              "target-arrow-shape": "triangle" as any,
              "curve-style": "bezier" as any,
              "arrow-scale": 0.8 as any,
            },
          },
          {
            selector: "edge[depType='batch']",
            style: {
              "line-style": "dashed" as any,
              "line-color": "#C4281C" as any,
              "target-arrow-color": "#C4281C" as any,
              width: 2 as any,
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-width": 3 as any,
              "border-color": "#C5913E" as any,
            },
          },
        ],
        layout: {
          name: "fcose",
          animate: false,
          quality: "proof",
          nodeDimensionsIncludeLabels: true,
          nodeRepulsion: () => 8000,
          idealEdgeLength: () => 80,
          edgeElasticity: () => 0.1,
          gravity: 0.3,
          gravityRange: 2.0,
          numIter: 5000,
          padding: 40,
        } as any,
      });

      cy.on("tap", "node", (evt: any) => {
        const taskId = parseInt(evt.target.id().replace("t", ""));
        const task = TASK_INSTANCES.find((t) => t.id === taskId);
        if (task) setSelectedTask(task);
      });

      cy.on("tap", (evt: any) => {
        if (evt.target === cy) setSelectedTask(null);
      });

      cyRef.current = cy;
      setLoaded(true);
    }

    init();
    return () => { mounted = false; cyRef.current?.destroy(); };
  }, []);

  return (
    <div style={{ background: "var(--color-surface)", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "var(--space-6) var(--space-8)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px" }}>WORKBENCH / DEPENDENCY GRAPH</div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", marginTop: 4 }}>任务依赖图</h1>
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)" }}>
            <button onClick={() => cyRef.current?.fit(undefined, 40)} style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, border: "none", cursor: "pointer" }}>
              适应画布
            </button>
            <Link href="/workbench" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>返回看板</Link>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", gap: 16, marginTop: 12, fontSize: "11px", color: "var(--color-text-secondary)" }}>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#003A70", marginRight: 4 }} />W1 采集期</span>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#C4281C", marginRight: 4 }} />W2 征期</span>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#1B7F4B", marginRight: 4 }} />W3 质检期</span>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#5A5A72", marginRight: 4 }} />W4 准备期</span>
          <span style={{ marginLeft: 16 }}>── 逐企业依赖</span>
          <span style={{ color: "#C4281C" }}>- - 批级依赖</span>
          <span style={{ marginLeft: 16 }}><span style={{ display: "inline-block", width: 10, height: 10, background: "#1B7F4B", marginRight: 4 }} />已完成</span>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#C5913E", marginRight: 4 }} />就绪</span>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#C3C6D1", marginRight: 4 }} />待启动</span>
        </div>
      </div>

      {/* Graph + Detail */}
      <div style={{ flex: 1, display: "flex", position: "relative" }}>
        {/* Cytoscape Canvas */}
        <div
          ref={containerRef}
          style={{
            flex: 1,
            background: "#0D1117",
            minHeight: "calc(100vh - 160px)",
          }}
        />

        {!loaded && (
          <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", color: "#5A5A72", fontSize: "14px" }}>
            加载依赖图...
          </div>
        )}

        {/* Selected Task Panel */}
        {selectedTask && (
          <div style={{ width: 340, background: "var(--color-surface-container-lowest)", borderLeft: "1px solid var(--color-surface-container)", padding: 20, overflowY: "auto" }}>
            <button onClick={() => setSelectedTask(null)} style={{ float: "right", background: "none", border: "none", fontSize: "16px", cursor: "pointer", color: "var(--color-text-secondary)" }}>x</button>

            <div style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", display: "inline-block", background: TIME_WINDOWS[selectedTask.window].bgColor, color: TIME_WINDOWS[selectedTask.window].color, marginBottom: 8 }}>
              {selectedTask.window} {TIME_WINDOWS[selectedTask.window].label}
            </div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 4 }}>
              T{selectedTask.id} {selectedTask.name}
            </h3>
            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: 16 }}>
              {AGENT_MAP[selectedTask.agentId]?.name} · {selectedTask.enterpriseCount}家 · {STATUS_STYLES[selectedTask.status].label}
            </div>

            {/* Upstream deps */}
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "1.5px", marginBottom: 6 }}>UPSTREAM</div>
            <div style={{ marginBottom: 16 }}>
              {DEPENDENCY_EDGES.filter(([, tgt]) => tgt === selectedTask.id).map(([src, , type]) => {
                const srcTask = TASK_INSTANCES.find((t) => t.id === src);
                return srcTask ? (
                  <div key={src} style={{ padding: "6px 10px", background: "var(--color-surface)", marginBottom: 2, fontSize: "12px", display: "flex", justifyContent: "space-between" }}>
                    <span>T{srcTask.id} {srcTask.name}</span>
                    <span style={{ fontSize: "10px", fontWeight: 700, padding: "1px 4px", background: type === "batch" ? "#FDECEB" : "#E8F0FE", color: type === "batch" ? "#C4281C" : "#003A70" }}>
                      {type === "batch" ? "批级" : "逐企业"}
                    </span>
                  </div>
                ) : null;
              })}
              {DEPENDENCY_EDGES.filter(([, tgt]) => tgt === selectedTask.id).length === 0 && (
                <div style={{ fontSize: "12px", color: "var(--color-text-tertiary)", fontStyle: "italic" }}>无上游依赖 (根任务)</div>
              )}
            </div>

            {/* Downstream deps */}
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "1.5px", marginBottom: 6 }}>DOWNSTREAM</div>
            <div>
              {DEPENDENCY_EDGES.filter(([src]) => src === selectedTask.id).map(([, tgt, type]) => {
                const tgtTask = TASK_INSTANCES.find((t) => t.id === tgt);
                return tgtTask ? (
                  <div key={tgt} style={{ padding: "6px 10px", background: "var(--color-surface)", marginBottom: 2, fontSize: "12px", display: "flex", justifyContent: "space-between" }}>
                    <span>T{tgtTask.id} {tgtTask.name}</span>
                    <span style={{ fontSize: "10px", fontWeight: 700, padding: "1px 4px", background: type === "batch" ? "#FDECEB" : "#E8F0FE", color: type === "batch" ? "#C4281C" : "#003A70" }}>
                      {type === "batch" ? "批级" : "逐企业"}
                    </span>
                  </div>
                ) : null;
              })}
              {DEPENDENCY_EDGES.filter(([src]) => src === selectedTask.id).length === 0 && (
                <div style={{ fontSize: "12px", color: "var(--color-text-tertiary)", fontStyle: "italic" }}>无下游依赖 (末端任务)</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
