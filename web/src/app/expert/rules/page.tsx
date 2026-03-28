"use client";

const RULES = [
  { id: "CR-001", name: "增值税一般纳税人认定", condition: "年应税销售额 > 500 万", status: "active", hitCount: 3842, lastHit: "2024-11-24" },
  { id: "CR-002", name: "研发费用加计扣除", condition: "研发支出占比 > 3% AND 高新认定有效", status: "active", hitCount: 1256, lastHit: "2024-11-23" },
  { id: "CR-003", name: "关联交易异常预警", condition: "关联方交易占比 > 30% OR 定价偏离 > 20%", status: "warning", hitCount: 89, lastHit: "2024-11-22" },
  { id: "CR-004", name: "存货周转异常", condition: "存货周转天数 > 行业均值 x 1.5", status: "active", hitCount: 234, lastHit: "2024-11-21" },
  { id: "CR-005", name: "现金流量异常", condition: "经营现金流 < 净利润 x 0.5 连续 2 季", status: "critical", hitCount: 12, lastHit: "2024-11-24" },
  { id: "CR-006", name: "进项税额抵扣合规", condition: "取得合规增值税专用发票 AND 用途合规", status: "active", hitCount: 8921, lastHit: "2024-11-24" },
  { id: "CR-007", name: "跨境支付预提税", condition: "支付境外 > 单笔 5 万美元 AND 非协定国", status: "active", hitCount: 45, lastHit: "2024-11-20" },
  { id: "CR-008", name: "印花税计提规则", condition: "合同金额 > 0 AND 属于应税凭证类型", status: "deprecated", hitCount: 0, lastHit: "--" },
];

const statusMap: Record<string, { label: string; color: string }> = {
  active: { label: "生效", color: "var(--color-success, #16A34A)" },
  warning: { label: "预警", color: "var(--color-secondary-dim, #B8860B)" },
  critical: { label: "严重", color: "var(--color-danger, #DC2626)" },
  deprecated: { label: "废弃", color: "var(--color-text-tertiary)" },
};

export default function RulesPage() {
  return (
    <div style={{ padding: "var(--space-6) var(--space-8)", maxWidth: 1100, margin: "0 auto" }}>
      <p style={{ fontSize: 13, color: "var(--color-text-tertiary)", marginBottom: 20 }}>
        查看、调试和测试 KG 中的合规规则触发条件
      </p>

      <div style={{ background: "var(--color-surface-container-lowest)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-surface-container)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-surface-container)" }}>
              {["ID", "规则名称", "触发条件", "状态", "命中次数", "最近命中"].map((h) => (
                <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--color-text-tertiary)", textTransform: "uppercase" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RULES.map((r) => {
              const s = statusMap[r.status];
              return (
                <tr key={r.id} style={{ borderBottom: "1px solid var(--color-surface-container-low)" }}>
                  <td style={{ padding: "10px 14px", color: "var(--color-text-tertiary)", fontSize: 11 }}>{r.id}</td>
                  <td style={{ padding: "10px 14px", color: "var(--color-text-primary)", fontWeight: 600 }}>{r.name}</td>
                  <td style={{ padding: "10px 14px", color: "var(--color-text-secondary)", fontSize: 12 }}>{r.condition}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: "var(--radius-sm)", background: `color-mix(in srgb, ${s.color} 10%, var(--color-surface))`, color: s.color }}>{s.label}</span>
                  </td>
                  <td style={{ padding: "10px 14px", color: "var(--color-text-primary)" }}>{r.hitCount.toLocaleString()}</td>
                  <td style={{ padding: "10px 14px", color: "var(--color-text-tertiary)", fontSize: 12 }}>{r.lastHit}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
