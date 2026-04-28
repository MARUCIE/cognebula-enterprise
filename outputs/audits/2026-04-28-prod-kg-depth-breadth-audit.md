# Prod KG Depth × Breadth Quality Audit · 2026-04-28

> **Scope**: production knowledge graph at `100.88.170.57:8400` (368,910 nodes / 1,014,862 edges, contabo-eu).
> **Method**: 200-node-per-type sampling via `/api/v1/nodes` + falsification probes (direct schema introspection via `/api/v1/nodes` 404-list, code grep on `kg-api-server.py`, valid_tables enumeration).
> **Status after R2 swarm**: 4 findings stand · 2 framing errors retracted · 1 new finding promoted to top.

---

## Executive summary

1. **V2-table proliferation is the highest-leverage gap.** `TaxIncentiveV2`, `ComplianceRuleV2`, `FilingFormV2`, `RiskIndicatorV2` and similar coexist with their V1 ancestors. Each pair represents identity-vs-occurrence complecting at table level. Future ingestions will silently double-count unless consolidated.
2. **`/api/v1/admin/migrate-table` line 1708 (`props[field] = str(val)[:500]`)** is a single-line clamp that truncates every field to 500 chars during any migration through this endpoint. **LegalClause's 24/200 nodes hitting exactly 500 chars** is the visible artifact of a past migration through this path. Root-cause located, but **do NOT blind-back-out**: investigate Chesterton's fence first (embedding-API token limits, index bloat, historical OOM).
3. **KnowledgeUnit content is genuinely fragmented at storage layer** (200-sample mean 136, max 193, zero ≥ 500). `/api/v1/nodes` does NOT truncate (returns `dict(row[0])` directly), so this measurement reflects storage truth. Whether intentional or upstream-source-limited remains open.
4. **56 over-ceiling un-declared types** persist (93 live tables vs 31 declared in schema). Schema discipline gap.
5. **Source-attribution is broken for non-LegalClause types**: only `CL_*` IDs carry source semantics. Other tables use hash-style IDs without source attestation. No `Source` node, no `source_id` foreign key.

**Retracted from R1 framing**:
- ~~"KnowledgeFact and CPAKnowledge unreachable"~~ — these tables **do not exist** in the KG schema. Falsification probe confirmed via valid_tables enumeration (93 tables; neither name present). HTTP 404 was the correct response.
- ~~"LegalDocument zero content"~~ — LegalDocument is **metadata-only by schema design**. Actual fields: `name, type, issueDate, effectiveDate, jurisdiction_code, source_doc_id, source_paragraph, issuingBodyId, override_chain_id, supersedes_id, argument_links_to, ...`. Content lives in LegalClause by intentional decomposition.

---

## Methodology

### Probe stack
1. **API-layer sample** (`scripts/_lib/prod_kg_client.py.nodes(type, limit=200)`) for content length distribution per type
2. **Schema-validity probe** via `/api/v1/nodes?type=<X>` 404 response (returns full valid_tables list)
3. **Field enumeration** by inspecting raw response keys for representative nodes
4. **Code grep** on `kg-api-server.py` for `[:500]` / `substring` / truncation logic
5. **Endpoint behavior audit**: confirmed `/api/v1/nodes` returns `dict(row[0])` without truncation (lines 1020-1040); `/api/v1/search` applies `[:500]` for display rendering (lines 1123, 1140, 1154)

### Why falsification was non-optional
Round 1 of the depth+breadth swarm had Munger flag HIGH-risk confirmation bias: "you measured the API surface, not the data." Without falsification, the audit would have shipped a "re-ingest 369K nodes" recommendation when:
- 2 of 6 findings were schema-correct-by-design (not bugs)
- 1 finding was a 5-line specific bug (line 1708 clamp), not a 369K-node project
- 3 findings were genuinely structural

This is the same class of error Rev. 1 of the deep-system audit committed (treating `.demo` as production). Memory promoted 2026-04-28: "Swarm verdict 必须验证目标文件" applied here.

---

## Findings (post-falsification)

### F1 — V2-table proliferation (LEVERAGE POINT #4 — system structure)

**Symptoms**: at least 5 V2 tables in valid_tables list (`TaxIncentiveV2`, `ComplianceRuleV2`, `FilingFormV2`, `RiskIndicatorV2`, plus ones not yet enumerated). `RiskIndicatorV2` exists with no observed `RiskIndicatorV1` — naming inconsistency.

