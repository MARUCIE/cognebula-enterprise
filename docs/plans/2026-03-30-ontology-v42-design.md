# CogNebula Ontology v4.2 Design — Swarm Consensus Report

> 2 rounds, 11 experts, 360-degree analysis. 2026-03-30.

## Executive Summary

**Verdict: v4.2 surgical increment (NOT v5.0 restructure)**

Two rounds of swarm analysis (6 strategic advisors + 5 domain experts) reached consensus:
the v4.1 ontology's 4-layer framework is sound, but has **critical concept gaps** (not hierarchy gaps).
The fix is adding 7-9 missing node types that represent entirely new knowledge dimensions,
plus rebuilding 2 garbage-data types from scratch.

---

## Round 1: Strategic Consensus (6/6 unanimous)

| Advisor | Verdict | Key Insight |
|---------|---------|-------------|
| Hickey | RETHINK | Hierarchy is edge patterns, not type inheritance. clauseLevel + PARENT_CLAUSE already exists |
| Drucker | RETHINK | Customer needs "task checklists" not "ontology layers". Validate with real queries first |
| Munger | CAUTION | "Surgical increment" — only touch types with real data. Worst-case = delete one column |
| Brooks | SIMPLIFY | Data garbage, empty content, missing hierarchy are 3 different problems. Don't solve with 1 approach |
| Meadows | INTERVENE | System purpose misaligned: "100M nodes KG" vs "monthly compliance knowledge base" |
| Ontology Research | GO incremental | FIBO recommends 5-6 depth. Restructure only when >30% types need reclassification |

**Strategic rules:**
- NO full restructure (second-system effect)
- NO hierarchy subtypes (LegalDocumentChapter etc.)
- Hierarchy via existing edges (clauseLevel + PARENT_CLAUSE + CHILD_OF)
- Data quality before structure expansion

---

## Round 2: Domain Expert Findings

### Tax Law Expert — 8 Elements Coverage Audit

Chinese tax law has 8 core elements per tax type. Current coverage:

| Element | Chinese | Coverage | Gap |
|---------|---------|----------|-----|
| Taxpayer | 纳税人 | Partial | Missing WithholdingAgent (扣缴义务人) |
| **Tax Item** | **征税范围/税目** | **MISSING** | Consumption tax 15 items, stamp tax 17 items not modeled |
| Tax Rate | 税率 | Good | — |
| **Tax Basis** | **计税依据** | **MISSING** | Ad valorem / specific / compound cannot be expressed |
| **Liability Trigger** | **纳税义务发生时间** | **MISSING** | VAT has 9 different trigger rules |
| Tax Location | 纳税地点 | Weak | Registration vs operation vs property location rules missing |
| Tax Incentive | 税收优惠 | Good | — |
| Administration | 征收管理 | Partial | — |

**Recommended**: 38 node types + ~48 edge types. 4-5 hop query depth is the practical limit.
Current ontology covers ~70-75% of Chinese tax knowledge structure.

### Accounting Expert — Business→Statement Chain

The core bookkeeping chain has 2 critical breaks:

```
BusinessActivity → [BREAK] → Journal Entry → Account Summary → [BREAK] → Financial Statement → Filing Form
                JournalEntryTemplate                        FinancialStatementItem
                (completely missing)                         (completely missing)
```

**P0 new types**: JournalEntryTemplate (200-300 entries), FinancialStatementItem (150-200 items)
**P0 new edges**: HAS_ENTRY_TEMPLATE, ENTRY_DEBITS, ENTRY_CREDITS, POPULATES
**Data expansion**: AccountingSubject 223→500-600 (add 2nd/3rd level detail accounts)

Monthly close 10-step process: steps 2/4/5/6/9 depend on missing knowledge nodes.

### Practice Expert — Knowledge Encyclopedia vs Operation Manual

> "Current ontology is a decent 'tax knowledge encyclopedia' but far from a 'bookkeeping operation manual'."

