#!/bin/bash
# m2_pipeline.sh -- CogNebula M2 500K Node Automation Pipeline
# Runs all 3 phases with quality gates. Idempotent: safe to re-run.
#
# Cron: 0 12 * * * /home/kg/cognebula-enterprise/scripts/m2_pipeline.sh
# Manual: ./scripts/m2_pipeline.sh [--phase 1|2|3|all] [--dry-run]
set -euo pipefail

cd "$(dirname "$0")/.."

# Load environment (API keys)
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

VENV="/home/kg/kg-env/bin/python3"
API="http://localhost:8400"
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/m2-pipeline-$(date +%Y%m%d-%H%M).log"
exec &> >(tee -a "$LOG")

# Parse args
PHASE="${1:---phase}"
PHASE_NUM="${2:-all}"
DRY_RUN=""
for arg in "$@"; do
    [[ "$arg" == "--dry-run" ]] && DRY_RUN="--dry-run"
    [[ "$arg" == "--phase" ]] && true  # consumed with next arg
done
if [[ "$PHASE" != "--phase" ]]; then
    PHASE_NUM="all"
fi

echo "================================================================"
echo "  CogNebula M2 Pipeline — $(date)"
echo "  Phase: $PHASE_NUM | Dry-run: ${DRY_RUN:-no}"
echo "================================================================"

# --- Helper: get node count from API ---
get_node_count() {
    # Try API first, fall back to direct DB query
    local count
    count=$(curl -sf "$API/api/v1/stats" 2>/dev/null | \
        $VENV -c "import sys,json; d=json.load(sys.stdin); print(d['total_nodes'])" 2>/dev/null)
    if [[ -n "$count" && "$count" != "0" ]]; then
        echo "$count"
    else
        # Direct DB query (only works when API is stopped)
        $VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph', read_only=True)
conn = kuzu.Connection(db)
r = conn.execute('MATCH (n) RETURN count(n)')
print(r.get_next()[0])
" 2>/dev/null || echo "0"
    fi
}

get_edge_count() {
    curl -sf "$API/api/v1/stats" 2>/dev/null | \
        $VENV -c "import sys,json; d=json.load(sys.stdin); print(d['total_edges'])" 2>/dev/null || echo "0"
}

# --- Helper: quality gate check ---
quality_gate() {
    local gate_name="$1"
    local target="$2"
    local current
    current=$(get_node_count)
    echo ""
    echo "--- Quality Gate: $gate_name ---"
    echo "  Current: $current nodes | Target: >= $target"
    if [[ "$current" -ge "$target" ]]; then
        echo "  PASS"
        return 0
    else
        echo "  NOT YET (need $(( target - current )) more nodes)"
        return 1
    fi
}

# --- Pre-flight ---
echo ""
echo "[Pre-flight] Checking KG API..."
if ! curl -sf "$API/api/v1/health" > /dev/null 2>&1; then
    echo "  API not running, attempting restart..."
    sudo systemctl start kg-api 2>/dev/null || true
    sleep 3
    if ! curl -sf "$API/api/v1/health" > /dev/null 2>&1; then
        echo "  WARN: API still not reachable. Phase 1 will handle it."
    fi
fi

INITIAL_NODES=$(get_node_count)
INITIAL_EDGES=$(get_edge_count)
echo "  Nodes: $INITIAL_NODES | Edges: $INITIAL_EDGES"
echo ""

