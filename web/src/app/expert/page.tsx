"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getStats, getQuality, type KGStats, type KGQuality } from "../lib/kg-api";
import { CN, cnCard, cnLabel, cnValue, cnBadge } from "../lib/cognebula-theme";

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
    <div style={{ padding: "24px 32px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: CN.text, marginBottom: 4 }}>
          System A 总览
        </h1>
        <p style={{ fontSize: 13, color: CN.textSecondary }}>
          CogNebula KG 基础设施健康状态 + 管线监控
        </p>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: CN.redBg, border: `1px solid ${CN.red}`, borderRadius: 6, color: CN.red, fontSize: 13, marginBottom: 20 }}>
          KG API 连接失败: {error}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        <div style={cnCard}>
          <div style={cnLabel}>节点总数</div>
          <div style={cnValue(CN.blue)}>{stats ? (stats.total_nodes || 0).toLocaleString() : "..."}</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>KuzuDB + LanceDB</div>
        </div>
        <div style={cnCard}>
          <div style={cnLabel}>边总数</div>
          <div style={cnValue(CN.blue)}>{stats ? (stats.total_edges || 0).toLocaleString() : "..."}</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>关系图谱</div>
        </div>
        <div style={cnCard}>
          <div style={cnLabel}>边密度</div>
          <div style={cnValue(CN.purple)}>{stats ? (stats.total_nodes > 0 ? (stats.total_edges / stats.total_nodes).toFixed(3) : "0") : "..."}</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>边数 / 节点数</div>
        </div>
        <div style={cnCard}>
          <div style={cnLabel}>质量评分</div>
          <div style={cnValue(quality && (quality.quality_score || 0) >= 80 ? CN.green : CN.amber)}>
            {quality ? `${(quality.quality_score || 0).toFixed(1)}%` : "..."}
          </div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>综合质量</div>
        </div>
      </div>

      {/* Quick Access Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 24 }}>
        <QuickCard href="/expert/kg" title="知识图谱探索器" desc="基于 Cytoscape.js fcose 布局的交互式图谱可视化。支持搜索、展开邻居节点、分层着色。" tag="核心工具" tagColor={CN.blue} />
        <QuickCard href="/expert/data-quality" title="数据质量仪表盘" desc="实时监控标题覆盖率、内容覆盖率、节点类型分布。已对接 KG API /quality 接口。" tag="监控" tagColor={CN.green} />
        <QuickCard href="/expert/reasoning" title="推理链检查器" desc="Agent 推理过程可视化。展示 INPUT > RETRIEVAL > REASONING > VALIDATION > OUTPUT 各阶段置信度。" tag="诊断" tagColor={CN.purple} />
        <QuickCard href="/expert/rules" title="合规规则调试器" desc="8 条合规规则状态监控 (生效/预警/严重/废弃)、命中次数、最近触发日志。" tag="诊断" tagColor={CN.purple} />
      </div>

      {/* System Status */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 11, fontWeight: 700, color: CN.blue, letterSpacing: "2px", marginBottom: 12 }}>
          系统状态
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <StatusRow label="KG API (FastAPI :8400)" status="ok" detail="100.75.77.112 经 Tailscale 连接" />
          <StatusRow label="KuzuDB" status="warn" detail="已归档 -- 计划 2026-09 前评估迁移" />
          <StatusRow label="LanceDB (向量库)" status="ok" detail="语义搜索运行中" />
          <StatusRow label="Know-Arc 管线" status="ok" detail="三元组生成 + 专家审核" />
          <StatusRow label="Edge Engine" status="ok" detail="SUPERSEDES 边关系，上次运行 107 条" />
          <StatusRow label="CF Worker 代理" status="pending" detail="尚未部署" />
        </div>
      </div>

      {/* Cross-System Link */}
      <div style={{ ...cnCard, borderLeft: `3px solid ${CN.blue}` }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: CN.blue, letterSpacing: "1.5px", marginBottom: 6 }}>
          架构说明
        </div>
        <div style={{ fontSize: 13, color: CN.textSecondary, lineHeight: 1.7 }}>
          System A (CogNebula) 仅作为内部基础设施。KG 通过 CF Worker 代理为 System B (灵阙) 的 Agent 提供不可见的知识查询层。
          客户看到的是&quot;高准确率&quot;，而非&quot;知识图谱&quot;。
        </div>
        <Link href="/expert/bridge" style={{ display: "inline-block", marginTop: 12, padding: "6px 16px", background: CN.blueBg, color: CN.blue, textDecoration: "none", fontSize: 12, fontWeight: 600, borderRadius: 6, border: `1px solid ${CN.border}` }}>
          查看系统桥接 &rarr;
        </Link>
      </div>
    </div>
  );
}

function QuickCard({ href, title, desc, tag, tagColor }: { href: string; title: string; desc: string; tag: string; tagColor: string }) {
  return (
    <Link href={href} style={{ textDecoration: "none" }}>
      <div style={{
        ...cnCard, borderTop: `2px solid ${tagColor}`,
        transition: "border-color 0.15s",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: CN.text }}>{title}</span>
          <span style={cnBadge(tagColor, `${tagColor}15`)}>{tag}</span>
        </div>
        <div style={{ fontSize: 12, color: CN.textSecondary, lineHeight: 1.6 }}>{desc}</div>
      </div>
    </Link>
  );
}

function StatusRow({ label, status, detail }: { label: string; status: "ok" | "warn" | "pending" | "error"; detail: string }) {
  const colors = { ok: CN.green, warn: CN.amber, pending: CN.textMuted, error: CN.red };
  const bgs = { ok: CN.greenBg, warn: CN.amberBg, pending: CN.bgElevated, error: CN.redBg };
  const labels = { ok: "在线", warn: "警告", pending: "待部署", error: "错误" };
  return (
    <div style={{ ...cnCard, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: CN.text }}>{label}</div>
        <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2 }}>{detail}</div>
      </div>
      <span style={cnBadge(colors[status], bgs[status])}>{labels[status]}</span>
    </div>
  );
}
