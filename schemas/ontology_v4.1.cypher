-- CogNebula Finance/Tax Knowledge Graph Ontology v4.1
-- Upgraded from v4.0 based on 29-Skill Expert Team Review (5-agent swarm)
-- Date: 2026-03-29
-- Changes: 18 -> 21 node tables, 40 -> 52 edge tables
-- Key additions: SocialInsuranceRule, InvoiceRule, IndustryBenchmark
-- Key enhancements: 12 attribute additions, 7 new edges, 5 edge attribute additions

-- ============================================================
-- PART 1: NODE TABLES (21)
-- ============================================================

-- === L1 Legal Layer (3) ===

-- N1. Legal Document (法律法规文件)
-- Merges: LawOrRegulation, AccountingStandard
-- v4.1: +documentType, +standardNumber, +status attributes
CREATE NODE TABLE IF NOT EXISTS LegalDocument (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,                        -- 法律|行政法规|部门规章|规范性文件|司法解释|会计准则
    documentType STRING,                -- v4.1: tax_law|accounting_standard|audit_standard|admin_regulation|data_protection
    standardNumber STRING,              -- v4.1: CAS编号 (e.g. "CAS-14") 或审计准则编号
    level INT64,                        -- 层级 (1:法律, 2:行政法规, 3:部门规章, 4:规范性文件)
    issuingBodyId STRING,
    issueDate STRING,
    effectiveDate STRING,
    expiryDate STRING,
    status STRING,                      -- v4.1: 现行有效|已失效|部分失效|尚未生效|已修订
    latestVersionId STRING              -- v4.1: 最新版本ID快捷指针 (避免遍历SUPERSEDES链)
);

-- N2. Legal Clause (法规条款)
-- Merges: RegulationClause, DocumentSection
-- v4.1: +clauseLevel, +sortOrder, +PARENT_CLAUSE self-ref edge
CREATE NODE TABLE IF NOT EXISTS LegalClause (
    id STRING PRIMARY KEY,
    documentId STRING,
    clauseNumber STRING,
    clauseLevel STRING,                 -- v4.1: chapter|section|article|paragraph|item (章|节|条|款|项)
    sortOrder INT64,                    -- v4.1: 同层级排序
    title STRING,
    content STRING,
    keywords STRING
);

-- N15. Issuing Body (发布机构)
CREATE NODE TABLE IF NOT EXISTS IssuingBody (
    id STRING PRIMARY KEY,
    name STRING,
    shortName STRING
);

-- === L2 Business Layer (8) ===

-- N3. Tax Rate (税率事实)
-- v4.1: +taxMethod, +rateType attributes
CREATE NODE TABLE IF NOT EXISTS TaxRate (
    id STRING PRIMARY KEY,
    name STRING,
    taxTypeId STRING,
    value DOUBLE,
    valueExpression STRING,
    calculationBasis STRING,
    taxMethod STRING,                   -- v4.1: general|simplified|withholding|deemed (一般|简易|代扣|核定)
    rateType STRING,                    -- v4.1: proportional|fixed|progressive|rebate (比例|定额|累进|退税)
    effectiveDate STRING,
    expiryDate STRING
);

-- N10. Tax Type (税种) -- 19 entries
CREATE NODE TABLE IF NOT EXISTS TaxType (
    id STRING PRIMARY KEY,
    name STRING
);

-- N9. Accounting Subject (会计科目)
-- v4.1: +level, +parentCode, +isLeaf, +monetaryType, +standardSource
CREATE NODE TABLE IF NOT EXISTS AccountingSubject (
    code STRING PRIMARY KEY,
    name STRING,
    category STRING,                    -- 资产|负债|权益|成本|损益
    balanceDirection STRING,            -- 借|贷
    level INT64,                        -- v4.1: 科目级次 (1/2/3/4)
    parentCode STRING,                  -- v4.1: 父科目编码 (一级科目为null)
    isLeaf INT64,                       -- v4.1: 1=末级科目(可做分录), 0=汇总科目
    monetaryType STRING,                -- v4.1: monetary|non_monetary|mixed (货币性|非货币性|混合)
    standardSource STRING               -- v4.1: cas_full|cas_small (企业会计准则|小企业会计准则)
);

