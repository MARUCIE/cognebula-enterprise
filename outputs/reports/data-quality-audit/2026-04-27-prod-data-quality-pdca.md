# Data Quality Audit — PDCA Delivery (2026-04-27)

**Scope**: 31 canonical types in PROD KuzuDB (`https://ops.hegui.org`), 2053 sampled rows.
**Pipeline**: existing `src/audit/data_quality_survey.py` extended +1 dimension this turn.
**Verdict**: STRUCTURAL FAIL on lineage envelope (4/5 critical columns 100% NULL across all 31 canonical types). Global `defect_rate=0.0697 ≤ 0.10` is an arithmetic PASS, not a structural one — large-sample types dilute the per-type-FAIL signal in the global average. 11/29 populated types FAIL the per-type threshold.

---

## P (Plan) — what we audited and how

### Inventory

- **31 canonical types** declared in `schemas/ontology_v4.2.cypher`
- **2053 rows** sampled (per-type cap = 100, smaller-cardinality types fully covered)
- **2 types fully empty** (`PolicyChange`, `TaxItem`) — fetch_misses
- **5 critical lineage columns** evaluated per row (`effective_from`, `confidence`, `source_doc_id`, `jurisdiction_code`, `jurisdiction_scope`)

### Gate dimensions before this turn (8)

| # | Dimension | Threshold |
|---|-----------|-----------|
| 1 | duplicate_id_count | per-row, count duplicates beyond first |
| 2 | stale_count | `effective_from` older than 10 years |
| 3 | integrity_violations | `reviewed_at` XOR `reviewed_by` |
| 4 | jurisdiction_mismatches | unknown scope OR XOR(code, scope) |
| 5 | prohibited_role_count | `analogy` role on tax nodes |
| 6 | invalid_chain_count | `override_chain_id` not in whitelist |
| 7 | inconsistent_scope_count | code+scope co-variance whitelist |
| 8 | null_rate (REPORTED but NOT counted in defects_total) — the gap |

### Gap identified

`null_rate` was computed per critical column and **rendered in the report**, but never rolled into `defects_total`. A column with 100% NULL across the entire sample produced 0 defect units. The verdict therefore could not see systematic absence — only per-row anomalies.

---

## D (Do) — what we ran

### Run 1 — baseline (8 dimensions only)

```
python scripts/data_quality_survey_via_api.py --sample 100 \
  --output outputs/reports/data-quality-audit/2026-04-27-prod-survey.json
```

**Result**: `defect_rate=0.0000  verdict=PASS  defects=0/2053`

This is the misleading verdict. The data is broken; the gate doesn't see it.

### Code change — extend gate (+1 dimension)

`src/audit/data_quality_survey.py`:

- New constant `DEFAULT_NULL_COVERAGE_THRESHOLD = 0.50`
- New parameter `null_coverage_threshold` on `survey_type()` and `survey()`
- New defect dimension `null_coverage_violation_count` = number of CRITICAL_COLUMNS where per-column `null_rate >= threshold`
- New report fields `null_coverage_violations` (list[str], the offending columns) and `null_coverage_threshold`
- Empty samples (sampled == 0) bypass — missing tables are reported via `fetch_misses`, not double-counted as 5 NULL defects
- `defects_total` now sums all 8 prior categories + `null_coverage_violation_count`

`tests/test_data_quality_survey.py`:

- New class `TestNullCoverageViolations` with 8 tests covering:
  threshold semantics (default, custom, disabled at 1.0+), boundary at exactly 50%,
  100%-NULL single-column case, all-cols-filled clean case, empty-sample no-phantom case,
  defects_total integration
- Updated 4 legacy tests in `TestCompoundDefects` and `TestSurveyOrchestration`
  whose fixtures relied on absent critical columns; now either pass `null_coverage_threshold=1.01`
  to disable, or fixtures fully populate critical columns
- Pre-extension: 45 tests passing
- Post-extension: 53 tests passing (45 legacy + 8 new)

### Run 2 — with NULL-coverage gate enabled

```
python scripts/data_quality_survey_via_api.py --sample 100 \
  --output outputs/reports/data-quality-audit/2026-04-27-prod-survey-v2.json
```

