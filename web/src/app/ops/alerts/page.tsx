/* Alert Center -- "/ops/alerts"
   Bloomberg Ops density. All mock data, no API calls.
   Co-located sub-components at bottom of file. */

"use client";

import { useState } from "react";
import Link from "next/link";
import { AGENT_SLUG, findAgentSlug } from "../../lib/agents";
import { useToast } from "../../components/Toast";

/* ================================================================
   Types
   ================================================================ */

type Severity = "critical" | "warning" | "info" | "resolved";
type AlertStatus = "open" | "acknowledged" | "resolved";
type Source = "kg" | "agent" | "billing" | "api" | "compliance";

interface Alert {
  id: string;
  source: Source;
  severity: Severity;
  title: string;
  desc: string;
  customer?: string;
  timestamp: string;
  status: AlertStatus;
}

/* ================================================================
   Mock data (15 alerts)
   ================================================================ */

const ALERTS: Alert[] = [
  // Critical (2)
  { id: "ALT-001", source: "agent", severity: "critical", title: "AI 专员 周小秘 连续 3 次任务失败", desc: "错误率 5.3% 超过阈值 3%。最近错误：知识图谱查询超时。建议暂停任务分配并检查专员状态。", customer: "云峰智源", timestamp: "2024-11-15 14:30", status: "open" },
  { id: "ALT-002", source: "kg", severity: "critical", title: "增值税政策知识节点 14 天未更新", desc: "增值税政策 2024 版最后更新于 2024-11-01，已超过 7 天更新周期。可能导致税务建议不准确，请尽快安排知识库更新。", timestamp: "2024-11-15 12:00", status: "open" },
  // Warning (4)
  { id: "ALT-003", source: "agent", severity: "warning", title: "张审核准确率持续偏低", desc: "过去 7 天平均准确率 96.3%, 接近预警线 95%. 审计任务质量可能受影响.", customer: "美团点评", timestamp: "2024-11-15 10:15", status: "acknowledged" },
  { id: "ALT-004", source: "billing", severity: "warning", title: "云峰智源企业版即将到期", desc: "订阅到期日 2024-12-01, 剩余 16 天. 客户尚未确认续费意向.", customer: "云峰智源", timestamp: "2024-11-15 09:00", status: "open" },
  { id: "ALT-005", source: "compliance", severity: "warning", title: "新增税务政策待合规审查", desc: "财政部 2024 年第 47 号公告已发布, 涉及研发费用加计扣除调整. 需更新合规规则库.", timestamp: "2024-11-14 16:30", status: "open" },
  { id: "ALT-006", source: "api", severity: "warning", title: "技能市场接口响应延迟", desc: "过去 1 小时响应时间偏高（2.3秒），正常应在 0.5 秒以内。技能商店页面加载可能变慢。", timestamp: "2024-11-14 15:45", status: "acknowledged" },
  // Info (3)
  { id: "ALT-007", source: "agent", severity: "info", title: "林税安完成季度高峰处理", desc: "Q3 增值税申报批量处理完成, 42 家客户全部提交成功, 零错误.", timestamp: "2024-11-15 11:00", status: "resolved" },
  { id: "ALT-008", source: "kg", severity: "info", title: "KG 月度健康检查通过", desc: "344K 节点, 1M 边. 数据质量评分 100/100. 无异常发现.", timestamp: "2024-11-14 08:00", status: "resolved" },
  { id: "ALT-009", source: "billing", severity: "info", title: "本月收入目标达成 87%", desc: "当前 MRR \u00A589,400, 目标 \u00A5102,800. 预计月底可达 95%+.", timestamp: "2024-11-13 18:00", status: "resolved" },
  // Resolved (6 more)
  { id: "ALT-010", source: "agent", severity: "warning", title: "王记账任务队列积压已清除", desc: "积压从 23 个降至 0. 处理耗时 4.2 小时.", timestamp: "2024-11-13 14:00", status: "resolved" },
  { id: "ALT-011", source: "api", severity: "warning", title: "AI 语言模型接口已恢复正常", desc: "13:00-13:45 期间出现间歇性故障，系统已自动切换至备用模型，现已完全恢复。", timestamp: "2024-11-13 13:50", status: "resolved" },
  { id: "ALT-012", source: "compliance", severity: "info", title: "年度审计准备文档已生成", desc: "林税安 + 赵合规协作完成 2024 年度审计底稿, 覆盖 12 家企业版客户.", timestamp: "2024-11-12 17:00", status: "resolved" },
  { id: "ALT-013", source: "kg", severity: "info", title: "法规更新批量导入完成", desc: "新增 47 条法规节点, 更新 183 条关联边. 来源: 国家税务总局 2024-Q3 批次.", timestamp: "2024-11-12 10:30", status: "resolved" },
  { id: "ALT-014", source: "agent", severity: "info", title: "赵合规技能树升级完成", desc: "新增 '跨境电商税务合规' 技能 (S级). 从 OpenClaw 安装成功.", timestamp: "2024-11-11 16:00", status: "resolved" },
  { id: "ALT-015", source: "billing", severity: "info", title: "3 家客户完成自动续费", desc: "中铁建设、腾讯科技、鹏程万里 企业版年度自动续费成功. 总计 \u00A535,964.", timestamp: "2024-11-11 00:05", status: "resolved" },
];

