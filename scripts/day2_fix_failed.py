#!/usr/bin/env python3
"""Day 2 Fix: Migrate tables that failed due to field_map errors.

Corrected field mappings based on actual source table schemas.
Run from Mac: python3 scripts/day2_fix_failed.py
"""
import json
import sys
import time
import urllib.request

API = "http://100.75.77.112:8400"
BATCH = 500
PAUSE = 1.0


def migrate(source, target, field_map, expected_count=0):
    print(f"\n  {source} -> {target} (expect ~{expected_count:,})")
    total_inserted = 0
    offset = 0
    retries = 0
    while True:
        payload = json.dumps({
            "source": source, "target": target,
            "field_map": field_map,
            "batch_size": BATCH, "offset": offset,
        }).encode()
        req = urllib.request.Request(
            f"{API}/api/v1/admin/migrate-table",
            data=payload, headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                inserted = result.get("inserted", 0)
                errors = result.get("errors", 0)
                total_inserted += inserted
                if inserted == 0 and errors == 0:
                    break
                offset += BATCH
                retries = 0
                print(f"    batch {offset//BATCH}: +{inserted} (total: {total_inserted:,})", end="\r")
                time.sleep(PAUSE)
        except Exception as e:
            retries += 1
            if retries > 3:
                print(f"\n    ABORT: {e}")
                break
            print(f"\n    retry {retries}: {str(e)[:60]}")
            time.sleep(15)
    print(f"\n  {source} -> {target}: {total_inserted:,} migrated")
    return total_inserted


def main():
    # Health check
    try:
        resp = urllib.request.urlopen(f"{API}/api/v1/health", timeout=10)
        health = json.loads(resp.read())
        if not health.get("kuzu"):
            print("ERROR: KuzuDB not healthy")
            sys.exit(1)
        print(f"API: {health['status']}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("=== Day 2 Fix: Corrected Field Maps ===\n")
    total = 0

    # 1. LegalDocument from LawOrRegulation (51K)
    # Real fields: id, title, regulationType, hierarchyLevel, issuingAuthority, effectiveDate, status
    print("[1/7] LegalDocument from LawOrRegulation")
    total += migrate("LawOrRegulation", "LegalDocument", {
        "id": "id",
        "name": "title",
        "type": "regulationType",      # exists! was working
        "level": "hierarchyLevel",      # STRING -> needs INT conversion
        "issuingBodyId": "issuingAuthority",
        "issueDate": "issuedDate",      # fixed: was empty string
        "effectiveDate": "effectiveDate",
        "expiryDate": "expiryDate",     # fixed: was "status"
        "status": "status",
    }, expected_count=51000)

    # 2. LegalDocument from AccountingStandard (43)
    # Real fields: id, name, effectiveDate, ...
    print("\n[2/7] LegalDocument from AccountingStandard")
    total += migrate("AccountingStandard", "LegalDocument", {
        "id": "id",
        "name": "name",
        "type": "'会计准则'",
        "level": "'3'",
        "issuingBodyId": "'财政部'",
        "issueDate": "effectiveDate",
        "effectiveDate": "effectiveDate",
        "expiryDate": "''",
        "status": "'现行有效'",
    }, expected_count=43)

    # 3. LegalClause from DocumentSection (42K)
    # Real fields: id, title, content, source
    print("\n[3/7] LegalClause from DocumentSection")
    total += migrate("DocumentSection", "LegalClause", {
        "id": "id",
        "documentId": "source",         # source = where it came from
        "clauseNumber": "''",
        "title": "title",
        "content": "content",
        "keywords": "''",
    }, expected_count=42000)

    # 4. Classification from TaxClassificationCode (4205)
    # Real fields: code(PK), item_name, level, category_abbr
    # NOTE: PK is 'code' not 'id' - need to map code->id
    print("\n[4/7] Classification from TaxClassificationCode")
    total += migrate("TaxClassificationCode", "Classification", {
        "id": "code",                   # code is the PK in source
        "name": "item_name",            # fixed: was 'name'
        "system": "'税收分类编码'",
    }, expected_count=4200)

    # 5. Classification from TaxCodeDetail (4061)
    # Real fields: id, code, item_name, parent_code, level
    print("\n[5/7] Classification from TaxCodeDetail")
    total += migrate("TaxCodeDetail", "Classification", {
        "id": "id",
        "name": "item_name",            # fixed: was 'name'
        "system": "'税收分类明细'",
    }, expected_count=4000)

    # 6. KnowledgeUnit from FAQEntry (1156)
    # Real fields: id, question, answer, category (NO 'source' field!)
    print("\n[6/7] KnowledgeUnit from FAQEntry")
    total += migrate("FAQEntry", "KnowledgeUnit", {
        "id": "id",
        "type": "'FAQ'",
        "title": "question",            # fixed: was mapped wrong
        "content": "answer",            # fixed: was mapped wrong
        "source": "category",           # use category as source
    }, expected_count=1156)

    # 7. TaxRate from TaxCodeRegionRate (9000)
    # Real fields: id, tax_code, item_name, region, applicable_rate (STRING!)
    print("\n[7/7] TaxRate from TaxCodeRegionRate")
    total += migrate("TaxCodeRegionRate", "TaxRate", {
        "id": "id",
        "name": "item_name",
        "taxTypeId": "tax_code",
        "value": "applicable_rate",     # STRING will be converted to DOUBLE by endpoint
        "valueExpression": "region",
        "calculationBasis": "''",
        "effectiveDate": "''",
        "expiryDate": "''",
    }, expected_count=9000)

    print(f"\n=== DONE: {total:,} total nodes migrated ===")


if __name__ == "__main__":
    main()
