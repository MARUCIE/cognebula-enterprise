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
    id: "CR-001", name: "VAT General Taxpayer Recognition",
    condition: "Annual taxable sales > 5M CNY",
    status: "active", hitCount: 3842, lastHit: "2024-11-24",
    logic: "IF annual_taxable_sales > 5_000_000 THEN classify AS general_taxpayer",
    recentHits: [
      { enterprise: "Hangzhou Mingda", result: "MATCH", time: "2024-11-24 10:42" },
      { enterprise: "Suzhou Weichuang", result: "MATCH", time: "2024-11-24 09:15" },
      { enterprise: "Nanjing Hengda", result: "MATCH", time: "2024-11-23 16:30" },
    ],
  },
  {
    id: "CR-002", name: "R&D Expense Super Deduction",
    condition: "R&D spend ratio > 3% AND high-tech cert valid",
    status: "active", hitCount: 1256, lastHit: "2024-11-23",
    logic: "IF rd_spend_ratio > 0.03 AND hightech_cert.valid THEN allow_super_deduction(200%)",
    recentHits: [
      { enterprise: "Beijing AI Lab", result: "MATCH", time: "2024-11-23 14:20" },
      { enterprise: "Shenzhen Robotics", result: "NO_MATCH", time: "2024-11-22 11:00" },
    ],
  },
  {
    id: "CR-003", name: "Related Party Transaction Alert",
    condition: "Related party tx ratio > 30% OR pricing deviation > 20%",
    status: "warning", hitCount: 89, lastHit: "2024-11-22",
    logic: "IF related_party_ratio > 0.30 OR abs(price_deviation) > 0.20 THEN alert(WARNING)",
  },
  {
    id: "CR-004", name: "Inventory Turnover Anomaly",
    condition: "Inventory turnover days > industry avg x 1.5",
    status: "active", hitCount: 234, lastHit: "2024-11-21",
  },
  {
    id: "CR-005", name: "Cash Flow Anomaly",
    condition: "Operating CF < net income x 0.5 for 2 consecutive quarters",
    status: "critical", hitCount: 12, lastHit: "2024-11-24",
    logic: "IF operating_cf < net_income * 0.5 FOR consecutive_quarters >= 2 THEN alert(CRITICAL)",
    recentHits: [
      { enterprise: "Zhongke Electronics", result: "MATCH", time: "2024-11-24 09:15" },
    ],
  },
  {
    id: "CR-006", name: "Input VAT Deduction Compliance",
    condition: "Valid VAT special invoice AND compliant purpose",
    status: "active", hitCount: 8921, lastHit: "2024-11-24",
  },
  {
    id: "CR-007", name: "Cross-border Withholding Tax",
    condition: "Overseas payment > 50K USD per transaction AND non-treaty country",
    status: "active", hitCount: 45, lastHit: "2024-11-20",
  },
  {
    id: "CR-008", name: "Stamp Duty Calculation Rule",
    condition: "Contract amount > 0 AND belongs to taxable document type",
    status: "deprecated", hitCount: 0, lastHit: "--",
  },
];

const STATUS_CONFIG = {
  active: { label: "ACTIVE", color: CN.green, bg: CN.greenBg },
  warning: { label: "WARNING", color: CN.amber, bg: CN.amberBg },
  critical: { label: "CRITICAL", color: CN.red, bg: CN.redBg },
  deprecated: { label: "DEPRECATED", color: CN.textMuted, bg: CN.bgElevated },
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
    <div style={{ padding: "20px 24px" }}>
      {/* Filter Bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        {(["all", "active", "warning", "critical", "deprecated"] as StatusFilter[]).map((f) => {
          const active = filter === f;
          const cfg = f === "all" ? { label: "ALL", color: CN.blue, bg: CN.blueBg } : STATUS_CONFIG[f];
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
            type="text" placeholder="Search rules..."
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
              {["ID", "Rule Name", "Trigger Condition", "Status", "Hits", "Last Hit"].map((h) => (
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
                <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>RULE LOGIC</div>
                <pre style={{
                  padding: "12px 16px", background: CN.bg, border: `1px solid ${CN.border}`,
                  color: CN.green, fontSize: 12, fontFamily: "'SF Mono', monospace",
                  overflow: "auto", whiteSpace: "pre-wrap",
                }}>
                  {rule.logic}
                </pre>
              </div>
            )}

            {rule.recentHits && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>RECENT HITS</div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${CN.border}` }}>
                      <th style={{ padding: "6px 0", textAlign: "left", color: CN.textMuted, fontSize: 10, fontWeight: 700 }}>Enterprise</th>
                      <th style={{ padding: "6px 0", textAlign: "left", color: CN.textMuted, fontSize: 10, fontWeight: 700 }}>Result</th>
                      <th style={{ padding: "6px 0", textAlign: "left", color: CN.textMuted, fontSize: 10, fontWeight: 700 }}>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rule.recentHits.map((h, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${CN.bgElevated}` }}>
                        <td style={{ padding: "6px 0", color: CN.text }}>{h.enterprise}</td>
                        <td style={{ padding: "6px 0" }}>
                          <span style={cnBadge(h.result === "MATCH" ? CN.green : CN.red, h.result === "MATCH" ? CN.greenBg : CN.redBg)}>
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
