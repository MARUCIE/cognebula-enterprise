#!/usr/bin/env python3
"""Inject 12366 tax hotline QA data into KuzuDB as LawOrRegulation nodes.

Reads crawled 12366 data from data/raw/*-12366*/ and injects QA pairs.

Usage:
    python src/inject_12366_data.py [--db data/finance-tax-graph] [--input data/raw/20260315-12366-full] [--dry-run]
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def esc(s) -> str:
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def find_json_files(input_dir: Path) -> list:
    """Find all JSON files in input directory (may be nested)."""
    files = []
    for root, dirs, fnames in os.walk(input_dir):
        for f in fnames:
            if f.endswith(".json"):
                files.append(Path(root) / f)
    return files


def load_qa_items(input_dir: Path) -> list:
    """Load QA items from all JSON files."""
    items = []
    for fpath in find_json_files(input_dir):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Handle different formats: list or dict with items/qa_pairs key
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict):
                for key in ["items", "qa_pairs", "results", "data"]:
                    if key in data and isinstance(data[key], list):
                        items.extend(data[key])
                        break
        except Exception as e:
            print(f"WARN: Could not load {fpath}: {e}")
    return items


def main():
    parser = argparse.ArgumentParser(description="Inject 12366 QA into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--input", default="data/raw/20260315-12366-full")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists():
        # Try nested
        for candidate in input_dir.parent.glob("*12366*"):
            if candidate.is_dir():
                input_dir = candidate
                break

    items = load_qa_items(input_dir)
    print(f"Loaded {len(items)} QA items from {input_dir}")

    if not items:
        print("ERROR: No items found")
        sys.exit(1)

    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    count = 0
    skipped = 0
    for item in items:
        # Extract fields (12366 API format)
        question = str(item.get("RDWTBT", item.get("question", item.get("title", ""))))
        answer = str(item.get("ZLCLJNR", item.get("answer", item.get("content", ""))))
        code = str(item.get("BH", item.get("code", item.get("id", ""))))
        category = str(item.get("LBMC", item.get("category", "")))
        date_str = str(item.get("FBSJ", item.get("date", "2026-01-01")))

        if len(question) < 5:
            skipped += 1
            continue

        nid = f"LR_12366_{hashlib.md5(question.encode()).hexdigest()[:8]}"

        # Clean answer HTML tags
        import re
        answer_clean = re.sub(r"<[^>]+>", "", answer).strip()

        title = f"[12366-QA] {question[:180]}"
        content = f"问：{question}\n答：{answer_clean[:1800]}" if answer_clean else f"问：{question}"

        # Parse date
        try:
            if len(date_str) >= 10:
                date_val = date_str[:10]
            else:
                date_val = "2026-01-01"
        except Exception:
            date_val = "2026-01-01"

        # Extract category for regulationType
        cat_parts = category.split("->") if "->" in category else [category]
        reg_type = f"12366_qa_{esc(cat_parts[-1].strip()[:30])}" if cat_parts else "12366_qa"

        sql = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(nid)}', "
            f"title: '{esc(title)}', "
            f"regulationNumber: '12366-{esc(code)}', "
            f"issuingAuthority: '12366-tax-hotline', "
            f"regulationType: '{reg_type}', "
            f"issuedDate: date('{date_val}'), "
            f"effectiveDate: date('{date_val}'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'active', "
            f"hierarchyLevel: 0, "
            f"sourceUrl: 'https://12366.chinatax.gov.cn', "
            f"contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
            f"fullText: '{esc(content[:2000])}', "
            f"validTimeStart: timestamp('{date_val} 00:00:00'), "
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
                skipped += 1

    print(f"OK: Injected {count} 12366 QA nodes, skipped {skipped}")
    return count


if __name__ == "__main__":
    main()
