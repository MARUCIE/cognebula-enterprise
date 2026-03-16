# CogNebula Finance/Tax Knowledge Base -- Platform Optimization Plan

> v4.0 | 2026-03-16 | Initiative: finance_tax_kb
> v4.0 change: **M1 DONE**: 87,701 nodes (100K achieved then purged 12.5K low-quality), 92,495 edges, orphan 20.5%, 768d vectors rebuilding. M2 (500K) planned.
> v3.2 change: 13,660 nodes, 273 RiskIndicators, 131 StandardCases, 43 BusinessScenarios, 27 industries, doc-tax 5-layer extraction
> v3.1 change: 123 tables, 7,295 nodes, 11 sources, 1,438 vectors, 5,781+ Obsidian files, competitive benchmark
> v3.0 change: 3-layer schema (107 tables) + Knowledge Pipeline (Obsidian→CF Pages) + 65 fleet pipelines
> v1.1 change: Replace custom Scrapy stack with AI-Fleet skill composition

## 1. Optimization Goals

| Goal | Current State | Target State | Metric |
|------|--------------|-------------|--------|
| Knowledge coverage | 0 finance/tax nodes | 100K+ nodes (M1) | Node count | **87,701 nodes (M1 DONE, post-quality-fix)** |
| Source breadth | 0 sources | 15+ government/professional | Source registry | **14 fetchers, 11 active sources** |
| Update freshness | Manual | < 24h automated | Crawl-to-graph latency | **Dual-batch cron 10:00+15:00 UTC** |
| Query accuracy | N/A | >= 85% Precision@5 | Manual eval 100 queries | **Pending eval (auto-pipeline queued)** |
| Integration depth | Code-only MCP | Code + Finance MCP tools | Tool count | **12 MCP tools live** |
| Graph connectivity | N/A | >= 3.0 edges/node | Edge density | **1.05 edges/node (92,495 edges, from 0.46)** |
| Orphan rate | N/A | < 5% | Orphan % | **20.5% (from 91.7%, P0 edge enrichment done)** |
| Schema coverage | 0 tables | 100+ tables | Table count | **84 REL + node tables (inc. LR_ABOUT_TAX/INDUSTRY)** |
| Embedding coverage | 0 vectors | 100% indexed | Vector count | **57,566 x 768d rebuilding (51% done)** |
| Obsidian vault | 0 files | 10,000+ files | File count | **5,781+ markdown files** |

## 2. Technology Stack Decisions

| Component | Choice | Rationale | Alternatives Considered |
|-----------|--------|-----------|------------------------|
| Graph DB | **KuzuDB** (existing) | Embedded, Cypher-native, bulk CSV loader, air-gapped | Neo4j (too heavy), NebulaGraph (distributed overkill) |
| Vector DB | **LanceDB 0.29.2** | Already in CogNebula, zero-config, 438 docs indexed | Milvus (separate infra), Qdrant (unnecessary) |
| Embedding | **Gemini Embedding 2 Preview (768d Matryoshka)** | Free preview, 768d for M2 scalability (was 3072d), via CF Worker proxy, 57K vectors rebuilding | OpenAI (paid), Jina (less Chinese coverage) |
| Content acquisition | **AI-Fleet skill ecosystem** | 40+ production-ready skills, zero custom spiders | Custom Scrapy (unnecessary new code) |
| Static HTML crawling | **agent-reach + defuddle** | 13+ platform support, clean extraction | Scrapy (reinventing the wheel) |
| Dynamic JS pages | **browser-automation** (Midscene) | Vision-driven, no DOM selectors needed | Playwright raw (more code) |
| Anti-bot bypass | **scrapling-crawler** | Cloudflare Turnstile bypass built-in | Custom middleware (fragile) |
| Policy discovery | **multi-search-engine** | 17 engines, zero API keys | Single search engine (limited) |
| Deep analysis | **deep-research** (GoT) | 7-stage pipeline, multi-agent | Manual synthesis (slow) |
| Content extraction | **defuddle / x-reader** | Universal URL → clean text | Trafilatura (good but not integrated) |
| WeChat content | **wechat-article-search** | Mirror-based, safer than direct scraping | Direct WeChat API (risky) |
| News monitoring | **news-aggregator-skill** | 28 sources built-in, extensible | Custom RSS reader (redundant) |
| PDF extraction | **PyMuPDF + PaddleOCR** | PaddleOCR best for CJK | Tesseract (poor Chinese) |
| Scheduler | **Fleet pipeline cron** | 62 pipelines proven, failover chains | Celery Beat (new dependency) |
| RSS generation | **RSSHub** (self-hosted) | Gov sites lack RSS | Manual polling (fragile) |
| NER (Phase 1) | **Rule-based regex** | Zero training data needed | spaCy (needs corpus) |

## 3. Phase Execution Plan

### P0: Foundation (Week 1-2)

**Goal**: KuzuDB schema + skill-based acquisition pipeline + initial data load

