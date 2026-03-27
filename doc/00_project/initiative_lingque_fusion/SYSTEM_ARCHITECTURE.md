# System Architecture: Virtual Finance/Tax Company

> v2.2 — 2026-03-27 | CogNebula x Lingque x OpenClaw Fusion | Multi-Surface Architecture (2 Apps)

## Executive Summary

Build a **virtual finance/tax company** — not a tool, not a dashboard, but a complete AI-staffed firm that accounting companies can "hire." Users see an office with departments, workstations, ID badges, skill trees, and cross-role workflows. Behind the scenes: CogNebula KG provides domain intelligence (514K nodes, 2,901 laws), OpenClaw supplies the skill chain (37K+ curated skills), and the Lingque engine orchestrates task execution.

**Product metaphor**: "You're not using an AI tool — you're hiring a fully staffed AI accounting firm."

## Architecture Principles

1. **Company-as-Interface**: The UI is an office, not a dashboard. Every interaction is framed as delegating work to a colleague.
2. **Agent-as-Employee**: Each agent has an identity (badge), a desk (workstation), skills (skill tree from OpenClaw), and workflows (cross-department collaboration).
3. **OpenClaw-as-HR**: Skills are hired from the OpenClaw marketplace, not hardcoded. New capabilities = hiring new skills for existing employees.
4. **KG-as-Company-Brain**: The knowledge graph is the company's institutional memory — every employee queries it, none of them own it.
5. **Separation of concerns**: Frontend (office UI) / Agent Runtime (employees) / KG Semantic Layer (brain) / OpenClaw (HR/skills) are independent subsystems.
6. **Multi-Surface, Shared Brain**: 2 deployed apps (office + internal) sharing 3 backend subsystems. Desktop for customer work, Internal for platform ops + expert tools. Mobile deferred to PWA + WeChat notifications. See `MULTI_SURFACE_ARCHITECTURE_V1.md` for full swarm-consensus ADR (7 decisions, 4 advisors).

## Multi-Surface Architecture (v1.0, 2026-03-27)

> Full ADR: `MULTI_SURFACE_ARCHITECTURE_V1.md` (swarm consensus: Drucker/Jobs/Hickey/Hara)

### Core Insight: 2 Information Needs, Not 4 Surfaces

Original proposal had 4 surfaces (PC Desktop, Expert Workbench, Ops Admin, Mobile App).
Swarm consensus: **architecture boundaries follow data permissions, not UI complexity.**

| Information Need | App | Surfaces | Data Permission |
|-----------------|-----|----------|----------------|
| **Customer** (delegate work) | `apps/office` | PC Desktop (built) + PWA/WeChat (Phase 6+) | Own company only, named KG queries |
| **Internal** (ensure system correctness) | `apps/internal` | Ops (P1) + Expert (P2) as route groups | All data, all customers, raw KG access |

### Target Structure (Monorepo)

```
lingque-fusion/
├── packages/
│   ├── ui/            # Shared design components
│   ├── api-client/    # Type-safe API client (3 subsystems)
│   ├── auth/          # JWT + RBAC middleware
│   └── types/         # Shared domain types
├── apps/
│   ├── office/        # Surface A: Customer (10 pages built, Next.js 15)
│   └── internal/      # Surface B: Platform (ops + expert route groups)
└── [backend subsystems unchanged]
```

### Key ADRs

| Decision | Chosen | Rejected |
|----------|--------|----------|
| Surface count | 2 apps | 4 apps |
| Expert Workbench | Route group in internal app | Standalone app |
| Mobile strategy | PWA + WeChat notifications | Native app |
| API topology | Direct connect, no gateway | Unified gateway |
| Auth model | Single JWT + role claim | OAuth + authorization server |
| KG access | 3-tier: named → explore templates → raw (admin) | Open Cypher |

### Build Priority

P0: Office iterate (accountability layer) → P1: Internal Ops → P2: Expert migration → P3: Mobile PWA

