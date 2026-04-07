# HANDOFF.md -- CogNebula / Lingque Desktop

> Last updated: 2026-04-07T09:30Z

## Session 32 — Full Pipeline Run + Management Report (2026-04-07)

### Status: DONE — All 3 pipelines completed (01:24→09:44 UTC, 8h20m)

### What was done

**1. Full Pipeline Trigger (01:24 UTC)**
- Triggered all 3 pipelines sequentially: M3 -> Daily -> M2
- M3 Orchestrator: 01:24-07:10 UTC (5h46m) — 9/9 steps complete
  - QA gen: +1,700 pairs (10 batches x 100 articles, Gemini 2.5 Flash Lite)
  - KU backfill: +482 nodes, +22 edges
  - FAQ fill: 1,000 entries
  - Edge enrichment: +2 edges (near saturation)
  - Deep crawl: 3/3 timed out (12366/chinaacc/baike_kuaiji, 30min each)
- Daily Crawl: 07:10-08:13 UTC (1h3m)
  - Crawled 2,875 records, deduped -> inserted 7 (0.24% — sources saturated)
- M2 Pipeline: 08:13 UTC -> RUNNING
  - Phase 1 clause split: +6 clauses (44K already split)
  - Phase 1.2 QA gen: +3,516 pairs, 0 errors
  - Phase 2 source expansion: running (fetchers near completion)

**2. Management Reports**
- Full report: `doc/CogNebula_Pipeline_Status_Report_20260407.html` (McKinsey Blue, 8 sections)
- Dashboard: `doc/CogNebula_Pipeline_Dashboard_20260407.html` (one-screen, 3-track view)
- Screenshot: `doc/CogNebula_Pipeline_Dashboard_20260407.png` (4320x2700 @3x DPI)
- Content: KPI overview + milestone bar + node composition chart + 3-track milestones + source matrix (12 sources with historical totals)

**3. 2-Hour Cron Monitor**
- CronCreate job active: checks pipeline progress every 2 hours at :17

### KG Stats (final)
```
Nodes: 581,985 (+3,529 today)
Edges: 1,156,541 (+3,522 today)
Density: 1.987
Quality: 100/100 PASS
LanceDB: 283,604 vectors
Total entities: 1,738,526 (nodes + edges)
```

### Source Totals (historical, all-time)
```
National Tax Bureau:    26,631
Tax Advisors Assoc:      6,927
Accounting School:       6,895
Accounting Wiki:         4,000
NPC Legislation DB:      9,474
NDRC + MOF:              5,611
CPA Association:           694
Stats Bureau:              355
12366 Tax Service:         420
Accounting Society:        318
HS Codes (Customs):     55,673
```

### Key Finding: Data Source Saturation
- Daily crawl dedup rate 99.76% (7/2,875) — existing 22 crawlers exhausted
- Deep crawl 3/3 timeout — target sites hardening anti-crawl
- Growth now depends on: (1) new P0 sources (NPC 17K, court 100K), (2) edge density engine

### Pipeline Completion
```
M3 Orchestrator:  01:24 → 07:10 UTC (5h46m)  QA +1700, KU +482, FAQ +1000
Daily Crawl:      07:10 → 08:13 UTC (1h03m)  +7 new records (sources saturated)
M2 Pipeline:      08:13 → 09:44 UTC (1h31m)  QA +3516, clause +6
Quality Gates:    Phase 1 PASS, Phase 3 PASS, M2 500K PASS
```

### Remaining
- Push local commit `c0bc20b` to GitHub
- Content coverage still 29.3% (KU backfill + FAQ fill improving this daily)
- Deep crawl 3/3 timeout — need Browser Proxy or batch strategy
- New P0 sources needed for growth beyond 600K (NPC 17K, court 100K)

---

## Session 31 — Pipeline Recovery: Gemini Key + auto_improve Fix (2026-04-06)

### Status: DONE — All 3 pipelines verified working

### Problem
All 3 autonomous pipelines were degraded for ~4 days (04-02→04-06):
- M2/M3 LLM steps: 403 Forbidden (Gemini API key deprecated 04-06)
- auto_improve.sh: crash every run (2 bash bugs)
- Result: pipelines "looked alive" (cron firing, logs writing DONE) but produced zero AI-generated content

### Fixes Applied

**1. Gemini API Key Rotation**
- Old key: `AIzaSyBu...` (deprecated 2026-04-06)
- New key: `AIzaSyCv...` (maoyuan.wen@proton.me Developer Program, valid to 2027-01-10)
- Updated: `/home/kg/cognebula-enterprise/.env` + `/home/kg/.env.kg-api`
- Verified: direct Google API + CF Worker proxy + httpx from VPS = all 200 OK

