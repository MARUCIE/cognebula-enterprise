# Finance/Tax Knowledge Base -- Task Plan

## Objective
Build a SOTA 3-layer Chinese finance/tax knowledge base on CogNebula, scaling to 100K+ nodes for production deployment:
- L1 法规中心 (Regulation) + L2 操作中心 (Operation) + L3 合规中心 (Compliance)
- 123 KuzuDB tables (47 node types + 76 edge types)
- Automated 24/7 crawling (dual-batch 10:00+15:00 UTC) via 12 active sources
- Hybrid RAG + 12 MCP tools + OpenClaw integration
- LanceDB 13,445 x 3072d vectors (Gemini Embedding 2 via CF Worker proxy, reindex in progress)
- Multi-Swarm AI synthesis pipeline with 4-layer quality control
- 3-tier backup: GitHub + CSV export + tar.gz rsync

## Current Phase
Sprint 0: PDCA implementation of 100K scaling strategy. 3 parallel swarms executing.

## Live Metrics (2026-03-15 Session 2)
- **~18,050 total nodes** (13,660 pre-injection + 4,205 TaxClassificationCode + 185 ComplianceRule/FormTemplate)
- **12,952 LawOrRegulation** + **273 RiskIndicator** + **131 OP_StandardCase** + **43 OP_BusinessScenario**
- **4,205 TaxClassificationCode** with 4,199 hierarchy edges (NEW)
- **27 FTIndustry** covering 19 sectors
- **LanceDB reindex in progress**: 13,445 nodes embedding (59% complete)
- **Backup**: GitHub MARUCIE/cognebula-enterprise (private) + daily LaunchAgent + 86MB tar.gz
- **Completeness**: L1 60% / L2 25% / L3 10% / Overall 32%
- **Target**: 100K nodes in 20 weeks via 4-path strategy

## Milestone Strategy
- **M1: 100K nodes** -- 质量检查 + 复盘 + 3层完备性审计 + Precision@5 评测
- **M2: 500K nodes** -- 完成对威科先行的超越 (结构+智能+可及性代差)
- Key insight: 条款级拆分是 M1->M2 的主力 (1 法规 -> 18 clause nodes, 全 L1)

## Sprint 0: Immediate Actions (this week)
- [ ] GB/T 4754 行业分类 + 会计科目表(160+) + 税收优惠(200+) + 税率表 injection
- [ ] doc-tax P0 gaps: 企业报告(8 PDF) + 1163 QA + xlsx + mindmap fix
- [ ] Multi-Swarm review pipeline prototype + 100 golden test entries
- [ ] LanceDB reindex completion + CPA 267 node injection (watcher running)
- [ ] PDCA doc sync + HTML deliverable

## Sprint 1 (W1-4): Structured Data Sources (+20K nodes)
- [ ] HS 海关编码 (~10K nodes)
- [ ] 行政区划代码 (~3K nodes)
- [ ] 税收优惠政策目录 (~2K nodes)
- [ ] 纳税申报日历 (~500 nodes)

## Sprint 2 (W3-10): Web Crawling Expansion (+30K nodes)
- [ ] 12366 热线问答归档 (~8K)
- [ ] 31 省税务局地方政策 (~5K)
- [ ] chinaacc.com 实务文章 (~10K)
- [ ] 中国裁判文书网税务案例 (~3K)

## Sprint 3 (W6-14): Professional Sources (+10K nodes)
- [ ] CPA 考试真题库 1997-2024 (~5K)
- [ ] 教材目录结构提取 (~1.5K)
- [ ] 微信公众号 KOL 文章 (~3K)

## Sprint 4 (W8-20): AI Synthesis + Multi-Swarm QC (+25K nodes)
- [ ] 行业分录模板 (30 x 80 = 2,400)
- [ ] 行业风险指标 (30 x 60 = 1,800)
- [ ] 税收优惠适用指南 (200 x 30 = 6,000)
- [ ] FAQ 问答对扩展 (~8,000)
- [ ] 合规检查清单 (30 x 12 x 3 = 1,080)

## Completed

