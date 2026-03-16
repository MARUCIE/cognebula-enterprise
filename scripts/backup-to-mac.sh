#!/bin/bash
# Backup cognebula-enterprise data from VPS to Mac
# Usage: ./scripts/backup-to-mac.sh [--full|--code|--data]
#
# L1: Code + docs -> rsync + git push to GitHub
# L2: KuzuDB CSV export -> rsync to Mac
# L3: Full data/ tar.gz -> rsync to Mac
#
# Runs from Mac side. Requires Tailscale VPN.

set -euo pipefail

VPS="root@100.106.223.39"
SSH_KEY="$HOME/.ssh/id_ed25519_vps"
SSH="ssh -i $SSH_KEY $VPS"
SCP="scp -i $SSH_KEY"
RSYNC="rsync -avz -e 'ssh -i $SSH_KEY'"

VPS_DIR="/root/Projects/cognebula-enterprise"
LOCAL_BACKUP="$HOME/Projects/cognebula-enterprise-backup"
LOCAL_DATA_BACKUP="$LOCAL_BACKUP/data-snapshots"
DATE=$(date +%Y-%m-%d)

MODE="${1:-code}"

echo "=== CogNebula Backup ($MODE) -- $DATE ==="

# L1: Code backup (always)
echo ""
echo "--- L1: Code rsync + GitHub push ---"
rsync -avz --exclude='data/' --exclude='.venv/' --exclude='__pycache__/' \
    --exclude='node_modules/' --exclude='.git/' \
    -e "ssh -i $SSH_KEY" \
    "$VPS:$VPS_DIR/" "$LOCAL_BACKUP/" 2>&1 | tail -5

cd "$LOCAL_BACKUP"
git add -A
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "backup: $DATE -- auto-sync from VPS"
    git push origin main
    echo "OK: Code pushed to GitHub"
else
    echo "OK: Code unchanged, skip push"
fi

if [ "$MODE" = "code" ]; then
    echo "Done (code only)"
    exit 0
fi

# L2: KuzuDB CSV export
if [ "$MODE" = "data" ] || [ "$MODE" = "--data" ] || [ "$MODE" = "full" ] || [ "$MODE" = "--full" ]; then
    echo ""
    echo "--- L2: KuzuDB CSV export ---"
    mkdir -p "$LOCAL_DATA_BACKUP"

    # Export all node tables to CSV on VPS
    $SSH "cd $VPS_DIR && .venv/bin/python3 -c \"
import kuzu, csv, os
db = kuzu.Database('data/finance-tax-graph')
conn = kuzu.Connection(db)
export_dir = '/tmp/kuzu-export-$DATE'
os.makedirs(export_dir, exist_ok=True)

# Get all node tables
result = conn.execute('CALL show_tables() RETURN *')
tables = []
while result.has_next():
    row = result.get_next()
    if str(row[1]).upper() in ('NODE', 'NODE_TABLE'):
        tables.append(str(row[0]))

for tbl in tables:
    try:
        r = conn.execute(f'MATCH (n:{tbl}) RETURN n.*')
        rows = []
        while r.has_next():
            rows.append(r.get_next())
        if rows:
            with open(f'{export_dir}/{tbl}.csv', 'w', newline='') as f:
                w = csv.writer(f)
                w.writerows(rows)
            print(f'  {tbl}: {len(rows)} rows')
    except Exception as e:
        print(f'  {tbl}: SKIP ({e})')

print(f'Export dir: {export_dir}')
print(f'Tables exported: {len([t for t in tables])}')
\"" 2>&1

    # rsync CSV export to Mac
    rsync -avz -e "ssh -i $SSH_KEY" \
        "$VPS:/tmp/kuzu-export-$DATE/" \
        "$LOCAL_DATA_BACKUP/$DATE-csv/" 2>&1 | tail -5
    echo "OK: CSV export synced to $LOCAL_DATA_BACKUP/$DATE-csv/"
fi

# L3: Full data tar.gz (weekly)
if [ "$MODE" = "full" ] || [ "$MODE" = "--full" ]; then
    echo ""
    echo "--- L3: Full data tar.gz ---"
    $SSH "cd $VPS_DIR && tar czf /tmp/cognebula-data-$DATE.tar.gz \
        --exclude='data/finance-tax-lance' \
        data/" 2>&1
    rsync -avz -e "ssh -i $SSH_KEY" \
        "$VPS:/tmp/cognebula-data-$DATE.tar.gz" \
        "$LOCAL_DATA_BACKUP/" 2>&1 | tail -3
    echo "OK: Full data backup at $LOCAL_DATA_BACKUP/cognebula-data-$DATE.tar.gz"
fi

echo ""
echo "=== Backup complete ($MODE) ==="
echo "  L1 Code: $LOCAL_BACKUP (GitHub: MARUCIE/cognebula-enterprise)"
echo "  L2 CSV:  $LOCAL_DATA_BACKUP/$DATE-csv/"
[ "$MODE" = "full" ] && echo "  L3 Full: $LOCAL_DATA_BACKUP/cognebula-data-$DATE.tar.gz"
