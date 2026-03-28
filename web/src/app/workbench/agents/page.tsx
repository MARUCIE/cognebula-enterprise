"use client";

/* Agent Team — 数字员工团队
   Design ref: design/stitch-export/stitch/ai_ai_team/screen.png
   Architecture ref: NEXT_GEN_WORKBENCH_DESIGN.md Section 2
   Design system: Heritage Monolith */

import { useState } from "react";
import Link from "next/link";
import {
  AGENTS,
  TASK_INSTANCES,
  TIER_STYLES,
  STATUS_STYLES,
  type Agent,
  type AgentTier,
  type TaskInstance,
} from "../../lib/workbench-data";

export default function AgentTeamPage() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  const totalTasks = AGENTS.reduce((s, a) => s + a.totalTasks, 0);
  const totalErrors = AGENTS.reduce((s, a) => s + a.errors, 0);
  const errorRate = ((totalErrors / totalTasks) * 100).toFixed(2);

  return (
    <div style={{ background: "var(--color-surface)", minHeight: "100vh" }}>
      {/* ── KPI Strip ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1px", background: "var(--color-surface-container)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <KPICell label="在岗数字员工" value={`${AGENTS.length} 位`} context="全部活跃" />
        <KPICell label="本月累计任务" value={totalTasks.toLocaleString()} context={`${AGENTS.length} 位协作完成`} />
        <KPICell label="综合错误率" value={`${errorRate}%`} context={`${totalErrors} 次错误 / ${totalTasks.toLocaleString()} 任务`} valueColor={totalErrors === 0 ? "#1B7F4B" : undefined} />
      </div>

      {/* ── Header ── */}
      <div style={{ padding: "var(--space-6) var(--space-8)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px" }}>
              WORKBENCH / AGENT TEAM
            </div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", marginTop: 4 }}>
              数字员工团队
            </h1>
          </div>
          <Link href="/workbench" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
            返回看板
          </Link>
        </div>
      </div>

      {/* ── Agent Grid + Detail ── */}
      <div style={{ display: "flex" }}>
        {/* Grid */}
        <div style={{ flex: 1, padding: "var(--space-6) var(--space-8)" }}>
          {/* Tier sections */}
          <TierSection tier="starter" label="基础团队 (Starter)" agents={AGENTS.filter((a) => a.tier === "starter")} selected={selectedAgent} onSelect={setSelectedAgent} />
          <TierSection tier="professional" label="专业团队 (Professional)" agents={AGENTS.filter((a) => a.tier === "professional")} selected={selectedAgent} onSelect={setSelectedAgent} />
          <TierSection tier="enterprise" label="企业团队 (Enterprise)" agents={AGENTS.filter((a) => a.tier === "enterprise")} selected={selectedAgent} onSelect={setSelectedAgent} />
        </div>

        {/* Detail Panel */}
        {selectedAgent && (
          <AgentDetailPanel agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
        )}
      </div>
    </div>
  );
}

/* ── KPI Cell ── */
function KPICell({ label, value, context, valueColor }: { label: string; value: string; context: string; valueColor?: string }) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--color-surface-container-lowest)" }}>
      <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: 800, color: valueColor || "var(--color-primary)", lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: "12px", color: "var(--color-text-tertiary)", marginTop: 4 }}>{context}</div>
    </div>
  );
}

/* ── Tier Section ── */
function TierSection({ tier, label, agents, selected, onSelect }: {
  tier: AgentTier;
  label: string;
  agents: Agent[];
  selected: Agent | null;
  onSelect: (a: Agent) => void;
}) {
  const style = TIER_STYLES[tier];
  if (agents.length === 0) return null;

  return (
    <div style={{ marginBottom: "var(--space-8)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-4)" }}>
        <span style={{ fontSize: "10px", fontWeight: 700, padding: "3px 10px", background: style.bg, color: style.text, letterSpacing: "1px" }}>
          {style.label}
        </span>
        <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-secondary)" }}>{label}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1px", background: "var(--color-surface-container)" }}>
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} selected={selected?.id === agent.id} onClick={() => onSelect(agent)} />
        ))}
      </div>
    </div>
  );
}

