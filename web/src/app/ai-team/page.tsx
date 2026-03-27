/* AI Team -- "AI 团队管理"
   Layout reference: design/stitch-export/stitch/ai_ai_team/screen.png
   All data is static mock for initial build. */

"use client";

import Link from "next/link";

const AGENT_SLUG: Record<string, string> = {
  "林税安": "lin-shui-an",
  "赵合规": "zhao-he-gui",
  "陈税策": "chen-shui-ce",
  "王记账": "wang-ji-zhang",
  "张审核": "zhang-shen-he",
  "李客服": "li-ke-fu",
  "周小秘": "zhou-xiao-mi",
};

const agents = [
  {
    id: "LQ-TX-001",
    name: "林税安",
    role: "高级税务会计",
    dept: "税务部",
    deptColor: "var(--color-dept-tax)",
    status: "active" as const,
    task: "正在处理 杭州明达科技 2024Q3 增值税申报核验",
    stats: { filings: "150 份", score: "100.0", savings: "¥1.2M" },
    icon: "TX",
  },
  {
    id: "LQ-HG-002",
    name: "赵合规",
    role: "合规审查专员",
    dept: "合规部",
    deptColor: "var(--color-dept-compliance)",
    status: "training" as const,
    task: "正在学习 2024最新跨国避税审计准则",
    stats: { filings: "89 份", score: "97.5", savings: "¥420K" },
    icon: "HG",
    trainingProgress: 78,
  },
  {
    id: "LQ-CS-003",
    name: "陈税策",
    role: "税务筹划顾问",
    dept: "税务部",
    deptColor: "var(--color-dept-tax)",
    status: "active" as const,
    task: "为上海锐意商贸制定节税方案",
    stats: { filings: "62 份", score: "99.2", savings: "¥890K" },
    icon: "CS",
  },
  {
    id: "LQ-JZ-004",
    name: "王记账",
    role: "智能记账专员",
    dept: "记账部",
    deptColor: "var(--color-dept-bookkeeping)",
    status: "active" as const,
    task: "深圳领航物流 9月凭证批量录入",
    stats: { filings: "1,240 笔", score: "99.8", savings: "¥180K" },
    icon: "JZ",
  },
  {
    id: "LQ-SH-005",
    name: "张审核",
    role: "审核会计",
    dept: "记账部",
    deptColor: "var(--color-dept-bookkeeping)",
    status: "idle" as const,
    task: "等待新任务分配",
    stats: { filings: "320 笔", score: "98.6", savings: "¥95K" },
    icon: "SH",
  },
  {
    id: "LQ-KF-006",
    name: "李客服",
    role: "客户经理",
    dept: "客户部",
    deptColor: "var(--color-dept-client)",
    status: "active" as const,
    task: "跟进 3 家客户季度对账确认",
    stats: { filings: "45 家", score: "96.0", savings: "—" },
    icon: "KF",
  },
  {
    id: "LQ-XM-007",
    name: "周小秘",
    role: "行政助理",
    dept: "行政部",
    deptColor: "var(--color-dept-admin)",
    status: "active" as const,
    task: "整理本月团队工作周报",
    stats: { filings: "87 份", score: "95.0", savings: "—" },
    icon: "XM",
  },
];

const taskQueue = [
  {
    title: "Q3 企业所得税预缴申报",
    deadline: "截止日期: 2024-10-15",
    agent: "林税安",
    agentIcon: "TX",
    priority: "urgent" as const,
    status: "正在计算 (85%)",
    statusDot: "var(--color-success)",
  },
  {
    title: "9月份全员社保汇缴核对",
    deadline: "关联单据: 450张",
    agent: "王记账",
    agentIcon: "JZ",
    priority: "normal" as const,
    status: "队列中",
    statusDot: "var(--color-text-tertiary)",
  },
  {
    title: "上海锐意商贸进项发票批量查验",
    deadline: "截止日期: 2024-10-20",
    agent: "张审核",
    agentIcon: "SH",
    priority: "normal" as const,
    status: "待分配",
    statusDot: "var(--color-warning)",
  },
];

