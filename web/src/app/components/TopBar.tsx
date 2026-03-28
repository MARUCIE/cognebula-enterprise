"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useToast } from "./Toast";
import { CLIENTS } from "../lib/clients";
import { REPORTS } from "../lib/reports";
import { AGENT_SLUG } from "../lib/agents";

const pageTitles: Record<string, string> = {
  "/": "今日概览",
  "/workbench": "月度工作台",
  "/workbench/agents": "数字员工团队",
  "/workbench/batch": "批量操作台",
  "/workbench/calendar": "日历视图",
  "/workbench/exceptions": "异常中心",
  "/workbench/dependencies": "任务依赖图",
  "/clients": "客户中心",
  "/reports": "报告中心",
  "/skills": "技能商店",
  "/settings": "系统设置",
  "/expert/kg": "知识图谱探索",
  "/expert/reasoning": "推理链检查器",
  "/expert/rules": "合规规则调试",
  "/expert/data-quality": "数据质量审计",
};

function getPageTitle(pathname: string): string {
  // Normalize: strip trailing slash for consistent lookup
  const p = pathname.endsWith("/") && pathname.length > 1 ? pathname.slice(0, -1) : pathname;
  if (p.startsWith("/clients/") && p !== "/clients") {
    return "客户详情";
  }
  if (p.startsWith("/reports/") && p !== "/reports") {
    return "报告详情";
  }
  return pageTitles[p] ?? "今日概览";
}

interface Notification {
  id: number;
  type: "action" | "info";
  text: string;
  href?: string;
  time: string;
}

const INITIAL_NOTIFICATIONS: Notification[] = [
  { id: 1, type: "action", text: "腾讯科技: Q3 现金流量表需关注，需人工确认", href: "/clients/tengxun-keji", time: "14:30" },
  { id: 2, type: "action", text: "深圳极智: 2 份报告待审批", href: "/reports", time: "11:20" },
  { id: 3, type: "info", text: "林税安完成 42 家 Q3 增值税批量申报", time: "10:00" },
  { id: 4, type: "info", text: "赵合规更新合规规则库（+47 条法规节点）", time: "09:15" },
  { id: 5, type: "info", text: "王记账完成腾讯科技月度凭证录入", time: "08:30" },
];

interface SearchResult {
  type: "客户" | "报告" | "AI 专员";
  label: string;
  sub: string;
  href: string;
}

function searchAll(query: string): SearchResult[] {
  if (!query.trim()) return [];
  const q = query.trim().toLowerCase();
  const results: SearchResult[] = [];

  for (const c of CLIENTS) {
    if (c.name.toLowerCase().includes(q) || c.industry.toLowerCase().includes(q)) {
      results.push({ type: "客户", label: c.name, sub: c.industry, href: `/clients/${c.id}` });
    }
    if (results.filter((r) => r.type === "客户").length >= 3) break;
  }

  for (const r of REPORTS) {
    if (r.company.toLowerCase().includes(q) || r.reportType.toLowerCase().includes(q) || r.reportTypeEn.toLowerCase().includes(q)) {
      results.push({ type: "报告", label: r.company, sub: r.reportType, href: `/reports/${r.id}` });
    }
    if (results.filter((r) => r.type === "报告").length >= 3) break;
  }

  for (const [name] of Object.entries(AGENT_SLUG)) {
    if (name.toLowerCase().includes(q)) {
      results.push({ type: "AI 专员", label: name, sub: "数字员工", href: "/workbench/agents" });
    }
    if (results.filter((r) => r.type === "AI 专员").length >= 3) break;
  }

  return results;
}

