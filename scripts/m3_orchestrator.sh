#!/bin/bash
# M3 Orchestrator -- Sequential pipeline execution
# Runs: Stop API → QA Gen → KU Backfill → Edge Engine → Enrichment → Start API → Density → Crawl
#
# Usage: ./scripts/m3_orchestrator.sh [qa_batches] [qa_batch_size]
#        Default: 50 batches × 100 articles = 5000 articles per run
set -euo pipefail

cd "$(dirname "$0")/.."

# Load env
if [[ -f .env ]]; then set -a; source .env; set +a; fi

# -u = unbuffered stdout/stderr (critical for tee pipe logging)
VENV="/home/kg/kg-env/bin/python3 -u"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/m3-orchestrator-$(date +%Y%m%d-%H%M).log"
exec &> >(tee -a "$LOG")

QA_BATCHES="${1:-10}"
QA_BATCH_SIZE="${2:-100}"
STEPS=9

echo "================================================================"
echo "  M3 Orchestrator — $(date)"
echo "  QA: ${QA_BATCHES} batches × ${QA_BATCH_SIZE} articles"
echo "================================================================"

# Step 0: Stop API (release KuzuDB flock)
echo "[0/$STEPS] Stopping API..."
sudo systemctl stop kg-api || true
for i in $(seq 1 15); do
    if ! pgrep -f "uvicorn.*kg-api-server" >/dev/null 2>&1; then
        echo "  API stopped (waited ${i}s)"
        break
    fi
    sleep 1
done
if pgrep -f "uvicorn.*kg-api-server" >/dev/null 2>&1; then
    echo "  WARN: API still running after 15s, sending SIGKILL"
    sudo pkill -9 -f "uvicorn.*kg-api-server" || true
    sleep 2
fi

# Step 1: M3 QA Generation (LR articles → KU QA pairs)
echo "[1/$STEPS] Running M3 QA Generation..."
OFFSET=$($VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph')
conn = kuzu.Connection(db)
r = conn.execute(\"MATCH (k:KnowledgeUnit) WHERE k.id STARTS WITH 'QA_' RETURN count(k)\")
print(r.get_next()[0])
del conn; del db
" 2>/dev/null || echo "0")
echo "  Existing QA nodes: $OFFSET (will offset query)"

# Max 2h for QA gen — must finish before daily pipeline at 10:00 UTC
timeout 7200 $VENV scripts/generate_lr_qa.py \
    --batch-size "$QA_BATCH_SIZE" \
    --max-batches "$QA_BATCHES" \
    --offset "$OFFSET" 2>&1 || echo "  WARN: QA generation had errors (or timeout)"

# Step 2: KU Content Backfill (Gemini → fill empty KU content)
echo "[2/$STEPS] Running KU Content Backfill..."
if [[ -f scripts/ku_content_backfill.py ]]; then
    timeout 3600 $VENV scripts/ku_content_backfill.py \
        --batch-size 20 --max-batches 100 2>&1 || echo "  WARN: KU backfill had errors (or timeout)"
else
    echo "  SKIP: ku_content_backfill.py not found"
fi

# Step 2b: FAQ Content Fill (Gemini → answer empty FAQ-type KUs)
echo "[2b/$STEPS] Running FAQ Content Fill..."
if [[ -f scripts/fill_faq_content.py ]]; then
    timeout 3600 $VENV scripts/fill_faq_content.py --max 2000 2>&1 || echo "  WARN: FAQ fill had errors (or timeout)"
else
    echo "  SKIP: fill_faq_content.py not found"
fi

# Step 3: Edge Engine (AI relationship discovery — Meadows: L3 = edge engine)
echo "[3/$STEPS] Running Edge Engine..."
timeout 3600 $VENV scripts/generate_edges_ai.py --batch-size 50 --max-batches 10 2>&1 || echo "  WARN: Edge engine had errors (or timeout)"

# Step 4: Batch edge enrichment (keyword-based, no LLM, fast)
echo "[4/$STEPS] Running batch edge enrichment..."
$VENV scripts/enrich_edges_batch.py 2>&1 || echo "  WARN: Enrichment had errors"

# Step 5: Restart API
echo "[5/$STEPS] Restarting API..."
sudo systemctl start kg-api
sleep 5

# Step 6: Density check (Meadows: compress feedback delay from weeks to 1 day)
echo "[6/$STEPS] Batch density check..."
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
if density < 2.0:
    print('  ALERT: Density below 2.0! Dilution detected.')
" || echo "  WARN: Quality check failed"

# Step 7: Daily Crawl — fast fetchers (file output only, no DB lock needed)
echo "[7/$STEPS] Running Daily Crawl (fast)..."
if [[ -x scripts/daily_pipeline.sh ]]; then
    timeout 1800 bash scripts/daily_pipeline.sh 2>&1 || echo "  WARN: Daily crawl had errors"
else
    echo "  SKIP: daily_pipeline.sh not executable"
fi

# Step 8: Deep Crawl — detail-page fetchers (12366, chinaacc, baike, tax_cases)
echo "[8/$STEPS] Running Deep Crawl..."
if [[ -x scripts/deep_crawl.sh ]]; then
    timeout 5400 bash scripts/deep_crawl.sh 2>&1 || echo "  WARN: Deep crawl had errors"
else
    echo "  SKIP: deep_crawl.sh not found"
fi

echo "================================================================"
echo "  M3 Orchestrator DONE — $(date)"
echo "================================================================"