-- N8. Classification (分类体系)
-- v4.1: +notes for HS chapter annotations
CREATE NODE TABLE IF NOT EXISTS Classification (
    code STRING PRIMARY KEY,
    name STRING,
    system STRING,                      -- 国民经济行业分类|HS编码|税收分类编码|企业类型
    notes STRING                        -- v4.1: HS章注/品目注释/分类说明
);

-- N11. Tax Entity (纳税主体)
-- v4.1: +residencyStatus, +functionalCurrency, +sizeCategory, +ownershipType
CREATE NODE TABLE IF NOT EXISTS TaxEntity (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,                        -- 企业|个人|个体工商户
    taxpayerStatus STRING,              -- 一般纳税人|小规模纳税人|自然人
    residencyStatus STRING,             -- v4.1: resident|non_resident (居民|非居民)
    functionalCurrency STRING,          -- v4.1: CNY|USD|HKD|EUR etc.
    sizeCategory STRING,                -- v4.1: micro|small|medium|large
    ownershipType STRING                -- v4.1: domestic|foreign|joint_venture|state_owned
);

-- N12. Region (地区)
-- v4.1: +regionType to support international treaty countries
CREATE NODE TABLE IF NOT EXISTS Region (
    code STRING PRIMARY KEY,
    name STRING,
    level INT64,                        -- 1:省 2:市 3:区县 4:国家/地区(v4.1)
    regionType STRING                   -- v4.1: domestic|international|special_zone (国内|国际|特殊区域)
);

-- N13. Filing Form (申报表)
-- v4.1: +frequency, +applicableTaxpayerType
CREATE NODE TABLE IF NOT EXISTS FilingForm (
    id STRING PRIMARY KEY,
    name STRING,
    reportCycle STRING,                 -- 月|季|年
    deadlineDay INT64,
    frequency STRING,                   -- v4.1: monthly|quarterly|semi_annual|annual|event_driven
    applicableTaxpayerType STRING       -- v4.1: general|small_scale|all
);

-- N14. Business Activity (经济业务)
CREATE NODE TABLE IF NOT EXISTS BusinessActivity (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING
);

-- === L3 Compliance Layer (7) ===

-- N4. Compliance Rule (合规规则)
-- v4.1: +applicableScope for industry/scale filtering
CREATE NODE TABLE IF NOT EXISTS ComplianceRule (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING,
    category STRING,                    -- 申报义务|代扣代缴|发票管理|记录保存|资质要求|社保公积金|工商行政
    consequence STRING,
    applicableScope STRING,             -- v4.1: JSON {taxpayerTypes, industries, scales, regions}
    effectiveDate STRING,
    expiryDate STRING
);

-- N5. Risk Indicator (风险指标)
-- v4.1: +formula, +severity, +category
CREATE NODE TABLE IF NOT EXISTS RiskIndicator (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING,
    indicatorType STRING,
    threshold DOUBLE,
    severity STRING,                    -- v4.1: low|medium|high|critical
    formula STRING,                     -- v4.1: 计算公式 (e.g. "实缴增值税/不含税收入*100%")
    category STRING                     -- v4.1: shell_company|hidden_income|related_party|tax_burden etc.
);

-- N6. Tax Incentive (税收优惠)
-- v4.1: +status, +incentiveType, +stackingGroup, +eligibilityCriteria
CREATE NODE TABLE IF NOT EXISTS TaxIncentive (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,
    description STRING,
    incentiveType STRING,               -- v4.1: rate_reduction|super_deduction|accelerated_depreciation|exemption|refund
    status STRING,                      -- v4.1: active|expired|pending_renewal
    stackingGroup STRING,               -- v4.1: 互斥组标识 (同组内不可叠加)
    eligibilityCriteria STRING,         -- v4.1: JSON结构化条件
    effectiveDate STRING,
    expiryDate STRING
);

-- N16. Penalty (处罚规定)
-- v4.1: +penaltyType for criminal vs administrative
CREATE NODE TABLE IF NOT EXISTS Penalty (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING,
    legalBasis STRING,
    penaltyType STRING,                 -- v4.1: administrative|criminal (行政处罚|刑事责任)
    minAmount STRING,
    maxAmount STRING,
    maxSentence STRING                  -- v4.1: 刑事最高刑期 (仅criminal类型)
);

