#!/bin/bash
# Wait for flk_fast_scan to finish, then run Phase A2 (metadata + content push)
set -e
cd "$(dirname "$0")/.."

echo "$(date +%H:%M:%S) Waiting for flk_fast_scan to finish..."
while pgrep -f flk_fast_scan > /dev/null 2>&1; do
    COUNT=$(wc -l < data/recrawl/flk_details.jsonl 2>/dev/null || echo 0)
    echo "$(date +%H:%M:%S) scan: $COUNT/2901"
    sleep 60
done

COUNT=$(wc -l < data/recrawl/flk_details.jsonl 2>/dev/null || echo 0)
echo "$(date +%H:%M:%S) Scan complete: $COUNT items"

# Phase A1: Metadata enrichment for all items
echo "$(date +%H:%M:%S) Running metadata enrichment..."
python3 scripts/flk_content_ingest.py --host 100.88.170.57

# Phase A2: Content fetch + push for items with content
echo "$(date +%H:%M:%S) Running content fetch + push..."
.venv/bin/python3 scripts/flk_content_fetch_and_push.py --kg-host 100.88.170.57

echo "$(date +%H:%M:%S) All done!"
