#!/usr/bin/env python3
"""Pre-commit / CI guard: reject `CREATE NODE TABLE <Name>` unless `<Name>` is canonical.

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

# scripts/ is not a Python package; add scripts/ to sys.path so we can import
# from the sibling `_lib/` shared library without making this file a package
# member. Sweep-4 / S18.18.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _lib.ontology_parser import (  # noqa: E402  (sys.path hack above is required)
    CREATE_NODE_TABLE_RE,
    parse_canonical_types,
)


REPO_ROOT = _SCRIPTS_DIR.parent
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

# Regex + parse_canonical_types are imported from _lib.ontology_parser
# (Sweep-4 / S18.18 + S18.21). The new pattern uses `(?!IF\b)` negative
# lookahead so the optional `IF NOT EXISTS` group cannot backtrack into
# capturing the literal keyword `IF` — the post-filter hack is gone.


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
    for m in CREATE_NODE_TABLE_RE.finditer(text):
        name = m.group(1)
        if name in canonical:
            continue
        # No `IF` post-filter needed anymore — the regex's negative lookahead
        # `(?!IF\b)` rejects the bad capture at match-time. See
        # `_lib/ontology_parser.py` docstring for the failure mode it prevents.
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


# Sweep-5 / S18.22 — diff-only scan helpers.
# Failure mode this prevents (Munger inversion): an unrelated edit to a file
# that ALREADY contains a pre-existing unauthorized table declaration (left
# behind by a historical commit) gets falsely rejected — training the team
# to whitelist that table to make commits go through. Whitelist creep.
# Diff-mode complains only about NEWLY ADDED `CREATE NODE TABLE` lines.

_DIFF_FILE_HEADER_RE = re.compile(r"^\+\+\+ b/(.+)$")
_DIFF_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _parse_unified_diff(diff_text: str) -> list[tuple[str, int, str]]:
    """Yield (relative_path, new_lineno, added_line_content) tuples for every
    `+` line in a unified diff (-U0 form). Skips removed (`-`) and context
    lines (which don't appear with `-U0` anyway). Path-prefix whitelist is
    applied separately by the caller, not here.
    """
    out: list[tuple[str, int, str]] = []
    current_path: str | None = None
    current_new_lineno = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            m = _DIFF_FILE_HEADER_RE.match(raw)
            current_path = m.group(1) if m else None
            in_hunk = False
            continue
        if raw.startswith("@@"):
            m = _DIFF_HUNK_HEADER_RE.match(raw)
            if m and current_path:
                current_new_lineno = int(m.group(1))
                in_hunk = True
            else:
                in_hunk = False
            continue
        if not in_hunk or current_path is None:
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            out.append((current_path, current_new_lineno, raw[1:]))
            current_new_lineno += 1
        # `-` lines do not advance new_lineno; `-U0` produces no context lines
    return out


def scan_staged_diff(canonical: set[str]) -> list[tuple[str, int, str]]:
    """Scan only ADDED lines in `git diff --cached -U0` for unauthorized
    `CREATE NODE TABLE` declarations. Returns [(rel_path, lineno, name)].

    Path-prefix whitelist is applied. Extension filter same as file-mode.
    """
    try:
        diff_out = subprocess.check_output(
            ["git", "diff", "--cached", "-U0"],
            cwd=REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []

    findings: list[tuple[str, int, str]] = []
    for rel_path, lineno, content in _parse_unified_diff(diff_out):
        # Extension + whitelist filter (same rules as file-mode).
        suffix = Path(rel_path).suffix
        if suffix not in {".py", ".cypher", ".sql", ".sh", ".md"}:
            continue
        if is_whitelisted(REPO_ROOT / rel_path):
            continue
        for m in CREATE_NODE_TABLE_RE.finditer(content):
            name = m.group(1)
            if name in canonical:
                continue
            findings.append((rel_path, lineno, name))
    return findings


def selftest() -> int:
    """§18.14 — verify the guard's three expected behaviors against fixture
    strings. Catches the failure mode where the guard silently no-ops
    (regex broken, canonical parse failing, etc.) and every commit "passes"
    while the hook is actually dead. Run via `--selftest` CLI flag and from
    `.github/workflows/ontology-gate.yml::whitelist-guard`.

    Cases:
      1. Empty input → exit 0
      2. Input with a rogue `<Name>` not in canonical → exit 1
      3. Input with a canonical type from ontology_v4.2.cypher → exit 0
      4. Input with `IF NOT EXISTS` + Python concat (regex-backtrack case) → exit 0
         (the `IF` keyword must be skipped, not captured as identifier)

    Failure of any case means the guard's invariants are broken and the
    hook should be considered offline until repaired.
    """
    import tempfile

    canonical = parse_canonical_types(CANONICAL_SCHEMA)
    if not canonical:
        print("SELFTEST FAIL: canonical schema parsed 0 node types", file=sys.stderr)
        return 2

    # Pick a real canonical type for case #3.
    a_canonical_type = sorted(canonical)[0]

    # Note: fixture strings below are built via concatenation so the
    # literals embedded in this script source do NOT themselves match the
    # guard's own regex — preventing the meta-rejection observed when
    # storing the fixtures inline.
    _CN = "CREATE" + " NODE" + " TABLE"  # built at runtime, not literal in source
    cases: list[tuple[str, str, int]] = [
        ("empty", "# nothing here\n", 0),
        ("rogue", f"{_CN} FakeNeverDeclaredXYZ (id STRING, PRIMARY KEY (id));\n", 1),
        ("canonical", f"{_CN} {a_canonical_type} (id STRING, PRIMARY KEY (id));\n", 0),
        ("if-not-exists-concat", f'sql = "{_CN} IF NOT EXISTS " + table_name + " (...)"\n', 0),
    ]

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ontology-guard-selftest-") as tmpdir:
        for name, content, expected_exit in cases:
            fixture = Path(tmpdir) / f"selftest-{name}.py"
            fixture.write_text(content, encoding="utf-8")
            hits = scan_file(fixture, canonical)
            actual_exit = 1 if hits else 0
            if actual_exit != expected_exit:
                failures.append(
                    f"  case={name}: expected exit={expected_exit}, "
                    f"got exit={actual_exit}, hits={hits}"
                )

    if failures:
        print("SELFTEST FAIL:", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1
    print(f"SELFTEST OK: {len(cases)} cases passed (canonical={len(canonical)} types)")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return selftest()

    # Sweep-5 / S18.22 — `--diff-mode` forces diff-only scan even with argv
    # present (useful for CI to opt in to PR-diff scanning). `--file-mode`
    # forces file scan even with no argv (useful for ad-hoc whole-repo
    # scans). Default: argv present → file-mode (legacy CI path);
    # argv empty → diff-mode (new pre-commit default that prevents
    # whitelist-creep from pre-existing rogue declarations).
    force_diff = False
    force_file = False
    if argv and argv[0] == "--diff-mode":
        force_diff = True
        argv = argv[1:]
    elif argv and argv[0] == "--file-mode":
        force_file = True
        argv = argv[1:]

    canonical = parse_canonical_types(CANONICAL_SCHEMA)
    if not canonical:
        print(
            f"ERROR: canonical schema {CANONICAL_SCHEMA} parsed 0 node types",
            file=sys.stderr,
        )
        return 2

    use_diff_mode = force_diff or (not argv and not force_file)
    if use_diff_mode:
        diff_findings = scan_staged_diff(canonical)
        if not diff_findings:
            return 0
        for rel_path, lineno, name in diff_findings:
            print(
                f"REJECTED {rel_path}:{lineno}: "
                f"+CREATE NODE TABLE {name!r} (newly added) — not in canonical "
                f"{CANONICAL_SCHEMA.relative_to(REPO_ROOT)}",
                file=sys.stderr,
            )
        print(
            f"\nontology-whitelist-guard (diff-mode): {len(diff_findings)} "
            f"newly-added violation(s). To add a new canonical type, first "
            f"edit {CANONICAL_SCHEMA.relative_to(REPO_ROOT)} in the same "
            f"PR, then re-stage. Pass `--file-mode` to scan whole files.",
            file=sys.stderr,
        )
        return 1

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
