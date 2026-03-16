# CogNebula Finance/Tax Knowledge Base -- PRD

> v3.1 | 2026-03-15 | Initiative: finance_tax_kb
> v3.1 change: 123 tables (47 node + 76 rel), 7,295 nodes, 11 sources, 1,438 x 3072d vectors, 5,781+ Obsidian files
> v3.0 change: 3-layer architecture (L1法规+L2操作+L3合规, 107 tables) + Knowledge Pipeline (爬取→落档→Obsidian管理→CF发布)
> v2.0 change: China-specific source catalog (50+ sources audited), expanded KuzuDB schema
> v1.1 change: Integrate existing AI-Fleet skill ecosystem (40+ skills) instead of custom Scrapy spiders

## 1. Objective

Build a **SOTA Chinese finance/tax (中国财税) knowledge operating system** on top of CogNebula Enterprise:
- **3-Layer Knowledge Graph**: L1 法规中心 (Regulation) + L2 操作中心 (Operation) + L3 合规中心 (Compliance) -- 123 KuzuDB tables, 47 node types, 76 edge types
- **Knowledge Pipeline**: 7-stage automated: Discover → Crawl (11 active sources) → News → Process (NER+KuzuDB) → Obsidian (5,781+ MD) → Embed (LanceDB 1,438 x 3072d) → Alert
- **Live metrics**: 7,295 nodes / 6,384 edges / 7,026 LawOrRegulation from 11 sources
- **Existing AI-Fleet skill ecosystem** (40+ skills) for content acquisition -- zero custom crawler code
- **China-specific ontology**: 18 tax types, 42 CAS, 91 chart of accounts, 7 lifecycle stages, 6 enterprise types
- Hybrid Graph RAG + 12 MCP tools + OpenClaw integration
- Daily incremental updates with 3-tier change detection
- Full automation: zero human intervention for routine operations

### Architecture Documents
| Document | Lines | Content |
|----------|-------|---------|
| THREE_LAYER_ARCHITECTURE.md | 1170 | L1/L2/L3 schema DDL + Cypher + Mermaid (123 tables) |
| KNOWLEDGE_PIPELINE.md | 831 | 7-stage pipeline: Discover→Crawl→News→Process→Obsidian→Embed→Alert |
| PDCA_STATUS_REPORT_2026-03-15.md | — | Full PDCA status report with competitive benchmark |

### Design Principles
1. **Compose, Don't Build**: Orchestrate 40+ existing AI-Fleet skills, not custom spiders
2. **China-First**: All sources, schema, NER patterns, and expert roles designed for PRC tax system
3. **Authority Hierarchy**: P0 government sources as ground truth; media/community as enrichment only

## 2. Problem Statement

### Pain Points
1. **Information fragmentation**: Tax policies scattered across 30+ government websites (国家税务总局, 财政部, 国务院, 海关总署, 央行...), no unified machine-readable API
2. **Temporal complexity**: Policies have effective/expiry dates, amendments, jurisdictional overrides (国家→省→市), incentive stacking -- manual tracking error-prone
3. **Context gap for AI Agents**: No structured knowledge graph exists for Chinese finance/tax domain that agents can query with Cypher
4. **Compliance lag**: New regulations published daily; 18 税种 × 31 省份 = combinatorial explosion of rules

### Target Users
| User | JTBD | Interaction |
|------|------|------------|
| AI Agent (OpenClaw) | Query tax rules, get structured context for compliance reasoning | MCP tools / REST API |
| Tax Compliance Officer (秦税安) | Monitor regulatory changes, receive alerts on new policies | Telegram digest / Dashboard |
| Finance Analyst (顾财道) | Track macro indicators, industry compliance, standards updates | Telegram digest / Dashboard |
| Product Manager (Maurice) | Build compliance products on top of knowledge base | CLI / API / Dashboard |

## 3. Scope

