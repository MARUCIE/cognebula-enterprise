"use client";

// Design: design/tax-workbench/tax-workbench.html (Stitch Heritage Monolith)
// Architecture: .stitch/DESIGN.md -- Zero-Radius, Zero-Shadow, Tonal Layering
// Route: /workbench/tax

import { useState } from "react";

// -- Tax period status types ---------------------------------------------------

type TaxStatus = "filed" | "pending" | "overdue";

interface TaxPeriodStats {
  filed: number;
  pending: number;
  overdue: number;
  deadline: string;
  daysLeft: number;
}

const PERIOD_STATS: TaxPeriodStats = {
  filed: 4,
  pending: 3,
  overdue: 1,
  deadline: "2026-04-15",
  daysLeft: 15,
};

// -- VAT data -----------------------------------------------------------------

interface VatLine {
  label: string;
  labelEn: string;
  amount: string;
}

const VAT_LINES: VatLine[] = [
  { label: "销项税额", labelEn: "Output", amount: "1,240,500.00" },
  { label: "进项税额", labelEn: "Input", amount: "856,200.00" },
  { label: "进项转出", labelEn: "Reversal", amount: "12,400.00" },
];

const VAT_SETTLEMENT = "396,700.00";

// -- CIT data -----------------------------------------------------------------

interface CitLine {
  label: string;
  amount: string;
  isAdjustment?: boolean;
  isPositive?: boolean;
}

const CIT_LINES: CitLine[] = [
  { label: "营业收入", amount: "8,450,000.00" },
  { label: "营业成本", amount: "5,120,000.00" },
  { label: "利润总额", amount: "3,330,000.00" },
  { label: "纳税调增/减", amount: "+45,000.00", isAdjustment: true, isPositive: true },
];

const CIT_TAXABLE = "3,375,000.00";
const CIT_LIABILITY = "843,750.00";

// -- PIT & Surcharges data ----------------------------------------------------

interface SurchargeLine {
  label: string;
  amount: string;
}

const SURCHARGES: SurchargeLine[] = [
  { label: "城建税 (7%)", amount: "27,769.00" },
  { label: "教育费附加 (3%)", amount: "11,901.00" },
];

const SURCHARGES_TOTAL = "39,670.00";
const PIT_TOTAL = "45,820.50";
const STAMP_TOTAL = "4,225.00";

// -- Bottom summary -----------------------------------------------------------

const SUMMARY_ITEMS = [
  { label: "合计金额", value: "1,330,165.50", isCurrency: true },
  { label: "税额小计", value: "396,700.00", isCurrency: true },
  { label: "待核销", value: "12 项", isCurrency: false },
];

// == Component ================================================================

