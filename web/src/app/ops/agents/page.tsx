/* Agent Performance Monitor -- "/ops/agents"
   Bloomberg Ops density. All mock data, no API calls.
   Co-located sub-components at bottom of file. */

"use client";

import Link from "next/link";

/* ================================================================
   Types
   ================================================================ */

type AgentStatus = "active" | "idle" | "error";

interface Agent {
  id: string;
  name: string;
  role: string;
  deptColor: string;
  status: AgentStatus;
  tasks: number;
  confidence: number;
  errorRate: number;
  utilization: number;
}

interface SkillStat {
  name: string;
  invocations: number;
  avgMs: number;
  errors: number;
}

interface ErrorRecord {
  time: string;
  agent: string;
  client: string;
  type: string;
  typeLabel: string;
  message: string;
  borderColor: string;
}

/* ================================================================
   Mock data
   ================================================================ */

const AGENTS: Agent[] = [
  { id: "LQ-TX-001", name: "林税安", role: "高级税务会计",   deptColor: "var(--color-dept-tax)",        status: "active", tasks: 42, confidence: 99.2, errorRate: 0.3, utilization: 87 },
  { id: "LQ-HG-001", name: "赵合规", role: "合规总监",       deptColor: "var(--color-dept-compliance)",  status: "active", tasks: 38, confidence: 98.5, errorRate: 0.8, utilization: 79 },
  { id: "LQ-TC-001", name: "陈税策", role: "税务策略师",     deptColor: "var(--color-dept-tax)",        status: "active", tasks: 25, confidence: 97.8, errorRate: 1.2, utilization: 62 },
  { id: "LQ-JZ-001", name: "王记账", role: "记账主管",       deptColor: "var(--color-dept-bookkeeping)", status: "active", tasks: 56, confidence: 99.5, errorRate: 0.1, utilization: 93 },
  { id: "LQ-SH-001", name: "张审核", role: "审计专员",       deptColor: "var(--color-dept-client)",      status: "idle",   tasks: 18, confidence: 96.3, errorRate: 2.1, utilization: 45 },
  { id: "LQ-KF-001", name: "李客服", role: "客户服务代表",   deptColor: "var(--color-dept-admin)",       status: "active", tasks: 31, confidence: 98.9, errorRate: 0.5, utilization: 71 },
  { id: "LQ-XM-007", name: "周小秘", role: "行政秘书",       deptColor: "var(--color-dept-admin)",       status: "error",  tasks: 8,  confidence: 89.1, errorRate: 5.3, utilization: 22 },
];

const SKILLS: SkillStat[] = [
  { name: "增值税申报",     invocations: 1240, avgMs: 3200, errors: 2 },
  { name: "财务报表生成",   invocations: 890,  avgMs: 5100, errors: 0 },
  { name: "银行对账",       invocations: 756,  avgMs: 2800, errors: 1 },
  { name: "企业所得税核验", invocations: 623,  avgMs: 4300, errors: 3 },
  { name: "合规风险扫描",   invocations: 518,  avgMs: 6700, errors: 5 },
  { name: "凭证录入",       invocations: 412,  avgMs: 1200, errors: 0 },
  { name: "个税专项扣除",   invocations: 389,  avgMs: 2100, errors: 1 },
  { name: "审计异常检测",   invocations: 267,  avgMs: 8900, errors: 4 },
  { name: "客户沟通记录",   invocations: 198,  avgMs: 900,  errors: 0 },
  { name: "月度结账",       invocations: 156,  avgMs: 12400, errors: 2 },
];

const AGENT_SLUG: Record<string, string> = {
  "林税安": "lin-shui-an",
  "赵合规": "zhao-he-gui",
  "陈税策": "chen-shui-ce",
  "王记账": "wang-ji-zhang",
  "张审核": "zhang-shen-he",
  "李客服": "li-ke-fu",
  "周小秘": "zhou-xiao-mi",
};

