# V1+V2 Lineage Unification Design Proposal · 2026-04-28

> **Scope**: design proposal for §20 Phase B2. Owner decision: Maurice.
> **Status**: PROPOSAL, not authorized for execution. Replaces the obsolete `deploy/contabo/migrations/phase1_v1_v2_rename.cypher` plan (2026-04-17 Session 69).
> **Why phase1 is obsolete**: phase1 assumed V1 tables were empty stubs and V2 were the active lineage; intent was rename V2 → canonical, drop V1. Between 2026-04-17 and 2026-04-28, V1 tables got repopulated by a different ingest pipeline (LLM-extraction with rich semantic schema). Both lineages are now active with disjoint schemas. The drop-and-rename strategy would lose one lineage's data.

---

## 0. Scope confinement

This design covers **3 V1+V2 pairs**:
- `ComplianceRule` ↔ `ComplianceRuleV2`
- `FilingForm` ↔ `FilingFormV2`
- `TaxIncentive` ↔ `TaxIncentiveV2`

NOT covered (single-table situations require their own analysis):
- `RiskIndicatorV2` (orphan after M3 cleanup; V1 was deleted in commit `ea83f033`)
- `FormTemplate` ↔ `FilingForm` ↔ `FilingFormField` triangle (mentioned in phase1 as Phase 4 legacy folding; out of scope here)

---

## 1. The two lineages (from §20 Phase A3 schema diff)

### Lineage L1 (V1) — LLM semantic-extraction pipeline

Schema fields characteristic of L1 (sample from ComplianceRule):

```
argument_links_to       — graph linking to upstream legal arguments
argument_role           — claim / evidence / conclusion / objection
argument_strength       — float 0-1
confidence              — extractor confidence
extracted_by            — LLM model / version / prompt id
source_doc_id           — pointer to source LegalDocument
source_paragraph        — exact paragraph quoted / extracted from
jurisdiction_code       — ISO-style jurisdiction
jurisdiction_scope      — national / provincial / city
override_chain_id       — schema-evolution chain pointer
supersedes_id           — temporal supersession
effective_from / effective_to — temporal validity
reviewed_at / reviewed_by — human review trace
notes                   — free-text annotations
[per-domain semantic fields]:
  ComplianceRule: applicableEntityTypes, applicableTaxTypes, ruleCode,
                  severityLevel, conditionDescription, conditionFormula,
                  detectionQuery, autoDetectable, requiredAction,
                  violationConsequence, sourceClause, sourceRegulationId
  FilingForm:     applicableTaxpayerType, calculationRules, deadline,
                  deadlineAdjustmentRule, fields, filingChannel,
                  filingFrequency, formCode, formNumber, onlineFilingUrl,
                  penaltyForLate, relatedForms, taxTypeId, version
  TaxIncentive:   beneficiaryType, combinable, eligibilityCriteria,
                  effectiveFrom, effectiveUntil, incentiveType,
                  lawReference, maxAnnualBenefit, value, valueBasis
```

L1 emphasis: **why this fact is true, where it came from in the document, who can use it, what argument structure it participates in.**

### Lineage L2 (V2) — Crawler canonical-metadata pipeline

Schema fields characteristic of L2:

```
description             — canonical description text
effectiveDate           — single-field temporal (vs L1's effective_from/to)
expiryDate              — single-field expiry
regulationNumber        — official document number
regulationType          — type taxonomy (TaxLawNotice / Decree / etc.)
sourceUrl               — direct URL to the source document
fullText                — full crawled text body
hierarchyLevel          — position in regulation hierarchy
createdAt               — ingest timestamp
[per-table specifics]:
  FilingFormV2:        title, reportCycle, deadlineDay
  TaxIncentiveV2:      type
  ComplianceRuleV2:    consequence
```

L2 emphasis: **what the official document says, where it lives on the web, when it was published, how it fits in the regulatory hierarchy.**

---

## 2. Why neither "drop V1" nor "drop V2" works

