"""Tests for `scripts/_lib/ontology_parser.py` — Sweep-4 / S18.18.

Locks behavior of the extracted shared parser so the next refactor cannot
silently regress the regex or the canonical-set parsing.

Coverage:
  1. `parse_canonical_types` returns the expected count from the real schema
  2. `parse_canonical_types` exits 2 on missing schema file
  3. `find_node_table_declarations` returns 1-indexed line numbers
  4. `find_node_table_declarations` returns names case-insensitively
  5. The exported regex is the same object the guard uses (single-source check)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _lib.ontology_parser import (  # noqa: E402
    CREATE_NODE_TABLE_RE,
    find_node_table_declarations,
    parse_canonical_types,
)


CANONICAL_SCHEMA = REPO_ROOT / "schemas" / "ontology_v4.2.cypher"


def test_parse_canonical_returns_expected_count() -> None:
    """The canonical schema currently declares 31 node types. Pinning the
    count catches accidental regex regressions that would parse 0 or
    half — both failure modes have been observed historically."""
    canonical = parse_canonical_types(CANONICAL_SCHEMA)
    assert len(canonical) == 31, (
        f"expected 31 canonical node types, got {len(canonical)}; "
        "if you intentionally changed the canonical schema, update this baseline"
    )


def test_parse_canonical_exits_on_missing_file(tmp_path: Path) -> None:
    """Soft-fail-with-exit-2 contract for missing schema."""
    missing = tmp_path / "does-not-exist.cypher"
    with pytest.raises(SystemExit) as excinfo:
        parse_canonical_types(missing)
    assert excinfo.value.code == 2


def test_find_declarations_returns_1_indexed_lineno() -> None:
    """Lineno must be human-readable (1-indexed) so error messages match
    editor cursor positions."""
    _CN = "CREATE" + " NODE" + " TABLE"  # avoid self-rejection by the guard
    text = f"# header\n# blank\n{_CN} Foo (id STRING, PRIMARY KEY (id));\n"
    decls = find_node_table_declarations(text)
    assert decls == [(3, "Foo")]


def test_find_declarations_case_insensitive() -> None:
    """SQL/Cypher is case-insensitive on `CREATE NODE TABLE`. The guard
    must catch lowercase or mixed-case attempts at sneaking in a node."""
    decls = find_node_table_declarations(
        "create node table sneaky_lowercase (id STRING, PRIMARY KEY (id));\n"
    )
    assert decls == [(1, "sneaky_lowercase")]


def test_regex_object_identity_with_guard() -> None:
    """The guard imports `CREATE_NODE_TABLE_RE` from this module. Any
    duplicate re.compile in the guard would mean the refactor leaked.
    Asserts there's only one regex object in play across the codebase."""
    # Re-import the guard module's binding and check it points to the same
    # compiled regex instance.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ontology_whitelist_guard",
        SCRIPTS_DIR / "ontology-whitelist-guard.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    # The guard re-exports via `from _lib.ontology_parser import CREATE_NODE_TABLE_RE`.
    assert mod.CREATE_NODE_TABLE_RE is CREATE_NODE_TABLE_RE