const ERRORS: ErrorRecord[] = [
  { time: "2024-11-15 14:23", agent: "周小秘", client: "云峰智源",   type: "timeout",         typeLabel: "超时",     message: "知识图谱查询超时（>30秒），建议检查数据量或分批处理",               borderColor: "var(--color-warning)" },
  { time: "2024-11-15 09:17", agent: "张审核", client: "美团点评",   type: "confidence_low",  typeLabel: "低准确率", message: "审计异常检测准确率 67.2%，低于阈值 85%，建议人工复核",                    borderColor: "var(--color-secondary)" },
  { time: "2024-11-14 16:45", agent: "赵合规", client: "华夏贸易",   type: "data_missing",    typeLabel: "数据缺失", message: "跨境税务合规检查缺少转让定价文档（2024年Q3），请联系客户补充",                                 borderColor: "var(--color-danger)" },
  { time: "2024-11-13 11:30", agent: "周小秘", client: "光影传媒",   type: "api_failure",     typeLabel: "接口故障",  message: "技能市场接口异常，技能加载失败，已自动重试",                 borderColor: "var(--color-danger)" },
  { time: "2024-11-13 08:55", agent: "陈税策", client: "泰和养老",   type: "confidence_low",  typeLabel: "低准确率", message: "所得税优化建议准确率 72.1%，低于标准，需人工审核确认",                                      borderColor: "var(--color-secondary)" },
];

/* ================================================================
   Page component
   ================================================================ */

export default function OpsAgentsPage() {
  return (
    <div>
      {/* -- Page header -- */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2
          className="font-display font-bold"
          style={{
            fontSize: 20,
            lineHeight: 1.3,
            color: "var(--color-text-primary)",
          }}
        >
          AI 专员性能监控
        </h2>
        <p
          style={{
            fontSize: 11,
            color: "var(--color-text-tertiary)",
            marginTop: "var(--space-1)",
          }}
        >
          {AGENTS.length} 位 AI 专员 | 过去 7 天数据
        </p>
      </section>

      {/* -- Agent status grid -- */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: "var(--space-6)",
        }}
      >
        {AGENTS.map((a) => (
          <AgentCard key={a.id} agent={a} />
        ))}
      </section>

      {/* -- Two-column middle section -- */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: "1fr 1fr",
          gap: "var(--space-6)",
          marginBottom: "var(--space-6)",
        }}
      >
        {/* Left: Utilization chart */}
        <div
          style={{
            padding: "var(--space-4)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <h3
            className="font-bold"
            style={{
              fontSize: 13,
              color: "var(--color-text-primary)",
              marginBottom: "var(--space-4)",
            }}
          >
            AI 专员利用率 (7天)
          </h3>
          <div className="flex flex-col" style={{ gap: 8 }}>
            {AGENTS.map((a) => (
              <UtilizationBar key={a.id} agent={a} />
            ))}
          </div>
        </div>

        {/* Right: Skill usage table */}
        <div
          style={{
            padding: "var(--space-4)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <h3
            className="font-bold"
            style={{
              fontSize: 13,
              color: "var(--color-text-primary)",
              marginBottom: "var(--space-4)",
            }}
          >
            技能使用统计
          </h3>
          <SkillTable skills={SKILLS} />
        </div>
      </section>

      {/* -- Recent errors -- */}
      <section
        style={{
          marginBottom: "var(--space-6)",
        }}
      >
        <div
          className="flex items-center"
          style={{ gap: 8, marginBottom: "var(--space-3)" }}
        >
          <h3
            className="font-bold"
            style={{ fontSize: 13, color: "var(--color-text-primary)" }}
          >
            最近错误 (过去 7 天)
          </h3>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              background: "color-mix(in srgb, var(--color-danger) 12%, transparent)",
              color: "var(--color-danger)",
            }}
          >
            {ERRORS.length}
          </span>
        </div>
        <ErrorTable errors={ERRORS} />
      </section>

      {/* -- Footer -- */}
      <footer
        className="text-center"
        style={{
          padding: "var(--space-8) 0 var(--space-4)",
          color: "var(--color-text-tertiary)",
          fontSize: 11,
        }}
      >
        <p>灵阙运营控制台 v1.0</p>
      </footer>
    </div>
  );
}

/* ================================================================
   Sub-components (co-located, page-specific)
   ================================================================ */

/* -- Agent card -- */

function AgentCard({ agent: a }: { agent: Agent }) {
  const statusConfig: Record<AgentStatus, { label: string; bg: string; color: string }> = {
    active: {
      label: "运行中",
      bg: "color-mix(in srgb, var(--color-success) 12%, transparent)",
      color: "var(--color-success)",
    },
    idle: {
      label: "空闲",
      bg: "color-mix(in srgb, var(--color-text-tertiary) 12%, transparent)",
      color: "var(--color-text-tertiary)",
    },
    error: {
      label: "异常",
      bg: "color-mix(in srgb, var(--color-danger) 12%, transparent)",
      color: "var(--color-danger)",
    },
  };

  const s = statusConfig[a.status];
  const isError = a.status === "error";

  return (
    <div
      style={{
        padding: "var(--space-3)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        borderLeft: isError ? "3px solid var(--color-danger)" : "3px solid transparent",
      }}
    >
      {/* Top row: avatar + name + status */}
      <div
        className="flex items-center"
        style={{ gap: 8, marginBottom: 8 }}
      >
        {/* Avatar */}
        <span
          className="flex items-center justify-center font-bold"
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: a.deptColor,
            color: "#fff",
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          {a.name[0]}
        </span>

        {/* Name + role */}
        <span
          style={{
            flex: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap" as const,
          }}
        >
          <span
            className="font-bold"
            style={{ fontSize: 12, color: "var(--color-text-primary)" }}
          >
            {a.name}
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--color-text-tertiary)",
              marginLeft: 6,
            }}
          >
            {a.role}
          </span>
        </span>

        {/* Status pill */}
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            background: s.bg,
            color: s.color,
            whiteSpace: "nowrap" as const,
            flexShrink: 0,
          }}
        >
          {s.label}
        </span>
      </div>

      {/* Micro-metrics row */}
      <div
        className="tabular-nums"
        style={{
          fontSize: 11,
          color: "var(--color-text-secondary)",
          display: "flex",
          gap: 4,
          textAlign: "left",
        }}
      >
        <span>
          完成:<span className="font-bold" style={{ color: "var(--color-text-primary)" }}>{a.tasks}</span>
        </span>
        <span style={{ color: "var(--color-outline-variant)" }}>|</span>
        <span>
          置信:<span className="font-bold" style={{ color: "var(--color-text-primary)" }}>{a.confidence.toFixed(1)}</span>
        </span>
        <span style={{ color: "var(--color-outline-variant)" }}>|</span>
        <span>
          错误:<span
            className="font-bold"
            style={{
              color: a.errorRate > 3 ? "var(--color-danger)" : "var(--color-text-primary)",
            }}
          >
            {a.errorRate.toFixed(1)}%
          </span>
        </span>
      </div>
    </div>
  );
}

