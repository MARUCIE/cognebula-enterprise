# CogNebula SOTA Enterprise -- Task Plan

## Objective
Research world-class SOTA products and platforms in the Code Intelligence / Knowledge Graph / Agent Context Engine space. Extract their SOPs, role divisions, quality gates, and metrics. Produce a comparison matrix, gap analysis, and transferable capabilities list to guide CogNebula Enterprise's next-generation architecture.

## Current Phase
Phase 2: Synthesis + Gap Analysis (Steps 3-4)

## SOTA External Submission Calendar (pinned 2026-04-25 per SOTA gap doc Day-1)

- **LegalBench-Tax soft-submission target date: 2026-08-01** (Maurice + PM)
  - Rationale: anti-pattern A1 forbids submission until internal replay beats current SOTA by ≥5 pts on ≥3 sub-tasks. Pinning the date as a Meadows leverage #3 (Goal of System) artifact restructures every engineering decision toward "will this answer benchmark query type X?"
  - Prerequisite gate: private 100-case Chinese tax eval set built (Day 61-75 milestone) AND internal replay shows ≥5pp lead vs Claude Opus 4.7 (70.3% on VALS.ai 2026-04-24) on ≥3 of {CIT, VAT, IIT, 小税种}
  - Withdrawal trigger: if at 2026-07-15 internal replay still below SOTA on ≥3 sub-tasks, slip date to 2026-10-01 (do NOT submit mediocre, per Munger inversion #4)
  - Cross-ref: `outputs/reports/ontology-audit-swarm/2026-04-25-sota-gap-deep-audit.md` §Day 1 + §Anti-pattern A1
  - CI gate enforcement: `tests/test_kg_gate.py` blocks merge if composite_gate.verdict != PASS (test currently FAILS — by design, becomes forcing function per Meadows leverage #6)

## Steps
- [x] 1. Initialize planning-with-files and doc structure
- [x] 2. Swarm Research: 4 parallel researchers covering 4 domains (2 rounds: 2026-03 + 2026-04 refresh)
  - [x] 2a. Code Intelligence Platforms (Sourcegraph, Copilot Workspace, Cursor, Augment)
  - [x] 2b. Knowledge Graph / Graph RAG (Neo4j, NebulaGraph, Dgraph, LanceDB, Weaviate, MS GraphRAG, LightRAG)
  - [x] 2c. AI Agent Infra / Context Engines (LangChain, CrewAI, Devin, SWE-Agent, Aider, Codex CLI, Claude Code)
  - [x] 2d. Enterprise DevTool Platforms (GitLab Duo, JetBrains AI, Snyk Code, Qodo, Tabnine, Amazon Q)
- [x] 3. Synthesize into comparison matrix + gap analysis (in notes.md)
- [x] 4. Extract transferable capabilities + risk assessment (in notes.md)
- [x] 5. Update PRD / SYSTEM_ARCHITECTURE / USER_EXPERIENCE_MAP / PLATFORM_OPTIMIZATION_PLAN (2026-04-10)
- [x] 6. Execution Roadmap (below)

## Execution Roadmap (from SOTA Research)

### Phase A: MCP Server (1-2 weeks, P0) -- DONE 2026-04-10
- [x] Design MCP tool schema (query, search, neighbors, quality, stats)
- [x] Implement MCP Server wrapping existing FastAPI endpoints (`cognebula_mcp.py`, 6 tools)
- [x] Test with Claude Code + LangGraph as consumers (registered in 2 projects)
- [x] Publish benchmark: 100 curated tax Q&A pairs (`benchmark/eval_100_qa.jsonl`)
- [x] Build benchmark runner (`benchmark/run_eval.py`) — baseline: 60% (68/100 pass)

### Phase B: KuzuDB Sustainability (1 week, P0) -- DONE 2026-04-10
- [x] Evaluate Vela Partners fork: multi-writer support, active maintenance
- [x] Evaluate FalkorDB migration path (Cypher-compatible)
- [x] Decision: **ADOPT Vela fork** (v0.12.0-vela, MIT, drop-in API, multi-writer)
- [x] Execute upgrade: EXPORT 0.11.3 (7s, 442MB) → fix 1 NULL PK → IMPORT 0.12.0-vela (33s) → verified 620K/1M

#### Decision Record
- Vela fork: GO — same API, same Cypher, MIT license, prebuilt wheels, multi-writer
- FalkorDB: NO-GO — SSPLv1 license risk, 116 files to rewrite, Redis memory overhead
- Upgrade blocker: 0.11→0.12 format incompatible, needs EXPORT/IMPORT. VPS has 45GB free vs 67GB DB
- Execution plan: clean old data → EXPORT (Parquet) → install Vela wheel → IMPORT → verify

### Phase C: Content Quality (ongoing, P1) -- UPDATED 2026-04-16

#### C.1 6D Quality Snapshot (Session 43 audit, 2026-04-12)
| Type | Total | Score | Gate | Issue |
|------|-------|-------|------|-------|
| TaxClassificationCode | 4,205 | 100.0 | PASS | -- |
| TaxCodeDetail | 4,061 | 100.0 | PASS | -- |
| TaxCodeIndustryMap | 1,380 | 100.0 | PASS | -- |
| LawOrRegulation | 23,117 | 99.7 | PASS | -- |
| KnowledgeUnit | 32,034 | 99.4 | PASS | -- |
| DocumentSection | 42,115 | 82.9 | PASS | 19% short |
| FAQEntry | 1,156 | 81.8 | PASS | -- |
| SocialInsuranceRule | 138 | 32.4 | FAIL | 100% short, no auth |
| TaxRiskScenario | 180 | 23.0 | FAIL | all short |
| ComplianceRule | 8 | 19.2 | FAIL | mostly short |
| AccountingEntry | 375 | 15.5 | FAIL | 53% short |
| MindmapNode | 28,526 | 0.0 | FAIL | no content by design |
| CPAKnowledge | 7,371 | 0.0 | FAIL | 200 empty, 0% domain |
| IndustryRiskProfile | 720 | 0.0 | FAIL | no content |
| RegionalTaxPolicy | 620 | 0.0 | FAIL | no content |

**Overall**: 92.4/100 | 7 PASS / 8 FAIL | 156K nodes / 35K edges / density 0.226
**Missing tables**: LegalClause, RegulationClause, LegalDocument, Classification, HSCode (not in current DB)

#### C.2 Quality Boost Plan (Updated Session 43)
- [x] Fill embedding gap: 503K vectors (completed Session 40)
- [x] KU content backfill: 32K/32K = 100% filled
- [ ] LD description backfill: BLOCKED (LegalDocument table not in current DB)
- [x] Expand crawl sources to 10+ (19+ active fetchers)
- [x] **Edge density boost**: 0.226 → 2.357 (2,017,420 edges on 856,072 nodes at latest manual verification). `SEMANTIC_SIMILAR` import unblocked on 2026-04-16
- [x] Quality Gate score: 92.4/100 PASS (but 8/15 types individually FAIL)
- [ ] **Small-type content expansion**: CPAKnowledge (7.3K, 0%), MindmapNode (28.5K, structural), 5 other small types
- [x] **Edge density scripts**: boost + semantic edge import verified on Vela 0.12.0

#### C.3 Automation (deployed Session 41)
- **quality_boost_pipeline.sh**: turbo M3 for content fill + edge density (cron 18:00 UTC daily)
- **M3 orchestrator updated**: KU backfill 600→2000 batches, added Step 2d (LD backfill)
- **Expected convergence**: KU 80% in ~3 days, LD 80% in ~5 days, edge density 4.0 in ~7 days

### Phase D: Enterprise Integration (2-4 weeks, P2)
- [x] API key authentication for protected REST/MCP/browser consumers (`KG_API_KEY` + browser-safe proxy)
- [x] Docker Compose packaging (api + static web proxy stack runtime-verified locally)
- [x] Hybrid RAG: LanceDB vector entry + KuzuDB graph traversal (`/api/v1/hybrid-search` live)

## Key Decisions
- Swarm mode: 4 researchers in parallel, each covering one competitive domain
- Time window: last 12 months (2025-03 to 2026-03)
- Focus: SOPs, quality gates, deployment models, agent integration patterns

## Evidence
- Research outputs: this file + notes.md
- Comparison matrix: notes.md
- Final deliverables: PRD.md, SYSTEM_ARCHITECTURE.md, USER_EXPERIENCE_MAP.md, PLATFORM_OPTIMIZATION_PLAN.md

## Session 48 Closure (2026-04-16)

- [x] Resolved `SEMANTIC_SIMILAR` REL TABLE GROUP bulk-load blocker with explicit `from/to` COPY syntax
- [x] Removed the earlier 1000-edge-per-type fallback residue before reload
- [x] Imported all 570,481 semantic edges successfully on VPS
- [x] Re-verified `/api/v1/quality` = PASS / 100
- [x] Re-verified hybrid benchmark = 79% overall / 100 question pass / 0 errors (`benchmark/results_hybrid_20260416_after_security_fix.json`)
- [x] Fixed benchmark auth env mismatch (`COGNEBULA_API_KEY` fallback to `KG_API_KEY`)

## Session 49 Ralph Continuation (2026-04-16)

- [x] Created Ralph context snapshot: `.omx/context/semantic-edge-closeout-20260416T001600Z.md`
- [x] Created Ralph plan artifacts: `.omx/plans/prd-semantic-edge-closeout.md`, `.omx/plans/test-spec-semantic-edge-closeout.md`
- [x] Added missing `PDCA_ITERATION_CHECKLIST.md`
- [x] Ran attacker review on touched code and scripts; fixed query-string auth acceptance, raw HTML passthrough confusion, and admin migration route hardening on the actual service target
- [x] Captured DNA capsule `semantic-rel-group-copy-fix` and passed `ai dna validate` + `ai dna doctor`
- [x] Fresh architect verification returned `APPROVED` with no remaining blockers

## Session 50 Closeout Tail Cleanup (2026-04-16)

- [x] Standardized benchmark + MCP auth tooling on canonical `KG_API_KEY`
- [x] Removed the residual `COGNEBULA_API_KEY` coupling from active code paths
- [x] Aligned historical handoff density wording with the canonical `2M+` total-edge KPI

## Session 51 Static Web Auth Proxy Alignment (2026-04-16)

- [x] Confirmed the web app must remain `output: export`, so a Next App Route proxy is incompatible
- [x] Repointed the browser KG client to `https://cognebula-kg-proxy.workers.dev/api/v1`
- [x] Updated the Cloudflare Worker proxy to inject `KG_API_KEY` from Worker env/secret
- [x] Rebuilt the static web app successfully after the proxy-path change

## Session 52 Self-hosted Compose Packaging (2026-04-16)

- [x] Added a static web container image (`web/Dockerfile`) that builds the exported Next.js app
- [x] Added nginx reverse-proxy template (`docker/nginx.web.conf.template`) to inject `X-API-Key` for `/api/v1/*`
- [x] Expanded `docker-compose.yml` to run `cognebula-api` + `cognebula-web`
- [x] Verified `docker compose config`
- [x] Verified `docker compose build` for both `cognebula-web` and `cognebula-api`
- [x] Verified packaged runtime on `COGNEBULA_WEB_PORT=3001`
- [x] Fixed packaged local graph mount to use the real baseline Kuzu file by default

## Session 53 Phase C Script Portability (2026-04-16)

- [x] Made `cpa_content_backfill.py`, `mindmap_batch_backfill.py`, and `ld_description_backfill.py` accept `--db-path`
- [x] Added `KUZU_DB_PATH` env fallback for those scripts
- [x] Added `--dry-run` read-only inspection mode so local prechecks do not require write locks
- [x] Added missing `MindmapNode` table-existence precheck to avoid binder crashes during dry-run

## Session 54 Local Demo Graph Bootstrap (2026-04-16)

- [x] Added `scripts/bootstrap_local_demo_graph.py` to create a richer local demo Kuzu file from the bundled baseline
- [x] Upgraded demo bootstrap to enrich with FAQ + CPA-case + tax incentive + administrative-region + native mindmap data by default
- [x] Generated `data/finance-tax-graph.demo`
- [x] Verified packaged API can serve the demo graph via `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo`

## Session 55 Demo Bootstrap Parity Fix (2026-04-16)

- [x] Fixed `scripts/bootstrap_local_demo_graph.py` so the default `--include` set actually contains `mindmap`
- [x] Rebuilt `data/finance-tax-graph.demo` and re-verified the native table mix (`FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `LawOrRegulation=0`)
- [x] Re-verified packaged API and packaged web proxy against the rebuilt demo graph on the local Compose stack

## Session 56 README Packaged API Sync (2026-04-17)

- [x] Replaced the stale README `localhost:8766/api/rag` example with the current packaged API `:8400` / `:3001` search + hybrid-search examples
- [x] Verified the README no longer advertises the legacy packaged entrypoint
- [x] Captured the current local Docker daemon blocker (`~/.docker/run/docker.sock` missing) instead of fabricating a third runtime pass

## Session 57 README Example Runtime Proof (2026-04-17)

- [x] Recovered the local Docker daemon socket by relaunching Docker Desktop
- [x] Re-ran the packaged stack against `data/finance-tax-graph.demo`
- [x] Verified the new README examples against live endpoints: `:8400` search, `:8400` hybrid-search, and `:3001` proxied search
- [x] Torn the local verification stack back down and confirmed `docker compose ps` is empty

## Session 58 Compose Command + Route Index Sync (2026-04-17)

- [x] Normalized README packaged startup examples from `docker-compose` to `docker compose`
- [x] Added local packaged `:3001` web/proxy entrypoints to `doc/index.md`
- [x] Re-verified `docker compose config` after the doc-only sync

## Session 59 PDCA Packaged Topology Sync (2026-04-17)

- [x] Updated `PRD.md` current packaging text to include the local `docker compose` package (`:8400` API, `:3001` web/proxy)
- [x] Updated `SYSTEM_ARCHITECTURE.md` to remove the stale `/api/rag` label from the historical prototype diagram and add the local packaged `8400/3001` topology block
- [x] Updated `USER_EXPERIENCE_MAP.md` Journey 1 from `docker-compose` + `:8766` to current `docker compose` + `:3001` / `:8400` setup flow
- [x] Updated `PLATFORM_OPTIMIZATION_PLAN.md` deployment baseline so it no longer claims Compose only packages the API container
- [x] Re-rendered `PRD.html`, `SYSTEM_ARCHITECTURE.html`, `USER_EXPERIENCE_MAP.html`, and `PLATFORM_OPTIMIZATION_PLAN.html`

## Session 60 Delivery-Surface Audit (2026-04-17)

- [x] Verified the four PDCA HTML companions contain no stale `:8766` / `/api/rag` / `docker-compose` / API-only Compose wording
- [x] Recovered Docker daemon after a transient session disconnect and re-verified `docker compose ps` is empty
- [x] Kept the self-hosted closeout lane in doc-only mode; no additional business-code changes were needed

## Session 61 Demo Graph Small-Type Expansion (2026-04-17)

- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `compliance` and `industry`
- [x] Rebuilt `data/finance-tax-graph.demo` with the new default path
- [x] Verified the rebuilt demo graph reached `4330` nodes with `ComplianceRule`, `FormTemplate`, `FTIndustry`, and `RiskIndicator` populated
- [x] Re-verified packaged API stats and a proxied `合规` search against the rebuilt demo graph

## Session 62 Seed Reference Expansion (2026-04-17)

- [x] Added `src/inject_seed_reference_data.py` for `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark`
- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `seedrefs`
- [x] Extended `seedrefs` to include `InvoiceRule`
- [x] Rebuilt `data/finance-tax-graph.demo` to `4603` nodes with the new seed-based small types populated
- [x] Re-verified packaged API stats plus proxied `养老保险`, `税负率`, `预收账款`, and `发票` search hits against the rebuilt demo graph

## Session 63 Chart of Accounts Expansion (2026-04-17)

- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `accounting`
- [x] Wired `accounting` through `src/inject_chart_of_accounts.py` (CAS 2024 standard, 157 first-level accounts, 6 categories)
- [x] Rebuilt `data/finance-tax-graph.demo` to `4732` nodes with CoA expanded from `30` to `159`
- [x] Verified the rebuilt demo graph directly in Kuzu: `nodes=4732`, `edges=642`, `ChartOfAccount=159`; other small types (`FAQEntry=1152`, `SocialInsuranceRule=138`, `InvoiceRule=40`, `ComplianceRule=84`) unchanged
- [x] Spot-checked CoA samples across all six CAS categories (资产 / 负债 / 共同 / 所有者权益 / 成本 / 损益)

## Session 64 Tax Enforcement Cases (2026-04-17)

- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `enforcement`
- [x] Wired `enforcement` through `src/inject_tax_cases.py --create-edges` (170 source records → 95 LawOrRegulation nodes + 38 FT_GOVERNED_BY edges to TaxType)
- [x] Rebuilt `data/finance-tax-graph.demo` to `4827` nodes / `680` edges
- [x] Verified the rebuilt demo graph directly in Kuzu: `LawOrRegulation=95` (enforcement_qa=75, enforcement_case=20), `FT_GOVERNED_BY=38`; `ChartOfAccount=159` unchanged
- [x] Spot-checked that injected TaxType→LR edges all resolve to VAT-fraud enforcement cases (TT_VAT → 嘉峪关宏兴西域能源 / 安徽星印网络 / 扬州春风船舶机械)

## Session 65 Tax Rate Tables (2026-04-17)

- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `rates`
- [x] Wired `rates` through `src/inject_tax_rates.py` (69 CAS-authoritative flat-rate mappings + 23 progressive brackets across 4 schedules + 92 supporting edges)
- [x] Rebuilt `data/finance-tax-graph.demo` to `4919` nodes / `772` edges
- [x] Verified the rebuilt demo graph directly in Kuzu: `TaxRateMapping=80` (11 baseline + 69 new), `TaxRateSchedule=23`, `OP_MAPS_TO_RATE=80`, `FT_RATE_SCHEDULE=23`
- [x] Confirmed the 4 progressive tax schedules have the right bracket counts (综合所得=7, 经营所得=5, 全年一次性奖金=7, 土地增值税=4) and that `TT_VAT` flat rates span 13%/9%/6%/zero/simplified 1.5%-5%

## Session 66 Enterprise Report Templates (2026-04-17)

- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `reports`
- [x] Wired `reports` through `src/inject_enterprise_reports.py` (+336 LawOrRegulation report chapters + 110 RiskIndicator metrics across 7 report types)
- [x] Rebuilt `data/finance-tax-graph.demo` to `5365` nodes (edges unchanged at `772`; reports inject adds node content only)
- [x] Verified in Kuzu: `LawOrRegulation=431` (report_template=336, enforcement_*=95 preserved), `RiskIndicator=235` (baseline 125 + 110 new)
- [x] Report-template breakdown (regulationNumber prefix): 投资尽调 100 / 经营参谋 75 / 全景 43 / 税务风险 37 / 企业尽调 34 / 供应商尽调 24 / 财政补贴 23
- [x] Deferred `inject_cpa_exams.py` (requires RELATED_TO rel table not in baseline; schema gap logged in HANDOFF Session 66 notes)

## Session 67 CPA Exam Questions + RELATED_TO Schema Fix (2026-04-17)

- [x] Closed Session 66's deferred gap at the origin: `src/inject_cpa_exams.py` now creates its own `RELATED_TO` REL TABLE GROUP (FROM OP_StandardCase TO TaxType, FROM OP_StandardCase TO AccountingStandard) via `CREATE REL TABLE GROUP IF NOT EXISTS` right after Kuzu connection open — fat-skill pattern, the injector owns its DDL
- [x] Extended `bootstrap_local_demo_graph.py` default enrichment set to include `cpa-exams`, reusing `ensure_accounting_schema()` for the `OP_StandardCase` base table prerequisite
- [x] Rebuilt `data/finance-tax-graph.demo` to `6219` nodes / `876` edges (deltas: `+854` nodes / `+104` edges vs Session 66)
- [x] Verified in Kuzu: `OP_StandardCase=1246` (baseline 392 + 854 `caseType='cpa_exam_question'`), 854 exam questions across 2018-2020 and 6 subjects (accounting/audit/economic_law/financial_management/strategy/tax_law)
- [x] First population of `RELATED_TO` in demo graph: 104 edges from OP_StandardCase to TaxType, spread across 11 tax types (TT_VAT 27, TT_CIT 25, TT_CONSUMPTION 17, TT_STAMP 9, TT_PROPERTY 7, TT_LAND_USE 5, TT_VEHICLE 4, TT_RESOURCE 4, TT_LAND_VAT 4, TT_TOBACCO 1, TT_TONNAGE 1)
- [x] Logged 197-edge ID-alignment gap (53 missing TaxType + 144 missing AccountingStandard ids) as follow-up in HANDOFF Session 67 — extractor's ID vocabulary wider than baseline's actual node IDs; MATCH-then-MERGE shape silently dropped them
- [x] Confirmed all other node tables unchanged (LawOrRegulation=431, TaxType=19, AccountingStandard=43, RiskIndicator=235, ChartOfAccount=159, TaxRateMapping=80, TaxRateSchedule=23)

## Session 68 Production Deployment + Real Data Wiring (2026-04-17)

- [x] Built Next.js static export (`web/out/`, 5.8MB) with `NEXT_PUBLIC_KG_API_BASE=/api/v1` injected at build time
- [x] Shipped static bundle to contabo `/home/kg/cognebula-web/` via rsync (SSH config `RemoteCommand none` workaround for tmux auto-attach)
- [x] Authored `deploy/contabo/nginx-cognebula.conf` — port 80 static root + `/api/v1/` reverse-proxy to `127.0.0.1:8400`
- [x] Fixed nginx 500 root cause: `/home/kg` was mode 700; `chmod o+rx /home /home/kg && chmod -R o+rX /home/kg/cognebula-web` granted www-data traversal
- [x] Patched `kg-api-server.py:25-26` to read `DB_PATH`/`LANCE_PATH` from env instead of hardcoded path (prod backup had hardcoded `/home/kg/data/lancedb`, local version had empty stub)
- [x] Installed systemd drop-in at `/etc/systemd/system/kg-api.service.d/override.conf` pinning prod paths
- [x] Verified `/health` restored: `lancedb=true, lancedb_rows=118011, kuzu=true` on production
- [x] Confirmed System A (`/expert/*`, `/api/v1/*`) wired to real 547K prod graph; System B (`/workbench/*`, `/clients/*`, `/reports/*`) uses frontend seed (no corresponding backend endpoints — architectural fact, not mock injection)

## Session 69 Ontology Conformance Auditor + Phase 0/1 Migrations (2026-04-17)

- [x] Authored canonical schema `schemas/ontology_v4.2.cypher` — 35 node types across 4 tiers (Legal Backbone 7 / Tax Domain Primitives 9 / Operational Rules 10 / Accounting+Reporting 9) + 79 REL TABLE declarations, 114 DDL statements validated 0-error on fresh Kuzu
- [x] Built `src/audit/ontology_conformance.py` — exports `BROOKS_CEILING=37`, `V1_V2_BLEED`, `DUPLICATE_CLUSTERS`, `SAAS_LEAK`, `LEGACY_PRE_V41`; functions `parse_canonical_schema`, `list_live_node_tables`, `classify_rogue`, `audit`
- [x] Deployed `/api/v1/ontology-audit` endpoint (read-only diff vs canonical) on prod; Dockerfile updated to `COPY src/audit/` + `COPY schemas/`
- [x] Published CI gate `.github/workflows/ontology-gate.yml` (push/PR + daily 06:00 UTC cron); threshold roadmap 70→55→35→15→0 tracked per phase
- [x] Generated drift reports: `ONTOLOGY_DRIFT_REPORT.md` (English canonical, 9.1KB) + `ONTOLOGY_DRIFT_REPORT.html` (Chinese BCG-styled, 13.8KB)
- [x] Authored `scripts/migrate_phase0_drop_empty.py` — REL-aware dependency resolver, enumerates blockers via `CALL show_connection()`, drops empty RELs before node tables; `--dry-run` default, `--execute` required
- [x] Validated Phase 0 end-to-end on local demo copy: 56→37 types (=Brooks ceiling), 44→25 rogue, over_by 19→0, 39 RELs + 19 nodes dropped with 0 errors
- [x] Staged `deploy/contabo/migrations/phase1_v1_v2_rename.cypher` — Phase 1a drop empty stubs + 1b `ALTER TABLE V2 RENAME` (Vela 0.12 supports it, validated via `FormTemplate` round-trip preserving 109 rows)
- [x] Added `tests/test_ontology_conformance.py` — 19 unit tests covering parser, live-table listing, rogue classification (v1/v2 bleed, duplicate clusters, saas leak, legacy, other, mixed), full audit integration (empty db, canonical-only, v1/v2 severity, over-ceiling, medium threshold, full-coverage PASS, result shape), Brooks ceiling constant
- [x] All 19 tests pass via `.venv/bin/python -m pytest tests/test_ontology_conformance.py -v`
- [ ] **B0 — Phase 0 prod execution** (HITL-gated): `ssh contabo; systemctl stop kg-api.service; python3 scripts/migrate_phase0_drop_empty.py --db /home/kg/cognebula-enterprise/data/finance-tax-graph --execute; systemctl start kg-api.service` (~10 min downtime; waits for explicit "B0" trigger)
- [ ] **B2 — Phase 1 prod execution** (HITL-gated): `ALTER TABLE ComplianceRuleV2/FilingFormV2/RiskIndicatorV2 RENAME TO canonical names` after dropping 3 empty stubs (~60s downtime; waits for explicit "B2" trigger)
- [x] **Phase 1d TaxIncentiveV2 row merge** — `scripts/migrate_phase1d_taxincentive_merge.py` validated end-to-end on fixture (Session 71)
- [ ] Phases 2-4: duplicate cluster collapse (19→4), SaaS layer eviction (6 types, needs System B backend first), legacy folding (CPAKnowledge 7,371 + MindmapNode 28,526 → KnowledgeUnit)

## Session 70 Data Quality Surface Reframe (2026-04-23)

- [x] Reframed `web/src/app/expert/data-quality/page.tsx` so `/api/v1/ontology-audit` becomes the primary gate, while `/api/v1/quality` is shown as secondary hygiene
- [x] Added operator-visible signals for rogue node types, rogue edge types, dominant bucket share, V1/V2 bleed, duplicate clusters, and legacy-table residue
- [x] Updated PDCA docs + `doc/index.md` to treat data quality as `structure + hygiene`, not a single `/quality` score
- [ ] Capture fresh visual evidence from the authenticated production shell (blocked in this session: `Computer Use` transport closed and unauthenticated `curl https://ops.hegui.org/expert/data-quality/` returns `401`)

## Session 71 UI/UX Hardening for Data Quality Workbench (2026-04-24)

- [x] Reworked the page from a report layout into a workbench layout: verdict hero, operator flow, governance lane, distribution evidence, risk breakdown, hygiene panel, and inspector section
- [x] Added a validation-only production-snapshot route at `/expert/data-quality/fixture` for screenshots, smoke tests, and visual regression baselines
- [x] Captured desktop/mobile screenshots + smoke JSON + Lighthouse reports against the fixture route
- [ ] Authenticated `ops.hegui.org` post-change screenshot still pending (local browser auth could not be recovered automatically)

## Session 71 Phase 1d Fixture Validation (2026-04-24)

- [x] Audit found existing untracked drafts: `scripts/migrate_phase1d_taxincentive_merge.py` (237 L), `deploy/contabo/migrations/phase2_duplicate_cluster_collapse.cypher` (156 L), `phase4_legacy_folding.cypher` (137 L) — Phase 1d was 80% done with punted edge-rewire; Phase 2/4 were ~30% scaffolds with commented-out MERGE blocks
- [x] Identified false-positive risk: `--dry-run` on `data/finance-tax-graph.demo` trivially reported "nothing to merge" because demo ships canonical `TaxIncentive` only; V2 lives on prod per Session 43 drift audit (109 rows)
- [x] Authored `scripts/fixture_phase1d_test.py` — clones demo DB, injects `TaxIncentiveV2` (5 rows: 2 id-conflicts with canonical + 3 fresh) and `FT_INCENTIVE_TAX_V2` rel (2 edges: 1 from a fresh row, 1 from a conflict row)
- [x] Enhanced `migrate_phase1d_taxincentive_merge.py` edge-rewire: previous version punted non-empty V2 rels ("manual rewrite or re-ingest"); now handles convention-driven rewire — if a V2 rel is named `FOO_V2`, its canonical twin `FOO` exists, and endpoint shape matches after `TaxIncentiveV2→TaxIncentive` swap, script runs `MATCH (v)-[e:V2_REL]->(x), (c:TaxIncentive {id: v.id}) CREATE (c)-[:CANONICAL_REL]->(x) DELETE e` per endpoint direction, then drops the V2 rel
- [x] Verified `--dry-run` on seeded fixture reports real signals: `V2 rows=5`, `conflicts=2`, `REL deps=[(FT_INCENTIVE_TAX_V2, [(TaxIncentiveV2, TaxType)], edges=2)]`, `schema diff=(none)` — no false green light
- [x] Verified `--execute` on seeded fixture: `TaxIncentive` 109→112 (3 fresh merged, 2 conflicts correctly skipped via `ON CREATE SET` semantics preserving canonical rows), rewired 2 V2 edges onto canonical `FT_INCENTIVE_TAX`, dropped `FT_INCENTIVE_TAX_V2` + `TaxIncentiveV2` tables, canonical row `INCE_AGRI_VAT.name` preserved (not overwritten by V2's `CONFLICT-A`)
- [x] Evidence DB left at `data/finance-tax-graph.phase1d-test` (110 MB, gitignored-class name — treat as transient)
- [ ] **B3 — Phase 1d prod execution** (HITL-gated): pre-req is snapshot + `systemctl stop kg-api.service`; command `.venv/bin/python scripts/migrate_phase1d_taxincentive_merge.py --db /home/kg/cognebula-enterprise/data/finance-tax-graph --execute`; waits for explicit "B3" trigger
- [ ] Phase 2 scaffold completion: 4 cluster MERGE blocks still commented out ("REWRITE with actual column names post-dry-run"); same fixture pattern can be applied per cluster
- [x] Phase 4 scaffold completion: see Session 72 — Vela 0.12 `ALTER TABLE ADD COLUMN` confirmed functional, Phase 4a/4b/4c implemented as single Python driver, demo-validated end-to-end

## Session 72 Phase 4 Legacy Folding — Demo Validation (2026-04-24)

- [x] Probed Vela 0.12 `ALTER TABLE ADD COLUMN` on demo copy: supported natively (3/3 ALTER statements OK), closing the `phase4_legacy_folding.cypher:128-129` abort concern ("Vela 0.12 fork may lack column add" → confirmed DOES NOT lack it)
- [x] Derived column mappings from live demo schemas (schema != scaffold assumption):
    - `CPAKnowledge(id, title, content, chapter, subject, source)` — flat structure, 649 rows on demo (7,371 on prod)
    - `MindmapNode(id, node_text, content, category, node_type, parent_text, source_file, heading_level, content_lines)` — parent refs via **text** not id (`parent_text` not `parentId`), 990 rows on demo (28,526 on prod); scaffold's `'MIND_' + m.parentId` scheme was aspirational — real demo parents are text-referenced, so `legacyParentId` holds `parent_text` verbatim (preserves data; future enrichment can resolve text→id)
- [x] Confirmed canonical `KnowledgeUnit` schema from `schemas/ontology_v4.2.cypher:46-49`: `id/topic/content/sourceDocId/embeddingId/authorityScore` — Phase 4a widens with 3 legacy columns on top
- [x] Authored `scripts/migrate_phase4_legacy_folding.py` (277 L) — single Python driver for 4a+4b+4c, same safety pattern as Phase 1d (`--dry-run` default, `--execute` opt-in, `--db` required, `CREATE IF NOT EXISTS` for portability across demo/prod)
- [x] Dry-run on fresh demo copy (`data/finance-tax-graph.phase4-test`) reported: `KnowledgeUnit absent`, `CPAKnowledge=649`, `MindmapNode=990`, `missing legacy columns=[legacyType, legacyParentId, legacyPath]`, `REL deps=0` (demo has no edges out of the two legacy tables — hedged rewire logic is a no-op on demo, live on prod if needed)
- [x] Execute on the test DB: CREATE KU + 3 ALTERs + 4b MERGE 649 CPA rows (`cpa_accounting=242, cpa_audit=38, cpa_financial_management=323, cpa_tax_law=46` — per-subject legacyType tags preserved) + 4c MERGE 990 Mindmap rows (8 distinct `mindmap_*` category tags preserved) + DROP CPAKnowledge + DROP MindmapNode, all OK with zero errors
- [x] Post-migration verification: `KnowledgeUnit=1639` (= 0 + 649 + 990, exact), `null legacyType=0` (no canonical leakage), both source tables GONE, sample CPA row `CPAK_CPA_67a4e78f` topic/legacyType/legacyPath all preserved intact
- [x] Evidence DB left at `data/finance-tax-graph.phase4-test` (110 MB, gitignored — transient)
- [ ] **B4 — Phase 4 prod execution** (HITL-gated): prod pre-req is EXPORT snapshot (KU already at 32,034 rows, ALTER must not lose existing rows — Vela ALTER is additive so this should hold, but snapshot is mandatory) + `systemctl stop kg-api.service`; prod command `.venv/bin/python scripts/migrate_phase4_legacy_folding.py --db /home/kg/cognebula-enterprise/data/finance-tax-graph --execute`; waits for explicit "B4" trigger
- [ ] Phase 2 clusters 2A-2D still untouched (scope-cut decision Session 72: each cluster needs its own fixture + conflict-strategy sub-phase; not a one-shot like Phase 4) — see Session 73 for readiness probe + blocker analysis

## Session 73 Phase 2 Readiness Probe + Demo Coverage Blocker (2026-04-24)

- [x] Attempted to extend "按推荐执行完整路线" to Phase 2 cluster completion; hit hard demo-coverage blocker: `0/3` sources for 2A, `2/5` for 2B, `2/6` for 2C (canonical `AccountingSubject` also absent), `2/6` for 2D (canonical `TaxRate` also absent)
- [x] Writing Phase 2 MERGE blocks without real source schemas would reproduce the exact false-positive failure mode Session 71 fixed (dry-run reporting "nothing to merge" on absent sources, then speculative MERGE Cypher failing on prod with wrong column names — the scaffold itself warns "REWRITE with actual column names post-dry-run")
- [x] Discovered architectural layer archaeology: `schemas/migration_mapping.json` v2.0 (2026-03-19) and `deploy/contabo/migrations/phase2_duplicate_cluster_collapse.cypher` v4.2 (2026-04-17) define **different** target groupings for overlapping sources — e.g., v2.0 puts `FTIndustry+IndustryBookkeeping+IndustryRiskProfile` into `Classification` while v4.2 puts them into `IndustryBenchmark`; v2.0 puts `TaxPolicy+TaxRateMapping+TaxRateDetail+TaxRateSchedule` into `TaxRule` while v4.2 puts them into `TaxRate`. v4.2 supersedes v2.0 per Session 69's canonical schema adoption; v2.0 is now historical reference
- [x] Authored `scripts/phase2_readiness_probe.py` — HITL-safe, read-only probe reporting per-cluster target presence, source presence + row counts + column schemas, and id-overlap between each present source and its target. No `--execute` flag (never writes). Runs identically against demo or prod
- [x] Ran probe on demo: confirmed coverage gaps above; harvested real column schemas for the 6 present sources across clusters (`FTIndustry`, `IndustryBookkeeping`, `AccountEntry`, `ChartOfAccount`, `TaxRateMapping`, `TaxRateSchedule`) — these are the only clusters where partial fixture work could proceed locally without prod probe
- [ ] **B5 — Prod probe run** (HITL-safe, read-only; execution needs SSH access I don't have): `ssh contabo; .venv/bin/python scripts/phase2_readiness_probe.py --db /home/kg/cognebula-enterprise/data/finance-tax-graph`. Output will show the real column schemas for all 19 Phase 2 source tables that are absent from demo. Only after this prod data lands can Phase 2 MERGE blocks be authored without speculation
- [ ] Scope decision (pending user): without B5 prod probe output, autonomous Phase 2 work ends here. Alternatives if you want to proceed without a B5 run: (a) I continue assuming columns from scaffold/migration_mapping.json hints — accepts authoring risk; (b) B3/B4 triggered for Phase 1d/4 prod — these are already demo-validated and safe to ship; (c) pivot to Phase 2C's sub-phase contract (`phase2_duplicate_cluster_collapse.cypher:149-156`) — author the contract doc only, not the merge code

## Session 74 Ontology Quality Audit + 4-Advisor Swarm + Visual Review (2026-04-24)

- [x] User trigger: 2 prod screenshots surfacing KnowledgeUnit dominance (33.9%, 185,455 rows) and content_coverage=0.51 gate-paradox (gate=PASS score=100 but coverage 51%). Directive: "执行大规模数据质量审计计划，输出 html 报告，再 pdca 执行，开始蜂群审计"
- [x] Captured live prod snapshots via `POST /api/v1/{stats,quality,audit}` into `/tmp/cog_*.json`: 547,761 nodes / 1,302,476 edges / 83 live node types vs 35 canonical (v4.2) / Brooks ceiling 37 / 64 rogue types / 16 missing_from_prod / verdict=FAIL severity=high
- [x] 4-lens swarm (parallel dispatch): advisor-hara (structural minimalism, verdict RESTRUCTURE — delete 15 code-graph pollution types, isolate SaaS-leaks, exclude metadata from coverage denominator), advisor-hickey (complecting, verdict "structure fine, data complected" — `legacyType` column is provenance-as-identity, `KU_ABOUT_TAX` 166K edges must split into DEFINES_TERM/SETS_THRESHOLD/PRESCRIBES_PROCEDURE/CITES_PRECEDENT), advisor-meadows (systems dynamics — R1 reinforcing loop + B_MISSING balancing loop missing, Leverage #3 goal reformulation + #8 write-entry whitelist), advisor-munger (inversions — Goodhart metric-gaming, weekend bulldozer, empty canonical stubs, Frankenstein synthesis, irreversibility traps)
- [x] MECE-merged 4 lenses into 5 executive findings: (1) "51% coverage" is measurement artifact — excluding code-graph + metadata from denominator compresses gap 29pp → 5–8pp; (2) 83 live types driven by R1 loop without B_MISSING counterweight; (3) KnowledgeUnit is correctly generic; sin is `legacyType` + undifferentiated `KU_ABOUT_TAX`; (4) highest-leverage fix is gate redefinition (not data migration); (5) B-batch remediation must be snapshot-gated and sequenced
- [x] PDCA plan authored: P (3-condition composite gate + write-entry whitelist + sequenced plan), D (9-step HITL-gated sequence: D1 → C0 → P0 → B3 → B4 → B0 → B2 → H1 → H2), C (re-audit per batch with new gate), A (sync 4-doc PDCA + rolling ledger + type-count target 35±2)
- [x] 8-decision next-actions table with owner/priority/due-date/status — 5×P0 structural, 1×P1 (visual swarm), 2×P3 deferred to Wave 2/3
- [x] Delivered 2份制 pair per Swarm Output Contract (09-output-format §): English canonical MD at `outputs/reports/ontology-audit-swarm/2026-04-24-cognebula-ontology-quality-audit.md` + Chinese HTML at `outputs/reports/ontology-audit-swarm/2026-04-24-cognebula-ontology-quality-audit.html` styled McKinsey Blue (per ontology-audit-swarm style routing rule, always McKinsey Blue)
- [x] Auto-visual-swarm-review executed (per rule 16 + memory feedback_auto_swarm_review): 3 rounds, 3 parallel advisors (Jobs/Hara/Orwell), 6 patches applied (2×Round1 2/3 consensus + 1×WCAG AA categorical + 3×Round3 3/3 unanimous), final verdict 3/3 APPROVE. Trace at `outputs/reports/auto-swarm-trace/2026-04-24-cognebula-ontology-quality-audit.md`
- [x] HTML `open`'d in browser (per auto-open memory rule)
- [x] `[SWARM]` + `[AUTO-VISUAL-SWARM]` + `[BOOTSTRAP-EVOLUTION]` receipts appended to `state/memory/2026-04-24.md`
- [ ] **D1 — Kuzu full snapshot prod execution** (HITL-gated): pre-req for any subsequent B-batch; command (SSH required) `ssh contabo; cp -r /home/kg/cognebula-enterprise/data/finance-tax-graph /home/kg/backups/ontology-audit-2026-04-24.kuzu`; waits for explicit "D1" trigger
- [x] **C0 — Quality gate redefinition DEPLOYED** (2026-04-24): backed up prod `src/audit/ontology_conformance.py` → `.pre-session74.bak`; scp'd new version (4933 B → 13762 B); `systemctl restart kg-api.service` clean (PID 1193863, active 3s); post-deploy `curl http://127.0.0.1:8400/api/v1/ontology-audit` confirms `composite_gate` + `noise_classification` fields present. Prod verdict: `composite_gate.verdict=FAIL, canonical_coverage_ratio=0.306, domain_types=62, domain_rogue=43, over_ceiling_by=46` — all 3 conditions FAIL (matches local smoke test exactly). Legacy `verdict/severity` unchanged (backward compat preserved). Note: this deploy did NOT require D1 snapshot because C0 is code-only (no data mutation); D1 remains a hard pre-req for B-batch migrations.
- [ ] **P0 — Write-entry whitelist guard** (install `ontology-whitelist-guard.py` pre-commit hook validating `CREATE NODE TABLE` against `schemas/ontology_v4.2.cypher`); waits for "P0" trigger after C0 done
- [ ] B3/B4/B0/B2/H1/H2 — sequenced remediation batches; each needs prior batch done + snapshot evidence; each waits for its own trigger word

## §P-Eval-CIT-Close — Atomic Execution Queue (2026-04-25)

**Phase milestone**: LegalBench-Tax v0 CIT 域 15/30 → 30/30 (close 50% gap from waves 14-20)
**Authoring source**: PRC CIT 法 (2007 主席令 §63) + 实施条例 (2007 国务院令 §512) + 后续公告
**Anti-pattern A4**: each case must cite real 法条/公告 in `sources` field
**Stop condition**: CIT 30/30 atteint = phase milestone, commit, honest stop
**Out-of-scope (this session)**: IIT 5→20, MISC 5→20, FFF extension, FK 4th pair

### Batch 1 (cit_016-025, 跨境/CFC/反避税/特殊扣除)

- [x] cit_016 — 受控外国企业（CFC）规则 (CIT 法 §45)
- [x] cit_017 — 关联交易转让定价独立交易原则 (CIT 法 §41 + 国家税务总局 6 号 2017)
- [x] cit_018 — 资本弱化关联方利息（金融 5:1 / 其他 2:1）(CIT 法 §46)
- [x] cit_019 — 资产损失税前扣除申报 (国家税务总局 25 号 2011)
- [x] cit_020 — 公益性捐赠 12% + 三年结转 (CIT 法 §9 + 财税[2018]15 号)
- [x] cit_021 — 业务招待费 60% × 5‰ 双限 (CIT 实施条例 §43)
- [x] cit_022 — 广告宣传费 15% + 结转 (CIT 实施条例 §44)
- [x] cit_023 — 跨年度发票汇算清缴前补凭 (国家税务总局 28 号 2018)
- [x] cit_024 — 不征税收入对应支出不得扣除 (财税[2011]70 号)
- [x] cit_025 — 长期股权投资权益法 vs 成本法税务处理 (CIT 实施条例 §17)

### Batch 2 (cit_026-030, 重组/清算/分支/特殊业务)

- [x] cit_026 — 企业重组特殊性税务处理 5 条件 (财税[2009]59 号)
- [x] cit_027 — 清算所得计算 (CIT 法 §55 + 财税[2009]60 号)
- [x] cit_028 — 非货币性资产投资 5 年分期 (财税[2014]116 号)
- [x] cit_029 — 跨地区经营汇总纳税分摊 (国家税务总局 57 号 2012)
- [x] cit_030 — 高新企业研发费用归集口径 vs 加计扣除口径差异 (国家税务总局 76 号 2018)

**Phase milestone reached 2026-04-25**: CIT 30/30 ✓ (LegalBench-Tax v0 CIT domain saturated). Total eval set 55 → 70 cases.

## §P-Eval-IIT-Close — Atomic Execution Queue (2026-04-25)

**Phase milestone**: LegalBench-Tax v0 IIT 域 5/20 → 20/20
**Authoring source**: 个人所得税法 (2018 修正) + 实施条例 + 国家税务总局公告
**Anti-pattern A4**: each case must cite real 法条/公告
**Stop condition**: IIT 20/20 atteint = phase milestone, commit, hard stop
**Out-of-scope (this session)**: MISC 5→20, FFF/FK/HITL paths

### Batch 1 (iit_006-015, 综合所得 + 经营所得 + 利息股息财产)

- [x] iit_006 — 工资薪金累计预扣法月度计算 (国家税务总局公告 2018 年第 61 号)
- [x] iit_007 — 劳务报酬预扣（800 起征 / 4000 减除）(IIT 法 §6 + 实施条例 §14)
- [x] iit_008 — 稿酬所得 70% 减计 + 收入额 (IIT 法 §6)
- [x] iit_009 — 特许权使用费综合所得并入 (IIT 法 §6)
- [x] iit_010 — 经营所得 5 级超额累进 5%-35% (IIT 法 §3 + 实施条例 §12)
- [x] iit_011 — 个人股息红利持股期限差别化（1月/1年）(财税[2015]101 号)
- [x] iit_012 — 个人股权转让所得 20% (国家税务总局公告 2014 年第 67 号)
- [x] iit_013 — 个人房屋出租综合税负（IIT 10% + 房产税 4% + VAT 1.5%）
- [x] iit_014 — 个人住房转让满 5 年唯一住房免征 (财税[1999]278 号)
- [x] iit_015 — 偶然所得 20% 不可扣减 (IIT 法 §3)

### Batch 2 (iit_016-020, 专项附加扣除 + 居民判定 + 跨境)

- [x] iit_016 — 子女教育专项附加 2000/月/孩 (财税[2018]101 号 + 国务院 2022 年第 14 号)
- [x] iit_017 — 住房贷款利息 1000/月 20 年 (财税[2018]101 号)
- [x] iit_018 — 赡养老人 3000/月独/分摊 (财税[2018]101 号)
- [x] iit_019 — 居民个人 183 天判定标准 (IIT 法 §1)
- [x] iit_020 — 无住所个人 6 年规则 (财税[2019]35 号)

**Phase milestone reached 2026-04-25**: IIT 20/20 ✓ (LegalBench-Tax v0 IIT domain saturated). Total eval set 70 → 85 cases. CIT/VAT/IIT all 100%; only MISC 5/20 remains.

## §P-Eval-MISC-Close — Atomic Execution Queue (2026-04-26)

**Phase milestone**: LegalBench-Tax v0 MISC 域 5/20 → 20/20 = **eval set 100/100 全套 saturated**
**Authoring source**: 印花税法 (2022) + 契税法 (2021) + 房产税暂行条例 + 土地增值税暂行条例 + 环保税法 (2018) + 资源税法 (2020) + 烟叶税法 (2017) + 城建税法 (2021) + 车船税法 (2012) + 关税法 + 船舶吨税法
**Anti-pattern A4**: each case must cite real 法条/条例
**Stop condition**: MISC 20/20 = full eval set 100/100 milestone, hard stop

### Batch 1 (misc_006-015, 印花/契/房产/土增/环保/资源 6 子税)

- [x] misc_006 — 借款合同印花税 万分之零点五 (印花税法 附件)
- [x] misc_007 — 产权转移书据印花税 万分之五 (印花税法 附件)
- [x] misc_008 — 首套住房契税 1%/1.5%/3% (契税法 + 财税[2016]23 号)
- [x] misc_009 — 单位赠予个人契税 全额征 3% (契税法 §3)
- [x] misc_010 — 自用房产税 1.2% × (原值×(1-减除比例)) (房产税暂行条例 §4)
- [x] misc_011 — 出租房产税 租金 12% / 个人住房 4% (财税[2008]24 号)
- [x] misc_012 — 土增税 4 级累进 30/40/50/60% (土增税暂行条例 §7)
- [x] misc_013 — 普通住房土增税豁免 (国发[2005]26 号)
- [x] misc_014 — 环保税四类应税污染物 (环保税法 §3)
- [x] misc_015 — 资源税油气从价计征 6%-10% (资源税法 附表)

### Batch 2 (misc_016-020, 烟叶/城建附加/车船/关税/船舶吨 5 子税)

- [x] misc_016 — 烟叶税 20% 比例税率 (烟叶税法 §3)
- [x] misc_017 — 城建税三档税率 7%/5%/1% (城建税法 §4)
- [x] misc_018 — 车船税地区差异税额 (车船税法 §3)
- [x] misc_019 — 进口关税完税价格 = CIF (关税法 §27)
- [x] misc_020 — 船舶吨税净吨位四档 (船舶吨税法 §3)

**Phase milestone reached 2026-04-26**: MISC 20/20 ✓ (LegalBench-Tax v0 MISC domain saturated). **Total eval set 100/100 ✓ FULL SATURATION** — all 4 domains (CIT/VAT/IIT/MISC) at 100% target. Day 61-75 SOTA prerequisite (private 100-case Chinese tax eval set) closed.

---

## 2026-04-28 — Step 0 Autonomous Preamble + Project Preflight Snapshot

**Task shape**: preflight / orchestration baseline under active OMX `autopilot` state, routed through `$analyze` because the submitted Step 0 contained the keyword `analyze` in the operating contract.

### Operating constraints accepted for this lane

- [x] Execute safe commands automatically and record automation traces in `task_plan.md` / `notes.md`.
- [x] Use installed skills/plugins/MCP first when they match the task; use subagents for bounded read-only mapping lanes.
- [x] Browser automation priority for Codex: Playwright MCP / in-app browser first, `agent-browser` fallback.
- [x] Preserve gates: docs, tests, security review, and release checks cannot be skipped for speed.
- [x] Treat external communication as blocked unless explicitly authorized.
- [x] Promote only verified reusable correction paths into DNA capsules; this preflight produced one candidate but not enough evidence for promotion yet.

### Project architecture + route map summary

| Area | Current evidence |
|---|---|
| Project root | `/Users/mauricewen/Projects/27-cognebula-enterprise` |
| Git HEAD | `1484131e20c6526af317cc9740ac8c1ec21066e9` |
| Active initiative | `doc/00_project/initiative_cognebula_sota/` |
| Required planning files | Present: `task_plan.md`, `notes.md`, `deliverable.md`, `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `USER_EXPERIENCE_MAP.md`, `PLATFORM_OPTIMIZATION_PLAN.md`, `ROLLING_REQUIREMENTS_AND_PROMPTS.md` |
| Web stack | Next.js `16.2.1`, React `19.2.4`, static export mode (`web/`) |
| Backend stack | FastAPI/Uvicorn + Kuzu/Vela + LanceDB + Redis (`kg-api-server.py`, `cognebula_mcp.py`) |
| Main web routes | `/`, `/workbench/*`, `/expert/*`, `/expert/data-quality`, `/expert/data-quality/fixture`, `/reports/*`, `/clients/*`, `/settings`, `/skills` |
| Main API routes | `/api/v1/health`, `/stats`, `/quality`, `/ontology-audit`, `/search`, `/hybrid-search`, `/graph`, `/admin/*`, `/ingest`, `/chat` |

### Blockers / risk ledger

- **P0 architectural blocker**: `SYSTEM_ARCHITECTURE.md` and `notes.md` already record a 2026-04-27 dual-backend drift: `kg-api-server.py` and `src/api/kg_api.py` both target port `8400` with disjoint route sets. Resolution remains HITL-pending: merge / formalize split / deprecate one.
- **Worktree risk**: repo is ahead of `origin/main` by 46 commits and has many modified/deleted/untracked files. Treat as active WIP; do not revert unrelated changes.
- **Security hardening risk**: subagent mapping found deploy hardening placeholders under `deploy/contabo/`; production status is not proven in this preflight.
- **Command hygiene correction**: one manifest-discovery command accidentally traversed `web/node_modules`; corrected bounded route/package commands now exclude generated dependency trees.

### State snapshot

- Created `.omx/context/project-preflight-step0-20260427T161242Z.md`.
- OMX MCP `state_write` failed with closed transport; fallback updated `.omx/state/sessions/019dcf07-e4b3-79f2-ade8-35c51a1bfb39/autopilot-state.json` and matching skill-active state to `preflight_snapshot`.

---

## §17. 2026-04-28 — SCAF-T LaunchAgent governance closeout

**Trigger**: KB audit pivot (Maurice mid-session) revealed 2 zombie LaunchAgents on Mac referencing the pre-`27-` project path.

### Atomic items (all CLOSED 2026-04-28)
- [x] S17.1 Scan orphan project shell `/Users/mauricewen/Projects/cognebula-enterprise/` for content classification (614 MB, 28 edge CSVs + 3 JSON/JSONL data files; HITL-decision item)
- [x] S17.2 `launchctl bootout` + remove `~/Library/LaunchAgents/com.cognebula.backup.plist` (referenced missing `backup-to-mac.sh`, never produced log)
- [x] S17.3 `launchctl bootout` + remove `~/Library/LaunchAgents/com.cognebula.doctax-ingest.plist` (referenced missing `.venv/bin/python3` + `scripts/ingest_doctax.py`, never produced log)
- [x] S17.4 Quarantine both plists to `~/.ai-fleet/disabled-launchagents/20260428-cognebula-orphan/` (audit trail preserved)
- [x] S17.5 Verify cognebula-free state: `launchctl list` empty + `~/Library/LaunchAgents/` empty for cognebula prefix
- [x] S17.6 Capture verdict + design rule in `deliverable.md` (`Backup-link audit must verify payload arrival, not scheduler existence`)

### HITL items deferred to Maurice
- **S17.HITL.1** Disposition of orphan project shell `/Users/mauricewen/Projects/cognebula-enterprise/` (614 MB) — options (a) verify superseded → rm -rf, (b) move to `~/Library/Application Support/cognebula-archive/`, (c) keep
- **S17.HITL.2** Disposition of doctax 535-file batch (March-era ~167-item partial failure run) — options (a) abandon (round4 seed canonical), (b) re-run, (c) audit partial inserts

### Next milestone
Sprint G4 S15.1 (Backend A `OPTIONS /api/v1/.well-known/capabilities` endpoint) — atomic queue declared in §15, NOT started. Phase boundary: §17 SCAF-T closure complete; §15 Sprint G4 kickoff awaits explicit signal or autonomous-extension trigger.
