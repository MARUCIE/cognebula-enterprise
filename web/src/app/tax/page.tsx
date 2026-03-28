/* Intelligent Tax -- "智能报税"
   Layout reference: design/stitch-export/stitch/intelligent_tax/screen.png
   All data is static mock for initial build. */

import { ToastButton } from "../components/ToastButton";

const pipelineSteps = [
  {
    name: "数据采集",
    description: "发票、银行流水已同步",
    icon: "folder",
    status: "done" as const,
    progress: 100,
  },
  {
    name: "智能核验",
    description: "正在进行税务合规性审查",
    icon: "check",
    status: "active" as const,
    progress: 67,
  },
  {
    name: "系统申报",
    description: "待核验完成后自动发起",
    icon: "send",
    status: "pending" as const,
    progress: 0,
  },
  {
    name: "申报完成",
    description: "等待税局回执",
    icon: "verified",
    status: "pending" as const,
    progress: 0,
  },
];

const reviewItems = [
  {
    title: "差旅发票存疑",
    description: "发票号码：77210034，金额 ¥4,200.00。AI 识别为非经营性支出，请核实其业务相关性。",
    severity: "high" as const,
    severityLabel: "高风险",
    action: "查看详情",
    updated: "15分钟前更新",
    bgColor: "color-mix(in srgb, var(--color-danger) 5%, transparent)",
    iconColor: "var(--color-danger)",
  },
  {
    title: "银行流水未对账",
    description: "存在一笔 ¥128,000.00 的入账缺少对应的业务合同样本，可能影响进项抵扣。",
    severity: "medium" as const,
    severityLabel: "待处理",
    action: "补录附件",
    updated: "1小时前更新",
    bgColor: "var(--color-surface-container)",
    iconColor: "var(--color-primary)",
  },
  {
    title: "研发费用加计扣除校验",
    description: "AI 识别到新的研发立项，是否将相关人力成本纳入本季申报范围？",
    severity: "low" as const,
    severityLabel: "建议核查",
    action: "立即确认",
    updated: "2小时前更新",
    bgColor: "var(--color-surface-container)",
    iconColor: "var(--color-primary)",
  },
];

const invoiceTable = [
  {
    number: "0032149582",
    seller: "北京宏达科技有限公司",
    date: "2024-09-12",
    category: "技术服务费",
    amount: "¥ 12,000.00",
    status: "pass" as const,
    statusLabel: "自动核验通过",
  },
  {
    number: "0032149583",
    seller: "上海润丰办公设备中心",
    date: "2024-09-15",
    category: "办公用品",
    amount: "¥ 1,240.00",
    status: "pass" as const,
    statusLabel: "自动核验通过",
  },
  {
    number: "0032149584",
    seller: "广州某某餐饮管理有限公司",
    date: "2024-09-18",
    category: "差旅餐费",
    amount: "¥ 4,200.00",
    status: "fail" as const,
    statusLabel: "需要人工干预",
  },
];

