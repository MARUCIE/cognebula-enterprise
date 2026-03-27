/* Compliance Dashboard -- "合规看板"
   Layout reference: design/stitch-export/stitch/compliance_dashboard/screen.png
   Brand: 灵阙财税 (NOT "智汇算 AI")
   All data is static mock for initial build. */

export default function ComplianceDashboardPage() {
  return (
    <div className="flex gap-0">
      {/* ── Main content area ── */}
      <div className="flex-1 min-w-0">
        {/* ── Page header ── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <h2
            className="font-display font-extrabold"
            style={{
              fontSize: "2rem",
              lineHeight: 1.2,
              color: "var(--color-text-primary)",
            }}
          >
            合规管理看板
          </h2>
          <p
            style={{
              fontSize: 13,
              color: "var(--color-text-secondary)",
              marginTop: "var(--space-2)",
            }}
          >
            灵阙 AI 全量扫描 200 位客户，实时监控合规状态
          </p>
        </section>

        {/* ── Stats bar ── */}
        <section
          className="grid gap-6"
          style={{
            gridTemplateColumns: "repeat(3, 1fr)",
            marginBottom: "var(--space-8)",
          }}
        >
          <ComplianceStat
            dotColor="var(--color-success)"
            label="合规客户"
            count={156}
            total={200}
            percent="78%"
          />
          <ComplianceStat
            dotColor="var(--color-warning)"
            label="需关注"
            count={32}
            total={200}
            percent="16%"
          />
          <ComplianceStat
            dotColor="var(--color-danger)"
            label="风险客户"
            count={12}
            total={200}
            percent="6%"
          />
        </section>

        {/* ── Filter row ── */}
        <section
          className="flex items-center justify-between"
          style={{
            marginBottom: "var(--space-6)",
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <div
            className="flex"
            style={{
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface-container)",
              padding: 3,
            }}
          >
            <FilterTab label="全部" active />
            <FilterTab label="合规" />
            <FilterTab label="需关注" />
            <FilterTab label="风险" />
          </div>
          <div className="flex items-center gap-3">
            <select
              className="font-body"
              style={{
                fontSize: 13,
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-surface-container-lowest)",
                color: "var(--color-text-secondary)",
                border: "none",
                outline: "none",
              }}
            >
              <option>所有行业</option>
              <option>科技信息</option>
              <option>贸易零售</option>
              <option>生产制造</option>
            </select>
            <span className="tabular-nums" style={{ fontSize: 12, color: "var(--color-text-tertiary)", textAlign: "left" }}>
              2024-11-24
            </span>
          </div>
        </section>

        {/* ── Traffic light grid ── */}
        <section
          className="grid gap-3"
          style={{
            gridTemplateColumns: "repeat(6, 1fr)",
            marginBottom: "var(--space-8)",
          }}
        >
          {COMPLIANCE_ITEMS.map((item) => (
            <ComplianceCard
              key={item.id}
              name={item.name}
              id={item.id}
              status={item.status}
              selected={item.selected}
            />
          ))}
        </section>

        {/* ── Action buttons ── */}
        <section
          className="flex gap-3"
          style={{ marginBottom: "var(--space-8)" }}
        >
          <button
            className="flex items-center gap-2 font-bold"
            style={{
              fontSize: 13,
              padding: "10px 24px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-primary)",
              color: "var(--color-on-primary)",
            }}
          >
            <ReportIcon />
            生成审计报告
          </button>
          <button
            className="flex items-center gap-2 font-bold"
            style={{
              fontSize: 13,
              padding: "10px 24px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-lowest)",
              color: "var(--color-primary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <MailIcon />
            发送风险提醒
          </button>
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

      {/* ── Right drawer panel ── */}
      <aside
        className="shrink-0 flex flex-col"
        style={{
          width: 380,
          marginLeft: "var(--space-6)",
          background: "var(--color-surface-container-lowest)",
          boxShadow: "-8px 0 24px rgba(0, 36, 74, 0.03)",
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
        }}
      >
        {/* Drawer header */}
        <div
          style={{
            padding: "var(--space-6)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <h3
            className="font-display font-extrabold"
            style={{ fontSize: 16, color: "var(--color-primary)" }}
          >
            深圳创新电子 -- 风险详情
          </h3>
          <p
            style={{
              fontSize: 11,
              color: "var(--color-text-tertiary)",
              marginTop: "var(--space-1)",
            }}
          >
            最后扫描: 2024-11-24 14:30
          </p>
        </div>

        {/* Risk items */}
        <div
          className="flex-1 overflow-y-auto flex flex-col gap-4"
          style={{ padding: "var(--space-6)" }}
        >
          {/* High risk */}
          <RiskItem
            severity="high"
            severityLabel="高"
            title="税务申报异常"
            description="在最近的增值税申报周期中，进项税额抵扣与进货单据总额存在 12.5% 的非正常偏差。"
            citations={["增值税暂行条例 第15条", "财税 [2016] 36号"]}
            aiSuggestion="请核查发票流水号 2024XJ-0012 至 2024XJ-0045 的申报状态。建议补充关联交易说明文件。"
          />

          {/* Medium risk */}
          <RiskItem
            severity="medium"
            severityLabel="中"
            title="研发费用加计扣除证据链"
            description="研发工时记录表缺失部门负责人电子签名，可能导致合规性审计扣分。"
            citations={["研发费用税前加计扣除指引"]}
          />

          {/* Low risk */}
          <RiskItem
            severity="low"
            severityLabel="低"
            title="股权转让个税申报提醒"
            description="检测到近期股东变更，请确保在协议签署后 30 日内完成税务备案。"
            citations={["个人所得税法 第8条"]}
          />
        </div>

        {/* Drawer actions */}
        <div style={{ padding: "var(--space-6)" }}>
          <button
            className="font-bold flex items-center justify-center gap-2"
            style={{
              width: "100%",
              fontSize: 13,
              padding: "12px 0",
              borderRadius: "var(--radius-md)",
              background: "var(--color-primary)",
              color: "var(--color-on-primary)",
            }}
          >
            <ReportIcon />
            生成详细审计报告
          </button>
          <button
            className="font-bold flex items-center justify-center gap-2"
            style={{
              width: "100%",
              fontSize: 13,
              padding: "12px 0",
              marginTop: "var(--space-3)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-lowest)",
              color: "var(--color-primary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <MailIcon />
            发送风险提醒给客户
          </button>
        </div>
      </aside>
    </div>
  );
}

/* ================================================================
   Mock data
   ================================================================ */

type ComplianceItemData = {
  name: string;
  id: string;
  status: "green" | "amber" | "red";
  selected?: boolean;
};

const COMPLIANCE_ITEMS: ComplianceItemData[] = [
  { name: "杭州明达科技", id: "8829-CN", status: "green" },
  { name: "上海恒远贸易", id: "9021-CN", status: "green" },
  { name: "深圳创新电子", id: "7623-CN", status: "red", selected: true },
  { name: "北京卓越咨询", id: "7712-CN", status: "amber" },
  { name: "广东星联实业", id: "1001-CN", status: "green" },
  { name: "江苏华茂物流", id: "1002-CN", status: "green" },
  { name: "浙江正泰控股", id: "1003-CN", status: "amber" },
  { name: "成都博众软件", id: "1004-CN", status: "green" },
  { name: "武汉天喻信息", id: "1005-CN", status: "green" },
  { name: "西安隆基股份", id: "1006-CN", status: "amber" },
  { name: "南京泉峰汽车", id: "1007-CN", status: "green" },
  { name: "长沙中联重科", id: "1008-CN", status: "green" },
  { name: "中铁建设集团", id: "2001-CN", status: "green" },
  { name: "阿里巴巴网络技术", id: "2002-CN", status: "amber" },
  { name: "腾讯科技深圳", id: "2003-CN", status: "green" },
  { name: "美团点评科技", id: "2004-CN", status: "green" },
  { name: "华为技术有限", id: "2005-CN", status: "green" },
  { name: "京东世纪贸易", id: "2006-CN", status: "amber" },
  { name: "比亚迪股份", id: "2007-CN", status: "green" },
  { name: "宁德时代新能源", id: "2008-CN", status: "green" },
  { name: "小米通讯技术", id: "2009-CN", status: "red" },
  { name: "字节跳动科技", id: "2010-CN", status: "green" },
  { name: "网易杭州网络", id: "2011-CN", status: "amber" },
  { name: "顺丰速运集团", id: "2012-CN", status: "green" },
  { name: "格力电器珠海", id: "2013-CN", status: "green" },
  { name: "海尔智家青岛", id: "2014-CN", status: "amber" },
  { name: "蚂蚁科技集团", id: "2015-CN", status: "green" },
  { name: "百度在线网络", id: "2016-CN", status: "red" },
  { name: "拼多多上海", id: "2017-CN", status: "green" },
  { name: "大疆创新科技", id: "2018-CN", status: "green" },
];

/* ================================================================
   Sub-components (co-located, page-specific)
   ================================================================ */

function ComplianceStat({
  dotColor,
  label,
  count,
  total,
  percent,
}: {
  dotColor: string;
  label: string;
  count: number;
  total: number;
  percent: string;
}) {
  return (
    <div
      className="flex items-center"
      style={{
        padding: "var(--space-4) var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div
        style={{
          width: 12,
          height: 12,
          borderRadius: "50%",
          background: dotColor,
          marginRight: "var(--space-4)",
          flexShrink: 0,
        }}
      />
      <div>
        <p style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-secondary)" }}>
          {label}
        </p>
        <p className="font-display font-bold" style={{ fontSize: 22, color: "var(--color-text-primary)" }}>
          {count}{" "}
          <span style={{ fontSize: 13, fontWeight: 400, color: "var(--color-text-tertiary)", opacity: 0.7 }}>
            ({percent})
          </span>
        </p>
      </div>
    </div>
  );
}

function FilterTab({ label, active }: { label: string; active?: boolean }) {
  return (
    <button
      className="font-medium"
      style={{
        fontSize: 13,
        padding: "5px 16px",
        borderRadius: "var(--radius-sm)",
        background: active ? "var(--color-surface-container-lowest)" : "transparent",
        color: active ? "var(--color-primary)" : "var(--color-text-secondary)",
        fontWeight: active ? 700 : 400,
        boxShadow: active ? "var(--shadow-sm)" : undefined,
      }}
    >
      {label}
    </button>
  );
}

function ComplianceCard({
  name,
  id,
  status,
  selected,
}: ComplianceItemData) {
  const dotColor =
    status === "green"
      ? "var(--color-success)"
      : status === "amber"
        ? "var(--color-warning)"
        : "var(--color-danger)";

  return (
    <div
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-md)",
        background: selected
          ? "color-mix(in srgb, var(--color-primary) 5%, transparent)"
          : "var(--color-surface-container-lowest)",
        boxShadow: selected ? undefined : "var(--shadow-sm)",
        cursor: "pointer",
        outline: selected ? "2px solid color-mix(in srgb, var(--color-primary) 40%, transparent)" : undefined,
      }}
    >
      <div
        className="flex justify-between items-start"
        style={{ marginBottom: "var(--space-3)" }}
      >
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: dotColor,
          }}
        />
        {selected && (
          <EyeIcon />
        )}
      </div>
      <h4
        className={selected ? "font-extrabold" : "font-bold"}
        style={{ fontSize: 13, color: "var(--color-text-primary)" }}
      >
        {name}
      </h4>
      <p style={{ fontSize: 10, color: "var(--color-text-tertiary)", marginTop: 2, opacity: 0.7 }}>
        {selected ? "查看风险详情" : `ID: ${id}`}
      </p>
    </div>
  );
}

function RiskItem({
  severity,
  severityLabel,
  title,
  description,
  citations,
  aiSuggestion,
}: {
  severity: "high" | "medium" | "low";
  severityLabel: string;
  title: string;
  description: string;
  citations: string[];
  aiSuggestion?: string;
}) {
  const borderColor =
    severity === "high"
      ? "var(--color-danger)"
      : severity === "medium"
        ? "var(--color-warning)"
        : "var(--color-text-secondary)";

  const bgColor =
    severity === "high"
      ? "color-mix(in srgb, var(--color-danger) 5%, transparent)"
      : severity === "medium"
        ? "color-mix(in srgb, var(--color-warning) 5%, transparent)"
        : "var(--color-surface-container-low)";

  const badgeBg = borderColor;

  return (
    <div
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-sm)",
        background: bgColor,
        borderLeft: `4px solid ${borderColor}`,
      }}
    >
      <div className="flex justify-between items-start">
        <h4 className="font-bold" style={{ fontSize: 13, color: "var(--color-text-primary)" }}>
          {title}
        </h4>
        <span
          style={{
            fontSize: 10,
            fontWeight: 800,
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            background: badgeBg,
            color: "var(--color-on-primary)",
          }}
        >
          {severityLabel}
        </span>
      </div>

      <p
        style={{
          fontSize: 12,
          color: "var(--color-text-secondary)",
          marginTop: "var(--space-2)",
          lineHeight: 1.75,
        }}
      >
        {description}
      </p>

      {/* Law citations */}
      <div className="flex flex-wrap gap-2" style={{ marginTop: "var(--space-3)" }}>
        {citations.map((c) => (
          <span
            key={c}
            style={{
              fontSize: 10,
              padding: "3px 8px",
              borderRadius: "var(--radius-sm)",
              background: "color-mix(in srgb, var(--color-primary) 8%, transparent)",
              color: "var(--color-primary)",
              fontWeight: 500,
            }}
          >
            {c}
          </span>
        ))}
      </div>

      {/* AI suggestion (only for high severity) */}
      {aiSuggestion && (
        <div
          style={{
            marginTop: "var(--space-3)",
            padding: "var(--space-3)",
            borderRadius: "var(--radius-sm)",
            background: "color-mix(in srgb, var(--color-surface-container-lowest) 80%, transparent)",
          }}
        >
          <div
            className="flex items-center gap-1"
            style={{ marginBottom: "var(--space-1)" }}
          >
            <SparklesIcon />
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--color-secondary)",
                textTransform: "uppercase" as const,
              }}
            >
              AI 修复建议
            </span>
          </div>
          <p style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.75 }}>
            {aiSuggestion}
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Inline SVG icons ── */

function ReportIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M6 2h8l6 6v14H6z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M10 13h4M10 17h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3 7l9 5 9-5" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" stroke="var(--color-primary)" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="3" stroke="var(--color-primary)" strokeWidth="1.5" />
    </svg>
  );
}

function SparklesIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="var(--color-secondary)">
      <path d="M12 2l1.5 5.5L19 9l-5.5 1.5L12 16l-1.5-5.5L5 9l5.5-1.5z" />
    </svg>
  );
}
