#!/usr/bin/env python3
"""Inject chinaacc.com crawled articles into KuzuDB as LawOrRegulation nodes.

Reads crawled JSON from data/raw/20260315-chinaacc-v2/ and injects articles
as knowledge nodes for the finance/tax knowledge base.

Usage:
    python src/inject_chinaacc_data.py [--db data/finance-tax-graph] [--input data/raw/20260315-chinaacc-v2] [--dry-run]
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def esc(s: str) -> str:
    """Escape string for Cypher query."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


# Map section names to regulation types for the knowledge graph
SECTION_TO_REG_TYPE = {
    "accounting_": "chinaacc_accounting",
    "cpa_": "chinaacc_cpa",
    "junior_": "chinaacc_junior_accounting",
    "senior_": "chinaacc_senior_accounting",
}

# Map section names to issuing authority labels
SECTION_TO_AUTHORITY = {
    "accounting_tax_affairs": "chinaacc-tax-practice",
    "accounting_tax_policy": "chinaacc-tax-policy",
    "accounting_tax_theory": "chinaacc-tax-theory",
    "accounting_standards": "chinaacc-accounting-standards",
    "accounting_settlement": "chinaacc-tax-settlement",
    "accounting_digital_tax": "chinaacc-digital-tax",
    "accounting_gst": "chinaacc-personal-tax",
    "accounting_tax_planning": "chinaacc-tax-reform",
}


def _reg_type(section: str) -> str:
    """Determine regulation type from section name."""
    for prefix, rtype in SECTION_TO_REG_TYPE.items():
        if section.startswith(prefix):
            return rtype
    return "chinaacc_article"


def _authority(section: str) -> str:
    """Determine issuing authority from section name."""
    return SECTION_TO_AUTHORITY.get(section, "chinaacc")


def find_json_files(input_dir: Path) -> list:
    """Find all JSON data files (not stats) in input directory."""
    files = []
    for root, dirs, fnames in os.walk(input_dir):
        for f in fnames:
            if f.endswith(".json") and not f.startswith("stats"):
                files.append(Path(root) / f)
    return sorted(files)


def load_articles(input_dir: Path) -> list:
    """Load articles from all JSON files."""
    items = []
    for fpath in find_json_files(input_dir):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict):
                for key in ["items", "articles", "results", "data"]:
                    if key in data and isinstance(data[key], list):
                        items.extend(data[key])
                        break
        except Exception as e:
            print(f"WARN: Could not load {fpath}: {e}")
    return items


def main():
    parser = argparse.ArgumentParser(description="Inject chinaacc articles into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph",
                        help="KuzuDB database path")
    parser.add_argument("--input", default="data/raw/20260315-chinaacc-v2",
                        help="Input directory with crawled JSON")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing to DB")
    parser.add_argument("--batch-size", type=int, default=500,
                        help="Commit every N records")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists():
        # Try to find a matching directory
        for candidate in input_dir.parent.glob("*chinaacc*"):
            if candidate.is_dir():
                input_dir = candidate
                print(f"NOTE: Using {input_dir}")
                break

    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    articles = load_articles(input_dir)
    print(f"Loaded {len(articles)} articles from {input_dir}")

    if not articles:
        print("ERROR: No articles found")
        sys.exit(1)

    # Deduplicate by URL
    seen = set()
    unique = []
    for art in articles:
        url = art.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(art)
    articles = unique
    print(f"After dedup: {len(articles)} unique articles")

    # Print section breakdown
    by_section = {}
    for art in articles:
        sec = art.get("section", "unknown")
        by_section[sec] = by_section.get(sec, 0) + 1
    print("\nSection breakdown:")
    for sec in sorted(by_section, key=by_section.get, reverse=True):
        print(f"  {sec}: {by_section[sec]}")
    print()

    if args.dry_run:
        print("DRY RUN: Would inject %d articles" % len(articles))
        return

    import kuzu
    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    count = 0
    skipped = 0
    errors = []

    for i, art in enumerate(articles):
        title = str(art.get("title", ""))
        url = str(art.get("url", ""))
        content = str(art.get("content", ""))
        section = str(art.get("section", ""))
        label = str(art.get("label", ""))
        date_str = str(art.get("date", ""))

        if len(title) < 3 and len(content) < 10:
            skipped += 1
            continue

        # Build node ID
        nid = f"LR_chinaacc_{hashlib.md5(url.encode()).hexdigest()[:10]}"

        # Parse date
        date_val = "2026-01-01"
        if date_str and len(date_str) >= 10:
            try:
                # Validate date format
                parts = date_str[:10].split("-")
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    date_val = date_str[:10]
            except Exception:
                pass

        reg_type = _reg_type(section)
        authority = _authority(section)

        # Build full text: title + label + content
        full_text = f"[{label}] {title}"
        if content:
            full_text += f"\n{content}"
        full_text = full_text[:2500]

        display_title = f"[chinaacc] {title[:180]}" if title else f"[chinaacc] {label}"

        sql = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(nid)}', "
            f"title: '{esc(display_title)}', "
            f"regulationNumber: 'chinaacc-{esc(section)}-{hashlib.md5(url.encode()).hexdigest()[:6]}', "
            f"issuingAuthority: '{esc(authority)}', "
            f"regulationType: '{esc(reg_type)}', "
            f"issuedDate: date('{date_val}'), "
            f"effectiveDate: date('{date_val}'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'active', "
            f"hierarchyLevel: 0, "
            f"sourceUrl: '{esc(url)}', "
            f"contentHash: '{hashlib.sha256(full_text.encode()).hexdigest()[:16]}', "
            f"fullText: '{esc(full_text)}', "
            f"validTimeStart: timestamp('{date_val} 00:00:00'), "
            f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
            f"txTimeCreated: timestamp('2026-03-15 00:00:00'), "
            f"txTimeUpdated: timestamp('2026-03-15 00:00:00')"
            f"}})"
        )

        try:
            conn.execute(sql)
            count += 1
        except Exception as e:
            err_msg = str(e)
            if "already exists" in err_msg.lower() or "duplicate" in err_msg.lower():
                skipped += 1
            else:
                skipped += 1
                if len(errors) < 10:
                    errors.append(f"  {nid}: {err_msg[:100]}")

        if (i + 1) % 500 == 0:
            print(f"  Progress: {i + 1}/{len(articles)}, injected={count}, skipped={skipped}")

    print(f"\nOK: Injected {count} chinaacc article nodes, skipped {skipped}")
    if errors:
        print(f"Sample errors ({len(errors)}):")
        for e in errors:
            print(e)

    return count


if __name__ == "__main__":
    main()
