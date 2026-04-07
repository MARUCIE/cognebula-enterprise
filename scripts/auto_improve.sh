#!/bin/bash
# CogNebula Auto-Improve — Push forward on pending items
#
# Runs after progress_patrol.sh, does incremental work:
#   1. Incremental embedding for new nodes
#   2. FAQ content fill (if quota remaining)
#   3. Edge enrichment
#   4. Deep crawl (if M3 didn't run today)
#
# Safe: only runs if API is up, stops briefly for DB writes, always restarts
set -uo pipefail

cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -a; source .env; set +a; fi

VENV="/home/kg/kg-env/bin/python3"
API="http://localhost:8400"
LOG="data/logs/auto-improve-$(date -u +%Y%m%d-%H%M).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== Auto-Improve $(date -u) ==="

# Time guard: skip heavy work near core pipeline windows
HOUR=$(date -u +%-H)
HEAVY_OK=true
# M3 runs 02:00-07:00, but auto_improve at 00:30 can run into M3 window
# M2 runs 14:00-15:00, auto_improve at 12:30 can run into M2 window
if [[ $HOUR -ge 0 && $HOUR -le 7 ]]; then
    HEAVY_OK=false
    echo "  Time guard: 00-07 UTC (M3 window) — skip API-stop operations"
fi
if [[ $HOUR -ge 12 && $HOUR -le 15 ]]; then
    HEAVY_OK=false
    echo "  Time guard: 12-15 UTC (M2 window) — skip API-stop operations"
fi

# Pre-check: no competing pipelines running
if pgrep -f "m2_pipeline.sh|m3_orchestrator.sh" > /dev/null 2>&1; then
    echo "M2 or M3 pipeline running — skip to avoid KuzuDB lock conflict"
    exit 0
fi

# Pre-check: API must be up
if ! curl -sf "$API/api/v1/health" > /dev/null 2>&1; then
    echo "API is down — skipping (M3 or M2 may be running)"
    exit 0
fi

# ── 1. Embedding Status (read-only check, no rebuild) ────────────────
echo "[1/4] Embedding status..."
HEALTH=$(curl -sf "$API/api/v1/health" 2>/dev/null)
if [[ -n "$HEALTH" ]]; then
    VECTORS=$(echo "$HEALTH" | python3 -c "import json,sys; print(json.load(sys.stdin).get('lancedb_rows',0))" 2>/dev/null || echo 0)
    STATS=$(curl -sf "$API/api/v1/stats" 2>/dev/null)
    NODES=$(echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total_nodes',0))" 2>/dev/null || echo 0)
    GAP=$((NODES - VECTORS))
    echo "  Vectors: $VECTORS / Nodes: $NODES (gap: $GAP)"
    if [[ $GAP -gt 5000 ]]; then
        echo "  NOTE: ${GAP} nodes not in vector index (rebuild needed when gap > 5000)"
    fi
else
    echo "  API health check failed — skip"
fi

# ── 2. FAQ Content Fill (daily quota: 2000) ──────────────────────────
echo "[2/4] FAQ Content Fill..."
# Check if M3 already did FAQ fill today (Step 2b)
M3_LOG=$(ls -t data/logs/m3-orchestrator-$(date -u +%Y%m%d)*.log 2>/dev/null | head -1)
FAQ_DONE=false
if [[ -n "$M3_LOG" ]] && grep -q "FAQ Content Fill" "$M3_LOG" 2>/dev/null; then
    FAQ_DONE=true
fi

if ! $FAQ_DONE && $HEAVY_OK; then
    echo "  M3 didn't run FAQ fill today — running standalone batch..."
    sudo systemctl stop kg-api || true
    sleep 2
    timeout 3600 $VENV scripts/fill_faq_content.py --max 1000 2>&1 | tail -5
    sudo systemctl start kg-api
    sleep 3
    echo "  FAQ fill batch done, API restarted"
elif ! $HEAVY_OK; then
    echo "  Skipped (time guard — near core pipeline window)"
else
    echo "  M3 already ran FAQ fill today — skip"
fi

# ── 3. Edge Enrichment ───────────────────────────────────────────────
echo "[3/4] Edge Enrichment..."
if $HEAVY_OK && curl -sf "$API/api/v1/health" > /dev/null 2>&1; then
    sudo systemctl stop kg-api || true
    sleep 2
    timeout 120 $VENV scripts/enrich_edges_batch.py 2>&1 | tail -5
    sudo systemctl start kg-api
    sleep 3
    echo "  Edge enrichment done, API restarted"
elif ! $HEAVY_OK; then
    echo "  Skipped (time guard)"
else
    echo "  API not available — skip"
fi

# ── 4. Deep Crawl (if M3 didn't crawl today) ─────────────────────────
echo "[4/4] Deep Crawl Check..."
RAW_DIR="data/raw/$(date -u +%Y-%m-%d)"
DEEP_FILES=$(find "$RAW_DIR" -name "12366*" -o -name "chinaacc*" -o -name "baike*" -o -name "tax_cases*" 2>/dev/null | wc -l)
if [[ $DEEP_FILES -eq 0 ]]; then
    echo "  No deep crawl data today — running deep_crawl.sh..."
    timeout 3600 bash scripts/deep_crawl.sh 2>&1 | tail -10
else
    echo "  Deep crawl data already exists ($DEEP_FILES files) — skip"
fi

# ── Final Stats ──────────────────────────────────────────────────────
echo ""
if curl -sf "$API/api/v1/health" > /dev/null 2>&1; then
    FINAL=$(curl -sf "$API/api/v1/stats" 2>/dev/null)
    FNODES=$(echo "$FINAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['total_nodes'])" 2>/dev/null)
    FEDGES=$(echo "$FINAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['total_edges'])" 2>/dev/null)
    echo "Final: Nodes=$FNODES Edges=$FEDGES"
fi
echo "=== Auto-Improve Done $(date -u) ==="
