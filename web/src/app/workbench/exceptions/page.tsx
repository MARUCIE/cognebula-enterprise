"use client";

/* Exception Center — 异常中心
   Design ref: design/stitch-export/stitch/ai_operations_dashboard/screen.png (anomaly alert section)
   Architecture ref: NEXT_GEN_WORKBENCH_DESIGN.md Section 6 + Section 8.1 View 6 */

import { useState } from "react";
import Link from "next/link";
import { AGENT_MAP } from "../../lib/workbench-data";

type Severity = "critical" | "warning" | "info";
type ExceptionType = "hitl" | "failed" | "overdue" | "risk";

interface ExceptionItem {
  id: string;
  severity: Severity;
  type: ExceptionType;
  enterprise: string;
  taskId: number;
  taskName: string;
  agentId: string;
  description: string;
  timestamp: string;
  detail: string;
}

const MOCK_EXCEPTIONS: ExceptionItem[] = [
  { id: "EX-001", severity: "critical", type: "hitl", enterprise: "深圳华税科技有限公司", taskId: 29, taskName: "全盘异常调账", agentId: "xiaoan", description: "需客户书面授意", timestamp: "2h 前", detail: "发现 3 笔异常交易（合计 ¥47,200），需要客户确认调账方向。已发送微信通知，等待回复。" },
  { id: "EX-002", severity: "critical", type: "hitl", enterprise: "广州信达财务咨询", taskId: 24, taskName: "税种申报反馈", agentId: "xiaoke", description: "等待客户同意扣款", timestamp: "5h 前", detail: "增值税 ¥12,340 + 附加税 ¥1,481。已发送扣款确认通知，客户尚未回复。超时阈值: 24h。" },
  { id: "EX-003", severity: "critical", type: "hitl", enterprise: "杭州明远实业集团", taskId: 24, taskName: "税种申报反馈", agentId: "xiaoke", description: "等待客户同意扣款", timestamp: "8h 前", detail: "企业所得税 ¥28,900。第二次提醒已发送。距超时阈值还有 16h。" },
  { id: "EX-004", severity: "warning", type: "failed", enterprise: "北京中信企业管理", taskId: 18, taskName: "增值税申报", agentId: "xiaoshui", description: "申报接口返回错误", timestamp: "1h 前", detail: "电子税务局 API 返回 500 错误。已自动重试 2 次失败。错误码: ETAX-50032 (服务器繁忙)。建议等待 30 分钟后重试。" },
  { id: "EX-005", severity: "warning", type: "failed", enterprise: "上海云帆物流", taskId: 17, taskName: "财报申报", agentId: "xiaoshui", description: "资产负债表不平衡", timestamp: "3h 前", detail: "借方合计 ¥2,345,678 vs 贷方合计 ¥2,345,123，差额 ¥555。可能原因: 未结转损益。需要小算 review。" },
  { id: "EX-006", severity: "warning", type: "failed", enterprise: "成都天府科技", taskId: 15, taskName: "个税申报", agentId: "xiaoshui", description: "员工信息不完整", timestamp: "4h 前", detail: "3 名员工缺少身份证号码。需联系客户补充信息后重新申报。" },
  { id: "EX-007", severity: "warning", type: "overdue", enterprise: "武汉光谷创新", taskId: 13, taskName: "税金记账", agentId: "xiaosuan", description: "超出预期完成时间", timestamp: "6h 前", detail: "预期 2h 内完成，实际已运行 8h。原因: 大量跨期调整凭证 (127 笔)。小算正在处理中，预计还需 2h。" },
  { id: "EX-008", severity: "info", type: "risk", enterprise: "南京紫金山环保", taskId: 31, taskName: "税务风险报告", agentId: "xiaoan", description: "发现潜在税务风险", timestamp: "1d 前", detail: "连续 3 个月增值税税负率低于行业平均 (1.2% vs 3.5%)。建议核查进项发票真实性。风险等级: 中。" },
  { id: "EX-009", severity: "info", type: "risk", enterprise: "厦门海峡贸易", taskId: 31, taskName: "税务风险报告", agentId: "xiaoan", description: "关联交易预警", timestamp: "1d 前", detail: "本月与关联方交易金额 ¥1,200,000，占总收入 42%。需关注转移定价合规性。" },
  { id: "EX-010", severity: "info", type: "risk", enterprise: "重庆渝中建设", taskId: 32, taskName: "风险提醒", agentId: "xiaoan", description: "社保基数调整提醒", timestamp: "2d 前", detail: "2026 年度社保缴费基数已更新，15 名员工需调整缴费金额。建议在下月 W1 采集期更新。" },
  { id: "EX-011", severity: "warning", type: "failed", enterprise: "西安古都文化", taskId: 1, taskName: "银行流水采集", agentId: "xiaozhi", description: "银行接口超时", timestamp: "12h 前", detail: "工商银行企业网银 API 连接超时。已切换到 OCR 扫描模式处理。" },
  { id: "EX-012", severity: "critical", type: "hitl", enterprise: "长沙岳麓科技", taskId: 28, taskName: "全盘账务反馈", agentId: "zongjian", description: "等待客户确认账务", timestamp: "1d 前", detail: "3 月全盘账务报告已发送。客户需确认无误后关闭质检流程。已发送第一次提醒。" },
];

const TYPE_TABS: { type: ExceptionType | "all"; label: string }[] = [
  { type: "all", label: "全部" },
  { type: "hitl", label: "HITL 待审批" },
  { type: "failed", label: "处理失败" },
  { type: "overdue", label: "逾期任务" },
  { type: "risk", label: "风险告警" },
];

