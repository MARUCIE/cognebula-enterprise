"""Property-based tests for `survey_type` — invariants over generated rows.

This file is the high-volume layer of the data-quality test suite. Where
`test_data_quality_survey.py` enumerates specific scenarios, this file
encodes properties that MUST hold for all rows in the input space (within
the row schema). Each `@given` test runs `max_examples` iterations
(default 100, bumped to 200 for critical safety properties), so the file
contributes ~5,000-7,000 generated test cases.

Invariants tested:

    1. Banlist matches are case-insensitive AND whitespace-stripped (Goodhart guard)
    2. Non-string values never trigger banlist (type guard)
    3. defects_total = sum of all 9 dimensions (no double-counting, no drops)
    4. defect_rate is in [0.0, +inf) and matches defects_total / max(sampled, 1)
    5. null_rate values are in [0.0, 1.0] for every CRITICAL_COLUMNS entry
    6. Empty sample never produces phantom defects in any dimension
    7. Permutation invariance: shuffling rows must not change report metrics
    8. Sample-size linearity: doubling rows with the same shape doubles defects
    9. Threshold monotonicity: stricter null_coverage_threshold = more violations
    10. Banlist whole-token semantics: substring containing banned word does not match

Hypothesis runs each property 100x by default, so a single file ships ~5K cases.
"""

from __future__ import annotations

import string
from datetime import date

from hypothesis import given, settings, strategies as st

from src.audit.data_quality_survey import (
    CRITICAL_COLUMNS,
    DEFAULT_NULL_COVERAGE_THRESHOLD,
    LINEAGE_STRING_FIELDS,
    PLACEHOLDER_BANLIST,
    _is_placeholder,
    survey_type,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Deliberately bound to ASCII printable + selected unicode to avoid generating
# pathological inputs that would be rejected by Cypher anyway. Real PROD rows
# carry CJK characters, so we mix Latin + CJK + control chars.
_LINEAGE_NORMAL_TEXT = st.text(
    alphabet=string.ascii_letters + string.digits + "_-中文票务规则",
    min_size=1,
    max_size=20,
)

_BANLIST_CHOICES = st.sampled_from(sorted(PLACEHOLDER_BANLIST))


def _vary_case_and_whitespace(s: str) -> st.SearchStrategy[str]:
    """Generate case + whitespace variants of s — all must hit banlist."""
    if not s:  # empty string is its own variant
        return st.sampled_from(["", "   ", "\t\n", " "])
    return st.sampled_from([
        s,
        s.upper(),
        s.lower(),
        s.title(),
        s.swapcase(),
        f"  {s}  ",
        f"\t{s}\n",
        f" {s.upper()} ",
        f"\n{s.title()}\t",
    ])


_BANLIST_VARIANT = _BANLIST_CHOICES.flatmap(_vary_case_and_whitespace)


def _row_strategy(
    *,
    populate_critical: bool = True,
    placeholder_in: str | None = None,
) -> st.SearchStrategy[dict]:
    """Build a single-row strategy.

    Args:
        populate_critical: if True, fills all CRITICAL_COLUMNS with valid data;
            this guarantees null_coverage stays clean unless overridden.
        placeholder_in: if given, sets that LINEAGE_STRING_FIELDS column to a
            random banlist variant (case/whitespace-mutated banned word).
    """
    base: dict = {"id": st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=10)}
    if populate_critical:
        base["effective_from"] = st.just("2024-01-01")
        base["confidence"] = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
        base["source_doc_id"] = _LINEAGE_NORMAL_TEXT
        base["jurisdiction_code"] = st.sampled_from(["CN", "CN-31", "CN-HK", "CN-FTZ-Hainan"])
        base["jurisdiction_scope"] = st.sampled_from(["national", "subnational", "experimental_zone"])
        # paired review fields — both populated → no XOR
        base["reviewed_at"] = st.just("2024-01-02")
        base["reviewed_by"] = _LINEAGE_NORMAL_TEXT
    if placeholder_in is not None:
        base[placeholder_in] = _BANLIST_VARIANT
    return st.fixed_dictionaries(base)


# ---------------------------------------------------------------------------
# Property 1 — Banlist is case-insensitive AND whitespace-stripped
# ---------------------------------------------------------------------------


