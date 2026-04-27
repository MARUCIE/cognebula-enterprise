"""Ingestion manifest — closes the corpus → KG observability black hole.

Every seed/import script must call `record_ingestion()` before exit.
Each call appends ONE line to `data/ingestion-manifest.jsonl`:

    {
      "ts": "2026-04-27T14:23:11Z",
      "source_file": "src/seed_accounting_subject_full.py",
      "rows_written": {"AccountingSubject": 1483},
      "duration_s": 12.4,
      "dry_run": false,
      "git_sha": "<short-sha-or-null>",
      "operator": "<USER>",
      "note": "free-form annotation"
    }

The CI gate reads this manifest:
- mtime < 48h source files MUST show rows_written above threshold
- absence of recent manifest entries → gate FAIL (corpus inflow stalled)

Reference: `outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md`
§5 Week-1 item 10 (Meadows leverage point #8 — gaming-resistant feedback loop).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = _REPO_ROOT / "data" / "ingestion-manifest.jsonl"


def _git_short_sha() -> str | None:
    """Return current HEAD short-SHA or None if not a git repo / git absent."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        pass
    return None


def record_ingestion(
    source_file: str | Path,
    rows_written: dict[str, int],
    duration_s: float,
    *,
    dry_run: bool = False,
    note: str = "",
    manifest_path: Path | None = None,
) -> dict:
    """Append one ingestion record to the manifest. Returns the recorded dict.

    Args:
        source_file: relative or absolute path to the seed/import script.
        rows_written: {table_name: row_count_added} (use 0 for tables not touched).
        duration_s: wall-clock seconds for the ingest run.
        dry_run: if True, the run made no DB writes; entry still recorded with flag.
        note: free-form annotation.
        manifest_path: override (tests). Defaults to repo `data/ingestion-manifest.jsonl`.

    Side effect: appends one JSON line. Creates the file (and parent dir) if absent.
    """
    path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    src = Path(source_file)
    try:
        rel_src = str(src.resolve().relative_to(_REPO_ROOT))
    except ValueError:
        rel_src = str(src)
    record = {
        "ts": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": rel_src,
        "rows_written": dict(rows_written),
        "rows_total": int(sum(rows_written.values())),
        "duration_s": round(float(duration_s), 3),
        "dry_run": bool(dry_run),
        "git_sha": _git_short_sha(),
        "operator": os.environ.get("USER", "unknown"),
        "note": note,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_manifest(
    *,
    since: _dt.datetime | None = None,
    manifest_path: Path | None = None,
) -> list[dict]:
    """Read all manifest entries, optionally filtering by `ts >= since`."""
    path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since:
                ts = _dt.datetime.strptime(rec["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=_dt.UTC
                )
                if ts < since:
                    continue
            out.append(rec)
    return out


def latest_per_source(
    manifest_path: Path | None = None,
) -> dict[str, dict]:
    """Return {source_file: most-recent-record} across all entries."""
    out: dict[str, dict] = {}
    for rec in read_manifest(manifest_path=manifest_path):
        src = rec["source_file"]
        if src not in out or rec["ts"] > out[src]["ts"]:
            out[src] = rec
    return out


__all__ = [
    "MANIFEST_PATH",
    "record_ingestion",
    "read_manifest",
    "latest_per_source",
]
