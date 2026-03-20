#!/usr/bin/env python3
"""Day 2: Bulk migrate large tables into v2.2 schema using COPY FROM CSV.

Strategy: Query old tables -> Write CSV -> COPY FROM CSV into new tables.
All operations run server-side (no network transfer).

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/migrate_bulk_tables.py
    sudo systemctl start kg-api
"""
import csv
import kuzu
import os
import sys
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_DIR = "/home/kg/cognebula-enterprise/data/migration_csv"
os.makedirs(CSV_DIR, exist_ok=True)

BATCH = 2000  # Read batch size


def safe(v, maxlen=500):
    """Sanitize value for CSV."""
    if v is None:
        return ""
    s = str(v)[:maxlen]
    return s.replace("\x00", "").strip()


def export_and_import(conn, new_table, query, fields, csv_name):
    """Export from old table via query, write CSV, COPY into new table."""
    csv_path = os.path.join(CSV_DIR, csv_name)
    t0 = time.time()

    # Step 1: Export to CSV
    print(f"  Exporting {csv_name}...", end=" ", flush=True)
    count = 0
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)  # Header
        try:
            r = conn.execute(query)
            while r.has_next():
                row = r.get_next()
                writer.writerow([safe(v) for v in row])
                count += 1
        except Exception as e:
            print(f"QUERY ERROR: {e}")
            return 0
    print(f"{count:,} rows", end=" ", flush=True)

    if count == 0:
        print("(skip)")
        return 0

    # Step 2: COPY FROM CSV into new table
    print("-> importing...", end=" ", flush=True)
    try:
        conn.execute(f'COPY {new_table} FROM "{csv_path}" (header=true)')
        elapsed = time.time() - t0
        print(f"OK ({elapsed:.1f}s)")
        return count
    except Exception as e:
        err = str(e)
        if "primary key" in err.lower() or "duplicate" in err.lower():
            print(f"SKIP (already imported)")
            return 0
        print(f"IMPORT ERROR: {err[:100]}")
        return 0


