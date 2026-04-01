#!/bin/bash
# CogNebula Daily Pipeline — Crawl + Inject + Embed
# Runs on kg-node via cron: 0 10 * * * /home/kg/cognebula-enterprise/scripts/daily_pipeline.sh
set -euo pipefail

LOG="/home/kg/cognebula-enterprise/data/logs/pipeline-$(date +%Y%m%d).log"
mkdir -p "$(dirname "$LOG")"
exec &> >(tee -a "$LOG")

echo "=== CogNebula Daily Pipeline $(date) ==="

cd /home/kg/cognebula-enterprise

# Load environment (API keys)
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

VENV="/home/kg/kg-env/bin/python3"
API="http://localhost:8400"
TODAY=$(date +%Y-%m-%d)
RAW_DIR="data/raw/$TODAY"

# Step 1: Run crawlers
echo "[1/4] Running crawlers (with content depth flags)..."
mkdir -p "$RAW_DIR"
for fetcher in src/fetchers/fetch_*.py; do
    name=$(basename "$fetcher" .py)
    # Enable full content fetching for crawlers that support it
    FLAGS=""
    case "$name" in
        fetch_chinaacc)    FLAGS="--fetch-content" ; TIMEOUT=900 ;;
        fetch_provincial)  FLAGS=""                ; TIMEOUT=600 ;;
        fetch_casc)        FLAGS=""                ; TIMEOUT=300 ;;
        fetch_ctax)        FLAGS=""                ; TIMEOUT=300 ;;
        fetch_customs)     FLAGS=""                ; TIMEOUT=300 ;;
        fetch_stats)       FLAGS=""                ; TIMEOUT=300 ;;
        fetch_baike_kuaiji) FLAGS=""               ; TIMEOUT=900 ;;
        fetch_12366)       FLAGS=""                ; TIMEOUT=600 ;;
        fetch_tax_cases)   FLAGS=""                ; TIMEOUT=900 ;;
        fetch_chinatax)    FLAGS=""                ; TIMEOUT=600 ;;
        fetch_chinatax_api) FLAGS=""               ; TIMEOUT=600 ;;
        fetch_cctaa)       FLAGS=""                ; TIMEOUT=300 ;;
        fetch_cf_browser)  continue ;;  # incompatible CLI, skip until fixed
        *)                 FLAGS=""                ; TIMEOUT=300 ;;
    esac
    echo "  $name (timeout=${TIMEOUT}s)..."
    timeout $TIMEOUT $VENV "$fetcher" --output "$RAW_DIR" $FLAGS 2>&1 | tail -5 || echo "  WARN: $name failed"
done

# Step 2: Dedup + Inject new records
echo "[2/4] Injecting new records..."
$VENV -c "
import json, os, glob, urllib.request

API = '$API/api/v1/ingest'
raw_dir = '$RAW_DIR'

all_records = {}
for fname in glob.glob(os.path.join(raw_dir, '*.json')):
    if 'stats' in fname:
        continue
    try:
        with open(fname) as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue
        for rec in data:
            rid = rec.get('id')
            if rid and rid not in all_records and len(rec.get('title', '')) >= 3:
                all_records[rid] = {
                    'id': rid,
                    'title': (rec.get('title') or '')[:500],
                    'sourceUrl': (rec.get('url') or '')[:500],
                    'fullText': (rec.get('content') or '')[:3000],
                    'regulationNumber': (rec.get('doc_num') or '')[:200],
                    'effectiveDate': str(rec.get('date', ''))[:20],
                    'hierarchyLevel': (rec.get('source') or '')[:100],
                    'regulationType': (rec.get('type') or 'daily_crawl')[:100],
                }
    except:
        pass

nodes = list(all_records.values())
print(f'  Deduped: {len(nodes)} records')

inserted = 0
errors = 0
BATCH = 30
for i in range(0, len(nodes), BATCH):
    batch = nodes[i:i+BATCH]
    payload = json.dumps({'table': 'LawOrRegulation', 'nodes': batch}).encode()
    req = urllib.request.Request(API, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            r = json.loads(resp.read())
            inserted += r.get('inserted', 0)
            errors += r.get('errors', 0)
    except:
        errors += len(batch)

print(f'  Inserted: {inserted}, Errors: {errors}')
"

# Step 3: Generate embeddings for new nodes
echo "[3/4] Generating embeddings..."
# TODO: Run embedding pipeline when LanceDB incremental indexer is set up
echo "  (Skipped — awaiting embedding pipeline setup)"

# Step 4: Health check
echo "[4/4] Health check..."
curl -sf "$API/api/v1/health" | python3 -m json.tool
curl -sf "$API/api/v1/stats" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  Nodes: {d[\"total_nodes\"]:,}  Edges: {d[\"total_edges\"]:,}')
"

echo "=== Pipeline complete $(date) ==="
