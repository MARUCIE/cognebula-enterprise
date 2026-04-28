#!/usr/bin/env bash
#
# smoke_test_hegui_deploy.sh — verify hegui-site.pages.dev → tunnel → KG API chain.
#
# Why this exists
# ---------------
# After a deploy or a tunnel URL rotation, this script proves the full proxy
# chain is functional for every endpoint the frontend (web/src/app/lib/kg-api.ts)
# actually calls. Catches: forgotten POST body forwarding, broken CORS preflight,
# proxy path errors, and tunnel staleness — failure modes invisible from a single
# /stats GET.
#
# Usage
# -----
#   bash scripts/smoke_test_hegui_deploy.sh
#   BASE=https://5b934ed8.hegui-site.pages.dev bash scripts/smoke_test_hegui_deploy.sh   # test a specific preview
#   BASE=https://hegui.io bash scripts/smoke_test_hegui_deploy.sh                        # post-DNS-swap
#
# Exit code: 0 = all PASS, 1 = at least one FAIL.

set -u
BASE="${BASE:-https://hegui-site.pages.dev}"
CURL=/usr/bin/curl   # bypass RTK rewrite (it eats --resolve and similar flags)

PASS=0
FAIL=0
FAILED_ENDPOINTS=()

probe_get() {
  local label="$1" path="$2" expect_field="$3"
  local out
  out="$($CURL -sS --max-time 20 "${BASE}${path}" 2>&1 || true)"
  if printf '%s' "$out" | grep -qE "\"${expect_field}\""; then
    printf '  [PASS] GET %-50s expect=%s\n' "$path" "$expect_field"
    PASS=$((PASS+1))
  else
    printf '  [FAIL] GET %-50s expect=%s\n' "$path" "$expect_field"
    printf '         response head: %s\n' "$(printf '%s' "$out" | head -c 200)"
    FAIL=$((FAIL+1))
    FAILED_ENDPOINTS+=("GET $path")
  fi
}

probe_post() {
  local label="$1" path="$2" body="$3" expect_status="$4"
  local out status
  status="$($CURL -sS --max-time 30 -o /tmp/smoke.body -w '%{http_code}' \
    -X POST "${BASE}${path}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$body" 2>&1 || true)"
  if [[ "$status" == "$expect_status" || "$status" == "200" ]]; then
    printf '  [PASS] POST %-49s status=%s\n' "$path" "$status"
    PASS=$((PASS+1))
  else
    printf '  [FAIL] POST %-49s status=%s expect=%s\n' "$path" "$status" "$expect_status"
    printf '         response head: %s\n' "$(head -c 200 /tmp/smoke.body 2>/dev/null)"
    FAIL=$((FAIL+1))
    FAILED_ENDPOINTS+=("POST $path")
  fi
}

probe_options() {
  local path="$1"
  local out
  out="$($CURL -sS --max-time 10 -X OPTIONS \
    -H "Origin: ${BASE}" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -I "${BASE}${path}" 2>&1 || true)"
  if printf '%s' "$out" | grep -qiE "access-control-allow-(origin|methods)"; then
    printf '  [PASS] OPTIONS %-46s CORS headers present\n' "$path"
    PASS=$((PASS+1))
  else
    printf '  [FAIL] OPTIONS %-46s CORS headers missing\n' "$path"
    FAIL=$((FAIL+1))
    FAILED_ENDPOINTS+=("OPTIONS $path")
  fi
}

echo "smoke_test_hegui_deploy"
echo "  base: $BASE"
echo "  date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "Section 1 — frontend root reachability"
out="$($CURL -sS --max-time 10 -I "$BASE/" 2>&1 | head -1 || true)"
if printf '%s' "$out" | grep -qE "200|301|302"; then
  printf '  [PASS] root GET                                         status=%s\n' "$(printf '%s' "$out" | tr -d '\r' | awk '{print $2}')"
  PASS=$((PASS+1))
else
  printf '  [FAIL] root GET                                         response=%s\n' "$out"
  FAIL=$((FAIL+1))
fi
echo

echo "Section 2 — GET endpoints (proxy chain via Pages Function)"
probe_get "stats"                "/api/v1/stats"                                               "total_nodes"
probe_get "ontology-audit"       "/api/v1/ontology-audit"                                      "canonical_count|intersection|tables"
probe_get "quality"              "/api/v1/quality"                                             "score|gate|metrics"
probe_get "graph (with table)"   "/api/v1/graph?table=LegalClause&id_value=CL_e1a6f311bfecb352_art1&depth=1"  "node|nodes|edges|center"
probe_get "constellation"        "/api/v1/constellation?limit=20"                              "nodes|edges"
probe_get "constellation type"   "/api/v1/constellation/type?type=LegalClause&limit=10"        "nodes|edges"
probe_get "search"               "/api/v1/search?q=tax&limit=3"                                "results"
probe_get "nodes"                "/api/v1/nodes?type=LegalClause&limit=3"                      "results|count|total"
probe_get "hybrid-search"        "/api/v1/hybrid-search?q=vat&limit=3"                         "results|method|query"
probe_get "reasoning-chain"      "/api/v1/reasoning-chain?question=test&limit=3"               "chain|reasoning|results|nodes"
echo

echo "Section 3 — OPTIONS preflight (CORS for browser POST)"
probe_options "/api/v1/chat"
probe_options "/api/v1/inspect/clause"
echo

echo "Section 4 — POST endpoints (body forwarding + Content-Type)"
probe_post "chat"                "/api/v1/chat"                  '{"question":"smoke test","limit":3}'                              "200"
echo
echo "Section 5 — known deploy gaps (frontend calls these; backend may not have them)"
echo "  Failure here = contabo kg-api-server.py is missing the endpoint, NOT a chain break."
probe_post "inspect/clause"       "/api/v1/inspect/clause"        '{"section":"test","text":"smoke","clause_id":"smoke-001"}'        "200"
probe_post "inspect/clause/batch" "/api/v1/inspect/clause/batch"  '{"rows":[{"section":"test","text":"smoke","clause_id":"smoke-1"}]}' "200"
echo

TOTAL=$((PASS+FAIL))
echo "summary"
echo "  total:  $TOTAL"
echo "  PASS:   $PASS"
echo "  FAIL:   $FAIL"
if (( FAIL > 0 )); then
  echo "  failed endpoints:"
  for ep in "${FAILED_ENDPOINTS[@]}"; do echo "    - $ep"; done
  exit 1
fi
exit 0
