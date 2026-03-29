# CogNebula Ontology v4.0 Proposal

> Based on: FIBO, XBRL, FinRegOnt, Chinese Tax KG Research, CPA/CTA frameworks
> References: ontology_v2.cypher (v3.1), migration_mapping.json, 4-advisor council review

## 1. v3.1 vs v4.0 Change Summary

| Dimension | v3.1 | v4.0 | Rationale |
|-----------|------|------|-----------|
| Node types | 15 | **18** (+3) | Add Penalty, AuditTrigger (already in KG), TaxAccountingGap (new) |
| Edge types | 36 | **40** (+4) | Add temporal + bridge edges |
| Naming | Mixed (V2 suffix) | **Unified** (no suffix) | Single convention |
| Temporal | Attribute-only | **Edge properties** | Enable "as-of" queries |
| 税会差异 | Not modeled | **First-class node** | Critical for automation |
| Evidence | Not modeled | **Node properties** | Audit trail |

## 2. Node Types (18)

### KEPT FROM v3.1 (12, unchanged schema)

| # | Node | Chinese | Merges | Count |
|---|------|---------|--------|-------|
| N1 | LegalDocument | 法律法规文件 | LawOrRegulation + AccountingStandard | ~94K |
| N2 | LegalClause | 法规条款 | RegulationClause + DocumentSection | ~155K |
| N3 | TaxRate | 税率事实 | TaxRateMapping + TaxRateDetail + TaxRateSchedule | ~9K |
| N7 | KnowledgeUnit | 知识单元 | CPAKnowledge + FAQEntry + MindmapNode + SpreadsheetEntry | ~190K |
| N8 | Classification | 分类体系 | HSCode + TaxClassificationCode + Industry + ... | ~61K |
| N9 | AccountingSubject | 会计科目 | ChartOfAccount + AccountingEntry + ... | ~1K |
| N10 | TaxType | 税种 | (unchanged, 19 entries) | 19 |
| N11 | TaxEntity | 纳税主体 | EnterpriseType + TaxpayerStatus | ~34 |
| N12 | Region | 地区 | Region + RegionalTaxPolicy | ~651 |
| N14 | BusinessActivity | 经济业务 | BusinessActivity + TaxRiskScenario | ~384 |
| N15 | IssuingBody | 发布机构 | (unchanged) | ~398 |
| N13 | FilingForm | 申报表 | FilingFormV2 + FormTemplate + TaxCalendar | ~242 |

### RENAMED FROM v3.1 (3, drop V2 suffix)

| # | v3.1 Name | v4.0 Name | Chinese | Why |
|---|-----------|-----------|---------|-----|
| N4 | ComplianceRuleV2 | **ComplianceRule** | 合规规则 | Drop V2 suffix, unified naming |
| N5 | RiskIndicatorV2 | **RiskIndicator** | 风险指标 | Drop V2 suffix |
| N6 | TaxIncentiveV2 | **TaxIncentive** | 税收优惠 | Drop V2 suffix, merge with old TaxIncentive |

### NEW IN v4.0 (3)

| # | Node | Chinese | Schema | Rationale |
|---|------|---------|--------|-----------|
| N16 | **Penalty** | 处罚规定 | `id PK, name, description, legalBasis, minAmount, maxAmount` | Already 127 nodes in KG; referenced by PENALIZED_BY edge; missing from v3.1 DDL |
| N17 | **AuditTrigger** | 审计触发 | `id PK, name, description, triggerCondition, threshold, frequency` | Already 463 nodes in KG; referenced by TRIGGERED_BY and AUDIT_FOR_TAX edges |
| N18 | **TaxAccountingGap** | 税会差异 | `id PK, name, accountingTreatment, taxTreatment, gapType, impact, example` | **Critical gap** per FIBO/FinRegOnt research. Links AccountingSubject to TaxType with explicit difference description. `gapType`: permanent/timing/method |

### NOT ADDED (considered but deferred)

| Proposal | Reason for Deferral |
|----------|-------------------|
| RegulationHierarchy (5-level node) | Use LegalDocument.level attribute instead (simpler, already works) |
| Evidence/Provenance (node) | Add as properties on existing nodes, not separate node type (avoid node explosion) |
| RevisionChain (node) | Model as SUPERSEDES/AMENDS edges with date properties (already in v3.1) |
| TaxTreatment (node) | Absorbed into TaxAccountingGap (single node covers the bridge) |

## 3. Edge Types (40)

### KEPT FROM v3.1 (36)

All 36 edge types from v3.1 retained. Key corrections:

```cypher
-- Fix: Use base names (no V2 suffix)
CREATE REL TABLE INCENTIVE_FOR_TAX (FROM TaxIncentive TO TaxType);   -- was TaxIncentiveV2
CREATE REL TABLE RULE_FOR_TAX (FROM ComplianceRule TO TaxType);       -- was ComplianceRuleV2
CREATE REL TABLE FILING_FOR_TAX (FROM FilingForm TO TaxType);         -- was FilingFormV2
CREATE REL TABLE RISK_FOR_TAX (FROM RiskIndicator TO TaxType);        -- was RiskIndicatorV2
CREATE REL TABLE PENALIZED_BY (FROM ComplianceRule TO Penalty);       -- was ComplianceRuleV2
CREATE REL TABLE TRIGGERED_BY (FROM AuditTrigger TO RiskIndicator);   -- was RiskIndicatorV2
```

