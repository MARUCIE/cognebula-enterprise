#!/bin/bash
# AI Synthesis continuous production pipeline
# Generates nodes through Multi-Swarm QC for all industries
# Usage: ./scripts/ai-synthesis-batch.sh [--count-per-industry N] [--dry-run]
#
# Default: 20 nodes per industry, 7 industries = 140 candidates
# At 49% acceptance rate = ~69 accepted nodes per run
# Run daily via cron for continuous production

set -euo pipefail
cd "$(dirname "$0")/.."

COUNT="${1:-20}"
DRY_RUN=""
if [[ "${2:-}" == "--dry-run" ]] || [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
    COUNT="${2:-20}"
fi

# Load API key
GEMINI_API_KEY=$(grep GEMINI_API_KEY ~/.openclaw/.env 2>/dev/null | head -1 | cut -d= -f2)
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY not found"
    exit 1
fi
export GEMINI_API_KEY

INDUSTRIES="manufacturing construction real_estate software hr_services medical_aesthetics live_streaming"
TOTAL_ACCEPT=0
TOTAL_REJECT=0
TOTAL_REVIEW=0

echo "=== AI Synthesis Batch $(date +%Y-%m-%d) ==="
echo "Count per industry: $COUNT | Industries: 7 | Dry run: ${DRY_RUN:-no}"

for IND in $INDUSTRIES; do
    echo ""
    echo "--- $IND ($COUNT nodes) ---"
    RESULT=$(.venv/bin/python3 -m src.ai_synthesis.generate_batch --industry "$IND" --count "$COUNT" $DRY_RUN 2>&1 | tail -1)
    echo "$RESULT"

    # Parse acceptance from JSON output
    ACCEPT=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('auto_inject',0))" 2>/dev/null || echo 0)
    REJECT=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reject',0))" 2>/dev/null || echo 0)
    REVIEW=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('human_review',0))" 2>/dev/null || echo 0)

    TOTAL_ACCEPT=$((TOTAL_ACCEPT + ACCEPT))
    TOTAL_REJECT=$((TOTAL_REJECT + REJECT))
    TOTAL_REVIEW=$((TOTAL_REVIEW + REVIEW))
done

echo ""
echo "=== Batch Summary ==="
echo "Total candidates: $((COUNT * 7))"
echo "Auto-inject: $TOTAL_ACCEPT"
echo "Human review: $TOTAL_REVIEW"
echo "Rejected: $TOTAL_REJECT"
echo "Acceptance rate: $(python3 -c "print(f'{$TOTAL_ACCEPT/max($TOTAL_ACCEPT+$TOTAL_REJECT+$TOTAL_REVIEW,1)*100:.0f}%')")"
echo "=== Done $(date) ==="
