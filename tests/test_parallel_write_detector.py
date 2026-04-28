"""Tests for `scripts/parallel_write_detector.py` — Sweep-9 / S18.31.

Locks the detection logic against three scenarios:

  - normal_sequence: every row's `parent` matches the previous row's `sha`
    → 0 findings
  - parallel_write: a row's `parent` doesn't match the previous row's `sha`
    AND reflog says it was NOT a force-push → flagged as `parallel_write`
  - force_push: same divergence pattern, but reflog reports `forced-update`
    on the sha → flagged as `force_push` (distinguished, not silenced)

Plus parser robustness: malformed jsonl rows tolerated; window filtering;
missing log file returns empty.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import parallel_write_detector as pwd  # noqa: E402


def _row(sha: str, parent: str, ts: str = "2026-04-28T00:00:00Z",
         session: str = "test", branch: str = "main") -> dict:
    return {"sha": sha, "parent": parent, "ts": ts,
            "session_id": session, "branch": branch}


def test_empty_log_returns_no_findings(tmp_path: Path) -> None:
    log = tmp_path / "commit-log.jsonl"
    log.write_text("", encoding="utf-8")
    rows = pwd._read_log(log)
    assert pwd.detect_parallel_writes(rows) == []


def test_missing_log_returns_empty_list(tmp_path: Path) -> None:
    rows = pwd._read_log(tmp_path / "does-not-exist.jsonl")
    assert rows == []


def test_normal_sequence_no_findings() -> None:
    """Each commit's parent matches the previous sha — no parallel writes."""
    rows = [
        _row("a1", ""),     # first commit, no parent
        _row("a2", "a1"),
        _row("a3", "a2"),
        _row("a4", "a3"),
    ]
    findings = pwd.detect_parallel_writes(rows)
    assert findings == []


def test_parallel_write_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Session A and B both branch from a1. B commits b1, A commits a2 from a1
    without rebasing. The jsonl shows a2's parent=a1 but previous row was b1."""
    rows = [
        _row("a1", "", session="A"),
        _row("b1", "a1", session="B"),
        _row("a2", "a1", session="A"),  # parent mismatch
    ]
    # Force "not force_push" — reflog returns nothing
    monkeypatch.setattr(pwd, "_is_force_push", lambda sha, repo: False)
    findings = pwd.detect_parallel_writes(rows)
    assert len(findings) == 1
    assert findings[0]["kind"] == "parallel_write"
    assert findings[0]["sha"] == "a2"
    assert findings[0]["parent"] == "a1"
    assert findings[0]["expected_parent"] == "b1"
    assert findings[0]["session_id"] == "A"


def test_force_push_distinguished(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same divergence, but reflog says it was a force-push — kind should
    be `force_push` not `parallel_write`."""
    rows = [
        _row("a1", ""),
        _row("a2", "a1"),
        _row("a3_new", "a1"),  # divergence (force-push reset to a1 then commit a3)
    ]
    monkeypatch.setattr(pwd, "_is_force_push", lambda sha, repo: sha == "a3_new")
    findings = pwd.detect_parallel_writes(rows)
    assert len(findings) == 1
    assert findings[0]["kind"] == "force_push"


def test_malformed_jsonl_tolerated(tmp_path: Path) -> None:
    """A bad line in the middle must NOT abort the scan."""
    log = tmp_path / "commit-log.jsonl"
    log.write_text(
        json.dumps({"sha": "a1", "parent": "", "ts": "2026-04-28T00:00:00Z"}) + "\n"
        "not valid json {{ broken\n"
        + json.dumps({"sha": "a2", "parent": "a1", "ts": "2026-04-28T00:00:01Z"}) + "\n",
        encoding="utf-8",
    )
    rows = pwd._read_log(log)
    assert len(rows) == 2  # the broken line is skipped
    assert rows[0]["sha"] == "a1"
    assert rows[1]["sha"] == "a2"


def test_window_filter_drops_old_rows() -> None:
    rows = [
        _row("a1", "", ts="2020-01-01T00:00:00Z"),     # old
        _row("a2", "a1", ts="2026-04-28T00:00:00Z"),   # recent
    ]
    kept = pwd.filter_window(rows, window_days=90)
    assert len(kept) == 1
    assert kept[0]["sha"] == "a2"


def test_window_zero_disables_filter() -> None:
    rows = [
        _row("a1", "", ts="2020-01-01T00:00:00Z"),
        _row("a2", "a1", ts="2026-04-28T00:00:00Z"),
    ]
    kept = pwd.filter_window(rows, window_days=0)
    assert len(kept) == 2


def test_window_filter_keeps_malformed_ts() -> None:
    """Rows with unparseable timestamps must be kept (silent drop is worse
    than a noisy keep — preserves audit completeness)."""
    rows = [
        _row("a1", "", ts="not-a-timestamp"),
    ]
    kept = pwd.filter_window(rows, window_days=90)
    assert len(kept) == 1


def test_first_commit_no_parent_not_flagged() -> None:
    """First-ever commit has empty parent — must NOT be flagged just
    because `prev_sha` is None."""
    rows = [
        _row("a1", ""),  # first commit
    ]
    assert pwd.detect_parallel_writes(rows) == []


def test_subsequent_empty_parent_not_flagged() -> None:
    """If a row has empty parent (corrupt or root commit), the scanner
    should advance prev_sha and not flag."""
    rows = [
        _row("a1", ""),
        _row("a2", "a1"),
        _row("a3", ""),  # corrupted parent record — skip flagging
        _row("a4", "a3"),
    ]
    findings = pwd.detect_parallel_writes(rows)
    assert findings == []


def test_install_hook_script_executable() -> None:
    """The install script + hook source must be executable so users
    don't have to chmod +x manually."""
    install = REPO_ROOT / "scripts" / "install_session_hooks.sh"
    hook = REPO_ROOT / "scripts" / "git-hooks" / "post-commit-session-stamp.sh"
    assert install.exists() and (install.stat().st_mode & 0o111), (
        "install script not executable"
    )
    assert hook.exists() and (hook.stat().st_mode & 0o111), (
        "post-commit hook source not executable"
    )