export default function AITeamPage() {
  const activeCount = agents.filter((a) => a.status === "active").length;
  const trainingCount = agents.filter((a) => a.status === "training").length;
  const idleCount = agents.filter((a) => a.status === "idle").length;
  const featured = agents[0]; // Lin Shui An as the featured agent

  return (
    <div>
      {/* ── Stats bar ── */}
      <section
        className="grid gap-5"
        style={{
          gridTemplateColumns: "1fr 1fr 1fr",
          marginBottom: "var(--space-8)",
        }}
      >
        <StatCard label="团队活跃度" value="98.4%" note="所有系统运行正常" accent="primary" />
        <StatCard label="本月处理任务" value="1,284" note="+12% 较上月增长" accent="secondary" />
        <StatCard label="平均响应时间" value="1.2s" note="全天候实时响应" accent="neutral" />
      </section>

      {/* ── Featured agent hero ── */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-4)" }}>
          <div>
            <h3
              className="font-display font-bold"
              style={{ fontSize: 22, color: "var(--color-text-primary)" }}
            >
              专项 AI 专家目录
            </h3>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              管理并分配您的自动化财税团队
            </p>
          </div>
          <button
            className="font-medium flex items-center gap-1"
            style={{ fontSize: 13, color: "var(--color-secondary-dim)" }}
          >
            查看全部团队成员
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        <div className="grid gap-6" style={{ gridTemplateColumns: "2fr 1fr" }}>
          {/* Hero card */}
          <div
            className="relative overflow-hidden flex flex-col justify-between"
            style={{
              padding: "var(--space-8)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-primary)",
              color: "var(--color-on-primary)",
              minHeight: 300,
            }}
          >
            {/* Status badge */}
            <div className="absolute" style={{ top: "var(--space-6)", right: "var(--space-6)" }}>
              <StatusBadge status={featured.status} />
            </div>

            <div className="flex items-start gap-6">
              <AgentAvatar initials={featured.icon} color="rgba(255,255,255,0.15)" textColor="var(--color-on-primary)" size={72} />
              <div>
                <h4
                  className="font-display font-bold"
                  style={{ fontSize: 24, marginBottom: 4, color: "var(--color-on-primary)" }}
                >
                  {featured.name}
                </h4>
                <p style={{ fontSize: 14, opacity: 0.8, margin: 0 }}>{featured.role}</p>
                <p style={{ fontSize: 13, opacity: 0.65, margin: 0, marginTop: 8, maxWidth: 400, lineHeight: 1.75 }}>
                  专注于增值税、企业所得税申报及税务筹划建议。具备全行业税务法规实时更新库。
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-8" style={{ marginTop: "var(--space-8)" }}>
              <div>
                <p style={{ fontSize: 10, textTransform: "uppercase", opacity: 0.6, fontWeight: 700, marginBottom: 4 }}>
                  本月申报
                </p>
                <p className="font-display font-bold" style={{ fontSize: 20, margin: 0 }}>
                  {featured.stats.filings}
                </p>
              </div>
              <div>
                <p style={{ fontSize: 10, textTransform: "uppercase", opacity: 0.6, fontWeight: 700, marginBottom: 4 }}>
                  合规评分
                </p>
                <p className="font-display font-bold" style={{ fontSize: 20, margin: 0, color: "var(--color-secondary)" }}>
                  {featured.stats.score}
                </p>
              </div>
              <div>
                <p style={{ fontSize: 10, textTransform: "uppercase", opacity: 0.6, fontWeight: 700, marginBottom: 4 }}>
                  节省税款
                </p>
                <p className="font-display font-bold" style={{ fontSize: 20, margin: 0 }}>
                  {featured.stats.savings}
                </p>
              </div>
            </div>

            <div className="flex gap-3" style={{ marginTop: "var(--space-6)" }}>
              <button
                className="font-medium flex items-center gap-2"
                style={{
                  fontSize: 13,
                  padding: "10px 20px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--color-on-primary)",
                  color: "var(--color-primary)",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3 8-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M20 12v7a2 2 0 01-2 2H6a2 2 0 01-2-2V7a2 2 0 012-2h9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                分配任务
              </button>
              <button
                className="font-medium"
                style={{
                  fontSize: 13,
                  padding: "10px 20px",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(255,255,255,0.12)",
                  color: "var(--color-on-primary)",
                }}
              >
                配置参数
              </button>
            </div>

            {/* Decorative background icon */}
            <div
              className="absolute"
              style={{
                bottom: -20,
                right: -20,
                opacity: 0.04,
                fontSize: 180,
                lineHeight: 1,
                fontWeight: 900,
                color: "var(--color-on-primary)",
                fontFamily: "var(--font-display)",
              }}
            >
              TX
            </div>
          </div>

          {/* Side column: training + idle agents */}
          <div className="flex flex-col gap-6">
            {agents
              .filter((a) => a.status === "training" || a.status === "idle")
              .slice(0, 2)
              .map((agent) => (
                <CompactAgentCard key={agent.id} agent={agent} />
              ))}
          </div>
        </div>
      </section>

      {/* ── Agent grid ── */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <h3
          className="font-display font-bold"
          style={{ fontSize: 18, color: "var(--color-text-primary)", marginBottom: "var(--space-4)" }}
        >
          全部 AI 专家 ({agents.length})
        </h3>
        <div
          className="grid gap-5"
          style={{ gridTemplateColumns: "repeat(3, 1fr)" }}
        >
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </section>

      {/* ── Task queue ── */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <h3
          className="font-display font-bold"
          style={{ fontSize: 18, color: "var(--color-text-primary)", marginBottom: "var(--space-4)" }}
        >
          实时工作队列
        </h3>
        <div
          style={{
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {/* Table header */}
          <div
            className="grid items-center"
            style={{
              gridTemplateColumns: "minmax(200px, 1.5fr) 1fr 100px 1fr 80px",
              padding: "10px 16px",
              background: "var(--color-surface-container-low)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
            }}
          >
            <span>任务详情</span>
            <span>分配专家</span>
            <span>优先级</span>
            <span>状态</span>
            <span style={{ textAlign: "right" }}>操作</span>
          </div>

          {taskQueue.map((task, i) => (
            <div
              key={task.title}
              className="grid items-center table-row-hover"
              style={{
                gridTemplateColumns: "minmax(200px, 1.5fr) 1fr 100px 1fr 80px",
                padding: "14px 16px",
                background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)",
                fontSize: 13,
              }}
            >
              <div>
                <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>
                  {task.title}
                </span>
                <br />
                <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{task.deadline}</span>
              </div>
              <div className="flex items-center gap-2">
                <AgentAvatar initials={task.agentIcon} color="var(--color-primary)" textColor="var(--color-on-primary)" size={24} />
                <span style={{ fontSize: 13 }}>{task.agent}</span>
              </div>
              <span>
                <span
                  className={task.priority === "urgent" ? "badge-danger" : "badge-info"}
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "2px 8px",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  {task.priority === "urgent" ? "紧急" : "普通"}
                </span>
              </span>
              <div className="flex items-center gap-2">
                <span
                  style={{
                    display: "inline-block",
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: task.statusDot,
                  }}
                />
                <span style={{ fontSize: 13 }}>{task.status}</span>
              </div>
              <span style={{ textAlign: "right" }}>
                <button
                  className="font-medium"
                  style={{ fontSize: 12, color: "var(--color-primary)" }}
                >
                  详情
                </button>
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ── AI recommendation panel ── */}
      <section
        className="flex items-center gap-8"
        style={{
          padding: "var(--space-8)",
          borderRadius: "var(--radius-md)",
          background: "var(--color-surface-container-lowest)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "var(--space-8)",
        }}
      >
        <div
          className="shrink-0 flex items-center justify-center"
          style={{
            width: 80,
            height: 80,
            borderRadius: "50%",
            background: "linear-gradient(135deg, var(--color-primary), var(--color-secondary))",
          }}
        >
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
            <path d="M12 2l2.09 6.26L20.18 9l-5 4.09L16.18 20 12 16.77 7.82 20l1-6.91-5-4.09 6.09-.74L12 2z" stroke="var(--color-on-primary)" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2" style={{ marginBottom: "var(--space-2)" }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 2l2.09 6.26L20.18 9l-5 4.09L16.18 20 12 16.77 7.82 20l1-6.91-5-4.09 6.09-.74L12 2z" stroke="var(--color-secondary)" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
            <span
              className="font-medium"
              style={{
                fontSize: 12,
                textTransform: "uppercase",
                color: "var(--color-secondary-dim)",
              }}
            >
              AI 团队智能建议
            </span>
          </div>
          <p
            className="font-medium"
            style={{
              fontSize: 16,
              color: "var(--color-text-primary)",
              lineHeight: 1.75,
              margin: 0,
              maxWidth: 640,
            }}
          >
            "根据近期增值税进项数据分析，建议 '林税安' 在下周开启针对电子信息行业的专项核销策略，预计可为 3 家客户额外节省 ¥85,000 税款。"
          </p>
          <button
            className="font-medium flex items-center gap-1"
            style={{
              marginTop: "var(--space-3)",
              fontSize: 13,
              color: "var(--color-primary)",
            }}
          >
            立即应用此建议
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
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
   Sub-components (co-located, AI Team page specific)
   ================================================================ */

function StatCard({
  label,
  value,
  note,
  accent,
}: {
  label: string;
  value: string;
  note: string;
  accent: "primary" | "secondary" | "neutral";
}) {
  const borderColor =
    accent === "primary"
      ? "var(--color-primary)"
      : accent === "secondary"
        ? "var(--color-secondary)"
        : "var(--color-outline-variant)";

  return (
    <div
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
        borderLeft: `4px solid ${borderColor}`,
      }}
    >
      <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginBottom: 4 }}>{label}</p>
      <p
        className="font-display font-extrabold"
        style={{ fontSize: 32, color: "var(--color-text-primary)", margin: 0, lineHeight: 1.2 }}
      >
        {value}
      </p>
      <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", margin: 0, marginTop: 12 }}>
        {accent === "primary" && (
          <span className="flex items-center gap-2">
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
            {note}
          </span>
        )}
        {accent === "secondary" && (
          <span className="font-medium" style={{ color: "var(--color-secondary-dim)" }}>{note}</span>
        )}
        {accent === "neutral" && <span>{note}</span>}
      </p>
    </div>
  );
}

function AgentAvatar({
  initials,
  color,
  textColor,
  size = 48,
}: {
  initials: string;
  color: string;
  textColor: string;
  size?: number;
}) {
  return (
    <div
      className="flex items-center justify-center shrink-0 font-medium"
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        color: textColor,
        fontSize: size * 0.3,
        fontWeight: 700,
      }}
    >
      {initials}
    </div>
  );
}

function StatusBadge({ status }: { status: "active" | "training" | "idle" }) {
  const config = {
    active: { label: "Active", badgeClass: "badge-success", dotColor: "var(--color-success)" },
    training: { label: "Training", badgeClass: "badge-warning", dotColor: "var(--color-warning)" },
    idle: { label: "Idle", badgeClass: "badge-info", dotColor: "var(--color-text-tertiary)" },
  };
  const c = config[status];

  return (
    <span
      className={c.badgeClass}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11,
        fontWeight: 600,
        padding: "3px 10px",
        borderRadius: "var(--radius-sm)",
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: c.dotColor,
        }}
      />
      {c.label}
    </span>
  );
}

type Agent = (typeof agents)[number];

function AgentCard({ agent }: { agent: Agent }) {
  const slug = AGENT_SLUG[agent.name] ?? "";
  return (
    <Link
      href={`/ai-team/${slug}`}
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
        textDecoration: "none",
        color: "inherit",
        transition: "box-shadow 0.15s ease",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 2px 12px rgba(0,0,0,0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "var(--shadow-sm)"; }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <AgentAvatar initials={agent.icon} color={agent.deptColor} textColor="var(--color-on-primary)" size={44} />
          <div>
            <p className="font-display font-bold" style={{ fontSize: 15, margin: 0, color: "var(--color-text-primary)" }}>
              {agent.name}
            </p>
            <p style={{ fontSize: 12, margin: 0, color: "var(--color-text-secondary)" }}>{agent.role}</p>
          </div>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.75, minHeight: 46 }}>
        {agent.task}
      </p>

      {agent.trainingProgress !== undefined && (
        <div>
          <div className="flex justify-between" style={{ fontSize: 11, marginBottom: 4 }}>
            <span style={{ color: "var(--color-text-tertiary)" }}>训练进度</span>
            <span className="font-medium">{agent.trainingProgress}%</span>
          </div>
          <div
            style={{
              height: 4,
              borderRadius: 2,
              background: "var(--color-surface-container)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${agent.trainingProgress}%`,
                background: "var(--color-secondary)",
                borderRadius: 2,
              }}
            />
          </div>
        </div>
      )}

      <div
        className="flex items-center justify-between"
        style={{
          paddingTop: "var(--space-3)",
          fontSize: 11,
          color: "var(--color-text-tertiary)",
        }}
      >
        <span>{agent.dept}</span>
        <span className="font-mono" style={{ fontSize: 10, opacity: 0.7 }}>
          {agent.id}
        </span>
      </div>
    </Link>
  );
}

