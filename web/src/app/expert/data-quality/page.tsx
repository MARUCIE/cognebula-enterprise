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
      <div style={{ height: 6, background: CN.bgElevated, overflow: "hidden" }}>
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
      .catch(() => setError("KG API unreachable (check Tailscale)"));
  }, []);

  const topTypes = stats
    ? Object.entries(stats.nodes_by_type).sort((a, b) => b[1] - a[1]).slice(0, 15)
    : [];

  const gradeColor = (score: number) =>
    score >= 80 ? CN.green : score >= 60 ? CN.amber : CN.red;

  return (
    <div style={{ padding: "20px 24px" }}>
      {error && (
        <div style={{ padding: "10px 16px", background: CN.redBg, color: CN.red, fontSize: 13, marginBottom: 16, border: `1px solid ${CN.border}` }}>
          {error}
        </div>
      )}

      {/* KPI Strip — 6 metrics full width */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "1px", background: CN.border, marginBottom: 24 }}>
        <KPI label="Total Nodes" value={stats ? `${(stats.total_nodes / 1000).toFixed(1)}K` : "..."} sub={`${stats?.node_tables || 0} tables`} color={CN.blue} />
        <KPI label="Total Edges" value={stats ? `${(stats.total_edges / 1000).toFixed(1)}K` : "..."} sub={`${stats?.rel_tables || 0} relations`} color={CN.blue} />
        <KPI label="Edge Density" value={stats ? (stats.total_nodes > 0 ? (stats.total_edges / stats.total_nodes).toFixed(3) : "0") : "..."} sub="edges / nodes" color={CN.purple} />
        <KPI label="Title Coverage" value={quality ? `${quality.title_coverage.toFixed(1)}%` : "..."} sub="target >= 95%" color={quality && quality.title_coverage >= 95 ? CN.green : CN.amber} />
        <KPI label="Content Coverage" value={quality ? `${quality.content_coverage.toFixed(1)}%` : "..."} sub="target >= 80%" color={quality && quality.content_coverage >= 80 ? CN.green : CN.amber} />
        <KPI label="Quality Score" value={quality ? `${quality.quality_score}` : "..."} sub={quality ? `Grade ${quality.grade}` : "--"} color={quality ? gradeColor(quality.quality_score) : CN.textMuted} />
      </div>

      {/* 2-Column: Bar Chart + Coverage */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Left: Node Type Distribution */}
        <div style={{ ...cnCard }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 14 }}>
            Node Type Distribution (TOP-15)
          </div>
          {topTypes.map(([type, count]) => {
            const maxCount = topTypes[0]?.[1] || 1;
            const pct = ((count as number) / (maxCount as number)) * 100;
            return (
              <div key={type} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: CN.textSecondary, minWidth: 140, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{type}</span>
                <div style={{ flex: 1, height: 14, background: CN.bgElevated, overflow: "hidden" }}>
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
                Coverage Metrics
              </div>
              <CoverageBar label="Title Coverage" value={quality.title_coverage} target={95} />
              <CoverageBar label="Content Coverage" value={quality.content_coverage} target={80} />
            </div>
          )}

          {quality && (
            <div style={cnCard}>
              <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 14 }}>
                Quality Breakdown
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${CN.border}` }}>
                    <th style={{ padding: "6px 0", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>Metric</th>
                    <th style={{ padding: "6px 0", textAlign: "right", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>Value</th>
                    <th style={{ padding: "6px 0", textAlign: "right", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { m: "Quality Score", v: `${quality.quality_score}`, ok: quality.quality_score >= 80 },
                    { m: "Grade", v: quality.grade, ok: quality.grade === "A" || quality.grade === "B" },
                    { m: "Edge Density", v: quality.edge_density.toFixed(3), ok: quality.edge_density >= 0.5 },
                    { m: "Title Coverage", v: `${quality.title_coverage.toFixed(1)}%`, ok: quality.title_coverage >= 95 },
                    { m: "Content Coverage", v: `${quality.content_coverage.toFixed(1)}%`, ok: quality.content_coverage >= 80 },
                  ].map((r) => (
                    <tr key={r.m} style={{ borderBottom: `1px solid ${CN.bgElevated}` }}>
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
