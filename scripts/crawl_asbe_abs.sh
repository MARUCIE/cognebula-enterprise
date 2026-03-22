#!/bin/bash
# Crawl ASBE standards using agent-browser-session (anti-detection, system Chrome)
# Output: data/asbe/asbe_abs.jsonl (one JSON per line)
set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="data/asbe"
OUT_FILE="$OUT_DIR/asbe_abs.jsonl"
mkdir -p "$OUT_DIR"
> "$OUT_FILE"  # Clear

ABS="agent-browser-session"
BASE="https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/"

echo "=== ASBE Crawler (agent-browser-session) ==="
echo "Phase 1: Collecting standard links from 5 pages..."

# Collect all links from paginated listing
LINKS_FILE=$(mktemp)
for page in "" "index_1.htm" "index_2.htm" "index_3.htm" "index_4.htm"; do
    URL="${BASE}${page}"
    echo "  Page: $URL"
    $ABS open "$URL" 2>/dev/null || continue
    sleep 2

    # Extract links containing 准则 and 号
    $ABS snapshot 2>/dev/null | grep -oP 'link "企业会计准则[^"]*"' | \
        sed 's/link "//; s/"//' >> "$LINKS_FILE" || true
    sleep 1
done

# Deduplicate titles
sort -u "$LINKS_FILE" > "${LINKS_FILE}.dedup"
TOTAL=$(wc -l < "${LINKS_FILE}.dedup")
echo "Found $TOTAL unique standard titles"

# Phase 2: Click each link and extract full text
echo ""
echo "Phase 2: Fetching full text for each standard..."
IDX=0

while IFS= read -r TITLE; do
    IDX=$((IDX + 1))
    [ -z "$TITLE" ] && continue

    # Extract CAS number
    CAS_NUM=$(echo "$TITLE" | grep -oP '第\K\d+' || echo "0")

    # Navigate to listing page that contains this standard
    if [ "$CAS_NUM" -le 9 ] || [ "$CAS_NUM" -eq 0 ]; then
        PAGE_URL="${BASE}"
    elif [ "$CAS_NUM" -le 19 ]; then
        PAGE_URL="${BASE}index_1.htm"
    elif [ "$CAS_NUM" -le 29 ]; then
        PAGE_URL="${BASE}index_2.htm"
    elif [ "$CAS_NUM" -le 39 ]; then
        PAGE_URL="${BASE}index_3.htm"
    else
        PAGE_URL="${BASE}index_4.htm"
    fi

    # Open listing page and click the standard link
    $ABS open "$PAGE_URL" 2>/dev/null || continue
    sleep 2
    $ABS find text "$TITLE" click 2>/dev/null || continue
    sleep 3

    # Extract page content
    CONTENT=$($ABS snapshot 2>/dev/null | sed '1,/^$/d' | head -500 || echo "")
    CONTENT_LEN=${#CONTENT}

    if [ "$CONTENT_LEN" -gt 500 ]; then
        STATUS="OK"
    elif [ "$CONTENT_LEN" -gt 100 ]; then
        STATUS="SHORT"
    else
        STATUS="FAIL"
    fi

    echo "  [$IDX/$TOTAL] $STATUS ${TITLE:0:40} (${CONTENT_LEN}c)"

    # Write JSONL
    python3 -c "
import json, sys
print(json.dumps({
    'title': sys.argv[1],
    'cas_number': int(sys.argv[2]),
    'content': sys.argv[3],
    'content_length': int(sys.argv[4]),
}, ensure_ascii=False))
" "$TITLE" "$CAS_NUM" "$CONTENT" "$CONTENT_LEN" >> "$OUT_FILE"

done < "${LINKS_FILE}.dedup"

rm -f "$LINKS_FILE" "${LINKS_FILE}.dedup"

GOOD=$(grep -c '"content_length": [5-9][0-9][0-9]\|"content_length": [0-9][0-9][0-9][0-9]' "$OUT_FILE" || echo "0")
echo ""
echo "=== Results ==="
echo "Total: $(wc -l < "$OUT_FILE") standards"
echo "Saved to $OUT_FILE"
echo "Done!"
