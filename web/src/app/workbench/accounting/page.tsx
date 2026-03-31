"use client";

// Design: design/accounting-workbench/accounting-workbench.html (Stitch Heritage Monolith)
// Architecture: .stitch/DESIGN.md — Zero-Radius, Zero-Shadow, Tonal Layering
// Route: /workbench/accounting

import { useState } from "react";

// ── Invoice data (demo) ─────────────────────────────────────────────────────

type InvoiceStatus = "done" | "processing" | "warning" | "pending";

interface Invoice {
  id: string;
  number: string;
  party: string;
  amount: string;
  tax: string;
  total: string;
  status: InvoiceStatus;
}

const INVOICES: Invoice[] = [
  { id: "1", number: "01234567", party: "四川聚清诚建设→成都市朋诚鑫盛", amount: "41,283.19", tax: "5,366.81", total: "46,650.00", status: "done" },
  { id: "2", number: "01234568", party: "简阳丰印象广告→联合创新贸易", amount: "8,490.57", tax: "509.43", total: "9,000.00", status: "done" },
  { id: "3", number: "01234569", party: "中唯耘源建设→四川省永绘企业", amount: "4,906.43", tax: "637.83", total: "5,544.26", status: "processing" },
  { id: "4", number: "01234570", party: "成都朋诚鑫盛→恒升投资管理", amount: "12,831.86", tax: "1,668.14", total: "14,500.00", status: "processing" },
  { id: "5", number: "01234571", party: "简阳丰印象→时代传媒有限", amount: "2,654.87", tax: "345.13", total: "3,000.00", status: "warning" },
  { id: "6", number: "01234572", party: "中唯耘源建设→大唐信息技术", amount: "18,584.07", tax: "2,415.93", total: "21,000.00", status: "pending" },
  { id: "7", number: "01234573", party: "成都朋诚鑫盛→鑫海物流集团", amount: "7,079.65", tax: "920.35", total: "8,000.00", status: "pending" },
  { id: "8", number: "01234574", party: "四川聚清诚建设→云峰智源股份", amount: "31,415.93", tax: "4,084.07", total: "35,500.00", status: "pending" },
];

const STATUS_COLORS: Record<InvoiceStatus, string> = {
  done: "var(--color-dept-bookkeeping)",
  processing: "var(--color-primary)",
  warning: "var(--color-secondary)",
  pending: "var(--color-text-tertiary)",
};

// ── Pipeline steps ──────────────────────────────────────────────────────────

const STEPS = [
  { label: "① 解析", done: true },
  { label: "② 分类", done: true },
  { label: "③ 生成", active: true },
  { label: "④ 校验" },
  { label: "⑤ 审核" },
];

// ── Journal entry (demo for selected invoice) ───────────────────────────────

const JOURNAL_LINES = [
  { code: "1122005", name: "应收账款_四川省永绘企业管理有限公司", debit: "5,544.26", credit: "" },
  { code: "5001001", name: "主营业务收入_销售收入", debit: "", credit: "4,906.43" },
  { code: "222100106", name: "应交税费_应交增值税_销项税额", debit: "", credit: "637.83" },
];

// ── Component ───────────────────────────────────────────────────────────────

