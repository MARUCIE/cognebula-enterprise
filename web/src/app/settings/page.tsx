/* System Settings -- "系统设置"
   Layout reference: design/stitch-export/stitch/system_settings/screen.png
   Firm profile + AI behavior + team RBAC + subscription */

const TEAM_MEMBERS = [
  {
    initials: "LZ",
    name: "林昭",
    email: "lin.zhao@lingque.ai",
    role: "超级管理员",
    roleAccent: true,
    lastActive: "2 分钟前",
  },
  {
    initials: "WM",
    name: "王美龄",
    email: "meiling.w@lingque.ai",
    role: "审计主管",
    roleAccent: false,
    lastActive: "1 小时前",
  },
  {
    initials: "KJ",
    name: "孔杰",
    email: "jie.kong@lingque.ai",
    role: "初级审计师",
    roleAccent: false,
    lastActive: "昨天 18:42",
  },
  {
    initials: "ZQ",
    name: "张琦",
    email: "qi.zhang@lingque.ai",
    role: "税务专员",
    roleAccent: false,
    lastActive: "3 天前",
  },
];

export default function SettingsPage() {
  return (
    <div style={{ paddingBottom: "var(--space-8)" }}>
      {/* ── Section 1: Firm Profile ── */}
      <SettingsSection
        title="事务所概况"
        description="管理您的机构基本信息，这些信息将出现在所有生成的财务报告与审计声明中。"
      >
        <div
          style={{
            padding: "var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {/* Logo + brand row */}
          <div
            className="flex items-center gap-6"
            style={{ marginBottom: "var(--space-6)" }}
          >
            <div
              className="flex items-center justify-center shrink-0 font-display font-bold"
              style={{
                width: 80,
                height: 80,
                borderRadius: "var(--radius-md)",
                background: "var(--color-surface-container-low)",
                color: "var(--color-primary)",
                fontSize: 28,
              }}
            >
              灵
            </div>
            <div>
              <h3
                className="font-display font-bold"
                style={{ fontSize: 14, color: "var(--color-primary)" }}
              >
                品牌标识
              </h3>
              <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: 4 }}>
                建议上传 500x500px PNG 或 SVG 文件
              </p>
            </div>
          </div>

          {/* Form fields in 2-column grid */}
          <div
            className="grid gap-6"
            style={{ gridTemplateColumns: "1fr 1fr" }}
          >
            <FormField label="机构全称" value="灵阙财税科技有限公司" />
            <FormField label="法定代表人" value="张明远" />
            <FormField label="统一社会信用代码" value="91310115MA1K4R8X2U" />
            <FormField label="注册地址" value="上海市浦东新区金融大道 88 号 22 层" />
          </div>
        </div>
      </SettingsSection>

      {/* ── Section 2: AI Behavior Config ── */}
      <SettingsSection
        title="AI 行为配置"
        description="自定义 AI 助手的审计严谨度与自动化程度。这些设置将直接影响初稿生成的逻辑。"
        aiGlow
      >
        <div
          style={{
            padding: "var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "var(--glass-bg)",
            backdropFilter: "blur(var(--glass-blur))",
            boxShadow: "var(--shadow-sm)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Top gradient accent */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: 2,
              background: "linear-gradient(90deg, var(--color-secondary), var(--color-primary))",
            }}
          />

          <div className="flex flex-col gap-8" style={{ paddingTop: "var(--space-2)" }}>
            {/* Risk Sensitivity slider */}
            <SliderControl
              label="风险敏感度 (Risk Sensitivity)"
              value={85}
              valueLabel="85% - 极其严格"
              description="高敏感度将捕捉所有微小的财报差异，并自动标记为待核查项。"
              accentColor="var(--color-primary)"
            />

            {/* Automation Level slider */}
            <SliderControl
              label="全自动化水平 (Automation Level)"
              value={60}
              valueLabel="60% - 协作模式"
              description="中等自动化下，AI 将完成 80% 的凭证比对，但最终合并报表需人工点击确认。"
              accentColor="var(--color-secondary)"
            />

            {/* Toggle: AI auto compliance */}
            <div
              className="flex items-center justify-between"
              style={{
                padding: "var(--space-4)",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-surface-container-low)",
              }}
            >
              <div className="flex items-center gap-3">
                <AiSparkIcon />
                <span className="font-medium" style={{ fontSize: 13 }}>
                  开启 AI 自动合规性纠错
                </span>
              </div>
              <ToggleSwitch on />
            </div>
          </div>
        </div>
      </SettingsSection>

      {/* ── Section 3: Team & Permissions ── */}
      <SettingsSection
        title="团队与权限"
        description="管理机构成员及其在平台内的操作权限。使用角色预设来快速分配职责。"
        action={
          <button
            className="flex items-center gap-2 font-bold"
            style={{
              marginTop: "var(--space-4)",
              fontSize: 13,
              color: "var(--color-primary)",
            }}
          >
            <PersonAddIcon /> 邀请新成员
          </button>
        }
      >
        <div
          style={{
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {/* Table header -- No-Line Rule: background color shift */}
          <div
            className="grid items-center"
            style={{
              gridTemplateColumns: "1.5fr 1fr 1fr 80px",
              padding: "12px 20px",
              background: "var(--color-surface-container-low)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-text-secondary)",
            }}
          >
            <span>成员</span>
            <span>当前角色</span>
            <span>最后活跃</span>
            <span style={{ textAlign: "right" }}>操作</span>
          </div>

          {/* Table rows */}
          {TEAM_MEMBERS.map((member, i) => (
            <div
              key={member.email}
              className="grid items-center"
              style={{
                gridTemplateColumns: "1.5fr 1fr 1fr 80px",
                padding: "14px 20px",
                background: i % 2 === 0
                  ? "var(--color-surface-container-lowest)"
                  : "var(--color-surface)",
                fontSize: 13,
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="flex items-center justify-center shrink-0 font-bold"
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: "var(--color-surface-container)",
                    color: member.roleAccent ? "var(--color-primary)" : "var(--color-text-secondary)",
                    fontSize: 11,
                  }}
                >
                  {member.initials}
                </div>
                <div>
                  <span
                    className="font-semibold"
                    style={{ fontSize: 13, color: "var(--color-text-primary)", display: "block" }}
                  >
                    {member.name}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>
                    {member.email}
                  </span>
                </div>
              </div>
              <span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: "var(--radius-sm)",
                    background: member.roleAccent
                      ? "var(--color-primary-fixed)"
                      : "var(--color-surface-container)",
                    color: member.roleAccent
                      ? "var(--color-primary-deep)"
                      : "var(--color-text-secondary)",
                  }}
                >
                  {member.role}
                </span>
              </span>
              <span style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
                {member.lastActive}
              </span>
              <span style={{ textAlign: "right" }}>
                <MoreIcon />
              </span>
            </div>
          ))}
        </div>
      </SettingsSection>

      {/* ── Section 4: Subscription ── */}
      <SettingsSection
        title="服务订阅"
        description="管理您的 AI 算力额度与订阅方案。订阅将在 2024 年 12 月 31 日到期。"
      >
        <div
          className="flex items-center justify-between"
          style={{
            padding: "var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
            boxShadow: "var(--shadow-ambient)",
          }}
        >
          {/* Left: plan info */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <CrownIcon />
              <span
                className="font-display font-bold"
                style={{ fontSize: 16 }}
              >
                企业尊享版 (Pro Plus)
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span
                className="font-display font-extrabold"
                style={{ fontSize: 28, color: "var(--color-secondary)" }}
              >
                &yen;2,999
              </span>
              <span style={{ fontSize: 12, opacity: 0.6 }}>/ 月</span>
            </div>
            <div className="flex gap-4">
              <div
                style={{
                  padding: "var(--space-2) var(--space-3)",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(255, 255, 255, 0.1)",
                }}
              >
                <div style={{ fontSize: 10, opacity: 0.6, marginBottom: 2 }}>剩余算力</div>
                <div className="font-bold tabular-nums" style={{ fontSize: 13 }}>
                  1,240,000 Tokens
                </div>
              </div>
              <div
                style={{
                  padding: "var(--space-2) var(--space-3)",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(255, 255, 255, 0.1)",
                }}
              >
                <div style={{ fontSize: 10, opacity: 0.6, marginBottom: 2 }}>审计席位</div>
                <div className="font-bold tabular-nums" style={{ fontSize: 13 }}>
                  12 / 20 个
                </div>
              </div>
            </div>
          </div>

          {/* Right: action buttons */}
          <div className="flex flex-col gap-3">
            <button
              className="font-bold"
              style={{
                fontSize: 13,
                padding: "10px 28px",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-secondary)",
                color: "var(--color-text-primary)",
              }}
            >
              立即续费
            </button>
            <button
              className="font-medium"
              style={{
                fontSize: 13,
                padding: "10px 28px",
                borderRadius: "var(--radius-sm)",
                background: "transparent",
                color: "var(--color-on-primary)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
              }}
            >
              账单历史
            </button>
          </div>
        </div>
      </SettingsSection>

      {/* ── Footer actions ── */}
      <div
        className="flex justify-end gap-4"
        style={{ paddingTop: "var(--space-8)" }}
      >
        <button
          className="font-bold"
          style={{
            fontSize: 13,
            padding: "10px 24px",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text-secondary)",
            background: "transparent",
          }}
        >
          取消更改
        </button>
        <button
          className="font-bold"
          style={{
            fontSize: 13,
            padding: "10px 28px",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          保存并应用所有设置
        </button>
      </div>

      {/* Footer */}
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
   Sub-components (co-located, settings-specific)
   ================================================================ */

function SettingsSection({
  title,
  description,
  children,
  aiGlow,
  action,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  aiGlow?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <section
      className="grid gap-6"
      style={{
        gridTemplateColumns: "280px 1fr",
        marginBottom: "var(--space-8)",
        alignItems: "start",
      }}
    >
      <div>
        <div className="flex items-center gap-2" style={{ marginBottom: "var(--space-2)" }}>
          <h2
            className="font-display font-bold"
            style={{ fontSize: 20, color: "var(--color-text-primary)" }}
          >
            {title}
          </h2>
          {aiGlow && (
            <span
              className="ai-glow"
              style={{
                display: "inline-block",
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: "var(--color-primary-fixed)",
              }}
            />
          )}
        </div>
        <p
          style={{
            fontSize: 13,
            color: "var(--color-text-secondary)",
            lineHeight: 1.75,
          }}
        >
          {description}
        </p>
        {action}
      </div>
      <div>{children}</div>
    </section>
  );
}

function FormField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label
        style={{
          display: "block",
          fontSize: 11,
          fontWeight: 700,
          color: "var(--color-text-secondary)",
          marginBottom: "var(--space-1)",
        }}
      >
        {label}
      </label>
      <input
        type="text"
        defaultValue={value}
        className="font-body"
        style={{
          width: "100%",
          fontSize: 13,
          padding: "8px 0",
          color: "var(--color-text-primary)",
          background: "transparent",
          border: "none",
          borderBottom: "1.5px solid var(--color-surface-container)",
          outline: "none",
        }}
      />
    </div>
  );
}