class TestBanlistInvariants:

    @given(_BANLIST_VARIANT)
    @settings(max_examples=500)
    def test_banlist_variants_always_match(self, banned: str):
        # Every variant of every banlist word must trigger _is_placeholder.
        assert _is_placeholder(banned), f"banlist miss on variant: {banned!r}"

    @given(_LINEAGE_NORMAL_TEXT)
    @settings(max_examples=500)
    def test_normal_text_never_triggers_banlist(self, text: str):
        # Normal lineage text (random alnum + CJK + _-) must NOT match banlist.
        # Edge: random text could include 'tba' substring; but banlist is
        # whole-token after strip+lower, not substring. Verify.
        if text.strip().lower() in PLACEHOLDER_BANLIST:
            # Hypothesis happened to generate a banlist word — skip this case.
            return
        assert not _is_placeholder(text), f"false positive on normal text: {text!r}"

    @given(st.one_of(
        st.none(),
        st.integers(),
        st.floats(allow_nan=False),
        st.lists(st.integers()),
        st.dictionaries(st.text(max_size=3), st.integers(), max_size=3),
    ))
    @settings(max_examples=500)
    def test_non_string_never_triggers_banlist(self, value):
        # Type guard: only strings are evaluated. None / numbers / lists / dicts
        # all skip the banlist gate. (True NULL is captured by null_rate.)
        assert not _is_placeholder(value)

    @given(_BANLIST_VARIANT)
    @settings(max_examples=100)
    def test_placeholder_in_source_doc_id_always_counts(self, banned: str):
        rows = [{
            "id": "n1",
            "effective_from": "2024-01-01",
            "confidence": 0.9,
            "source_doc_id": banned,
            "jurisdiction_code": "CN",
            "jurisdiction_scope": "national",
            "reviewed_at": "2024-01-02",
            "reviewed_by": "auditor",
        }]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["placeholder_string_count"] == 1
        assert r["placeholder_per_field"]["source_doc_id"] == 1

    @given(st.lists(_BANLIST_VARIANT, min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_n_placeholders_yield_n_hits_in_one_field(self, banned_list):
        # N rows each with placeholder source_doc_id → N placeholder hits.
        rows = [
            {
                "id": f"n{i}",
                "effective_from": "2024-01-01",
                "confidence": 0.9,
                "source_doc_id": b,
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
                "reviewed_at": "2024-01-02",
                "reviewed_by": "auditor",
            }
            for i, b in enumerate(banned_list)
        ]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["placeholder_string_count"] == len(banned_list)
        assert r["placeholder_per_field"]["source_doc_id"] == len(banned_list)


# ---------------------------------------------------------------------------
# Property 2 — defects_total accounting (sum invariant, no double-counting)
# ---------------------------------------------------------------------------


class TestDefectsTotalAccounting:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=20))
    @settings(max_examples=500)
    def test_defects_total_equals_sum_of_dimensions(self, rows):
        r = survey_type(rows, today=date(2024, 6, 1))
        # defects_total must equal explicit sum of all 9 named dimensions.
        explicit_sum = (
            r["duplicate_id_count"]
            + r["stale_count"]
            + r["integrity_violations"]
            + r["jurisdiction_mismatches"]
            + r["prohibited_role_count"]
            + r["invalid_chain_count"]
            + r["inconsistent_scope_count"]
            + r["null_coverage_violation_count"]
            + r["placeholder_string_count"]
        )
        assert r["defects_total"] == explicit_sum

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=20))
    @settings(max_examples=500)
    def test_defect_rate_is_total_over_sampled(self, rows):
        r = survey_type(rows, today=date(2024, 6, 1))
        sampled = r["sampled"]
        if sampled == 0:
            assert r["defect_rate"] == 0.0
        else:
            # Allow tiny float epsilon since report rounds to 4 decimals.
            expected = round(r["defects_total"] / sampled, 4)
            assert abs(r["defect_rate"] - expected) < 1e-4

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=10))
    @settings(max_examples=500)
    def test_defects_never_negative(self, rows):
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["defects_total"] >= 0
        assert r["defect_rate"] >= 0.0
        for dim in (
            "duplicate_id_count", "stale_count", "integrity_violations",
            "jurisdiction_mismatches", "prohibited_role_count",
            "invalid_chain_count", "inconsistent_scope_count",
            "null_coverage_violation_count", "placeholder_string_count",
        ):
            assert r[dim] >= 0, f"{dim} went negative: {r[dim]}"

    @given(st.lists(_row_strategy(populate_critical=True), min_size=1, max_size=10))
    @settings(max_examples=500)
    def test_defects_bounded_by_max_per_row_times_n(self, rows):
        # No row contributes more than ~12 defects (5 critical NULL columns +
        # 5 lineage placeholder fields + 1 stale + 1 integrity + ...).
        # Loose bound: defects_total <= 20 * sampled is a sanity check.
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["defects_total"] <= 20 * r["sampled"]


