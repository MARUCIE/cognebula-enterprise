#!/bin/bash
# CogNebula Progress Patrol — 4-hourly health check + incremental improvements
#
# Crontab: 0 */4 * * * /home/kg/cognebula-enterprise/scripts/progress_patrol.sh
#
# Actions per run:
#   1. Health check + stats snapshot
#   2. Incremental embedding for new nodes (if API up)
#   3. Edge enrichment check
#   4. Generate progress report
#   5. Push to Telegram (if configured)
set -uo pipefail

cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -a; source .env; set +a; fi

VENV="/home/kg/kg-env/bin/python3"
API="http://localhost:8400"
LOG_DIR="data/logs"
REPORT_DIR="data/reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

TIMESTAMP=$(date -u +%Y%m%d-%H%M)
LOG="$LOG_DIR/patrol-${TIMESTAMP}.log"
REPORT="$REPORT_DIR/progress-${TIMESTAMP}.md"

exec > >(tee -a "$LOG") 2>&1

echo "================================================================"
echo "  Progress Patrol — $(date -u)"
echo "================================================================"

# ── 1. Health Check ──────────────────────────────────────────────────
echo "[1/5] Health Check..."
API_OK=false
HEALTH=$(curl -sf "$API/api/v1/health" 2>/dev/null)
if echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['status']=='healthy'" 2>/dev/null; then
    API_OK=true
    echo "  API: healthy"
    LANCEDB_ROWS=$(echo "$HEALTH" | python3 -c "import json,sys; print(json.load(sys.stdin).get('lancedb_rows',0))" 2>/dev/null)
    echo "  LanceDB: $LANCEDB_ROWS vectors"
else
    echo "  API: DOWN (M3 or M2 may be running)"
fi

STATS=""
NODES=0; EDGES=0
if $API_OK; then
    STATS=$(curl -sf "$API/api/v1/stats" 2>/dev/null)
    NODES=$(echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin)['total_nodes'])" 2>/dev/null || echo 0)
    EDGES=$(echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin)['total_edges'])" 2>/dev/null || echo 0)
    echo "  Nodes: $NODES  Edges: $EDGES"
fi

# ── 2. Pipeline Status ───────────────────────────────────────────────
echo "[2/5] Pipeline Status..."
TODAY=$(date -u +%Y-%m-%d)
M3_LOG=$(ls -t data/logs/m3-orchestrator-$(date -u +%Y%m%d)*.log 2>/dev/null | head -1)
DAILY_LOG="data/logs/pipeline-$(date -u +%Y%m%d).log"
M2_LOG=$(ls -t data/logs/m2-pipeline-$(date -u +%Y%m%d)*.log 2>/dev/null | head -1)

M3_STATUS="not run"
if [[ -n "$M3_LOG" ]]; then
    if grep -q "DONE" "$M3_LOG" 2>/dev/null; then
        M3_STATUS="completed"
        M3_QA=$(grep "Generated:" "$M3_LOG" 2>/dev/null | tail -1 | grep -o '[0-9]* QA' || echo "?")
        M3_KU=$(grep "Updated:" "$M3_LOG" 2>/dev/null | tail -1 | grep -o '[0-9]* KU' || echo "?")
        echo "  M3: $M3_STATUS ($M3_QA, $M3_KU)"
    elif pgrep -f m3_orchestrator > /dev/null 2>&1; then
        M3_STATUS="running"
        echo "  M3: running"
    fi
else
    echo "  M3: not run today"
fi

DAILY_STATUS="not run"
if [[ -f "$DAILY_LOG" ]]; then
    if grep -q "Pipeline complete" "$DAILY_LOG" 2>/dev/null; then
        DAILY_STATUS="completed"
        DAILY_RECORDS=$(grep "Deduped:" "$DAILY_LOG" 2>/dev/null | tail -1 | grep -o '[0-9]* records' || echo "?")
        echo "  Daily: $DAILY_STATUS ($DAILY_RECORDS)"
    fi
else
    echo "  Daily: not run today"
fi

M2_STATUS="not run"
if [[ -n "$M2_LOG" ]]; then
    M2_STATUS="ran"
    echo "  M2: $M2_STATUS"
else
    echo "  M2: not run today"
fi

# ── 3. Incremental Work (only if API is up) ──────────────────────────
echo "[3/5] Incremental Improvements..."
INCR_EMBED=0
INCR_EDGES=0
INCR_FAQ=0

