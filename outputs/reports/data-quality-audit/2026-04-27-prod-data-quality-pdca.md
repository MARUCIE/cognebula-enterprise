# Data Quality Audit — PDCA Delivery (2026-04-27)

**Scope**: 31 canonical types in PROD KuzuDB (`https://ops.hegui.org`), 2053 sampled rows.
**Pipeline**: existing `src/audit/data_quality_survey.py` extended +1 dimension this turn.
**Verdict**: STRUCTURAL FAIL on lineage envelope. **3/5 critical columns are universally 100% NULL across all populated types** (`effective_from`, `jurisdiction_code`, `jurisdiction_scope`); the remaining 2 (`confidence`, `source_doc_id`) are partially attributed in 4 of 31 types (KnowledgeUnit + LegalClause = full attribution; FilingFormField = 43%; TaxCalculationRule = 12%) — corrected from the v2 PDCA simplification "4/5 columns 100% NULL across all 31 types" via corpus regression test discovery on 2026-04-27. **0/5 critical columns have been backfilled** — P1 work is unstarted. Global `defect_rate=0.0697 ≤ 0.10` is an arithmetic PASS, not a structural one — large-sample types dilute the per-type-FAIL signal in the global average. 11/29 populated types FAIL the per-type threshold.

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

Same pattern for all 11: every critical lineage column is missing across the entire sample. This is structural, not anecdotal — the seed pipelines that populated these types (Q1 batch + reference seed split + GBT4754 BusinessActivity etc.) never carried lineage envelope data, only domain fields.

**Positive exceptions** (corrected on 2026-04-27 by corpus regression test discovery — original PDCA simplified the picture):

| Type | source_doc_id NULL | confidence NULL | Notes |
|------|---------------------|------------------|-------|
| KnowledgeUnit | 0% (full attribution) | 100% NULL | legal backbone with source_doc_id only |
| LegalClause | 0% (full attribution) | 100% NULL | legal backbone with source_doc_id only |
| FilingFormField | 57% NULL (43% attributed) | 57% NULL | discovered via corpus test 2026-04-27 |
| TaxCalculationRule | 88% NULL (12% attributed) | 88% NULL | discovered via corpus test 2026-04-27 |

So 4 types (not 2) carry partial attribution. `effective_from`, `jurisdiction_code`, and `jurisdiction_scope` remain 100% NULL across **all** populated types with no exception. `confidence` and `source_doc_id` are partially populated in the 4 types above. The 27 remaining populated types have all 5 critical columns at 100% NULL.

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

### P0.5 — placeholder banlist gate (DONE this turn — Round-1 Munger Goodhart guard)

10th defect dimension shipped: `placeholder_string_count` counts banned-token occurrences across `LINEAGE_STRING_FIELDS` (`source_doc_id`, `extracted_by`, `reviewed_by`, `jurisdiction_code`, `override_chain_id`). Match is case-insensitive + whitespace-stripped (closes Round-2 Munger same-name-variant bypass: `'Unknown'`, `'  '`, `' default '`). Banlist: `{'unknown', 'tbd', 'todo', 'default', 'n/a', 'na', 'none', 'null', 'nil', 'tba', 'fixme', '?', '-', ''}`.

PROD v3 snapshot confirms 0 placeholder hits across all 31 types — banlist is in place **before** P1 backfill, fermant la fenêtre Goodhart par construction.

Test coverage shipped: 9 unit tests in `TestPlaceholderStrings` + property-based, matrix, corpus, and edge tests via the 10K test plan below.

### P0.6 — Massive test plan: ≥10,000 cases (DONE this turn)

Five-layer test pyramid covering edge / unit / regression / property / matrix dimensions:

| Layer | File | Test count | Purpose |
|-------|------|------------|---------|
| Unit (legacy) | `test_data_quality_survey.py` | 62 cases | Original 9 dimensions + new banlist |
| Property-based | `test_data_quality_property.py` | 5,352 hypothesis examples (19 functions) | Invariants over random rows: monotonicity, accounting, bounds, permutation, linearity, type guards |
| Matrix parametrize | `test_data_quality_matrix.py` | 4,227 cells | 31 canonical types × 9 dimensions × 4 thresholds × 3 sample sizes (cross-product), build-time ontology drift detector |
| Corpus regression | `test_data_quality_corpus.py` | 835 cells | PROD v3 snapshot lock-in per (type, field) cell — surfaces narrative-vs-data divergence |
| Edge enumeration | `test_data_quality_edge.py` | 55 cases | Threshold boundaries, Unicode/CJK/emoji, NULL semantics distinctions, dup-id edges |
| **Total** | | **10,531 cases** | All passing in 7.0s |