# ---------------------------------------------------------------------------
# Property 3 — null_rate is always in [0.0, 1.0]
# ---------------------------------------------------------------------------


class TestNullRateBounds:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=20))
    @settings(max_examples=500)
    def test_null_rate_in_unit_interval(self, rows):
        r = survey_type(rows, today=date(2024, 6, 1))
        for col in CRITICAL_COLUMNS:
            assert 0.0 <= r["null_rate"][col] <= 1.0, (
                f"null_rate[{col}] out of bounds: {r['null_rate'][col]}"
            )

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_null_rate_keys_match_critical_columns(self, rows):
        r = survey_type(rows, today=date(2024, 6, 1))
        assert set(r["null_rate"].keys()) == set(CRITICAL_COLUMNS)


# ---------------------------------------------------------------------------
# Property 4 — Empty sample produces no phantom defects
# ---------------------------------------------------------------------------


class TestEmptySampleSafety:

    @given(st.just([]))
    @settings(max_examples=10)
    def test_empty_sample_zero_defects(self, rows):
        # Re-asserting via @given for property style; trivially true but
        # guards against regression if survey_type adds size-independent logic.
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["sampled"] == 0
        assert r["defects_total"] == 0
        assert r["defect_rate"] == 0.0
        assert r["null_coverage_violation_count"] == 0
        assert r["placeholder_string_count"] == 0


# ---------------------------------------------------------------------------
# Property 5 — Permutation invariance (order doesn't matter)
# ---------------------------------------------------------------------------


class TestPermutationInvariance:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=2, max_size=10))
    @settings(max_examples=100)
    def test_shuffle_does_not_change_report(self, rows):
        # Survey is a pure aggregation — row order must not affect counts.
        import random
        rows_a = list(rows)
        rows_b = list(rows)
        random.Random(42).shuffle(rows_b)
        r_a = survey_type(rows_a, today=date(2024, 6, 1))
        r_b = survey_type(rows_b, today=date(2024, 6, 1))
        # Compare scalar fields that must be order-invariant.
        for k in (
            "sampled", "defects_total", "defect_rate",
            "duplicate_id_count", "stale_count", "integrity_violations",
            "jurisdiction_mismatches", "prohibited_role_count",
            "invalid_chain_count", "inconsistent_scope_count",
            "null_coverage_violation_count", "placeholder_string_count",
        ):
            assert r_a[k] == r_b[k], f"order-dependent on key {k}: {r_a[k]} vs {r_b[k]}"


# ---------------------------------------------------------------------------
# Property 6 — Sample-size linearity (doubling rows doubles defects, modulo dup-id)
# ---------------------------------------------------------------------------


class TestSampleSizeLinearity:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=1, max_size=5))
    @settings(max_examples=80)
    def test_double_with_unique_ids_doubles_per_row_defects(self, rows):
        # Caveat: duplicate_id_count BREAKS linearity (becomes O(n^2)-like
        # for repeated ids). To preserve linearity we re-id the second copy.
        # Other dimensions (stale, integrity, jurisdiction, banlist) ARE linear.
        rows_2x = list(rows) + [
            {**r, "id": f"{r['id']}_copy"} for r in rows
        ]
        r1 = survey_type(rows, today=date(2024, 6, 1))
        r2 = survey_type(rows_2x, today=date(2024, 6, 1))
        for dim in (
            "stale_count", "integrity_violations", "jurisdiction_mismatches",
            "prohibited_role_count", "invalid_chain_count",
            "inconsistent_scope_count", "placeholder_string_count",
        ):
            assert r2[dim] == 2 * r1[dim], (
                f"{dim} not linear: 1x={r1[dim]} 2x={r2[dim]}"
            )


# ---------------------------------------------------------------------------
# Property 7 — Threshold monotonicity for null_coverage gate
# ---------------------------------------------------------------------------