if $API_OK; then
    # 3a. Check for new nodes not in vector index
    NEW_NODES=$((NODES - LANCEDB_ROWS))
    if [[ $NEW_NODES -gt 100 ]]; then
        echo "  NOTE: $NEW_NODES nodes not in vector index (rebuild needed when gap > 5000)"
    else
        echo "  Vectors: synced ($NEW_NODES gap)"
    fi

    # 3b. Quick edge enrichment (keyword-based, no LLM, ~10 sec)
    # Only run if API will be stopped briefly
    # Skip for now — don't stop API in patrol mode
    echo "  Edge enrichment: deferred (requires API stop)"
fi

# ── 4. Quality Metrics ───────────────────────────────────────────────
echo "[4/5] Quality Metrics..."
if $API_OK; then
    QUALITY=$(curl -sf "$API/api/v1/quality" 2>/dev/null)
    TITLE_COV=$(echo "$QUALITY" | python3 -c "import json,sys; print(f'{json.load(sys.stdin)[\"metrics\"][\"title_coverage\"]:.1%}')" 2>/dev/null || echo "?")
    CONTENT_COV=$(echo "$QUALITY" | python3 -c "import json,sys; print(f'{json.load(sys.stdin)[\"metrics\"][\"content_coverage\"]:.1%}')" 2>/dev/null || echo "?")
    EDGE_DEN=$(echo "$QUALITY" | python3 -c "import json,sys; print(f'{json.load(sys.stdin)[\"metrics\"][\"edge_density\"]:.3f}')" 2>/dev/null || echo "?")
    echo "  title_coverage:   $TITLE_COV"
    echo "  content_coverage: $CONTENT_COV"
    echo "  edge_density:     $EDGE_DEN"
fi

# ── 5. Crawl Data Check ─────────────────────────────────────────────
echo "[5/5] Today's Crawl Data..."
RAW_DIR="data/raw/$(date -u +%Y-%m-%d)"
if [[ -d "$RAW_DIR" ]]; then
    TOTAL_SIZE=$(du -sh "$RAW_DIR" 2>/dev/null | cut -f1)
    FILE_COUNT=$(find "$RAW_DIR" -name "*.json" -size +2c 2>/dev/null | wc -l)
    EMPTY_COUNT=$(find "$RAW_DIR" -name "*.json" -size -3c 2>/dev/null | wc -l)
    echo "  Raw data: $TOTAL_SIZE ($FILE_COUNT files with data, $EMPTY_COUNT empty)"
else
    echo "  No crawl data today yet"
fi

# ── Generate Report ──────────────────────────────────────────────────
cat > "$REPORT" << REPORT_EOF
# CogNebula Progress Report — $(date -u +"%Y-%m-%d %H:%M UTC")

## System
- API: $($API_OK && echo "healthy" || echo "DOWN")
- Nodes: $(printf "%'d" $NODES)
- Edges: $(printf "%'d" $EDGES)
- Vectors: $(printf "%'d" ${LANCEDB_ROWS:-0}) @ 3072-dim
- Disk: $(df -h / | tail -1 | awk '{print $4 " free (" $5 " used)"}')

## Quality
- title: ${TITLE_COV:-?}
- content: ${CONTENT_COV:-?}
- density: ${EDGE_DEN:-?}

## Pipelines Today
- M3 (02:00): ${M3_STATUS}
- Daily (10:00): ${DAILY_STATUS}
- M2 (14:00): ${M2_STATUS}

## Crawl
- Files: ${FILE_COUNT:-0} with data, ${EMPTY_COUNT:-0} empty
REPORT_EOF

echo ""
echo "Report saved: $REPORT"
echo "================================================================"
echo "  Patrol Done — $(date -u)"
echo "================================================================"

# ── Telegram Notification (if bot token configured) ──────────────────
TG_TOKEN="${TG_BOT_TOKEN:-}"
TG_CHAT="${TG_CHAT_ID:-}"
if [[ -n "$TG_TOKEN" && -n "$TG_CHAT" ]]; then
    MSG="📊 CogNebula $(date -u +%H:%M)
Nodes: $(printf "%'d" $NODES) | Edges: $(printf "%'d" $EDGES)
Content: ${CONTENT_COV:-?} | Density: ${EDGE_DEN:-?}
M3: ${M3_STATUS} | Daily: ${DAILY_STATUS}"
    curl -sf "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -d "chat_id=${TG_CHAT}" \
        -d "text=${MSG}" \
        -d "parse_mode=Markdown" > /dev/null 2>&1 || true
    echo "  Telegram: sent"
fi