**2. auto_improve.sh Bug Fixes (3 issues)**
- `date +%H` → `date +%-H`: octal parse error on hours 08/09 (bash treats 08 as invalid octal)
- `$API_OK` undefined variable → replaced with proper `$HEALTH` curl check
- Embedding node count: read from `/api/v1/stats` instead of missing field in `/api/v1/health`

**3. KuzuDB Lock Conflict Guard**
- Problem: auto_improve at 16:30 UTC overlaps M2 (14:00-17:30), both write KuzuDB → lock error
- Fix: added `pgrep -f "m2_pipeline.sh|m3_orchestrator.sh"` check before any DB writes
- Replaces fragile time-window guard with process detection

### Verification

**M2 Manual Trigger (15:41→17:29 UTC)**
- Phase 1 QA: 2000/2000 clauses → **+4,547 QA nodes + 4,547 edges**, 0 errors
- All Gemini calls: 200 OK (occasional 503 rate-limit, auto-retried)
- Phase 2: crawlers ran (normal mix of success/timeout)
- Phase 3: quality gate PASS
- Final: 578,456 nodes / 1,152,995 edges (+4,547 / +4,547)

**auto_improve Manual Trigger**
- 4/4 steps executed successfully, no crashes
- Edge enrichment: +0 (already saturated), API restarted cleanly

### KG Stats
```
Nodes: 578,456 (+4,547 from M2 QA)
Edges: 1,152,995 (+4,547)
Density: ~2.0
LanceDB: 263,688 vectors (gap: 314,768 — rebuild needed)
content_coverage: 29.3%
title_coverage: 99.6%
```

### Remaining Items
- **Embedding rebuild**: 314K node gap (263K indexed vs 578K total). ~5h run, manual trigger
- **content_coverage 29.3%**: needs LLM-driven content backfill (M3 QA + KU backfill)
- **Crawler failures**: casc/mof/ndrc/provincial/samr timeout or blocked. Not critical
- **fetch_cf_browser**: broken CLI arg parsing (passes output dir as command)

### Crontab (unchanged)
```
0 2  * * *   M3 orchestrator
0 10 * * *   Daily crawl
0 14 * * *   M2 pipeline
0 */4 * * *  Progress patrol
30 */4 * * * Auto-improve (now with process lock guard)
0 6  * * 0   Weekly backup
```

### Gotchas
1. **API key rotation is a silent killer**: pipelines log `DONE` even when all LLM calls 403. Only `content_coverage` metric (stuck at 29.3%) reveals the problem. Consider adding 403 alerting to patrol
2. **`date +%H` in bash**: zero-padded hours are octal. Use `%-H` or `10#$HOUR`
3. **Python pipe buffering**: `tail -20` on subprocess = no intermediate output. Add `-u` flag to Python calls for observability
4. **CF Worker blocks `urllib` User-Agent**: `Python-urllib/3.12` gets 403, `httpx` passes. Production scripts use httpx so not affected, but test scripts can be misleading

---

## Session 30 — Full System Restoration (2026-04-01 → 04-02)

### Status: DONE — All pipelines verified autonomous

### What was done

**12. LanceDB Vector Index Rebuild — COMPLETE**
- 263,688 vectors at 3072-dim (gemini-embedding-2-preview native)
- Old: 37,329 vectors / 768-dim → New: 263K / 3072-dim (7x coverage, 4x dim)
- IVF_PQ index created: 256 partitions, 96 sub-vectors, cosine metric
- Total embed time: 275.6 min (4.6h), 15 vectors/sec
- LanceDB size: 3.2 GB
- Search verified working: "企业所得税研发费加计扣除" → TaxType/TaxRate/TaxIncentive hits

**13. API Server Symlink Fix**
- Root cause: systemd loaded `/home/kg/kg-api-server.py` (Mar 21 stale copy) not `/home/kg/cognebula-enterprise/kg-api-server.py` (updated)
- Stale copy had `outputDimensionality: 768` → query dim mismatch with 3072-dim index
- Fix: symlink `/home/kg/kg-api-server.py → cognebula-enterprise/kg-api-server.py`
- Cleared `__pycache__/*.pyc` to prevent bytecode drift

**14. M2 Pipeline Fix (API was dead 12+ hours)**
- M2 14:00 UTC Apr 1: stopped API → file not found error → `set -euo pipefail` exit → API never restarted
- Root cause: `cd "$(dirname "$0")/.."` went to `/home/kg` instead of `/home/kg/cognebula-enterprise`
- Fix: `cd "$(dirname "$0")"` (script is at project root)
- Added `trap "systemctl start kg-api" EXIT` to both M2 and M3 (safety net)

**15. Pipeline Bug Fixes (3 fetcher fixes)**
- fetch_flk_npc: SyntaxError (f-string backslash) + TypeError (`int + str`) → fixed → 1,579 items
- fetch_customs: JSL CDN blocks VPS IP → stub
- fetch_npc: dead API (405) → skip in daily pipeline

