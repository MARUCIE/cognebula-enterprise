#!/usr/bin/env bash
# Data-quality test suite tiered runner.
#
# Three tiers per CI strategy:
#   fast      → PR-level gate (must complete < 5s)
#   standard  → merge-to-main gate (< 15s)
#   nightly   → cron gate (< 60s)
#
# Each tier is a strict superset of the prior tier's coverage axis but
# deduplicated: nightly does NOT re-run fast tests separately; the assumption
# is nightly = fast ∪ standard ∪ heavy. Use `all` to run every layer.
#
# Usage:
#   ./scripts/run_data_quality_tests.sh fast
#   ./scripts/run_data_quality_tests.sh standard
#   ./scripts/run_data_quality_tests.sh nightly
#   ./scripts/run_data_quality_tests.sh all
#   ./scripts/run_data_quality_tests.sh count   # report case count without running

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python3}"
PYTEST="${PYTEST:-$PYTHON -m pytest}"

FAST_FILES=(
    "tests/test_data_quality_survey.py"
    "tests/test_data_quality_api_client.py"
    "tests/test_data_quality_edge.py"
)

STANDARD_FILES=(
    "${FAST_FILES[@]}"
    "tests/test_data_quality_orchestration.py"
    "tests/test_data_quality_corpus.py"
    "tests/test_data_quality_golden.py"
    "tests/test_data_quality_perf_regression.py"
)

NIGHTLY_FILES=(
    "${STANDARD_FILES[@]}"
    "tests/test_data_quality_property.py"
    "tests/test_data_quality_matrix.py"
    "tests/test_data_quality_mutation.py"
    "tests/test_schema_completeness.py"
    "tests/test_api_contract_drift.py"
)

case "${1:-standard}" in
    fast)
        echo "=== fast tier (PR gate) ==="
        $PYTEST "${FAST_FILES[@]}" -q
        ;;
    standard)
        echo "=== standard tier (merge-to-main gate) ==="
        $PYTEST "${STANDARD_FILES[@]}" -q
        ;;
    nightly|all)
        echo "=== nightly tier (full suite) ==="
        $PYTEST "${NIGHTLY_FILES[@]}" -q
        ;;
    count)
        echo "=== test case count by tier ==="
        echo "(executes pytest --collect-only; no tests run)"
        echo
        echo "--- fast ---"
        $PYTEST "${FAST_FILES[@]}" --collect-only -q 2>&1 | tail -1
        echo
        echo "--- standard ---"
        $PYTEST "${STANDARD_FILES[@]}" --collect-only -q 2>&1 | tail -1
        echo
        echo "--- nightly ---"
        $PYTEST "${NIGHTLY_FILES[@]}" --collect-only -q 2>&1 | tail -1
        ;;
    *)
        echo "usage: $0 {fast|standard|nightly|all|count}" >&2
        exit 2
        ;;
esac
