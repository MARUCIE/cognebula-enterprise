"""Data-quality survey — real defects in stored nodes, not Schema coverage.

The audit on 2026-04-21 identified this as the single highest-ROI next action.
All previous auditors (provenance / jurisdiction / argument) measure whether
the *Schema* carries the expected columns. This auditor measures whether the
actual stored data is plausible: NULL rates on critical columns, duplicate
ids, stale effective-dates, confidence-reviewed integrity violations, and
jurisdictional code/scope consistency.

Contract (input): a Kuzu connection handle OR anything with a compatible
`.execute(cypher).get_as_df()` interface. Pure read, never writes.

Contract (output) — returned by `survey()`:

    {
        "sample_size": int,
        "per_type": {
            "TaxType": {
                "sampled": int,
                "null_rate": {"effective_from": 0.12, ...},
                "duplicate_id_count": int,
                "stale_rate": float,          # effective_from older than threshold
                "integrity_violations": int,  # reviewed_by NULL but reviewed_at set
                "jurisdiction_mismatches": int,  # code/scope inconsistency
                "defects_total": int,
                "defect_rate": float,
            },
            ...
        },
        "overall": {
            "canonical_types_surveyed": int,
            "total_sampled": int,
            "total_defects": int,
            "defect_rate": float,
            "verdict": "PASS" | "FAIL",
            "target_defect_rate": float,
        },
    }

`verdict=PASS` iff `defect_rate <= target_defect_rate` (default 0.10).

This is intentionally *separate* from the coverage auditors: coverage answers
"does the container exist?", survey answers "is what's inside it any good?".
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.audit.ontology_conformance import parse_canonical_schema
from src.kg.bitemporal_query import ALLOWED_JURISDICTION_SCOPES
from src.kg.clause_inspector import inspect as _inspect_clause

_DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "ontology_v4.2.cypher"
)


DEFAULT_SAMPLE_SIZE = 100
DEFAULT_STALE_YEARS = 10
DEFAULT_TARGET_DEFECT_RATE = 0.10
# Closes the 2026-04-27 gap: prior gate reported per-column null_rate but
# never aggregated NULL severity into defects_total — making 100%-NULL
# lineage envelopes (e.g. effective_from across all 31 canonical types)
# invisible to PASS/FAIL verdicts. A column where ≥50% of sampled rows
# carry NULL is treated as systematic absence, not noise.
DEFAULT_NULL_COVERAGE_THRESHOLD = 0.50

CRITICAL_COLUMNS: tuple[str, ...] = (
    "effective_from",
    "confidence",
    "source_doc_id",
    "jurisdiction_code",
    "jurisdiction_scope",
)

# Closes the 2026-04-27 Round-1 Munger inversion + Round-2 follow-up:
# placeholder strings ('unknown' / 'TBD' / 'default' / 'N/A' / '') in lineage
# fields are NULL-equivalents pretending to be real attributions. They flip
# null_rate green without real lineage. The banlist enforces semantic-NULL
# detection alongside structural-NULL detection.
#
# Match is case-insensitive + whitespace-stripped, so 'Unknown', '  ', and
# ' default ' all hit. Empty string '' also hits — it's the canonical
# Cypher result for a column the writer "set" to no content.
LINEAGE_STRING_FIELDS: tuple[str, ...] = (
    "source_doc_id",
    "extracted_by",
    "reviewed_by",
    "jurisdiction_code",
    "override_chain_id",
)
PLACEHOLDER_BANLIST: frozenset[str] = frozenset({
    "unknown", "tbd", "todo", "default", "n/a", "na",
    "none", "null", "nil", "tba", "fixme", "?", "-", "",
})


def _is_placeholder(value: object) -> bool:
    """Return True if value is a NULL-equivalent placeholder string.

    Case-insensitive + whitespace-stripped. Numeric / None / non-string
    inputs return False (banlist applies only to *strings*; True NULL is
    counted by null_rate, not by placeholder gate).
    """
    if not isinstance(value, str):
        return False
    return value.strip().lower() in PLACEHOLDER_BANLIST


def _count_placeholder_strings(rows: list[dict]) -> tuple[int, dict[str, int]]:
    """Count per-field placeholder hits across tracked lineage string columns.

    Returns (total_count, per_field_counts) where per_field_counts maps each
    LINEAGE_STRING_FIELDS entry to its hit count in this sample. The total
    is the sum of all fields' hits — a row with placeholder values in 3
    fields contributes 3 hits, mirroring how `integrity_violations` and
    `jurisdiction_mismatches` count.
    """
    per_field: dict[str, int] = {col: 0 for col in LINEAGE_STRING_FIELDS}
    for r in rows:
        for col in LINEAGE_STRING_FIELDS:
            if _is_placeholder(r.get(col)):
                per_field[col] += 1
    return sum(per_field.values()), per_field


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _is_stale(value: Any, today: date, years: int) -> bool:
    d = _parse_date(value)
    if d is None:
        return False
    return (today - d) > timedelta(days=years * 365)


def _count_nulls(rows: list[dict], column: str) -> int:
    return sum(1 for r in rows if r.get(column) is None or r.get(column) == "")


def _count_duplicates(rows: list[dict], id_column: str = "id") -> int:
    seen: dict[Any, int] = {}
    for r in rows:
        seen[r.get(id_column)] = seen.get(r.get(id_column), 0) + 1
    return sum(count - 1 for count in seen.values() if count > 1)


def _count_integrity_violations(rows: list[dict]) -> int:
    """reviewed_at is set but reviewed_by is NULL — audit-trail broken."""
    n = 0
    for r in rows:
        reviewed_at = r.get("reviewed_at")
        reviewed_by = r.get("reviewed_by")
        if reviewed_at and not reviewed_by:
            n += 1
        if reviewed_by and not reviewed_at:
            n += 1
    return n


def _count_jurisdiction_mismatches(rows: list[dict]) -> int:
    """Unknown scope OR code set without scope (or vice versa)."""
    n = 0
    for r in rows:
        code = r.get("jurisdiction_code")
        scope = r.get("jurisdiction_scope")
        if scope and scope not in ALLOWED_JURISDICTION_SCOPES:
            n += 1
            continue
        # XOR: exactly one set without the other.
        if bool(code) ^ bool(scope):
            n += 1
    return n


def _clause_defect_counts(rows: list[dict]) -> dict[str, int]:
    """One-pass count of clause-axis defects via ``clause_inspector.inspect``.

    Delegates to the same façade the REST endpoint + operator CLI use,
    so defect semantics stay in exactly one place. When the inspector
    adds a new clause-axis flag (or changes an existing threshold), the
    survey picks it up automatically — no parallel maintenance.

    Returns only the flags this survey historically exposed as counters,
    keeping the public ``survey_type()`` dict shape stable:

    * ``prohibited_role_count``  ← ``prohibited_role``
    * ``invalid_chain_count``    ← ``invalid_override_chain``
    * ``inconsistent_scope_count`` ← ``inconsistent_code_scope``

    ``unknown_role`` / ``unknown_jurisdiction_code`` / invalid multiparent
    are also flagged by the inspector but not exposed here — they belong
    in a future audit expansion, not a silent shape change.
    """
    counts = {
        "prohibited_role_count": 0,
        "invalid_chain_count": 0,
        "inconsistent_scope_count": 0,
    }
    for r in rows:
        flags = set(_inspect_clause(r).defect_flags)
        if "prohibited_role" in flags:
            counts["prohibited_role_count"] += 1
        if "invalid_override_chain" in flags:
            counts["invalid_chain_count"] += 1
        if "inconsistent_code_scope" in flags:
            counts["inconsistent_scope_count"] += 1
    return counts


def survey_type(
    rows: list[dict],
    *,
    today: date | None = None,
    stale_years: int = DEFAULT_STALE_YEARS,
    null_coverage_threshold: float = DEFAULT_NULL_COVERAGE_THRESHOLD,
) -> dict[str, Any]:
    """Survey a single canonical type from a materialized sample.

    Keeping the per-type analysis pure (no DB handle) makes it directly
    testable with fixture dicts and easy to unit-test offline.

    `null_coverage_threshold`: a CRITICAL_COLUMNS entry whose null_rate
    is >= this threshold counts as one defect unit. Default 0.50 (column
    with majority NULL = systematic absence, not noise). Set to 1.0 to
    disable (only fully-NULL columns count, which essentially never trigger
    on sampled data) or to a lower value (e.g. 0.20) for a stricter gate.
    """
    today = today or date.today()
    sampled = len(rows)
    null_rate = {
        col: round(_count_nulls(rows, col) / sampled, 4) if sampled else 0.0
        for col in CRITICAL_COLUMNS
    }
    duplicate_id_count = _count_duplicates(rows, "id")
    stale_count = sum(
        1 for r in rows if _is_stale(r.get("effective_from"), today, stale_years)
    )
    integrity_violations = _count_integrity_violations(rows)
    jurisdiction_mismatches = _count_jurisdiction_mismatches(rows)
    clause_defects = _clause_defect_counts(rows)
    prohibited_role_count = clause_defects["prohibited_role_count"]
    invalid_chain_count = clause_defects["invalid_chain_count"]
    inconsistent_scope_count = clause_defects["inconsistent_scope_count"]
    # 2026-04-27 extension: count critical-column NULL coverage as a
    # first-class defect category. Skip on empty samples (sampled == 0)
    # because a missing table is reported elsewhere via fetch_misses,
    # not double-counted as five NULL-coverage defects.
    null_coverage_violation_count = (
        sum(1 for col in CRITICAL_COLUMNS if null_rate[col] >= null_coverage_threshold)
        if sampled
        else 0
    )
    null_coverage_violations = (
        sorted(
            col for col in CRITICAL_COLUMNS
            if null_rate[col] >= null_coverage_threshold
        )
        if sampled
        else []
    )
    placeholder_string_count, placeholder_per_field = _count_placeholder_strings(rows)

    defects_total = (
        duplicate_id_count
        + stale_count
        + integrity_violations
        + jurisdiction_mismatches
        + prohibited_role_count
        + invalid_chain_count
        + inconsistent_scope_count
        + null_coverage_violation_count
        + placeholder_string_count
    )
    defect_rate = round(defects_total / sampled, 4) if sampled else 0.0
    return {
        "sampled": sampled,
        "null_rate": null_rate,
        "duplicate_id_count": duplicate_id_count,
        "stale_count": stale_count,
        "stale_rate": round(stale_count / sampled, 4) if sampled else 0.0,
        "integrity_violations": integrity_violations,
        "jurisdiction_mismatches": jurisdiction_mismatches,
        "prohibited_role_count": prohibited_role_count,
        "invalid_chain_count": invalid_chain_count,
        "inconsistent_scope_count": inconsistent_scope_count,
        "null_coverage_violation_count": null_coverage_violation_count,
        "null_coverage_violations": null_coverage_violations,
        "null_coverage_threshold": null_coverage_threshold,
        "placeholder_string_count": placeholder_string_count,
        "placeholder_per_field": placeholder_per_field,
        "defects_total": defects_total,
        "defect_rate": defect_rate,
    }


def survey(
    conn,
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    target_defect_rate: float = DEFAULT_TARGET_DEFECT_RATE,
    stale_years: int = DEFAULT_STALE_YEARS,
    null_coverage_threshold: float = DEFAULT_NULL_COVERAGE_THRESHOLD,
    schema_path=None,
    today: date | None = None,
) -> dict[str, Any]:
    """Run the full survey against a live Kuzu connection.

    `conn` only needs `.execute(cypher).get_as_df().to_dict(orient="records")`
    semantics; any offline stub satisfying that contract works.
    """
    path = Path(schema_path) if schema_path else _DEFAULT_SCHEMA_PATH
    canonical_types = sorted(parse_canonical_schema(path))
    per_type: dict[str, Any] = {}
    total_sampled = 0
    total_defects = 0

    for t in canonical_types:
        try:
            df = conn.execute(
                f"MATCH (n:{t}) RETURN n LIMIT {int(sample_size)}"
            ).get_as_df()
            rows = df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
        except Exception:  # pragma: no cover — live-DB error path
            rows = []
        report = survey_type(
            rows,
            today=today,
            stale_years=stale_years,
            null_coverage_threshold=null_coverage_threshold,
        )
        per_type[t] = report
        total_sampled += report["sampled"]
        total_defects += report["defects_total"]

    overall_defect_rate = (
        round(total_defects / total_sampled, 4) if total_sampled else 0.0
    )
    verdict = "PASS" if overall_defect_rate <= target_defect_rate else "FAIL"
    return {
        "sample_size": sample_size,
        "per_type": per_type,
        "overall": {
            "canonical_types_surveyed": len(canonical_types),
            "total_sampled": total_sampled,
            "total_defects": total_defects,
            "defect_rate": overall_defect_rate,
            "verdict": verdict,
            "target_defect_rate": target_defect_rate,
        },
    }
