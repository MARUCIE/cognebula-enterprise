/* Customer Health Matrix -- "/ops/customers"
   Bloomberg Ops density. All mock data, no API calls.
   Co-located sub-components at bottom of file. */

"use client";

import { useState } from "react";

/* ================================================================
   Types
   ================================================================ */

type Tier = "enterprise" | "professional" | "starter";
type Health = "green" | "yellow" | "red";

interface Customer {
  name: string;
  tier: Tier;
  lastActive: string;
  agentUtil: number;
  completionRate: number;
  errorRate: number;
}

/* ================================================================
   Mock data (12 companies)
   ================================================================ */

const CUSTOMERS: Customer[] = [
  { name: "中铁建设集团有限公司",       tier: "enterprise",    lastActive: "2024-11-15", agentUtil: 82,  completionRate: 96.1, errorRate: 0.8 },
  { name: "阿里巴巴（中国）网络技术",   tier: "enterprise",    lastActive: "2024-11-14", agentUtil: 91,  completionRate: 98.3, errorRate: 0.3 },
  { name: "腾讯科技（深圳）有限公司",   tier: "enterprise",    lastActive: "2024-11-13", agentUtil: 78,  completionRate: 94.7, errorRate: 1.2 },
  { name: "美团点评（北京）科技有限公司", tier: "professional", lastActive: "2024-11-12", agentUtil: 65,  completionRate: 89.2, errorRate: 3.1 },
  { name: "深圳极智科技有限公司",       tier: "professional",  lastActive: "2024-11-11", agentUtil: 71,  completionRate: 92.5, errorRate: 1.5 },
  { name: "华夏贸易进出口有限公司",     tier: "professional",  lastActive: "2024-11-09", agentUtil: 58,  completionRate: 85.0, errorRate: 3.8 },
  { name: "光影传媒艺术工作室",         tier: "starter",       lastActive: "2024-11-08", agentUtil: 45,  completionRate: 88.4, errorRate: 1.0 },
  { name: "泰和养老服务集团",           tier: "professional",  lastActive: "2024-11-10", agentUtil: 69,  completionRate: 91.8, errorRate: 0.9 },
  { name: "云峰智源股份",               tier: "enterprise",    lastActive: "2024-10-28", agentUtil: 33,  completionRate: 72.1, errorRate: 8.2 },
  { name: "联合创新贸易有限公司",       tier: "professional",  lastActive: "2024-11-11", agentUtil: 76,  completionRate: 93.6, errorRate: 1.1 },
  { name: "时代传媒有限公司",           tier: "starter",       lastActive: "2024-11-06", agentUtil: 41,  completionRate: 80.5, errorRate: 2.4 },
  { name: "鹏程万里物流集团",           tier: "enterprise",    lastActive: "2024-11-14", agentUtil: 88,  completionRate: 97.0, errorRate: 0.5 },
];

const TIER_LABEL: Record<Tier, string> = {
  enterprise: "企业版",
  professional: "专业版",
  starter: "入门版",
};

const TIER_FILTERS: Array<{ key: Tier | "all"; label: string }> = [
  { key: "all", label: "全部" },
  { key: "enterprise", label: "企业版" },
  { key: "professional", label: "专业版" },
  { key: "starter", label: "入门版" },
];

function deriveHealth(c: Customer): Health {
  if (c.errorRate > 5) return "red";
  if (c.errorRate > 2) return "yellow";
  return "green";
}

/* ================================================================
   Page component
   ================================================================ */