### P0: Foundation -- DONE (2026-03-14, extended 2026-03-15)
- [x] KuzuDB schema: 3-layer expanded to 123 tables (47 node + 76 rel) with +4 node tables (BusinessScenario, FilingStep, StandardCase, SubAccount) + 12 edge tables
- [x] BulkLoader: init_kuzu_db auto-creates all 4 layers
- [x] `finance-tax-crawl.sh` 6-phase orchestrator
- [x] `finance_tax_processor.py` NER (7 reg patterns + 18 taxes) + change detect + ingest
- [x] Pipeline: `finance-tax-daily-crawl` + `finance-tax-morning-digest` registered (62->64)
- [x] 6 source fetchers + run_all.py (src/fetchers/, 8 files)
- [x] E2E pipeline test: 5 docs -> NER -> KuzuDB (5 laws, 4 taxes, 5 edges)
- [x] THREE_LAYER_ARCHITECTURE.md (1170 lines, 3-layer design with Mermaid + DDL + Cypher)

### P1: RAG + MCP -- DONE (2026-03-14)
- [x] 5 MCP tools: tax_query, policy_search, compliance_check, change_monitor, case_lookup
- [x] Hybrid RAG: finance_tax_rag.py (LanceDB semantic + KuzuDB structural + tiered context)
- [x] OpenClaw MCP: cognebula registered in mcpServers (12 tools)

### P2: Expert Team -- PARTIAL (2026-03-14)
- [x] Expert #9 秦税安 (UC-81~90: tax compliance, Big-4 level)
- [x] Expert #10 顾财道 (UC-91~100: finance analysis, Chief Economist level)

### Data Seeding -- DONE (2026-03-14)
- [x] seed_data.py: 97 nodes seeded across 3 layers
  - L1: 19 TaxType + 5 TaxpayerStatus + 6 EnterpriseType
  - L2: 30 ChartOfAccount + 11 TaxRateMapping
  - L3: 12 TaxCalendar(2026) + 6 EntityTypeProfile + 8 ComplianceRule
- [x] Cross-layer queries verified (一般纳税人→税种, 高新企业→优惠, 软件→税率, 2026日历)

## Remaining (Needs VPS / Real Data)

### P0 Remaining -- VPS DEPLOYED (2026-03-15)
- [x] VPS deployment: Python venv + kuzu + httpx + bs4 + Redis -- ColoCrossing 100.106.223.39
- [x] Live crawl MOF: 24 real policies (regex fallback parser) -- 2026-03-15
- [x] Live crawl PBC: 20 real regulations (中国人民银行令〔2026〕) -- 2026-03-15
- [x] NER pipeline on live data: 48 docs, 0 errors, 48 LawOrRegulation nodes -- 2026-03-15
- [x] Total graph: 205 nodes (157 seed + 48 live) -- 2026-03-15
- NOTE: chinatax.gov.cn 法规库 is Vue SPA, needs browser-automation (not plain HTTP)
- NOTE: BS4 selectors unreliable on gov HTML; regex fallback is the correct strategy
- [x] VPS cron: 3 jobs added (116→124): daily crawl 06:00, pipeline 07:30, digest 01:30 UTC -- 2026-03-15
- [x] Mac LaunchAgent: reloaded with Obsidian vault WatchPath -- 2026-03-15
- [x] Source audit: NPC(405/SPA), Customs(412/WAF), CTax(DNS dead) -- all need browser-automation or replacement -- 2026-03-15
- [x] New fetcher: fetch_safe.py (SAFE 外汇管理局, 3 sections, 60 items) -- 2026-03-15
- [x] New fetcher: fetch_csrc.py (CSRC 证监会, 3 sections, 177 items) -- 2026-03-15
- [x] Updated run_all.py: 5 active sources (chinatax/mof/pbc/safe/csrc), 3 disabled (npc/customs/ctax)
- [x] Updated finance-tax-crawl.sh: wired SAFE + CSRC, removed dead sources
- [x] chinatax FGK JSON API: fetch_chinatax_api.py (57,073 records available, 7,026 fetched so far) -- 2026-03-15
- [x] 3 new fetchers: fetch_ndrc.py(592), fetch_casc.py(53), fetch_stats.py(30) -- 2026-03-15
- [x] Total active sources: 11 (chinatax+FGK API, mof, pbc, safe, csrc, ndrc, casc, stats, baike_kuaiji running) -- 2026-03-15
- [x] Dual-batch cron: 10:00 + 15:00 UTC with flock singleton -- 2026-03-15
- [x] 7,295 total nodes / 6,384 edges in KuzuDB -- 2026-03-15
- [ ] browser-automation for NPC/Customs/chinatax法规库 (P3, needs Playwright/Midscene)
- [ ] baike_kuaiji.com: crawling 17K entries (2,790+ so far, target 10K+ nodes)

