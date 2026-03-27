import type { Metadata } from "next";
import { Manrope, Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";

const manrope = Manrope({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
  weight: ["500", "600", "700", "800"],
});

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "灵阙财税 | AI 虚拟财税公司",
  description:
    "灵阙财税 -- AI-Staffed Finance & Tax Firm. 全自动 AI 代理团队处理报税、记账、合规与客户服务。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${manrope.variable} ${inter.variable} h-full`}
    >
      <body className="h-full flex" style={{ background: "var(--color-surface)" }}>
        {/* Sidebar -- fixed 240px */}
        <Sidebar />

        {/* Main area */}
        <div className="flex-1 flex flex-col min-h-screen" style={{ marginLeft: "var(--sidebar-width)" }}>
          <TopBar />
          <main
            className="flex-1 overflow-y-auto"
            style={{
              padding: "var(--space-8) var(--space-8)",
              paddingTop: "var(--space-6)",
            }}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
