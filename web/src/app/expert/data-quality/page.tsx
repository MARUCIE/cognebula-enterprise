"use client";

import { useState, useEffect } from "react";
import { getStats, getQuality, type KGStats, type KGQuality } from "../../lib/kg-api";
import { CN, cnCard, cnLabel, cnValue } from "../../lib/cognebula-theme";

function KPI({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div style={cnCard}>
      <div style={cnLabel}>{label}</div>
      <div style={cnValue(color)}>{value}</div>
      <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function CoverageBar({ label, value, target }: { label: string; value: number; target: number }) {
  const hit = value >= target;
  const color = hit ? CN.green : CN.amber;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: CN.textSecondary, marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ color, fontVariantNumeric: "tabular-nums" }}>
          {value.toFixed(1)}% / {target}%
        </span>
      </div>
      <div style={{ height: 6, background: CN.border, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.min(value, 100)}%`, background: color, transition: "width 0.5s" }} />
      </div>
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
      .catch(() => setError("KG API 无法连接 (请检查 Tailscale)"));
  }, []);

  const topTypes = stats
    ? Object.entries(stats.nodes_by_type).sort((a, b) => b[1] - a[1]).slice(0, 15)
    : [];

  const gradeColor = (score: number) =>
    score >= 80 ? CN.green : score >= 60 ? CN.amber : CN.red;

  return (
    <div style={{ padding: "24px 32px" }}>
      {error && (
        <div style={{ padding: "10px 16px", background: CN.redBg, color: CN.red, fontSize: 13, marginBottom: 16, border: `1px solid ${CN.border}` }}>
          {error}
        </div>
      )}

      {/* KPI Strip — 6 metrics full width */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "1px", background: CN.border, marginBottom: 24 }}>
        <KPI label="节点总数" value={stats ? `${(stats.total_nodes / 1000).toFixed(1)}K` : "..."} sub={`${stats?.node_tables || 0} 张表`} color={CN.blue} />
        <KPI label="边总数" value={stats ? `${(stats.total_edges / 1000).toFixed(1)}K` : "..."} sub={`${stats?.rel_tables || 0} 种关系`} color={CN.blue} />
        <KPI label="边密度" value={stats ? (stats.total_nodes > 0 ? (stats.total_edges / stats.total_nodes).toFixed(3) : "0") : "..."} sub="边数 / 节点数" color={CN.purple} />
        <KPI label="标题覆盖率" value={quality ? `${(quality.title_coverage || 0).toFixed(1)}%` : "..."} sub="目标 >= 95%" color={quality && (quality.title_coverage || 0) >= 95 ? CN.green : CN.amber} />
        <KPI label="内容覆盖率" value={quality ? `${(quality.content_coverage || 0).toFixed(1)}%` : "..."} sub="目标 >= 80%" color={quality && (quality.content_coverage || 0) >= 80 ? CN.green : CN.amber} />
        <KPI label="质量评分" value={quality ? `${quality.quality_score || 0}` : "..."} sub={quality ? `等级 ${quality.grade || "--"}` : "--"} color={quality ? gradeColor(quality.quality_score || 0) : CN.textMuted} />
      </div>

      {/* 2-Column: Bar Chart + Coverage */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Left: Node Type Distribution */}
        <div style={{ ...cnCard }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 14 }}>
            节点类型分布 (TOP-15)
          </div>
          {topTypes.map(([type, count]) => {
            const maxCount = topTypes[0]?.[1] || 1;
            const pct = ((count as number) / (maxCount as number)) * 100;
            return (
              <div key={type} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: CN.textSecondary, minWidth: 180, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{type}</span>
                <div style={{ flex: 1, height: 14, background: CN.border, borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${pct}%`, background: CN.blue, transition: "width 0.5s" }} />
                </div>
                <span style={{ fontSize: 11, color: CN.text, minWidth: 60, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {(count as number).toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>

        {/* Right: Coverage + Quality Breakdown */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {quality && (
            <div style={cnCard}>
              <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 14 }}>
                覆盖率指标
              </div>
              <CoverageBar label="标题覆盖率" value={quality.title_coverage || 0} target={95} />
              <CoverageBar label="内容覆盖率" value={quality.content_coverage || 0} target={80} />
            </div>
          )}

          {quality && (
            <div style={cnCard}>
              <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 14 }}>
                质量分解
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${CN.border}` }}>
                    <th style={{ padding: "6px 0", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>指标</th>
                    <th style={{ padding: "6px 0", textAlign: "right", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>数值</th>
                    <th style={{ padding: "6px 0", textAlign: "right", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { m: "质量评分", v: `${quality.quality_score || 0}`, ok: (quality.quality_score || 0) >= 80 },
                    { m: "等级", v: quality.grade || "--", ok: quality.grade === "A" || quality.grade === "B" },
                    { m: "边密度", v: (quality.edge_density || 0).toFixed(3), ok: (quality.edge_density || 0) >= 0.5 },
                    { m: "标题覆盖率", v: `${(quality.title_coverage || 0).toFixed(1)}%`, ok: (quality.title_coverage || 0) >= 95 },
                    { m: "内容覆盖率", v: `${(quality.content_coverage || 0).toFixed(1)}%`, ok: (quality.content_coverage || 0) >= 80 },
                  ].map((r) => (
                    <tr key={r.m} style={{ borderBottom: `1px solid ${CN.border}` }}>
                      <td style={{ padding: "6px 0", color: CN.textSecondary }}>{r.m}</td>
                      <td style={{ padding: "6px 0", textAlign: "right", color: CN.text, fontVariantNumeric: "tabular-nums" }}>{r.v}</td>
                      <td style={{ padding: "6px 0", textAlign: "right" }}>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", color: r.ok ? CN.green : CN.amber, background: r.ok ? CN.greenBg : CN.amberBg }}>
                          {r.ok ? "OK" : "WARN"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
