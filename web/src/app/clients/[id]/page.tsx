/* Client Detail -- "/clients/[id]"
   Action-first layout (Jobs): status → risk → agent activity → pending → history
   Swarm consensus: "老板不看法人电话，他看这个客户今天有没有雷" */

import Link from "next/link";
import { CLIENTS, CLIENT_IDS, getClientById } from "../../lib/clients";
import { AGENT_SLUG } from "../../lib/agents";

export function generateStaticParams() {
  return CLIENT_IDS.map((id) => ({ id }));
}

/* ================================================================
   Page component
   ================================================================ */

export default async function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const client = getClientById(id);
  if (!client) return <div>客户不存在</div>;

  const c = client;
  const pendingActions = c.recentActivity.filter((a) => a.status === "progress" || a.status === "error");
  const completedActions = c.recentActivity.filter((a) => a.status === "done");

  const statusColor =
    c.complianceScore >= 95
      ? "var(--color-success)"
      : c.complianceScore >= 85
        ? "var(--color-warning)"
        : "var(--color-danger)";

  const statusLabel =
    c.complianceScore >= 95 ? "正常" : c.complianceScore >= 85 ? "需关注" : "风险";

  // AI Risk Insight (mock, context-aware)
  const riskInsights: Record<string, string> = {
    "zhongtie-jianshe": "该客户连续 3 个月增值税税负率低于行业均值 0.3%，建议人工复核进项抵扣明细",
    "alibaba-wangluo": "跨境关联交易占总收入 42%，已触发转让定价预警线（>30%），建议提前准备同期资料",
    "tengxun-keji": "研发费用加计扣除金额同比增长 58%，超出同行业平均增速，建议留存完整研发台账备查",
    "meituan-dianping": "Q3 合规审查已全部通过，无待处理事项。客户健康状况良好",
    "shenzhen-jizhi": "高新技术企业认定年审临近（2025-01-15），建议提前 2 个月准备申报材料",
    "huaxia-maoyi": "跨境转让定价文档缺失 2024 Q3 部分，合规风险等级已上调至中",
    "guangying-chuanmei": "小规模纳税人季度收入接近 30 万元起征点（当前 28.6 万），建议关注开票节奏",
    "taihe-yanglao": "连锁分店间内部交易频繁，建议季度性合并报表审查以确保一致性",
  };
  const riskText = riskInsights[c.id] ?? "暂无风险提示";
  const isGoodNews = c.complianceScore >= 95 && !riskText.includes("建议");

  return (
    <div>
      {/* ── Back + Header ── */}
      <div className="flex items-center gap-3" style={{ marginBottom: "var(--space-4)" }}>
        <Link
          href="/clients"
          style={{
            fontSize: 12,
            color: "var(--color-primary)",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          &larr; 返回客户列表
        </Link>
      </div>

      <section
        className="flex items-start justify-between"
        style={{ marginBottom: "var(--space-6)" }}
      >
        <div className="flex items-center gap-4">
          <div
            className="flex items-center justify-center font-display font-bold"
            style={{
              width: 48,
              height: 48,
              borderRadius: "var(--radius-md)",
              background: `color-mix(in srgb, ${c.initialColor} 12%, transparent)`,
              color: c.initialColor,
              fontSize: 22,
            }}
          >
            {c.initial}
          </div>
          <div>
            <h2
              className="font-display font-bold"
              style={{ fontSize: 20, color: "var(--color-text-primary)", lineHeight: 1.3 }}
            >
              {c.name}
            </h2>
            <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginTop: 2 }}>
              {c.industry} · {c.tier === "enterprise" ? "企业版" : c.tier === "professional" ? "专业版" : "入门版"} · 服务开始 {c.serviceStartDate}
            </p>
          </div>
        </div>
        <div
          className="flex items-center gap-2"
          style={{
            padding: "6px 14px",
            borderRadius: "var(--radius-sm)",
            background: `color-mix(in srgb, ${statusColor} 8%, transparent)`,
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor, display: "inline-block" }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: statusColor }}>{statusLabel}</span>
        </div>
      </section>

      {/* ── KPI strip + AI Risk Insight ── */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: "1fr 1fr 1fr 1.5fr",
          gap: 12,
          marginBottom: "var(--space-6)",
        }}
      >
        <KpiCard label="合规评分" value={`${c.complianceScore}`} tint={statusColor} suffix="/100" />
        <KpiCard label="AI 已完成任务" value={String(c.aiTasksCompleted)} />
        <KpiCard label="待处理" value={String(c.aiTasksPending + pendingActions.length)} tint={pendingActions.length > 0 ? "var(--color-warning)" : undefined} />

        {/* AI Risk Insight card */}
        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            background: isGoodNews
              ? "color-mix(in srgb, var(--color-success) 4%, var(--color-surface-container-lowest))"
              : "color-mix(in srgb, var(--color-secondary) 6%, var(--color-surface-container-lowest))",
            borderLeft: `3px solid ${isGoodNews ? "var(--color-success)" : "var(--color-secondary)"}`,
          }}
        >
          <p
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "var(--color-text-tertiary)",
              marginBottom: 6,
            }}
          >
            AI 风险嗅探
          </p>
          <p style={{ fontSize: 12, color: "var(--color-text-primary)", lineHeight: 1.6 }}>
            {riskText}
          </p>
        </div>
      </section>

      {/* ── Current Agent Activity ── */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h3
          className="font-display font-bold"
          style={{ fontSize: 16, color: "var(--color-text-primary)", marginBottom: "var(--space-4)" }}
        >
          当前 AI 专员活动
        </h3>
        <div className="flex flex-col gap-3">
          {c.recentActivity.map((a, i) => {
            const slug = AGENT_SLUG[a.agent] ?? "";
            return (
              <div
                key={i}
                className="flex items-center justify-between"
                style={{
                  padding: "12px 16px",
                  borderRadius: "var(--radius-md)",
                  background: a.status === "progress"
                    ? "color-mix(in srgb, var(--color-primary) 4%, var(--color-surface-container-lowest))"
                    : "var(--color-surface-container-lowest)",
                  borderLeft: a.status === "progress"
                    ? "3px solid var(--color-primary)"
                    : a.status === "error"
                      ? "3px solid var(--color-danger)"
                      : "3px solid transparent",
                }}
              >
                <div>
                  <span className="font-bold" style={{ fontSize: 13, color: "var(--color-text-primary)" }}>
                    {a.action}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginLeft: 12 }}>
                    {a.date}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <StatusDot status={a.status} />
                  {slug ? (
                    <Link
                      href={`/ai-team/${slug}`}
                      style={{ fontSize: 11, fontWeight: 600, color: "var(--color-secondary-dim)", textDecoration: "none" }}
                    >
                      {a.agent} &rarr;
                    </Link>
                  ) : (
                    <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{a.agent}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Client Profile (below fold) ── */}
      <section
        style={{
          padding: "var(--space-6)",
          borderRadius: "var(--radius-md)",
          background: "var(--color-surface-container-lowest)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "var(--space-6)",
        }}
      >
        <h3
          className="font-display font-bold"
          style={{ fontSize: 16, color: "var(--color-text-primary)", marginBottom: "var(--space-5)" }}
        >
          客户基本信息
        </h3>
        <div
          className="grid"
          style={{ gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}
        >
          <InfoRow label="统一社会信用代码" value={c.registrationNo} />
          <InfoRow label="法定代表人" value={c.legalRep} />
          <InfoRow label="注册地址" value={c.address} />
          <InfoRow label="联系电话" value={c.phone} />
          <InfoRow label="税号" value={c.taxId} />
          <InfoRow label="年营收" value={c.annualRevenue} />
          <InfoRow label="员工人数" value={`${c.employeeCount.toLocaleString()} 人`} />
          <InfoRow label="月度服务费" value={c.monthlyFee} />
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        className="text-center"
        style={{
          padding: "var(--space-8) 0 var(--space-4)",
          color: "var(--color-text-tertiary)",
          fontSize: 11,
        }}
      >
        <p>安全加密数据环境 -- 灵阙 AI 引擎 V2.4</p>
        <p>&copy; 2024 灵阙财税科技. All rights reserved.</p>
      </footer>
    </div>
  );
}

/* ================================================================
   Sub-components
   ================================================================ */

function KpiCard({ label, value, tint, suffix }: { label: string; value: string; tint?: string; suffix?: string }) {
  return (
    <div
      style={{
        padding: "14px 16px",
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
          marginBottom: 4,
        }}
      >
        {label}
      </p>
      <span
        className="font-display font-bold tabular-nums"
        style={{ fontSize: 24, lineHeight: 1.1, color: tint ?? "var(--color-text-primary)" }}
      >
        {value}
      </span>
      {suffix && (
        <span style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginLeft: 2 }}>{suffix}</span>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 2 }}>
        {label}
      </p>
      <p style={{ fontSize: 13, color: "var(--color-text-primary)" }}>{value}</p>
    </div>
  );
}

function StatusDot({ status }: { status: "done" | "progress" | "error" }) {
  const color =
    status === "done"
      ? "var(--color-success)"
      : status === "progress"
        ? "var(--color-primary)"
        : "var(--color-danger)";
  return (
    <span
      className={status === "progress" ? "ai-glow" : ""}
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: color,
      }}
    />
  );
}
