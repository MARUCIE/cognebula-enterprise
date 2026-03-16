#!/usr/bin/env python3
"""Inject tax enforcement case data into KuzuDB as LawOrRegulation nodes.

Reads crawled data from data/raw/tax-cases/tax_cases.json and injects as
LawOrRegulation nodes with:
  - regulationType: 'enforcement_case' | 'enforcement_policy' | 'enforcement_qa'
  - hierarchyLevel: 0 (national SAT cases) or 1 (provincial)
  - Structured fields stored in fullText and notes

Creates edges:
  - LawOrRegulation -> TaxType (XL_REGULATES_TAX) for each mentioned tax type
  - LawOrRegulation -> AdministrativeRegion (XL_APPLIES_IN) for provincial cases

Usage:
    python src/inject_tax_cases.py [--db data/finance-tax-graph] [--input data/raw/tax-cases]
    python src/inject_tax_cases.py --dry-run
    python src/inject_tax_cases.py --input data/raw/tax-cases --dry-run
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def esc(s: str) -> str:
    """Escape a string for Cypher literal."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, text: str) -> str:
    """Generate deterministic ID from prefix + text."""
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def parse_date(date_str: str) -> str:
    """Parse a date string into YYYY-MM-DD format."""
    if not date_str:
        return "2026-01-01"
    m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)
    m = re.match(r"(\d{4}-\d{2})", date_str)
    if m:
        return f"{m.group(1)}-01"
    m = re.match(r"(\d{4})/(\d{2})/(\d{2})", date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return "2026-01-01"


# Mapping from source type to regulationType
SOURCE_TO_REG_TYPE = {
    "sat_case_report": "enforcement_case",
    "fgk_enforcement": "enforcement_policy",
    "12366_enforcement": "enforcement_qa",
}

# Province code to AdministrativeRegion ID mapping (uppercase, matching KuzuDB)
PROVINCE_REGION_MAP = {
    "jiangsu": "AR_JIANGSU",
    "zhejiang": "AR_ZHEJIANG",
    "shanghai": "AR_SHANGHAI",
    "tianjin": "AR_TIANJIN",
    "guangdong": "AR_GUANGDONG",
    "shandong": "AR_SHANDONG",
    "beijing": "AR_BEIJING",
    "chongqing": "AR_CHONGQING",
}

# Tax type keyword to TaxType ID mapping (must match existing TaxType nodes)
# Actual IDs verified from KuzuDB: TT_VAT, TT_CIT, TT_PIT, TT_CONSUMPTION, etc.
TAX_TYPE_ID_MAP = {
    "增值税": "TT_VAT",
    "企业所得税": "TT_CIT",
    "个人所得税": "TT_PIT",
    "消费税": "TT_CONSUMPTION",
    "关税": "TT_TARIFF",
    "出口退税": "TT_VAT",  # Export rebate relates to VAT
    "城建税": "TT_URBAN",
    "城市维护建设税": "TT_URBAN",
    "房产税": "TT_PROPERTY",
    "印花税": "TT_STAMP",
    "土地增值税": "TT_LAND_VAT",
    "资源税": "TT_RESOURCE",
    "环保税": "TT_ENVIRONMENT",
    "车辆购置税": "TT_VEHICLE",
    "契税": "TT_DEED",
}


def build_notes_field(item: dict) -> str:
    """Build a structured notes string from enforcement metadata."""
    parts = []

    violation_types = item.get("violation_types", [])
    if violation_types:
        parts.append(f"Violation: {', '.join(violation_types)}")

    penalty_amounts = item.get("penalty_amounts", [])
    if penalty_amounts:
        parts.append(f"Amounts: {', '.join(penalty_amounts)}")

    legal_basis = item.get("legal_basis", [])
    if legal_basis:
        parts.append(f"Legal basis: {'; '.join(legal_basis[:5])}")

    companies = item.get("case_parties_companies", [])
    if companies:
        parts.append(f"Parties: {'; '.join(companies[:5])}")

    persons = item.get("case_parties_persons", [])
    if persons:
        parts.append(f"Persons: {', '.join(persons)}")

    tax_types = item.get("tax_types", [])
    if tax_types:
        parts.append(f"Tax types: {', '.join(tax_types)}")

    search_kw = item.get("search_keyword", "")
    if search_kw:
        parts.append(f"Search keyword: {search_kw}")

    return " | ".join(parts)


def determine_reg_type(item: dict) -> str:
    """Determine regulationType from item source."""
    source = item.get("source", "")
    if source.startswith("provincial_"):
        return "enforcement_provincial"
    return SOURCE_TO_REG_TYPE.get(source, "enforcement_case")


def determine_hierarchy(item: dict) -> int:
    """0 = national (SAT), 1 = provincial."""
    source = item.get("source", "")
    if source.startswith("provincial_"):
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Inject tax enforcement cases into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--input", default="data/raw/tax-cases")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print SQL without executing")
    parser.add_argument("--create-edges", action="store_true",
                        help="Also create edges to TaxType and AdministrativeRegion")
    args = parser.parse_args()

    # Load input data
    input_path = Path(args.input) / "tax_cases.json"
    if not input_path.exists():
        print(f"ERROR: Input file does not exist: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Loaded {len(items)} tax enforcement items from {input_path}")

    if not items:
        print("ERROR: No items found")
        sys.exit(1)

    # Connect to KuzuDB
    conn = None
    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)

    count = 0
    skipped = 0
    edge_count = 0
    seen_ids = set()

    for item in items:
        title = item.get("title", "").strip()
        url = item.get("url", "")
        content = item.get("content", "")
        source = item.get("source", "unknown")
        date_str = item.get("date", "")

        if len(title) < 5:
            skipped += 1
            continue

        # Generate unique ID
        nid = f"LR_enf_{hashlib.md5(f'{source}:{url}'.encode()).hexdigest()[:10]}"
        if nid in seen_ids:
            skipped += 1
            continue
        seen_ids.add(nid)

        date_val = parse_date(date_str)
        reg_type = determine_reg_type(item)
        hierarchy = determine_hierarchy(item)
        authority = item.get("source_authority", "国家税务总局")
        doc_num = item.get("doc_num", "")
        notes = build_notes_field(item)

        # Build full text
        full_text = item.get("full_text", title)
        if not full_text or full_text == title:
            full_text = f"{title}\n\n{content[:2000]}" if content else title

        content_hash = hashlib.sha256(full_text.encode()).hexdigest()[:16]

        sql = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(nid)}', "
            f"title: '{esc(title[:300])}', "
            f"regulationNumber: '{esc(doc_num[:100])}', "
            f"issuingAuthority: '{esc(authority[:200])}', "
            f"regulationType: '{esc(reg_type)}', "
            f"issuedDate: date('{date_val}'), "
            f"effectiveDate: date('{date_val}'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'active', "
            f"hierarchyLevel: {hierarchy}, "
            f"sourceUrl: '{esc(url[:500])}', "
            f"contentHash: '{content_hash}', "
            f"fullText: '{esc(full_text[:2000])}', "
            f"validTimeStart: timestamp('{date_val} 00:00:00'), "
            f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
            f"txTimeCreated: timestamp('2026-03-15 00:00:00'), "
            f"txTimeUpdated: timestamp('2026-03-15 00:00:00')"
            f"}})"
        )

        if args.dry_run:
            if count < 3:
                print(f"\nDRY-RUN SQL:\n{sql[:400]}...")
            count += 1
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception as e:
                err_str = str(e).lower()
                if "already exists" in err_str or "duplicate" in err_str:
                    skipped += 1
                else:
                    print(f"WARN: Failed to inject {nid}: {e}")
                    skipped += 1

        # Create edges if requested
        if args.create_edges and (conn or args.dry_run):
            # TaxType edges: use existing FT_GOVERNED_BY (FROM TaxType TO LawOrRegulation)
            tax_types = item.get("tax_types", [])
            seen_tt = set()
            for tt in tax_types:
                tt_id = TAX_TYPE_ID_MAP.get(tt)
                if not tt_id or tt_id in seen_tt:
                    continue
                seen_tt.add(tt_id)
                edge_sql = (
                    f"MATCH (tt:TaxType {{id: '{esc(tt_id)}'}}), "
                    f"(lr:LawOrRegulation {{id: '{esc(nid)}'}}) "
                    f"CREATE (tt)-[:FT_GOVERNED_BY]->(lr)"
                )
                if args.dry_run:
                    if edge_count < 2:
                        print(f"\nDRY-RUN EDGE SQL:\n{edge_sql[:300]}")
                    edge_count += 1
                else:
                    try:
                        conn.execute(edge_sql)
                        edge_count += 1
                    except Exception:
                        pass  # Edge may already exist or target node missing

    # Print summary
    print(f"\n{'DRY-RUN ' if args.dry_run else ''}SUMMARY:")
    print(f"  Total items loaded: {len(items)}")
    print(f"  Nodes injected: {count}")
    print(f"  Edges created: {edge_count}")
    print(f"  Skipped: {skipped}")

    # By source breakdown
    source_counts = {}
    for item in items:
        src = item.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    print(f"  By source: {json.dumps(source_counts, ensure_ascii=False)}")

    return count


if __name__ == "__main__":
    main()