# ================================================================
# PHASE 1: Clause-Level Deep Split (+180K target)
# ================================================================
run_phase1() {
    echo "================================================================"
    echo "  PHASE 1: Clause-Level Deep Split"
    echo "================================================================"

    # KuzuDB single-writer lock: API must be stopped for direct DB access
    # Split and QA scripts use `import kuzu` directly, not the HTTP API
    echo "[P1.0] Stopping kg-api for direct DB access..."
    sudo systemctl stop kg-api 2>/dev/null || true
    sleep 2

    # Step 1a: Split regulations into clauses
    echo "[P1.1] Splitting regulations into clauses..."
    if [[ -n "$DRY_RUN" ]]; then
        $VENV src/split_clauses_v2.py --dry-run 2>&1 | tail -10
    else
        $VENV src/split_clauses_v2.py 2>&1 | tail -20
    fi

    local after_split
    # Can query DB directly since API is stopped
    after_split=$($VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph', read_only=True)
conn = kuzu.Connection(db)
r = conn.execute('MATCH (n) RETURN count(n)')
print(r.get_next()[0])
" 2>/dev/null || echo "0")
    echo "  Nodes after split: $after_split"

    # Step 1b: Generate QA pairs from clauses (requires Gemini API key)
    # Process 2000 clauses per cron run (~30 min). Full 28K takes ~14 days.
    echo ""
    echo "[P1.2] Generating QA pairs from clauses (Gemini, limit=2000)..."
    if [[ -n "$DRY_RUN" ]]; then
        $VENV src/generate_clause_qa_v2.py --dry-run --limit 100 2>&1 | tail -10
    else
        timeout 3600 $VENV src/generate_clause_qa_v2.py --limit 2000 --batch-size 10 2>&1 | tail -20
    fi

    # Restart API
    echo ""
    echo "[P1.3] Restarting kg-api..."
    sudo systemctl start kg-api 2>/dev/null || true
    sleep 3

    # Verify API is back
    if curl -sf "$API/api/v1/health" > /dev/null 2>&1; then
        echo "  API restored OK"
    else
        echo "  WARN: API may not have restarted. Check: systemctl status kg-api"
    fi

    quality_gate "Phase 1 (150K)" 150000 || true
}

# ================================================================
# PHASE 2: Source Expansion (+150K target)
# ================================================================
run_phase2() {
    echo "================================================================"
    echo "  PHASE 2: Source Expansion"
    echo "================================================================"

    # Step 2a: Run all fetchers (daily crawl)
    echo "[P2.1] Running all fetchers..."
    local raw_dir="data/raw/$(date +%Y-%m-%d)"
    mkdir -p "$raw_dir"
    for fetcher in src/fetchers/fetch_*.py; do
        name=$(basename "$fetcher" .py)
        echo "  $name..."
        timeout 180 $VENV "$fetcher" --output "$raw_dir" 2>&1 | tail -1 || echo "  WARN: $name failed"
    done

    # Step 2b: Inject crawled data
    echo ""
    echo "[P2.2] Injecting crawled records..."
    $VENV -c "
import json, os, glob, urllib.request

API = '$API/api/v1/ingest'
raw_dir = '$raw_dir'

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
" 2>&1

    # Step 2c: Inject un-injected data sources (chinaacc, 12366, HS codes)
    echo ""
    echo "[P2.3] Injecting accumulated data sources..."
    for inject_script in src/inject_*.py; do
        name=$(basename "$inject_script" .py)
        echo "  $name..."
        if [[ -n "$DRY_RUN" ]]; then
            echo "    (dry-run skipped)"
        else
            timeout 300 $VENV "$inject_script" 2>&1 | tail -3 || echo "  WARN: $name failed"
        fi
    done

    # Step 2d: Enrich orphan edges
    echo ""
    echo "[P2.4] Enriching orphan edges..."
    if [[ -f "src/enrich_orphan_edges.py" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            echo "  (dry-run skipped)"
        else
            timeout 600 $VENV src/enrich_orphan_edges.py 2>&1 | tail -10 || echo "  WARN: edge enrichment failed"
        fi
    else
        echo "  SKIP: enrich_orphan_edges.py not found"
    fi

    quality_gate "Phase 2 (250K)" 250000 || true
}

# ================================================================
# PHASE 3: AI Synthesis + Cross-Reference (+82K target)
# ================================================================
run_phase3() {
    echo "================================================================"
    echo "  PHASE 3: AI Synthesis + Cross-Reference"
    echo "================================================================"

    # Step 3a: Industry x Tax x Scenario matrix
    echo "[P3.1] Generating cross-product matrix..."
    if [[ -f "src/generate_cross_product.py" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            $VENV src/generate_cross_product.py --dry-run 2>&1 | tail -5 || true
        else
            timeout 1800 $VENV src/generate_cross_product.py 2>&1 | tail -10 || echo "  WARN: cross-product failed"
        fi
    else
        echo "  SKIP: generate_cross_product.py not found"
    fi

    # Step 3b: Lifecycle compliance matrix
    echo ""
    echo "[P3.2] Generating lifecycle matrix..."
    if [[ -f "src/generate_lifecycle_matrix.py" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            $VENV src/generate_lifecycle_matrix.py --dry-run 2>&1 | tail -5 || true
        else
            timeout 1800 $VENV src/generate_lifecycle_matrix.py 2>&1 | tail -10 || echo "  WARN: lifecycle matrix failed"
        fi
    else
        echo "  SKIP: generate_lifecycle_matrix.py not found"
    fi

    # Step 3c: Compliance matrix
    echo ""
    echo "[P3.3] Generating compliance matrix..."
    if [[ -f "src/generate_compliance_matrix.py" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            $VENV src/generate_compliance_matrix.py --dry-run 2>&1 | tail -5 || true
        else
            timeout 1800 $VENV src/generate_compliance_matrix.py 2>&1 | tail -10 || echo "  WARN: compliance matrix failed"
        fi
    else
        echo "  SKIP: generate_compliance_matrix.py not found"
    fi

    # Step 3d: Industry FAQ matrix
    echo ""
    echo "[P3.4] Generating industry FAQ matrix..."
    if [[ -f "src/generate_industry_faq_matrix.py" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            $VENV src/generate_industry_faq_matrix.py --dry-run 2>&1 | tail -5 || true
        else
            timeout 1800 $VENV src/generate_industry_faq_matrix.py 2>&1 | tail -10 || echo "  WARN: FAQ matrix failed"
        fi
    else
        echo "  SKIP: generate_industry_faq_matrix.py not found"
    fi

    quality_gate "Phase 3 (350K)" 350000 || true
}

# ================================================================
# FINAL: Summary + Quality Gate
# ================================================================
run_summary() {
    echo ""
    echo "================================================================"
    echo "  PIPELINE SUMMARY"
    echo "================================================================"
    local final_nodes final_edges
    final_nodes=$(get_node_count)
    final_edges=$(get_edge_count)
    echo "  Start:  $INITIAL_NODES nodes / $INITIAL_EDGES edges"
    echo "  Final:  $final_nodes nodes / $final_edges edges"
    echo "  Delta:  +$(( final_nodes - INITIAL_NODES )) nodes / +$(( final_edges - INITIAL_EDGES )) edges"
    echo ""

    # Final quality gate
    if quality_gate "M2 Target (500K)" 500000; then
        echo ""
        echo "  >>> M2 ACHIEVED! <<<"
    else
        echo ""
        echo "  M2 not yet reached. Continue pipeline runs."
    fi

    # Log rotation: keep last 30 days
    find "$LOG_DIR" -name "m2-pipeline-*.log" -mtime +30 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "pipeline-*.log" -mtime +30 -delete 2>/dev/null || true

    echo ""
    echo "  Log: $LOG"
    echo "  Done: $(date)"
}

# ================================================================
# DISPATCH
# ================================================================
case "$PHASE_NUM" in
    1)     run_phase1; run_summary ;;
    2)     run_phase2; run_summary ;;
    3)     run_phase3; run_summary ;;
    all)   run_phase1; run_phase2; run_phase3; run_summary ;;
    *)     echo "Usage: $0 [--phase 1|2|3|all] [--dry-run]"; exit 1 ;;
esac
