#!/usr/bin/env python3
"""Inject CPA study material extractions into KuzuDB.

Reads from data/extracted/cpa/ and injects:
- Journal entries -> OP_StandardCase nodes (with CPA exam context)
- Formulas -> into LawOrRegulation as reference material
- Tax rules -> LawOrRegulation

Usage:
    python src/inject_cpa_data.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def esc(s) -> str:
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, text: str) -> str:
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def load_cpa_files(cpa_dir: Path) -> list:
    """Load all CPA extraction JSON files."""
    manifest_path = cpa_dir / "manifest.json"
    if not manifest_path.exists():
        return []
    with open(manifest_path) as f:
        manifest = json.load(f)

    results = []
    for entry in manifest.get("files", []):
        output_file = entry.get("output_file", "")
        if not output_file:
            continue
        fpath = Path(output_file)
        if not fpath.exists():
            fpath = cpa_dir / fpath.name
        if not fpath.exists():
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
            results.append({**entry, "data": data})
        except Exception:
            pass
    return results


def inject_journal_entries(conn, files: list, dry_run: bool) -> int:
    """Inject CPA journal entries as OP_StandardCase nodes."""
    count = 0
    for file_entry in files:
        data = file_entry.get("data", {})
        entries = data.get("journal_entries", [])
        subject = file_entry.get("subject", "accounting")
        label = file_entry.get("label", "")

        for i, entry in enumerate(entries[:50]):  # Cap per file
            if isinstance(entry, str):
                text = entry
                scenario = label
            elif isinstance(entry, dict):
                # CPA format: {title, lines} or {text, scenario}
                lines = entry.get("lines", [])
                text = entry.get("text", "\n".join(lines) if lines else str(entry))
                scenario = entry.get("title", entry.get("scenario", entry.get("context", label)))
            else:
                continue

            if len(str(text)) < 10:
                continue

            case_id = make_id("SC_CPA", f"{label}_{i}")
            sql = (
                f"CREATE (n:OP_StandardCase {{"
                f"id: '{esc(case_id)}', "
                f"name: '{esc(str(scenario)[:80])}', "
                f"standardId: '', clauseRef: '', "
                f"caseType: 'cpa_exam', "
                f"scenario: '{esc(str(scenario)[:200])}', "
                f"correctTreatment: '{esc(str(text)[:500])}', "
                f"commonMistake: '', "
                f"industryRelevance: 'all', "
                f"diffFromSme: false, diffFromIfrs: false, "
                f"diffDescription: '', "
                f"notes: 'source: CPA {esc(subject)} / {esc(label[:50])}'"
                f"}})"
            )

            if dry_run:
                count += 1
            else:
                try:
                    conn.execute(sql)
                    count += 1
                except Exception:
                    pass

    return count


def inject_cpa_references(conn, files: list, dry_run: bool) -> int:
    """Inject CPA key point summaries as LawOrRegulation reference nodes."""
    count = 0
    for file_entry in files:
        data = file_entry.get("data", {})
        subject = file_entry.get("subject", "accounting")
        label = file_entry.get("label", "")

        # Get sections/chapters from the extraction
        sections = data.get("sections", data.get("chapters", []))
        if not sections and data.get("full_text"):
            # Single document without sections - split by pages
            text = data["full_text"]
            # Create one reference node per file
            sections = [{"title": label, "content": text[:3000]}]

        for i, section in enumerate(sections[:30]):
            if isinstance(section, str):
                title = f"CPA {subject} - {label} #{i+1}"
                content = section
            elif isinstance(section, dict):
                title = section.get("title", section.get("heading", f"{label} #{i+1}"))
                content = section.get("content", section.get("text", ""))
            else:
                continue

            if len(str(content)) < 30:
                continue

            nid = make_id("LR_CPA", f"{label}_{i}")
            content_str = str(content)[:2000]

            sql = (
                f"CREATE (n:LawOrRegulation {{"
                f"id: '{esc(nid)}', "
                f"title: '{esc('[CPA-' + subject + '] ' + str(title)[:180])}', "
                f"regulationNumber: '', "
                f"issuingAuthority: 'CPA-exam-{esc(subject)}', "
                f"regulationType: 'cpa_reference', "
                f"issuedDate: date('2021-01-01'), "
                f"effectiveDate: date('2021-01-01'), "
                f"expiryDate: date('2099-12-31'), "
                f"status: 'reference', "
                f"hierarchyLevel: 0, "
                f"sourceUrl: 'local://doc-tax/09CPA学习', "
                f"contentHash: '{hashlib.sha256(content_str.encode()).hexdigest()[:16]}', "
                f"fullText: '{esc(content_str)}', "
                f"validTimeStart: timestamp('2021-01-01 00:00:00'), "
                f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
                f"txTimeCreated: timestamp('2026-03-15 00:00:00'), "
                f"txTimeUpdated: timestamp('2026-03-15 00:00:00')"
                f"}})"
            )

            if dry_run:
                count += 1
            else:
                try:
                    conn.execute(sql)
                    count += 1
                except Exception:
                    pass

    return count


def main():
    parser = argparse.ArgumentParser(description="Inject CPA data into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cpa_dir = Path("data/extracted/cpa")
    files = load_cpa_files(cpa_dir)
    print(f"Loaded {len(files)} CPA extraction files")

    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    print("\n=== Injecting Journal Entries ===")
    n_entries = inject_journal_entries(conn, files, args.dry_run)
    print(f"OK: {n_entries} OP_StandardCase nodes")

    print("\n=== Injecting CPA References ===")
    n_refs = inject_cpa_references(conn, files, args.dry_run)
    print(f"OK: {n_refs} LawOrRegulation nodes")

    print(f"\n=== Total: +{n_entries + n_refs} new nodes ===")


if __name__ == "__main__":
    main()
