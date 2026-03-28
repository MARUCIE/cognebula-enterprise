/* Skill Store -- "技能商店"
   Layout reference: design/stitch-export/stitch/skill_store_winner/screen.png
   Hero banner + category filters + skill card grid + installed sidebar */

import { ToastButton } from "../components/ToastButton";
import { SkillCardWrapper } from "../components/SkillDrawer";

const SKILLS = [
  {
    char: "增",
    name: "增值税申报",
    desc: "自动检查增值税申报表的完整性和准确性，覆盖进项、销项全流程校验",
    rating: "S" as const,
    category: "税务",
    agents: ["林税安", "赵合规"],
    agentColors: ["var(--color-dept-tax)", "var(--color-dept-compliance)"],
    installed: true,
  },
  {
    char: "企",
    name: "企业所得税优化",
    desc: "智能分析年度所得税调整项，自动识别可优化的税前扣除空间",
    rating: "A" as const,
    category: "税务",
    agents: ["林税安"],
    agentColors: ["var(--color-dept-tax)"],
    installed: false,
  },
  {
    char: "个",
    name: "个税专项扣除",
    desc: "批量核算员工专项附加扣除，自动校验申报数据合规性",
    rating: "A" as const,
    category: "税务",
    agents: ["林税安", "王记账"],
    agentColors: ["var(--color-dept-tax)", "var(--color-dept-bookkeeping)"],
    installed: false,
  },
  {
    char: "跨",
    name: "跨境税务合规",
    desc: "处理海外主体税务申报合规，覆盖转让定价与常设机构判定",
    rating: "B" as const,
    category: "合规",
    agents: ["赵合规"],
    agentColors: ["var(--color-dept-compliance)"],
    installed: false,
  },
  {
    char: "财",
    name: "财务报表生成",
    desc: "一键生成资产负债表、利润表、现金流量表，符合最新会计准则",
    rating: "S" as const,
    category: "记账",
    agents: ["王记账", "赵合规"],
    agentColors: ["var(--color-dept-bookkeeping)", "var(--color-dept-compliance)"],
    installed: true,
  },
  {
    char: "审",
    name: "审计异常检测",
    desc: "基于多维规则引擎与 AI 模型联合检测财务数据异常模式",
    rating: "A" as const,
    category: "审计",
    agents: ["张审核", "赵合规"],
    agentColors: ["var(--color-dept-client)", "var(--color-dept-compliance)"],
    installed: true,
  },
];

const CATEGORIES = [
  { label: "全部", count: 247 },
  { label: "税务", count: 86 },
  { label: "记账", count: 45 },
  { label: "合规", count: 52 },
  { label: "审计", count: 31 },
  { label: "客户服务", count: 38 },
];

const INSTALLED_GROUPS = [
  {
    name: "林税安",
    initials: "LS",
    color: "var(--color-dept-tax)",
    count: 12,
    skills: ["报税", "审计", "所得税汇算", "财报分析"],
  },
  {
    name: "赵合规",
    initials: "ZH",
    color: "var(--color-dept-compliance)",
    count: 8,
    skills: ["法务", "内控", "风险预警"],
  },
  {
    name: "王记账",
    initials: "WJ",
    color: "var(--color-dept-bookkeeping)",
    count: 6,
    skills: ["凭证录入", "银行对账", "月结"],
  },
];

