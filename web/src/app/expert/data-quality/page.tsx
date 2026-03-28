"use client";

import { useState, useEffect } from "react";
import { getStats, getQuality, type KGStats, type KGQuality } from "../../lib/kg-api";

function MetricCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div style={{ background: "#161B22", borderRadius: 8, border: "1px solid #30363D", padding: "16px 20px" }}>
      <div style={{ fontSize: 11, color: "#8B949E", textTransform: "uppercase", letterSpacing: "0.05em", fontFamily: "'SF Mono', monospace" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color, fontFamily: "'SF Mono', monospace", marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: 11, color: "#484F58", marginTop: 2 }}>{sub}</div>
    </div>
  );
}

export default function DataQualityPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getQuality()])
      .then(([s, q]) => { setStats(s); setQuality(q); })
      .catch(() => setError("无法连接 KG 服务 (确保 Tailscale 已连接)"));
  }, []);

  const topTypes = stats
    ? Object.entries(stats.nodes_by_type).sort((a, b) => b[1] - a[1]).slice(0, 15)
    : [];

  return (
    <div style={{ height: "calc(100vh - var(--topbar-height))", background: "#0D1117", overflow: "auto" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "24px 32px" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#C9D1D9", marginBottom: 4, fontFamily: "'SF Mono', monospace" }}>
          数据质量审计
        </h2>
        <p style={{ fontSize: 13, color: "#8B949E", marginBottom: 24 }}>
          实时监控知识图谱的数据覆盖率、边密度和内容质量
        </p>

        {error && (
          <div style={{ padding: "12px 16px", background: "#3D1F1F", color: "#F85149", borderRadius: 6, marginBottom: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* KPI cards */}
        <div className="grid grid-cols-4 gap-4" style={{ marginBottom: 24 }}>
          <MetricCard
            label="总节点"
            value={stats ? `${(stats.total_nodes / 1000).toFixed(1)}K` : "--"}
            sub={`${stats?.node_tables || 0} 张表`}
            color="#58A6FF"
          />
          <MetricCard
            label="总边数"
            value={stats ? `${(stats.total_edges / 1000).toFixed(1)}K` : "--"}
            sub={`${stats?.rel_tables || 0} 种关系`}
            color="#3FB950"
          />
          <MetricCard
            label="边密度"
            value={quality ? quality.edge_density.toFixed(2) : "--"}
            sub={`目标 ≥ 0.50`}
            color={quality && quality.edge_density >= 0.5 ? "#3FB950" : "#D29922"}
          />
          <MetricCard
            label="质量评分"
            value={quality ? `${quality.quality_score}` : "--"}
            sub={quality ? `等级 ${quality.grade}` : "--"}
            color={quality && quality.quality_score >= 80 ? "#3FB950" : quality && quality.quality_score >= 60 ? "#D29922" : "#F85149"}
          />
        </div>

        {/* Coverage bars */}
        {quality && (
          <div style={{ background: "#161B22", borderRadius: 8, border: "1px solid #30363D", padding: "16px 20px", marginBottom: 24 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: "#C9D1D9", marginBottom: 12 }}>覆盖率指标</h3>
            {[
              { label: "标题覆盖率", value: quality.title_coverage, target: 95 },
              { label: "内容覆盖率", value: quality.content_coverage, target: 80 },
            ].map((m) => (
              <div key={m.label} style={{ marginBottom: 12 }}>
                <div className="flex justify-between" style={{ fontSize: 12, color: "#8B949E", marginBottom: 4 }}>
                  <span>{m.label}</span>
                  <span style={{ color: m.value >= m.target ? "#3FB950" : "#D29922" }}>{m.value.toFixed(1)}% (目标 {m.target}%)</span>
                </div>
                <div style={{ height: 6, background: "#21262D", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.min(m.value, 100)}%`, background: m.value >= m.target ? "#238636" : "#9E6A03", borderRadius: 3, transition: "width 0.5s" }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Node type distribution */}
        <div style={{ background: "#161B22", borderRadius: 8, border: "1px solid #30363D", padding: "16px 20px" }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: "#C9D1D9", marginBottom: 12 }}>节点类型分布 (TOP-15)</h3>
          {topTypes.map(([type, count]) => {
            const maxCount = topTypes[0]?.[1] || 1;
            const pct = ((count as number) / (maxCount as number)) * 100;
            return (
              <div key={type} className="flex items-center gap-3" style={{ marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: "#8B949E", fontFamily: "'SF Mono', monospace", minWidth: 160, textAlign: "right" }}>{type}</span>
                <div style={{ flex: 1, height: 14, background: "#21262D", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${pct}%`, background: "#1F6FEB", borderRadius: 3 }} />
                </div>
                <span style={{ fontSize: 11, color: "#C9D1D9", fontFamily: "'SF Mono', monospace", minWidth: 60, textAlign: "right" }}>
                  {(count as number).toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
