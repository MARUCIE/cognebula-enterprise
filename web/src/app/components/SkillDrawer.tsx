"use client";

import { useState } from "react";
import { useToast } from "./Toast";

interface SkillData {
  char: string;
  name: string;
  desc: string;
  rating: "S" | "A" | "B" | "C";
  category: string;
  agents: string[];
  agentColors: string[];
  installed: boolean;
}

const MOCK_LOGS = [
  { task: "中铁建设 Q3 增值税核验", time: "2 小时前", status: "done" as const },
  { task: "阿里巴巴进项发票批量查验", time: "昨天 16:30", status: "done" as const },
  { task: "腾讯科技跨境合规审查", time: "昨天 09:15", status: "review" as const },
];

export function SkillCardWrapper({
  skill,
  children,
}: {
  skill: SkillData;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const toast = useToast();

  return (
    <>
      <div onClick={() => setOpen(true)} style={{ cursor: "pointer" }}>
        {children}
      </div>

      {/* Backdrop */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.2)",
            zIndex: 200,
          }}
        />
      )}

      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: open ? 0 : -400,
          width: 380,
          height: "100vh",
          background: "var(--color-surface-container-lowest)",
          boxShadow: open ? "-8px 0 32px rgba(0,0,0,0.12)" : "none",
          zIndex: 201,
          transition: "right 0.25s ease",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            background: "var(--color-surface-container-low)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                background: "color-mix(in srgb, var(--color-primary) 8%, transparent)",
                color: "var(--color-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 16,
                fontWeight: 700,
              }}
            >
              {skill.char}
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>
                {skill.name}
              </h3>
              <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>
                {skill.category} · {skill.rating} 级
              </span>
            </div>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); setOpen(false); }}
            style={{
              width: 28,
              height: 28,
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface-container)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              color: "var(--color-text-tertiary)",
            }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
          {/* Description */}
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.75, marginBottom: 20 }}>
            {skill.desc}
          </p>

          {/* Assigned agents */}
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 8, textTransform: "uppercase" }}>
              已分配专员
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              {skill.agents.map((agent, i) => (
                <div
                  key={agent}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 10px",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-surface-container-low)",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "var(--color-text-primary)",
                  }}
                >
                  <span
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      background: skill.agentColors[i],
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 8,
                      fontWeight: 700,
                    }}
                  >
                    {agent.charAt(0)}
                  </span>
                  {agent}
                </div>
              ))}
            </div>
          </div>

          {/* Recent executions */}
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 8, textTransform: "uppercase" }}>
              最近执行记录
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {MOCK_LOGS.map((log, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-surface)",
                    fontSize: 12,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: log.status === "done" ? "var(--color-success)" : "var(--color-warning)",
                      }}
                    />
                    <span style={{ color: "var(--color-text-primary)", fontWeight: 500 }}>{log.task}</span>
                  </div>
                  <span style={{ fontSize: 10, color: "var(--color-text-tertiary)", whiteSpace: "nowrap", marginLeft: 8 }}>
                    {log.time}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
              marginBottom: 20,
            }}
          >
            <div style={{ padding: "12px 14px", borderRadius: "var(--radius-sm)", background: "var(--color-surface-container-low)" }}>
              <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 4 }}>总调用次数</p>
              <p style={{ fontSize: 20, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>
                {skill.installed ? "2,847" : "—"}
              </p>
            </div>
            <div style={{ padding: "12px 14px", borderRadius: "var(--radius-sm)", background: "var(--color-surface-container-low)" }}>
              <p style={{ fontSize: 10, fontWeight: 700, color: "var(--color-text-tertiary)", marginBottom: 4 }}>准确率</p>
              <p style={{ fontSize: 20, fontWeight: 700, color: "var(--color-success)", margin: 0 }}>
                {skill.installed ? "99.2%" : "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Footer action */}
        <div style={{ padding: "16px 24px", background: "var(--color-surface-container-low)" }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              toast(
                skill.installed
                  ? `「${skill.name}」已安装并启用`
                  : `「${skill.name}」安装成功，已分配给 ${skill.agents.join("、")}`,
                skill.installed ? "info" : "success"
              );
              setOpen(false);
            }}
            style={{
              width: "100%",
              padding: "10px 0",
              borderRadius: "var(--radius-sm)",
              fontSize: 13,
              fontWeight: 700,
              background: skill.installed ? "var(--color-surface-container)" : "var(--color-primary)",
              color: skill.installed ? "var(--color-text-secondary)" : "var(--color-on-primary)",
            }}
          >
            {skill.installed ? "已安装" : "开通此技能"}
          </button>
        </div>
      </div>
    </>
  );
}