VAT complete chain coverage: **40-50%**. Skeleton exists but lacks:
- Calculation logic (how to compute output/input VAT)
- Filing form field-level logic (which row = which formula)
- Batch processing: missing ENTITY_HAS_TAX_OBLIGATION edge (cannot filter "which clients need to file property tax this month")

**P0 new types**: TaxCalculationRule, FilingFormField
**P1 new types**: ResponseStrategy (risk response), PolicyChange (policy impact tracking)

### Tax Risk Expert — Complete Rebuild Plan

RiskIndicator (463) and AuditTrigger (463) are **100% garbage** (textbook imports).
Must TRUNCATE and rebuild with structured expert knowledge.

Golden Tax IV risk system has 6 modules:
1. Tax burden indicators (20-25)
2. Invoice indicators (25-30)
3. Financial ratio indicators (30-35)
4. Filing behavior indicators (15-20)
5. Banking/funds indicators (20-25) — GT4 new
6. Cross-system comparison indicators (15-20)

**Rebuild target**: 150-200 RiskIndicator + 80-120 AuditTrigger (replacing 926 garbage nodes)
**New types**: AntiMoneyLaunderingRule (40-60), TransferPricingMethod (25-30), CriminalThreshold (15-20)
**IndustryBenchmark**: expand from 45 → 500-600 (30 industries × 6 metrics × 3 regions)

---

## Consolidated v4.2 Schema Change

### New Node Types (+9)

| Priority | Type | Chinese | Est. Data | Source |
|----------|------|---------|-----------|--------|
| **P0** | `JournalEntryTemplate` | 会计分录模板 | 200-300 | Accounting Expert |
| **P0** | `FinancialStatementItem` | 报表项目 | 150-200 | Accounting Expert |
| **P0** | `TaxCalculationRule` | 税额计算规则 | 100-150 | Practice Expert |
| **P0** | `FilingFormField` | 申报表栏次 | 300-500 | Practice Expert |
| **P1** | `TaxItem` | 税目 | 80-100 | Tax Law Expert |
| **P1** | `TaxBasis` | 计税依据 | 30-50 | Tax Law Expert |
| **P1** | `TaxLiabilityTrigger` | 纳税义务发生时间 | 50-80 | Tax Law Expert |
| **P2** | `ResponseStrategy` | 预警应对策略 | 50-80 | Practice + Risk |
| **P2** | `PolicyChange` | 政策变动事件 | 20-50 | Practice Expert |

### New Edge Types (+15)

| Priority | Edge | From → To | Purpose |
|----------|------|-----------|---------|
| **P0** | `HAS_ENTRY_TEMPLATE` | BusinessActivity → JournalEntryTemplate | Business→journal |
| **P0** | `ENTRY_DEBITS` | JournalEntryTemplate → AccountingSubject | Debit account |
| **P0** | `ENTRY_CREDITS` | JournalEntryTemplate → AccountingSubject | Credit account |
| **P0** | `POPULATES` | AccountingSubject → FinancialStatementItem | Account→statement |
| **P0** | `FIELD_OF` | FilingFormField → FilingForm | Field belongs to form |
| **P0** | `DERIVES_FROM` | FilingFormField → FilingFormField | Form cross-reference |
| **P0** | `CALCULATION_FOR_TAX` | TaxCalculationRule → TaxType | Calc rule for tax |
| **P1** | `HAS_ITEM` | TaxType → TaxItem | Tax type has items |
| **P1** | `COMPUTED_BY` | TaxItem → TaxBasis | Item uses basis |
| **P1** | `LIABILITY_TRIGGERED_BY` | TaxType → TaxLiabilityTrigger | Liability trigger |
| **P1** | `INDICATES_RISK` | RiskIndicator → AuditTrigger | Indicator→trigger |
| **P1** | `PENALIZED_FOR` | Penalty → BusinessActivity | Violation→penalty |
| **P1** | `ESCALATES_TO` | Penalty → Penalty | Admin→criminal ladder |
| **P2** | `RISK_RESPONSE` | RiskIndicator → ResponseStrategy | Alert response |
| **P2** | `POLICY_AFFECTS` | PolicyChange → TaxIncentive | Policy impact |