export default function OpsCustomersPage() {
  const [activeTier, setActiveTier] = useState<Tier | "all">("all");

  const filtered =
    activeTier === "all"
      ? CUSTOMERS
      : CUSTOMERS.filter((c) => c.tier === activeTier);

  const healthCounts = { green: 0, yellow: 0, red: 0 };
  let utilSum = 0;
  for (const c of CUSTOMERS) {
    healthCounts[deriveHealth(c)]++;
    utilSum += c.agentUtil;
  }
  const avgUtil = (utilSum / CUSTOMERS.length).toFixed(1);

  const GRID_COLS = "minmax(200px, 1.5fr) 80px 100px 90px 80px 80px 60px 60px";

  return (
    <div>
      {/* -- Page header -- */}
      <section
        className="flex justify-between items-end"
        style={{ marginBottom: "var(--space-6)" }}
      >
        <div>
          <h2
            className="font-display font-bold"
            style={{
              fontSize: 20,
              lineHeight: 1.3,
              color: "var(--color-text-primary)",
            }}
          >
            客户健康矩阵
          </h2>
          <p
            style={{
              fontSize: 11,
              color: "var(--color-text-tertiary)",
              marginTop: "var(--space-1)",
            }}
          >
            {CUSTOMERS.length} 家活跃客户 | 最后刷新: 2024-11-15 14:30
          </p>
        </div>

        {/* Tier filter pills */}
        <div className="flex gap-1">
          {TIER_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setActiveTier(f.key)}
              style={{
                fontSize: 11,
                fontWeight: activeTier === f.key ? 700 : 500,
                padding: "4px 12px",
                borderRadius: "var(--radius-sm)",
                background:
                  activeTier === f.key
                    ? "var(--color-primary)"
                    : "var(--color-surface-container-low)",
                color:
                  activeTier === f.key
                    ? "var(--color-on-primary)"
                    : "var(--color-text-secondary)",
                cursor: "pointer",
                border: "none",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </section>

      {/* -- KPI strip -- */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 12,
          marginBottom: "var(--space-6)",
        }}
      >
        <KpiCard label="客户总数" value={String(CUSTOMERS.length)} />
        <KpiCard
          label="健康"
          value={String(healthCounts.green)}
          tint="var(--color-success)"
        />
        <KpiCard
          label="待关注"
          value={String(healthCounts.yellow)}
          tint="var(--color-warning)"
        />
        <KpiCard
          label="风险客户"
          value={String(healthCounts.red)}
          tint="var(--color-danger)"
        />
        <KpiCard label="平均利用率" value={`${avgUtil}%`} />
      </section>

      {/* -- Customer health table -- */}
      <section
        style={{
          borderRadius: "var(--radius-md)",
          background: "var(--color-surface-container-low)",
          overflow: "hidden",
          marginBottom: "var(--space-6)",
        }}
      >
        {/* Column headers */}
        <div
          className="grid items-center"
          style={{
            gridTemplateColumns: GRID_COLS,
            padding: "10px 16px",
            background: "var(--color-surface-container)",
            fontSize: 10,
            fontWeight: 700,
            color: "var(--color-text-secondary)",
            textTransform: "uppercase" as const,
            fontFamily: "var(--font-body)",
          }}
        >
          <span>公司名称</span>
          <span>订阅</span>
          <span>最后活跃</span>
          <span>Agent利用率</span>
          <span>完成率</span>
          <span>错误率</span>
          <span>健康</span>
          <span>操作</span>
        </div>

        {/* Rows */}
        {filtered.map((c, i) => (
          <CustomerRow key={c.name} customer={c} alt={i % 2 === 1} gridCols={GRID_COLS} />
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
}: {
  label: string;
  value: string;
  tint?: string;
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
        className="font-display font-bold tabular-nums"
        style={{
          fontSize: 22,
          lineHeight: 1.1,
          color: tint ?? "var(--color-text-primary)",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function CustomerRow({
  customer: c,
  alt,
  gridCols,
}: {
  customer: Customer;
  alt: boolean;
  gridCols: string;
}) {
  const health = deriveHealth(c);

  const healthColor =
    health === "green"
      ? "var(--color-success)"
      : health === "yellow"
        ? "var(--color-warning)"
        : "var(--color-danger)";

  const errorColor =
    c.errorRate > 5
      ? "var(--color-danger)"
      : c.errorRate > 2
        ? "var(--color-warning)"
        : "var(--color-text-secondary)";

  return (
    <div
      className="grid items-center"
      style={{
        gridTemplateColumns: gridCols,
        height: 36,
        padding: "0 16px",
        background: alt
          ? "var(--color-surface-container-lowest)"
          : "var(--color-surface)",
        fontSize: 12,
        color: "var(--color-text-primary)",
      }}
    >
      {/* Company name */}
      <span
        className="font-bold"
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap" as const,
        }}
      >
        {c.name}
      </span>

      {/* Tier badge */}
      <span>
        <TierBadge tier={c.tier} />
      </span>

      {/* Last active */}
      <span
        className="tabular-nums"
        style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}
      >
        {c.lastActive}
      </span>

      {/* Agent utilization: number + mini bar */}
      <span className="flex items-center gap-2">
        <MiniBar pct={c.agentUtil} />
        <span className="tabular-nums" style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
          {c.agentUtil}%
        </span>
      </span>

      {/* Completion rate */}
      <span className="tabular-nums" style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
        {c.completionRate.toFixed(1)}%
      </span>

      {/* Error rate */}
      <span
        className="tabular-nums font-bold"
        style={{ fontSize: 11, color: errorColor }}
      >
        {c.errorRate.toFixed(1)}%
      </span>

      {/* Health dot */}
      <span className="flex items-center justify-center">
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: healthColor,
            display: "inline-block",
          }}
        />
      </span>

      {/* Action */}
      <span>
        <button
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: "var(--color-primary)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          详情
        </button>
      </span>
    </div>
  );
}

function TierBadge({ tier }: { tier: Tier }) {
  const colorMap: Record<Tier, string> = {
    enterprise: "var(--color-primary)",
    professional: "var(--color-secondary-dim)",
    starter: "var(--color-text-tertiary)",
  };
  const c = colorMap[tier];

  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 6px",
        borderRadius: "var(--radius-sm)",
        background: `color-mix(in srgb, ${c} 10%, transparent)`,
        color: c,
        whiteSpace: "nowrap" as const,
      }}
    >
      {TIER_LABEL[tier]}
    </span>
  );
}

function MiniBar({ pct }: { pct: number }) {
  const fillColor =
    pct >= 70
      ? "var(--color-success)"
      : pct >= 50
        ? "var(--color-warning)"
        : "var(--color-danger)";

  return (
    <span
      style={{
        display: "inline-block",
        width: 40,
        height: 4,
        borderRadius: 2,
        background: "var(--color-surface-container)",
        overflow: "hidden",
      }}
    >
      <span
        style={{
          display: "block",
          width: `${pct}%`,
          height: "100%",
          borderRadius: 2,
          background: fillColor,
        }}
      />
    </span>
  );
}
