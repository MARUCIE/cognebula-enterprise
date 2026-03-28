"use client";

/* AppShell — conditionally renders System B chrome (Sidebar + TopBar)
   Expert routes (/expert/*) use their own layout (System A: CogNebula).
   Workbench routes get the full-width treatment (no padding). */

import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isExpert = pathname.startsWith("/expert");
  const isWorkbench = pathname.startsWith("/workbench");

  // System A (Expert/CogNebula) — skip System B chrome entirely
  if (isExpert) {
    return <>{children}</>;
  }

  // System B with Workbench (full-width, no padding)
  if (isWorkbench) {
    return (
      <>
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-screen" style={{ marginLeft: "var(--sidebar-width)" }}>
          <TopBar />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
        </div>
      </>
    );
  }

  // Default System B pages (with padding)
  return (
    <>
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen" style={{ marginLeft: "var(--sidebar-width)" }}>
        <TopBar />
        <main
          className="flex-1 overflow-y-auto"
          style={{ padding: "var(--space-6) var(--space-8)" }}
        >
          {children}
        </main>
      </div>
    </>
  );
}
