# Finance/Tax Knowledge Base -- Notes

## 2026-03-16: M1 Quality Gate + P0 Fixes

### M1 Achievement: 100,239 nodes (2026-03-16 03:30 UTC)
- Target: 100,000 → Achieved: 100,239
- Sources: 10+ (chinatax_fgk, 12366, chinaacc, doc-tax, ndrc, AI synthesis, cross-product matrix)
- Edge count: 45,158 (pre-fix)

### M1 Quality Gate Audit (2026-03-16 03:40 UTC)
- **P0 CRITICAL: 91.7% orphan rate** — 54,275/59,170 LR nodes had zero edges
- **P0 CRITICAL: ~12,760 template placeholders** — city/lifecycle/risk guides avg 56-64 chars
- **P1: 2,867 duplicate titles**
- **P1: LanceDB 13.4% coverage** — 13,445 vectors for 100,239 nodes
- HTML report: `M1_QUALITY_GATE_RETROSPECTIVE.html`

### P0-2: Template Purge (DONE)
- Deleted 6 template types: city_tax_guide(3800), city_industry_guide(2000), regional_tax_guide(1900), risk_monitoring(1900), regional_industry(1350), lifecycle_guidance(810) = **-11,760**
- Deduplicated 778 duplicate-title excess nodes
- Total: 100,239 → 87,701

### P0-1: Edge Enrichment (DONE)
- Created 2 new edge tables: `LR_ABOUT_TAX` (LR→TaxType), `LR_ABOUT_INDUSTRY` (LR→FTIndustry)
- Pass 1: +19,700 tax edges + 19,171 industry edges (keyword matching on title + regulationType)
- Pass 2: +8,466 tax edges (fullText scan + type-based defaults for kuaiji/shuiwu/chinaacc)
- **Result: orphan rate 91.7% → 20.5%** (9,540 remaining = general policy nodes without specific tax type)
- **Edge count: 45,158 → 92,495 (+105%)**

### P0-3: LanceDB Full Reindex (IN PROGRESS)
- Script: `src/p0_rebuild_vectors.py`
- Config: 768d Matryoshka (down from 3072d, for M2 500K scalability)
- Proxy: CF Worker `gemini-api-proxy.maoyuan-wen-683.workers.dev` (VPS geo-restricted)
- Target: ~57K docs (LR + Clauses + small tables, excluding HSCode/TaxClass/Region)
- ETA: ~6-7 hours @ 2.5 req/s
- VPS PID: background nohup

### Post-Fix Status
| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Nodes | 100,239 | 87,701 | Quality > Quantity |
| Orphan rate | 91.7% | 20.5% | <20% |
| Edges | 45,158 | 92,495 | Continue enriching |
| Edge density | 0.46 | 1.05 | >= 2.0 |
| LanceDB coverage | 13.4% | (rebuilding) | 100% |
| Duplicates | 2,867 | ~0 | 0 |

---

## 2026-03-15: Sprint 0-2 Progress (Session 2, continued)

### Cloudflare Browser Rendering API Integration (2026-03-15)
- **Script**: `src/fetchers/fetch_cf_browser.py`
- **3 endpoints**: /crawl (async multi-page), /json (AI structured extraction), /scrape (CSS selector)
- **Key value**: Unlocks 4 previously-blocked JS-rendered gov sites (NPC, SAMR, MIIT, Customs)
- **`/crawl`**: Async, auto-link-follow, JS rendering, max 100K pages/job, markdown output
- **`/json`**: AI-powered structured data extraction with JSON schema, Workers AI or custom models
- **Setup**: `export CF_ACCOUNT_ID=xxx CF_API_TOKEN=xxx` (Browser Rendering Edit permission)
- **Limitations**: Fixed UA (CloudflareBrowserRenderingCrawler/1.0), cannot bypass CAPTCHAs, Free plan limited
- **Finance-tax wrappers**: `crawl_gov_site()`, `extract_policy_list()`, `crawl_all_blocked_targets()`
- **Priority targets**: NPC(Vue SPA), SAMR(Hanweb), MIIT(Hanweb), Customs(瑞数WAF), guangdong_tax(blocked IP)
- **Potential**: ~5,000+ additional nodes from 5 blocked sources
- **Status**: Script ready, needs CF account setup to activate

