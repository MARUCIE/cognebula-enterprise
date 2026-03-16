#!/bin/bash
# Continuous expansion loop -- run until 500K nodes
# Usage: nohup ./scripts/continuous-expansion.sh > /tmp/expansion.log 2>&1 &
#
# Cycles:
# 1. Check current node count
# 2. If < 500K, run next expansion batch
# 3. Sleep, repeat
#
# Expansion sources (in priority order):
# - QA generation from clauses (batch of 500 clauses = ~1,000 QA nodes)
# - Clause split on new regulations
# - AI synthesis batch (7 industries x 30 = 210 candidates)
# - FGK deep crawl + process (if new data available)

set -euo pipefail
cd /root/Projects/cognebula-enterprise
PY=".venv/bin/python3"
TARGET=500000
BATCH=0

get_count() {
    $PY -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph')
conn = kuzu.Connection(db)
r = conn.execute('MATCH (n) RETURN count(n)')
print(r.get_next()[0])
" 2>/dev/null || echo 0
}

wait_for_db() {
    local max_wait=300
    local waited=0
    while [ $waited -lt $max_wait ]; do
        count=$(get_count)
        if [ "$count" != "0" ]; then
            echo "$count"
            return 0
        fi
        sleep 10
        waited=$((waited + 10))
    done
    echo "0"
    return 1
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Continuous Expansion Loop Started ==="
log "Target: $TARGET nodes"

while true; do
    BATCH=$((BATCH + 1))
    log "--- Batch $BATCH ---"

    # Wait for DB to be available
    CURRENT=$(wait_for_db)
    if [ "$CURRENT" = "0" ]; then
        log "WARN: DB locked, waiting 60s..."
        sleep 60
        continue
    fi

    log "Current nodes: $CURRENT / $TARGET"

    if [ "$CURRENT" -ge "$TARGET" ]; then
        log "TARGET REACHED! $CURRENT >= $TARGET"
        break
    fi

    REMAINING=$((TARGET - CURRENT))
    log "Remaining: $REMAINING nodes to go"

    # === EXPANSION STEP 1: QA from clauses ===
    log "Step 1: Generating QA from clauses (batch of 500)..."
    if [ -f src/generate_clause_qa.py ]; then
        GEMINI_EMBED_BASE="https://gemini-api-proxy.maoyuan-wen-683.workers.dev" \
        $PY src/generate_clause_qa.py --db data/finance-tax-graph --limit 500 2>&1 | tail -5 || log "QA generation had issues"
    fi

    # === EXPANSION STEP 2: Clause split on new regulations ===
    log "Step 2: Clause split (skip existing)..."
    if [ -f src/split_regulation_clauses.py ]; then
        $PY src/split_regulation_clauses.py --db data/finance-tax-graph --limit 1000 --skip-existing 2>&1 | tail -5 || log "Clause split had issues"
    fi

    # === EXPANSION STEP 3: Process any pending raw data ===
    log "Step 3: Processing raw data..."
    for dir in data/raw/20260316-* data/raw/20260315-fgk-deep; do
        if [ -d "$dir" ]; then
            log "  Processing $dir..."
            $PY src/finance_tax_processor.py --input "$dir" --db data/finance-tax-graph 2>&1 | tail -3 || true
        fi
    done

    # Report progress
    NEW_COUNT=$(get_count)
    GAINED=$((NEW_COUNT - CURRENT))
    log "Batch $BATCH complete: $CURRENT -> $NEW_COUNT (+$GAINED)"

    if [ "$GAINED" -lt 10 ]; then
        log "Low yield (<10 nodes). Sleeping 30 min before next batch..."
        sleep 1800
    else
        log "Good yield. Sleeping 5 min before next batch..."
        sleep 300
    fi
done

log "=== Expansion Loop Complete: $(get_count) nodes ==="