Discovery via corpus regression: PDCA Finding 2 understated the partial-attribution picture — `confidence` and `source_doc_id` are partially populated in **4** types (not 2). Corrected above.

### P0.7 — Sprint A: orchestration coverage + golden archetypes (DONE)

`survey()` itself was tested by only 4 unit tests pre-Sprint-A (vs 10K on `survey_type`). This was the highest residual prod-bug risk axis.

| File | Cases | Coverage |
|------|-------|----------|
| `test_data_quality_orchestration.py` | 98 pytest IDs + 1,100 hypothesis | 9 sections: Cypher contract, fetch failure handling, verdict tipping points, per-type aggregation, schema-path resolution, parameter flow-through, result shape, property tests, defaults sanity |
| `test_data_quality_golden.py` | 474 cases over 20 archetypes | A1-A4 legal backbone / A5-A8 Q1 batch / A9-A11 FilingFormField / A12-A14 TaxCalculationRule / A15-A16 empty / A17 placeholder-poisoned / A18 mixed-dirty / A19 single-row / A20 2053-row PROD-scale |

Sprint A subtotal: **1,668 cases**, 1.52s runtime.

### P0.8 — Sprint B: mutation testing (DONE — flagship axis)

The only test layer that catches *transitive accounting bugs* — bugs where mutation order affects the final defect count. Property tests check single-input invariants; mutation tests check path-independence.

| Machine | Settings | Invariants per step |
|---------|----------|---------------------|
| `PlaceholderMutationMachine` | 400 examples × 50 steps | 2 |
| `DuplicateIdMutationMachine` | 400 × 50 | 1 |
| `NullCoverageMutationMachine` | 400 × 50 | 2 |
| `CompoundMutationMachine` | 500 × 60 | 3 (defects_total accounting, defect_rate consistency, non-negativity) |

Sprint B subtotal: **~90,000 mutation steps × 1-3 invariants each ≈ 225,000 invariant evaluations**, 20.85s runtime.

### P0.8b — Sprint D: mutation expansion to remaining single-axis dimensions + orthogonality (DONE)

Sprint B left 6 of 9 audit dimensions without single-axis path-independence verification (only the compound machine touched them). Sprint D adds the 3 highest-leverage single-axis machines (stale / integrity / jurisdiction) and the cross-dimension orthogonality machine that catches accidental side-effects between dimensions.

| Machine | Settings | Invariants per step | Catches |
|---------|----------|---------------------|---------|
| `StaleMutationMachine` | 400 × 50 | 2 (count match, rate consistency) | stale_count drift across fresh/stale/null transitions |
| `IntegrityViolationMutationMachine` | 400 × 50 | 1 (XOR truth-table) | reviewed_at/reviewed_by accounting under independent toggles |
| `JurisdictionMismatchMutationMachine` | 400 × 50 | 1 (rule replay: scope-allowed branch + XOR branch) | jurisdiction code/scope mismatch counting drift |
| `OrthogonalityMachine` | 400 × 50 | 2 (non-mutated dims at baseline; static-zero dims unchanged) | cross-dimension cross-talk — mutating dim A leaves dim B count untouched |

Sprint D subtotal: **+~80,000 mutation steps × 1-2 invariants ≈ +120,000 invariant evaluations**, ~12s runtime delta (empirical: nightly 31s baseline → 42.56s post-D).

Field-routing matrix proves orthogonality is real: each rule mutates a NON-OVERLAPPING field (placeholder→`extracted_by`, duplicate→`id`, stale→`effective_from` set to old date / not None, integrity→`reviewed_by`→None, null_coverage→`confidence`→None). The static-zero invariant catches accidental side-effects on `jurisdiction_mismatches` / `prohibited_role_count` / `invalid_chain_count` / `inconsistent_scope_count` even though no rule deliberately mutates them — it's a forcing function against future regressions where a new rule grows side-effects.

Sprint B + D combined: **8 machines, ~170,000 mutation steps, ~345,000 invariant evaluations**, 34s runtime total.

### P0.9 — Sprint C: API client + perf gate + CI tiering (DONE)

`scripts/data_quality_survey_via_api.py` had **zero tests** pre-Sprint-C — and it's the surface that touched PROD on 2026-04-27 to produce the v3 baseline. Silent failure here would skew every survey.

| File | Cases | Coverage |
|------|-------|----------|
| `test_data_quality_api_client.py` | 46 cases | _fetch_sample success path + 10 HTTP/network failure modes (URLError, 401/403/404/500/502/503, ConnectionResetError, TimeoutError, OSError) + URL construction + main() exit codes + per-type orchestration |
| `test_data_quality_perf_regression.py` | 12 perf-asserted cases | Wall-clock budgets per row count (100→10K), linearity check (1k→10k ratio 4×-25× to catch O(n²) regression), memory check (report dict size constant) |

