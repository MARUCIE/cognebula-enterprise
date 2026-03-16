#!/usr/bin/env python3
"""Inject provincial tax bureau crawl data into KuzuDB as LawOrRegulation nodes.

Reads crawled data from data/raw/20260315-provincial/{province}/ and injects
as LawOrRegulation nodes with:
  - issuingAuthority: the provincial tax bureau name
  - regulationType: 'local_policy'
  - hierarchyLevel: 1 (provincial, below national level 0)

Usage:
    python src/inject_provincial_data.py [--db data/finance-tax-graph] [--input data/raw/20260315-provincial] [--dry-run]
    python src/inject_provincial_data.py --provinces jiangsu shanghai --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Province code -> Chinese authority name mapping
AUTHORITY_MAP = {
    "jiangsu": "国家税务总局江苏省税务局",
    "zhejiang": "国家税务总局浙江省税务局",
    "shanghai": "国家税务总局上海市税务局",
    "tianjin": "国家税务总局天津市税务局",
    "guangdong": "国家税务总局广东省税务局",
    "shandong": "国家税务总局山东省税务局",
    "henan": "国家税务总局河南省税务局",
    "sichuan": "国家税务总局四川省税务局",
    "hubei": "国家税务总局湖北省税务局",
    "hunan": "国家税务总局湖南省税务局",
    "anhui": "国家税务总局安徽省税务局",
    "fujian": "国家税务总局福建省税务局",
    "beijing": "国家税务总局北京市税务局",
    "chongqing": "国家税务总局重庆市税务局",
}


def esc(s: str) -> str:
    """Escape a string for Cypher literal."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def load_provincial_items(input_dir: Path, provinces: list[str] | None = None) -> list[dict]:
    """Load crawled items from provincial JSON files."""
    items = []
    if not input_dir.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        return items

    for prov_dir in sorted(input_dir.iterdir()):
        if not prov_dir.is_dir():
            continue
        province = prov_dir.name
        if provinces and province not in provinces:
            continue

        for json_file in prov_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        item.setdefault("province", province)
                    items.extend(data)
                print(f"OK: Loaded {len(data)} items from {json_file.name} ({province})")
            except Exception as e:
                print(f"WARN: Could not load {json_file}: {e}")

    return items


def parse_date(date_str: str) -> str:
    """Parse a date string into YYYY-MM-DD format, with fallback."""
    if not date_str:
        return "2026-01-01"
    # Already in YYYY-MM-DD
    m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)
    # YYYY-MM format
    m = re.match(r"(\d{4}-\d{2})", date_str)
    if m:
        return f"{m.group(1)}-01"
    return "2026-01-01"


def determine_regulation_type(item: dict) -> str:
    """Determine regulation type from item metadata."""
    item_type = item.get("type", "")
    title = item.get("title", "")

    # Check for common patterns in the type field
    if "policy_interpret" in item_type or "解读" in title:
        return "local_policy_interpretation"
    if "notice" in item_type or "通知公告" in item_type or "公告" in title[:10]:
        return "local_notice"
    if "hot_qa" in item_type or "问答" in item_type:
        return "local_qa"
    if "info_disclosure" in item_type:
        return "local_info_disclosure"

    # Check title patterns for specific document types
    if "办法" in title or "规定" in title or "条例" in title:
        return "local_regulation"
    if "解读" in title:
        return "local_policy_interpretation"
    if "公告" in title:
        return "local_announcement"
    if "通知" in title:
        return "local_notification"

    return "local_policy"


def determine_issuing_authority(item: dict) -> str:
    """Determine issuing authority from item metadata."""
    # Shanghai WAS5 provides explicit issuing authority
    auth = item.get("issuing_authority", "")
    if auth:
        return auth

    # Fall back to province-based authority
    province = item.get("province", "")
    return AUTHORITY_MAP.get(province, f"国家税务总局{province}税务局")


def main():
    parser = argparse.ArgumentParser(description="Inject provincial data into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--input", default="data/raw/20260315-provincial")
    parser.add_argument("--provinces", nargs="*", default=None,
                        help="Only inject specific provinces (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print SQL without executing")
    args = parser.parse_args()

    input_dir = Path(args.input)
    items = load_provincial_items(input_dir, args.provinces)
    print(f"\nLoaded {len(items)} total items from {input_dir}")

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
    seen_ids = set()

    for item in items:
        title = item.get("title", "").strip()
        url = item.get("url", "")
        content = item.get("content", "")
        province = item.get("province", "unknown")
        date_str = item.get("date", "")
        doc_num = item.get("doc_num", "")

        if len(title) < 5:
            skipped += 1
            continue

        # Generate unique ID based on province + URL
        nid = f"LR_prov_{province}_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        if nid in seen_ids:
            skipped += 1
            continue
        seen_ids.add(nid)

        # Determine metadata
        date_val = parse_date(date_str)
        reg_type = determine_regulation_type(item)
        issuing_auth = determine_issuing_authority(item)

        # Build full text: title + content
        full_text = title
        if content:
            full_text = f"{title}\n\n{content[:1800]}"

        content_hash = hashlib.sha256(full_text.encode()).hexdigest()[:16]

        sql = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{esc(nid)}', "
            f"title: '{esc(title[:300])}', "
            f"regulationNumber: '{esc(doc_num[:100])}', "
            f"issuingAuthority: '{esc(issuing_auth)}', "
            f"regulationType: '{esc(reg_type)}', "
            f"issuedDate: date('{date_val}'), "
            f"effectiveDate: date('{date_val}'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'active', "
            f"hierarchyLevel: 1, "
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
                print(f"\nDRY-RUN SQL:\n{sql[:300]}...")
            count += 1
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    skipped += 1
                else:
                    print(f"WARN: Failed to inject {nid}: {e}")
                    skipped += 1

    # Print summary
    print(f"\n{'DRY-RUN ' if args.dry_run else ''}SUMMARY:")
    print(f"  Total items loaded: {len(items)}")
    print(f"  Nodes injected: {count}")
    print(f"  Skipped: {skipped}")

    # Per-province breakdown
    province_counts = {}
    for item in items:
        p = item.get("province", "unknown")
        province_counts[p] = province_counts.get(p, 0) + 1
    print(f"  By province: {json.dumps(province_counts, ensure_ascii=False)}")

    return count


if __name__ == "__main__":
    main()