### In Scope
- **Content acquisition via existing AI-Fleet skills** (no custom spiders):
  - `news-aggregator-skill`: extend with `finance-tax` profile + 8 new source fetchers
  - `agent-reach`: multi-platform crawling (government portals, WeChat)
  - `browser-automation` (Midscene): vision-driven JS page handling (税务总局法规库)
  - `multi-search-engine`: 17-engine discovery (Baidu, Sogou, etc.)
  - `deep-research`: 7-stage GoT synthesis for complex policy analysis
  - `defuddle` / `x-reader`: clean article extraction from any URL
  - `wechat-article-search`: WeChat public account content (mirror-based)
  - `scrapling-crawler`: anti-bot bypass for protected sites
- **KuzuDB schema**: 13 node types + 15 relationship types (China tax ontology)
- **LanceDB vector embeddings** (Gemini Embedding 2 Preview via `bin/embed`)
- **3-tier change detection**: hash + line diff + semantic similarity
- **OpenClaw MCP integration**: 5 new finance-tax query tools
- **Expert Team**: 2 new roles (秦税安 Tax, 顾财道 Finance)
- **Pipeline registration** in AI-Fleet pipeline-registry.json
- **Delivery**: Telegram alert + CF Pages dashboard
- **PDF/OCR**: PyMuPDF + PaddleOCR for government gazettes
- **Orchestration**: `scripts/finance-tax-crawl.sh` (~100 lines, composes skills)

### Out of Scope (v1)
- Custom Scrapy spiders (use existing skill ecosystem)
- 北大法宝 pkulaw.com (institutional paywall + legal risk per PRC Penal Code Art.285)
- 裁判文书网 bulk crawl (optional v2, selective only)
- Province-level tax bureau crawl (redundant with national; maybe top 5 in v2)
- Multi-jurisdiction beyond PRC (v2)
- NER model fine-tuning (rule-based regex first)
- Commercial SaaS packaging

## 4. Data Sources -- China Domestic (中国国内信源全景)

### Tier 1: P0 Critical -- Government Authority (Daily Crawl)

| # | Source | URL | Content | Volume | Structure | Skill |
|---|--------|-----|---------|--------|-----------|-------|
| 1 | 国家税务总局 (non-SPA) | chinatax.gov.cn/chinatax/ | Tax policies, announcements | 132/run | Static HTML | `fetch_chinatax.py` regex | **ACTIVE** |
| 2 | 财政部 政策发布 | mof.gov.cn/zhengwuxinxi/zhengcefabu/ | Fiscal policy, accounting rules | 50/run | Static + regex | `fetch_mof.py` | **ACTIVE** |
| 3 | 中国人民银行 条法司 | pbc.gov.cn/tiaofasi/ | Financial regulations | 10/run | Static HTML | `fetch_pbc.py` | **ACTIVE** |
| 4 | 国家外汇管理局 | safe.gov.cn/safe/ | Forex policy, cross-border | 60/run | Static HTML | `fetch_safe.py` | **ACTIVE** (new 2026-03-15) |
| 5 | 中国证监会 | csrc.gov.cn/csrc/ | Securities regulations | 177/run | Static HTML | `fetch_csrc.py` | **ACTIVE** (new 2026-03-15) |
| 6 | 国家发改委 | ndrc.gov.cn | Development policy | 592/run | Static HTML | `fetch_ndrc.py` | **ACTIVE** (new 2026-03-15) |
| 7 | 中国科学院 | casc.ac.cn | Science/tech policy | 53/run | Static HTML | `fetch_casc.py` | **ACTIVE** (new 2026-03-15) |
| 8 | 国家统计局 | stats.gov.cn | Statistics policy | 30/run | Static HTML | `fetch_stats.py` | **ACTIVE** (new 2026-03-15) |
| 9 | 税务总局法规库 API | fgk.chinatax.gov.cn (JSON) | Tax regulations | 57,073 total | JSON API | `fetch_chinatax_api.py` | **ACTIVE** (breakthrough 2026-03-15) |
| 10 | 会计百科 | baike.kuaiji.com | Accounting wiki | 17K entries | HTML | `fetch_baike_kuaiji.py` | **RUNNING** (2,790+ fetched) |

### Deferred Sources (Need Browser-Automation, P3)

