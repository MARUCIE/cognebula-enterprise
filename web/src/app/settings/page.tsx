"use client";

// Design: design/settings/settings.html (Stitch Heritage Monolith)
// Architecture: .stitch/DESIGN.md — Zero-Radius, Zero-Shadow, Tonal Layering
// Route: /settings

import { useState } from "react";

// ── Settings nav sections ──────────────────────────────────────────────────

type SettingsSection =
  | "chart-of-accounts"
  | "voucher-templates"
  | "tax-rates"
  | "filing-calendar"
  | "team"
  | "ai-engine"
  | "backup";

interface NavItem {
  id: SettingsSection;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { id: "chart-of-accounts", label: "科目表管理", icon: <WalletIcon /> },
  { id: "voucher-templates", label: "凭证模板", icon: <ReceiptIcon /> },
  { id: "tax-rates", label: "税率配置", icon: <PercentIcon /> },
  { id: "filing-calendar", label: "申报日历", icon: <CalendarIcon /> },
  { id: "team", label: "团队管理", icon: <PeopleIcon /> },
  { id: "ai-engine", label: "AI 引擎", icon: <AiIcon /> },
  { id: "backup", label: "数据备份", icon: <BackupIcon /> },
];

// ── Chart of Accounts data (demo) ──────────────────────────────────────────

type AccountCategory = "asset" | "liability" | "pnl";

interface Account {
  code: string;
  name: string;
  category: AccountCategory;
  direction: string;
  enabled: boolean;
  indent: boolean;
}

const ACCOUNTS: Account[] = [
  { code: "1001", name: "库存现金", category: "asset", direction: "借", enabled: true, indent: false },
  { code: "1002", name: "银行存款", category: "asset", direction: "借", enabled: true, indent: false },
  { code: "1002001", name: "工商银行", category: "asset", direction: "借", enabled: true, indent: true },
  { code: "1002002", name: "建设银行", category: "asset", direction: "借", enabled: true, indent: true },
  { code: "1122", name: "应收账款", category: "asset", direction: "借", enabled: true, indent: false },
  { code: "2001", name: "短期借款", category: "liability", direction: "贷", enabled: true, indent: false },
  { code: "5001", name: "主营业务收入", category: "pnl", direction: "贷", enabled: true, indent: false },
  { code: "6001", name: "管理费用", category: "pnl", direction: "借", enabled: true, indent: false },
];

const CATEGORY_STYLE: Record<AccountCategory, { bg: string; color: string; label: string }> = {
  asset: { bg: "#FDF6EB", color: "#8C6D1F", label: "资产" },
  liability: { bg: "var(--color-surface-container)", color: "var(--color-text-secondary)", label: "负债" },
  pnl: { bg: "#D5E3FF", color: "#3D5981", label: "损益" },
};

