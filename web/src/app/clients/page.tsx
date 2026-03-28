/* Client Center -- "客户中心"
   Layout reference: design/stitch-export/stitch/client_center/screen.png
   All data is static mock for initial build. */

import Link from "next/link";
import { ToastButton } from "../components/ToastButton";

export default function ClientCenterPage() {
  return (
    <div>
      {/* ── Page header ── */}
      <section
        className="flex justify-between items-end"
        style={{ marginBottom: "var(--space-8)" }}
      >
        <div>
          <h2
            className="font-display font-extrabold"
            style={{
              fontSize: "1.875rem",
              lineHeight: 1.2,
              color: "var(--color-text-primary)",
            }}
          >
            客户概览
          </h2>
          <p
            style={{
              fontSize: 13,
              color: "var(--color-text-secondary)",
              marginTop: "var(--space-2)",
            }}
          >
            管理并追踪您名下的 128 位签约客户财税进度
          </p>
        </div>
        <div className="flex gap-3">
          <ToastButton
            message="筛选面板即将上线"
            type="info"
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
            高级筛选
          </ToastButton>
          <ToastButton
            message="新客户录入流程即将上线"
            type="info"
            className="flex items-center gap-2 font-bold"
            style={{
              fontSize: 13,
              padding: "8px 20px",
              borderRadius: "var(--radius-md)",
              background: "linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-container) 100%)",
              color: "var(--color-on-primary)",
            }}
          >
            <PersonAddIcon />
            新增客户账户
          </ToastButton>
        </div>
      </section>

      {/* ── Stats cards ── */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "repeat(4, 1fr)",
          marginBottom: "var(--space-8)",
        }}
      >
        <StatCard
          label="活跃客户"
          value="1,240"
          trend="+12% 本月"
          trendColor="var(--color-success)"
          bgIcon={<GroupsIcon />}
          valueColor="var(--color-primary)"
        />
        <StatCard
          label="待审核申报"
          value="42"
          trend="需本周完成"
          trendColor="var(--color-warning)"
          bgIcon={<PendingIcon />}
          valueColor="var(--color-secondary-dim)"
        />
        <StatCard
          label="AI 智能合规率"
          value="99.8%"
          trend="高于行业均值"
          trendColor="var(--color-success)"
          bgIcon={<VerifiedIcon />}
          valueColor="var(--color-primary)"
        />
        <StatCard
          label="预计节税额"
          value="&yen;8.4M"
          trend="为客户创造价值"
          trendColor="var(--color-secondary-dim)"
          bgIcon={<SavingsIcon />}
          valueColor="var(--color-secondary-dim)"
        />
      </section>

      {/* ── Client table ── */}
      <section
        style={{
          borderRadius: "var(--radius-md)",
          background: "var(--color-surface-container-low)",
          boxShadow: "var(--shadow-sm)",
          overflow: "hidden",
          marginBottom: "var(--space-12)",
        }}
      >
        {/* Table header bar */}
        <div
          className="flex justify-between items-center"
          style={{
            padding: "var(--space-4) var(--space-6)",
            background: "var(--color-surface-container)",
          }}
        >
          <h3
            className="font-display font-bold flex items-center gap-2"
            style={{ fontSize: 14, color: "var(--color-text-primary)" }}
          >
            <DatabaseIcon />
            客户档案数据库
          </h3>
          <div className="flex gap-4" style={{ fontSize: 11, fontWeight: 500, color: "var(--color-text-secondary)" }}>
            <span className="flex items-center gap-1">
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-success)", display: "inline-block" }} />
              已完成
            </span>
            <span className="flex items-center gap-1">
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-warning)", display: "inline-block" }} />
              进行中
            </span>
            <span className="flex items-center gap-1">
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-primary)", display: "inline-block" }} />
              待审核
            </span>
          </div>
        </div>

        {/* Table header */}
        <div
          className="grid items-center"
          style={{
            gridTemplateColumns: "minmax(220px, 1.5fr) 1fr 140px 120px 100px",
            padding: "12px 24px",
            background: "var(--color-surface-container-low)",
            fontSize: 11,
            fontWeight: 700,
            color: "var(--color-text-secondary)",
            textTransform: "uppercase" as const,
          }}
        >
          <span>客户名称 / 行业</span>
          <span>负责 AI 助手</span>
          <span>最后申报日期</span>
          <span>合规状态</span>
          <span style={{ textAlign: "right" }}>操作</span>
        </div>

        {/* Rows */}
        {CLIENTS.map((c, i) => (
          <ClientRow key={c.name} {...c} alt={i % 2 === 1} />
        ))}

        {/* Pagination */}
        <div
          className="flex justify-between items-center"
          style={{
            padding: "var(--space-4) var(--space-6)",
            background: "var(--color-surface-container-low)",
            fontSize: 12,
            color: "var(--color-text-tertiary)",
          }}
        >
          <span>显示 1 到 8 条，共 128 条客户记录</span>
          <div className="flex gap-1">
            <PaginationBtn label="<" />
            <PaginationBtn label="1" active />
            <PaginationBtn label="2" />
            <PaginationBtn label="3" />
            <PaginationBtn label="..." />
            <PaginationBtn label=">" />
          </div>
        </div>
      </section>

      {/* ── AI Insight bento section ── */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "2fr 1fr",
          marginBottom: "var(--space-8)",
        }}
      >
        {/* Insight hero card */}
        <div
          style={{
            padding: "var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "linear-gradient(135deg, var(--color-primary-deep) 0%, var(--color-primary-container) 100%)",
            color: "var(--color-on-primary)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div style={{ position: "relative", zIndex: 1 }}>
            <div
              className="flex items-center gap-2"
              style={{ marginBottom: "var(--space-4)" }}
            >
              <SparklesIcon color="var(--color-secondary)" />
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: "uppercase" as const,
                }}
              >
                AI 智能洞察
              </span>
            </div>
            <h3
              className="font-display font-bold"
              style={{ fontSize: 24, marginBottom: "var(--space-4)" }}
            >
              本月发现 3 个税务优化机会
            </h3>
            <p
              style={{
                fontSize: 13,
                lineHeight: 1.75,
                opacity: 0.85,
                maxWidth: 520,
              }}
            >
              基于 2024 年第四季度最新的研发费用加计扣除政策，我们已识别出"极智科技"等
              5 位客户存在申报优化的空间，预计可额外减免税额约 &yen;240,000。
            </p>
            <ToastButton
              message="AI 正在生成优化建议书，预计 3 分钟完成"
              className="font-bold"
              style={{
                marginTop: "var(--space-6)",
                fontSize: 13,
                padding: "10px 24px",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-secondary)",
                color: "var(--color-on-primary)",
              }}
            >
              立即生成优化建议书
            </ToastButton>
          </div>
          {/* Background decorative icon */}
          <div
            style={{
              position: "absolute",
              right: "-5%",
              top: "-15%",
              opacity: 0.06,
              fontSize: 240,
              lineHeight: 1,
              fontWeight: 900,
              color: "var(--color-on-primary)",
              pointerEvents: "none" as const,
            }}
          >
            AI
          </div>
        </div>

        {/* System compliance check card */}
        <div
          className="flex flex-col justify-between"
          style={{
            padding: "var(--space-6)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div>
            <h3
              className="font-display font-bold"
              style={{ fontSize: 16, color: "var(--color-text-primary)", marginBottom: 4 }}
            >
              系统合规性检查
            </h3>
            <p style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
              所有客户账户当前运行状况良好
            </p>
          </div>

          {/* Ring gauge */}
          <div className="flex justify-center" style={{ padding: "var(--space-6) 0" }}>
            <div style={{ position: "relative", width: 128, height: 128 }}>
              <svg width="128" height="128" viewBox="0 0 128 128" style={{ transform: "rotate(-90deg)" }}>
                <circle
                  cx="64" cy="64" r="54"
                  fill="transparent"
                  stroke="var(--color-surface-container)"
                  strokeWidth="8"
                />
                <circle
                  cx="64" cy="64" r="54"
                  fill="transparent"
                  stroke="var(--color-primary)"
                  strokeWidth="8"
                  strokeDasharray={`${2 * Math.PI * 54}`}
                  strokeDashoffset={`${2 * Math.PI * 54 * 0.05}`}
                  strokeLinecap="round"
                />
              </svg>
              <div
                className="flex flex-col items-center justify-center"
                style={{
                  position: "absolute",
                  inset: 0,
                }}
              >
                <span
                  className="font-display font-extrabold"
                  style={{ fontSize: 24, color: "var(--color-text-primary)" }}
                >
                  95%
                </span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: "var(--color-text-tertiary)",
                    textTransform: "uppercase" as const,
                  }}
                >
                  安全指数
                </span>
              </div>
            </div>
          </div>

          <Link
            href="/compliance"
            className="font-bold"
            style={{
              display: "block",
              width: "100%",
              fontSize: 12,
              padding: "8px 0",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface-container-low)",
              color: "var(--color-primary)",
              textDecoration: "none",
              textAlign: "center",
            }}
          >
            查看完整诊断报告
          </Link>
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

