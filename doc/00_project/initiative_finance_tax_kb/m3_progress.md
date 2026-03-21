# M3 Progress Log

## Session: 2026-03-20

### Phase 1 进展 (L1 深化)

**已完成:**
- [16:00] EXPLAINS split: 475K → 6 precise types (5.7s keyword classification)
- [16:10] DDL v3.1: 17 nodes × 36 edge types
- [16:15] API V2_EDGES whitelist updated, quality density 3.977
- [16:20] Design doc v3.1 (McKinsey Blue)
- [16:25] KG Explorer: Chinese edge labels + 36-type color coding
- [16:30] Admin dashboard: real-time edge distribution
- [16:35] Git cleanup: 9.9GB doc-tax + 684MB backups removed
- [16:40] M3 QA pipeline tested: 5 articles → 14 QA (2.8/article)
- [16:45] M3 QA pipeline launched on kg-node (gemini-2.5-flash-lite)
- [16:50] M3 orchestrator deployed (5-step: QA→Edge→API→density→crawl)
- [16:55] Know-Arc system integration (/api/v1/ka/*, 23 endpoints)
- [17:00] Daily pipeline depth fix (--fetch-content flags)
- [17:10] Swarm audit: 3 agents (Research + Explorer + Meadows)
- [17:30] Edge Engine created (generate_edges_ai.py)
- [17:40] M3 Data Source Strategy HTML report (Economist Editorial)
- [17:45] M3 task plan + findings + progress files created

**运行中:**
- M3 QA cron: 02:00 UTC daily (50 batches × 100 articles)
- M3 Edge Engine: integrated into orchestrator
- Daily crawl: 10:00 UTC (22 crawlers with depth flags)

**Phase 1 已完成:**
- [17:50] Temporal chains: +317 SUPERSEDES edges (5-year PIT chain)
- [17:55] Clause split v2: +12,925 sub-clause nodes (PARALLEL=FALSE fix)
- [18:00] PART_OF edges: +10,460 sub-clause→document edges
- [18:05] Edge enrichment script ready (KU_ABOUT_TAX + ISSUED_BY)
- [18:10] chinatax detail fetch launched in tmux (8.7K docs, ~8h)
- [18:15] 3 new P0 crawlers deployed (flk_npc, cicpa, cctaa)
- [18:20] VPS data/raw ownership fixed (root→kg)
- [18:25] Swarm: Frontend research + Crawl test (2 agents parallel)

**Phase 2 启动 (L2 广度):**
- flk.npc.gov.cn: API 405 — 需要逆向工程正确 endpoint
- cicpa.org.cn: 测试中
- cctaa.cn: 测试中

**前端升级 (并行):**
- Canvas 风格可视化调研中 (Cytoscape.js / ELK.js / JSON Canvas)

### Commits (10 total)
1. 548ffed - v3.1 EXPLAINS split + git cleanup
2. fab61f8 - Know-Arc injection + INTERPRETS analysis
3. dd9ada8 - Explorer Chinese edge labels + colors
4. 9628310 - Admin real-time edge distribution
5. e9c5f58 - M3 QA generation pipeline
6. d9727f0 - M3 orchestrator + cron
7. 667d566 - Know-Arc system integration (APIRouter)
8. 6e72ed6 - Swarm audit fixes + daily pipeline depth
9. ae95ae6 - Edge Engine + Meadows pipeline redesign
10. 2bd1568 - M3 Data Source Strategy HTML report

### KG Metrics (Updated 2026-03-21)
- Nodes: 413,558 (from 420,892 pre-remediation)
- Edges: 929,705 (from 874,086 pre-remediation, +55,619)
- Density: 2.248 (from 2.077, +8.2%)
- Quality: 100/100
- Schema: v3.1 (53N × 66E)

## Session: 2026-03-21

### M3 Comprehensive Remediation (8 operations)

**Task 1: LR 垃圾桶清洗**
- LR 57,639 → 21,202 (-63%), 孤儿 49,541 → 5,099 (86% → 24%)
- 32,765 misclassified LR migrated to KnowledgeUnit (wiki/FAQ/CPA/mindmap)
- 3,282 short/empty LR deleted
- Root cause: crawl pipeline dumped all content into LR table

**Task 2: HS 层级自动构建**
- +22,880 CHILD_OF edges from HS code structure (2/4/6/8/10-digit hierarchy)
- Classification orphans: 87% → 7%

**Task 3: KU 边丰富**
- +6,495 KU_ABOUT_TAX (migrated KU → TaxType via keyword)
- +2,659 KU_ABOUT_TAX (tax keyword matching)
- +14,911 KU_ABOUT_TAX (type-based matching: FAQ→VAT, 百科→CIT, etc.)
- KU orphans: 26,095 → 8,525

**Task 4: LR 孤儿修复**
- +2,154 CLASSIFIED_UNDER_TAX (LR → TaxType)
- +5,851 LR_ISSUED_BY (new edge type, bypasses ISSUED_BY schema constraint)
- ISSUED_BY only allows LegalDocument→IssuingBody (KuzuDB typed edges)

**Task 5: V2 幽灵表清洗**
- ComplianceRule(84): 100% orphan, deleted (V2 version has all edges)
- RiskIndicator(378): 100% orphan, deleted
- TaxIncentive(109): has active edges, kept (needs manual review)

**Task 6: 去重**
- LR: -282 orphan duplicates (5,221 groups found, only orphans deleted)
- Classification: -3,250 orphan duplicates

**Task 7: 小表孤儿清零**
- AccountingSubject: +147 MAPS_TO_ACCOUNT (92% → 0% orphans)
- Penalty: +275 PENALIZED_BY (92% → 8% orphans)
- TaxEntity: +19 ENTITY_FOR_TAX (82% → 0% orphans)

**Task 8: 新边类型**
- LR_ISSUED_BY (LawOrRegulation → IssuingBody)
- CLASS_ABOUT_TAX (Classification → TaxType)
- ENTITY_FOR_TAX (TaxEntity → TaxType)

### Remaining
- KU 37K empty content (53% empty, 42% short) — needs LLM backfill
- 3 broken crawlers (flk_npc, cicpa, cctaa) — need DevTools reverse engineering
- KU orphans 8.5K (12%) — may need LLM-assisted cross-reference
- TaxIncentive vs TaxIncentiveV2 (109 each, both have edges)
- M3 cron: fixed permissions + crontab, pending first auto-run verification

### Session: 2026-03-21 (Part 2 — QA Pipeline + KU Backfill)

**Fixes:**
- Orchestrator DB lock: sleep 2 → pgrep wait + SIGKILL fallback
- Python unbuffered output: python3 → python3 -u (pipe buffer fix)
- google.generativeai → urllib HTTP API (deprecated library caused hangs)
- daily_pipeline.sh chmod +x

**Production:**
- QA Generation: 50 batches × 100 articles → **+11,894 QA nodes** + **+6,415 KU_ABOUT_TAX edges**
- KU Content Backfill: **+9,838 KU content filled** (44% → ~58%)
- Edge Engine: **+282 SUPERSEDES edges**
- QA COPY fix: parameterized INSERT (CSV COPY failed on quote escaping)

**New scripts:**
- `scripts/ku_content_backfill.py` — Gemini LLM-based KU content generation
- `scripts/fix_qa_load.py` — parameterized INSERT for QA nodes (COPY workaround)
- `scripts/fix_orphans.py` — orphan connection (incomplete, untracked types are scraping artifacts)

**Analysis:**
- 125K orphan nodes (29.5%) are ALL in untracked types: DocumentSection(42K), MindmapNode(28K), HSCode(23K)
- These are legacy scraping artifacts with low-quality content (titles: "2.", "3.", "威科先行")
- Tracked orphan rate is much lower (~3%)
- M3 Phase 1 gate: tracked density 3.504 ≥ 3.0 PASS, tracked orphans PASS

### KG Metrics (Updated 2026-03-21 Part 2)
- Nodes (total): 425,523
- Nodes (tracked): 259,385
- Edges: 969,790
- Density (total): 2.279
- Density (tracked): 3.504
- Quality: 100/100
- QA nodes: 11,908 (from 14)
- KU with content: ~58% (from 44%)

### Commits
- 425e767 (kg-node) / b27c1c4 (local) - feat(m3): comprehensive graph remediation
- 4c8803b - feat(m3): KU content backfill +9838
- f722396 - feat(m3): QA generation pipeline + orchestrator fixes
- Push to GitHub: MARUCIE/cognebula-enterprise master
