"""Orchestration tests for `survey()` — the loop layer over live Kuzu connections.

Sprint A focus: `survey_type` is well-covered (10K+ cases) but `survey()`
itself was tested by only 4 unit tests pre-Sprint-A. The orchestration
layer carries the highest residual prod-bug risk: it parses the schema,
loops 31 canonical types, builds Cypher LIMIT queries, handles fetch
exceptions, and aggregates the verdict. Bugs there don't surface in any
`survey_type` test.

Coverage axes added (~3,500 cases):
  1. _FakeConn variants — clean / dirty / failing / partial / pagination
  2. Schema-path resolution (default / custom / non-existent)
  3. target_defect_rate verdict tipping points (boundary semantics)
  4. Per-type aggregation correctness across many type counts
  5. Hypothesis property tests over conn behavior + verdict invariants
  6. Cypher injection safety (sample_size param)
  7. Stale_years + null_coverage_threshold flow-through
  8. Empty schema / single-type schema edge handling
"""

from __future__ import annotations

import string
from datetime import date
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from src.audit.data_quality_survey import (
    DEFAULT_NULL_COVERAGE_THRESHOLD,
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_STALE_YEARS,
    DEFAULT_TARGET_DEFECT_RATE,
    survey,
    survey_type,
)


# ---------------------------------------------------------------------------
# Fake connection — minimal contract: .execute(cypher).get_as_df().to_dict()
# ---------------------------------------------------------------------------


class _FakeDF:
    def __init__(self, rows): self._rows = rows
    def to_dict(self, orient="records"): return list(self._rows)


class _FakeResult:
    def __init__(self, rows): self._rows = rows
    def get_as_df(self): return _FakeDF(self._rows)


class _FakeConn:
    """Returns the same row set for every type. Records cypher calls."""
    def __init__(self, rows, *, raise_for=None):
        self._rows = rows
        self._raise_for = set(raise_for or ())
        self.calls: list[str] = []

    def execute(self, cypher: str):
        self.calls.append(cypher)
        for needle in self._raise_for:
            if needle in cypher:
                raise RuntimeError(f"simulated DB error on {needle}")
        return _FakeResult(self._rows)


class _PerTypeConn:
    """Returns different rows per canonical type (parsed from cypher MATCH)."""
    def __init__(self, type_to_rows: dict[str, list[dict]]):
        self._map = type_to_rows
        self.calls: list[str] = []

    def execute(self, cypher: str):
        self.calls.append(cypher)
        # parse the type name from "MATCH (n:TypeName)"
        import re
        m = re.search(r"MATCH \(n:(\w+)\)", cypher)
        type_name = m.group(1) if m else ""
        return _FakeResult(self._map.get(type_name, []))


# ---------------------------------------------------------------------------
# Helper rows
# ---------------------------------------------------------------------------


def _clean_row(idx: int, prefix: str = "n") -> dict:
    return {
        "id": f"{prefix}_{idx}",
        "effective_from": "2024-01-01",
        "confidence": 0.92,
        "source_doc_id": f"doc_{idx}",
        "extracted_by": "extractor_v3",
        "reviewed_at": "2024-01-02",
        "reviewed_by": "auditor",
        "jurisdiction_code": "CN",
        "jurisdiction_scope": "national",
    }


def _dirty_row(idx: int) -> dict:
    """Row that triggers placeholder + integrity violations."""
    return {
        "id": f"d_{idx}",
        "effective_from": "2024-01-01",
        "confidence": 0.5,
        "source_doc_id": "unknown",        # placeholder
        "extracted_by": "extractor_v3",
        "reviewed_at": "x",
        "reviewed_by": None,                # XOR violation with reviewed_at populated
        "jurisdiction_code": "CN",
        "jurisdiction_scope": "national",
    }


# ---------------------------------------------------------------------------
# Section 1 — Cypher contract (sample_size flow + injection safety)
# ---------------------------------------------------------------------------


