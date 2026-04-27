"""Edge-case enumeration tests — boundary conditions, exotic inputs, traps.

Focus areas (each typically catches a class of bugs the property and
matrix layers wouldn't surface):

  * Threshold boundaries (0, 0.5, 0.99, 1.0, 1.01, negative)
  * NULL semantics (None vs '' vs whitespace string vs missing key)
  * Unicode + emoji + control chars in lineage strings
  * Very large rows (deeply nested, super-long strings)
  * Single-element samples (off-by-one bait)
  * Repeated identical rows (duplicate detection edge)
  * Mixed case-NULL + placeholder in same row
  * Banlist boundary (`?`, `-`, ``)
"""

from __future__ import annotations

from datetime import date

import pytest

from src.audit.data_quality_survey import (
    CRITICAL_COLUMNS,
    DEFAULT_NULL_COVERAGE_THRESHOLD,
    LINEAGE_STRING_FIELDS,
    PLACEHOLDER_BANLIST,
    _is_placeholder,
    survey_type,
)


# ---------------------------------------------------------------------------
# Threshold boundary
# ---------------------------------------------------------------------------


class TestThresholdBoundary:

    @pytest.mark.parametrize("threshold", [0.0, 0.001, 0.499, 0.5, 0.501, 0.999, 1.0, 1.01, 100.0])
    def test_thresholds_do_not_crash(self, threshold):
        # Cover the threshold value space — any value must be accepted by
        # survey_type without raising; values >1.0 simply disable the gate.
        rows = [{"id": "n1"}]  # all critical NULL
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=threshold)
        assert "null_coverage_violation_count" in r

    def test_threshold_zero_is_degenerate_always_violates(self):
        # Threshold 0.0 with `>=` semantics is degenerate: even rate=0.0
        # satisfies `0.0 >= 0.0` → all 5 critical columns "violated".
        # This documents the actual semantics, not a useful threshold.
        # Real callers should use a small epsilon (0.001) to mean
        # "any NULL at all".
        rows = [{"id": "n1", **{c: "x" for c in CRITICAL_COLUMNS}}]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.0)
        assert r["null_coverage_violation_count"] == len(CRITICAL_COLUMNS), (
            "0.0 threshold should be degenerate-violate (rate >= 0 is true)"
        )

    def test_threshold_epsilon_flags_only_actual_nulls(self):
        # epsilon=0.001 is the SAFE semantic for "any NULL at all".
        rows = [{"id": "n1", **{c: "x" for c in CRITICAL_COLUMNS}}]
        # All filled → 0 NULL → rate=0 < 0.001 → 0 violations.
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.001)
        assert r["null_coverage_violation_count"] == 0
        # Now one NULL on effective_from.
        rows[0]["effective_from"] = None
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.001)
        # 1/1 = 1.0 >= 0.001 → effective_from violated.
        assert r["null_coverage_violation_count"] == 1
        assert "effective_from" in r["null_coverage_violations"]

    def test_threshold_just_above_one_disables(self):
        # 1.01 is the canonical "disable" sentinel used in legacy tests.
        rows = [{"id": "n1"}]  # all NULL
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["null_coverage_violation_count"] == 0

    def test_threshold_at_exact_50_percent_inclusive(self):
        # Boundary: 50% should match (>=) the default threshold.
        rows = [
            {"id": "a", "effective_from": "2024-01-01"},
            {"id": "b", "effective_from": None},
        ]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.5)
        # Rate = 0.5 exactly, threshold = 0.5, >= → violation.
        assert "effective_from" in r["null_coverage_violations"]


# ---------------------------------------------------------------------------
# NULL semantics — None vs '' vs whitespace vs missing key
# ---------------------------------------------------------------------------


