# Finance/Tax Knowledge Base -- Task Plan

## Objective
Build a SOTA AI-native Chinese finance/tax knowledge base on KuzuDB graph database.
- **M1 (100K)**: DONE (2026-03-16). Post-fix: 87,701 nodes, 92,495 edges.
- **M2 (500K)**: IN PLANNING. 3 phases, 18 weeks, ~$107 budget.
- Target: AI Agent that can autonomously do bookkeeping, tax filing, audit, compliance.

## Current State (2026-03-16)
- **Nodes**: 87,701 (was 100,239, purged 12,538 low-quality)
- **Edges**: 92,495 (was 45,158, +105% from edge enrichment)
- **Orphan rate**: 20.5% (was 91.7%)
- **Edge density**: 1.05 (target: 3.0)
- **LanceDB**: rebuilding 57,566 vectors x 768d (51% complete)
- **GitHub**: MARUCIE/cognebula-enterprise (3 Mac commits + 1 VPS local)

## Active (Running Now)
- [x] LanceDB 768d full rebuild (VPS background, ETA ~3h)
- [x] Post-rebuild auto-pipeline: P@5 → clause split → embed (waiting)

## Pending (After Rebuild Completes)
- [ ] P@5 precision evaluation (100 test queries, target >= 85%)
- [ ] Phase 1 clause split v2 (dry-run → execute)
- [ ] Incremental embedding of new clause nodes
- [ ] PDF injection (7,140 nodes from 98 doc-tax PDFs)

## Backlog (M2 Preparation)
- [ ] Provincial fetcher fix (Hanweb API hanging)
- [ ] ChinaAcc deep crawl (complete remaining 37 sections)
- [ ] Tax classification code expansion (4,205 → full 5-level hierarchy)
- [ ] Judicial cases fetcher (裁判文书网)
- [ ] International tax treaties (109 DTAs)
- [ ] Social insurance regulations fetcher
- [ ] browser-automation for NPC/Customs/chinatax法规库 (needs Playwright)
- [ ] Telegram alert template
- [ ] CF Pages finance-tax dashboard
- [ ] Change detection Tier 2-3 (diff + cosine similarity)
- [ ] NotebookLM integration

---

## M1: 100K Milestone -- COMPLETED

### M1 Achievement (2026-03-16 03:30 UTC)
- [x] 100,239 nodes achieved via: crawling + AI synthesis + clause splitting + cross-product matrix
- [x] Sources: chinatax FGK API (5,427), 12366 hotline (5,246), ChinaAcc (1,973), doc-tax local (3,504), AI synthesis (11,238), cross-product (15,000+), mindmap (926), NDRC (590), HSCode (23,342), TaxClassCode (4,205), RegulationClause (10,551)

### M1 Quality Gate (2026-03-16 03:40 UTC)
- [x] Verdict: CONDITIONAL PASS
- [x] P0-2 Template Purge: -11,760 single-sentence placeholders -778 duplicates
- [x] P0-1 Edge Enrichment: +47,337 edges (new LR_ABOUT_TAX + LR_ABOUT_INDUSTRY tables)
- [x] P0-3 LanceDB Rebuild: 768d Matryoshka via CF Worker proxy (in progress)
- [x] Retrospective: M1_QUALITY_GATE_RETROSPECTIVE.html

### M1 Key Lessons
1. Edge-first: 91.7% orphan rate = document store, not knowledge graph
2. No template filler: single-sentence nodes (avg 56 chars) pollute vector index
3. Quality gates at milestones, not after
4. KuzuDB single-process lock blocks parallel operations

---

## M2: 500K Milestone -- PLANNED

### Phase 1: Clause-Level Deep Split (+180K, W1-4)
- [ ] Full regulation → Article/Paragraph/Item split (~120K clauses)
- [ ] Clause-level QA generation via Gemini (~60K QA pairs)
- [ ] Mini Gate 1 at 150K: orphan < 15%, density > 1.5

### Phase 2: Source Expansion (+150K, W5-12)
- [ ] Provincial tax bureau policies (31 provinces, ~46.5K)
- [ ] ChinaAcc deep crawl (full 39 sections, ~28K)
- [ ] Tax classification expansion (full 5-level, ~38K)
- [ ] Judicial cases (~12K)
- [ ] International tax treaties (~15K)
- [ ] Social insurance regulations (~10K)
- [ ] Mini Gate 2 at 250K: P@5 >= 75%, L1 >= 50%
- [ ] Mini Gate 3 at 350K: P@5 >= 80%, orphan < 8%

### Phase 3: AI Synthesis + Cross-Reference (+82K, W13-16)
- [ ] Industry × Tax × Scenario enriched matrix (~25K, Multi-Swarm QC 70%)
- [ ] Temporal version chains (~8K)
- [ ] Regulation → Journal Entry mapping (~15K)
- [ ] Risk indicator expansion (~12K)
- [ ] Cross-regulation reference edges (~22K edges only)

### M2 Final Gate (W17-18)
- [ ] P@5 >= 85%, orphan < 5%, edge density >= 3.0
- [ ] Production readiness check
- [ ] Competitive comparison vs Wolters Kluwer

---

## Completed Sprints (Historical)

### Sprint 0-2 (2026-03-14 ~ 2026-03-16)
- [x] KuzuDB 123 tables (47 node + 76 rel)
- [x] 11 active web crawl sources
- [x] 14 fetcher scripts + 20 injection scripts + 6 generation scripts
- [x] Multi-Swarm AI synthesis pipeline (49% acceptance)
- [x] 3-tier backup: GitHub + CSV + tar.gz
- [x] CF Browser Rendering Worker
- [x] 5 MCP tools + Hybrid RAG + OpenClaw integration
- [x] Expert #9 秦税安 + Expert #10 顾财道
- [x] LanceDB 13,445 → 57,566 vectors (768d, rebuilding)
- [x] 4 HTML deliverables (McKinsey Blue + Bloomberg Terminal styles)
- [x] doc-tax 5-layer extraction (28 industry guides, 66 tax burden rates, CPA materials)
- [x] Cross-product matrix generators (7 scripts)
- [x] M1 quality gate + P0 fixes (edge enrichment, template purge, dedup)
- [x] M2 scaling plan HTML
- [x] Phase 1 clause split v2 + incremental embedder + P@5 eval scripts

## Architecture
- **4-Layer**: L1 Regulation + L2 Operation + L3 Compliance + L4 Intelligence
- **KuzuDB**: embedded, VPS `data/finance-tax-graph`
- **LanceDB**: `data/finance-tax-lance` (768d Matryoshka)
- **84 edge tables** including LR_ABOUT_TAX, LR_ABOUT_INDUSTRY
- **CF Worker proxy**: `gemini-api-proxy.maoyuan-wen-683.workers.dev`
- **VPS**: ColoCrossing, Tailscale 100.106.223.39

## Key Decisions
- KuzuDB retained to 500K (migrate at 1M+)
- 768d Matryoshka (down from 3072d, 75% storage savings)
- Edge-first injection: every node MUST have edges
- Content minimum: LR >= 100 chars, QA >= 50 chars
- Dedup at source: title hash check before CREATE
- Quality gate at every 50K increment
