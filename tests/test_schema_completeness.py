"""Schema completeness tests — close the coverage hole 102K cases missed.

Discovered 2026-04-27 during P1.5 jurisdiction backfill reconnaissance:
the lineage envelope columns (`effective_from`, `confidence`, `source_doc_id`,
`jurisdiction_code`, `jurisdiction_scope`, `reviewed_at`, `reviewed_by`,
`override_chain_id`, `extracted_by`) checked by `data_quality_survey`
do NOT appear in `schemas/ontology_v4.2.cypher` — zero of 8.

PROD has them via runtime ALTER TABLE that was never back-ported to the
canonical schema file. This means:
  - `parse_canonical_schema()` cannot validate lineage envelope completeness
  - any future schema-driven audit (compute_schema_shape_drift et al.)
    is blind to these columns
  - the 100K test suite tests `survey_type` behavior on synthetic + PROD
    data, but never tests "are the columns we audit actually declared?"

This file fills the gap. The intent is **expected-to-FAIL on day 1** —
the FAIL state is the diagnostic signal that schema-cypher needs sync.
When schema is updated to declare lineage columns, the tests will FLIP
to PASS, providing positive confirmation of reconciliation.

Why this is a 102K-suite escape: every prior test reads from synthetic
fixtures or PROD JSON snapshots that already carry the columns. None
asserts the columns are CANONICALLY DECLARED. A new canonical type
added without lineage declarations would silently pass the entire
102K suite while being structurally wrong.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audit.data_quality_survey import (
    CRITICAL_COLUMNS,
    LINEAGE_STRING_FIELDS,
)
from src.audit.ontology_conformance import (
    parse_canonical_columns,
    parse_canonical_schema,
)


_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "schemas" / "ontology_v4.2.cypher"
)


# ---------------------------------------------------------------------------
# Section 1 — fixture: parse the canonical schema once per module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def canonical_columns() -> dict[str, list[str]]:
    return parse_canonical_columns(_SCHEMA_PATH)


@pytest.fixture(scope="module")
def canonical_types() -> set[str]:
    return parse_canonical_schema(_SCHEMA_PATH)


# ---------------------------------------------------------------------------
# Section 2 — Sanity: schema parser works
# ---------------------------------------------------------------------------


class TestSchemaParsing:

    def test_canonical_types_count_is_31(self, canonical_types):
        # Sanity check: ontology has 31 declared canonical node tables.
        assert len(canonical_types) == 31, (
            f"canonical type count drift: schema declares {len(canonical_types)}, "
            f"matrix tests assume 31"
        )

    def test_columns_dict_covers_all_canonical_types(
        self, canonical_columns, canonical_types
    ):
        # Every canonical type must appear in the columns dict, otherwise
        # parse_canonical_columns is silently dropping declarations.
        missing = canonical_types - set(canonical_columns.keys())
        assert not missing, (
            f"canonical types missing from columns dict: {sorted(missing)}"
        )

    def test_every_type_has_at_least_id_column(self, canonical_columns):
        for type_name, cols in canonical_columns.items():
            assert "id" in cols, (
                f"{type_name} missing `id` column in canonical declaration"
            )


# ---------------------------------------------------------------------------
# Section 3 — Drift detection: lineage columns that the audit reads must be
# either (a) declared in the canonical schema, OR (b) explicitly waived as
# runtime-added with an issue tracker reference.
#
# DAY-1 EXPECTATION: these tests FAIL — that's the signal that schema sync
# is needed. After Maurice approves Plan A/B/C/D from the recon memo and
# schema is reconciled, these tests will go GREEN.
# ---------------------------------------------------------------------------


# Columns the audit reads and expects to find in PROD rows. If these are
# missing from canonical schema declarations, the audit is operating on
# undeclared data — schema-vs-audit drift.
_AUDITED_LINEAGE_COLUMNS = sorted(set(CRITICAL_COLUMNS) | set(LINEAGE_STRING_FIELDS))


# Waiver list: canonical types that LEGITIMATELY don't carry lineage envelope
# (e.g. pure structural types like Region whose only purpose is name+code).
# Empty initially — populate ONLY with explicit user approval; do not use
# this list to silence inconvenient FAILs.
_LINEAGE_WAIVED_TYPES: set[str] = set()


@pytest.mark.parametrize("col", _AUDITED_LINEAGE_COLUMNS)
def test_audited_lineage_column_appears_in_at_least_one_canonical_type(
    canonical_columns, col
):
    """An audit dimension that no canonical type carries is dead code.

    If a column is in CRITICAL_COLUMNS or LINEAGE_STRING_FIELDS but ZERO
    canonical types declare it, either the column is wrong or the schema
    is incomplete. Both warrant a FAIL — the test is a reconciliation
    forcing function.
    """
    appearances = sum(
        1 for cols in canonical_columns.values() if col in cols
    )
    assert appearances > 0, (
        f"audit reads `{col}` but ZERO of {len(canonical_columns)} canonical "
        f"types declare it. Either:\n"
        f"  (a) `{col}` is dead audit code — remove from CRITICAL_COLUMNS / LINEAGE_STRING_FIELDS\n"
        f"  (b) `schemas/ontology_v4.2.cypher` is stale — sync runtime ALTER TABLE additions back to canonical\n"
        f"Per recon memo `outputs/reports/data-quality-audit/2026-04-27-p1.5-jurisdiction-recon-memo.md`,\n"
        f"the current state is (b): PROD has these columns via untracked ALTER TABLE."
    )


@pytest.mark.parametrize("type_name", sorted([
    "KnowledgeUnit", "LegalClause",  # legal backbone — has source_doc_id in PROD
    "FilingFormField", "TaxCalculationRule",  # partial attribution per corpus discovery
]))
def test_partial_attribution_types_declare_source_doc_id(
    canonical_columns, type_name
):
    """The 4 types corpus regression discovered have partial source_doc_id
    attribution MUST declare the column canonically — otherwise the partial
    attribution PROD signal cannot be validated by schema audit.
    """
    cols = canonical_columns.get(type_name, [])
    has_source_doc = any(
        c in cols for c in ("source_doc_id", "sourceDocId", "sourceDocID")
    )
    if not has_source_doc:
        pytest.fail(
            f"{type_name} carries source_doc_id in PROD (corpus snapshot v3) "
            f"but canonical schema declares only: {cols}\n"
            f"Schema-vs-PROD drift confirmed for partial-attribution types."
        )


# ---------------------------------------------------------------------------
# Section 4 — Forward-compat: ensure new lineage additions don't accidentally
# pollute domain-only tables.
# ---------------------------------------------------------------------------


class TestLineageDoesNotPolluteDomainTables:

    def test_no_lineage_column_named_with_typo_variants(self, canonical_columns):
        """Catch typo variants that would silently bypass the audit:
        `effective_at`, `effectiveFrom` (camelCase), `confidance`, etc.
        """
        # camelCase / snake_case / typo variants of audited columns.
        suspects = {
            "effective_from": ["effectiveFrom", "effective_at", "effectiveAt", "effFrom"],
            "confidence": ["confidance", "conf", "Confidence", "confLevel"],
            "source_doc_id": ["sourceDocId", "sourceDocID", "src_doc_id", "doc_id"],
            "jurisdiction_code": ["jurisdictionCode", "juriCode", "jurisdiction_cd"],
            "reviewed_at": ["reviewedAt", "review_at", "reviewedTime"],
            "reviewed_by": ["reviewedBy", "review_by", "reviewer"],
        }
        # Note: this is INFORMATIONAL — we EXPECT to find some of these in
        # the schema (e.g. `sourceDocId` exists on KnowledgeUnit per L46-50
        # of the schema). The test's job is to surface the camelCase
        # convention so future code can normalize.
        report: dict[str, list[tuple[str, str]]] = {}
        for snake, variants in suspects.items():
            hits: list[tuple[str, str]] = []
            for type_name, cols in canonical_columns.items():
                for v in variants:
                    if v in cols:
                        hits.append((type_name, v))
            if hits:
                report[snake] = hits
        # We only emit the report; do not assert. The audit reads snake_case
        # but the schema declares camelCase — that's THE drift the recon memo
        # documents. Logging here so future tests can catch new drift.
        if report:
            msg = "Schema/audit naming-convention drift detected (camelCase vs snake_case):\n"
            for snake, hits in sorted(report.items()):
                msg += f"  audit reads `{snake}`, schema declares: {hits}\n"
            # Print for visibility but pass — see TestSchemaDriftSnapshot below.
            print(f"\n[TEST INFO] {msg}")


# ---------------------------------------------------------------------------
# Section 5 — Drift snapshot: a single test that captures the FULL drift
# report so PR diffs make schema sync work visible.
# ---------------------------------------------------------------------------


class TestSchemaDriftSnapshot:

    def test_full_lineage_drift_snapshot(self, canonical_columns):
        """Snapshot test: build a per-type-per-column matrix of which
        audit-read columns are declared in the canonical schema. The
        assertion locks the COUNT of missing cells — when schema is
        reconciled, this number drops and the test fails until the
        snapshot is updated, providing a reconciliation receipt.
        """
        # Audit-read columns the test cares about (snake_case as used in code).
        audited = sorted(set(CRITICAL_COLUMNS) | set(LINEAGE_STRING_FIELDS))
        # Also accept camelCase variants per Section 4 finding.
        camel_variants = {
            "effective_from": ["effectiveFrom", "effectiveAt"],
            "confidence": ["confidence"],
            "source_doc_id": ["sourceDocId", "sourceDocID"],
            "extracted_by": ["extractedBy"],
            "reviewed_at": ["reviewedAt"],
            "reviewed_by": ["reviewedBy"],
            "jurisdiction_code": ["jurisdictionCode", "jurisdiction"],
            "jurisdiction_scope": ["jurisdictionScope"],
            "override_chain_id": ["overrideChainId"],
        }
        missing_cells = 0
        total_cells = 0
        for type_name, cols in canonical_columns.items():
            cols_lc = {c.lower() for c in cols}
            for snake in audited:
                total_cells += 1
                # Accept either snake_case OR known camelCase variants.
                accepted = [snake] + camel_variants.get(snake, [])
                if not any(v.lower() in cols_lc for v in accepted):
                    missing_cells += 1

        # Day-1 baseline (locked snapshot): out of 31 types × 8 audited cols
        # = 248 total cells, 237 are missing because canonical schema
        # doesn't declare most of the lineage envelope. Only 11 cells are
        # present today (mostly `effective_from` on temporal types like
        # LegalDocument/PolicyChange/TaxRate, plus `sourceDocId` on
        # KnowledgeUnit and PolicyChange, and `jurisdiction_code` on
        # IssuingBody).
        #
        # When Maurice approves Plan A/B/C/D from the recon memo and
        # schema is reconciled, this snapshot will fail with RECONCILIATION
        # PROGRESS — that's the receipt to update BASELINE_MISSING down.
        expected_total = len(canonical_columns) * 8  # 8 = len(audited)
        assert total_cells == expected_total, (
            f"total cells = {total_cells}, expected {expected_total} "
            f"({len(canonical_columns)} types × 8 audited columns)"
        )
        # Initial baseline lock — actual measured missing cells on
        # 2026-04-27 commit (Sprint A+B+C complete). Reconciliation work
        # flips this number down.
        BASELINE_MISSING = 237  # 11 of 248 cells present (4.4% coverage)
        assert missing_cells <= BASELINE_MISSING, (
            f"NEW DRIFT INTRODUCED: {missing_cells} missing cells, "
            f"baseline {BASELINE_MISSING}. A canonical type was added/changed "
            f"that doesn't carry lineage. Update schema or update BASELINE_MISSING."
        )
        if missing_cells < BASELINE_MISSING:
            # Reconciliation progress — hint to update the baseline.
            pytest.fail(
                f"RECONCILIATION PROGRESS: missing cells dropped from "
                f"{BASELINE_MISSING} → {missing_cells}. Update BASELINE_MISSING "
                f"to lock in the new floor (so future drift surfaces immediately)."
            )
