# Lingque Fusion Optimized Architecture v2.0

> Post-swarm redesign (Drucker/Hickey/Meadows 3-round review, 2026-03-28).
> Decision: Split into 2 independent systems. Agents + Skill Marketplace = moat.

---

## 0. Swarm Verdict Summary

All 3 advisors: **RETHINK**. Core issues identified:

1. **Goal drift**: System optimizing internal completeness, not customer value delivery
2. **Complection**: Mock demo + real KG tool + product UI braided into 1 app (41 pages)
3. **Complexity overload**: B2 (complexity braking loop) is dominant; R1 (knowledge flywheel) is broken at S3 (customers = 0)
4. **Infrastructure exposed as product**: KG/Agent/OpenClaw are implementation means, not customer features

**User override on swarm**: Agents + Skill marketplace are NOT expendable — they are the moat. Architecture must make them the competitive advantage, not hide them.

---

## 1. Two Independent Systems

```
┌─────────────────────────────────────────────────────┐
│  System A: CogNebula Platform (内部基础设施)          │
│  Purpose: Knowledge engine + data quality            │
│  Users: Internal team only (Maurice + future ops)    │
│  Deploy: VPS (Tailscale), NOT customer-facing        │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ KuzuDB   │  │ LanceDB  │  │ Know-Arc │           │
│  │ 514K     │  │ Vectors  │  │ Pipeline │           │
│  │ nodes    │  │ Semantic  │  │ Ingest   │           │
│  └────┬─────┘  └────┬─────┘  └──────────┘           │
│       │              │                               │
│  ┌────┴──────────────┴────┐                          │
│  │ KG API (FastAPI :8400) │                          │
│  │ /stats /search /graph  │                          │
│  │ /quality /chat         │                          │
│  └────────────┬───────────┘                          │
│               │                                      │
│  ┌────────────┴───────────┐                          │
│  │ KG Explorer (internal) │                          │
│  │ Cytoscape.js + React   │                          │
│  └────────────────────────┘                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  System B: 灵阙财税 (产品)                            │
│  Purpose: AI-staffed virtual accounting firm         │
│  Users: Accounting firms (B2B2C)                     │
│  Deploy: CF Pages (frontend) + CF Workers (API)      │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │          L1: 代账工作台 (Core Workflow)       │     │
│  │  Task Queue → Risk Matrix → Human Confirm   │     │
│  └────────────────────┬────────────────────────┘     │
│                       │                              │
│  ┌────────────────────┴────────────────────────┐     │
│  │          L2: 数字员工 (Agent Runtime)  [MOAT] │     │
│  │  7 named agents, track record, accuracy     │     │
│  │  Identity = trust anchor for customers      │     │
│  └────────────────────┬────────────────────────┘     │
│                       │                              │
│  ┌────────────────────┴────────────────────────┐     │
│  │      L3: 技能商店 (Skill Marketplace)  [$$]  │     │
│  │  Free tier + Premium skills (per-use/sub)   │     │
│  │  Skills FROM OpenClaw + curated packs       │     │
│  └────────────────────┬────────────────────────┘     │
│                       │                              │
│  ┌────────────────────┴────────────────────────┐     │
│  │      L4: 知识引擎 (KG Semantic Layer)        │     │
│  │  INVISIBLE to customer. Powers L2 accuracy  │     │
│  │  Calls System A KG API via CF Worker proxy  │     │
│  └─────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
```

### System A: CogNebula Platform

**What it is**: Knowledge Graph infrastructure + quality tooling.

**What it is NOT**: A product. Not customer-facing. No revenue from here.

| Component | Tech | Purpose |
|-----------|------|---------|
| KG Store | KuzuDB + LanceDB | 514K nodes, 1.1M edges, 3-mode query |
| KG API | FastAPI :8400 | REST endpoints for graph/search/stats |
| KG Explorer | React + Cytoscape.js | Internal visualization + quality audit |
| Know-Arc | Python pipelines | Triple generation, expert review, ingest |

**Migration plan**: KuzuDB is archived (2025-10). Evaluate Neo4j Community or Apache AGE within 6 months. LanceDB is stable.

### System B: 灵阙财税 (The Product)

**What it is**: An AI-staffed virtual accounting firm that helps real accounting firms 3x their client capacity.

**4 layers, strict visibility rules:**

---

## 2. L1 — 代账工作台 (Core Workflow)

**What the customer sees first. Task queue, not KG visualization.**

