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
        # ── Fast fetchers (listing only, <5 min) ──
        fetch_chinatax_api) FLAGS=""               ; TIMEOUT=600 ;;
        fetch_provincial)  FLAGS=""                ; TIMEOUT=120 ;;  # most provinces blocked by VPS IP
        fetch_chinatax)    FLAGS=""                ; TIMEOUT=600 ;;
        fetch_cctaa)       FLAGS="--fetch-content" ; TIMEOUT=1200 ;;
        fetch_casc)        FLAGS=""                ; TIMEOUT=300 ;;
        fetch_cicpa)       FLAGS="--fetch-content" ; TIMEOUT=900 ;;
        fetch_csrc)        FLAGS=""                ; TIMEOUT=300 ;;
        fetch_mof)         FLAGS=""                ; TIMEOUT=300 ;;
        fetch_ndrc)        FLAGS=""                ; TIMEOUT=300 ;;
        fetch_pbc)         FLAGS=""                ; TIMEOUT=300 ;;
        fetch_safe)        FLAGS=""                ; TIMEOUT=300 ;;
        fetch_stats)       FLAGS=""                ; TIMEOUT=300 ;;
        fetch_npc)         continue ;;  # dead API (405), replaced by fetch_flk_npc
        fetch_customs)     FLAGS=""                ; TIMEOUT=180 ;;  # Playwright JSL cookies
        fetch_ctax)        FLAGS=""                ; TIMEOUT=120 ;;  # domain dead, quick fail
        fetch_flk_npc)     FLAGS=""                ; TIMEOUT=30  ;;  # reads Playwright cache
        fetch_samr)        FLAGS=""                ; TIMEOUT=60  ;;  # Playwright
        fetch_miit)        FLAGS=""                ; TIMEOUT=60  ;;  # Playwright
        fetch_hs_codes)    FLAGS=""                ; TIMEOUT=300 ;;
        # ── Deep fetchers (detail pages, 10-30 min each) ── skip in daily pipeline
        fetch_chinaacc|fetch_baike_kuaiji|fetch_12366|fetch_tax_cases)
            echo "    SKIP (deep fetcher, runs via M3 orchestrator)"
            continue ;;
        fetch_cf_browser)  continue ;;  # replaced by Playwright fetchers
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
