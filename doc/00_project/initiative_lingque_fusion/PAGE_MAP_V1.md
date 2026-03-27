# Lingque Desktop -- Page Map v1.0

> 15 routes, 22 static pages (7 agent workstation variants), deployed to lingque-desktop.pages.dev

## Site Architecture

```
lingque-desktop.pages.dev/
│
├── Customer Surface (Office) ──────────────────────────────────
│   ├── /                        Dashboard (今日概览)
│   ├── /ai-team                 AI Team Management (AI 专家团队)
│   ├── /ai-team/[id]            Agent Workstation (AI 专家工作站) x7
│   ├── /clients                 Client Center (客户中心)
│   ├── /tax                     Intelligent Tax Filing (智能报税)
│   ├── /reports                 Financial Reporting (报告中心)
│   ├── /skills                  Skill Store (技能商店)
│   ├── /compliance              Compliance Dashboard (合规管理看板)
│   ├── /audit                   Audit Workbench (智能审计工作台)
│   └── /settings                System Settings (系统设置)
│
├── Internal Surface (Ops) ─────────────────────────────────────
│   ├── /ops/customers           Customer Health Matrix (客户健康矩阵)
│   ├── /ops/agents              Agent Performance Monitor (Agent 性能监控)
│   └── /ops/alerts              System Alert Center (系统告警中心)
│
└── Shared Components ──────────────────────────────────────────
    ├── Sidebar                  240px fixed, 9 nav + 3 ops + 2 bottom
    ├── TopBar                   Route-aware title, search, notification, avatar
    └── Ops Layout               Bloomberg density wrapper
```

## Page Detail Matrix

### Customer Surface (10 pages)

| # | Route | Page Name | Key Sections | Data Entities | Primary Action |
|---|-------|-----------|-------------|---------------|----------------|
| 1 | `/` | 今日概览 | Welcome hero, KPI cards (4), Activity feed, Reports sidebar, Approval table | Tasks, Clients, Reports | Review + Approve |
| 2 | `/ai-team` | AI 专家团队 | Stats bar (4 KPIs), Hero agent card (林税安), Agent grid (7 cards), Task queue | 7 Agents, Tasks | View agent → Workstation |
| 3 | `/ai-team/[id]` | AI 专家工作站 | 2-col (Profile 320px + Chat), Skill tree (S/A/B/C), Task history, Confidence meter | Agent detail, Skills, Chat | Chat with agent |
| 4 | `/clients` | 客户中心 | KPI strip (4), Client table (8 rows, paginated), AI Insight panel, Compliance circle | 128 Clients, Tasks | View client details |
| 5 | `/tax` | 智能报税 | 4-stage pipeline visualization, Review queue, Tax advisor panel (¥45,829.30) | Tax filings, Regulations | Review + Submit |
| 6 | `/reports` | 报告中心 | KPI strip (3), Report templates grid, Anomaly detection, Export center | Reports, Templates | Generate + Export |
| 7 | `/skills` | 技能商店 | Hero banner, Category filters (6), Skill cards (6), Installed sidebar, AI suggestion | Skills (247), Agents | Install skill |
| 8 | `/compliance` | 合规管理看板 | Traffic light grid (30 cards, 6-col), Law citations sidebar, Risk summary | Compliance items, Laws | Review violations |
| 9 | `/audit` | 智能审计工作台 | 4-step flow, Finding list (FND codes), AI assistant panel, Evidence section | Audit findings, Evidence | Review + Resolve |
| 10 | `/settings` | 系统设置 | Firm profile form, AI behavior sliders (85%/60%), Team management, Billing (¥2,999/月) | Settings, Team, Billing | Configure |

### Internal Surface (3 pages)

