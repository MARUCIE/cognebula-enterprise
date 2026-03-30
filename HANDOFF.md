# HANDOFF.md -- CogNebula / Lingque Desktop

> Last updated: 2026-03-30T08:30Z

## Session 21 — KG Search + RAG Usability Fix

### Problem Diagnosis
System audit revealed 5 critical issues:
1. **Search BROKEN**: LanceDB only indexed 37K/540K nodes (7%), Gemini 429 → placeholder vectors → random results
2. **RAG Chat BROKEN**: Gemini 429 on both embedding AND generation → empty/error responses
3. **Node content 38% empty**: LegalDocument(54K) all empty, KnowledgeUnit(152K) titles only, TaxIncentive(109) no fullText
4. **Edge noise**: MAPS_TO_ACCOUNT over-connected (VAT → 43 accounting subjects including insurance accounts)
5. **LanceDB coverage**: Only 6 legacy tables indexed (FAQEntry, CPAKnowledge, MindmapNode, etc.)

### Fixes Applied (commit d74532e)
1. **New `_cypher_text_search()`**: CONTAINS-based search across all 21 v4.1 + 2 legacy tables
   - Fallback Chinese bigram splitting ("上海社保" → "上海" + "社保" separate searches)
   - Relevance scoring: exact name=100, name contains=80, title=60, fullText=40
2. **Search endpoint rewrite**: Cypher text primary, LanceDB vector as optional boost (when Gemini works)
3. **RAG retrieval rewrite**: text search + keyword extraction + 7 structured domain queries
4. **Structured fallback**: When Gemini 429, format context_parts directly (not empty error)
5. **Column name fixes**: SocialInsuranceRule.regionId, InvoiceRule.condition, IndustryBenchmark.ratioName

### Validation Results
| Query | Structured Data | Key Tables |
|-------|----------------|------------|
| 增值税税率 | 30 lines | TaxType (0-13% tiered monthly) |
| 社保缴纳 | 30 lines | SocialInsuranceRule (7 insurance types, employer/employee rates) |
| 税会差异 | 41 lines | TaxAccountingGap (timing/permanent gaps) |
| 发票合规 | 26 lines | InvoiceRule (certification, deduction rules) |
| Graph TaxType/增值税 | 100 neighbors | MAPS_TO_ACCOUNT, FT_INCENTIVE_TAX, etc. |

### Remaining TODOs (not blockers)
1. **Content enrichment**: TaxIncentive(109), ComplianceRule(84) need fullText (names exist, bodies empty)
2. **Edge cleanup**: MAPS_TO_ACCOUNT noise (43 irrelevant accounting subjects for VAT)
3. **Permanent tunnel**: Quick tunnel URL is temporary
4. **Frontend visual audit**: 3-round polish not yet done
5. **LanceDB rebuild**: After content enrichment, re-index all tables with real Gemini embeddings

---

## Session 20 — KG v4.1 Migration Phase 1-3

### Phase 1: Data Migration DONE (+26,611 nodes)
- Fixed migrate-table API: removed 500-char truncation, added column alias for KuzuDB
- Added 19 missing columns to target tables via ALTER TABLE
- Migrated 34 source tables → 12 target tables (scripts/migrate_v4.1.py)
- Key additions: Classification +25,085, RiskIndicator +463, TaxRate +160, FilingForm +133
- Total nodes: 513,893 → 540,504

### Phase 3a: Edge Tables Created (13 new + 4 existed)
- Created 17 v4.1 edge tables (PARENT_CLAUSE, PARENT_SUBJECT, STACKS_WITH, etc.)

### Phase 2: Seed Data IN PROGRESS
- 3 agents generating: TaxAccountingGap(50+), SocialInsuranceRule(120+), InvoiceRule(40), IndustryBenchmark(30)
- Ingest script: scripts/ingest_seed_v4.1.py

