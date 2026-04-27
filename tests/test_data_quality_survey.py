"""Data-quality survey tests.

Closes audit 2026-04-21 next-cycle inversion test: before any new Schema
work, we must have a mechanical way to detect *actual* data defects, not
just Schema coverage.

Tests are structured in two layers:
  1. `survey_type` — pure function over row dicts. Directly testable with
     in-memory fixtures, no DB required.
  2. `survey` — orchestration over a stub connection satisfying the
     `conn.execute(cypher).get_as_df().to_dict(orient="records")` contract.
"""

from __future__ import annotations

from datetime import date


from src.audit.data_quality_survey import (
    CRITICAL_COLUMNS,
    survey,
    survey_type,
)

# -------------------------------------------------------------------------
# survey_type — pure analysis
# -------------------------------------------------------------------------


class TestSurveyTypeBasics:
    def test_empty_sample(self):
        r = survey_type([])
        assert r["sampled"] == 0
        assert r["defects_total"] == 0
        assert r["defect_rate"] == 0.0
        # NULL-rate map must still cover every critical column
        for col in CRITICAL_COLUMNS:
            assert r["null_rate"][col] == 0.0

    def test_clean_sample_has_zero_defects(self):
        rows = [
            {
                "id": f"n{i}",
                "effective_from": "2024-01-01",
                "confidence": 0.9,
                "source_doc_id": "doc1",
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
                "reviewed_at": "2024-01-02",
                "reviewed_by": "maurice",
            }
            for i in range(10)
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["sampled"] == 10
        assert r["defects_total"] == 0
        assert r["defect_rate"] == 0.0


class TestNullRateDetection:
    def test_null_effective_from(self):
        rows = [
            {"id": "a", "effective_from": None, "confidence": 0.5},
            {"id": "b", "effective_from": "2024-01-01", "confidence": 0.5},
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["null_rate"]["effective_from"] == 0.5

    def test_empty_string_counts_as_null(self):
        rows = [{"id": "a", "effective_from": ""}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["null_rate"]["effective_from"] == 1.0

    def test_null_rate_round_to_four_decimals(self):
        rows = [{"id": f"n{i}", "confidence": None} for i in range(3)]
        r = survey_type(rows, today=date(2024, 6, 1))
        # 3/3 = 1.0
        assert r["null_rate"]["confidence"] == 1.0


class TestDuplicateDetection:
    def test_detects_duplicate_ids(self):
        rows = [
            {"id": "x", "effective_from": "2024-01-01"},
            {"id": "x", "effective_from": "2024-01-01"},
            {"id": "y", "effective_from": "2024-01-01"},
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        # id "x" appears twice → 1 duplicate beyond first occurrence
        assert r["duplicate_id_count"] == 1

    def test_triple_duplicate(self):
        rows = [{"id": "z"} for _ in range(3)]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["duplicate_id_count"] == 2


class TestStaleDetection:
    def test_old_effective_from_is_stale(self):
        rows = [
            {"id": "a", "effective_from": "2000-01-01"},
            {"id": "b", "effective_from": "2024-01-01"},
        ]
        r = survey_type(rows, today=date(2024, 6, 1), stale_years=10)
        assert r["stale_count"] == 1
        assert r["stale_rate"] == 0.5

    def test_stale_threshold_respected(self):
        """Rule dated well inside the window should NOT be flagged stale."""
        # 9 years gap — clearly under the 10-year threshold.
        rows = [{"id": "a", "effective_from": "2015-06-01"}]
        r = survey_type(rows, today=date(2024, 6, 1), stale_years=10)
        assert r["stale_count"] == 0

    def test_null_effective_from_not_counted_as_stale(self):
        """NULL is a distinct defect class tracked via null_rate, not staleness."""
        rows = [{"id": "a", "effective_from": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["stale_count"] == 0


class TestIntegrityViolations:
    def test_reviewed_at_without_reviewed_by_flagged(self):
        rows = [{"id": "a", "reviewed_at": "2024-01-01", "reviewed_by": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["integrity_violations"] == 1

    def test_reviewed_by_without_reviewed_at_flagged(self):
        rows = [{"id": "a", "reviewed_by": "maurice", "reviewed_at": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["integrity_violations"] == 1

    def test_both_set_is_clean(self):
        rows = [{"id": "a", "reviewed_by": "m", "reviewed_at": "2024-01-01"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["integrity_violations"] == 0

    def test_both_null_is_clean(self):
        rows = [{"id": "a", "reviewed_by": None, "reviewed_at": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["integrity_violations"] == 0


class TestJurisdictionMismatches:
    def test_unknown_scope_flagged(self):
        rows = [{"id": "a", "jurisdiction_scope": "galactic"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["jurisdiction_mismatches"] == 1

    def test_code_without_scope_flagged(self):
        rows = [{"id": "a", "jurisdiction_code": "CN", "jurisdiction_scope": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["jurisdiction_mismatches"] == 1

    def test_scope_without_code_flagged(self):
        rows = [
            {"id": "a", "jurisdiction_code": None, "jurisdiction_scope": "national"}
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["jurisdiction_mismatches"] == 1

    def test_both_populated_with_valid_scope_is_clean(self):
        rows = [
            {"id": "a", "jurisdiction_code": "CN", "jurisdiction_scope": "national"}
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["jurisdiction_mismatches"] == 0

    def test_special_zone_scope_accepted(self):
        """v4.2.2+ scopes (experimental_zone, trade_port, special_economic_zone)
        must be recognized as valid (audit Must-Fix #5)."""
        for scope in ("experimental_zone", "trade_port", "special_economic_zone"):
            rows = [{"id": "a", "jurisdiction_code": "CN", "jurisdiction_scope": scope}]
            r = survey_type(rows, today=date(2024, 6, 1))
            assert r["jurisdiction_mismatches"] == 0, f"scope {scope} should be valid"


class TestProhibitedRoles:
    """Closes 2026-04-21 audit Round 2 Tax Law: `analogy` is barred under
    税收法定 but schema whitelist alone accepts it. Survey now catches it
    as a real defect."""

    def test_analogy_role_flagged_as_defect(self):
        rows = [{"id": "a", "argument_role": "analogy"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["prohibited_role_count"] == 1
        assert r["defects_total"] >= 1

    def test_permitted_roles_not_flagged(self):
        # All 13 non-analogy roles are permitted on tax nodes
        rows = [
            {"id": f"r{i}", "argument_role": role}
            for i, role in enumerate(
                [
                    "premise", "rule", "holding", "dicta", "counter",
                    "concession", "authority",
                    "yiju", "danshu", "guoduguiding", "shouquan", "doudi", "shiyi",
                ]
            )
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["prohibited_role_count"] == 0

    def test_null_role_is_not_a_prohibition(self):
        """NULL argument_role is a coverage gap, not a prohibition breach."""
        rows = [{"id": "a", "argument_role": None}, {"id": "b"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["prohibited_role_count"] == 0

    def test_unknown_role_not_double_counted(self):
        """Unknown strings are caught by the bitemporal_query whitelist
        elsewhere; the survey silently ignores them here rather than
        double-counting the same defect."""
        rows = [{"id": "a", "argument_role": "unknown-role-xyz"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["prohibited_role_count"] == 0

    def test_multiple_analogies_counted_independently(self):
        rows = [
            {"id": "a", "argument_role": "analogy"},
            {"id": "b", "argument_role": "analogy"},
            {"id": "c", "argument_role": "yiju"},  # permitted
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["prohibited_role_count"] == 2


class TestInvalidOverrideChain:
    """Closes the silent-typo gap: override_chain_id accepts any string
    at the Cypher layer. The survey now flags non-resolvable codes so
    an operator typo doesn't linger as dark data."""

    def test_valid_national_code_not_flagged(self):
        rows = [{"id": "a", "override_chain_id": "CN"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["invalid_chain_count"] == 0

    def test_valid_iso_admin_not_flagged(self):
        rows = [
            {"id": "a", "override_chain_id": "CN-31"},
            {"id": "b", "override_chain_id": "CN-HK"},
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["invalid_chain_count"] == 0

    def test_valid_special_zone_not_flagged(self):
        rows = [
            {"id": "a", "override_chain_id": "CN-FTZ-SHA"},
            {"id": "b", "override_chain_id": "CN-GBA"},
            {"id": "c", "override_chain_id": "CN-HFTP"},
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["invalid_chain_count"] == 0

    def test_unknown_code_flagged(self):
        rows = [{"id": "a", "override_chain_id": "garbage"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["invalid_chain_count"] == 1
        assert r["defects_total"] >= 1

    def test_null_override_not_flagged_here(self):
        """NULL override_chain_id is a coverage concern, not an integrity
        breach. null_rate tracks it separately."""
        rows = [{"id": "a", "override_chain_id": None}, {"id": "b"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["invalid_chain_count"] == 0

    def test_mixed_valid_and_invalid(self):
        rows = [
            {"id": "a", "override_chain_id": "CN-FTZ-SHA"},  # valid
            {"id": "b", "override_chain_id": "FR-75"},  # invalid
            {"id": "c", "override_chain_id": "CN-ZZZ-BAD"},  # invalid
            {"id": "d", "override_chain_id": None},  # coverage gap, not defect
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["invalid_chain_count"] == 2


class TestInconsistentScope:
    """Closes audit M2 (co-variance): code + scope must be jointly valid.

    The schema whitelists each column in isolation. A ``CN-FTZ-SHA`` row
    with ``municipal`` scope passes both filters while being nonsense.
    Survey now catches the disagreement as a separate defect category,
    distinct from ``jurisdiction_mismatches`` (which catches unknown
    scope strings) and ``invalid_chain_count`` (which catches unknown
    override codes)."""

    def test_consistent_ftz_not_flagged(self):
        rows = [
            {
                "id": "a",
                "jurisdiction_code": "CN-FTZ-SHA",
                "jurisdiction_scope": "experimental_zone",
            }
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 0

    def test_ftz_with_wrong_scope_flagged(self):
        rows = [
            {
                "id": "a",
                "jurisdiction_code": "CN-FTZ-SHA",
                "jurisdiction_scope": "municipal",
            }
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 1
        assert r["defects_total"] >= 1

    def test_hainan_ftp_with_experimental_zone_flagged(self):
        """Same Hainan geography, two codes (FTZ + FTP) with different
        scopes. The test pins the co-variance at the ambiguous case."""
        rows = [
            {
                "id": "a",
                "jurisdiction_code": "CN-HFTP",
                "jurisdiction_scope": "experimental_zone",
            }
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 1

    def test_null_code_not_counted_here(self):
        rows = [{"id": "a", "jurisdiction_code": None, "jurisdiction_scope": "national"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 0

    def test_null_scope_not_counted_here(self):
        rows = [{"id": "a", "jurisdiction_code": "CN", "jurisdiction_scope": None}]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 0

    def test_unknown_code_not_counted_here(self):
        """Unknown codes are captured by other defect categories. Avoid
        double-counting so the defect_rate remains interpretable."""
        rows = [
            {"id": "a", "jurisdiction_code": "bogus", "jurisdiction_scope": "national"}
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 0

    def test_multiple_inconsistencies_counted(self):
        rows = [
            {"id": "a", "jurisdiction_code": "CN", "jurisdiction_scope": "municipal"},
            {
                "id": "b",
                "jurisdiction_code": "CN-FTZ-SHA",
                "jurisdiction_scope": "trade_port",
            },
            {
                "id": "c",
                "jurisdiction_code": "CN-31",
                "jurisdiction_scope": "subnational",
            },  # ok
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["inconsistent_scope_count"] == 2


class TestNullCoverageViolations:
    """Closes 2026-04-27 audit gap: prior gate reported per-column null_rate
    but never aggregated NULL severity into defects_total. A column where
    ≥50% of rows are NULL is treated as systematic absence (one defect unit
    per such column), not noise."""

    def test_zero_violations_when_all_columns_filled(self):
        rows = [
            {
                "id": "a",
                "effective_from": "2024-01-01",
                "confidence": 0.9,
                "source_doc_id": "doc1",
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
            }
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["null_coverage_violation_count"] == 0
        assert r["null_coverage_violations"] == []

    def test_single_column_at_100_percent_null_counts_one(self):
        rows = [{"id": f"n{i}"} for i in range(5)]  # all 5 critical cols missing
        r = survey_type(rows, today=date(2024, 6, 1))
        # All 5 CRITICAL_COLUMNS at 100% NULL → 5 violation units
        assert r["null_coverage_violation_count"] == 5
        assert "effective_from" in r["null_coverage_violations"]
        assert "source_doc_id" in r["null_coverage_violations"]

    def test_threshold_strict_below_does_not_trigger(self):
        # 4 of 10 rows NULL on effective_from = 40% < 50% threshold
        rows = [{"id": f"n{i}", "effective_from": "2024-01-01"} for i in range(6)]
        rows.extend([{"id": f"m{i}"} for i in range(4)])
        r = survey_type(rows, today=date(2024, 6, 1))
        # effective_from null_rate = 0.4, below 0.5 threshold → NOT a violation
        # but the other 4 critical columns are 100% NULL → 4 violations
        assert "effective_from" not in r["null_coverage_violations"]
        assert r["null_coverage_violation_count"] == 4

    def test_threshold_at_exactly_50_percent_triggers(self):
        # 5 of 10 rows NULL on confidence = 50% = threshold (>=)
        rows = [{"id": f"n{i}", "confidence": 0.9} for i in range(5)]
        rows.extend([{"id": f"m{i}"} for i in range(5)])
        r = survey_type(rows, today=date(2024, 6, 1))
        assert "confidence" in r["null_coverage_violations"]

    def test_custom_threshold_overrides_default(self):
        # 3 of 10 rows NULL on source_doc_id = 30%
        rows = [{"id": f"n{i}", "source_doc_id": "d1"} for i in range(7)]
        rows.extend([{"id": f"m{i}"} for i in range(3)])
        # With strict 0.20 threshold, 30% triggers
        r_strict = survey_type(rows, today=date(2024, 6, 1),
                               null_coverage_threshold=0.20)
        assert "source_doc_id" in r_strict["null_coverage_violations"]
        # With default 0.50 threshold, 30% does not trigger
        r_default = survey_type(rows, today=date(2024, 6, 1))
        assert "source_doc_id" not in r_default["null_coverage_violations"]

    def test_empty_sample_does_not_create_phantom_defects(self):
        # Empty sample = missing table; reported via fetch_misses, not
        # double-counted as 5 NULL-coverage defects
        r = survey_type([], today=date(2024, 6, 1))
        assert r["null_coverage_violation_count"] == 0
        assert r["null_coverage_violations"] == []
        assert r["defects_total"] == 0

    def test_defects_total_includes_null_coverage(self):
        # Single row, all critical cols NULL
        rows = [{"id": "a"}]
        r = survey_type(rows, today=date(2024, 6, 1))
        # 5 NULL-coverage violations + 0 from other categories
        assert r["null_coverage_violation_count"] == 5
        assert r["defects_total"] == 5

    def test_threshold_disabled_at_1_0(self):
        # With threshold=1.0, only fully-NULL columns count.
        # All 5 critical cols at 100% NULL → all 5 still trigger (>= 1.0)
        rows = [{"id": "a"}]
        r_max = survey_type(rows, today=date(2024, 6, 1),
                            null_coverage_threshold=1.0)
        assert r_max["null_coverage_violation_count"] == 5


class TestCompoundDefects:
    """Compound-defect fixtures use `null_coverage_threshold=1.0` to isolate
    the per-row defect categories from the new column-level NULL coverage
    check (added 2026-04-27). Tests dedicated to NULL coverage live in
    TestNullCoverageViolations."""

    _NCT = 1.01  # threshold > 1.0 disables null-coverage entirely (null_rate ≤ 1.0)

    def test_defects_sum_across_categories(self):
        rows = [
            {"id": "x"},  # will dupe with next
            {"id": "x"},  # dup
            {"id": "y", "effective_from": "1990-01-01"},  # stale
            {"id": "z", "reviewed_at": "2024-01-01", "reviewed_by": None},  # integrity
            {"id": "w", "jurisdiction_scope": "galactic"},  # jurisdiction
        ]
        r = survey_type(
            rows, today=date(2024, 6, 1), stale_years=10,
            null_coverage_threshold=self._NCT,
        )
        assert r["duplicate_id_count"] == 1
        assert r["stale_count"] == 1
        assert r["integrity_violations"] == 1
        assert r["jurisdiction_mismatches"] == 1
        assert r["prohibited_role_count"] == 0
        assert r["null_coverage_violation_count"] == 0  # disabled by threshold
        assert r["defects_total"] == 4
        assert r["defect_rate"] == 0.8  # 4/5

    def test_prohibited_role_sums_with_other_defects(self):
        rows = [
            {"id": "x"},
            {"id": "x"},  # dup
            {"id": "y", "argument_role": "analogy"},  # prohibited
            {"id": "z", "argument_role": "analogy"},  # prohibited
        ]
        r = survey_type(
            rows, today=date(2024, 6, 1),
            null_coverage_threshold=self._NCT,
        )
        assert r["duplicate_id_count"] == 1
        assert r["prohibited_role_count"] == 2
        assert r["null_coverage_violation_count"] == 0  # disabled by threshold
        assert r["defects_total"] == 3
        assert r["defect_rate"] == 0.75


# -------------------------------------------------------------------------
# Placeholder banlist (10th defect dimension) — Goodhart guard
# -------------------------------------------------------------------------
#
# Closes Round-1 Munger inversion: lineage strings like 'unknown' / 'TBD' /
# 'default' / '' must NOT pass as legitimate attribution. Banlist match is
# case-insensitive and whitespace-stripped (closes Round-2 Munger
# same-name-variant bypass: 'Unknown', '  ', ' default ').
#
# Banlist applies ONLY to LINEAGE_STRING_FIELDS — true NULL is counted by
# null_rate, not double-counted here. Non-string types pass through.


class TestPlaceholderStrings:
    # Canonical clean lineage — mirrors the shape used in
    # TestSurveyTypeBasics.test_clean_sample_has_zero_defects so the row
    # produces ZERO defects across ALL nine prior dimensions. Any new
    # dimension test on top of this fixture must remain isolated to its
    # own metric, so defects_total integration tests are clean.
    _CLEAN_LINEAGE: dict = {
        "effective_from": "2024-01-01",
        "confidence": 0.9,
        "source_doc_id": "doc_123",
        "extracted_by": "extractor_v2",
        "reviewed_at": "2024-01-02",  # paired with reviewed_by — no XOR violation
        "reviewed_by": "maurice",
        "jurisdiction_code": "CN",
        "jurisdiction_scope": "national",
        # override_chain_id intentionally omitted — NULL is permitted and
        # avoids invalid_chain whitelist mismatch noise in defects_total.
    }

    def _row(self, **overrides) -> dict:
        return {"id": "n1", **self._CLEAN_LINEAGE, **overrides}

    def test_no_placeholder_clean(self):
        # 5 rows fully populated with legitimate strings → 0 hits.
        rows = [self._row(id=f"n{i}") for i in range(5)]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["placeholder_string_count"] == 0
        assert all(v == 0 for v in r["placeholder_per_field"].values())

    def test_unknown_lowercase_flagged(self):
        rows = [self._row(source_doc_id="unknown")]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["placeholder_string_count"] == 1
        assert r["placeholder_per_field"]["source_doc_id"] == 1

    def test_unknown_uppercase_flagged_case_insensitive(self):
        # Both 'Unknown' and 'UNKNOWN' must trigger — same-name-variant bypass closure.
        rows = [
            self._row(id="n1", source_doc_id="Unknown"),
            self._row(id="n2", source_doc_id="UNKNOWN"),
            self._row(id="n3", source_doc_id="UnKnOwN"),
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["placeholder_string_count"] == 3
        assert r["placeholder_per_field"]["source_doc_id"] == 3

    def test_whitespace_stripped_flagged(self):
        # ' default ', '  ', '\tTBD\n' — strip then lowercase before banlist match.
        rows = [
            self._row(id="n1", extracted_by=" default "),
            self._row(id="n2", reviewed_by="  "),
            self._row(id="n3", override_chain_id="\tTBD\n"),
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["placeholder_string_count"] == 3
        assert r["placeholder_per_field"]["extracted_by"] == 1
        assert r["placeholder_per_field"]["reviewed_by"] == 1
        assert r["placeholder_per_field"]["override_chain_id"] == 1

    def test_empty_string_in_lineage_field_flagged(self):
        # '' is in the banlist — note this OVERLAPS with null_rate (which also
        # treats '' as NULL). Both metrics fire independently; that's intended:
        # null_rate signals absence, banlist signals "absence with intent to
        # appear present". Here we assert banlist sees it.
        rows = [self._row(jurisdiction_code="")]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["placeholder_string_count"] == 1
        assert r["placeholder_per_field"]["jurisdiction_code"] == 1

    def test_normal_string_not_flagged(self):
        # Legitimate IDs like 'doc_123' / 'extractor_v2' / 'CN' must pass.
        rows = [
            self._row(id="n1", source_doc_id="doc_unknown_subset_2024"),  # contains 'unknown' substring but not equal
            self._row(id="n2", extracted_by="default_extractor_v3"),  # contains 'default' substring but not equal
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        # Banlist matches whole-token after strip+lower, NOT substring.
        assert r["placeholder_string_count"] == 0

    def test_multiple_fields_count_independently(self):
        # One row with placeholder in 3 different lineage fields → 3 hits.
        rows = [
            self._row(
                source_doc_id="unknown",
                extracted_by="TBD",
                jurisdiction_code="N/A",
            ),
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        assert r["placeholder_string_count"] == 3
        assert r["placeholder_per_field"]["source_doc_id"] == 1
        assert r["placeholder_per_field"]["extracted_by"] == 1
        assert r["placeholder_per_field"]["jurisdiction_code"] == 1

    def test_non_string_value_not_flagged(self):
        # None / 42 / [] are not strings → banlist skips. None IS counted by
        # null_rate, but that's a separate dimension (sums independently).
        rows = [
            self._row(id="n1", source_doc_id=None),
            self._row(id="n2", extracted_by=42),
            self._row(id="n3", reviewed_by=[]),
        ]
        r = survey_type(rows, today=date(2024, 6, 1))
        # Banlist sees zero — only strings are evaluated.
        assert r["placeholder_string_count"] == 0

    def test_defects_total_includes_placeholder_count(self):
        # Integration: a placeholder-only row must contribute to defects_total
        # via the new dimension, even when other dimensions are clean.
        rows = [
            self._row(id=f"n{i}", source_doc_id="unknown")
            for i in range(4)
        ]
        # Disable null-coverage threshold (CRITICAL_COLUMNS are populated except
        # source_doc_id which is a banned string, NOT NULL).
        r = survey_type(
            rows,
            today=date(2024, 6, 1),
            null_coverage_threshold=1.01,
        )
        assert r["placeholder_string_count"] == 4
        # Other dimensions clean → defects_total == placeholder_string_count.
        assert r["duplicate_id_count"] == 0
        assert r["null_coverage_violation_count"] == 0
        assert r["defects_total"] == 4
        assert r["defect_rate"] == 1.0


# -------------------------------------------------------------------------
# survey — orchestration over a stub connection
# -------------------------------------------------------------------------


class _FakeDF:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def to_dict(self, orient: str = "records") -> list[dict]:
        return list(self._rows)


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def get_as_df(self) -> _FakeDF:
        return _FakeDF(self._rows)


class _FakeConn:
    """Returns the same fixture for every type, so the report is deterministic."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.executed: list[str] = []

    def execute(self, cypher: str) -> _FakeResult:
        self.executed.append(cypher)
        return _FakeResult(self._rows)


class TestSurveyOrchestration:
    """Orchestration tests use rich fixtures (all 5 critical columns set) so
    they exercise duplicate / stale / integrity / jurisdiction defect paths
    in isolation. NULL-coverage behavior is covered by
    TestNullCoverageViolations."""

    def test_clean_data_gives_pass(self, tmp_path):
        schema = tmp_path / "schema.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY(id));\n"
            "CREATE NODE TABLE TaxType (id STRING, PRIMARY KEY(id));\n"
        )
        conn = _FakeConn(
            [
                {
                    "id": f"n{i}",
                    "effective_from": "2024-01-01",
                    "confidence": 0.9,
                    "source_doc_id": "doc1",
                    "jurisdiction_code": "CN",
                    "jurisdiction_scope": "national",
                    "reviewed_at": "2024-01-02",
                    "reviewed_by": "m",
                }
                for i in range(5)
            ]
        )
        r = survey(conn, sample_size=5, schema_path=schema)
        assert r["overall"]["verdict"] == "PASS"
        assert r["overall"]["defect_rate"] == 0.0
        # Every canonical type got queried
        assert len(conn.executed) == 2

    def test_dirty_data_gives_fail(self, tmp_path):
        schema = tmp_path / "schema.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY(id));\n")
        dirty = [
            {"id": "dup"},
            {"id": "dup"},  # duplicate
            {"id": "stale", "effective_from": "1990-01-01"},
        ]
        r = survey(conn=_FakeConn(dirty), sample_size=3, schema_path=schema)
        assert r["overall"]["verdict"] == "FAIL"
        assert r["overall"]["total_defects"] >= 2

    def test_sample_size_flows_into_cypher_limit(self, tmp_path):
        schema = tmp_path / "schema.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY(id));\n")
        conn = _FakeConn([])
        survey(conn, sample_size=42, schema_path=schema)
        assert "LIMIT 42" in conn.executed[0]

    def test_target_defect_rate_controls_verdict(self, tmp_path):
        schema = tmp_path / "schema.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY(id));\n")
        # Fixture: 2 dup rows BUT with all 5 critical cols filled, so the
        # only defect category exercised is duplicate detection (1 defect / 2 rows = 0.5).
        rows = [
            {
                "id": "dup",
                "effective_from": "2024-01-01",
                "confidence": 0.9,
                "source_doc_id": "doc1",
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
            },
            {
                "id": "dup",
                "effective_from": "2024-01-01",
                "confidence": 0.9,
                "source_doc_id": "doc1",
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
            },
        ]
        # With generous target 0.6, should PASS (defect_rate 0.5 <= 0.6)
        r = survey(
            _FakeConn(rows), sample_size=2, schema_path=schema, target_defect_rate=0.6
        )
        assert r["overall"]["verdict"] == "PASS"
        # With strict target 0.1, should FAIL (defect_rate 0.5 > 0.1)
        r = survey(
            _FakeConn(rows), sample_size=2, schema_path=schema, target_defect_rate=0.1
        )
        assert r["overall"]["verdict"] == "FAIL"


# -------------------------------------------------------------------------
# CLI — smoke test via script import
# -------------------------------------------------------------------------


class TestCLI:
    def test_missing_db_returns_exit_2(self, tmp_path, capsys):
        import importlib.util

        script = tmp_path.parent.parent / "scripts" / "data_quality_survey.py"
        # Use the actual script via relative resolution.
        from pathlib import Path

        real_script = (
            Path(__file__).resolve().parent.parent
            / "scripts"
            / "data_quality_survey.py"
        )
        spec = importlib.util.spec_from_file_location("_dqs_cli", real_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        code = module.main(["--db", "/nonexistent/path/that/does/not/exist"])
        assert code == 2

    def test_render_summary_has_verdict_line(self):
        from pathlib import Path
        import importlib.util

        real_script = (
            Path(__file__).resolve().parent.parent
            / "scripts"
            / "data_quality_survey.py"
        )
        spec = importlib.util.spec_from_file_location("_dqs_cli", real_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        fake_report = {
            "overall": {
                "total_sampled": 100,
                "canonical_types_surveyed": 5,
                "total_defects": 3,
                "defect_rate": 0.03,
                "target_defect_rate": 0.10,
                "verdict": "PASS",
            },
            "per_type": {
                "TaxRate": {
                    "sampled": 20,
                    "defect_rate": 0.05,
                    "duplicate_id_count": 1,
                    "stale_count": 0,
                    "integrity_violations": 0,
                    "jurisdiction_mismatches": 0,
                },
            },
        }
        summary = module.render_summary(fake_report)
        assert "PASS" in summary
        assert "TaxRate" in summary