/* ================================================================
   Filter configs
   ================================================================ */

type SeverityFilter = "all" | "open" | "critical" | "warning" | "info" | "resolved";
type SourceFilter = "all" | Source;

const SEVERITY_FILTERS: Array<{ key: SeverityFilter; label: string; count: number }> = [
  { key: "open", label: "待处理", count: 9 },
  { key: "all", label: "全部", count: 15 },
  { key: "critical", label: "严重", count: 2 },
  { key: "warning", label: "警告", count: 4 },
  { key: "info", label: "信息", count: 3 },
  { key: "resolved", label: "已解决", count: 6 },
];

const SOURCE_FILTERS: Array<{ key: SourceFilter; label: string }> = [
  { key: "all", label: "全部来源" },
  { key: "kg", label: "KG" },
  { key: "agent", label: "AI 专员" },
  { key: "billing", label: "计费" },
  { key: "api", label: "API" },
  { key: "compliance", label: "合规" },
];

const SOURCE_LABEL: Record<Source, string> = {
  kg: "KG",
  agent: "AI 专员",
  billing: "计费",
  api: "API",
  compliance: "合规",
};

const SOURCE_COLOR: Record<Source, string> = {
  kg: "var(--color-primary)",
  agent: "var(--color-dept-tax)",
  billing: "var(--color-secondary)",
  api: "var(--color-text-secondary)",
  compliance: "var(--color-dept-compliance)",
};

const SEVERITY_BAR_COLOR: Record<Severity, string> = {
  critical: "var(--color-danger)",
  warning: "var(--color-warning)",
  info: "var(--color-primary)",
  resolved: "var(--color-primary)",
};

/* ================================================================
   Helpers
   ================================================================ */

function isResolved(a: Alert): boolean {
  return a.status === "resolved";
}

function matchSeverityFilter(a: Alert, f: SeverityFilter): boolean {
  if (f === "all") return true;
  if (f === "open") return !isResolved(a);
  if (f === "resolved") return isResolved(a);
  return a.severity === f && !isResolved(a);
}

function matchSourceFilter(a: Alert, f: SourceFilter): boolean {
  if (f === "all") return true;
  return a.source === f;
}

/* ================================================================
   Page component
   ================================================================ */

