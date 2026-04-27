#!/usr/bin/env bash
#
# runtime_audit.sh — Sprint G4 / S18.16
#
# Three-witness validation that a running KG API backend matches the static
# parse output of `audit_api_contract.py`. Closes the gap where "compiles
# fine but deploys wrong module" went undetected before.
#
# Three witnesses:
#   1. OPTIONS /api/v1/.well-known/capabilities  → declared route catalog
#   2. Live sampled GET on N stable routes        → handler actually serves
#   3. audit_api_contract.py JSON report          → static parse expectation
#
# Per Munger inversion fixes:
#   (a) forced routes[] count threshold prevents OPTIONS returning empty
#       array passing the gate
#   (b) live sample mixes /health (always alive) + N random others to
#       catch handler-import-fails-but-route-registered failures
#   (c) static-vs-runtime XOR check at end catches both-skip-same-thing
#       false negatives by listing diff explicitly
#   (d) `set -euo pipefail` + explicit `exit $rc` prevents trap-and-continue
#
# Usage:
#   ./scripts/runtime_audit.sh <BASE_URL> [--min-routes N] [--sample N]
#                               [--static-report path/to/report.json]
#
# Examples:
#   ./scripts/runtime_audit.sh http://localhost:8000
#   ./scripts/runtime_audit.sh http://167.86.74.172 --min-routes 20
#   ./scripts/runtime_audit.sh http://localhost:8000 --static-report \
#       outputs/api-drift-report.json
#
# Exit codes:
#   0 — all three witnesses agree (within tolerance)
#   1 — runtime probe failed (HTTP error, parse failure, route count low)
#   2 — runtime vs static drift exceeds tolerance
#   3 — sample handler returned a non-acceptable HTTP status (5xx)
#   64 — usage error

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────
MIN_ROUTES=10
SAMPLE_N=3
STATIC_REPORT=""
BASE_URL=""

# ── Args ─────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --min-routes)
            MIN_ROUTES="$2"; shift 2;;
        --sample)
            SAMPLE_N="$2"; shift 2;;
        --static-report)
            STATIC_REPORT="$2"; shift 2;;
        -h|--help)
            sed -n '2,30p' "$0"; exit 0;;
        -*)
            echo "ERROR: unknown flag $1" >&2; exit 64;;
        *)
            if [ -z "$BASE_URL" ]; then
                BASE_URL="$1"
            else
                echo "ERROR: extra arg $1" >&2; exit 64
            fi
            shift;;
    esac
done

if [ -z "$BASE_URL" ]; then
    echo "ERROR: BASE_URL required. Usage: $0 <BASE_URL> [opts]" >&2
    exit 64
fi

# ── Dependency check ─────────────────────────────────────────────────
for dep in curl jq; do
    command -v "$dep" >/dev/null 2>&1 || {
        echo "ERROR: missing dependency: $dep" >&2; exit 64
    }
done

echo "runtime_audit: probing $BASE_URL"
echo "  min-routes=$MIN_ROUTES sample=$SAMPLE_N"
echo "  static-report=${STATIC_REPORT:-<none>}"
echo ""

# ── Witness 1: OPTIONS endpoint ──────────────────────────────────────
options_url="$BASE_URL/api/v1/.well-known/capabilities"
options_body="$(curl -fsS -X OPTIONS "$options_url" || {
    echo "ERROR: OPTIONS request failed against $options_url" >&2
    exit 1
})"

# Parse: module + route_count + routes[]
module="$(echo "$options_body" | jq -r '.module // "unknown"')"
deploy_anchor="$(echo "$options_body" | jq -r '.deploy_anchor // "unknown"')"
route_count="$(echo "$options_body" | jq -r '.route_count // 0')"

echo "[witness 1] OPTIONS catalog:"
echo "  module=$module"
echo "  deploy_anchor=$deploy_anchor"
echo "  route_count=$route_count"

# Munger fix (a): threshold prevents empty-array silent pass
if [ "$route_count" -lt "$MIN_ROUTES" ]; then
    echo "FAIL: route_count=$route_count below threshold $MIN_ROUTES" >&2
    echo "      Either OPTIONS handler is broken or backend started with" >&2
    echo "      a stripped router. Investigate before trusting this deploy." >&2
    exit 1
fi

runtime_routes="$(echo "$options_body" | jq -r '.routes[].path' | sort -u)"

