"use client";

import { useState } from "react";
import { useToast } from "./Toast";

const AI_RESPONSES: Record<string, string> = {
  "default": "已收到您的指令，正在处理中。预计 2-3 秒后返回结果。",
  "税": "已调取相关税务数据，正在进行合规性核验...",
  "发票": "已启动发票批量查验流程，正在与税务局系统对接...",
  "客户": "正在加载客户档案信息...",
  "申报": "正在核验申报数据完整性，请稍候...",
  "报告": "报告生成任务已提交，预计 3 分钟内完成。",
};

function getAiResponse(input: string): string {
  for (const [keyword, response] of Object.entries(AI_RESPONSES)) {
    if (keyword !== "default" && input.includes(keyword)) return response;
  }
  return AI_RESPONSES["default"];
}

export function ChatInput() {
  const [value, setValue] = useState("");
  const [messages, setMessages] = useState<{ type: "user" | "agent"; text: string; time: string }[]>([]);
  const toast = useToast();

  const handleSend = () => {
    if (!value.trim()) return;
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
    const userMsg = { type: "user" as const, text: value, time: timeStr };
    const aiMsg = { type: "agent" as const, text: getAiResponse(value), time: timeStr };
    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setValue("");
    toast("指令已发送");
  };

  return (
    <div>
      {/* New messages */}
      {messages.length > 0 && (
        <div className="flex flex-col gap-4" style={{ padding: "0 var(--space-8) var(--space-4)" }}>
          {messages.map((msg, i) =>
            msg.type === "user" ? (
              <div key={i} className="flex justify-end">
                <div style={{
                  maxWidth: "70%",
                  padding: "10px 16px",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-primary)",
                  color: "var(--color-on-primary)",
                  fontSize: 13,
                  lineHeight: 1.75,
                }}>
                  {msg.text}
                  <span style={{ display: "block", fontSize: 10, opacity: 0.6, marginTop: 4 }}>{msg.time}</span>
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-start">
                <div style={{
                  maxWidth: "70%",
                  padding: "10px 16px",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-surface-container-low)",
                  color: "var(--color-text-primary)",
                  fontSize: 13,
                  lineHeight: 1.75,
                  borderLeft: "2px solid var(--color-secondary)",
                }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: "var(--color-secondary-dim)", display: "block", marginBottom: 4 }}>
                    AI 回复
                  </span>
                  {msg.text}
                  <span style={{ display: "block", fontSize: 10, color: "var(--color-text-tertiary)", marginTop: 4 }}>{msg.time}</span>
                </div>
              </div>
            )
          )}
        </div>
      )}

      {/* Input bar */}
      <div style={{
        padding: "var(--space-4) var(--space-6)",
        background: "color-mix(in srgb, var(--color-surface-container-low) 50%, transparent)",
      }}>
        <div className="flex items-center" style={{ position: "relative" }}>
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
            placeholder="输入指令或补充客户信息..."
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
            <button
              onClick={() => toast("附件上传即将上线", "info")}
              style={{ padding: 4, color: "var(--color-text-tertiary)" }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
            <button
              onClick={handleSend}
              className="flex items-center justify-center"
              style={{
                width: 34,
                height: 34,
                borderRadius: "var(--radius-sm)",
                background: value.trim() ? "var(--color-primary)" : "var(--color-surface-container)",
                transition: "background 0.15s ease",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke={value.trim() ? "var(--color-on-primary)" : "var(--color-text-tertiary)"} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
