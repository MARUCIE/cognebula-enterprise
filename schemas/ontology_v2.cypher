-- CogNebula Finance/Tax Knowledge Graph Ontology v3.1
-- Designed by: Gemini 2.5 Pro + 4-advisor council review (Hickey/Meadows/Munger/Musk)
-- Date: 2026-03-20
-- Migration: 70 tables -> 17 node tables + 36 edge tables
-- Target: KuzuDB 0.11.3+
-- Strategy: Dual-track incremental (old tables read-only, new tables receive all writes)

-- ============================================================
-- PART 1: NODE TABLES (15)
-- ============================================================

-- N1. Legal Document (法律法规文件)
-- Merges: LawOrRegulation, AccountingStandard
CREATE NODE TABLE IF NOT EXISTS LegalDocument (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,                        -- 法律|行政法规|部门规章|规范性文件|司法解释|会计准则
    level INT64,                        -- 层级 (1:法律, 2:行政法规, 3:部门规章, 4:规范性文件)
    issuingBodyId STRING,
    issueDate STRING,
    effectiveDate STRING,
    expiryDate STRING,
    status STRING                       -- 现行有效|已失效|部分失效|尚未生效
);

-- N2. Legal Clause (法规条款)
-- Merges: RegulationClause, DocumentSection
CREATE NODE TABLE IF NOT EXISTS LegalClause (
    id STRING PRIMARY KEY,
    documentId STRING,
    clauseNumber STRING,
    title STRING,
    content STRING,
    keywords STRING
);

-- N3. Tax Rate (税率事实) -- SPLIT from TaxRule per Hickey review
-- Merges: TaxCodeRegionRate, TaxRateMapping, TaxRateDetail, TaxRateSchedule
-- Lifecycle: annual adjustment, lookup queries
CREATE NODE TABLE IF NOT EXISTS TaxRate (
    id STRING PRIMARY KEY,
    name STRING,
    taxTypeId STRING,
    value DOUBLE,
    valueExpression STRING,             -- for progressive/tiered rates
    calculationBasis STRING,
    effectiveDate STRING,
    expiryDate STRING
);

-- N4. Compliance Rule (合规约束) -- SPLIT from TaxRule per Hickey review
-- Merges: ComplianceRule, TaxPolicy
-- Lifecycle: changes with regulation amendments, checklist queries
CREATE NODE TABLE IF NOT EXISTS ComplianceRule (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING,
    category STRING,                    -- 申报义务|代扣代缴|发票管理|记录保存|资质要求
    consequence STRING,                 -- violation consequence
    effectiveDate STRING,
    expiryDate STRING
);

-- N5. Risk Indicator (风险信号) -- SPLIT from TaxRule per Hickey review
-- Merges: TaxCreditIndicator, TaxWarningIndicator, RiskIndicator
-- Lifecycle: evolves with audit practices, scoring queries
CREATE NODE TABLE IF NOT EXISTS RiskIndicator (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING,
    indicatorType STRING,               -- 信用指标|预警指标|风险指标
    threshold DOUBLE,
    severity STRING                     -- 高|中|低
);

-- N6. Tax Incentive (税收优惠) -- kept separate per Hickey approval
CREATE NODE TABLE IF NOT EXISTS TaxIncentive (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,                        -- 减免税额|即征即退|加计扣除|税额抵免|先征后返
    description STRING,
    effectiveDate STRING,
    expiryDate STRING
);

-- N7. Knowledge Unit (知识单元)
-- Merges: CPAKnowledge, FAQEntry, MindmapNode, SpreadsheetEntry, IndustryKnowledge
CREATE NODE TABLE IF NOT EXISTS KnowledgeUnit (
    id STRING PRIMARY KEY,
    type STRING,                        -- FAQ|案例解析|考点|风险提示|操作指南|思维导图
    title STRING,
    content STRING,
    source STRING
);