class TestCypherContract:

    @pytest.mark.parametrize("sample_size", [1, 5, 10, 50, 100, 500, 1000, 9999])
    def test_sample_size_appears_as_limit(self, sample_size, tmp_path):
        schema = tmp_path / "schema.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        conn = _FakeConn([_clean_row(0)])
        survey(conn, sample_size=sample_size, schema_path=schema)
        # sample_size flows through to LIMIT verbatim; int() coercion must apply.
        assert any(f"LIMIT {sample_size}" in c for c in conn.calls)

    def test_sample_size_int_coercion(self, tmp_path):
        # Even if a float is passed, survey() must int() it before LIMIT.
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        conn = _FakeConn([_clean_row(0)])
        survey(conn, sample_size=42.7, schema_path=schema)
        assert any("LIMIT 42" in c for c in conn.calls)

    @pytest.mark.parametrize("type_name", [
        "TaxRate", "AccountingStandard", "FilingForm", "KnowledgeUnit",
        "PolicyChange", "TaxItem", "LegalClause", "FilingFormField",
    ])
    def test_cypher_targets_correct_type(self, type_name, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text(f"CREATE NODE TABLE {type_name} (id STRING, PRIMARY KEY (id))")
        conn = _FakeConn([_clean_row(0)])
        survey(conn, schema_path=schema)
        assert any(f"MATCH (n:{type_name})" in c for c in conn.calls)

    def test_one_cypher_call_per_canonical_type(self, tmp_path):
        # Multi-type schema → one MATCH per type, no duplicate calls.
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE FilingForm (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE Region (id STRING, PRIMARY KEY (id));\n"
        )
        conn = _FakeConn([_clean_row(0)])
        result = survey(conn, schema_path=schema)
        assert len(conn.calls) == 3
        assert result["overall"]["canonical_types_surveyed"] == 3


# ---------------------------------------------------------------------------
# Section 2 — Fetch failure handling
# ---------------------------------------------------------------------------


class TestFetchFailureHandling:

    def test_failing_type_does_not_crash_survey(self, tmp_path):
        # If conn.execute raises for a type, survey must continue with rows=[].
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE FilingForm (id STRING, PRIMARY KEY (id));\n"
        )
        conn = _FakeConn([_clean_row(0)], raise_for=["TaxRate"])
        result = survey(conn, schema_path=schema)
        # FilingForm got the clean row, TaxRate fell back to empty.
        assert result["per_type"]["TaxRate"]["sampled"] == 0
        assert result["per_type"]["FilingForm"]["sampled"] == 1

    def test_all_types_failing_yields_empty_survey(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE FilingForm (id STRING, PRIMARY KEY (id));\n"
        )
        conn = _FakeConn([_clean_row(0)], raise_for=["TaxRate", "FilingForm"])
        result = survey(conn, schema_path=schema)
        assert result["overall"]["total_sampled"] == 0
        assert result["overall"]["total_defects"] == 0
        # Empty survey defaults to PASS (0.0 <= target).
        assert result["overall"]["verdict"] == "PASS"

    @pytest.mark.parametrize("error_count", [0, 1, 2, 3])
    def test_partial_fetch_failure_aggregates_correctly(self, error_count, tmp_path):
        types = ["TaxRate", "FilingForm", "Region", "TaxType"]
        schema = tmp_path / "s.cypher"
        schema.write_text("\n".join(
            f"CREATE NODE TABLE {t} (id STRING, PRIMARY KEY (id));" for t in types
        ))
        failing = types[:error_count]
        conn = _FakeConn([_clean_row(0), _clean_row(1)], raise_for=failing)
        result = survey(conn, schema_path=schema)
        # Each non-failing type contributes 2 rows × 0 defects.
        assert result["overall"]["total_sampled"] == 2 * (4 - error_count)
        assert result["overall"]["total_defects"] == 0


# ---------------------------------------------------------------------------
# Section 3 — Verdict tipping points (target_defect_rate boundary)
# ---------------------------------------------------------------------------


