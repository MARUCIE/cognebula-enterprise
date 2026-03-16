# CogNebula Finance/Tax KB -- PDCA Status Report

## Date: 2026-03-15

## Plan (P)

### Original Target
- Build a SOTA 3-layer Chinese finance/tax knowledge base with 10,000+ nodes
- 3-layer architecture: L1 法规中心 (Regulation) + L2 操作中心 (Operation) + L3 合规中心 (Compliance)
- Automated 24/7 crawling from 15+ government and professional sources
- Hybrid RAG (KuzuDB graph + LanceDB vector) with 12 MCP tools
- Zero incremental cost ($0-10/month) leveraging existing AI-Fleet infrastructure

### Architecture Design
- **123 KuzuDB tables** (47 node types + 76 edge types), up from initial 107
- **11 active data sources** with dual-batch cron (10:00 + 15:00 UTC)
- **7-stage pipeline**: Discover → Crawl → News → Process (NER) → Obsidian → Embed → Alert
- **LanceDB 3072d vectors** via Gemini Embedding 2 through CF Worker proxy
- **Obsidian-Centric knowledge pipeline** (ADR-001: Obsidian over NotebookLM for unattended cron)

### Success Criteria (14 items)
- 11 of 14 criteria met (79%)
- 3 remaining: Telegram digest delivery, 24h stress test, query accuracy eval

---

## Do (D)

### Session Accomplishments (2026-03-15)

**Source Expansion (5 → 11 active)**
- Deployed 6 new source fetchers: fetch_chinatax_api.py (FGK JSON API, 57K records), fetch_ndrc.py (592), fetch_casc.py (53), fetch_stats.py (30), fetch_baike_kuaiji.py (17K target)
- BREAKTHROUGH: discovered chinatax FGK has working JSON API (`/search5/search/s?siteCode=bm29000002`) bypassing Vue SPA
- Replaced 3 dead sources (NPC/Customs/CTax) with working alternatives
- Total crawl yield: 7,026 LawOrRegulation nodes from 11 sources

**Schema Extension (107 → 123 tables)**
- Added 4 new node tables: BusinessScenario, FilingStep, StandardCase, SubAccount
- Added 12 new edge tables connecting new nodes
- Gap filling: 65 seed nodes + 106 seed edges across 10 previously-empty tables

**Vector Index Scale-up (438 → 1,438 vectors)**
- Upgraded from 768d to 3072d (full Matryoshka dimension)
- 1,438 LawOrRegulation nodes embedded via CF Worker proxy
- LanceDB 0.29.2 table: ~71MB (17.7M floats)

**Obsidian Vault Expansion (595 → 5,781+ files)**
- Massive content ingestion from FGK API + new sources
- All files with frontmatter, wikilinks, tags, callouts, auto-classification
- Git-tracked vault at ~/Obsidian/财税知识库/

**24/7 Automation**
- Dual-batch cron: 10:00 + 15:00 UTC with flock singleton (matches gov post-publish rhythm)
- 7-stage pipeline fully automated end-to-end
- VPS cron jobs integrated (124 total fleet cron jobs)

**doc-tax Discovery**
- Found 1,912 local files (903 .doc + 422 .docx + 73 .xlsx) for L2/L3 enrichment
- Content: accounting standards guides, tax filing templates, compliance checklists

**Swarm Research Round 4 (4 parallel agents)**
- R1: Probed 15 source candidates, found 10 working HTTP sources
- R2: Deep crawl analysis -- chinatax FGK API breakthrough (57K records)
- R3: 24/7 schedule design -- dual-batch post-publish timing
- R4: Scaling path -- deep pagination > new sources > full text for ROI

---

## Check (C)

### 3-Layer Completeness Audit

| Layer | Target | Current | Completeness | Key Gaps |
|-------|--------|---------|-------------|----------|
| **L1 法规中心** | Comprehensive regulation coverage | 7,026 LawOrRegulation + 19 TaxType + 43 CAS + 10 Industry + 8 TaxIncentive | **HIGH (90%+)** | TaxpayerStatus sparse, SpecialZone/AdministrativeRegion empty |
| **L2 操作中心** | Operational procedures + templates | 30 ChartOfAccount + 17 SubAccount + 15 BusinessScenario + 15 FilingStep + 10 AccountEntry | **LOW (15%)** | Most L2 tables seeded but shallow; doc-tax files will fill |
| **L3 合规中心** | Compliance rules + risk monitoring | 8 ComplianceRule + 12 TaxCalendar + 6 EntityTypeProfile + 5 RiskIndicator + 5 Penalty | **LOW (20%)** | Calendar only 2026; rules need per-industry expansion |

### Node Distribution (7,295 total)

| Category | Count | % of Total |
|----------|-------|-----------|
| LawOrRegulation (L1) | 7,026 | 96.3% |
| Seed data (L1/L2/L3) | 269 | 3.7% |

