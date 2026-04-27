"""Performance regression tests — wall-clock budgets on survey_type.

Sprint C focus: catch algorithmic regression. Today survey_type is O(n)
across 9 dimensions. If a future change accidentally makes any dimension
O(n²) (e.g. nested loop on duplicate detection, or a per-row schema
re-parse), these tests fire before the change merges.

Budgets (with 50% headroom over current observed times to avoid
CI-flakiness false-positives — the goal is catching regressions, not
optimizing for perfection):

  100 rows  → < 5ms   (typical: 1-2ms)
  1k rows   → < 30ms  (typical: 10-15ms)
  10k rows  → < 200ms (typical: 80-120ms)
  100k rows → < 2s    (typical: 800ms-1.2s)

If a typical case approaches the budget, investigate. If it exceeds, fail.
"""

from __future__ import annotations

import time
from datetime import date

import pytest

from src.audit.data_quality_survey import survey_type


def _gen_clean_rows(n: int) -> list[dict]:
    return [
        {
            "id": f"r_{i}",
            "effective_from": "2024-01-01",
            "confidence": 0.92,
            "source_doc_id": f"doc_{i}",
            "extracted_by": "extractor_v3",
            "reviewed_at": "2024-01-02",
            "reviewed_by": "auditor",
            "jurisdiction_code": "CN",
            "jurisdiction_scope": "national",
        }
        for i in range(n)
    ]


def _gen_dirty_rows(n: int) -> list[dict]:
    """Rows that exercise multiple dimensions — more realistic perf shape."""
    return [
        {
            "id": f"d_{i % (n // 10 if n >= 10 else 1)}",  # induce duplicates
            "effective_from": "2010-01-01" if i % 5 == 0 else "2024-01-01",
            "confidence": None if i % 7 == 0 else 0.5,
            "source_doc_id": "unknown" if i % 11 == 0 else f"doc_{i}",
            "reviewed_at": "x" if i % 3 == 0 else None,
            "reviewed_by": "y" if i % 4 == 0 else None,
            "jurisdiction_code": "CN" if i % 2 == 0 else None,
            "jurisdiction_scope": "national" if i % 2 == 1 else None,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Budget table
# ---------------------------------------------------------------------------


@pytest.mark.perf
@pytest.mark.parametrize("n,budget_ms", [
    (100, 5),
    (500, 15),
    (1_000, 30),
    (5_000, 100),
    (10_000, 200),
])
def test_clean_rows_perf_budget(n, budget_ms):
    rows = _gen_clean_rows(n)
    t0 = time.perf_counter()
    survey_type(rows, today=date(2024, 6, 1))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < budget_ms, (
        f"survey_type({n} clean rows) took {elapsed_ms:.1f}ms, "
        f"budget {budget_ms}ms. Algorithmic regression?"
    )


@pytest.mark.perf
@pytest.mark.parametrize("n,budget_ms", [
    (100, 10),
    (500, 30),
    (1_000, 60),
    (5_000, 200),
    (10_000, 400),
])
def test_dirty_rows_perf_budget(n, budget_ms):
    rows = _gen_dirty_rows(n)
    t0 = time.perf_counter()
    survey_type(rows, today=date(2024, 6, 1))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < budget_ms, (
        f"survey_type({n} dirty rows) took {elapsed_ms:.1f}ms, "
        f"budget {budget_ms}ms. Algorithmic regression?"
    )


# ---------------------------------------------------------------------------
# Linearity check — runtime must scale ~linearly with n
# ---------------------------------------------------------------------------


@pytest.mark.perf
def test_runtime_scales_linearly_with_n():
    """Detect O(n^k>1) regression by measuring 1k vs 10k row ratio.

    Linear: ratio ≈ 10× (within 4×-25× to allow O() noise).
    Quadratic: ratio ≈ 100× — would fail this gate immediately.
    """
    rows_small = _gen_clean_rows(1_000)
    rows_large = _gen_clean_rows(10_000)

    # Warm-up to amortize JIT / cache effects.
    survey_type(rows_small, today=date(2024, 6, 1))
    survey_type(rows_large, today=date(2024, 6, 1))

    # Best-of-3 to reduce noise.
    def time_it(rows):
        return min(
            (time.perf_counter() - t0) for t0 in (
                (lambda: (lambda t: (survey_type(rows, today=date(2024, 6, 1)), t)[1])(time.perf_counter()))()
                for _ in range(3)
            )
        )
    # Simpler:
    def best_of_3(rows):
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            survey_type(rows, today=date(2024, 6, 1))
            times.append(time.perf_counter() - t0)
        return min(times)

    t_small = best_of_3(rows_small)
    t_large = best_of_3(rows_large)
    ratio = t_large / max(t_small, 1e-6)
    # Linear scaling = 10×. Allow 4×-25× for sub-microsecond floor noise +
    # OS scheduling jitter. >25× = quadratic regression.
    assert 4 < ratio < 25, (
        f"runtime ratio 1k→10k = {ratio:.2f}× (expected ~10×). "
        f"t_small={t_small*1000:.2f}ms t_large={t_large*1000:.2f}ms"
    )


# ---------------------------------------------------------------------------
# Memory budget (rough — using sys.getsizeof on report dict)
# ---------------------------------------------------------------------------


@pytest.mark.perf
def test_report_dict_size_is_constant():
    """The report dict size is independent of input size — only
    summary metrics are stored, not the input rows.

    Catch: a future change that accidentally embeds raw rows or per-row
    breakdown into the report dict, blowing up memory at scale.
    """
    import sys
    r_small = survey_type(_gen_clean_rows(100), today=date(2024, 6, 1))
    r_large = survey_type(_gen_clean_rows(10_000), today=date(2024, 6, 1))
    size_small = sys.getsizeof(r_small)
    size_large = sys.getsizeof(r_large)
    # Should be within 2× — definitely not proportional to input size.
    assert size_large < size_small * 3, (
        f"report dict grew from {size_small}B to {size_large}B for 100x input. "
        f"Possible row data leaking into report?"
    )