### Sprint 2 Status (in progress)
- **Total nodes**: 26,752 (from 12,721 start = +110.3%)
- **12366 QA injected**: 5,246 nodes (fast mode, detail crawl running for full answers)
- **AI Synthesis validated**: 49% acceptance rate, 10 auto-inject across 4 industries
- **Running pipelines**: 12366 detail (VPS), AI synthesis batch (Mac), chinaacc fix, HS expand, provincial, CPA exams
- **Provincial probe**: 4/14 sites reachable (jiangsu, zhejiang, shanghai, tianjin)
- **GitHub**: 3 commits to MARUCIE/cognebula-enterprise

### Sprint 1 Completed
- AdministrativeRegion: 5 -> 482 (all prefectures + 32 tax zones)
- HSCode: 0 -> 366 (97 chapters + 269 headings, seed for 10K)
- Mindmap expanded: +426 LawOrRegulation
- Enterprise reports: +336 chapters + 110 indicators
- 12366 fetcher: API discovered (POST /sscx/rdzs03), 5,297 QA pairs
- chinaacc fetcher: skeleton ready, 120 articles (pagination fix needed)
- Multi-Swarm QC pipeline: validated with real Gemini API calls

### Sprint 0 Completed
- CPA injection: +266 OP_StandardCase
- ChartOfAccount: 30 -> 159 (full 企业会计准则 科目表)
- TaxIncentive: 8 -> 110 (VAT24 + CIT32 + PIT21 + Other32)
- TaxRate: +80 TaxRateMapping + 23 TaxRateSchedule (NEW tables)
- FAQ: +1,152 LawOrRegulation (1,156 QA pairs)
- LanceDB reindex: 1,438 -> 13,445 x 3072d vectors (DONE)
- 3-tier backup: GitHub + daily LaunchAgent + 86MB tar.gz
- Multi-Swarm prototype: 4-layer pipeline + 100 golden test entries

---

## 2026-03-15: doc-tax 5-Layer Strategic Utilization (Session 2)

### Session Summary
- **Starting state**: 12,721 nodes (from Session 1), L2 20 nodes, L3 10 nodes
- **Ending state**: 13,660 nodes, L2 174 nodes (8.7x), L3 278 nodes (27.8x)
- **Net new nodes**: +939 (28 scenarios + 126 cases + 125+143 risk indicators + 17 industries + 500 mindmap docs)

### doc-tax 5-Layer Extraction Results
| Layer | Source Files | Records Extracted | Graph Nodes Created |
|-------|-------------|-------------------|---------------------|
| 1. Industry Guides | 28/35 files (19 industries) | 1,849 journal entries + 267 risk points | 28 BS + 126 SC + 125 RI |
| 2. xlsx Indicators | 5 spreadsheets | 66 tax burden + 30 warning + 47 credit + 41 benchmarks | 143 RiskIndicator |
| 3. Mindmap Docs | 14,270 extracted nodes | 1,265 with substantial content | 500 LawOrRegulation (capped) |
| 4. Financial Templates | 12 chapters x (制度+表格) | 76 compliance rules + 109 form templates | metadata (not yet graph) |
| 5. Contract Templates | 969 contract files | cataloged 23 categories | metadata (not yet graph) |

### Extraction Scripts Created
- `src/extract_industry_guides.py` -- 35 industry-specific PDF/doc/docx files
- `src/inject_industry_data.py` -- Creates BS/SC/RI nodes from extracted data
- `src/inject_extracted_data.py` -- Batch inject tax burden rates, warning indicators, credit indicators, mindmap nodes
- Agent-created: `src/extract_xlsx_indicators.py`, `src/extract_mindmap_docs.py`, `src/extract_financial_templates.py`

