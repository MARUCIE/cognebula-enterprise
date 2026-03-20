# Finance/Tax Knowledge Base -- Task Plan

## Objective
Build a SOTA AI-native Chinese finance/tax knowledge base on KuzuDB graph database.
- **M1 (100K)**: DONE (2026-03-16). Post-fix: 87,701 nodes.
- **M2 (500K)**: IN PROGRESS. QA pipeline running, target 500K by ~2026-03-27.
- **M3 (1M)**: PLANNED. 16 weeks, ~$350 budget.
- Target: AI Agent that can autonomously do bookkeeping, tax filing, audit, compliance.

## Current State (2026-03-20)
- **Nodes**: 407,848 (17 v2 types + legacy)
- **Edges**: 860,320 (36 v2 edge types)
- **Density**: 2.109
- **Quality**: 100/100 PASS
- **Schema**: v3.1 (17 nodes x 36 edges, EXPLAINS split into 6 types)
- **Platform**: Unified Tab Shell at http://100.75.77.112:8400
  - Explore: KG Explorer (vis.js, Chinese edge labels + color coding)
  - Curate: Know-Arc Expert Workbench (integrated at /api/v1/ka/*)
  - Admin: Real-time dashboard (live edge distribution from API)
- **GitHub**: MARUCIE/cognebula-enterprise (10+ commits today)

## Active (Running Now)
- [x] M3 QA pipeline (cron 02:00 UTC daily, 5000 articles/run, ~14K QA/day)
- [x] Daily crawl pipeline (cron 10:00 UTC, 22 crawlers, content depth flags enabled)
- [x] Know-Arc integration (23 endpoints at /api/v1/ka/*, same-origin iframe)
- [ ] M3 QA scale-up: 42K articles total, ~7 days to M2 500K milestone

## Completed Today (2026-03-20)
- [x] EXPLAINS split: 475K edges -> 6 precise types (INTERPRETS/EXEMPLIFIED_BY/EXPLAINS_RATE/WARNS_ABOUT/DESCRIBES_INCENTIVE/GUIDES_FILING)
- [x] DDL v3.1: 17 nodes x 36 edge types
- [x] API V2_EDGES whitelist updated (36 types, quality density 3.977)
- [x] Design doc v3.1 (McKinsey Blue, updated)
- [x] KG Explorer: Chinese edge labels + 36-type color coding
- [x] Admin dashboard: real-time edge distribution from /api/v1/stats
- [x] Git cleanup: removed 9.9GB doc-tax + 684MB backups from repo
- [x] Know-Arc system integration (APIRouter merge, /api/v1/ka/*)
- [x] M3 QA generation pipeline (gemini-2.5-flash-lite, tested + deployed)
- [x] M3 orchestrator + cron setup
- [x] Daily pipeline depth fix (--fetch-content flags)
- [x] Swarm audit: 3-agent review (crawl quality + missing sources + systems dynamics)
- [x] INTERPRETS analysis: confirmed 82% rate is valid (76% mind-map nodes)
- [x] Know-Arc injection pipeline framework (entity/predicate mapping)

## Swarm Audit Findings (2026-03-20)
### Crawl Depth Crisis
- 4/22 crawlers (18%) fetch full text — SOTA quality
- 10/22 crawlers (45%) title-only — daily_pipeline.sh was missing --fetch-content
- 3/22 crawlers (14%) broken/unused
- FIX APPLIED: daily_pipeline.sh now passes content flags + per-crawler timeouts

### Missing Data Sources (18 identified)
P0: flk.npc.gov.cn (17K laws), cicpa.org.cn, cctaa.cn
P1: aifa.org.cn (ASBE), pbc.gov.cn/data, chinamoney.com.cn, epub.cnipa.gov.cn
P2: splcgk.court.gov.cn (100K cases), qcc.com, pkulaw.com, shui5.cn

### Density Paradox
- Target density 6.0 = 6M edges for 1M nodes
- Current: 860K edges — need +5.14M
- Edge growth must be 7x node growth
- Leverage: depth (existing source full-text) > breadth (new sources)

## M3 Roadmap
- Phase 1 (W1-4): L1 deepening — QA generation + content depth fix (+150K)
- Phase 2 (W5-10): L2 new sources — 8 new crawlers (+200K)
- Phase 3 (W11-14): L3 AI synthesis + L4 crowdsource (+150K)
- Phase 4 (W15-16): Final gate + optional engine migration
- Gates: 500K / 600K / 700K / 850K / 1M

## Key Risks
- KuzuDB archived (Apple acquisition) — single-writer lock limits concurrency
- Density dilution: adding nodes without edges degrades quality
- chinatax_api 57K docs need detail fetch (snippet-only currently)
- Court data (裁判文书网) has anti-crawling (DES3 encryption)

---
Maurice | maurice_wen@proton.me
