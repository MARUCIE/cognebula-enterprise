"use client";

// Design: design/dashboard/dashboard.html (Stitch Heritage Monolith)
// Architecture: .stitch/DESIGN.md — Zero-Radius, Zero-Shadow, Tonal Layering
// Route: /dashboard

import { useState } from "react";

// ── KPI data (demo) ────────────────────────────────────────────────────────

interface KpiCard {
  label: string;
  value: string;
  unit?: string;
  delta: string;
  deltaType: "positive" | "negative";
  valueColor?: string;
}

const KPI_CARDS: KpiCard[] = [
  { label: "服务客户", value: "128", delta: "较上月 +5", deltaType: "positive", valueColor: "var(--color-primary)" },
  { label: "本月收入", value: "¥458,320.00", delta: "+12.3%", deltaType: "positive", valueColor: "var(--color-secondary)" },
  { label: "待处理发票", value: "342", unit: "张", delta: "-8%", deltaType: "positive", valueColor: "var(--color-primary)" },
  { label: "合规风险", value: "3", unit: "项", delta: "+1", deltaType: "negative", valueColor: "var(--color-dept-compliance)" },
];

// ── Revenue trend data (demo) ──────────────────────────────────────────────

interface BarData {
  month: string;
  label: string;
  value: number;
  isCurrent: boolean;
}

const REVENUE_DATA: BarData[] = [
  { month: "10月", label: "320k", value: 320, isCurrent: false },
  { month: "11月", label: "355k", value: 355, isCurrent: false },
  { month: "12月", label: "310k", value: 310, isCurrent: false },
  { month: "1月", label: "390k", value: 390, isCurrent: false },
  { month: "2月", label: "408k", value: 408, isCurrent: false },
  { month: "3月", label: "458k", value: 458, isCurrent: true },
];

const MAX_REVENUE = Math.max(...REVENUE_DATA.map((d) => d.value));

// ── Task list data (demo) ──────────────────────────────────────────────────

type TaskPriority = "urgent" | "processing" | "queued" | "done";

interface Task {
  name: string;
  priority: TaskPriority;
  priorityLabel: string;
  completed?: boolean;
}

const TASKS: Task[] = [
  { name: "3月增值税申报", priority: "urgent", priorityLabel: "紧急" },
  { name: "企业所得税季报", priority: "urgent", priorityLabel: "紧急" },
  { name: "社保基数年审", priority: "processing", priorityLabel: "处理中" },
  { name: "新客户建账", priority: "queued", priorityLabel: "排队" },
  { name: "2月凭证复核", priority: "done", priorityLabel: "已完成", completed: true },
];

const PRIORITY_DOT_COLORS: Record<TaskPriority, string> = {
  urgent: "var(--color-dept-compliance)",
  processing: "var(--color-secondary)",
  queued: "#445F88",
  done: "var(--color-dept-bookkeeping)",
};

const PRIORITY_LABEL_COLORS: Record<TaskPriority, string> = {
  urgent: "var(--color-dept-compliance)",
  processing: "#614000",
  queued: "#445F88",
  done: "var(--color-dept-bookkeeping)",
};

// ── Customer type data (demo) ──────────────────────────────────────────────

const CUSTOMER_TYPES = [
  { label: "一般纳税人", count: "86家", pct: "67.2%", pctNum: 67.2, color: "var(--color-primary)" },
  { label: "小规模纳税人", count: "42家", pct: "32.8%", pctNum: 32.8, color: "var(--color-secondary)" },
];

