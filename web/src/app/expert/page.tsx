"use client";

/* System A Dashboard — CogNebula Platform Overview
   Per OPTIMIZED_ARCHITECTURE_V2.md: Internal KG infrastructure dashboard.
   Shows KG health, pipeline status, and quality metrics at a glance. */

import { useState, useEffect } from "react";
import Link from "next/link";
import { getStats, getQuality, type KGStats, type KGQuality } from "../lib/kg-api";

export default function ExpertDashboardPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getQuality()])
      .then(([s, q]) => { setStats(s); setQuality(q); })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "#E6EDF3", marginBottom: 4 }}>
          System A 总览
        </h1>
        <p style={{ fontSize: "13px", color: "#8B949E" }}>
          CogNebula KG 基础设施健康状态 + 管线监控
        </p>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#3D1F1F", border: "1px solid #F85149", color: "#F85149", fontSize: "13px", marginBottom: 20 }}>
          KG API 连接失败: {error}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1px", background: "#30363D", marginBottom: 24 }}>
        <KPICard label="节点总数" value={stats ? (stats.total_nodes || 0).toLocaleString() : "..."} sub="KuzuDB + LanceDB" color="#58A6FF" />
        <KPICard label="边总数" value={stats ? (stats.total_edges || 0).toLocaleString() : "..."} sub="关系图谱" color="#58A6FF" />
        <KPICard label="边密度" value={stats ? (stats.total_nodes > 0 ? (stats.total_edges / stats.total_nodes).toFixed(3) : "0") : "..."} sub="edges / nodes" color="#D2A8FF" />
        <KPICard label="质量评分" value={quality ? `${(quality.quality_score || 0).toFixed(1)}%` : "..."} sub="综合质量" color={quality && quality.quality_score >= 80 ? "#3FB950" : "#D29922"} />
      </div>

      {/* Quick Access Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 24 }}>
        <QuickCard href="/expert/kg" title="知识图谱探索器" desc="交互式图谱可视化，Cytoscape.js fcose 布局。支持搜索、展开邻居、分层着色。" tag="CORE TOOL" tagColor="#58A6FF" />
        <QuickCard href="/expert/data-quality" title="数据质量仪表盘" desc="实时监控标题覆盖率、内容覆盖率、节点类型分布。连接 KG API /quality 端点。" tag="MONITORING" tagColor="#3FB950" />
        <QuickCard href="/expert/reasoning" title="推理链检查器" desc="Agent 推理过程可视化。显示 INPUT → RETRIEVAL → REASONING → VALIDATION → OUTPUT 各阶段置信度。" tag="DIAGNOSTIC" tagColor="#D2A8FF" />
        <QuickCard href="/expert/rules" title="合规规则调试器" desc="8 条规则的状态监控（active/warning/critical/deprecated），命中次数、最近命中时间。" tag="DIAGNOSTIC" tagColor="#D2A8FF" />
      </div>

      {/* System Status */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "11px", fontWeight: 700, color: "#58A6FF", letterSpacing: "2px", marginBottom: 12 }}>
          SYSTEM STATUS
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1px", background: "#30363D" }}>
          <StatusRow label="KG API (FastAPI :8400)" status="ok" detail="100.75.77.112 via Tailscale" />
          <StatusRow label="KuzuDB" status="warn" detail="Archived status — evaluate migration by 2026-09" />
          <StatusRow label="LanceDB (Vectors)" status="ok" detail="Semantic search operational" />
          <StatusRow label="Know-Arc Pipeline" status="ok" detail="Triple generation + expert review" />
          <StatusRow label="Edge Engine" status="ok" detail="SUPERSEDES edges, 107 last run" />
          <StatusRow label="CF Worker Proxy" status="pending" detail="Not yet deployed — mixed content issue" />
        </div>
      </div>

      {/* Architecture reminder */}
      <div style={{ padding: "16px 20px", background: "#161B22", border: "1px solid #30363D", borderLeft: "3px solid #58A6FF" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "#58A6FF", letterSpacing: "1.5px", marginBottom: 6 }}>
          ARCHITECTURE NOTE
        </div>
        <div style={{ fontSize: "13px", color: "#8B949E", lineHeight: 1.7 }}>
          System A (CogNebula) 是纯内部基础设施，不面向客户。KG 通过 CF Worker 代理为 System B (灵阙) 的 Agent 提供不可见的知识查询。
          客户看到的是「高准确率」，不是「知识图谱」。
        </div>
      </div>
    </div>
  );
}

function KPICard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div style={{ padding: "16px 20px", background: "#0D1117" }}>
      <div style={{ fontSize: "10px", fontWeight: 600, color: "#8B949E", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: 800, color, lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: "11px", color: "#484F58", marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function QuickCard({ href, title, desc, tag, tagColor }: { href: string; title: string; desc: string; tag: string; tagColor: string }) {
  return (
    <Link href={href} style={{ textDecoration: "none" }}>
      <div style={{
        padding: "20px",
        background: "#161B22",
        border: "1px solid #30363D",
        borderTop: `2px solid ${tagColor}`,
        transition: "border-color 0.15s",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: "#E6EDF3" }}>{title}</span>
          <span style={{ fontSize: "9px", fontWeight: 700, padding: "2px 8px", background: `${tagColor}20`, color: tagColor, letterSpacing: "1px" }}>{tag}</span>
        </div>
        <div style={{ fontSize: "12px", color: "#8B949E", lineHeight: 1.6 }}>{desc}</div>
      </div>
    </Link>
  );
}

function StatusRow({ label, status, detail }: { label: string; status: "ok" | "warn" | "pending" | "error"; detail: string }) {
  const colors = { ok: "#3FB950", warn: "#D29922", pending: "#8B949E", error: "#F85149" };
  const labels = { ok: "ONLINE", warn: "WARNING", pending: "PENDING", error: "ERROR" };
  return (
    <div style={{ padding: "12px 16px", background: "#0D1117", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: "13px", fontWeight: 600, color: "#E6EDF3" }}>{label}</div>
        <div style={{ fontSize: "11px", color: "#484F58", marginTop: 2 }}>{detail}</div>
      </div>
      <span style={{ fontSize: "9px", fontWeight: 700, padding: "2px 8px", color: colors[status], background: `${colors[status]}15`, letterSpacing: "1px" }}>
        {labels[status]}
      </span>
    </div>
  );
}