function SliderControl({
  label,
  value,
  valueLabel,
  description,
  accentColor,
}: {
  label: string;
  value: number;
  valueLabel: string;
  description: string;
  accentColor: string;
}) {
  return (
    <div>
      <div
        className="flex items-center justify-between"
        style={{ marginBottom: "var(--space-3)" }}
      >
        <label className="font-bold flex items-center gap-2" style={{ fontSize: 13 }}>
          {label}
          {accentColor === "var(--color-primary)" && (
            <VerifiedIcon />
          )}
        </label>
        <span className="font-bold" style={{ fontSize: 13, color: "var(--color-primary)" }}>
          {valueLabel}
        </span>
      </div>
      {/* Slider track */}
      <div
        style={{
          position: "relative",
          height: 6,
          borderRadius: 3,
          background: "var(--color-surface-container)",
          marginBottom: "var(--space-2)",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            height: "100%",
            width: `${value}%`,
            borderRadius: 3,
            background: accentColor,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: `${value}%`,
            transform: "translate(-50%, -50%)",
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: "var(--color-surface-container-lowest)",
            boxShadow: `0 0 0 3px ${accentColor}`,
          }}
        />
      </div>
      <p style={{ fontSize: 12, color: "var(--color-text-tertiary)", lineHeight: 1.75, margin: 0 }}>
        {description}
      </p>
    </div>
  );
}

