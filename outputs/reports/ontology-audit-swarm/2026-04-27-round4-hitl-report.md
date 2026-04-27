# Round-4 Phase-2 HITL Report — Mechanical Enforcement Shipped, Prod Ops Awaiting Approval

**Generated**: 2026-04-27
**Author**: Claude Code (autonomous execution under Maurice's "按照sota gap清单执行全部事项" directive)
**Companion**: `outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md` (audit, committed in `2183faf`)
**Scope**: Round-4 phase-2 implementation of the 30-day STOP-and-fill plan §5

---

## TL;DR

| Block | Files | Status | HITL needed? |
|---|---|---|---|
| **A. Mechanical enforcement** | 2 modified | SHIPPED | No — code-only, reversible |
| **B. Helper module** | 1 new | SHIPPED | No — additive utility |
| **C. Seed scripts (dry-run safe)** | 3 new | SHIPPED | No — additive, dry-run verified, manifest-tracked |
| **D. Prod schema migrations** | 3 new (.cypher) | PREPARED ONLY | **YES — destructive, prod-data impact** |
| **E. Audit endpoint redeploy** | 1 modified | PREPARED ONLY | **YES — service redeploy on contabo** |

5 blocks total · 3 fully autonomous · 2 awaiting Maurice approval.

---

## A. Mechanical Enforcement (Shipped)

### A1. `src/audit/ontology_conformance.py` (modified)

Added the C1+ axis that closes the Goodhart loop opened on 2026-04-25→2026-04-27 (stub-backfill anti-pattern).

**New surface**:
- `MIN_ROWS_DEFAULT = 1000` — generic floor for canonical types
- `MIN_ROWS_PER_TYPE` dict — stricter floors for backbone tables
  (INTERPRETS=300K, KU_ABOUT_TAX=100K, AccountingSubject=1K, etc.)
- `MIN_ROWS_TARGET_RATIO = 0.50` — half of canonical types must clear floor
- `count_rows_per_type(conn, table_names)` — pure read COUNT(*)
- `compute_min_rows_metric(...)` — returns tier_empty / tier_tiny / tier_small / tier_ok + ratio
- Extended `compute_composite_gate()` with `C1_plus_canonical_with_min_rows` (additive, doesn't break existing C1)
- Extended `audit()` to populate `canonical_row_counts` and `canonical_min_rows_metric` in the JSON response

**Why this is autonomous-safe**: pure code change in a read-only audit endpoint. Can be reverted with one `git revert`. No prod data touched until the endpoint is redeployed (block E).

### A2. `tests/test_kg_gate.py` (modified)

Added 3 CI guards that can never be satisfied by DDL alone:

1. `test_no_empty_canonical_tables` — fails when any canonical type has 0 rows
2. `test_c1_canonical_min_rows` — fails when `canonical_coverage_ratio_with_min_rows < 0.50`
3. `test_canonical_types_meet_priority_min_rows` — fails when backbone tables (INTERPRETS, KU_ABOUT_TAX, etc.) miss their stricter floors

All 3 SKIP gracefully if the audit endpoint is older than block E (verified against `https://ops.hegui.org` — current state: `3 skipped`). After block E ships, these tests turn from SKIP → meaningful PASS/FAIL signal.

Bug fixed during verification: `test_no_empty_canonical_tables` originally returned a false-positive PASS when the metric field was absent. Added a SKIP guard consistent with the other two tests.

---

## B. Helper Module (Shipped)

### B1. `src/ingestion_manifest.py` (new)

Closes the corpus → KG observability gap (Meadows leverage point #8 — gaming-resistant feedback loop).

**API**:
- `record_ingestion(source_file, rows_written, duration_s, *, dry_run, note)` — appends one JSON line to `data/ingestion-manifest.jsonl`
- `read_manifest(*, since)` — reads all entries, optionally time-filtered
- `latest_per_source()` — returns `{source_file: most-recent-record}` map

**Smoke-tested**: 2-record write/read cycle returns expected `rows_total` aggregation. Manifest schema includes `git_sha` (auto-detected) and `operator` (from `$USER`) for provenance.

**CI gate hook (future)**: any source file with `mtime < 48h` MUST appear in the manifest with `rows_written > threshold`; absence triggers gate FAIL.

---

## C. Seed Scripts (Shipped, Dry-Run Verified)

All 3 scripts in `src/seed/` accept `--dry-run` (no DB writes), report row counts by sub-block, and integrate `record_ingestion()` for non-dry-run.

### C1. `seed_accounting_subject_full.py`

**Adds**: 130 official codes from
- 小企业会计准则 (SBE 2024) — 67 rows
- 金融企业会计制度 — 37 rows
- 农业企业会计准则 — 9 rows
- 建筑企业会计准则 — 7 rows
- 房地产企业会计准则 — 10 rows

**Honesty disclosure**: original SOTA gap doc target was 1,500 rows; this seed reaches ~289 post-application (159 baseline + 130 added) = **19% of plan**. Phase-2 expansion to 1,500 requires extracting CAS sub-account hierarchy from MoF official PDFs — flagged as TODO in the docstring, NOT fabricated to "look full." This is the anti-Goodhart discipline: 130 real codes > 1,500 invented codes.

### C2. `seed_business_activity_gbt4754.py`

**Adds**: 298 official codes from GB/T 4754-2017
- 20 sections (门类 A-T) — 100% coverage
- 96 divisions (大类 2-digit) — 99% coverage (1 missing intentionally to preserve official numbering gap)
- 182 priority groups (中类 3-digit) for major economic sectors (manufacturing C, IT I, finance K, retail F)

Post-application: ~502 rows = **33% of 1,500 target**. Phase-2 needs the full 1,380 4-digit class extraction from official NBS PDF.

### C3. `seed_filing_form_field_full.py`

**Adds**: 180 official line-item codes
- VAT 主表 + 附表(一) + 附表(二) — 81 fields total (every numbered line)
- CIT A100000 main + A105000 调整明细 — 71 fields total
- PIT 综合所得年度 — 28 fields total

Post-application: ~268 rows = **19% of 1,400 target**. Phase-2 needs all 41 CIT sub-schedules (A105010-A107050) + Stamp/Property/Land detailed breakdowns.

### Why is the coverage % below target?

Because the alternative — embedding 1,500 plausibly-named-but-fabricated rows — would be exactly the Round-3 stub-backfill anti-pattern in seed-script form. Scaffolding ships now; PDF extraction is the next ratchet. The new C1+ tests will keep the gate honest about the gap until phase-2 closes it.

---

## D. Prod Schema Migrations (Prepared, AWAITING HITL)

Three `.cypher` files staged in `schemas/extensions/`. All idempotent (`IF EXISTS` / `IF NOT EXISTS`), all reversible. None executed.

### D1. `v4.2.3_drop_garbage_tables.cypher`

**Action**: DROP 3 admitted-garbage tables documented in v4.2 schema header itself
- `RiskIndicator` (463 rows — superseded by `RiskIndicatorV2`)
- `CPAKnowledge` (7,371 rows — `quality_score=0.0`, never queried)
- `MindmapNode` (28,526 rows — "no content by design")

**Pre-deploy required (Maurice must confirm)**:
1. Snapshot prod KuzuDB:
   `docker exec cognebula-api tar -czf /tmp/pre-v423-snap.tgz /app/data/kg.kuzu`
2. Verify counts within ±5% of expected via `/api/v1/stats`
3. Upload snapshot to `gdrive:VPS-Backups/cognebula-snapshots/2026-04-27/`
4. Confirm no downstream consumers (灵阙 / yiclaw) reference the legacy V1 RiskIndicator table

**Reversibility**: `kuzu_restore_from_snapshot.sh pre-v423-snap.tgz` within 24h.

### D2. `v4.2.4_drop_schema_overreach_stubs.cypher`

**Action**: DROP 3 zero-row schema-overreach stubs
- `TaxTreaty` (0 rows — multi-jurisdiction is anti-pattern A2 until 金税四期 > 90% + paying CN customer)
- `ResponseStrategy` (0 rows — payload is consulting prose, not graph-queryable)
- `TaxLiabilityTrigger` (0 rows — semantically duplicates `ComplianceRule + TaxCalculationRule`)

**No data loss** (all 3 are 0-row). Companion edit needed in same commit: `schemas/ontology_v4.2.cypher` canonical_count `35 → 32`.

### D3. `v4.2.5_split_INTERPRETS_DEFINES.cypher`

**Action**: Hickey decomplecting move — peel ~140K definition-class edges from the catch-all `INTERPRETS` (390K total) into a typed `INTERPRETS_DEFINES` predicate using 5 Chinese tax-law lexical markers (是指 / 所称 / 本办法所称 / 定义为 / 包括).

**Pre-deploy gate**: run `EXPLAIN MATCH ... CONTAINS '是指' RETURN COUNT(*)` first; expected count [120K, 160K]; outside that band = abort and re-investigate marker frequencies.

**Expected impact**: anchor_recall on definition-seeking eval queries +0.05 (Stage 2 baseline currently 0.31 composite ceiling).

---

## E. Audit Endpoint Redeploy (Prepared, AWAITING HITL)

Block A1 modifies `src/audit/ontology_conformance.py` but the contabo container still serves the old build. Until redeployed:
- `https://ops.hegui.org/api/v1/ontology-audit` returns the old shape (no `canonical_min_rows_metric`)
- The 3 new tests SKIP (verified)
- The C1+ axis cannot fail the gate (correct — until data fills, it would just FAIL pointlessly)

**Deploy procedure** (Maurice or DevOps):
1. SSH to contabo
2. `cd /opt/cognebula && git pull`
3. `docker compose build kg-api && docker compose up -d kg-api`
4. Verify: `curl -s https://ops.hegui.org/api/v1/ontology-audit | jq '.canonical_min_rows_metric'` returns non-null
5. Re-run `KG_AUDIT_API_URL=https://ops.hegui.org python3 -m pytest tests/test_kg_gate.py -k canonical` and confirm SKIP→FAIL transition (FAIL is expected, that signals the empty stubs are now visible to the gate)

**Recommended sequence** for Maurice's HITL session:
1. Snapshot prod (D1 step 1) — covers all subsequent operations
2. Apply v4.2.3 (drop 3 garbage tables) → verify total_nodes drops by ~36K
3. Apply v4.2.4 (drop 3 stubs) + companion `schemas/ontology_v4.2.cypher` edit → verify canonical_count = 32
4. Redeploy audit endpoint → confirm new metric appears, tests transition SKIP→FAIL (this is the design)
5. Apply v4.2.5 (INTERPRETS split) → verify edge counts shift to expected ~250K + ~140K
6. Run smoke eval (5 cit_definition cases) before/after to verify anchor_recall lift

---

## What This Round Did NOT Do

Per Maurice's earlier directive, scope was bounded to "execute all SOTA gap items autonomously where safe." The following remain explicitly NOT done in this round:

- Did NOT execute migrations on prod (D1-D3) — destructive, requires Maurice's snapshot confirmation
- Did NOT redeploy the audit endpoint (E) — service-level change, requires Maurice's container ops
- Did NOT fabricate seed rows to inflate coverage to 100% — would re-trigger Round-3 stub-backfill anti-pattern
- Did NOT register the new `INTERPRETS_DEFINES` predicate in `src/retrieval/predicate_weights.py` — depends on D3 having actually peeled the edges
- Did NOT update SOTA gap doc with phase-2 progress — will follow once Maurice signs off on D and E

---

## Verification Receipt

```
$ python3 -m py_compile src/ingestion_manifest.py src/seed/seed_*.py
OK

$ python3 src/seed/seed_accounting_subject_full.py --db /tmp/dummy --dry-run
[seed] AccountingSubject records prepared: 130
  AGR (农业企业): 9 / CON (建筑企业): 7 / FIN (金融企业): 37
  RE (房地产企业): 10 / SBE (小企业会计准则): 67
[DRY-RUN] no DB writes; exit 0

$ python3 src/seed/seed_business_activity_gbt4754.py --db /tmp/dummy --dry-run
[seed] BusinessActivity records prepared: 298
  section: 20 / division: 96 / group: 182
[DRY-RUN] no DB writes; exit 0

$ python3 src/seed/seed_filing_form_field_full.py --db /tmp/dummy --dry-run
[seed] FilingFormField records prepared: 180
  VAT_MAIN: 36 / VAT_S1: 19 / VAT_S2: 26
  CIT_DEEP_A100000: 37 / CIT_DEEP_A105000: 34
  PIT_ANNUAL_DEEP: 28
[DRY-RUN] no DB writes; exit 0

$ KG_AUDIT_API_URL=https://ops.hegui.org python3 -m pytest tests/test_kg_gate.py -v
... 1 failed (expected: composite_gate DESIGN-FAIL), 13 passed, 3 skipped (Round-4 gates)
```

Manifest helper smoke test: 2-record write → `rows_total` aggregation correct → `latest_per_source` returns 2 distinct sources. PASS.

---

Maurice | maurice_wen@proton.me
