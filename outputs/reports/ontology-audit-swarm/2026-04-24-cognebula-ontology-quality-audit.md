# CogNebula Ontology Quality Audit — Swarm Synthesis

**Date**: 2026-04-24
**Swarm group**: ontology-audit-swarm
**Participants**: advisor-hara (structural minimalism), advisor-hickey (complecting), advisor-meadows (systems dynamics), advisor-munger (inversion risk)
**Prod snapshot**: 547,761 nodes / 1,302,476 edges / 62 node tables / 73 rel tables
**Audit data**: `/tmp/cog_stats.json` + `/tmp/cog_quality.json` + `/tmp/cog_audit.json`

---

## Executive Summary

1. **The audit-reported `content_coverage = 0.51` is a measurement artifact, not a content gap.** Roughly 9 code-graph pollution types (ArrowFunction / Class / Method / Folder / File / External / Section / Interface / Function) sit in the coverage denominator as schema-present but row-empty tables, plus 3 metadata types (HSCode 22,976 / Classification 28,035 / MindmapNode 28,526) that were never designed to carry `content` fields. Re-scoping coverage to canonical domain types compresses the true content gap from 29pp to an estimated 5–8pp.

2. **Ontology polyphony is real — 83 live types vs 35 canonical vs 37 Brooks ceiling — and driven by a reinforcing loop with no balancing counterweight.** `rogue_in_prod` (64 types) breaks into 5 named buckets: V1/V2 bleed (5), duplicate clusters (4 domains × ~5 types each), SaaS-layer leak (6), legacy (7), code-graph pollution (~27). There is no write-entry validation; anyone adding a node table today bypasses both the canonical spec and the Brooks ceiling alarm.

3. **Structure is sound; the real decomplection sin is at the property and predicate layer.** `KnowledgeUnit` node is correctly generic (Hickey verdict). The actual complection is (a) `legacyType` string column that makes provenance masquerade as type identity, and (b) a single `KU_ABOUT_TAX` predicate carrying 166,466 edges with no distinction between *defines*, *sets threshold*, *prescribes procedure*, or *cites precedent*. Splitting predicates and demoting `legacyType` to a `SOURCED_FROM` edge would make the graph useful for the first time.

4. **The highest-leverage intervention is gate redefinition, not data migration.** Munger inversion #1: aggressively collapsing 64 rogue tables into KnowledgeUnit would push KnowledgeUnit share from 33.9% to 55%+ and pass every current gate — while destroying retrievability. Redefining the gate (exclude code-graph + metadata types, add `rogue_count = 0` and `canonical_coverage ≥ 80%` as ANDed conditions) must precede any DROP TABLE or MERGE.

5. **Any remediation batch must be snapshot-gated and sequenced.** Meadows + Munger convergence: `D1 snapshot → C (gate redef) → P (write-entry whitelist) → B3 TaxIncentive V2 merge → B4 legacy folding → B0 empty-table drops → B2 V1/V2 suffix renames`. Reverse order risks dangling FKs (B0 before snapshot = permanent data loss) and sweeping-before-closing-window (B-batch before whitelist = drift reopens within weeks).

---

## Live Prod Snapshot

| Metric | Value | Notes |
|---|---|---|
| Total nodes | 547,761 | 33.9% KnowledgeUnit (185,455) |
| Total edges | 1,302,476 | 30% INTERPRETS (390,756), 12.8% KU_ABOUT_TAX (166,466) |
| Node tables (live) | 62 schema / 60 with rows | 2 empty: TaxIncentiveV2 coexists with canonical |
| Canonical types (v4.2) | 35 | Brooks ceiling = 37 |
| Live vs canonical | over_ceiling_by = 46 | +131% bloat |
| `intersection` (correctly-in-canonical) | 19 | Only 54% of canonical is live |
| `missing_from_prod` | 16 | DeductionRule, TaxItem, TaxBasis, TaxTreaty, IndustryBenchmark, etc. |
| `rogue_in_prod` | 64 | 5 named buckets below |
| Audit verdict | FAIL, severity = high | Canonical-coverage gate failing |
| Quality-gate score | 100 (PASS) | **Gate definition is broken** — see Munger #1 |

### Rogue buckets (64 types)