def main():
    print("=== Day 2: Bulk Table Migration ===")
    print(f"DB: {DB_PATH}")
    print(f"CSV: {CSV_DIR}\n")

    db = kuzu.Database(DB_PATH, buffer_pool_size=1024 * 1024 * 1024)
    conn = kuzu.Connection(db)
    print("KuzuDB connected\n")

    total = 0

    # 1. LegalDocument (from LawOrRegulation 51K + AccountingStandard 43)
    print("[1/5] LegalDocument")
    n = export_and_import(conn, "LegalDocument",
        "MATCH (n:LawOrRegulation) RETURN n.id, n.title, '规范性文件', 4, '', '', n.effectiveDate, '', n.status",
        ["id", "name", "type", "level", "issuingBodyId", "issueDate", "effectiveDate", "expiryDate", "status"],
        "legal_document_lor.csv")
    total += n

    n = export_and_import(conn, "LegalDocument",
        "MATCH (n:AccountingStandard) RETURN n.id, n.name, '会计准则', 3, '', '', n.effectiveDate, '', 'active'",
        ["id", "name", "type", "level", "issuingBodyId", "issueDate", "effectiveDate", "expiryDate", "status"],
        "legal_document_as.csv")
    total += n

    # 2. LegalClause (from RegulationClause 28K + DocumentSection 42K)
    print("\n[2/5] LegalClause")
    n = export_and_import(conn, "LegalClause",
        "MATCH (n:RegulationClause) RETURN n.id, n.regulationId, n.articleNumber, n.title, n.fullText, n.keywords",
        ["id", "documentId", "clauseNumber", "title", "content", "keywords"],
        "legal_clause_rc.csv")
    total += n

    n = export_and_import(conn, "LegalClause",
        "MATCH (n:DocumentSection) RETURN n.id, n.source, '', n.title, n.content, ''",
        ["id", "documentId", "clauseNumber", "title", "content", "keywords"],
        "legal_clause_ds.csv")
    total += n

    # 3. Classification (from HSCode 23K + TaxClassificationCode 4K + Industry tables)
    print("\n[3/5] Classification")
    n = export_and_import(conn, "Classification",
        "MATCH (n:HSCode) RETURN n.id, n.name, 'HS编码'",
        ["id", "name", "system"],
        "classification_hs.csv")
    total += n

    n = export_and_import(conn, "Classification",
        "MATCH (n:TaxClassificationCode) RETURN n.id, n.name, '税收分类编码'",
        ["id", "name", "system"],
        "classification_tc.csv")
    total += n

    n = export_and_import(conn, "Classification",
        "MATCH (n:TaxCodeDetail) RETURN n.id, n.name, '税收分类明细'",
        ["id", "name", "system"],
        "classification_td.csv")
    total += n

    for old_tbl, sys_name in [("Industry", "国民经济行业分类"), ("FTIndustry", "外贸行业分类"),
                               ("TaxCodeIndustryMap", "行业税码映射")]:
        n = export_and_import(conn, "Classification",
            f"MATCH (n:{old_tbl}) RETURN n.id, n.name, '{sys_name}'",
            ["id", "name", "system"],
            f"classification_{old_tbl.lower()}.csv")
        total += n

    # 4. KnowledgeUnit (from CPAKnowledge 7K + FAQEntry 1K + MindmapNode 28K + others)
    print("\n[4/5] KnowledgeUnit")
    n = export_and_import(conn, "KnowledgeUnit",
        "MATCH (n:CPAKnowledge) RETURN n.id, '考点', n.topic, n.content, n.source",
        ["id", "type", "title", "content", "source"],
        "knowledge_cpa.csv")
    total += n

    n = export_and_import(conn, "KnowledgeUnit",
        "MATCH (n:FAQEntry) RETURN n.id, 'FAQ', n.question, n.answer, n.source",
        ["id", "type", "title", "content", "source"],
        "knowledge_faq.csv")
    total += n

    n = export_and_import(conn, "KnowledgeUnit",
        "MATCH (n:MindmapNode) RETURN n.id, '思维导图', n.node_text, n.category, 'mindmap'",
        ["id", "type", "title", "content", "source"],
        "knowledge_mm.csv")
    total += n

    for old_tbl, ktype in [("SpreadsheetEntry", "表格"), ("IndustryKnowledge", "行业知识")]:
        n = export_and_import(conn, "KnowledgeUnit",
            f"MATCH (n:{old_tbl}) RETURN n.id, '{ktype}', n.name, n.content, 'seed'",
            ["id", "type", "title", "content", "source"],
            f"knowledge_{old_tbl.lower()}.csv")
        total += n

    # 5. TaxRate (from TaxCodeRegionRate 9K + TaxRateMapping 80 + TaxRateDetail 37 + TaxRateSchedule 23)
    print("\n[5/5] TaxRate")
    n = export_and_import(conn, "TaxRate",
        "MATCH (n:TaxCodeRegionRate) RETURN n.id, n.item_name, n.tax_code, n.applicable_rate, '', '', '', ''",
        ["id", "name", "taxTypeId", "value", "valueExpression", "calculationBasis", "effectiveDate", "expiryDate"],
        "taxrate_region.csv")
    total += n

    n = export_and_import(conn, "TaxRate",
        "MATCH (n:TaxRateMapping) RETURN n.id, n.productCategory, n.taxTypeId, n.applicableRate, n.simplifiedRate, '', n.effectiveFrom, n.effectiveUntil",
        ["id", "name", "taxTypeId", "value", "valueExpression", "calculationBasis", "effectiveDate", "expiryDate"],
        "taxrate_mapping.csv")
    total += n

    for old_tbl in ["TaxRateDetail", "TaxRateSchedule"]:
        n = export_and_import(conn, "TaxRate",
            f"MATCH (n:{old_tbl}) RETURN n.id, n.name, '', 0.0, '', '', '', ''",
            ["id", "name", "taxTypeId", "value", "valueExpression", "calculationBasis", "effectiveDate", "expiryDate"],
            f"taxrate_{old_tbl.lower()}.csv")
        total += n

    # Summary
    print(f"\n=== DONE ===")
    print(f"Total migrated: {total:,} nodes into v2.2 tables")
    print(f"CSV files: {CSV_DIR}")

    # Cleanup CSV (optional)
    # for f in os.listdir(CSV_DIR):
    #     os.remove(os.path.join(CSV_DIR, f))


if __name__ == "__main__":
    main()