### API Contract Rule

Agent Runtime returns **structured data envelopes**, never pre-rendered content:

```json
{
  "agent": { "id": "tax-accountant", "name": "林税安", "status": "busy" },
  "task": { "type": "vat-filing-check", "result": {...}, "confidence": 0.91 },
  "citations": [{ "source": "LawOrRegulation", "id": "FLK_xxx", "title": "..." }],
  "workflow_position": { "step": 3, "total": 5, "next_agent": "compliance-officer" }
}
```

Desktop renders this as a detailed workstation view with skill tree + citation sidebar.
Mobile renders the same data as a chat bubble with a confidence badge and a "查看详情" link.

### Mobile Surface: WeChat Mini Program

Target: WeChat Mini Program (not native app). Reasons:
- Accounting firms live in WeChat ecosystem (client groups, document sharing, payments)
- Zero-install distribution (scan QR → start using)
- WeChat Pay integration for future billing
- Template message push for workflow alerts (税期提醒, 审批通知)

## Virtual Company Organization

### Department Structure

```
灵阙财税 (Lingque Finance & Tax Co.)
│
├── 税务部 Tax Department
│   ├── 税务会计 Tax Accountant (P0)
│   └── 税务顾问 Tax Advisor (P1)
│
├── 记账部 Bookkeeping Department
│   ├── 记账员 Bookkeeper (P1)
│   └── 审核会计 Review Accountant (P2)
│
├── 合规部 Compliance Department
│   └── 合规主管 Compliance Officer (P0)
│
├── 客户部 Client Services
│   └── 客户经理 Account Manager (P2)
│
└── 行政部 Administration
    └── 行政助理 Admin Assistant (P2)
```

### Agent Identity System

Each agent has a complete identity:

```
AgentIdentity
  id: "tax-accountant"
  name: "林税安"                    // Chinese name (memorable)
  english_name: "Lina"
  title: "高级税务会计"
  department: "税务部"
  badge_number: "LQ-TX-001"
  avatar: generated via AI
  motto: "准确是我的底线，法规是我的武器"

  skills: SkillTree               // From OpenClaw
  workflows: WorkflowDef[]        // Cross-department collaboration
  kg_tools: string[]              // KG semantic layer tools
  confidence_profile: {           // Per-task confidence thresholds
    "tax-qa": 0.85,
    "vat-filing": 0.92,
  }
```

### Agent Role Cards

| Badge | Name | Title | Department | P0 Skills | KG Tools |
|-------|------|-------|-----------|-----------|----------|
| LQ-TX-001 | 林税安 | 高级税务会计 | 税务部 | tax-qa, vat-check, regulation-lookup | lookup_tax_rate, trace_regulation_chain |
| LQ-HG-001 | 赵合规 | 合规主管 | 合规部 | golden-tax-scan, compliance-audit | batch_compliance_scan, check_compliance_rules |
| LQ-TX-002 | 陈税策 | 税务顾问 | 税务部 | tax-planning, risk-assessment | search_similar_scenarios, trace_regulation_chain |
| LQ-JZ-001 | 王记账 | 记账员 | 记账部 | voucher-gen, reconciliation | lookup_tax_rate |
| LQ-SH-001 | 张审核 | 审核会计 | 记账部 | review-voucher, error-detect | check_compliance_rules |
| LQ-KH-001 | 李客服 | 客户经理 | 客户部 | client-qa, report-gen | search_similar_scenarios |
| LQ-XZ-001 | 周小秘 | 行政助理 | 行政部 | calendar, filing-reminder | (none) |

## Skill Tree Architecture (OpenClaw-Powered)

### Skill Supply Chain

