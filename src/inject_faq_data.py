#!/usr/bin/env python3
"""Inject 1,156 finance/tax FAQ QA pairs into KuzuDB as LawOrRegulation nodes.

Usage:
    python src/inject_faq_data.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def esc(s) -> str:
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    faq_path = Path("data/extracted/faq/finance_tax_faq_1163.json")
    if not faq_path.exists():
        print("ERROR: FAQ file not found")
        sys.exit(1)

    with open(faq_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs = data.get("qa_pairs", data.get("pairs", data.get("questions", [])))
    print(f"Loaded {len(pairs)} QA pairs")

    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    count = 0
    for pair in pairs:
        q = str(pair.get("question", pair.get("q", "")))
        a = str(pair.get("answer", pair.get("a", "")))
        cat = str(pair.get("category", "general"))
        num = pair.get("number", pair.get("id", count + 1))

        if len(q) < 5:
            continue

        nid = f"LR_FAQ_{hashlib.md5(q.encode()).hexdigest()[:8]}"
        title = f"[FAQ-{cat}] {q[:150]}"
        content = f"问：{q}\n答：{a}" if a else f"问：{q}"

        sql = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(nid)}', "
            f"title: '{esc(title)}', "
            f"regulationNumber: 'FAQ-{num}', "
            f"issuingAuthority: 'doc-tax-faq-1163', "
            f"regulationType: 'faq_{esc(cat)}', "
            f"issuedDate: date('2026-01-01'), "
            f"effectiveDate: date('2026-01-01'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'reference', "
            f"hierarchyLevel: 0, "
            f"sourceUrl: 'local://doc-tax/财税实战答疑脑图', "
            f"contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
            f"fullText: '{esc(content[:2000])}', "
            f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
            f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
            f"txTimeCreated: timestamp('2026-03-15 00:00:00'), "
            f"txTimeUpdated: timestamp('2026-03-15 00:00:00')"
            f"}})"
        )

        if args.dry_run:
            count += 1
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception:
                pass

    print(f"OK: Injected {count} FAQ nodes as LawOrRegulation")


if __name__ == "__main__":
    main()
