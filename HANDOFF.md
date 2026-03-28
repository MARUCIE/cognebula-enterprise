# HANDOFF.md -- CogNebula / Lingque Desktop

> Last updated: 2026-03-28T12:40Z

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

### Next Steps
1. **flk detail scan**: Run `flk_fast_scan.py` on 10,099 new IDs → `flk_details.jsonl`
2. **flk content generation**: Run Poe LLM summary for items without content
3. **flk KG ingest**: Push new nodes + edges to VPS KG
4. **Embedding refresh**: Re-embed all newly content-enriched nodes
5. **Edge Engine v2**: Fix REFERENCES_CLAUSE node type mismatch; expand to KU→KU edges

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
