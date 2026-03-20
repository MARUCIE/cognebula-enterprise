#!/usr/bin/env python3
"""Create v2.2 structural edges offline (direct KuzuDB, no API).

Must stop kg-api before running:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 /home/kg/cognebula-enterprise/scripts/create_v2_edges.py
    sudo systemctl start kg-api

Creates edges in small batches with periodic checkpoint to avoid OOM.
"""
import kuzu
import sys
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
BATCH = 100  # Small batch to avoid buffer overflow

db = kuzu.Database(DB_PATH, buffer_pool_size=1024 * 1024 * 1024)
conn = kuzu.Connection(db)
print("KuzuDB connected\n")


def create_edges_batched(cypher_template, description, max_batches=500):
    """Create edges using LIMIT-based batching."""
    total = 0
    for i in range(max_batches):
        try:
            # The template should use LIMIT to control batch size
            conn.execute(cypher_template.format(limit=BATCH))
            total += BATCH
            if (i + 1) % 10 == 0:
                print(f"  {description}: ~{total:,}", end="\r")
        except Exception as e:
            err = str(e)
            if "no result" in err.lower() or "empty" in err.lower():
                break
            print(f"  {description}: ERROR at ~{total}: {err[:80]}")
            break
    print(f"  {description}: ~{total:,} (approximate)")
    return total


def create_edges_by_id_match(source_table, target_table, source_fk, rel_type, desc):
    """Create edges by matching foreign key to target ID, row by row."""
    total = 0
    errors = 0

    # Read all source nodes with FK
    r = conn.execute(
        f"MATCH (s:{source_table}) WHERE s.{source_fk} IS NOT NULL AND s.{source_fk} <> '' "
        f"RETURN s.id, s.{source_fk} LIMIT 100000"
    )

    pairs = []
    while r.has_next():
        row = r.get_next()
        pairs.append((str(row[0]), str(row[1])))

    print(f"  {desc}: {len(pairs):,} pairs to process")

    for sid, tid in pairs:
        try:
            conn.execute(
                f"MATCH (s:{source_table} {{id: $sid}}), (t:{target_table} {{id: $tid}}) "
                f"CREATE (s)-[:{rel_type}]->(t)",
                {"sid": sid, "tid": tid}
            )
            total += 1
        except:
            errors += 1

        if (total + errors) % 1000 == 0:
            print(f"  {desc}: {total:,} created, {errors:,} skipped", end="\r")

    print(f"  {desc}: {total:,} created, {errors:,} skipped")
    return total


total_edges = 0

# 1. PART_OF: LegalClause -> LegalDocument (via documentId)
print("[1/5] PART_OF edges")
total_edges += create_edges_by_id_match(
    "LegalClause", "LegalDocument", "documentId", "PART_OF",
    "LegalClause->LegalDocument"
)

# 2. CHILD_OF: Classification -> Classification (via parent hierarchy)
# HSCode has parent_code in TaxCodeDetail
print("\n[2/5] CHILD_OF edges (classification hierarchy)")
try:
    r = conn.execute(
        "MATCH (c:Classification) WHERE c.id IS NOT NULL RETURN c.id LIMIT 1"
    )
    # Classification doesn't have parent_code - skip for now
    print("  SKIP: Classification doesn't have parent FK field")
except:
    print("  SKIP: Classification table issue")

# 3. APPLIES_TO_TAX: TaxRate -> TaxType (via taxTypeId)
print("\n[3/5] APPLIES_TO_TAX edges")
total_edges += create_edges_by_id_match(
    "TaxRate", "TaxType", "taxTypeId", "APPLIES_TO_TAX",
    "TaxRate->TaxType"
)

# 4. ISSUED_BY: LegalDocument -> IssuingBody (via issuingBodyId)
print("\n[4/5] ISSUED_BY edges")
total_edges += create_edges_by_id_match(
    "LegalDocument", "IssuingBody", "issuingBodyId", "ISSUED_BY",
    "LegalDocument->IssuingBody"
)

# 5. EXPLAINS: KnowledgeUnit -> LegalClause (content-based, simplified)
# Match KnowledgeUnit to LegalClause by shared documentId/source
print("\n[5/5] EXPLAINS edges (knowledge -> clause)")
# This requires semantic matching - skip for now, needs AI
print("  SKIP: Requires Gemini AI extraction (Day 4+)")

print(f"\n=== DONE: {total_edges:,} total new edges ===")

# Final stats
r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
print(f"Total edges in DB: {r.get_next()[0]:,}")

del conn
del db