| # | Source | Issue | Workaround |
|---|--------|-------|-----------|
| D1 | 国家税务总局 法规库 (fgk.chinatax.gov.cn) | Pure Vue SPA, 455-byte JS shell | Using non-SPA pages instead |
| D2 | 国家法律法规数据库 (flk.npc.gov.cn) | Pure Vue SPA, API returns 405 | Needs Playwright/Midscene |
| D3 | 海关总署 (customs.gov.cn) | 瑞数信息 WAF, 412 JS challenge | Needs browser-automation |
| D4 | 中国税务网 (ctax.org.cn) | Domain DNS dead | Replaced by CSRC |

### Tier 2: P1 High Value (Daily/Weekly Crawl)

| # | Source | URL | Content | Structure | Skill |
|---|--------|-----|---------|-----------|-------|
| 5 | 中国人民银行 条法司 | pbc.gov.cn/tiaofasi/ | Financial regulations | Static HTML | `agent-reach` |
| 6 | 国务院 涉税政策 | gss.mof.gov.cn/gzdt/zhengcefabu/ | State Council tax decisions | Static | `defuddle` |
| 7 | 中国注册会计师协会 | cicpa.org.cn/.../xxzztx/ | CAS + audit standards | Static HTML | `defuddle` |
| 8 | 国家统计局 | data.stats.gov.cn | Tax collection statistics | Query interface | `browser-automation` |
| 9 | 国家外汇管理局 | safe.gov.cn/beijing/zcfg/ | Cross-border tax policy | Static HTML | `agent-reach` |
| 10 | 商务部 | mofcom.gov.cn/zwgk/zcfb/ | Import/export tax policy | Static + PDF | `defuddle` |

### Tier 3: P2 Professional Media (Daily)

| # | Source | URL | Content | Skill |
|---|--------|-----|---------|-------|
| 11 | 华尔街见闻 | wallstreetcn.com | Macro/fiscal analysis | `news-aggregator` (built-in) |
| 12 | 税屋网 | shui5.cn | Tax practitioner cases + forum | `agent-reach` + `defuddle` |
| 13 | 澎湃新闻 财经 | thepaper.cn | Investigative tax journalism | `news-aggregator` (built-in) |
| 14 | 中国会计视野 | esnai.com | CAS updates, audit practice | `agent-reach` |
| 15 | 第一财经 | yicai.com | Policy interpretation | `news-aggregator` |
| 16 | 中国税务网 | ctax.org.cn | Tax research + opinions | `defuddle` |

### Tier 4: P3 Community & Enrichment (Weekly)

| # | Source | URL | Content | Skill |
|---|--------|-----|---------|-------|
| 17 | 中国会计视野论坛 | bbs.esnai.com | Q&A, case studies | `browser-automation` |
| 18 | 知乎 财税话题 | zhihu.com | Expert discussions | `agent-reach` |
| 19 | 四大中国税务 | kpmg/pwc/ey/deloitte .com/cn | Professional insights | `defuddle` |
| 20 | 36氪 财税标签 | 36kr.com | Fintech/tax-tech | `news-aggregator` (built-in) |

### Skip List (有明确理由)

| Source | Reason |
|--------|--------|
| 北大法宝 pkulaw.com | Institutional paywall ($5K+/yr) + slider CAPTCHA + PRC Art.285 risk |
| 财新网 caixin.com | 50-70% paywall, not official source |
| 中国税务报 ctaxnews.net.cn | Paywall after 4 pages |
| 省级税务局 (31 provinces) | Highly redundant with national site; v2 add top 5 only |

### Skill-to-Source Mapping (Compose, Don't Build)

| Acquisition Task | Primary Skill | Fallback Skill |
|-----------------|--------------|----------------|
| JS-heavy gov sites (税务总局法规库) | `browser-automation` (Midscene vision) | `chrome-bridge-automation` |
| Static gov HTML (财政部, 央行, 海关) | `agent-reach` + `defuddle` | `browser-automation` |
| Anti-bot sites | `scrapling-crawler` | `chrome-bridge-automation` |
| Policy discovery | `multi-search-engine` (Baidu, Sogou...) | `tavily-search` |
| Deep policy analysis | `deep-research` (7-stage GoT) | `grok-search` |
| WeChat expert content | `wechat-article-search` (mirror) | `agent-reach` WeChat |
| News monitoring | `news-aggregator-skill` (finance-tax profile) | `web-multi-search` |
| PDF documents | PyMuPDF + PaddleOCR | `defuddle` (text-layer) |
| Universal URL | `defuddle` / `x-reader` | `agent-reach` |

