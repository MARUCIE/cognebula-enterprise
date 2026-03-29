#!/bin/bash
# Sync locally-built LanceDB to VPS after embedding build completes.
#
# Run: bash scripts/sync_lancedb_to_vps.sh
#
# Prerequisites:
#   - data/lancedb-build/ exists with kg_nodes table
#   - VPS kg-api will be restarted to pick up new index

set -e

LOCAL_LANCE="/Users/mauricewen/Projects/27-cognebula-enterprise/data/lancedb-build"
VPS_LANCE="/home/kg/data/lancedb"
VPS="root@100.88.170.57"

# Check if build is complete
if [ ! -d "$LOCAL_LANCE" ]; then
    echo "ERROR: $LOCAL_LANCE not found. Run build_kg_nodes_local.py first."
    exit 1
fi

COUNT=$(python3 -c "
import lancedb
db = lancedb.connect('$LOCAL_LANCE')
tbl = db.open_table('kg_nodes')
print(tbl.count_rows())
" 2>/dev/null)

if [ -z "$COUNT" ] || [ "$COUNT" -lt 1000 ]; then
    echo "ERROR: LanceDB has only $COUNT rows. Build may be incomplete."
    exit 1
fi

echo "Local LanceDB: $COUNT vectors in kg_nodes table"
echo "Syncing to VPS $VPS:$VPS_LANCE ..."

# Stop kg-api to release LanceDB lock
ssh "$VPS" "systemctl stop kg-api; sleep 1; echo 'kg-api stopped'"

# Rsync with compression
rsync -az --progress "$LOCAL_LANCE/" "$VPS:$VPS_LANCE/"

# Restart kg-api
ssh "$VPS" "systemctl start kg-api; sleep 2; echo 'kg-api restarted'"

# Verify
ssh "$VPS" "curl -sf http://localhost:8400/api/v1/stats | python3 -c \"
import sys, json
d = json.load(sys.stdin)
print(f'VPS KG: {d[\"total_nodes\"]:,} nodes, {d[\"total_edges\"]:,} edges')
\""

echo ""
echo "DONE: $COUNT vectors synced to VPS"
echo "Vector search is now live on kg-api:8400"