-- N17. Audit Trigger (审计触发)
CREATE NODE TABLE IF NOT EXISTS AuditTrigger (
    id STRING PRIMARY KEY,
    name STRING,
    description STRING,
    triggerCondition STRING,
    threshold STRING,
    frequency STRING
);

-- N18. Tax Accounting Gap (税会差异)
-- v4.1: +adjustmentDirection, +A105000LineRef, +carryForward, +deferredTaxType, +legalBasis, +source
CREATE NODE TABLE IF NOT EXISTS TaxAccountingGap (
    id STRING PRIMARY KEY,
    name STRING,
    accountingTreatment STRING,
    taxTreatment STRING,
    gapType STRING,                     -- permanent|timing|method
    adjustmentDirection STRING,         -- v4.1: increase|decrease|both (调增|调减|双向)
    impact STRING,
    example STRING,
    A105000LineRef STRING,              -- v4.1: 纳税调整明细表行号
    carryForward INT64,                 -- v4.1: 1=可结转, 0=不可结转
    deferredTaxType STRING,             -- v4.1: DTA|DTL|none (递延所得税资产|负债|无)
    legalBasis STRING,                  -- v4.1: 主要法规依据
    source STRING                       -- v4.1: CPA教材|CTA教材|实务案例
);

-- === NEW in v4.1 (3 nodes) ===

-- N19. Social Insurance Rule (社保公积金规则) -- NEW v4.1
-- Source: ft-social-insurance skill review (P0 gap)
CREATE NODE TABLE IF NOT EXISTS SocialInsuranceRule (
    id STRING PRIMARY KEY,
    name STRING,
    insuranceType STRING,               -- 养老|医疗|失业|工伤|生育|公积金|残保金
    employerRate STRING,                -- 单位比例 (STRING因各地不同)
    employeeRate STRING,                -- 个人比例
    baseFloor STRING,                   -- 基数下限规则 (e.g. "社平工资60%")
    baseCeiling STRING,                 -- 基数上限规则 (e.g. "社平工资300%")
    adjustmentMonth STRING,             -- 调整月份 (e.g. "7月")
    effectiveDate STRING,
    regionId STRING                     -- 适用地区
);

-- N20. Invoice Rule (发票管理规则) -- NEW v4.1
-- Source: ft-invoice-manager skill review (P0 gap)
CREATE NODE TABLE IF NOT EXISTS InvoiceRule (
    id STRING PRIMARY KEY,
    name STRING,
    ruleType STRING,                    -- certification|deduction|transfer_out|red_letter|verification|e_invoice
    invoiceType STRING,                 -- 专票|普票|数电票|机动车|农产品收购|通行费
    condition STRING,                   -- 适用条件
    procedure STRING,                   -- 操作流程
    legalBasis STRING                   -- 法规依据
);

-- N21. Industry Benchmark (行业基准数据) -- NEW v4.1
-- Source: ft-risk-assessment + ft-financial-statement review (P1 gap)
CREATE NODE TABLE IF NOT EXISTS IndustryBenchmark (
    id STRING PRIMARY KEY,
    industryCode STRING,                -- 关联Classification.code
    ratioName STRING,                   -- 毛利率|净利率|税负率|费用率|存货周转|应收周转
    minValue DOUBLE,
    maxValue DOUBLE,
    unit STRING,                        -- %|天|次
    year STRING,
    regionId STRING,                    -- 地区 (各地预警值不同)
    source STRING                       -- 数据来源 (税务局/行业协会/统计局)
);

-- === Knowledge Layer (1) ===

-- N7. Knowledge Unit (知识单元)
CREATE NODE TABLE IF NOT EXISTS KnowledgeUnit (
    id STRING PRIMARY KEY,
    type STRING,                        -- FAQ|案例解析|考点|风险提示|操作指南|思维导图|审计发现|犯罪构成|争议案例|行业基准
    title STRING,
    content STRING,
    source STRING
);


-- ============================================================
-- PART 2: EDGE TABLES (52)
-- ============================================================

-- === v3.1 Original (36, with v4.1 attribute enhancements) ===