export default function IntelligentTaxPage() {
  return (
    <div>
      {/* ── Header with AI status ── */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-4)" }}>
          <div>
            <h2
              className="font-display font-extrabold"
              style={{ fontSize: 28, color: "var(--color-text-primary)", lineHeight: 1.3 }}
            >
              2024年Q3 季度税收申报进度
            </h2>
            <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0, marginTop: 4 }}>
              AI 正在根据最新的财务数据实时同步您的税务报表。
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span
              className="flex items-center gap-2 badge-info"
              style={{
                fontSize: 12,
                fontWeight: 600,
                padding: "6px 14px",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <span
                className="ai-glow"
                style={{
                  display: "inline-block",
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: "var(--color-primary)",
                }}
              />
              AI 正在处理
            </span>
            <div style={{ textAlign: "right" }}>
              <div
                style={{
                  fontSize: 10,
                  textTransform: "uppercase",
                  fontWeight: 700,
                  color: "var(--color-text-tertiary)",
                }}
              >
                截止日期
              </div>
              <div className="font-display font-bold" style={{ fontSize: 16, color: "var(--color-danger)" }}>
                2024-10-15
              </div>
            </div>
          </div>
        </div>

        {/* ── 4-stage pipeline ── */}
        <div
          className="grid gap-5"
          style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
        >
          {pipelineSteps.map((step) => (
            <PipelineStep key={step.name} step={step} />
          ))}
        </div>
      </section>

      {/* ── Two-column: Review queue + Advisor panel ── */}
      <section
        className="grid gap-8"
        style={{
          gridTemplateColumns: "1fr 320px",
          marginBottom: "var(--space-8)",
        }}
      >
        {/* Left: Review queue */}
        <div>
          <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-4)" }}>
            <h3
              className="font-display font-bold flex items-center gap-2"
              style={{ fontSize: 18, color: "var(--color-text-primary)" }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="var(--color-danger)" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
              </svg>
              待人工复核事项
            </h3>
            <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
              共 {reviewItems.length} 项异常
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {reviewItems.map((item) => (
              <ReviewCard key={item.title} item={item} />
            ))}
          </div>
        </div>

        {/* Right: AI advisor panel (320px) */}
        <div className="flex flex-col gap-6">
          {/* Summary card -- dark blue */}
          <div
            className="relative overflow-hidden"
            style={{
              padding: "var(--space-8)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-primary)",
              color: "var(--color-on-primary)",
            }}
          >
            {/* Decorative triangle */}
            <div
              className="absolute inset-0"
              style={{
                opacity: 0.06,
                background: "linear-gradient(135deg, transparent 50%, white 50%)",
                pointerEvents: "none",
              }}
            />

            <div className="relative" style={{ zIndex: 1 }}>
              <div className="flex items-center gap-2" style={{ marginBottom: "var(--space-6)" }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2l2.09 6.26L20.18 9l-5 4.09L16.18 20 12 16.77 7.82 20l1-6.91-5-4.09 6.09-.74L12 2z" stroke="var(--color-secondary)" strokeWidth="1.5" strokeLinejoin="round" />
                </svg>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    opacity: 0.8,
                  }}
                >
                  AI 税务简报
                </span>
              </div>

              <div style={{ marginBottom: "var(--space-4)" }}>
                <div style={{ fontSize: 13, opacity: 0.7 }}>预计应缴纳税额</div>
                <div
                  className="font-display font-extrabold tabular-nums"
                  style={{ fontSize: 36, letterSpacing: "-0.02em", marginTop: 4, textAlign: "left" }}
                >
                  &yen; 45,829.30
                </div>
              </div>

              <hr style={{ background: "rgba(255,255,255,0.15)", height: 1, margin: "var(--space-4) 0" }} />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div style={{ fontSize: 10, opacity: 0.6, textTransform: "uppercase" }}>增值税</div>
                  <div className="font-display font-bold tabular-nums" style={{ fontSize: 18, textAlign: "left" }}>
                    &yen; 32,100.00
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, opacity: 0.6, textTransform: "uppercase" }}>附加税</div>
                  <div className="font-display font-bold tabular-nums" style={{ fontSize: 18, textAlign: "left" }}>
                    &yen; 3,210.00
                  </div>
                </div>
              </div>

              <ToastButton
                message="报表已提交生成，预计 2 分钟完成"
                className="w-full flex items-center justify-center gap-2 font-medium"
                style={{
                  marginTop: "var(--space-6)",
                  padding: "12px 0",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--color-secondary)",
                  color: "var(--color-on-primary)",
                  fontSize: 14,
                }}
              >
                确认并生成报表
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </ToastButton>
            </div>
          </div>

          {/* Tax optimization suggestions */}
          <div
            style={{
              padding: "var(--space-6)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-low)",
              borderLeft: "4px solid var(--color-secondary)",
            }}
          >
            <h4
              className="font-display font-bold"
              style={{ fontSize: 14, marginBottom: "var(--space-4)", color: "var(--color-text-primary)" }}
            >
              税务优化建议
            </h4>
            <div className="flex flex-col gap-3">
              <SuggestionItem text="识别到 2 项符合高新企业减税政策的支出，建议更新资质。" />
              <SuggestionItem text="当前社保基数调整可节约本季人力成本约 ¥3,400。" />
            </div>
          </div>

          {/* Compliance radar */}
          <div
            className="flex flex-col items-center"
            style={{
              padding: "var(--space-6)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-lowest)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <div
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                color: "var(--color-text-secondary)",
                marginBottom: "var(--space-6)",
                alignSelf: "flex-start",
              }}
            >
              实时合规雷达
            </div>

            {/* Donut chart */}
            <div
              className="relative flex items-center justify-center"
              style={{ width: 120, height: 120, marginBottom: "var(--space-4)" }}
            >
              <svg width="120" height="120" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" fill="none" stroke="var(--color-surface-container)" strokeWidth="10" />
                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke="var(--color-primary)"
                  strokeWidth="10"
                  strokeDasharray={`${2 * Math.PI * 50 * 0.98} ${2 * Math.PI * 50 * 0.02}`}
                  strokeLinecap="round"
                  transform="rotate(-90 60 60)"
                />
              </svg>
              <div className="absolute text-center">
                <div
                  className="font-display font-extrabold"
                  style={{ fontSize: 24, color: "var(--color-primary)" }}
                >
                  98%
                </div>
                <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", fontWeight: 700 }}>
                  合规指数
                </div>
              </div>
            </div>

            <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", textAlign: "center", lineHeight: 1.6, margin: 0 }}>
              基于当前 1,204 条财务记录与最新税法实时比对
            </p>
          </div>
        </div>
      </section>

      {/* ── Invoice detail table ── */}
      <section
        style={{
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
          background: "var(--color-surface-container-lowest)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "var(--space-8)",
        }}
      >
        <div
          className="flex items-center justify-between"
          style={{
            padding: "var(--space-6) var(--space-8)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <h3
            className="font-display font-bold"
            style={{ fontSize: 16, color: "var(--color-text-primary)" }}
          >
            本期进项发票明细 (待核验)
          </h3>
          <ToastButton
            message="发票明细导出已提交"
            className="flex items-center gap-2 font-medium"
            style={{ fontSize: 13, color: "var(--color-primary)" }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            导出明细
          </ToastButton>
        </div>

        {/* Table header */}
        <div
          className="grid items-center"
          style={{
            gridTemplateColumns: "120px minmax(160px, 1.5fr) 100px 1fr 120px 140px",
            padding: "10px var(--space-8)",
            background: "var(--color-surface-container-low)",
            fontSize: 11,
            fontWeight: 700,
            textTransform: "uppercase" as const,
            color: "var(--color-text-secondary)",
          }}
        >
          <span>发票号码</span>
          <span>销方名称</span>
          <span>开票日期</span>
          <span>项目类型</span>
          <span style={{ textAlign: "right" }}>含税总计</span>
          <span style={{ textAlign: "right" }}>状态</span>
        </div>

        {/* Rows */}
        {invoiceTable.map((row, i) => (
          <div
            key={row.number}
            className="grid items-center table-row-hover"
            style={{
              gridTemplateColumns: "120px minmax(160px, 1.5fr) 100px 1fr 120px 140px",
              padding: "14px var(--space-8)",
              background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)",
              fontSize: 13,
            }}
          >
            <span
              className="font-mono"
              style={{
                color: row.status === "fail" ? "var(--color-danger)" : "var(--color-text-primary)",
              }}
            >
              {row.number}
            </span>
            <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>
              {row.seller}
            </span>
            <span style={{ color: "var(--color-text-secondary)" }}>{row.date}</span>
            <span style={{ color: "var(--color-text-secondary)" }}>{row.category}</span>
            <span
              className="font-medium tabular-nums"
              style={{
                textAlign: "right",
                color: "var(--color-text-primary)",
              }}
            >
              {row.amount}
            </span>
            <span style={{ textAlign: "right" }}>
              <span
                className={row.status === "pass" ? "badge-success" : "badge-danger"}
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {row.statusLabel}
              </span>
            </span>
          </div>
        ))}

        {/* Table footer */}
        <div
          className="flex justify-center"
          style={{
            padding: "var(--space-4)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <ToastButton
            message="完整发票列表即将上线"
            type="info"
            className="font-medium"
            style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}
          >
            查看全部 142 张发票
          </ToastButton>
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
   Sub-components (co-located, tax page specific)
   ================================================================ */

function PipelineStep({
  step,
}: {
  step: { name: string; description: string; icon: string; status: "done" | "active" | "pending"; progress: number };
}) {
  const isDone = step.status === "done";
  const isActive = step.status === "active";
  const isPending = step.status === "pending";

  return (
    <div
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: isPending ? "var(--color-surface-container-low)" : "var(--color-surface-container-lowest)",
        boxShadow: isActive ? "var(--shadow-ambient)" : "var(--shadow-sm)",
        opacity: isPending ? 0.55 : 1,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Top accent bar */}
      {(isDone || isActive) && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: 3,
            background: isDone ? "var(--color-secondary)" : "var(--color-primary)",
            opacity: isDone ? 0.3 : 1,
          }}
        />
      )}

      <div className="flex justify-between items-start" style={{ marginBottom: "var(--space-3)" }}>
        <div
          className="flex items-center justify-center"
          style={{
            width: 36,
            height: 36,
            borderRadius: "var(--radius-sm)",
            background: isActive
              ? "var(--color-primary)"
              : isDone
                ? "var(--color-surface-container)"
                : "var(--color-surface-container)",
          }}
        >
          <PipelineIcon name={step.icon} color={isActive ? "var(--color-on-primary)" : isDone ? "var(--color-secondary)" : "var(--color-text-tertiary)"} />
        </div>

        {isDone && (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M9 12l2 2 4-4" stroke="var(--color-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="12" cy="12" r="10" stroke="var(--color-secondary)" strokeWidth="1.8" />
          </svg>
        )}
        {isActive && (
          <span className="font-medium" style={{ fontSize: 12, color: "var(--color-primary)" }}>
            进行中
          </span>
        )}
      </div>

      <h4
        className="font-display font-bold"
        style={{ fontSize: 16, marginBottom: 4, color: "var(--color-text-primary)" }}
      >
        {step.name}
      </h4>
      <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", margin: 0 }}>
        {step.description}
      </p>

      {/* Progress bar */}
      {!isPending && (
        <div
          style={{
            marginTop: "var(--space-4)",
            height: 3,
            borderRadius: 2,
            background: "var(--color-surface-container)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${step.progress}%`,
              borderRadius: 2,
              background: isDone ? "var(--color-secondary)" : "var(--color-primary)",
            }}
          />
        </div>
      )}
    </div>
  );
}

