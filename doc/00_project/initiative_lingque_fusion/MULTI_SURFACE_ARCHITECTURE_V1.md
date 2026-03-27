# Lingque Fusion Multi-Surface Architecture v1.0

> Swarm consensus from 4 advisors (Drucker/Jobs/Hickey/Hara) on 2026-03-27.
> Decision: 4 proposed surfaces → 2 deployed apps + 2 deferred rendering variants.

---

## 1. Problem Restatement

The original proposal was 4 independent surfaces:

| # | Surface | Target User | Status |
|---|---------|-------------|--------|
| S1 | PC Desktop (客户工作台) | Customer (Boss/CFO) | Built (10 pages) |
| S2 | Expert Workbench (专家工作台) | Internal expert | Legacy D3.js |
| S3 | Ops Admin (运营后台) | Platform operator | Not built |
| S4 | Mobile App (移动客户端) | Customer (mobile) | Not built |

**Swarm verdict: 4 surfaces is a complection.** The real structure is:

- **2 information needs**: Customer (delegate work) vs Internal (ensure system correctness)
- **2 rendering variants**: Desktop vs Mobile (same concern, different density)

S2 and S3 serve the same user (internal team) with different depth levels — they belong in one app.
S4 is S1 rendered differently — it's a PWA / WeChat notification layer, not a separate app.

---

## 2. Target Architecture: 2 Apps, 1 Monorepo

```
lingque-fusion/
├── packages/                          # Shared code
│   ├── ui/                            # Design components (buttons, cards, layouts)
│   ├── api-client/                    # Type-safe API client (3 backend subsystems)
│   ├── auth/                          # JWT verification + RBAC middleware
│   └── types/                         # Shared domain types (Agent, Task, Client)
│
├── apps/
│   ├── office/                        # Surface A: Customer-facing (PC + PWA)
│   │   └── src/app/
│   │       ├── page.tsx               # Dashboard
│   │       ├── ai-team/              # Team list + Agent Workstation
│   │       ├── tax/                   # Intelligent Tax Filing
│   │       ├── clients/              # Client Center
│   │       ├── compliance/           # Compliance Dashboard
│   │       ├── audit/                # Audit Workbench
│   │       ├── reports/              # Financial Reporting
│   │       ├── skills/               # Skill Store (OpenClaw)
│   │       └── settings/             # System Settings
│   │
│   └── internal/                      # Surface B: Platform-internal
│       └── src/app/
│           ├── (ops)/                 # Route group: Operations
│           │   ├── customers/         # Multi-tenant customer health
│           │   ├── agents/            # Agent performance metrics
│           │   ├── billing/           # Subscription & billing
│           │   └── alerts/            # System alerts & incidents
│           ├── (expert)/              # Route group: Expert Tools
│           │   ├── kg-explorer/       # Knowledge Graph visualization (D3.js)
│           │   ├── reasoning/         # Agent reasoning chain inspector
│           │   ├── rules/             # Compliance rule debugger
│           │   └── data-quality/      # KG data quality audit
│           └── (shared)/              # Route group: Shared
│               ├── login/
│               └── settings/
│
└── [backend subsystems unchanged]
```

### Why 2, Not 4

| Principle | Application |
|-----------|------------|
| Architecture boundaries follow data permissions, not UI complexity | Customer sees own data; Internal sees all data. That's the real boundary |
| Expert + Ops serve the same user at different depths | Both are "the team running the platform" — separate by Tab, not by App |
| Mobile is a rendering variant, not a new concern | Same information need (delegate work), different density. PWA + WeChat first |
| 1-person team can maintain 2 apps, not 4 | Interface Inflation kills products — attention dilution across surfaces |

---

## 3. Surface Definitions

### Surface A: Office (客户工作台)

**User**: Accounting firm boss, CFO, finance director
**Metaphor**: Walking into a virtual office where 7 AI employees are working
**Information density**: Medium (chat + dashboard + approvals)
**Interaction mode**: Delegative ("help me do X")
**Data permission**: Own company's agents, tasks, workflows, named KG queries only

**Design language**: Digital Atelier
- Heritage Blue `#003A70` as authority color
- Prestige Gold `#C5913E` as accent
- Warm Cream `#F9F9F7` as surface
- Generous whitespace, low density — bosses need confidence, not data

**Mobile strategy** (Phase 6+):
- PWA manifest on existing Next.js app (responsive breakpoints)
- WeChat Service Account template messages for push notifications
- H5 approval page (reuse existing components) for urgent decisions
- Native app only after validating mobile usage patterns with real customers

**Mobile scope** (only 3 functions):
1. Approve/Reject workflows (single-screen, thumb-reachable)
2. Exception awareness (filtered alerts, not all notifications)
3. Quick chat with AI team (one question, one answer)

