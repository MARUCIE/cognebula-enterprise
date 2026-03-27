/* Dashboard -- "今日概览"
   Layout reference: design/stitch-export/stitch/dashboard/screen.png
   All data is static mock for initial build. */

export default function DashboardPage() {
  return (
    <div>
      {/* ── Welcome header ── */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <h2
          className="font-display font-extrabold"
          style={{
            fontSize: "1.75rem",
            lineHeight: 1.2,
            color: "var(--color-text-primary)",
            maxWidth: 480,
          }}
        >
          早上好，陈先生。
          <br />
          您的 AI 团队已处理 142 项任务。
        </h2>
      </section>

      {/* ── KPI cards row ── */}
      <section
        className="grid gap-5"
        style={{
          gridTemplateColumns: "repeat(4, 1fr)",
          marginBottom: "var(--space-8)",
        }}
      >
        <KpiCard
          icon={<ClientsIcon />}
          label="服务中客户"
          value="1,284"
          badge="+12% vs 年"
        />
        <KpiCard
          icon={<AutomationIcon />}
          label="AI 自动化完成率"
          value="82.5%"
        />
        <KpiCard
          icon={<ReviewIcon />}
          label="待人工审核"
          value="18"
          accent="warning"
        />
        {/* Gold savings card */}
        <div
          className="flex flex-col justify-center"
          style={{
            padding: "var(--space-4) var(--space-6)",
            borderRadius: "var(--radius-md)",
            background: "linear-gradient(135deg, #FDF6EB 0%, #F9EDD8 100%)",
            minHeight: 120,
          }}
        >
          <span
            style={{
              fontSize: 11,
              color: "var(--color-secondary-dim)",
              marginBottom: 4,
              fontWeight: 500,
            }}
          >
            今日预估节省
          </span>
          <span
            className="font-display font-bold tabular-nums"
            style={{ fontSize: 28, color: "var(--color-secondary-dim)", textAlign: "left" }}
          >
            &yen;12.4k
          </span>
        </div>
      </section>

      {/* ── Approval table (action-first: before activity feed) ── */}
      <section
        style={{
          padding: "var(--space-6)",
          borderRadius: "var(--radius-md)",
          background: "var(--color-surface-container-lowest)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "var(--space-8)",
        }}
      >
        <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-6)" }}>
          <h3
            className="font-display font-semibold"
            style={{ fontSize: 16, color: "var(--color-text-primary)" }}
          >
            关键审批事项
          </h3>
          <div className="flex items-center gap-4" style={{ fontSize: 13 }}>
            <button className="font-medium" style={{ color: "var(--color-primary)" }}>
              待筛审批 (12)
            </button>
            <button style={{ color: "var(--color-text-tertiary)" }}>已完成</button>
          </div>
        </div>

        {/* Table -- No-Line Rule: use background color shifts, no borders */}
        <div style={{ borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
          {/* Header */}
          <div
            className="grid items-center"
            style={{
              gridTemplateColumns: "minmax(200px, 1.2fr) 1fr 1fr 140px 100px",
              padding: "10px 16px",
              background: "var(--color-surface-container-low)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase" as const,
            }}
          >
            <span>客户名称</span>
            <span>事项类型</span>
            <span>AI 建议</span>
            <span>更新时间</span>
            <span style={{ textAlign: "right" }}>操作</span>
          </div>

          {/* Rows */}
          <ApprovalRow
            initials="LH"
            initialsColor="var(--color-dept-tax)"
            name="联合创新贸易有限公司"
            type="高额认定费用核算"
            suggestion="建议通过"
            suggestionStatus="success"
            time="2024-10-15 14:22"
          />
          <ApprovalRow
            initials="YF"
            initialsColor="var(--color-warning)"
            name="云峰智源股份"
            type="跨省税收协定确认"
            suggestion="人工干预"
            suggestionStatus="warning"
            time="2024-10-15 11:05"
            rowAlt
          />
          <ApprovalRow
            initials="SC"
            initialsColor="var(--color-dept-client)"
            name="时代传媒有限公司"
            type="月度进项税额抵扣"
            suggestion="建议调整"
            suggestionStatus="danger"
            time="2024-10-15 09:48"
          />
        </div>
      </section>

      {/* ── Two-column: Activity feed + Reports ── */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "1fr 320px",
          marginBottom: "var(--space-8)",
        }}
      >
        {/* Activity feed */}
        <div
          style={{
            padding: "var(--space-6)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-6)" }}>
            <h3
              className="font-display font-semibold"
              style={{ fontSize: 16, color: "var(--color-text-primary)" }}
            >
              实时 AI 活动动态
            </h3>
            <span
              className="flex items-center gap-2"
              style={{
                fontSize: 11,
                fontWeight: 600,
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                background: "color-mix(in srgb, var(--color-success) 10%, transparent)",
                color: "var(--color-success)",
              }}
            >
              <span
                className="ai-glow"
                style={{
                  display: "inline-block",
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "var(--color-success)",
                }}
              />
              处理中
            </span>
          </div>
          <p style={{ fontSize: 13, color: "var(--color-text-tertiary)", marginBottom: "var(--space-6)" }}>
            3 位 AI 专员正在并发工作中
          </p>

          <div className="flex flex-col gap-4">
            <ActivityItem
              avatar="T1"
              avatarColor="var(--color-dept-tax)"
              name="智能申报专员 Tax-01"
              task="正在处理 上海鸿腾科技有限公司 2024 Q3 销项税核验"
              status="progress"
              statusLabel="正在核算"
              href="/ai-team/lin-shui-an"
            />
            <ActivityItem
              avatar="A4"
              avatarColor="var(--color-dept-bookkeeping)"
              name="审计校验专员 Audit-04"
              task="已验证 北京万事金业 分公司年度支出 127 笔异常项中 42 项"
              status="progress"
              statusLabel="数据调验"
              href="/ai-team/zhang-shen-he"
            />
            <ActivityItem
              avatar="R2"
              avatarColor="var(--color-primary)"
              name="报告生成专员 Report-02"
              task="完成 深圳微波智能科技 8月存货审核 月报企业资产评估"
              status="done"
              statusLabel="已就绪"
              href="/ai-team/chen-shui-ce"
            />
          </div>
        </div>

        {/* Recent reports */}
        <div
          style={{
            padding: "var(--space-6)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-6)" }}>
            <h3
              className="font-display font-semibold"
              style={{ fontSize: 16, color: "var(--color-text-primary)" }}
            >
              近期报告
            </h3>
            <button
              style={{
                fontSize: 12,
                color: "var(--color-primary)",
                fontWeight: 500,
              }}
            >
              全部 &rarr;
            </button>
          </div>
          <div className="flex flex-col gap-4">
            <ReportItem
              title="2024Q3 集团税务风险评估"
              meta="完成 2小时前 - 4.2MB"
            />
            <ReportItem
              title="华南审计银信汇清账底稿"
              meta="完成 昨天 16:30 - 12.9MB"
            />
            <ReportItem
              title="各省子公司纳税数据透视"
              meta="完成 10/12/1 - 1.5MB"
            />
          </div>

          {/* Expert consultation CTA */}
          <div
            style={{
              marginTop: "var(--space-6)",
              padding: "var(--space-4)",
              borderRadius: "var(--radius-md)",
              background: "linear-gradient(135deg, #FDF6EB 0%, #F9EDD8 100%)",
            }}
          >
            <p
              className="font-display font-semibold"
              style={{ fontSize: 14, color: "var(--color-secondary-dim)", marginBottom: 4 }}
            >
              需要专家解读？
            </p>
            <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 12, lineHeight: 1.6 }}>
              AI 生成的报告含财税知识，您可以让智能财税顾问进行 1 对 1 深度咨询。
            </p>
            <button
              className="font-medium"
              style={{
                fontSize: 12,
                padding: "6px 16px",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-secondary)",
                color: "var(--color-on-primary)",
              }}
            >
              立即咨询
            </button>
          </div>
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
   Sub-components (co-located, dashboard-specific)
   ================================================================ */

