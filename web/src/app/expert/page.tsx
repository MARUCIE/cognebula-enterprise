"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  getStats,
  getQuality,
  getHealth,
  getOntologyAudit,
  type KGStats,
  type KGQuality,
  type KGHealth,
  type OntologyAudit,
} from "../lib/kg-api";
import { CN, cnCard, cnLabel, cnValue, cnBadge } from "../lib/cognebula-theme";

export default function ExpertDashboardPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [health, setHealth] = useState<KGHealth | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);
  const [audit, setAudit] = useState<OntologyAudit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastProbed, setLastProbed] = useState<Date | null>(null);

  useEffect(() => {
    const fetchAll = () => {
      Promise.allSettled([getStats(), getQuality(), getHealth(), getOntologyAudit()])
        .then(([sR, qR, hR, aR]) => {
          if (sR.status === "fulfilled") setStats(sR.value);
          if (qR.status === "fulfilled") setQuality(qR.value);
          if (hR.status === "fulfilled") {
            setHealth(hR.value);
            setHealthErr(null);
          } else {
            setHealthErr(hR.reason?.message || "probe failed");
          }
          if (aR.status === "fulfilled") setAudit(aR.value);
          setLastProbed(new Date());
          // Surface KG-API-down only if stats AND health both fail
          if (sR.status === "rejected" && hR.status === "rejected") {
            setError("KG API 无法连接");
          } else {
            setError(null);
          }
        });
    };
    fetchAll();
    const id = setInterval(fetchAll, 30_000);
    return () => clearInterval(id);
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
          <div style={cnLabel}>发布门 (composite gate)</div>
          <div style={cnValue(audit ? (audit.verdict === "PASS" ? CN.green : CN.red) : CN.textMuted)}>
            {audit ? audit.verdict : "..."}
          </div>
          <div style={{ fontSize: 10, color: CN.textMuted, marginTop: 4, lineHeight: 1.5 }}>
            {quality ? (
              <>
                title <span style={{ color: quality.title_coverage >= 95 ? CN.green : CN.amber, fontWeight: 600 }}>{quality.title_coverage.toFixed(1)}%</span>
                {" · "}
                content <span style={{ color: quality.content_coverage >= 80 ? CN.green : CN.amber, fontWeight: 600 }}>{quality.content_coverage.toFixed(1)}%</span>
              </>
            ) : "..."}
            {audit ? <><br />rogue <span style={{ color: audit.rogue_in_prod.length === 0 ? CN.green : CN.red, fontWeight: 600 }}>{audit.rogue_in_prod.length}</span> · over Brooks <span style={{ color: audit.over_ceiling_by === 0 ? CN.green : CN.red, fontWeight: 600 }}>+{audit.over_ceiling_by}</span></> : null}
          </div>
        </div>
      </div>

      {/* System Status — wired to live /api/v1/health probe (every 30s) */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
          <h2 style={{ fontSize: 11, fontWeight: 700, color: CN.blue, letterSpacing: "2px" }}>
            系统状态 · live probe
          </h2>
          <span style={{ fontSize: 10, color: CN.textMuted }}>
            {lastProbed ? `last probed ${formatProbedAgo(lastProbed)}` : "probing..."}
          </span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <ProbedStatusRow
            label="KG API (FastAPI :8400)"
            ok={!!health && !healthErr}
            detail={health ? `${health.status} · 经 nginx /api/v1 同源代理` : (healthErr ?? "probing...")}
          />
          <ProbedStatusRow
            label="KuzuDB"
            ok={!!health?.kuzu}
            warn={!!health?.kuzu}
            detail={health ? `runtime ${health.kuzu ? "OK" : "DOWN"} · upstream archived 2025-10 (EOL 2026-09)` : "probing..."}
          />
          <ProbedStatusRow
            label="LanceDB (向量库)"
            ok={!!health?.lancedb}
            detail={health ? `runtime OK · ${health.lancedb_rows?.toLocaleString() ?? "?"} rows` : "probing..."}
          />
          <UnprobedStatusRow
            label="Know-Arc 管线"
            detail="无健康端点 · 三元组生成 + 专家审核 (上次写入 2026-04-28)"
          />
          <UnprobedStatusRow
            label="Edge Engine"
            detail="无健康端点 · SUPERSEDES 边关系 (上次写入 2026-04-28)"
          />
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

function ProbedStatusRow({ label, ok, warn, detail }: { label: string; ok: boolean; warn?: boolean; detail: string }) {
  const color = !ok ? CN.red : warn ? CN.amber : CN.green;
  const bg = !ok ? CN.redBg : warn ? CN.amberBg : CN.greenBg;
  const text = !ok ? "DOWN" : warn ? "RUNNING · EOL" : "在线";
  return (
    <div style={{ ...cnCard, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: CN.text }}>{label}</div>
        <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2 }}>{detail}</div>
      </div>
      <span style={cnBadge(color, bg)}>{text}</span>
    </div>
  );
}

function UnprobedStatusRow({ label, detail }: { label: string; detail: string }) {
  return (
    <div style={{ ...cnCard, display: "flex", justifyContent: "space-between", alignItems: "center", borderStyle: "dashed" }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: CN.textSecondary }}>{label}</div>
        <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2 }}>{detail}</div>
      </div>
      <span style={cnBadge(CN.textMuted, CN.bgElevated)}>未探测</span>
    </div>
  );
}

function formatProbedAgo(t: Date): string {
  const sec = Math.max(0, Math.floor((Date.now() - t.getTime()) / 1000));
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return t.toLocaleString();
}