**Result**: `defect_rate=0.0697  verdict=PASS  defects=143/2053`

Overall PASS at target 0.10, but per-type breakdown reveals the real story.

---

## C (Check) — findings

### Finding 1 — the overall verdict still hides the per-type failures

Global `defect_rate=0.0697 PASS` is correct given the target 0.10, but it **averages over 31 types**. The big types (sample 100) absorb most of the 5-NULL hit into their denominator and pass; the small bounded-cardinality types (sample 14-45) get amplified to 0.11-0.36 and fail.

### Finding 2 — 11/29 populated types FAIL the same per-type threshold

| Rank | Type | Sample | Defects | Defect rate | Cause |
|------|------|--------|---------|-------------|-------|
| 1 | FilingForm | 14 | 5 | 0.357 | All 5 critical cols ≥50% NULL |
| 2 | TaxEntity | 17 | 5 | 0.294 | All 5 critical cols ≥50% NULL |
| 3 | TaxType | 19 | 5 | 0.263 | All 5 critical cols ≥50% NULL |
| 4 | JournalEntryTemplate | 20 | 5 | 0.250 | All 5 critical cols ≥50% NULL |
| 5 | TaxBasis | 20 | 5 | 0.250 | All 5 critical cols ≥50% NULL |
| 6 | TaxMilestoneEvent | 20 | 5 | 0.250 | All 5 critical cols ≥50% NULL |
| 7 | DeductionRule | 25 | 5 | 0.200 | All 5 critical cols ≥50% NULL |
| 8 | FinancialIndicator | 32 | 5 | 0.156 | All 5 critical cols ≥50% NULL |
| 9 | InvoiceRule | 40 | 5 | 0.125 | All 5 critical cols ≥50% NULL |
| 10 | AccountingStandard | 43 | 5 | 0.116 | All 5 critical cols ≥50% NULL |
| 11 | IndustryBenchmark | 45 | 5 | 0.111 | All 5 critical cols ≥50% NULL |

Same pattern for all 11: every critical lineage column is missing across the entire sample. This is structural, not anecdotal — the seed pipelines that populated these types (Q1 batch + reference seed split + GBT4754 BusinessActivity etc.) never carried lineage envelope data, only domain fields. **Positive exception**: `KnowledgeUnit` + `LegalClause` (legal backbone) have `source_doc_id` populated — only 4 NULL violations rather than 5 — indicating attribution work began on backbone types. The other 4 columns (`effective_from`, `confidence`, `jurisdiction_code`, `jurisdiction_scope`) remain 100% NULL across all 31 canonical types.

### Finding 3 — non-NULL defect categories are clean

Across all 2053 sampled rows:

- duplicate_id_count: 0
- stale_count: 0 (no row has `effective_from` to be stale against)
- integrity_violations: 0
- jurisdiction_mismatches: 0
- prohibited_role_count: 0
- invalid_chain_count: 0
- inconsistent_scope_count: 0

Per-row data quality is OK. The defect is structural NULL coverage, not row-level errors.

---

## A (Act) — prioritized remediation queue

### P0 — gate extension (DONE this turn)

Closed in this commit set. NULL-coverage now contributes to `defects_total`, surfaces as `null_coverage_violations` array, and is covered by 8 new pytest cases. The gate is honest.

### P1 — `effective_from` backfill + Goodhart guard (HIGH)

Affects 11 FAIL-level types. Per Round-1 Munger inversion the **guard precedes the backfill**:

1. **Placeholder banlist** (gate-side): `source_doc_id` and similar lineage strings must NOT be in the banned set `{'unknown', 'TBD', 'todo', 'default', 'N/A', ''}`. Match must be **case-insensitive + whitespace-stripped** so variants like `'Unknown'`, `'  '`, `' default '` also trigger — closes the Round-2 Munger same-name-variant bypass. Add to existing data-quality survey as a 10th defect dimension before any P1 backfill runs — otherwise backfill could flip null_rate green via placeholder strings without real attribution.
2. **Seed-derived rows**: backfill from JSON source `effectiveDate` field where present (SocialInsuranceRule and several others have it).
3. **Q1 batch with no source date**: use real date `2024-01-01` AND introduce a separate enum column `effective_from_source: enum('source', 'seed_default', 'extracted')`. Use enum, not string, so the placeholder banlist doesn't false-positive on legitimate defaults.