```
OpenClaw Foundry (37K+ skills, rated S/A/B/C/D)
  ↓ Blueprint generation (role + industry = finance-tax)
  ↓ Filtered to ~200 finance/tax relevant skills
  ↓ Categorized into skill trees per agent role
  ↓
Agent Skill Tree (per employee)
  ├── L0 Universal Skills (all employees)
  │   ├── document-understanding
  │   ├── search-first
  │   └── grammar-check
  │
  ├── L1 Department Skills (shared within dept)
  │   ├── [税务部] tax-regulation-lookup, tax-rate-calc
  │   ├── [记账部] voucher-template, reconciliation
  │   └── [合规部] compliance-checklist, risk-scoring
  │
  └── L2 Role Skills (unique to this agent)
      ├── [税务会计] vat-filing-check, tax-qa-expert
      ├── [合规主管] golden-tax-iv-scan, batch-audit
      └── [客户经理] client-report-gen, faq-responder
```

### Skill Tree Visual Model

Each agent's workstation displays their skill tree as an interactive visualization:

```
             [核心能力]
            /    |     \
      [税法知识] [申报]  [合规]
       /   \      |      |   \
  [增值税] [企业所得税] [金税四期] [风险预警]
    |        |          |         |
  [申报]  [汇算清缴]  [异常检测]  [预警报告]
```

Each skill node shows:
- Skill name (Chinese)
- Source: OpenClaw skill ID
- Proficiency level: S/A/B/C (from OpenClaw rating)
- Usage count (how many times this employee used it)
- Last used date

## Cross-Role Workflows

### Workflow 1: 月度报税 (Monthly Tax Filing)

```
客户经理(李客服)          记账员(王记账)         税务会计(林税安)        合规主管(赵合规)
    │                        │                      │                     │
    ├─ 收集客户资料 ────────→│                      │                     │
    │                        ├─ 生成凭证 ──────────→│                     │
    │                        │                      ├─ 增值税计算          │
    │                        │                      ├─ 申报表生成          │
    │                        │                      ├─ 法规合规检查 ──────→│
    │                        │                      │                     ├─ 金税四期扫描
    │                        │                      │                     ├─ 风险评估
    │                        │                      │◄─ 审核通过/驳回 ────┤
    │                        │                      ├─ 提交申报            │
    │◄─ 结果通知 ────────────┤◄─ 归档凭证 ─────────┤                     │
```

### Workflow 2: 客户合规体检 (Client Compliance Health Check)

```
合规主管(赵合规) triggers:
  1. batch_compliance_scan(all_clients, current_period)
  2. For each HIGH risk client:
     → 税务顾问(陈税策) deep analysis
     → 客户经理(李客服) notify client
  3. Generate compliance report → 行政助理(周小秘) distribute
```

### Workflow Data Model

```
WorkflowDefinition
  id: "monthly-tax-filing"
  name: "月度报税"
  trigger: "cron:monthly-5th" | "manual" | "event:client-data-received"
  steps:
    - agent: "account-manager"
      task: "collect-client-data"
      output: "client_data_package"
      next: "bookkeeper-voucher"
    - agent: "bookkeeper"
      task: "generate-vouchers"
      input: "client_data_package"
      output: "voucher_set"
      next: "tax-accountant-calc"
    - agent: "tax-accountant"
      task: "vat-filing-check"
      input: "voucher_set"
      output: "filing_draft"
      next: "compliance-review"
    - agent: "compliance-officer"
      task: "golden-tax-risk-scan"
      input: "filing_draft"
      output: "review_result"
      next_if_pass: "tax-accountant-submit"
      next_if_fail: "tax-accountant-revise"
```

## System Topology (Updated v2.1)

