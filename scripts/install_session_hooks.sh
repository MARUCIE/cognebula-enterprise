#!/bin/bash
# install_session_hooks.sh — Sweep-9 / S18.31.
#
# Installs `scripts/git-hooks/post-commit-session-stamp.sh` as the repo's
# `.git/hooks/post-commit` so every commit on this clone gets stamped
# into `state/git/commit-log.jsonl` for parallel-write detection.
#
# Idempotent — running twice is safe; second run just re-confirms the
# symlink target.
#
# Why a symlink and not a copy: a symlink follows the source script, so
# editing the source updates behavior immediately without a re-install.
# (Note: if `git config core.hooksPath` is set, the symlink at .git/hooks
# is bypassed; we honor that by also reporting hooksPath state.)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: not in a git repo" >&2
    exit 1
}
SOURCE="$REPO_ROOT/scripts/git-hooks/post-commit-session-stamp.sh"
TARGET_DIR="$REPO_ROOT/.git/hooks"
TARGET="$TARGET_DIR/post-commit"

if [ ! -f "$SOURCE" ]; then
    echo "ERROR: source hook missing at $SOURCE" >&2
    exit 1
fi

# Ensure source is executable (a chmod -x slipped past code review would
# silently break the hook).
chmod +x "$SOURCE"

mkdir -p "$TARGET_DIR"

# If a different post-commit hook is already installed, refuse to clobber.
if [ -f "$TARGET" ] && [ ! -L "$TARGET" ]; then
    if ! grep -q "post-commit-session-stamp" "$TARGET" 2>/dev/null; then
        echo "WARN: $TARGET exists and is not our hook." >&2
        echo "      Move it aside and re-run, or chain manually:" >&2
        echo "        # in $TARGET, add: bash $SOURCE" >&2
        exit 1
    fi
fi

# Install symlink
ln -sf "$SOURCE" "$TARGET"
echo "OK: installed post-commit hook → $SOURCE"

# Warn if hooksPath is overriding .git/hooks
HP="$(git -C "$REPO_ROOT" config --get core.hooksPath 2>/dev/null || true)"
if [ -n "$HP" ]; then
    echo "WARN: core.hooksPath is set to '$HP' — .git/hooks/post-commit will" >&2
    echo "      be IGNORED. Either unset (git config --unset core.hooksPath)" >&2
    echo "      or symlink the hook into '$HP' instead." >&2
fi

echo "Stamps will accumulate at: $REPO_ROOT/state/git/commit-log.jsonl"
echo "Inspect with: python3 scripts/parallel_write_detector.py"
