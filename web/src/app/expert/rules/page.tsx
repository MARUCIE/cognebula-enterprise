"use client";

import { useState } from "react";
import { CN, cnCard, cnBadge, cnInput } from "../../lib/cognebula-theme";

interface Rule {
  id: string;
  name: string;
  condition: string;
  status: "active" | "warning" | "critical" | "deprecated";
  hitCount: number;
  lastHit: string;
  logic?: string;
  recentHits?: { enterprise: string; result: string; time: string }[];
}

const RULES: Rule[] = [
  {
    id: "CR-001", name: "增值税一般纳税人认定",
    condition: "年应税销售额 > 500 万元",
    status: "active", hitCount: 3842, lastHit: "2024-11-24",
    logic: "IF annual_taxable_sales > 5_000_000 THEN classify AS general_taxpayer",
    recentHits: [
      { enterprise: "杭州明达", result: "命中", time: "2024-11-24 10:42" },
      { enterprise: "苏州微创", result: "命中", time: "2024-11-24 09:15" },
      { enterprise: "南京恒达", result: "命中", time: "2024-11-23 16:30" },
    ],
  },
  {
    id: "CR-002", name: "研发费用加计扣除",
    condition: "研发支出占比 > 3% 且高新技术认证有效",
    status: "active", hitCount: 1256, lastHit: "2024-11-23",
    logic: "IF rd_spend_ratio > 0.03 AND hightech_cert.valid THEN allow_super_deduction(200%)",
    recentHits: [
      { enterprise: "北京 AI 实验室", result: "命中", time: "2024-11-23 14:20" },
      { enterprise: "深圳机器人科技", result: "未命中", time: "2024-11-22 11:00" },
    ],
  },
  {
    id: "CR-003", name: "关联方交易预警",
    condition: "关联方交易占比 > 30% 或定价偏离 > 20%",
    status: "warning", hitCount: 89, lastHit: "2024-11-22",
    logic: "IF related_party_ratio > 0.30 OR abs(price_deviation) > 0.20 THEN alert(WARNING)",
  },
  {
    id: "CR-004", name: "存货周转异常",
    condition: "存货周转天数 > 行业均值 x 1.5",
    status: "active", hitCount: 234, lastHit: "2024-11-21",
  },
  {
    id: "CR-005", name: "现金流异常",
    condition: "经营性现金流 < 净利润 x 0.5 连续 2 个季度",
    status: "critical", hitCount: 12, lastHit: "2024-11-24",
    logic: "IF operating_cf < net_income * 0.5 FOR consecutive_quarters >= 2 THEN alert(CRITICAL)",
    recentHits: [
      { enterprise: "中科电子", result: "命中", time: "2024-11-24 09:15" },
    ],
  },
  {
    id: "CR-006", name: "进项增值税抵扣合规",
    condition: "增值税专用发票有效且用途合规",
    status: "active", hitCount: 8921, lastHit: "2024-11-24",
  },
  {
    id: "CR-007", name: "跨境代扣代缴税",
    condition: "单笔境外付款 > 5 万美元且非协定国",
    status: "active", hitCount: 45, lastHit: "2024-11-20",
  },
  {
    id: "CR-008", name: "印花税计算规则",
    condition: "合同金额 > 0 且属于应税凭证类型",
    status: "deprecated", hitCount: 0, lastHit: "--",
  },
];

const STATUS_CONFIG = {
  active: { label: "生效", color: CN.green, bg: CN.greenBg },
  warning: { label: "预警", color: CN.amber, bg: CN.amberBg },
  critical: { label: "严重", color: CN.red, bg: CN.redBg },
  deprecated: { label: "废弃", color: CN.textMuted, bg: CN.bgElevated },
} as const;

type StatusFilter = "all" | "active" | "warning" | "critical" | "deprecated";

