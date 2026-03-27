/* Agent Workstation -- "智能工作站"
   Layout reference: design/stitch-export/stitch/ai_agent_workstation/screen.png
   Hardcoded agent: 林税安 (LQ-TX-001)
   All data is static mock for initial build. */

export function generateStaticParams() {
  return [
    { id: "lin-shui-an" },
    { id: "zhao-he-gui" },
    { id: "chen-shui-ce" },
    { id: "wang-ji-zhang" },
    { id: "zhang-shen-he" },
    { id: "li-ke-fu" },
    { id: "zhou-xiao-mi" },
  ];
}

const agent = {
  id: "LQ-TX-001",
  name: "林税安",
  role: "高级税务会计",
  dept: "税务部",
  deptColor: "var(--color-dept-tax)",
  quote: "准确是我的底线，法规是我的武器",
};

const skills = [
  { level: "L0", name: "核心能力", rating: "S" as const, calls: "8.5k" },
  { level: "L1", name: "税法知识", rating: "S" as const, calls: "4.2k" },
  { level: "L1", name: "申报执行", rating: "A" as const, calls: "2.8k" },
  { level: "L1", name: "合规审计", rating: "S" as const, calls: "1.5k" },
  { level: "L2", name: "跨境税务", rating: "B" as const, calls: "620" },
  { level: "L2", name: "税收优惠", rating: "A" as const, calls: "1.1k" },
];

const chatMessages = [
  {
    type: "user" as const,
    text: "帮我查一下杭州明达科技的增值税申报情况。",
    time: "10:42 AM",
  },
  {
    type: "agent" as const,
    text: '已为您调取 <b>杭州明达科技有限公司</b> 2023年度Q3至Q4的增值税申报记录。\n\n根据系统比对，该客户当前状态为 <span style="color:var(--color-success);font-weight:700">已按期申报</span>。上季度应纳税额为 <span style="color:var(--color-secondary-dim);font-weight:700;font-family:monospace">¥124,500.00</span>，已享受高新技术企业增值税加计抵减。',
    time: "10:42 AM",
    latency: "1.2s",
    citations: [
      { title: "2023_Q4_VAT_Return.pdf", meta: "官方税务凭证 -- 2.4MB", icon: "doc" },
      { title: "税负波动分析报告", meta: "AI 生成分析 -- 实时", icon: "chart" },
    ],
  },
];

const taskHistory = [
  {
    task: "月度增值税申报",
    client: "杭州明达科技",
    confidence: 98,
    time: "10:42:15",
    status: "done" as const,
  },
  {
    task: "所得税预缴校对",
    client: "上海锐意商贸",
    confidence: 85,
    time: "09:15:30",
    status: "review" as const,
  },
  {
    task: "进项发票批量查验",
    client: "深圳领航物流",
    confidence: 100,
    time: "昨天 17:40",
    status: "done" as const,
  },
  {
    task: "跨省税收协定审核",
    client: "云峰智源股份",
    confidence: 72,
    time: "昨天 14:20",
    status: "escalated" as const,
  },
];

