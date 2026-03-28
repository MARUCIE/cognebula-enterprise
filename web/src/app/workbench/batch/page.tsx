"use client";

/* Batch Control — 批量操作台
   Design ref: NEXT_GEN_WORKBENCH_DESIGN.md Section 3 + Section 8.1 View 2
   The signature UX: "一键处理 999 家企业" */

import { useState } from "react";
import Link from "next/link";
import {
  TASK_INSTANCES,
  AGENT_MAP,
  TIME_WINDOWS,
  STATUS_STYLES,
  type TaskInstance,
} from "../../lib/workbench-data";

const ACTIVE_TASKS = TASK_INSTANCES.filter((t) => t.status === "processing" || t.status === "ready");

export default function BatchControlPage() {
  const [selectedTask, setSelectedTask] = useState<TaskInstance>(
    ACTIVE_TASKS[0] || TASK_INSTANCES[14] // default to first active task (T15 个税申报)
  );

  const agent = AGENT_MAP[selectedTask.agentId];
  const windowMeta = TIME_WINDOWS[selectedTask.window];
  const readyCount = selectedTask.enterpriseCount - selectedTask.completedEnterprises - selectedTask.blockedEnterprises;
  const processingPct = selectedTask.progress;

  return (
    <div style={{ background: "var(--color-surface)", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ padding: "var(--space-6) var(--space-8)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px" }}>WORKBENCH / BATCH CONTROL</div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", marginTop: 4 }}>批量操作台</h1>
          </div>
          <Link href="/workbench" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>返回看板</Link>
        </div>
      </div>

      <div style={{ display: "flex" }}>
        {/* Task Selector (Left) */}
        <div style={{ width: 280, borderRight: "1px solid var(--color-surface-container)", overflowY: "auto", height: "calc(100vh - 100px)" }}>
          <div style={{ padding: "12px 16px", fontSize: "11px", fontWeight: 700, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1.5px" }}>
            活跃任务 ({ACTIVE_TASKS.length})
          </div>
          {ACTIVE_TASKS.map((task) => {
            const ss = STATUS_STYLES[task.status];
            const isSelected = selectedTask.id === task.id;
            return (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                style={{
                  padding: "10px 16px",
                  cursor: "pointer",
                  background: isSelected ? "var(--color-primary-fixed)" : "transparent",
                  borderLeft: isSelected ? "3px solid var(--color-primary)" : "3px solid transparent",
                  borderBottom: "1px solid var(--color-surface-container)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-text-primary)" }}>T{task.id} {task.name}</span>
                  <span style={{ fontSize: "9px", fontWeight: 700, padding: "1px 6px", background: ss.bg, color: ss.text }}>{ss.label}</span>
                </div>
                <div style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>{task.enterpriseCount}家 · {task.progress}%</div>
              </div>
            );
          })}
        </div>

        {/* Main Batch Panel */}
        <div style={{ flex: 1, padding: "var(--space-6) var(--space-8)" }}>
          {/* Task Header */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", background: windowMeta.bgColor, color: windowMeta.color }}>{selectedTask.window} {windowMeta.label}</span>
              <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", background: STATUS_STYLES[selectedTask.status].bg, color: STATUS_STYLES[selectedTask.status].text }}>
                {STATUS_STYLES[selectedTask.status].label}
              </span>
            </div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 4 }}>
              任务 {selectedTask.id}: {selectedTask.name}
            </h2>
            <div style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
              Agent: {agent?.name} ({agent?.role}) · Skill: <code style={{ padding: "1px 6px", background: "var(--color-surface-container-low)", fontSize: "12px" }}>{selectedTask.primarySkill}</code>
            </div>
          </div>

          {/* 4 Status Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1px", background: "var(--color-surface-container)", marginBottom: 24 }}>
            <StatusCard label="就绪" value={readyCount} total={selectedTask.enterpriseCount} color="#1B7F4B" />
            <StatusCard label="处理中" value={selectedTask.status === "processing" ? Math.floor(selectedTask.enterpriseCount * processingPct / 100) - selectedTask.completedEnterprises : 0} total={selectedTask.enterpriseCount} color="#003A70" />
            <StatusCard label="阻塞" value={selectedTask.blockedEnterprises} total={selectedTask.enterpriseCount} color="#C4281C" />
            <StatusCard label="已完成" value={selectedTask.completedEnterprises} total={selectedTask.enterpriseCount} color="#5A5A72" />
          </div>

          {/* Progress Bar */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: "12px", color: "var(--color-text-secondary)" }}>
              <span>进度 {processingPct}%</span>
              <span>{selectedTask.completedEnterprises} / {selectedTask.enterpriseCount} 企业</span>
            </div>
            <div style={{ height: 8, background: "var(--color-surface-container)" }}>
              <div style={{ height: "100%", width: `${processingPct}%`, background: selectedTask.status === "completed" ? "#1B7F4B" : "var(--color-primary)", transition: "width 0.3s" }} />
            </div>
            {selectedTask.status === "processing" && (
              <div style={{ fontSize: "11px", color: "var(--color-text-tertiary)", marginTop: 4 }}>
                速度: 8.2 企业/分钟 · 预计剩余: {Math.ceil((selectedTask.enterpriseCount - selectedTask.completedEnterprises) / 8.2)} 分钟
              </div>
            )}
          </div>

          {/* CTA Button */}
          {(selectedTask.status === "ready" || selectedTask.status === "processing") && (
            <button style={{
              width: "100%",
              padding: "16px",
              background: "var(--gradient-cta)",
              color: "#fff",
              border: "none",
              fontSize: "16px",
              fontWeight: 800,
              cursor: "pointer",
              marginBottom: 24,
              letterSpacing: "0.5px",
            }}>
              {selectedTask.status === "ready"
                ? `一键处理 ${readyCount} 家就绪企业`
                : `继续处理 (${selectedTask.enterpriseCount - selectedTask.completedEnterprises} 家剩余)`}
            </button>
          )}

          {/* HITL Warning */}
          {selectedTask.hitl && (
            <div style={{ padding: "16px 20px", background: "#FDECEB", borderLeft: "3px solid #C4281C", marginBottom: 24 }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#C4281C", letterSpacing: "1px", marginBottom: 4 }}>HUMAN-IN-THE-LOOP REQUIRED</div>
              <div style={{ fontSize: "13px", color: "var(--color-text-primary)" }}>
                此任务需要客户人工授权: <strong>{selectedTask.hitlType}</strong>。Agent 将发送通知并等待客户回复后继续处理。
              </div>
            </div>
          )}

          {/* Blocked Enterprises Table */}
          {selectedTask.blockedEnterprises > 0 && (
            <div>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px", marginBottom: 8 }}>
                阻塞企业 ({selectedTask.blockedEnterprises})
              </div>
              <div style={{ background: "var(--color-surface-container)" }}>
                {/* Table header */}
                <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr", gap: "1px" }}>
                  {["企业名称", "阻塞原因", "上游任务", "操作"].map((h) => (
                    <div key={h} style={{ padding: "8px 12px", background: "var(--color-primary)", color: "#fff", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      {h}
                    </div>
                  ))}
                </div>
                {/* Mock blocked rows */}
                {MOCK_BLOCKED.slice(0, selectedTask.blockedEnterprises > 5 ? 5 : selectedTask.blockedEnterprises).map((row, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr", gap: "1px" }}>
                    <div style={{ padding: "10px 12px", background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)", fontSize: "13px", color: "var(--color-text-primary)" }}>{row.name}</div>
                    <div style={{ padding: "10px 12px", background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)", fontSize: "12px", color: "#C4281C" }}>{row.reason}</div>
                    <div style={{ padding: "10px 12px", background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)", fontSize: "12px", color: "var(--color-text-secondary)" }}>{row.upstream}</div>
                    <div style={{ padding: "10px 12px", background: i % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)" }}>
                      <button style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-primary)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>查看</button>
                    </div>
                  </div>
                ))}
              </div>
              {selectedTask.blockedEnterprises > 5 && (
                <div style={{ padding: "8px 12px", fontSize: "12px", color: "var(--color-text-tertiary)", textAlign: "center" }}>
                  还有 {selectedTask.blockedEnterprises - 5} 家阻塞企业...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Status Card ── */
function StatusCard({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--color-surface-container-lowest)" }}>
      <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: "1.5rem", fontWeight: 800, color, lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: "11px", color: "var(--color-text-tertiary)", marginTop: 2 }}>{total > 0 ? ((value / total) * 100).toFixed(1) : 0}%</div>
    </div>
  );
}

const MOCK_BLOCKED = [
  { name: "深圳前海金融", reason: "任务14 税金结账未完成", upstream: "T14" },
  { name: "广州天河科技", reason: "发票数据缺失", upstream: "T8" },
  { name: "北京朝阳投资", reason: "客户未提供工资表", upstream: "T12" },
  { name: "上海浦东贸易", reason: "跨期凭证未调整", upstream: "T6" },
  { name: "杭州西湖电商", reason: "银行流水导入异常", upstream: "T1" },
  { name: "成都高新生物", reason: "进项发票未认证", upstream: "T11" },
  { name: "武汉东湖光电", reason: "上月结账未完成", upstream: "T7" },
];
