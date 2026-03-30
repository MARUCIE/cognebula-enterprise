# CogNebula Ontology v4.2 Final Design

> 3 rounds, 17 experts, 360-degree swarm consensus. 2026-03-30.

## Decision

**v4.2 surgical increment on v4.1 framework. +14 node types, +20 edge types, 2 type rebuilds.**

Total: 35 node types, ~72 edge types. Within Brooks' conceptual integrity limit (37).

---

## New Node Types (+14)

### P0 — Core chain completion (Week 1-2)

| # | Type | Chinese | Est. Data | Rationale | Sources |
|---|------|---------|-----------|-----------|---------|
| 1 | `JournalEntryTemplate` | 会计分录模板 | 200-300 | Business→journal chain break | Accounting, Practice, CPA |
| 2 | `FinancialStatementItem` | 报表项目 | 150-200 | Journal→statement chain break | Accounting, Financial |
| 3 | `TaxCalculationRule` | 税额计算规则 | 100-150 | "How to calculate" missing entirely | Practice, Tax Law, Planning |
| 4 | `FilingFormField` | 申报表栏次 | 300-500 | "How to fill the form" missing | Practice |
| 5 | `FinancialIndicator` | 财务分析指标 | 80-120 | DuPont decomposition, tax burden analysis | Financial, CPA (4/4 consensus) |
| 6 | `AccountingStandard` | 会计准则 | 60-80 | CAS 1-42 must not mix with LegalDocument | CPA (structural separation) |
| 7 | `TaxTreaty` | 税收协定 | 112 | Cannot answer "withholding rate to Singapore?" | Tax Law, Lifecycle, Cross-border (3/3) |

### P1 — Tax law completeness (Week 3-4)

| # | Type | Chinese | Est. Data | Rationale | Sources |
|---|------|---------|-----------|-----------|---------|
| 8 | `TaxItem` | 税目 | 80-100 | 8-element gap: consumption tax 15 items, stamp tax 17 | Tax Law |
| 9 | `TaxBasis` | 计税依据 | 30-50 | 8-element gap: ad valorem/specific/compound | Tax Law |
| 10 | `TaxLiabilityTrigger` | 纳税义务发生时间 | 50-80 | 8-element gap: VAT has 9 trigger rules | Tax Law, Payroll |
| 11 | `DeductionRule` | 扣除限额规则 | 60-80 | CIT/PIT deduction standards (20+ items) | CPA |
| 12 | `TaxMilestoneEvent` | 生命周期事件 | 30-50 | Establishment→operation→M&A→liquidation chain | Lifecycle |

### P2 — Operations & risk (Week 5-6)

| # | Type | Chinese | Est. Data | Rationale | Sources |
|---|------|---------|-----------|-----------|---------|
| 13 | `ResponseStrategy` | 预警应对策略 | 50-80 | "Got an alert, now what?" chain missing | Practice, Risk |
| 14 | `PolicyChange` | 政策变动事件 | 20-50 | "Policy changed, what's affected?" chain | Practice |

---

## New Edge Types (+20)

### P0 edges

| Edge | From → To | Purpose | Source |
|------|-----------|---------|--------|
| `HAS_ENTRY_TEMPLATE` | BusinessActivity → JournalEntryTemplate | Business→journal | Accounting |
| `ENTRY_DEBITS` | JournalEntryTemplate → AccountingSubject | Debit side | Accounting |
| `ENTRY_CREDITS` | JournalEntryTemplate → AccountingSubject | Credit side | Accounting |
| `POPULATES` | AccountingSubject → FinancialStatementItem | Account→statement | Accounting, Financial |
| `FIELD_OF` | FilingFormField → FilingForm | Field belongs to form | Practice |
| `DERIVES_FROM` | FilingFormField → FilingFormField | Cross-form reference | Practice |
| `CALCULATION_FOR_TAX` | TaxCalculationRule → TaxType | Calc rule for tax | Practice |
| `DECOMPOSES_INTO` | FinancialIndicator → FinancialIndicator | DuPont decomposition tree | Financial (P0) |
| `COMPUTED_FROM` | FinancialIndicator → FinancialStatementItem | Indicator data source | Financial |
| `HAS_BENCHMARK` | FinancialIndicator → IndustryBenchmark | Indicator baseline | Financial |
| `PARTY_TO` | Region → TaxTreaty | Treaty signatory | Cross-border |
| `OVERRIDES_RATE` | TaxTreaty → TaxRate | Treaty rate overrides domestic | Cross-border |

### P1 edges

| Edge | From → To | Purpose | Source |
|------|-----------|---------|--------|
| `HAS_ITEM` | TaxType → TaxItem | Tax type has items | Tax Law |
| `COMPUTED_BY` | TaxItem → TaxBasis | Item uses basis | Tax Law |
| `LIABILITY_TRIGGERED_BY` | TaxType → TaxLiabilityTrigger | Liability trigger | Tax Law |
| `INDICATES_RISK` | RiskIndicator → AuditTrigger | Indicator→trigger | Risk |
| `PENALIZED_FOR` | Penalty → BusinessActivity | Violation→penalty | Risk |
| `ESCALATES_TO` | Penalty → Penalty | Admin→criminal ladder | Risk |
| `SPLITS_INTO` | BusinessActivity → BusinessActivity | Mixed sale / separate ops | Planning |
| `DEDUCTS_FROM` | DeductionRule → TaxBasis | Deduction reduces tax base | CPA |

---