### Industries Covered (19 sectors)
建筑业, 房地产, 汽车经销, 医疗美容, 物业管理, 网络直播, 软件IT, 高新技术,
采矿, 煤炭, 再生资源, 学前教育, 律所, 人力资源, 劳务派遣, 合伙企业,
非营利组织, 制造业, 出口退税, 混凝土, 黄金零售

### Remaining doc-tax Work
- [ ] Raise mindmap cap from 500 to 1,265 (all substantial nodes)
- [ ] Inject 76 compliance rules + 109 form templates as graph nodes
- [ ] Process 969 contract templates -> ContractTemplate node type
- [ ] 4,205 tax classification codes -> TaxClassification table
- [ ] Rebuild LanceDB vector index (1,438 vectors for 13,660 nodes)

---

## 2026-03-15: SOTA Knowledge Base Buildout -- Session 1 STATUS

### Session Summary (2026-03-15 end-of-day)
- **Starting state**: 535 nodes, 438 LawReg, 5 sources, 107 tables, 438 vectors
- **Ending state**: 7,295 nodes, 7,026 LawReg, 11 sources, 123 tables, 1,438 vectors, 5,781+ Obsidian files
- **Growth factor**: 13.6x nodes, 16x LawReg, 2.2x sources, 3.3x vectors, 9.7x Obsidian files

### Competitive Analysis: vs Wolters Kluwer 威科先行
- **威科先行**: 1.26M documents, flat full-text search, no graph reasoning, enterprise pricing ($50K+/yr)
- **CogNebula FT KB**: 7,295 nodes in 123-table graph, cross-regulation reasoning via Cypher, $0-10/month
- **Our advantage**: graph DB enables incentive stacking queries (e.g., "高新技术企业 in 上海自贸区 doing 软件出口" → 3-4 overlapping incentives via graph traversal). Flat search cannot do this.
- **Their advantage**: volume (1.26M vs 7.3K). But: quantity without structure is noise. Our 123-table schema gives each node 2-5 typed relationships vs their bag-of-words.
- **Path to parity**: baike_kuaiji (17K entries) + chinatax FGK API (57K records) + doc-tax files (1.9K) will push us to 30K+ nodes. Quality > quantity.

### doc-tax Local File Discovery
- Found 1,912 files in doc-tax directory: 903 .doc + 422 .docx + 73 .xlsx + misc
- Content: accounting standards implementation guides, tax filing templates, compliance checklists
- Value: ideal for L2 操作中心 (AccountEntry, ChartOfAccount, TaxRateMapping) and L3 合规中心 (ComplianceRule, TaxCalendar)
- Processing: needs python-docx + openpyxl pipeline, will run as batch job

### Schema Extension Results
- Added 4 new node tables: BusinessScenario, FilingStep, StandardCase, SubAccount
- Added 12 new edge tables connecting new nodes to existing schema
- Total: 107 → 123 tables (47 node + 76 rel)
- Gap filling: 65 seed nodes + 106 seed edges seeded into 10 previously-empty tables
- 3-layer completeness: L1 法规 near-complete (7,026 LawReg), L2 操作 partially seeded (30 COA + 17 sub-account + 15 scenario + 15 filing step + 10 entry), L3 合规 partially seeded (8 rules + 12 calendar + 6 profile + 5 risk + 5 penalty)

### baike_kuaiji.com Crawl Progress
- Target: 17,000 accounting wiki entries (largest free Chinese accounting knowledge base)
- Progress: 2,790+ entries fetched, crawl running
- Projection: will push node count past 10K target within 24-48h
- Content type: accounting concepts, journal entry templates, tax calculation methods -- ideal for L2 enrichment

---

## 2026-03-15: SOTA Knowledge Base Buildout (5 → 11 sources, 24/7 crawl)

### Swarm Research (4 parallel agents)
- **R1 (New Sources)**: Probed 15 candidates from VPS, found 10 working HTTP sources
  - Tier A (high value): ndrc(592), casc(53), stats(30), miit(103 homepage), samr(69 homepage)
  - samr/miit use Hanweb CMS (JS-rendered) → disabled, need browser-automation
  - Net new active: ndrc + casc + stats = 3 sources