| Task | Owner | DoD |
|------|-------|-----|
| Create finance-tax node/edge tables in cognebula.py | Dev | Schema loads without error |
| BulkLoader extension for finance node types | Dev | CSV bulk import works |
| `finance-tax-crawl.sh` orchestrator script | Dev | Composes skills, runs end-to-end |
| `finance_tax_processor.py` (NER + change detect + ingest) | Dev | Parses JSON -> KuzuDB nodes |
| news-aggregator-skill: add `finance-tax` profile + 6 source fetchers | Dev | `fetch_news.py --profile finance-tax` works |
| Test: agent-reach + defuddle on chinatax.gov.cn | Dev | Extracts policy list + full text |
| Test: browser-automation on mof.gov.cn (JS pages) | Dev | Vision-driven extraction works |
| Test: multi-search-engine for policy discovery | Dev | Returns relevant gov URLs |
| Pipeline registration in pipeline-registry.json | Dev | `finance-tax-daily-crawl` registered |
| VPS cron setup for daily 06:00 UTC run | Ops | Cron running, heartbeat green |
| Initial full crawl via skill pipeline | Dev | >= 5000 nodes in KuzuDB |

**Verification**: `cognebula status --repo finance-tax` shows 5000+ nodes, 10K+ edges

### P1: RAG + MCP Integration (Week 3-4)

**Goal**: 5 new MCP tools, LanceDB embeddings, OpenClaw integration

| Task | Owner | DoD |
|------|-------|-----|
| LanceDB table: finance_tax_embeddings | Dev | Embeddings stored, searchable |
| Embed all regulations via Gemini Embedding 2 | Dev | 5000+ embeddings generated |
| MCP tool: tax_query | Dev | Returns relevant context |
| MCP tool: policy_search | Dev | Filters by jurisdiction + date |
| MCP tool: compliance_check | Dev | Returns obligations checklist |
| MCP tool: change_monitor | Dev | Returns last-24h changes |
| MCP tool: case_lookup | Dev | Returns relevant precedents |
| Hybrid RAG: semantic + graph traversal | Dev | Combined results > either alone |
| OpenClaw MCP server registration | Dev | `cognebula` in openclaw.json mcpServers |
| Query accuracy eval (100 test queries) | QA | Precision@5 >= 80% |

**Verification**: OpenClaw can answer "软件企业增值税优惠" with grounded citations

### P2: Expert Team + Delivery (Week 5-6)

**Goal**: 2 new experts, Telegram digest, CF Pages dashboard

| Task | Owner | DoD |
|------|-------|-----|
| Expert #9 秦税安 prompt (UC-81~90) | PM | Prompt in scripts/telegram-expert-team/prompts/ |
| Expert #10 顾财道 prompt (UC-91~100) | PM | Prompt in scripts/telegram-expert-team/prompts/ |
| Pipeline: finance-tax-daily-crawl | Dev | Registered in pipeline-registry.json |
| Pipeline: finance-tax-morning-digest | Dev | 09:30 CST delivery |
| Telegram alert template | Dev | New policy notification format |
| CF Pages: /finance-tax/ dashboard | Dev | Timeline + browse + search views |
| VPS cron job setup (2 new jobs) | Ops | Cron running, heartbeat green |
| Expert team integration test | QA | Digest delivered to Telegram |

**Verification**: Telegram receives morning finance digest; CF Pages shows timeline

### P3: Change Detection + PDF (Week 7-8)

**Goal**: 3-tier change detection, PDF/OCR pipeline

| Task | Owner | DoD |
|------|-------|-----|
| Hash-based change detection (Tier 1) | Dev | SHA256 per-page, hourly check |
| Diff-based change detection (Tier 2) | Dev | unified_diff on changed pages |
| Semantic change detection (Tier 3) | Dev | Embedding cosine < 0.95 triggers alert |
| Version chain in KuzuDB (SUPERSEDES edges) | Dev | Queryable version history |
| Git archival of raw HTML (audit trail) | Dev | Every change committed |
| PyMuPDF text extraction | Dev | PDF -> text with layout |
| PaddleOCR integration | Dev | Scanned PDF -> text |
| pdfplumber table extraction | Dev | Tables -> JSON |
| Tier-2 source fetchers (cicpa, ctax, esnai) | Dev | 3 new fetch_*.py in news-aggregator |
| End-to-end pipeline stress test | QA | 24h unattended run, zero crashes |

**Verification**: Policy change on chinatax.gov.cn detected within 24h, alert sent

## 4. Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Full crawl (15 sources) | < 30 min | Pipeline duration |
| Incremental crawl (changes only) | < 10 min | Pipeline duration |
| Single MCP query | < 3s | MCP round-trip time |
| Embedding generation (100 docs) | < 60s | Batch processing time |
| Graph traversal (3-hop) | < 500ms | KuzuDB Cypher execution |
| Change detection (1 source) | < 5s | Hash + diff time |
| Docker cluster startup | < 30s | `docker-compose up` to healthy |