function PipelineIcon({ name, color }: { name: string; color: string }) {
  switch (name) {
    case "folder":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M2 7V5a2 2 0 012-2h4l2 2h8a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V7z" stroke={color} strokeWidth="1.8" />
        </svg>
      );
    case "check":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M9 11l3 3 8-8" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M20 12v6a2 2 0 01-2 2H6a2 2 0 01-2-2V7a2 2 0 012-2h9" stroke={color} strokeWidth="1.8" />
        </svg>
      );
    case "send":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke={color} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
        </svg>
      );
    case "verified":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M9 12l2 2 4-4" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.8" />
        </svg>
      );
    default:
      return null;
  }
}

function ReviewCard({
  item,
}: {
  item: {
    title: string;
    description: string;
    severity: "high" | "medium" | "low";
    severityLabel: string;
    action: string;
    updated: string;
    bgColor: string;
    iconColor: string;
  };
}) {
  const badgeClass =
    item.severity === "high"
      ? "badge-danger"
      : item.severity === "medium"
        ? "badge-warning"
        : "badge-info";

  return (
    <div
      className="flex items-center gap-5"
      style={{
        padding: "var(--space-5, 1.25rem)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Icon */}
      <div
        className="flex items-center justify-center shrink-0"
        style={{
          width: 48,
          height: 48,
          borderRadius: "var(--radius-sm)",
          background: item.bgColor,
        }}
      >
        <ReviewItemIcon severity={item.severity} color={item.iconColor} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2" style={{ marginBottom: 4 }}>
          <span className="font-medium" style={{ fontSize: 14, color: "var(--color-text-primary)" }}>
            {item.title}
          </span>
          <span
            className={badgeClass}
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {item.severityLabel}
          </span>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.75 }}>
          {item.description}
        </p>
      </div>

      {/* Action */}
      <div className="flex flex-col items-end gap-2 shrink-0">
        <ToastButton
          message={`已处理「${item.title}」，AI 正在更新核验状态`}
          className="font-medium"
          style={{
            fontSize: 12,
            padding: "6px 14px",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-surface-container)",
            color: "var(--color-text-primary)",
          }}
        >
          {item.action}
        </ToastButton>
        <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>{item.updated}</span>
      </div>
    </div>
  );
}

function ReviewItemIcon({ severity, color }: { severity: string; color: string }) {
  if (severity === "high") {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M6 2h8l6 6v14H6z" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M14 2v6h6" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M12 10v4M12 18h.01" stroke={color} strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  if (severity === "medium") {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M4 4h16v16H4z" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M12 8v4M12 16h.01" stroke={color} strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.8" />
      <path d="M8 12l3 3 5-6" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SuggestionItem({ text }: { text: string }) {
  return (
    <div className="flex gap-3" style={{ fontSize: 13 }}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ marginTop: 3 }}>
        <path d="M9 18h6M12 2a7 7 0 00-3 13.33V18h6v-2.67A7 7 0 0012 2z" stroke="var(--color-secondary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span style={{ color: "var(--color-text-secondary)", lineHeight: 1.75 }}>{text}</span>
    </div>
  );
}
