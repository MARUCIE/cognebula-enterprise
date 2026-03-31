# Lingque Desktop (灵阙财税) — Site Vision

> Design System: Heritage Monolith ("The Architectural Ledger")
> Stitch Project ID: 12770423165646112515

## 1. Vision

AI-Staffed Finance & Tax Firm desktop application. Enterprise accounting workbench for Chinese bookkeeping firms. Every screen is a production tool, not a marketing page.

## 2. Design System

See `.stitch/DESIGN.md` — Heritage Monolith: Zero-Radius, Zero-Shadow, Tonal Layering.

## 3. Tech Stack

- Frontend: Next.js 15 + Tailwind CSS v4
- Backend: FastAPI (Python) + KuzuDB Knowledge Graph
- API: VPS 100.75.77.112:8400 (Tailscale)
- Deployment: Cloudflare Pages (lingque-desktop.pages.dev)

## 4. Sitemap

- [x] `/workbench/accounting` — 核算工作台 (Invoice upload + AI journal entry review)
- [x] `/workbench/tax` — 税务工作台 (Tax calculation + filing)
- [x] `/dashboard` — 仪表盘 (Monthly overview + KPIs)
- [x] `/clients` — 客户管理 (Client list + service status)
- [x] `/settings` — 系统设置 (Chart of accounts, templates, team)

## 5. Roadmap

1. ~~核算工作台~~ DONE
2. ~~税务工作台~~ DONE
3. ~~仪表盘~~ DONE
4. ~~客户管理~~ DONE
5. ~~系统设置~~ DONE

## 6. Creative Freedom

- 报表中心 — Financial statement generation
- 知识库 — Regulation knowledge base (KuzuDB powered)
- 审计日志 — Audit trail viewer