export default function SkillStorePage() {
  return (
    <>
    <div style={{ display: "flex", gap: "var(--space-8)" }}>
      {/* Main content area */}
      <div className="flex-1 min-w-0">
        {/* Hero banner */}
        <section
          style={{
            padding: "var(--space-8) var(--space-8)",
            borderRadius: "var(--radius-md)",
            background: "linear-gradient(135deg, #E6EEF5 0%, var(--color-surface) 60%, #FAFAF8 100%)",
            marginBottom: "var(--space-6)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <h2
            className="font-display font-extrabold"
            style={{
              fontSize: "2rem",
              lineHeight: 1.2,
              color: "var(--color-primary)",
              marginBottom: "var(--space-2)",
              maxWidth: 520,
            }}
          >
            灵阙财税技能商店
          </h2>
          <p
            style={{
              fontSize: 14,
              color: "var(--color-text-secondary)",
              marginBottom: "var(--space-3)",
            }}
          >
            为您的 AI 员工招募新技能
          </p>
          <p
            style={{
              fontSize: 12,
              color: "var(--color-text-tertiary)",
            }}
          >
            powered by OpenClaw -- 37,000+ 技能生态
          </p>
        </section>

        {/* Category filter tabs */}
        <div
          className="flex gap-6"
          style={{
            marginBottom: "var(--space-6)",
            paddingBottom: "var(--space-3)",
          }}
        >
          {CATEGORIES.map((cat, i) => (
            <ToastButton
              key={cat.label}
              message={`正在筛选「${cat.label}」类别技能`}
              type="info"
              className="font-medium"
              style={{
                fontSize: 13,
                color: i === 1 ? "var(--color-primary)" : "var(--color-text-tertiary)",
                paddingBottom: 8,
                borderBottom: i === 1 ? "2px solid var(--color-primary)" : "2px solid transparent",
                whiteSpace: "nowrap",
              }}
            >
              {cat.label}{" "}
              <span style={{ opacity: 0.5, fontSize: 11 }}>({cat.count})</span>
            </ToastButton>
          ))}
        </div>

        {/* Skill card grid */}
        <div
          className="grid gap-5"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}
        >
          {SKILLS.map((skill) => (
            <SkillCardWrapper key={skill.name} skill={skill}>
              <SkillCard skill={skill} />
            </SkillCardWrapper>
          ))}
        </div>
      </div>

      {/* Right sidebar: installed skills */}
      <aside
        style={{
          width: 260,
          flexShrink: 0,
          paddingTop: "var(--space-2)",
        }}
      >
        <div
          className="flex items-center justify-between"
          style={{ marginBottom: "var(--space-6)" }}
        >
          <h3
            className="font-display font-bold"
            style={{ fontSize: 15, color: "var(--color-primary)" }}
          >
            已安装技能{" "}
            <span style={{ color: "var(--color-text-tertiary)", fontWeight: 400, fontSize: 13 }}>
              (47)
            </span>
          </h3>
        </div>

        <div className="flex flex-col gap-8">
          {INSTALLED_GROUPS.map((group) => (
            <InstalledGroup key={group.name} group={group} />
          ))}
        </div>

        {/* AI suggestion card */}
        <div
          style={{
            marginTop: "var(--space-8)",
            padding: "var(--space-4)",
            borderRadius: "var(--radius-md)",
            background: "linear-gradient(135deg, #FDF6EB 0%, #F9EDD8 100%)",
          }}
        >
          <div
            className="flex items-center gap-2"
            style={{ marginBottom: "var(--space-2)" }}
          >
            <span
              className="ai-glow"
              style={{
                display: "inline-block",
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--color-secondary)",
              }}
            />
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--color-secondary-dim)",
              }}
            >
              AI 建议
            </span>
          </div>
          <p
            style={{
              fontSize: 12,
              color: "var(--color-text-secondary)",
              lineHeight: 1.75,
              fontStyle: "italic",
            }}
          >
            &ldquo;检测到您的出口业务量近期增加，建议为林税安安装&lsquo;海关退税自动核算&rsquo;技能。&rdquo;
          </p>
          <ToastButton
            message="正在为您定位推荐技能..."
            className="font-bold"
            style={{
              marginTop: "var(--space-3)",
              fontSize: 11,
              color: "var(--color-primary)",
            }}
          >
            立即查看
          </ToastButton>
        </div>
      </aside>
    </div>

    <footer
      className="text-center"
      style={{
        padding: "var(--space-12) 0 var(--space-8)",
        color: "var(--color-text-tertiary)",
        fontSize: 12,
      }}
    >
      <p>安全加密数据环境 -- 灵阙 AI 引擎 V2.4</p>
      <p style={{ marginTop: 4, opacity: 0.7 }}>
        &copy; 2024 灵阙财税科技. All rights reserved.
      </p>
    </footer>
    </>
  );
}

/* ================================================================
   Sub-components (co-located, skill-store-specific)
   ================================================================ */

type Rating = "S" | "A" | "B" | "C";

