#!/usr/bin/env bash
#
# deploy/contabo/post-deploy.sh — Sprint G4 / S18.17
#
# Run this after `systemctl restart kg-api` (or after a Docker compose up).
# It waits for the backend to come up healthy, then runs runtime_audit.sh
# against localhost to verify the deploy actually shipped a working router.
#
# Closes the gap that motivated Sprint G4: "compiles fine but deploys
# wrong module" used to slip through. Now every deploy is followed by a
# three-witness check (OPTIONS catalog + live sample + static comparison).
#
# Usage:
#   ./deploy/contabo/post-deploy.sh                     # default localhost:8000
#   ./deploy/contabo/post-deploy.sh http://127.0.0.1:8001 \
#       --static-report outputs/api-drift-report.json
#
# Wire into your deploy runbook OR add to systemd unit:
#   [Service]
#   ExecStartPost=/opt/cognebula/deploy/contabo/post-deploy.sh
#
# Exit codes propagated from runtime_audit.sh; treat any non-zero as a
# deploy that should be rolled back.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_AUDIT="$REPO_ROOT/scripts/runtime_audit.sh"
BASE_URL="${1:-http://127.0.0.1:8000}"
shift || true

if [ ! -x "$RUNTIME_AUDIT" ]; then
    echo "ERROR: $RUNTIME_AUDIT missing or not executable" >&2
    echo "       Run: chmod +x $RUNTIME_AUDIT" >&2
    exit 64
fi

# ── Health wait loop ─────────────────────────────────────────────────
# Backend may take a few seconds to bind after systemctl restart. Poll
# /health up to 30s before giving up.
echo "post-deploy: waiting for $BASE_URL/health to come up (max 30s)..."
deadline=$(( $(date +%s) + 30 ))
healthy=""
while [ "$(date +%s)" -lt "$deadline" ]; do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
        healthy="yes"
        break
    fi
    sleep 2
done

if [ -z "$healthy" ]; then
    echo "FAIL: $BASE_URL/health did not return 2xx within 30s" >&2
    echo "      Backend likely didn't bind. Check: systemctl status kg-api" >&2
    exit 1
fi

echo "post-deploy: backend is healthy, running runtime_audit"
echo ""

# ── Three-witness audit ──────────────────────────────────────────────
# Pass through any extra args (e.g. --static-report ...) to runtime_audit.
"$RUNTIME_AUDIT" "$BASE_URL" "$@"
audit_rc=$?

if [ $audit_rc -ne 0 ]; then
    echo "" >&2
    echo "FAIL: post-deploy audit returned exit $audit_rc" >&2
    echo "      Roll back this deploy or investigate before serving traffic." >&2
    exit "$audit_rc"
fi

echo ""
echo "post-deploy: OK"
exit 0