function CompactAgentCard({ agent }: { agent: Agent }) {
  const slug = AGENT_SLUG[agent.name] ?? "";
  return (
    <Link
      href={`/ai-team/${slug}`}
      className="flex flex-col flex-1"
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
        textDecoration: "none",
        color: "inherit",
        transition: "box-shadow 0.15s ease",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 2px 12px rgba(0,0,0,0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "var(--shadow-sm)"; }}
    >
      <div className="flex justify-between items-start" style={{ marginBottom: "var(--space-4)" }}>
        <AgentAvatar initials={agent.icon} color={agent.deptColor} textColor="var(--color-on-primary)" size={48} />
        <StatusBadge status={agent.status} />
      </div>

      <h4
        className="font-display font-bold"
        style={{ fontSize: 18, color: "var(--color-text-primary)", marginBottom: 4 }}
      >
        {agent.name}
      </h4>
      <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.75, flex: 1 }}>
        {agent.task}
      </p>

      {agent.trainingProgress !== undefined && (
        <div style={{ marginTop: "var(--space-4)" }}>
          <div className="flex justify-between" style={{ fontSize: 11, marginBottom: 4 }}>
            <span style={{ color: "var(--color-text-tertiary)" }}>训练进度</span>
            <span className="font-medium">{agent.trainingProgress}%</span>
          </div>
          <div
            style={{
              height: 4,
              borderRadius: 2,
              background: "var(--color-surface-container)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${agent.trainingProgress}%`,
                background: "var(--color-secondary)",
                borderRadius: 2,
              }}
            />
          </div>
        </div>
      )}

      <button
        className="font-medium"
        style={{
          marginTop: "var(--space-4)",
          width: "100%",
          padding: "10px 0",
          borderRadius: "var(--radius-sm)",
          background: "var(--color-surface-container)",
          color: "var(--color-text-primary)",
          fontSize: 13,
        }}
      >
        {agent.status === "idle" ? "立即唤醒" : "查看详情"}
      </button>
    </Link>
  );
}