```
┌─────────────────────────────────┐  ┌──────────────────────────┐
│   Desktop Frontend (Next.js 15) │  │  Mobile (WeChat Mini)     │
│   Phase 0-3 ★                   │  │  Phase 6-8                │
│                                 │  │                          │
│  Lobby · Workstation · Workflow │  │  Chat · Approve · Alerts │
│  Compliance · Skill Store · KG  │  │  Status · Agent Cards    │
└────────────────┬────────────────┘  └────────────┬─────────────┘
                 │ REST API (JSON envelopes)       │
                 └────────────────┬────────────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                 │
                 ▼                ▼                 ▼
        ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
        │ Agent Runtime│ │ KG Semantic  │ │ OpenClaw     │
        │ (Gateway)    │ │ Layer        │ │ Skills API   │
        │              │ │ (FastAPI)    │ │              │
        │ - Identity   │ │ - Named      │ │ - Skill      │
        │   Registry   │ │   Query Tools│ │   Catalog    │
        │ - Task Router│ │ - Vector     │ │ - Blueprint  │
        │ - Workflow   │ │   Search     │ │   Generator  │
        │   Engine     │ │ - Citation   │ │ - Rating     │
        │ - Confidence │ │   Builder    │ │   System     │
        │   Scorer     │ │              │ │              │
        │ PostgreSQL   │ │ KuzuDB +     │ │ D1 + R2      │
        │              │ │ LanceDB      │ │ (CF Workers) │
        └──────────────┘ └─────────────┘ └──────────────┘
                                ▲
                         ┌──────┴───────┐
                         │ KG Build     │
                         │ Pipeline     │
                         │ (Offline)    │
                         └──────────────┘
```

### Subsystem Responsibilities

| Subsystem | Owns | Changes When |
|-----------|------|-------------|
| **Frontend** | Office UI, workstation views, skill tree viz, workflow monitor | New UI/UX needed |
| **Agent Runtime** | Agent identities, task routing, workflow DAG execution, confidence | New agent or workflow added |
| **KG Semantic Layer** | Named queries, citation builder, vector search | New query or KG schema change |
| **OpenClaw Skills** | Skill catalog, blueprints, ratings, skill-to-role mapping | New skill published or rating updated |
| **KG Build Pipeline** | Crawlers, ingest, edge enrichment | New data source |

## Frontend Pages

### Page 1: Office Lobby (公司大厅)

The landing page. Shows:
- Company org chart (interactive, click department to zoom)
- Department summary cards with agent avatars
- Real-time activity feed ("林税安正在处理XX公司增值税申报")
- Quick action: "找人帮忙" → natural language input → routes to best agent

### Page 2: Workstation (工位)

Individual agent view. Shows:
- Agent badge card (avatar, name, title, badge number, motto)
- Skill tree (interactive visualization, OpenClaw-sourced)
- Chat interface (delegate tasks to this specific agent)
- Recent work history (task executions with citations)
- Performance metrics (tasks completed, accuracy rate, avg confidence)

### Page 3: Workflow Monitor (工作流看板)

Cross-agent collaboration view. Shows:
- Active workflows as Kanban/swim-lane boards
- Each lane = one agent, cards flow between lanes
- Status: pending → in-progress → review → completed
- Click any card to see execution details + citations

### Page 4: Compliance Dashboard (合规看板)

