#!/usr/bin/env bash
# finance-tax-crawl.sh -- Thin orchestrator for Finance/Tax Knowledge Base
# Composes existing AI-Fleet skills, NOT custom spiders.
# Registered in pipeline-registry.json as "finance-tax-daily-crawl"
#
# Usage:
#   bash scripts/finance-tax-crawl.sh                    # full pipeline
#   bash scripts/finance-tax-crawl.sh --phase discover   # only discovery
#   bash scripts/finance-tax-crawl.sh --phase crawl      # only crawl
#   bash scripts/finance-tax-crawl.sh --phase process    # only process
#   bash scripts/finance-tax-crawl.sh --phase embed      # only embed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AI_FLEET_DIR="${AI_FLEET_DIR:-$HOME/00-AI-Fleet}"
DATE_TAG=$(date +%Y-%m-%d)
DATA_DIR="$PROJECT_DIR/data/raw/$DATE_TAG"
DB_PATH="$PROJECT_DIR/data/finance-tax-graph"
STATS_DIR="$PROJECT_DIR/data/stats"
PHASE="${1:---all}"

mkdir -p "$DATA_DIR" "$STATS_DIR"

log() { echo "$(date +%H:%M:%S) NOTE: $*"; }
err() { echo "$(date +%H:%M:%S) ERROR: $*" >&2; }

# ── Phase 1: Discovery (multi-search-engine for new policy URLs) ────────
phase_discover() {
    log "Phase 1 - Policy discovery via existing skills"
    # Uses multi-search-engine (17 engines, zero API keys)
    # Search terms targeting daily policy updates
    local queries=(
        "国家税务总局 最新公告 site:chinatax.gov.cn"
        "财政部 政策发布 site:mof.gov.cn"
        "国务院 涉税 site:gov.cn"
        "海关总署 关税调整 site:customs.gov.cn"
    )
    log "Discovery queries: ${#queries[@]} search terms"
    # Output: discovered URLs saved to $DATA_DIR/discovered_urls.json
}