const CLIENTS: ClientRowProps[] = [
  {
    id: "zhongtie-jianshe",
    initial: "中",
    initialColor: "var(--color-dept-tax)",
    name: "中铁建设集团有限公司",
    industry: "基础建设 / 大型国企",
    agent: "灵阙智税-01",
    agentDept: "tax",
    lastDate: "2024-11-15",
    status: "done",
    statusLabel: "已完成",
  },
  {
    id: "alibaba-wangluo",
    initial: "阿",
    initialColor: "var(--color-dept-bookkeeping)",
    name: "阿里巴巴（中国）网络技术",
    industry: "互联网科技 / 一般纳税人",
    agent: "灵阙审计-04",
    agentDept: "bookkeeping",
    lastDate: "2024-11-12",
    status: "review",
    statusLabel: "待审核",
  },
  {
    id: "tengxun-keji",
    initial: "腾",
    initialColor: "var(--color-dept-client)",
    name: "腾讯科技（深圳）有限公司",
    industry: "互联网科技 / 上市企业",
    agent: "灵阙智税-02",
    agentDept: "tax",
    lastDate: "2024-11-10",
    status: "progress",
    statusLabel: "进行中",
  },
  {
    id: "meituan-dianping",
    initial: "美",
    initialColor: "var(--color-dept-compliance)",
    name: "美团点评（北京）科技有限公司",
    industry: "生活服务 / 上市企业",
    agent: "灵阙合规-01",
    agentDept: "compliance",
    lastDate: "2024-10-31",
    status: "done",
    statusLabel: "已完成",
  },
  {
    id: "shenzhen-jizhi",
    initial: "深",
    initialColor: "var(--color-dept-tax)",
    name: "深圳极智科技有限公司",
    industry: "高新信息技术 / 一般纳税人",
    agent: "灵阙智税-01",
    agentDept: "tax",
    lastDate: "2024-10-28",
    status: "done",
    statusLabel: "已完成",
  },
  {
    id: "huaxia-maoyi",
    initial: "华",
    initialColor: "var(--color-secondary-dim)",
    name: "华夏贸易进出口有限公司",
    industry: "跨境电商 / 外资企业",
    agent: "灵阙审计-04",
    agentDept: "bookkeeping",
    lastDate: "2024-10-25",
    status: "review",
    statusLabel: "待审核",
  },
  {
    id: "guangying-chuanmei",
    initial: "光",
    initialColor: "var(--color-tertiary)",
    name: "光影传媒艺术工作室",
    industry: "文化创意 / 小规模纳税人",
    agent: "灵阙智税-02",
    agentDept: "tax",
    lastDate: "2024-10-20",
    status: "progress",
    statusLabel: "进行中",
  },
  {
    id: "taihe-yanglao",
    initial: "泰",
    initialColor: "var(--color-dept-client)",
    name: "泰和养老服务集团",
    industry: "医疗健康 / 连锁经营",
    agent: "灵阙智税-01",
    agentDept: "tax",
    lastDate: "2024-10-15",
    status: "done",
    statusLabel: "已完成",
  },
];