**16. M3 Orchestrator Ready**
- 4 depth scripts deployed: generate_lr_qa.py, ku_content_backfill.py, generate_edges_ai.py, enrich_edges_batch.py
- generate_edges_ai.py: removed llm_client Poe dep → direct Gemini API
- M3 cron: added log redirect
- M3 first run: 2026-04-02 02:00 UTC (pending verification)

### Gotchas discovered
1. **systemd WorkingDirectory ≠ git repo**: `/home/kg/kg-api-server.py` was a COPY not symlink. All scp deploys went to `cognebula-enterprise/` but systemd read from `~`. Fix: symlink.
2. **M2 cd path**: root-level `m2_pipeline.sh` + `cd $(dirname $0)/..` = wrong parent. Scripts in `scripts/` work fine.
3. **No cleanup trap**: `set -euo pipefail` + no trap = API stays dead on ANY step failure. Both M2 and M3 now have EXIT traps.
4. **__pycache__ bytecode drift**: Python serves stale `.pyc` even when `.py` is updated via scp. Always `rm __pycache__/*.pyc` after deploy.

**17. M3 First Autonomous Run — VERIFIED (02:00-03:38 UTC Apr 2)**
- Step 1 QA: +178 QA pairs from 100 articles (1 batch, manually capped to avoid 15h block)
- Step 2 KU Backfill: +240 content nodes, +12 edges (30 min)
- Step 3 Edge Engine: +7 SUPERSEDES edges via Gemini AI
- Step 4 Enrichment: 0 new (missing PKs — non-critical)
- Step 5 API Restart: healthy ✓
- Step 7 Crawl: flk_npc 1,579 items (fix verified), chinatax 1,590 items
- Total time: 1h38min. Tomorrow's run: ~5h (10 batches with timeouts)

**18. effectiveDate Round 3+3b**
- R3 (title extraction): +71
- R3b (aggressive fullText): +962
- Final: 30,996/39,386 = **78.7%** (was 76.3%)
- Remaining 8,390: no extractable date from any local field

**19. Edge Density Improvements**
- CLASSIFIED_UNDER_TAX: +3,433 LR→TaxType edges via fullText keyword matching
- KU_ABOUT_TAX: +25 edges for new FAQ/QA nodes
- PART_OF: +95 LegalClause→LegalDocument edges
- Edge table discovery: CLAUSE_OF connects RegulationClause (not LegalClause)
- Orphan analysis: 44K LegalClause orphans are plain hash IDs without parent encoding

### KG Stats (final)
```
Nodes: 540,635
Edges: 1,115,084 (+3,553 this session)
LanceDB: 263,688 vectors @ 3072-dim (IVF_PQ indexed)
effectiveDate: 78.7%
content_coverage: 29.3% (+1,941 FAQ, auto-growing 2K/day)
edge_density: 2.063
```

### Remaining items (Phase 6+)
- LawOrRegulation.effectiveDate: 21.3% unfilled (need web scraping or residential proxy)
- LegalDocument triage: migrate qa→FAQEntry, knowledge→KnowledgeUnit
- V1/V2 edge migration
- Provincial crawlers + customs: blocked by VPS IP (need residential proxy)
- enrich_edges_batch: missing PK references (CL_*/CT_* IDs not found)

---

## Session 28 — Ontology Phase 3: TaxItem + V1/V2 Cleanup + CPA (2026-03-31)

### Status: DONE

### What was done

**1. TaxItem 19/19 Tax Type Coverage (93 → 138)**
- Added 45 TaxItem nodes for 14 previously empty tax types
- Coverage: all 19 tax types + 2 surcharges now have TaxItem detail
- Includes: 房产税(2), 土地增值税(4), 城镇土地使用税(4), 车船税(7), 契税(5), 关税(2), 资源税(5), 烟叶税(1), 船舶吨税(2), 耕地占用税(4), 环境保护税(4), 城建税(3), 教育费附加(1), 地方教育附加(1)
- All 45 HAS_ITEM edges created (TaxType → TaxItem)

**2. V1/V2 Table Cleanup**
- Analysis: 4 pairs (ComplianceRule/V2, RiskIndicator/V2, TaxIncentive/V2, FilingForm/V2)
- Decision: V1 data is richer in all cases; V2 are stripped-down duplicates or noise
- Action: DETACH DELETE all V2 data (852 nodes, 1,645 edges removed)
- API: SEARCH_TABLES already pointed to V1; updated V2_TABLES/metadata_tables
- DIRTY_TYPES: removed "RiskIndicator" and "AuditTrigger" (now curated, not dirty)
- V2 table schemas preserved (edge table dependencies prevent DROP)

**3. LegalDocument 54K Triage**
- Discovery: ~70% of LegalDocument nodes are NOT legal documents
  - ~31% real legal docs (policy/local/announcement)
  - ~21% Q&A (tax hotline, 12366)
  - ~22% knowledge/education (kuaiji, doctax, chinaacc, CPA)
  - ~7% templates (report/contract/finance)
