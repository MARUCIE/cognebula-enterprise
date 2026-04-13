#!/bin/bash
# clause_split_loop.sh — External restart loop for split_clauses_v2.py
# Restarts the Python process every N regs to release C++ heap memory.
# The Python script's resume mechanism (existing_regs check) handles continuity.
#
# Usage: bash scripts/clause_split_loop.sh
set -euo pipefail

cd /home/kg/cognebula-enterprise
VENV="/home/kg/kg-env/bin/python3 -u"
LOG="/tmp/clause_split_loop.log"
MAX_PER_RUN=1000  # Exit and restart after this many processed regs

echo "================================================================" | tee -a "$LOG"
echo "  Clause Split Loop — $(date)" | tee -a "$LOG"
echo "  Max per run: $MAX_PER_RUN" | tee -a "$LOG"
echo "================================================================" | tee -a "$LOG"

run=0
while true; do
    run=$((run + 1))

    # Check how many regs are already split
    before=$($VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph', read_only=True)
conn = kuzu.Connection(db)
r = conn.execute('MATCH (c:RegulationClause) RETURN DISTINCT c.regulationId')
c = 0
while r.has_next(): r.get_next(); c += 1
print(c)
del conn, db
" 2>/dev/null || echo "0")

    echo "[Run $run] Start — $before regs already split — $(date)" | tee -a "$LOG"

    # Run the splitter with max-processed limit
    $VENV src/split_clauses_v2.py \
        --batch-size 200 \
        --checkpoint-every 50 \
        --recycle-every 9999 \
        --max-processed "$MAX_PER_RUN" 2>&1 | tee -a "$LOG"

    rc=${PIPESTATUS[0]}

    # Check how many regs are now split
    after=$($VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph', read_only=True)
conn = kuzu.Connection(db)
r = conn.execute('MATCH (c:RegulationClause) RETURN DISTINCT c.regulationId')
c = 0
while r.has_next(): r.get_next(); c += 1
n = conn.execute('MATCH (n) RETURN count(n)').get_next()[0]
print(f'{c} {n}')
del conn, db
" 2>/dev/null || echo "0 0")

    regs_now=$(echo "$after" | cut -d' ' -f1)
    nodes_now=$(echo "$after" | cut -d' ' -f2)
    new_regs=$((regs_now - before))

    echo "[Run $run] Done — regs: $before→$regs_now (+$new_regs) — nodes: $nodes_now — exit=$rc — $(date)" | tee -a "$LOG"

    # If no new regs were processed, we're done
    if [[ "$new_regs" -le 0 ]]; then
        echo "No more regulations to process. DONE." | tee -a "$LOG"
        break
    fi

    # Brief pause to let OS reclaim memory
    sleep 3
    echo "[Run $((run + 1))] Memory before restart: $(free -m | awk '/Mem/{printf "%dMB/%dMB", $3, $2}')" | tee -a "$LOG"
done

echo "================================================================" | tee -a "$LOG"
echo "  Clause Split Loop COMPLETE — $(date)" | tee -a "$LOG"

# Final stats
$VENV -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph', read_only=True)
conn = kuzu.Connection(db)
n = conn.execute('MATCH (n) RETURN count(n)').get_next()[0]
e = conn.execute('MATCH ()-[e]->() RETURN count(e)').get_next()[0]
rc = conn.execute('MATCH (c:RegulationClause) RETURN count(c)').get_next()[0]
print(f'  Final: {n:,} nodes / {e:,} edges / {rc:,} RegulationClause')
del conn, db
" 2>&1 | tee -a "$LOG"

echo "================================================================" | tee -a "$LOG"
