#!/usr/bin/env python3
"""Inject Know-Arc approved triples into CogNebula KG.

Pipeline: Know-Arc (expert review) → CSV → kg-node COPY FROM → CogNebula KG

This script:
1. Reads Know-Arc result JSON files
2. Maps entity types to CogNebula ontology v3.1 node tables
3. Maps relationships to CogNebula edge tables
4. Generates CSV files for bulk import
5. Pushes to kg-node via SCP + SSH execution

Usage:
    python3 scripts/inject_know_arc.py [--dry-run] [--results-dir PATH]
"""
import json
import csv
import os
import sys
import hashlib
from pathlib import Path
from typing import Optional

# CogNebula v3.1 ontology mapping
ENTITY_TO_NODE_TABLE = {
    # Direct mappings
    "TaxRate": "TaxRate",
    "PrepaymentTaxRate": "TaxRate",
    "TaxType": "TaxType",
    "TaxEntity": "TaxEntity",
    "RealEstateCompany": "TaxEntity",
    "Company": "TaxEntity",
    "Enterprise": "TaxEntity",
    "AccountingSubject": "AccountingSubject",
    "ContractLiability": "AccountingSubject",
    "AccountEntry": "AccountingSubject",
    "FilingForm": "FilingFormV2",
    "TaxDeclaration": "FilingFormV2",
    "ComplianceRule": "ComplianceRuleV2",
    "TaxPolicy": "ComplianceRuleV2",
    "RiskIndicator": "RiskIndicatorV2",
    "BusinessActivity": "BusinessActivity",
    "TaxIncentive": "TaxIncentiveV2",
    "LegalDocument": "LegalDocument",
    "Regulation": "LegalDocument",
    "Region": "Region",
    "Classification": "Classification",
    "Industry": "Classification",
    "IssuingBody": "IssuingBody",
    # Know-Arc generated entity types
    "ValueAddedTax": "TaxType",
    "LandValueAddedTax": "TaxType",
    "CorporateIncomeTax": "TaxType",
    "PersonalIncomeTax": "TaxType",
    "StampDuty": "TaxType",
    "ConsumptionTax": "TaxType",
    "UrbanMaintenanceTax": "TaxType",
    "EducationSurcharge": "TaxType",
    "SmallProfitEnterprise": "TaxEntity",
    "GeneralTaxpayer": "TaxEntity",
    "SmallScaleTaxpayer": "TaxEntity",
    "TaxAuthority": "IssuingBody",
    "AccountingTreatment": "AccountingSubject",
    "TaxDeclarationForm": "FilingFormV2",
    "Regulation": "LegalDocument",
    "PreSaleRevenue": "BusinessActivity",
}

RELATION_TO_EDGE_TABLE = {
    # Direct mappings
    "APPLIES_TO": "APPLIES_TO_TAX",
    "APPLIES_TO_TAX": "APPLIES_TO_TAX",
    "BASED_ON": "BASED_ON",
    "GOVERNED_BY": "GOVERNED_BY",
    "GOVERNED_BY_TAX_LAW": "GOVERNED_BY",
    "GOVERNED_BY_ACCOUNTING_STANDARD": "GOVERNED_BY",
    "GOVERNS": "GOVERNED_BY",
    "REQUIRES_FILING": "REQUIRES_FILING",
    "FILES": "REQUIRES_FILING",
    "INTERPRETS": "INTERPRETS",
    "WARNS_ABOUT": "WARNS_ABOUT",
    "TRIGGERS_TAX": "TRIGGERS_TAX",
    "DEBITS": "DEBITS_V2",
    "CREDITS": "CREDITS_V2",
    # Know-Arc generated predicates
    "PRE_PAYS": "TRIGGERS_TAX",
    "CALCULATES_AS": "APPLIES_TO_TAX",
    "RECOGNIZED_AS": "MAPS_TO_ACCOUNT",
    "MUST_FILE": "REQUIRES_FILING",
    "SUBJECT_TO": "GOVERNED_BY",
    "QUALIFIES_FOR": "INCENTIVE_FOR_TAX",
    "DEFINES_TAX_TREATMENT_FOR": "GOVERNED_BY",
    "APPLIES_METHOD": "GOVERNED_BY",
    "APPLIES_ACCOUNTING_TREATMENT": "GOVERNED_BY",
    "APPLIES_TAX_TREATMENT": "GOVERNED_BY",
    "REQUIRES_PREPAYMENT_FOR": "TRIGGERS_TAX",
    "REQUIRES_PREPAYMENT_BASED_ON": "TRIGGERS_TAX",
    "REQUIRES_COMPLIANCE_BY": "GOVERNED_BY",
    "ESTABLISHES_RULE_FOR": "RULE_FOR_TAX",
    "DEFINES_BENEFIT_RULE": "INCENTIVE_FOR_TAX",
    "RESULTS_IN_TAX": "TRIGGERS_TAX",
    "GUIDES_TAX_TREATMENT": "GOVERNED_BY",
    "CLASSIFIED_AS": "APPLIES_TO_CLASS",
    "USES_RATE": "APPLIES_TO_TAX",
    "CALCULATES": "APPLIES_TO_TAX",
    "CALCULATED_BASED_ON": "BASED_ON",
    "CALCULATED_BY": "BASED_ON",
}


