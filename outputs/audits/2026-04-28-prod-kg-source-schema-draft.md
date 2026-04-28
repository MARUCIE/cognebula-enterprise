# `Source` Node Schema Draft · 2026-04-28

> **Scope**: §20 Phase A5 deliverable. Designs the `Source` node type that closes F5 (source-attribution gap).
> **Status**: DRAFT. Owner authorization needed before declaration in `schemas/`.

---

## Why `Source` exists

F5 finding from depth-breadth audit: only `LegalClause` carries semantic source attribution (via `CL_*` ID prefix). All other node types use hash-style auto-generated IDs with no `source_id` foreign key. The KG cannot answer "where did this fact come from?" for the majority of its 368,910 nodes.

A `Source` node centralizes provenance. Every fact-bearing node gets a `source_id` foreign key pointing to a `Source` row. Lineage queries become a single graph traversal.

---

## Schema (proposed — NOT YET DECLARED in canonical ontology; see §authorization)

Field list for the proposed `Source` node type:

| Field | Type | Required | Purpose / Example |
|---|---|---|---|
| `id` | STRING (PK) | yes | canonical source ID, e.g. `chinatax_gov_2024_announce_47` |
| `label` | STRING | yes | human-readable name, e.g. `国家税务总局公告 2024 年第 47 号` |
| `url` | STRING | yes | canonical URL on the source's website |
| `source_type` | STRING | yes | `crawler` / `llm-extracted` / `manual` / `imported` |
| `ingest_pipeline` | STRING | yes | pipeline identifier, e.g. `chinatax-crawl-v3` |
| `ingest_ts` | TIMESTAMP | no | when this source was first ingested |
| `publication_ts` | TIMESTAMP | no | when the original document was published |
| `jurisdiction` | STRING | no | `national` / `provincial:广东` / etc. |
| `authority` | STRING | no | issuing body, e.g. `国家税务总局` / `财政部` |

Five required, four optional. Minimal possible while still answering the canonical question "give me everything from chinatax.gov.cn published in 2024 about VAT."

---

## Per-table source coverage matrix (current state)

Based on the §20 Phase A field enumeration, here is what each major table already carries that maps to `Source`:

| Table | Has implicit source? | Mapping path | source_id backfill cost |
|---|---|---|---|
| `LegalClause` | YES — `CL_*` ID prefix encodes chinatax origin | Parse prefix → look up source registry | LOW (deterministic) |
| `KnowledgeUnit` | PARTIAL — has `source_doc_id` field | Join on `source_doc_id` → resolve to `Source` | LOW (existing field) |
| `FAQEntry` | PARTIAL — subset has `12366_qa_*` prefix | Parse prefix; rest needs guess | MEDIUM (subset only) |
| `LegalDocument` | YES — has `source_doc_id`, `source_paragraph` | Already structured | LOW |
| `TaxIncentive` | NO — hash IDs, no source field | Need re-ingest with source attribution | HIGH |
| `TaxIncentiveV2` | YES — has `sourceUrl` | Resolve URL → `Source.url` | LOW |
| `ComplianceRule` (L1) | PARTIAL — has `source_doc_id`, `sourceClause`, `sourceRegulationId` | Triangulate three fields | MEDIUM |
| `ComplianceRuleV2` (L2) | NO — has neither | Need URL extraction from crawl logs | HIGH |
| `FilingForm` (L1) | NO — `formCode` is internal, not source | Cross-ref through `taxTypeId` → policy | HIGH |
| `FilingFormV2` (L2) | YES — has `sourceUrl` | Resolve URL → `Source.url` | LOW |
| `RiskIndicatorV2` | YES — has `sourceUrl` | Same as FilingFormV2 | LOW |
| `TaxRate*` family | NO — `code` is internal | Need re-association via reform-policy graph | HIGH |
| `Industry*` family | NO | Need re-ingest | HIGH |
| `IssuingBody`, `Region`, `TaxType` | N/A — these ARE source-side dimensions, not facts | Skip; they describe sources rather than carry source | — |

**Pattern**: V2 lineage already has reasonable source attribution (via `sourceUrl`); V1 lineage has partial structured provenance (via `source_doc_id`, `extracted_by`); the auto-generated hash-ID tables (TaxRate, Industry, etc.) are the highest-cost backfill.

---

## Backfill phasing (proposal)

Phase 1 (LOW-cost backfills, ~70% coverage):
- `LegalClause` — parse `CL_*` prefix, populate from chinatax registry
- `KnowledgeUnit` — chase `source_doc_id` to `LegalDocument`, resolve up to `Source`
- `LegalDocument` — direct `source_doc_id` → `Source`
- All V2-lineage tables (`*V2`) — resolve `sourceUrl` → `Source.url`

Phase 2 (MEDIUM-cost):
- `FAQEntry` — parse `12366_qa_*` prefix subset; rest stays NULL
- `ComplianceRule` (L1) — triangulate three source fields

Phase 3 (HIGH-cost — defer to ingest pipeline rewrite):
- `TaxIncentive` (L1, hash IDs)
- `ComplianceRuleV2` (L2 without sourceUrl-only)
- `FilingForm` (L1)
- `TaxRate*` family
- `Industry*` family

Phase 1 alone would close ~70% of the source-attribution gap. Phase 2 adds another ~10%. Phase 3 is structurally hard and requires upstream pipeline changes, not just backfill.

---

## Open questions for Maurice

- [ ] **`source_type` enum closed or open?** Closed = strict ('crawler' | 'llm-extracted' | 'manual' | 'imported'). Open = free string. Strict is safer for analytics, open is friendlier for unforeseen ingest paths.
- [ ] **Backfill ordering**: do Phase 1 first (and ship F5 as ~70% closed), or hold for full Phase 1+2+3?
- [ ] **`_lineage_present` (B2) vs `source_id` (this draft)**: do we need both? Proposal: `_lineage_present` describes WHICH PIPELINE produced this row; `source_id` describes WHICH SOURCE DOCUMENT the fact came from. Different axes; both have value. But Maurice may want to consolidate.

---

Maurice | maurice_wen@proton.me
