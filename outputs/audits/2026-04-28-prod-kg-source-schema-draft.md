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

> **2026-04-28 update — empirical falsification**: 5 of the original 7 Phase-1
> LOW-cost claims below were FALSIFIED by direct probe
> (`scripts/probe_source_attribution.py --sample-size 200`). Schema-declared ≠
> populated: V2 tables carry `sourceUrl` as a column but it is universally
> empty (0/sampled across all 4 V2 tables); `LegalDocument.source_doc_id` is
> declared but 0/200 populated. The two confirmed paths are LegalClause and
> KnowledgeUnit — these alone cover ~50% of nodes, NOT the ~70% originally
> claimed. The matrix below shows ORIGINAL design vs PROBED reality.

| Table | Original claim | Probed reality (2026-04-28) | Phase-1 verdict |
|---|---|---|---|
| `LegalClause` | LOW via `CL_*` prefix | **CONFIRMED** — 200/200 IDs match `CL_<doc-hash>_<clause>`; 24 distinct doc-groups in 200 sample | **LOW** |
| `KnowledgeUnit` | LOW via `source_doc_id` | **CONFIRMED** — 500/500 populated, ~500-800 distinct source files extrapolated | **LOW** |
| `LegalDocument` | LOW via `source_doc_id` | **FALSIFIED** — 0/200 rows have populated `source_doc_id`. Column declared but empty. | **EMPTY-FIELD** |
| `ComplianceRuleV2` | LOW via `sourceUrl` | **FALSIFIED** — 0/84 rows have populated `sourceUrl` | **EMPTY-FIELD** |
| `FilingFormV2` | LOW via `sourceUrl` | **FALSIFIED** — 0/121 rows | **EMPTY-FIELD** |
| `TaxIncentiveV2` | LOW via `sourceUrl` | **FALSIFIED** — 0/109 rows | **EMPTY-FIELD** |
| `RiskIndicatorV2` | LOW via `sourceUrl` | **FALSIFIED** — 0/200 rows | **EMPTY-FIELD** |
| `FAQEntry` | MEDIUM via `12366_qa_*` subset | NOT-PROBED-YET | (deferred to Phase 2) |
| `ComplianceRule` (L1) | MEDIUM via triangulation | NOT-PROBED-YET | (deferred to Phase 2) |
| `TaxIncentive` (L1) | HIGH (no source field) | NOT-PROBED-YET | (deferred to Phase 3) |
| `FilingForm` (L1) | HIGH (no source field) | NOT-PROBED-YET | (deferred to Phase 3) |
| `TaxRate*` family | HIGH (`code` internal) | NOT-PROBED-YET | (deferred to Phase 3) |
| `Industry*` family | HIGH (no source) | NOT-PROBED-YET | (deferred to Phase 3) |
| `IssuingBody`, `Region`, `TaxType` | N/A (source-side dimensions) | unchanged | — |

**Pattern (revised)**: V2 lineage's structural promise (`sourceUrl` column) is
not realized in data — the crawler pipeline declared the schema but never
wrote the URL. V1 LLM-extraction provenance fields (`source_doc_id`,
`extracted_by`) are similarly declared on `LegalDocument` but unpopulated.
The two paths that DO work are: (a) `LegalClause` ID-prefix parsing and
(b) `KnowledgeUnit.source_doc_id`. Everything else needs re-ingest or
upstream pipeline fix before any backfill is feasible.

---

## Backfill phasing (revised, post-probe)

**Phase 1 (LOW-cost CONFIRMED, ~50% coverage NOT 70%)**:
- `LegalClause` — parse `CL_*` prefix → registry of source documents (~30 distinct).
- `KnowledgeUnit` — chase `source_doc_id` → resolve to `Source` (~500-800 distinct source files).

That's it for confirmed LOW-cost. The 5 originally-claimed LOW paths are
either column-declared-but-empty (V2 sourceUrl) or column-declared-but-empty
(LegalDocument source_doc_id), and need upstream pipeline fix before backfill.

**Phase 2 (MEDIUM-cost; needs probe before commitment)**:
- `FAQEntry` — parse `12366_qa_*` prefix subset; rest stays NULL. Probe pending.
- `ComplianceRule` (L1) — triangulate three source fields (`source_doc_id`,
  `sourceClause`, `sourceRegulationId`). Probe pending — these may be empty
  too (LegalDocument's source_doc_id was, despite being declared).

**Phase 3 (HIGH-cost; upstream pipeline rewrite required, not "backfill")**:
- All originally-LOW V2 tables (ComplianceRuleV2 / FilingFormV2 / TaxIncentiveV2 /
  RiskIndicatorV2) — promoted from LOW to HIGH because `sourceUrl` is empty
  and there is no fallback pipeline output to derive from. Need to re-run the
  crawler with a writes-sourceUrl option, OR derive URL from external metadata.
- `LegalDocument` — promoted from LOW to HIGH for the same reason.
- `TaxIncentive` (L1, hash IDs) — unchanged.
- `FilingForm` (L1) — unchanged.
- `TaxRate*` family — unchanged.
- `Industry*` family — unchanged.

**Revised closure estimate**: Phase 1 alone closes ~50% of the source-attribution
gap (NOT ~70%). Phase 2 may add 5-10% if probes confirm field populated rates.
Phase 3 is the bulk of the work and depends on upstream pipeline rewrites that
were not visible from the design-time field enumeration.

---

## Open questions for Maurice

- [ ] **`source_type` enum closed or open?** Closed = strict ('crawler' | 'llm-extracted' | 'manual' | 'imported'). Open = free string. Strict is safer for analytics, open is friendlier for unforeseen ingest paths.
- [ ] **Backfill ordering**: do Phase 1 first (and ship F5 as ~70% closed), or hold for full Phase 1+2+3?
- [ ] **`_lineage_present` (B2) vs `source_id` (this draft)**: do we need both? Proposal: `_lineage_present` describes WHICH PIPELINE produced this row; `source_id` describes WHICH SOURCE DOCUMENT the fact came from. Different axes; both have value. But Maurice may want to consolidate.

---

Maurice | maurice_wen@proton.me