// ── Component ──────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("chart-of-accounts");
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - var(--topbar-height))" }}>
      {/* Page Header */}
      <section style={{ background: "var(--color-surface)", padding: "var(--space-6) var(--space-8)" }}>
        <div style={{ marginBottom: "var(--space-2)" }}>
          <span style={{
            fontSize: 11,
            color: "var(--color-primary)",
            fontWeight: 700,
            letterSpacing: "2px",
            textTransform: "uppercase" as const,
            fontFamily: "var(--font-body)",
          }}>
            SETTINGS
          </span>
        </div>
        <h1 style={{
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--color-text-primary)",
          fontFamily: "var(--font-display)",
        }}>
          系统设置
        </h1>
      </section>

      {/* Main Content: 25/75 split */}
      <section style={{ display: "flex", flex: 1, padding: "0 var(--space-8) var(--space-8)", gap: 0 }}>
        {/* LEFT: Settings Nav (25%) */}
        <div style={{
          width: "25%",
          background: "var(--color-surface-container-low)",
          display: "flex",
          flexDirection: "column",
        }}>
          {NAV_ITEMS.map((item) => {
            const isActive = item.id === activeSection;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "var(--space-4) var(--space-6)",
                  fontSize: 14,
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left" as const,
                  background: isActive ? "var(--color-primary)" : "transparent",
                  color: isActive ? "#fff" : "var(--color-primary)",
                  transition: "background 0.15s, color 0.15s",
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  {item.icon}
                  {item.label}
                </span>
                {isActive && <ChevronRightIcon />}
              </button>
            );
          })}
        </div>

        {/* RIGHT: Content Area (75%) */}
        <div style={{
          width: "75%",
          background: "var(--color-surface-container-lowest)",
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Content Header */}
          <div style={{ padding: "var(--space-6)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-6)" }}>
              <div>
                <h2 style={{
                  fontSize: "1.25rem",
                  fontWeight: 700,
                  fontFamily: "var(--font-display)",
                  color: "var(--color-primary)",
                  marginBottom: "var(--space-1)",
                }}>
                  科目表管理
                </h2>
                <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", fontFamily: "var(--font-body)" }}>
                  一级科目: <b style={{ fontVariantNumeric: "tabular-nums" }}>68</b> | 明细科目: <b style={{ fontVariantNumeric: "tabular-nums" }}>284</b>
                </p>
              </div>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button style={{
                  background: "var(--color-surface-container)",
                  color: "var(--color-primary)",
                  padding: "var(--space-2) var(--space-6)",
                  fontWeight: 700,
                  fontSize: 12,
                  fontFamily: "var(--font-display)",
                  border: "none",
                  cursor: "pointer",
                }}>
                  导入
                </button>
                <button style={{
                  background: "var(--gradient-cta)",
                  color: "#fff",
                  padding: "var(--space-2) var(--space-6)",
                  fontWeight: 700,
                  fontSize: 12,
                  fontFamily: "var(--font-display)",
                  border: "none",
                  cursor: "pointer",
                }}>
                  新增科目
                </button>
              </div>
            </div>

            {/* Search */}
            <div style={{ position: "relative", marginBottom: "var(--space-8)" }}>
              <label style={{
                display: "block",
                fontSize: 10,
                fontWeight: 700,
                color: "var(--color-text-tertiary)",
                textTransform: "uppercase" as const,
                marginBottom: "var(--space-1)",
                paddingLeft: "var(--space-1)",
              }}>
                Search Database
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索科目编码或名称..."
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  borderBottom: "2px solid var(--color-surface-container)",
                  padding: "var(--space-2) var(--space-1)",
                  fontSize: 13,
                  fontFamily: "var(--font-body)",
                  color: "var(--color-text-primary)",
                  outline: "none",
                }}
              />
              <div style={{ position: "absolute", right: "var(--space-2)", bottom: "var(--space-2)" }}>
                <SearchIcon />
              </div>
            </div>

            {/* Table */}
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--color-surface-container)" }}>
                    {["科目编码", "科目名称", "类别", "余额方向", "状态", "操作"].map((h, i) => (
                      <th key={h} style={{
                        padding: "var(--space-4)",
                        fontSize: 11,
                        fontWeight: 700,
                        color: "var(--color-primary)",
                        letterSpacing: "1.5px",
                        textTransform: "uppercase" as const,
                        fontFamily: "var(--font-display)",
                        textAlign: i === 5 ? "right" as const : "left" as const,
                        ...(i === 0 ? { width: 128 } : {}),
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody style={{ fontSize: 13, fontFamily: "var(--font-body)" }}>
                  {ACCOUNTS.filter((a) => {
                    if (!searchQuery) return true;
                    const q = searchQuery.toLowerCase();
                    return a.code.includes(q) || a.name.toLowerCase().includes(q);
                  }).map((account, i) => {
                    const cat = CATEGORY_STYLE[account.category];
                    const isEven = i % 2 === 0;
                    return (
                      <tr
                        key={account.code}
                        style={{
                          height: 48,
                          background: isEven
                            ? "var(--color-surface-container-lowest)"
                            : "var(--color-surface-container-low)",
                          transition: "background 0.15s",
                        }}
                      >
                        {/* Code */}
                        <td style={{
                          padding: "0 var(--space-4)",
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: account.indent ? 500 : 600,
                          color: account.indent ? "var(--color-text-tertiary)" : "var(--color-text-primary)",
                          paddingLeft: account.indent ? "var(--space-8)" : "var(--space-4)",
                        }}>
                          {account.code}
                        </td>
                        {/* Name */}
                        <td style={{
                          padding: "0 var(--space-4)",
                          color: account.indent ? "var(--color-text-secondary)" : "var(--color-text-primary)",
                          paddingLeft: account.indent ? "var(--space-12)" : "var(--space-4)",
                        }}>
                          {account.name}
                        </td>
                        {/* Category Badge */}
                        <td style={{ padding: "0 var(--space-4)" }}>
                          <span style={{
                            background: cat.bg,
                            color: cat.color,
                            padding: "2px 8px",
                            fontSize: 11,
                            fontWeight: 700,
                          }}>
                            {cat.label}
                          </span>
                        </td>
                        {/* Direction */}
                        <td style={{ padding: "0 var(--space-4)" }}>
                          {account.direction}
                        </td>
                        {/* Status */}
                        <td style={{ padding: "0 var(--space-4)" }}>
                          <span style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-1)",
                            fontWeight: 700,
                            color: "#1B7A4E",
                          }}>
                            <span style={{
                              width: 6,
                              height: 6,
                              background: "#1B7A4E",
                              display: "inline-block",
                              flexShrink: 0,
                            }} />
                            启用
                          </span>
                        </td>
                        {/* Actions */}
                        <td style={{ padding: "0 var(--space-4)", textAlign: "right" }}>
                          <button style={{
                            color: "var(--color-primary)",
                            fontWeight: 700,
                            textDecoration: "underline",
                            textUnderlineOffset: 4,
                            textDecorationThickness: 2,
                            fontSize: 12,
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                          }}>
                            编辑
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Statistics Footer (tonal shift) */}
          <div style={{
            marginTop: "auto",
            background: "var(--color-surface-container-low)",
            padding: "var(--space-6)",
            display: "flex",
            gap: "var(--space-12)",
            fontSize: 12,
            fontWeight: 600,
            fontFamily: "var(--font-body)",
            color: "var(--color-text-secondary)",
          }}>
            {[
              { color: "#FDF6EB", label: "资产类", count: "32" },
              { color: "var(--color-surface-container)", label: "负债类", count: "12" },
              { color: "#D5E3FF", label: "权益类", count: "6" },
              { color: "#D5E3FF", label: "损益类", count: "18" },
            ].map((stat) => (
              <div key={stat.label} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span style={{ width: 8, height: 8, background: stat.color, display: "inline-block", flexShrink: 0 }} />
                {stat.label}: <span style={{ color: "var(--color-primary)", fontWeight: 700, fontVariantNumeric: "tabular-nums", marginLeft: "var(--space-1)" }}>{stat.count}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom Status Strip */}
      <footer style={{
        position: "sticky",
        bottom: 0,
        zIndex: 10,
        height: 48,
        background: "var(--color-primary-deep)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 var(--space-8)",
      }}>
        <div style={{ display: "flex", gap: "var(--space-8)" }}>
          {[
            { label: "科目总数:", value: "284", accent: false },
            { label: "启用:", value: "276", accent: false },
            { label: "停用:", value: "8", accent: true },
          ].map((item) => (
            <div key={item.label} style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-2)",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "1.5px",
              fontFamily: "var(--font-display)",
              color: item.accent ? "var(--color-secondary)" : "#fff",
            }}>
              <span style={{ opacity: item.accent ? 1 : 0.5 }}>{item.label}</span>
              <span style={{ fontVariantNumeric: "tabular-nums" }}>{item.value}</span>
            </div>
          ))}
        </div>
        <div style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "1.5px",
          fontFamily: "var(--font-display)",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
        }}>
          <span style={{ opacity: 0.5, textTransform: "uppercase" as const }}>Last Synchronization:</span>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>2026-03-28 14:30:12</span>
        </div>
      </footer>
    </div>
  );
}