| # | Route | Page Name | Key Sections | Data Entities | Primary Action |
|---|-------|-----------|-------------|---------------|----------------|
| 11 | `/ops/customers` | 客户健康矩阵 | KPI strip (5), Tier filter pills, Customer table (12 rows), Health dots, Utilization bars | 12 Customers | Monitor health |
| 12 | `/ops/agents` | Agent 性能监控 | Agent grid (4-col), Utilization bar chart, Skill usage table, Error log (5 rows) | 7 Agents, 10 Skills, 5 Errors | Investigate issues |
| 13 | `/ops/alerts` | 系统告警中心 | KPI strip (4), Severity + Source filters, Alert feed (15 cards), Status badges | 15 Alerts | Triage + Resolve |

## Navigation Structure

### Sidebar Navigation (left, 240px, dark)

```
[灵阙财税 Logo]
[AI-Staffed Firm]

├─ 工作台        →  /
├─ AI 团队       →  /ai-team
├─ 客户中心      →  /clients
├─ 智能报税      →  /tax
├─ 报告中心      →  /reports
├─ 技能商店      →  /skills
│
─── OPS ─────────
├─ 客户健康      →  /ops/customers
├─ Agent 监控    →  /ops/agents
├─ 系统告警      →  /ops/alerts
│
[+ 发起新任务]
├─ 设置          →  /settings
└─ 帮助中心      →  /help
```

### TopBar (route-aware)

| Route Pattern | Display Title |
|--------------|---------------|
| `/` | 今日概览 |
| `/ai-team` | AI 专家团队 |
| `/ai-team/*` | AI 专家工作站 |
| `/clients` | 客户中心 |
| `/tax` | 智能报税 |
| `/reports` | 报告中心 |
| `/skills` | 技能商店 |
| `/compliance` | 合规管理看板 |
| `/audit` | 智能审计工作台 |
| `/settings` | 系统设置 |
| `/ops/customers` | 客户健康矩阵 |
| `/ops/agents` | Agent 性能监控 |
| `/ops/alerts` | 系统告警中心 |

## User Flow Map

### Flow 1: Boss Morning Check (daily)
```
/ (Dashboard) → Review KPIs → Check activity feed → Approve pending items
    ↓
/ai-team → Spot check agent status → Click 林税安
    ↓
/ai-team/lin-shui-an → Review task history → Chat "Q3申报进度如何？"
```

### Flow 2: Tax Filing Cycle (weekly/monthly)
```
/tax → Check pipeline stages → Review queue items → Approve filings
    ↓
/compliance → Verify green lights → Check law citations for flagged items
    ↓
/reports → Generate tax report → Export PDF
```

### Flow 3: Client Onboarding (occasional)
```
/clients → Click "新增客户账户" → Fill client info
    ↓
/skills → Browse skills by category → Install relevant skills for agents
    ↓
/ai-team → Assign agents to new client → Monitor first-run
```

### Flow 4: Ops Morning Triage (daily, internal)
```
/ops/alerts → Filter by Critical → Triage open alerts → Acknowledge/Resolve
    ↓
/ops/agents → Check error agent (周小秘) → Review error log
    ↓
/ops/customers → Check 云峰智源 health (red) → Investigate low utilization
```

## Design System Summary

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#003A70` (Heritage Blue) | Navigation, headings, authority |
| Secondary | `#C5913E` (Prestige Gold) | Active indicators, AI suggestion, accent |
| Surface | `#F9F9F7` (Warm Cream) | Page background |
| Dept Tax | `#003A70` | 林税安, 陈税策 |
| Dept Bookkeeping | `#1B7A4E` | 王记账 |
| Dept Compliance | `#C44536` | 赵合规 |
| Dept Client | `#6B4C9A` | 张审核 |
| Dept Admin | `#8B8B8B` | 李客服, 周小秘 |

| Rule | Description |
|------|-------------|
| No-Line | Section separation via background shift, not borders |
| CJK Keep-All | `word-break: keep-all` for anti-orphan |
| No letterSpacing on CJK | Latin-only property |
| Fluid Layout | No root maxWidth, content fills viewport |
| Ops Density | 12px base, 36px rows, compact padding |

---

Maurice | maurice_wen@proton.me