Estimated work: 2-3 hours scripted (additive UPDATE batches via wrapper).

### P1.5 — `jurisdiction_code/scope` derive-from-prefix default (AUTO, opt-out)

**Downgraded HITL → AUTO per Round-1 Munger + Autonomous Extension rule.** Sane defaults exist; permission-asking would be a violation.

Derivation rules:
1. `id` contains `CN-FTZ-*` → `scope=experimental_zone`, `code=<prefix>`
2. `id` contains ISO admin (`CN-31`, `CN-HK`, etc.) → `scope=subnational`, `code=<as-is>`
3. Otherwise → `code=CN`, `scope=national`

All derived rows mark `jurisdiction_source='derived'`. Maurice reviews only the exception subset (expected <5 types where defaults are wrong), does not block the default path.

Estimated work: 1-2 hours scripted.

### P3 — `source_doc_id` / `confidence` backfill (MEDIUM)

`source_doc_id`: for seed-derived rows can use the source JSON path as a `seed:filename` URI scheme. For extracted rows already use `source_file` field — needs mapping to `source_doc_id`. Approximate work 4-6 hours.

`confidence`: for hand-curated seed data 0.95 default; for extracted data populate from extraction confidence. Approximate work 2 hours.

### P4 — extend gate with cross-table referential integrity (FUTURE)

Add a 10th defect dimension: `orphan_fk_count` = rows where a foreign-key field (e.g. `taxTypeId`, `scenarioId`, `regionId`) does not resolve to an existing target. Estimated work 4-6 hours, becomes a real consumer-side gate for yiclaw / 灵阙.

---

## Swarm consensus (Round 1 → 2 patches applied)

Round 1 dispatched 3 advisors (Hara · Hickey · Munger) in parallel. Verdict: 1 APPROVE-as-is (Hickey, with deferred suggestion), 1 PRUNE (Hara), 1 REQUEST_CHANGES (Munger). Patches applied below in this turn:

- **Verdict reframe** (3/3 consensus): pill changed from amber `PASS / 11 FAIL` to red `STRUCTURAL FAIL · 4 cols 100% NULL` with secondary muted line clarifying the global PASS is arithmetic. KPI #4 swapped from `0.0697 PASS` to `4/5 100%-NULL columns`. Closes the anchoring bias Munger flagged.
- **Finding compression** (Hara): old Finding 3 (KnowledgeUnit/LegalClause partial-lineage signal) merged into Finding 2 trailing sentence; old Finding 4 renumbered to Finding 3. Net −1 subsection.
- **P1 Goodhart guard** (Munger): banlist constraint inlined ahead of backfill; `effective_from_source` typed as enum (not string) to defuse placeholder banlist false-positives.
- **P2 → P1.5 AUTO** (Munger + autonomous-extension rule): jurisdiction defaults are derive-from-prefix opt-out, not HITL opt-in. Maurice reviews exception subset only.
- **Swarm section compressed** (Hara · 2/3 majority): 3 advisor blockquotes replaced by 2-line action-item summary. The advisor names are not the findings; the findings are in §C.

Hickey's deferred patch (auto-generate the §C Finding 2 11-row table from `prod-survey-v2.json` instead of hand-typing) is acknowledged but **not in scope this turn** — adding a render script for one table is over-engineering for a single deliverable; revisit when ≥2 reports need the same projection.

Round 2 verification: see `outputs/reports/auto-swarm-trace/2026-04-27-data-quality-pdca-visual-review.md`.

---

## Reproducibility

Re-run baseline + extended in 90s total:

```
cd /Users/mauricewen/Projects/27-cognebula-enterprise
python -m pytest tests/test_data_quality_survey.py -v        # 53 tests
python scripts/data_quality_survey_via_api.py --sample 100   # 31 types × 100 rows
```

Reversibility: gate extension is value-additive (new field, no removed field) — downstream consumers reading the report dict will see new keys but no missing keys. No PROD mutation occurred.

---

Maurice | maurice_wen@proton.me