// ── Inline SVG icons (no external dependency) ─────────────────────────────

function WalletIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M21 7H3c-1.1 0-2 .9-2 2v6c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2zm0 8H3V9h18v6zm-2-3c0 .55-.45 1-1 1s-1-.45-1-1 .45-1 1-1 1 .45 1 1zM4 5h16V3H4v2z" />
    </svg>
  );
}

function ReceiptIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.5 3.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2 4.5 3.5 3 2v20l1.5-1.5L6 22l1.5-1.5L9 22l1.5-1.5L12 22l1.5-1.5L15 22l1.5-1.5L18 22l1.5-1.5L21 22V2l-1.5 1.5zM19 19.09H5V4.91h14v14.18zM6 15h12v2H6v-2zm0-4h12v2H6v-2zm0-4h12v2H6V7z" />
    </svg>
  );
}

function PercentIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M7.5 11C9.43 11 11 9.43 11 7.5S9.43 4 7.5 4 4 5.57 4 7.5 5.57 11 7.5 11zm0-5C8.33 6 9 6.67 9 7.5S8.33 9 7.5 9 6 8.33 6 7.5 6.67 6 7.5 6zm9 7c-1.93 0-3.5 1.57-3.5 3.5S14.57 20 16.5 20s3.5-1.57 3.5-3.5S18.43 13 16.5 13zm0 5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5.41 20L4 18.59 18.59 4 20 5.41 5.41 20z" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7v-5z" />
    </svg>
  );
}

function PeopleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" />
    </svg>
  );
}

function AiIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M21 10.12h-6.78l2.74-2.82-2.2-2.2L12 7.94V1H10v6.94L7.24 5.1 5.04 7.3l2.74 2.82H1v2h6.78l-2.74 2.82 2.2 2.2L10 14.3V21h2v-6.7l2.76 2.84 2.2-2.2-2.74-2.82H21z" />
    </svg>
  );
}

function BackupIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2v9.67z" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="var(--color-text-tertiary)">
      <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" />
    </svg>
  );
}
