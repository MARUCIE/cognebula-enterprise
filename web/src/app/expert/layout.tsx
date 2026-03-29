"use client";

/* System A: CogNebula Platform — Internal KG Infrastructure
   LIGHT theme with slate-blue sidebar.
   Visual distinction from System B (Heritage Monolith warm-cream + navy). */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CN } from "../lib/cognebula-theme";

const navItems = [
  { href: "/expert", label: "总览", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4" },
  { href: "/expert/kg", label: "知识图谱", icon: "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" },
  { href: "/expert/data-quality", label: "数据质量", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { href: "/expert/reasoning", label: "推理检查", icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" },
  { href: "/expert/rules", label: "规则调试", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z" },
  { href: "/expert/bridge", label: "系统桥接", icon: "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" },
];

export default function ExpertLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div style={{ display: "flex", minHeight: "100vh", width: "100%", background: CN.bg }}>
      {/* Slate-blue sidebar — distinguishes from Heritage Monolith navy */}
      <aside style={{
        width: 220,
        background: CN.bgSidebar,
        display: "flex",
        flexDirection: "column",
        position: "fixed",
        top: 0,
        left: 0,
        bottom: 0,
        zIndex: 40,
      }}>
        {/* Brand */}
        <div style={{ padding: "20px 16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "#60A5FA", letterSpacing: "0.5px" }}>
            CogNebula
          </div>
          <div style={{ fontSize: 10, color: CN.textOnDarkMuted, marginTop: 2, letterSpacing: "1.5px", textTransform: "uppercase" }}>
            知识图谱基础设施
          </div>
        </div>

        {/* Nav */}
        <nav style={{ padding: 8, flex: 1 }}>
          {navItems.map((item) => {
            const active = pathname === item.href || (item.href !== "/expert" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 12px",
                  marginBottom: 2,
                  color: active ? "#60A5FA" : CN.textOnDark,
                  background: active ? "rgba(96,165,250,0.12)" : "transparent",
                  borderLeft: active ? "2px solid #60A5FA" : "2px solid transparent",
                  textDecoration: "none",
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  borderRadius: "0 4px 4px 0",
                  transition: "all 0.15s",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d={item.icon} />
                </svg>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* System info */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid rgba(255,255,255,0.08)", fontSize: 10, color: CN.textOnDarkMuted }}>
          <div>System A -- 仅内部使用</div>
          <div style={{ marginTop: 2 }}>KG API: 100.75.77.112:8400</div>
        </div>

        {/* Back to System B */}
        <div style={{ padding: 8 }}>
          <Link
            href="/workbench/"
            style={{
              display: "block",
              padding: "8px 12px",
              color: CN.textOnDarkMuted,
              textDecoration: "none",
              fontSize: 11,
              textAlign: "center",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 4,
            }}
          >
            &larr; 返回灵阙产品端
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <main style={{
        marginLeft: 220,
        flex: 1,
        background: CN.bg,
        color: CN.text,
        minHeight: "100vh",
      }}>
        {/* Top bar — white with subtle bottom border */}
        <div style={{
          padding: "12px 32px",
          borderBottom: `1px solid ${CN.border}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: CN.bgTopbar,
        }}>
          <div style={{ fontSize: 11, color: CN.textMuted, letterSpacing: "1px", fontWeight: 500 }}>
            CogNebula 知识图谱平台
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11, color: CN.textMuted }}>
            <span>514K nodes</span>
            <span style={{ color: CN.border }}>|</span>
            <span>1.1M edges</span>
            <span style={{ color: CN.border }}>|</span>
            <span style={{ color: CN.green, fontWeight: 600 }}>API OK</span>
          </div>
        </div>

        {children}
      </main>
    </div>
  );
}