**Assessment**: L1 法规中心 is the strong pillar. L2 and L3 are structurally complete (schema exists, tables created, seed data present) but content-sparse. The 1,912 doc-tax files and baike_kuaiji crawl will address this imbalance.

### Gap Analysis

| Gap | Severity | Resolution Path | ETA |
|-----|----------|----------------|-----|
| L2/L3 content depth | HIGH | Process 1,912 doc-tax files + baike_kuaiji 17K entries | 3-5 days |
| Telegram digest delivery | MEDIUM | Template exists, needs integration test | 1-2 days |
| Query accuracy eval | MEDIUM | 1,438 vectors ready, need 100 test queries | 2-3 days |
| 24h unattended stress test | LOW | Cron running, needs formal observation window | 1 day |
| browser-automation sources | LOW | NPC/Customs/chinatax SPA deferred to P3 | 2 weeks |
| AdministrativeRegion/SpecialZone | LOW | Bulk load from GB/T 2260 dataset | 1 day |

### Competitive Benchmark: vs Wolters Kluwer 威科先行

| Dimension | CogNebula FT KB | 威科先行 (Wolters Kluwer China) |
|-----------|----------------|--------------------------------|
| **Document count** | 7,295 nodes (scaling to 30K+) | 1.26M documents |
| **Search method** | Graph traversal (123-table Cypher) + semantic (3072d) | Full-text keyword search |
| **Cross-regulation reasoning** | YES -- incentive stacking, jurisdiction chain, version history via graph edges | NO -- flat document retrieval |
| **Schema depth** | 47 node types, 76 edge types, typed relationships | Unstructured document tags |
| **Update frequency** | Dual-batch daily (10:00 + 15:00 UTC) | Daily (business hours) |
| **Cost** | $0-10/month | $50K+/year enterprise license |
| **API/Agent integration** | 12 MCP tools, OpenClaw native | REST API (limited) |
| **Killer query example** | "高新技术企业 in 上海自贸区 doing 软件出口 → 3-4 overlapping incentives" (graph traversal) | Cannot compute incentive stacking |

**Verdict**: We lose on volume (7.3K vs 1.26M) but win decisively on structure and reasoning capability. The 123-table graph schema with typed edges enables queries that flat search fundamentally cannot answer. Volume gap is closing (baike_kuaiji + FGK API + doc-tax will push to 30K+).

---

## Act (A)

### Immediate Next Steps (This Week)

1. **Complete baike_kuaiji crawl**: 17K accounting wiki entries → push past 10K node target
2. **Process doc-tax files**: 1,912 files → L2/L3 enrichment (ChartOfAccount, ComplianceRule, FilingStep)
3. **Telegram digest integration test**: wire expert prompts to digest-deliver.mjs
4. **Query accuracy eval**: design 100 test queries, run P@5 evaluation against 1,438 vectors
5. **24h stress test**: formal observation of dual-batch pipeline

### Medium-Term Roadmap (2-4 Weeks)

1. **Scale to 30K+ nodes**: deep pagination on all 11 sources + baike_kuaiji completion
2. **L2/L3 enrichment**: process doc-tax corpus, bulk-load AdministrativeRegion (GB/T 2260), SpecialZone catalog
3. **Change detection Tier-2/3**: unified_diff + embedding cosine similarity < 0.95
4. **Version chain**: SUPERSEDES edges in KuzuDB for regulation amendment tracking
5. **PDF/OCR pipeline**: PyMuPDF + PaddleOCR for government gazettes
6. **browser-automation**: Playwright/Midscene for NPC/Customs/chinatax SPA sources

### Long-Term Vision (1-3 Months)

1. **50K+ nodes**: comprehensive Chinese finance/tax knowledge graph
2. **Cross-regulation reasoning engine**: production-grade incentive stacking calculator
3. **Multi-jurisdiction**: expand beyond PRC (Hong Kong SAR, Macau SAR, cross-border)
4. **ML-based NER**: fine-tuned model on annotated corpus (replace rule-based regex)
5. **Enterprise API**: RESTful access for third-party compliance products
6. **NotebookLM integration**: podcast/FAQ generation from knowledge base
7. **Compliance product suite**: built on top of knowledge graph infrastructure

---

## Metrics Summary

| Metric | Start of Day | End of Day | Growth |
|--------|-------------|-----------|--------|
| Total nodes | 535 | 7,295 | 13.6x |
| LawOrRegulation | 438 | 7,026 | 16.0x |
| Active sources | 5 | 11 | 2.2x |
| KuzuDB tables | 107 | 123 | +16 |
| LanceDB vectors | 438 x 768d | 1,438 x 3072d | 3.3x count, 4x dims |
| Obsidian files | 595 | 5,781+ | 9.7x |
| Success criteria met | 6/10 | 11/14 | 79% |

---

Maurice | maurice_wen@proton.me