class TestThresholdMonotonicity:

    @given(
        st.lists(_row_strategy(populate_critical=False), min_size=1, max_size=10),
        st.floats(min_value=0.01, max_value=0.99, allow_nan=False),
        st.floats(min_value=0.01, max_value=0.99, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_lower_threshold_yields_at_least_as_many_violations(
        self, rows, t_low, t_high
    ):
        # If t_low < t_high, the lower threshold MUST flag at least as many
        # columns as the higher one — strict subset relationship.
        if t_low > t_high:
            t_low, t_high = t_high, t_low
        r_low = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=t_low)
        r_high = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=t_high)
        assert r_low["null_coverage_violation_count"] >= r_high["null_coverage_violation_count"]

    @given(st.lists(_row_strategy(populate_critical=False), min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_threshold_at_or_above_one_disables(self, rows):
        # Threshold > 1.0 must disable the gate entirely (no rate can exceed 1).
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["null_coverage_violation_count"] == 0


# ---------------------------------------------------------------------------
# Property 8 — Banlist substring vs whole-token semantics
# ---------------------------------------------------------------------------


class TestBanlistSubstringSafety:

    @given(_BANLIST_CHOICES, _LINEAGE_NORMAL_TEXT)
    @settings(max_examples=500)
    def test_banned_word_as_substring_does_not_match(self, banned: str, prefix: str):
        # Construct a string where banned word is embedded inside other text.
        # If banned is empty string it would match ANY string after strip — skip.
        if banned == "":
            return
        # banned == "?" or "-" can pathologically sit alone; concatenate to
        # ensure substring-not-whole-token.
        composite = f"{prefix}_{banned}_real_doc_id"
        # Strip + lower must still produce a non-banlist token.
        canonical = composite.strip().lower()
        if canonical in PLACEHOLDER_BANLIST:
            # Edge: hypothesis happened to land on a banlist whole-token after
            # transformation — skip these cases.
            return
        assert not _is_placeholder(composite), (
            f"substring false positive: {composite!r}"
        )


# ---------------------------------------------------------------------------
# Property 9 — Defaults wired correctly
# ---------------------------------------------------------------------------


class TestDefaults:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_default_threshold_value_used_when_omitted(self, rows):
        # Calling without explicit threshold must equal explicit DEFAULT.
        r_implicit = survey_type(rows, today=date(2024, 6, 1))
        r_explicit = survey_type(
            rows,
            today=date(2024, 6, 1),
            null_coverage_threshold=DEFAULT_NULL_COVERAGE_THRESHOLD,
        )
        assert r_implicit["null_coverage_threshold"] == DEFAULT_NULL_COVERAGE_THRESHOLD
        assert r_implicit["null_coverage_violation_count"] == r_explicit["null_coverage_violation_count"]


# ---------------------------------------------------------------------------
# Property 10 — Lineage string fields coverage
# ---------------------------------------------------------------------------


class TestLineageFieldCoverage:

    @given(st.sampled_from(LINEAGE_STRING_FIELDS), _BANLIST_VARIANT)
    @settings(max_examples=500)
    def test_each_lineage_field_independently_detects_placeholder(
        self, field: str, banned: str
    ):
        rows = [{
            "id": "n1",
            "effective_from": "2024-01-01",
            "confidence": 0.9,
            "source_doc_id": "doc_legit",  # populate the "default" critical fields
            "jurisdiction_code": "CN",
            "jurisdiction_scope": "national",
            "reviewed_at": "2024-01-02",
            "reviewed_by": "auditor",
        }]
        # Override the field under test with a banlist variant.
        rows[0][field] = banned
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        # Banlist must detect at least one hit on the targeted field.
        assert r["placeholder_per_field"][field] >= 1, (
            f"banlist failed to detect on {field}: {banned!r}"
        )


# ---------------------------------------------------------------------------
# Property 11 — Idempotence (Sprint E1)
#
# survey_type must be a pure function — calling it twice on the same input
# must return identical output. Catches accidental statefulness (e.g. global
# caches, in-place mutation of the row list, time.time() leaking into the
# computation).
# ---------------------------------------------------------------------------


class TestIdempotence:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=15))
    @settings(max_examples=300)
    def test_survey_type_is_pure_function(self, rows):
        # Two consecutive calls with identical args = identical output.
        r1 = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.5)
        r2 = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.5)
        assert r1 == r2, (
            f"survey_type non-deterministic: r1={r1} r2={r2}"
        )

    @given(st.lists(_row_strategy(populate_critical=True), min_size=1, max_size=10))
    @settings(max_examples=300)
    def test_survey_type_does_not_mutate_input(self, rows):
        # Snapshot rows before the call (deep enough since rows are flat dicts).
        snapshot = [dict(r) for r in rows]
        survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.5)
        # Rows must be unchanged — survey_type is pure read.
        assert rows == snapshot, (
            f"survey_type mutated input: before={snapshot} after={rows}"
        )