### Migration Progress
```
Phase 0: Schema      DONE
Phase 1: Data 185K   DONE (+26,611 new, rest already existed)
Phase 2: Seed data   DONE (+273 records: 50 Gap + 138 Insurance + 40 Invoice + 45 Benchmark)
Phase 3a: Edge DDL   DONE (17 tables created)
Phase 3b: Seed edges DONE (+213: 123 Insurance + 40 Invoice + 50 Gap)
Phase 3c: AI edges   PENDING (PARENT_CLAUSE, STACKS_WITH, HAS_RATE, etc. — need semantic extraction)
Phase 4a: Frontend   DONE (21 v4.1 types only in LAYER_GROUPS, NODE_COLORS, NODE_ZH)
Phase 4b: DROP legacy DEFERRED (39 tables, 184K nodes — keep until full verification)
Phase 4c: CF deploy  DONE (v4.1 frontend deployed, CF Worker proxy deployed but 1003 on bare IP)
```

### Phase 3c Edge Enrichment DONE (+2,547 edges)
- 15/17 edge tables populated via keyword matching + domain rule inference
- Remaining 2: PARENT_CLAUSE (flat clauseNumbers), RELATED_PARTY (needs enterprise data)

### Production Deployment DONE
- CF Tunnel: `cloudflared tunnel --url http://localhost:8400` on VPS (quick tunnel, temporary URL)
- Current URL: `https://opportunity-pentium-blessed-notes.trycloudflare.com`
- Frontend deployed to CF Pages with tunnel URL
- 4 commits: fa8dc3d, 3246b25, d0e2ea2

### Blockers / TODOs
1. **Permanent tunnel**: Quick tunnel URL changes on restart. Fix: `cloudflared tunnel login` (interactive OAuth, user must run on VPS), then create named tunnel → `kg-api.cloudcc.io`
2. **cloudflared systemd**: Install as service so it auto-restarts on VPS reboot: `cloudflared service install`
3. **2 empty edge tables**: PARENT_CLAUSE (need clauseLevel data enrichment), RELATED_PARTY (need real enterprise data)
4. **Frontend visual audit**: 3-round polish not yet done on v4.1 sidebar + 3D graph

### API Fixes Applied to VPS
1. kg-api-server.py line 707: `str(val)[:500]` → `str(val)` (no truncation)
2. migrate-table: added `AS col_i` aliases to prevent KuzuDB duplicate column error
3. execute-ddl: added "CALL" to ALLOWED_PREFIXES

VPS: kg@100.75.77.112, KuzuDB: /home/kg/cognebula-enterprise/data/finance-tax-graph

---

## Session 19 — KG Ontology v4.1 + 29-Skill Finance Tax Team + 3D Graph

### DONE: Frontend + Backend + Ontology + Skills
- All 6 Expert pages connected to real KG API (3D graph, Q&A, data quality, legal browser)
- Backend: /graph truncation 300->10000, content_coverage, Gemini model fix
- Data: 76 ComplianceRuleV2 fullText re-ingested
- Ontology v4.1: 21 nodes + 52 edges (DDL: schemas/ontology_v4.1.cypher)
- 29 Skills + 284 Playbooks created, 9 rounds audited, registered in skill-groups.json v6.0.0
- Phase 0 Schema: 3 new tables + 35 ALTER attributes on VPS

---

## Session 18 Summary — System A PC Redesign + 3-Round Visual Audit + Cleanup

### Phase 1: System A (CogNebula) PC Desktop Redesign
- Created `cognebula-theme.ts` — shared dark theme tokens (CN.* constants)
- Rewrote KG Explorer: full-width 3-panel layout, collapsible sidebar, graph canvas takes all remaining width
- Rewrote Data Quality: 6-KPI strip + 2-column (bar chart + quality breakdown table)
- Rewrote Reasoning Inspector: left panel chain list + right vertical pipeline flowchart with confidence bars
- Rewrote Rules Debugger: filter toggles + expandable row detail with rule logic code block
- Created System Bridge page: split-view A|DataFlow|B with SVG arrows, unified status bar
- Updated expert layout: +Bridge nav, width:100% fix, English nav labels