/* ================================================================
   Sub-components (co-located, page-specific)
   ================================================================ */

function StatCard({
  label,
  value,
  trend,
  trendColor,
  bgIcon,
  valueColor,
}: {
  label: string;
  value: string;
  trend: string;
  trendColor: string;
  bgIcon: React.ReactNode;
  valueColor: string;
}) {
  return (
    <div
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-low)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ position: "relative", zIndex: 1 }}>
        <p
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: "var(--color-text-secondary)",
            textTransform: "uppercase" as const,
            marginBottom: "var(--space-2)",
          }}
        >
          {label}
        </p>
        <h4
          className="font-display font-extrabold tabular-nums"
          style={{ fontSize: 30, color: valueColor, lineHeight: 1.1 }}
          dangerouslySetInnerHTML={{ __html: value }}
        />
        <div
          className="flex items-center gap-1"
          style={{
            marginTop: "var(--space-4)",
            fontSize: 12,
            fontWeight: 600,
            color: trendColor,
          }}
        >
          <TrendUpIcon />
          <span>{trend}</span>
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          right: -12,
          bottom: -12,
          opacity: 0.05,
          color: valueColor,
          pointerEvents: "none" as const,
        }}
      >
        {bgIcon}
      </div>
    </div>
  );
}

type ClientRowProps = {
  id: string;
  initial: string;
  initialColor: string;
  name: string;
  industry: string;
  agent: string;
  agentDept: string;
  lastDate: string;
  status: "done" | "progress" | "review";
  statusLabel: string;
  alt?: boolean;
};