| Bucket | Count | Examples | Remediation |
|---|---|---|---|
| `v1_v2_bleed` | 5 | ComplianceRuleV2, FilingFormV2, FormTemplate, RiskIndicatorV2, TaxIncentiveV2 | B2 rename / B3 merge |
| `duplicate_clusters.tax_rate` | 5 | TaxRateDetail, TaxRateMapping, TaxRateSchedule, TaxCodeIndustryMap, TaxpayerRatePolicy | B2D collapse to TaxRate |
| `duplicate_clusters.accounting` | 6 | AccountEntry, AccountingEntry, AccountRuleMapping, ChartOfAccount, ChartOfAccountDetail, DepreciationRule | B2C collapse to AccountingSubject |
| `duplicate_clusters.industry` | 5 | Industry, FTIndustry, IndustryKnowledge, IndustryBookkeeping, IndustryRiskProfile | B2B collapse to IndustryBenchmark |
| `duplicate_clusters.policy` | 3 | TaxPolicy, RegionalTaxPolicy, TaxExemptionThreshold | B2A collapse to TaxIncentive |
| `saas_leak` | 6 | ChurnIndicator, CrossSellTrigger, CustomerProfile, EnterpriseType, EntityTypeProfile, ServiceCatalog | **Extract to separate SaaS graph** (Hara) |
| `legacy` | 7 | CPAKnowledge, DocumentSection, FAQEntry, HSCode, MindmapNode, TaxClassificationCode, TaxCodeDetail | B4 fold (CPAK + Mindmap); keep HSCode/Classification as metadata-only |
| `other` (code-graph + misc) | 27 | ArrowFunction, Class, Function, Method, Folder, File, Interface, Section, External, Document | **Delete** — pollution from tree-sitter indexing mixed into domain KG |

### Quality metric deep-dive

| Type | Total | With content | Coverage |
|---|---|---|---|
| KnowledgeUnit | 185,455 | ~94K | ~51% (the headline gap) |
| LegalClause | 83,443 | 83,418 | 100% |
| LegalDocument | 54,865 | 54,863 | 100% |
| DocumentSection | 42,252 | (no content field designed) | N/A |
| Classification | 28,035 | 27,889 | 99.5% (title, not content) |
| MindmapNode | 28,526 | (structural, not prose) | N/A |
| HSCode | 22,976 | (code-label, not content) | N/A |

**Core finding**: the 51% gap is concentrated in KnowledgeUnit. Other node types either meet coverage or are structurally exempt. Treating this as one aggregate "content_coverage" number masks that the problem is in exactly one type, where the fix is enrichment of 91K KU rows, not blanket content-filling.

---

## Synthesis — 4-Lens Findings, MECE-Merged

### (S1) Structural layer (Hara + Hickey)

- **Kill 9 code-graph types immediately**: ArrowFunction, Class, Function, Method, File, Folder, Interface, Section, External. These are empty schemas left over from tree-sitter indexing experiments; they inflate `rogue_in_prod` and `brooks_ceiling` comparisons without carrying data.
- **Move 6 SaaS-leak types to a separate service graph**: ChurnIndicator, CrossSellTrigger, CustomerProfile, EnterpriseType, EntityTypeProfile, ServiceCatalog. These belong to customer-success tooling, not tax/law ontology. Bi-graph separation prevents tax queries from touching CRM rows.
- **Exclude metadata-only types from content_coverage denominator**: HSCode (22,976), Classification (28,035), MindmapNode (28,526), DocumentSection (42,252). None were designed to carry `content`; including them in the coverage metric is a false negative.

### (S2) Semantic layer (Hickey)

- **Demote `legacyType` from node column to edge**: replace `KnowledgeUnit.legacyType = 'cpa_...'` with `(KnowledgeUnit)-[:SOURCED_FROM]->(LegacySource)`. Provenance is a relationship, not a type attribute. Frees KnowledgeUnit to be genuinely polymorphic.
- **Split `KU_ABOUT_TAX` (166,466 edges) into 4 semantic predicates**:
  - `DEFINES_TERM` (definition text)
  - `SETS_THRESHOLD` (numeric boundaries)
  - `PRESCRIBES_PROCEDURE` (how-to)
  - `CITES_PRECEDENT` (case/ruling reference)
