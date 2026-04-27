// ============================================================================
// CogNebula Ontology v4.2 — Canonical Schema
// Source: doc/00_project/initiative_cognebula_sota/ONTOLOGY_V42_DESIGN.html
// Derived: 2026-04-17 (Session 68 post-deploy audit)
// ----------------------------------------------------------------------------
// Hard rules (from design doc):
//   - 35 node types, ~72 edge types, layered 4-tier architecture
//   - Brooks conceptual integrity ceiling: 37 types. Do not exceed.
//   - Keep 540K+ existing nodes. Do not mass-migrate.
//   - TRUNCATE only designated garbage (RiskIndicator 463, AuditTrigger 463) when
//     superseded by V2 counterpart.
//   - Every type carries a purpose-field. Zero placeholder columns.
// ============================================================================

// ------------------ Tier 1: Legal Backbone (7 types) ------------------
CREATE NODE TABLE IF NOT EXISTS LegalDocument(
    id STRING, title STRING, docType STRING, issuedAt STRING,
    issuingBody STRING, effectiveAt STRING, supersededAt STRING,
    fullText STRING, sourceUrl STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS LegalClause(
    id STRING, docId STRING, clauseNumber STRING, title STRING,
    fullText STRING, effectiveAt STRING, supersededAt STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS IssuingBody(
    id STRING, name STRING, level STRING, jurisdiction STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS Classification(
    id STRING, name STRING, code STRING, level INT64, parentId STRING,
    scheme STRING, description STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS PolicyChange(
    id STRING, name STRING, effectiveAt STRING, changeType STRING,
    description STRING, sourceDocId STRING,
    PRIMARY KEY (id));

// TaxTreaty REMOVED 2026-04-27 (v4.2.4 schema-overreach DROP).
// Multi-jurisdiction is anti-pattern A2 — banned until 金税四期 coverage > 90%
// AND ≥1 paying CN customer renews. Re-introduce with: CREATE NODE TABLE
// TaxTreaty(id STRING, name STRING, partyA STRING, partyB STRING,
// signedAt STRING, effectiveAt STRING, scope STRING, PRIMARY KEY(id));

CREATE NODE TABLE IF NOT EXISTS KnowledgeUnit(
    id STRING, topic STRING, content STRING, sourceDocId STRING,
    embeddingId STRING, authorityScore DOUBLE,
    PRIMARY KEY (id));

// ------------------ Tier 2: Tax Domain Primitives (9 types) ------------------
CREATE NODE TABLE IF NOT EXISTS TaxType(
    id STRING, name STRING, code STRING, scope STRING, description STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxEntity(
    id STRING, name STRING, entityKind STRING, description STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS Region(
    id STRING, name STRING, code STRING, level STRING, parentId STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxBasis(
    id STRING, name STRING, description STRING, scope STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxRate(
    id STRING, rate DOUBLE, taxTypeId STRING, effectiveAt STRING,
    supersededAt STRING, description STRING, bracketKind STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxCalculationRule(
    id STRING, name STRING, formula STRING, description STRING,
    taxTypeId STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxItem(
    id STRING, name STRING, description STRING, taxTypeId STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS DeductionRule(
    id STRING, name STRING, description STRING, taxTypeId STRING,
    threshold DOUBLE, unit STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS BusinessActivity(
    id STRING, name STRING, description STRING,
    PRIMARY KEY (id));

// ------------------ Tier 3: Operational Rules (10 types) ------------------
CREATE NODE TABLE IF NOT EXISTS ComplianceRule(
    id STRING, name STRING, description STRING, severity STRING,
    sourceClauseId STRING, status STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxIncentive(
    id STRING, name STRING, description STRING, effectiveAt STRING,
    supersededAt STRING, sourceClauseId STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS InvoiceRule(
    id STRING, name STRING, description STRING, invoiceType STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS FilingForm(
    id STRING, name STRING, formCode STRING, description STRING,
    taxTypeId STRING, effectiveAt STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS FilingFormField(
    id STRING, formId STRING, fieldCode STRING, fieldName STRING,
    description STRING, dataType STRING,
    PRIMARY KEY (id));

// RiskIndicator REMOVED 2026-04-27 (v4.2.3 garbage DROP, superseded by RiskIndicatorV2).
// V1 was 463 admitted-garbage rows; V2 carries the same 463 rows with proper schema.
// Schema authors marked it for TRUNCATE in this file's own header (line 10).
// This declaration removal closes that loop — canonical_count 32 → 31.

CREATE NODE TABLE IF NOT EXISTS AuditTrigger(
    id STRING, name STRING, description STRING, severity STRING,
    triggerKind STRING,
    PRIMARY KEY (id));

// TaxLiabilityTrigger REMOVED 2026-04-27 (v4.2.4 schema-overreach DROP).
// Functionally identical to ComplianceRule + TaxCalculationRule (semantic dup).
//
// ResponseStrategy REMOVED 2026-04-27 (v4.2.4 schema-overreach DROP).
// Payload `recommendedSteps STRING` is consulting prose, not graph-queryable
// structure. No SOTA tax KG (TaxLOD/ONESOURCE/Bloomberg Tax) carries this.
// Risk semantics handled via ComplianceRule + Penalty + RiskIndicatorV2 chains.

CREATE NODE TABLE IF NOT EXISTS Penalty(
    id STRING, name STRING, description STRING, amount DOUBLE,
    unit STRING, sourceClauseId STRING,
    PRIMARY KEY (id));

// ------------------ Tier 4: Accounting + Reporting Bridge (9 types) ------------------
CREATE NODE TABLE IF NOT EXISTS AccountingStandard(
    id STRING, name STRING, code STRING, issuer STRING,
    effectiveAt STRING, description STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS AccountingSubject(
    id STRING, code STRING, name STRING, category STRING,
    balanceSide STRING, parentId STRING, description STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS JournalEntryTemplate(
    id STRING, name STRING, description STRING, scenarioId STRING,
    debitSubjectId STRING, creditSubjectId STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS FinancialStatementItem(
    id STRING, name STRING, statementKind STRING, lineNumber INT64,
    description STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS FinancialIndicator(
    id STRING, name STRING, formula STRING, description STRING,
    interpretation STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS IndustryBenchmark(
    id STRING, industryId STRING, metric STRING, p25 DOUBLE, p50 DOUBLE,
    p75 DOUBLE, source STRING, year INT64,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS SocialInsuranceRule(
    id STRING, name STRING, description STRING, regionId STRING,
    effectiveAt STRING, baseMin DOUBLE, baseMax DOUBLE,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxAccountingGap(
    id STRING, name STRING, description STRING, gapKind STRING,
    direction STRING,
    PRIMARY KEY (id));

CREATE NODE TABLE IF NOT EXISTS TaxMilestoneEvent(
    id STRING, name STRING, description STRING, dueRule STRING,
    taxTypeId STRING,
    PRIMARY KEY (id));

// ----------------------------------------------------------------------------
// Total canonical v4.2 node types: 35
//   Tier 1 Legal Backbone:           7
//   Tier 2 Tax Domain Primitives:    9
//   Tier 3 Operational Rules:       10
//   Tier 4 Accounting + Reporting:   9
// Brooks ceiling: 37 — headroom of 2 remaining.
// ----------------------------------------------------------------------------

// ============================================================================
// Ontology v4.2 — Edge Tables (79 edges across 4 tiers)
// Appended 2026-04-17 Session 69 (Action D).
// Extracted from ONTOLOGY_V42_DESIGN.html. Every FROM/TO references a canonical
// 35-type node from the NODE section above. Edge tables carry minimal metadata
// (source clause anchor when known, effectivity window where relevant).
// ============================================================================

// ------------------ Tier 1 -- Legal backbone + Knowledge interpretation (16) ------------------
CREATE REL TABLE IF NOT EXISTS AMENDS(FROM LegalDocument TO LegalDocument,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CHILD_OF(FROM Classification TO Classification,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CLASSIFIED_UNDER_TAX(FROM Classification TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CONFLICTS_WITH(FROM LegalClause TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS DESCRIBES_INCENTIVE(FROM KnowledgeUnit TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS EXEMPLIFIED_BY(FROM KnowledgeUnit TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS EXPLAINS_RATE(FROM KnowledgeUnit TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS GUIDES_FILING(FROM KnowledgeUnit TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS INTERPRETS(FROM KnowledgeUnit TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS ISSUED_BY(FROM LegalDocument TO IssuingBody,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS PARENT_CLAUSE(FROM LegalClause TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS PARENT_SUBJECT(FROM AccountingSubject TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS PART_OF(FROM LegalClause TO LegalDocument,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS REFERENCES_CLAUSE(FROM LegalClause TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS SUPERSEDES(FROM LegalDocument TO LegalDocument,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS WARNS_ABOUT(FROM KnowledgeUnit TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);

// ------------------ Tier 2 -- Tax-domain primitives (21) ------------------
CREATE REL TABLE IF NOT EXISTS APPLIES_IN_REGION(FROM TaxRate TO Region,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_CLASS(FROM TaxRate TO Classification,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_ENTITY(FROM TaxRate TO TaxEntity,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS APPLIES_TO_TAX(FROM TaxRate TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS BASED_ON(FROM TaxRate TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CALCULATED_FROM(FROM TaxType TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CALCULATION_FOR_TAX(FROM TaxCalculationRule TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS COMPUTED_BY(FROM TaxItem TO TaxBasis,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS DEDUCTS_FROM(FROM DeductionRule TO TaxBasis,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS ENTITY_FOR_TAX(FROM TaxEntity TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS HAS_ITEM(FROM TaxType TO TaxItem,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS HAS_RATE(FROM Classification TO TaxRate,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS INSURANCE_IN_REGION(FROM SocialInsuranceRule TO Region,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS INVOICE_FOR_TAX(FROM InvoiceRule TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS KU_ABOUT_TAX(FROM KnowledgeUnit TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
// LIABILITY_TRIGGERED_BY / OVERRIDES_RATE / PARTY_TO REMOVED 2026-04-27
// (companion to v4.2.4 — these REL declared FROM/TO into the 3 dropped stub
// node tables and would have failed to apply on a fresh DB after this edit.)
CREATE REL TABLE IF NOT EXISTS RELATED_PARTY(FROM TaxEntity TO TaxEntity,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS RELATED_TAX(FROM TaxType TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS SURCHARGE_OF(FROM TaxType TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);

// ------------------ Tier 3 -- Operational rules (26) ------------------
CREATE REL TABLE IF NOT EXISTS AUDIT_FOR_TAX(FROM AuditTrigger TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS AUDIT_TRIGGERS(FROM AuditTrigger TO ComplianceRule,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS DERIVES_FROM(FROM FilingFormField TO FilingFormField,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS ESCALATES_TO(FROM Penalty TO Penalty,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS EXCLUDES(FROM TaxIncentive TO TaxIncentive,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS FIELD_OF(FROM FilingFormField TO FilingForm,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS FILING_FOR_TAX(FROM FilingForm TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS FT_APPLIES_TO(FROM FilingForm TO TaxEntity,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS FT_GOVERNED_BY(FROM FilingForm TO ComplianceRule,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS FT_INCENTIVE_TAX(FROM TaxIncentive TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS FT_QUALIFIES_FOR(FROM TaxEntity TO TaxIncentive,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS GOVERNED_BY(FROM BusinessActivity TO ComplianceRule,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS INCENTIVE_BASED_ON(FROM TaxIncentive TO LegalClause,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS INCENTIVE_FOR_TAX(FROM TaxIncentive TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
// INDICATES_RISK REMOVED 2026-04-27 (companion to RiskIndicator V1 drop).
// V2 equivalent: edge from RiskIndicatorV2 to AuditTrigger if needed.
CREATE REL TABLE IF NOT EXISTS OVERRIDES_IN(FROM Region TO ComplianceRule,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS PENALIZED_BY(FROM ComplianceRule TO Penalty,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS PENALIZED_FOR(FROM Penalty TO BusinessActivity,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS REQUIRES_FILING(FROM BusinessActivity TO FilingForm,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
// RISK_FOR_TAX REMOVED 2026-04-27 (companion to RiskIndicator V1 drop).
// V2 equivalent already exists in production as RISK_FOR_TAX-style edge from RiskIndicatorV2.
CREATE REL TABLE IF NOT EXISTS RULE_FOR_INDUSTRY(FROM ComplianceRule TO Classification,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS RULE_FOR_TAX(FROM ComplianceRule TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS SPLITS_INTO(FROM BusinessActivity TO BusinessActivity,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS STACKS_WITH(FROM TaxIncentive TO TaxIncentive,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
// TRIGGERED_BY REMOVED 2026-04-27 (companion to RiskIndicator V1 drop).
CREATE REL TABLE IF NOT EXISTS TRIGGERS_TAX(FROM BusinessActivity TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);

// ------------------ Tier 4 -- Accounting + Reporting (16) ------------------
CREATE REL TABLE IF NOT EXISTS BENCHMARK_FOR(FROM IndustryBenchmark TO Classification,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS COMPUTED_FROM(FROM FinancialIndicator TO FinancialStatementItem,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CREATES_GAP(FROM TaxIncentive TO TaxAccountingGap,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS CREDITS_V2(FROM TaxType TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS DEBITS_V2(FROM TaxType TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS DECOMPOSES_INTO(FROM FinancialIndicator TO FinancialIndicator,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS ENTRY_CREDITS(FROM JournalEntryTemplate TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS ENTRY_DEBITS(FROM JournalEntryTemplate TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS GAP_FOR_TAX(FROM TaxAccountingGap TO TaxType,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS HAS_BENCHMARK(FROM FinancialIndicator TO IndustryBenchmark,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS HAS_BUSINESS_GAP(FROM BusinessActivity TO TaxAccountingGap,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS HAS_ENTRY_TEMPLATE(FROM BusinessActivity TO JournalEntryTemplate,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS HAS_GAP(FROM AccountingSubject TO TaxAccountingGap,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS MAPS_TO_ACCOUNT(FROM TaxType TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS MAPS_TO_SUBJECT(FROM BusinessActivity TO AccountingSubject,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);
CREATE REL TABLE IF NOT EXISTS POPULATES(FROM AccountingSubject TO FinancialStatementItem,
    sourceClauseId STRING, effectiveAt STRING, supersededAt STRING);

// ----------------------------------------------------------------------------
// Total edges: 79
// ============================================================================