- Action: Added `_contentCategory` classification to API (legal/qa/knowledge/template/other)
- Function: `_classify_legal_doc_type()` in kg-api-server.py
- Deployed to VPS, verified working

**4. CPA Knowledge Gap Fill (7,371 → 7,729)**
- Imported 358 CPAKnowledge nodes: 经济法 (5 exam files) + 公司战略 (4 exam files)
- Content: exam questions with answers/analysis + knowledge points
- CPA subject coverage: 4/6 → 6/6 (added economic_law + strategy)

### VPS Final Stats
- 540,426 nodes / 1,111,507 edges
- 91 node tables (4 V2 tables now empty), 115 rel tables
- Audit score estimate: ~7.0/10 → ~7.5/10

### Key decisions
1. **V2 tables not dropped**: edge table definitions (GOVERNED_BY, TRIGGERED_BY, etc.) reference V2 types. DETACH DELETE zeros data; schemas remain as frozen legacy.
2. **LegalDocument not migrated**: Reclassifying 37K nodes across tables too risky (edge cascades). Classification via API `_contentCategory` field is the pragmatic path.

### Phase 4 (same session, continued)

**5. LawOrRegulation.effectiveDate Extraction (0% → 61.1%)**
- Extracted dates from AI-generated summaries using 4-strategy regex pipeline:
  - Priority 1: "施行" context ("自YYYY年M月D日起施行")
  - Priority 2: "生效/执行/实施" context
  - Priority 3: Any full date (YYYY年M月D日) in summary
  - Priority 4: Year from title (fallback, YYYY-01-01)
- Result: 15,333 nodes updated out of 39,182 (61.1% fill rate)
- Gotcha: effectiveDate is DATE type, requires `date('2021-01-01')` not string literal
- Script: `/tmp/extract_lor_dates_vps.py` (ran on VPS)

**6. KnowledgeUnit Content Backfill (93 nodes)**
- Applied prepared backfill from `data/backfill/cicpa_content.jsonl`
- 93/93 KnowledgeUnit nodes got content (CICPA 审计准则体系)

### VPS Final Stats (Phase 4)
- 540,426 nodes / 1,111,507 edges
- LawOrRegulation.effectiveDate: 0% → 61.1%
- KnowledgeUnit content: +93 nodes backfilled

### Phase 5 (Session 29, 2026-04-01)

**7. Gemini API Key Upgrade**
- New key: Google Cloud $300 credit project (replacing expired AI Studio key)
- Generation model: gemini-2.5-flash → `gemini-3.1-pro-preview` (latest)
- Embedding model: already `gemini-embedding-2-preview` (3072 dim)
- Deployed to VPS .env.kg-api + kg-api-server.py

**8. LawOrRegulation.effectiveDate Round 2 (61.1% → 77.8%)**
- Round 2 strategies (no web scraping needed):
  - URL path extraction: `/art/YYYY/M/D/` → 4,214 nodes
  - Regulation number year: `〔2020〕` or `公告2020年第` → 2,867 nodes
- Combined: +7,081 nodes fixed, total ~30,503 / 39,182 (77.8%)

**9. CPAKnowledge Content Generation (Gemini Flash)**
- 3,515 empty heading nodes → Gemini per-heading summary generation
- Result: 2,246 updated (73.9% content fill rate, up from 42%)
- 1,269 failed (titles too short for meaningful generation)

**10. LanceDB Vector Index Full Rebuild (RUNNING)**
- Model: gemini-embedding-2-preview (3072 dim, native)
- Batch API: batchEmbedContents, 50 texts/call, 2s sleep (conservative rate)
- Scope: 31 tables, 278,499 texts
- Old index: 37,329 vectors / 768 dim → New: 278K / 3072 dim (7.5x coverage)
- Script: `scripts/rebuild_embeddings.py --batch-size 50 --resume`
- Bug fixed: `len(embedded)` → `total_written` (NameError at end)
- OOM fixed: incremental LanceDB writes every 5K vectors (FLUSH_SIZE = 5000)
- Status: 55K/278K (20%), 14/sec, ETA ~16:50 UTC Apr 1

**11. Crawl Pipeline Full Restoration**
- Root cause: 3-layer cascade failure (chmod + missing scripts + disabled crontab)
- Pipeline dead for 14 days (since 2026-03-18)
- Fixes applied:
  - daily_pipeline.sh: chmod +x + timeout 2x for all fetchers
  - fetch_flk_npc: rewritten as Playwright adapter (old API dead, Vue SPA)
  - fetch_customs: JSL CDN blocks VPS IP → stub (returns empty until proxy available)
  - fetch_samr: new Playwright fetcher (was CF Browser only) → 42 items
  - fetch_miit: new Playwright fetcher (was CF Browser only) → 10 items
  - fetch_casc: URL double-domain bug fixed (urljoin)
  - fetch_npc: dead API (405) → skip (replaced by fetch_flk_npc)
  - fetch_cf_browser: skipped (replaced by Playwright fetchers)
  - M3 orchestrator: 4 depth scripts deployed + crontab re-enabled (02:00 UTC)
  - M2 pipeline: re-enabled at 14:00 UTC, inject_chinaacc_data.py deployed