**Diagnosis (Hickey)**: schema-version was treated as PLACE, not VALUE. New schema → new table instead of new attribute on the same canonical entity. Datomic-thinking: facts accumulate, schemas attach as attributes. The current shape says "schemas are places."

**Inversion (Munger)**: V1+V2 separation is CORRECT when (a) V1 has live downstream consumers that cannot be migrated atomically, (b) V2 schema diverges semantically (not just renamed fields), (c) V2 is an experiment with rollback optionality. Consolidation instinct is WRONG when it forces a big-bang migration to satisfy aesthetics.

**Required next-round work**:
- Enumerate ALL V2 tables (current count ≥5, full count unknown)
- For each V1+V2 pair: classify as (i) renamed-field-only → consolidate, (ii) semantic-divergence → keep separate but document, (iii) experimental → set sunset criteria
- For accepted-separations: declare consolidation policy (when does V2 absorb V1) in schema docs

### F2 — `/api/v1/admin/migrate-table` line 1708 clamp (LEVERAGE POINT #10 — stock-flow)

**Code**: `props[field] = str(val)[:500]` — applied to every field of every node migrated through this endpoint.

**Visible damage**: LegalClause sample of 200 shows 24 nodes hitting exactly 500 chars (12% truncation tell). Past migrations through this code path froze at-most-500-char content into the canonical store.

**Chesterton's fence** (Munger): before removing, identify WHY the clamp was added. Hypotheses to falsify:
- Embedding-API token limits (Poe / Gemini have token caps per chunk)
- Kuzu STRING column index limits (Kuzu schema may have implicit max sizes for index columns)
- Historical OOM during large-batch migration
- Defensive coding from an unrelated incident

**Required next-round work**:
- `git log -p` on line 1708's birth commit + neighborhood
- Audit migrate-table call sites (which tables migrated through this path historically)
- For migrations where source data exceeds 500 chars: assess re-migration cost from `source_doc_id` reference if still resolvable
- Choose: raise to 4000 (safe-margin), parametrize per-field, or remove with per-field replacement

### F3 — KnowledgeUnit content fragmentation (LEVERAGE POINT #12 — parameter)

**Storage-layer truth**: 200-node sample mean 136 chars, max 193, 0 nodes ≥ 500. Confirmed via `/api/v1/nodes` which does not truncate.

**Open question**: is this fragmentation (a) intentional design (one-fact-per-node), (b) upstream-source-limited (the crawler split source documents into chunks at ingest), or (c) accidental?

**Required next-round work**:
- Identify the ingest path that creates KnowledgeUnit nodes
- Inspect 5-10 nodes whose `source_doc_id` (if present) points to a known chinatax / chinaacc article
- Compare KnowledgeUnit content vs the original source paragraph length
- Decision tree: (a) intentional → document the design and stop calling it "fragmentation"; (b) upstream-limited → discuss with crawler owner; (c) accidental → identify the truncation site

### F4 — Schema-vs-runtime drift (LEVERAGE POINT #5 — rules)

**Numbers**: 93 live tables in production vs 31 declared in `ontology` schema definitions. Drift = 62 tables.

**Diagnosis**: ingest pipeline lacks a schema-validation gate. New tables can be created via DDL during ad-hoc migrations without updating the declared ontology. The schema is being treated as documentation, not as a runtime contract.

**Hickey reframe**: schema-as-value vs schema-as-place. Currently a place that gets mutated by writes; should be a value the system holds and validates against.

**Required next-round work**:
- Enumerate the 62 undeclared live tables
- Classify each as (i) legitimate-but-undeclared → add to schema, (ii) experimental → mark as `_experimental` namespace, (iii) abandoned → mark for sunset
- Add schema-validation gate to `/api/v1/admin/execute-ddl` and `/api/v1/admin/migrate-table` so new tables require declared schema entry

### F5 — Source attribution gap (LEVERAGE POINT #6 — information flow)

**Symptoms**: only LegalClause uses semantic IDs (`CL_*`). Other tables use hash-style auto-generated IDs with no `source_id` field. No `Source` node type exists in valid_tables list.

**Consequence**: KG cannot answer "where did this fact come from?" for the majority of nodes. Lineage and recall trust both depend on source resolvability.

