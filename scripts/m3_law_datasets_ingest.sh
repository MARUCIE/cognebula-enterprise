#!/bin/bash
# Ingest law-datasets after m3_continue finishes.
# Waits for STARD + edge boost to complete, then ingests 509 tax laws.
# Run: nohup bash scripts/m3_law_datasets_ingest.sh > /tmp/law_datasets_ingest.log 2>&1 &
set -euo pipefail
cd /home/kg/cognebula-enterprise

VENV="/home/kg/kg-env/bin/python3 -u"

echo "================================================================"
echo "  Law-Datasets Ingest — $(date)"
echo "================================================================"

# Wait for m3_continue's expansion matrix to start (it's the last step)
echo "[0] Waiting for m3_continue pipeline to finish STARD + edges..."
while pgrep -f "[m]3_continue" >/dev/null 2>&1; do
    echo "  m3_continue still running (checking every 30s)"
    sleep 30
done
echo "  m3_continue finished!"

# Check if API is stopped (matrix expansion should be running)
if ! systemctl is-active --quiet kg-api; then
    echo "[1] API is stopped (expected: matrix expansion running). Ingesting..."
    $VENV scripts/ingest_law_datasets.py --ingest 2>&1
    echo "  Done!"
else
    echo "[1] API is running. Stopping for ingest..."
    sudo systemctl stop kg-api
    sleep 3
    $VENV scripts/ingest_law_datasets.py --ingest 2>&1
    sudo systemctl start kg-api
    echo "  Done + API restarted!"
fi

echo "================================================================"
echo "  Law-Datasets Ingest DONE — $(date)"
echo "================================================================"