| Action | What's lost | Who breaks |
|---|---|---|
| Drop V1, keep V2 (phase1 intent) | All argument structure, jurisdiction granularity, per-domain semantic fields, human review trace | yiclaw SaaS queries that reason on rule severity / applicable taxpayer type / etc. |
| Drop V2, keep V1 | sourceUrl, fullText, regulationNumber, hierarchyLevel, regulationType | Any UI that needs to link back to the source crawl, any RAG citation, the hierarchy view |
| Keep both, no merge | Identity-vs-occurrence stays braided forever | Future ingestions duplicate; agent retrieval double-counts; the canonical question "give me all compliance rules" stays ambiguous |

The right answer is **lineage merge into a single canonical entity with both schemas + a lineage tag**.

---

## 3. Proposed unified schema (NOT YET DECLARED in canonical ontology — see §7)

For each canonical entity (`ComplianceRule`, `FilingForm`, `TaxIncentive`), the unified schema is **L1's rich schema PLUS L2's canonical fields PLUS lineage metadata**.

### Field groups (showing `ComplianceRule` example; same shape for `FilingForm` / `TaxIncentive` with table-specific fields)

**Identity**
- `id` STRING PRIMARY KEY
- `name` STRING

**L2 canonical metadata** (from V2 crawler pipeline)
- `description` STRING
- `effectiveDate` DATE
- `expiryDate` DATE
- `regulationNumber` STRING
- `regulationType` STRING
- `sourceUrl` STRING
- `fullText` STRING
- `hierarchyLevel` INT64
- `createdAt` TIMESTAMP
- `consequence` STRING

**L1 per-domain semantic fields** (from V1 LLM-extraction pipeline; ComplianceRule example)
- `category`, `applicableEntityTypes` STRING[], `applicableTaxTypes` STRING[]
- `ruleCode`, `severityLevel`
- `conditionDescription`, `conditionFormula`, `detectionQuery`, `autoDetectable` BOOLEAN
- `requiredAction`, `violationConsequence`
- `sourceClause`, `sourceRegulationId`

**L1 argument structure**
- `argument_role` STRING (claim / evidence / conclusion / objection)
- `argument_strength` DOUBLE
- `argument_links_to` STRING

**L1 provenance**
- `source_doc_id`, `source_paragraph`
- `extracted_by`, `confidence` DOUBLE

**L1 jurisdictional**
- `jurisdiction_code`, `jurisdiction_scope`

**L1 temporal granular**
- `effective_from`, `effective_to` TIMESTAMP

**L1 review trace**
- `reviewed_at` TIMESTAMP, `reviewed_by`, `notes`

**L1 schema-evolution**
- `override_chain_id`, `supersedes_id`

**Lineage tag (NEW — Hickey synthesis target)**
- `_lineage_present` STRING[] — e.g. `['L1','L2']` when both lineages contribute, `['L1']` or `['L2']` when one only, `['L1','L2','manual']` when human review added a third

**Key design decision**: `_lineage_present` is an array. A row carries the *list* of lineages that contributed data, not a single "version" tag. This is **Hickey's synthesis target made concrete**: schema-version is a value attached to a single canonical entity, not a separate place.

---

## 4. Migration shape (deferred to B2 execution session)

### High-level steps (per pair)

1. **Backup** — full Parquet snapshot of both tables before any write.
2. **Create unified table** — `ComplianceRule_Unified` with the schema above. Use `_Unified` suffix during migration to avoid collision with live `ComplianceRule` (L1).
3. **Populate from L1** — for each row in `ComplianceRule`, INSERT into `_Unified` with `_lineage_present = ['L1']`. Keep L2 fields NULL.
4. **Merge L2 in** — for each row in `ComplianceRuleV2`, find matching id in `_Unified`. If match: UPDATE L2 fields, append `'L2'` to `_lineage_present`. If no match: INSERT with `_lineage_present = ['L2']`, L1 fields NULL.
5. **Conflict resolution** — for rows where both L1 and L2 have a value for a *common* field (e.g., both define `name` differently), explicit precedence rule: L1 wins for `name` (LLM-extracted is canonical), L2 wins for `effectiveDate` (crawler is authoritative for dates). Document the precedence map per field.
6. **Rewire edges** — every relationship pointing at `ComplianceRule` or `ComplianceRuleV2` gets duplicated to point at `_Unified`. The old tables stay populated (read-only) during rewire.
7. **Cutover** — when all readers point at `_Unified`, drop both `ComplianceRule` and `ComplianceRuleV2`. Rename `ComplianceRule_Unified` → `ComplianceRule`.
8. **Verification** — count rows pre/post; spot-check 10 rows for each lineage flag; run `ai check` on dependent tests.

