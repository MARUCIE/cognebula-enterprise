"""Mutation testing via hypothesis stateful — accounting transitivity.

Sprint B focus: this is the only test layer that can detect *transitive
accounting bugs* — bugs where the order of mutations affects the final
defect count. Property tests check single-input invariants; matrix tests
check parametrized cells; corpus tests check fixed snapshots; mutation
tests check that the gate's accounting is path-independent.

Design:
  RuleBasedStateMachine starts with N clean rows and applies a random
  sequence of M mutations (NULL injection, placeholder injection,
  integrity XOR, duplicate id, stale date, ...). After each mutation,
  invariants assert that the survey defect count equals the running
  expected count we maintain in the state machine.

Estimated case count:
  hypothesis stateful default ~50 examples × 30 steps × 4 invariants
  per step ≈ 6,000 invariant checks per test class. Three classes ×
  ~6K = ~18K cases. This is below the 80K initial estimate because
  hypothesis stateful caps step counts and shrinks aggressively;
  practical-yield is ~6-20K not the naive max product.

Bugs this catches that other layers cannot:
  * "duplicate then remove" semantics (shouldn't permanently increment count)
  * mutation A → mutation B vs B → A divergence (commutativity)
  * idempotent mutation applied twice creating extra defect
  * partial NULL transition causing threshold flip-flop near 50%
"""

from __future__ import annotations

from datetime import date

