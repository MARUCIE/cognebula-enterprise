"use client";

import { useState } from "react";
import { CN, cnCard, cnBadge } from "../../lib/cognebula-theme";

interface Step {
  phase: string;
  label: string;
  detail: string;
  confidence: number;
  duration: string;
}

interface Chain {
  id: string;
  agent: string;
  task: string;
  time: string;
  confidence: number;
  steps: Step[];
}

const CHAINS: Chain[] = [
  {
    id: "RC-001", agent: "林税安",
    task: "月度增值税申报 -- 杭州明达科技",
    time: "2024-11-24 10:42", confidence: 98,
    steps: [
      { phase: "INPUT", label: "接收任务", detail: "查询杭州明达科技增值税申报状态", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "KG 实体检索", detail: "匹配到 12 条 KnowledgeUnit + LawOrRegulation 记录", confidence: 96, duration: "0.8s" },
      { phase: "REASONING", label: "规则推理", detail: "一般纳税人 13% 税率，高新技术企业加计扣除", confidence: 94, duration: "0.3s" },
      { phase: "VALIDATION", label: "合规校验", detail: "交叉验证 3 部法规，无冲突", confidence: 98, duration: "0.2s" },
      { phase: "OUTPUT", label: "生成回复", detail: "申报状态 + 税额计算 + 扣除说明", confidence: 98, duration: "1.2s" },
    ],
  },
  {
    id: "RC-002", agent: "赵合规",
    task: "转让定价文档审核 -- 华夏贸易",
    time: "2024-11-23 14:20", confidence: 72,
    steps: [
      { phase: "INPUT", label: "接收审核任务", detail: "审核华夏贸易进出口转让定价文档", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "法规检索", detail: "匹配 OECD 转让定价指南 + 42 号公告", confidence: 88, duration: "1.2s" },
      { phase: "REASONING", label: "合规分析", detail: "CUT 方法参数偏离行业均值 15%", confidence: 65, duration: "2.1s" },
      { phase: "ESCALATION", label: "触发人工审核", detail: "置信度低于 80% 阈值，标记待审核", confidence: 72, duration: "0.1s" },
    ],
  },
  {
    id: "RC-003", agent: "周风控",
    task: "现金流异常检测 -- 中科电子",
    time: "2024-11-22 09:15", confidence: 91,
    steps: [
      { phase: "INPUT", label: "定时扫描", detail: "中科电子 Q3 现金流异常检测", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "财务数据提取", detail: "连续 4 个季度经营性现金流/净利润比率", confidence: 95, duration: "0.5s" },
      { phase: "REASONING", label: "模式匹配", detail: "触发 CR-005: 经营性现金流 < 净利润 x 0.5 连续 2 个季度", confidence: 88, duration: "0.4s" },
      { phase: "VALIDATION", label: "交叉验证", detail: "对比行业基准，确认异常", confidence: 91, duration: "0.3s" },
      { phase: "OUTPUT", label: "生成告警", detail: "向审计团队发送风险告警，严重级别: 警告", confidence: 91, duration: "0.2s" },
    ],
  },
];

const PHASE_COLORS: Record<string, string> = {
  INPUT: CN.blue,
  RETRIEVAL: CN.purple,
  REASONING: CN.amber,
  VALIDATION: CN.green,
  OUTPUT: CN.blue,
  ESCALATION: CN.red,
};

function confColor(v: number) {
  if (v >= 90) return CN.green;
  if (v >= 75) return CN.amber;
  return CN.red;
}

export default function ReasoningPage() {
  const [selected, setSelected] = useState<string>(CHAINS[0].id);
  const chain = CHAINS.find((c) => c.id === selected) || CHAINS[0];

  return (
    <div style={{ display: "flex", height: "calc(100vh - 49px)" }}>
      {/* Left: Chain List */}
      <div style={{
        width: 320, flexShrink: 0, overflowY: "auto",
        background: CN.bgCard, borderRight: `1px solid ${CN.border}`,
      }}>
        <div style={{ padding: "12px 16px", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px", borderBottom: `1px solid ${CN.border}` }}>
          推理链
        </div>
        {CHAINS.map((c) => (
          <button key={c.id}
            onClick={() => setSelected(c.id)}
            style={{
              display: "block", width: "100%", padding: "12px 16px", textAlign: "left",
              background: c.id === selected ? CN.blueBg : "transparent",
              border: "none",
              borderLeft: `2px solid ${c.id === selected ? CN.blue : "transparent"}`,
              borderBottom: `1px solid ${CN.border}`,
              cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: CN.text }}>{c.agent}</span>
              <span style={cnBadge(confColor(c.confidence), c.confidence >= 90 ? CN.greenBg : c.confidence >= 75 ? CN.amberBg : CN.redBg)}>
                {c.confidence}%
              </span>
            </div>
            <div style={{ fontSize: 12, color: CN.textSecondary, marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {c.task}
            </div>
            <div style={{ fontSize: 10, color: CN.textMuted }}>{c.time}</div>
          </button>
        ))}
      </div>

      {/* Right: Chain Detail */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px", background: CN.bg }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: CN.text, margin: 0 }}>{chain.task}</h2>
          <span style={cnBadge(confColor(chain.confidence), chain.confidence >= 90 ? CN.greenBg : chain.confidence >= 75 ? CN.amberBg : CN.redBg)}>
            {chain.confidence}%
          </span>
        </div>
        <div style={{ display: "flex", gap: 12, marginBottom: 24, fontSize: 12, color: CN.textSecondary }}>
          <span>Agent: <strong style={{ color: CN.text }}>{chain.agent}</strong></span>
          <span>编号: <span style={{ fontFamily: "monospace", color: CN.textMuted }}>{chain.id}</span></span>
          <span>时间: {chain.time}</span>
        </div>

        {/* Pipeline Steps */}
        <div style={{ position: "relative", paddingLeft: 24 }}>
          {/* Vertical line */}
          <div style={{ position: "absolute", left: 11, top: 0, bottom: 0, width: 2, background: CN.border }} />

          {chain.steps.map((step, i) => {
            const phaseColor = PHASE_COLORS[step.phase] || CN.textMuted;
            return (
              <div key={i} style={{ position: "relative", marginBottom: 20 }}>
                {/* Dot on the line */}
                <div style={{
                  position: "absolute", left: -18, top: 6,
                  width: 14, height: 14, borderRadius: "50%",
                  background: CN.bg, border: `2px solid ${phaseColor}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: phaseColor }} />
                </div>

                <div style={{ ...cnCard, marginLeft: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={cnBadge(phaseColor, `${phaseColor}15`)}>{step.phase}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: CN.text }}>{step.label}</span>
                    </div>
                    <span style={{ fontSize: 11, color: CN.textMuted, fontFamily: "monospace" }}>{step.duration}</span>
                  </div>
                  <div style={{ fontSize: 12, color: CN.textSecondary, marginBottom: 10, lineHeight: 1.6 }}>
                    {step.detail}
                  </div>
                  {/* Confidence bar */}
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ flex: 1, height: 4, background: CN.bgElevated, borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${step.confidence}%`, background: confColor(step.confidence), borderRadius: 2, transition: "width 0.3s" }} />
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 700, color: confColor(step.confidence), fontVariantNumeric: "tabular-nums", minWidth: 36, textAlign: "right" }}>
                      {step.confidence}%
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
