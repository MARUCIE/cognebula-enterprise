#!/usr/bin/env bash
# finance-tax-knowledge-pipeline.sh -- 4-Stage Knowledge Accumulation Pipeline
# Crawl → Digest → Obsidian → CF Pages
# Registered as pipeline: finance-tax-knowledge-pipeline (65th)
#
# Usage:
#   bash scripts/finance-tax-knowledge-pipeline.sh              # full pipeline
#   bash scripts/finance-tax-knowledge-pipeline.sh --stage 2    # only digest
#   bash scripts/finance-tax-knowledge-pipeline.sh --stage 3    # only obsidian sync
#   bash scripts/finance-tax-knowledge-pipeline.sh --stage 4    # only publish

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VAULT_DIR="${VAULT_DIR:-$HOME/Obsidian/财税知识库}"
AI_FLEET_DIR="${AI_FLEET_DIR:-$HOME/00-AI-Fleet}"
DATE_TAG=$(date +%Y-%m-%d)
DATA_DIR="$PROJECT_DIR/data/raw/$DATE_TAG"
DB_PATH="$PROJECT_DIR/data/finance-tax-graph"
STATS_DIR="$PROJECT_DIR/data/stats"
STAGE="${2:-all}"

mkdir -p "$DATA_DIR" "$STATS_DIR"

log() { echo "$(date +%H:%M:%S) NOTE: $*"; }
err() { echo "$(date +%H:%M:%S) ERROR: $*" >&2; }

# ── Stage 1: Crawl (reuses finance-tax-crawl.sh) ───────────────────────
stage_crawl() {
    log "Stage 1/4 - CRAWL: Invoking finance-tax-crawl.sh"
    if [[ -x "$SCRIPT_DIR/finance-tax-crawl.sh" ]]; then
        bash "$SCRIPT_DIR/finance-tax-crawl.sh"
    else
        err "finance-tax-crawl.sh not found or not executable"
        return 1
    fi
    log "Stage 1 complete: raw data in $DATA_DIR"
}

# ── Stage 2: Digest (NER + KuzuDB + Embeddings) ────────────────────────
stage_digest() {
    log "Stage 2/4 - DIGEST: NER + KuzuDB ingest + Embeddings"

    # 2a: Process JSON → KuzuDB nodes
    python3 "$PROJECT_DIR/src/finance_tax_processor.py" \
        --input "$DATA_DIR" \
        --db "$DB_PATH" \
        --stats-output "$STATS_DIR/$DATE_TAG.json"

    # 2b: Generate embeddings (if bin/embed available)
    if [[ -x "$AI_FLEET_DIR/bin/embed" ]]; then
        python3 "$PROJECT_DIR/src/embed_finance_tax.py" --db "$DB_PATH" 2>/dev/null || true
    fi

    log "Stage 2 complete: KuzuDB updated, stats at $STATS_DIR/$DATE_TAG.json"
}

# ── Stage 3: Obsidian Vault Sync ────────────────────────────────────────
stage_obsidian() {
    log "Stage 3/4 - OBSIDIAN: JSON → Obsidian markdown"

    python3 "$PROJECT_DIR/src/json_to_obsidian.py" \
        --input "$DATA_DIR" \
        --vault "$VAULT_DIR"

    # Git commit if vault is a git repo
    if [[ -d "$VAULT_DIR/.git" ]]; then
        cd "$VAULT_DIR"
        git add -A
        git diff --cached --quiet || git commit -m "auto: finance-tax update $DATE_TAG" --no-verify 2>/dev/null || true
        cd "$PROJECT_DIR"
    fi

    local md_count
    md_count=$(find "$VAULT_DIR" -name "*.md" -type f | wc -l | tr -d ' ')
    log "Stage 3 complete: $md_count markdown files in vault"
}

# ── Stage 4: Publish to CF Pages ────────────────────────────────────────
stage_publish() {
    log "Stage 4/4 - PUBLISH: Export vault → CF Pages deploy"

    # Check if dashboard sync is available
    local DASHBOARD_DIR="$AI_FLEET_DIR/dashboard"
    local FINANCE_DIR="$DASHBOARD_DIR/public/finance-tax"

    if [[ -d "$DASHBOARD_DIR" ]]; then
        mkdir -p "$FINANCE_DIR"

        # Copy latest daily summary to dashboard
        if [[ -f "$STATS_DIR/$DATE_TAG.json" ]]; then
            cp "$STATS_DIR/$DATE_TAG.json" "$FINANCE_DIR/latest-stats.json"
        fi

        # Generate index page from vault structure
        python3 -c "
import json
from pathlib import Path
from datetime import datetime

vault = Path('$VAULT_DIR')
md_files = sorted(vault.rglob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)

index = {
    'generated': datetime.now().isoformat(),
    'total_files': len(md_files),
    'latest': [{'path': str(f.relative_to(vault)), 'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()} for f in md_files[:20]],
    'by_directory': {}
}
for f in md_files:
    d = str(f.parent.relative_to(vault))
    index['by_directory'].setdefault(d, 0)
    index['by_directory'][d] += 1

Path('$FINANCE_DIR/index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2))
print(f'OK: Index generated: {len(md_files)} files')
" 2>/dev/null || true

        # Trigger dashboard rebuild (if LaunchAgent watches this path)
        touch "$FINANCE_DIR/.trigger-rebuild" 2>/dev/null || true

        log "Stage 4 complete: CF Pages finance-tax index updated"
    else
        log "WARN: Dashboard dir not found at $DASHBOARD_DIR, skipping publish"
    fi
}

# ── Main ────────────────────────────────────────────────────────────────
main() {
    log "=== Finance/Tax Knowledge Pipeline (4-Stage) ==="
    log "Date: $DATE_TAG | Vault: $VAULT_DIR | DB: $DB_PATH"

    case "${1:-}" in
        --stage)
            case "$STAGE" in
                1|crawl)    stage_crawl ;;
                2|digest)   stage_digest ;;
                3|obsidian) stage_obsidian ;;
                4|publish)  stage_publish ;;
                *)          err "Unknown stage: $STAGE"; exit 1 ;;
            esac
            ;;
        *)
            stage_crawl
            stage_digest
            stage_obsidian
            stage_publish
            ;;
    esac

    log "=== Knowledge Pipeline complete ==="
}

main "$@"