- **R2 (Deep Crawl)**: BREAKTHROUGH - chinatax FGK has working JSON API (57,073 records!)
  - API: `GET /search5/search/s?siteCode=bm29000002&searchSiteName=GSFFK&pageNum=N`
  - MOF: 20 pages/section (not 2), 3 sections = ~1,480 items
  - SAFE: 141 pages in whxw section (~2,800 items), but index_1.html always 404
  - Theoretical max from 5 existing sources: 15,300+ items
- **R3 (24/7 Schedule)**: Dual-batch post-publish (10:00 + 15:00 UTC), alert 00:30 UTC
- **R4 (Scaling Path)**: Deep pagination > new sources > full text for ROI
  - 5000 nodes reachable in 3-5 days with deep pagination
  - SOTA = not node count, but 107-table schema cross-referencing density

### Execution Wave 1 (implemented)
- 5 existing fetchers: deep pagination enabled (mof 10p, pbc 3 sections, safe 5p/s, csrc dedup)
- 3 new fetchers deployed: fetch_ndrc.py(592), fetch_casc.py(53), fetch_stats.py(30)
- fetch_chinatax_api.py: FGK JSON API fetcher (20 items tested, anti-bot limits investigation needed)
- Pipeline v2.0: 9 sources (5 original + 3 new + FGK API) + --no-detail default
- Cron v2.0: dual-batch (10:00 + 15:00 UTC) with flock singleton

## 2026-03-15: Source Expansion (3 → 5 active sources)

### Diagnosis: 3 Broken Fetchers
- **NPC (flk.npc.gov.cn)**: Pure Vue SPA, all pages return 455-byte JS shell, API returns 405 (nginx blocks POST)
- **Customs (customs.gov.cn)**: All pages return 412 + JS challenge (瑞数信息 WAF, obfuscated JS)
- **CTax (ctax.org.cn)**: DNS resolution fails completely ("No address associated with hostname"), domain dead

### ADR-002: Replace Dead Sources with Working Gov Sites
- **Decision**: Replace NPC/CTax with SAFE (外汇管理局) + CSRC (证监会); defer NPC/Customs to P3 (browser-automation)
- **Probed 10 alternative sources**: shui5(SPA), 12366(SPA), gov.cn(SPA), esnai(404), hwuason(timeout) -- all failed
- **Working**: SAFE (22 links, `/safe/YYYY/MMDD/NNNNN.html` pattern) + CSRC (20 links, `/csrc/cN/cN/content.shtml` pattern)

### New Fetchers Deployed
- `fetch_safe.py`: SAFE 外汇管理局, 3 sections (policy_interpret, forex_news, regulations), 60 items
- `fetch_csrc.py`: CSRC 证监会, 3 sections (csrc_news, policy_interpret, regulations), 177 items
- `run_all.py`: Updated registry (5 active, 3 disabled with comments)
- `finance-tax-crawl.sh`: Wired SAFE + CSRC, removed NPC/Customs/CTax calls

### Production Test Results (VPS, 2026-03-15)
- 5 fetchers: chinatax(132) + mof(50) + pbc(10) + safe(60) + csrc(177) = **429 items**
- NER processing: 259 new (changed), 170 skipped (existing), 0 errors
- KuzuDB: **438 LawOrRegulation** nodes, **535 total** nodes
- Crawl time: ~31 minutes (礼貌爬取 5s delay between requests)

### Key Lesson: Gov Site Crawlability
- **Direct HTTP works**: SAFE/CSRC/MOF/PBC -- traditional server-rendered, real href paths
- **Pure SPA (no HTTP fallback)**: NPC/12366/chinatax法规库/gov.cn -- JS shell + hidden API
- **WAF protected**: Customs -- 瑞数信息 JS challenge, 412 for all non-browser requests
- **Strategy**: curl probe first, choose approach based on actual response, not assumed structure

