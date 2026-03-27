/* Financial Reporting Center -- "财务报告中心"
   Layout reference: design/stitch-export/stitch/financial_reporting_center/screen.png
   All data is static mock for initial build. */

export default function ReportsCenterPage() {
  return (
    <div>
      {/* ── KPI dashboard row ── */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "repeat(3, 1fr)",
          marginBottom: "var(--space-8)",
        }}
      >
        <ReportKpi
          label="本月生成报告"
          value="1,284"
          trend="较上月增长 12%"
          trendColor="var(--color-secondary-dim)"
          bgIcon={<DocBgIcon />}
        />
        <ReportKpi
          label="AI 准确率"
          value="99.8%"
          trend="处于行业领先水平"
          trendColor="var(--color-tertiary)"
          bgIcon={<VerifiedBgIcon />}
        />
        <ReportKpi
          label="待复核任务"
          value="42"
          trend="包含 5 个紧急项目"
          trendColor="var(--color-danger)"
          bgIcon={<HourglassBgIcon />}
        />
      </section>

      {/* ── Report table section ── */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        {/* Table header */}
        <div
          className="flex justify-between items-end"
          style={{ marginBottom: "var(--space-4)" }}
        >
          <div>
            <h3
              className="font-display font-bold"
              style={{ fontSize: 22, color: "var(--color-text-primary)" }}
            >
              实时报告列表
            </h3>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
              智能引擎实时监控并生成的财务摘要
            </p>
          </div>
          <div className="flex gap-3">
            <button
              className="flex items-center gap-2 font-semibold"
              style={{
                fontSize: 13,
                padding: "8px 16px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-surface-container-lowest)",
                color: "var(--color-primary)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <FilterIcon />
              筛选
            </button>
            <button
              className="flex items-center gap-2 font-semibold"
              style={{
                fontSize: 13,
                padding: "8px 16px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-surface-container-lowest)",
                color: "var(--color-primary)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <DownloadIcon />
              批量导出
            </button>
            <button
              className="flex items-center gap-2 font-bold"
              style={{
                fontSize: 13,
                padding: "8px 20px",
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-container) 100%)",
                color: "var(--color-on-primary)",
              }}
            >
              全部批准
            </button>
          </div>
        </div>

        {/* Table -- No-Line Rule: background color shifts only */}
        <div
          style={{
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
          }}
        >
          {/* Column headers */}
          <div
            className="grid items-center"
            style={{
              gridTemplateColumns: "minmax(240px, 1.5fr) 160px 180px 1fr 100px",
              padding: "12px 24px",
              background: "var(--color-surface-container-low)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase" as const,
            }}
          >
            <span>客户名称 / 报告类型</span>
            <span>生成日期</span>
            <span>状态</span>
            <span style={{ textAlign: "right" }}>资产总计 (CNY)</span>
            <span style={{ textAlign: "center" }}>操作</span>
          </div>

          {/* Rows */}
          {REPORTS.map((r, i) => (
            <ReportRow key={r.company + r.reportType} {...r} alt={i % 2 === 1} />
          ))}
        </div>
      </section>

      {/* ── Bento: AI anomaly detection + Export center ── */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "3fr 1fr",
          marginBottom: "var(--space-8)",
        }}
      >
        {/* AI anomaly detection panel */}
        <div
          style={{
            padding: "var(--space-8)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
            borderRadius: "var(--radius-md)",
            borderTop: "2px solid var(--color-secondary)",
            position: "relative",
          }}
        >
          <div
            className="flex justify-between items-start"
            style={{ marginBottom: "var(--space-6)" }}
          >
            <div>
              <h4
                className="font-display font-bold"
                style={{ fontSize: 18, color: "var(--color-primary-deep)" }}
              >
                AI 异常检测分析
              </h4>
              <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>
                基于深度学习的财务数据健康监测
              </p>
            </div>
            <SparklesIcon />
          </div>

          <div
            className="grid gap-8"
            style={{ gridTemplateColumns: "1fr 1fr" }}
          >
            {/* Insight cards */}
            <div className="flex flex-col gap-4">
              <InsightCard
                type="risk"
                label="风险提示"
                text="检测到中铁建设集团的现金流与往期相比存在 15% 的异常偏移，建议人工核实。"
              />
              <InsightCard
                type="compliance"
                label="合规性"
                text="当前 95% 的报告已完成增值税法合规性检查。"
              />
            </div>

            {/* Trend visualization */}
            <div
              className="flex flex-col items-center justify-center"
              style={{
                background: "var(--color-surface-container-low)",
                borderRadius: "var(--radius-sm)",
                position: "relative",
                overflow: "hidden",
                minHeight: 160,
              }}
            >
              {/* Bar chart (decorative) */}
              <div
                className="flex items-end justify-around gap-3"
                style={{
                  position: "absolute",
                  inset: 0,
                  padding: "0 32px 16px",
                  opacity: 0.25,
                }}
              >
                {BARS.map((h, i) => (
                  <div
                    key={i}
                    style={{
                      width: 28,
                      height: h,
                      background: i % 2 === 0 ? "var(--color-primary)" : "var(--color-secondary)",
                      borderRadius: "2px 2px 0 0",
                    }}
                  />
                ))}
              </div>
              <span
                style={{
                  position: "relative",
                  zIndex: 1,
                  fontSize: 10,
                  fontWeight: 700,
                  textTransform: "uppercase" as const,
                  letterSpacing: "0.12em",
                  color: "var(--color-text-secondary)",
                }}
              >
                趋势分析
              </span>
            </div>
          </div>
        </div>

        {/* Export center sidebar */}
        <div
          className="flex flex-col justify-between"
          style={{
            padding: "var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-primary-deep)",
            color: "var(--color-on-primary)",
          }}
        >
          <div>
            <h4
              className="font-display font-bold"
              style={{ fontSize: 18, marginBottom: "var(--space-6)" }}
            >
              快速导出中心
            </h4>
            <ul className="flex flex-col gap-4">
              <ExportItem icon={<PdfIcon />} label="PDF 标准财报" />
              <ExportItem icon={<ExcelIcon />} label="Excel 完整明细" />
              <ExportItem icon={<AiReportIcon />} label="AI 智能解读报告" />
            </ul>
          </div>
          <button
            className="font-bold"
            style={{
              marginTop: "var(--space-8)",
              width: "100%",
              fontSize: 11,
              padding: "10px 0",
              borderRadius: "var(--radius-sm)",
              background: "rgba(255, 255, 255, 0.08)",
              color: "var(--color-on-primary)",
              textTransform: "uppercase" as const,
            }}
          >
            管理导出路径
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        className="text-center"
        style={{
          padding: "var(--space-12) 0 var(--space-8)",
          color: "var(--color-text-tertiary)",
          fontSize: 12,
        }}
      >
        <p>安全加密数据环境 -- 灵阙 AI 引擎 V2.4</p>
        <p style={{ marginTop: 4, opacity: 0.7 }}>&copy; 2024 灵阙财税科技. All rights reserved.</p>
      </footer>
    </div>
  );
}

/* ================================================================
   Mock data
   ================================================================ */

const BARS = [96, 128, 64, 80, 112, 48, 100];

type ReportRowData = {
  company: string;
  reportType: string;
  reportTypeEn: string;
  date: string;
  status: "ai" | "reviewed" | "flagged";
  statusLabel: string;
  amount: string;
};

const REPORTS: ReportRowData[] = [
  {
    company: "中铁建设集团有限公司",
    reportType: "资产负债表",
    reportTypeEn: "Asset Balance Sheet",
    date: "2024-11-24 14:20",
    status: "ai",
    statusLabel: "AI 生成",
    amount: "45,280,000.00",
  },
  {
    company: "阿里巴巴（中国）网络技术",
    reportType: "损益表",
    reportTypeEn: "Profit & Loss Statement",
    date: "2024-11-24 10:15",
    status: "reviewed",
    statusLabel: "已人工复核",
    amount: "128,450,200.00",
  },
  {
    company: "腾讯科技（深圳）有限公司",
    reportType: "现金流量表",
    reportTypeEn: "Cash Flow Statement",
    date: "2024-11-23 16:45",
    status: "flagged",
    statusLabel: "需关注",
    amount: "92,000,540.00",
  },
  {
    company: "美团点评（北京）科技有限公司",
    reportType: "年度财务摘要",
    reportTypeEn: "Annual Summary",
    date: "2024-11-23 09:00",
    status: "ai",
    statusLabel: "AI 生成",
    amount: "34,120,000.00",
  },
  {
    company: "华为技术有限公司",
    reportType: "月度税务报告",
    reportTypeEn: "Monthly Tax Report",
    date: "2024-11-22 17:30",
    status: "reviewed",
    statusLabel: "已人工复核",
    amount: "215,800,000.00",
  },
  {
    company: "京东世纪贸易有限公司",
    reportType: "季度审计报告",
    reportTypeEn: "Quarterly Audit Report",
    date: "2024-11-22 11:00",
    status: "flagged",
    statusLabel: "需关注",
    amount: "67,340,800.00",
  },
  {
    company: "比亚迪股份有限公司",
    reportType: "年度财务报告",
    reportTypeEn: "Annual Financial Report",
    date: "2024-11-21 15:45",
    status: "ai",
    statusLabel: "AI 生成",
    amount: "189,560,000.00",
  },
];

/* ================================================================
   Sub-components (co-located, page-specific)
   ================================================================ */

function ReportKpi({
  label,
  value,
  trend,
  trendColor,
  bgIcon,
}: {
  label: string;
  value: string;
  trend: string;
  trendColor: string;
  bgIcon: React.ReactNode;
}) {
  return (
    <div
      style={{
        padding: "var(--space-8)",
        background: "var(--color-surface-container-low)",
        borderRadius: "var(--radius-md)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ position: "absolute", top: 16, right: 16, opacity: 0.08 }}>
        {bgIcon}
      </div>
      <p
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: "var(--color-text-secondary)",
          marginBottom: "var(--space-2)",
        }}
      >
        {label}
      </p>
      <h3
        className="font-display font-extrabold tabular-nums"
        style={{
          fontSize: 36,
          color: "var(--color-primary-deep)",
          lineHeight: 1.1,
        }}
      >
        {value}
      </h3>
      <div
        className="flex items-center gap-2"
        style={{
          marginTop: "var(--space-4)",
          fontSize: 12,
          fontWeight: 600,
          color: trendColor,
        }}
      >
        <TrendIcon />
        <span>{trend}</span>
      </div>
    </div>
  );
}

function ReportRow({
  company,
  reportType,
  reportTypeEn,
  date,
  status,
  statusLabel,
  amount,
  alt,
}: ReportRowData & { alt?: boolean }) {
  return (
    <div
      className="grid items-center"
      style={{
        gridTemplateColumns: "minmax(240px, 1.5fr) 160px 180px 1fr 100px",
        padding: "16px 24px",
        background: alt ? "var(--color-surface)" : "var(--color-surface-container-lowest)",
        fontSize: 13,
      }}
    >
      {/* Company + report type */}
      <div>
        <span className="font-bold" style={{ color: "var(--color-text-primary)", display: "block" }}>
          {company}
        </span>
        <span style={{ fontSize: 11, color: "var(--color-text-tertiary)", display: "block", marginTop: 2 }}>
          {reportType} ({reportTypeEn})
        </span>
      </div>

      {/* Date */}
      <span
        className="tabular-nums"
        style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)", textAlign: "left" }}
      >
        {date}
      </span>

      {/* Status badge */}
      <span>
        <StatusBadge status={status} label={statusLabel} />
      </span>

      {/* Amount */}
      <span
        className="font-display font-bold tabular-nums"
        style={{ color: "var(--color-text-primary)", textAlign: "right" }}
      >
        &yen;{amount}
      </span>

      {/* Action */}
      <span style={{ textAlign: "center" }}>
        <button
          className="font-bold flex items-center justify-center gap-1"
          style={{ fontSize: 12, color: "var(--color-secondary)", margin: "0 auto" }}
        >
          查看详情
          <ChevronRightIcon />
        </button>
      </span>
    </div>
  );
}