## 5. Knowledge Graph Schema (China Tax Ontology)

### Node Types (47 types, showing core 13 + 4 new)

| Node Type | Key Properties | Cardinality | Example |
|-----------|---------------|-------------|---------|
| `TaxType` | name, code, rate_range, filing_frequency, liability_type, category, governing_law | 18 | 增值税 0%/6%/9%/13% |
| `TaxpayerStatus` | name, domain(VAT/CIT/PIT), threshold, qualification_criteria | ~10 | 一般纳税人, 小规模纳税人 |
| `EnterpriseType` | name, classification_basis, tax_jurisdiction, global_income_scope | ~8 | 居民企业, 非居民企业, 合伙企业 |
| `PersonalIncomeType` | name, category(综合/分类), rate_structure, standard_deduction | 9 | 工资薪金, 劳务报酬, 经营所得 |
| `LawOrRegulation` | regulation_number, title, issuing_authority, type, effective_date, status, full_text | 50K+ | 国发[2024]15号 |
| `AccountingStandard` | name, cas_number, ifrs_equivalent, scope, difference_from_ifrs | 43 | CAS 16 政府补助 ≈ IAS 20 |
| `TaxIncentive` | name, type(exemption/reduction/deduction/deferral/credit), value, eligibility, combinable | 200+ | 高新技术企业15%优惠税率 |
| `Industry` | gb_code(GB/T 4754-2017), name, level, has_preferential_policy | ~1500 | A01 农业, I65 软件和信息技术 |
| `AdministrativeRegion` | name, type(province/city/district), level(0-4), parent_id | ~3200 | 国家 > 浙江省 > 杭州市 |
| `SpecialZone` | name, type(SEZ/FTZ/DevZone), location, established_date | ~200 | 上海自贸区, 深圳经济特区 |
| `TaxAuthority` | name, level(0-3), parent_id, policy_making_authority | ~3200 | 国家税务总局 > 浙江省税务局 |
| `FilingObligation` | name, tax_type, frequency, deadline, required_documents, penalty | ~50 | 增值税月度申报 (次月15日前) |
| `TaxRateVersion` | tax_type, effective_date, expiry_date, rate, applicable_status | ~100 | 增值税 13% (2019-04-01起) |

### Relationship Types (15 types)

| Relationship | From -> To | Key Properties |
|-------------|-----------|---------------|
| `APPLIES_TO` | TaxType -> TaxpayerStatus | special_treatment |
| `QUALIFIES_FOR` | TaxpayerStatus -> TaxIncentive | priority, combinable |
| `MUST_REPORT` | EnterpriseType -> TaxType | income_scope |
| `GOVERNED_BY` | TaxType -> LawOrRegulation | governance_level, effective_period |
| `MAPS_TO` | AccountingStandard -> LawOrRegulation | mapping_type |
| `AFFECTS` | AccountingStandard -> TaxType | impact_area |
| `APPLIES_TO_TAX` | TaxIncentive -> TaxType | reduction_amount, basis |
| `APPLIES_TO_REGION` | TaxIncentive -> AdministrativeRegion | geographic_scope |
| `SUBJECT_TO` | Industry -> TaxType | rate_applicable, special_rules |
| `OFFERS` | SpecialZone -> TaxIncentive | zone_exclusivity |
| `ADMINISTERS` | TaxAuthority -> AdministrativeRegion | exclusivity |
| `REPORTS_TO` | TaxAuthority -> TaxAuthority | reporting_frequency |
| `REFERENCES` | LawOrRegulation -> LawOrRegulation | type(amends/supersedes/clarifies) |
| `TRIGGERS` | TaxTrigger -> FilingObligation | condition, deferral |
| `SUPERSEDES` | TaxRateVersion -> TaxRateVersion | replacement_date |