### Phase 2: 3-Round Visual Audit (12 pages)
- Round 1: Screenshotted all 12 pages, found 8 issues (1 P0, 3 P1, 4 P2)
- Round 2: Fixed P0 (quality.toFixed crash), P1 (TopBar trailing slash, node type truncation), P2 (bridge width, reasoning border, layout leak)
- Round 3: Verified all fixes, deployed clean build

### Phase 3: Legacy Page Cleanup
- Removed 8 legacy pages: /tax, /ai-team/*, /compliance, /audit, /ops/* (-5,559 lines)
- Updated TopBar: removed old pageTitles, /ops/alerts → /workbench/exceptions, search → /workbench/agents
- Build: 49 → 27 pages, 0 errors

### Phase 4: CI/CD
- Created `.github/workflows/deploy.yml` — auto-deploy on push to main
- CLOUDFLARE_ACCOUNT_ID secret set
- CLOUDFLARE_API_TOKEN pending (user must create at CF dashboard)

### Commits
```
3f67901  feat: System A (CogNebula) PC desktop redesign + System Bridge
a65112f  fix: 3-round visual audit — crash fix + TopBar titles + layout polish
912bb35  chore: remove 8 legacy pages + clean TopBar references
ac5665c  ci: add GitHub Actions auto-deploy to CF Pages
```

### Deployment
- URL: https://lingque-desktop.pages.dev/
- System A: /expert/ (6 pages, dark CogNebula theme)
- System B: /workbench/ (6 pages, Heritage Monolith light theme)
- Build: 27 pages, 0 errors

### Next Steps (Priority Order)
1. **CLOUDFLARE_API_TOKEN**: Create at dash.cloudflare.com/profile/api-tokens (Pages:Edit), set via `gh secret set`
2. **P1 core engine**: task-definitions.yaml + dependency-engine.ts + calendar-engine.ts
3. **First customer**: Find 1 real accounting firm for pilot (3 scenarios)

---

## Session 17 Summary — Deep Design + Stitch Pipeline + 6 Workbench Views + System Split

### Phase 1: Deep Design Document
- `NEXT_GEN_WORKBENCH_DESIGN.md` (EN, agent-readable) + `-zh.html` (McKinsey Blue)
- Core thesis: bookkeeping = factory production line. 41 tasks x 999 enterprises = 40,959 units/month
- Calendar-driven state machine, 7 named agents, batch engine, dual dependency types, 79 Skills

### Phase 2: Stitch Design Pipeline
- Project: `projects/7648290641270673368`, Design System: Heritage Monolith
- 12 screens exported (HTML + PNG) to `design/stitch-export/stitch/`

### Phase 3: 6 Workbench Views Implemented
| Route | View | Key Features |
|-------|------|-------------|
| `/workbench` | 月度看板 | 4-column kanban (W1-W4), KPI strip, 41 task cards |
| `/workbench/batch` | 批量操作台 | "一键处理 N 家" CTA, blocked enterprises table |
| `/workbench/agents` | 数字员工 | 7 agents, SVG trust circles, skill inventory |
| `/workbench/calendar` | 日历视图 | Monthly grid, W1-W4 bars, day-15 deadline marker |
| `/workbench/exceptions` | 异常中心 | 12 exceptions, 4 filter tabs, detail panel |
| `/workbench/dependencies` | 依赖图 | Cytoscape.js DAG, 41 nodes, 44 edges |

### Phase 4: Architecture v2 System Split
- Removed Expert section (System A) from product sidebar
- New sidebar: L1 代账工作台 / AI 引擎 / 业务 (3 groups, 9 items)
- Root `/` redirects to `/workbench/`
- Heritage Monolith CSS: zero-radius, zero-shadow, gradient CTA, ghost border

### Deployment
- Method: `wrangler pages deploy web/out --project-name=lingque-desktop` (NOT git-connected)
- URL: https://lingque-desktop.pages.dev/workbench/
- Build: 47/47 pages, 0 errors

### Commits
```
4909364  feat: next-gen workbench deep design + Stitch prototypes + kanban page
527b7ee  feat: agent team + calendar view workbench pages
85a2a6d  feat: exception center + batch control workbench pages
7e543e9  feat: dependency graph — 41-task DAG with Cytoscape.js
0463380  fix: add trailingSlash for CF Pages route resolution
6dabb4f  fix: split sidebar per architecture v2 — remove Expert (System A)
```

### Next Steps (Priority Order)
1. **P1 core engine**: task-definitions.yaml + dependency-engine.ts + calendar-engine.ts
2. **Connect CF Pages to Git**: Auto-deploy (root: `web`, build: `npm run build`, output: `out`)
3. **Remove old mock pages**: /tax, /ai-team, /compliance, /audit, /ops
4. **First customer**: Find 1 real accounting firm for pilot (3 scenarios)

---

## Session 16 Summary — Architecture Redesign + Expert Workbench + 41-Task Model

### Architecture Redesign (Swarm 3-Round Review)

**Swarm verdict: RETHINK** (Drucker/Hickey/Meadows unanimous)
- 41-page single app mixes mock demo + real KG tool = complection
- System goal drifted to "build complete system" instead of "serve customer"
- User decision: Split into 2 independent systems, but Agent + Skill = moat (not expendable)

**Result**: OPTIMIZED_ARCHITECTURE_V2.md + .html (McKinsey Blue)
- System A: CogNebula Platform (internal KG infrastructure)
- System B: Lingque Product (4 layers: Workbench / Agent / Skill Store / KG Engine invisible)
- Revenue: SaaS base + Agent slots (3/5/7) + Skill marketplace (70/30 split)

### Expert Workbench (migrated from VPS)

4 pages migrated from VPS single-file HTML (Cytoscape.js) to React:
- `/expert/kg` — KG Explorer with real API (514K nodes, 1.1M edges)
- `/expert/reasoning` — Agent reasoning chain inspector
- `/expert/rules` — Compliance rule debugger
- `/expert/data-quality` — Real-time KG quality metrics

Architecture decision: Expert pages will be separated from product (internal tool only).
Unified to Office light theme (only Cytoscape canvas stays dark).

### TopBar Features

- Global search: cross-entity (clients/reports/agents) with grouped dropdown
- Notification dismiss: "处理" removes + navigates, "已读" removes, badge updates reactively

### 41-Task Accounting Workflow Discovery

Source: Competitor workbench HTML (16,709 lines), real accounting firm monthly workflow.

**4 Time Windows**:
- W1 采集期 (1-5): 11 tasks — data collection + initial bookkeeping
- W2 征期 (6-15): 14 tasks — tax filing (LEGAL DEADLINE, 15th)
- W3 质检期 (16-24): 10 tasks — quality check + risk reports
- W4 准备期 (25-31): 7 tasks — next month prep + client notifications

**Key insight**: Each task has `enterprises` field (batch size: 23-999). This is the batch automation foundation. Tasks have strict dependency chains (bookkeeping → quality check → adjustment → close → file → feedback).

### Commits (this session)
```
717aeb5  feat: TopBar global search + notification dismiss
9b8f5af  feat: Expert Workbench — KG Explorer + 3 diagnostic pages
8322b12  fix: unify Expert pages to Office light theme
```

### Production
- URL: https://lingque-desktop.pages.dev
- Pages: 41/41, 0 build errors
- KG API: 100.75.77.112:8400 (Tailscale, mixed content issue pending CF Worker proxy)

### Next Steps (Priority Order)

1. **Deep design**: Next-gen accounting workbench based on 41-task model + OpenClaw proactive Agent + batch automation
   - Task queue organized by 4 time windows
   - Agent assignment per task type (mapping to L2 digital employees)
   - Batch operation: "一键处理 999 家企业的银行采集" pattern
   - Dependency graph: auto-trigger next task when upstream completes
   - OpenClaw Skills: each of 41 tasks maps to 1+ Skills

2. **System split execution**: Phase 1 from architecture v2
   - KG Explorer → internal tool
   - Agent data → agents.json config
   - CF Worker proxy for KG API

3. **First customer**: Find 1 real accounting firm for pilot (3 scenarios)

---

## Session 15 Summary — KG Queue 1-2-3 (flk + 12366 + Edge Engine)

### Task 1: flk 补全 — DONE
- **flk.npc.gov.cn API reverse-engineered**: `POST /law-search/search/list`, Ruoyi framework pagination (`pageNum`/`pageSize`)
- **28 flfgCodeId values discovered** (100-350), total 29,196 items across all categories
- **API 500-page hard limit**: max 10,000 items per query, `sortTr` ignored
- **Strategy**: category-based collection (per flfgCodeId), bypasses limit for codes < 10K items
- **Result**: 2,568 → **11,234 unique law IDs** (4.4x increase), 10,099 new IDs pending detail scan
- **Gotcha**: code 230 (地方法规) has 22,137 items but only 10,000 accessible — no workaround via sort/date filters
- **Browser crash recovery**: Chromium leaks after ~450 pages; added auto-restart every 250 API calls + crash recovery

### Task 2: 12366 补全 — DONE (was already complete)
- 5,297 raw items, 4,859 with content >= 100 chars
- All 4,859 ingestible items already in KG (previous session). 438 items below quality threshold.
- KU coverage: 36.0%

### Task 3: Edge Engine — DONE (+107 SUPERSEDES)
- **Markdown stripping fix**: Poe API wraps JSON in ` ```json...``` `, causing `json.loads()` failure. Added `_strip_markdown()` regex
- **SUPERSEDES**: +107 edges discovered (LLM-powered, 14 tax keywords x top-100 docs)
- **REFERENCES_CLAUSE**: COPY failed (missing PKs), row-by-row fallback found 0 valid edges (LegalClause→LawOrRegulation type mismatch)
- **KG State**: 546,076 nodes / 1,141,894 edges / density 2.091

### Scripts Modified
- `scripts/flk_collect_ids.py` — complete rewrite: DOM parsing → search list API with category-based pagination
- `scripts/generate_edges_ai.py` — added `_strip_markdown()`, GEMINI_API_KEY → POE_API_KEY, COPY fallback to row-by-row

### Key API Gotchas Learned
1. **Ruoyi pagination params**: `pageNum`/`pageSize` (NOT `page`/`size`). Wrong names silently return page 1 data
2. **500-page hard limit**: Server returns empty beyond page 500 regardless of filters or sort
3. **WAF cookie requirement**: All `/law-search/` endpoints need browser context (direct HTTP returns HTML shell)
4. **Poe API markdown wrapping**: Gemini via Poe wraps JSON in code fences; must strip before parsing

### Pipeline Continuation (same session, extended)
1. ~~**flk detail scan**~~: DONE — 10,334 scanned, 8,981 fetched, 11,549 lines in flk_details.jsonl
2. ~~**flk content generation**~~: DONE — 4,107 items via Poe LLM (gemini-3.1-pro, 837/hr, 5h)
3. ~~**flk KG ingest**~~: DONE — Phase 1: +674 nodes, Phase 3: 6,299 items ingested (0 skip)
4. **Embedding build**: IN PROGRESS — 107,755 nodes (39K LR + 67K KU + 1K FAQ), Mac-local build with checkpoint resume
   - VPS Gemini key rate-limited (403), using Mac openclaw key instead
   - Script: `src/build_kg_nodes_local.py`, checkpoint: `data/embed_checkpoint.json`
   - Fixed 3 mismatches: 768D (not 3072), table `kg_nodes` (not `finance_tax_embeddings`), includes KU nodes
   - After completion: `bash scripts/sync_lancedb_to_vps.sh` to deploy
5. **Edge Engine v2**: DONE — REFERENCES_CLAUSE: 0/494 (target IDs don't exist, stale data), KU_ABOUT_TAX: +29 edges
   - Total edges: 1,141,923

### KG Final State (Session 15)
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total nodes | 546,076 | 547,579 | +1,503 |
| Total edges | 1,141,787 | 1,141,894 | +107 |
| KU total | 183,952 | 185,455 | +1,503 |
| KU with content | 66,199 | 67,024 | +825 |
| flk IDs collected | 2,568 | 11,234 | +8,666 |
| Poe content generated | 2,192 | 6,299 | +4,107 |

---

## Session 14 Summary — Lingque Desktop Interactive Upgrade

### What was done

**1. Dead Button Elimination (68+ buttons)**
- Created ToastProvider + ToastButton system (2 client components)
- Converted all dead `<button>` to either `<Link>` (navigation) or `ToastButton` (action feedback)
- Fixed all `cursor:pointer` elements without handlers (evidence tiles, compliance cards, toggles)
- Swarm review (4-advisor: Jobs/Drucker/Hara/Hickey): PASS after 6 P0 fixes

**2. Skills Sheet Side Drawer (P2)**
- SkillCardWrapper client component: click skill card -> 380px drawer slides in
- Shows: name, rating, agents, 3 recent executions, stats, install button

**3. Full Mock API Layer (10 pages converted to interactive)**
- Skills: category filter + install state toggle
- Compliance: traffic light filter + company selection -> risk detail panel (3 companies)
- Reports: status filter tabs + batch approve (PendingCards disappear, KPI updates 42->0)
- Report Detail: approve button changes status + disables (ReportDetailClient boundary)
- Dashboard: approval tab toggle (pending <-> completed datasets)
- Settings: toggle switches + save/reset
- Audit: finding selection -> right panel updates (3 findings with detail data)
- Clients: status filter tabs (all/done/progress/review)
- AI Team Workstation: live chat input with mock AI responses (ChatInput component)

**4. Visual Review Pipeline**
- 11 pages screenshotted via Chrome DevTools MCP
- Fixed: TopBar title for dynamic routes (/clients/[id] -> "客户详情", /reports/[id] -> "报告详情")
- Fixed: notification href pointed to non-existent client -> changed to real client ID

### Commits (this session)
```
4c4453e  fix: eliminate all 68+ dead buttons with Toast system + navigation Links
ccc8c5d  fix: close remaining dead buttons from swarm P0 review
4270728  fix: close cursor:pointer dead spots (evidence tiles, cards, toggles)
9fb37fc  feat: add Skills Sheet side drawer (P2 from L2 design decision)
3ab0a82  fix: TopBar shows contextual titles for detail pages
0243337  feat: full mock API layer -- all interactions are real client-side state
e541f86  chore: trigger CF Pages rebuild
```

### Production
- URL: https://lingque-desktop.pages.dev
- GitHub: MARUCIE/cognebula-enterprise@e541f86 (master)
- Pages: 37/37, 0 build errors
- New components: Toast.tsx, ToastButton.tsx, SkillDrawer.tsx, ChatInput.tsx, ReportDetailClient.tsx

### Architecture
- All state is client-side (useState per page) -- compatible with output: "export" to CF Pages
- Server Components preserved for SSG pages (reports/[id] uses ReportDetailClient boundary)
- ToastProvider wraps entire app in layout.tsx
- No global store -- page-level isolation, gradual API upgrade path

### Verified interactions (local dev server)
- Reports "全部批准": PendingCards disappear, KPI 42->0, all badges turn green
- Skills category filter: "合规" shows 1 card, "全部" shows 6
- Skills install: button toggles, sidebar count (3)->(4)
- Dashboard tab switch: pending <-> completed rows
- Audit finding click: right panel updates with different detail data

### What's next
- Verify CF Pages production deployment reflects all interactive features
- TopBar search functionality (full-text search across mock data)
- Notification popover "处理" -> mark as handled + remove from list