- Fetcher status: 12/16 working, 2 skipped (cf_browser, npc), 1 dead (ctax), 1 blocked (customs/JSL)

### Crontab (active)
```
0 2  * * *   M3 orchestrator (QA gen + content backfill + edge engine + crawl)
0 10 * * *   Daily crawl pipeline (15 fetchers + inject + health check)
0 14 * * *   M2 pipeline (clause split + source expansion + AI synthesis)
0 6  * * 0   Weekly backup (VPS → Mac)
```

### Remaining items (Phase 6+)
- **Embedding rebuild**: 277K vectors at 3072 dim, running (~2h remaining)
- LawOrRegulation.effectiveDate: 22.2% still unfilled (chinatax.gov.cn dynamic pages)
- LegalDocument triage: migrate qa→FAQEntry, knowledge→KnowledgeUnit (large scope)
- V1/V2 edge migration: create parallel V1-targeting edge tables, then DROP V2 schemas
- Local←→VPS data sync mechanism
- Provincial crawlers: 10 provinces blocked by VPS IP (need residential proxy)

---

## Session 27 — Ontology Audit + Search Fix (2026-03-31)

### Status: DONE

### What was done

**1. 17-Expert 3-Round Swarm Audit** (ontology-audit-swarm)
- Round 1: 6 strategic advisors → highest leverage: TaxType.code (10min, impacts everything)
- Round 2: 5 domain experts → score 4.4/10 → 10 P0 items identified
- Round 3: 6 business deep-dive → NOT READY (5/6), PARTIAL (1/6)
- Report: `doc/ONTOLOGY_AUDIT_REPORT_2026-03-31.md`

**2. Phase 0 Remediation (local + VPS)**
- TaxType.code: 0% → 100% (18/18 Golden Tax IV codes, both envs)
- AccountingStandard.effectiveDate: 0% → 100% (43/43 CAS dates, both envs)
- LegalDocument.level: 0 → mapped (11 type→level rules on VPS)
- SocialInsuranceRule: 0 → 138 nodes (local: created table + imported)
- IndustryBenchmark: 0 → 45 nodes (local: created table + imported)
- Script: `scripts/fix_audit_phase0.py`

**3. Phase 1 Data Expansion (VPS via API)**
- TaxItem: 42 → 93 (+29 CIT + 22 PIT, covering 企业所得税/个人所得税)
- JournalEntryTemplate: 30 → 60 (+30 templates with debit/credit edges)
- FilingFormField: 45 → 150 (+69 main forms + 36 small taxes)
- BusinessActivity: +30 standard activities (was only risk scenarios)
- HAS_ENTRY_TEMPLATE: 0 → 30 edges (business→journal chain connected)
- ENTRY_DEBITS/CREDITS: 34 → 103 edges
- HAS_ITEM: 42 → 93 edges (TaxType→TaxItem)
- FIELD_OF: 45 → 69+ edges
- IndustryRiskProfile.benchmark: 0% → 100% (720 nodes, 21 pattern rules)

**4. Classification Search Fix**
- API: Added `system` to SEARCH_FIELDS; added TaxClassificationCode + HSCode to SEARCH_TABLES
- Frontend: Split HS海关编码 from 税收分类编码 as separate browsable types
- Commit: 8052957

### VPS Final Stats
- 540,875 nodes (+216) / 1,112,490 edges (+100)
- Audit score estimate: 4.4/10 → ~7/10

### Key findings (Gotchas for next session)
1. **LegalDocument 54K is polluted**: ~30K accounting concepts + ~24K CPA headings, NOT real legal documents
2. **Real legal docs are in LawOrRegulation** (39K nodes, fullText=100% but effectiveDate=0%)
3. **LawOrRegulation fullText is AI summary**, not original text — can't extract dates from it
4. **BusinessActivity 384 nodes were all risk scenarios** (虚开发票×15 etc.), fixed with +30 standard activities
5. **Local DB (100K) ≠ VPS DB (540K)**: v2 tables only on VPS, seed JSONs not imported locally

### Next steps (Phase 3)
- V1/V2 table cleanup (ComplianceRuleV2/FilingFormV2/RiskIndicatorV2 → merge or drop)
- LegalDocument data triage (classify 54K into real legal docs vs concepts vs CPA material)
- LawOrRegulation.effectiveDate: need original crawl data or web lookup (AI summaries lack dates)
- CPA knowledge: 经济法 + 公司战略 两科完全缺失 (0/6 → need ~1,500 nodes)
- TaxItem: 93 → 100+ (need 7 more for other tax types: 车辆购置税/耕地占用税 etc.)

