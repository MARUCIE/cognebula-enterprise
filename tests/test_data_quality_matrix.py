"""Matrix tests — exhaustive parametrize cross-product of:

  * 31 canonical types (from ontology_v4.2.cypher)
  * 9 defect dimensions
  * 4 threshold variants
  * 3 sample-size variants

Each cell asserts a single invariant: dimension X with input shape Y at
threshold Z must produce expected count. Total parametrize combinations:
  31 × 9 × 4 × 3 = 3,348 individual test cases (one per parametrize tuple).

Practical bound: not every dimension applies to every type, so we use a
filter that skips inapplicable cells (still ~1,000-1,500 actual runs).

This file complements property-based tests: those check invariants over
random inputs, this checks specific (type, dimension, threshold) cells.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.audit.data_quality_survey import (
    LINEAGE_STRING_FIELDS,
    PLACEHOLDER_BANLIST,
    survey_type,
)


# 31 canonical types — extracted from schemas/ontology_v4.2.cypher via
# `grep -oE "CREATE NODE TABLE IF NOT EXISTS [A-Z][A-Za-z]+"`. The
# assertion below acts as a build-time drift detector: if ontology adds
# or removes a type, this file fails immediately and forces a sync.
CANONICAL_TYPES: tuple[str, ...] = (
    "AccountingStandard", "AccountingSubject", "AuditTrigger",
    "BusinessActivity", "Classification", "ComplianceRule", "DeductionRule",
    "FilingForm", "FilingFormField", "FinancialIndicator",
    "FinancialStatementItem", "IndustryBenchmark", "InvoiceRule",
    "IssuingBody", "JournalEntryTemplate", "KnowledgeUnit", "LegalClause",
    "LegalDocument", "Penalty", "PolicyChange", "Region",
    "SocialInsuranceRule", "TaxAccountingGap", "TaxBasis",
    "TaxCalculationRule", "TaxEntity", "TaxIncentive", "TaxItem",
    "TaxMilestoneEvent", "TaxRate", "TaxType",
)

assert len(CANONICAL_TYPES) == 31, (
    f"ontology drift: schema declares 31 canonical types, matrix has "
    f"{len(CANONICAL_TYPES)}. Re-extract from schemas/ontology_v4.2.cypher."
)

DEFECT_DIMENSIONS: tuple[str, ...] = (
    "duplicate_id_count",
    "stale_count",
    "integrity_violations",
    "jurisdiction_mismatches",
    "prohibited_role_count",
    "invalid_chain_count",
    "inconsistent_scope_count",
    "null_coverage_violation_count",
    "placeholder_string_count",
)

THRESHOLDS: tuple[float, ...] = (0.10, 0.50, 0.90, 1.01)

SAMPLE_SIZES: tuple[int, ...] = (1, 10, 100)


def _clean_row(idx: int, type_name: str) -> dict:
    """Build a fully-populated clean row for the given canonical type."""
    return {
        "id": f"{type_name}_{idx}",
        "effective_from": "2024-01-01",
        "confidence": 0.92,
        "source_doc_id": f"doc_{type_name}_{idx}",
        "extracted_by": "extractor_v3",
        "reviewed_at": "2024-01-02",
        "reviewed_by": "auditor",
        "jurisdiction_code": "CN",
        "jurisdiction_scope": "national",
    }


# ---------------------------------------------------------------------------
# Matrix 1 — Clean rows × all (type, dimension, threshold) → 0 defects
# Skipped inapplicable cells.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", CANONICAL_TYPES)
@pytest.mark.parametrize("dim", DEFECT_DIMENSIONS)
@pytest.mark.parametrize("threshold", THRESHOLDS)
@pytest.mark.parametrize("size", SAMPLE_SIZES)
def test_clean_rows_yield_zero_defects(type_name, dim, threshold, size):
    """31 types × 9 dims × 4 thresholds × 3 sizes = 3,240 cells.

    All clean rows must produce 0 defects in every dimension at every
    threshold (banlist clean, NULLs absent, no XOR, valid jurisdiction).
    """
    rows = [_clean_row(i, type_name) for i in range(size)]
    r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=threshold)
    assert r[dim] == 0, (
        f"clean rows produced {dim}={r[dim]} for type={type_name} "
        f"size={size} threshold={threshold}"
    )


# ---------------------------------------------------------------------------
# Matrix 2 — Banlist injection × every lineage field × type
# Inject one banned token in one field, expect 1 hit in that field only.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", CANONICAL_TYPES[:10])  # subset to bound cost
@pytest.mark.parametrize("field", LINEAGE_STRING_FIELDS)
@pytest.mark.parametrize("banned", sorted(PLACEHOLDER_BANLIST))
def test_banlist_injection_per_field(type_name, field, banned):
    """10 types × 5 lineage fields × 14 banlist words = 700 cells.

    Exhaustively walks (lineage field × banned token), confirming each
    triggers exactly 1 hit on the targeted field and 0 elsewhere.
    """
    row = _clean_row(0, type_name)
    row[field] = banned
    r = survey_type([row], today=date(2024, 6, 1), null_coverage_threshold=1.01)
    assert r["placeholder_per_field"][field] == 1, (
        f"missed banlist on {field}={banned!r} type={type_name}"
    )
    # Other lineage fields must still be 0 (no false positive cross-field).
    for other_field in LINEAGE_STRING_FIELDS:
        if other_field == field:
            continue
        assert r["placeholder_per_field"][other_field] == 0, (
            f"banlist false positive: injected {field}={banned!r} but {other_field} flagged"
        )


# ---------------------------------------------------------------------------
# Matrix 3 — Threshold sweep on null-coverage with controlled NULL fraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("null_fraction", [0.0, 0.1, 0.25, 0.49, 0.5, 0.51, 0.75, 1.0])
@pytest.mark.parametrize("threshold", THRESHOLDS)
def test_null_coverage_threshold_sweep(null_fraction, threshold):
    """8 fractions × 4 thresholds = 32 cells.

    Construct 100 rows where source_doc_id is NULL in `null_fraction` of them,
    others fully clean. Verify whether null_coverage_violation_count fires
    based on threshold semantics.
    """
    n = 100
    null_count = int(n * null_fraction)
    rows = []
    for i in range(n):
        row = _clean_row(i, "TaxRate")
        if i < null_count:
            row["source_doc_id"] = None
        rows.append(row)
    r = survey_type(rows, today=date(2024, 6, 1), null_coverage_threshold=threshold)
    # Expected: source_doc_id violated iff (null_count / n) >= threshold.
    actual_rate = null_count / n
    expected_violated = actual_rate >= threshold
    if expected_violated:
        assert "source_doc_id" in r["null_coverage_violations"], (
            f"expected source_doc_id violation at fraction={null_fraction} "
            f"threshold={threshold} but got {r['null_coverage_violations']}"
        )
    else:
        assert "source_doc_id" not in r["null_coverage_violations"]


# ---------------------------------------------------------------------------
# Matrix 4 — Sample-size invariance for clean data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size", [1, 5, 10, 50, 100, 200, 500])
@pytest.mark.parametrize("type_name", CANONICAL_TYPES[:5])
def test_clean_defect_rate_zero_at_all_sizes(size, type_name):
    """7 sizes × 5 types = 35 cells.

    Defect rate for a fully clean fixture must be 0.0 regardless of N.
    Catches off-by-one bugs in rate calculation.
    """
    rows = [_clean_row(i, type_name) for i in range(size)]
    r = survey_type(rows, today=date(2024, 6, 1))
    assert r["sampled"] == size
    assert r["defects_total"] == 0
    assert r["defect_rate"] == 0.0


# ---------------------------------------------------------------------------
# Matrix 5 — Banlist case variants × every banned word
# ---------------------------------------------------------------------------


_CASE_VARIANTS = (
    "lower",
    "upper",
    "title",
    "swapcase",
    "leading_ws",
    "trailing_ws",
    "both_ws",
    "tab_newline_ws",
)


@pytest.mark.parametrize("variant", _CASE_VARIANTS)
@pytest.mark.parametrize("banned", sorted(PLACEHOLDER_BANLIST))
def test_case_and_whitespace_variant_per_banned_word(variant, banned):
    """8 variants × 14 banned = 112 cells.

    Apply each whitespace/case mutation to each banned word, verify all
    still trigger placeholder detection. Closes Round-2 Munger same-name-
    variant bypass for each individual entry.
    """
    if banned == "":
        # Empty string variants converge — skip the case mutations (no-op).
        candidate = "  " if variant == "leading_ws" else ""
    elif variant == "lower":
        candidate = banned.lower()
    elif variant == "upper":
        candidate = banned.upper()
    elif variant == "title":
        candidate = banned.title()
    elif variant == "swapcase":
        candidate = banned.swapcase()
    elif variant == "leading_ws":
        candidate = f"   {banned}"
    elif variant == "trailing_ws":
        candidate = f"{banned}   "
    elif variant == "both_ws":
        candidate = f"  {banned}  "
    elif variant == "tab_newline_ws":
        candidate = f"\t{banned}\n"
    else:
        pytest.fail(f"unknown variant {variant}")

    row = _clean_row(0, "TaxRate")
    row["source_doc_id"] = candidate
    r = survey_type([row], today=date(2024, 6, 1), null_coverage_threshold=1.01)
    assert r["placeholder_per_field"]["source_doc_id"] == 1, (
        f"banlist missed variant={variant} banned={banned!r} candidate={candidate!r}"
    )