function ToggleSwitch({ on }: { on: boolean }) {
  return (
    <div
      style={{
        width: 44,
        height: 24,
        borderRadius: 12,
        background: on ? "var(--color-primary)" : "var(--color-surface-container)",
        position: "relative",
        cursor: "pointer",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 3,
          left: on ? 23 : 3,
          width: 18,
          height: 18,
          borderRadius: "50%",
          background: "var(--color-surface-container-lowest)",
          transition: "left 0.2s ease",
        }}
      />
    </div>
  );
}

/* ── Inline SVG icons ── */

function AiSparkIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2z"
        fill="var(--color-primary)"
        stroke="var(--color-primary)"
        strokeWidth="1"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function VerifiedIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M9 12l2 2 4-4M12 2l2.09 2.91L17.5 4l1.09 3.41L22 9.5l-2.91 2.09L20 15l-3.41 1.09L14.5 20l-2.5-2.91L9.5 20 7.41 16.09 4 15l2.91-2.09L4 9.5l3.41-1.09L8.5 5l2.5 2.91L12 2z"
        fill="var(--color-secondary)"
      />
    </svg>
  );
}

function PersonAddIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="10" cy="8" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path d="M2 20c0-3.3 3-6 8-6s8 2.7 8 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M19 8v6M22 11h-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ cursor: "pointer" }}>
      <circle cx="6" cy="12" r="1.5" fill="var(--color-text-tertiary)" />
      <circle cx="12" cy="12" r="1.5" fill="var(--color-text-tertiary)" />
      <circle cx="18" cy="12" r="1.5" fill="var(--color-text-tertiary)" />
    </svg>
  );
}

function CrownIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M3 18h18v2H3v-2zM5 10l3 6h8l3-6-4 3-4-7-4 7-2-3z"
        fill="var(--color-secondary)"
      />
    </svg>
  );
}