function StatusBadge({ status, label }: { status: "ai" | "reviewed" | "flagged"; label: string }) {
  if (status === "ai") {
    return (
      <span
        className="inline-flex items-center gap-1"
        style={{
          fontSize: 10,
          fontWeight: 700,
          padding: "4px 10px",
          borderRadius: "var(--radius-sm)",
          background: "var(--color-primary-fixed)",
          color: "var(--color-primary)",
        }}
      >
        <span
          className="ai-glow"
          style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--color-primary)",
          }}
        />
        {label}
      </span>
    );
  }

  if (status === "reviewed") {
    return (
      <span
        className="badge-success inline-flex items-center gap-1"
        style={{
          fontSize: 10,
          fontWeight: 700,
          padding: "4px 10px",
          borderRadius: "var(--radius-sm)",
        }}
      >
        <CheckIcon />
        {label}
      </span>
    );
  }

  return (
    <span
      className="badge-danger inline-flex items-center gap-1"
      style={{
        fontSize: 10,
        fontWeight: 700,
        padding: "4px 10px",
        borderRadius: "var(--radius-sm)",
      }}
    >
      <WarningIcon />
      {label}
    </span>
  );
}

function InsightCard({
  type,
  label,
  text,
}: {
  type: "risk" | "compliance";
  label: string;
  text: string;
}) {
  const borderColor = type === "risk" ? "var(--color-secondary)" : "var(--color-primary)";
  const labelColor = borderColor;

  return (
    <div
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-sm)",
        background: "var(--color-surface-container)",
        borderLeft: `2px solid ${borderColor}`,
      }}
    >
      <p
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: labelColor,
          marginBottom: "var(--space-1)",
        }}
      >
        {label}
      </p>
      <p
        className="font-medium"
        style={{ fontSize: 13, color: "var(--color-text-primary)", lineHeight: 1.75 }}
      >
        {text}
      </p>
    </div>
  );
}