export default function OpsAlertsPage() {
  const [activeSeverity, setActiveSeverity] = useState<SeverityFilter>("open");
  const [activeSource, setActiveSource] = useState<SourceFilter>("all");

  const filtered = ALERTS.filter(
    (a) => matchSeverityFilter(a, activeSeverity) && matchSourceFilter(a, activeSource),
  );

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
          系统告警中心
        </h2>
        <p
          style={{
            fontSize: 11,
            color: "var(--color-text-tertiary)",
            marginTop: "var(--space-1)",
            display: "flex",
            alignItems: "center",
            gap: 6,
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
              flexShrink: 0,
            }}
          />
          实时监控 | {ALERTS.length} 条告警
        </p>
      </section>

      {/* -- KPI strip -- */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: "var(--space-6)",
        }}
      >
        <KpiCard label="待处理" value="8" />
        <KpiCard label="严重" value="2" tint="var(--color-danger)" badgeClass="badge-critical" />
        <KpiCard label="警告" value="4" tint="var(--color-warning)" />
        <KpiCard label="今日已解决" value="6" tint="var(--color-success)" secondary="MTTR 23 分钟" />
      </section>

      {/* -- Filter pills -- */}
      <section style={{ marginBottom: "var(--space-4)" }}>
        {/* Severity row */}
        <div className="flex gap-1" style={{ marginBottom: 8 }}>
          {SEVERITY_FILTERS.map((f) => (
            <PillButton
              key={f.key}
              label={`${f.label}(${f.count})`}
              active={activeSeverity === f.key}
              onClick={() => setActiveSeverity(f.key)}
            />
          ))}
        </div>
        {/* Source row */}
        <div className="flex gap-1">
          {SOURCE_FILTERS.map((f) => (
            <PillButton
              key={f.key}
              label={f.label}
              active={activeSource === f.key}
              onClick={() => setActiveSource(f.key)}
            />
          ))}
        </div>
      </section>

      {/* -- Alert feed -- */}
      <section
        style={{
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
          marginBottom: "var(--space-6)",
        }}
      >
        {filtered.length === 0 && (
          <div
            style={{
              padding: "var(--space-8)",
              textAlign: "center",
              fontSize: 12,
              color: "var(--color-text-tertiary)",
              background: "var(--color-surface-container-lowest)",
            }}
          >
            无匹配告警
          </div>
        )}
        {filtered.map((a, i) => (
          <AlertCard key={a.id} alert={a} alt={i % 2 === 1} />
        ))}
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

function KpiCard({
  label,
  value,
  tint,
  badgeClass,
  secondary,
}: {
  label: string;
  value: string;
  tint?: string;
  badgeClass?: string;
  secondary?: string;
}) {
  return (
    <div
      style={{
        padding: "12px 16px",
        borderRadius: "var(--radius-md)",
        background: tint
          ? `color-mix(in srgb, ${tint} 6%, var(--color-surface-container-lowest))`
          : "var(--color-surface-container-lowest)",
      }}
    >
      <p
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: "var(--color-text-tertiary)",
          textTransform: "uppercase" as const,
          fontFamily: "Inter, var(--font-body)",
          marginBottom: 4,
        }}
      >
        {label}
      </p>
      <span
        className={`font-display font-bold tabular-nums ${badgeClass ?? ""}`}
        style={{
          fontSize: 22,
          lineHeight: 1.1,
          color: tint ?? "var(--color-text-primary)",
          ...(badgeClass
            ? { padding: "2px 8px", borderRadius: "var(--radius-sm)" }
            : {}),
        }}
      >
        {value}
      </span>
      {secondary && (
        <p
          style={{
            fontSize: 10,
            color: "var(--color-text-tertiary)",
            marginTop: 6,
          }}
        >
          {secondary}
        </p>
      )}
    </div>
  );
}

function PillButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 11,
        fontWeight: active ? 700 : 500,
        padding: "4px 12px",
        borderRadius: "var(--radius-sm)",
        background: active
          ? "var(--color-primary)"
          : "var(--color-surface-container)",
        color: active
          ? "var(--color-on-primary)"
          : "var(--color-text-secondary)",
        cursor: "pointer",
        border: "none",
      }}
    >
      {label}
    </button>
  );
}