---

## Session 25 — Accounting Workbench Stitch Loop DONE

### Status: COMPLETE

### Stitch MCP OAuth Fix
- Root cause: Stitch API dropped API Key support, only accepts OAuth2 Bearer tokens
- But `stitch-mcp proxy` only supports API Key auth (hardcoded `X-Goog-Api-Key`)
- Fix: Built `bin/stitch-oauth-proxy` (Node.js stdio MCP proxy, gcloud OAuth, 50min auto-refresh)
- Patched npx cache entry point to delegate `proxy` to our OAuth proxy
- Account: `alphameta010@gmail.com`, project: `gen-lang-client-0070301879`

### Stitch Loop Steps (ALL DONE)
1. ~~Read baton~~ DONE
2. ~~Read context files~~ DONE
3. ~~Generate with Stitch~~ DONE — Project `12770423165646112515`, Screen `fe19a2be7ace4b3fb732c8f6e1275de5`
4. ~~Integrate into web/~~ DONE — `web/src/app/workbench/accounting/page.tsx` + Sidebar nav
5. ~~Update SITE.md~~ DONE
6. Next baton: 税务工作台 (pending)

### Artifacts
- Stitch project: `12770423165646112515`
- Design system: Heritage Monolith (auto-generated)
- HTML: `design/accounting-workbench/accounting-workbench.html`
- Screenshot: `design/accounting-workbench/screenshot.png`
- React: `web/src/app/workbench/accounting/page.tsx`
- Build: `npx next build` PASS

---

## Session 23 — v4.2 Phase 1+2 PDCA Execution

### Phase 1 DONE

#### DDL (24 statements, 24 OK)
- CREATE 6 new node tables: JournalEntryTemplate, FinancialStatementItem, TaxCalculationRule, FilingFormField, FinancialIndicator, TaxTreaty
- ALTER AccountingStandard: +4 columns (fullText, description, chineseName, category)
- CREATE 12 edge tables: HAS_ENTRY_TEMPLATE, ENTRY_DEBITS, ENTRY_CREDITS, POPULATES, FIELD_OF, DERIVES_FROM, CALCULATION_FOR_TAX, DECOMPOSES_INTO, COMPUTED_FROM, HAS_BENCHMARK, PARTY_TO, OVERRIDES_RATE
- DETACH DELETE: RiskIndicator 463→0, AuditTrigger 463→0

#### Seed Data
- JournalEntryTemplate: 30 (top common entries: revenue/cost/purchase/salary/tax/depreciation/closing)
- FinancialStatementItem: 40 (balance sheet + income statement + cash flow)
- TaxCalculationRule: 10 (VAT general/simple/withholding/export, CIT general/small/R&D, PIT comprehensive/withholding, stamp)
- FinancialIndicator: 17 (DuPont decomposition tree + liquidity + solvency + efficiency + tax burden)
- TaxTreaty: 20 (top-20: HK/SG/US/UK/JP/KR/DE/FR/AU/CA/NL/TH/MY/RU/IN/MO/TW/CH/IE/LU)
- AccountingStandard: 12 enriched (CAS 00-33 descriptions)
- AccountingSubject: 223→284 (+61 L2/L3 detail accounts: 应交税费15个明细, 应付职工薪酬7个, 管理费用18个, 销售费用7个, 财务费用4个, etc.)
- TaxIncentive: 109→112 (+3 PIT special deductions, 4 already existed)

#### Edges
- ENTRY_DEBITS: 18, ENTRY_CREDITS: 16
- POPULATES: 50 (AccountingSubject→FinancialStatementItem)
- CALCULATION_FOR_TAX: 10, DECOMPOSES_INTO: 3 (DuPont), COMPUTED_FROM: 12
- STACKS_WITH: +5→13, EXCLUDES: +1→16 (PIT stacking rules)
- PARENT_SUBJECT: +96→155 (L2/L3 hierarchy)
- HAS_ENTRY_TEMPLATE: 0 (deferred — BusinessActivity IDs are hash-based)
- PARTY_TO: 0 (deferred — Region IDs are province-level, no national node)

#### API Server
- Constellation: +6 types, +12 edge tables in scan
- Search: +6 types in SEARCH_TABLES
- INTERNAL_EDGES: +DECOMPOSES_INTO, +DERIVES_FROM

#### Frontend
- LAYER_GROUPS: v4.2 (27 types across 4 layers)
- NODE_COLORS: +6 types
- EDGE_LABELS_ZH: +12 v4.2 edges
- FIELD_ZH: +40 v4.2 property labels
- Deployed: lingque-desktop.pages.dev

#### Stats After Phase 1
- Total nodes: 540,030 (was 540,775; -926 garbage + 117 new + some other delta)
- Total edges: 1,111,998
- Node tables: 84 (was 78; +6)
- Edge tables: 104 (was 92; +12)
- Constellation: 1,304 nodes / 2,830 edges / 25 types visible

