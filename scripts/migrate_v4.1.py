#!/usr/bin/env python3
"""CogNebula Ontology v4.1 Migration — Phase 1: Node Data Migration.

Migrates ~193K nodes from 39 legacy source tables into 17 target ontology tables.
Uses the admin/migrate-table API endpoint (batch Cypher, no truncation after fix).

Usage:
    python3 scripts/migrate_v4.1.py                # Run all migrations
    python3 scripts/migrate_v4.1.py --group 1      # Run specific group only
    python3 scripts/migrate_v4.1.py --dry-run      # Show plan without executing
    python3 scripts/migrate_v4.1.py --status        # Check current table counts
"""
import json
import sys
import time
import urllib.request
from datetime import datetime

KG_API = "http://100.75.77.112:8400"
BATCH_SIZE = 500
DRY_RUN = "--dry-run" in sys.argv
STATUS_ONLY = "--status" in sys.argv
GROUP_FILTER = None
for a in sys.argv:
    if a.startswith("--group"):
        GROUP_FILTER = int(sys.argv[sys.argv.index(a) + 1])

# ── Migration Definitions ──────────────────────────────────────────────
# Each entry: (source_table, target_table, field_map, expected_count, group)
# field_map: {target_field: "source_field"} or {target_field: "'literal'"}

