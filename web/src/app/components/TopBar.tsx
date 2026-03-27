"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";

const pageTitles: Record<string, string> = {
  "/": "今日概览",
  "/ai-team": "AI 专家团队",
  "/clients": "客户中心",
  "/tax": "智能报税",
  "/reports": "报告中心",
  "/skills": "技能商店",
  "/compliance": "合规管理看板",
  "/audit": "智能审计工作台",
  "/settings": "系统设置",
  "/ops/customers": "客户健康矩阵",
  "/ops/agents": "AI 专员性能监控",
  "/ops/alerts": "系统告警中心",
};

function getPageTitle(pathname: string): string {
  if (pathname.startsWith("/ai-team/") && pathname !== "/ai-team") {
    return "AI 专家工作站";
  }
  return pageTitles[pathname] ?? "今日概览";
}

const NOTIFICATIONS = [
  { id: 1, type: "action" as const, text: "云峰智源: Q3 增值税申报异常，需人工确认", href: "/clients/yunfeng-zhiyuan", time: "14:30" },
  { id: 2, type: "action" as const, text: "深圳极智: 2 份报告待审批", href: "/reports", time: "11:20" },
  { id: 3, type: "info" as const, text: "林税安完成 42 家 Q3 增值税批量申报", time: "10:00" },
  { id: 4, type: "info" as const, text: "赵合规更新合规规则库（+47 条法规节点）", time: "09:15" },
  { id: 5, type: "info" as const, text: "王记账完成腾讯科技月度凭证录入", time: "08:30" },
];

export function TopBar() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    }
    if (notifOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [notifOpen]);

  const actionCount = NOTIFICATIONS.filter((n) => n.type === "action").length;

  return (
    <header
      className="flex items-center justify-between shrink-0"
      style={{
        height: "var(--topbar-height)",
        padding: "0 var(--space-8)",
        background: "var(--color-surface)",
      }}
    >
      {/* Page title */}
      <h1
        className="font-display font-semibold"
        style={{ fontSize: 18, color: "var(--color-text-primary)" }}
      >
        {title}
      </h1>

      {/* Right side: search + notification + avatar */}
      <div className="flex items-center gap-5">
        {/* Search */}
        <div
          className="flex items-center gap-2"
          style={{
            padding: "8px 14px",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-container-low)",
            minWidth: 220,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="var(--color-text-tertiary)" strokeWidth="1.8" />
            <path d="M16 16l5 5" stroke="var(--color-text-tertiary)" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>
            搜索客户、报告或任务...
          </span>
        </div>

        {/* Notification bell + popover */}
        <div ref={notifRef} style={{ position: "relative" }}>
          <button
            className="relative flex items-center justify-center transition-colors"
            style={{ width: 36, height: 36, borderRadius: "var(--radius-sm)" }}
            onClick={() => setNotifOpen((v) => !v)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9z"
                stroke="var(--color-text-secondary)"
                strokeWidth="1.8"
              />
              <path d="M13.73 21a2 2 0 01-3.46 0" stroke="var(--color-text-secondary)" strokeWidth="1.8" />
            </svg>
            {actionCount > 0 && (
              <span
                className="absolute flex items-center justify-center"
                style={{
                  top: 4,
                  right: 4,
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: "var(--color-danger)",
                  color: "#fff",
                  fontSize: 9,
                  fontWeight: 700,
                }}
              >
                {actionCount}
              </span>
            )}
          </button>

          {/* Notification popover */}
          {notifOpen && (
            <div
              style={{
                position: "absolute",
                top: 44,
                right: 0,
                width: 380,
                borderRadius: "var(--radius-md)",
                background: "var(--color-surface-container-lowest)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
                zIndex: 100,
                overflow: "hidden",
              }}
            >
              {/* Header */}
              <div
                style={{
                  padding: "12px 16px",
                  background: "var(--color-surface-container-low)",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "var(--color-text-primary)",
                }}
              >
                待处理 {actionCount} 件 · 今日动态 {NOTIFICATIONS.length - actionCount} 条
              </div>

              {/* Action items */}
              {NOTIFICATIONS.filter((n) => n.type === "action").map((n) => (
                <div
                  key={n.id}
                  className="flex items-center justify-between"
                  style={{
                    padding: "10px 16px",
                    borderBottom: "1px solid var(--color-surface-container)",
                    background: "color-mix(in srgb, var(--color-danger) 4%, var(--color-surface-container-lowest))",
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)", margin: 0, lineHeight: 1.5 }}>
                      {n.text}
                    </p>
                    <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>{n.time}</span>
                  </div>
                  <button
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: "4px 12px",
                      borderRadius: "var(--radius-sm)",
                      background: "var(--color-primary)",
                      color: "var(--color-on-primary)",
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                      marginLeft: 8,
                    }}
                  >
                    处理
                  </button>
                </div>
              ))}

              {/* Info items */}
              {NOTIFICATIONS.filter((n) => n.type === "info").map((n) => (
                <div
                  key={n.id}
                  style={{
                    padding: "8px 16px",
                    borderBottom: "1px solid var(--color-surface-container)",
                    fontSize: 12,
                    color: "var(--color-text-secondary)",
                    lineHeight: 1.5,
                  }}
                >
                  <span>{n.text}</span>
                  <span style={{ fontSize: 10, color: "var(--color-text-tertiary)", marginLeft: 8 }}>{n.time}</span>
                </div>
              ))}

              {/* Footer */}
              <Link
                href="/ops/alerts"
                style={{
                  display: "block",
                  padding: "10px 16px",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--color-primary)",
                  textAlign: "center",
                  textDecoration: "none",
                  background: "var(--color-surface-container-low)",
                }}
                onClick={() => setNotifOpen(false)}
              >
                查看全部告警 &rarr;
              </Link>
            </div>
          )}
        </div>

        {/* Settings gear */}
        <button
          className="flex items-center justify-center"
          style={{ width: 36, height: 36, borderRadius: "var(--radius-sm)" }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" stroke="var(--color-text-secondary)" strokeWidth="1.8" />
            <path
              d="M12 1v3M12 20v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M1 12h3M20 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
              stroke="var(--color-text-secondary)"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </button>

        {/* User avatar */}
        <div
          className="flex items-center justify-center font-medium text-xs"
          style={{
            width: 34,
            height: 34,
            borderRadius: "50%",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
          }}
        >
          陈
        </div>
      </div>
    </header>
  );
}