def generate_id(entity_type: str, name: str) -> str:
    """Generate deterministic ID for a Know-Arc entity."""
    raw = f"KA_{entity_type}_{name}"
    return f"KA_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


def process_result_file(filepath: Path) -> tuple[list, list]:
    """Process a single Know-Arc result file, return (nodes, edges)."""
    with open(filepath) as f:
        data = json.load(f)

    nodes = []
    edges = []
    entity_ids = {}  # name -> (id, table)

    # Process entities from ontology
    ontology = data.get("ontology", {})
    for ent in ontology.get("entity_types", []):
        name = ent["name"]
        table = ENTITY_TO_NODE_TABLE.get(name)
        if not table:
            continue

        eid = generate_id(name, ent.get("description_zh", name))
        entity_ids[name] = (eid, table)
        nodes.append({
            "id": eid,
            "table": table,
            "name": ent.get("description_zh", name),
            "source": "know-arc",
        })

    # Process triples
    for triple in data.get("triples", []):
        subject_type = triple.get("subject_type", "")
        object_type = triple.get("object_type", "")
        relation = triple.get("predicate", triple.get("relation", ""))

        edge_table = RELATION_TO_EDGE_TABLE.get(relation)
        if not edge_table:
            continue

        subject_info = entity_ids.get(subject_type)
        object_info = entity_ids.get(object_type)
        if not subject_info or not object_info:
            continue

        edges.append({
            "from_id": subject_info[0],
            "from_table": subject_info[1],
            "to_id": object_info[0],
            "to_table": object_info[1],
            "edge_table": edge_table,
        })

    return nodes, edges


def main():
    dry_run = "--dry-run" in sys.argv

    results_dir = Path("/Users/mauricewen/Projects/24-know-arc/data/results")
    for arg in sys.argv:
        if arg.startswith("--results-dir="):
            results_dir = Path(arg.split("=", 1)[1])

    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        sys.exit(1)

    result_files = sorted(results_dir.glob("result_*.json"))
    print(f"Found {len(result_files)} Know-Arc result files")

    all_nodes = []
    all_edges = []
    for fp in result_files:
        nodes, edges = process_result_file(fp)
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        if nodes or edges:
            print(f"  {fp.name}: {len(nodes)} nodes, {len(edges)} edges")

    # Deduplicate
    seen_nodes = set()
    unique_nodes = []
    for n in all_nodes:
        key = (n["table"], n["id"])
        if key not in seen_nodes:
            seen_nodes.add(key)
            unique_nodes.append(n)

    seen_edges = set()
    unique_edges = []
    for e in all_edges:
        key = (e["edge_table"], e["from_id"], e["to_id"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    print(f"\nTotal: {len(unique_nodes)} unique nodes, {len(unique_edges)} unique edges")

    if dry_run:
        print("\n[DRY RUN] Would inject:")
        for n in unique_nodes:
            print(f"  NODE {n['table']}: {n['id']} = {n['name']}")
        for e in unique_edges:
            print(f"  EDGE {e['edge_table']}: {e['from_id']} -> {e['to_id']}")
        return

    if not unique_nodes and not unique_edges:
        print("Nothing to inject.")
        return

    # Generate CSV files
    csv_dir = Path("/Users/mauricewen/Projects/cognebula-enterprise/data/know_arc_inject")
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Group nodes by table
    nodes_by_table = {}
    for n in unique_nodes:
        nodes_by_table.setdefault(n["table"], []).append(n)

    for table, nodes in nodes_by_table.items():
        csv_path = csv_dir / f"nodes_{table.lower()}.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            for n in nodes:
                w.writerow([n["id"], n["name"]])
        print(f"  CSV: {csv_path.name} ({len(nodes)} rows)")

    # Group edges by table
    edges_by_table = {}
    for e in unique_edges:
        edges_by_table.setdefault(e["edge_table"], []).append(e)

    for table, edges in edges_by_table.items():
        csv_path = csv_dir / f"edges_{table.lower()}.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            for e in edges:
                w.writerow([e["from_id"], e["to_id"]])
        print(f"  CSV: {csv_path.name} ({len(edges)} rows)")

    print(f"\nCSV files ready in: {csv_dir}")
    print("Next: SCP to kg-node + run COPY FROM import")


if __name__ == "__main__":
    main()