```
┌─────────────────────────────────────────┐
│  今日任务                    5 待处理    │
├─────────────────────────────────────────┤
│  🟢 中铁建设 - 月度凭证录入     王记账   │
│  🟡 腾讯科技 - Q3 现金流异常    张审核   │
│  🔴 华夏贸易 - 转让定价审查     赵合规   │
│  🟢 明达科技 - 增值税申报       林税安   │
│  🟢 泰和养老 - 社保核算         王记账   │
├─────────────────────────────────────────┤
│  需要您确认 (2)                          │
│  ├ 腾讯科技: 现金流偏离 15%, 建议人工核实 │
│  └ 华夏贸易: 关联交易占比超 30%          │
└─────────────────────────────────────────┘
```

**Design principles (Drucker-informed):**
- Task queue is the primary view (not dashboard KPIs)
- Risk traffic light (green/yellow/red) for every client
- Human confirmation items are few and explicit
- Everything else runs automatically in the background

**Pages (reduced from 41 to ~12 for product):**

| Page | Purpose | Data Source |
|------|---------|-------------|
| / (Dashboard) | Today's task queue + risk overview | Real API |
| /clients | Client list with health status | Real API |
| /clients/[id] | Client detail + activity timeline | Real API |
| /reports | Generated reports + approval queue | Real API |
| /reports/[id] | Report detail with AI annotations | Real API |
| /agents | Digital employee team overview | Real API |
| /agents/[id] | Agent workstation + chat | Real API |
| /skills | Skill marketplace (install/uninstall) | Real API |
| /tax | Tax filing assistant | Real API |
| /compliance | Risk dashboard (traffic light grid) | Real API |
| /settings | System settings + billing | Real API |
| /audit | Audit workspace | Real API |

**Zero mock data rule**: Every number comes from an API call or shows a loading state.

---

## 3. L2 — 数字员工 (Agent Runtime) — THE MOAT

**Why agents are the moat (user override on swarm):**

Swarm said "agent identity is ceremony." User disagrees. Here's why agents are defensible:

### 3.1 Agent Identity = Trust Anchor

```
Customer mental model:
  "林税安 has been doing my VAT filing for 6 months.
   Accuracy rate: 98.2%. Zero compliance incidents.
   I trust 林税安."

NOT:
  "Pipeline VAT_FILING_V3 executed successfully."
```

In China's B2B accounting market, **trust is personal, not institutional**. Accounting firms assign specific accountants to specific clients. The digital employee metaphor maps directly to this cultural expectation.

**Trust is earned through track record, not through branding.** Each agent accumulates:
- Accuracy rate (per task type)
- Tasks completed (volume)
- Compliance incidents (zero = trustworthy)
- Client tenure (how long serving this client)

This track record is **non-portable** — if a customer switches to a competitor, they lose their agent's history. This is lock-in through trust.

### 3.2 Agent Architecture (Hickey-informed simplification)

```
agents.json (single source of truth):
{
  "lin-shui-an": {
    "display": { "name": "林税安", "title": "高级税务会计", "dept": "税务部", "avatar": "..." },
    "capabilities": ["vat-filing", "income-tax", "tax-incentive-review"],
    "installed_skills": ["SK-VAT-001", "SK-CIT-002", "SK-INCENTIVE-003"],
    "metrics": { "accuracy": 0.982, "tasks_completed": 1284, "incidents": 0 }
  }
}
```

**Hickey's simplification applied:**
- Identity (display) is a pure config → JSON, not 700 lines of TSX
- Capabilities map to skill IDs → decoupled from agent identity
- Metrics are values (immutable records) → not mutable state in React

**Agent is NOT a container of skills. Agent is a TRUST INTERFACE that delegates to skills.**

```
Customer request → Agent receives → Agent selects skills → Skills execute using KG
                                                          → Results attributed to Agent
```

### 3.3 Agent Slots as Revenue Tier

| Tier | Agents | Skills per Agent | Price |
|------|--------|-----------------|-------|
| Starter | 3 (税/账/合规) | 5 basic each | Free / ¥999/mo |
| Professional | 5 (+审核+客服) | 15 each + premium | ¥2,999/mo |
| Enterprise | 7 (full team) | Unlimited | ¥8,999/mo |

More agents = more parallel work = higher client capacity = more revenue for accounting firm.

---

## 4. L3 — 技能商店 (Skill Marketplace) — THE REVENUE ENGINE

### 4.1 Skill as Plugin

A skill is an atomic, composable capability that an agent can install and use.

