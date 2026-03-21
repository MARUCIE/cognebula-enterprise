#!/usr/bin/env python3
"""Fix title coverage for promoted node types."""
import kuzu

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

# RegulationClause: copy fullText to title
r = conn.execute(
    "MATCH (n:RegulationClause) WHERE n.title IS NULL OR size(n.title) < 5 RETURN count(n)"
)
print(f"RegulationClause missing title: {r.get_next()[0]}")

r = conn.execute(
    "MATCH (n:RegulationClause) "
    "WHERE (n.title IS NULL OR size(n.title) < 5) "
    "AND n.fullText IS NOT NULL AND size(n.fullText) >= 10 "
    "SET n.title = substring(n.fullText, 0, 80) "
    "RETURN count(n)"
)
print(f"  Fixed from fullText: {r.get_next()[0]}")

# TaxCodeDetail: set title = item_name
r = conn.execute(
    "MATCH (n:TaxCodeDetail) WHERE n.title IS NULL OR size(n.title) < 5 RETURN count(n)"
)
print(f"\nTaxCodeDetail missing title: {r.get_next()[0]}")

r = conn.execute(
    "MATCH (n:TaxCodeDetail) "
    "WHERE (n.title IS NULL OR size(n.title) < 5) "
    "AND n.item_name IS NOT NULL AND size(n.item_name) >= 2 "
    "SET n.title = n.item_name "
    "RETURN count(n)"
)
print(f"  Fixed from item_name: {r.get_next()[0]}")

# TaxClassificationCode: set title = item_name
r = conn.execute(
    "MATCH (n:TaxClassificationCode) WHERE n.title IS NULL OR size(n.title) < 5 RETURN count(n)"
)
print(f"\nTaxClassificationCode missing title: {r.get_next()[0]}")

try:
    r = conn.execute(
        "MATCH (n:TaxClassificationCode) "
        "WHERE (n.title IS NULL OR size(n.title) < 5) "
        "AND n.item_name IS NOT NULL AND size(n.item_name) >= 2 "
        "SET n.title = n.item_name "
        "RETURN count(n)"
    )
    print(f"  Fixed from item_name: {r.get_next()[0]}")
except Exception as e:
    print(f"  Error: {str(e)[:80]}")

del conn; del db
print("\nDone")
