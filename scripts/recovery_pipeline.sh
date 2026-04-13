#!/bin/bash
# recovery_pipeline.sh — Post clause-split recovery steps
# Run AFTER split_clauses_v2.py completes
# Requires: API stopped, DB write lock available

set -euo pipefail
VENV="/home/kg/kg-env/bin/python3"
DB_PATH="/home/kg/cognebula-enterprise/data/finance-tax-graph"
export GEMINI_API_KEY=$(grep GEMINI_API_KEY /home/kg/.env.kg-api | cut -d= -f2)

cd /home/kg/cognebula-enterprise

echo "================================================================"
echo "  Recovery Pipeline — $(date)"
echo "================================================================"

# Step 1: Verify clause split results
echo "[1/6] Verifying clause split..."
$VENV -c "
import kuzu
db = kuzu.Database('$DB_PATH')
conn = kuzu.Connection(db)
r = conn.execute('MATCH (n) RETURN count(n)')
nodes = r.get_next()[0]
r = conn.execute('MATCH ()-[e]->() RETURN count(e)')
edges = r.get_next()[0]
try:
    r = conn.execute('MATCH (n:RegulationClause) RETURN count(n)')
    rc = r.get_next()[0]
except: rc = 0
print(f'  Nodes: {nodes:,} | Edges: {edges:,} | RegulationClause: {rc:,}')
conn.execute('CHECKPOINT')
del conn, db
"

# Step 2: CPA Content Backfill (remaining ~4K nodes)
echo "[2/6] CPA Content Backfill..."
timeout 1800 $VENV scripts/cpa_content_backfill.py --batch-size 15 --max-batches 300 2>&1 | tail -5 || echo "  WARN: CPA backfill had errors"

# Step 3: Edge density boost (hardened version)
echo "[3/6] Edge Density Boost..."
timeout 600 $VENV scripts/boost_edge_density.py 2>&1 | tail -10 || echo "  WARN: Edge boost had errors"

# Step 4: Batch edge enrichment
echo "[4/6] Batch Edge Enrichment..."
timeout 600 $VENV scripts/enrich_edges_batch.py 2>&1 | tail -5 || echo "  WARN: Enrichment had errors"

# Step 5: Final checkpoint + stats
echo "[5/6] Final checkpoint and stats..."
$VENV -c "
import kuzu
db = kuzu.Database('$DB_PATH')
conn = kuzu.Connection(db)
conn.execute('CHECKPOINT')
r = conn.execute('MATCH (n) RETURN count(n)')
nodes = r.get_next()[0]
r = conn.execute('MATCH ()-[e]->() RETURN count(e)')
edges = r.get_next()[0]
density = edges / nodes if nodes > 0 else 0
r = conn.execute('CALL show_tables() RETURN *')
tables = []
while r.has_next(): tables.append(r.get_next())
nt = sum(1 for t in tables if t[2] == 'NODE')
rt = sum(1 for t in tables if t[2] == 'REL')
print(f'  Final: {nodes:,} nodes / {edges:,} edges / density {density:.3f}')
print(f'  Tables: {nt} NODE / {rt} REL')
del conn, db
"

# Step 6: Restart API
echo "[6/6] Restarting API..."
sudo systemctl start kg-api
sleep 3
curl -sf http://localhost:8400/api/v1/health && echo " API healthy" || echo " API FAILED"

echo "================================================================"
echo "  Recovery Pipeline DONE — $(date)"
echo "================================================================"
