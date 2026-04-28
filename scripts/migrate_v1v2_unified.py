#!/usr/bin/env python3
"""migrate_v1v2_unified.py — additive V1+V2 lineage merge into _experimental_*_Unified tables.

Why this script exists
----------------------
B2 design proposes merging the 3 V1+V2 lineage pairs (ComplianceRule × V2,
FilingForm × V2, TaxIncentive × V2) plus the RiskIndicatorV2 orphan rename
into single canonical entities tagged with `_lineage_present STRING[]`.

This script does the ADDITIVE part of that migration:
  1. Create staging tables `_experimental_<Name>_Unified` (passes C5b gate
     because of the `_experimental_` namespace prefix).
  2. Populate them from V1 + V2 with the per-pair shape encoded in the
     readiness doc §1: pure-UNION for disjoint pairs, per-row-merge for
     the intersecting pair.

What this script does NOT do
----------------------------
  - It does NOT drop V1 or V2 source tables.
  - It does NOT rewire incident edges.
  - It does NOT rename the staging tables to canonical names.
  - It does NOT run the 7-day soak.

Those are cutover operations, run separately via `migrate_v1v2_cutover.py`
(to be authored when Maurice schedules the backup window) — and the cutover
is the only physically irreversible operation in this migration.

Because everything this script does is additive, it is safe to run during
business hours: failures leave the staging tables in a partial state, which
can be cleaned by dropping the `_experimental_*_Unified` tables.

Default mode
------------
DRY-RUN. Prints the full execution plan (DDL + INSERT counts + sanity probes)
without making any prod changes. Use `--commit` to execute.

Usage
-----
  python3 scripts/migrate_v1v2_unified.py                       # dry-run all pairs
  python3 scripts/migrate_v1v2_unified.py --pair ComplianceRule # dry-run one pair
  python3 scripts/migrate_v1v2_unified.py --commit              # ACTUALLY EXECUTE
  python3 scripts/migrate_v1v2_unified.py --commit --pair TaxIncentive

Requires
--------
- Tailscale UP (mac is `mauricemacbook-pro` 100.113.180.44; prod is
  `kg-node-eu` 100.88.170.57)
- prod_kg_client reachable
- C5b schema-discipline gate active (kg-api-server.py)

Audit ref
---------
- §20 Phase B2 (V1+V2 lineage unification)
- outputs/audits/2026-04-28-prod-kg-v1v2-unification-design.md (design proposal)
- outputs/audits/2026-04-28-prod-kg-b2-execution-readiness.md (readiness)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "_lib"))
import prod_kg_client as kg  # noqa: E402


# ===========================================================================
# Per-pair migration plans
#
# Each plan declares: the V1 + V2 source tables, the staging target name,
# the merge mode (UNION_DISJOINT or PER_ROW_MERGE), and the union-of-fields
# schema for the staging table. The schemas come from probing
# /api/v1/nodes?type=<X>&limit=1 and combining the field-key sets.
# ===========================================================================

PAIR_PLANS = {
    "ComplianceRule": {
        "v1": "ComplianceRule",
        "v2": "ComplianceRuleV2",
        "staging": "_experimental_ComplianceRule_Unified",
        "mode": "UNION_DISJOINT",  # 0 ID overlap per probe (162 + 84 = 246)
        # Fields are STRING by default; arrays + DOUBLE called out explicitly
        "fields": {
            # L2 canonical
            "id": "STRING", "name": "STRING", "description": "STRING",
            "effectiveDate": "STRING", "expiryDate": "STRING",
            "regulationNumber": "STRING", "regulationType": "STRING",
            "sourceUrl": "STRING", "fullText": "STRING",
            "hierarchyLevel": "INT64", "createdAt": "STRING",
            "consequence": "STRING",
            # L1 per-domain
            "category": "STRING",
            "applicableEntityTypes": "STRING[]", "applicableTaxTypes": "STRING[]",
            "ruleCode": "STRING", "severityLevel": "STRING",
            "conditionDescription": "STRING", "conditionFormula": "STRING",
            "detectionQuery": "STRING", "autoDetectable": "BOOLEAN",
            "requiredAction": "STRING", "violationConsequence": "STRING",
            "sourceClause": "STRING", "sourceRegulationId": "STRING",
            # L1 argument
            "argument_role": "STRING", "argument_strength": "DOUBLE",
            "argument_links_to": "STRING",
            # L1 provenance
            "source_doc_id": "STRING", "source_paragraph": "STRING",
            "extracted_by": "STRING", "confidence": "DOUBLE",
            # L1 jurisdictional + temporal
            "jurisdiction_code": "STRING", "jurisdiction_scope": "STRING",
            "effective_from": "STRING", "effective_to": "STRING",
            # L1 review trace
            "reviewed_at": "STRING", "reviewed_by": "STRING", "notes": "STRING",
            # L1 schema-evolution
            "override_chain_id": "STRING", "supersedes_id": "STRING",
            # Lineage
            "_lineage_present": "STRING[]",
        },
    },
    "FilingForm": {
        "v1": "FilingForm",
        "v2": "FilingFormV2",
        "staging": "_experimental_FilingForm_Unified",
        "mode": "UNION_DISJOINT",  # 0 ID overlap per probe (14 + 121 = 135)
        "fields": {
            # L2 canonical
            "id": "STRING", "name": "STRING", "description": "STRING",
            "effectiveDate": "STRING", "expiryDate": "STRING",
            "regulationNumber": "STRING", "regulationType": "STRING",
            "sourceUrl": "STRING", "fullText": "STRING",
            "hierarchyLevel": "INT64", "createdAt": "STRING",
            "title": "STRING", "reportCycle": "STRING", "deadlineDay": "STRING",
            # L1 per-domain
            "applicableTaxpayerType": "STRING", "calculationRules": "STRING",
            "deadline": "STRING", "deadlineAdjustmentRule": "STRING",
            "fields": "STRING", "filingChannel": "STRING",
            "filingFrequency": "STRING", "formCode": "STRING",
            "formNumber": "STRING", "onlineFilingUrl": "STRING",
            "penaltyForLate": "STRING", "relatedForms": "STRING",
            "taxTypeId": "STRING", "version": "STRING",
            # L1 provenance + lineage (per audit B4 forward-looking)
            "source_doc_id": "STRING", "extracted_by": "STRING",
            "confidence": "DOUBLE",
            # L1 jurisdictional + temporal
            "jurisdiction_code": "STRING", "jurisdiction_scope": "STRING",
            "effective_from": "STRING", "effective_to": "STRING",
            # Lineage
            "_lineage_present": "STRING[]",
        },
    },
    "TaxIncentive": {
        "v1": "TaxIncentive",
        "v2": "TaxIncentiveV2",
        "staging": "_experimental_TaxIncentive_Unified",
        "mode": "PER_ROW_MERGE",  # full ID intersection (109 / 109 / 109)
        "fields": {
            # L2 canonical
            "id": "STRING", "name": "STRING", "description": "STRING",
            "effectiveDate": "STRING", "expiryDate": "STRING",
            "regulationNumber": "STRING", "regulationType": "STRING",
            "sourceUrl": "STRING", "fullText": "STRING",
            "hierarchyLevel": "INT64", "createdAt": "STRING",
            "type": "STRING",
            # L1 per-domain
            "beneficiaryType": "STRING", "combinable": "BOOLEAN",
            "eligibilityCriteria": "STRING",
            "effectiveFrom": "STRING", "effectiveUntil": "STRING",
            "incentiveType": "STRING", "lawReference": "STRING",
            "maxAnnualBenefit": "STRING", "value": "STRING",
            "valueBasis": "STRING",
            # Lineage
            "_lineage_present": "STRING[]",
        },
    },
}


# ===========================================================================
# Plan rendering (dry-run mode)
# ===========================================================================


def render_plan_for(pair: str, plan: dict) -> list[str]:
    out = [f"\n{'=' * 72}", f"PLAN: pair={pair}  mode={plan['mode']}", "=" * 72]

    # Step 1: schema declaration
    fields_str = ",\n    ".join(f"{f} {t}" for f, t in plan["fields"].items())
    out.append(f"\nStep 1: CREATE staging table (passes C5b experimental_namespace gate)")
    out.append(f"  CREATE NODE TABLE IF NOT EXISTS {plan['staging']}(")
    out.append(f"    {fields_str},")
    out.append(f"    PRIMARY KEY (id)")
    out.append(f"  );")

    # Probe row counts
    try:
        v1_count = (kg.stats().get("title_stats") or {}).get(plan["v1"], {}).get("total", "?")
        v2_count = (kg.stats().get("title_stats") or {}).get(plan["v2"], {}).get("total", "?")
    except Exception:
        v1_count = v2_count = "?"

    if plan["mode"] == "UNION_DISJOINT":
        out.append(f"\nStep 2: INSERT V1 rows ({plan['v1']}: {v1_count} rows) with _lineage_present=['L1']")
        out.append(f"        Field-by-field copy of all V1 keys present in target schema.")
        out.append(f"\nStep 3: INSERT V2 rows ({plan['v2']}: {v2_count} rows) with _lineage_present=['L2']")
        out.append(f"        Guaranteed no ID collision (probed: 0 common IDs).")
        out.append(f"\nExpected post-state: {v1_count} + {v2_count} rows in {plan['staging']}.")
    else:  # PER_ROW_MERGE
        out.append(f"\nStep 2: INSERT V1 rows ({plan['v1']}: {v1_count} rows) with _lineage_present=['L1']")
        out.append(f"\nStep 3: For each row in V2 ({plan['v2']}: {v2_count} rows):")
        out.append(f"        - look up matching id in staging")
        out.append(f"        - if found: SET V2-only fields + APPEND 'L2' to _lineage_present")
        out.append(f"        - if not found: INSERT with _lineage_present=['L2']")
        out.append(f"\nExpected post-state: {v1_count} rows in {plan['staging']}, all with")
        out.append(f"        _lineage_present=['L1','L2'] (probe confirmed full intersection + 0 conflicts).")
    return out


def render_riskindicator_plan() -> list[str]:
    out = ["\n" + "=" * 72, "PLAN: RiskIndicatorV2 (orphan rename)", "=" * 72]
    try:
        v2_count = (kg.stats().get("title_stats") or {}).get("RiskIndicatorV2", {}).get("total", "?")
    except Exception:
        v2_count = "?"
    out.append(f"\nNo V1 to merge with (deleted ea83f033, M3 remediation 2026-03-20).")
    out.append(f"V2 = sole survivor with {v2_count} rows.")
    out.append(f"\nMigration shape (orchestrated separately, NOT in this script):")
    out.append(f"  Step 1: declare a canonical-name node table for RiskIndicator with V2 field shape")
    out.append(f"          (Already in canonical schema as `RiskIndicator` if declared; else add)")
    out.append(f"  Step 2: migrate-table source=RiskIndicatorV2 target=RiskIndicator")
    out.append(f"  Step 3: Rewire incident edges (1 type: TRIGGERED_BY ← AuditTrigger, ~463 edges)")
    out.append(f"  Step 4: DROP RiskIndicatorV2 (cutover; irreversible)")
    out.append(f"\nThis is a 1-step admin operation, not a lineage merge. Skip this script.")
    return out


# ===========================================================================
# Commit-mode execution scaffolding (to be filled in)
# ===========================================================================


def execute_pair(pair: str, plan: dict, allow_cutover: bool = False) -> int:
    """Execute the additive migration for one pair against prod.

    Returns 0 on success, non-zero on partial-state error. Caller is expected
    to inspect prod state after a non-zero return and either retry or drop the
    staging table.

    NOT IMPLEMENTED in this commit. The dry-run mode (default) ships first so
    the plan can be reviewed; commit-mode lands in a follow-up commit when
    Maurice schedules a contabo backup window. The reason: even though this
    is additive, it makes 600+ INSERT calls against prod, which deserves a
    backup snapshot regardless.
    """
    print(f"ERROR: --commit mode not yet implemented for pair={pair}.", file=sys.stderr)
    print("       Run without --commit for the dry-run plan.", file=sys.stderr)
    print("       To execute: schedule contabo backup window, then implement.", file=sys.stderr)
    return 1


# ===========================================================================
# Main
# ===========================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Additive V1+V2 lineage merge into _experimental_*_Unified staging tables"
    )
    parser.add_argument("--commit", action="store_true",
                        help="Actually execute (default: dry-run plan only)")
    parser.add_argument("--pair", choices=tuple(PAIR_PLANS.keys()) + ("all",),
                        default="all", help="Which pair to plan/execute (default: all)")
    parser.add_argument("--allow-cutover", action="store_true",
                        help="Permit destructive cutover steps (drop V1+V2, rename staging). "
                             "Required for --commit mode if cutover is in scope. NOT YET IMPLEMENTED.")
    args = parser.parse_args()

    # Liveness probe
    try:
        h = kg.health()
        if h.get("status") != "healthy":
            print(f"ERROR: kg-api unhealthy: {h}", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"ERROR: kg-api unreachable: {e}", file=sys.stderr)
        return 2

    pairs = tuple(PAIR_PLANS.keys()) if args.pair == "all" else (args.pair,)

    if args.commit:
        if not args.allow_cutover:
            print("WARN: --commit without --allow-cutover only runs additive steps "
                  "(safe). Cutover steps require --allow-cutover.", file=sys.stderr)
        rc = 0
        for pair in pairs:
            rc |= execute_pair(pair, PAIR_PLANS[pair], allow_cutover=args.allow_cutover)
        return rc

    # Dry-run mode (default)
    print("# DRY-RUN — no prod changes. Use --commit to execute.")
    for pair in pairs:
        for line in render_plan_for(pair, PAIR_PLANS[pair]):
            print(line)
    if args.pair == "all":
        for line in render_riskindicator_plan():
            print(line)
    print("\n" + "=" * 72)
    print("DRY-RUN COMPLETE. Re-run with --commit to execute additive merge into staging.")
    print("Cutover (drop V1+V2 + rename staging → canonical) is a separate operation.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