### Regulation Numbering Patterns (5 types)

| Pattern | Authority | Hierarchy Level | Regex |
|---------|----------|----------------|-------|
| 国发[YYYY]N号 | State Council | 0 (highest) | `国发\[?\d{4}\]?\d+号` |
| 财税[YYYY]N号 | MOF + SAT Joint | 1 | `财税\[?\d{4}\]?\d+号` |
| 税总发[YYYY]N号 | SAT Issuance | 2 | `税总[办]?发\[?\d{4}\]?\d+号` |
| 国家税务总局公告YYYY年第N号 | SAT Announcement | 3 | `国家税务总局公告\d{4}年第\d+号` |
| 海关通告YYYY年第N号 | Customs | 3 | `海关通告\d{4}年第\d+号` |

### Temporal Model
- **Bitemporal**: `valid_time` (policy effective period) + `transaction_time` (KB record timestamp)
- **Version chain**: `TaxRateVersion` nodes + `SUPERSEDES` edges
- **Status enum**: `active` | `amended` | `repealed` | `pending` | `proposed`
- **Conflict resolution**: Lower hierarchy_level takes precedence (国发 > 财税 > 税总)

## 5b. 3-Layer Schema (v3.0)

The knowledge graph uses a 3-layer architecture. Full DDL in THREE_LAYER_ARCHITECTURE.md.

| Layer | Node Types | Edge Types | Purpose |
|-------|-----------|-----------|---------|
| L1 法规中心 | 17 (TaxType, LawOrRegulation, AccountingStandard, Industry, TaxIncentive...) | 19 (FT_*) | "What are the rules?" |
| L2 操作中心 | 13 (AccountEntry, ChartOfAccount, TaxRateMapping, BusinessScenario, FilingStep, StandardCase, SubAccount...) | 21 (OP_*) | "How do I do it?" |
| L3 合规中心 | 12 (ComplianceRule, RiskIndicator, TaxCalendar, Penalty...) | 19 (CO_*) | "Am I doing it right?" |
| XL 跨层 | 5 | 17 (XL_*) | Connecting 3 layers |
| **Total** | **47 node types** | **76 edge types** | **123 KuzuDB tables** |

## 5c. Knowledge Pipeline (知识沉淀管线)

4-stage Obsidian-Centric pipeline (full design in KNOWLEDGE_PIPELINE.md):

| Stage | Tool | Input | Output |
|-------|------|-------|--------|
| 1. Crawl | finance-tax-crawl.sh (existing) | 20 gov/media sources | JSON in data/raw/ |
| 2. Digest | finance_tax_processor.py + json_to_obsidian.py | Raw JSON | NER-enriched Obsidian MD |
| 3. Manage | Obsidian vault (~/Obsidian/财税知识库/) | MD files with wikilinks + tags | Local knowledge base |
| 4. Publish | CF Pages (ai-fleet-dashboard.pages.dev/finance-tax/) | Vault export | Online searchable dashboard |

**Optional enrichment**: NotebookLM (anything-to-notebooklm skill, manual trigger for podcast/FAQ generation)

**Architecture Decision**: Obsidian-Centric (not NotebookLM-Centric) because NotebookLM OAuth cannot run in unattended cron. See KNOWLEDGE_PIPELINE.md ADR-001.

## 6. Integration Architecture

### OpenClaw MCP Server (7 existing + 5 new tools)

| Tool | Input | Output |
|------|-------|--------|
| `tax_query` | Natural language question | Structured context (regulations + clauses + rates + citations) |
| `policy_search` | Keyword + jurisdiction + tax_type + date | Matching policies with temporal validity |
| `compliance_check` | Industry(GB code) + taxpayer_type + region | Complete obligation checklist + applicable incentives |
| `change_monitor` | Tax_type or regulation_number | Last-N-days changes + diffs |
| `case_lookup` | Dispute topic + jurisdiction | Relevant case precedents |

### Expert Team Extension