### Rebuild Types (2)

| Type | Current | Target | Action |
|------|---------|--------|--------|
| `RiskIndicator` | 463 garbage | 150-200 structured | TRUNCATE + rebuild with 6-module system |
| `AuditTrigger` | 463 garbage | 80-120 structured | TRUNCATE + rebuild with 3-level trigger system |

### Data Expansion (existing types)

| Type | Current | Target | What to add |
|------|---------|--------|-------------|
| AccountingSubject | 223 | 500-600 | 2nd/3rd level detail accounts |
| TaxAccountingGap | 50 | 80-100 | Cover all A105000 line items |
| IndustryBenchmark | 45 | 500-600 | 30 industries × 6 metrics × 3 regions |
| ComplianceRule | 84 | 200+ | Anti-money laundering, transfer pricing |
| Penalty | 127 | 200+ | Criminal liability + collateral consequences |
| InvoiceRule | 40 | 55 | Add deduction, e-invoice transition rules |

---

## Schema Size Summary

| Metric | v4.1 (current) | v4.2 (proposed) | Change |
|--------|----------------|-----------------|--------|
| Node types | 21 | 30 | +9 |
| Edge types | 52 | 67 | +15 |
| Quality nodes | ~50K (of 540K) | ~55K + 1500 new | Focus on density |
| Garbage nodes | 926 (RI+AT) | 0 | TRUNCATED |
| Rebuilt nodes | — | 230-320 (RI+AT) | Expert-curated |

**Conceptual integrity check (Brooks)**: 30 node types is within the "one mind can hold it" boundary.
53 types was the previous v3.1 count — that was too many. 30 is the sweet spot.

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- P0 types: JournalEntryTemplate, FinancialStatementItem, TaxCalculationRule, FilingFormField
- P0 edges: 7 new edge tables
- TRUNCATE RiskIndicator + AuditTrigger garbage data
- AccountingSubject expansion to 500+

### Phase 2: Tax Law Completeness (Week 3-4)
- P1 types: TaxItem, TaxBasis, TaxLiabilityTrigger
- P1 edges: HAS_ITEM, COMPUTED_BY, LIABILITY_TRIGGERED_BY
- RiskIndicator rebuild (150-200 structured entries)
- AuditTrigger rebuild (80-120 structured entries)
- IndustryBenchmark expansion to 500+

### Phase 3: Operations & Risk (Week 5-6)
- P2 types: ResponseStrategy, PolicyChange
- ComplianceRule expansion (anti-money laundering, transfer pricing)
- Penalty expansion (criminal + collateral)
- InvoiceRule supplementation (+15 rules)

### Phase 4: Validation
- 10 real business query test (Hickey/Drucker consensus)
- Monthly close 10-step chain verification
- VAT complete chain end-to-end test
- Constellation visualization update

---

## What We Are NOT Doing (Anti-Requirements)

1. NOT adding hierarchy subtypes (LegalDocumentChapter, LegalDocumentSection, etc.)
2. NOT restructuring the 4-layer framework
3. NOT migrating 540K existing nodes
4. NOT increasing ontology depth beyond 4-5 hops
5. NOT adding >30 node types (Brooks: conceptual integrity limit)
6. NOT chasing "1M nodes" as a KPI (Meadows: false stock metric)

---

## Expert Sources

Round 1: Hickey (simplicity), Drucker (business value), Munger (risk/inversion),
Brooks (complexity/schedule), Meadows (system dynamics), Ontology Research (FIBO/academic)

Round 2: Tax Law Structure Expert, Accounting Standards Expert (CAS),
Tax Compliance Practice Expert (10yr bookkeeping), KG Ontology Design Researcher,
Tax Risk & Audit Expert (tax bureau perspective)

---

Maurice | maurice_wen@proton.me