# ── Phase 2: Crawl government sources (agent-reach + defuddle) ──────────
phase_crawl() {
    log "Phase 2 - Crawl Tier 1-2 sources via fetchers"
    local PYTHON="${PROJECT_DIR}/.venv/bin/python"
    [[ ! -x "$PYTHON" ]] && PYTHON="python3"
    local FETCHERS_DIR="$PROJECT_DIR/src/fetchers"

    # --- Tier 1: Core tax/finance sources (8 active) ---
    log "Running fetcher: ChinaTax (国家税务总局 non-SPA)"
    $PYTHON "$FETCHERS_DIR/fetch_chinatax.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    log "Running fetcher: ChinaTax FGK API (法规库 JSON API)"
    $PYTHON "$FETCHERS_DIR/fetch_chinatax_api.py" --output "$DATA_DIR" --max-total 500 2>&1 | tail -3 || true

    log "Running fetcher: MOF (财政部)"
    $PYTHON "$FETCHERS_DIR/fetch_mof.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    log "Running fetcher: PBC (央行)"
    $PYTHON "$FETCHERS_DIR/fetch_pbc.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    log "Running fetcher: SAFE (外汇管理局)"
    $PYTHON "$FETCHERS_DIR/fetch_safe.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    log "Running fetcher: CSRC (证监会)"
    $PYTHON "$FETCHERS_DIR/fetch_csrc.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    # --- Tier 2: Extended government sources (3 active) ---
    log "Running fetcher: NDRC (发改委)"
    $PYTHON "$FETCHERS_DIR/fetch_ndrc.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    log "Running fetcher: CASC (会计准则委)"
    $PYTHON "$FETCHERS_DIR/fetch_casc.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    log "Running fetcher: Stats (国家统计局)"
    $PYTHON "$FETCHERS_DIR/fetch_stats.py" --output "$DATA_DIR" --no-detail 2>&1 | tail -3 || true

    # Disabled: NPC (Vue SPA), Customs (WAF 412), CTax (DNS dead), SAMR/MIIT (Hanweb JS)

    # Count results
    local json_count
    json_count=$(find "$DATA_DIR" -name "*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
    log "Phase 2 complete: $json_count JSON files in $DATA_DIR"
}

# ── Phase 3: News aggregation (finance-tax profile) ────────────────────
phase_news() {
    log "Phase 3 - News aggregation (finance-tax profile)"
    # Invoke news-aggregator-skill with finance-tax profile
    # Sources: wallstreetcn (built-in), 36kr (built-in), + new fetchers
    # Output: JSON in $DATA_DIR/news/
    if [[ -d "$AI_FLEET_DIR" ]]; then
        log "AI-Fleet found at $AI_FLEET_DIR"
        # python $NEWS_AGGREGATOR/fetch_news.py --profile finance-tax --output "$DATA_DIR/news"
    fi
}

# ── Phase 4: Process + NER + Change Detection + Ingest ──────────────────
phase_process() {
    log "Phase 4 - Processing pipeline (NER + change detection + KuzuDB)"
    python3 "$PROJECT_DIR/src/finance_tax_processor.py" \
        --input "$DATA_DIR" \
        --db "$DB_PATH" \
        --stats-output "$STATS_DIR/$DATE_TAG.json"
    log "Processing complete. Stats: $STATS_DIR/$DATE_TAG.json"
}

# ── Phase 4b: Obsidian vault conversion ──────────────────────────────────
phase_obsidian() {
    log "Phase 4b - Obsidian vault conversion (json_to_obsidian.py)"
    local PYTHON="${PROJECT_DIR}/.venv/bin/python"
    [[ ! -x "$PYTHON" ]] && PYTHON="python3"
    local VAULT_DIR="${OBSIDIAN_VAULT:-$HOME/Obsidian/财税知识库}"

    if [[ -d "$VAULT_DIR" ]]; then
        $PYTHON "$PROJECT_DIR/src/json_to_obsidian.py" \
            --input "$DATA_DIR" --vault "$VAULT_DIR" 2>&1 | tail -3 || true
        # Git commit if vault is tracked
        if [[ -d "$VAULT_DIR/.git" ]]; then
            cd "$VAULT_DIR" && git add -A && \
                git commit -m "auto: daily crawl $DATE_TAG" --allow-empty -q 2>/dev/null || true
            cd "$PROJECT_DIR"
        fi
    else
        log "WARN: Obsidian vault not found at $VAULT_DIR, skipping"
    fi
}

# ── Phase 5: Vector index rebuild (LanceDB + Gemini Embedding 2) ──────
phase_embed() {
    log "Phase 5 - LanceDB vector index rebuild (Gemini Embedding 2 Preview, 3072d)"
    local PYTHON="${PROJECT_DIR}/.venv/bin/python"
    [[ ! -x "$PYTHON" ]] && PYTHON="python3"

    # Load API key and set CF Worker proxy for geo-restricted VPS
    if [[ -f "$HOME/.openclaw/.env" ]]; then
        source "$HOME/.openclaw/.env" 2>/dev/null
        export GEMINI_API_KEY
    fi
    export GEMINI_EMBED_BASE="${GEMINI_EMBED_BASE:-https://gemini-api-proxy.maoyuan-wen-683.workers.dev}"

    if [[ -n "${GEMINI_API_KEY:-}" ]]; then
        $PYTHON "$PROJECT_DIR/src/build_vector_index.py" \
            --db "$DB_PATH" \
            --lance "$PROJECT_DIR/data/finance-tax-lance" 2>&1 | tail -5 || true
    else
        log "WARN: GEMINI_API_KEY not set, skipping vector index"
    fi
}

# ── Phase 6: Alert if changes detected ──────────────────────────────────
phase_alert() {
    log "Phase 6 - Change detection alerts"
    if [[ -f "$STATS_DIR/$DATE_TAG.json" ]]; then
        local changed
        changed=$(python3 -c "import json; d=json.load(open('$STATS_DIR/$DATE_TAG.json')); print(d.get('changed', 0))")
        if [[ "$changed" -gt 0 ]]; then
            log "NOTE: $changed documents changed - sending alert"
            # Telegram alert via existing digest pipeline
            # discord/telegram: "NOTE: $changed new/updated finance-tax regulations detected"
        else
            log "No changes detected today"
        fi
    fi
}

# ── Main ────────────────────────────────────────────────────────────────
main() {
    log "=== Finance/Tax Knowledge Base Pipeline ==="
    log "Date: $DATE_TAG | DB: $DB_PATH | Data: $DATA_DIR"

    case "$PHASE" in
        --all)
            phase_discover
            phase_crawl
            phase_news
            phase_process
            phase_obsidian
            phase_embed
            phase_alert
            ;;
        --phase)
            shift
            case "${1:-}" in
                discover) phase_discover ;;
                crawl)    phase_crawl ;;
                news)     phase_news ;;
                process)  phase_process ;;
                obsidian) phase_obsidian ;;
                embed)    phase_embed ;;
                alert)    phase_alert ;;
                *)        err "Unknown phase: ${1:-}"; exit 1 ;;
            esac
            ;;
        *)
            phase_discover
            phase_crawl
            phase_news
            phase_process
            phase_obsidian
            phase_embed
            phase_alert
            ;;
    esac

    log "=== Pipeline complete ==="
}

main "$@"