/* -- Utilization bar -- */

function UtilizationBar({ agent: a }: { agent: Agent }) {
  const barColor =
    a.utilization > 95
      ? "var(--color-danger)"
      : a.utilization > 80
        ? "var(--color-warning)"
        : "var(--color-primary)";

  return (
    <div className="flex items-center" style={{ gap: 8, height: 20 }}>
      {/* Agent name, fixed width */}
      <span
        style={{
          width: 70,
          fontSize: 11,
          color: "var(--color-text-secondary)",
          textOverflow: "ellipsis",
          overflow: "hidden",
          whiteSpace: "nowrap" as const,
          flexShrink: 0,
        }}
      >
        {a.name}
      </span>

      {/* Bar track */}
      <span
        style={{
          flex: 1,
          height: 16,
          borderRadius: 2,
          background: "var(--color-surface-container)",
          overflow: "hidden",
        }}
      >
        <span
          style={{
            display: "block",
            width: `${a.utilization}%`,
            height: "100%",
            borderRadius: 2,
            background: barColor,
            transition: "width 0.3s ease",
          }}
        />
      </span>

      {/* Percentage text */}
      <span
        className="tabular-nums font-bold"
        style={{
          width: 36,
          fontSize: 11,
          textAlign: "right",
          color: barColor,
          flexShrink: 0,
        }}
      >
        {a.utilization}%
      </span>
    </div>
  );
}

/* -- Skill table -- */