### Phase 2 DONE

#### DDL (13 statements, 13 OK)
- CREATE 5 P1 node tables: TaxItem, TaxBasis, TaxLiabilityTrigger, DeductionRule, TaxMilestoneEvent
- CREATE 8 P1 edge tables: HAS_ITEM, COMPUTED_BY, LIABILITY_TRIGGERED_BY, INDICATES_RISK, PENALIZED_FOR, ESCALATES_TO, SPLITS_INTO, DEDUCTS_FROM

#### Seed Data
- RiskIndicator: 49 (Golden Tax IV 6-module: tax_burden 8, invoice 10, financial_ratio 12, filing_behavior 6, banking 7, cross_system 6)
- AuditTrigger: 20 (3-level: automatic 8, manual_review 7, escalation 5)
- TaxItem: 42 (consumption 15 + stamp 17 + VAT categories 10)
- TaxBasis: 12 (ad_valorem/specific/compound/income_based/area_based/rental)
- TaxLiabilityTrigger: 13 (VAT 9 rules + CIT 2 + PIT 2)
- DeductionRule: 14 (CIT limited/super_deduction/non_deductible)
- TaxMilestoneEvent: 10 (establishment→operation→ma→liquidation)

#### Edges
- HAS_ITEM: 42 (TaxType→TaxItem)
- LIABILITY_TRIGGERED_BY: 13 (TaxType→TaxLiabilityTrigger)
- INDICATES_RISK: 12 (RiskIndicator→AuditTrigger, cross-module)

#### KuzuDB Gotcha
- ALTER TABLE-added columns cannot be set in CREATE statement — must use CREATE then MATCH+SET

### Final Stats (Phase 1+2)
- Total: 540,190 nodes / 1,112,194 edges
- Node tables: 89 (+11 from v4.1), Edge tables: 112 (+20)
- Constellation: 1,393 nodes / 2,883 edges / 30 types visible
- New v4.2 nodes: ~230 (P0: 117 + P1: ~160, minus rebuilds)
- New v4.2 edges: ~230 (P0: ~160 + P1: ~67)

### Phase 3 DONE (seed_v42_phase3.py executed)
- ResponseStrategy: 17 (seed 脚本定义 17 条，全量入库。设计目标 40 待扩展)
- PolicyChange: 11 (seed 脚本定义 11 条，全量入库。设计目标 30 待扩展)
- IndustryBenchmark: 199 (扩展 from 45, 20 industries × 8 metrics)
- RESPONDS_TO: 15, TRIGGERED_BY_CHANGE: 11, BENCHMARK_FOR edges created

### Session 24 — API Server v4.2 Registration Fix (2026-03-31)

**问题**: Phase 1-3 数据全部入库成功，但 API server 的 TYPES / SEARCH_TABLES / ALL_EDGE_TABLES 仍停留在 v4.1 版本，导致 14 个 v4.2 新类型 + 23 条新边在 constellation 和 search 端点完全不可见。

**修复**:
- `kg-api-server.py` TYPES: +14 v4.2 类型 (P0: 7 + P1: 5 + P2: 2), 修正 sample_limit
- `kg-api-server.py` SEARCH_TABLES: +14 v4.2 类型
- `kg-api-server.py` ALL_EDGE_TABLES: +23 v4.2 边 (P0: 12 + P1: 8 + P2: 3)
- `kg-api-server.py` INTERNAL_EDGES: +3 自引用边 (DECOMPOSES_INTO, DERIVES_FROM, ESCALATES_TO)
- VPS: scp + rm __pycache__ + restart uvicorn

**验证后 Stats**:
- 540,417 nodes / 1,112,243 edges / 91 node tables / 115 edge tables

**坑点文档**: `docs/KG_GOTCHAS.md` (9 条实战教训 + 发布 checklist)

**FilingFormField Seed DONE** (seed_v42_phase4_filing_fields.py):
- ALTER TABLE 补 3 列 (formCode, dataType, formula)
- 45 nodes: VAT 主表(8) + 附表一(3) + 附表二(4) + CIT 年报(8) + A105000(4) + PIT(5) + 印花税(2) + 预缴/附加/房产/土地/代扣(11)
- 45 FIELD_OF edges (FilingFormField→FilingForm)
- 11 DERIVES_FROM edges (跨表栏次引用: A105000→CIT主表, VAT附表→主表, 城建税←VAT)

**RS/PC Expansion DONE** (seed_v42_phase5_expand_rs_pc.py):
- ResponseStrategy: 17→39 (+22: invoice forensics, industry-specific, GT4, incentive mgmt, intl tax)
- PolicyChange: 11→30 (+19: 2022-2026 major reforms, digital economy, global minimum tax, ESG)
- New edges: 28 RESPONDS_TO + 33 TRIGGERED_BY_CHANGE