function KpiCard({
  icon,
  label,
  value,
  badge,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  badge?: string;
  accent?: "warning";
}) {
  return (
    <div
      className="flex flex-col justify-between"
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
        minHeight: 120,
      }}
    >
      <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-3)" }}>
        <span style={{ color: "var(--color-primary)", opacity: 0.7 }}>{icon}</span>
        {badge && (
          <span
            className="badge-info"
            style={{
              fontSize: 10,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {badge}
          </span>
        )}
        {accent === "warning" && (
          <span
            className="badge-warning"
            style={{
              fontSize: 10,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            需关注
          </span>
        )}
      </div>
      <div>
        <span
          style={{
            display: "block",
            fontSize: 12,
            color: "var(--color-text-tertiary)",
            marginBottom: 4,
          }}
        >
          {label}
        </span>
        <span
          className="font-display font-bold tabular-nums"
          style={{
            fontSize: 32,
            color: accent === "warning" ? "var(--color-warning)" : "var(--color-text-primary)",
            lineHeight: 1.1,
            textAlign: "left",
          }}
        >
          {value}
        </span>
      </div>
    </div>
  );
}

function ActivityItem({
  avatar,
  avatarColor,
  name,
  task,
  status,
  statusLabel,
  href,
}: {
  avatar: string;
  avatarColor: string;
  name: string;
  task: string;
  status: "progress" | "done";
  statusLabel: string;
  href?: string;
}) {
  const Wrapper = href ? "a" : "div";
  return (
    <Wrapper
      {...(href ? { href } : {})}
      className="flex items-start gap-4"
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-sm)",
        background: "var(--color-surface)",
        textDecoration: "none",
        color: "inherit",
        display: "flex",
      }}
    >
      <div
        className="flex items-center justify-center shrink-0 font-medium"
        style={{
          width: 36,
          height: 36,
          borderRadius: "var(--radius-sm)",
          background: avatarColor,
          color: "var(--color-on-primary)",
          fontSize: 12,
        }}
      >
        {avatar}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3" style={{ marginBottom: 4 }}>
          <span className="font-medium" style={{ fontSize: 13, color: "var(--color-text-primary)" }}>
            {name}
          </span>
          <span
            className={status === "done" ? "badge-success" : "badge-info"}
            style={{
              fontSize: 10,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              whiteSpace: "nowrap",
            }}
          >
            {statusLabel}
          </span>
        </div>
        <p
          style={{
            fontSize: 12,
            color: "var(--color-text-secondary)",
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          {task}
        </p>
      </div>
    </Wrapper>
  );
}

function ReportItem({ title, meta }: { title: string; meta: string }) {
  return (
    <div
      className="flex items-start gap-3"
      style={{
        padding: "var(--space-3)",
        borderRadius: "var(--radius-sm)",
      }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        className="shrink-0"
        style={{ marginTop: 2 }}
      >
        <path d="M6 2h8l6 6v14H6z" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M14 2v6h6" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinejoin="round" />
      </svg>
      <div>
        <p className="font-medium" style={{ fontSize: 13, color: "var(--color-text-primary)", margin: 0, marginBottom: 2 }}>
          {title}
        </p>
        <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", margin: 0 }}>{meta}</p>
      </div>
    </div>
  );
}

function ApprovalRow({
  initials,
  initialsColor,
  name,
  type,
  suggestion,
  suggestionStatus,
  time,
  rowAlt,
}: {
  initials: string;
  initialsColor: string;
  name: string;
  type: string;
  suggestion: string;
  suggestionStatus: "success" | "warning" | "danger";
  time: string;
  rowAlt?: boolean;
}) {
  const badgeClass =
    suggestionStatus === "success"
      ? "badge-success"
      : suggestionStatus === "warning"
        ? "badge-warning"
        : "badge-danger";

  return (
    <div
      className="grid items-center table-row-hover"
      style={{
        gridTemplateColumns: "minmax(200px, 1.2fr) 1fr 1fr 140px 100px",
        padding: "14px 16px",
        background: rowAlt ? "var(--color-surface)" : "var(--color-surface-container-lowest)",
        fontSize: 13,
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center shrink-0 font-medium"
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: initialsColor,
            color: "var(--color-on-primary)",
            fontSize: 11,
          }}
        >
          {initials}
        </div>
        <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>
          {name}
        </span>
      </div>
      <span style={{ color: "var(--color-text-secondary)" }}>{type}</span>
      <span>
        <span
          className={badgeClass}
          style={{
            fontSize: 11,
            fontWeight: 600,
            padding: "3px 10px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {suggestion}
        </span>
      </span>
      <span className="tabular-nums" style={{ color: "var(--color-text-tertiary)", fontSize: 12 }}>
        {time}
      </span>
      <span style={{ textAlign: "right" }}>
        <button
          className="font-medium"
          style={{
            fontSize: 12,
            color: "var(--color-primary)",
            padding: "4px 0",
          }}
        >
          查看详情
        </button>
      </span>
    </div>
  );
}

/* ── Inline SVG icons for KPI cards ── */

function ClientsIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="7" r="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3 20c0-3 2.5-5.5 6-5.5s6 2.5 6 5.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="17" cy="8" r="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M18.5 14c2 .7 3 2 3 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function AutomationIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M4 4h16v16H4z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M8 12l3 3 5-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReviewIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 7v5l3.5 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