function AlertCard({ alert: a, alt }: { alert: Alert; alt: boolean }) {
  const toast = useToast();
  const resolved = isResolved(a);
  const barColor = SEVERITY_BAR_COLOR[a.severity];
  const srcColor = SOURCE_COLOR[a.source];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto auto",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "var(--space-3) var(--space-4)",
        paddingLeft: 0,
        background: alt
          ? "var(--color-surface-container-lowest)"
          : "var(--color-surface)",
        borderBottom: "1px solid var(--color-surface-container)",
        opacity: resolved ? 0.5 : 1,
        position: "relative",
      }}
    >
      {/* Severity bar (left edge) */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 4,
          background: resolved ? "var(--color-text-tertiary)" : barColor,
          borderRadius: "var(--radius-sm) 0 0 var(--radius-sm)",
        }}
      />

      {/* Main content */}
      <div style={{ paddingLeft: "var(--space-4)", minWidth: 0 }}>
        {/* Row 1: title */}
        <p
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: "var(--color-text-primary)",
            lineHeight: 1.4,
            margin: 0,
          }}
        >
          {a.title}
        </p>
        {/* Row 2: desc + source badge + timestamp */}
        <div
          className="flex items-center gap-2"
          style={{
            marginTop: 2,
            fontSize: 11,
            color: "var(--color-text-tertiary)",
            minWidth: 0,
          }}
        >
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap" as const,
              flexShrink: 1,
              minWidth: 0,
            }}
          >
            {a.desc}
          </span>
          <SourceBadge source={a.source} color={srcColor} />
          <span
            className="tabular-nums"
            style={{
              flexShrink: 0,
              fontSize: 10,
              color: "var(--color-text-tertiary)",
              textAlign: "left",
            }}
          >
            {a.timestamp}
          </span>
        </div>
      </div>

      {/* Status badge */}
      <StatusBadge status={a.status} />

      {/* Actions */}
      <div className="flex items-center gap-3" style={{ flexShrink: 0 }}>
        {(() => {
          const slug = findAgentSlug(a.title);
          return slug ? (
            <Link
              href={`/ai-team/${slug}`}
              style={{
                fontSize: 10,
                fontWeight: 600,
                color: "var(--color-secondary-dim)",
                textDecoration: "none",
                whiteSpace: "nowrap" as const,
              }}
            >
              查看专员 &rarr;
            </Link>
          ) : null;
        })()}
        <button
          onClick={() => toast(resolved ? `已打开告警 ${a.id} 详情` : `告警 ${a.id} 已标记为处理中`)}
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: "var(--color-primary)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "2px 4px",
            whiteSpace: "nowrap" as const,
          }}
        >
          {resolved ? "查看" : "处理"}
        </button>
      </div>
    </div>
  );
}

function SourceBadge({ source, color }: { source: Source; color: string }) {
  return (
    <span
      style={{
        flexShrink: 0,
        fontSize: 10,
        fontWeight: 600,
        padding: "1px 6px",
        borderRadius: "var(--radius-sm)",
        background: `color-mix(in srgb, ${color} 10%, transparent)`,
        color,
        whiteSpace: "nowrap" as const,
      }}
    >
      {SOURCE_LABEL[source]}
    </span>
  );
}

function StatusBadge({ status }: { status: AlertStatus }) {
  const config: Record<AlertStatus, { label: string; bg: string; color: string; border?: string }> = {
    open: {
      label: "待处理",
      bg: "transparent",
      color: "var(--color-danger)",
      border: "1px solid var(--color-danger)",
    },
    acknowledged: {
      label: "已确认",
      bg: "color-mix(in srgb, var(--color-warning) 12%, transparent)",
      color: "var(--color-secondary-dim)",
    },
    resolved: {
      label: "已解决",
      bg: "color-mix(in srgb, var(--color-success) 10%, transparent)",
      color: "var(--color-success)",
    },
  };

  const c = config[status];

  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: "var(--radius-sm)",
        background: c.bg,
        color: c.color,
        border: c.border ?? "none",
        whiteSpace: "nowrap" as const,
      }}
    >
      {c.label}
    </span>
  );
}