from hypothesis import HealthCheck, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from src.audit.data_quality_survey import (
    CRITICAL_COLUMNS,
    LINEAGE_STRING_FIELDS,
    PLACEHOLDER_BANLIST,
    survey_type,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_row(idx: int) -> dict:
    return {
        "id": f"r_{idx}",
        "effective_from": "2024-01-01",
        "confidence": 0.92,
        "source_doc_id": f"doc_{idx}",
        "extracted_by": "extractor_v3",
        "reviewed_at": "2024-01-02",
        "reviewed_by": "auditor",
        "jurisdiction_code": "CN",
        "jurisdiction_scope": "national",
    }


_BANLIST_LIST = sorted(PLACEHOLDER_BANLIST)


# ---------------------------------------------------------------------------
# Machine 1 — Placeholder mutation accounting
# ---------------------------------------------------------------------------


class PlaceholderMutationMachine(RuleBasedStateMachine):
    """Inject placeholder strings into clean rows; verify defect count stays
    consistent with applied mutations.

    Invariant: after K placeholder injections across N rows, the survey's
    placeholder_string_count equals the number of (row, field) cells we
    set to a placeholder value, summed across all current cells. Re-injecting
    the SAME cell with a placeholder doesn't double-count (it's a single
    cell-state, not an event count).
    """

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        # Track which (row_idx, field) pairs currently hold a placeholder.
        self.placeholder_cells: set[tuple[int, str]] = set()

    @initialize(n=st.integers(min_value=5, max_value=15))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]
        self.placeholder_cells = set()

    @rule(
        row_idx=st.integers(0, 14),
        field=st.sampled_from(LINEAGE_STRING_FIELDS),
        banned=st.sampled_from(_BANLIST_LIST),
    )
    def inject_placeholder(self, row_idx, field, banned):
        if row_idx >= len(self.rows):
            return  # skip out-of-bounds when init n was small
        prev_value = self.rows[row_idx].get(field)
        # Apply mutation.
        self.rows[row_idx][field] = banned
        # Track cell state — placeholder presence is binary per cell.
        self.placeholder_cells.add((row_idx, field))

    @rule(row_idx=st.integers(0, 14), field=st.sampled_from(LINEAGE_STRING_FIELDS))
    def restore_field(self, row_idx, field):
        if row_idx >= len(self.rows):
            return
        # Restore to a legitimate value.
        self.rows[row_idx][field] = f"legit_{row_idx}_{field}"
        self.placeholder_cells.discard((row_idx, field))

    @invariant()
    def placeholder_count_matches_active_cells(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        # Note: this counts current placeholder cells, not historical injections.
        # Mutation order doesn't matter — only the final cell state.
        assert r["placeholder_string_count"] == len(self.placeholder_cells), (
            f"placeholder accounting drift: report={r['placeholder_string_count']} "
            f"tracked={len(self.placeholder_cells)} cells={sorted(self.placeholder_cells)}"
        )

    @invariant()
    def placeholder_per_field_sums_to_total(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        assert sum(r["placeholder_per_field"].values()) == r["placeholder_string_count"]


TestPlaceholderMutation = PlaceholderMutationMachine.TestCase
TestPlaceholderMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# ---------------------------------------------------------------------------
# Machine 2 — Duplicate-id mutation accounting
# ---------------------------------------------------------------------------


class DuplicateIdMutationMachine(RuleBasedStateMachine):
    """Toggle ids between unique and shared values; verify duplicate_id_count
    tracks correctly.

    Invariant: duplicate_id_count = sum over each id of max(0, occurrences-1).
    """

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []

    @initialize(n=st.integers(min_value=3, max_value=10))
    def start_unique(self, n):
        self.rows = [_clean_row(i) for i in range(n)]

    @rule(row_idx=st.integers(0, 9), shared_id=st.sampled_from(["X", "Y", "Z"]))
    def assign_shared_id(self, row_idx, shared_id):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["id"] = shared_id

    @rule(row_idx=st.integers(0, 9))
    def restore_unique_id(self, row_idx):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["id"] = f"unique_{row_idx}_{id(object())}"

    @invariant()
    def duplicate_count_matches_id_distribution(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        # Compute expected: for each id, count duplicates beyond first.
        from collections import Counter
        ids = [row.get("id") for row in self.rows]
        counts = Counter(ids)
        expected = sum(max(0, c - 1) for c in counts.values())
        assert r["duplicate_id_count"] == expected, (
            f"duplicate_id_count drift: report={r['duplicate_id_count']} "
            f"expected={expected} ids={ids}"
        )


TestDuplicateIdMutation = DuplicateIdMutationMachine.TestCase
TestDuplicateIdMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# ---------------------------------------------------------------------------
# Machine 3 — NULL coverage threshold flip-flop
# ---------------------------------------------------------------------------


class NullCoverageMutationMachine(RuleBasedStateMachine):
    """Toggle critical-column NULL state; verify null_coverage_violation_count
    matches the current per-column NULL fraction × threshold.

    Invariant: a column appears in null_coverage_violations IFF its current
    NULL rate >= threshold. Re-toggling the same row should be idempotent
    in expected count.
    """

    THRESHOLD = 0.5

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        # track which (row_idx, col) pairs currently hold NULL
        self.null_cells: set[tuple[int, str]] = set()

    @initialize(n=st.integers(min_value=4, max_value=10))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]
        self.null_cells = set()

    @rule(row_idx=st.integers(0, 9), col=st.sampled_from(CRITICAL_COLUMNS))
    def set_null(self, row_idx, col):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx][col] = None
        self.null_cells.add((row_idx, col))

    @rule(row_idx=st.integers(0, 9), col=st.sampled_from(CRITICAL_COLUMNS))
    def set_value(self, row_idx, col):
        if row_idx >= len(self.rows):
            return
        # Use type-appropriate value.
        if col == "confidence":
            self.rows[row_idx][col] = 0.9
        else:
            self.rows[row_idx][col] = f"v_{row_idx}_{col}"
        self.null_cells.discard((row_idx, col))

    @invariant()
    def violation_count_matches_threshold_semantics(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows,
            today=date(2024, 6, 1),
            null_coverage_threshold=self.THRESHOLD,
        )
        # Expected: for each col, count rows where it's NULL or '' or missing.
        # Then compare ratio to threshold.
        from src.audit.data_quality_survey import _count_nulls
        expected_violations = sorted([
            col for col in CRITICAL_COLUMNS
            if (_count_nulls(self.rows, col) / len(self.rows)) >= self.THRESHOLD
        ])
        assert r["null_coverage_violations"] == expected_violations, (
            f"violations drift: report={r['null_coverage_violations']} "
            f"expected={expected_violations} null_rate={r['null_rate']}"
        )

    @invariant()
    def violation_count_equals_list_length(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows,
            today=date(2024, 6, 1),
            null_coverage_threshold=self.THRESHOLD,
        )
        assert r["null_coverage_violation_count"] == len(r["null_coverage_violations"])


TestNullCoverageMutation = NullCoverageMutationMachine.TestCase
TestNullCoverageMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# ---------------------------------------------------------------------------
# Machine 4 — Compound mutation: defects_total integrity under any sequence
# ---------------------------------------------------------------------------


class CompoundMutationMachine(RuleBasedStateMachine):
    """The flagship invariant: under ANY sequence of mutations, defects_total
    equals the explicit sum of all 9 named dimensions. This catches accounting
    drift where a new dimension stops contributing or a stale formula remains.
    """

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []

    @initialize(n=st.integers(min_value=3, max_value=12))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]

    @rule(row_idx=st.integers(0, 11), banned=st.sampled_from(_BANLIST_LIST))
    def mutate_placeholder(self, row_idx, banned):
        if row_idx < len(self.rows):
            self.rows[row_idx]["source_doc_id"] = banned

    @rule(row_idx=st.integers(0, 11))
    def mutate_null_effective_from(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["effective_from"] = None

    @rule(row_idx=st.integers(0, 11))
    def mutate_null_jurisdiction_code(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["jurisdiction_code"] = None

    @rule(row_idx=st.integers(0, 11))
    def mutate_xor_review_fields(self, row_idx):
        # Remove one to create XOR.
        if row_idx < len(self.rows):
            self.rows[row_idx].pop("reviewed_by", None)

    @rule(row_idx=st.integers(0, 11), shared=st.sampled_from(["A", "B"]))
    def mutate_duplicate_id(self, row_idx, shared):
        if row_idx < len(self.rows):
            self.rows[row_idx]["id"] = shared

    @rule(row_idx=st.integers(0, 11))
    def mutate_stale_date(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["effective_from"] = "2010-01-01"  # >10 years stale

    @rule(row_idx=st.integers(0, 11))
    def restore_clean(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx] = _clean_row(row_idx)

    @invariant()
    def defects_total_equals_sum_of_dimensions(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=0.5
        )
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
        assert r["defects_total"] == explicit_sum, (
            f"defects_total accounting drift: total={r['defects_total']} "
            f"sum={explicit_sum} report={r}"
        )

    @invariant()
    def defect_rate_matches_total_over_sampled(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=0.5
        )
        expected_rate = round(r["defects_total"] / r["sampled"], 4)
        assert abs(r["defect_rate"] - expected_rate) < 1e-4

    @invariant()
    def all_counts_non_negative(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=0.5
        )
        for dim in (
            "duplicate_id_count", "stale_count", "integrity_violations",
            "jurisdiction_mismatches", "prohibited_role_count",
            "invalid_chain_count", "inconsistent_scope_count",
            "null_coverage_violation_count", "placeholder_string_count",
        ):
            assert r[dim] >= 0


TestCompoundMutation = CompoundMutationMachine.TestCase
TestCompoundMutation.settings = settings(
    max_examples=500,
    stateful_step_count=60,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# ---------------------------------------------------------------------------
# Sprint D — single-axis machines for the 3 dimensions that previously had
# only compound coverage. Path-independence on each dimension proven in
# isolation surfaces accounting drift the compound machine can mask under
# noisy mutation streams.
# ---------------------------------------------------------------------------


# Machine 5 — Stale-date mutation accounting
# ---------------------------------------------------------------------------


class StaleMutationMachine(RuleBasedStateMachine):
    """Toggle `effective_from` between fresh and stale dates, verify stale_count.

    Invariant: stale_count == #rows whose current effective_from is older than
    today - 10 years. None / "" / unparseable values do NOT count as stale
    (they vanish into null_rate, not stale_rate).
    """

    TODAY = date(2024, 6, 1)
    FRESH_DATE = "2024-01-01"  # < 10y, not stale
    STALE_DATE = "2010-01-01"  # > 10y, stale
    # _is_stale uses `timedelta(days=10*365) = 3650 days`, which differs from
    # 10 calendar years by ~2-3 days (leap-year drift). Threshold lands around
    # 2014-06-04, so 2014-06-02 is actually 1 day STALE. Pick a date that is
    # unambiguously fresh — 2-year buffer past the boundary is plenty.
    SECOND_FRESH_DATE = "2018-06-01"

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        # Track which row-indexes carry a stale date right now.
        self.stale_indexes: set[int] = set()

    @initialize(n=st.integers(min_value=4, max_value=12))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]
        self.stale_indexes = set()

    @rule(row_idx=st.integers(0, 11))
    def make_stale(self, row_idx):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["effective_from"] = self.STALE_DATE
        self.stale_indexes.add(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_fresh(self, row_idx):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["effective_from"] = self.FRESH_DATE
        self.stale_indexes.discard(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_alt_fresh(self, row_idx):
        # Alternate fresh value — exercises the path where row was stale and
        # is moved back to a different (still-fresh) date. Distinct from the
        # FRESH_DATE rule so hypothesis exercises both transitions.
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["effective_from"] = self.SECOND_FRESH_DATE
        self.stale_indexes.discard(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_null(self, row_idx):
        # NULL effective_from is NOT stale — null_rate counts it instead.
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["effective_from"] = None
        self.stale_indexes.discard(row_idx)

    @invariant()
    def stale_count_matches_active_indexes(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=self.TODAY, null_coverage_threshold=1.01
        )
        assert r["stale_count"] == len(self.stale_indexes), (
            f"stale_count drift: report={r['stale_count']} "
            f"tracked={len(self.stale_indexes)} "
            f"indexes={sorted(self.stale_indexes)}"
        )

    @invariant()
    def stale_rate_consistent_with_count(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=self.TODAY, null_coverage_threshold=1.01
        )
        expected_rate = round(r["stale_count"] / r["sampled"], 4)
        assert abs(r["stale_rate"] - expected_rate) < 1e-4


TestStaleMutation = StaleMutationMachine.TestCase
TestStaleMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# Machine 6 — Integrity-violation mutation accounting
# ---------------------------------------------------------------------------


class IntegrityViolationMutationMachine(RuleBasedStateMachine):
    """Independently toggle `reviewed_at` and `reviewed_by`; verify
    integrity_violations == count(rows where exactly-one is set).

    Truth table per row (treating None / "" as falsy):
      reviewed_at | reviewed_by | violation?
      ──────────────────────────────────────
      F           | F           | no
      T           | F           | YES
      F           | T           | YES
      T           | T           | no
    """

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []

    @initialize(n=st.integers(min_value=4, max_value=12))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]

    @rule(row_idx=st.integers(0, 11))
    def remove_reviewed_at(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["reviewed_at"] = None

    @rule(row_idx=st.integers(0, 11))
    def remove_reviewed_by(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["reviewed_by"] = None

    @rule(row_idx=st.integers(0, 11))
    def restore_both(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["reviewed_at"] = "2024-01-02"
            self.rows[row_idx]["reviewed_by"] = "auditor"

    @rule(row_idx=st.integers(0, 11))
    def remove_both(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["reviewed_at"] = None
            self.rows[row_idx]["reviewed_by"] = None

    @invariant()
    def integrity_count_matches_xor(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        # Recompute expected: count rows where bool(at) ^ bool(by).
        expected = sum(
            1 for row in self.rows
            if bool(row.get("reviewed_at")) ^ bool(row.get("reviewed_by"))
        )
        assert r["integrity_violations"] == expected, (
            f"integrity drift: report={r['integrity_violations']} "
            f"expected={expected} "
            f"pairs={[(r2.get('reviewed_at'), r2.get('reviewed_by')) for r2 in self.rows]}"
        )


TestIntegrityViolationMutation = IntegrityViolationMutationMachine.TestCase
TestIntegrityViolationMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# Machine 7 — Jurisdiction-mismatch mutation accounting
# ---------------------------------------------------------------------------


class JurisdictionMismatchMutationMachine(RuleBasedStateMachine):
    """Toggle jurisdiction_code / jurisdiction_scope; verify mismatch count.

    The audit's `_count_jurisdiction_mismatches` rule:
      1. If scope is set AND not in ALLOWED_JURISDICTION_SCOPES → +1 (continue)
      2. Else if XOR(code, scope) → +1
      3. Else → 0

    So a row contributes IFF: (scope set AND scope ∉ ALLOWED) OR XOR(code, scope).
    """

    # Sample one valid scope and one invalid one to drive both branches.
    VALID_SCOPE = "national"
    INVALID_SCOPE = "galactic"  # not in ALLOWED_JURISDICTION_SCOPES

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []

    @initialize(n=st.integers(min_value=4, max_value=12))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]

    @rule(row_idx=st.integers(0, 11))
    def remove_code(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["jurisdiction_code"] = None

    @rule(row_idx=st.integers(0, 11))
    def remove_scope(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["jurisdiction_scope"] = None

    @rule(row_idx=st.integers(0, 11))
    def set_invalid_scope(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["jurisdiction_scope"] = self.INVALID_SCOPE

    @rule(row_idx=st.integers(0, 11))
    def set_valid_scope(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["jurisdiction_scope"] = self.VALID_SCOPE

    @rule(row_idx=st.integers(0, 11))
    def restore_pair(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["jurisdiction_code"] = "CN"
            self.rows[row_idx]["jurisdiction_scope"] = self.VALID_SCOPE

    @invariant()
    def mismatch_count_matches_rule(self):
        if not self.rows:
            return
        from src.kg.bitemporal_query import ALLOWED_JURISDICTION_SCOPES
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        expected = 0
        for row in self.rows:
            code = row.get("jurisdiction_code")
            scope = row.get("jurisdiction_scope")
            if scope and scope not in ALLOWED_JURISDICTION_SCOPES:
                expected += 1
                continue
            if bool(code) ^ bool(scope):
                expected += 1
        assert r["jurisdiction_mismatches"] == expected, (
            f"jurisdiction mismatch drift: report={r['jurisdiction_mismatches']} "
            f"expected={expected} "
            f"pairs={[(r2.get('jurisdiction_code'), r2.get('jurisdiction_scope')) for r2 in self.rows]}"
        )


TestJurisdictionMismatchMutation = JurisdictionMismatchMutationMachine.TestCase
TestJurisdictionMismatchMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# Machine 8 — Cross-dimension orthogonality
# ---------------------------------------------------------------------------


class OrthogonalityMachine(RuleBasedStateMachine):
    """Each rule mutates exactly ONE dimension via a NON-OVERLAPPING field.
    Invariant: dimensions NOT mutated stay at their clean baseline (0).

    Field-routing matrix:
      dim            | field mutated      | side-effects
      placeholder    | extracted_by       | NOT in CRITICAL_COLUMNS → null_coverage unaffected
      duplicate      | id                 | id never tracked by other dims
      stale          | effective_from set to old date → still non-NULL → null_coverage unaffected
      integrity      | reviewed_by → None | NOT in CRITICAL_COLUMNS → null_coverage unaffected;
                                            None ≠ banlist string → placeholder unaffected
      null_coverage  | confidence → None  | NOT a string → placeholder unaffected;
                                            confidence not used elsewhere

    Static-zero dimensions (never intentionally mutated, must stay at 0):
      jurisdiction_mismatches, prohibited_role_count, invalid_chain_count,
      inconsistent_scope_count.
    """

    TODAY = date(2024, 6, 1)
    THRESHOLD = 0.5

    DIM_KEY = {
        "placeholder": "placeholder_string_count",
        "duplicate": "duplicate_id_count",
        "stale": "stale_count",
        "integrity": "integrity_violations",
        "null_coverage": "null_coverage_violation_count",
    }
    STATIC_ZERO_DIMS = (
        "jurisdiction_mismatches",
        "prohibited_role_count",
        "invalid_chain_count",
        "inconsistent_scope_count",
    )

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        # Track which abstract dimensions have received at least one mutation.
        self.expected_pos: set[str] = set()

    @initialize(n=st.integers(min_value=4, max_value=12))
    def start_clean(self, n):
        self.rows = [_clean_row(i) for i in range(n)]
        self.expected_pos = set()

    @rule(row_idx=st.integers(0, 11), banned=st.sampled_from(_BANLIST_LIST))
    def mutate_placeholder_only(self, row_idx, banned):
        if row_idx < len(self.rows):
            self.rows[row_idx]["extracted_by"] = banned
            self.expected_pos.add("placeholder")

    @rule(row_idx=st.integers(0, 11))
    def mutate_duplicate_only(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["id"] = "SHARED"
            self.expected_pos.add("duplicate")

    @rule(row_idx=st.integers(0, 11))
    def mutate_stale_only(self, row_idx):
        if row_idx < len(self.rows):
            # Set to old date, NOT None — preserves non-NULL for null_coverage isolation.
            self.rows[row_idx]["effective_from"] = "2010-01-01"
            self.expected_pos.add("stale")

    @rule(row_idx=st.integers(0, 11))
    def mutate_integrity_only(self, row_idx):
        if row_idx < len(self.rows):
            self.rows[row_idx]["reviewed_by"] = None  # XOR with reviewed_at
            self.expected_pos.add("integrity")

    @rule(row_idx=st.integers(0, 11))
    def mutate_null_coverage_only(self, row_idx):
        if row_idx < len(self.rows):
            # confidence is the cleanest critical column to NULL: numeric, not
            # a string (so placeholder gate doesn't fire even at 0% rows), not
            # a date (stale gate doesn't fire), not in lineage envelope.
            self.rows[row_idx]["confidence"] = None
            # Whether this dim actually fires depends on threshold — only flag
            # `expected_pos` if at least 50% of rows are now NULL on confidence.
            null_share = sum(
                1 for r in self.rows if r.get("confidence") is None
            ) / max(len(self.rows), 1)
            if null_share >= self.THRESHOLD:
                self.expected_pos.add("null_coverage")
            else:
                # Below threshold → no defect should fire; keep expected_pos clean.
                self.expected_pos.discard("null_coverage")

    @invariant()
    def non_mutated_dims_stay_at_baseline(self):
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=self.TODAY, null_coverage_threshold=self.THRESHOLD
        )
        for dim_name, count_key in self.DIM_KEY.items():
            if dim_name not in self.expected_pos:
                assert r[count_key] == 0, (
                    f"orthogonality breach: dim={dim_name} count={r[count_key]} "
                    f"despite no mutation. mutated={sorted(self.expected_pos)}\n"
                    f"rows snapshot: {self.rows[:3]}..."
                )

    @invariant()
    def static_zero_dims_remain_zero(self):
        # Dimensions we never mutate must stay at baseline 0 — catches
        # accidental cross-talk if a rule body grows side-effects.
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=self.TODAY, null_coverage_threshold=self.THRESHOLD
        )
        for dim in self.STATIC_ZERO_DIMS:
            assert r[dim] == 0, (
                f"static-zero dim {dim} broke baseline: count={r[dim]}\n"
                f"mutated={sorted(self.expected_pos)}\n"
                f"rows snapshot: {self.rows[:3]}..."
            )


TestOrthogonality = OrthogonalityMachine.TestCase
TestOrthogonality.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# ---------------------------------------------------------------------------
# Machine 9 — Prohibited-role clause-axis mutation accounting (Sprint E2)
# ---------------------------------------------------------------------------


class ProhibitedRoleMutationMachine(RuleBasedStateMachine):
    """Toggle `argument_role` between non-prohibited and 税收法定-prohibited
    values, verify prohibited_role_count tracks rows currently in the
    prohibited state.

    Invariant: prohibited_role_count == #rows whose current argument_role is
    on the 税收法定 prohibition list. None and unknown roles do NOT count
    as prohibited (they vanish into other inspector flags, not this counter).

    Anchor values (from `src/kg/argument_role_registry.py`):
      * `analogy`   — RoleMeta(prohibited_in_tax_law=True, label_zh=类推适用)
      * `yiju`      — statutory basis, not prohibited
      * `shouquan`  — delegated authority, not prohibited

    Two distinct non-prohibited roles cover both clean→clean transitions
    (yiju→shouquan) and prohibited→clean transitions (analogy→yiju).
    Single-clean designs miss the second transition class — same lesson
    Sprint D learned with `make_alt_fresh`.
    """

    PROHIBITED_ROLE = "analogy"
    CLEAN_ROLE = "yiju"
    ALT_CLEAN_ROLE = "shouquan"

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        # Row-indexes whose argument_role is currently prohibited.
        self.prohibited_indexes: set[int] = set()

    @initialize(n=st.integers(min_value=4, max_value=12))
    def start_clean(self, n):
        self.rows = []
        for i in range(n):
            row = _clean_row(i)
            row["argument_role"] = self.CLEAN_ROLE
            self.rows.append(row)
        self.prohibited_indexes = set()

    @rule(row_idx=st.integers(0, 11))
    def make_prohibited(self, row_idx):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["argument_role"] = self.PROHIBITED_ROLE
        self.prohibited_indexes.add(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_clean(self, row_idx):
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["argument_role"] = self.CLEAN_ROLE
        self.prohibited_indexes.discard(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_alt_clean(self, row_idx):
        # Alternate clean role — exercises prohibited→alt-clean and
        # clean→alt-clean transitions distinct from the CLEAN_ROLE rule.
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["argument_role"] = self.ALT_CLEAN_ROLE
        self.prohibited_indexes.discard(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_null_role(self, row_idx):
        # NULL argument_role is NOT prohibited — inspector returns role=None
        # which `is_prohibited_in_tax_law` never sees.
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["argument_role"] = None
        self.prohibited_indexes.discard(row_idx)

    @invariant()
    def prohibited_count_matches_active_indexes(self):
        if not self.rows:
            return
        # null_coverage_threshold=1.01 ensures null_coverage gate never fires
        # — keeps this machine focused on the prohibited_role axis only.
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        assert r["prohibited_role_count"] == len(self.prohibited_indexes), (
            f"prohibited_role_count drift: report={r['prohibited_role_count']} "
            f"tracked={len(self.prohibited_indexes)} "
            f"indexes={sorted(self.prohibited_indexes)}"
        )


TestProhibitedRoleMutation = ProhibitedRoleMutationMachine.TestCase
TestProhibitedRoleMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)


# ---------------------------------------------------------------------------
# Machine 10 — Inconsistent-scope clause-axis mutation accounting (Sprint F1)
# ---------------------------------------------------------------------------


class InconsistentScopeMutationMachine(RuleBasedStateMachine):
    """Toggle (jurisdiction_code, jurisdiction_scope) between consistent
    and clause-axis-inconsistent pairs, verify inconsistent_scope_count
    tracks rows whose pair currently violates the co-variance decision
    table (national ↔ national / iso_admin ↔ {subnational,municipal} /
    special_zone ↔ zone.scope).

    Invariant: inconsistent_scope_count == #rows whose current
    (code, scope) pair has `_check_consistency` verdict == "inconsistent".

    Orthogonality contract (key design decision):
      All chosen pairs use codes + scopes that pass row-axis
      `_count_jurisdiction_mismatches` (scope ∈ ALLOWED_JURISDICTION_SCOPES,
      both code+scope set so XOR is False). This isolates the clause-axis
      counter from the row-axis counter — flipping a row from CONSISTENT
      to INCONSISTENT must increment `inconsistent_scope_count` by exactly
      1 and leave `jurisdiction_mismatches` at 0.

    Anchor pairs (verified against `src/kg/jurisdiction_consistency.py`):
      Consistent baseline:
        ("CN", "national")  — national kind expects scope="national" ✓
      Inconsistent (clause-axis only, row-axis still 0):
        ("CN", "subnational")        — national kind, scope mismatch
        ("CN-31", "national")        — iso_admin kind, scope mismatch
    Why two distinct inconsistent pairs: same Sprint D / Sprint E2 lesson —
    single-mutation-rule designs miss the inconsistent_A → inconsistent_B
    transition class. Hypothesis exercises consistent ↔ inconsistent_1 ↔
    inconsistent_2 triangle, not just a binary toggle.

    Null-scope handling (verdict='scope_not_set' → no flag, but row-axis XOR
    fires because code is set + scope is None) is intentionally NOT exercised
    by this machine — that mixed concern is a separate Sprint F2 candidate.
    Keeping all three rules in the row-axis-clean band ensures the explicit
    orthogonality invariant below stays meaningful.
    """

    CODE_NATIONAL = "CN"
    CODE_ISO_ADMIN = "CN-31"
    CONSISTENT_SCOPE = "national"  # matches CN (national kind)
    INCONSISTENT_SCOPE_FOR_NATIONAL = "subnational"  # in whitelist, mismatches CN
    # CN-31 (iso_admin) expects {subnational, municipal}; "national" is the
    # mismatch that still passes the row-axis whitelist check.
    INCONSISTENT_SCOPE_FOR_ISO = "national"

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        # Row-indexes whose (code, scope) is currently clause-axis-inconsistent.
        self.inconsistent_indexes: set[int] = set()

    @initialize(n=st.integers(min_value=4, max_value=12))
    def start_clean(self, n):
        self.rows = []
        for i in range(n):
            row = _clean_row(i)
            row["jurisdiction_code"] = self.CODE_NATIONAL
            row["jurisdiction_scope"] = self.CONSISTENT_SCOPE
            self.rows.append(row)
        self.inconsistent_indexes = set()

    @rule(row_idx=st.integers(0, 11))
    def make_national_inconsistent(self, row_idx):
        # CN + subnational: national kind expects scope=national; subnational
        # is in whitelist (row-axis OK) but mismatches per decision table.
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["jurisdiction_code"] = self.CODE_NATIONAL
        self.rows[row_idx]["jurisdiction_scope"] = (
            self.INCONSISTENT_SCOPE_FOR_NATIONAL
        )
        self.inconsistent_indexes.add(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_iso_inconsistent(self, row_idx):
        # CN-31 + national: iso_admin expects {subnational, municipal};
        # national is in whitelist (row-axis OK) but mismatches per table.
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["jurisdiction_code"] = self.CODE_ISO_ADMIN
        self.rows[row_idx]["jurisdiction_scope"] = self.INCONSISTENT_SCOPE_FOR_ISO
        self.inconsistent_indexes.add(row_idx)

    @rule(row_idx=st.integers(0, 11))
    def make_consistent(self, row_idx):
        # Restore baseline (CN, national).
        if row_idx >= len(self.rows):
            return
        self.rows[row_idx]["jurisdiction_code"] = self.CODE_NATIONAL
        self.rows[row_idx]["jurisdiction_scope"] = self.CONSISTENT_SCOPE
        self.inconsistent_indexes.discard(row_idx)

    @invariant()
    def inconsistent_count_matches_active_indexes(self):
        if not self.rows:
            return
        # null_coverage_threshold=1.01 ensures null_coverage gate never fires.
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        assert r["inconsistent_scope_count"] == len(self.inconsistent_indexes), (
            f"inconsistent_scope_count drift: report={r['inconsistent_scope_count']} "
            f"tracked={len(self.inconsistent_indexes)} "
            f"indexes={sorted(self.inconsistent_indexes)}"
        )

    @invariant()
    def row_axis_jurisdiction_mismatches_stays_at_zero(self):
        # ORTHOGONALITY CONTRACT: every state this machine reaches has
        # both code+scope set, scope ∈ ALLOWED_JURISDICTION_SCOPES, so
        # row-axis _count_jurisdiction_mismatches must return 0. If this
        # ever fails, the machine has accidentally contaminated the
        # row-axis dim and is no longer a clean clause-axis test.
        if not self.rows:
            return
        r = survey_type(
            self.rows, today=date(2024, 6, 1), null_coverage_threshold=1.01
        )
        assert r["jurisdiction_mismatches"] == 0, (
            f"orthogonality broken: row-axis jurisdiction_mismatches "
            f"={r['jurisdiction_mismatches']} (expected 0). "
            f"A clause-axis machine must not leak into row-axis count.\n"
            f"rows snapshot: {self.rows[:3]}..."
        )


TestInconsistentScopeMutation = InconsistentScopeMutationMachine.TestCase
TestInconsistentScopeMutation.settings = settings(
    max_examples=400,
    stateful_step_count=50,
    suppress_health_check=[HealthCheck.filter_too_much],
)