-- N8. Classification (分类体系)
-- Merges: HSCode, TaxClassificationCode, TaxCodeDetail, TaxCodeIndustryMap,
--         Industry, FTIndustry, IndustryRiskProfile, IndustryBookkeeping
CREATE NODE TABLE IF NOT EXISTS Classification (
    code STRING PRIMARY KEY,
    name STRING,
    system STRING                       -- 国民经济行业分类|HS编码|税收分类编码|企业类型
);

-- N9. Accounting Subject (会计科目)
-- Merges: ChartOfAccount, ChartOfAccountDetail, AccountEntry, AccountingEntry, AccountRuleMapping
CREATE NODE TABLE IF NOT EXISTS AccountingSubject (
    code STRING PRIMARY KEY,
    name STRING,
    category STRING,                    -- 资产|负债|权益|成本|损益
    balanceDirection STRING             -- 借|贷
);

-- N10. Tax Type (税种) -- unchanged, 19 entries
CREATE NODE TABLE IF NOT EXISTS TaxType (
    id STRING PRIMARY KEY,
    name STRING
);

-- N11. Tax Entity (纳税主体)
-- Merges: EnterpriseType, TaxpayerStatus, EntityTypeProfile
CREATE NODE TABLE IF NOT EXISTS TaxEntity (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,                        -- 企业|个人|个体工商户
    taxpayerStatus STRING               -- 一般纳税人|小规模纳税人|自然人
);

-- N12. Region (地区)
CREATE NODE TABLE IF NOT EXISTS Region (
    code STRING PRIMARY KEY,
    name STRING,
    level INT64                         -- 1:省 2:市 3:区县
);

-- N13. Filing Form (申报表)
-- Merges: FilingForm, FormTemplate, TaxCalendar
CREATE NODE TABLE IF NOT EXISTS FilingForm (
    id STRING PRIMARY KEY,
    name STRING,
    reportCycle STRING,                 -- 月|季|年
    deadlineDay INT64
);

-- N14. Business Activity (经济业务)
-- Merges: TaxRiskScenario + new
CREATE NODE TABLE IF NOT EXISTS BusinessActivity (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING
);

-- N15. Issuing Body (发布机构)
CREATE NODE TABLE IF NOT EXISTS IssuingBody (
    id STRING PRIMARY KEY,
    name STRING,
    shortName STRING
);


-- ============================================================
-- PART 2: EDGE TABLES (36)
-- v3.1: EXPLAINS split into 6 precise types (Hickey/Meadows P0)
-- v3.0: +17 structural/inter-tax/compliance edges
-- ============================================================

-- --- Structural (2) ---
CREATE REL TABLE IF NOT EXISTS PART_OF (FROM LegalClause TO LegalDocument);
CREATE REL TABLE IF NOT EXISTS CHILD_OF (FROM Classification TO Classification);

-- --- Legal Evolution (3) ---
CREATE REL TABLE IF NOT EXISTS SUPERSEDES (FROM LegalDocument TO LegalDocument);
CREATE REL TABLE IF NOT EXISTS AMENDS (FROM LegalDocument TO LegalDocument);
CREATE REL TABLE IF NOT EXISTS CONFLICTS_WITH (FROM LegalClause TO LegalClause);

-- --- Authority & Citation (4) ---
CREATE REL TABLE IF NOT EXISTS REFERENCES_CLAUSE (FROM LegalClause TO LegalClause);
CREATE REL TABLE IF NOT EXISTS BASED_ON (FROM TaxRate TO LegalClause);
CREATE REL TABLE IF NOT EXISTS INCENTIVE_BASED_ON (FROM TaxIncentive TO LegalClause);
CREATE REL TABLE IF NOT EXISTS ISSUED_BY (FROM LegalDocument TO IssuingBody);

-- --- Applicability & Conditions (4) ---
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_TAX (FROM TaxRate TO TaxType);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_ENTITY (FROM TaxRate TO TaxEntity);
CREATE REL TABLE IF NOT EXISTS APPLIES_IN_REGION (FROM TaxRate TO Region);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_CLASS (FROM TaxRate TO Classification);