### P1 Remaining
- [x] Batch embed 157 nodes via Gemini Embedding 2 (768d, all successful) -- 2026-03-14
- [x] embed_finance_tax.py (embedding pipeline script) -- 2026-03-14
- [x] LanceDB 0.29.2 installed in VPS venv -- 2026-03-15
- [x] build_vector_index.py: KuzuDB → Gemini Embedding → LanceDB pipeline -- 2026-03-15
- [x] 1,438 LawOrRegulation nodes embedded (3072d) into LanceDB via CF Worker proxy -- 2026-03-15
- [x] json_to_obsidian.py: added SAFE/CSRC/chinatax_fgk/pbc_tiaofasi/mof_zhengcefabu source maps + UTF-8 byte truncation fix -- 2026-03-15
- [x] Obsidian vault: 5,781+ markdown files (from 595 initial, massive expansion via FGK API + new sources) -- 2026-03-15
- [ ] Query accuracy eval: 100 test queries, target >= 85% P@5

### P2 Remaining
- [x] Pipeline 7-stage automation: discover→crawl(5)→news→process→obsidian→embed→alert -- 2026-03-15
- [x] phase_obsidian: json_to_obsidian.py + Git auto-commit in pipeline -- 2026-03-15
- [x] phase_embed: build_vector_index.py + CF Worker proxy in pipeline -- 2026-03-15
- [ ] Telegram alert template (new policy notification)
- [ ] CF Pages: /finance-tax/ dashboard views
- [ ] Integration test: expert digest delivery end-to-end

### Schema Extension + Gap Filling -- DONE (2026-03-15)
- [x] +4 node tables: BusinessScenario, FilingStep, StandardCase, SubAccount -- 2026-03-15
- [x] +12 edge tables for new node types -- 2026-03-15
- [x] Total schema: 123 tables (47 node + 76 rel), up from 107 -- 2026-03-15
- [x] Gap filling: 65 seed nodes + 106 seed edges across 10 previously-empty tables -- 2026-03-15

### doc-tax Local File Processing -- IN PROGRESS (2026-03-15)
- [x] Discovered 1,912 local files (903 doc + 422 docx + 73 xlsx) for L2/L3 enrichment -- 2026-03-15
- [ ] Process doc/docx files for L2 操作中心 content (AccountEntry, ChartOfAccount, etc.)
- [ ] Process xlsx files for L3 合规中心 content (TaxCalendar, ComplianceRule, etc.)

### baike_kuaiji.com Crawl -- IN PROGRESS (2026-03-15)
- [x] Crawler deployed for 17K accounting wiki entries -- 2026-03-15
- [x] 2,790+ entries fetched so far -- 2026-03-15
- [ ] Target: 10K+ nodes (will push total well past 10K node target)

### P3: Change Detection + PDF (Week 7-8)
- [x] Change detection Tier-1: SHA256 hash-based in finance_tax_processor.py -- 2026-03-15
- [ ] Change detection Tier-2: unified_diff on changed pages
- [ ] Change detection Tier-3: embedding cosine similarity < 0.95
- [ ] Version chain: SUPERSEDES edges in KuzuDB
- [ ] Git archival: raw HTML audit trail
- [ ] PyMuPDF + PaddleOCR PDF pipeline
- [ ] 24h unattended stress test

