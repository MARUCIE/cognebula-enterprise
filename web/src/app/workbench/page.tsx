"use client";

/* Monthly Kanban Workbench -- 月度看板
   Design ref: design/stitch-export/stitch/ai_operations_dashboard/screen.png
   Architecture ref: NEXT_GEN_WORKBENCH_DESIGN.md Section 8.1 View 1
   Design system: Heritage Monolith (Zero-Radius, Tonal Layering) */

import { useState } from "react";
import Link from "next/link";
import {
  TASK_INSTANCES,
  AGENT_MAP,
  TIME_WINDOWS,
  STATUS_STYLES,
  getKPIs,
  getTasksByWindow,
  type TimeWindow,
  type TaskInstance,
} from "../lib/workbench-data";

export default function WorkbenchPage() {
  const kpis = getKPIs();
  const [selectedTask, setSelectedTask] = useState<TaskInstance | null>(null);

  return (
    <div style={{ background: "var(--color-surface)", minHeight: "100vh" }}>
      {/* ── KPI Strip ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "1px",
          background: "var(--color-surface-container)",
          borderBottom: "1px solid var(--color-surface-container)",
        }}
      >
        <KPICard label="本月进度" value={`${kpis.tasksCompleted}/${kpis.tasksTotal}`} context={`${kpis.tasksPercent}% 任务完成`} />
        <KPICard label="已处理企业" value={kpis.processedUnits.toLocaleString()} context={`/ ${kpis.totalUnits.toLocaleString()} (${kpis.unitsPercent}%)`} />
        <KPICard
          label="征期倒计时"
          value={`${kpis.deadlineDaysLeft} 天`}
          context="15号法定截止"
          valueColor={kpis.deadlineDaysLeft <= 3 ? "#C4281C" : kpis.deadlineDaysLeft <= 5 ? "#C5913E" : undefined}
        />
        <KPICard label="异常待处理" value={`${kpis.exceptions}`} context="需人工介入" valueColor={kpis.exceptions > 0 ? "#C5913E" : undefined} />
      </div>

      {/* ── Page Header ── */}
      <div style={{ padding: "var(--space-6) var(--space-8)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px", textTransform: "uppercase" }}>
              WORKBENCH / MONTHLY KANBAN
            </div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", marginTop: 4 }}>
              月度工作台
            </h1>
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)" }}>
            <Link href="/workbench/agents" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
              数字员工
            </Link>
            <Link href="/workbench/calendar" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
              日历视图
            </Link>
          </div>
        </div>
      </div>

      {/* ── 4-Column Kanban ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, minHeight: "calc(100vh - 180px)" }}>
        {(["W1", "W2", "W3", "W4"] as TimeWindow[]).map((w) => (
          <WindowColumn key={w} window={w} tasks={getTasksByWindow(w)} onTaskClick={setSelectedTask} selectedTaskId={selectedTask?.id} />
        ))}
      </div>

      {/* ── Task Detail Drawer ── */}
      {selectedTask && (
        <TaskDetailDrawer task={selectedTask} onClose={() => setSelectedTask(null)} />
      )}
    </div>
  );
}

/* ── KPI Card ── */
function KPICard({ label, value, context, valueColor }: { label: string; value: string; context: string; valueColor?: string }) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--color-surface-container-lowest)" }}>
      <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: "1.4rem", fontWeight: 800, color: valueColor || "var(--color-primary)", lineHeight: 1.2 }}>
        {value}
      </div>
      <div style={{ fontSize: "12px", color: "var(--color-text-tertiary)", marginTop: 4 }}>
        {context}
      </div>
    </div>
  );
}

