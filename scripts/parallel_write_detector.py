#!/usr/bin/env python3
"""parallel_write_detector.py — Sweep-9 / S18.31.

Scans `state/git/commit-log.jsonl` (populated by the post-commit
session-stamp hook) and flags rows where `parent ≠ previous row's sha`
— that is the parallel-write signal.

Background: when two sessions A and B both start at HEAD=X, B commits
Y, and A commits Z without rebasing, the jsonl looks like:

  {sha: Y, parent: X, session_id: B, ts: t1}
  {sha: Z, parent: X, session_id: A, ts: t2}    <-- parent ≠ Y → flagged

False positives this script handles:
  - First-ever commit (parent = empty, no previous row): NOT flagged
  - Force-push detected via `git reflog` lookup: distinguished from
    parallel-write by reporting `kind=force_push` instead of
    `kind=parallel_write`. Note: graceful — if reflog is unavailable
    we fall back to flagging as parallel_write (safer to over-report).

Usage:
  python3 scripts/parallel_write_detector.py
  python3 scripts/parallel_write_detector.py --json    # machine output
  python3 scripts/parallel_write_detector.py --window-days 30
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = REPO_ROOT / "state" / "git" / "commit-log.jsonl"


def _read_log(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    rows: list[dict] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            # Tolerate malformed lines — better partial than nothing
            continue
    return rows


def _is_force_push(sha: str, repo_root: Path) -> bool:
    """Best-effort: check `git reflog show HEAD` for a force-update on `sha`.
    Reflog format includes `forced-update` markers for non-fast-forward
    moves. Returns False if reflog can't be read."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "reflog", "show", "HEAD", "--no-color"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    for ln in out.splitlines():
        if sha in ln and ("forced-update" in ln or "reset:" in ln):
            return True
    return False


def detect_parallel_writes(rows: list[dict]) -> list[dict]:
    """Return list of flagged events with kind ∈ {parallel_write, force_push}."""
    findings: list[dict] = []
    prev_sha: str | None = None
    for i, row in enumerate(rows):
        if prev_sha is None:
            prev_sha = row.get("sha")
            continue
        parent = row.get("parent", "")
        # Empty parent means first-ever commit; skip
        if not parent:
            prev_sha = row.get("sha")
            continue
        # Force-push: lossy reset has no parent linkage to previous sha
        if parent != prev_sha:
            kind = "force_push" if _is_force_push(row["sha"], REPO_ROOT) else "parallel_write"
            findings.append({
                "row_index": i,
                "kind": kind,
                "sha": row.get("sha"),
                "parent": parent,
                "expected_parent": prev_sha,
                "session_id": row.get("session_id"),
                "ts": row.get("ts"),
                "branch": row.get("branch"),
            })
        prev_sha = row.get("sha")
    return findings


def filter_window(rows: list[dict], window_days: int) -> list[dict]:
    """Keep only rows from the last `window_days`."""
    if window_days <= 0:
        return rows
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=window_days)
    out: list[dict] = []
    for r in rows:
        try:
            ts = _dt.datetime.strptime(r.get("ts", ""), "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=_dt.timezone.utc
            )
        except (ValueError, TypeError):
            # Keep rows with malformed timestamps to avoid silent drops
            out.append(r)
            continue
        if ts >= cutoff:
            out.append(r)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--window-days", type=int, default=90)
    parser.add_argument("--json", action="store_true", help="Output machine JSON")
    args = parser.parse_args(argv)

    log_path = Path(args.log)
    rows = _read_log(log_path)
    rows = filter_window(rows, args.window_days)
    findings = detect_parallel_writes(rows)

    report = {
        "schema_version": 1,
        "log_path": str(log_path),
        "window_days": args.window_days,
        "rows_scanned": len(rows),
        "parallel_writes": [f for f in findings if f["kind"] == "parallel_write"],
        "force_pushes": [f for f in findings if f["kind"] == "force_push"],
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        pw = len(report["parallel_writes"])
        fp = len(report["force_pushes"])
        print(f"parallel_write_detector: scanned {len(rows)} rows in {args.window_days}-day window")
        print(f"  parallel_writes: {pw}")
        print(f"  force_pushes:    {fp}")
        for f in report["parallel_writes"]:
            print(
                f"  PARALLEL_WRITE @ row {f['row_index']}: "
                f"sha={f['sha']} parent={f['parent']} "
                f"expected_parent={f['expected_parent']} session={f['session_id']}"
            )
    # Non-zero exit when parallel-writes detected — for CI gating later
    return 1 if report["parallel_writes"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
