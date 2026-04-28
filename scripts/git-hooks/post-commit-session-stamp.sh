#!/bin/bash
# post-commit-session-stamp.sh — Sweep-9 / S18.31.
#
# Records each commit + its parent + a session id into
# `state/git/commit-log.jsonl` so `parallel_write_detector.py` can flag
# the case where two sessions interleave commits based on stale HEADs.
#
# Installed as `.git/hooks/post-commit` via `scripts/install_session_hooks.sh`.
#
# Failure mode this prevents: Session A starts at HEAD=X, Session B starts
# at HEAD=X. B commits Y. A then commits Z without rebasing → Z's parent
# is X, not Y — parallel-write hazard. Detector reads the jsonl post-hoc
# and flags rows where `parent ≠ previous row's sha`.
#
# Hook failures must NOT break commit. Wrap entire body in `|| true`.

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_ROOT" ] && exit 0

LOG_DIR="$REPO_ROOT/state/git"
LOG_FILE="$LOG_DIR/commit-log.jsonl"
mkdir -p "$LOG_DIR" 2>/dev/null

SHA=$(git rev-parse --short HEAD 2>/dev/null)
PARENT=$(git rev-parse --short HEAD~1 2>/dev/null)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION_ID="${SESSION_ID:-pid-$$}"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Single-line JSON via printf (atomic O_APPEND write).
printf '{"sha":"%s","parent":"%s","ts":"%s","session_id":"%s","branch":"%s"}\n' \
    "$SHA" "$PARENT" "$TS" "$SESSION_ID" "$BRANCH" \
    >> "$LOG_FILE" 2>/dev/null

exit 0
