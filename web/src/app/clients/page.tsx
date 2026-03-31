"use client";

// Design: design/clients/clients.html (Stitch Heritage Monolith)
// Architecture: .stitch/DESIGN.md — Zero-Radius, Zero-Shadow, Tonal Layering
// Route: /clients

import { useState } from "react";

// ── Types ──────────────────────────────────────────────────────────────────────

type TaxType = "general" | "small";
type ClientStatus = "normal" | "pending" | "abnormal" | "new";
type FilterKey = "all" | "general" | "small" | "abnormal";

interface Client {
  id: string;
  name: string;
  creditCode: string;
  taxType: TaxType;
  owner: string;
  monthlyFee: string;
  status: ClientStatus;
  lastActive: string;
}

// ── Mock data ──────────────────────────────────────────────────────────────────

const CLIENTS: Client[] = [
  { id: "1", name: "成都朋诚鑫盛商贸有限公司", creditCode: "91510100MA6...", taxType: "general", owner: "李明", monthlyFee: "2,800.00", status: "normal", lastActive: "2026-03-28" },
  { id: "2", name: "四川聚清诚建设工程有限公司", creditCode: "91510100...", taxType: "general", owner: "王芳", monthlyFee: "3,500.00", status: "normal", lastActive: "2026-03-27" },
  { id: "3", name: "简阳丰印象广告有限公司", creditCode: "91510100...", taxType: "small", owner: "张伟", monthlyFee: "1,200.00", status: "normal", lastActive: "2026-03-25" },
  { id: "4", name: "中唯耘源建设集团有限公司", creditCode: "91510100...", taxType: "general", owner: "刘洋", monthlyFee: "4,200.00", status: "normal", lastActive: "2026-03-24" },
  { id: "5", name: "恒升投资管理有限公司", creditCode: "91510100...", taxType: "general", owner: "陈静", monthlyFee: "2,500.00", status: "pending", lastActive: "2026-03-20" },
  { id: "6", name: "时代传媒有限公司", creditCode: "91510100...", taxType: "small", owner: "赵敏", monthlyFee: "800.00", status: "normal", lastActive: "2026-03-18" },
  { id: "7", name: "大唐信息技术有限公司", creditCode: "91510100...", taxType: "general", owner: "周磊", monthlyFee: "3,200.00", status: "abnormal", lastActive: "2026-03-15" },
  { id: "8", name: "鑫海物流集团有限公司", creditCode: "91510100...", taxType: "general", owner: "吴强", monthlyFee: "2,000.00", status: "new", lastActive: "2026-03-30" },
];

const FILTERS: { key: FilterKey; label: string; count: number }[] = [
  { key: "all", label: "全部", count: 128 },
  { key: "general", label: "一般纳税人", count: 86 },
  { key: "small", label: "小规模", count: 42 },
  { key: "abnormal", label: "异常", count: 3 },
];

const SUMMARY_ITEMS = [
  { label: "活跃客户:", value: "125", color: "#fff" },
  { label: "本月新增:", value: "3", color: "#fff" },
  { label: "月费收入:", value: "¥458,320", color: "var(--color-secondary)" },
  { label: "异常客户:", value: "3", color: "#BA1A1A" },
];

// ── Status config ──────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ClientStatus, { label: string; bg: string; color: string }> = {
  normal: { label: "正常", bg: "#E6F4EA", color: "#1B7A4E" },
  pending: { label: "待审", bg: "#FFF8E1", color: "#F59E0B" },
  abnormal: { label: "异常", bg: "#FEE2E2", color: "#BA1A1A" },
  new: { label: "新建", bg: "var(--color-primary-deep)", color: "#fff" },
};

const TAX_TYPE_CONFIG: Record<TaxType, { label: string; bg: string; color: string }> = {
  general: { label: "一般纳税人", bg: "#FDF6EB", color: "#C5913E" },
  small: { label: "小规模", bg: "var(--color-surface-container)", color: "var(--color-text-secondary)" },
};

// ── Component ──────────────────────────────────────────────────────────────────