### Surface B: Internal (内部控制台)

**User**: Platform operator (you), internal experts, future ops team
**Information density**: High to extreme
**Interaction mode**: Monitoring ("what's broken") + Exploration ("why does this edge exist")
**Data permission**: All data, all customers, raw KG access (role-gated)

**Two route groups within one app**:

| Route Group | Role Required | Functions |
|-------------|--------------|-----------|
| `(ops)` | `admin` | Customer health matrix, agent performance, billing, system alerts, skill curation |
| `(expert)` | `expert` or `admin` | KG Explorer (D3.js), reasoning chain viewer, compliance rule debugger, data quality |
| `(shared)` | any internal | Login, personal settings |

**Design language**: Bloomberg Ops (ops) + Terminal Academia (expert)
- Dark sidebar, light content area
- High density tables and metrics
- Status colors (green/yellow/red) amplified
- KG Explorer: dark background, force-directed graph, monospace labels
- No decorative elements — information density is the design

---

## 4. Shared Design Token System

All surfaces share one token layer; each surface applies its own visual language on top.

### Non-negotiable brand elements (all surfaces):

| Element | Rule | Rationale |
|---------|------|-----------|
| Heritage Blue `#003A70` | Authority color, used sparingly for most important info | If it's everywhere, it means nothing |
| Financial numbers in monospace | Every amount, tax figure, date uses monospace font | Signals precision; enables column alignment |
| Unified alert colors | Green/Yellow/Red identical across all surfaces | User learns meaning once, applies everywhere |
| No decorative animations | Motion only for: "processing" indicator or "state changed" | Finance users need trust, not delight |
| CJK typography: `word-break: keep-all` | Anti-orphan rule for all Chinese text | Prevents single-character line wrapping |

### Token structure:

```
packages/ui/tokens/
├── colors.ts          # Shared palette (primary, secondary, semantic, dept colors)
├── typography.ts      # Font stacks, sizes, line-heights
├── spacing.ts         # 4px base unit system
├── shadows.ts         # Elevation system
└── surfaces/
    ├── office.ts      # Digital Atelier overrides (larger spacing, lower density)
    └── internal.ts    # Bloomberg Ops overrides (compact spacing, higher density)
```

---

## 5. API Architecture: No Gateway, Direct Connect

```
┌──────────────┐     ┌──────────────┐
│  apps/office │     │apps/internal │
└──────┬───────┘     └──────┬───────┘
       │                     │
       │   packages/api-client (type-safe, JWT attached)
       │                     │
   ┌───┴─────────────────────┴───┐
   │         REST API Layer       │
   │   (JSON envelopes, JWT auth) │
   ├─────────┬─────────┬─────────┤
   │         │         │         │
   ▼         ▼         ▼         │
Agent      KG        OpenClaw    │
Runtime    Semantic   Skills     │
(FastAPI   Layer      API        │
+PG)       (FastAPI   (CF       │
:8400      +Kuzu     Workers    │
           +Lance)    +D1)      │
           :8400/kg             │
└─────────────────────────────────┘
  Each subsystem: independent deploy,
  independent auth, independent failure
```

### Why no API Gateway:

1. Gateway complects 3 independent failure domains — Agent Runtime crash shouldn't block Skill Store browsing
2. Backend already returns structured JSON envelopes — it IS the BFF
3. Auth is handled by JWT middleware in frontend, not a runtime proxy
4. Gateway only justified for rate limiting / 3rd-party API access (Phase N)

### KG Access 3-Tier Model:

| Tier | Endpoint | Role | Use Case |
|------|----------|------|----------|
| T1 Named Queries | `/api/kg/query/{name}` | customer+ | Parameterized, safe, returns structured results |
| T2 Explore Templates | `/api/kg/explore` | expert+ | 10-15 graph traversal templates (expand_node, trace_path, subgraph, filter_by_type) |
| T3 Raw Cypher | `/api/kg/admin/raw` | admin only | Ad-hoc queries with cost limits. YAGNI until proven needed |

---

## 6. Auth & RBAC

Single JWT, single role claim. No OAuth provider, no authorization server.

```typescript
interface JWTPayload {
  sub: string                              // user id
  role: 'customer' | 'expert' | 'admin'   // single role
  org_id: string                           // which company (customer) or 'platform' (internal)
}
```

| Role | apps/office | apps/internal (ops) | apps/internal (expert) | KG T1 | KG T2 | KG T3 |
|------|-------------|--------------------|-----------------------|-------|-------|-------|
| customer | Full access | 403 | 403 | Yes | No | No |
| expert | Read-only (debug) | 403 | Full access | Yes | Yes | No |
| admin | Full access | Full access | Full access | Yes | Yes | Yes |

