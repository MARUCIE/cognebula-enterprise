#!/usr/bin/env python3
"""Pre-commit / CI guard: reject `CREATE NODE TABLE X` unless X is canonical.

Session 74 Wave 1 — P0 remediation. Installs the balancing feedback loop
(B_MISSING per Meadows) that was previously absent: today any Python/SQL/Cypher
change can add a new node type without review, so the ontology drifts
unboundedly (R1 reinforcing loop). This guard adds the PR-gated check.

Behavior:
  For each file passed on argv (or read from `git diff --cached --name-only` in
  pre-commit mode), scan the file's text for `CREATE NODE TABLE <Name>` or
  `CREATE NODE TABLE IF NOT EXISTS <Name>` statements. Look up each Name in the
  canonical set parsed from `schemas/ontology_v4.2.cypher`. Reject on miss.

Exceptions (whitelisted; not flagged):
  - The canonical schema file itself: `schemas/ontology_v4.2.cypher`
  - Migration staging files under `deploy/<any>/migrations/` — these are
    reviewed as part of migration authoring and may legitimately touch V2 or
    legacy tables by name.
  - Test files under `tests/` — tests may create throwaway tables with names
    like `A`, `B`, `TestNode` for isolated kuzu_db fixtures. These never reach
    production. Match by path prefix.

Canonical upgrade path (when you DO want to add a new canonical type):
  1. Open a PR that edits `schemas/ontology_v4.2.cypher` first, adding the new
     `CREATE NODE TABLE <Name>` stanza.
  2. In the same PR, add any migration / ingestion code that references it.
  3. This guard parses the updated canonical on each invocation, so the new
     type is accepted as long as the schema file edit lands first in the PR's
     working tree.

Install as pre-commit hook:
  $ ln -s ../../scripts/ontology-whitelist-guard.py .git/hooks/pre-commit

Install as CI check:
  $ python3 scripts/ontology-whitelist-guard.py $(git diff --name-only origin/main...HEAD)

Manual use:
  $ python3 scripts/ontology-whitelist-guard.py path/to/file.py [more files...]

Exit codes:
  0 — no violations (or no files scanned)
  1 — one or more violations found
  2 — configuration error (schema file missing, etc.)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_SCHEMA = REPO_ROOT / "schemas" / "ontology_v4.2.cypher"

# Path-prefix whitelist (relative to REPO_ROOT). Files under these prefixes
# are NOT scanned.
WHITELISTED_PREFIXES = (
    "schemas/",                # canonical schema itself
    "deploy/contabo/migrations/",  # migration staging area
    "deploy/local/migrations/",
    "deploy/gcp/migrations/",
    "tests/",                  # test fixtures
    "data/",                   # never scan data dumps
    ".venv/",
    "venv/",
    "node_modules/",
)

# Case-insensitive; captures the table name.
_CREATE_NODE_TABLE_RE = re.compile(
    r"CREATE\s+NODE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def parse_canonical_types(schema_path: Path) -> set[str]:
    """Extract node-type names from `schemas/ontology_v4.2.cypher`."""
    if not schema_path.exists():
        print(
            f"ERROR: canonical schema missing at {schema_path}",
            file=sys.stderr,
        )
        sys.exit(2)
    text = schema_path.read_text(encoding="utf-8")
    return {m.group(1) for m in _CREATE_NODE_TABLE_RE.finditer(text)}


def is_whitelisted(path: Path) -> bool:
    """True if the path sits under a whitelisted prefix."""
    try:
        rel = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        # Path is outside repo — leave it alone.
        return True
    rel_str = str(rel).replace("\\", "/") + "/"
    return any(rel_str.startswith(p) for p in WHITELISTED_PREFIXES)


def scan_file(path: Path, canonical: set[str]) -> list[tuple[int, str]]:
    """Return list of (lineno, table_name) violations found in `path`."""
    if not path.exists() or not path.is_file():
        return []
    violations: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"WARN: could not read {path}: {exc}", file=sys.stderr)
        return []
    for m in _CREATE_NODE_TABLE_RE.finditer(text):
        name = m.group(1)
        if name in canonical:
            continue
        # Compute 1-indexed line number from match start.
        lineno = text.count("\n", 0, m.start()) + 1
        violations.append((lineno, name))
    return violations


def files_from_git_staged() -> list[Path]:
    """Return staged files from `git diff --cached --name-only`."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    return [REPO_ROOT / ln.strip() for ln in out.splitlines() if ln.strip()]


def main(argv: list[str]) -> int:
    canonical = parse_canonical_types(CANONICAL_SCHEMA)
    if not canonical:
        print(
            f"ERROR: canonical schema {CANONICAL_SCHEMA} parsed 0 node types",
            file=sys.stderr,
        )
        return 2

    if argv:
        files = [Path(a) for a in argv]
    else:
        files = files_from_git_staged()

    files = [
        f
        for f in files
        # Only scan text-ish extensions. Skip binaries, json dumps, etc.
        if f.suffix in {".py", ".cypher", ".sql", ".sh", ".md"}
        and not is_whitelisted(f)
    ]

    if not files:
        return 0

    total_violations = 0
    for path in files:
        hits = scan_file(path, canonical)
        if not hits:
            continue
        for lineno, name in hits:
            rel = path.resolve()
            try:
                rel = rel.relative_to(REPO_ROOT)
            except ValueError:
                pass
            print(
                f"REJECTED {rel}:{lineno}: "
                f"CREATE NODE TABLE {name!r} — not in canonical "
                f"{CANONICAL_SCHEMA.relative_to(REPO_ROOT)}",
                file=sys.stderr,
            )
            total_violations += 1

    if total_violations:
        print(
            f"\nontology-whitelist-guard: {total_violations} violation(s). "
            f"To add a new canonical type, first edit "
            f"{CANONICAL_SCHEMA.relative_to(REPO_ROOT)} in the same PR, then "
            f"re-stage.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