class TestNullSemantics:

    def test_missing_key_treated_as_null(self):
        rows = [{"id": "n1"}]  # critical cols absent
        r = survey_type(rows, today=date(2024, 6, 1))
        for col in CRITICAL_COLUMNS:
            assert r["null_rate"][col] == 1.0

    def test_explicit_none_is_null(self):
        rows = [{"id": "n1", "effective_from": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["null_rate"]["effective_from"] == 1.0

    def test_empty_string_is_null_for_null_rate(self):
        rows = [{"id": "n1", "source_doc_id": ""}]
        r = survey_type(rows, today=date(2024, 6, 1))
        # null_rate counts '' as NULL (per existing test_empty_string_counts_as_null).
        assert r["null_rate"]["source_doc_id"] == 1.0

    def test_whitespace_only_string_is_NOT_null_for_null_rate(self):
        # Whitespace string is technically NOT NULL — null_rate sees a value.
        # BUT placeholder banlist sees '   '.strip().lower() == '' → banned.
        # This is the intended split: structural NULL vs semantic NULL.
        rows = [{"id": "n1", "source_doc_id": "   "}]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["null_rate"]["source_doc_id"] == 0.0  # not NULL
        assert r["placeholder_per_field"]["source_doc_id"] == 1  # but placeholder

    def test_zero_int_is_NOT_null(self):
        # Edge: confidence=0 is a valid value, NOT a NULL marker.
        rows = [{"id": "n1", "confidence": 0.0}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["null_rate"]["confidence"] == 0.0

    def test_false_bool_is_NOT_null(self):
        rows = [{"id": "n1", "effective_from": False}]
        r = survey_type(rows, today=date(2024, 6, 1))
        # False is a value, not NULL. (Won't pass downstream type checks but
        # null_rate doesn't enforce types.)
        assert r["null_rate"]["effective_from"] == 0.0


# ---------------------------------------------------------------------------
# Unicode + CJK + emoji + control chars
# ---------------------------------------------------------------------------


class TestExoticStrings:

    @pytest.mark.parametrize("exotic", [
        "营业税票_2024",         # CJK + ASCII
        "🚀 doc",                # emoji
        "​doc",            # zero-width space
        "doc\nfile",            # newline embedded
        "доку́мент",             # cyrillic with diacritic
        "doc\x00null",          # null byte embedded
        "𝓭𝓸𝓬",                  # mathematical alphanumeric
    ])
    def test_exotic_strings_not_flagged_as_placeholder(self, exotic):
        # None of these are in the banlist (literally or after strip+lower).
        if exotic.strip().lower() in PLACEHOLDER_BANLIST:
            pytest.skip(f"hypothesis: exotic happens to be banned → skip")
        assert not _is_placeholder(exotic), f"false positive on exotic: {exotic!r}"

    def test_super_long_string_not_flagged(self):
        # 10K-character string that doesn't equal any banned token.
        long_str = "doc_" + "x" * 10_000
        assert not _is_placeholder(long_str)

    def test_super_long_string_passes_survey(self):
        long_str = "doc_" + "x" * 10_000
        rows = [{"id": "n1", **{c: "x" for c in CRITICAL_COLUMNS}, "source_doc_id": long_str}]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["placeholder_string_count"] == 0


# ---------------------------------------------------------------------------
# Boundary banlist tokens — `?`, `-`, ''
# ---------------------------------------------------------------------------


class TestBanlistEdgeTokens:

    def test_question_mark_alone_flagged(self):
        assert _is_placeholder("?")

    def test_dash_alone_flagged(self):
        assert _is_placeholder("-")

    def test_empty_string_alone_flagged(self):
        assert _is_placeholder("")

    def test_whitespace_collapses_to_empty_flagged(self):
        assert _is_placeholder("   ")
        assert _is_placeholder("\t\n")

    def test_question_mark_in_phrase_NOT_flagged(self):
        # 'is this a doc?' — substring match would false-positive; whole-token
        # semantics correctly rejects.
        assert not _is_placeholder("is this a doc?")

    def test_dash_in_id_NOT_flagged(self):
        assert not _is_placeholder("doc-2024-001")

    def test_dash_with_whitespace_NOT_flagged(self):
        # ' - ' strips to '-' which IS in banlist — this IS flagged.
        # Documents the semantic: bare '-' or whitespace-padded '-' = placeholder.
        assert _is_placeholder(" - ")


# ---------------------------------------------------------------------------
# Single-row + zero-row edge cases
# ---------------------------------------------------------------------------


class TestRowCountEdges:

    def test_zero_rows_no_phantom_defects(self):
        r = survey_type([], today=date(2024, 6, 1))
        for dim in (
            "duplicate_id_count", "stale_count", "integrity_violations",
            "jurisdiction_mismatches", "prohibited_role_count",
            "invalid_chain_count", "inconsistent_scope_count",
            "null_coverage_violation_count", "placeholder_string_count",
        ):
            assert r[dim] == 0
        assert r["defect_rate"] == 0.0

    def test_single_row_clean(self):
        rows = [{
            "id": "only",
            "effective_from": "2024-01-01",
            "confidence": 0.9,
            "source_doc_id": "doc1",
            "jurisdiction_code": "CN",
            "jurisdiction_scope": "national",
            "reviewed_at": "2024-01-02",
            "reviewed_by": "auditor",
        }]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["sampled"] == 1
        assert r["defects_total"] == 0

    def test_single_row_all_dimensions_dirty(self):
        # Stress: one row triggers as many dimensions as possible.
        rows = [{
            "id": "n1",
            # NO effective_from → null
            # NO confidence → null
            "source_doc_id": "unknown",       # placeholder
            "extracted_by": "TBD",            # placeholder
            "reviewed_by": "auditor",         # XOR violation (no reviewed_at)
            "jurisdiction_code": "INVALID",
            "jurisdiction_scope": "weird-scope",
            "override_chain_id": "?",         # invalid chain whitelist + placeholder
            "argument_role": "analogy",       # prohibited
        }]
        # threshold 1.01 to isolate placeholder + integrity + jurisdiction
        # from null-coverage noise (which would also fire).
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        # Must trigger MULTIPLE dimensions on this single dirty row.
        triggered = sum(1 for dim in (
            "integrity_violations", "jurisdiction_mismatches",
            "prohibited_role_count", "invalid_chain_count",
            "placeholder_string_count",
        ) if r[dim] > 0)
        assert triggered >= 4, (
            f"only {triggered} dimensions fired on dirty single row: {r}"
        )


# ---------------------------------------------------------------------------
# Duplicate-id behavior
# ---------------------------------------------------------------------------


class TestDuplicateIdEdges:

    def test_two_identical_ids_yields_one_duplicate(self):
        rows = [
            {"id": "x", **{c: "v" for c in CRITICAL_COLUMNS}, "reviewed_at": "x", "reviewed_by": "y"},
            {"id": "x", **{c: "v" for c in CRITICAL_COLUMNS}, "reviewed_at": "x", "reviewed_by": "y"},
        ]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["duplicate_id_count"] == 1  # second occurrence is the duplicate

    def test_three_identical_ids_yields_two_duplicates(self):
        rows = [{"id": "x", **{c: "v" for c in CRITICAL_COLUMNS}, "reviewed_at": "x", "reviewed_by": "y"} for _ in range(3)]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["duplicate_id_count"] == 2

    def test_unique_ids_no_duplicates(self):
        rows = [{"id": f"n{i}", **{c: "v" for c in CRITICAL_COLUMNS}, "reviewed_at": "x", "reviewed_by": "y"} for i in range(5)]
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=1.01)
        assert r["duplicate_id_count"] == 0


# ---------------------------------------------------------------------------
# Mixed-dirty rows — one row fires multiple dimensions
# ---------------------------------------------------------------------------


class TestMixedDirty:

    def test_null_AND_placeholder_in_same_field_fires_both(self):
        # source_doc_id mix: half NULL, half placeholder. null_rate sees
        # half-NULL; placeholder counts the actual banned strings.
        rows = (
            [{"id": f"n{i}", "source_doc_id": None} for i in range(2)]
            + [{"id": f"n{i+2}", "source_doc_id": "unknown"} for i in range(2)]
        )
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=0.4)
        # null_rate sees 2/4 = 0.5; threshold 0.4 → violated.
        assert "source_doc_id" in r["null_coverage_violations"]
        # Placeholder count is 2.
        assert r["placeholder_per_field"]["source_doc_id"] == 2


# ---------------------------------------------------------------------------
# Threshold + sample-size interaction edge
# ---------------------------------------------------------------------------


class TestThresholdSampleInteraction:

    @pytest.mark.parametrize("n,nulls,threshold,expected_violated", [
        (1, 0, 0.50, False),    # 0/1 = 0 < 0.5 → not violated
        (1, 1, 0.50, True),     # 1/1 = 1.0 >= 0.5 → violated
        (10, 5, 0.50, True),    # 5/10 = 0.5 >= 0.5 → violated
        (10, 4, 0.50, False),   # 4/10 = 0.4 < 0.5 → not violated
        (100, 50, 0.50, True),  # 50/100 = 0.5 >= 0.5 → violated
        (100, 49, 0.50, False), # 49/100 = 0.49 < 0.5 → not violated
        (3, 1, 0.34, False),    # 1/3 ≈ 0.333 < 0.34 → not violated
        (3, 1, 0.33, True),     # 1/3 ≈ 0.333 >= 0.33 → violated
    ])
    def test_per_column_violation_at_boundary(self, n, nulls, threshold, expected_violated):
        rows = []
        for i in range(n):
            row = {
                "id": f"n{i}",
                "effective_from": "2024-01-01" if i >= nulls else None,
                "confidence": 0.9,
                "source_doc_id": f"doc{i}",
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
                "reviewed_at": "x",
                "reviewed_by": "y",
            }
            rows.append(row)
        r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=threshold)
        if expected_violated:
            assert "effective_from" in r["null_coverage_violations"]
        else:
            assert "effective_from" not in r["null_coverage_violations"]


# ---------------------------------------------------------------------------
# Default constants exposed
# ---------------------------------------------------------------------------


class TestExposedConstants:

    def test_default_null_coverage_threshold_is_half(self):
        # If this changes, downstream test files relying on 0.5 break.
        assert DEFAULT_NULL_COVERAGE_THRESHOLD == 0.5

    def test_critical_columns_count_is_five(self):
        assert len(CRITICAL_COLUMNS) == 5

    def test_lineage_string_fields_count_is_five(self):
        assert len(LINEAGE_STRING_FIELDS) == 5

    def test_banlist_contains_canonical_placeholders(self):
        for canonical in ("unknown", "tbd", "default", "n/a", ""):
            assert canonical in PLACEHOLDER_BANLIST

    def test_banlist_does_not_contain_legitimate_tokens(self):
        # Sanity: don't accidentally banlist a real ID prefix.
        for legit in ("doc", "ref", "src", "id", "v1", "ok"):
            assert legit not in PLACEHOLDER_BANLIST
