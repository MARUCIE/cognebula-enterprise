"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useToast } from "./Toast";

const dailyNavItems = [
  { href: "/", label: "工作台", icon: DashboardIcon },
  { href: "/workbench", label: "月度看板", icon: WorkbenchIcon },
  { href: "/clients", label: "客户中心", icon: ClientIcon },
  { href: "/reports", label: "报告中心", icon: ReportIcon },
];

const proNavItems = [
  { href: "/tax", label: "智能报税", icon: TaxIcon },
  { href: "/ai-team", label: "AI 团队", icon: TeamIcon },
  { href: "/skills", label: "技能商店", icon: SkillIcon },
];

const opsNavItems = [
  { href: "/ops/customers", label: "客户健康", icon: OpsCustomersIcon },
  { href: "/ops/agents", label: "AI 专员监控", icon: OpsAgentsIcon },
  { href: "/ops/alerts", label: "系统告警", icon: OpsAlertsIcon },
];

const expertNavItems = [
  { href: "/expert/kg", label: "知识图谱", icon: KGIcon },
  { href: "/expert/reasoning", label: "推理检查", icon: ReasoningIcon },
  { href: "/expert/rules", label: "规则调试", icon: RulesIcon },
  { href: "/expert/data-quality", label: "数据质量", icon: DataQualityIcon },
];

const bottomItems = [
  { href: "/settings", label: "设置", icon: SettingsIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const toast = useToast();

  return (
    <aside
      className="fixed left-0 top-0 bottom-0 flex flex-col justify-between"
      style={{
        width: "var(--sidebar-width)",
        background: "var(--color-sidebar-bg)",
        zIndex: 40,
      }}
    >
      {/* Logo */}
      <div>
        <div
          className="flex items-center gap-3"
          style={{ padding: "var(--space-6) var(--space-6) var(--space-4)" }}
        >
          <div
            className="flex items-center justify-center"
            style={{
              width: 36,
              height: 36,
              background: "var(--color-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 21V7l9-4 9 4v14H3z"
                stroke="var(--color-on-primary)"
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
              <path d="M9 21v-6h6v6" stroke="var(--color-on-primary)" strokeWidth="1.8" />
              <path d="M12 7v4" stroke="var(--color-secondary)" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <div
              className="font-display font-bold text-[15px]"
              style={{ color: "var(--color-on-primary)" }}
            >
              灵阙财税
            </div>
            <div
              className="text-[10px] font-medium tracking-[0.18em] uppercase"
              style={{ color: "var(--color-sidebar-text)", opacity: 0.6 }}
            >
              AI-Staffed Firm
            </div>
          </div>
        </div>

        {/* Daily operations */}
        <nav className="mt-2" style={{ padding: "0 var(--space-3)" }}>
          {dailyNavItems.map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} />
          ))}
        </nav>

        {/* Professional tools section */}
        <SectionLabel label="专业工具" />
        <nav style={{ padding: "0 var(--space-3)" }}>
          {proNavItems.map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} />
          ))}
        </nav>

        {/* Ops section */}
        <SectionLabel label="OPS" />
        <nav style={{ padding: "0 var(--space-3)" }}>
          {opsNavItems.map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} size="sm" />
          ))}
        </nav>

        {/* Expert section */}
        <SectionLabel label="EXPERT" />
        <nav style={{ padding: "0 var(--space-3)" }}>
          {expertNavItems.map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} size="sm" />
          ))}
        </nav>
      </div>

      {/* Bottom section */}
      <div style={{ padding: "0 var(--space-3) var(--space-4)" }}>
        {/* New task button */}
        <button
          onClick={() => toast("新任务创建面板即将上线")}
          className="w-full flex items-center justify-center gap-2 font-medium transition-opacity hover:opacity-90"
          style={{
            padding: "10px 0",
            marginBottom: 12,
            borderRadius: "var(--radius-sm)",
            background: "linear-gradient(135deg, var(--color-primary), var(--color-primary-deep))",
            color: "var(--color-on-primary)",
            fontSize: 13,
            boxShadow: "0 2px 12px rgba(0, 58, 112, 0.3)",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          发起新任务
        </button>

        {/* Settings / Help */}
        {bottomItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="w-full flex items-center gap-3 text-left transition-colors"
            style={{
              padding: "8px 12px 8px 16px",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-sidebar-text)",
              fontSize: 13,
              textDecoration: "none",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--color-sidebar-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            <item.icon active={false} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}

/* ---- Shared sub-components ---- */

function SectionLabel({ label }: { label: string }) {
  return (
    <div style={{ padding: "var(--space-4) var(--space-6) 0" }}>
      <div style={{ height: 1, background: "rgba(255,255,255,0.08)", marginBottom: "var(--space-3)" }} />
      <span
        className="font-medium uppercase"
        style={{
          fontSize: 10,
          color: "var(--color-sidebar-text)",
          opacity: 0.4,
          letterSpacing: "0.16em",
          display: "block",
          padding: "0 10px",
          marginBottom: "var(--space-2)",
        }}
      >
        {label}
      </span>
    </div>
  );
}

function NavLink({
  item,
  pathname,
  size = "md",
}: {
  item: { href: string; label: string; icon: React.ComponentType<{ active: boolean }> };
  pathname: string;
  size?: "md" | "sm";
}) {
  const isActive =
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
  return (
    <Link
      href={item.href}
      className="w-full flex items-center gap-3 relative text-left transition-colors"
      style={{
        padding: "10px 12px 10px 16px",
        marginBottom: 2,
        borderRadius: "var(--radius-sm)",
        color: isActive
          ? "var(--color-sidebar-text-active)"
          : "var(--color-sidebar-text)",
        background: isActive
          ? "rgba(255, 255, 255, 0.08)"
          : "transparent",
        fontSize: size === "sm" ? 13 : 14,
        fontWeight: isActive ? 600 : 400,
        textDecoration: "none",
      }}
      onMouseEnter={(e) => {
        if (!isActive) e.currentTarget.style.background = "var(--color-sidebar-hover)";
      }}
      onMouseLeave={(e) => {
        if (!isActive) e.currentTarget.style.background = "transparent";
      }}
    >
      {isActive && (
        <span
          className="absolute left-0 top-1/2 -translate-y-1/2"
          style={{
            width: 4,
            height: 20,
            borderRadius: "0 2px 2px 0",
            background: "var(--color-secondary)",
          }}
        />
      )}
      <item.icon active={isActive} />
      <span>{item.label}</span>
    </Link>
  );
}

/* ---- Inline SVG Icons ---- */

function WorkbenchIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="4" height="18" stroke={c} strokeWidth="1.8" />
      <rect x="9" y="3" width="4" height="18" stroke={c} strokeWidth="1.8" />
      <rect x="15" y="3" width="4" height="18" stroke={c} strokeWidth="1.8" />
      <line x1="3" y1="9" x2="21" y2="9" stroke={c} strokeWidth="1" opacity="0.5" />
    </svg>
  );
}

function DashboardIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="8" height="8" rx="1" stroke={c} strokeWidth="1.8" />
      <rect x="13" y="3" width="8" height="4" rx="1" stroke={c} strokeWidth="1.8" />
      <rect x="13" y="10" width="8" height="11" rx="1" stroke={c} strokeWidth="1.8" />
      <rect x="3" y="14" width="8" height="7" rx="1" stroke={c} strokeWidth="1.8" />
    </svg>
  );
}

function TeamIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="7" r="3.5" stroke={c} strokeWidth="1.8" />
      <path d="M2 20c0-3.5 3-6 7-6s7 2.5 7 6" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="17" cy="8" r="2.5" stroke={c} strokeWidth="1.8" />
      <path d="M19 14c2.5.8 4 2.5 4 5" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function ClientIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="4" width="20" height="16" rx="2" stroke={c} strokeWidth="1.8" />
      <path d="M8 10h8M8 14h5" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function TaxIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 4h16v16H4z" stroke={c} strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M8 12l3 3 5-6" stroke={c} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReportIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M6 2h8l6 6v14H6z" stroke={c} strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke={c} strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M9 13h6M9 17h4" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function SkillIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.8" />
      <path d="M12 7v5l3 3" stroke={c} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SettingsIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke={c} strokeWidth="1.8" />
      <path
        d="M12 1v3M12 20v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M1 12h3M20 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
        stroke={c}
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function HelpIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={c} strokeWidth="1.8" />
      <path d="M9 9a3 3 0 115 2.5c0 1.5-2 2-2 3" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="18" r="0.5" fill={c} stroke={c} strokeWidth="1" />
    </svg>
  );
}

/* ---- Ops Icons ---- */

function OpsCustomersIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="7" height="7" rx="1.5" stroke={c} strokeWidth="1.8" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" stroke={c} strokeWidth="1.8" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke={c} strokeWidth="1.8" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" stroke={c} strokeWidth="1.8" />
    </svg>
  );
}

function OpsAgentsIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke={c} strokeWidth="1.8" />
      <path d="M12 1v4M12 19v4M4.2 4.2l2.8 2.8M17 17l2.8 2.8M1 12h4M19 12h4M4.2 19.8l2.8-2.8M17 7l2.8-2.8" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.2" strokeDasharray="3 3" />
    </svg>
  );
}

function OpsAlertsIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M12 2L2 20h20L12 2z" stroke={c} strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 9v5" stroke={c} strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="17" r="0.5" fill={c} stroke={c} strokeWidth="1" />
    </svg>
  );
}

/* ---- Expert Icons ---- */

function KGIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="5" r="2.5" stroke={c} strokeWidth="1.8" />
      <circle cx="5" cy="18" r="2.5" stroke={c} strokeWidth="1.8" />
      <circle cx="19" cy="18" r="2.5" stroke={c} strokeWidth="1.8" />
      <path d="M10.5 7L6.5 16M13.5 7L17.5 16M7.5 18h9" stroke={c} strokeWidth="1.5" />
    </svg>
  );
}

function ReasoningIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 4v16" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="4" cy="6" r="2" stroke={c} strokeWidth="1.5" />
      <circle cx="4" cy="12" r="2" stroke={c} strokeWidth="1.5" />
      <circle cx="4" cy="18" r="2" stroke={c} strokeWidth="1.5" />
      <path d="M6 6h6l4 6-4 6H6" stroke={c} strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M16 12h5" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function RulesIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="2" stroke={c} strokeWidth="1.8" />
      <path d="M7 8h10M7 12h7M7 16h4" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="17" cy="16" r="2" stroke={c} strokeWidth="1.5" />
    </svg>
  );
}

function DataQualityIcon({ active }: { active: boolean }) {
  const c = active ? "var(--color-on-primary)" : "var(--color-sidebar-text)";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 20V10M9 20V6M14 20V13M19 20V4" stroke={c} strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