MIGRATIONS = [
    # ── Group 1: LegalDocument (39,225) ────────────────────────────
    ("LawOrRegulation", "LegalDocument", {
        "id": "id",
        "name": "title",
        "type": "regulationType",
        "documentType": "'tax_law'",
        "standardNumber": "regulationNumber",
        "level": "'0'",  # will be cast to INT by API
        "issuingBodyId": "issuingAuthority",
        "issueDate": "issuedDate",
        "effectiveDate": "effectiveDate",
        "expiryDate": "expiryDate",
        "status": "status",
        "latestVersionId": "''",
    }, 39182, 1),

    ("AccountingStandard", "LegalDocument", {
        "id": "id",
        "name": "name",
        "type": "'会计准则'",
        "documentType": "'accounting_standard'",
        "standardNumber": "''",
        "level": "'0'",
        "issuingBodyId": "''",
        "issueDate": "''",
        "effectiveDate": "''",
        "expiryDate": "''",
        "status": "'现行有效'",
        "latestVersionId": "''",
    }, 43, 1),

    # ── Group 2: LegalClause (71,907) ─────────────────────────────
    ("RegulationClause", "LegalClause", {
        "id": "id",
        "documentId": "regulationId",
        "clauseNumber": "articleNumber",
        "clauseLevel": "'article'",
        "sortOrder": "'0'",
        "title": "title",
        "content": "fullText",
        "keywords": "keywords",
    }, 29655, 2),

    ("DocumentSection", "LegalClause", {
        "id": "id",
        "documentId": "source",
        "clauseNumber": "''",
        "clauseLevel": "'section'",
        "sortOrder": "'0'",
        "title": "title",
        "content": "content",
        "keywords": "''",
    }, 42252, 2),

    # ── Group 3: KnowledgeUnit (37,435) ───────────────────────────
    ("CPAKnowledge", "KnowledgeUnit", {
        "id": "id",
        "type": "'考点'",
        "title": "title",
        "content": "content",
        "source": "source",
    }, 7371, 3),

    ("FAQEntry", "KnowledgeUnit", {
        "id": "id",
        "type": "'FAQ'",
        "title": "question",
        "content": "answer",
        "source": "category",
    }, 1156, 3),

    ("MindmapNode", "KnowledgeUnit", {
        "id": "id",
        "type": "'思维导图'",
        "title": "node_text",
        "content": "parent_text",
        "source": "category",
    }, 28526, 3),

    ("SpreadsheetEntry", "KnowledgeUnit", {
        "id": "id",
        "type": "'表格'",
        "title": "title",
        "content": "content",
        "source": "source",
    }, 280, 3),

    ("IndustryKnowledge", "KnowledgeUnit", {
        "id": "id",
        "type": "'行业知识'",
        "title": "title",
        "content": "content",
        "source": "source",
    }, 102, 3),

    # ── Group 4: Classification (33,392) ──────────────────────────
    # NOTE: Actual Classification table uses "id" as PK (not "code" per v4.1 DDL).
    ("HSCode", "Classification", {
        "id": "code",
        "name": "name",
        "system": "'HS编码'",
        "notes": "section",
    }, 22976, 4),

    ("TaxClassificationCode", "Classification", {
        "id": "code",
        "name": "item_name",
        "system": "'税收分类编码'",
        "notes": "description",
    }, 4205, 4),

    ("TaxCodeDetail", "Classification", {
        "id": "code",
        "name": "item_name",
        "system": "'税收分类编码明细'",
        "notes": "''",
    }, 4061, 4),

    ("TaxCodeIndustryMap", "Classification", {
        "id": "id",
        "name": "tax_code_name",
        "system": "'税收行业映射'",
        "notes": "applicability",
    }, 1380, 4),

    ("IndustryRiskProfile", "Classification", {
        "id": "id",
        "name": "id",  # no good name field, use id
        "system": "'行业风险画像'",
        "notes": "''",
    }, 720, 4),

    ("Industry", "Classification", {
        "id": "id",
        "name": "name",
        "system": "'国民经济行业分类'",
        "notes": "category",
    }, 24, 4),

    ("FTIndustry", "Classification", {
        "id": "gbCode",
        "name": "name",
        "system": "'国民经济行业分类'",
        "notes": "classificationLevel",
    }, 19, 4),

    ("IndustryBookkeeping", "Classification", {
        "id": "id",
        "name": "industryName",
        "system": "'行业记账指南'",
        "notes": "costMethod",
    }, 7, 4),

    # ── Group 5: TaxRate (160) ────────────────────────────────────
    ("TaxRateMapping", "TaxRate", {
        "id": "id",
        "name": "productCategory",
        "taxTypeId": "taxTypeId",
        "value": "applicableRate",
        "valueExpression": "rateLabel",
        "calculationBasis": "specialPolicy",
        "taxMethod": "'general'",
        "rateType": "'proportional'",
        "effectiveDate": "effectiveFrom",
        "expiryDate": "effectiveUntil",
    }, 80, 5),

    ("TaxRateDetail", "TaxRate", {
        "id": "id",
        "name": "description",
        "taxTypeId": "tax_type",
        "value": "rate_pct",
        "valueExpression": "''",
        "calculationBasis": "applicable_to",
        "taxMethod": "'general'",
        "rateType": "'proportional'",
        "effectiveDate": "''",
        "expiryDate": "''",
    }, 37, 5),

    ("TaxRateSchedule", "TaxRate", {
        "id": "id",
        "name": "scheduleName",
        "taxTypeId": "taxTypeId",
        "value": "rate",
        "valueExpression": "quickDeduction",
        "calculationBasis": "applicableScope",
        "taxMethod": "'general'",
        "rateType": "'progressive'",
        "effectiveDate": "effectiveFrom",
        "expiryDate": "effectiveUntil",
    }, 23, 5),

    ("TaxPolicy", "TaxRate", {
        "id": "id",
        "name": "policy_name",
        "taxTypeId": "applicable_tax",
        "value": "'0'",
        "valueExpression": "benefit",
        "calculationBasis": "conditions",
        "taxMethod": "'general'",
        "rateType": "'proportional'",
        "effectiveDate": "effective_period",
        "expiryDate": "''",
    }, 20, 5),

    # ── Group 6: Small Entity Tables ──────────────────────────────
    ("ComplianceRuleV2", "ComplianceRule", {
        "id": "id",
        "name": "name",
        "description": "description",
        "category": "category",
        "consequence": "consequence",
        "applicableScope": "''",
        "effectiveDate": "effectiveDate",
        "expiryDate": "expiryDate",
    }, 84, 6),

    ("RiskIndicatorV2", "RiskIndicator", {
        "id": "id",
        "name": "name",
        "description": "description",
        "indicatorType": "indicatorType",
        "threshold": "threshold",
        "severity": "severity",
        "formula": "formula",
        "category": "category",
    }, 463, 6),

    ("FilingFormV2", "FilingForm", {
        "id": "id",
        "name": "name",
        "reportCycle": "reportCycle",
        "deadlineDay": "deadlineDay",
        "frequency": "''",
        "applicableTaxpayerType": "''",
    }, 121, 6),

    ("FormTemplate", "FilingForm", {
        "id": "id",
        "name": "name",
        "reportCycle": "category",
        "deadlineDay": "'0'",
        "frequency": "''",
        "applicableTaxpayerType": "''",
    }, 109, 6),

    ("TaxCalendar", "FilingForm", {
        "id": "id",
        "name": "name",
        "reportCycle": "'月'",
        "deadlineDay": "'15'",
        "frequency": "'monthly'",
        "applicableTaxpayerType": "''",
    }, 12, 6),

    ("TaxRiskScenario", "BusinessActivity", {
        "id": "id",
        "name": "scenario",
        "description": "description",
    }, 180, 6),

    ("EnterpriseType", "TaxEntity", {
        "id": "id",
        "name": "name",
        "type": "'企业'",
        "taxpayerStatus": "classificationBasis",
        "residencyStatus": "''",
        "functionalCurrency": "'CNY'",
        "sizeCategory": "''",
        "ownershipType": "''",
    }, 6, 6),

    ("TaxpayerStatus", "TaxEntity", {
        "id": "id",
        "name": "name",
        "type": "'身份'",
        "taxpayerStatus": "domain",
        "residencyStatus": "''",
        "functionalCurrency": "''",
        "sizeCategory": "''",
        "ownershipType": "''",
    }, 5, 6),

    ("EntityTypeProfile", "TaxEntity", {
        "id": "id",
        "name": "name",
        "type": "entityType",
        "taxpayerStatus": "taxpayerCategory",
        "residencyStatus": "''",
        "functionalCurrency": "''",
        "sizeCategory": "''",
        "ownershipType": "''",
    }, 6, 6),

    # NOTE: RegionalTaxPolicy (620 policy records with hash IDs) != Region (31 geographic codes)
    # Skip: policies should not be merged into the geography table

    ("TaxIncentiveV2", "TaxIncentive", {
        "id": "id",
        "name": "name",
        "type": "type",
        "description": "description",
        "incentiveType": "incentiveType",
        "status": "'active'",
        "stackingGroup": "stackingGroup",
        "eligibilityCriteria": "eligibilityCriteria",
        "effectiveDate": "effectiveDate",
        "expiryDate": "expiryDate",
    }, 109, 6),

    # ── Group 7: AccountingSubject merge ──────────────────────────
    # NOTE: Actual table uses "id" as PK (not "code" per v4.1 DDL)
    ("ChartOfAccount", "AccountingSubject", {
        "id": "code",
        "name": "name",
        "category": "category",
        "balanceDirection": "direction",
        "level": "level",
        "parentCode": "parentAccountCode",
        "isLeaf": "isLeaf",
        "monetaryType": "''",
        "standardSource": "standardBasis",
    }, 159, 7),

    ("ChartOfAccountDetail", "AccountingSubject", {
        "id": "code",
        "name": "name",
        "category": "category",
        "balanceDirection": "''",
        "level": "level",
        "parentCode": "parent_code",
        "isLeaf": "'0'",
        "monetaryType": "''",
        "standardSource": "''",
    }, 123, 7),
]


