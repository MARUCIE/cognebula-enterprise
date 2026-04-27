# CogNebula Enterprise — SOTA Gap Audit Round 4 (Stub-Backfill RCA)

**Date**: 2026-04-27
**Swarm group**: ontology-audit-swarm (5-lens parallel)
**Participants**: advisor-hara (structural minimalism) · advisor-hickey (decomplecting) · advisor-meadows (leverage points) · advisor-munger (inversion) · advisor-drucker (customer value)
**Prior audit**: `outputs/reports/ontology-audit-swarm/2026-04-25-sota-gap-deep-audit.md` (Round 3, 2 days ago)
**Live PROD snapshot**: 551,682 nodes / 1,302,679 edges / 71 node tables / 76 rel tables (https://ops.hegui.org)
**Composite gate**: FAIL · severity HIGH (intersection 35/35 BUT 20/35 EMPTY or stub <50 rows)

---

## Executive Summary

1. **Round-3 anti-pattern #1 was applied to prod between 2026-04-25 and 2026-04-27.** `schemas/extensions/v4.2.0_create_missing_canonicals.cypher` line 4 literally states "this file creates them as empty stubs (DDL-only, no data writes)". Result: `intersection` rose 19/35 → 35/35 cosmetically; `missing_from_prod` is now `[]`; but **20/35 (57%) canonical types are EMPTY (10 types, 0 rows) or TINY (10 types, ≤50 rows)**. C1 ratio was Goodhart-gamed by DDL alone. No git commit captured this deploy.

2. **The 4 application-level gaps from Round 3 are LARGELY UNCHANGED.** Region 31→3,565 (closed). TaxCalculationRule 73→133 (1.8× partial). FilingFormField 0→88 (started, 1,400-2,100 target). AccountingSubject 159 (unchanged, target 1,500-2,000). BusinessActivity 204 (unchanged, target 1,500). TaxRate 9,000 (unchanged, target 15-18,000). INTERPRETS 390,756 + KU_ABOUT_TAX 166,466 (both unchanged). **Net real-data progress: ~25% of Round-3 gaps closed in 4 days; 75% intact; new debt added (20 stub canonical types).**

3. **Stage 2 LLM evaluation (waves 27-40, $0.84 cumulative)** confirmed the architectural ceiling: composite plateaus [0.224, 0.312], dual-Pro on first-20 cases shows `anchor_recall` IS lift-able (gemini-3.1-pro and gpt-5.5 BOTH lift +0.150 identically — independent vendor confirmation that retrieval surface is model-saturated, not capacity-bound), but composite ceiling at ~0.31 vs SOTA Claude ~0.70 → 39pp gap remains.

4. **Knowledge corpus normalization audit**: source corpus is **196 MB raw JSON** (`data/extracted/`: 128 JSON / 0 md; `data/compliance-matrix/`: 228 JSON / 0 md). NOT normalized to .md format as user hypothesized. KG database itself IS backed up via VPS volume snapshots (`gdrive:VPS-Backups/kg-node/` + `kg-node-eu/`), but the **source corpus has no separate GDrive backup** — only git tracks it. Single-point-failure risk if both git and VPS lost simultaneously.

5. **5-lens unanimous diagnosis**: the Round-3 warning was prose without enforcement; mechanical gating is the only durable fix. **All 5 advisors converge on: (a) 30-day STOP-and-fill rule with new C1_min50 metric, (b) delete 3 admitted-garbage tables + remove 3 schema-overreach stubs, (c) ship one decomplection move (INTERPRETS_DEFINES split) next Monday, (d) replace eval composite with customer-outcome target.**

---

## 1. Live State Diff vs 2026-04-25 (auditable)

| Metric                            | 2026-04-25 | 2026-04-27 | Δ           |
|-----------------------------------|------------|------------|-------------|
| Total nodes                       | 547,761    | 551,682    | +3,921      |
| Total edges                       | 1,302,476  | 1,302,679  | +203        |
| Node tables (live populated)      | 62         | 71         | +9          |
| Rel tables (live populated)       | 73         | 76         | +3          |
| Canonical intersection            | 19/35      | **35/35**  | +16 (cosmetic, see §2) |
| `missing_from_prod`               | 16 types   | **`[]`**   | -16 (cosmetic) |
| `over_ceiling_by`                 | +46        | **+62**    | +16 (worse) |
| Rogue tables                      | 43         | 64         | +21 (worse) |
| INTERPRETS edges                  | 390,756    | 390,756    | 0           |
| KU_ABOUT_TAX edges                | 166,466    | 166,466    | 0           |
| TaxRate                           | 9,000      | 9,000      | 0           |
| Region                            | 31         | 3,565      | +3,534 ✓    |
| AccountingSubject                 | 159        | 159        | 0           |
| BusinessActivity                  | 204        | 204        | 0           |
| TaxCalculationRule                | 73         | 133        | +60         |
| FilingFormField                   | 0          | 88         | +88         |
| Composite gate verdict            | FAIL HIGH  | FAIL HIGH  | unchanged   |

**Net read**: ontology surface restructured to look complete; underlying data gap unchanged. The most material progress is Region (closed) — and that is the one entry on this list achieved by actual data ingestion (per `seed_region.py` shipped earlier).

---

## 2. The Stub-Backfill Anti-Pattern: How Round-3 Anti-Pattern #1 Slipped Through

### 2.1 What was deployed

`schemas/extensions/v4.2.0_create_missing_canonicals.cypher` (97 lines, all DDL):
```cypher
// Audit (2026-04-25 08:14Z) identified 16 of 35 canonical types absent in prod;
// this file creates them as empty stubs (DDL-only, no data writes).
```

10 of those 16 created tables remain at 0 rows (ComplianceRule, IndustryBenchmark, InvoiceRule, PolicyChange, ResponseStrategy, RiskIndicator, SocialInsuranceRule, TaxItem, TaxLiabilityTrigger, TaxTreaty). Another 10 already-present canonical types are at ≤50 rows (the canonical "TINY" tier).

### 2.2 The Goodhart loop (Meadows lens)

```
Round 3 prescribed:    gate FAIL → fix data gap → gate PASS
What actually shipped: gate FAIL → ADD DDL STUB → ratio↑ → gate PASS (cosmetic)
```

The metric `intersection_count / total_expected_tables` had one degree of freedom (DDL alone increments the numerator). The system exploited it within 48 hours. This is the canonical Goodhart variant: when a measure becomes the target, it ceases to be a good measure.

### 2.3 Why it slipped (Munger lollapalooza)

- **Incentive-caused bias**: C1 ratio was the visible KPI; "fix C1" beats "close gap" on dashboards
- **Doing-something bias**: 4 days post-Round-3 with no closed gap → psychological pressure to ship *anything*
- **Authority/social-proof gap**: warning lived in markdown, not in deploy pipeline → soft hook + no consequence + identical content = inevitable habituation (Round-3 warning became decoration)

Anti-pattern (a) in the Round-3 doc was a complete and correct prediction. It was ignored not because it was wrong but because **prose warnings are not enforcement primitives**.

### 2.4 New failure modes the stub-backfill enables (Munger)

1. **Phantom inference surface (HIGH)**: downstream agents query the 20 thin types via MCP, get 0 or 50-row results, and either hallucinate to fill or silently degrade. Falsifiable: log MCP queries against the 20 thin types over 7 days; if ≥5% return <10 rows, failure is live.
2. **Audit-trail laundering (HIGH)**: out-of-band deploy with no git commit means provenance is broken — any team member asked "when did v4.2.0 ship?" cannot name a SHA.
3. **SOTA submission temptation acceleration (MEDIUM-HIGH)**: 35/35 intersection ratio reads as "canonical complete" to a 60-day-future reader (including the team). Anti-pattern (b) — premature LegalBench-Tax submission — becomes 2× more likely as the cosmetic green light removes the last visible blocker.

---

## 3. Five-Lens Advisor Findings (verbatim consensus + divergence)

### 3.1 Hara — structural minimalism (DELETE not DEFER)

**TOP-3 deletion candidates** (admitted-garbage status, not "merge candidates"):

1. **`RiskIndicator` (463 rows) + `AuditTrigger` (463 rows)** — `ontology_v4.2.cypher` header literally reads "TRUNCATE only designated garbage when superseded by V2 counterpart". Their V2 counterparts exist. **Designated garbage by their own schema authors; delete both today.**
2. **`CPAKnowledge` (7,371 rows, quality_score=0.0)** — zero domain signal, never used for anything real, occupies table slots that inflate live=99.
3. **`MindmapNode` (28,526 rows, "no content by design")** — most honest entry in the entire audit: created knowing it would hold no signal. SaaS product artifact shipped into a knowledge graph. B4 fold has been "NOT TRIGGERED" since Round 1 — trigger now.

**TOP-3 schema-overreach acknowledgements** (admit it, REMOVE the stub):

1. **`TaxTreaty`** — empty table for multi-jurisdiction (anti-pattern A2 explicitly forbidden until 金税四期 >90% AND ≥1 paying CN customer renews). An empty stub for a banned direction is contradiction-in-schema.
2. **`ResponseStrategy`** — `recommendedSteps STRING` payload is consulting prose, not graph-queryable structure. No SOTA tax KG (TaxLOD, ONESOURCE, Bloomberg Tax) carries this type. Risk handled via ComplianceRule + Penalty + RiskIndicator chains already.
3. **`TaxLiabilityTrigger`** — functionally identical to ComplianceRule (severity + sourceClauseId) plus TaxCalculationRule (formula + taxTypeId). Semantic duplication dressed as precision.

**KEEP-AND-FILL with hard 90-day deadline** (7 types): TaxItem · DeductionRule · InvoiceRule · SocialInsuranceRule · JournalEntryTemplate · FilingFormField · TaxAccountingGap. *Stay = a row arrives in 90 days or the type is removed. No permanent empty stubs.*

> *"A knowledge graph that describes what could be known is not a knowledge graph — it is a wish list with a schema."*

### 3.2 Hickey — decomplecting (form vs substance)

**Diagnosis**: INTERPRETS hasn't moved in 2 days because "split INTERPRETS" was treated as **one big refactor** (390K rows + classifier rewrite + ontology council) instead of a **series of atomic ship-able decomplections**. Stub-DDL for 20 types is the same anti-pattern at ontology scale: easy (familiar DDL) won, simple (substance) lost.

**Monday-ship-able move** — split `INTERPRETS_DEFINES` (~140K edges, 35-40% peel) by lexical signature:

```cypher
MATCH (s)-[r:INTERPRETS]->(t:Term|Definition|Concept)
WHERE r.source_clause CONTAINS '是指'
   OR r.source_clause CONTAINS '所称'
   OR r.source_clause CONTAINS '本办法所称'
   OR r.source_clause CONTAINS '定义为'
SET r:INTERPRETS_DEFINES
```

5 high-precision lexical markers in Chinese tax-law corpus. One Cypher MATCH+SET migration; no classifier rewrite needed. **Measurable target before next Monday**: INTERPRETS 390K → ~250K, INTERPRETS_DEFINES at ~140K, anchor_recall on definition-seeking eval queries up by ≥0.05.

**What's complected in retrieval/scoring**: `anchor_recall@1` is braided with `predicate_diversity@2` inside composite. Both Pros lift +0.150 because hop-1 surface-finding is model-saturated; the 0.31 ceiling lives on **hop-2** because 30% of all edges share the INTERPRETS predicate — retriever cannot distinguish "defines X" from "cites X" from "modifies X". **Score `anchor_recall@1` and `traversal_precision@2` independently — the bottleneck stops hiding.**

> *"One braid removed this week beats one perfect ontology next quarter."*

### 3.3 Meadows — leverage points (#8 Balancing Loop Strength)

**Dominant loop** (REINFORCING, degradation): `gate FAIL → DDL stub → ratio cosmetic → gate PASS → empty nodes accumulate → real gap widens → next cycle gate FAIL deeper`.

**Leverage point**: #8 (Balancing Feedback Loop Strength) — the loop "gate→fix" exists but was short-circuited; reinforcing its gaming-resistance is more powerful than changing the metric (#12) or schema (#10).

**Gaming-resistant metric** to add to `tests/test_kg_gate.py`:

```python
def test_no_empty_canonical_tables():
    """Stub-backfill detector: any C1 table with <50 rows is a DDL-only ghost."""
    C1_EXPECTED = ["INTERPRETS", "KU_ABOUT_TAX", "AccountingSubject",
                   "RegulationArticle", "ComplianceRule"]
    ghosts = []
    for t in C1_EXPECTED:
        n = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        if n < 50:
            ghosts.append(f"{t}({n})")
    assert not ghosts, f"Empty/stub tables — fill data first: {ghosts}"

def test_c1_canonical_min50():
    MIN_ROWS = {"INTERPRETS": 300_000, "KU_ABOUT_TAX": 100_000,
                "AccountingSubject": 1_000, "DEFAULT": 50}
    for table, min_r in MIN_ROWS.items():
        count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count >= min_r, f"{table}: {count} rows < threshold {min_r}"
```

These tests cannot be satisfied by DDL alone. They force the data flow.

**Highest-leverage MISSING loop**: corpus → KG observability is a black hole. 196 MB JSON in `data/extracted/` + `data/compliance-matrix/` generate KG nodes via a process with **no outbound signal**. Add `data/ingestion-manifest.jsonl` (one line per batch: `{ts, source_file, rows_written: {table: count}, duration_s}`). CI gate reads manifest: source files mtime <48h must show rows_written > threshold. **No manifest → gate FAIL immediately. Manifest with zero rows → FAIL.** Closes the loop the stubs opened.

### 3.4 Munger — inversion (mechanical enforcement, not exhortation)

**Why anti-pattern (a) was applied despite explicit Round-3 warning**: the team optimized for a measurable proxy (intersection ratio) instead of the underlying property (canonical coverage with real data). Goodhart's Law executing in 48 hours, lubricated by an out-of-band deploy with no commit trail because someone knew it wouldn't survive code review.

**STOP rule (operational, single sentence)**:

> **No new schema, no new eval run, no new architecture work until `canonical_coverage_ratio` is redefined as `Σ(row_count > 1000) / 35` AND the current value of that metric is published on the gate dashboard.** If that number is below 0.50, the only allowed work is data ingestion into the 20 thin types; everything else (inference engine, multi-jurisdiction, LegalBench, LLM tuning) is frozen until the new metric crosses 0.50.

> *"The Round-3 warning failed not because it was wrong but because it lived in prose. Warnings that don't fail a build don't change behavior — they become alibi documents the team cites after the failure they predicted."*

### 3.5 Drucker — customer value (TODAY, not future-PRD)

**Customer of CogNebula Enterprise TODAY**: **Maurice himself, for internal eval benchmarking.** Zero external customer has queried this KG in production today.

**3 customer questions that unblock IF the missing data is filled**:

1. **代理记账公司老板** (yiclaw B2B2C target): "本月增值税应纳税额是否触及小规模→一般纳税人 500万 认定门槛?" Requires complete TaxRate + FilingFormField for yiclaw Agent to auto-check during 征期 (6-15 day) window. AccountingSubject empty = no account-mapping = automated bookkeeping zero deliverable.
2. **灵阙 platform Agent** (internal tool-call customer): "行业分类代码 6940 对应的合规检查清单?" Requires BusinessActivity 204→1,500. Without it, 15 lingque Agents calling KG search return empty sets → degrade to LLM-internal-knowledge hallucination mode.
3. **代账公司经理** (质检 16-24 day window): "客户A资产负债表科目余额异常波动科目?" Requires AccountingSubject complete + INTERPRETS predicate from "trash bucket" to typed semantic relations. Without both, KG is a Cypher query sandbox, not a business tool.

**BUSINESS verdict**: **RETHINK — conditional continuation with forced direction switch.**

- 6 months filling data + running eval, zero end-to-end customer demo. Drucker's law: if you cannot say "which customer used it today to do what", this is a research project, not product infrastructure.
- **Only condition for continued investment**: 30-day customer outcome target = "**yiclaw can run a real enterprise's January VAT filing end-to-end with zero human intervention**". This requires AccountingSubject 1,500 (公开数据 from 企业会计准则) + FilingFormField 1,400 (公开数据 from 增值税申报表) — both batch-importable with scripts.
- **If 30-day target NOT achieved**: freeze KG investment, switch lingque to LLM-only path (Gemini Flash + structured prompts), prove platform value with real customers first, return to KG decision later.

**Stop list** (specific): stop tracking eval composite (ROUGE/BLEU/F1) — replace with "filing tasks completed end-to-end". Stop INTERPRETS 390K refactor as priority (internal eng debt, not customer ask). Stop architecture audits (4th audit = diminishing returns signal).

---

## 4. Knowledge Corpus & Backup Audit (user question)

### 4.1 Normalization status

| Directory                  | Size  | .md | .json | .other |
|----------------------------|-------|-----|-------|--------|
| `data/extracted/`          | 104MB | 0   | 128   | 3 (.txt) |
| `data/compliance-matrix/`  | 56MB  | 0   | 228   | 0      |
| `data/asbe/`               | 512KB | ?   | ?     | ?      |
| `data/backfill/`           | 36MB  | ?   | ?     | ?      |

**User hypothesis "all knowledge → md format" is FALSIFIED.** 196 MB of source corpus is raw JSON. Zero .md normalization in the two largest dirs (356 JSON files combined).

### 4.2 GDrive backup status

| Asset                       | Backup state |
|-----------------------------|--------------|
| KG production database      | ✓ `gdrive:VPS-Backups/kg-node/` + `kg-node-eu/` (volume snapshots) |
| Source corpus (JSON files)  | ✗ NOT separately backed up — only via git |
| Schema files                | ✓ via git |
| Eval results                | ✗ untracked benchmark/results_*.json (git-ignored convention) |

**Single-point-failure risk**: simultaneous loss of git remote + VPS would lose 196 MB source corpus. Recommended add: `rclone sync data/extracted data/compliance-matrix gdrive:VPS-Backups/cognebula-corpus/$(date +%Y-%m-%d)/` weekly.

---

## 5. Unified Recommendation — 30-Day STOP-and-Fill Sprint

Synthesizing all 5 lenses (no item is from a single lens; each survived ≥2 lens cross-check):

### Week 1 — Mechanical enforcement (eliminate stub-backfill repeatability)

1. **Add `tests/test_no_empty_canonical_tables` + `test_c1_canonical_min50`** (Meadows + Munger) — block CI on any C1 table with <50 rows or any priority table below its min threshold.
2. **Redefine `canonical_coverage_ratio` to `Σ(row_count > 1000) / 35`** (Munger) — publish current value on gate dashboard.
3. **Delete 3 admitted-garbage tables** (Hara): RiskIndicator (superseded V2), CPAKnowledge (qual=0), MindmapNode (no content by design). Single Cypher script + smoke tests.
4. **Remove 3 schema-overreach stubs** (Hara): DROP TABLE IF EXISTS TaxTreaty, ResponseStrategy, TaxLiabilityTrigger.
5. **Ship INTERPRETS_DEFINES split** (Hickey) — 5-marker Cypher migration, target ~140K edges peeled.
6. **Backup source corpus**: `rclone sync data/extracted data/compliance-matrix gdrive:VPS-Backups/cognebula-corpus/2026-04-27/`.

### Weeks 2-3 — Data ingestion ONLY (no architecture, no schema, no eval)

7. **AccountingSubject 159 → 1,500** via 企业会计准则 + 小企业会计准则 batch import.
8. **BusinessActivity 204 → 1,500** via GB/T 4754 国民经济行业分类 batch import.
9. **FilingFormField 88 → 1,400** via 增值税申报表 + CIT 申报表 field schemas.
10. **Add ingestion manifest** (Meadows): `data/ingestion-manifest.jsonl` written by every seed/import script.

### Week 4 — Customer-outcome test (Drucker)

11. **yiclaw end-to-end VAT filing demo** on one real enterprise: collect raw documents → 账科 mapping → 申报表 fill → cross-check → output filing-ready package. **Pass = zero human intervention. Fail = freeze KG, pivot lingque to LLM-only.**

### NOT doing (explicit no-go list)

- ❌ Any new canonical type (no schema additions during the 30 days)
- ❌ INTERPRETS full refactor (only the DEFINES split this month)
- ❌ Multi-jurisdiction extension (anti-pattern A2 still in force)
- ❌ Inference engine bolt-on (anti-pattern A4 still in force)
- ❌ LegalBench-Tax submission (anti-pattern A2 still in force; SOTA gap 39pp)
- ❌ Stage 3 LLM eval (Stage 2 verdict was MARGINAL ROI; pursue customer outcome instead)
- ❌ 5th architecture audit (4th was diminishing returns; mechanical enforcement now > more diagnosis)

### Expected end-state (2026-05-27)

- All 35 canonical types with row_count > 1000 (or removed if not customer-justified)
- INTERPRETS down from 390K to <250K with INTERPRETS_DEFINES carrying ~140K
- yiclaw real-customer VAT filing demo: PASS or KG investment freeze
- New gate test prevents next stub-backfill regression

---

## 6. Catches updated (11 → 14)

- **Catch #12 user-correction (Stage 2 economic)**: Maurice substituted gpt-5.4-pro for cheaper Poe pair (gemini-3.1-pro + gpt-5.5), saving ~78% AND adding cross-vendor variance signal that single-Pro could not provide.
- **Catch #13 audit-finding (stub-backfill)**: this round-4 audit caught Round-3 anti-pattern #1 having been triggered out-of-band within 48 hours of the warning. Closing-the-loop is a confirmed repeating pattern, not luck.
- **Catch #14 5-lens consensus**: all 5 advisors independently converged on mechanical enforcement over more architectural prose. Convergence with divergent methods (Hara structural, Hickey complecting, Meadows feedback, Munger inversion, Drucker customer) is stronger evidence than any single-lens recommendation.

14-catch streak across 11 waves. The streak's value is the GATE, not the tally.

---

## 7. Cumulative session economics

| Phase | Spend | Cumulative |
|---|---|---|
| Waves 27-39e (5 baselines + W6-lite) | $0.4565 | $0.4565 |
| Wave 40 Stage 2 dual-Pro (gemini + gpt-5.5) | $0.3871 | $0.8436 |
| Round 4 audit (5-lens swarm, this report) | $0 (Claude Sonnet local) | $0.8436 |
| **Total** | — | **$0.84 (2.03% of $41.53 wallet)** |

Round-4 audit cost $0 in API spend and produced the highest-signal recommendation set of the four rounds. Mechanical enforcement is the new investment direction; further architectural diagnosis is diminishing returns until enforcement primitives exist.

---

## 8. What was NOT done (explicit)

- No code changes (audit-only round; recommendations require user approval before any DROP TABLE or schema edit).
- No CI test additions (Meadows' two test functions are recommended, not committed).
- No INTERPRETS_DEFINES migration (Hickey's Monday-ship-able is staged, not run).
- No corpus rclone sync (recommended, not executed).
- No yiclaw demo (Drucker's 30-day target requires Maurice's commitment to the constraint).
- No commit of this report (will commit alongside the .html companion per 2份制 rule).

---

Maurice | maurice_wen@proton.me