- The current undifferentiated predicate is the #1 retrieval-precision killer. Classifier can be bootstrapped from the existing `legacyType` tag + content-length heuristics.
- **Canonicalize the INTERPRETS-family (390,756 edges)** into a documented taxonomy. 5 predicates inside INTERPRETS* already exist; promote them to first-class.

### (S3) Systemic layer (Meadows)

- **R1 reinforcing loop (currently unchecked)**: ad-hoc ETL or agent-authored schema migration → new table added → canonical drift increases → next ETL sees drift as precedent → more new tables. Loop doubling time observed at ~2 weeks.
- **B_MISSING balancing loop (must be installed)**: every write-schema operation must pass a whitelist check against `schemas/ontology_v4.2.cypher`. Any new type requires a canonical-decision PR (not a migration script). Meadows Leverage #8: the rules of the system are the leverage, not the content.
- **Leverage #3 (goal reformulation)**: replace goal `quality_score = 100` with `canonical_coverage_ratio ≥ 0.80 AND rogue_types = 0 AND over_ceiling_by ≤ 0`. Three conditions, ANDed, not a single metric that can be gamed.

### (S4) Risk layer (Munger — inversions)

- **(I1) Goodhart metric-gaming**: reclassifying 64 rogues → KnowledgeUnit via bulk MERGE pushes KU share 33.9% → 55%+ and every coverage-by-title metric passes, while precision collapses. **Therefore**: gate redefinition must precede any B-batch migration.
- **(I2) Weekend bulldozer**: running B0 + B2 + B3 + B4 in sequence with `--execute` before write-entry whitelist = 185K KU predicates re-wired by blind UPSERT, no rollback. **Therefore**: atomic per-batch, snapshot before each, whitelist gate between.
- **(I3) Empty canonical auto-stubs**: creating stub rows for the 16 `missing_from_prod` types pads the intersection count from 19 to 35 without adding a single fact. Looks like progress; is debt. **Therefore**: missing types become canonical only when first real row is migrated in, not pre-stubbed.
- **(I4) Swarm-theatre synthesis**: merging 4 advisor outputs into a Frankenstein plan where every recommendation is partially adopted is worse than picking 2 and executing fully. **Therefore**: this PDCA adopts Munger's gate-first + Meadows's whitelist, defers 3 of 5 Hara recs and 1 of 5 Hickey recs to Wave 2.
- **(I5) Irreversibility trap**: `DROP TABLE CPAKnowledge` before D1 snapshot is permanent. Dangling FKs in REL tables become un-diagnosable. **Therefore**: D1 snapshot is a hard precondition; any agent that proposes B0/B2/B3/B4 without snapshot evidence is refused.

---

## Per-Expert Evidence (verbatim findings)

### advisor-hara — Verdict: RESTRUCTURE

1. **Delete 15 code-graph pollution types**: ArrowFunction, Class, Function, Method, File, Folder, Interface, Section, External, Document, Community, LifecycleActivity, LifecycleStage, Topic, SpecialZone. These are indexing artifacts with 0 domain semantics.
2. **Isolate SaaS-layer leaks to a separate service graph**: 6 types (ChurnIndicator, CrossSellTrigger, CustomerProfile, EnterpriseType, EntityTypeProfile, ServiceCatalog) — do not belong in a tax/compliance KG.
3. **Drop all V2-suffixed tables after merge**: ComplianceRuleV2, FilingFormV2, RiskIndicatorV2, TaxIncentiveV2. Suffix naming is a smell; canonical should own the name.
4. **Exclude HSCode + Classification + MindmapNode from content_coverage**: these are taxonomy/navigation nodes, not prose-carrying nodes. Including them drops measured coverage from ~92% to 51% — a 29pp artifact.
5. **KnowledgeUnit should eventually split into semantic subtypes** (TermDefinition / ProcedureStep / Threshold / PrecedentCitation). Wave 3 work, not Wave 1.

### advisor-hickey — "Structure is fine; data is complected"

1. **Kill `legacyType` as a node column**. It is provenance masquerading as identity. Migrate to `(KU)-[:SOURCED_FROM]->(Source)` edge.
2. **Split `KU_ABOUT_TAX` (166,466 edges)** into `DEFINES_TERM / SETS_THRESHOLD / PRESCRIBES_PROCEDURE / CITES_PRECEDENT`. Classifier: length + lexical features + existing `legacyType` tag.
3. **Treat the 5 INTERPRETS-family predicates as canonical taxonomy** — don't collapse them, formalize them.
4. **Content gap is a value problem, not a structure problem**. The 51% is real *for KU rows*, but filling it is an LLM-enrichment pipeline, not a schema migration.
5. **Freeze 83 tables before adding more**. Deletion-before-addition is non-negotiable for 6 months.