/* ── Window Column (W1-W4) ── */
function WindowColumn({
  window: w,
  tasks,
  onTaskClick,
  selectedTaskId,
}: {
  window: TimeWindow;
  tasks: TaskInstance[];
  onTaskClick: (t: TaskInstance) => void;
  selectedTaskId?: number;
}) {
  const meta = TIME_WINDOWS[w];
  const completed = tasks.filter((t) => t.status === "completed").length;

  return (
    <div style={{ borderRight: w !== "W4" ? "1px solid var(--color-surface-container)" : undefined, display: "flex", flexDirection: "column" }}>
      {/* Column Header */}
      <div
        style={{
          padding: "12px 16px",
          background: meta.color,
          color: "#fff",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1.5px", opacity: 0.7 }}>{w}</div>
          <div style={{ fontSize: "14px", fontWeight: 700 }}>{meta.label}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "13px", opacity: 0.8 }}>{meta.days}</div>
          <div style={{ fontSize: "12px", fontWeight: 600 }}>{completed}/{tasks.length}</div>
        </div>
      </div>

      {/* Deadline warning for W2 */}
      {w === "W2" && (
        <div style={{ padding: "6px 16px", background: "#FDECEB", color: "#C4281C", fontSize: "11px", fontWeight: 700, letterSpacing: "1px" }}>
          15号法定截止日
        </div>
      )}

      {/* Task Cards */}
      <div style={{ flex: 1, padding: "8px", overflowY: "auto" }}>
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onClick={() => onTaskClick(task)}
            selected={selectedTaskId === task.id}
          />
        ))}
      </div>
    </div>
  );
}