def api_call(path: str, payload: dict) -> dict:
    """Call KG API endpoint."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{KG_API}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_table_count(table_name: str) -> int:
    """Get current row count for a table."""
    try:
        resp = api_call("/api/v1/stats", {})
    except:
        # GET endpoint, use different method
        pass
    req = urllib.request.Request(f"{KG_API}/api/v1/stats")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("nodes_by_type", {}).get(table_name, 0)
    except:
        return -1


def migrate_one(source: str, target: str, field_map: dict,
                expected: int, batch_size: int = BATCH_SIZE) -> dict:
    """Run one source->target migration in batches."""
    total_inserted = 0
    total_errors = 0
    offset = 0

    while True:
        payload = {
            "source": source,
            "target": target,
            "field_map": field_map,
            "batch_size": batch_size,
            "offset": offset,
        }
        result = api_call("/api/v1/admin/migrate-table", payload)

        if "error" in result:
            print(f"  ERROR at offset {offset}: {result['error'][:100]}")
            total_errors += 1
            break

        inserted = result.get("inserted", 0)
        errors = result.get("errors", 0)
        total_inserted += inserted
        total_errors += errors

        if inserted == 0 and errors == 0:
            break  # No more data

        offset += batch_size
        pct = min(100, offset * 100 // max(expected, 1))
        print(f"  ... {offset}/{expected} ({pct}%) +{inserted} ins, {errors} err", end="\r")

        # Safety: don't exceed 2x expected
        if offset > expected * 2:
            print(f"\n  SAFETY STOP: offset {offset} > 2x expected {expected}")
            break

    return {"inserted": total_inserted, "errors": total_errors}


def show_status():
    """Show current counts for all target tables."""
    targets = set()
    for _, target, _, _, _ in MIGRATIONS:
        targets.add(target)

    print("\n=== Target Table Status ===\n")
    req = urllib.request.Request(f"{KG_API}/api/v1/stats")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    nodes = data.get("nodes_by_type", {})
    for t in sorted(targets):
        count = nodes.get(t, 0)
        print(f"  {t:25} {count:>8}")

    print(f"\n  {'TOTAL':25} {data.get('total_nodes', 0):>8}")


def main():
    if STATUS_ONLY:
        show_status()
        return

    # Group migrations
    groups = {}
    for src, tgt, fmap, exp, grp in MIGRATIONS:
        groups.setdefault(grp, []).append((src, tgt, fmap, exp))

    # Filter if requested
    if GROUP_FILTER:
        groups = {k: v for k, v in groups.items() if k == GROUP_FILTER}

    total_expected = sum(exp for _, _, _, exp, _ in MIGRATIONS if GROUP_FILTER is None or _ == GROUP_FILTER)
    # Recalculate correctly
    total_expected = sum(exp for items in groups.values() for _, _, _, exp in items)

    print(f"\n{'='*60}")
    print(f"  CogNebula v4.1 Migration — Phase 1: Node Data")
    print(f"  {len(MIGRATIONS)} migrations, ~{total_expected:,} records")
    print(f"  API: {KG_API}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    grand_inserted = 0
    grand_errors = 0
    grand_skipped = 0
    results_log = []

    for grp_num in sorted(groups.keys()):
        items = groups[grp_num]
        grp_total = sum(exp for _, _, _, exp in items)
        print(f"\n--- Group {grp_num} ({len(items)} tables, ~{grp_total:,} records) ---\n")

        for src, tgt, fmap, exp in items:
            print(f"  {src} ({exp:,}) -> {tgt}")

            if DRY_RUN:
                print(f"    [DRY RUN] Would migrate {exp:,} records")
                print(f"    Fields: {', '.join(fmap.keys())}")
                results_log.append({"source": src, "target": tgt, "status": "DRY_RUN", "expected": exp})
                continue

            t0 = time.time()
            result = migrate_one(src, tgt, fmap, exp)
            elapsed = time.time() - t0

            ins = result["inserted"]
            err = result["errors"]
            skipped = exp - ins - err  # Approximate (duplicates)
            grand_inserted += ins
            grand_errors += err
            grand_skipped += max(0, skipped)

            status = "OK" if err == 0 else "WARN"
            print(f"\n    {status}: +{ins:,} inserted, {err} errors, ~{max(0, skipped):,} skipped (dup), {elapsed:.1f}s")
            results_log.append({
                "source": src, "target": tgt, "status": status,
                "inserted": ins, "errors": err, "elapsed": round(elapsed, 1),
            })

    # Summary
    print(f"\n{'='*60}")
    print(f"  MIGRATION COMPLETE")
    print(f"  Inserted: {grand_inserted:,}")
    print(f"  Errors:   {grand_errors}")
    print(f"  Skipped:  ~{grand_skipped:,} (duplicates)")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Write results log
    log_path = "data/migration_v4.1_log.json"
    with open(log_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_inserted": grand_inserted,
            "total_errors": grand_errors,
            "migrations": results_log,
        }, f, indent=2, ensure_ascii=False)
    print(f"  Log written to {log_path}")

    # Show final counts
    show_status()


if __name__ == "__main__":
    main()
