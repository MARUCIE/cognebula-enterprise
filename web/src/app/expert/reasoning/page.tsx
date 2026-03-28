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
    task: "Monthly VAT Filing -- Hangzhou Mingda Tech",
    time: "2024-11-24 10:42", confidence: 98,
    steps: [
      { phase: "INPUT", label: "Receive task", detail: "Query VAT filing status for Hangzhou Mingda Tech", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "KG entity search", detail: "Matched 12 KnowledgeUnit + LawOrRegulation records", confidence: 96, duration: "0.8s" },
      { phase: "REASONING", label: "Rule inference", detail: "General taxpayer 13% rate, high-tech enterprise additional deduction", confidence: 94, duration: "0.3s" },
      { phase: "VALIDATION", label: "Compliance check", detail: "Cross-verified 3 regulations, no conflict", confidence: 98, duration: "0.2s" },
      { phase: "OUTPUT", label: "Generate response", detail: "Filing status + tax amount + deduction explanation", confidence: 98, duration: "1.2s" },
    ],
  },
  {
    id: "RC-002", agent: "赵合规",
    task: "Transfer Pricing Document Review -- Huaxia Trade",
    time: "2024-11-23 14:20", confidence: 72,
    steps: [
      { phase: "INPUT", label: "Receive review task", detail: "Review import/export transfer pricing docs for Huaxia Trade", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "Regulation search", detail: "Matched OECD TP Guidelines + Circular 42", confidence: 88, duration: "1.2s" },
      { phase: "REASONING", label: "Compliance analysis", detail: "CUT method parameters deviate 15% from industry mean", confidence: 65, duration: "2.1s" },
      { phase: "ESCALATION", label: "HITL triggered", detail: "Confidence below 80% threshold, flagged for review", confidence: 72, duration: "0.1s" },
    ],
  },
  {
    id: "RC-003", agent: "周风控",
    task: "Cash Flow Anomaly Detection -- Zhongke Electronics",
    time: "2024-11-22 09:15", confidence: 91,
    steps: [
      { phase: "INPUT", label: "Scheduled scan", detail: "Q3 cash flow anomaly detection for Zhongke Electronics", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "Financial data pull", detail: "Operating CF/Net Income ratio for 4 consecutive quarters", confidence: 95, duration: "0.5s" },
      { phase: "REASONING", label: "Pattern match", detail: "CR-005 triggered: Operating CF < Net Income x 0.5 for 2 quarters", confidence: 88, duration: "0.4s" },
      { phase: "VALIDATION", label: "Cross-check", detail: "Verified against industry benchmarks, confirmed anomaly", confidence: 91, duration: "0.3s" },
      { phase: "OUTPUT", label: "Alert generated", detail: "Risk alert issued to audit team, severity: WARNING", confidence: 91, duration: "0.2s" },
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
          REASONING CHAINS
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
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: CN.text, margin: 0 }}>{chain.task}</h2>
          <span style={cnBadge(confColor(chain.confidence), chain.confidence >= 90 ? CN.greenBg : chain.confidence >= 75 ? CN.amberBg : CN.redBg)}>
            {chain.confidence}%
          </span>
        </div>
        <div style={{ display: "flex", gap: 12, marginBottom: 24, fontSize: 12, color: CN.textSecondary }}>
          <span>Agent: <strong style={{ color: CN.text }}>{chain.agent}</strong></span>
          <span>ID: <span style={{ fontFamily: "monospace", color: CN.textMuted }}>{chain.id}</span></span>
          <span>Time: {chain.time}</span>
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
                    <div style={{ flex: 1, height: 4, background: CN.bgElevated, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${step.confidence}%`, background: confColor(step.confidence), transition: "width 0.3s" }} />
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