**Required next-round work**:
- Declare `Source` node type with `(id, label, url, ingest_ts, ingest_pipeline)` schema
- Add `source_id` foreign key to KnowledgeUnit, FAQEntry, TaxRate, TaxIncentive, etc.
- Backfill `source_id` for existing nodes where a deterministic mapping exists (e.g., LegalClause `CL_*` already encodes source; KnowledgeUnit may have `source_doc_id` already; FAQEntry may have `12366_qa_*` prefix on subset)

---

## Leverage ranking (Meadows axis, post-R2 consensus)

| Rank | Finding | Meadows LP # | Why this rank |
|------|---------|--------------|---------------|
| 1 | F1 — V2 proliferation consolidation | #4 (system structure) | Active divergence loop without balancing arm; bifurcates ontology |
| 2 | F2 — migrate-table [:500] back-out (with Chesterton check) | #10 (stock-flow) | Active corruption mechanism; future migrations still lossy |
| 3 | F4 — schema-runtime drift gate | #5 (rules) | Generates F1 and re-generates F4 on each new ingest |
| 4 | F5 — source-attribution gate | #6 (info flow) | Quality observability prerequisite |
| 5 | F3 — KU fragmentation | #12 (parameter) | Lowest leverage but highest visible-symptom — fix only after F1-F4 to avoid stacking interventions |

---

## Complection map (Hickey axis, post-R2 consensus)

1. **Identity-vs-occurrence at TABLE level** (V2 proliferation) — schema version braided with table identity
2. **Migration mechanism braided with data semantics** (line 1708) — transport opinions about "how much" belong in schemas, not in `migrate-table`
3. **Schema-as-place** (run-time drift) — declared and live diverge because schema is a place, not a value

R1's "content-role split" complection (preview/summary/body) was retracted in R2 — LegalDocument-as-metadata + LegalClause-as-content is actually correct values-vs-places thinking, and the original framing was mis-reading.

---

## Inversion checklist for next round (Munger axis)

Before ANY remediation work begins, the next-round queue must:
- [ ] Pendulum-bias check: 2 R1 findings died; do NOT under-weight the 3 surviving findings as compensation
- [ ] Chesterton's fence on line 1708: locate the rationale (git blame + commit message + slack/issue archeology) before changing the clamp
- [ ] Chesterton's fence on V2 separation: classify each pair before consolidating; some V2s may have legitimate downstream consumers
- [ ] Sample-size question: the 200-node-per-type sampling has 0.054% coverage on KU; for actions touching > 1000 nodes, run a stratified random 1000-sample re-probe before acting
- [ ] API-vs-storage discipline: every numeric finding must declare which layer it measured

---

## Synthesis target for next-round queue

Per Hickey R3: when the next-round atomic queue picks up this audit, it should sequence under one composite target —

> **Treat schema-version as a value attached to a single canonical entity, and make migration a pure identity-preserving function.**

This binds F1 (V2 consolidation) and F2 (migrate-table de-truncation) into one design intent rather than two parallel cleanup streams. F4 (schema-runtime drift gate) becomes the enforcement mechanism for that intent. F3 and F5 sequence after.

---

## What this audit does NOT do

- Does not propose specific table-consolidation patches for F1
- Does not change line 1708 — pre-change rationale audit required
- Does not re-ingest any data
- Does not declare success/failure on the prior `.demo`/Rev. 4 audit findings — those covered different surface
- Does not estimate remediation timelines (depends on Chesterton outcomes)

The audit's job is to ship the **corrected framing**. Remediation is a separate atomic queue that sequences after this framing ships.

---

## Trace

Swarm protocol: 3 advisors × 2 rounds dispatched, R3 final ship verification pending on this deliverable. Trace artifact: `outputs/reports/auto-swarm-trace/2026-04-28-prod-kg-depth-breadth-audit.md` (to be written on R3 ship).

Round 1: 3/3 REVISE (Meadows leverage / Hickey complecting / Munger inversion-with-HIGH-risk).
Round 2: 2/3 REVISE on R1-as-shipped + 1/3 APPROVE-MEDIUM on R2-corrected framing.
Falsification probes between R1 and R2 invalidated 2 of 6 R1 findings, located 1 root cause, surfaced 1 new finding.

---

Maurice | maurice_wen@proton.me
