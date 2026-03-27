"use client";

import { usePathname } from "next/navigation";

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

export function TopBar() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);

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

        {/* Notification bell */}
        <button
          className="relative flex items-center justify-center transition-colors"
          style={{ width: 36, height: 36, borderRadius: "var(--radius-sm)" }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path
              d="M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9z"
              stroke="var(--color-text-secondary)"
              strokeWidth="1.8"
            />
            <path d="M13.73 21a2 2 0 01-3.46 0" stroke="var(--color-text-secondary)" strokeWidth="1.8" />
          </svg>
          {/* Notification dot */}
          <span
            className="absolute"
            style={{
              top: 6,
              right: 7,
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--color-danger)",
            }}
          />
        </button>

        {/* Help icon */}
        <button
          className="flex items-center justify-center"
          style={{ width: 36, height: 36, borderRadius: "var(--radius-sm)" }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="var(--color-text-secondary)" strokeWidth="1.8" />
            <path d="M9 9a3 3 0 115 2.5c0 1.5-2 2-2 3" stroke="var(--color-text-secondary)" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="12" cy="18" r="0.5" fill="var(--color-text-secondary)" />
          </svg>
        </button>

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
