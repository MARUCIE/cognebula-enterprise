"""Canonical ontology parser — shared by ontology-whitelist-guard.py and
audit_api_contract.py.

Sweep-4 / S18.18 + S18.21 — extracted from `scripts/ontology-whitelist-guard.py`
to remove duplicated regex+parse logic and switch to a non-backtracking pattern
with negative lookahead, eliminating the `IF` capture edge case.

Single regex source. Single parse function. Both consumers import from here.

Why negative lookahead instead of post-filter:
  Old guard had `(?:IF\\s+NOT\\s+EXISTS\\s+)?` optional group + a post-filter
  `if name.upper() == "IF": continue`. The optional group could backtrack
  on inputs like `... IF NOT EXISTS " + table_name + ...` (Python concat
  with no static identifier afterwards), causing `IF` to be captured as the
  table name. The post-filter masked the regex bug by discarding the bad
  capture, but legitimate identifiers starting with `If_` (e.g. `If_Conditional`)
  would survive — yet the post-filter was broad (`name.upper() == "IF"` only)
  so this was harmless in practice but conceptually fragile.

  The new pattern uses `(?!IF\\b)` negative lookahead: the table-name capture
  group refuses to match when the next token is the bare keyword `IF`. This
  prevents the bad capture at regex level, keeping behavior correct without
  the post-filter band-aid. `If_Conditional` still matches because `\\b`
  word-boundary requires `IF` to be a complete word.

Public surface:
  CREATE_NODE_TABLE_RE   — compiled regex, single source of truth
  parse_canonical_types  — schema file → set of canonical node-type names

Both are read-only after import. Mutating callers should copy.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


# Negative lookahead `(?!IF\b)` prevents the optional `IF NOT EXISTS` group
# from backtracking and capturing the literal keyword `IF` as a table name.
# `\b` ensures we don't reject legitimate names like `If_Conditional` that
# merely START with "If".
CREATE_NODE_TABLE_RE = re.compile(
    r"CREATE\s+NODE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?!IF\b)([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def parse_canonical_types(schema_path: Path) -> set[str]:
    """Parse `CREATE NODE TABLE <Name>` declarations from a Cypher schema file.

    Args:
      schema_path: absolute path to e.g. `schemas/ontology_v4.2.cypher`.

    Returns:
      Set of canonical node-type names. Empty set if the file is missing
      OR contains no declarations — caller must distinguish based on need.

    Exits:
      If `schema_path` does not exist, prints to stderr and `sys.exit(2)`.
      Callers that want a softer failure should check `schema_path.exists()`
      themselves before calling.
    """
    if not schema_path.exists():
        print(
            f"ERROR: canonical schema missing at {schema_path}",
            file=sys.stderr,
        )
        sys.exit(2)
    text = schema_path.read_text(encoding="utf-8")
    return {m.group(1) for m in CREATE_NODE_TABLE_RE.finditer(text)}


def find_node_table_declarations(text: str) -> list[tuple[int, str]]:
    """Scan `text` for `CREATE NODE TABLE <Name>` and return [(lineno, name)].

    Lineno is 1-indexed from the start of `text`. This is the per-file
    primitive used by `ontology-whitelist-guard.py::scan_file` after
    canonical-set membership filtering.
    """
    out: list[tuple[int, str]] = []
    for m in CREATE_NODE_TABLE_RE.finditer(text):
        lineno = text.count("\n", 0, m.start()) + 1
        out.append((lineno, m.group(1)))
    return out