// ── Component ──────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [currentMonth] = useState("2026年3月");
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - var(--topbar-height))" }}>
      {/* Page Header */}
      <section style={{ background: "var(--color-surface)", padding: "var(--space-6) var(--space-8)" }}>
        <div style={{ marginBottom: "var(--space-2)" }}>
          <span style={{
            fontSize: "11px",
            color: "var(--color-primary)",
            fontWeight: 700,
            letterSpacing: "2px",
            textTransform: "uppercase" as const,
            fontFamily: "var(--font-body)",
          }}>
            DASHBOARD
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <h1 style={{
            fontSize: "1.5rem",
            fontWeight: 800,
            color: "var(--color-text-primary)",
            fontFamily: "var(--font-display)",
          }}>
            月度仪表盘
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
            {/* Month Selector */}
            <div style={{
              display: "flex",
              alignItems: "center",
              background: "var(--color-surface-container)",
              height: 40,
              padding: "0 var(--space-1)",
            }}>
              <button style={{
                padding: "var(--space-2)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}>
                <ChevronLeftIcon />
              </button>
              <span style={{
                padding: "0 var(--space-4)",
                fontSize: 14,
                fontWeight: 700,
                fontFamily: "var(--font-display)",
              }}>
                {currentMonth}
              </span>
              <button style={{
                padding: "var(--space-2)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}>
                <ChevronRightIcon />
              </button>
            </div>
            {/* Export Button */}
            <button style={{
              background: "var(--gradient-cta)",
              color: "#fff",
              fontWeight: 700,
              padding: "0 var(--space-6)",
              height: 40,
              fontSize: 14,
              border: "none",
              cursor: "pointer",
              letterSpacing: "-0.01em",
            }}>
              导出报告
            </button>
          </div>
        </div>
      </section>

      {/* KPI Strip */}
      <section style={{
        padding: "0 var(--space-8)",
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: "var(--space-4)",
        marginBottom: "var(--space-8)",
      }}>
        {KPI_CARDS.map((kpi) => (
          <div key={kpi.label} style={{
            background: "var(--color-surface-container-lowest)",
            padding: "var(--space-6)",
          }}>
            <p style={{
              fontSize: 12,
              color: "var(--color-text-tertiary)",
              fontWeight: 700,
              marginBottom: "var(--space-4)",
            }}>
              {kpi.label}
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-3)" }}>
              <span style={{
                fontSize: kpi.label === "服务客户" ? "2.5rem" : "2rem",
                fontWeight: 800,
                fontFamily: "var(--font-display)",
                color: kpi.valueColor,
                lineHeight: 1,
                fontVariantNumeric: "tabular-nums",
              }}>
                {kpi.value}
                {kpi.unit && (
                  <span style={{ fontSize: 16, fontWeight: 500, marginLeft: 4 }}>{kpi.unit}</span>
                )}
              </span>
              <span style={{
                fontSize: 12,
                fontWeight: 700,
                fontFamily: "var(--font-body)",
                color: kpi.deltaType === "positive"
                  ? "var(--color-dept-bookkeeping)"
                  : "var(--color-dept-compliance)",
              }}>
                {kpi.delta}
              </span>
            </div>
          </div>
        ))}
      </section>

      {/* Main Content: 60/40 split */}
      <div style={{
        padding: "0 var(--space-8)",
        display: "grid",
        gridTemplateColumns: "6fr 4fr",
        gap: "var(--space-8)",
        flex: 1,
      }}>
        {/* LEFT: Revenue Trend + Customer Types (60%) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-8)" }}>
          {/* Bar Chart Section */}
          <div style={{
            background: "var(--color-surface-container-lowest)",
            padding: "var(--space-8)",
          }}>
            <h3 style={{
              fontSize: 14,
              fontWeight: 700,
              fontFamily: "var(--font-display)",
              marginBottom: "var(--space-8)",
              textTransform: "uppercase" as const,
              letterSpacing: "0.15em",
              color: "var(--color-text-tertiary)",
            }}>
              月度收入趋势 (Revenue Trend)
            </h3>
            <div style={{
              height: 256,
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "space-between",
              gap: "var(--space-2)",
            }}>
              {REVENUE_DATA.map((bar, i) => {
                const heightPct = (bar.value / MAX_REVENUE) * 100;
                const isHovered = hoveredBar === i;
                return (
                  <div
                    key={bar.month}
                    style={{
                      flex: 1,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "var(--space-4)",
                    }}
                    onMouseEnter={() => setHoveredBar(i)}
                    onMouseLeave={() => setHoveredBar(null)}
                  >
                    <span style={{
                      fontSize: 10,
                      fontWeight: 700,
                      fontVariantNumeric: "tabular-nums",
                      color: bar.isCurrent ? "var(--color-secondary)" : "var(--color-primary)",
                      opacity: bar.isCurrent || isHovered ? 1 : 0,
                      transition: "opacity 0.15s",
                    }}>
                      {bar.label}
                    </span>
                    <div style={{
                      width: "100%",
                      height: `${heightPct}%`,
                      background: bar.isCurrent
                        ? "var(--color-secondary)"
                        : isHovered
                          ? "var(--color-primary)"
                          : "var(--color-surface-container)",
                      cursor: "pointer",
                      transition: "background 0.15s",
                    }} />
                    <span style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: bar.isCurrent ? "var(--color-primary)" : "var(--color-text-tertiary)",
                    }}>
                      {bar.month}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Customer Type Distribution */}
          <div style={{ background: "var(--color-surface-container-lowest)", overflow: "hidden" }}>
            <div style={{
              padding: "var(--space-6) var(--space-8)",
              background: "var(--color-surface-container)",
            }}>
              <h3 style={{
                fontSize: 14,
                fontWeight: 700,
                fontFamily: "var(--font-display)",
                textTransform: "uppercase" as const,
                letterSpacing: "0.15em",
                color: "var(--color-primary)",
              }}>
                客户类型分布
              </h3>
            </div>
            <div style={{ padding: "var(--space-8)" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-8)" }}>
                {CUSTOMER_TYPES.map((ct) => (
                  <div key={ct.label}>
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "var(--space-4)",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                        <div style={{ width: 8, height: 8, background: ct.color }} />
                        <span style={{ fontSize: 14, fontWeight: 700 }}>{ct.label}</span>
                      </div>
                      <span style={{ fontSize: 14, fontVariantNumeric: "tabular-nums", fontWeight: 700 }}>
                        {ct.count}{" "}
                        <span style={{ color: "var(--color-text-tertiary)", marginLeft: 8 }}>{ct.pct}</span>
                      </span>
                    </div>
                    <div style={{
                      width: "100%",
                      background: "var(--color-surface-container)",
                      height: 8,
                    }}>
                      <div style={{
                        background: ct.color,
                        height: "100%",
                        width: `${ct.pctNum}%`,
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT: Task List + AI Overview (40%) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-8)" }}>
          {/* To-Do List */}
          <div style={{ background: "var(--color-surface-container-lowest)" }}>
            <div style={{
              padding: "var(--space-6) var(--space-8)",
              borderBottom: "1px solid var(--color-surface-container-low)",
            }}>
              <h3 style={{
                fontSize: 14,
                fontWeight: 700,
                fontFamily: "var(--font-display)",
                textTransform: "uppercase" as const,
                letterSpacing: "0.15em",
                color: "var(--color-primary)",
              }}>
                待办事项
              </h3>
            </div>
            <div>
              {TASKS.map((task, i) => (
                <div
                  key={task.name}
                  style={{
                    padding: "var(--space-4) var(--space-8)",
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-4)",
                    borderBottom: i < TASKS.length - 1
                      ? "1px solid var(--color-surface-container-low)"
                      : "none",
                  }}
                >
                  <div style={{
                    width: 8,
                    height: 8,
                    background: PRIORITY_DOT_COLORS[task.priority],
                    flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: 14,
                    fontWeight: 500,
                    ...(task.completed ? {
                      color: "var(--color-text-tertiary)",
                      textDecoration: "line-through",
                    } : {}),
                  }}>
                    {task.name}
                  </span>
                  <span style={{
                    marginLeft: "auto",
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase" as const,
                    color: PRIORITY_LABEL_COLORS[task.priority],
                  }}>
                    {task.priorityLabel}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* AI Processing Overview */}
          <div style={{
            background: "var(--color-surface-container-low)",
            padding: "var(--space-8)",
          }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
              marginBottom: "var(--space-6)",
            }}>
              <AiChipIcon />
              <h3 style={{
                fontSize: 14,
                fontWeight: 700,
                fontFamily: "var(--font-display)",
                textTransform: "uppercase" as const,
                letterSpacing: "0.15em",
                color: "var(--color-primary)",
              }}>
                AI 处理概览
              </h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
              {/* Auto-generated Vouchers */}
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-end",
                borderBottom: "2px solid rgba(195, 198, 209, 0.1)",
                paddingBottom: "var(--space-4)",
              }}>
                <div>
                  <p style={{
                    fontSize: 10,
                    color: "var(--color-text-tertiary)",
                    fontWeight: 700,
                    textTransform: "uppercase" as const,
                    marginBottom: "var(--space-1)",
                  }}>
                    今日自动生成凭证
                  </p>
                  <p style={{
                    fontSize: "1.5rem",
                    fontWeight: 900,
                    fontFamily: "var(--font-display)",
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    45<span style={{ fontSize: 14, fontWeight: 500, marginLeft: 4 }}>笔</span>
                  </p>
                </div>
                {/* Mini sparkline */}
                <div style={{ width: 64, height: 32, display: "flex", alignItems: "flex-end", gap: 2 }}>
                  <div style={{ background: "rgba(0, 36, 74, 0.2)", width: "100%", height: "40%" }} />
                  <div style={{ background: "rgba(0, 36, 74, 0.2)", width: "100%", height: "60%" }} />
                  <div style={{ background: "rgba(0, 36, 74, 0.2)", width: "100%", height: "30%" }} />
                  <div style={{ background: "var(--color-primary)", width: "100%", height: "90%" }} />
                </div>
              </div>

              {/* AI Accuracy */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                <div>
                  <p style={{
                    fontSize: 10,
                    color: "var(--color-text-tertiary)",
                    fontWeight: 700,
                    textTransform: "uppercase" as const,
                    marginBottom: "var(--space-1)",
                  }}>
                    AI 准确率
                  </p>
                  <p style={{
                    fontSize: "1.5rem",
                    fontWeight: 900,
                    fontFamily: "var(--font-display)",
                    fontVariantNumeric: "tabular-nums",
                    color: "var(--color-dept-bookkeeping)",
                  }}>
                    97.8%
                  </p>
                </div>
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: "var(--color-dept-bookkeeping)",
                  border: "1px solid var(--color-dept-bookkeeping)",
                  padding: "var(--space-1) var(--space-2)",
                }}>
                  稳健
                </span>
              </div>

              {/* Status Note */}
              <div style={{ paddingTop: "var(--space-4)" }}>
                <p style={{
                  fontSize: 10,
                  lineHeight: 1.8,
                  color: "var(--color-text-tertiary)",
                  fontWeight: 500,
                }}>
                  AI 审计节点正常运行。系统已自动识别 12 笔潜在的重复报销，正在等待人工二次确认。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Summary Strip */}
      <footer style={{
        height: 48,
        background: "var(--color-primary-deep)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-12)",
        marginTop: "var(--space-8)",
      }}>
        {[
          { label: "活跃客户", value: "128" },
          { label: "本月凭证", value: "1,247笔" },
          { label: "收入合计", value: "¥458,320.00", highlight: true },
          { label: "AI 处理率", value: "96.2%", highlight: true },
        ].map((m, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span style={{
              fontSize: 11,
              fontWeight: 600,
              color: "rgba(255,255,255,0.7)",
              letterSpacing: "1px",
            }}>
              {m.label}
            </span>
            <span style={{
              fontSize: 14,
              fontWeight: 700,
              color: m.highlight ? "var(--color-secondary)" : "#fff",
              fontVariantNumeric: "tabular-nums",
            }}>
              {m.value}
            </span>
          </div>
        ))}
      </footer>
    </div>
  );
}

// ── Small inline icons (no external dependency) ─────────────────────────────

function ChevronLeftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 6 15 12 9 18" />
    </svg>
  );
}

function AiChipIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="var(--color-primary)">
      <path d="M7 5h10v14H7V5zm2 2v10h6V7H9zm-4 2H3v2h2V9zm0 4H3v2h2v-2zm14-4h2v2h-2V9zm0 4h2v2h-2v-2zM9 3V1h2v2H9zm4 0V1h2v2h-2zM9 23v-2h2v2H9zm4 0v-2h2v2h-2z" />
    </svg>
  );
}
