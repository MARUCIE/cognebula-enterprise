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
