import type { Metadata } from "next";
import { Manrope, Inter } from "next/font/google";
import "./globals.css";
import { AppShell } from "./components/AppShell";
import { ToastProvider } from "./components/Toast";

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
        <ToastProvider>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