```typescript
interface Skill {
  id: string;              // "SK-VAT-001"
  name: string;            // "增值税一般纳税人申报"
  category: SkillCategory; // "tax" | "bookkeeping" | "compliance" | "audit"
  tier: "free" | "premium" | "enterprise";
  price?: {
    model: "per-use" | "monthly" | "one-time";
    amount: number;        // CNY
  };
  requires_kg: string[];   // KG node types this skill queries
  input_schema: JSONSchema;
  output_schema: JSONSchema;
  accuracy_benchmark: number; // minimum accuracy on test set
}
```

### 4.2 Pricing Model (Marketplace)

| Category | Free Tier | Premium | Enterprise |
|----------|-----------|---------|------------|
| 基础记账 (Bookkeeping) | 凭证录入, 银行对账 | 多币种处理, 合并报表 | 自定义科目体系 |
| 税务申报 (Tax Filing) | 增值税, 企业所得税 | 加计扣除, 跨境税务 | 转让定价, 税收协定 |
| 合规检查 (Compliance) | 基础合规扫描 | 行业专项, 风险预警 | 自定义规则引擎 |
| 审计辅助 (Audit) | 异常检测 | 抽样策略, 审计底稿 | 持续审计 |

**Revenue share**: Platform 70% / Skill developer 30% (for third-party skills from OpenClaw ecosystem).

**Lock-in mechanics:**
1. **Skill installation** = configuration + calibration for client's specific business. Switching means reconfiguring.
2. **Accuracy improvement** = skills get better with use (feedback loop). New competitor starts at 0.
3. **Skill composition** = complex workflows chain multiple skills. The more skills installed, the deeper the integration.

### 4.3 OpenClaw Integration

```
OpenClaw Marketplace (external)
    ↓ curated import (rated S/A/B/C)
灵阙 Skill Store (internal marketplace)
    ↓ install to agent
Agent Runtime (execution)
    ↓ calls KG for knowledge
KG Semantic Layer (System A)
```

OpenClaw provides the **skill supply chain**. Lingque provides the **trust runtime**.

---

## 5. L4 — 知识引擎 (KG Semantic Layer) — INVISIBLE

**Customer never sees this layer.** Its value shows up as:
- Agent answers are more accurate
- Compliance checks catch more risks
- Tax optimizations save more money

### 5.1 KG Access Pattern

```
Frontend (System B)
    ↓ REST call
CF Worker Proxy (HTTPS, eliminates mixed content)
    ↓ authenticated proxy
KG API (System A, FastAPI :8400)
    ↓ KuzuDB Cypher + LanceDB vector
Response → formatted for frontend consumption
```

**The CF Worker proxy solves:**
1. Mixed content (HTTPS → HTTP)
2. API key management (customer never sees KG credentials)
3. Rate limiting (prevent abuse)
4. Response transformation (raw KG → frontend-friendly JSON)

### 5.2 Three Query Tiers (unchanged from v1)

| Tier | Who | What | Example |
|------|-----|------|---------|
| T1 Named | Customer (via agent) | Parameterized safe queries | "这家企业适用什么税率?" |
| T2 Explore | Expert (internal) | Template-based exploration | expand_node, trace_path |
| T3 Raw | Admin only | Direct Cypher | Debug, data repair |

---

## 6. Moat Analysis

```
                    MOAT DEPTH
                    ─────────────►

  Easy to copy      Hard to copy       Impossible to copy
  ├─────────────────┼──────────────────┼──────────────────┤
  │                 │                  │                  │
  │  UI Design      │  KG (514K nodes  │  Trust Record    │
  │  Page Layout    │   domain-specific│  (Agent accuracy │
  │  Color Scheme   │   curated data)  │   over 6 months  │
  │                 │                  │   per customer)  │
  │  Basic Skills   │  Skill Ecosystem │                  │
  │  (everyone can  │  (configured +   │  Workflow Lock-in│
  │   build VAT     │   calibrated for │  (10+ skills     │
  │   filing)       │   Chinese tax)   │   chained into   │
  │                 │                  │   custom flow)   │
  └─────────────────┴──────────────────┴──────────────────┘
```

**Three moat layers:**

1. **Knowledge moat** (KG): 514K curated Chinese tax law nodes. Competitor needs 6-12 months to replicate. But this is a **depreciating asset** — must keep feeding new regulations.

2. **Skill ecosystem moat** (Marketplace): Network effects. More skills → more scenarios covered → more customers → more skill developers → more skills. Classic marketplace flywheel.

3. **Trust moat** (Agent track record): Non-portable. "林税安 has served Tencent for 6 months with 98.2% accuracy" cannot be copied. This is the **strongest moat** — it grows with time and usage.

---