export function TopBar() {
  const pathname = usePathname();
  const router = useRouter();
  const toast = useToast();
  const title = getPageTitle(pathname);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(INITIAL_NOTIFICATIONS);
  const notifRef = useRef<HTMLDivElement>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const searchResults = useMemo(() => searchAll(searchQuery), [searchQuery]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    }
    if (notifOpen || searchOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [notifOpen, searchOpen]);

  const actionCount = notifications.filter((n) => n.type === "action").length;

  function handleDismissNotification(id: number, href?: string) {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    setNotifOpen(false);
    if (href) router.push(href);
    toast("已处理并跳转");
  }

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
        <div ref={searchRef} style={{ position: "relative" }}>
          <div
            className="flex items-center gap-2"
            style={{
              padding: "8px 14px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-low)",
              minWidth: 260,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
              <circle cx="11" cy="11" r="7" stroke="var(--color-text-tertiary)" strokeWidth="1.8" />
              <path d="M16 16l5 5" stroke="var(--color-text-tertiary)" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            <input
              type="text"
              placeholder="搜索客户、报告或专员..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setSearchOpen(true); }}
              onFocus={() => { if (searchQuery) setSearchOpen(true); }}
              onKeyDown={(e) => { if (e.key === "Escape") { setSearchOpen(false); setSearchQuery(""); } }}
              style={{
                border: "none",
                outline: "none",
                background: "transparent",
                color: "var(--color-text-primary)",
                fontSize: 13,
                width: "100%",
              }}
            />
          </div>

          {/* Search results dropdown */}
          {searchOpen && searchResults.length > 0 && (
            <div
              style={{
                position: "absolute",
                top: 44,
                left: 0,
                right: 0,
                minWidth: 340,
                borderRadius: "var(--radius-md)",
                background: "var(--color-surface-container-lowest)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
                zIndex: 100,
                overflow: "hidden",
              }}
            >
              {(["客户", "报告", "AI 专员"] as const).map((type) => {
                const group = searchResults.filter((r) => r.type === type);
                if (group.length === 0) return null;
                return (
                  <div key={type}>
                    <div
                      style={{
                        padding: "6px 14px",
                        fontSize: 10,
                        fontWeight: 700,
                        color: "var(--color-text-tertiary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        background: "var(--color-surface-container-low)",
                      }}
                    >
                      {type}
                    </div>
                    {group.map((r) => (
                      <button
                        key={r.href}
                        onClick={() => {
                          router.push(r.href);
                          setSearchQuery("");
                          setSearchOpen(false);
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          width: "100%",
                          padding: "8px 14px",
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          textAlign: "left",
                          borderBottom: "1px solid var(--color-surface-container)",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-surface-container-low)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)" }}>{r.label}</div>
                          <div style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{r.sub}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                );
              })}
            </div>
          )}

          {searchOpen && searchQuery.trim() && searchResults.length === 0 && (
            <div
              style={{
                position: "absolute",
                top: 44,
                left: 0,
                right: 0,
                minWidth: 340,
                borderRadius: "var(--radius-md)",
                background: "var(--color-surface-container-lowest)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
                zIndex: 100,
                padding: "16px",
                textAlign: "center",
                fontSize: 13,
                color: "var(--color-text-tertiary)",
              }}
            >
              未找到匹配结果
            </div>
          )}
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
                {actionCount > 0
                  ? `待处理 ${actionCount} 件 · 今日动态 ${notifications.length - actionCount} 条`
                  : `今日动态 ${notifications.length} 条`}
              </div>

              {notifications.length === 0 && (
                <div style={{ padding: "24px 16px", textAlign: "center", fontSize: 13, color: "var(--color-text-tertiary)" }}>
                  暂无通知
                </div>
              )}

              {/* Action items */}
              {notifications.filter((n) => n.type === "action").map((n) => (
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
                    onClick={() => handleDismissNotification(n.id, n.href)}
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
              {notifications.filter((n) => n.type === "info").map((n) => (
                <div
                  key={n.id}
                  className="flex items-center justify-between"
                  style={{
                    padding: "8px 16px",
                    borderBottom: "1px solid var(--color-surface-container)",
                    fontSize: 12,
                    color: "var(--color-text-secondary)",
                    lineHeight: 1.5,
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <span>{n.text}</span>
                    <span style={{ fontSize: 10, color: "var(--color-text-tertiary)", marginLeft: 8 }}>{n.time}</span>
                  </div>
                  <button
                    onClick={() => {
                      setNotifications((prev) => prev.filter((x) => x.id !== n.id));
                      toast("已标记已读");
                    }}
                    style={{
                      fontSize: 10,
                      padding: "2px 8px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-surface-container)",
                      background: "transparent",
                      color: "var(--color-text-tertiary)",
                      cursor: "pointer",
                      flexShrink: 0,
                      marginLeft: 8,
                    }}
                  >
                    已读
                  </button>
                </div>
              ))}

              {/* Footer */}
              <Link
                href="/workbench/exceptions"
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
        <Link
          href="/settings"
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
        </Link>

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