export default function TaxWorkbenchPage() {
  const [activePeriod] = useState("2026年3月");

  return (
    <div className="flex flex-col" style={{ minHeight: "calc(100vh - var(--topbar-height))" }}>
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
            WORKBENCH / TAX
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <h1 style={{
            fontSize: "2.25rem",
            fontWeight: 800,
            color: "var(--color-text-primary)",
            fontFamily: "var(--font-display)",
          }}>
            税务工作台
          </h1>
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <SecondaryBtn>税种总览</SecondaryBtn>
            <SecondaryBtn>税率表</SecondaryBtn>
            <SecondaryBtn>申报日历</SecondaryBtn>
            <button style={{
              background: "var(--gradient-cta)",
              color: "#fff",
              fontWeight: 700,
              padding: "var(--space-3) var(--space-6)",
              fontSize: 13,
              border: "none",
              cursor: "pointer",
            }}>
              开始申报
            </button>
          </div>
        </div>
      </section>

      {/* Tax Period Bar */}
      <section style={{
        height: 56,
        background: "var(--color-surface-container-lowest)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 var(--space-8)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-6)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <CalendarIcon />
            <span style={{ fontWeight: 700, color: "var(--color-text-primary)", fontSize: 14 }}>
              申报期: {activePeriod}
            </span>
          </div>
          <div style={{ display: "flex", gap: "var(--space-4)" }}>
            <StatusChip color="var(--color-dept-bookkeeping)" label={`已申报: ${PERIOD_STATS.filed}`} />
            <StatusChip color="var(--color-primary)" label={`待申报: ${PERIOD_STATS.pending}`} />
            <StatusChip color="var(--color-dept-compliance)" label={`逾期: ${PERIOD_STATS.overdue}`} />
          </div>
        </div>
        <span style={{
          fontSize: 13,
          fontWeight: 700,
          color: "var(--color-text-tertiary)",
          fontVariantNumeric: "tabular-nums",
        }}>
          截止日: <span style={{ color: "var(--color-text-primary)" }}>{PERIOD_STATS.deadline}</span>
          {" | "}
          剩余 <span style={{ color: "var(--color-dept-compliance)" }}>{PERIOD_STATS.daysLeft}</span> 天
        </span>
      </section>

      {/* Main Content: Three Column Layout */}
      <section style={{ display: "flex", flex: 1 }}>
        {/* Col 1: VAT */}
        <div style={{ flex: 1, background: "var(--color-surface-container-low)", padding: "var(--space-8)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-8)" }}>
            <div>
              <h3 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", fontFamily: "var(--font-display)" }}>
                增值税 (VAT)
              </h3>
              <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: "var(--space-1)", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "1.5px" }}>
                Value Added Tax Registry
              </p>
            </div>
            <TaxBadge status="pending" />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            {VAT_LINES.map((line) => (
              <VatRow key={line.labelEn} label={line.label} labelEn={line.labelEn} amount={line.amount} />
            ))}
          </div>

          {/* Settlement Box */}
          <div style={{ paddingTop: "var(--space-8)", marginTop: "var(--space-4)" }}>
            <div style={{
              background: "var(--color-surface-container-lowest)",
              padding: "var(--space-6)",
              position: "relative",
              overflow: "hidden",
            }}>
              <div style={{
                position: "absolute",
                top: 0,
                right: 0,
                width: 64,
                height: 64,
                background: "rgba(197, 145, 62, 0.1)",
                transform: "translateX(32px) translateY(-32px) rotate(45deg)",
              }} />
              <span style={{
                fontSize: 10,
                fontWeight: 900,
                color: "var(--color-secondary)",
                textTransform: "uppercase" as const,
                letterSpacing: "2px",
                display: "block",
                marginBottom: "var(--space-2)",
              }}>
                Final Settlement
              </span>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--color-text-primary)" }}>应纳税额</span>
                <span style={{ fontSize: "1.875rem", fontWeight: 900, fontVariantNumeric: "tabular-nums", color: "var(--color-secondary)" }}>
                  {VAT_SETTLEMENT}
                </span>
              </div>
            </div>
          </div>

          {/* Warning */}
          <div style={{
            background: "rgba(196, 69, 54, 0.05)",
            padding: "var(--space-4)",
            display: "flex",
            alignItems: "flex-start",
            gap: "var(--space-3)",
            marginTop: "var(--space-4)",
          }}>
            <WarningIcon />
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--color-dept-compliance)" }}>2张异常发票</p>
              <p style={{ fontSize: 11, color: "rgba(196, 69, 54, 0.8)", lineHeight: 1.65, marginTop: "var(--space-1)" }}>
                检测到发票代码不匹配，请在提交申报前完成人工核对。
              </p>
            </div>
          </div>
        </div>

        {/* Col 2: CIT */}
        <div style={{ flex: 1, background: "var(--color-surface-container)", padding: "var(--space-8)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-8)" }}>
            <div>
              <h3 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", fontFamily: "var(--font-display)" }}>
                企业所得税 (CIT)
              </h3>
              <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: "var(--space-1)", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "1.5px" }}>
                Corporate Income Tax
              </p>
            </div>
            <TaxBadge status="filed" />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            {CIT_LINES.map((line) => (
              <div key={line.label} style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                padding: "var(--space-2) 0",
                borderBottom: "1px solid rgba(195, 198, 209, 0.3)",
                fontStyle: line.isAdjustment ? "italic" : "normal",
              }}>
                <span style={{
                  fontWeight: line.isAdjustment ? 500 : 700,
                  color: line.isAdjustment ? "var(--color-text-tertiary)" : "var(--color-text-secondary)",
                }}>
                  {line.label}
                </span>
                <span style={{
                  fontVariantNumeric: "tabular-nums",
                  fontWeight: 700,
                  color: line.isPositive ? "var(--color-dept-bookkeeping)" : "var(--color-text-primary)",
                }}>
                  {line.amount}
                </span>
              </div>
            ))}
          </div>

          {/* Taxable Income Box */}
          <div style={{ paddingTop: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div style={{ background: "var(--color-surface-container-low)", padding: "var(--space-4)" }}>
              <span style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--color-text-tertiary)",
                textTransform: "uppercase" as const,
                marginBottom: "var(--space-1)",
                display: "block",
              }}>
                Taxable Income
              </span>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontWeight: 700, color: "var(--color-text-primary)", fontSize: 14 }}>应纳所得额</span>
                <span style={{ fontSize: "1.25rem", fontWeight: 700, fontVariantNumeric: "tabular-nums", color: "var(--color-text-primary)" }}>
                  {CIT_TAXABLE}
                </span>
              </div>
            </div>

            {/* Final Liability */}
            <div style={{
              background: "var(--color-surface-container-lowest)",
              padding: "var(--space-4) var(--space-6)",
              borderLeft: "4px solid var(--color-secondary)",
            }}>
              <span style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--color-secondary)",
                textTransform: "uppercase" as const,
                marginBottom: "var(--space-1)",
                display: "block",
              }}>
                Final Liability
              </span>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--color-text-primary)" }}>应纳税额</span>
                <span style={{ fontSize: "1.5rem", fontWeight: 900, fontVariantNumeric: "tabular-nums", color: "var(--color-secondary)" }}>
                  {CIT_LIABILITY}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Col 3: PIT & Surcharges */}
        <div style={{ flex: 1, background: "var(--color-surface)", padding: "var(--space-8)" }}>
          <div style={{ marginBottom: "var(--space-8)" }}>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", fontFamily: "var(--font-display)" }}>
              附加及其他
            </h3>
            <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: "var(--space-1)", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "1.5px" }}>
              Payroll & Surcharge
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-8)" }}>
            {/* PIT Section */}
            <section>
              <SectionBar label="个人所得税 (PIT)" />
              <div style={{ background: "var(--color-surface-container-lowest)", padding: "var(--space-4)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-tertiary)" }}>代扣代缴总额</span>
                  <span style={{ fontSize: "1.25rem", fontWeight: 900, fontVariantNumeric: "tabular-nums", color: "var(--color-secondary)" }}>
                    {PIT_TOTAL}
                  </span>
                </div>
              </div>
            </section>

            {/* Surcharges Section */}
            <section>
              <SectionBar label="附加税费" />
              <div style={{ background: "var(--color-surface-container-lowest)" }}>
                {SURCHARGES.map((item, i) => (
                  <div key={item.label} style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "var(--space-3)",
                    borderBottom: i < SURCHARGES.length - 1 ? "1px solid rgba(195, 198, 209, 0.15)" : "none",
                  }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>{item.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, fontVariantNumeric: "tabular-nums", color: "var(--color-text-primary)" }}>{item.amount}</span>
                  </div>
                ))}
                {/* Subtotal */}
                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "var(--space-3)",
                  background: "var(--color-surface-container-low)",
                }}>
                  <span style={{ fontSize: 12, fontWeight: 900, color: "var(--color-text-primary)" }}>小计</span>
                  <span style={{ fontSize: 13, fontWeight: 900, fontVariantNumeric: "tabular-nums", color: "var(--color-secondary)" }}>
                    {SURCHARGES_TOTAL}
                  </span>
                </div>
              </div>
            </section>

            {/* Stamp Duty Section */}
            <section>
              <SectionBar label="印花税" />
              <div style={{ background: "var(--color-surface-container-lowest)", padding: "var(--space-4)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-tertiary)" }}>本期合计</span>
                  <span style={{ fontSize: "1.25rem", fontWeight: 900, fontVariantNumeric: "tabular-nums", color: "var(--color-secondary)" }}>
                    {STAMP_TOTAL}
                  </span>
                </div>
              </div>
            </section>
          </div>
        </div>
      </section>

      {/* Bottom Summary Strip */}
      <footer style={{
        height: 48,
        background: "var(--color-primary-deep)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-12)",
      }}>
        {SUMMARY_ITEMS.map((item) => (
          <div key={item.label} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <SummaryIcon type={item.label} />
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              color: "rgba(255,255,255,0.6)",
              letterSpacing: "1px",
              textTransform: "uppercase" as const,
              fontFamily: "var(--font-body)",
              fontVariantNumeric: "tabular-nums",
            }}>
              {item.label}:
            </span>
            <span style={{
              fontSize: 14,
              fontWeight: 700,
              fontVariantNumeric: "tabular-nums",
              color: item.isCurrency ? "var(--color-secondary)" : "#fff",
              fontFamily: "var(--font-body)",
            }}>
              {item.isCurrency ? `\u00A5 ${item.value}` : item.value}
            </span>
          </div>
        ))}
        {/* Status indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", color: "var(--color-secondary)" }}>
          <VerifiedIcon />
          <span style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "1px",
            textTransform: "uppercase" as const,
            fontFamily: "var(--font-body)",
            fontVariantNumeric: "tabular-nums",
          }}>
            状态: 实时数据核对中
          </span>
        </div>
      </footer>
    </div>
  );
}

// == Sub-components ===========================================================

function SecondaryBtn({ children }: { children: React.ReactNode }) {
  return (
    <button style={{
      background: "var(--color-surface-container)",
      color: "var(--color-text-primary)",
      fontWeight: 700,
      padding: "var(--space-3) var(--space-6)",
      fontSize: 13,
      border: "none",
      cursor: "pointer",
    }}>
      {children}
    </button>
  );
}

function StatusChip({ color, label }: { color: string; label: string }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "var(--space-2)",
      padding: "var(--space-1) var(--space-3)",
      background: `color-mix(in srgb, ${color} 10%, transparent)`,
    }}>
      <span style={{ width: 8, height: 8, background: color, display: "inline-block" }} />
      <span style={{ fontSize: 12, fontWeight: 700, color, fontVariantNumeric: "tabular-nums" }}>{label}</span>
    </div>
  );
}

function TaxBadge({ status }: { status: "filed" | "pending" | "overdue" }) {
  const config: Record<string, { bg: string; label: string }> = {
    filed: { bg: "var(--color-dept-bookkeeping)", label: "已申报" },
    pending: { bg: "var(--color-primary)", label: "待申报" },
    overdue: { bg: "var(--color-dept-compliance)", label: "逾期" },
  };
  const { bg, label } = config[status];
  return (
    <span style={{
      background: bg,
      color: "#fff",
      padding: "var(--space-1) var(--space-4)",
      fontSize: 10,
      fontWeight: 700,
    }}>
      {label}
    </span>
  );
}

function VatRow({ label, labelEn, amount }: { label: string; labelEn: string; amount: string }) {
  return (
    <div>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-end",
        borderBottom: "2px solid rgba(195, 198, 209, 0.3)",
        paddingBottom: "var(--space-2)",
      }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-tertiary)", textTransform: "uppercase" as const }}>
          {label} ({labelEn})
        </span>
        <span style={{ fontSize: "1.25rem", fontWeight: 700, fontVariantNumeric: "tabular-nums", color: "var(--color-text-primary)" }}>
          {amount}
        </span>
      </div>
    </div>
  );
}

function SectionBar({ label }: { label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
      <span style={{ width: 4, height: 16, background: "var(--color-text-primary)", display: "inline-block" }} />
      <h4 style={{ fontSize: 13, fontWeight: 900, color: "var(--color-text-primary)" }}>{label}</h4>
    </div>
  );
}

// == Inline SVG Icons =========================================================

function CalendarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="var(--color-text-primary)">
      <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM9 10H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="var(--color-dept-compliance)">
      <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
    </svg>
  );
}

function CheckIcon({ size = 14, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
    </svg>
  );
}

function VerifiedIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M23 12l-2.44-2.79.34-3.69-3.61-.82-1.89-3.2L12 2.96 8.6 1.5 6.71 4.69 3.1 5.5l.34 3.7L1 12l2.44 2.79-.34 3.7 3.61.82L8.6 22.5 12 21.04l3.4 1.46 1.89-3.19 3.61-.82-.34-3.69L23 12zm-12.91 4.72l-3.8-3.81 1.48-1.48 2.32 2.33 5.85-5.87 1.48 1.48-7.33 7.35z" />
    </svg>
  );
}

function SummaryIcon({ type }: { type: string }) {
  if (type === "合计金额") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="rgba(255,255,255,0.5)">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1.41 16.09V20h-2.67v-1.93c-1.71-.36-3.16-1.46-3.27-3.4h1.96c.1 1.05.82 1.87 2.65 1.87 1.96 0 2.4-.98 2.4-1.59 0-.83-.44-1.61-2.67-2.14-2.48-.6-4.18-1.62-4.18-3.67 0-1.72 1.39-2.84 3.11-3.21V4h2.67v1.95c1.86.45 2.79 1.86 2.85 3.39H14.3c-.05-1.11-.64-1.87-2.22-1.87-1.5 0-2.4.68-2.4 1.64 0 .84.65 1.39 2.67 1.94s4.18 1.36 4.18 3.85c0 1.89-1.44 2.96-3.12 3.19z" />
      </svg>
    );
  }
  if (type === "税额小计") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="rgba(255,255,255,0.5)">
        <path d="M18.5 3.5L20 5l-1.5 1.5L20 8l-1.5 1.5L20 11h-6V3h6l-1.5 1.5zM3.5 11h6V3h-6l1.5 1.5L3.5 6 5 7.5 3.5 9 5 10.5 3.5 11zM9.5 13v8h-6l1.5-1.5L3.5 18 5 16.5 3.5 15 5 13.5 3.5 13h6zm11 0l-1.5 1.5L20 15l-1.5 1.5L20 18l-1.5 1.5L20 21h-6v-8h6z" />
      </svg>
    );
  }
  // Default: pending actions
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="rgba(255,255,255,0.5)">
      <path d="M17 12c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zm1.65 7.35L16.5 17.2V14h1v2.79l1.85 1.85-.7.71zM18 3h-3.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H6c-1.1 0-2 .9-2 2v15c0 1.1.9 2 2 2h6.11c-.59-.57-1.07-1.25-1.42-2H6V5h2v3h8V5h2v5.08c.71.1 1.38.31 2 .6V5c0-1.1-.9-2-2-2zm-6 2c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z" />
    </svg>
  );
}
