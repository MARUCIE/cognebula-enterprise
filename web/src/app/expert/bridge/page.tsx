"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getStats, getQuality, type KGStats, type KGQuality } from "../../lib/kg-api";
import { CN, cnCard, cnLabel, cnValue, cnBadge } from "../../lib/cognebula-theme";

export default function SystemBridgePage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [kgOk, setKgOk] = useState<boolean | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getQuality()])
      .then(([s, q]) => { setStats(s); setQuality(q); setKgOk(true); })
      .catch(() => setKgOk(false));
  }, []);

  return (
    <div style={{ padding: "24px 32px" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: CN.text, marginBottom: 4 }}>
          系统桥接
        </h1>
        <p style={{ fontSize: 13, color: CN.textSecondary }}>
          CogNebula (A) 与灵阙 (B) 之间的跨系统导航与数据流
        </p>
      </div>

      {/* Split View: System A | Data Flow | System B */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 240px 1fr", gap: 0, marginBottom: 24 }}>
        {/* System A Card */}
        <div style={{ ...cnCard, borderTop: `3px solid ${CN.blue}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, background: CN.blueBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 18, fontWeight: 900, color: CN.blue }}>A</span>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: CN.blue }}>CogNebula</div>
                <div style={{ fontSize: 11, fontFamily: "ui-monospace, 'JetBrains Mono', monospace", color: CN.green, fontWeight: 600 }}>hegui.io</div>
                <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 6px", borderRadius: 3, background: CN.greenBg, color: CN.green, letterSpacing: "0.5px" }}>LIVE</span>
              </div>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginTop: 2 }}>
                内部 KG 基础设施
              </div>
            </div>
          </div>

          {/* KPI */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: CN.border, marginBottom: 16 }}>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>节点</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: CN.blue }}>{stats ? `${(stats.total_nodes / 1000).toFixed(0)}K` : "..."}</div>
            </div>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>边</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: CN.blue }}>{stats ? `${(stats.total_edges / 1000).toFixed(0)}K` : "..."}</div>
            </div>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>质量</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: quality && (quality.quality_score || 0) >= 80 ? CN.green : CN.amber }}>
                {quality ? `${(quality.quality_score || 0).toFixed(1)}%` : "..."}
              </div>
            </div>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>API</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: kgOk ? CN.green : kgOk === false ? CN.red : CN.textMuted }}>
                {kgOk === null ? "..." : kgOk ? "OK" : "DOWN"}
              </div>
            </div>
          </div>

          {/* Quick Nav */}
          <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 8 }}>
            工具
          </div>
          {[
            { href: "/expert/kg", label: "知识图谱探索器", color: CN.blue },
            { href: "/expert/data-quality", label: "数据质量", color: CN.green },
            { href: "/expert/reasoning", label: "知识问答", color: CN.blue },
            { href: "/expert/rules", label: "合规规则调试器", color: CN.purple },
          ].map((item) => (
            <Link key={item.href} href={item.href} style={{
              display: "block", padding: "6px 10px", marginBottom: 2,
              color: CN.text, textDecoration: "none", fontSize: 12,
              background: "transparent", borderLeft: `2px solid ${item.color}`,
            }}>
              {item.label}
            </Link>
          ))}
        </div>

        {/* Center: Data Flow Arrows */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: "0 8px" }}>
          {/* A -> B */}
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: CN.blue, letterSpacing: "1px", marginBottom: 4 }}>KG 查询 API</div>
            <svg width="120" height="32" viewBox="0 0 120 32">
              <defs>
                <marker id="arrowR" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                  <path d="M0,0 L8,3 L0,6" fill={CN.blue} />
                </marker>
              </defs>
              <line x1="10" y1="16" x2="100" y2="16" stroke={CN.blue} strokeWidth="2" markerEnd="url(#arrowR)" strokeDasharray="6,3" />
            </svg>
            <div style={{ fontSize: 9, color: CN.textMuted }}>经 Pages Function + Tunnel</div>
          </div>

          <div style={{ width: 1, height: 24, background: CN.border }} />

          {/* B -> A */}
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: CN.green, letterSpacing: "1px", marginBottom: 4 }}>Agent 反馈</div>
            <svg width="120" height="32" viewBox="0 0 120 32">
              <defs>
                <marker id="arrowL" markerWidth="8" markerHeight="6" refX="0" refY="3" orient="auto">
                  <path d="M8,0 L0,3 L8,6" fill={CN.green} />
                </marker>
              </defs>
              <line x1="20" y1="16" x2="110" y2="16" stroke={CN.green} strokeWidth="2" markerStart="url(#arrowL)" strokeDasharray="6,3" />
            </svg>
            <div style={{ fontSize: 9, color: CN.textMuted }}>质量信号</div>
          </div>
        </div>

        {/* System B Card — Light theme styling to show contrast */}
        <div style={{
          padding: "16px 20px", border: `1px solid ${CN.border}`,
          background: "#F9F9F7", borderTop: "3px solid #003A70",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, background: "rgba(0,58,112,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 18, fontWeight: 900, color: "#003A70" }}>B</span>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: "#003A70" }}>灵阙</div>
                <div style={{ fontSize: 11, fontFamily: "ui-monospace, 'JetBrains Mono', monospace", color: CN.green, fontWeight: 600 }}>hegui.app</div>
                <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 6px", borderRadius: 3, background: CN.greenBg, color: CN.green, letterSpacing: "0.5px" }}>LIVE</span>
              </div>
              <div style={{ fontSize: 10, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px", marginTop: 2 }}>
                客户产品端
              </div>
            </div>
          </div>

          {/* Mock KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: "#E5E7EB", marginBottom: 16 }}>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>企业数</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#003A70" }}>999</div>
            </div>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>数字员工</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#003A70" }}>7</div>
            </div>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>任务数</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#1B7A4E" }}>41</div>
            </div>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>技能数</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#1B7A4E" }}>79</div>
            </div>
          </div>

          {/* Quick Nav */}
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 8 }}>
            工作台
          </div>
          {[
            { href: "/workbench/", label: "月度看板" },
            { href: "/workbench/agents/", label: "数字员工" },
            { href: "/workbench/batch/", label: "批量操作" },
            { href: "/workbench/calendar/", label: "日历视图" },
          ].map((item) => (
            <Link key={item.href} href={item.href} style={{
              display: "block", padding: "6px 10px", marginBottom: 2,
              color: "#1D1B19", textDecoration: "none", fontSize: 12,
              background: "transparent", borderLeft: "2px solid #003A70",
            }}>
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Unified Status Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1px", background: CN.border }}>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>KG API</span>
          <span style={cnBadge(kgOk === null ? CN.textMuted : kgOk ? CN.green : CN.red, kgOk === null ? CN.bgElevated : kgOk ? CN.greenBg : CN.redBg)}>{kgOk === null ? "探测中" : kgOk ? "在线" : "离线"}</span>
        </div>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>Pages Function</span>
          <span style={cnBadge(kgOk === null ? CN.textMuted : kgOk ? CN.green : CN.red, kgOk === null ? CN.bgElevated : kgOk ? CN.greenBg : CN.redBg)}>{kgOk === null ? "探测中" : kgOk ? "代理在线" : "代理离线"}</span>
        </div>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>灵阙前端 (hegui.app)</span>
          <span style={cnBadge(CN.textMuted, CN.bgElevated)}>外部 · 未跨域探测</span>
        </div>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>Agent 引擎</span>
          <span style={cnBadge(CN.textMuted, CN.bgElevated)}>外部 · 未跨域探测</span>
        </div>
      </div>
    </div>
  );
}
