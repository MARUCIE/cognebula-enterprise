#!/bin/bash
# M3 Session Continuation — wait for matrix, then run STARD + edges + density boost
# Run on kg-node: nohup bash scripts/m3_continue.sh > /tmp/m3_continue.log 2>&1 &
set -euo pipefail
cd /home/kg/cognebula-enterprise

VENV="/home/kg/kg-env/bin/python3 -u"
LOG_START=$(date '+%Y-%m-%d %H:%M:%S')

echo "================================================================"
echo "  M3 Continue Pipeline — $LOG_START"
echo "================================================================"

# Step 0: Wait for Fast Matrix to finish
echo "[0/5] Waiting for Fast Matrix to complete..."
# Use [c] trick to prevent pgrep from matching itself or this script
while pgrep -f "[c]ompliance_matrix_fast" >/dev/null 2>&1; do
    LAST=$(tail -1 /tmp/matrix_fast.log 2>/dev/null | grep -oP '\d+/20000' || echo "?")
    echo "  Matrix running: $LAST  (checking every 60s)"
    sleep 60
done
echo "  Fast Matrix completed!"
sleep 5

# Step 1: STARD 55K → ~5.6K tax-filtered ingest + edges
echo ""
echo "[1/5] STARD tax-filtered ingest..."
$VENV scripts/ingest_stard.py 2>&1

# Step 2: Edge density boost (KU→TaxType + KU→LR regulation refs + orphan rescue)
echo ""
echo "[2/5] Edge density boost..."
$VENV scripts/boost_edge_density.py 2>&1

# Step 3: REFERENCES edge batch (Cypher-based, fast)
echo ""
echo "[3/5] REFERENCES edge batch..."
if [[ -f scripts/edge_cypher_batch.py ]]; then
    $VENV scripts/edge_cypher_batch.py 2>&1 || echo "  WARN: edge_cypher_batch had errors"
else
    echo "  SKIP: edge_cypher_batch.py not found"
fi

# Step 4: Restart API
echo ""
echo "[4/5] Restarting API..."
sudo systemctl start kg-api
sleep 5
if systemctl is-active --quiet kg-api; then
    echo "  API started OK"
else
    echo "  ERROR: API failed to start"
fi

# Step 5: Quality check
echo ""
echo "[5/5] Quality check..."
sleep 3
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
" || echo "  WARN: Quality check failed (API may need more time)"

# Step 6: Launch Fast Matrix expansion (offset 22600 → +114K combos)
echo ""
echo "[6/6] Launching Fast Matrix expansion (offset 22600, target 114K)..."
sudo systemctl stop kg-api || true
for i in $(seq 1 15); do
    if ! pgrep -f "uvicorn.*kg-api-server" >/dev/null 2>&1; then break; fi
    sleep 1
done

nohup $VENV scripts/generate_compliance_matrix_fast.py \
    --max-total 114000 --offset 22600 \
    > /tmp/matrix_fast_expansion.log 2>&1 &

echo "  Expansion launched (PID: $!, log: /tmp/matrix_fast_expansion.log)"
echo "  Target: +114K combos → ~100K valid nodes"

echo ""
echo "================================================================"
echo "  M3 Continue Pipeline DONE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Next: monitor /tmp/matrix_fast_expansion.log"
echo "================================================================"