export default function AccountingWorkbenchPage() {
  const [selectedId, setSelectedId] = useState("3");

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
            WORKBENCH / ACCOUNTING
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <h1 style={{
            fontSize: "1.5rem",
            fontWeight: 800,
            color: "var(--color-text-primary)",
            fontFamily: "var(--font-display)",
          }}>
            核算工作台
          </h1>
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button className="btn-primary" style={{
              background: "var(--gradient-cta)",
              color: "#fff",
              fontWeight: 700,
              padding: "var(--space-2) var(--space-4)",
              fontSize: "13px",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "var(--space-1)",
            }}>
              <UploadIcon /> 导入发票
            </button>
            <SecondaryBtn>本月汇总</SecondaryBtn>
            <SecondaryBtn>科目表</SecondaryBtn>
            <SecondaryBtn>凭证模板</SecondaryBtn>
          </div>
        </div>
      </section>

      {/* Pipeline Status Bar */}
      <section style={{
        height: 56,
        background: "var(--color-surface-container-lowest)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 var(--space-8)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-6)", height: "100%" }}>
          {STEPS.map((s, i) => (
            <div key={i} style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-1)",
              fontSize: 12,
              fontWeight: 700,
              height: "100%",
              ...(s.active ? {
                background: "var(--color-primary)",
                color: "#fff",
                padding: "0 var(--space-4)",
              } : s.done ? {
                color: "var(--color-dept-bookkeeping)",
              } : {
                color: "var(--color-text-tertiary)",
                opacity: 0.6,
              }),
            }}>
              {s.done && <CheckIcon />}
              {s.label}
            </div>
          ))}
        </div>
        <span style={{ fontSize: 12, color: "var(--color-text-secondary)", fontFamily: "var(--font-body)" }}>
          本批次: <b style={{ fontVariantNumeric: "tabular-nums" }}>12/20</b> 张发票 | 预计剩余: <b style={{ fontVariantNumeric: "tabular-nums" }}>~30s</b>
        </span>
      </section>

      {/* Main Content: 60/40 split */}
      <section style={{ display: "flex", flex: 1 }}>
        {/* LEFT: Invoice Queue (60%) */}
        <div style={{ width: "60%", background: "var(--color-surface)", display: "flex", flexDirection: "column" }}>
          {/* Table Header */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "60px 140px 1fr 100px 80px 110px",
            background: "var(--color-surface-container-low)",
            padding: "var(--space-2) var(--space-8)",
          }}>
            {["状态", "发票号码", "购方 / 销方", "金额", "税额", "价税合计"].map((h, i) => (
              <div key={h} style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--color-text-secondary)",
                textTransform: "uppercase" as const,
                letterSpacing: "1px",
                textAlign: i >= 3 ? "right" as const : "left" as const,
              }}>
                {h}
              </div>
            ))}
          </div>

          {/* Invoice Rows */}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {INVOICES.map((inv, i) => {
              const isSelected = inv.id === selectedId;
              const isEven = i % 2 === 0;
              return (
                <div
                  key={inv.id}
                  onClick={() => setSelectedId(inv.id)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "60px 140px 1fr 100px 80px 110px",
                    padding: "0 var(--space-8)",
                    height: 48,
                    alignItems: "center",
                    cursor: "pointer",
                    background: isSelected
                      ? "#D5E3FF"
                      : isEven
                        ? "var(--color-surface-container-lowest)"
                        : "var(--color-surface)",
                    transition: "background 0.15s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "center" }}>
                    <div style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: STATUS_COLORS[inv.status],
                    }} />
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{inv.number}</div>
                  <div style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const, lineHeight: 1.65 }}>{inv.party}</div>
                  <div style={{ fontSize: 13, fontVariantNumeric: "tabular-nums", textAlign: "right" }}>¥{inv.amount}</div>
                  <div style={{ fontSize: 13, fontVariantNumeric: "tabular-nums", textAlign: "right" }}>¥{inv.tax}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, fontVariantNumeric: "tabular-nums", textAlign: "right" }}>¥{inv.total}</div>
                </div>
              );
            })}
          </div>

          {/* Upload Drop Zone */}
          <div style={{
            margin: "var(--space-8)",
            height: 80,
            background: "var(--color-surface-container-low)",
            border: "1px dashed rgba(195, 198, 209, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "var(--space-4)",
            cursor: "pointer",
          }}>
            <CloudUploadIcon />
            <div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>拖拽发票文件到此处，或点击选择</div>
              <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>支持 Excel / PDF / 图片，可批量上传</div>
            </div>
          </div>
        </div>

        {/* RIGHT: Journal Entry Preview (40%) */}
        <div style={{
          width: "40%",
          background: "var(--color-surface-container-lowest)",
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Title Bar */}
          <div style={{ padding: "var(--space-4) var(--space-6)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <h2 style={{ fontSize: 14, fontWeight: 700, fontFamily: "var(--font-display)", color: "var(--color-text-primary)" }}>
                凭证预览
              </h2>
              <span style={{
                padding: "2px 8px",
                background: "#FDF6EB",
                color: "#815600",
                fontSize: 10,
                fontWeight: 800,
              }}>
                记-1
              </span>
              <span style={{
                padding: "2px 8px",
                background: "rgba(27, 122, 78, 0.1)",
                color: "var(--color-dept-bookkeeping)",
                fontSize: 10,
                fontWeight: 800,
                display: "flex",
                alignItems: "center",
                gap: 2,
              }}>
                <CheckIcon size={10} /> 已校验
              </span>
            </div>
          </div>

          {/* Metadata Strip */}
          <div style={{
            padding: "var(--space-2) var(--space-6)",
            background: "var(--color-surface-container-low)",
            fontSize: 12,
            color: "var(--color-text-secondary)",
            display: "flex",
            gap: "var(--space-3)",
          }}>
            <span>日期: 2026-01-31</span>
            <span style={{ opacity: 0.3 }}>|</span>
            <span>附件: 1张</span>
            <span style={{ opacity: 0.3 }}>|</span>
            <span>规则: JR001</span>
          </div>

          {/* Ledger */}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {/* Summary Row */}
            <div style={{
              padding: "var(--space-3) var(--space-6)",
              background: "var(--color-surface-container-low)",
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-text-primary)",
              lineHeight: 1.65,
            }}>
              销售软饮料和方便食品
            </div>

            {/* Column Headers */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr 1fr",
              background: "var(--color-surface-container-low)",
            }}>
              {["科目编码", "科目名称", "借方", "贷方"].map((h, i) => (
                <div key={h} style={{
                  padding: "var(--space-2) var(--space-3)",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "var(--color-text-secondary)",
                  textTransform: "uppercase" as const,
                  textAlign: i >= 2 ? "right" as const : "left" as const,
                }}>
                  {h}
                </div>
              ))}
            </div>

            {/* Entry Lines */}
            {JOURNAL_LINES.map((line, i) => (
              <div key={line.code} style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr 1fr",
                background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)",
              }}>
                <div style={{ padding: "var(--space-3)", fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{line.code}</div>
                <div style={{ padding: "var(--space-3)", fontSize: 12, lineHeight: 1.65 }}>{line.name}</div>
                <div style={{ padding: "var(--space-3)", fontSize: 12, fontVariantNumeric: "tabular-nums", textAlign: "right", fontWeight: line.debit ? 700 : 400 }}>
                  {line.debit}
                </div>
                <div style={{ padding: "var(--space-3)", fontSize: 12, fontVariantNumeric: "tabular-nums", textAlign: "right", fontWeight: line.credit ? 700 : 400 }}>
                  {line.credit}
                </div>
              </div>
            ))}

            {/* Total Row */}
            <div style={{
              margin: "var(--space-4) 0 0 0",
              padding: "var(--space-4) var(--space-6)",
              background: "#FDF6EB",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <CheckIcon color="var(--color-dept-bookkeeping)" />
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-dept-bookkeeping)" }}>借贷平衡</span>
              </div>
              <span style={{
                fontSize: 14,
                fontWeight: 700,
                color: "var(--color-secondary)",
                fontVariantNumeric: "tabular-nums",
              }}>
                ¥ 5,544.26
              </span>
            </div>

            {/* Validation Panel */}
            <div style={{
              margin: "var(--space-6)",
              padding: "var(--space-4) var(--space-6)",
              background: "var(--color-surface)",
            }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: "var(--space-3)" }}>校验结果</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-start" }}>
                  <WarningIcon />
                  <span style={{ fontSize: 12, lineHeight: 1.75, color: "var(--color-text-secondary)" }}>
                    WARN: 科目 1122005 未在客户科目表中注册
                  </span>
                </div>
                <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-start" }}>
                  <InfoIcon />
                  <span style={{ fontSize: 12, lineHeight: 1.75, color: "var(--color-text-secondary)" }}>
                    NOTE: 适用小企业会计准则第59条
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{
            padding: "var(--space-4) var(--space-6)",
            display: "flex",
            gap: "var(--space-3)",
          }}>
            <button style={{
              background: "var(--color-dept-bookkeeping)",
              color: "#fff",
              padding: "var(--space-3) var(--space-6)",
              fontWeight: 700,
              fontSize: 13,
              border: "none",
              cursor: "pointer",
            }}>
              通过
            </button>
            <button style={{
              background: "var(--color-surface-container)",
              color: "var(--color-text-primary)",
              padding: "var(--space-3) var(--space-6)",
              fontWeight: 700,
              fontSize: 13,
              border: "none",
              cursor: "pointer",
            }}>
              修改
            </button>
            <button style={{
              background: "transparent",
              color: "var(--color-dept-compliance)",
              padding: "var(--space-3) var(--space-6)",
              fontWeight: 700,
              fontSize: 13,
              border: "none",
              cursor: "pointer",
            }}>
              拒绝
            </button>
          </div>
        </div>
      </section>

      {/* Bottom Summary Strip */}
      <footer style={{
        position: "sticky",
        bottom: 0,
        zIndex: 10,
        height: 48,
        background: "var(--color-primary-deep)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-12)",
      }}>
        {[
          { label: "本月发票", value: "45张" },
          { label: "生成凭证", value: "42笔" },
          { label: "借方合计", value: "¥1,234,567.89" },
          { label: "贷方合计", value: "¥1,234,567.89" },
        ].map((m, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.7)", letterSpacing: "1px" }}>{m.label}</span>
            <span style={{
              fontSize: 14,
              fontWeight: 700,
              color: m.value.includes("¥") ? "var(--color-secondary)" : "#fff",
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

function UploadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function CheckIcon({ size = 16, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
    </svg>
  );
}

function CloudUploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 16V8m0 0l-3 3m3-3l3 3" />
      <path d="M20 16.7428C21.2215 15.734 22 14.2195 22 12.5C22 9.46243 19.5376 7 16.5 7C16.2815 7 16.0771 6.886 15.9661 6.69774C14.6621 4.48484 12.2544 3 9.5 3C5.35786 3 2 6.35786 2 10.5C2 12.5661 2.83545 14.4371 4.18695 15.7935" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="var(--color-secondary)">
      <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="var(--color-primary)">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
    </svg>
  );
}

function SecondaryBtn({ children }: { children: React.ReactNode }) {
  return (
    <button style={{
      background: "var(--color-surface-container)",
      color: "var(--color-text-primary)",
      fontWeight: 700,
      padding: "var(--space-2) var(--space-4)",
      fontSize: 13,
      border: "none",
      cursor: "pointer",
    }}>
      {children}
    </button>
  );
}