/* ── Agent Card ── */
function AgentCard({ agent, selected, onClick }: { agent: Agent; selected: boolean; onClick: () => void }) {
  const tierStyle = TIER_STYLES[agent.tier];
  const agentTasks = TASK_INSTANCES.filter((t) => t.agentId === agent.id);
  const activeTasks = agentTasks.filter((t) => t.status === "processing").length;

  return (
    <div
      onClick={onClick}
      style={{
        padding: "20px",
        background: selected ? "var(--color-primary-fixed)" : "var(--color-surface-container-lowest)",
        cursor: "pointer",
        borderLeft: selected ? "3px solid var(--color-primary)" : "3px solid transparent",
        transition: "background 0.15s",
      }}
    >
      {/* Name + Role */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--color-text-primary)" }}>{agent.name}</div>
          <div style={{ fontSize: "12px", color: "var(--color-text-tertiary)", marginTop: 2 }}>{agent.role}</div>
        </div>
        {activeTasks > 0 && (
          <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", background: "#E8F0FE", color: "#003A70" }}>
            {activeTasks} 活跃
          </span>
        )}
      </div>

      {/* Trust Score Circle */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
        <TrustCircle score={agent.trustScore} size={56} />
        <div>
          <div style={{ fontSize: "11px", color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1px" }}>累计任务</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--color-text-primary)" }}>{agent.totalTasks.toLocaleString()}</div>
        </div>
      </div>

      {/* Bottom stats */}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--color-text-tertiary)" }}>
        <span>错误 <strong style={{ color: agent.errors === 0 ? "#1B7F4B" : "#C4281C" }}>{agent.errors}</strong></span>
        <span>服务 <strong style={{ color: "var(--color-text-primary)" }}>{agent.tenureMonths} 月</strong></span>
        <span style={{ fontSize: "10px", fontWeight: 700, padding: "1px 6px", background: tierStyle.bg, color: tierStyle.text }}>{tierStyle.label}</span>
      </div>
    </div>
  );
}

/* ── Trust Score Circle (SVG) ── */
function TrustCircle({ score, size = 56 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  const color = score >= 99 ? "#1B7F4B" : score >= 95 ? "#003A70" : "#C5913E";

  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-surface-container)" strokeWidth={4} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={4} strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="butt" />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        style={{ transform: "rotate(90deg)", transformOrigin: "center", fontSize: "11px", fontWeight: 800, fill: "var(--color-text-primary)" }}
      >
        {score}%
      </text>
    </svg>
  );
}

/* ── Agent Detail Panel ── */
function AgentDetailPanel({ agent, onClose }: { agent: Agent; onClose: () => void }) {
  const agentTasks = TASK_INSTANCES.filter((t) => t.agentId === agent.id);
  const tierStyle = TIER_STYLES[agent.tier];

  return (
    <div style={{
      width: 380,
      borderLeft: "1px solid var(--color-surface-container)",
      background: "var(--color-surface-container-lowest)",
      padding: "24px",
      overflowY: "auto",
      height: "calc(100vh - 140px)",
      position: "sticky",
      top: 140,
    }}>
      <button onClick={onClose} style={{ float: "right", background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "var(--color-text-secondary)" }}>x</button>

      {/* Agent Header */}
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <TrustCircle score={agent.trustScore} size={80} />
        <div style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--color-text-primary)", marginTop: 12 }}>{agent.name}</div>
        <div style={{ fontSize: "14px", color: "var(--color-text-secondary)", marginTop: 2 }}>{agent.role}</div>
        <span style={{ display: "inline-block", marginTop: 8, fontSize: "10px", fontWeight: 700, padding: "3px 12px", background: tierStyle.bg, color: tierStyle.text, letterSpacing: "1px" }}>
          {tierStyle.label}
        </span>
      </div>

      {/* Trust Metrics */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px", marginBottom: 8 }}>TRUST RECORD</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: "var(--color-surface-container)" }}>
          <MetricCell label="准确率" value={`${agent.trustScore}%`} valueColor={agent.trustScore >= 99 ? "#1B7F4B" : undefined} />
          <MetricCell label="服务月数" value={`${agent.tenureMonths}`} />
          <MetricCell label="累计任务" value={agent.totalTasks.toLocaleString()} />
          <MetricCell label="错误次数" value={`${agent.errors}`} valueColor={agent.errors === 0 ? "#1B7F4B" : "#C4281C"} />
        </div>
      </div>

      {/* Active Tasks */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px", marginBottom: 8 }}>
          ASSIGNED TASKS ({agentTasks.length})
        </div>
        {agentTasks.map((task) => {
          const ss = STATUS_STYLES[task.status];
          return (
            <div key={task.id} style={{ padding: "10px 12px", background: "var(--color-surface)", marginBottom: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>T{task.id} {task.name}</span>
                <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 6px", background: ss.bg, color: ss.text }}>{ss.label}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--color-text-tertiary)" }}>
                <span>{task.enterpriseCount} 企业</span>
                <span>{task.progress}%</span>
              </div>
              {task.status === "processing" && (
                <div style={{ height: 3, background: "var(--color-surface-container)", marginTop: 4 }}>
                  <div style={{ height: "100%", width: `${task.progress}%`, background: "var(--color-primary)" }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Skills */}
      <div>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px", marginBottom: 8 }}>SKILLS</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {[...new Set(agentTasks.map((t) => t.primarySkill))].map((skill) => (
            <span key={skill} style={{ padding: "3px 8px", background: "var(--color-surface-container-low)", fontSize: "11px", fontFamily: "monospace", color: "var(--color-text-secondary)" }}>
              {skill}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Metric Cell ── */
function MetricCell({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{ padding: "10px 14px", background: "var(--color-surface-container-lowest)" }}>
      <div style={{ fontSize: "10px", fontWeight: 600, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: "1rem", fontWeight: 800, color: valueColor || "var(--color-text-primary)" }}>{value}</div>
    </div>
  );
}