## 7. Migration Plan (Current → Target)

### Phase 1: Split (2 weeks)

| Action | From | To |
|--------|------|-----|
| KG Explorer pages | web/src/app/expert/* | Standalone app OR internal-only route |
| KG API proxy | Direct HTTP to Tailscale IP | CF Worker proxy (HTTPS) |
| Agent data | Hardcoded in TSX files | agents.json config file |
| Skill data | Hardcoded in skills/page.tsx | skills.json + API endpoint |

### Phase 2: Real Backend (4 weeks)

| Action | Details |
|--------|---------|
| Agent Runtime API | FastAPI/Hono: CRUD agents, task assignment, metrics tracking |
| Skill Registry API | CF Workers + D1: skill catalog, install/uninstall, usage tracking |
| Task Queue | PostgreSQL/D1: real task CRUD, status transitions, assignment |
| Auth | JWT with role claim (customer/expert/admin) |

### Phase 3: First Customer (4 weeks)

| Action | Details |
|--------|---------|
| Scope: 3 scenarios | VAT filing + bookkeeping entries + basic compliance check |
| KG validation | Top 1000 KU nodes manually verified for 3 scenarios |
| Agent calibration | 1 agent (林税安) serving 1 real client with human oversight |
| Feedback loop | Agent answer → customer accept/reject → accuracy tracking |

### Phase 4: Marketplace (8 weeks)

| Action | Details |
|--------|---------|
| Skill packaging | Define skill manifest format (input/output/KG deps/pricing) |
| Install/uninstall | Agent-level skill management with dependency resolution |
| Usage metering | Per-use tracking for premium skills |
| Billing integration | Stripe/WeChat Pay for skill marketplace transactions |

---

## 8. Tech Stack (Optimized)

| Layer | Current | Target | Rationale |
|-------|---------|--------|-----------|
| Frontend | Next.js 16 static export | Next.js 16 SSR (CF Workers) | Need API routes for auth + proxy |
| Frontend deploy | CF Pages | CF Pages + CF Workers | Workers for BFF/proxy |
| Agent API | Mock (useState) | Hono on CF Workers + D1 | Zero-VPS, edge-first |
| KG API | FastAPI on VPS | FastAPI on VPS (unchanged) | KuzuDB requires VPS |
| KG Proxy | None (direct HTTP) | CF Worker proxy | Solves mixed content + auth |
| Skill API | Mock (useState) | Hono on CF Workers + D1 | Same pattern as OpenClaw Foundry |
| Auth | None | JWT (CF Workers KV) | Minimal, role-based |
| Task Queue | None | D1 + Durable Objects | Persistent, edge-native |

---

## 9. Key Architecture Decisions (ADR)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-V2-01 | Split into 2 systems | Eliminate complection between internal tool and product |
| ADR-V2-02 | Agent identity = product feature | Trust anchor for Chinese B2B market, not ceremony |
| ADR-V2-03 | Skill marketplace = revenue engine | Plugin model creates lock-in + recurring revenue |
| ADR-V2-04 | KG invisible to customer | Value shows through agent accuracy, not graph visualization |
| ADR-V2-05 | CF Worker proxy for KG | Solves HTTPS/HTTP mixed content + adds auth layer |
| ADR-V2-06 | Zero mock data in product | Every number from API or shows loading state |
| ADR-V2-07 | SSR over static export | Need server-side auth + API proxy |
| ADR-V2-08 | Agent slots as pricing tier | More agents = more capacity = natural upgrade path |
| ADR-V2-09 | 70/30 revenue share for marketplace | Standard SaaS marketplace split |
| ADR-V2-10 | KuzuDB migration within 6 months | Archived dependency is time bomb |

---

## 10. What Changes from v1 Architecture

| Aspect | v1 (Current) | v2 (Target) |
|--------|-------------|-------------|
| App count | 1 app (41 pages, mock + real) | 2 systems (product + internal tool) |
| Product pages | 41 (80% mock) | ~12 (all real API) |
| Agent identity | TSX hardcoded, ceremonial | JSON config, trust anchor with metrics |
| Skill store | Mock install button | Real marketplace with pricing tiers |
| KG visibility | Expert pages in product | Invisible to customer, internal tool only |
| Data source | useState mock | Real API (CF Workers + D1 + KG API) |
| Deploy model | Static export only | SSR + Workers (edge-native) |
| Revenue model | SaaS subscription only | SaaS base + skill marketplace + agent slots |
| Moat | None (demo has no moat) | Trust record + skill ecosystem + KG |

---

Maurice | maurice_wen@proton.me