The "200 clients at a glance" view (Jobs' "1000 songs" moment):
- Grid of all client companies
- Each cell: company name + traffic light (green/amber/red)
- Click to drill down: risk details + citations + remediation
- Triggered by 合规主管(赵合规) batch scan

### Page 5: Skill Store (技能商店)

OpenClaw-powered skill marketplace:
- Browse available skills by category
- See which agent can learn which skill
- One-click "hire skill" (install from OpenClaw → assign to agent)
- Skill ratings (S/A/B/C from OpenClaw)

## Agent Identity Data Model

```
AgentIdentity (stored in PostgreSQL)
  id: "tax-accountant"
  name: "林税安"
  english_name: "Lina"
  title: "高级税务会计"
  department_id: "tax-dept"
  badge_number: "LQ-TX-001"
  avatar_url: "/avatars/lina.png"
  motto: "准确是我的底线，法规是我的武器"
  status: "online" | "busy" | "offline"

  // OpenClaw skill binding
  openclaw_blueprint_id: "bp-finance-tax-accountant-v1"
  installed_skills: [
    { skill_id: "tax-qa-expert", source: "openclaw", rating: "S", installed_at: ... },
    { skill_id: "vat-filing-check", source: "aifleet", rating: "A", installed_at: ... },
  ]

  // KG tool binding
  kg_tools: ["lookup_tax_rate", "trace_regulation_chain", "check_compliance_rules"]

  // Confidence profile
  confidence_thresholds: {
    "tax-qa": 0.85,
    "vat-filing-check": 0.92,
    "regulation-lookup": 0.80,
  }

SkillTreeNode
  skill_id: "vat-filing-check"
  parent_id: "tax-filing"          // Tree hierarchy
  name: "增值税申报检查"
  category: "L2-role"              // L0/L1/L2
  source: "openclaw"
  openclaw_rating: "A"
  usage_count: 147
  last_used: timestamp
  proficiency: 0.94                // Calculated from execution history

WorkflowInstance (append-only)
  id: uuid
  workflow_def_id: "monthly-tax-filing"
  client_id: "company-xxx"
  current_step: 3
  steps_completed: [
    { agent: "account-manager", task: "collect-data", result: ..., at: ... },
    { agent: "bookkeeper", task: "gen-vouchers", result: ..., at: ... },
  ]
  status: "in-progress" | "completed" | "blocked"
```

## Implementation Phases

### Desktop-First (Phase 0-5)

| Phase | Scope | Duration | Key Deliverable |
|-------|-------|----------|----------------|
| **0** | KG Semantic Tools | 2 days | 5 named query endpoints on :8400 |
| **1** | Agent Identity + Runtime | 3 days | 7 agents with identities, task routing, confidence |
| **2** | Stitch Design → Desktop Frontend | 3 days | Office lobby + workstation + workflow monitor |
| **3** | OpenClaw Integration | 2 days | Skill tree from blueprints, skill store page |
| **4** | Workflows + Compliance | 3 days | Monthly filing workflow, batch scan, "200家看板" |
| **5** | Polish + Deploy | 2 days | 3 rounds UI polish, Docker, VPS production |

### Mobile-Second (Phase 6-8)

| Phase | Scope | Duration | Key Deliverable |
|-------|-------|----------|----------------|
| **6** | WeChat Mini Program Shell | 3 days | Auth + agent chat + workflow status (same API) |
| **7** | Push Notifications + Approvals | 2 days | Template messages for 税期提醒, one-tap approve/reject |
| **8** | Mobile Polish + Launch | 2 days | 3 rounds UI polish, WeChat审核提交 |

Phase 6-8 reuses 100% of the backend from Phase 0-5. Zero new API endpoints needed — only a new rendering surface.

## ADRs (Carried Forward)

All 5 ADRs from v1.0 remain valid:
- ADR-1: Task agents (behind role identity facade)
- ADR-2: Semantic query layer (no raw Cypher)
- ADR-3: Confidence gating (3-tier)
- ADR-4: Citation chain (every answer has source trail)
- ADR-5: New thin frontend (Next.js)

Added:
- **ADR-6: Agent Identity System** — Each agent has a persistent identity (name, badge, avatar, motto). Identity is stored in PostgreSQL, not in prompts. This enables the "virtual colleague" experience.
- **ADR-7: OpenClaw Skill Binding** — Agent skills are sourced from OpenClaw blueprints, not hardcoded. Adding capabilities = "hiring a new skill" from the marketplace. This keeps the system extensible without code changes.
- **ADR-8: Workflow Engine** — Cross-agent workflows are declarative DAGs (JSON), not imperative code. New workflows are data, not deployments.
- **ADR-9: Dual-Surface Strategy** — Desktop (Next.js) for expert work, Mobile (WeChat Mini Program) for daily ops. Both hit the same Agent Runtime API. Desktop-first (Phase 0-5), Mobile-second (Phase 6-8). API returns structured JSON envelopes, never pre-rendered content.

---

Maurice | maurice_wen@proton.me
