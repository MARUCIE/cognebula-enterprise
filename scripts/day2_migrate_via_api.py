#!/usr/bin/env python3
"""Day 2: Bulk migrate large tables via API migrate-table endpoint.

No SSH needed. Calls API in batches of 500, with retry on OOM recovery.
Run from Mac: python3 scripts/day2_migrate_via_api.py
"""
import json
import sys
import time
import urllib.request

API = "http://100.75.77.112:8400"
BATCH = 500
PAUSE = 1.0  # seconds between batches (let KuzuDB breathe)


def migrate(source, target, field_map, expected_count=0):
    """Migrate one table in batches."""
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
                    # No more data
                    break

                offset += BATCH
                retries = 0
                print(f"    batch {offset//BATCH}: +{inserted} (total: {total_inserted:,})", end="\r")
                time.sleep(PAUSE)

        except Exception as e:
            retries += 1
            if retries > 5:
                print(f"\n    ABORT after 5 retries: {e}")
                break
            print(f"\n    retry {retries} (waiting 15s): {str(e)[:60]}")
            time.sleep(15)  # Wait for API to recover from potential OOM

    print(f"\n  {source} -> {target}: {total_inserted:,} migrated")
    return total_inserted


def main():
    # Check API health
    try:
        resp = urllib.request.urlopen(f"{API}/api/v1/health", timeout=10)
        health = json.loads(resp.read())
        print(f"API: {health['status']}")
    except:
        print("ERROR: API not reachable")
        sys.exit(1)

    # Check if migrate-table endpoint exists
    try:
        resp = urllib.request.urlopen(f"{API}/openapi.json", timeout=10)
        paths = json.loads(resp.read()).get("paths", {})
        if "/api/v1/admin/migrate-table" not in paths:
            print("ERROR: migrate-table endpoint not deployed yet")
            print("Run: scp kg-api-server.py kg-node:/home/kg/ && ssh kg-node 'sudo systemctl restart kg-api'")
            sys.exit(1)
    except:
        pass

    print("=== Day 2: Bulk Migration via API ===\n")
    total = 0

    # 1. LegalDocument (51K from LawOrRegulation + 43 from AccountingStandard)
    print("[1/5] LegalDocument")
    total += migrate("LawOrRegulation", "LegalDocument", {
        "id": "id", "name": "title", "type": "'规范性文件'",
        "level": "'4'", "issuingBodyId": "issuingAuthority",
        "issueDate": "''", "effectiveDate": "effectiveDate",
        "expiryDate": "''", "status": "status",
    }, expected_count=51000)

    total += migrate("AccountingStandard", "LegalDocument", {
        "id": "id", "name": "name", "type": "'会计准则'",
        "level": "'3'", "issuingBodyId": "''",
        "issueDate": "''", "effectiveDate": "effectiveDate",
        "expiryDate": "''", "status": "'active'",
    }, expected_count=43)

    # 2. LegalClause (28K from RegulationClause + 42K from DocumentSection)
    print("\n[2/5] LegalClause")
    total += migrate("RegulationClause", "LegalClause", {
        "id": "id", "documentId": "regulationId",
        "clauseNumber": "articleNumber", "title": "title",
        "content": "fullText", "keywords": "keywords",
    }, expected_count=28000)

    total += migrate("DocumentSection", "LegalClause", {
        "id": "id", "documentId": "source",
        "clauseNumber": "''", "title": "title",
        "content": "content", "keywords": "''",
    }, expected_count=42000)

    # 3. Classification (23K HSCode + 4K TaxClassificationCode + others)
    print("\n[3/5] Classification")
    total += migrate("HSCode", "Classification", {
        "id": "id", "name": "name", "system": "'HS编码'",
    }, expected_count=23000)

    total += migrate("TaxClassificationCode", "Classification", {
        "id": "id", "name": "name", "system": "'税收分类编码'",
    }, expected_count=4200)

    total += migrate("TaxCodeDetail", "Classification", {
        "id": "id", "name": "name", "system": "'税收分类明细'",
    }, expected_count=4000)

    for old_tbl, sys_name, count in [
        ("Industry", "国民经济行业分类", 24),
        ("FTIndustry", "外贸行业分类", 19),
        ("TaxCodeIndustryMap", "行业税码映射", 1380),
    ]:
        total += migrate(old_tbl, "Classification", {
            "id": "id", "name": "name", "system": f"'{sys_name}'",
        }, expected_count=count)

    # 4. KnowledgeUnit (7K CPA + 1K FAQ + 28K MindmapNode + others)
    print("\n[4/5] KnowledgeUnit")
    total += migrate("CPAKnowledge", "KnowledgeUnit", {
        "id": "id", "type": "'考点'", "title": "topic",
        "content": "content", "source": "source",
    }, expected_count=7300)

    total += migrate("FAQEntry", "KnowledgeUnit", {
        "id": "id", "type": "'FAQ'", "title": "question",
        "content": "answer", "source": "source",
    }, expected_count=1156)

    total += migrate("MindmapNode", "KnowledgeUnit", {
        "id": "id", "type": "'思维导图'", "title": "node_text",
        "content": "category", "source": "'mindmap'",
    }, expected_count=28500)

    # 5. TaxRate (9K TaxCodeRegionRate + 80 TaxRateMapping + 60 others)
    print("\n[5/5] TaxRate")
    total += migrate("TaxCodeRegionRate", "TaxRate", {
        "id": "id", "name": "item_name", "taxTypeId": "tax_code",
        "value": "'0'", "valueExpression": "''",
        "calculationBasis": "''", "effectiveDate": "''", "expiryDate": "''",
    }, expected_count=9000)

    total += migrate("TaxRateMapping", "TaxRate", {
        "id": "id", "name": "productCategory", "taxTypeId": "taxTypeId",
        "value": "'0'", "valueExpression": "simplifiedRate",
        "calculationBasis": "''", "effectiveDate": "effectiveFrom", "expiryDate": "effectiveUntil",
    }, expected_count=80)

    print(f"\n=== DONE: {total:,} total nodes migrated ===")


if __name__ == "__main__":
    main()