export default function ClientsPage() {
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");
  const [search, setSearch] = useState("");

  const filtered = CLIENTS.filter((c) => {
    if (activeFilter === "general" && c.taxType !== "general") return false;
    if (activeFilter === "small" && c.taxType !== "small") return false;
    if (activeFilter === "abnormal" && c.status !== "abnormal") return false;
    if (search) {
      const q = search.toLowerCase();
      return c.name.toLowerCase().includes(q) || c.creditCode.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - var(--topbar-height))" }}>
      {/* ── Page Header ── */}
      <section style={{
        background: "var(--color-surface)",
        padding: "var(--space-10) var(--space-8) var(--space-6)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-end",
      }}>
        <div>
          <nav style={{
            display: "flex",
            alignItems: "center",
            fontSize: 11,
            color: "var(--color-primary)",
            fontWeight: 700,
            letterSpacing: "0.15em",
            marginBottom: "var(--space-2)",
            fontFamily: "var(--font-body)",
          }}>
            <span style={{ opacity: 0.5, textTransform: "uppercase" }}>Directory</span>
            <span style={{ margin: "0 8px", opacity: 0.3 }}>/</span>
            <span style={{ textTransform: "uppercase" }}>CLIENTS</span>
          </nav>
          <h1 style={{
            fontSize: "2.25rem",
            fontWeight: 800,
            color: "var(--color-primary)",
            lineHeight: 1,
            letterSpacing: "-0.02em",
            fontFamily: "var(--font-display)",
          }}>
            客户管理
          </h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
          {/* Search */}
          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}>
              <SearchIcon />
            </div>
            <input
              type="text"
              placeholder="搜索客户名称或纳税人识别号..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: "2px solid var(--color-surface-container)",
                paddingLeft: 28,
                paddingBottom: 4,
                paddingTop: 4,
                width: 260,
                fontSize: 12,
                fontFamily: "var(--font-body)",
                color: "var(--color-text-primary)",
                outline: "none",
              }}
            />
          </div>

          {/* CTA */}
          <button style={{
            background: "var(--gradient-cta)",
            color: "#fff",
            padding: "var(--space-3) var(--space-8)",
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: "0.1em",
            border: "none",
            cursor: "pointer",
            fontFamily: "var(--font-body)",
          }}>
            新增客户
          </button>
        </div>
      </section>

      {/* ── Filter Bar ── */}
      <section style={{
        height: 56,
        background: "var(--color-surface-container-lowest)",
        padding: "0 var(--space-8)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          {FILTERS.map((f) => {
            const isActive = activeFilter === f.key;
            const isAbnormal = f.key === "abnormal";
            return (
              <button
                key={f.key}
                onClick={() => setActiveFilter(f.key)}
                style={{
                  padding: "0 var(--space-6)",
                  height: 36,
                  background: isActive ? "var(--color-primary)" : "var(--color-surface-container)",
                  color: isActive
                    ? "#fff"
                    : isAbnormal
                      ? "#BA1A1A"
                      : "var(--color-primary)",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.05em",
                  border: "none",
                  cursor: "pointer",
                  fontFamily: "var(--font-body)",
                }}
              >
                {f.label} ({f.count})
              </button>
            );
          })}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", cursor: "pointer" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.1em" }}>排序:</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-primary)" }}>最近活跃</span>
          <ChevronDownIcon />
        </div>
      </section>

      {/* ── Client Table ── */}
      <section style={{ padding: "var(--space-6) var(--space-8)", flex: 1 }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--color-surface-container-low)", height: 40 }}>
              {TABLE_HEADERS.map((h) => (
                <th key={h.label} style={{
                  padding: "0 var(--space-4)",
                  fontSize: 10,
                  fontWeight: 700,
                  color: "var(--color-text-tertiary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.2em",
                  textAlign: h.align as "left" | "right" | "center",
                  fontFamily: "var(--font-body)",
                }}>
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody style={{ fontFamily: "var(--font-body)", fontSize: 13 }}>
            {filtered.map((c, i) => {
              const isEven = i % 2 === 0;
              const tax = TAX_TYPE_CONFIG[c.taxType];
              const status = STATUS_CONFIG[c.status];
              return (
                <tr
                  key={c.id}
                  style={{
                    height: 56,
                    background: isEven ? "var(--color-surface-container-lowest)" : "var(--color-surface)",
                    cursor: "pointer",
                  }}
                >
                  {/* Name */}
                  <td style={{ padding: "0 var(--space-4)", fontWeight: 600, color: "var(--color-primary)" }}>
                    {c.name}
                  </td>
                  {/* Credit Code */}
                  <td style={{ padding: "0 var(--space-4)", color: "var(--color-text-tertiary)", fontVariantNumeric: "tabular-nums" }}>
                    {c.creditCode}
                  </td>
                  {/* Tax Type */}
                  <td style={{ padding: "0 var(--space-4)" }}>
                    <span style={{
                      background: tax.bg,
                      color: tax.color,
                      padding: "4px 12px",
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: "uppercase",
                    }}>
                      {tax.label}
                    </span>
                  </td>
                  {/* Owner */}
                  <td style={{ padding: "0 var(--space-4)", color: "var(--color-text-secondary)" }}>
                    {c.owner}
                  </td>
                  {/* Monthly Fee */}
                  <td style={{
                    padding: "0 var(--space-4)",
                    textAlign: "right",
                    fontWeight: 700,
                    color: "var(--color-secondary)",
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    ¥{c.monthlyFee}
                  </td>
                  {/* Status */}
                  <td style={{ padding: "0 var(--space-4)", textAlign: "center" }}>
                    <span style={{
                      background: status.bg,
                      color: status.color,
                      padding: "4px 12px",
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: "uppercase",
                    }}>
                      {status.label}
                    </span>
                  </td>
                  {/* Last Active */}
                  <td style={{
                    padding: "0 var(--space-4)",
                    textAlign: "right",
                    color: "var(--color-text-tertiary)",
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    {c.lastActive}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* ── Pagination ── */}
      <section style={{
        padding: "0 var(--space-8) var(--space-12)",
        display: "flex",
        justifyContent: "flex-end",
        alignItems: "center",
        gap: "var(--space-6)",
      }}>
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          color: "var(--color-text-tertiary)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}>
          共 {FILTERS[0].count} 条 | 第 1/16 页
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          <PaginationBtn><ChevronLeftIcon /></PaginationBtn>
          <PaginationBtn active>1</PaginationBtn>
          <PaginationBtn>2</PaginationBtn>
          <PaginationBtn><ChevronRightIcon /></PaginationBtn>
        </div>
      </section>

      {/* ── Bottom Summary Strip ── */}
      <footer style={{
        height: 48,
        background: "var(--color-primary-deep)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-8)",
        fontFamily: "var(--font-body)",
      }}>
        {SUMMARY_ITEMS.map((item, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span style={{
              fontSize: 12,
              fontWeight: 600,
              color: "rgba(255,255,255,0.7)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}>
              {item.label}
            </span>
            <span style={{
              fontSize: 13,
              fontWeight: 700,
              color: item.color,
              fontVariantNumeric: "tabular-nums",
            }}>
              {item.value}
            </span>
            {i < SUMMARY_ITEMS.length - 1 && (
              <div style={{ width: 1, height: 16, background: "rgba(255,255,255,0.1)", marginLeft: "var(--space-6)" }} />
            )}
          </div>
        ))}
      </footer>
    </div>
  );
}

// ── Table headers config ───────────────────────────────────────────────────────

const TABLE_HEADERS = [
  { label: "客户名称", align: "left" },
  { label: "统一社会信用代码", align: "left" },
  { label: "纳税类型", align: "left" },
  { label: "负责人", align: "left" },
  { label: "月代账费", align: "right" },
  { label: "状态", align: "center" },
  { label: "最后活跃", align: "right" },
];

// ── Sub-components ─────────────────────────────────────────────────────────────

function PaginationBtn({ children, active }: { children: React.ReactNode; active?: boolean }) {
  return (
    <button style={{
      width: 40,
      height: 40,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: active ? "var(--color-primary)" : "var(--color-surface-container)",
      color: active ? "#fff" : "var(--color-primary)",
      fontSize: 12,
      fontWeight: 700,
      border: "none",
      cursor: active ? "default" : "pointer",
    }}>
      {children}
    </button>
  );
}

// ── Inline SVG icons ───────────────────────────────────────────────────────────

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 6 15 12 9 18" />
    </svg>
  );
}
