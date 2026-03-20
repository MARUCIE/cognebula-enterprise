#!/bin/bash
# M3 Orchestrator -- Sequential pipeline execution
# Runs: M3 QA → Daily Crawl (catch-up) → Restart API
#
# Usage: ./scripts/m3_orchestrator.sh [qa_batches] [qa_batch_size]
#        Default: 50 batches × 100 articles = 5000 articles per run
set -euo pipefail

cd "$(dirname "$0")/.."

# Load env
if [[ -f .env ]]; then set -a; source .env; set +a; fi

VENV="/home/kg/kg-env/bin/python3"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/m3-orchestrator-$(date +%Y%m%d-%H%M).log"
exec &> >(tee -a "$LOG")

QA_BATCHES="${1:-50}"
QA_BATCH_SIZE="${2:-100}"

echo "================================================================"
echo "  M3 Orchestrator — $(date)"
echo "  QA: ${QA_BATCHES} batches × ${QA_BATCH_SIZE} articles"
echo "================================================================"

# Step 0: Stop API (release DB lock)
echo "[0/4] Stopping API..."
sudo systemctl stop kg-api || true
sleep 2

# Step 1: M3 QA Generation
echo "[1/4] Running M3 QA Generation..."
# Find next offset from existing QA nodes
OFFSET=$($VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph')
conn = kuzu.Connection(db)
r = conn.execute(\"MATCH (k:KnowledgeUnit) WHERE k.id STARTS WITH 'QA_' RETURN count(k)\")
print(r.get_next()[0])
del conn; del db
" 2>/dev/null || echo "0")
echo "  Existing QA nodes: $OFFSET (will offset query)"

$VENV scripts/generate_lr_qa.py \
    --batch-size "$QA_BATCH_SIZE" \
    --max-batches "$QA_BATCHES" \
    --offset "$OFFSET" 2>&1 || echo "  WARN: QA generation had errors"

# Step 2: Edge Engine (Meadows: L3 = edge generation, not node generation)
echo "[2/5] Running Edge Engine (AI relationship discovery)..."
$VENV scripts/generate_edges_ai.py --batch-size 50 --max-batches 10 2>&1 || echo "  WARN: Edge engine had errors"

# Step 3: Restart API (release DB lock before daily crawl)
echo "[3/5] Restarting API..."
sudo systemctl start kg-api
sleep 3

# Step 4: Batch density check (Meadows: compress feedback delay from weeks to 1 day)
echo "[4/5] Batch density check..."
curl -sf http://localhost:8400/api/v1/quality 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
m = d.get('metrics', {})
score = d.get('score', 0)
nodes = m.get('total_nodes', 0)
edges = m.get('total_edges', 0)
density = m.get('edge_density', 0)
print(f'  Score: {score}')
print(f'  Nodes: {nodes:,}')
print(f'  Edges: {edges:,}')
print(f'  Density: {density:.3f}')
print(f'  Target: 6.000 (gap: {6.0 - density:.3f})')
# Alert if density dropped
if density < 2.0:
    print('  ALERT: Density below 2.0! Dilution detected.')
" || echo "  WARN: Quality check failed"

# Step 5: Daily Crawl (file-level only, no DB lock needed)
echo "[5/5] Running Daily Crawl (file output only)..."
if [[ -x scripts/daily_pipeline.sh ]]; then
    timeout 1800 bash scripts/daily_pipeline.sh 2>&1 || echo "  WARN: Daily crawl had errors"
else
    echo "  SKIP: daily_pipeline.sh not executable"
fi

echo "================================================================"
echo "  M3 Orchestrator DONE — $(date)"
echo "================================================================"
