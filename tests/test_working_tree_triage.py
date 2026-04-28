"""Tests for `scripts/working_tree_triage.py` — Sweep-8 / S18.30.

Locks the bucketing classifier + JSON schema so a future refactor can't
silently mis-classify critical_code into other (catastrophic loss of
signal) or drop bucket counts from the summary.

Coverage:
  1. _classify routes paths to the expected bucket (parametrized)
  2. _parse_status_line handles all common porcelain forms
  3. build_triage produces the documented JSON schema
  4. The script runs end-to-end without crashing
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# scripts/working_tree_triage.py is a script, not a package member, but
# the filename is import-friendly (underscores), so we can import it.
import working_tree_triage as triage  # noqa: E402


@pytest.mark.parametrize(
    "path,expected_bucket",
    [
        # critical_code
        ("kg-api-server.py", "critical_code"),
        ("src/api/kg_api.py", "critical_code"),
        ("src/_lib/capabilities.py", "critical_code"),
        ("scripts/audit_api_contract.py", "critical_code"),
        ("schemas/ontology_v4.2.cypher", "critical_code"),
        ("src/kg/whatever.py", "critical_code"),
        # tests
        ("tests/test_api_contract_drift.py", "tests"),
        ("tests/test_capabilities_factory.py", "tests"),
        # docs
        ("doc/00_project/initiative_cognebula_sota/HANDOFF.md", "docs"),
        ("README.md", "docs"),
        ("HANDOFF.md", "docs"),
        ("CLAUDE.md", "docs"),
        ("doc/index.md", "docs"),
        # configs
        ("configs/audit-manifest.json", "configs"),
        (".github/workflows/quality-gate.yml", "configs"),
        ("docker-compose.yml", "configs"),
        ("pytest.ini", "configs"),
        # data_or_cache
        ("data/finance-tax-graph.kuzu", "data_or_cache"),
        ("outputs/old-report.json", "data_or_cache"),
        (".wrangler/state/v3/r2/foo.sqlite", "data_or_cache"),
        ("__pycache__/foo.pyc", "data_or_cache"),
        ("foo.lock", "data_or_cache"),
        # other (catch-all)
        ("random/unclassified/file.txt", "other"),
        ("benchmark/results.json", "other"),
    ],
)
def test_classify_bucketing(path: str, expected_bucket: str) -> None:
    assert triage._classify(path) == expected_bucket, (
        f"path {path!r} bucketed as {triage._classify(path)!r}, "
        f"expected {expected_bucket!r}"
    )


@pytest.mark.parametrize(
    "line,expected",
    [
        (" M src/api/kg_api.py", (" M", "src/api/kg_api.py")),
        ("M  configs/foo.json", ("M ", "configs/foo.json")),
        (" D doc/old.md", (" D", "doc/old.md")),
        ("?? new_untracked.py", ("??", "new_untracked.py")),
        ("R  old_path -> new_path", ("R ", "new_path")),
        # Unparseable / too short
        ("", None),
        ("X", None),
    ],
)
def test_parse_status_line(line: str, expected: tuple[str, str] | None) -> None:
    assert triage._parse_status_line(line) == expected


def test_build_triage_schema_shape() -> None:
    """The JSON output shape is what scripts and humans consume.
    Pinning it here catches accidental key drops or renames."""
    result = triage.build_triage()
    # Either error-form or full-form.
    if "error" in result:
        assert "schema_version" in result
        return
    required_top_keys = {
        "schema_version",
        "run_utc",
        "git_head_sha",
        "git_branch",
        "summary",
        "buckets",
    }
    assert required_top_keys.issubset(result.keys()), (
        f"missing required top-level keys: "
        f"{required_top_keys - result.keys()}"
    )

    # Summary structure
    summary = result["summary"]
    assert {"total_dirty_entries", "status_breakdown", "bucket_counts"}.issubset(
        summary.keys()
    )
    assert isinstance(summary["total_dirty_entries"], int)
    assert isinstance(summary["bucket_counts"], dict)

    # Each bucket entry that exists must have the documented shape
    for name, b in result["buckets"].items():
        assert {
            "count",
            "status_breakdown",
            "total_added",
            "total_deleted",
            "top_5_by_churn",
        }.issubset(b.keys()), f"bucket {name} missing keys"
        assert len(b["top_5_by_churn"]) <= 5
        for entry in b["top_5_by_churn"]:
            assert {"path", "status", "added", "deleted", "churn"}.issubset(
                entry.keys()
            )


def test_script_runs_end_to_end(tmp_path: Path) -> None:
    """End-to-end: script produces both JSON + Markdown files."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "working_tree_triage.py"),
            "--out-dir",
            str(tmp_path),
            "--quiet",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"script failed (rc={result.returncode}); stderr: {result.stderr}"
    )
    json_out = tmp_path / "working-tree-triage.json"
    md_out = tmp_path / "working-tree-triage.md"
    assert json_out.exists()
    assert md_out.exists()
    # Validate JSON parses
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1


def test_render_markdown_includes_required_sections() -> None:
    result = triage.build_triage()
    md = triage.render_markdown(result)
    if "error" in result:
        assert "Error:" in md
        return
    assert "# Working Tree Triage Manifest" in md
    assert "## Summary" in md
    assert "## Top-5 by churn per bucket" in md
    # Bucket headers must be present (those that have entries).
    for name in result["buckets"]:
        assert f"`{name}`" in md
