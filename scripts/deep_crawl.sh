#!/bin/bash
# CogNebula Deep Crawl — Detail-page fetchers (long-running, 10-30 min each)
#
# These fetchers download individual article content (not just listings).
# Too slow for the daily pipeline; run separately via M3 orchestrator or cron.
#
# Cron: called from m3_orchestrator.sh Step 7, or standalone
# Manual: ./scripts/deep_crawl.sh [--fetcher fetch_12366]
set -uo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then set -a; source .env; set +a; fi

VENV="/home/kg/kg-env/bin/python3"
TODAY=$(date +%Y-%m-%d)
RAW_DIR="data/raw/$TODAY"
mkdir -p "$RAW_DIR"

# Deep fetchers with generous timeouts
DEEP_FETCHERS=(
    "fetch_12366:1800"          # 5,297 QA pairs, ~25 min
    "fetch_chinaacc:1800"       # 7,500 articles with --fetch-content, ~25 min
    "fetch_baike_kuaiji:1800"   # accounting encyclopedia, ~20 min
    "fetch_tax_cases:1800"      # tax court cases, ~25 min
)

# Optional: run only one specific fetcher
TARGET="${1:-}"
[[ "$TARGET" == "--fetcher" ]] && TARGET="${2:-}"

for entry in "${DEEP_FETCHERS[@]}"; do
    name="${entry%%:*}"
    tout="${entry##*:}"
    fetcher="src/fetchers/${name}.py"

    if [[ -n "$TARGET" && "$name" != "$TARGET" ]]; then
        continue
    fi

    if [[ ! -f "$fetcher" ]]; then
        echo "  SKIP: $fetcher not found"
        continue
    fi

    FLAGS=""
    [[ "$name" == "fetch_chinaacc" ]] && FLAGS="--fetch-content"

    echo "[$(date +%H:%M)] $name (timeout=${tout}s)..."
    timeout "$tout" $VENV "$fetcher" --output "$RAW_DIR" $FLAGS 2>&1 | tail -10 || echo "  WARN: $name timed out or failed"

    # Show result
    outfile=$(find "$RAW_DIR" -name "*.json" -newer "$RAW_DIR" -maxdepth 1 2>/dev/null | sort -t/ -k1 | tail -1)
    if [[ -n "$outfile" ]]; then
        size=$(stat -c %s "$outfile" 2>/dev/null || echo 0)
        echo "  → $(basename "$outfile"): ${size} bytes"
    fi
done

echo "[$(date +%H:%M)] Deep crawl complete"