### advisor-meadows — Systems dynamics

- **R1 (reinforcing, uncapped)**: convenience of creating new table > cost of reusing canonical → drift accelerates.
- **B_MISSING (must install)**: write-time validation against `schemas/ontology_v4.2.cypher`. PR + canonical-decision gate, not a migration-script fait-accompli.
- **Leverage #3 (goal)**: redefine quality_score as composite (canonical_coverage AND rogue_types == 0 AND over_ceiling_by ≤ 0).
- **Leverage #8 (rules)**: write-entry whitelist is the single highest-leverage change; without it, B-batch work is sweeping with windows open.
- **Sequence warning**: don't run B0/B2/B3/B4 before write-entry whitelist lands, or drift reopens in ≤ 4 weeks.

### advisor-munger — Inversions

- **I1 Goodhart-gaming**: reclass-to-KU inflates share without adding retrievability → kill the metric that rewards it before you build the pipeline that exploits it.
- **I2 Weekend bulldozer**: B0+B2+B3+B4 in one --execute run = 185K predicate rewire with zero undo → atomic batches, snapshot gate between each.
- **I3 Empty canonical stubs**: 16 missing types padded to intersection inflates coverage metric with zero real facts → only promote a canonical type when first real row lands.
- **I4 Frankenstein synthesis**: partially adopt 5 recs from 4 advisors → noise. Pick 2 and execute fully.
- **I5 Irreversibility**: DROP TABLE before D1 snapshot = dangling FK permanent. Snapshot is a gate, not a suggestion.

---

## PDCA Plan

### P — Plan (this audit is the Plan)

1. **Redefine the quality gate** to a 3-condition composite:
   - `canonical_coverage_ratio = (nodes_in_canonical_types) / (nodes_in_domain_types) ≥ 0.80`
   - `rogue_types_count = 0`
   - `over_ceiling_by ≤ 0`
   All three ANDed. `domain_types` excludes: code-graph pollution (9), SaaS-leak (6), metadata-only (3 — HSCode / Classification / MindmapNode).
2. **Install write-entry whitelist** at the schema-migration layer. Any `CREATE NODE TABLE` outside `schemas/ontology_v4.2.cypher` fails the pre-commit hook; requires a PR adding to canonical first.
3. **Sequence the B-batch** with snapshot gates:
   `D1 snapshot → C (gate redef) → P (whitelist) → B3 TaxIncentiveV2 merge → B4 legacy fold (CPAK+Mindmap) → B0 empty-drop → B2 V1/V2 renames`.

### D — Do (not yet triggered, HITL-gated)

| Batch | Scope | Trigger word | Precondition |
|---|---|---|---|
| D1 | Kuzu full snapshot to `/home/kg/backups/ontology-audit-2026-04-24.kuzu` | `D1` | None |
| C0 | Patch `quality_gate` definition; re-run audit | `C0` | D1 done |
| P0 | Install `ontology-whitelist-guard.py` pre-commit hook | `P0` | C0 done |
| B3 | `migrate_phase1d_taxincentive_merge.py --execute` (prod) | `B3` | P0 done + demo fixture green |
| B4 | `migrate_phase4_legacy_folding.py --execute` (prod) | `B4` | B3 done |
| B0 | Drop 9 code-graph + 27 misc empty tables | `B0` | B4 done |
| B2 | Rename V2 tables to canonical | `B2` | B0 done |
| H1 (Hickey) | Split `KU_ABOUT_TAX` into 4 semantic predicates | `H1` | B2 done |
| H2 (Hickey) | Migrate `legacyType` column → `SOURCED_FROM` edge | `H2` | H1 done |

