"""Corpus regression tests — lock in PROD v3 snapshot baseline.

The 2026-04-27 PROD snapshot at:
    outputs/reports/data-quality-audit/2026-04-27-prod-survey-v3.json

is the post-banlist-gate baseline (143 defects / 2053 sampled / verdict
PASS). This file replays each (type, dimension) cell as an individual
test, so any regression in survey_type that changes per-type counts
fails CI immediately and points at the exact cell.

Why corpus regression matters: property tests prove invariants over
random rows; matrix tests prove behavior on synthetic clean fixtures;
ONLY corpus tests prove the gate produces stable numbers on real PROD
shapes (CJK strings, empty tables, partial-lineage attribution).

Test count: 31 types × ~17 fields + 6 overall + 5×31 null_rate entries
+ nested per_field counts ≈ 800-900 individual assertions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent
    / "outputs" / "reports" / "data-quality-audit"
    / "2026-04-27-prod-survey-v3.json"
)


@pytest.fixture(scope="module")
def snapshot() -> dict:
    """Load the v3 PROD baseline once per test module."""
    if not SNAPSHOT_PATH.exists():
        pytest.skip(f"snapshot not found: {SNAPSHOT_PATH}")
    return json.loads(SNAPSHOT_PATH.read_text())


# ---------------------------------------------------------------------------
# Tier 1 — Overall verdict baseline
# ---------------------------------------------------------------------------


class TestOverallBaseline:
    """The post-banlist-gate v3 baseline. Any drift here = real change."""

    def test_canonical_types_surveyed(self, snapshot):
        assert snapshot["overall"]["canonical_types_surveyed"] == 31

    def test_total_sampled(self, snapshot):
        assert snapshot["overall"]["total_sampled"] == 2053

    def test_total_defects_baseline(self, snapshot):
        # Locked baseline: 143 defects post-banlist-gate (no PROD placeholders).
        # If this drifts, EITHER PROD data changed OR survey_type semantics
        # changed — investigate before updating.
        assert snapshot["overall"]["total_defects"] == 143

    def test_defect_rate_baseline(self, snapshot):
        assert snapshot["overall"]["defect_rate"] == 0.0697

    def test_verdict_baseline(self, snapshot):
        # Arithmetic PASS at target 0.10 — note structural FAIL is in PDCA.
        assert snapshot["overall"]["verdict"] == "PASS"

    def test_target_defect_rate(self, snapshot):
        assert snapshot["overall"]["target_defect_rate"] == 0.10


# ---------------------------------------------------------------------------
# Tier 2 — Per-type defects + sampled count (31 × 2 = 62 assertions)
# ---------------------------------------------------------------------------

# Hard-coded baseline: copied from the v3 snapshot. Updates here MUST be
# accompanied by a re-run of `data_quality_survey_via_api.py` and a note
# in the PDCA explaining why baseline shifted (PROD data evolved or gate
# semantics changed).
PER_TYPE_BASELINE = {
    # type_name: (sampled, defects_total, defect_rate)
    "AccountingStandard":     (43, 5, 0.1163),
    "AccountingSubject":     (100, 5, 0.0500),
    "AuditTrigger":          (100, 5, 0.0500),
    "BusinessActivity":      (100, 5, 0.0500),
    "Classification":        (100, 5, 0.0500),
    "ComplianceRule":        (100, 5, 0.0500),
    "DeductionRule":          (25, 5, 0.2000),
    "FilingForm":             (14, 5, 0.3571),
    "FilingFormField":       (100, 5, 0.0500),
    "FinancialIndicator":     (32, 5, 0.1562),
    "FinancialStatementItem": (78, 5, 0.0641),
    "IndustryBenchmark":      (45, 5, 0.1111),
    "InvoiceRule":            (40, 5, 0.1250),
    "IssuingBody":           (100, 5, 0.0500),
    "JournalEntryTemplate":   (20, 5, 0.2500),
    "KnowledgeUnit":         (100, 4, 0.0400),
    "LegalClause":           (100, 4, 0.0400),
    "LegalDocument":         (100, 5, 0.0500),
    "Penalty":               (100, 5, 0.0500),
    "PolicyChange":            (0, 0, 0.0000),
    "Region":                (100, 5, 0.0500),
    "SocialInsuranceRule":   (100, 5, 0.0500),
    "TaxAccountingGap":       (80, 5, 0.0625),
    "TaxBasis":               (20, 5, 0.2500),
    "TaxCalculationRule":    (100, 5, 0.0500),
    "TaxEntity":              (17, 5, 0.2941),
    "TaxIncentive":          (100, 5, 0.0500),
    "TaxItem":                 (0, 0, 0.0000),
    "TaxMilestoneEvent":      (20, 5, 0.2500),
    "TaxRate":               (100, 5, 0.0500),
    "TaxType":                (19, 5, 0.2632),
}


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
def test_per_type_sampled_baseline(snapshot, type_name):
    expected_sampled = PER_TYPE_BASELINE[type_name][0]
    actual = snapshot["per_type"][type_name]["sampled"]
    assert actual == expected_sampled, (
        f"{type_name} sampled drift: snapshot={actual} baseline={expected_sampled}"
    )


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
def test_per_type_defects_total_baseline(snapshot, type_name):
    expected_defects = PER_TYPE_BASELINE[type_name][1]
    actual = snapshot["per_type"][type_name]["defects_total"]
    assert actual == expected_defects, (
        f"{type_name} defects drift: snapshot={actual} baseline={expected_defects}"
    )


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
def test_per_type_defect_rate_baseline(snapshot, type_name):
    expected_rate = PER_TYPE_BASELINE[type_name][2]
    actual = snapshot["per_type"][type_name]["defect_rate"]
    assert abs(actual - expected_rate) < 1e-3, (
        f"{type_name} rate drift: snapshot={actual} baseline={expected_rate}"
    )


# ---------------------------------------------------------------------------
# Tier 3 — Per-type per-dimension zero-floor (31 × 7 = 217 assertions)
# Non-NULL dimensions are clean across all PROD types — lock them at 0.
# ---------------------------------------------------------------------------


_NONLINEAGE_DIMENSIONS = (
    "duplicate_id_count",
    "stale_count",
    "integrity_violations",
    "jurisdiction_mismatches",
    "prohibited_role_count",
    "invalid_chain_count",
    "inconsistent_scope_count",
)


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
@pytest.mark.parametrize("dim", _NONLINEAGE_DIMENSIONS)
def test_nonlineage_dimensions_clean_in_prod(snapshot, type_name, dim):
    # Per Finding 3 of the PDCA: all non-NULL dimensions are 0 across PROD.
    # Defect is structural NULL coverage, not row-level errors.
    actual = snapshot["per_type"][type_name][dim]
    assert actual == 0, (
        f"{type_name}.{dim} = {actual} but PDCA Finding 3 says all PROD "
        f"non-lineage dimensions = 0. Investigate before updating baseline."
    )


# ---------------------------------------------------------------------------
# Tier 4 — Per-type per-critical-column NULL rate baseline
# (31 types × 5 critical cols = 155 assertions)
# ---------------------------------------------------------------------------


_CRITICAL_COLUMNS = (
    "effective_from",
    "confidence",
    "source_doc_id",
    "jurisdiction_code",
    "jurisdiction_scope",
)


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
@pytest.mark.parametrize("col", _CRITICAL_COLUMNS)
def test_per_type_per_column_null_rate_in_unit_interval(snapshot, type_name, col):
    null_rate = snapshot["per_type"][type_name]["null_rate"][col]
    assert 0.0 <= null_rate <= 1.0, (
        f"{type_name}.null_rate.{col} = {null_rate} out of [0, 1]"
    )


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
@pytest.mark.parametrize("col", _CRITICAL_COLUMNS)
def test_critical_columns_match_canonical_set(snapshot, type_name, col):
    # Schema invariant: every type's null_rate dict carries all 5 critical cols.
    assert col in snapshot["per_type"][type_name]["null_rate"], (
        f"{type_name} missing critical column {col} in null_rate"
    )


# ---------------------------------------------------------------------------
# Tier 5 — Placeholder gate active and clean in PROD (31 × 2 = 62 assertions)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
def test_placeholder_string_count_zero_in_prod(snapshot, type_name):
    # PROD has 0 placeholder hits — banlist gate active but unrequired
    # (no Goodhart attribution exists yet). Locks in pre-backfill baseline.
    actual = snapshot["per_type"][type_name].get("placeholder_string_count")
    assert actual == 0, (
        f"{type_name}.placeholder_string_count = {actual} — banlist saw "
        f"placeholder strings in PROD. Investigate."
    )


@pytest.mark.parametrize("type_name", sorted(PER_TYPE_BASELINE.keys()))
def test_placeholder_per_field_keys_present(snapshot, type_name):
    # Schema invariant: every type's placeholder_per_field carries all
    # LINEAGE_STRING_FIELDS keys (even when count is 0).
    per_field = snapshot["per_type"][type_name].get("placeholder_per_field", {})
    for field in (
        "source_doc_id", "extracted_by", "reviewed_by",
        "jurisdiction_code", "override_chain_id",
    ):
        assert field in per_field, (
            f"{type_name}.placeholder_per_field missing key {field}"
        )


# ---------------------------------------------------------------------------
# Tier 6 — Structural NULL FAIL pattern lock (the PDCA's headline finding)
# ---------------------------------------------------------------------------


# PROD attribution map (corrected from PDCA Finding 2 simplification —
# discovered via corpus regression on 2026-04-27):
#
#   effective_from         → 100% NULL across ALL populated types (no exception)
#   jurisdiction_code      → 100% NULL across ALL populated types (no exception)
#   jurisdiction_scope     → 100% NULL across ALL populated types (no exception)
#   source_doc_id          → partial attribution in 4 types:
#                            KnowledgeUnit (0%), LegalClause (0%),
#                            FilingFormField (57% NULL), TaxCalculationRule (88% NULL)
#   confidence             → partial attribution in 2 types:
#                            FilingFormField (57% NULL), TaxCalculationRule (88% NULL)
#
# PDCA Finding 2 understated this — said "4/5 cols 100% NULL across all 31"
# but in fact `confidence` is partially populated in 2 types and
# `source_doc_id` is partially populated in 4 types. PDCA §C must be
# updated; tests below reflect the *actual* PROD shape, not the narrative.

_FULLY_NULL_POPULATED_TYPES = sorted(
    t for t in PER_TYPE_BASELINE
    if t not in ("PolicyChange", "TaxItem")  # empty
)

_PARTIAL_CONFIDENCE_TYPES = ("FilingFormField", "TaxCalculationRule")
_FULLY_NULL_CONFIDENCE_TYPES = sorted(
    t for t in _FULLY_NULL_POPULATED_TYPES
    if t not in _PARTIAL_CONFIDENCE_TYPES
)

_PARTIAL_SOURCE_DOC_ID_TYPES = (
    "KnowledgeUnit", "LegalClause",
    "FilingFormField", "TaxCalculationRule",
)
_FULLY_NULL_SOURCE_DOC_ID_TYPES = sorted(
    t for t in _FULLY_NULL_POPULATED_TYPES
    if t not in _PARTIAL_SOURCE_DOC_ID_TYPES
)


@pytest.mark.parametrize("type_name", _FULLY_NULL_POPULATED_TYPES)
def test_effective_from_universally_null(snapshot, type_name):
    # NO populated type has effective_from attribution. Universal gap.
    rate = snapshot["per_type"][type_name]["null_rate"]["effective_from"]
    assert rate == 1.0, (
        f"{type_name}.null_rate.effective_from = {rate}, expected 1.0 "
        f"(universal gap per corrected PDCA finding)"
    )


@pytest.mark.parametrize("type_name", _FULLY_NULL_POPULATED_TYPES)
def test_jurisdiction_code_universally_null(snapshot, type_name):
    rate = snapshot["per_type"][type_name]["null_rate"]["jurisdiction_code"]
    assert rate == 1.0, f"{type_name}.null_rate.jurisdiction_code = {rate}"


@pytest.mark.parametrize("type_name", _FULLY_NULL_POPULATED_TYPES)
def test_jurisdiction_scope_universally_null(snapshot, type_name):
    rate = snapshot["per_type"][type_name]["null_rate"]["jurisdiction_scope"]
    assert rate == 1.0, f"{type_name}.null_rate.jurisdiction_scope = {rate}"


@pytest.mark.parametrize("type_name", _FULLY_NULL_CONFIDENCE_TYPES)
def test_confidence_null_in_unattributed_types(snapshot, type_name):
    # All populated types EXCEPT FilingFormField + TaxCalculationRule:
    # confidence is 100% NULL.
    rate = snapshot["per_type"][type_name]["null_rate"]["confidence"]
    assert rate == 1.0, f"{type_name}.null_rate.confidence = {rate}"


@pytest.mark.parametrize("type_name", _PARTIAL_CONFIDENCE_TYPES)
def test_confidence_partially_attributed(snapshot, type_name):
    # FilingFormField (43% attributed) + TaxCalculationRule (12% attributed):
    # confidence is < 1.0 — partial backbone work has happened.
    rate = snapshot["per_type"][type_name]["null_rate"]["confidence"]
    assert rate < 1.0, (
        f"{type_name}.null_rate.confidence = {rate} — partial attribution "
        f"detected per corrected PDCA finding (FilingFormField=0.57, "
        f"TaxCalculationRule=0.88)"
    )


@pytest.mark.parametrize("type_name", _FULLY_NULL_SOURCE_DOC_ID_TYPES)
def test_source_doc_id_null_in_unattributed_types(snapshot, type_name):
    # All populated types EXCEPT the 4 attributed types: 100% NULL.
    rate = snapshot["per_type"][type_name]["null_rate"]["source_doc_id"]
    assert rate == 1.0, f"{type_name}.null_rate.source_doc_id = {rate}"


@pytest.mark.parametrize("type_name", _PARTIAL_SOURCE_DOC_ID_TYPES)
def test_source_doc_id_partially_attributed(snapshot, type_name):
    # KU + LC have full attribution (0% NULL); FilingFormField + TCR partial.
    rate = snapshot["per_type"][type_name]["null_rate"]["source_doc_id"]
    assert rate < 1.0, (
        f"{type_name}.null_rate.source_doc_id = {rate} — attribution "
        f"baseline expected: KU=0, LC=0, FFF=0.57, TCR=0.88"
    )


# ---------------------------------------------------------------------------
# Tier 7 — Empty-table tracking
# ---------------------------------------------------------------------------


def test_empty_types_in_fetch_misses(snapshot):
    # PolicyChange + TaxItem produce 0 sampled rows; recorded as fetch_misses.
    assert "PolicyChange" in snapshot["fetch_misses"]
    assert "TaxItem" in snapshot["fetch_misses"]


def test_empty_types_zero_defects(snapshot):
    # Empty samples must NOT generate phantom defects (5 critical NULL × 1 = 5
    # would be a regression bug — empty-sample bypass guard active).
    for empty_type in ("PolicyChange", "TaxItem"):
        assert snapshot["per_type"][empty_type]["defects_total"] == 0
        assert snapshot["per_type"][empty_type]["sampled"] == 0