/* ── Task Card ── */
function TaskCard({ task, onClick, selected }: { task: TaskInstance; onClick: () => void; selected: boolean }) {
  const agent = AGENT_MAP[task.agentId];
  const statusStyle = STATUS_STYLES[task.status];

  return (
    <div
      onClick={onClick}
      style={{
        padding: "12px",
        marginBottom: "6px",
        background: selected ? "var(--color-primary-fixed)" : "var(--color-surface-container-lowest)",
        cursor: "pointer",
        borderLeft: selected ? "3px solid var(--color-primary)" : "3px solid transparent",
        transition: "background 0.15s",
      }}
    >
      {/* Task name + status */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", lineHeight: 1.4, flex: 1 }}>
          {task.name}
        </div>
        <span
          style={{
            fontSize: "10px",
            fontWeight: 700,
            padding: "2px 8px",
            background: statusStyle.bg,
            color: statusStyle.text,
            whiteSpace: "nowrap",
            marginLeft: 6,
          }}
        >
          {statusStyle.label}
        </span>
      </div>

      {/* Progress bar (only for processing/completed) */}
      {(task.status === "processing" || task.status === "completed") && (
        <div style={{ height: 3, background: "var(--color-surface-container)", marginBottom: 6 }}>
          <div
            style={{
              height: "100%",
              width: `${task.progress}%`,
              background: task.status === "completed" ? "#1B7F4B" : "var(--color-primary)",
              transition: "width 0.3s",
            }}
          />
        </div>
      )}

      {/* Agent + enterprise count */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>
          {agent?.name} · {agent?.role}
        </div>
        <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-secondary)" }}>
          {task.enterpriseCount}家
        </div>
      </div>

      {/* HITL indicator */}
      {task.hitl && (
        <div style={{ marginTop: 4, fontSize: "10px", fontWeight: 700, color: "#C4281C" }}>
          HITL: {task.hitlType}
        </div>
      )}
    </div>
  );
}

/* ── Task Detail Drawer ── */
function TaskDetailDrawer({ task, onClose }: { task: TaskInstance; onClose: () => void }) {
  const agent = AGENT_MAP[task.agentId];
  const statusStyle = STATUS_STYLES[task.status];
  const meta = TIME_WINDOWS[task.window];

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: 420,
        height: "100vh",
        background: "var(--color-surface-container-lowest)",
        borderLeft: "1px solid var(--color-surface-container)",
        zIndex: 100,
        overflowY: "auto",
        padding: "24px",
      }}
    >
      {/* Close */}
      <button onClick={onClose} style={{ float: "right", background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "var(--color-text-secondary)" }}>
        x
      </button>

      {/* Header */}
      <div style={{ fontSize: "11px", fontWeight: 700, color: meta.color, letterSpacing: "2px", marginBottom: 4 }}>
        {task.window} {meta.label} · 任务 {task.id}
      </div>
      <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 16 }}>
        {task.name}
      </h2>

      {/* Status + Agent */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 12px", background: statusStyle.bg, color: statusStyle.text }}>
          {statusStyle.label}
        </span>
        <span style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
          {agent?.name} ({agent?.role})
        </span>
      </div>

      {/* Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: "var(--color-surface-container)", marginBottom: 20 }}>
        <MetricCell label="企业总数" value={task.enterpriseCount.toString()} />
        <MetricCell label="已完成" value={task.completedEnterprises.toString()} />
        <MetricCell label="阻塞" value={task.blockedEnterprises.toString()} valueColor={task.blockedEnterprises > 0 ? "#C4281C" : undefined} />
        <MetricCell label="进度" value={`${task.progress}%`} />
      </div>

      {/* Progress bar */}
      <div style={{ height: 6, background: "var(--color-surface-container)", marginBottom: 20 }}>
        <div style={{ height: "100%", width: `${task.progress}%`, background: task.status === "completed" ? "#1B7F4B" : "var(--color-primary)" }} />
      </div>

      {/* Skill */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>
          Primary Skill
        </div>
        <div style={{ display: "inline-block", padding: "4px 12px", background: "var(--color-surface-container-low)", fontSize: "12px", fontFamily: "var(--font-mono, monospace)", color: "var(--color-text-secondary)" }}>
          {task.primarySkill}
        </div>
      </div>

      {/* HITL */}
      {task.hitl && (
        <div style={{ padding: "12px 16px", background: "#FDECEB", borderLeft: "3px solid #C4281C", marginBottom: 16 }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#C4281C", marginBottom: 4 }}>HUMAN-IN-THE-LOOP</div>
          <div style={{ fontSize: "13px", color: "var(--color-text-primary)" }}>{task.hitlType}</div>
        </div>
      )}

      {/* CTA */}
      {(task.status === "ready" || task.status === "processing") && (
        <button
          style={{
            width: "100%",
            padding: "12px",
            background: "var(--gradient-cta)",
            color: "#fff",
            border: "none",
            fontSize: "14px",
            fontWeight: 700,
            cursor: "pointer",
            marginTop: 8,
          }}
        >
          {task.status === "ready"
            ? `一键处理 ${task.enterpriseCount} 家企业`
            : `继续处理 (${task.enterpriseCount - task.completedEnterprises} 家剩余)`
          }
        </button>
      )}

      {/* Agent trust */}
      {agent && (
        <div style={{ marginTop: 24, padding: "16px", background: "var(--color-surface-container-low)" }}>
          <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>
            Agent Trust Record
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: 4 }}>
            <span style={{ color: "var(--color-text-secondary)" }}>准确率</span>
            <span style={{ fontWeight: 700, color: "var(--color-text-primary)" }}>{agent.trustScore}%</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: 4 }}>
            <span style={{ color: "var(--color-text-secondary)" }}>累计任务</span>
            <span style={{ fontWeight: 700, color: "var(--color-text-primary)" }}>{agent.totalTasks.toLocaleString()}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: 4 }}>
            <span style={{ color: "var(--color-text-secondary)" }}>错误次数</span>
            <span style={{ fontWeight: 700, color: agent.errors === 0 ? "#1B7F4B" : "#C4281C" }}>{agent.errors}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
            <span style={{ color: "var(--color-text-secondary)" }}>服务月数</span>
            <span style={{ fontWeight: 700, color: "var(--color-text-primary)" }}>{agent.tenureMonths}</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Metric Cell (for detail drawer) ── */
function MetricCell({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{ padding: "12px 16px", background: "var(--color-surface-container-lowest)" }}>
      <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: "1.1rem", fontWeight: 800, color: valueColor || "var(--color-primary)" }}>
        {value}
      </div>
    </div>
  );
}
