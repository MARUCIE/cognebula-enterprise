/* Report Detail -- "/reports/[id]"
   Jobs: "AI置信度+源追溯+变动高亮, NOT a PDF viewer"
   Drucker: "价值闭环的核心证明——AI生成+人工审批的完整动作" */

import Link from "next/link";
import { REPORT_IDS, getReportById } from "../../lib/reports";
import { ToastButton } from "../../components/ToastButton";

export function generateStaticParams() {
  return REPORT_IDS.map((id) => ({ id }));
}

export default async function ReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = getReportById(id);
  if (!report) return <div>报告不存在</div>;

  const r = report;
  const isFlagged = r.status === "flagged";
  const isAi = r.status === "ai";
  const confidenceColor =
    r.confidence >= 95
      ? "var(--color-success)"
      : r.confidence >= 90
        ? "var(--color-warning)"
        : "var(--color-danger)";

  return (
    <div>
      {/* ── Back + Header ── */}
      <div className="flex items-center gap-3" style={{ marginBottom: "var(--space-4)" }}>
        <Link
          href="/reports"
          style={{ fontSize: 12, color: "var(--color-primary)", textDecoration: "none", fontWeight: 600 }}
        >
          &larr; 返回报告列表
        </Link>
      </div>

      <section
        className="flex items-start justify-between"
        style={{ marginBottom: "var(--space-6)" }}
      >
        <div>
          <h2
            className="font-display font-bold"
            style={{ fontSize: 20, color: "var(--color-text-primary)", lineHeight: 1.3 }}
          >
            {r.company} — {r.period} {r.reportType}
          </h2>
          <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginTop: 4 }}>
            {r.status === "ai" ? "AI 生成" : r.status === "reviewed" ? "已人工复核" : "需关注"} · {r.date} · &yen;{r.amount}
          </p>
        </div>
        <div className="flex gap-3">
          <ToastButton
            message="PDF 导出已提交，预计 30 秒完成"
            className="font-bold"
            style={{
              fontSize: 12,
              padding: "8px 20px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-lowest)",
              color: "var(--color-primary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            导出 PDF
          </ToastButton>
          <ToastButton
            message="已发送至客户邮箱，请在通知中心查看状态"
            className="font-bold"
            style={{
              fontSize: 12,
              padding: "8px 20px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-lowest)",
              color: "var(--color-primary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            发送给客户
          </ToastButton>
          {(isAi || isFlagged) && (
            <ToastButton
              message="报告已批准，状态已更新为「已人工复核」"
              className="font-bold"
              style={{
                fontSize: 12,
                padding: "8px 20px",
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-container) 100%)",
                color: "var(--color-on-primary)",
              }}
            >
              ✓ 批准
            </ToastButton>
          )}
        </div>
      </section>

      {/* ── Confidence + Review strip ── */}
      <section
        className="grid"
        style={{ gridTemplateColumns: "1fr 1fr 2fr", gap: 12, marginBottom: "var(--space-6)" }}
      >
        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            background: `color-mix(in srgb, ${confidenceColor} 6%, var(--color-surface-container-lowest))`,
          }}
        >
          <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 4 }}>
            AI 置信度
          </p>
          <span
            className="font-display font-bold tabular-nums"
            style={{ fontSize: 28, color: confidenceColor }}
          >
            {r.confidence}%
          </span>
        </div>
        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            background: r.reviewItems > 0
              ? "color-mix(in srgb, var(--color-warning) 6%, var(--color-surface-container-lowest))"
              : "var(--color-surface-container-lowest)",
          }}
        >
          <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 4 }}>
            需人工确认
          </p>
          <span
            className="font-display font-bold tabular-nums"
            style={{
              fontSize: 28,
              color: r.reviewItems > 0 ? "var(--color-warning)" : "var(--color-success)",
            }}
          >
            {r.reviewItems}
          </span>
          <span style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginLeft: 4 }}>处</span>
        </div>
        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            borderLeft: "3px solid var(--color-secondary)",
          }}
        >
          <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 6 }}>
            AI 摘要
          </p>
          <p style={{ fontSize: 12, color: "var(--color-text-primary)", lineHeight: 1.7 }}>
            {r.aiSummary}
          </p>
        </div>
      </section>

      {/* ── Change Highlights (Jobs: "变动高亮") ── */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h3
          className="font-display font-bold"
          style={{ fontSize: 16, color: "var(--color-text-primary)", marginBottom: "var(--space-4)" }}
        >
          变动高亮 ({r.highlights.length} 项)
        </h3>
        <div className="flex flex-col gap-3">
          {r.highlights.map((h, i) => {
            const isUp = h.changePercent > 0;
            const isAlert = Math.abs(h.changePercent) >= 20;
            const changeColor = isAlert
              ? (isUp ? "var(--color-secondary-dim)" : "var(--color-danger)")
              : "var(--color-text-secondary)";

            return (
              <div
                key={i}
                style={{
                  padding: "16px 20px",
                  borderRadius: "var(--radius-md)",
                  background: isAlert
                    ? `color-mix(in srgb, ${changeColor} 4%, var(--color-surface-container-lowest))`
                    : "var(--color-surface-container-lowest)",
                  borderLeft: isAlert ? `3px solid ${changeColor}` : "3px solid transparent",
                }}
              >
                <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
                  <span className="font-bold" style={{ fontSize: 14, color: "var(--color-text-primary)" }}>
                    {h.label}
                  </span>
                  <div className="flex items-center gap-4">
                    <span
                      className="tabular-nums font-display font-bold"
                      style={{ fontSize: 16, color: "var(--color-text-primary)" }}
                    >
                      {h.currentValue}
                    </span>
                    <span
                      className="tabular-nums font-bold"
                      style={{ fontSize: 12, color: changeColor }}
                    >
                      {isUp ? "↑" : "↓"} {Math.abs(h.changePercent)}%
                    </span>
                  </div>
                </div>
                <p style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
                  <span style={{ color: "var(--color-primary)", fontWeight: 600, marginRight: 6 }}>AI:</span>
                  {h.aiNote}
                </p>
                <p style={{ fontSize: 10, color: "var(--color-text-tertiary)", marginTop: 4 }}>
                  上期: {h.prevValue}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        className="text-center"
        style={{ padding: "var(--space-8) 0 var(--space-4)", color: "var(--color-text-tertiary)", fontSize: 11 }}
      >
        <p>安全加密数据环境 -- 灵阙 AI 引擎 V2.4</p>
        <p>&copy; 2024 灵阙财税科技. All rights reserved.</p>
      </footer>
    </div>
  );
}