### Why this is NOT yet executable

- The **conflict resolution precedence map** needs Maurice's domain judgment (which field is authoritative when both lineages disagree)
- The **edge rewire enumeration** requires listing every relationship that points at the V1 or V2 tables (deferred to B2 execution)
- The **cutover gate** depends on every consumer (yiclaw SaaS / kg-api UI / agent retrieval) being audited and confirmed to handle the new unified schema
- Per Munger R2 Chesterton's fence: any irreversible drop of V1 or V2 must wait until **post-migration verification + 7-day soak**

---

## 5. Special cases NOT covered by this design

### `RiskIndicatorV2` orphan

V1 `RiskIndicator` was deleted in commit `ea83f033` (M3 remediation, 2026-03-20 — "RiskIndicator(378) deleted"). V2 is the SURVIVOR. Schema follows L2 pattern (createdAt, fullText, hierarchyLevel, regulationNumber, regulationType, sourceUrl).

Recommendation: rename `RiskIndicatorV2` → `RiskIndicator` directly. No L1 lineage exists to merge in. This is a 1-step admin operation, much simpler than the 3-pair lineage unification above. **Owner**: Maurice for separate authorization, not part of B2 lineage merge.

### `TaxIncentiveV2` row count vs `TaxIncentive` row count

phase1_v1_v2_rename.cypher line 4-7 noted: "TaxIncentiveV2 (109 rows) coexists with TaxIncentive (already populated, intersection)". Need re-probe of current row counts before B2 execution. The intersection-handling logic (step 5 above) becomes load-bearing here.

---

## 6. Connection to other §20 findings

| §20 Finding | How this design touches it |
|---|---|
| F1 V2 proliferation | Directly addresses — converts 3 pairs to 1 canonical each |
| F2 line 1708 [:500] | Independent — unified migration scripts must NOT use the legacy `migrate-table` admin endpoint with its [:500] clamp; new migration code writes directly via Cypher |
| F4 schema-runtime drift | Adds — `_Unified` tables MUST be declared in `schemas/ontology_v4.3.cypher` (extending v4.2) BEFORE migration runs |
| F5 source attribution | Reinforced — `_lineage_present` is one form of source attribution; can integrate with the broader `Source` node when A5 lands |

---

## 7. Owner decision needed

Before B2 can move from PROPOSAL to EXECUTABLE, Maurice authorizes:

- [ ] **Approve unified schema shape** (single canonical entity + L1 fields + L2 fields + `_lineage_present` tag) vs alternative (e.g., keep two tables, add cross-edges only)
- [ ] **Approve `_Unified` migration table pattern** vs alternative (in-place rename + ALTER ADD COLUMN)
- [ ] **Author conflict-resolution precedence map** for each pair (which lineage wins per overlapping field)
- [ ] **Authorize backup window** before migration runs
- [ ] **Authorize cutover gate criteria** (consumer audit + soak window)

Without these decisions, the migration script writing is premature and would have to be rewritten.

---

## 8. Synthesis target (Hickey, R3 audit)

> Treat schema-version as a value attached to a single canonical entity, and make migration a pure identity-preserving function.

This design **realizes** that target:
- **Schema-version as value**: `_lineage_present` is a row-level array, not a table-level fact. Adding L3 (e.g., a new ingest pipeline) extends the array, not the table count.
- **Migration as identity-preserving function**: every row in L1 ∪ L2 maps to exactly one row in `_Unified`. Identity is preserved by `id`. No row is dropped, no row is duplicated. The function is total and bijective on the union.

---

Maurice | maurice_wen@proton.me