-- --- Inter-Tax (3) [v3.0] ---
CREATE REL TABLE IF NOT EXISTS CALCULATED_FROM (FROM TaxType TO TaxType);     -- e.g. 城建税 calculated from VAT
CREATE REL TABLE IF NOT EXISTS SURCHARGE_OF (FROM TaxType TO TaxType);        -- e.g. 教育费附加 surcharge of VAT
CREATE REL TABLE IF NOT EXISTS RELATED_TAX (FROM TaxType TO TaxType);         -- general tax relationship

-- --- Tax-Bridge (8) [v3.0] -- break TaxType isolation ---
CREATE REL TABLE IF NOT EXISTS TRIGGERS_TAX (FROM BusinessActivity TO TaxType);
CREATE REL TABLE IF NOT EXISTS INCENTIVE_FOR_TAX (FROM TaxIncentiveV2 TO TaxType);
CREATE REL TABLE IF NOT EXISTS RULE_FOR_TAX (FROM ComplianceRuleV2 TO TaxType);
CREATE REL TABLE IF NOT EXISTS FILING_FOR_TAX (FROM FilingFormV2 TO TaxType);
CREATE REL TABLE IF NOT EXISTS MAPS_TO_ACCOUNT (FROM TaxType TO AccountingSubject);
CREATE REL TABLE IF NOT EXISTS RISK_FOR_TAX (FROM RiskIndicatorV2 TO TaxType);
CREATE REL TABLE IF NOT EXISTS KU_ABOUT_TAX (FROM KnowledgeUnit TO TaxType);
CREATE REL TABLE IF NOT EXISTS AUDIT_FOR_TAX (FROM AuditTrigger TO TaxType);

-- --- Filing & Compliance (2) ---
CREATE REL TABLE IF NOT EXISTS REQUIRES_FILING (FROM BusinessActivity TO FilingForm);
CREATE REL TABLE IF NOT EXISTS GOVERNED_BY (FROM BusinessActivity TO ComplianceRule);

-- --- Accounting (2) [v3.0] ---
CREATE REL TABLE IF NOT EXISTS DEBITS_V2 (FROM TaxType TO AccountingSubject);
CREATE REL TABLE IF NOT EXISTS CREDITS_V2 (FROM TaxType TO AccountingSubject);

-- --- Compliance (2) [v3.0] ---
CREATE REL TABLE IF NOT EXISTS PENALIZED_BY (FROM ComplianceRuleV2 TO Penalty);
CREATE REL TABLE IF NOT EXISTS TRIGGERED_BY (FROM AuditTrigger TO RiskIndicatorV2);

-- --- Knowledge (6) [v3.1 EXPLAINS split] ---
-- Replaces monolithic EXPLAINS (475K edges, 55% of total)
-- Classification: keyword-based on KnowledgeUnit type + title + content
CREATE REL TABLE IF NOT EXISTS INTERPRETS (FROM KnowledgeUnit TO LegalClause);            -- default: legal interpretation (82%)
CREATE REL TABLE IF NOT EXISTS EXEMPLIFIED_BY (FROM KnowledgeUnit TO LegalClause);        -- case studies, examples (1%)
CREATE REL TABLE IF NOT EXISTS EXPLAINS_RATE (FROM KnowledgeUnit TO LegalClause);         -- tax rate explanations (4%)
CREATE REL TABLE IF NOT EXISTS WARNS_ABOUT (FROM KnowledgeUnit TO LegalClause);           -- risk warnings, violations (5%)
CREATE REL TABLE IF NOT EXISTS DESCRIBES_INCENTIVE (FROM KnowledgeUnit TO LegalClause);   -- incentive descriptions (4%)
CREATE REL TABLE IF NOT EXISTS GUIDES_FILING (FROM KnowledgeUnit TO LegalClause);         -- filing guidance (4%);
