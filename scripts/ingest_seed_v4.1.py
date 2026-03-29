#!/usr/bin/env python3
"""Ingest v4.1 seed data into KG via API.

Usage:
    python3 scripts/ingest_seed_v4.1.py              # Ingest all seed files
    python3 scripts/ingest_seed_v4.1.py --table TaxAccountingGap  # Specific table
    python3 scripts/ingest_seed_v4.1.py --dry-run     # Show what would be ingested
"""
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

KG_API = "http://100.75.77.112:8400"
DATA_DIR = Path(__file__).parent.parent / "data"
DRY_RUN = "--dry-run" in sys.argv
TABLE_FILTER = None
for i, a in enumerate(sys.argv):
    if a == "--table" and i + 1 < len(sys.argv):
        TABLE_FILTER = sys.argv[i + 1]

# Seed file → target table mapping
SEED_FILES = {
    "seed_tax_accounting_gap.json": "TaxAccountingGap",
    "seed_social_insurance.json": "SocialInsuranceRule",
    "seed_invoice_rules.json": "InvoiceRule",
    "seed_industry_benchmarks.json": "IndustryBenchmark",
}


def ingest_batch(table: str, records: list) -> dict:
    """Ingest records into a table via execute-ddl CREATE statements."""
    inserted = 0
    errors = 0
    error_samples = []

    for rec in records:
        # Build parameterized CREATE
        fields = list(rec.keys())
        props_parts = []
        for f in fields:
            val = rec[f]
            if isinstance(val, (int, float)):
                props_parts.append(f"{f}: {val}")
            else:
                # Escape single quotes in string values
                safe_val = str(val).replace("'", "\\'")
                props_parts.append(f"{f}: '{safe_val}'")

        stmt = f"CREATE (:{table} {{{', '.join(props_parts)}}})"

        payload = json.dumps({"statements": [stmt]}).encode()
        req = urllib.request.Request(
            f"{KG_API}/api/v1/admin/execute-ddl",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                r = json.loads(resp.read())
                if r.get("ok", 0) > 0:
                    inserted += 1
                elif r.get("skipped", 0) > 0:
                    pass  # Duplicate, skip silently
                else:
                    errors += 1
                    if len(error_samples) < 3:
                        error_samples.append(r.get("results", [{}])[0].get("reason", "unknown")[:100])
        except Exception as e:
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(str(e)[:100])

    return {"inserted": inserted, "errors": errors, "error_samples": error_samples}


def main():
    print(f"\n{'='*60}")
    print(f"  CogNebula v4.1 Seed Data Ingest")
    print(f"  API: {KG_API}")
    print(f"  Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    total_inserted = 0
    total_errors = 0

    for filename, table in SEED_FILES.items():
        if TABLE_FILTER and table != TABLE_FILTER:
            continue

        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} (file not found)")
            continue

        with open(filepath) as f:
            records = json.load(f)

        print(f"  {table}: {len(records)} records from {filename}")

        if DRY_RUN:
            print(f"    [DRY RUN] Would ingest {len(records)} records")
            if records:
                print(f"    Sample fields: {list(records[0].keys())}")
            continue

        t0 = time.time()
        result = ingest_batch(table, records)
        elapsed = time.time() - t0

        ins = result["inserted"]
        err = result["errors"]
        total_inserted += ins
        total_errors += err

        status = "OK" if err == 0 else "WARN"
        print(f"    {status}: +{ins} inserted, {err} errors, {elapsed:.1f}s")
        if result["error_samples"]:
            for e in result["error_samples"]:
                print(f"    ERR: {e}")

    print(f"\n{'='*60}")
    print(f"  INGEST COMPLETE: +{total_inserted} inserted, {total_errors} errors")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