**Non-goals for this wave (Wave 2 / Wave 3)**:
- KnowledgeUnit subtyping (Hara #5)
- Missing canonical type backfill (16 types) — only promote on first real row
- INTERPRETS-family formalization (Hickey #3)

### C — Check (after each D batch)

- `POST /api/v1/audit` with new gate definition → expect `verdict = PASS` only after B3+B4+B0+B2 all complete
- Diff rogue_types list against pre-batch snapshot → expect Δ = removed set matches B-batch plan
- Sample 50 random KU rows → expect `legacyType` absent after H2, `SOURCED_FROM` edge present

### A — Act (after wave closes)

- Sync `schemas/ontology_v4.2.cypher` to reflect deletions (remove 36 rogue types from historical doc)
- Update PDCA 4-doc set (PRD + SYSTEM_ARCHITECTURE + USER_EXPERIENCE_MAP + PLATFORM_OPTIMIZATION_PLAN) to reference Wave 1 close
- Add rolling ledger entry: "Gate redefined 2026-04-24; 3-condition ANDed; metric-gaming resistant"
- Freeze 83 → target 35 ± 2 after Wave 1

---

## Decisions / Next Actions

| Decision | Owner | Priority | Due | Status |
|---|---|---|---|---|
| Adopt 3-condition composite gate (`canonical_coverage ≥ 0.80 AND rogue_types = 0 AND over_ceiling_by ≤ 0`) | Maurice | P0 | Pre-D1 | Proposed in this audit |
| D1 snapshot before any B-batch | Maurice + ops | P0 | Before B3 | Blocked on explicit `D1` trigger |
| Install `ontology-whitelist-guard.py` pre-commit hook | Maurice | P0 | Before B3 | Not started |
| Exclude code-graph + SaaS-leak + metadata-only from coverage denominator | Maurice | P0 | C0 batch | Spec drafted in S1 above |
| Sequence B3 → B4 → B0 → B2 (NOT parallel) | Maurice | P0 | After P0 done | Plan drafted |
| Defer KnowledgeUnit subtyping (Hara #5) to Wave 3 | Maurice | P3 | +6 months | Explicit deferral |
| Defer missing canonical backfill (16 types) — only on first real row | Maurice | P3 | Ongoing | Policy decision |
| Run `auto-visual-swarm-review` on this audit's HTML | Maurice | P1 | Today | Scheduled post-HTML write |

---

## Appendix — Rogue type inventory (full, 64 items)

**v1_v2_bleed (5)**: ComplianceRuleV2, FilingFormV2, FormTemplate, RiskIndicatorV2, TaxIncentiveV2

**duplicate_clusters.tax_rate (5)**: TaxCodeIndustryMap, TaxRateDetail, TaxRateMapping, TaxRateSchedule, TaxpayerRatePolicy

**duplicate_clusters.accounting (6)**: AccountEntry, AccountRuleMapping, AccountingEntry, ChartOfAccount, ChartOfAccountDetail, DepreciationRule

**duplicate_clusters.industry (5)**: FTIndustry, Industry, IndustryBookkeeping, IndustryKnowledge, IndustryRiskProfile

**duplicate_clusters.policy (3)**: RegionalTaxPolicy, TaxExemptionThreshold, TaxPolicy

**saas_leak (6)**: ChurnIndicator, CrossSellTrigger, CustomerProfile, EnterpriseType, EntityTypeProfile, ServiceCatalog

**legacy (7)**: CPAKnowledge, DocumentSection, FAQEntry, HSCode, MindmapNode, TaxClassificationCode, TaxCodeDetail

**other (27)**: ArrowFunction, Class, Community, DeductionStandard, Document, External, File, FilingObligation, Folder, Function, Interface, LawOrRegulation, LifecycleActivity, LifecycleStage, Method, RegulationClause, Section, SpecialZone, SpreadsheetEntry, TaxCalendar, TaxCreditIndicator, TaxPlanningStrategy, TaxRateVersion, TaxRiskScenario, TaxWarningIndicator, TaxpayerStatus, Topic

**Missing from prod (canonical, 16)**: DeductionRule, FilingFormField, FinancialIndicator, FinancialStatementItem, IndustryBenchmark, InvoiceRule, JournalEntryTemplate, PolicyChange, ResponseStrategy, SocialInsuranceRule, TaxAccountingGap, TaxBasis, TaxItem, TaxLiabilityTrigger, TaxMilestoneEvent, TaxTreaty

---

Maurice | maurice_wen@proton.me
CogNebula Enterprise — Ontology Quality Audit (swarm synthesis) — 2026-04-24
Data source: POST /api/v1/{stats,quality,audit} on 2026-04-24 06:20 UTC
