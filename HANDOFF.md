# HANDOFF.md -- CogNebula Session 13 (KG Data Sprint)

> Last updated: 2026-03-28T00:30Z

## Session 13 Summary — KG Data Sprint

### LLM Backend Migration: Gemini → Poe API — DONE
- Google AI Studio at $232/$300 limit. All 9 batch scripts + VPS kg-api-server migrated to Poe API
- `scripts/llm_client.py`: unified adapter, old model names auto-mapped (gemini-2.5-flash-lite → gemini-3.1-flash-lite)
- VPS: `.env.kg-api` with POE_API_KEY, `_gemini_generate()` Poe-first + Gemini fallback
- Embedding stays on Google API (cheap, Poe doesn't support)

### KG API Port Discovery
- API was never down — runs on port **8400** (not 8766 from Docker Compose era)

### Data Ingest Results

| Task | Items | Status |
|------|-------|--------|
| flk content update (structure trees) | 310 / 318 | DONE |
| flk clause nodes (KnowledgeUnit) | +17,134 | DONE |
| HAS_CLAUSE edges (new rel type KU→KU) | +21,351 | DONE |
| LR shard re-ingest | 15,781 | DONE (no net new — overwrites) |
| LR content generation (Poe) | 22,042 / 22,044 | DONE |
| flk law summary generation (Poe) | 2,192 / 2,248 | DONE |
| LR + flk content ingest to DB | 24,234 | DONE (0 errors) |

### KG Final State

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Quality nodes | 344,356 | 361,490 | +17,134 |
| Total nodes | 528,942 | 546,076 | +17,134 |
| Total edges | 1,120,436 | 1,141,787 | +21,351 |
| HAS_CLAUSE | 0 | 21,351 | new |
| KU with content | 10,721 | 66,199 | +55,478 (6.2x) |
| Quality score | 100 | 100 | maintained |
| Gate | PASS | PASS | maintained |

### Key Gotchas Learned
1. **KuzuDB DDL API silent failure**: MATCH+CREATE returns "ok" even when MATCH finds 0 rows. Always verify with count queries
2. **Node ID format mismatch**: flk_npc nodes use `KU_flk_` + bbbs[:16], not raw bbbs. Check actual DB IDs before bulk operations
3. **KuzuDB strong typing**: Each edge type (REL TABLE) only connects predefined node types. Created `HAS_CLAUSE (KU→KU)` for new edges
4. **OFD reader renders as images**: flkofd.npc.gov.cn uses image rendering, not DOM text. Poe LLM summary is the pragmatic alternative

### Scripts Created
- `scripts/llm_client.py` — Poe API unified adapter (drop-in for all Gemini calls)
- `scripts/flk_content_ingest.py` — structure tree content update + clause extraction
- `scripts/flk_clauses_and_edges.py` — batch clause node + edge creation
- `scripts/flk_docx_extract.py` — OFD reader text extraction (abandoned: image rendering)

### Next Steps
1. **M3 L1 Depth**: remaining ~16K lr_cleanup nodes still without content (content < 50 chars after ingest)
2. **M3 L2 Breadth**: new sources (pbc.gov.cn, cctaa.cn, ASBE) per M3 strategy
3. **M3 L3 Edge Engine**: Gemini cross-reference scan for SUPERSEDES/CONFLICTS_WITH edges
4. **Embedding refresh**: re-embed 55K newly content-enriched nodes for vector search quality

---

## Session 12 Summary (Frontend — Audit Fixes + Polish)

### All Audit Fixes + 2 Rounds Polish — COMPLETE

| Milestone | Status | Commit |
|-----------|--------|--------|
| 10 customer pages (Stitch → Next.js) | DONE | e5d3875 |
| 3-round UI polish (CJK + fluid layout) | DONE | e5d3875 |
| Multi-surface architecture ADR (4→2 apps) | DONE | e5d3875 |
| 3 ops pages (Bloomberg density) | DONE | 86b7c22 |
| CF Pages deploy (lingque-desktop.pages.dev) | DONE | 33cb6ad |
| UX audit (4-advisor swarm) | DONE | df7d006 → ae911c8 |
| McKinsey Skill gotchas #12 #13 | DONE | ae911c8 |
| Audit TOP 10 fixes (10/10) | DONE | 7e08b4d + 7876e5a |
| Round 2+3 polish | DONE | 505d1d0 |

### Audit-Driven TOP 10 Fixes

| # | Fix | Status | Commit |
|---|-----|--------|--------|
| 1 | Dashboard approval table → above activity feed | DONE | 7876e5a |
| 2 | Unify AI role name → "AI 专员" (7 files) | DONE | 7876e5a |
| 3 | Reports status labels Chinese (AI生成/已人工复核/需关注) | DONE | 7876e5a |
| 4 | Ops customers English KPI labels → Chinese | DONE | 7e08b4d |
| 5 | Error messages dev-speak → actionable Chinese | DONE | 7876e5a |
| 6 | Alerts default view → "待处理" tab | DONE | 7e08b4d |
| 7 | Alert/agent error messages localized | DONE | 7876e5a |
| 8 | "置信度" → "准确率" (4 files) | DONE | 7e08b4d |
| 9 | Remove "WELCOME BACK, MANAGER" | DONE | 7e08b4d |
| 10 | Sidebar 3-section grouping (日常/专业工具/OPS) | DONE | 7876e5a |

### Round 2+3 Polish (505d1d0)

| Item | Detail |
|------|--------|
| Welcome font | 2.5rem → 1.75rem (B2B-appropriate) |
| Typo fix | "财税理顾问" → "财税顾问" |
| Activity count | "4 位" → "3 位" (match shown items) |
| letterSpacing cleanup | Removed from 5 Chinese text instances |
| Table header unify | 11px/700/uppercase across all pages |
| KPI cards equal-width | "1fr 1fr 1fr auto" → "repeat(4, 1fr)" |
| Table row hover | .table-row-hover CSS class, applied to 3 tables |

### Production
- URL: https://lingque-desktop.pages.dev
- Preview: https://7518164a.lingque-desktop.pages.dev
- Build: 22 pages, 0 TypeScript errors, static export
- GitHub: MARUCIE/cognebula-enterprise@505d1d0 (master)

### Files Modified This Session (Session 12)
- web/src/app/page.tsx (Dashboard restructure + polish)
- web/src/app/components/Sidebar.tsx (3-section grouping + NavLink component)
- web/src/app/components/TopBar.tsx ("AI 专员" rename)
- web/src/app/ops/agents/page.tsx ("AI 专员" + error messages)
- web/src/app/ops/alerts/page.tsx ("AI 专员" + error messages)
- web/src/app/ops/customers/page.tsx ("AI 专员" + hover)
- web/src/app/reports/page.tsx (labels + letterSpacing + hover)
- web/src/app/globals.css (table-row-hover class)
- web/src/app/compliance/page.tsx (letterSpacing cleanup)
- web/src/app/settings/page.tsx (letterSpacing cleanup)
- web/src/app/audit/page.tsx (letterSpacing cleanup)
- web/src/app/tax/page.tsx (table header unify)

### Next Steps (if continuing)
- Reports page: could benefit from task-driven redesign (current: feature directory)
- Cross-page navigation: alerts → agent detail deep links
- Mobile responsive pass (current: desktop-only)
- API integration planning (current: all mock data)
- PDCA 4-doc sync with latest architecture changes