function ExportItem({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <li
      className="flex items-center gap-3"
      style={{ fontSize: 13, cursor: "pointer" }}
    >
      {icon}
      <span>{label}</span>
    </li>
  );
}

/* ── Inline SVG icons ── */

function FilterIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M4 6h16M6 12h12M9 18h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 4v12M8 12l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function TrendIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M7 17l5-5 3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 10h6v6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <path d="M12 9v4M12 17h.01" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M10.3 3.2L1.8 18.5a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.2a2 2 0 00-3.4 0z" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function SparklesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="var(--color-secondary)">
      <path d="M12 2l1.5 5.5L19 9l-5.5 1.5L12 16l-1.5-5.5L5 9l5.5-1.5z" />
      <path d="M18 14l.8 2.8L22 18l-3.2.8L18 22l-.8-3.2L14 18l3.2-.8z" opacity="0.6" />
    </svg>
  );
}

function DocBgIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 2h8l6 6v14H6z" />
    </svg>
  );
}

function VerifiedBgIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l2.4 4.8L20 8l-4 3.8.9 5.2-4.9-2.6L7.1 17l.9-5.2L4 8l5.6-1.2z" />
    </svg>
  );
}

function HourglassBgIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 2h12v4l-4 4 4 4v4H6v-4l4-4-4-4z" />
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M6 2h8l6 6v14H6z" stroke="var(--color-secondary)" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke="var(--color-secondary)" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function ExcelIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="2" stroke="var(--color-secondary)" strokeWidth="1.5" />
      <path d="M3 9h18M3 15h18M9 3v18" stroke="var(--color-secondary)" strokeWidth="1.5" />
    </svg>
  );
}

function AiReportIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="var(--color-secondary)" strokeWidth="1.5" />
      <path d="M12 7v5l3 2" stroke="var(--color-secondary)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