const SKILL_GRID_COLS = "1fr 80px 80px 50px";

function SkillTable({ skills }: { skills: SkillStat[] }) {
  return (
    <div
      style={{
        borderRadius: "var(--radius-sm)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        className="grid items-center"
        style={{
          gridTemplateColumns: SKILL_GRID_COLS,
          padding: "6px 10px",
          background: "var(--color-surface-container)",
          fontSize: 10,
          fontWeight: 700,
          color: "var(--color-text-tertiary)",
        }}
      >
        <span>技能名称</span>
        <span style={{ textAlign: "right" }}>调用次数</span>
        <span style={{ textAlign: "right" }}>平均耗时</span>
        <span style={{ textAlign: "right" }}>错误</span>
      </div>

      {/* Rows */}
      {skills.map((sk, i) => (
        <div
          key={sk.name}
          className="grid items-center table-row-hover"
          style={{
            gridTemplateColumns: SKILL_GRID_COLS,
            padding: "5px 10px",
            fontSize: 11,
            background:
              i % 2 === 1
                ? "var(--color-surface-container-lowest)"
                : "var(--color-surface)",
            color: "var(--color-text-primary)",
          }}
        >
          <span>{sk.name}</span>
          <span
            className="tabular-nums"
            style={{ textAlign: "right", color: "var(--color-text-secondary)" }}
          >
            {sk.invocations.toLocaleString()}
          </span>
          <span
            className="tabular-nums"
            style={{ textAlign: "right", color: "var(--color-text-secondary)" }}
          >
            {formatMs(sk.avgMs)}
          </span>
          <span
            className="tabular-nums font-bold"
            style={{
              textAlign: "right",
              color: sk.errors > 0 ? "var(--color-danger)" : "var(--color-text-tertiary)",
            }}
          >
            {sk.errors}
          </span>
        </div>
      ))}
    </div>
  );
}

/* -- Error table -- */

const ERROR_GRID_COLS = "120px 60px 80px 70px 1fr";

function ErrorTable({ errors }: { errors: ErrorRecord[] }) {
  return (
    <div
      style={{
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-low)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        className="grid items-center"
        style={{
          gridTemplateColumns: ERROR_GRID_COLS,
          padding: "8px 12px",
          background: "var(--color-surface-container)",
          fontSize: 10,
          fontWeight: 700,
          color: "var(--color-text-tertiary)",
        }}
      >
        <span>时间</span>
        <span>专员</span>
        <span>客户</span>
        <span>错误类型</span>
        <span>错误信息</span>
      </div>

      {/* Rows */}
      {errors.map((e, i) => (
        <div
          key={`${e.time}-${e.agent}`}
          className="grid items-center table-row-hover"
          style={{
            gridTemplateColumns: ERROR_GRID_COLS,
            padding: "6px 12px",
            fontSize: 11,
            background:
              i % 2 === 1
                ? "var(--color-surface-container-lowest)"
                : "var(--color-surface)",
            color: "var(--color-text-primary)",
            borderLeft: `3px solid ${e.borderColor}`,
          }}
        >
          <span
            className="tabular-nums"
            style={{ color: "var(--color-text-tertiary)", fontSize: 10 }}
          >
            {e.time}
          </span>
          <Link
            href={`/ai-team/${AGENT_SLUG[e.agent] ?? ""}`}
            className="font-bold"
            style={{ color: "var(--color-primary)", textDecoration: "none" }}
          >
            {e.agent}
          </Link>
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap" as const,
            }}
          >
            {e.client}
          </span>
          <span>
            <span
              style={{
                fontSize: 10,
                fontWeight: 600,
                padding: "1px 6px",
                borderRadius: "var(--radius-sm)",
                background: `color-mix(in srgb, ${e.borderColor} 10%, transparent)`,
                color: e.borderColor,
                whiteSpace: "nowrap" as const,
              }}
            >
              {e.typeLabel}
            </span>
          </span>
          <span
            style={{
              color: "var(--color-text-secondary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap" as const,
              fontFamily: "var(--font-body)",
            }}
          >
            {e.message}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ================================================================
   Helpers
   ================================================================ */

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}
