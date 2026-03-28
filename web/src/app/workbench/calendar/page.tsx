"use client";

/* Calendar View — 日历视图
   Design ref: design/stitch-export/stitch/automated_task_schedule_timeline/screen.png
   Architecture ref: NEXT_GEN_WORKBENCH_DESIGN.md Section 8.1 View 5
   Design system: Heritage Monolith */

import Link from "next/link";
import {
  TASK_INSTANCES,
  AGENT_MAP,
  TIME_WINDOWS,
  STATUS_STYLES,
  type TimeWindow,
} from "../../lib/workbench-data";

const MONTH_LABEL = "2026 年 3 月";
const TODAY = 12; // mock: 12th of month (W2 征期)
const DAYS_IN_MONTH = 31;
const FIRST_DAY_OFFSET = 6; // March 2026 starts on Sunday (offset 6 in Mon-start grid)

const WINDOW_RANGES: { window: TimeWindow; start: number; end: number }[] = [
  { window: "W1", start: 1, end: 5 },
  { window: "W2", start: 6, end: 15 },
  { window: "W3", start: 16, end: 24 },
  { window: "W4", start: 25, end: 31 },
];

export default function CalendarPage() {
  const days: (number | null)[] = [];
  for (let i = 0; i < FIRST_DAY_OFFSET; i++) days.push(null);
  for (let d = 1; d <= DAYS_IN_MONTH; d++) days.push(d);
  while (days.length % 7 !== 0) days.push(null);

  const todayTasks = TASK_INSTANCES.filter((t) => {
    const range = WINDOW_RANGES.find((r) => r.window === t.window);
    return range && TODAY >= range.start && TODAY <= range.end && t.status !== "pending";
  });

  return (
    <div style={{ background: "var(--color-surface)", minHeight: "100vh" }}>
      {/* ── Header ── */}
      <div style={{ padding: "var(--space-6) var(--space-8)", borderBottom: "1px solid var(--color-surface-container)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px" }}>
              WORKBENCH / CALENDAR
            </div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-text-primary)", marginTop: 4 }}>
              日历视图 — {MONTH_LABEL}
            </h1>
          </div>
          <Link href="/workbench" style={{ padding: "8px 16px", background: "var(--color-surface-container)", color: "var(--color-text-primary)", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
            返回看板
          </Link>
        </div>
      </div>

      {/* ── Time Window Bars ── */}
      <div style={{ padding: "var(--space-6) var(--space-8) 0" }}>
        <div style={{ display: "flex", gap: 0, height: 36 }}>
          {WINDOW_RANGES.map(({ window: w, start, end }) => {
            const meta = TIME_WINDOWS[w];
            const tasks = TASK_INSTANCES.filter((t) => t.window === w);
            const completed = tasks.filter((t) => t.status === "completed").length;
            const widthPct = ((end - start + 1) / DAYS_IN_MONTH) * 100;

            return (
              <div
                key={w}
                style={{
                  width: `${widthPct}%`,
                  background: meta.color,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0 12px",
                  fontSize: "12px",
                  fontWeight: 700,
                }}
              >
                <span>{w} {meta.label} {tasks.length}任务</span>
                <span style={{ opacity: 0.7 }}>{completed}/{tasks.length}</span>
              </div>
            );
          })}
        </div>

        {/* Deadline marker */}
        <div style={{ position: "relative", height: 20 }}>
          <div
            style={{
              position: "absolute",
              left: `${(14.5 / DAYS_IN_MONTH) * 100}%`,
              top: 0,
              fontSize: "10px",
              fontWeight: 700,
              color: "#C4281C",
              whiteSpace: "nowrap",
            }}
          >
            15号 法定截止日
          </div>
        </div>
      </div>

      {/* ── Calendar Grid ── */}
      <div style={{ padding: "0 var(--space-8) var(--space-6)" }}>
        {/* Weekday headers */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "1px", background: "var(--color-surface-container)", marginBottom: "1px" }}>
          {["一", "二", "三", "四", "五", "六", "日"].map((d) => (
            <div key={d} style={{ padding: "8px", textAlign: "center", fontSize: "11px", fontWeight: 700, color: "var(--color-text-secondary)", background: "var(--color-surface-container-low)", textTransform: "uppercase", letterSpacing: "1px" }}>
              {d}
            </div>
          ))}
        </div>

        {/* Day cells */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "1px", background: "var(--color-surface-container)" }}>
          {days.map((day, i) => {
            if (day === null) {
              return <div key={i} style={{ padding: "12px", minHeight: 80, background: "var(--color-surface-container-low)" }} />;
            }

            const isToday = day === TODAY;
            const windowMatch = WINDOW_RANGES.find((r) => day >= r.start && day <= r.end);
            const windowMeta = windowMatch ? TIME_WINDOWS[windowMatch.window] : null;
            const isDeadline = day === 15;

            return (
              <div
                key={i}
                style={{
                  padding: "8px",
                  minHeight: 80,
                  background: isToday ? "var(--color-primary-fixed)" : "var(--color-surface-container-lowest)",
                  borderLeft: isToday ? "3px solid var(--color-primary)" : "3px solid transparent",
                  position: "relative",
                }}
              >
                {/* Day number */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{
                    fontSize: "14px",
                    fontWeight: isToday ? 900 : 600,
                    color: isToday ? "var(--color-primary)" : isDeadline ? "#C4281C" : "var(--color-text-primary)",
                  }}>
                    {day}
                  </span>
                  {windowMeta && (
                    <span style={{ fontSize: "9px", fontWeight: 700, padding: "1px 4px", background: windowMeta.bgColor, color: windowMeta.color }}>
                      {windowMatch!.window}
                    </span>
                  )}
                </div>

                {/* Deadline marker */}
                {isDeadline && (
                  <div style={{ fontSize: "9px", fontWeight: 700, color: "#C4281C", marginBottom: 2 }}>
                    法定截止
                  </div>
                )}

                {/* Today marker */}
                {isToday && (
                  <div style={{ fontSize: "9px", fontWeight: 700, color: "var(--color-primary)", marginBottom: 2 }}>
                    TODAY
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Today's Tasks ── */}
      <div style={{ padding: "0 var(--space-8) var(--space-8)" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", letterSpacing: "2px", marginBottom: 12 }}>
          TODAY — {TODAY}号任务清单
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1px", background: "var(--color-surface-container)" }}>
          {todayTasks.slice(0, 8).map((task) => {
            const agent = AGENT_MAP[task.agentId];
            const ss = STATUS_STYLES[task.status];
            return (
              <div key={task.id} style={{ padding: "12px 16px", background: "var(--color-surface-container-lowest)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>T{task.id} {task.name}</span>
                  <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 6px", background: ss.bg, color: ss.text }}>{ss.label}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--color-text-tertiary)" }}>
                  <span>{agent?.name} · {agent?.role}</span>
                  <span>{task.enterpriseCount}企业 · {task.progress}%</span>
                </div>
                {task.status === "processing" && (
                  <div style={{ height: 3, background: "var(--color-surface-container)", marginTop: 6 }}>
                    <div style={{ height: "100%", width: `${task.progress}%`, background: "var(--color-primary)" }} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