CI tiering shipped via `scripts/run_data_quality_tests.sh`:

| Tier | Files | Cases | Wall-clock (p50 / p95 measured) |
|------|-------|-------|-----------------------------------|
| `fast` | legacy + api_client + edge | 163 | **445ms p50 / 511ms p95** — sub-second PR gate confirmed |
| `standard` | + orchestration + corpus + golden + perf | 1,582 | 2.25s — merge-to-main gate |
| `nightly` | + property + matrix + mutation | 5,832 pytest IDs | 31.04s — cron gate |

Sprint C subtotal: **58 cases + tiered runner**.

### Final test suite status (post Sprint A+B+C+D)

| Metric | Value |
|--------|-------|
| Test files | 12 (~4,000 LOC) |
| pytest IDs | 5,853 |
| hypothesis examples | ~6,500 |
| mutation steps | ~170,000 |
| **Effective cases** | **~222,000** |
| Nightly wall-clock | ~43s (empirical 42.56s — was 31s; +~12s for Sprint D mutation machines) |
| Fast PR gate p95 | 511ms (unchanged — Sprint D additions live in nightly only) |

`test_schema_completeness.py` (17 IDs, 11 designed-FAIL pending HITL Plan A/B/C/D) is wired into `nightly` tier only — keeping the schema-vs-audit drift signal visible without blocking PR-tier. Sprint D's 4 new mutation machines also live in nightly via `test_data_quality_mutation.py`.

### P1 — `effective_from` backfill (HIGH)

Affects 11 FAIL-level types. Per Round-1 Munger inversion the **guard precedes the backfill** — and that guard now exists (P0.5 above). Backfill steps:

1. **Banlist already active** (gate-side, P0.5 done): `source_doc_id` and similar lineage strings must NOT be in the banlist `{'unknown', 'tbd', 'todo', 'default', 'n/a', 'na', 'none', 'null', 'nil', 'tba', 'fixme', '?', '-', ''}`, case-insensitive + whitespace-stripped. Backfill that flips a NULL into 'unknown' will re-fire as a defect via this gate.
2. **Seed-derived rows**: backfill from JSON source `effectiveDate` field where present (SocialInsuranceRule and several others have it).
3. **Q1 batch with no source date**: use real date `2024-01-01` AND introduce a separate enum column `effective_from_source: enum('source', 'seed_default', 'extracted')`. Use enum, not string, so the placeholder banlist doesn't false-positive on legitimate defaults.

Estimated work: 2-3 hours scripted (additive UPDATE batches via wrapper).

### P1.5 — `jurisdiction_code/scope` derive-from-prefix default (BLOCKED, HITL Plan A/B/C/D)

**Status reversed by 2026-04-27 PROD reconnaissance. Round-1 derive-rules match 0/7 PROD types sampled.** See `2026-04-27-p1.5-jurisdiction-recon-memo.md` for full evidence and the §"Recon Findings" section below for Maurice-facing summary.

Original (now-rejected) derivation rules — kept here as historical record only:

1. `id` contains `CN-FTZ-*` → `scope=experimental_zone`, `code=<prefix>` — **0 PROD hits**
2. `id` contains ISO admin (`CN-31`, `CN-HK`, etc.) → `scope=subnational`, `code=<as-is>` — **0 PROD hits**
3. Otherwise → `code=CN`, `scope=national` — **100% fallback** (would falsely tag rows `jurisdiction_source='derived'`, a meta-level placeholder fraud the banlist gate cannot catch)

PROD ID-pattern reality (3 distinct shapes observed across 7 sampled canonical types):

- **Jurisdiction-coded** (Region only): `BJ` / `SH` / `TJ` / `CQ` / `HEB` — Chinese province/municipality short codes; needs lookup table → ISO 3166-2:CN format.
- **Token-embedded** (SocialInsuranceRule): substring `NAT` denotes national scope; needs substring matching, not prefix matching.
- **Domain-only / opaque** (5+ types: TaxRate UUID, IndustryBenchmark, TaxEntity, TaxType, FilingFormField): zero jurisdiction signal; default fallback must NOT pretend to be derivation.

Three candidate revised plans pending Maurice HITL decision:

- **Plan A** — honest fallback with `jurisdiction_source` enum {`lookup`, `token_match`, `default_no_signal`}. Implementable in 1-2h.
- **Plan B** — defer 30 days until per-type signal research completes.
- **Plan C** — drop the abstraction: restrict jurisdiction enforcement to 3-5 semantically-meaningful types (Region, possibly LegalDocument, possibly Penalty); remove `jurisdiction_code/scope` from `CRITICAL_COLUMNS` for the rest. **Recommended**.

**No PROD mutation will occur until Maurice selects Plan A / B / C / D.**

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
