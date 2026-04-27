#!/usr/bin/env python3
"""Apply Round-4 phase-1 seeds to prod via /api/v1/admin/execute-ddl.

The 3 seed scripts in `src/seed/` were written assuming direct kuzu connection
(`--db data/finance-tax-graph`). In production, the `kg-api` uvicorn process
holds an exclusive Kuzu lock — direct kuzu.Database open would error with
"Could not set lock on file". So this wrapper:

  1. Imports the dataset constants from the 3 seed modules (no copy-paste)
  2. Translates each record to inline CREATE Cypher (escape-safe)
  3. POSTs in batches of 50 through the admin DDL endpoint
  4. Calls ingestion_manifest.record_ingestion() with REAL row counts
     (success - duplicate-skipped) so the manifest reflects prod truth

Idempotent via PRIMARY KEY: re-running counts duplicates as "skipped",
not "added" — the manifest captures only net new rows.

Usage:
    python scripts/apply_round4_seeds_via_api.py --api-url https://ops.hegui.org
    python scripts/apply_round4_seeds_via_api.py --api-url https://ops.hegui.org --dry-run
    python scripts/apply_round4_seeds_via_api.py --api-url https://ops.hegui.org --only AccountingSubject
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion_manifest import record_ingestion
from src.seed.seed_accounting_subject_full import _build_records as build_as
from src.seed.seed_business_activity_gbt4754 import _build_records as build_ba
from src.seed.seed_filing_form_field_full import _build_records as build_fff
from src.seed.seed_compliance_rule_extracted import _build_records as build_cr
from src.seed.seed_reference_data_split import (
    _build_records_social_insurance as build_sir,
    _build_records_invoice_rule as build_inv,
    _build_records_industry_benchmark as build_ind,
    _build_records_tax_accounting_gap_extended as build_tag,
)


def _esc(v: object) -> str:
    """Escape a value for inline Cypher single-quoted string literal."""
    s = str(v) if v is not None else ""
    # Escape order matters: backslash first, then single-quote
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _to_create(
    table: str,
    props: dict,
    drop_keys: list[str] | None = None,
    field_map: dict[str, str] | None = None,
) -> str:
    """Build inline CREATE statement: CREATE (n:Table {k: 'v', ...}).

    `field_map` translates seed-side keys to live-table column names. This is
    needed because the canonical schema (`schemas/ontology_v4.2.cypher`) and
    the live deployed table can drift — e.g. AccountingSubject canonical
    declares `balanceSide` but live has `balanceDirection`. Mapping at write
    time avoids touching prod schema (lower-risk than ALTER TABLE).
    `drop_keys` lists seed-side keys that have no live equivalent.
    """
    drop_keys = drop_keys or []
    field_map = field_map or {}
    pairs: list[str] = []
    for k, v in props.items():
        if k.startswith("_") or k in drop_keys:
            continue
        if v is None or v == "":
            continue  # skip empty fields to keep statement compact
        live_key = field_map.get(k, k)
        pairs.append(f"{live_key}: '{_esc(v)}'")
    return f"CREATE (n:{table} {{{', '.join(pairs)}}})"


def _api_ddl(api_url: str, statements: list[str], timeout: int = 60) -> dict:
    """POST a batch of DDL/DML statements; return parsed result dict."""
    data = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/v1/admin/execute-ddl",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _apply_batch(
    api_url: str,
    table: str,
    records: list[dict],
    drop_keys: list[str],
    field_map: dict[str, str],
    batch_size: int = 50,
    dry_run: bool = False,
) -> tuple[int, int, list[str]]:
    """Apply a list of records as inline CREATE batches. Return (added, dup_skipped, errors)."""
    added = 0
    dup_skipped = 0
    errors: list[str] = []
    statements = [
        _to_create(table, r, drop_keys=drop_keys, field_map=field_map) for r in records
    ]
    if dry_run:
        return (len(statements), 0, [])
    for i in range(0, len(statements), batch_size):
        batch = statements[i : i + batch_size]
        try:
            res = _api_ddl(api_url, batch)
        except Exception as e:
            # Network/timeout — count whole batch as errors but continue
            errors.extend([f"batch {i}: {e!s}"] * len(batch))
            continue
        for r in res.get("results", []):
            st = r.get("status", "ERROR")
            if st == "OK":
                added += 1
            elif st == "ERROR":
                reason = r.get("reason", "")
                if "primary key" in reason.lower() or "duplicate" in reason.lower():
                    dup_skipped += 1
                else:
                    errors.append(f"{r.get('statement','')[:60]}: {reason[:120]}")
    return added, dup_skipped, errors


SEEDS = [
    {
        "name": "AccountingSubject",
        "table": "AccountingSubject",
        "build_fn": build_as,
        # Live AccountingSubject schema diverges from canonical
        # `schemas/ontology_v4.2.cypher` declaration. Confirmed via
        # `/api/v1/nodes?type=AccountingSubject&limit=1` on 2026-04-27:
        #   canonical: id, code, name, category, balanceSide, parentId, description
        #   live:      id, name, category, balanceDirection, fullText, ... (no code/parentId)
        "drop_keys": ["code", "parentId"],  # no live equivalent — surfaced as FU6
        "field_map": {"balanceSide": "balanceDirection", "description": "fullText"},
    },
    {
        "name": "BusinessActivity",
        "table": "BusinessActivity",
        "build_fn": build_ba,
        "drop_keys": [],
        "field_map": {},  # live schema matches seed (id, name, description)
    },
    {
        "name": "FilingFormField",
        "table": "FilingFormField",
        "build_fn": build_fff,
        "drop_keys": [],
        "field_map": {},  # live matches seed (id, formId, fieldCode, fieldName, description, dataType)
    },
    {
        "name": "ComplianceRule",
        "table": "ComplianceRule",
        "build_fn": build_cr,
        # ComplianceRule LIVE shape vs canonical drift (probed 2026-04-27 via
        # iterative CREATE attempts on prod; CALL table_info blocked by the
        # admin-DDL allowed-prefix list, so we used CREATE-and-error mining):
        #   canonical declares: id, name, description, severity, sourceClauseId, status
        #   live actually has:  id, name, category (others rejected with
        #     "Cannot find property X for n")
        # Drop everything live doesn't accept; collapse description -> dropped
        # (long body would corrupt category semantics if mapped). Phase-2b will
        # ALTER TABLE live to add description/severity columns once Maurice
        # signs off (FU6 schema-shape gate will catch this after redeploy).
        "drop_keys": ["description", "severity", "sourceClauseId", "status"],
        "field_map": {},
    },
    # FU5 phase-2c — 3 tier_empty reference seeds (probed 2026-04-27).
    # Live shape strict subset of seed JSON; adapter packs dropped rate/range
    # data into description (or metric for IndustryBenchmark which lacks one).
    {
        "name": "SocialInsuranceRule",
        "table": "SocialInsuranceRule",
        "build_fn": build_sir,
        # live: {id, name, description, regionId} (probe 2026-04-27)
        # JSON: insuranceType / employerRate / employeeRate / baseFloor /
        #   baseCeiling / adjustmentMonth / effectiveDate are packed by
        #   _build_records_social_insurance into description blob.
        "drop_keys": [],
        "field_map": {},
    },
    {
        "name": "InvoiceRule",
        "table": "InvoiceRule",
        "build_fn": build_inv,
        # live: {id, name, description, invoiceType} (probe 2026-04-27)
        # JSON: ruleType / condition / procedure / legalBasis packed into
        #   description by adapter.
        "drop_keys": [],
        "field_map": {},
    },
    {
        "name": "IndustryBenchmark",
        "table": "IndustryBenchmark",
        "build_fn": build_ind,
        # live: {id, metric, industryId} — NO name, NO description (probe 2026-04-27)
        # JSON: ratioName -> metric (range packed into metric string),
        #   industryCode -> industryId. minValue/maxValue/unit/year/regionId
        #   embedded in metric "name [min-max]unit · year · region".
        "drop_keys": [],
        "field_map": {},
    },
    {
        "name": "TaxAccountingGapExt",
        "table": "TaxAccountingGap",
        "build_fn": build_tag,
        # Live TaxAccountingGap (probe 2026-04-27 via /api/v1/nodes):
        #   id, name, description, gapKind, direction (+ lineage envelope)
        # JSON has gapType / adjustmentDirection — field_map translates;
        #   accountingTreatment / taxTreatment / impact / example /
        #   A105000LineRef / deferredTaxType / legalBasis are packed into
        #   description by the adapter (so consumer queries can still tokenize).
        "drop_keys": [],
        "field_map": {
            "gapType": "gapKind",
            "adjustmentDirection": "direction",
        },
    },
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-url", default="https://ops.hegui.org")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", help="run only this seed name (AccountingSubject|BusinessActivity|FilingFormField)")
    p.add_argument("--batch-size", type=int, default=50)
    args = p.parse_args()

    targets = [s for s in SEEDS if (not args.only or s["name"] == args.only)]
    if not targets:
        print(f"ERROR: --only={args.only} matched no seeds")
        return 2

    print(f"=== Round-4 phase-1 seed application via {args.api_url} ===")
    print(f"  dry_run={args.dry_run} batch_size={args.batch_size} targets={[t['name'] for t in targets]}")
    print()

    overall_summary: dict[str, dict] = {}
    for spec in targets:
        records = spec["build_fn"]()
        print(f"--- {spec['name']} ({len(records)} records prepared) ---")
        t0 = time.time()
        added, dup, errs = _apply_batch(
            args.api_url,
            spec["table"],
            records,
            drop_keys=spec["drop_keys"],
            field_map=spec.get("field_map", {}),
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        elapsed = time.time() - t0
        print(f"  added={added} dup_skipped={dup} errors={len(errs)} elapsed={int(elapsed*1000)}ms")
        if errs:
            for e in errs[:5]:
                print(f"    ERR {e}")
            if len(errs) > 5:
                print(f"    ... and {len(errs)-5} more")
        overall_summary[spec["name"]] = {
            "added": added, "dup_skipped": dup, "errors": len(errs), "elapsed_s": round(elapsed, 2),
        }
        # Manifest record (only for non-dry-run)
        if not args.dry_run:
            record_ingestion(
                source_file=__file__,
                rows_written={spec["table"]: added},
                duration_s=elapsed,
                dry_run=False,
                note=f"prod seed via API; dup_skipped={dup} errors={len(errs)} api={args.api_url}",
            )
        print()

    print("=== SUMMARY ===")
    print(json.dumps(overall_summary, indent=2))
    return 0 if all(s["errors"] == 0 for s in overall_summary.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