**Final v4.2 Stats**: 540,458 nodes / 1,112,278 edges

**CR/Penalty Expansion DONE** (seed_v42_phase6_expand_cr_pen.py):
- ComplianceRule: 84→159 (+75: AML/TP/发票/VAT/CIT扣除/PIT/社保/房产/印花/环保/GT4/国际税)
- Penalty: 127→164 (+37: 通用/发票/注册/代扣/TP/社保/房产/环保/刑事/GT4/AML)
- 边创建失败: RULE_FOR_TAX/PENALIZED_BY 边表绑定 ComplianceRuleV2 而非 ComplianceRule (Gotchas #9)
- Penalty SET fullText 失败: Penalty 表无 fullText 列 (Gotchas #10)

**FilingForm补建**: +14 个具体申报表节点 (FF_VAT_GENERAL, FF_CIT_ANNUAL 等) + 45 FIELD_OF 边重建成功

**Phase 4 Validation PASSED** (validate_v42_business_queries.py):
- 27/27 PASS, 0 FAIL, 2 WARN (Search URL编码, 非本体问题)
- 10 条业务查询全部通过: 月结链路/税额计算/栏次填报/风险应对/政策变动/杜邦分析/税收协定/行业基准/优惠叠加/合规处罚
- **Grade A (100%)**

**V1/V2 Bridge Fix**: 75 条新 CR 镜像到 ComplianceRuleV2 + 67 条 RULE_FOR_TAX/PENALIZED_BY 边创建成功

### Session 26 — Frontend UX Overhaul (2026-03-31)

**Commits**: 80c4eb2 → b42db95 (10 commits)

Done:
- v4.2 类型中文化 (14 个 NODE_ZH)
- 知识问答页: 去掉 broken Cytoscape, 改为摘要链接
- 法规条款浏览器: +14 v4.2 类型 + 列定义
- 大表分级菜单 (>1K 阈值): LegalClause(9组50+项) / LegalDocument(3组) / KnowledgeUnit(5组) / Classification(3组) / TaxRate(3组 NEW)
- API 修复: LegalClause 搜索 500 → per-table SEARCH_FIELDS
- API 修复: total count 字段 (COUNT query)
- API 修复: SEARCH_FIELDS 必须匹配实际列 (Gotchas #12)
- KG_GOTCHAS.md: 8→12 条

**Final Stats**: 540,659 nodes / 1,112,390 edges

### Next: Data Quality Swarm Audit (蜂群模式)

**问题**: 法律文件 (54K) 搜索结果大量缺失关键字段:
- effectiveDate: 绝大部分为 "--"
- description: 空
- level: 全是 0
- type: 混杂 (shuiwu/kuaiji/tax_policy_announce/policy_law)

**目标**: 系统性审计 540K 节点的数据完整度, 修复关键缺失, 提升内容可用性

**建议蜂群配置**:
- Expert 1: 数据完整度审计 (哪些表哪些字段缺失率最高)
- Expert 2: 字段映射修复 (effectiveDate/description 从关联表或 fullText 提取)
- Expert 3: 分类体系清洗 (type 字段标准化)
- Expert 4: 数据去重 (V1/V2 表合并)
- Expert 5: 质量门禁升级 (Quality Gate 检查点更新)

**启动命令**: `/clear` → 新会话 → `ontology-audit-swarm` skill

### 未完成项
1. 数据质量审计 + 修复 (蜂群模式, 上述 5 路)
2. V1/V2 表长期合并
3. Classification 53K 分类导航需要改进 (HS编码搜索返回0, 因为内容是编码不是税种关键词)

### Key Commands
```bash
# VPS restart
ssh root@100.75.77.112 "fuser -k 8400/tcp; sleep 3; rm -rf /home/kg/cognebula-enterprise/__pycache__; cd /home/kg/cognebula-enterprise && nohup sudo -u kg /home/kg/kg-env/bin/python3 -m uvicorn kg-api-server:app --host 0.0.0.0 --port 8400 --workers 1 > /home/kg/kg-api.log 2>&1 &"

# DDL via API
curl -sf "http://100.75.77.112:8400/api/v1/admin/execute-ddl" -X POST -H "Content-Type: application/json" -d '{"statements": ["..."]}'

# Frontend deploy
cd web && npx next build && npx wrangler pages deploy out --project-name=lingque-desktop --branch=master

# Seed scripts
python3 scripts/seed_v42_phase1.py   # P0 foundation types
python3 scripts/seed_v42_phase1b.py  # AccountingSubject + TaxIncentive + edges
python3 scripts/seed_v42_phase2.py   # P1 tax law completeness
python3 scripts/seed_v42_phase3.py   # P2 operations + IndustryBenchmark expansion
```

### Git
- Branch: main
- Remote: github.com:MARUCIE/cognebula-enterprise