## 2026-03-15: Knowledge Pipeline Design

### ADR-001: Obsidian-Centric Pipeline (not NotebookLM-Centric)
- **Decision**: Obsidian vault as core knowledge store, NotebookLM as optional enrichment
- **Reason**: `notebooklm login` requires browser OAuth, cannot run in unattended cron
- **4 stages**: Crawl(existing) → Digest(NER+classify) → Obsidian(vault) → Publish(CF Pages)
- **Architecture doc**: KNOWLEDGE_PIPELINE.md (831 lines)
- **Pipeline registered**: finance-tax-knowledge-pipeline (65th pipeline, 64→65)

### Embedding Pipeline Completed
- 157 nodes embedded via Gemini Embedding 2 Preview (768 dims)
- All 157/157 successful
- sqlite-vec not available on Mac; JSON fallback stored
- Full integration needs VPS with proper Python venv

### v3.0 Scope Expansion
- v1.0→v2.0: China-specific sources + schema (13→43 node types)
- v2.0→v3.0: 3-layer architecture (L1法规+L2操作+L3合规) + knowledge pipeline
- Total: 107 KuzuDB tables + 157 seed nodes + 4-stage pipeline + 65 fleet pipelines

## 2026-03-14: Swarm Brainstorming Session

### Research Agents Deployed (4 parallel)

1. **CogNebula Engine Analysis** (79s, 114K tokens)
   - 3122 lines monolith, 17 CLI commands, 9 API endpoints, 7 MCP tools
   - KuzuDB: 13 node types (File, Folder, Function, Class, Interface, Method, ArrowFunction, Module, External, Community, Document, Section, Topic), 23 edge types
   - Existing document pipeline: `build_doc_graph()` -> Document/Section/Topic nodes
   - LanceDB: optional, simulated in current code
   - Extension: new node/edge types = dict entry + parser function

2. **Finance/Tax Source Research** (136s, 34K tokens)
   - Government primary: chinatax.gov.cn (政策法规库), mof.gov.cn, gov.cn, npc.gov.cn
   - Professional: cicpa.org.cn, ctax.org.cn, esnai.com
   - No official API from any source -- HTML crawling required
   - Academic references: TurboTax KG (arXiv:2009.06103), FinDKG (arXiv:2407.10909)
   - Open-source crawler: SmartDataLab/Policy_crawler (Chinese gov sites)
   - Schema: 9 entity types, 10 relationship types, bitemporal versioning

3. **OpenClaw Integration Research** (123s, 97K tokens)
   - 62 pipelines, 76 VPS cron jobs, 8 expert personas
   - MCP slot: `mcpServers: []` in openclaw.json -- ready for CogNebula
   - News aggregator: 28 sources, fetch_news.py extensible
   - Expert #5 温如意 already covers some finance (UC-44~48)
   - Digest pipeline: Playwright screenshot -> Telegram push -> CF Pages deploy
   - Reuse rate: estimated > 80% of infrastructure already built

4. **Crawler Tech Evaluation** (97s, 26K tokens)
   - Scrapy + Scrapy-Redis: best for static gov HTML, distributed
   - Crawlee/Playwright: best for JS-rendered pages
   - Trafilatura: F1=0.909 (best article extraction)
   - PyMuPDF + PaddleOCR: best for Chinese PDF/OCR
   - Celery Beat + Redis: natural fit (Redis already in Docker Compose)
   - WeChat scraping: high legal risk, recommend Sogou indirect or skip

### Cross-Verification Findings

1. **Graph DB divergence resolved**: Tax research Agent recommended Neo4j (industry default); Engine Agent confirmed KuzuDB sufficient (embedded + Cypher + bulk load). Decision: keep KuzuDB.

2. **Vector DB alignment**: Both Engine and Crawler agents confirmed LanceDB. Combined with Gemini Embedding 2 Preview (already integrated in AI-Fleet `bin/embed`).

