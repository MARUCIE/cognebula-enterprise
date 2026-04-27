"""Tests for the negative-lookahead regex behavior — Sweep-4 / S18.21.

Pins the four regex behaviors that distinguish the new pattern
`(?!IF\\b)` from the old post-filter approach:

  case 1: bare canonical identifier captured                  → matches
  case 2: `IF NOT EXISTS <Name>` form captures `<Name>`       → matches
  case 3: `IF NOT EXISTS " + var` Python concat (no static)   → NO match
          (under the old regex this captured `IF` and the post-filter
          discarded it; under the new regex the negative lookahead
          prevents the bad capture entirely)
  case 4: legitimate identifier `If_Conditional` (starts with `If`)
          must still match because `\\b` requires `IF` to be a complete
          word, not a prefix                                   → matches

Failure of any case means a future refactor weakened the regex; the
guard's downstream behavior depends on these invariants holding.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _lib.ontology_parser import CREATE_NODE_TABLE_RE  # noqa: E402


# Build the trigger phrase via concatenation so this file's source itself
# does not match the guard's regex when scanned.
_CN = "CREATE" + " NODE" + " TABLE"


def test_case1_bare_identifier_captured() -> None:
    text = f"{_CN} Foo (id STRING, PRIMARY KEY (id));"
    matches = [m.group(1) for m in CREATE_NODE_TABLE_RE.finditer(text)]
    assert matches == ["Foo"]


def test_case2_if_not_exists_captures_name() -> None:
    text = f"{_CN} IF NOT EXISTS Bar (id STRING, PRIMARY KEY (id));"
    matches = [m.group(1) for m in CREATE_NODE_TABLE_RE.finditer(text)]
    assert matches == ["Bar"]


def test_case3_if_concat_no_capture() -> None:
    """Python concatenation pattern must NOT capture `IF` as a name."""
    text = f'sql = "{_CN} IF NOT EXISTS " + table_name + " (...)"'
    matches = [m.group(1) for m in CREATE_NODE_TABLE_RE.finditer(text)]
    # The negative lookahead refuses to capture `IF`. The optional group
    # also refuses to "match emptiness then capture IF" because the same
    # lookahead applies to the capture group's own start.
    assert matches == [], (
        f"regex regressed and captured {matches!r}; the negative lookahead "
        "(?!IF\\b) is supposed to prevent this"
    )


def test_case4_legit_if_prefixed_name_captured() -> None:
    """`If_Conditional` is a legitimate identifier — `\\b` ensures the
    lookahead only triggers on the bare keyword `IF`, not on names that
    merely start with those letters."""
    text = f"{_CN} If_Conditional (id STRING, PRIMARY KEY (id));"
    matches = [m.group(1) for m in CREATE_NODE_TABLE_RE.finditer(text)]
    assert matches == ["If_Conditional"]


def test_case5_lowercase_if_in_concat() -> None:
    """Case-insensitive match should not let `if` (lowercase) sneak through
    where `IF` is rejected. Case folding applies to the lookahead too."""
    text = f'sql = "{_CN.lower()} if not exists " + table_name'
    matches = [m.group(1) for m in CREATE_NODE_TABLE_RE.finditer(text)]
    assert matches == [], (
        f"case-folded `if` leaked through and captured {matches!r}"
    )