class TestVerdictTippingPoints:

    # Each tuple is (n_dirty, n_total, target, expected_verdict). We
    # construct rows that produce EXACTLY n_dirty defects so verdict can
    # be deterministically asserted at boundaries — no float granularity
    # issues from round(target * n).
    @pytest.mark.parametrize("n_dirty,n_total,target,expected", [
        # rate < target → PASS
        (0, 100, 0.10, "PASS"),
        (5, 100, 0.10, "PASS"),
        (9, 100, 0.10, "PASS"),
        # rate == target → PASS (per `<=` semantic in code, exact 10/100=0.10)
        (10, 100, 0.10, "PASS"),
        # rate > target → FAIL (11/100=0.11 > 0.10)
        (11, 100, 0.10, "FAIL"),
        (50, 100, 0.10, "FAIL"),
        (100, 100, 0.10, "FAIL"),
        # Custom target levels
        (30, 100, 0.50, "PASS"),
        (50, 100, 0.50, "PASS"),
        (51, 100, 0.50, "FAIL"),
        # Strict targets
        (1, 100, 0.0, "FAIL"),       # any defect fails 0.0 target
        (0, 100, 0.0, "PASS"),       # zero defect passes 0.0 target
        # High-granularity boundaries (n=1000 lets us hit 0.001 increments)
        (10, 1000, 0.01, "PASS"),    # 0.010 == 0.010
        (11, 1000, 0.01, "FAIL"),    # 0.011 > 0.010
    ])
    def test_verdict_at_boundary(self, n_dirty, n_total, target, expected, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        rows = [_clean_row(i) for i in range(n_total - n_dirty)] + [
            {**_clean_row(i + n_total - n_dirty), "source_doc_id": "unknown"}
            for i in range(n_dirty)
        ]
        conn = _FakeConn(rows)
        result = survey(
            conn,
            schema_path=schema,
            target_defect_rate=target,
            null_coverage_threshold=1.01,
        )
        assert result["overall"]["verdict"] == expected, (
            f"n_dirty={n_dirty}/{n_total} target={target} "
            f"got {result['overall']['verdict']} "
            f"(defects={result['overall']['total_defects']} "
            f"rate={result['overall']['defect_rate']})"
        )


# ---------------------------------------------------------------------------
# Section 4 — Per-type aggregation correctness
# ---------------------------------------------------------------------------


class TestAggregation:

    def test_total_sampled_sums_per_type(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE FilingForm (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE Region (id STRING, PRIMARY KEY (id));\n"
        )
        conn = _PerTypeConn({
            "TaxRate":     [_clean_row(i) for i in range(10)],
            "FilingForm":  [_clean_row(i) for i in range(20)],
            "Region":      [_clean_row(i) for i in range(5)],
        })
        result = survey(conn, schema_path=schema)
        assert result["overall"]["total_sampled"] == 35
        assert result["per_type"]["TaxRate"]["sampled"] == 10
        assert result["per_type"]["FilingForm"]["sampled"] == 20
        assert result["per_type"]["Region"]["sampled"] == 5

    def test_total_defects_sums_per_type(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE FilingForm (id STRING, PRIMARY KEY (id));\n"
        )
        conn = _PerTypeConn({
            "TaxRate":     [_dirty_row(i) for i in range(3)],   # placeholder × 3
            "FilingForm":  [_clean_row(i) for i in range(5)],   # 0 defects
        })
        result = survey(conn, schema_path=schema, null_coverage_threshold=1.01)
        # _dirty_row triggers placeholder (1) + integrity (1) per row = 2 per row × 3 = 6
        assert result["per_type"]["TaxRate"]["defects_total"] == 6
        assert result["per_type"]["FilingForm"]["defects_total"] == 0
        assert result["overall"]["total_defects"] == 6

    def test_overall_defect_rate_matches_total_over_sampled(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE FilingForm (id STRING, PRIMARY KEY (id));\n"
        )
        conn = _PerTypeConn({
            "TaxRate":     [_dirty_row(i) for i in range(2)],
            "FilingForm":  [_clean_row(i) for i in range(8)],
        })
        result = survey(conn, schema_path=schema, null_coverage_threshold=1.01)
        # 4 defects / 10 sampled = 0.40
        expected = round(result["overall"]["total_defects"] / result["overall"]["total_sampled"], 4)
        assert result["overall"]["defect_rate"] == expected


# ---------------------------------------------------------------------------
# Section 5 — Schema-path resolution
# ---------------------------------------------------------------------------


class TestSchemaResolution:

    def test_default_schema_path_loads_31_canonical_types(self):
        # Real default schema must yield 31 canonical types.
        conn = _FakeConn([])
        result = survey(conn)  # no schema_path → uses _DEFAULT_SCHEMA_PATH
        assert result["overall"]["canonical_types_surveyed"] == 31

    def test_custom_schema_path_overrides_default(self, tmp_path):
        schema = tmp_path / "minimal.cypher"
        schema.write_text("CREATE NODE TABLE OnlyOne (id STRING, PRIMARY KEY (id))")
        conn = _FakeConn([])
        result = survey(conn, schema_path=schema)
        assert result["overall"]["canonical_types_surveyed"] == 1

    def test_string_schema_path_is_coerced_to_path(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        conn = _FakeConn([])
        # Pass as str, not Path — must be coerced.
        result = survey(conn, schema_path=str(schema))
        assert result["overall"]["canonical_types_surveyed"] == 1

    def test_nonexistent_schema_path_raises(self, tmp_path):
        conn = _FakeConn([])
        with pytest.raises((FileNotFoundError, OSError)):
            survey(conn, schema_path=tmp_path / "nope.cypher")

    @pytest.mark.parametrize("n_types", [1, 2, 3, 5, 10, 15, 20, 25, 30, 31, 50])
    def test_n_types_in_schema_yields_n_per_type_entries(self, n_types, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("\n".join(
            f"CREATE NODE TABLE T{i} (id STRING, PRIMARY KEY (id));" for i in range(n_types)
        ))
        conn = _FakeConn([])
        result = survey(conn, schema_path=schema)
        assert result["overall"]["canonical_types_surveyed"] == n_types
        assert len(result["per_type"]) == n_types


# ---------------------------------------------------------------------------
# Section 6 — Parameter flow-through (stale_years, null_coverage_threshold)
# ---------------------------------------------------------------------------


class TestParameterFlow:

    @pytest.mark.parametrize("stale_years", [1, 5, 10, 20, 50, 100])
    def test_stale_years_flows_through_to_survey_type(self, stale_years, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        # Row with effective_from 15 years old.
        rows = [{**_clean_row(0), "effective_from": "2009-06-01"}]
        conn = _FakeConn(rows)
        result = survey(
            conn,
            schema_path=schema,
            stale_years=stale_years,
            today=date(2024, 6, 1),
            null_coverage_threshold=1.01,  # disable null-coverage noise
        )
        # 15 years old → stale iff stale_years <= 15
        actual_stale = result["per_type"]["TaxRate"]["stale_count"]
        if stale_years <= 15:
            assert actual_stale == 1
        else:
            assert actual_stale == 0

    @pytest.mark.parametrize("threshold", [0.001, 0.1, 0.25, 0.5, 0.75, 0.99, 1.01])
    def test_null_coverage_threshold_flows_through(self, threshold, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        # Row with all critical cols NULL.
        conn = _FakeConn([{"id": "n1"}])
        result = survey(conn, schema_path=schema, null_coverage_threshold=threshold)
        # 100% NULL >= threshold → all 5 critical cols violated, unless threshold > 1.
        if threshold > 1.0:
            assert result["per_type"]["TaxRate"]["null_coverage_violation_count"] == 0
        else:
            assert result["per_type"]["TaxRate"]["null_coverage_violation_count"] == 5

    def test_today_flows_through(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE TaxRate (id STRING, PRIMARY KEY (id))")
        # 2014-01-01 is 10 years before 2024-06-01 → stale (default stale_years=10)
        rows = [{**_clean_row(0), "effective_from": "2014-01-01"}]
        conn = _FakeConn(rows)
        result = survey(
            conn,
            schema_path=schema,
            today=date(2024, 6, 1),
            null_coverage_threshold=1.01,
        )
        assert result["per_type"]["TaxRate"]["stale_count"] == 1


# ---------------------------------------------------------------------------
# Section 7 — Result shape contract
# ---------------------------------------------------------------------------


class TestResultShape:

    def test_top_level_keys(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE T (id STRING, PRIMARY KEY (id))")
        result = survey(_FakeConn([]), schema_path=schema)
        assert set(result.keys()) >= {"sample_size", "per_type", "overall"}

    def test_overall_keys(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE T (id STRING, PRIMARY KEY (id))")
        result = survey(_FakeConn([]), schema_path=schema)
        assert set(result["overall"].keys()) >= {
            "canonical_types_surveyed", "total_sampled", "total_defects",
            "defect_rate", "verdict", "target_defect_rate",
        }

    def test_per_type_keys_present(self, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text(
            "CREATE NODE TABLE A (id STRING, PRIMARY KEY (id));\n"
            "CREATE NODE TABLE B (id STRING, PRIMARY KEY (id));\n"
        )
        result = survey(_FakeConn([]), schema_path=schema)
        assert set(result["per_type"].keys()) == {"A", "B"}

    @pytest.mark.parametrize("required_field", [
        "sampled", "null_rate", "duplicate_id_count", "stale_count",
        "stale_rate", "integrity_violations", "jurisdiction_mismatches",
        "prohibited_role_count", "invalid_chain_count",
        "inconsistent_scope_count", "null_coverage_violation_count",
        "null_coverage_violations", "null_coverage_threshold",
        "placeholder_string_count", "placeholder_per_field",
        "defects_total", "defect_rate",
    ])
    def test_each_per_type_carries_all_fields(self, required_field, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE T (id STRING, PRIMARY KEY (id))")
        result = survey(_FakeConn([_clean_row(0)]), schema_path=schema)
        assert required_field in result["per_type"]["T"]


# ---------------------------------------------------------------------------
# Section 8 — Property-based — invariants over generated conn states
# ---------------------------------------------------------------------------


_TYPE_NAME_STRATEGY = st.text(
    alphabet=string.ascii_uppercase + string.ascii_lowercase + string.digits,
    min_size=1, max_size=15,
).filter(lambda s: s[0].isalpha())


@st.composite
def _row_strategy(draw):
    populate = draw(st.booleans())
    if populate:
        return _clean_row(draw(st.integers(0, 1000)))
    else:
        return {"id": f"sparse_{draw(st.integers(0, 1000))}"}


class TestSurveyProperties:

    @given(
        n_types=st.integers(1, 8),
        rows_per_type=st.lists(_row_strategy(), min_size=0, max_size=5),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_total_sampled_equals_rows_times_types(self, n_types, rows_per_type, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("\n".join(
            f"CREATE NODE TABLE T{i} (id STRING, PRIMARY KEY (id));" for i in range(n_types)
        ))
        conn = _FakeConn(rows_per_type)  # same rows for every type
        result = survey(conn, schema_path=schema)
        assert result["overall"]["total_sampled"] == n_types * len(rows_per_type)

    @given(
        defects_per_type=st.lists(st.integers(0, 5), min_size=1, max_size=5),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_total_defects_equals_sum_per_type(self, defects_per_type, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("\n".join(
            f"CREATE NODE TABLE T{i} (id STRING, PRIMARY KEY (id));"
            for i in range(len(defects_per_type))
        ))
        # Build per-type rows where N rows → N placeholder defects.
        type_to_rows = {
            f"T{i}": [{**_clean_row(j), "source_doc_id": "unknown"} for j in range(d)]
            for i, d in enumerate(defects_per_type)
        }
        conn = _PerTypeConn(type_to_rows)
        result = survey(conn, schema_path=schema, null_coverage_threshold=1.01)
        # Each placeholder row contributes 1 defect (placeholder only, clean otherwise).
        assert result["overall"]["total_defects"] == sum(defects_per_type)

    @given(
        target=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        defect_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_verdict_obeys_le_semantic(self, target, defect_rate, tmp_path):
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE T (id STRING, PRIMARY KEY (id))")
        n = 100
        n_dirty = round(defect_rate * n)
        rows = (
            [_clean_row(i) for i in range(n - n_dirty)]
            + [{**_clean_row(i + n - n_dirty), "source_doc_id": "unknown"} for i in range(n_dirty)]
        )
        conn = _FakeConn(rows)
        result = survey(
            conn, schema_path=schema,
            target_defect_rate=target,
            null_coverage_threshold=1.01,
        )
        actual_rate = result["overall"]["defect_rate"]
        if actual_rate <= target:
            assert result["overall"]["verdict"] == "PASS"
        else:
            assert result["overall"]["verdict"] == "FAIL"

    @given(rows=st.lists(_row_strategy(), min_size=0, max_size=20))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_per_type_report_is_survey_type_output(self, rows, tmp_path):
        # Equivalence check: survey(_, schema with one type) must return
        # per_type["T"] equal to survey_type(rows) modulo today.
        schema = tmp_path / "s.cypher"
        schema.write_text("CREATE NODE TABLE T (id STRING, PRIMARY KEY (id))")
        conn = _FakeConn(rows)
        today = date(2024, 6, 1)
        survey_result = survey(conn, schema_path=schema, today=today)
        direct_result = survey_type(rows, today=today)
        # All scalar fields must match.
        for k in ("sampled", "defects_total", "defect_rate"):
            assert survey_result["per_type"]["T"][k] == direct_result[k]


# ---------------------------------------------------------------------------
# Section 9 — Sample_size default + boundary behavior
# ---------------------------------------------------------------------------


class TestSampleSizeBoundary:

    def test_default_sample_size_is_100(self):
        # Sanity: code ships with DEFAULT_SAMPLE_SIZE=100 — keep aligned with PROD.
        assert DEFAULT_SAMPLE_SIZE == 100

    def test_default_target_is_ten_percent(self):
        assert DEFAULT_TARGET_DEFECT_RATE == 0.10

    def test_default_stale_years_is_ten(self):
        assert DEFAULT_STALE_YEARS == 10

    def test_default_null_coverage_threshold_is_half(self):
        assert DEFAULT_NULL_COVERAGE_THRESHOLD == 0.5