function ratingStyle(rating: Rating) {
  switch (rating) {
    case "S":
      return {
        background: "color-mix(in srgb, var(--color-secondary) 12%, transparent)",
        color: "var(--color-secondary-dim)",
      };
    case "A":
      return {
        background: "color-mix(in srgb, var(--color-primary) 10%, transparent)",
        color: "var(--color-primary)",
      };
    case "B":
      return {
        background: "color-mix(in srgb, var(--color-success) 12%, transparent)",
        color: "var(--color-success)",
      };
    case "C":
      return {
        background: "var(--color-surface-container)",
        color: "var(--color-text-tertiary)",
      };
  }
}

function SkillCard({
  skill,
}: {
  skill: (typeof SKILLS)[number];
}) {
  const badge = ratingStyle(skill.rating);

  return (
    <div
      className="flex flex-col"
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: "var(--color-surface-container-lowest)",
        boxShadow: "var(--shadow-sm)",
        minHeight: 220,
      }}
    >
      {/* Top row: character icon + rating */}
      <div
        className="flex items-start justify-between"
        style={{ marginBottom: "var(--space-4)" }}
      >
        <div
          className="flex items-center justify-center font-display font-bold"
          style={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            background: "color-mix(in srgb, var(--color-primary) 6%, transparent)",
            color: "var(--color-primary)",
            fontSize: 16,
          }}
        >
          {skill.char}
        </div>
        <span
          style={{
            ...badge,
            fontSize: 10,
            fontWeight: 700,
            padding: "3px 10px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {skill.rating} 级
        </span>
      </div>

      {/* Name + description */}
      <h4
        className="font-display font-bold"
        style={{
          fontSize: 15,
          color: "var(--color-text-primary)",
          marginBottom: "var(--space-2)",
        }}
      >
        {skill.name}
      </h4>
      <p
        style={{
          fontSize: 12,
          color: "var(--color-text-secondary)",
          lineHeight: 1.75,
          marginBottom: "var(--space-4)",
          flex: 1,
        }}
      >
        {skill.desc}
      </p>

      {/* Bottom: agent avatars + install button */}
      <div
        className="flex items-center justify-between"
        style={{
          paddingTop: "var(--space-3)",
          background: "transparent",
        }}
      >
        {/* Agent avatar chips */}
        <div className="flex -space-x-2">
          {skill.agents.map((agent, i) => (
            <div
              key={agent}
              className="flex items-center justify-center shrink-0"
              title={agent}
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: skill.agentColors[i],
                color: "var(--color-on-primary)",
                fontSize: 9,
                fontWeight: 600,
                border: "2px solid var(--color-surface-container-lowest)",
              }}
            >
              {agent.charAt(0)}
            </div>
          ))}
        </div>
        <ToastButton
          message={skill.installed ? "此技能已安装并启用" : `「${skill.name}」安装成功，已分配给相关专员`}
          type={skill.installed ? "info" : "success"}
          className="font-bold"
          style={{
            fontSize: 11,
            padding: "6px 14px",
            borderRadius: "var(--radius-sm)",
            background: skill.installed ? "var(--color-surface-container)" : "var(--color-primary)",
            color: skill.installed ? "var(--color-text-secondary)" : "var(--color-on-primary)",
          }}
        >
          {skill.installed ? "已安装" : "安装技能"}
        </ToastButton>
      </div>
    </div>
  );
}

function InstalledGroup({
  group,
}: {
  group: (typeof INSTALLED_GROUPS)[number];
}) {
  return (
    <div>
      <div
        className="flex items-center gap-3"
        style={{ marginBottom: "var(--space-3)" }}
      >
        <div
          className="flex items-center justify-center shrink-0 font-medium"
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: group.color,
            color: "var(--color-on-primary)",
            fontSize: 11,
          }}
        >
          {group.initials}
        </div>
        <div>
          <span
            className="font-medium"
            style={{
              fontSize: 13,
              color: "var(--color-text-primary)",
              display: "block",
            }}
          >
            {group.name}
          </span>
          <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>
            {group.count} 项技能已启用
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {group.skills.map((s) => (
          <span
            key={s}
            style={{
              fontSize: 11,
              padding: "3px 10px",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface-container-lowest)",
              color: "var(--color-text-secondary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