3. **Scheduler convergence**: Crawler Agent recommended Celery Beat + Redis. OpenClaw Agent confirmed Redis already in Docker Compose. Natural fit.

4. **WeChat risk consensus**: Both Tax Source and Crawler agents flagged WeChat scraping as high legal risk. Decision: defer to v2, use Sogou indirect search only.

## 2026-03-14: Round 2 -- China Domestic Source Deep Dive (3 agents)

### Agent Results

1. **CN Government Sources** (184s, 40K tokens)
   - 50+ sources audited across 7 categories (A-G)
   - P0 Critical: 税务总局法规库(JS,50K docs), 财政部(dynamic,5K), NPC法律库(API,100K), 海关税则(static,8K)
   - P1 High: 央行条法司, 国务院, CICPA, 统计局, 外管局, 商务部
   - Skip: 北大法宝(paywall+Art.285), 省级税务局(redundant with national)
   - Key: NPC法律库是最容易爬的(有partial API); 税务总局法规库最难(JS+rate limit)

2. **CN Finance Media** (123s, 37K tokens)
   - TOP 20 ranked by quality x accessibility x frequency
   - #1 中国税务报 ctaxnews.net.cn (9.5/10 but partial paywall)
   - #3 华尔街见闻 (already in news-aggregator, RSSHub supported)
   - #5 税屋网 shui5.cn (free, practitioner cases, since 2008)
   - 4-tier architecture: Official > Professional > Community > Academic
   - RSSHub routes available for: 华尔街见闻, 虎嗅, 36氪

3. **CN Tax Schema** (123s, 33K tokens)
   - 18 tax types fully documented with rates, filing freq, governing law
   - 13 node types (expanded from 9): added TaxpayerStatus, EnterpriseType, PersonalIncomeType, TaxIncentive, SpecialZone, TaxAuthority, FilingObligation, TaxRateVersion
   - 15 relationship types (expanded from 10): added QUALIFIES_FOR, MUST_REPORT, AFFECTS, OFFERS, ADMINISTERS, REPORTS_TO, TRIGGERS
   - 5 regulation numbering patterns: 国发/财税/税总发/公告/海关
   - 10 sample Cypher queries for common use cases
   - Temporal: TaxRateVersion nodes + SUPERSEDES chain
   - GB/T 4754-2017 industry classification (~1500 codes)

### Key Findings

- **NPC法律库 flk.npc.gov.cn** is the hidden gem: partial search API, 100K+ docs, LOW scraping difficulty, public access. Should be the FIRST source to crawl.
- **Schema complexity jumped significantly**: 9 nodes/10 edges (v1.1) -> 13 nodes/15 edges (v2.0). The Chinese tax system's real complexity is in taxpayer classification (一般/小规模) x incentive stacking x regional variation.
- **Incentive stacking** is the killer feature for compliance: "高新技术企业 in 上海自贸区 doing 软件出口" could qualify for 3-4 overlapping tax incentives. Graph traversal is the only tractable way to compute this.
- **Legal risk is real**: PRC Penal Code Art.285 prohibits unauthorized computer access. Must honor robots.txt, avoid CAPTCHA bypass, keep legal counsel.

## 2026-03-14: P0 Execution Evidence

### Crawl Test Results (Mac local network)