## 5. Cost Model

| Resource | Monthly Cost | Notes |
|----------|-------------|-------|
| Gemini Embedding 2 (preview) | $0 | Free during preview |
| Gemini Embedding 2 (GA) | ~$10 | Est. 50K docs/month @ $0.20/1M tokens |
| VPS compute (existing) | $0 incremental | Crawler runs on existing VPS |
| Redis (existing) | $0 incremental | Reuses CogNebula Redis |
| CF Pages (existing) | $0 | Free tier sufficient |
| Brave Search API (existing) | $0 | 2000/month free tier |
| PaddleOCR | $0 | Open-source, local compute |
| RSSHub | $0 | Self-hosted Docker |
| **Total incremental** | **~$0-10/month** | |

## 6. Risk Mitigations

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|-----------|-------|
| Gov site layout change | Medium | High | Skill fallback chain: defuddle -> browser-automation (vision) -> chrome-bridge | Dev |
| KuzuDB 100K+ node perf | Low | Medium | Bulk CSV loader; partition by jurisdiction if needed | Dev |
| Embedding API rate limit | Low | Low | Batch with backoff; fallback to text search | Dev |
| Crawler IP block | Medium | Medium | scrapling-crawler (anti-bot) + 5s delay + skill UA rotation | Ops |
| PaddleOCR accuracy < 90% | Medium | Medium | Manual review queue; priority on text-layer PDFs | QA |
| Skill ecosystem update | Low | Low | Skills are git-tracked; version-pinned; SKILL-MANIFEST.json integrity | Dev |

## 7. Success Criteria (v1 DoD)

- [x] >= 5000 regulation nodes in KuzuDB (current: 13,660 nodes / 12,952 LawReg -- **273% of 5K target**) -- 2026-03-15
- [x] >= 5 sources crawled daily (11 active + doc-tax local) -- 2026-03-15
- [x] 5 new MCP tools operational (tax_query, policy_search, compliance_check, change_monitor, case_lookup) -- 2026-03-14
- [x] OpenClaw can answer finance/tax queries with citations (MCP server registered) -- 2026-03-14
- [ ] Daily Telegram digest delivered (09:30 CST) -- experts ready, template pending
- [x] CF Pages dashboard live with timeline view (/finance-tax/index.html Bloomberg-style) -- 2026-03-15
- [x] Change detection working: SHA256 hash-based (Tier 1) in finance_tax_processor.py -- 2026-03-15
- [x] Schema expanded: 123 tables (47 node + 76 rel) with +4 node tables + 12 edge tables -- 2026-03-15
- [x] Gap filling: 65 seed nodes + 106 seed edges across 10 previously-empty tables -- 2026-03-15
- [x] Embedding coverage: 1,438 x 3072d vectors in LanceDB -- 2026-03-15
- [x] Obsidian vault: 5,781+ markdown files with wikilinks + tags -- 2026-03-15
- [x] doc-tax 5-layer extraction: 28 industry guides + 14,270 mindmap nodes + 66 tax burden rates + 30 warning indicators -- 2026-03-15
- [x] L2 enrichment: 43 BusinessScenarios + 131 StandardCases + 27 industries covering 19 sectors -- 2026-03-15
- [x] L3 enrichment: 273 RiskIndicators (industry benchmarks + warning thresholds + credit scoring) -- 2026-03-15
- [ ] 24h unattended stress test passed -- dual-batch cron running, needs formal 24h test
- [ ] Query accuracy >= 85% Precision@5 -- LanceDB 3072d index ready, eval pending
- [ ] LanceDB vector rebuild (1,438 vectors for 13,660 nodes -- needs full reindex)
- [x] Zero security incidents (no secrets exposed, no IP bans) -- 2026-03-15

### Execution Status (2026-03-15)

| Phase | Status | Evidence |
|-------|--------|----------|
| P0 Foundation | **DONE** | 13,660 nodes, 12 sources, dual-batch cron, 7-stage pipeline |
| P1 RAG + MCP | **DONE** | LanceDB 1,438×3072d, 12 MCP tools, Hybrid RAG live |
| P2 Expert + Delivery | **PARTIAL** | 2 experts ready, dashboard live, 9,781+ Obsidian files, Telegram pending |
| P3 Schema Extension | **DONE** | 123 tables (47 node + 76 rel), 65 seed nodes, 106 seed edges |
| P4 Change Detection | **PARTIAL** | Tier-1 hash done, Tier-2/3 + PDF pending |
| P5 Scale to 30K+ | **IN PROGRESS** | 13,660/30K (45.5%), doc-tax extracted, baike running |
| P6 doc-tax Enrichment | **DONE** | 5-layer extraction: 28 guides, 14K mindmap, 66+30+47 indicators, 76 rules, 109 templates |

---

Maurice | maurice_wen@proton.me