export default function AgentWorkstationPage() {
  return (
    <div
      className="grid gap-8"
      style={{
        gridTemplateColumns: "320px 1fr",
        /* fluid width — fills available space */
      }}
    >
      {/* ── Left panel: Agent profile ── */}
      <div className="flex flex-col gap-6">
        {/* Badge card */}
        <section
          className="flex flex-col items-center text-center"
          style={{
            padding: "var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {/* Avatar with status ring */}
          <div className="relative" style={{ marginBottom: "var(--space-4)" }}>
            <div
              className="flex items-center justify-center"
              style={{
                width: 120,
                height: 120,
                borderRadius: "50%",
                background: `linear-gradient(135deg, var(--color-primary), var(--color-secondary))`,
                padding: 4,
              }}
            >
              <div
                className="flex items-center justify-center font-display font-bold"
                style={{
                  width: "100%",
                  height: "100%",
                  borderRadius: "50%",
                  background: "var(--color-surface-container-lowest)",
                  color: "var(--color-primary)",
                  fontSize: 36,
                }}
              >
                {agent.name.charAt(0)}
              </div>
            </div>
            {/* Online dot */}
            <div
              className="absolute"
              style={{
                bottom: 4,
                right: 4,
                width: 20,
                height: 20,
                borderRadius: "50%",
                background: "var(--color-success)",
                border: "3px solid var(--color-surface-container-lowest)",
              }}
            />
          </div>

          <h2
            className="font-display font-extrabold"
            style={{ fontSize: 28, color: "var(--color-text-primary)", marginBottom: 4 }}
          >
            {agent.name}
          </h2>
          <p className="font-medium" style={{ fontSize: 14, color: "var(--color-secondary-dim)", marginBottom: "var(--space-3)" }}>
            {agent.role}
          </p>

          <span
            className="font-mono"
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "4px 12px",
              borderRadius: "var(--radius-sm)",
              background: "color-mix(in srgb, var(--color-primary) 6%, transparent)",
              color: "var(--color-primary)",
              fontSize: 11,
              fontWeight: 700,
              marginBottom: "var(--space-4)",
            }}
          >
            ID: {agent.id}
          </span>

          <div
            className="font-medium"
            style={{
              width: "100%",
              padding: "8px 0",
              background: agent.deptColor,
              color: "var(--color-on-primary)",
              fontSize: 12,
              textTransform: "uppercase",
              marginBottom: "var(--space-4)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {agent.dept}
          </div>

          <blockquote
            style={{
              fontStyle: "italic",
              fontSize: 13,
              color: "var(--color-text-secondary)",
              lineHeight: 1.75,
              borderLeft: "2px solid color-mix(in srgb, var(--color-secondary) 30%, transparent)",
              paddingLeft: "var(--space-4)",
              textAlign: "left",
              margin: 0,
            }}
          >
            &ldquo;{agent.quote}&rdquo;
          </blockquote>
        </section>

        {/* Skill tree */}
        <section
          style={{
            padding: "var(--space-6)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-low)",
          }}
        >
          <h3
            className="font-display font-bold flex items-center gap-2"
            style={{
              fontSize: 12,
              textTransform: "uppercase",
              color: "var(--color-text-secondary)",
              marginBottom: "var(--space-6)",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2v6M12 22v-6M2 12h6M22 12h-6M6 6l4 4M18 18l-4-4M6 18l4-4M18 6l-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            能力图谱 / Skill Tree
          </h3>

          {/* Root node */}
          <div className="flex justify-center" style={{ marginBottom: "var(--space-4)" }}>
            <span
              className="font-medium"
              style={{
                display: "inline-block",
                padding: "6px 20px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-primary)",
                color: "var(--color-on-primary)",
                fontSize: 13,
              }}
            >
              核心能力
            </span>
          </div>

          {/* Skill nodes */}
          <div className="flex flex-col gap-3">
            {skills.slice(1).map((skill) => (
              <SkillNode key={skill.name} skill={skill} />
            ))}
          </div>
        </section>
      </div>

      {/* ── Right panel: Chat + History ── */}
      <div className="flex flex-col gap-6">
        {/* Chat interface */}
        <section
          className="flex flex-col"
          style={{
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
            overflow: "hidden",
            minHeight: 480,
          }}
        >
          {/* Chat header */}
          <div
            className="flex items-center justify-between"
            style={{
              padding: "var(--space-4) var(--space-6)",
              background: "var(--color-surface-container-low)",
            }}
          >
            <div className="flex items-center gap-3">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinejoin="round" />
              </svg>
              <h3
                className="font-display font-bold"
                style={{ fontSize: 15, color: "var(--color-text-primary)" }}
              >
                交互工作流
              </h3>
            </div>
            <div className="flex gap-2">
              <button style={{ padding: 6, borderRadius: "var(--radius-sm)", color: "var(--color-text-tertiary)" }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M3 12a9 9 0 1018 0 9 9 0 00-18 0" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M12 7v5l3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </button>
              <button style={{ padding: 6, borderRadius: "var(--radius-sm)", color: "var(--color-text-tertiary)" }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="6" r="1.5" fill="currentColor" />
                  <circle cx="12" cy="12" r="1.5" fill="currentColor" />
                  <circle cx="12" cy="18" r="1.5" fill="currentColor" />
                </svg>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 flex flex-col gap-6" style={{ padding: "var(--space-6) var(--space-8)" }}>
            {chatMessages.map((msg, i) =>
              msg.type === "user" ? (
                <UserBubble key={i} text={msg.text} time={msg.time} />
              ) : (
                <AgentBubble
                  key={i}
                  html={msg.text}
                  time={msg.time}
                  latency={msg.latency}
                  citations={msg.citations}
                />
              ),
            )}
          </div>

          {/* Input */}
          <div
            style={{
              padding: "var(--space-4) var(--space-6)",
              background: "color-mix(in srgb, var(--color-surface-container-low) 50%, transparent)",
            }}
          >
            <div className="flex items-center" style={{ position: "relative" }}>
              <input
                type="text"
                placeholder="输入指令或补充客户信息..."
                readOnly
                style={{
                  width: "100%",
                  padding: "12px 80px 12px 16px",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-surface-container-lowest)",
                  color: "var(--color-text-primary)",
                  fontSize: 13,
                  outline: "none",
                  border: "none",
                }}
              />
              <div className="flex items-center gap-2" style={{ position: "absolute", right: 12 }}>
                <button style={{ padding: 4, color: "var(--color-text-tertiary)" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </button>
                <button
                  className="flex items-center justify-center"
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-primary)",
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="var(--color-on-primary)" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Task history table */}
        <section
          style={{
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-lowest)",
            boxShadow: "var(--shadow-sm)",
            overflow: "hidden",
          }}
        >
          <div
            className="flex items-center gap-2"
            style={{ padding: "var(--space-4) var(--space-6)", background: "var(--color-surface-container-low)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M3 12a9 9 0 1018 0 9 9 0 00-18 0" stroke="var(--color-primary)" strokeWidth="1.8" />
              <path d="M12 7v5l3 3" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            <h3
              className="font-display font-bold"
              style={{ fontSize: 15, color: "var(--color-text-primary)" }}
            >
              最近处理任务
            </h3>
          </div>

          {/* Table header */}
          <div
            className="grid items-center"
            style={{
              gridTemplateColumns: "minmax(160px, 1.5fr) 1fr minmax(120px, 1fr) 100px",
              padding: "10px 20px",
              background: "var(--color-surface-container-low)",
              fontSize: 10,
              fontWeight: 800,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
            }}
          >
            <span>任务</span>
            <span>客户</span>
            <span>置信度</span>
            <span style={{ textAlign: "right" }}>时间</span>
          </div>

          {/* Rows */}
          {taskHistory.map((row, i) => (
            <div
              key={row.task}
              className="grid items-center"
              style={{
                gridTemplateColumns: "minmax(160px, 1.5fr) 1fr minmax(120px, 1fr) 100px",
                padding: "12px 20px",
                background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)",
                fontSize: 13,
              }}
            >
              <div className="flex items-center gap-3">
                <span
                  style={{
                    display: "inline-block",
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background:
                      row.status === "done"
                        ? "var(--color-success)"
                        : row.status === "review"
                          ? "var(--color-warning)"
                          : "var(--color-danger)",
                  }}
                />
                <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>
                  {row.task}
                </span>
              </div>
              <span style={{ color: "var(--color-text-secondary)" }}>{row.client}</span>
              <div className="flex items-center gap-3">
                <div
                  className="flex-1"
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
                      width: `${row.confidence}%`,
                      borderRadius: 2,
                      background:
                        row.confidence >= 95
                          ? "var(--color-primary)"
                          : row.confidence >= 80
                            ? "var(--color-secondary)"
                            : "var(--color-warning)",
                    }}
                  />
                </div>
                <span
                  className="font-mono"
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color:
                      row.confidence >= 95
                        ? "var(--color-primary)"
                        : row.confidence >= 80
                          ? "var(--color-secondary-dim)"
                          : "var(--color-warning)",
                  }}
                >
                  {row.confidence}%
                </span>
              </div>
              <span
                className="font-mono"
                style={{ fontSize: 11, color: "var(--color-text-tertiary)", textAlign: "right" }}
              >
                {row.time}
              </span>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

/* ================================================================
   Sub-components (co-located, workstation-specific)
   ================================================================ */

function SkillNode({
  skill,
}: {
  skill: { level: string; name: string; rating: "S" | "A" | "B" | "C"; calls: string };
}) {
  const ratingColor = {
    S: "var(--color-secondary)",
    A: "var(--color-primary)",
    B: "var(--color-dept-bookkeeping)",
    C: "var(--color-text-tertiary)",
  };

  const ratingBg = {
    S: "color-mix(in srgb, var(--color-secondary) 12%, transparent)",
    A: "color-mix(in srgb, var(--color-primary) 10%, transparent)",
    B: "color-mix(in srgb, var(--color-dept-bookkeeping) 10%, transparent)",
    C: "var(--color-surface-container)",
  };

  return (
    <div
      className="flex items-center gap-3"
      style={{
        padding: "var(--space-3)",
        borderRadius: "var(--radius-sm)",
        background: "var(--color-surface-container-lowest)",
      }}
    >
      <div
        className="flex items-center justify-center shrink-0 font-black"
        style={{
          width: 32,
          height: 32,
          borderRadius: "var(--radius-sm)",
          background: ratingBg[skill.rating],
          color: ratingColor[skill.rating],
          fontSize: 12,
        }}
      >
        {skill.rating}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium" style={{ fontSize: 13, color: "var(--color-text-primary)", margin: 0 }}>
          {skill.name}
        </p>
        <p style={{ fontSize: 10, color: "var(--color-text-tertiary)", margin: 0 }}>
          {skill.calls} 次调用
        </p>
      </div>
      <span
        className="font-mono"
        style={{ fontSize: 10, color: "var(--color-text-tertiary)", opacity: 0.6 }}
      >
        {skill.level}
      </span>
    </div>
  );
}

function UserBubble({ text, time }: { text: string; time: string }) {
  return (
    <div className="flex justify-end">
      <div
        style={{
          maxWidth: "70%",
          padding: "var(--space-4) var(--space-6)",
          borderRadius: "var(--radius-md)",
          borderTopRightRadius: 0,
          background: "var(--color-surface-variant)",
        }}
      >
        <p className="font-medium" style={{ fontSize: 14, lineHeight: 1.75, margin: 0, color: "var(--color-text-primary)" }}>
          {text}
        </p>
        <span style={{ display: "block", fontSize: 10, color: "var(--color-text-tertiary)", marginTop: 8, textAlign: "right" }}>
          {time}
        </span>
      </div>
    </div>
  );
}

function AgentBubble({
  html,
  time,
  latency,
  citations,
}: {
  html: string;
  time: string;
  latency?: string;
  citations?: { title: string; meta: string; icon: string }[];
}) {
  return (
    <div className="flex gap-3">
      {/* Agent avatar */}
      <div
        className="flex items-center justify-center shrink-0"
        style={{
          width: 36,
          height: 36,
          borderRadius: "var(--radius-sm)",
          background: "var(--color-primary)",
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="11" width="18" height="10" rx="2" stroke="var(--color-on-primary)" strokeWidth="1.8" />
          <circle cx="8.5" cy="15.5" r="1.5" fill="var(--color-on-primary)" />
          <circle cx="15.5" cy="15.5" r="1.5" fill="var(--color-on-primary)" />
          <path d="M9 3h6v8H9z" stroke="var(--color-on-primary)" strokeWidth="1.8" />
        </svg>
      </div>

      <div style={{ maxWidth: "85%" }}>
        <div
          style={{
            padding: "var(--space-4) var(--space-6)",
            borderRadius: "var(--radius-md)",
            borderTopLeftRadius: 0,
            background: "var(--color-surface-container-low)",
          }}
        >
          <p
            style={{ fontSize: 14, lineHeight: 1.75, margin: 0, color: "var(--color-text-primary)" }}
            dangerouslySetInnerHTML={{ __html: html.replace(/\n/g, "<br/>") }}
          />

          {/* Citations */}
          {citations && citations.length > 0 && (
            <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr", marginTop: "var(--space-4)" }}>
              {citations.map((c) => (
                <div
                  key={c.title}
                  className="flex items-start gap-3"
                  style={{
                    padding: "var(--space-3)",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-surface-container-lowest)",
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ marginTop: 2 }}>
                    {c.icon === "doc" ? (
                      <>
                        <path d="M6 2h8l6 6v14H6z" stroke="var(--color-secondary)" strokeWidth="1.8" strokeLinejoin="round" />
                        <path d="M14 2v6h6" stroke="var(--color-secondary)" strokeWidth="1.8" strokeLinejoin="round" />
                      </>
                    ) : (
                      <>
                        <path d="M3 3v18h18" stroke="var(--color-secondary)" strokeWidth="1.8" strokeLinecap="round" />
                        <path d="M7 14l4-4 4 4 5-5" stroke="var(--color-secondary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                      </>
                    )}
                  </svg>
                  <div className="min-w-0">
                    <p className="font-medium truncate" style={{ fontSize: 11, color: "var(--color-text-primary)", margin: 0 }}>
                      {c.title}
                    </p>
                    <p style={{ fontSize: 10, color: "var(--color-text-tertiary)", margin: 0 }}>
                      {c.meta}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <span style={{ display: "block", fontSize: 10, color: "var(--color-text-tertiary)", marginTop: 4, marginLeft: 4 }}>
          {time}
          {latency && ` -- 响应耗时 ${latency}`}
        </span>
      </div>
    </div>
  );
}