-- Structural (3, +1 self-ref)
CREATE REL TABLE IF NOT EXISTS PART_OF (FROM LegalClause TO LegalDocument);
CREATE REL TABLE IF NOT EXISTS CHILD_OF (FROM Classification TO Classification);
CREATE REL TABLE IF NOT EXISTS PARENT_CLAUSE (FROM LegalClause TO LegalClause);          -- v4.1: 章节层级自引用

-- Legal Evolution (3)
CREATE REL TABLE IF NOT EXISTS SUPERSEDES (FROM LegalDocument TO LegalDocument);
CREATE REL TABLE IF NOT EXISTS AMENDS (FROM LegalDocument TO LegalDocument);
CREATE REL TABLE IF NOT EXISTS CONFLICTS_WITH (FROM LegalClause TO LegalClause);

-- Authority & Citation (4)
CREATE REL TABLE IF NOT EXISTS REFERENCES_CLAUSE (FROM LegalClause TO LegalClause);
CREATE REL TABLE IF NOT EXISTS BASED_ON (FROM TaxRate TO LegalClause);
CREATE REL TABLE IF NOT EXISTS INCENTIVE_BASED_ON (FROM TaxIncentive TO LegalClause);
CREATE REL TABLE IF NOT EXISTS ISSUED_BY (FROM LegalDocument TO IssuingBody);

-- Applicability (4)
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_TAX (FROM TaxRate TO TaxType);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_ENTITY (FROM TaxRate TO TaxEntity);
CREATE REL TABLE IF NOT EXISTS APPLIES_IN_REGION (FROM TaxRate TO Region);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_CLASS (FROM TaxRate TO Classification);

-- Inter-Tax (3)
CREATE REL TABLE IF NOT EXISTS CALCULATED_FROM (FROM TaxType TO TaxType);
CREATE REL TABLE IF NOT EXISTS SURCHARGE_OF (FROM TaxType TO TaxType);
CREATE REL TABLE IF NOT EXISTS RELATED_TAX (FROM TaxType TO TaxType);

-- Tax-Bridge (8)
CREATE REL TABLE IF NOT EXISTS TRIGGERS_TAX (FROM BusinessActivity TO TaxType);          -- v4.1: +taxRole, +condition edge properties
CREATE REL TABLE IF NOT EXISTS INCENTIVE_FOR_TAX (FROM TaxIncentive TO TaxType);
CREATE REL TABLE IF NOT EXISTS RULE_FOR_TAX (FROM ComplianceRule TO TaxType);
CREATE REL TABLE IF NOT EXISTS FILING_FOR_TAX (FROM FilingForm TO TaxType);
CREATE REL TABLE IF NOT EXISTS MAPS_TO_ACCOUNT (FROM TaxType TO AccountingSubject);
CREATE REL TABLE IF NOT EXISTS RISK_FOR_TAX (FROM RiskIndicator TO TaxType);
CREATE REL TABLE IF NOT EXISTS KU_ABOUT_TAX (FROM KnowledgeUnit TO TaxType);
CREATE REL TABLE IF NOT EXISTS AUDIT_FOR_TAX (FROM AuditTrigger TO TaxType);

-- Filing & Compliance (2)
CREATE REL TABLE IF NOT EXISTS REQUIRES_FILING (FROM BusinessActivity TO FilingForm);
CREATE REL TABLE IF NOT EXISTS GOVERNED_BY (FROM BusinessActivity TO ComplianceRule);

-- Accounting (2)
CREATE REL TABLE IF NOT EXISTS DEBITS_V2 (FROM TaxType TO AccountingSubject);
CREATE REL TABLE IF NOT EXISTS CREDITS_V2 (FROM TaxType TO AccountingSubject);

-- Compliance (2)
CREATE REL TABLE IF NOT EXISTS PENALIZED_BY (FROM ComplianceRule TO Penalty);
CREATE REL TABLE IF NOT EXISTS TRIGGERED_BY (FROM AuditTrigger TO RiskIndicator);

