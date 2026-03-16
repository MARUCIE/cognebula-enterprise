#!/usr/bin/env python3
"""Inject 76 compliance rules + 109 form templates into KuzuDB.

Data sources:
- data/extracted/financial_templates/compliance_rules.json (76 ComplianceRule records)
- data/extracted/financial_templates/form_templates.json (109 FormTemplate records)

ComplianceRule table already exists (8 rows). New records use the existing schema.
FormTemplate table is created if not present.

Usage:
    python src/inject_compliance_data.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def esc(s) -> str:
    """Escape string for Cypher single-quoted literals."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, text: str) -> str:
    """Generate deterministic ID from prefix + text."""
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


# ---------------------------------------------------------------------------
# ComplianceRule injection
# ---------------------------------------------------------------------------

def inject_compliance_rules(conn, dry_run: bool) -> int:
    """Inject 76 compliance rules into the existing ComplianceRule table.

    Maps extracted fields to existing ComplianceRule schema:
      id, name, ruleCode, category, conditionDescription, conditionFormula,
      requiredAction, violationConsequence, severityLevel, sourceRegulationId,
      sourceClause, applicableTaxTypes, applicableEntityTypes,
      effectiveFrom(DATE), effectiveUntil(DATE), autoDetectable(BOOL),
      detectionQuery, notes, confidence(DOUBLE)
    """
    path = Path("data/extracted/financial_templates/compliance_rules.json")
    if not path.exists():
        print(f"WARN: {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    count = 0
    skipped = 0
    for idx, rec in enumerate(rules):
        name = str(rec.get("name", ""))
        if not name:
            skipped += 1
            continue

        chapter_num = int(rec.get("chapter_number", 0))
        chapter_name = str(rec.get("chapter_name", ""))
        category = str(rec.get("category", ""))
        source_file = str(rec.get("source_file", ""))
        article_count = int(rec.get("article_count", 0))
        key_reqs = rec.get("key_requirements", [])

        # Build deterministic ID from source file path
        source_path = str(rec.get("source_path", name))
        rid = make_id("CR_FT", source_path)
        rule_code = f"CR-FT-{chapter_num:02d}-{idx+1:03d}"

        # First 3 key requirements as condition description
        cond_desc = " | ".join(str(r)[:200] for r in key_reqs[:3])
        if len(cond_desc) > 800:
            cond_desc = cond_desc[:800]

        # Full key requirements as notes (truncated)
        all_reqs = " || ".join(str(r)[:300] for r in key_reqs)
        if len(all_reqs) > 2000:
            all_reqs = all_reqs[:2000]

        sql = (
            f"CREATE (n:ComplianceRule {{"
            f"id: '{esc(rid)}', "
            f"name: '{esc(name[:120])}', "
            f"ruleCode: '{esc(rule_code)}', "
            f"category: '{esc(category)}', "
            f"conditionDescription: '{esc(cond_desc)}', "
            f"conditionFormula: '', "
            f"requiredAction: 'ch{chapter_num} {esc(chapter_name)}: {article_count} articles', "
            f"violationConsequence: '', "
            f"severityLevel: 'reference', "
            f"sourceRegulationId: '{esc(source_file)}', "
            f"sourceClause: '{esc(source_path[:300])}', "
            f"applicableTaxTypes: '', "
            f"applicableEntityTypes: 'enterprise', "
            f"effectiveFrom: date('2026-01-01'), "
            f"effectiveUntil: date('2099-12-31'), "
            f"autoDetectable: false, "
            f"detectionQuery: '', "
            f"notes: '{esc(all_reqs)}', "
            f"confidence: 0.85"
            f"}})"
        )

        if dry_run:
            count += 1
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception as e:
                print(f"  WARN: Failed rule '{name}': {e}")
                skipped += 1

    print(f"OK: Injected {count} compliance rules (skipped {skipped})")
    return count


# ---------------------------------------------------------------------------
# FormTemplate table creation + injection
# ---------------------------------------------------------------------------

DDL_FORM_TEMPLATE = """
CREATE NODE TABLE IF NOT EXISTS FormTemplate (
    id STRING,
    name STRING,
    category STRING,
    chapterNumber INT64,
    chapterName STRING,
    fieldCount INT64,
    tableCount INT64,
    fields STRING,
    purpose STRING,
    sourceFile STRING,
    sourcePath STRING,
    notes STRING,
    confidence DOUBLE,
    PRIMARY KEY (id)
)
"""


def inject_form_templates(conn, dry_run: bool) -> int:
    """Create FormTemplate table and inject 109 form template records."""
    path = Path("data/extracted/financial_templates/form_templates.json")
    if not path.exists():
        print(f"WARN: {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        forms = json.load(f)

    # Create table
    if not dry_run:
        try:
            conn.execute(DDL_FORM_TEMPLATE)
            print("OK: FormTemplate table created (or already exists)")
        except Exception as e:
            print(f"WARN: DDL issue: {e}")

    count = 0
    skipped = 0
    for idx, rec in enumerate(forms):
        name = str(rec.get("name", ""))
        if not name:
            skipped += 1
            continue

        chapter_num = int(rec.get("chapter_number", 0))
        chapter_name = str(rec.get("chapter_name", ""))
        category = str(rec.get("category", ""))
        source_file = str(rec.get("source_file", ""))
        source_path = str(rec.get("source_path", name))
        field_count = int(rec.get("field_count", 0))
        table_count = int(rec.get("table_count", 0))
        purpose = str(rec.get("purpose", ""))[:500]

        # Serialize fields list as pipe-separated string
        fields_raw = rec.get("fields", [])
        fields_str = " | ".join(str(f)[:100] for f in fields_raw)
        if len(fields_str) > 1000:
            fields_str = fields_str[:1000]

        # Paragraphs as notes
        paragraphs = rec.get("paragraphs", [])
        notes_str = " || ".join(str(p)[:200] for p in paragraphs)
        if len(notes_str) > 1500:
            notes_str = notes_str[:1500]

        fid = make_id("FT", source_path)

        sql = (
            f"CREATE (n:FormTemplate {{"
            f"id: '{esc(fid)}', "
            f"name: '{esc(name[:120])}', "
            f"category: '{esc(category)}', "
            f"chapterNumber: {chapter_num}, "
            f"chapterName: '{esc(chapter_name)}', "
            f"fieldCount: {field_count}, "
            f"tableCount: {table_count}, "
            f"fields: '{esc(fields_str)}', "
            f"purpose: '{esc(purpose)}', "
            f"sourceFile: '{esc(source_file)}', "
            f"sourcePath: '{esc(source_path[:300])}', "
            f"notes: '{esc(notes_str)}', "
            f"confidence: 0.80"
            f"}})"
        )

        if dry_run:
            count += 1
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception as e:
                print(f"  WARN: Failed form '{name}': {e}")
                skipped += 1

    print(f"OK: Injected {count} form templates (skipped {skipped})")
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Inject compliance rules + form templates")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")
    args = parser.parse_args()

    if not args.dry_run:
        try:
            import kuzu
        except ImportError:
            print("ERROR: kuzu not installed. Run: pip install kuzu")
            sys.exit(1)
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    total = 0

    print("=== Injecting Compliance Rules (76) ===")
    total += inject_compliance_rules(conn, args.dry_run)

    print("\n=== Injecting Form Templates (109) ===")
    total += inject_form_templates(conn, args.dry_run)

    print(f"\n=== Grand Total: +{total} new nodes ===")


if __name__ == "__main__":
    main()