function ClientRow({
  id,
  initial,
  initialColor,
  name,
  industry,
  agent,
  lastDate,
  status,
  statusLabel,
  alt,
}: ClientRowProps) {
  const statusBadge =
    status === "done"
      ? "badge-success"
      : status === "review"
        ? "badge-info"
        : "badge-warning";

  return (
    <div
      className="grid items-center table-row-hover"
      style={{
        gridTemplateColumns: "minmax(220px, 1.5fr) 1fr 140px 120px 100px",
        padding: "16px 24px",
        background: alt ? "var(--color-surface-container-lowest)" : "var(--color-surface)",
        fontSize: 13,
      }}
    >
      {/* Company */}
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center shrink-0 font-bold"
          style={{
            width: 36,
            height: 36,
            borderRadius: "var(--radius-sm)",
            background: `color-mix(in srgb, ${initialColor} 12%, transparent)`,
            color: initialColor,
            fontSize: 14,
          }}
        >
          {initial}
        </div>
        <div>
          <span className="font-bold" style={{ color: "var(--color-text-primary)", display: "block" }}>
            {name}
          </span>
          <span style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: 2, display: "block" }}>
            {industry}
          </span>
        </div>
      </div>

      {/* Agent */}
      <div className="flex items-center gap-2">
        <AgentIcon />
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-primary)" }}>{agent}</span>
      </div>

      {/* Date */}
      <span className="tabular-nums" style={{ fontSize: 12, color: "var(--color-text-tertiary)", textAlign: "left" }}>
        {lastDate}
      </span>

      {/* Status */}
      <span>
        <span
          className={statusBadge}
          style={{
            fontSize: 10,
            fontWeight: 700,
            padding: "3px 10px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {statusLabel}
        </span>
      </span>

      {/* Action */}
      <span style={{ textAlign: "right" }}>
        <Link
          href={`/clients/${id}`}
          className="font-bold"
          style={{ fontSize: 12, color: "var(--color-primary)", textDecoration: "none" }}
        >
          查看详情 &rarr;
        </Link>
      </span>
    </div>
  );
}

function PaginationBtn({ label, active }: { label: string; active?: boolean }) {
  return (
    <ToastButton
      message={label === "..." ? "更多页面即将上线" : `正在加载第 ${label} 页`}
      type="info"
      className="flex items-center justify-center"
      style={{
        width: 28,
        height: 28,
        borderRadius: "var(--radius-sm)",
        fontSize: 12,
        fontWeight: active ? 700 : 400,
        background: active ? "var(--color-primary)" : "var(--color-surface-container-lowest)",
        color: active ? "var(--color-on-primary)" : "var(--color-text-secondary)",
        boxShadow: active ? undefined : "var(--shadow-sm)",
      }}
    >
      {label}
    </ToastButton>
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

function PersonAddIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="10" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3 20c0-3.5 2.5-6 7-6s7 2.5 7 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M19 8v6M22 11h-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function GroupsIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor" opacity="0.8">
      <circle cx="9" cy="7" r="3" />
      <path d="M3 20c0-3 2.5-5.5 6-5.5s6 2.5 6 5.5" />
      <circle cx="17" cy="8" r="2" />
      <path d="M18.5 14c2 .7 3 2 3 4" />
    </svg>
  );
}

function PendingIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor" opacity="0.8">
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

function VerifiedIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor" opacity="0.8">
      <path d="M12 2l2.4 4.8L20 8l-4 3.8.9 5.2-4.9-2.6L7.1 17l.9-5.2L4 8l5.6-1.2z" />
    </svg>
  );
}

function SavingsIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor" opacity="0.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 6v12M8 10h8" fill="none" stroke="white" strokeWidth="1.5" />
    </svg>
  );
}

function TrendUpIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M7 17l5-5 3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 10h6v6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <ellipse cx="12" cy="6" rx="8" ry="3" stroke="var(--color-secondary)" strokeWidth="1.8" />
      <path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6" stroke="var(--color-secondary)" strokeWidth="1.8" />
      <path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" stroke="var(--color-secondary)" strokeWidth="1.8" />
    </svg>
  );
}

function AgentIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="4" y="4" width="16" height="16" rx="3" stroke="var(--color-primary)" strokeWidth="1.5" />
      <circle cx="9" cy="11" r="1.5" fill="var(--color-primary)" />
      <circle cx="15" cy="11" r="1.5" fill="var(--color-primary)" />
      <path d="M9 15h6" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function SparklesIcon({ color }: { color: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill={color}>
      <path d="M12 2l1.5 5.5L19 9l-5.5 1.5L12 16l-1.5-5.5L5 9l5.5-1.5z" />
      <path d="M18 14l.8 2.8L22 18l-3.2.8L18 22l-.8-3.2L14 18l3.2-.8z" opacity="0.6" />
    </svg>
  );
}