| Expert | ID | UC Range | Focus | Sources |
|--------|-----|---------|-------|---------|
| 秦税安 (Tax Compliance) | #9 | UC-81~90 | Policy updates, filing deadlines, audit risk, incentive alerts | Tier 1-2 gov sources |
| 顾财道 (Finance Analysis) | #10 | UC-91~100 | Macro indicators, CAS updates, industry compliance trends | Tier 2-3 media sources |

### Pipeline Registration

```json
{
  "id": "finance-tax-daily-crawl",
  "category": "intelligence",
  "trigger": "cron",
  "schedule": "0 6 * * *",
  "script": "scripts/finance-tax-crawl.sh",
  "defaultDevice": "vps",
  "failoverChain": ["mac"],
  "outputs": ["knowledge-graph-update", "change-alert-telegram", "cf-pages-report"],
  "dependencies": ["heartbeat", "cognebula-api"],
  "sla": {"maxDurationSec": 900, "minSuccessRate": 0.9}
}
```

## 7. Success Metrics

| Metric | Target (v1) | Measurement |
|--------|------------|-------------|
| P0 sources indexed | 4 government authority sources | Source registry |
| Total sources | >= 16 (Tier 1-3) | Source registry |
| Regulations in graph | >= 10,000 nodes (initial load) | KuzuDB node count |
| 18 tax types modeled | 18/18 | Schema check |
| Daily incremental update | < 15 min end-to-end | Pipeline duration |
| Change detection latency | < 24h from publication | Diff timestamp vs source |
| RAG query accuracy | >= 85% P@5 (100 China tax queries) | Manual eval |
| Expert digest quality | >= 4.0/5 user rating | Weekly survey |
| System uptime | >= 99% | Heartbeat monitor |

## 8. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| PRC Penal Code Art.285 (unauthorized access) | HIGH | Only crawl public sources; honor robots.txt; 5s delay; NO CAPTCHA bypass; legal counsel |
| 税务总局法规库 JS rendering | HIGH | `browser-automation` (Midscene vision-driven); fallback: `chrome-bridge` |
| Gov site redesign | MEDIUM | Skill fallback chain: `defuddle` -> `browser-automation` -> `chrome-bridge` |
| No official API (HTML-only) | MEDIUM | NPC法律库 has partial API; others use `multi-search-engine` + hash check |
| PDF OCR accuracy | MEDIUM | PaddleOCR (CJK optimized) + manual review queue |
| Incentive stacking complexity | MEDIUM | `combinable` flag per incentive; HITL for uncertain combinations |
| Regional policy fragmentation | LOW | 4-level AdministrativeRegion hierarchy; lazy load provincial data |
| KuzuDB 100K+ nodes | LOW | Bulk CSV loader; partition by jurisdiction if needed |

## 9. Release Plan

| Phase | Scope | Timeline | DoD | Status |
|-------|-------|----------|-----|--------|
| P0: 3-Layer Schema + Crawlers | 123 tables, 11 fetchers, orchestrator, seed data | Week 1-2 | 7,295 nodes, 11 sources, pipeline running | DONE |
| P1: RAG + MCP + Embeddings | 5 MCP tools, Hybrid RAG, 1,438 embeddings, OpenClaw | Week 3-4 | MCP live, 1,438 x 3072d vectors | DONE |
| P2: Experts + Knowledge Pipeline | 2 experts, Obsidian vault (5,781+ files), CF Pages | Week 5-6 | Vault populated, dashboard live | IN PROGRESS (Telegram pending) |
| P3: Schema Extension + Gap Filling | +4 node tables, +12 edge tables, 65 seed nodes | Week 7 | 123 tables, 10 previously-empty tables seeded | DONE |
| P4: Change Detection + PDF + NotebookLM | 3-tier diff, PDF/OCR, NotebookLM enrichment | Week 7-8 | Tier-1 done, Tier-2/3 + PDF pending | IN PROGRESS |
| P5: Scale to 30K+ nodes | baike_kuaiji (17K), doc-tax (1.9K files), deep pagination | Week 9-10 | 30K+ nodes, comprehensive L2/L3 | IN PROGRESS |

---

Maurice | maurice_wen@proton.me