-- Knowledge (6)
CREATE REL TABLE IF NOT EXISTS INTERPRETS (FROM KnowledgeUnit TO LegalClause);
CREATE REL TABLE IF NOT EXISTS EXEMPLIFIED_BY (FROM KnowledgeUnit TO LegalClause);
CREATE REL TABLE IF NOT EXISTS EXPLAINS_RATE (FROM KnowledgeUnit TO LegalClause);
CREATE REL TABLE IF NOT EXISTS WARNS_ABOUT (FROM KnowledgeUnit TO LegalClause);
CREATE REL TABLE IF NOT EXISTS DESCRIBES_INCENTIVE (FROM KnowledgeUnit TO LegalClause);
CREATE REL TABLE IF NOT EXISTS GUIDES_FILING (FROM KnowledgeUnit TO LegalClause);

-- === v4.0 Edges (4) ===
CREATE REL TABLE IF NOT EXISTS HAS_GAP (FROM AccountingSubject TO TaxAccountingGap);
CREATE REL TABLE IF NOT EXISTS GAP_FOR_TAX (FROM TaxAccountingGap TO TaxType);
CREATE REL TABLE IF NOT EXISTS OVERRIDES_IN (FROM Region TO ComplianceRule);
CREATE REL TABLE IF NOT EXISTS AUDIT_TRIGGERS (FROM AuditTrigger TO ComplianceRule);

-- === v4.1 NEW Edges (12) ===

-- Accounting hierarchy (1)
CREATE REL TABLE IF NOT EXISTS PARENT_SUBJECT (FROM AccountingSubject TO AccountingSubject);  -- 科目层级自引用

-- Business → Accounting mapping (1) -- P0: 核心路径
CREATE REL TABLE IF NOT EXISTS MAPS_TO_SUBJECT (FROM BusinessActivity TO AccountingSubject);   -- 业务活动→会计科目(借方/贷方)

-- Tax Incentive stacking (2) -- P1: 筹划核心
CREATE REL TABLE IF NOT EXISTS STACKS_WITH (FROM TaxIncentive TO TaxIncentive);               -- 可叠加
CREATE REL TABLE IF NOT EXISTS EXCLUDES (FROM TaxIncentive TO TaxIncentive);                  -- 互斥

-- Tax Incentive → Gap bridge (1) -- P0: 汇算清缴直通
CREATE REL TABLE IF NOT EXISTS CREATES_GAP (FROM TaxIncentive TO TaxAccountingGap);

-- Business-level gap (1)
CREATE REL TABLE IF NOT EXISTS HAS_BUSINESS_GAP (FROM BusinessActivity TO TaxAccountingGap);

-- Entity relationships (1) -- P0: 合并报表+转让定价硬依赖
CREATE REL TABLE IF NOT EXISTS RELATED_PARTY (FROM TaxEntity TO TaxEntity);                   -- properties: shareholdingRatio, relationshipType, controlType

-- Classification → Rate (1) -- P1: 出口退税核心路径
CREATE REL TABLE IF NOT EXISTS HAS_RATE (FROM Classification TO TaxRate);                     -- HS编码→退税率/征税率

-- Social Insurance (1)
CREATE REL TABLE IF NOT EXISTS INSURANCE_IN_REGION (FROM SocialInsuranceRule TO Region);

-- Invoice (1)
CREATE REL TABLE IF NOT EXISTS INVOICE_FOR_TAX (FROM InvoiceRule TO TaxType);

-- Industry Benchmark (1)
CREATE REL TABLE IF NOT EXISTS BENCHMARK_FOR (FROM IndustryBenchmark TO Classification);

-- Industry-specific compliance (1)
CREATE REL TABLE IF NOT EXISTS RULE_FOR_INDUSTRY (FROM ComplianceRule TO Classification);


-- ============================================================
-- PART 3: SCOPE BOUNDARY (v4.1 新增章节)
-- ============================================================
-- KG 存储静态知识（规则/法规/阈值/基准），不存运行时数据。
-- 以下数据明确由外部系统提供：
--   - 企业财务数据（科目余额/报表数据）→ ERP/财务系统
--   - 实时汇率 → 央行API
--   - 银行流水 → 银行系统
--   - 社保实际缴纳数据 → 社保系统
--   - 发票明细数据 → 金税系统/电子税务局
--   - 可比企业财务数据 → BvD/同花顺
--   - 关联方持股比例 → 企业工商系统
--   - 标准成本/实际成本差异 → 成本核算系统
-- KG 通过 ComplianceRule/KnowledgeUnit 告诉业务系统"应该用什么规则处理这些数据"