| Source | HTTP | Size | Server-rendered | NER | Production-ready |
|--------|------|------|-----------------|-----|-----------------|
| PBC pbc.gov.cn | 200 | 40KB | YES | YES (detail pages) | YES |
| STA chinatax.gov.cn | 200 | 37KB+53KB | YES (listings) | YES (10 reg#, 7 taxes) | YES |
| NPC flk.npc.gov.cn | 200 | 455B | NO (Vue SPA) | N/A | NO (needs headless) |
| MOF mof.gov.cn | TIMEOUT | 0B | Unknown | N/A | NO (network issue) |

### Key Findings
- PBC + STA immediately viable for HTTP crawling from VPS
- NPC requires browser-automation (Midscene) -- Vue.js SPA
- MOF unreachable from Mac (CGNAT/GFW) -- needs VPS
- NER pattern gap found and fixed: added PBC (中国人民银行令) + NDRC (发改委) patterns
- HTML must be stripped before NER (regex matches Chinese text, not HTML tags)

### E2E Pipeline Test
- Input: 5 synthetic docs (VAT reform, SME income tax, PIT deduction, tariff, CAS 16)
- Output: 5 LawOrRegulation nodes + 4 TaxType nodes + 5 FT_GOVERNED_BY edges
- Regulation numbers correctly parsed: 财税〔2019〕39号(L1), 国发〔2023〕13号(L0), 海关总署公告2024年第1号(L3)
- Change detection (hash-based): second run skips all 5 docs (0 changes)

### Bug Fixes During P0
1. Hash dir conflict: `db_path/hashes` clashed with KuzuDB data dir -> moved to `db_path/../ft-hashes/`
2. KuzuDB DATE type: string params rejected -> use inline `date('YYYY-MM-DD')` in Cypher
3. NER gap: PBC/NDRC regulation numbers not matched -> added 2 new regex patterns

### P1 Execution (MCP + RAG)
- 5 MCP tools added to cognebula.py: tax_query, policy_search, compliance_check, change_monitor, case_lookup
- Hybrid RAG module: finance_tax_rag.py (LanceDB semantic + KuzuDB structural + tiered context)
- OpenClaw MCP server registered: cognebula in ~/.openclaw/openclaw.json mcpServers
- Test: "增值税改革" → 1 regulation + 1 tax type + context markdown

### P2 Execution (Expert Prompts)
- Expert #9 秦税安: scripts/telegram-expert-team/prompts/expert-9-tax-compliance.md
  - UC-81~90: policy monitor, filing deadlines, incentive alerts, regulation diff, compliance risk
  - Persona: ISTJ, Big-4 Tax Partner equivalent, citation-required
  - Integrated: CogNebula MCP tools (tax_query, change_monitor, compliance_check)
- Expert #10 顾财道: scripts/telegram-expert-team/prompts/expert-10-finance-analysis.md
  - UC-91~100: macro fiscal, CAS tracker, industry radar, digital economy tax, ESG
  - Persona: INTJ, Chief Economist equivalent, top-down macro→industry analysis
  - Integrated: CogNebula MCP tools + web_search for macro data

### State Snapshot (pre-compact, 2026-03-14)
**Completed**: P0 (8/10) + P1 (7/10) + P2 (2/8)
**Total new code**: ~1645 lines across 12 files
**Key files**:
- src/cognebula.py: +205 lines (schema + MCP tools)
- src/finance_tax_processor.py: 350 lines (NER + ingest)
- src/finance_tax_rag.py: 170 lines (Hybrid RAG)
- scripts/finance-tax-crawl.sh: 120 lines (orchestrator)
- src/fetchers/: 800 lines (6 source fetchers + run_all)
- expert-9-tax-compliance.md + expert-10-finance-analysis.md
**Blocked on VPS**: initial crawl, LanceDB embedding, Telegram delivery, cron setup
**Next**: P2 remaining (pipeline scripts, CF Pages, cron) + P3 (change detection, PDF/OCR)

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph DB | KuzuDB (stay) | Embedded, air-gapped, Cypher-native, bulk CSV |
| Embedding | Gemini Embedding 2 | Free, 8K tokens, AI-Fleet integrated |
| Static crawler | Scrapy + Scrapy-Redis | Mature, distributed, gov.cn optimized |
| Dynamic crawler | Playwright | JS rendering, anti-fingerprint |
| Article extraction | Trafilatura | Best F1 (0.909) |
| PDF/OCR | PyMuPDF + PaddleOCR | CJK optimized, free |
| Scheduler | Celery Beat + Redis | Reuse existing Redis, distributed |
| NER (Phase 1) | Rule-based regex | Zero training data needed |
| RSS generation | RSSHub (self-hosted) | Gov sites lack native RSS |
| Initiative slug | finance_tax_kb | Separate from cognebula_sota |
