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

function CoverageBar({ label, value, target, desc }: { label: string; value: number; target: number; desc: string }) {
  const hit = value >= target;
  const color = hit ? CN.green : CN.amber;
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: CN.textSecondary, marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ color, fontVariantNumeric: "tabular-nums" }}>
          {value.toFixed(1)}% / {target}%
        </span>
      </div>
      <div style={{ height: 6, background: CN.border, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.min(value, 100)}%`, background: color, transition: "width 0.5s" }} />
      </div>
      <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4, lineHeight: 1.5 }}>
        {desc}
      </div>
    </div>
  );
}

/* Metric explanation data */
const METRIC_EXPLANATIONS: Record<string, { formula: string; meaning: string; threshold: string }> = {
  "节点总数": {
    formula: "SUM(COUNT(n) for each node table)",
    meaning: "KuzuDB 中所有节点表的节点总数。包括法规条款、知识单元、税率、会计科目等 74 张表。",
    threshold: "无固定阈值。数量越多表示知识图谱覆盖面越广。",
  },
  "边总数": {
    formula: "SUM(COUNT(e) for each edge table)",
    meaning: "所有关系边的总数。边表示节点间的语义关联，如 INTERPRETS（解释）、ISSUED_BY（发布）、REFERENCES_CLAUSE（引用条款）等。",
    threshold: "无固定阈值。边越多表示知识关联越丰富。",
  },
  "边密度": {
    formula: "total_edges / total_nodes",
    meaning: "平均每个节点拥有的边数。反映图谱的连通性和关联丰富度。密度越高说明节点之间的关系越丰富。",
    threshold: ">= 0.5 为 OK。当前 3.0+ 表示平均每个节点有 3 条关联，属于高质量水平。",
  },
  "标题覆盖率": {
    formula: "COUNT(nodes with title >= 2 chars) / total_nodes * 100%",
    meaning: "v4.1 本体 21 类节点表中，拥有有效标题（title/name/topic 字段 >= 2 字符）的节点占比。标题是节点的可读标识，没有标题的节点在搜索和展示时会显示为 ID 哈希。",
    threshold: ">= 95% 为 OK。当前 99.6% 表示仅极少数节点缺少标题。",
  },
  "内容覆盖率": {
    formula: "COUNT(nodes with content >= 20 chars) / total_nodes * 100%",
    meaning: "v4.1 本体 21 类节点表中，拥有有效内容（fullText/content/description 字段 >= 20 字符）的节点占比。内容是节点的核心信息，决定了 RAG 检索和知识问答的回答质量。",
    threshold: ">= 80% 为 OK。当前 31.2% 偏低，主要因为元数据节点（HSCode、Classification 等）本身只有编码无正文。",
  },
  "质量评分": {
    formula: "100 - (title_gap * 100) - (density_gap * 50)",
    meaning: "综合质量分。从 100 分起扣：标题覆盖率每低于 95% 目标扣 1 分（按差值百分比），边密度每低于 0.5 目标扣 0.5 分。",
    threshold: ">= 80 为 A，>= 60 为 B，< 60 为 C。当前 100 表示标题覆盖率和边密度均达标。",
  },
  "等级": {
    formula: "A: score >= 90 | B: score >= 70 | C: score < 70 | F: gate FAIL",
    meaning: "基于质量评分的等级划分。A 表示图谱质量优秀，所有核心指标达标。",
    threshold: "PASS gate 要求 score >= 60。",
  },
};

export default function DataQualityPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);

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

      {/* 3-Column: Chart + Coverage + Detail */}
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
              <CoverageBar
                label="标题覆盖率" value={quality.title_coverage || 0} target={95}
                desc="统计范围: v4.1 节点表 (21 张) | 检查字段: title / name / topic | 有效阈值: >= 2 字符"
              />
              <CoverageBar
                label="内容覆盖率" value={quality.content_coverage || 0} target={80}
                desc="统计范围: v4.1 节点表 (21 张) | 检查字段: fullText / content / description | 有效阈值: >= 20 字符"
              />
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
                  ].map((r) => {
                    const explanation = METRIC_EXPLANATIONS[r.m];
                    const isExpanded = expandedMetric === r.m;
                    return (
                      <tr key={r.m}
                        style={{ borderBottom: `1px solid ${CN.border}`, cursor: "pointer" }}
                        onClick={() => setExpandedMetric(isExpanded ? null : r.m)}
                      >
                        <td style={{ padding: "6px 0", color: CN.textSecondary }}>
                          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <span style={{ color: CN.textMuted, fontSize: 10 }}>{isExpanded ? "v" : ">"}</span>
                            {r.m}
                          </span>
                        </td>
                        <td style={{ padding: "6px 0", textAlign: "right", color: CN.text, fontVariantNumeric: "tabular-nums" }}>{r.v}</td>
                        <td style={{ padding: "6px 0", textAlign: "right" }}>
                          <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", color: r.ok ? CN.green : CN.amber, background: r.ok ? CN.greenBg : CN.amberBg }}>
                            {r.ok ? "OK" : "WARN"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Expanded Metric Explanation */}
      {expandedMetric && METRIC_EXPLANATIONS[expandedMetric] && (
        <div style={{
          ...cnCard, borderLeft: `3px solid ${CN.blue}`, marginBottom: 24,
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: CN.text }}>
              {expandedMetric} -- 计算说明
            </div>
            <button onClick={() => setExpandedMetric(null)}
              style={{ background: "none", border: "none", color: CN.textMuted, cursor: "pointer", fontSize: 16 }}>x</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "80px 1fr", gap: "12px 16px", fontSize: 13 }}>
            <span style={{ fontWeight: 700, color: CN.textMuted }}>公式</span>
            <code style={{ padding: "4px 10px", background: CN.bgElevated, borderRadius: 4, fontSize: 12, fontFamily: "'SF Mono', monospace", color: CN.text }}>
              {METRIC_EXPLANATIONS[expandedMetric].formula}
            </code>
            <span style={{ fontWeight: 700, color: CN.textMuted }}>含义</span>
            <span style={{ color: CN.textSecondary, lineHeight: 1.7 }}>
              {METRIC_EXPLANATIONS[expandedMetric].meaning}
            </span>
            <span style={{ fontWeight: 700, color: CN.textMuted }}>阈值</span>
            <span style={{ color: CN.textSecondary, lineHeight: 1.7 }}>
              {METRIC_EXPLANATIONS[expandedMetric].threshold}
            </span>
          </div>
        </div>
      )}

      {/* Data Source & Methodology */}
      <div style={{ ...cnCard, borderTop: `2px solid ${CN.blue}` }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 12 }}>
          数据来源与计算方法
        </div>
        <div style={{ fontSize: 12, color: CN.textSecondary, lineHeight: 1.8 }}>
          <p style={{ marginBottom: 12 }}>
            <strong>数据来源</strong>: 所有指标实时查询 KuzuDB 图数据库 (API: <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>GET /api/v1/quality</code>)。
            统计范围限定于 v4.1 本体的 21 张节点表 (TaxType, TaxIncentive, ComplianceRule, LegalDocument, LegalClause 等)，覆盖 L1-L4 四层。
          </p>
          <p style={{ marginBottom: 12 }}>
            <strong>边密度计算</strong>: 仅统计 v4.1 本体的 52 种边类型 (INTERPRETS, ISSUED_BY, REFERENCES_CLAUSE 等)。
            公式: <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>total_edges / total_nodes</code>。
            当前值 3.044 表示平均每个节点有 3 条语义关联。
          </p>
          <p style={{ marginBottom: 12 }}>
            <strong>质量评分</strong>: 满分 100，两项扣分: (1) 标题覆盖率每低于 95% 目标差值按比例扣分 (权重 100); (2) 边密度每低于 0.5 目标差值按比例扣分 (权重 50)。
            Gate 通过条件: score {">"}= 60。
          </p>
          <p style={{ marginBottom: 0 }}>
            <strong>内容覆盖率说明</strong>: 当前 31.2% 偏低属于结构性原因 -- KG 中有大量元数据节点 (HSCode 23K, Classification 28K, TaxClassificationCode 4K 等) 本身只有编码和名称，没有正文内容。
            法规类节点 (LegalClause 83K, LawOrRegulation 39K) 的内容覆盖率显著更高。提升整体覆盖率需要为元数据节点补充释义文本。
          </p>
        </div>
      </div>
    </div>
  );
}
