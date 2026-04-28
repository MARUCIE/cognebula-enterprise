#!/usr/bin/env python3
"""working_tree_triage.py — Sweep-8 / S18.30.

Bucket the project's working-tree drift into reviewable categories so the
"is this 138-file dirty state safe?" question becomes data-driven.

Buckets (priority-ordered):
  1. critical_code   — src/api/, scripts/, kg-api-server.py, schemas/, src/_lib/
  2. tests           — tests/
  3. docs            — doc/, *.md, README, HANDOFF.md
  4. configs         — configs/, *.toml, *.yaml, *.json (top-level)
  5. data_or_cache   — data/, outputs/, .wrangler/, .next/, node_modules/
  6. other           — anything not matched above

Output:
  - outputs/working-tree-triage.json (structured, for re-ingestion)
  - outputs/working-tree-triage.md  (human-readable summary)

Per bucket: total count, status breakdown (M/D/??), top-5 by churn
(`+lines + -lines`).

Why this exists (Hara + Taleb):
  138-file `git status` is information density 0. Without a structural
  triage, every session re-discovers drift differently — fragile. Scripted
  bucketing makes the discovery repeatable and the signal stable.

Failure modes prevented (Munger inversion):
  - Output overwhelms Maurice → top-5 cap per bucket
  - Cache files (.wrangler, .next, node_modules) flood signal → bucket
    them separately into `data_or_cache` so Maurice can ignore as a unit
  - Script breaks outside a git repo → graceful exit with explicit message
  - Stale manifest read by next session → JSON includes `run_utc` +
    `git_head_sha` so freshness is visible

Usage:
  python3 scripts/working_tree_triage.py [--out-dir outputs/]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1


def _run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return ""
    except FileNotFoundError:
        print("ERROR: git not found on PATH", file=sys.stderr)
        sys.exit(2)


def _is_git_repo() -> bool:
    return (REPO_ROOT / ".git").exists()


def _classify(path: str) -> str:
    """Return bucket name for a given relative path. Order matters —
    first match wins, so put more-specific patterns first."""
    p = path.lstrip("/")

    # Critical code (high-signal source)
    if (
        p.startswith("src/api/")
        or p.startswith("src/_lib/")
        or p.startswith("scripts/")
        or p == "kg-api-server.py"
        or p.startswith("schemas/")
        or p.startswith("src/kg/")
    ):
        return "critical_code"

    # Tests
    if p.startswith("tests/") or p.endswith("_test.py") or p.startswith("test_"):
        return "tests"

    # Docs (markdown + doc/ tree)
    if (
        p.startswith("doc/")
        or p.endswith(".md")
        or p in ("README.md", "HANDOFF.md", "CLAUDE.md", "AGENTS.md")
    ):
        return "docs"

    # Configs
    if (
        p.startswith("configs/")
        or p.startswith(".github/")
        or p.endswith((".toml", ".yaml", ".yml"))
        or p in ("docker-compose.yml", "Dockerfile", "pyproject.toml", "pytest.ini")
    ):
        return "configs"

    # Data / cache (low-signal, often noise)
    if (
        p.startswith("data/")
        or p.startswith("outputs/")
        or p.startswith(".wrangler/")
        or p.startswith(".next/")
        or p.startswith("node_modules/")
        or p.startswith(".pytest_cache/")
        or p.startswith("__pycache__/")
        or p.endswith((".lock", ".log", ".sqlite", ".sqlite-shm", ".sqlite-wal", ".pyc"))
    ):
        return "data_or_cache"

    return "other"


def _parse_status_line(line: str) -> tuple[str, str] | None:
    """Parse a single `git status --porcelain` line.
    Returns (status_code, path) or None for unparseable lines.

    Status codes (first 2 chars):
      ' M' / 'M ' = modified, ' D' / 'D ' = deleted, '??' = untracked,
      'A ' = added, 'R ' = renamed, etc.
    """
    if len(line) < 4:
        return None
    code = line[:2]
    rest = line[3:].strip()
    # For renames "R  old -> new", take the new path.
    if " -> " in rest:
        rest = rest.split(" -> ", 1)[1]
    rest = rest.strip().strip('"')
    return code, rest


def _gather_diff_stats() -> dict[str, tuple[int, int]]:
    """Run `git diff HEAD --numstat` to get per-file +/- line counts.
    Returns {path: (added, deleted)}.

    Untracked files are not in this dict — they have no committed
    counterpart to diff against.
    """
    out = _run_git(["diff", "HEAD", "--numstat"])
    stats: dict[str, tuple[int, int]] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added_str, deleted_str, path = parts
        # Binary files show "-\t-\tpath" — treat as 0 churn.
        try:
            added = int(added_str) if added_str != "-" else 0
            deleted = int(deleted_str) if deleted_str != "-" else 0
        except ValueError:
            continue
        stats[path] = (added, deleted)
    return stats


def build_triage() -> dict:
    if not _is_git_repo():
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "not a git repo",
            "buckets": {},
        }

    head_sha = _run_git(["rev-parse", "--short", "HEAD"]).strip()
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    status_out = _run_git(["status", "--porcelain"])
    diff_stats = _gather_diff_stats()

    buckets: dict[str, list[dict]] = defaultdict(list)
    status_counts: dict[str, int] = defaultdict(int)

    for line in status_out.splitlines():
        parsed = _parse_status_line(line)
        if not parsed:
            continue
        code, path = parsed
        added, deleted = diff_stats.get(path, (0, 0))
        churn = added + deleted
        bucket = _classify(path)
        buckets[bucket].append({
            "path": path,
            "status": code,
            "added": added,
            "deleted": deleted,
            "churn": churn,
        })
        status_counts[code] += 1

    bucket_summary: dict[str, dict] = {}
    for name, entries in buckets.items():
        entries.sort(key=lambda e: e["churn"], reverse=True)
        per_status: dict[str, int] = defaultdict(int)
        total_added = 0
        total_deleted = 0
        for e in entries:
            per_status[e["status"]] += 1
            total_added += e["added"]
            total_deleted += e["deleted"]
        bucket_summary[name] = {
            "count": len(entries),
            "status_breakdown": dict(per_status),
            "total_added": total_added,
            "total_deleted": total_deleted,
            "top_5_by_churn": entries[:5],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "run_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head_sha": head_sha,
        "git_branch": branch,
        "summary": {
            "total_dirty_entries": sum(status_counts.values()),
            "status_breakdown": dict(status_counts),
            "bucket_counts": {
                name: bucket_summary[name]["count"]
                for name in sorted(bucket_summary)
            },
        },
        "buckets": bucket_summary,
    }


_BUCKET_ORDER = [
    "critical_code",
    "tests",
    "docs",
    "configs",
    "data_or_cache",
    "other",
]


def render_markdown(triage: dict) -> str:
    if "error" in triage:
        return f"# Working Tree Triage\n\nError: {triage['error']}\n"

    md: list[str] = []
    md.append("# Working Tree Triage Manifest")
    md.append("")
    md.append(f"- **Run (UTC)**: `{triage['run_utc']}`")
    md.append(f"- **Branch**: `{triage['git_branch']}`")
    md.append(f"- **HEAD**: `{triage['git_head_sha']}`")
    md.append(f"- **Schema version**: {triage['schema_version']}")
    md.append("")

    s = triage["summary"]
    md.append("## Summary")
    md.append("")
    md.append(f"- Total dirty entries: **{s['total_dirty_entries']}**")
    md.append(f"- Status breakdown: `{s['status_breakdown']}`")
    md.append("")

    md.append("| Bucket | Count |")
    md.append("|---|---:|")
    for name in _BUCKET_ORDER:
        cnt = s["bucket_counts"].get(name, 0)
        md.append(f"| `{name}` | {cnt} |")
    md.append("")

    md.append("## Top-5 by churn per bucket")
    md.append("")
    for name in _BUCKET_ORDER:
        b = triage["buckets"].get(name)
        if not b:
            continue
        md.append(f"### `{name}` — {b['count']} files, +{b['total_added']} / -{b['total_deleted']}")
        md.append("")
        md.append("| Status | Path | + | - | Churn |")
        md.append("|---|---|---:|---:|---:|")
        for e in b["top_5_by_churn"]:
            md.append(
                f"| `{e['status']}` | `{e['path']}` | {e['added']} | {e['deleted']} | {e['churn']} |"
            )
        md.append("")

    md.append("---")
    md.append("")
    md.append("> Re-generate with: `python3 scripts/working_tree_triage.py`.")
    md.append("> JSON form at `outputs/working-tree-triage.json` for re-ingestion.")
    return "\n".join(md) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="outputs",
        help="Directory to write triage outputs (default: outputs/)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Don't print summary to stdout",
    )
    args = parser.parse_args(argv)

    out_dir = REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "working-tree-triage.json"
    md_path = out_dir / "working-tree-triage.md"

    triage = build_triage()
    json_path.write_text(
        json.dumps(triage, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(triage), encoding="utf-8")

    if not args.quiet:
        print(f"working-tree-triage: {triage['summary']['total_dirty_entries']} dirty entries")
        print(f"  json: {json_path.relative_to(REPO_ROOT)}")
        print(f"  md:   {md_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