### NEW IN v4.0 (4)

| Edge | From | To | Purpose |
|------|------|----|---------|
| **HAS_GAP** | AccountingSubject | TaxAccountingGap | Links accounting item to its tax-accounting difference |
| **GAP_FOR_TAX** | TaxAccountingGap | TaxType | Which tax type the gap affects |
| **OVERRIDES_IN** | Region | ComplianceRule | Regional override of national rule |
| **AUDIT_TRIGGERS** | AuditTrigger | ComplianceRule | Which compliance rules an audit trigger monitors |

## 4. Migration Plan (v3.1 → v4.0)

### Phase 0: Schema Preparation (no data change)
1. Add 3 new node tables (Penalty, AuditTrigger, TaxAccountingGap)
2. Add 4 new edge tables
3. Rename V2 tables: `ComplianceRuleV2→ComplianceRule`, etc.
   - KuzuDB doesn't support RENAME TABLE; use CREATE + MIGRATE + DROP

### Phase 1: Merge Legacy → Ontology (big data move)
Priority by data volume:

| Target | Sources | ~Nodes | Method |
|--------|---------|--------|--------|
| KnowledgeUnit | CPAKnowledge, FAQEntry, MindmapNode, SpreadsheetEntry, IndustryKnowledge | +37K | admin/migrate-table API |
| Classification | HSCode, TaxClassificationCode, TaxCodeDetail, TaxCodeIndustryMap, Industry, FTIndustry, IndustryRiskProfile, IndustryBookkeeping | +33K | admin/migrate-table API |
| LegalDocument | LawOrRegulation, AccountingStandard | +39K | admin/migrate-table API |
| LegalClause | RegulationClause, DocumentSection | +72K | admin/migrate-table API |
| AccountingSubject | ChartOfAccount, ChartOfAccountDetail, AccountEntry, AccountingEntry, AccountRuleMapping | +867 | admin/migrate-table API |
| Region | RegionalTaxPolicy | +620 | admin/migrate-table API |
| BusinessActivity | TaxRiskScenario | +180 | admin/migrate-table API |
| TaxEntity | EnterpriseType, TaxpayerStatus, EntityTypeProfile | +17 | admin/migrate-table API |
| FilingForm | FormTemplate, TaxCalendar | +121 | admin/migrate-table API |
| TaxRate | TaxRateMapping, TaxRateDetail, TaxRateSchedule | +140 | admin/migrate-table API |
| ComplianceRule | ComplianceRuleV2, TaxPolicy | +104 | admin/migrate-table API |
| RiskIndicator | RiskIndicatorV2, TaxCreditIndicator, TaxWarningIndicator | +548 | admin/migrate-table API |
| TaxIncentive | TaxIncentiveV2 | +109 | admin/migrate-table API |

### Phase 2: Seed New Data
1. TaxAccountingGap: Seed 50 common 税会差异 from CPA/CTA exam content
2. Verify Penalty + AuditTrigger data integrity (already in KG)

### Phase 3: Edge Migration
1. Re-point edges from old source tables to new target tables
2. Create new edge types (HAS_GAP, GAP_FOR_TAX, OVERRIDES_IN, AUDIT_TRIGGERS)
3. Verify edge integrity (no dangling references)

### Phase 4: Cleanup
1. Verify all data migrated (count comparison)
2. Drop legacy tables (70 tables → 0)
3. Update frontend to use only 18 ontology tables
4. Update kg-api-server.py quality audit to only check v4 tables

## 5. Frontend Impact

After migration, the frontend should ONLY show these 18 node types:

```typescript
const ONTOLOGY_TYPES = {
  "L1 法规层": ["LegalDocument", "LegalClause", "IssuingBody"],
  "L2 业务层": ["TaxRate", "TaxType", "AccountingSubject", "Classification", "TaxEntity", "Region", "FilingForm", "BusinessActivity"],
  "L3 合规层": ["ComplianceRule", "RiskIndicator", "TaxIncentive", "Penalty", "AuditTrigger", "TaxAccountingGap"],
  "知识层":    ["KnowledgeUnit"],
};
```

## 6. Decision Log

| Decision | Option Chosen | Alternatives Considered | Why |
|----------|--------------|------------------------|-----|
| Add TaxAccountingGap | YES | Embed in edge properties | First-class node enables RAG + search + versioning |
| Keep Penalty/AuditTrigger | YES | Merge into ComplianceRule | Already 590 nodes; separate lifecycle |
| NOT add RegulationHierarchy | Use level attribute | 5 separate node types | Simpler; KuzuDB property query sufficient |
| NOT add Evidence node | Add properties | Separate node type | Avoid node explosion; properties work for MVP |
| Unified naming (no V2) | YES | Keep V2 suffix | Consistency; v2/v3/v4 version is ontology version, not node name |
| 18 types (not 22+) | YES | Add more specialized types | Minimal complexity; can split later if needed |

---

Maurice | maurice_wen@proton.me
