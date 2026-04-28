"use client";

/* Skill Store -- "技能商店"
   Layout reference: design/stitch-export/stitch/skill_store_winner/screen.png
   Hero banner + category filters + skill card grid + installed sidebar */

import { useState } from "react";
import { useToast } from "../components/Toast";
import { ToastButton } from "../components/ToastButton";
import { SkillCardWrapper } from "../components/SkillDrawer";

const SKILLS = [
  // === 税务 (11) ===
  { char: "税", name: "税务顾问", desc: "18 税种判定、税率适用、增值税/企业所得税/个税/附加税纳税申报全流程", rating: "S" as const, category: "税务", agents: ["林税安", "陈申报"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-client)"], installed: true },
  { char: "优", name: "税收优惠", desc: "高新技术企业认定辅导、小型微利企业标准判定、研发加计扣除归集与备查", rating: "S" as const, category: "税务", agents: ["林税安"], agentColors: ["var(--color-dept-tax)"], installed: true },
  { char: "筹", name: "税务筹划", desc: "优惠政策匹配、组织架构税务优化、节税方案测算、合法性边界判断", rating: "A" as const, category: "税务", agents: ["林税安", "赵合规"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-compliance)"], installed: false },
  { char: "差", name: "税会差异", desc: "50+ 常见税会差异识别与分类(永久性/暂时性)、调整方向判定、递延所得税计算", rating: "A" as const, category: "税务", agents: ["林税安", "王记账"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-bookkeeping)"], installed: false },
  { char: "退", name: "出口退税", desc: "免退/免抵退方式选择、退税率查询与差额处理、出口发票与报关单匹配", rating: "A" as const, category: "税务", agents: ["林税安"], agentColors: ["var(--color-dept-tax)"], installed: false },
  { char: "关", name: "关税消费税", desc: "关税计算、进口增值税和消费税核算、HS 编码归类、保税区特殊处理", rating: "B" as const, category: "税务", agents: ["林税安"], agentColors: ["var(--color-dept-tax)"], installed: false },
  { char: "印", name: "小税种专家", desc: "印花税、房产税、城镇土地使用税、契税、土地增值税、车船税、环保税等非主体税种", rating: "B" as const, category: "税务", agents: ["林税安", "陈申报"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-client)"], installed: false },
  { char: "跨", name: "国际税务", desc: "跨境交易税务处理、非居民企业所得税代扣代缴、税收协定优惠适用、境外税收抵免", rating: "B" as const, category: "税务", agents: ["林税安", "赵合规"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-compliance)"], installed: false },
  { char: "转", name: "转让定价", desc: "关联交易定价合规、五种定价方法选择、同期资料准备、预约定价安排", rating: "B" as const, category: "税务", agents: ["林税安", "赵合规"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-compliance)"], installed: false },
  { char: "数", name: "数字资产税务", desc: "数据资产入表(资本化判定)、AI 模型成本归集、碳排放配额会计与税务处理", rating: "C" as const, category: "税务", agents: ["林税安"], agentColors: ["var(--color-dept-tax)"], installed: false },
  { char: "社", name: "社保公积金", desc: "五险一金核算、基数年度调整(每年7月)、工伤生育报销、残保金申报", rating: "A" as const, category: "税务", agents: ["陈申报", "王记账"], agentColors: ["var(--color-dept-client)", "var(--color-dept-bookkeeping)"], installed: true },
  // === 记账 (7) ===
  { char: "账", name: "会计核算", desc: "凭证录入、科目映射、期末结账、报表编制，严格遵循企业会计准则(CAS)", rating: "S" as const, category: "记账", agents: ["王记账"], agentColors: ["var(--color-dept-bookkeeping)"], installed: true },
  { char: "报", name: "财务报表", desc: "资产负债表、利润表、现金流量表编制，关键比率计算与报表间勾稽关系验证", rating: "S" as const, category: "记账", agents: ["王记账", "赵合规"], agentColors: ["var(--color-dept-bookkeeping)", "var(--color-dept-compliance)"], installed: true },
  { char: "成", name: "成本核算", desc: "工业/商贸/服务业成本模型搭建、制造费用分配方案设计、标准成本差异分析", rating: "A" as const, category: "记账", agents: ["王记账"], agentColors: ["var(--color-dept-bookkeeping)"], installed: false },
  { char: "外", name: "外币核算", desc: "外币交易初始确认、期末汇率调整、汇兑损益计算、境外子公司报表折算", rating: "B" as const, category: "记账", agents: ["王记账"], agentColors: ["var(--color-dept-bookkeeping)"], installed: false },
  { char: "合", name: "合并报表", desc: "合并范围判定、内部交易抵消、少数股东权益计算、合并抵消分录编制", rating: "B" as const, category: "记账", agents: ["王记账", "张审核"], agentColors: ["var(--color-dept-bookkeeping)", "var(--color-dept-client)"], installed: false },
  { char: "历", name: "申报日历", desc: "申报截止日自动计算、节假日延期规则、提醒生成，避免逾期申报罚款", rating: "A" as const, category: "记账", agents: ["陈申报"], agentColors: ["var(--color-dept-client)"], installed: true },
  // === 合规 (7) ===
  { char: "规", name: "合规审计员", desc: "风险识别、合规规则匹配、金税四期预警应对、账务质检与整改建议", rating: "S" as const, category: "合规", agents: ["赵合规"], agentColors: ["var(--color-dept-compliance)"], installed: true },
  { char: "清", name: "合规检查单", desc: "按行业+企业规模+纳税人类型自动生成月度/季度/年度结构化合规检查清单", rating: "A" as const, category: "合规", agents: ["赵合规"], agentColors: ["var(--color-dept-compliance)"], installed: true },
  { char: "票", name: "发票管理", desc: "进项认证/勾选抵扣、数电票处理、异常发票排查、留抵退税申报、发票真伪验证", rating: "S" as const, category: "合规", agents: ["陈申报", "赵合规"], agentColors: ["var(--color-dept-client)", "var(--color-dept-compliance)"], installed: true },
  { char: "查", name: "法规查询", desc: "对接知识图谱 54 万+节点，精准检索税法条文、政策解读、案例判例", rating: "A" as const, category: "合规", agents: ["赵合规", "林税安"], agentColors: ["var(--color-dept-compliance)", "var(--color-dept-tax)"], installed: true },
  { char: "评", name: "风险评估", desc: "行业基准对标分析、异常指标自动检测、风险等级量化评估与预警报告", rating: "A" as const, category: "合规", agents: ["赵合规"], agentColors: ["var(--color-dept-compliance)"], installed: false },
  { char: "注", name: "工商注册", desc: "企业注册、工商变更、年报年检、简易注销、经营范围调整、股东变更", rating: "B" as const, category: "合规", agents: ["李助理"], agentColors: ["var(--color-dept-bookkeeping)"], installed: false },
  { char: "律", name: "税务法律顾问", desc: "税务争议解决、行政复议策略、税务稽查应对、涉税刑事风险预判", rating: "B" as const, category: "合规", agents: ["赵合规"], agentColors: ["var(--color-dept-compliance)"], installed: false },
  // === 审计 (2) ===
  { char: "审", name: "内部审计", desc: "内控评价、业务流程审计、舞弊风险识别，基于 COSO 内部控制框架", rating: "A" as const, category: "审计", agents: ["张审核", "赵合规"], agentColors: ["var(--color-dept-client)", "var(--color-dept-compliance)"], installed: false },
  { char: "补", name: "政府补贴申报", desc: "财政补贴项目筛选、申报材料准备、评审应对、资金使用合规管理", rating: "B" as const, category: "审计", agents: ["李助理", "赵合规"], agentColors: ["var(--color-dept-bookkeeping)", "var(--color-dept-compliance)"], installed: false },
  // === 客户服务 (2) ===
  { char: "析", name: "业务分析师", desc: "理解客户经营场景、识别涉税事项、拆解业务流，输出结构化业务事件", rating: "A" as const, category: "客户服务", agents: ["李助理", "林税安"], agentColors: ["var(--color-dept-bookkeeping)", "var(--color-dept-tax)"], installed: false },
  { char: "智", name: "财税团队路由", desc: "意图分类→专家分发→协作编排→结果综合，所有财税问题的统一入口", rating: "S" as const, category: "客户服务", agents: ["林税安", "赵合规", "王记账"], agentColors: ["var(--color-dept-tax)", "var(--color-dept-compliance)", "var(--color-dept-bookkeeping)"], installed: true },
];

const CATEGORIES = [
  { label: "全部", count: 29 },
  { label: "税务", count: 11 },
  { label: "记账", count: 7 },
  { label: "合规", count: 7 },
  { label: "审计", count: 2 },
  { label: "客户服务", count: 2 },
];

const INSTALLED_GROUPS = [
  {
    name: "林税安",
    initials: "LS",
    color: "var(--color-dept-tax)",
    count: 14,
    skills: ["税务顾问", "税收优惠", "法规查询", "税会差异"],
  },
  {
    name: "赵合规",
    initials: "ZH",
    color: "var(--color-dept-compliance)",
    count: 11,
    skills: ["合规审计员", "发票管理", "风险评估", "合规检查单"],
  },
  {
    name: "王记账",
    initials: "WJ",
    color: "var(--color-dept-bookkeeping)",
    count: 8,
    skills: ["会计核算", "财务报表", "成本核算", "外币核算"],
  },
  {
    name: "陈申报",
    initials: "CS",
    color: "var(--color-dept-client)",
    count: 5,
    skills: ["申报日历", "社保公积金", "发票管理", "小税种"],
  },
];

export default function SkillStorePage() {
  const [activeCategory, setActiveCategory] = useState("全部");
  const [installedSkills, setInstalledSkills] = useState<Set<string>>(
    () => new Set(SKILLS.filter((s) => s.installed).map((s) => s.name))
  );
  const toast = useToast();

  const filteredSkills =
    activeCategory === "全部"
      ? SKILLS
      : SKILLS.filter((s) => s.category === activeCategory);

  function handleInstall(skillName: string) {
    if (installedSkills.has(skillName)) {
      toast("此技能已安装", "info");
      return;
    }
    setInstalledSkills((prev) => new Set(prev).add(skillName));
    const skill = SKILLS.find((s) => s.name === skillName);
    toast(
      `「${skillName}」安装成功，已分配给${skill?.agents.join("、") ?? "相关专员"}`,
      "success"
    );
  }

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
          {CATEGORIES.map((cat) => {
            const isActive = cat.label === activeCategory;
            return (
              <button
                key={cat.label}
                onClick={() => setActiveCategory(cat.label)}
                className="font-medium"
                style={{
                  fontSize: 13,
                  color: isActive ? "var(--color-primary)" : "var(--color-text-tertiary)",
                  paddingBottom: 8,
                  whiteSpace: "nowrap" as const,
                  background: "none",
                  border: "none",
                  borderBottom: isActive ? "2px solid var(--color-primary)" : "2px solid transparent",
                  cursor: "pointer",
                }}
              >
                {cat.label}{" "}
                <span style={{ opacity: 0.5, fontSize: 11 }}>({cat.count})</span>
              </button>
            );
          })}
        </div>

        {/* Skill card grid */}
        <div
          className="grid gap-5"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}
        >
          {filteredSkills.map((skill) => {
            const isInstalled = installedSkills.has(skill.name);
            const skillWithState = { ...skill, installed: isInstalled };
            return (
              <SkillCardWrapper
                key={skill.name}
                skill={skillWithState}
                onInstall={() => handleInstall(skill.name)}
              >
                <SkillCard
                  skill={skillWithState}
                  onInstall={() => handleInstall(skill.name)}
                />
              </SkillCardWrapper>
            );
          })}
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
              ({installedSkills.size})
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
  onInstall,
}: {
  skill: (typeof SKILLS)[number];
  onInstall: () => void;
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
        <button
          onClick={(e) => { e.stopPropagation(); onInstall(); }}
          className="font-bold"
          style={{
            fontSize: 11,
            padding: "6px 14px",
            borderRadius: "var(--radius-sm)",
            background: skill.installed ? "var(--color-surface-container)" : "var(--color-primary)",
            color: skill.installed ? "var(--color-text-secondary)" : "var(--color-on-primary)",
            border: "none",
            cursor: "pointer",
          }}
        >
          {skill.installed ? "已安装" : "安装技能"}
        </button>
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