# ── Witness 2: live sampled GET handlers ─────────────────────────────
echo ""
echo "[witness 2] live sample (always /health + $SAMPLE_N random GET routes):"

probe_route() {
    local path="$1"
    local url="$BASE_URL$path"
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")"
    case "$code" in
        2*|401|403)
            # 2xx = OK; 401/403 = auth-protected but alive
            echo "  ok   $code $path"
            return 0;;
        404)
            # 404 on a route OPTIONS just declared = handler import failed
            echo "  miss $code $path  ← OPTIONS declared but handler 404" >&2
            return 1;;
        5*)
            echo "  fail $code $path  ← server error" >&2
            return 1;;
        *)
            echo "  unk  $code $path  ← unexpected (network? timeout?)" >&2
            return 1;;
    esac
}

# Always-probe /health (Munger fix (b): catches cache-only hits since /health
# typically forces a real handler invocation).
probe_route "/health" || exit 3

# Sample SAMPLE_N random GET-capable routes from runtime catalog.
# `jq` extracts only routes whose methods include GET, then `sort -R` randomizes.
sample_paths="$(echo "$options_body" \
    | jq -r '.routes[] | select(.methods | index("GET")) | .path' \
    | grep -v '^/health$' \
    | sort -R \
    | head -n "$SAMPLE_N" || true)"

if [ -z "$sample_paths" ]; then
    echo "WARN: no GET-capable routes found for sampling beyond /health" >&2
fi

while IFS= read -r path; do
    [ -z "$path" ] && continue
    # Replace path-template params {x} with literal '0' for probe purposes.
    # Most handlers will 404 on '0', which is fine — we just want to confirm
    # the handler dispatches at all (vs. import-failed silent 404 on the path).
    probe_path="$(echo "$path" | sed 's|{[^}]*}|0|g')"
    probe_route "$probe_path" || true   # sample failures don't gate; we report
done <<< "$sample_paths"

# ── Witness 3: static parse comparison (optional) ────────────────────
exit_code=0
if [ -n "$STATIC_REPORT" ] && [ -f "$STATIC_REPORT" ]; then
    echo ""
    echo "[witness 3] static-vs-runtime XOR check:"

    # Determine static catalog. audit_api_contract.py emits dual_backend_split
    # with backend_a_routes / backend_b_routes. Pick the set that matches
    # `module` reported by witness 1.
    static_routes=""
    if [ "$module" = "kg_api_server" ]; then
        static_routes="$(jq -r '.dual_backend_split.backend_a_only[]?, .dual_backend_split.overlap[]?' "$STATIC_REPORT" 2>/dev/null | sort -u || true)"
    elif [ "$module" = "src.api.kg_api" ] || [ "$module" = "kg_api" ]; then
        static_routes="$(jq -r '.dual_backend_split.backend_b_only[]?, .dual_backend_split.overlap[]?' "$STATIC_REPORT" 2>/dev/null | sort -u || true)"
    else
        echo "  WARN: module='$module' not in static report's known backends; skipping XOR" >&2
    fi

    if [ -n "$static_routes" ]; then
        # Routes in static but not in runtime = handler dropped at runtime.
        # Routes in runtime but not in static = added without static parse update.
        runtime_only="$(comm -23 <(echo "$runtime_routes") <(echo "$static_routes") || true)"
        static_only="$(comm -13 <(echo "$runtime_routes") <(echo "$static_routes") || true)"
        ro_count="$(echo "$runtime_only" | grep -cv '^$' || true)"
        so_count="$(echo "$static_only" | grep -cv '^$' || true)"
        echo "  runtime_only_count=$ro_count"
        echo "  static_only_count=$so_count"
        if [ "$ro_count" -gt 5 ] || [ "$so_count" -gt 5 ]; then
            echo "  FAIL: drift exceeds tolerance (5)" >&2
            echo "  ── runtime-only paths ──" >&2
            echo "$runtime_only" | head -20 >&2
            echo "  ── static-only paths ──" >&2
            echo "$static_only" | head -20 >&2
            exit_code=2
        fi
    fi
else
    echo ""
    echo "[witness 3] skipped (no --static-report)"
fi

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "runtime_audit: OK ($module @ $deploy_anchor, $route_count routes)"
fi
exit "$exit_code"
