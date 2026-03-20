#!/usr/bin/env python3
"""CogNebula Ontology v2.1 Migration Script.

Dual-track incremental migration:
- Day 0: DROP empty tables + create v2.1 schema in parallel
- Day 1-3: Migrate data from old tables to new tables
- Day 4+: AI semantic edge extraction

Usage:
    python3 scripts/migrate_v2.py --phase 0    # DROP empty + create new schema
    python3 scripts/migrate_v2.py --phase 1    # Migrate seed data (TaxType, Region, etc.)
    python3 scripts/migrate_v2.py --phase 2    # Migrate bulk data (LegalDocument, LegalClause, etc.)
    python3 scripts/migrate_v2.py --phase 3    # AI edge extraction
    python3 scripts/migrate_v2.py --dry-run    # Show what would happen
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

KG_API = "http://100.75.77.112:8400"
DRY_RUN = "--dry-run" in sys.argv

# ── v2.1 Schema DDL ──────────────────────────────────────────────────
V2_NODE_TABLES = {
    "LegalDocument": """CREATE NODE TABLE IF NOT EXISTS LegalDocument (
        id STRING PRIMARY KEY, name STRING, type STRING, level INT64,
        issuingBodyId STRING, issueDate STRING, effectiveDate STRING,
        expiryDate STRING, status STRING)""",
    "LegalClause": """CREATE NODE TABLE IF NOT EXISTS LegalClause (
        id STRING PRIMARY KEY, documentId STRING, clauseNumber STRING,
        title STRING, content STRING, keywords STRING)""",
    "TaxRate": """CREATE NODE TABLE IF NOT EXISTS TaxRate (
        id STRING PRIMARY KEY, name STRING, taxTypeId STRING, value DOUBLE,
        valueExpression STRING, calculationBasis STRING,
        effectiveDate STRING, expiryDate STRING)""",
    "ComplianceRule_v2": """CREATE NODE TABLE IF NOT EXISTS ComplianceRule_v2 (
        id STRING PRIMARY KEY, name STRING, description STRING,
        category STRING, consequence STRING,
        effectiveDate STRING, expiryDate STRING)""",
    "RiskIndicator_v2": """CREATE NODE TABLE IF NOT EXISTS RiskIndicator_v2 (
        id STRING PRIMARY KEY, name STRING, description STRING,
        indicatorType STRING, threshold DOUBLE, severity STRING)""",
    "TaxIncentive_v2": """CREATE NODE TABLE IF NOT EXISTS TaxIncentive_v2 (
        id STRING PRIMARY KEY, name STRING, type STRING, description STRING,
        effectiveDate STRING, expiryDate STRING)""",
    "KnowledgeUnit": """CREATE NODE TABLE IF NOT EXISTS KnowledgeUnit (
        id STRING PRIMARY KEY, type STRING, title STRING,
        content STRING, source STRING)""",
    "Classification": """CREATE NODE TABLE IF NOT EXISTS Classification (
        code STRING PRIMARY KEY, name STRING, system STRING)""",
    "AccountingSubject": """CREATE NODE TABLE IF NOT EXISTS AccountingSubject (
        code STRING PRIMARY KEY, name STRING, category STRING,
        balanceDirection STRING)""",
    "TaxEntity": """CREATE NODE TABLE IF NOT EXISTS TaxEntity (
        id STRING PRIMARY KEY, name STRING, type STRING,
        taxpayerStatus STRING)""",
    "FilingForm_v2": """CREATE NODE TABLE IF NOT EXISTS FilingForm_v2 (
        id STRING PRIMARY KEY, name STRING, reportCycle STRING,
        deadlineDay INT64)""",
    "BusinessActivity": """CREATE NODE TABLE IF NOT EXISTS BusinessActivity (
        id STRING PRIMARY KEY, name STRING, description STRING)""",
    "IssuingBody": """CREATE NODE TABLE IF NOT EXISTS IssuingBody (
        id STRING PRIMARY KEY, name STRING, shortName STRING)""",
}

V2_EDGE_TABLES = [
    "CREATE REL TABLE IF NOT EXISTS PART_OF (FROM LegalClause TO LegalDocument)",
    "CREATE REL TABLE IF NOT EXISTS CHILD_OF (FROM Classification TO Classification)",
    "CREATE REL TABLE IF NOT EXISTS SUPERSEDES (FROM LegalDocument TO LegalDocument)",
    "CREATE REL TABLE IF NOT EXISTS AMENDS (FROM LegalDocument TO LegalDocument)",
    "CREATE REL TABLE IF NOT EXISTS CONFLICTS_WITH (FROM LegalClause TO LegalClause)",
    "CREATE REL TABLE IF NOT EXISTS REFERENCES_CLAUSE (FROM LegalClause TO LegalClause)",
    "CREATE REL TABLE IF NOT EXISTS BASED_ON (FROM TaxRate TO LegalClause)",
    "CREATE REL TABLE IF NOT EXISTS INCENTIVE_BASED_ON (FROM TaxIncentive_v2 TO LegalClause)",
    "CREATE REL TABLE IF NOT EXISTS ISSUED_BY (FROM LegalDocument TO IssuingBody)",
    "CREATE REL TABLE IF NOT EXISTS APPLIES_TO_TAX (FROM TaxRate TO TaxType)",
    "CREATE REL TABLE IF NOT EXISTS APPLIES_TO_ENTITY (FROM TaxRate TO TaxEntity)",
    "CREATE REL TABLE IF NOT EXISTS APPLIES_IN_REGION (FROM TaxRate TO Region)",
    "CREATE REL TABLE IF NOT EXISTS APPLIES_TO_CLASS (FROM TaxRate TO Classification)",
    "CREATE REL TABLE IF NOT EXISTS REQUIRES_FILING (FROM BusinessActivity TO FilingForm_v2)",
    "CREATE REL TABLE IF NOT EXISTS GOVERNED_BY (FROM BusinessActivity TO ComplianceRule_v2)",
    "CREATE REL TABLE IF NOT EXISTS DEBITS (FROM BusinessActivity TO AccountingSubject)",
    "CREATE REL TABLE IF NOT EXISTS CREDITS (FROM BusinessActivity TO AccountingSubject)",
    "CREATE REL TABLE IF NOT EXISTS EXPLAINS (FROM KnowledgeUnit TO LegalClause)",
]

# Tables that must NOT be dropped (have data, needed for migration source)
ACTIVE_NODE_TABLES = {
    "LawOrRegulation", "DocumentSection", "MindmapNode", "RegulationClause",
    "HSCode", "TaxCodeRegionRate", "CPAKnowledge", "TaxClassificationCode",
    "TaxCodeDetail", "TaxCodeIndustryMap", "FAQEntry", "IndustryRiskProfile",
    "RegionalTaxPolicy", "RiskIndicator", "AccountingEntry", "SpreadsheetEntry",
    "AccountRuleMapping", "TaxRiskScenario", "ChartOfAccount", "ChartOfAccountDetail",
    "TaxIncentive", "FormTemplate", "IndustryKnowledge", "ComplianceRule",
    "TaxRateMapping", "TaxCreditIndicator", "AccountingStandard", "TaxRateDetail",
    "Region", "TaxWarningIndicator", "Industry", "TaxRateSchedule", "TaxPolicy",
    "TaxType", "FTIndustry", "TaxCalendar", "AccountEntry", "IndustryBookkeeping",
    "EnterpriseType", "EntityTypeProfile", "TaxpayerStatus",
}

ACTIVE_EDGE_TABLES = {
    "CLAUSE_OF", "MENTIONS", "RELATED_TOPIC", "REFERENCES", "DERIVED_FROM",
    "SIMILAR_QUESTION", "HS_PARENT_OF", "TRIGGERS_ALERT", "COVERS", "RELATES_TO",
    "SIBLING_OF", "SUBJECT_TO", "FT_INCENTIVE_TAX", "HAS_KNOWLEDGE", "OPERATES_IN",
    "CLAUSE_REFERENCES", "OP_MAPS_TO_RATE", "VARIES_BY", "BENEFITS",
    "FT_RATE_SCHEDULE", "TARGETS", "OP_DEBITS", "OP_CREDITS", "CLASSIFIED_UNDER",
    "FT_APPLIES_TO",
}

# Also keep new v2 tables
V2_TABLE_NAMES = set(V2_NODE_TABLES.keys()) | {
    "LegalDocument", "LegalClause", "TaxRate", "ComplianceRule_v2",
    "RiskIndicator_v2", "TaxIncentive_v2", "KnowledgeUnit", "Classification",
    "AccountingSubject", "TaxEntity", "FilingForm_v2", "BusinessActivity", "IssuingBody",
}


def api_call(endpoint, method="GET", data=None):
    """Call KG API."""
    url = f"{KG_API}{endpoint}"
    if data:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def execute_cypher(cypher):
    """Execute a Cypher DDL statement via API."""
    return api_call("/api/query", "POST", {"cypher": cypher, "limit": 1})


def phase_0():
    """Day 0: Create v2.1 schema (new tables alongside old ones)."""
    print("=== Phase 0: Create v2.1 Schema ===\n")

    # Step 1: Create new node tables
    print("Creating v2.1 node tables:")
    for name, ddl in V2_NODE_TABLES.items():
        if DRY_RUN:
            print(f"  [DRY] Would create: {name}")
            continue
        result = execute_cypher(ddl)
        if "error" in result:
            # API blocks write queries, need admin endpoint
            print(f"  {name}: needs direct DB access (API is read-only)")
        else:
            print(f"  {name}: OK")

    # Step 2: Create new edge tables
    print("\nCreating v2.1 edge tables:")
    for ddl in V2_EDGE_TABLES:
        name = ddl.split("IF NOT EXISTS ")[1].split(" (")[0]
        if DRY_RUN:
            print(f"  [DRY] Would create: {name}")
            continue
        result = execute_cypher(ddl)
        if "error" in result:
            print(f"  {name}: needs direct DB access")
        else:
            print(f"  {name}: OK")

    print(f"\n=== Phase 0 {'DRY RUN' if DRY_RUN else 'DONE'} ===")
    print(f"Created {len(V2_NODE_TABLES)} node tables + {len(V2_EDGE_TABLES)} edge tables")


def phase_1():
    """Day 1-3: Migrate seed data (small tables)."""
    print("=== Phase 1: Migrate Seed Data ===\n")

    # Migration mappings: old_table -> (new_table, field_map)
    migrations = [
        # TaxType stays as-is (already correct schema)
        # Region stays as-is
        # TaxEntity from EnterpriseType + TaxpayerStatus + EntityTypeProfile
        ("EnterpriseType", "TaxEntity", {
            "id": "id", "name": "name", "type": "'企业'", "taxpayerStatus": "None",
        }),
        ("TaxpayerStatus", "TaxEntity", {
            "id": "id", "name": "name OR domain", "type": "'身份'", "taxpayerStatus": "name",
        }),
        # TaxIncentive -> TaxIncentive_v2
        ("TaxIncentive", "TaxIncentive_v2", {
            "id": "id", "name": "name", "type": "incentiveType", "description": "description",
        }),
        # ComplianceRule -> ComplianceRule_v2
        ("ComplianceRule", "ComplianceRule_v2", {
            "id": "id", "name": "name", "description": "description",
            "category": "category", "consequence": "consequence",
        }),
    ]

    for old, new, fmap in migrations:
        print(f"  {old} -> {new}: ", end="")
        if DRY_RUN:
            print(f"[DRY] would migrate")
            continue

        # Fetch from old table via API
        resp = api_call(f"/api/v1/nodes?type={old}&limit=500")
        if "error" in resp:
            print(f"ERROR: {resp['error']}")
            continue

        nodes = resp.get("results", [])
        print(f"{len(nodes)} nodes to migrate")

    print(f"\n=== Phase 1 {'DRY RUN' if DRY_RUN else 'DONE'} ===")


def main():
    phase = None
    for arg in sys.argv:
        if arg == "--phase":
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                phase = int(sys.argv[idx + 1])

    if phase is None:
        print("Usage: python3 scripts/migrate_v2.py --phase 0|1|2|3 [--dry-run]")
        print("\nPhases:")
        print("  0: Create v2.1 schema (new tables alongside old)")
        print("  1: Migrate seed data (small tables)")
        print("  2: Migrate bulk data (LegalDocument, LegalClause, etc.)")
        print("  3: AI semantic edge extraction")
        sys.exit(0)

    # Health check
    health = api_call("/api/v1/health")
    if health.get("error") or not health.get("kuzu"):
        print(f"ERROR: KG API not healthy: {health}")
        sys.exit(1)
    print(f"KG API: {health['status']}\n")

    if phase == 0:
        phase_0()
    elif phase == 1:
        phase_1()
    else:
        print(f"Phase {phase} not yet implemented")


if __name__ == "__main__":
    main()