export default function RulesPage() {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = RULES.filter((r) => {
    if (filter !== "all" && r.status !== filter) return false;
    if (search && !r.name.toLowerCase().includes(search.toLowerCase()) && !r.condition.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    all: RULES.length,
    active: RULES.filter((r) => r.status === "active").length,
    warning: RULES.filter((r) => r.status === "warning").length,
    critical: RULES.filter((r) => r.status === "critical").length,
    deprecated: RULES.filter((r) => r.status === "deprecated").length,
  };

  return (
    <div style={{ padding: "24px 32px" }}>
      {/* Filter Bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        {(["all", "active", "warning", "critical", "deprecated"] as StatusFilter[]).map((f) => {
          const active = filter === f;
          const cfg = f === "all" ? { label: "全部", color: CN.blue, bg: CN.blueBg } : STATUS_CONFIG[f];
          return (
            <button key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "6px 14px", fontSize: 11, fontWeight: 700, letterSpacing: "0.5px",
                color: active ? cfg.color : CN.textMuted,
                background: active ? cfg.bg : "transparent",
                border: `1px solid ${active ? cfg.color : CN.border}`,
                cursor: "pointer",
              }}
            >
              {cfg.label} ({counts[f]})
            </button>
          );
        })}
        <div style={{ marginLeft: "auto" }}>
          <input
            type="text" placeholder="搜索规则..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            style={{ ...cnInput, width: 260 }}
          />
        </div>
      </div>

      {/* Rules Table */}
      <div style={{ ...cnCard, padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${CN.border}` }}>
              {["ID", "规则名称", "触发条件", "状态", "命中次数", "最近命中"].map((h) => (
                <th key={h} style={{
                  padding: "10px 14px", textAlign: "left", fontSize: 10, fontWeight: 700,
                  color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px",
                  background: CN.bgElevated,
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const s = STATUS_CONFIG[r.status];
              const isExpanded = expanded === r.id;
              return (
                <tr key={r.id} style={{ cursor: "pointer" }}
                  onClick={() => setExpanded(isExpanded ? null : r.id)}
                >
                  <td style={{ padding: "10px 14px", color: CN.textMuted, fontSize: 11, fontFamily: "monospace", borderBottom: `1px solid ${CN.bgElevated}` }}>{r.id}</td>
                  <td style={{ padding: "10px 14px", color: CN.text, fontWeight: 600, borderBottom: `1px solid ${CN.bgElevated}` }}>{r.name}</td>
                  <td style={{ padding: "10px 14px", color: CN.textSecondary, fontSize: 12, borderBottom: `1px solid ${CN.bgElevated}` }}>{r.condition}</td>
                  <td style={{ padding: "10px 14px", borderBottom: `1px solid ${CN.bgElevated}` }}>
                    <span style={cnBadge(s.color, s.bg)}>{s.label}</span>
                  </td>
                  <td style={{ padding: "10px 14px", color: CN.text, fontVariantNumeric: "tabular-nums", borderBottom: `1px solid ${CN.bgElevated}` }}>
                    {r.hitCount.toLocaleString()}
                  </td>
                  <td style={{ padding: "10px 14px", color: CN.textMuted, fontSize: 12, borderBottom: `1px solid ${CN.bgElevated}` }}>{r.lastHit}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Expanded Detail Panel */}
      {expanded && (() => {
        const rule = RULES.find((r) => r.id === expanded);
        if (!rule) return null;
        const s = STATUS_CONFIG[rule.status];
        return (
          <div style={{ ...cnCard, marginTop: 16, borderTop: `2px solid ${s.color}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: CN.text }}>{rule.name}</span>
              <span style={cnBadge(s.color, s.bg)}>{s.label}</span>
              <span style={{ marginLeft: "auto", fontSize: 11, color: CN.textMuted }}>ID: {rule.id}</span>
            </div>

            {rule.logic && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>规则逻辑</div>
                <pre style={{
                  padding: "12px 16px", background: CN.bgElevated, border: `1px solid ${CN.border}`,
                  borderRadius: 6, color: CN.text, fontSize: 12, fontFamily: "'SF Mono', monospace",
                  overflow: "auto", whiteSpace: "pre-wrap",
                }}>
                  {rule.logic}
                </pre>
              </div>
            )}

            {rule.recentHits && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>最近命中</div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${CN.border}` }}>
                      <th style={{ padding: "6px 0", textAlign: "left", color: CN.textMuted, fontSize: 10, fontWeight: 700 }}>企业</th>
                      <th style={{ padding: "6px 0", textAlign: "left", color: CN.textMuted, fontSize: 10, fontWeight: 700 }}>结果</th>
                      <th style={{ padding: "6px 0", textAlign: "left", color: CN.textMuted, fontSize: 10, fontWeight: 700 }}>时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rule.recentHits.map((h, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${CN.bgElevated}` }}>
                        <td style={{ padding: "6px 0", color: CN.text }}>{h.enterprise}</td>
                        <td style={{ padding: "6px 0" }}>
                          <span style={cnBadge(h.result === "命中" ? CN.green : CN.red, h.result === "命中" ? CN.greenBg : CN.redBg)}>
                            {h.result}
                          </span>
                        </td>
                        <td style={{ padding: "6px 0", color: CN.textMuted, fontFamily: "monospace" }}>{h.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