# ---------------------------------------------------------------------------
# Property 12 — Defects upper bound (Sprint E1)
#
# defects_total cannot exceed sampled × max-defect-units-per-row. This
# catches accounting drift where a dimension's count grows unboundedly
# (e.g. a per-cell loop running through every column instead of every row).
# Per-row max-defect-units = 5 critical NULL coverage violations + 5 lineage
# placeholder hits + 1 each for: stale, integrity, jurisdiction, prohibited,
# invalid_chain, inconsistent, duplicate. But NULL coverage is per-COLUMN
# (not per-row), so it's bounded by len(CRITICAL_COLUMNS) regardless of
# sampled. Adjusting:
#
#   bound = sampled * (5 + 1 + 1 + 1 + 1 + 1 + 1 + 1)  +  len(CRITICAL_COLUMNS)
#         = sampled * 11                                +  5
#         = 11 * sampled + 5
#
# (5 placeholder per row × len(LINEAGE_STRING_FIELDS) at max + duplicate +
# stale + integrity + jurisdiction + prohibited + chain + scope = 11 row-axis
# units; null_coverage = up to 5 column-axis units.)
# ---------------------------------------------------------------------------


class TestDefectsUpperBound:

    @given(st.lists(_row_strategy(populate_critical=True), min_size=0, max_size=12))
    @settings(max_examples=300)
    def test_defects_total_is_bounded(self, rows):
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.5)
        sampled = r["sampled"]
        # Upper bound: 11 row-axis units * sampled + 5 column-axis null_coverage.
        upper_bound = 11 * sampled + len(CRITICAL_COLUMNS)
        assert 0 <= r["defects_total"] <= upper_bound, (
            f"defects_total={r['defects_total']} violates "
            f"[0, 11*{sampled}+5={upper_bound}]"
        )

    @given(st.lists(_row_strategy(populate_critical=True), min_size=1, max_size=10))
    @settings(max_examples=300)
    def test_per_dimension_counts_bounded_by_sampled(self, rows):
        # Each row-axis dimension is bounded by sampled (each row contributes
        # at most 1 to the dimension). NULL coverage is bounded by 5 (number
        # of CRITICAL_COLUMNS), independent of sampled.
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.5)
        sampled = r["sampled"]
        per_row_max = sampled
        for dim in (
            "duplicate_id_count", "stale_count", "integrity_violations",
            "jurisdiction_mismatches", "prohibited_role_count",
            "invalid_chain_count", "inconsistent_scope_count",
        ):
            assert 0 <= r[dim] <= per_row_max, (
                f"{dim}={r[dim]} violates [0, {per_row_max}]"
            )
        # NULL coverage = column-axis: bounded by 5 (CRITICAL_COLUMNS count).
        assert 0 <= r["null_coverage_violation_count"] <= len(CRITICAL_COLUMNS)


# ---------------------------------------------------------------------------
# Property 13 — Defects monotone-non-decreasing under add-only mutation (Sprint E1)
#
# If you add a row to the sample and the new row introduces (≥0) new defects,
# defects_total cannot DECREASE. This is the path-independence sibling of
# the mutation tests but at property granularity — a new row never erases a
# pre-existing defect (except duplicate_id_count, which is a count over the
# whole set and CAN decrease if the new row's id was duplicated; we exclude
# that dimension from this property).
# ---------------------------------------------------------------------------


class TestDefectsMonotoneAddOnly:

    @given(
        st.lists(_row_strategy(populate_critical=True), min_size=1, max_size=10),
        _row_strategy(populate_critical=True),
    )
    @settings(max_examples=300)
    def test_adding_row_does_not_decrease_non_global_dims(self, rows, new_row):
        # Make sure the new row's id is unique to avoid duplicate_id swing.
        new_row = dict(new_row)
        new_row["id"] = f"unique_{id(new_row)}_{len(rows)}"
        r_before = survey_type(
            rows, today=date(2024, 6, 1), null_coverage_threshold=0.5
        )
        r_after = survey_type(
            rows + [new_row], today=date(2024, 6, 1), null_coverage_threshold=0.5
        )
        # Row-axis dims that count individual-row anomalies must be monotone.
        # (duplicate_id_count is excluded — adding a row CAN reduce % NULL etc.,
        #  but raw counts of placeholder/stale/integrity/jurisdiction/clause-axis
        #  cannot decrease because the prior rows' anomalies remain.)
        for dim in (
            "stale_count", "integrity_violations", "jurisdiction_mismatches",
            "prohibited_role_count", "invalid_chain_count",
            "inconsistent_scope_count", "placeholder_string_count",
        ):
            assert r_after[dim] >= r_before[dim], (
                f"{dim} regressed under add-only: before={r_before[dim]} "
                f"after={r_after[dim]} new_row={new_row}"
            )
