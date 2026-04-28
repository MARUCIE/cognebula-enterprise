"""Tests for diff-mode scanning — Sweep-5 / S18.22.

The guard now has two scan modes:

  - file-mode (legacy CI path, argv-driven) — scans the FULL TEXT of each
    file in argv. False-rejects on pre-existing unauthorized declarations.
  - diff-mode (new default for pre-commit, argv-empty path) — scans only
    `+` lines in `git diff --cached -U0`. Pre-existing rogue declarations
    no longer block unrelated edits.

These tests exercise the unified-diff parser directly with synthetic
fixtures (no git invocation), so they're hermetic.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Import the guard module dynamically (it has a hyphen in its filename).
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ontology_whitelist_guard",
    SCRIPTS_DIR / "ontology-whitelist-guard.py",
)
assert _spec is not None and _spec.loader is not None
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)  # type: ignore[union-attr]


_CN = "CREATE" + " NODE" + " TABLE"


def test_parse_unified_diff_added_lines_only() -> None:
    """Removed lines must NOT appear in the output. Hunk header `@@ -X,Y +Z,W @@`
    sets the new-file lineno to Z; subsequent `+` lines increment from there."""
    diff = (
        "diff --git a/scripts/foo.py b/scripts/foo.py\n"
        "--- a/scripts/foo.py\n"
        "+++ b/scripts/foo.py\n"
        "@@ -10,1 +10,2 @@\n"
        "-old_line_removed\n"
        "+new_line_added\n"
        "+second_added\n"
    )
    out = guard._parse_unified_diff(diff)
    assert out == [
        ("scripts/foo.py", 10, "new_line_added"),
        ("scripts/foo.py", 11, "second_added"),
    ]


def test_parse_unified_diff_lineno_advances_only_on_added() -> None:
    """`-` lines do not advance new-file lineno. With `-U0` no context lines
    appear, so a hunk that pairs `-` and `+` keeps the same lineno for `+`."""
    diff = (
        "+++ b/scripts/bar.py\n"
        "@@ -5,1 +5,1 @@\n"
        "-replaced\n"
        "+replacement\n"
    )
    out = guard._parse_unified_diff(diff)
    assert out == [("scripts/bar.py", 5, "replacement")]


def test_parse_unified_diff_handles_multiple_files() -> None:
    """Path tracking must reset on each `+++ b/<path>` header."""
    diff = (
        "+++ b/a.py\n"
        "@@ -0,0 +1,1 @@\n"
        "+from_a\n"
        "+++ b/b.py\n"
        "@@ -0,0 +1,1 @@\n"
        "+from_b\n"
    )
    out = guard._parse_unified_diff(diff)
    assert out == [("a.py", 1, "from_a"), ("b.py", 1, "from_b")]


def test_parse_unified_diff_skips_diff_metadata() -> None:
    """`diff --git`, `index abc..def`, `Binary files differ`, etc. must not
    appear as added content."""
    diff = (
        "diff --git a/scripts/x.py b/scripts/x.py\n"
        "index 1234567..abcdefg 100644\n"
        "--- a/scripts/x.py\n"
        "+++ b/scripts/x.py\n"
        "@@ -1,0 +1,1 @@\n"
        "+real_added_line\n"
    )
    out = guard._parse_unified_diff(diff)
    assert out == [("scripts/x.py", 1, "real_added_line")]


def test_diff_mode_catches_newly_added_rogue() -> None:
    """End-to-end: a `+` line introducing an unauthorized declaration is
    detected. Uses the parser directly + the regex from _lib."""
    from _lib.ontology_parser import CREATE_NODE_TABLE_RE

    diff = (
        "+++ b/src/api/sneaky.py\n"
        "@@ -0,0 +1,1 @@\n"
        f'+    cursor.execute("{_CN} FakeNeverDeclared (id STRING)")\n'
    )
    parsed = guard._parse_unified_diff(diff)
    rogue_hits: list[tuple[str, int, str]] = []
    for rel_path, lineno, content in parsed:
        for m in CREATE_NODE_TABLE_RE.finditer(content):
            rogue_hits.append((rel_path, lineno, m.group(1)))
    assert rogue_hits == [("src/api/sneaky.py", 1, "FakeNeverDeclared")]


def test_diff_mode_ignores_pre_existing_rogue() -> None:
    """The whole point of S18.22: a pre-existing rogue declaration that is
    NOT on a `+` line must be invisible to diff-mode. Here we simulate
    `git diff` only showing an unrelated edit at line 50, while the rogue
    declaration sits at line 5 of the file (not in the diff)."""
    from _lib.ontology_parser import CREATE_NODE_TABLE_RE

    # The rogue line is referenced via `-` (or simply absent from the diff
    # entirely). We model it as a `-` line that gets removed and re-added
    # unchanged — but more realistically, a pre-existing rogue is just
    # nowhere in the diff at all. Test the simpler case: diff has only a
    # benign edit elsewhere.
    diff = (
        "+++ b/src/api/legacy.py\n"
        "@@ -50,1 +50,1 @@\n"
        "-    return False  # old comment\n"
        "+    return True  # fixed bug\n"
    )
    parsed = guard._parse_unified_diff(diff)
    rogue_hits: list[tuple[str, int, str]] = []
    for rel_path, lineno, content in parsed:
        for m in CREATE_NODE_TABLE_RE.finditer(content):
            rogue_hits.append((rel_path, lineno, m.group(1)))
    assert rogue_hits == [], "diff-mode must not flag pre-existing declarations"