Frontend middleware enforces route-level access. Backend enforces data-level access (row-level security on org_id for customers).

---

## 7. Build Priority (Drucker Assessment)

| Priority | Surface | Rationale | Timeline |
|----------|---------|-----------|----------|
| P0 | apps/office iterate | Already built. Next: add accountability layer (who did what, error notifications) | Now |
| P1 | apps/internal (ops) | "Management requires visibility" — can't scale without seeing customer health | Next sprint |
| P2 | apps/internal (expert) | Migrate legacy D3.js into internal app, add reasoning chain viewer | After P1 |
| P3 | Mobile PWA + WeChat | Validate mobile usage with real customers first, then decide native vs PWA | Phase 6+ |

### What to NOT build:

- Separate Expert Workbench app (merge into internal)
- Separate Mobile app (use PWA + WeChat Service Account)
- API Gateway (direct connect to 3 subsystems)
- OAuth authorization server (single JWT is sufficient)

---

## 8. Migration Path from Current State

### Step 1: Restructure to Monorepo

```bash
# Current
web/src/app/          # 10 customer pages (already built)
src/web/              # Legacy D3.js visualizations

# Target
apps/office/src/app/  # Move existing 10 pages here
apps/internal/src/app/ # New: ops + expert route groups
packages/ui/          # Extract shared components
packages/api-client/  # New: type-safe API client
packages/auth/        # New: JWT + RBAC middleware
```

### Step 2: Build Internal App (P1)

Start with 3 ops pages:
1. `/customers` — Multi-tenant health matrix (client list + status + last activity)
2. `/agents` — Agent performance dashboard (task throughput, error rate, avg confidence)
3. `/alerts` — System health alerts (KG staleness, agent failures, billing events)

### Step 3: Migrate Expert Tools (P2)

Move legacy D3.js KG explorer into `apps/internal/(expert)/kg-explorer/`:
- Wrap existing D3.js visualization in React component
- Connect to KG Semantic Layer T2 explore endpoints
- Add reasoning chain viewer (new page)

### Step 4: Mobile Surface (P3)

1. Add PWA manifest to apps/office
2. Add responsive breakpoints for mobile viewports
3. Build WeChat Service Account integration for push notifications
4. Build H5 approval page (responsive, thumb-friendly)
5. Measure mobile usage for 3 months before considering native app

---

## ADR Log

| # | Decision | Chosen | Rejected | Rationale |
|---|----------|--------|----------|-----------|
| ADR-S1 | Surface count | 2 apps | 4 apps | Data permission boundary = architecture boundary. Expert + Ops = same user, different depth |
| ADR-S2 | Mobile strategy | PWA + WeChat | Native app | 1-person team cannot maintain iOS + Android. Validate demand first |
| ADR-S3 | Code organization | Monorepo (turborepo) | Polyrepo | Shared packages eliminate duplication; apps stay isolated |
| ADR-S4 | API topology | Direct connect, no gateway | Unified gateway | Avoid complecting failure domains. Gateway adds latency + single point of failure |
| ADR-S5 | Auth model | Single JWT + role claim | OAuth + authorization server | 3 roles don't justify the complexity. Upgrade when selling to 100+ enterprises |
| ADR-S6 | KG access | 3-tier (named → explore → raw) | Open Cypher for all | Security + simplicity. 15 explore templates cover 95% of expert needs |
| ADR-S7 | Expert Workbench | Route group in internal app | Standalone app | Same user group, same data permissions. Tab separation, not app separation |

---

## Appendix: Swarm Advisor Contributions

| Advisor | Key Insight | Impact on Architecture |
|---------|------------|----------------------|
| Drucker | "3 types of users: paying customer, internal expert, operations team. S3 is most urgent — no visibility = no scaling" | Priority order: P0 office iterate → P1 ops → P2 expert → P3 mobile |
| Jobs | "One Design Token system, four Visual Languages. Mobile: only approve/exceptions/quick-chat. Brand consistency = terminology + alert colors, not visual style" | Token architecture, mobile scope definition, 5 brand non-negotiables |
| Hickey | "4 surfaces → 3 concerns + 1 rendering variant → 2 apps. Architecture boundaries follow data permissions. No gateway — avoid complecting failure domains" | 2-app monorepo, direct API connect, 3-tier KG access, JWT RBAC |
| Hara | "一个人的团队只负担得起一张客户的脸、一张自己的脸. Expert Workbench has no irreplaceable function — merge into Ops tab" | Surface elimination, PWA over native, ruthless scope reduction |

---

Maurice | maurice_wen@proton.me