### Knowledge Pipeline (知识沉淀管线) -- NEW
- [x] KNOWLEDGE_PIPELINE.md architecture (831 lines, Obsidian-Centric) -- 2026-03-15
- [x] json_to_obsidian.py (230 lines: frontmatter+wikilinks+tags+callouts+auto-classify) -- 2026-03-15
- [x] Obsidian vault scaffold: ~/Obsidian/财税知识库/ (51 dirs + 3 templates) -- 2026-03-15
- [x] finance-tax-knowledge-pipeline.sh (4-stage orchestrator, 120 lines) -- 2026-03-15
- [x] Pipeline registered: finance-tax-knowledge-pipeline (65th pipeline) -- 2026-03-15
- [x] Stage 3 tested: 5 test docs → 5 Obsidian MD with wikilinks+tags -- 2026-03-15
- [x] CF Pages /finance-tax/index.html (Bloomberg-style dashboard, 18 tax types) -- 2026-03-15
- [x] LaunchAgent WatchPath: added ~/Obsidian/财税知识库 to dashboard-sync plist -- 2026-03-15
- [x] Git init vault (master branch, 8 files committed) -- 2026-03-15
- [x] Memory saved: project_cognebula_finance_tax_kb.md + MEMORY.md updated -- 2026-03-15
- [ ] NotebookLM manual upload workflow (anything-to-notebooklm skill)
- [ ] Integration test: crawl → obsidian → CF Pages end-to-end

### Doc Sync v3.1 -- 2026-03-15
- [x] PRD.md: updated data sources (5 active + 4 deferred), 7-stage pipeline, volume per source -- 2026-03-15
- [x] SYSTEM_ARCHITECTURE.md: updated embedding section (3072d, LanceDB 0.29.2, CF Worker proxy, cron rebuild) -- 2026-03-15
- [x] USER_EXPERIENCE_MAP.md: replaced Scrapy with AI-Fleet skill fetchers, updated Journey B flow -- 2026-03-15
- [x] PLATFORM_OPTIMIZATION_PLAN.md: added execution status table, updated success criteria (6/10 done), added actual metrics -- 2026-03-15
- [x] Generate 4 Chinese HTML: PRD-zh(Claude) + ARCH-zh(Claude) + UX-zh(Claude) + OPT-zh(McKinsey) -- 2026-03-15

## Key Decisions
- **3-Layer Architecture**: L1 法规 + L2 操作 + L3 合规 + XL 跨层
- **Compose, Don't Build**: 40+ AI-Fleet skills, zero custom spiders
- **KuzuDB**: 123 tables (47 node + 76 rel), embedded, Cypher-native, air-gapped
- **Edge naming**: FT_/OP_/CO_/XL_ prefixes prevent collision in single DB
- **FilingForm in L2** (not L1): it's an operational tool, not a regulation
- **7 lifecycle stages**: maps 1:1 to enterprise financial rhythm
- **chinatax FGK JSON API**: breakthrough discovery, 57K records available via working API endpoint
- **Dual-batch cron**: 10:00 + 15:00 UTC matches gov site post-publish rhythm
- **3072d embeddings**: full-dimension Matryoshka via CF Worker proxy on VPS (not 768d)
- **Competitive moat**: graph DB with 123 tables enables cross-regulation reasoning vs Wolters Kluwer flat search

## Evidence
- 4 rounds of swarm research (10+ agents total)
  - Round 1: CogNebula engine + finance sources + OpenClaw + crawler tech
  - Round 2: CN gov sources + CN media + CN tax schema
  - Round 3: accounting standards + tax rate mapping + enterprise lifecycle
  - Round 4 (2026-03-15): 4 parallel agents -- new sources, deep crawl, 24/7 schedule, scaling path
- Architecture: THREE_LAYER_ARCHITECTURE.md (1170 lines)
- Knowledge Pipeline: KNOWLEDGE_PIPELINE.md (831 lines)
- Verification: 7,295 nodes, 6,384 edges, 1,438 vectors, 5,781+ Obsidian files
- Competitive benchmark: vs Wolters Kluwer 威科先行 (1.26M docs, flat search, no graph reasoning)