## Rebuild Types (2)

| Type | Current | Target | Action |
|------|---------|--------|--------|
| `RiskIndicator` | 463 garbage | 150-200 structured | TRUNCATE + 6-module rebuild |
| `AuditTrigger` | 463 garbage | 80-120 structured | TRUNCATE + 3-level rebuild |

---

## Data Expansion (existing types)

| Type | Current | Target | Priority |
|------|---------|--------|----------|
| AccountingSubject | 223 | 500-600 | P0 (add 2nd/3rd level) |
| TaxAccountingGap | 50 | 80-100 | P1 (cover A105000) |
| IndustryBenchmark | 45 | 500-600 | P1 (30 industries × 6 metrics × 3 regions) |
| ComplianceRule | 84 | 200+ | P1 (AML, transfer pricing) |
| Penalty | 127 | 200+ | P1 (criminal + collateral) |
| InvoiceRule | 40 | 55 | P2 (add deduction, e-invoice) |
| TaxIncentive | 109 | 120+ | P0 (add 7 PIT special deductions) |
| **STACKS_WITH/EXCLUDES edges** | **0** | **60-80** | **P0** (tax incentive stacking rules) |

---

## Schema Size Summary

| Metric | v4.1 | v4.2 | Change |
|--------|------|------|--------|
| Node types | 21 | **35** | +14 |
| Edge types | 52 | **~72** | +20 |
| Garbage nodes | 926 | 0 | TRUNCATED |
| Rebuilt nodes | — | 230-320 | Expert-curated |
| Quality data additions | — | ~3,000-5,000 | Seed + LLM enrichment |

---

## What We Are NOT Doing

1. NOT v5.0 full restructure (Brooks: second-system effect)
2. NOT hierarchy subtypes (LegalDocumentChapter etc.) — use clauseLevel + PARENT_CLAUSE edges
3. NOT TaxPlanningStrategy type (planning = graph path search + Agent reasoning)
4. NOT L5 International Tax Layer as full layer (TaxTreaty is P0, rest is P3 on-demand)
5. NOT migrating 540K existing nodes
6. NOT exceeding 37 node types (Brooks conceptual integrity limit)
7. NOT adding ProcessStep/Workflow types (P2+ deferred, use KnowledgeUnit.type="process_guide")
8. NOT chasing "1M nodes" KPI (Meadows: false stock metric)

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- DDL: CREATE 7 P0 node tables + 12 P0 edge tables
- Seed: JournalEntryTemplate top-100 entries, FinancialStatementItem 150+
- Seed: TaxCalculationRule VAT/CIT/PIT core formulas
- Seed: FilingFormField VAT main form + schedules
- Seed: FinancialIndicator 40 core metrics with DuPont tree
- Seed: AccountingStandard CAS 1-42
- Seed: TaxTreaty top-20 treaties (HK, SG, US, UK, JP, KR, DE, etc.)
- Data: AccountingSubject expand to 500+
- Data: TaxIncentive +7 PIT special deductions
- Data: STACKS_WITH/EXCLUDES 60-80 edges (deterministic rules)
- TRUNCATE: RiskIndicator + AuditTrigger garbage

### Phase 2: Tax Law + Risk (Week 3-4)
- DDL: CREATE 5 P1 node tables + 8 P1 edge tables
- Seed: TaxItem (consumption 15 + stamp 17 + VAT categories)
- Seed: TaxBasis (ad valorem, specific, compound per tax type)
- Seed: TaxLiabilityTrigger (VAT 9 rules, CIT, PIT)
- Seed: DeductionRule (CIT 20+ items, PIT deductions)
- Seed: TaxMilestoneEvent (establishment→operation→M&A→liquidation)
- Rebuild: RiskIndicator 150-200 (6-module Golden Tax IV system)
- Rebuild: AuditTrigger 80-120 (3-level trigger system)
- Data: IndustryBenchmark expand to 500+
- Data: ComplianceRule expand to 200+
- Data: SPLITS_INTO edges 30-50

### Phase 3: Operations (Week 5-6)
- DDL: CREATE 2 P2 node tables + remaining edges
- Seed: ResponseStrategy 50-80 (risk response procedures)
- Seed: PolicyChange (recent policy changes with impact mapping)
- Data: Penalty expand to 200+ (criminal + collateral)
- Data: InvoiceRule +15 (加计抵减, e-invoice transition)
- Content: LLM batch fullText enrichment for all types

### Phase 4: Validation
- 10 real business query test
- Monthly close 10-step chain verification
- VAT complete chain end-to-end test
- DuPont analysis decomposition tree test
- Constellation visualization update
- Skill playbook → ontology gap closure verification

---

## Swarm Expert Sources (3 rounds, 17 experts)

### Round 1: Strategic (6 experts)
Hickey (simplicity), Drucker (business value), Munger (risk/inversion),
Brooks (complexity/schedule), Meadows (system dynamics), Ontology Research (FIBO/academic)

### Round 2: Domain (5 experts)
Tax Law Structure, Accounting Standards (CAS), Tax Compliance Practice (10yr bookkeeping),
KG Ontology Design Researcher, Tax Risk & Audit (tax bureau perspective)

### Round 3: Business Deep-Dive (6 experts)
CPA 6-Subject Knowledge, Tax Planning Strategy, Enterprise Lifecycle Tax,
Financial Analysis & Management Accounting, Cross-Border International Tax,
Payroll & Social Insurance

---

Maurice | maurice_wen@proton.me