const SEVERITY_STYLES: Record<Severity, { dot: string; bg: string }> = {
  critical: { dot: "#C4281C", bg: "#FDECEB" },
  warning: { dot: "#C5913E", bg: "#FEF3E0" },
  info: { dot: "#003A70", bg: "#E8F0FE" },
};

export default function ExceptionsPage() {
  const [activeTab, setActiveTab] = useState<ExceptionType | "all">("all");
  const [selected, setSelected] = useState<ExceptionItem | null>(MOCK_EXCEPTIONS[0]);

  const filtered = activeTab === "all" ? MOCK_EXCEPTIONS : MOCK_EXCEPTIONS.filter((e) => e.type === activeTab);
  const counts: Record<string, number> = {
    all: MOCK_EXCEPTIONS.length,
    hitl: MOCK_EXCEPTIONS.filter((e) => e.type === "hitl").length,
    failed: MOCK_EXCEPTIONS.filter((e) => e.type === "failed").length,
    overdue: MOCK_EXCEPTIONS.filter((e) => e.type === "overdue").length,
    risk: MOCK_EXCEPTIONS.filter((e) => e.type === "risk").length,
  };

  return (
    <div style={{ background: "var(--color-surface)", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ padding: "var(--space-6) var(--space-8)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px" }}>WORKBENCH / EXCEPTIONS</div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", marginTop: 4 }}>异常中心</h1>
          </div>
          <Link href="/workbench" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>返回看板</Link>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--color-surface-container)", padding: "0 var(--space-8)" }}>
        {TYPE_TABS.map((tab) => (
          <button
            key={tab.type}
            onClick={() => setActiveTab(tab.type)}
            style={{
              padding: "12px 20px",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.type ? "2px solid var(--color-primary)" : "2px solid transparent",
              fontSize: "13px",
              fontWeight: activeTab === tab.type ? 700 : 400,
              color: activeTab === tab.type ? "var(--color-primary)" : "var(--color-text-secondary)",
              cursor: "pointer",
            }}
          >
            {tab.label} ({counts[tab.type]})
          </button>
        ))}
      </div>

      {/* Content: List + Detail */}
      <div style={{ display: "flex", height: "calc(100vh - 160px)" }}>
        {/* Exception List */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {filtered.map((ex) => {
            const agent = AGENT_MAP[ex.agentId];
            const sev = SEVERITY_STYLES[ex.severity];
            const isSelected = selected?.id === ex.id;

            return (
              <div
                key={ex.id}
                onClick={() => setSelected(ex)}
                style={{
                  padding: "14px var(--space-8)",
                  borderBottom: "1px solid var(--color-surface-container)",
                  background: isSelected ? "var(--color-primary-fixed)" : "transparent",
                  cursor: "pointer",
                  borderLeft: isSelected ? "3px solid var(--color-primary)" : "3px solid transparent",
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  {/* Severity dot */}
                  <div style={{ width: 8, height: 8, background: sev.dot, marginTop: 5, flexShrink: 0 }} />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Enterprise + Task */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {ex.enterprise}
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)", whiteSpace: "nowrap", marginLeft: 8 }}>{ex.timestamp}</span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "12px" }}>
                      <span style={{ color: "var(--color-text-secondary)" }}>T{ex.taskId} {ex.taskName}</span>
                      <span style={{ color: "var(--color-text-tertiary)" }}>·</span>
                      <span style={{ color: "var(--color-text-tertiary)" }}>{agent?.name}</span>
                    </div>

                    <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: 4 }}>{ex.description}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div style={{ width: 420, borderLeft: "1px solid var(--color-surface-container)", background: "var(--color-surface-container-lowest)", padding: 24, overflowY: "auto" }}>
            {/* Severity banner */}
            <div style={{ padding: "8px 12px", background: SEVERITY_STYLES[selected.severity].bg, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 8, height: 8, background: SEVERITY_STYLES[selected.severity].dot }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: SEVERITY_STYLES[selected.severity].dot, textTransform: "uppercase", letterSpacing: "1px" }}>
                {selected.severity === "critical" ? "紧急" : selected.severity === "warning" ? "警告" : "提示"}
              </span>
            </div>

            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-text-tertiary)", letterSpacing: "1px", marginBottom: 4 }}>{selected.id} · {selected.timestamp}</div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 4 }}>{selected.enterprise}</h2>
            <div style={{ fontSize: "13px", color: "var(--color-text-secondary)", marginBottom: 16 }}>T{selected.taskId} {selected.taskName} · {AGENT_MAP[selected.agentId]?.name} ({AGENT_MAP[selected.agentId]?.role})</div>

            {/* Description */}
            <div style={{ padding: "12px 16px", background: "var(--color-surface)", marginBottom: 16, fontSize: "13px", lineHeight: 1.7, color: "var(--color-text-primary)" }}>
              {selected.detail}
            </div>

            {/* Action buttons */}
            <div style={{ display: "flex", gap: 8 }}>
              <button style={{ flex: 1, padding: "10px", background: "var(--gradient-cta)", color: "#fff", border: "none", fontSize: "13px", fontWeight: 700, cursor: "pointer" }}>
                处理
              </button>
              <button style={{ padding: "10px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", border: "none", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}>
                跳过
              </button>
              <button style={{ padding: "10px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", border: "none", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}>
                升级到总监
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
