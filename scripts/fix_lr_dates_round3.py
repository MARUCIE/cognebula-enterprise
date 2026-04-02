#!/usr/bin/env python3
"""Round 3: Extract effectiveDate from LR titles and issuedDate fallback.

Previous rounds:
- R1: fullText summary regex → 15,333 nodes (61.1%)
- R2: URL path + regulation number → 7,081 nodes (77.8%)
- R3 (this): title year extraction + issuedDate fallback

Connects directly to KuzuDB (API must be stopped).
"""
import re
import kuzu
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fix_lr_dates_r3")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"


def extract_date_from_title(title: str) -> str:
    """Extract a date from title patterns like '关于2023年度...' or '2024年第X号'."""
    if not title:
        return ""

    # Pattern 1: Full date YYYY年M月D日
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # Pattern 2: YYYY年M月 (no day → use 1st)
    m = re.search(r'(\d{4})年(\d{1,2})月', title)
    if m and 2000 <= int(m.group(1)) <= 2030:
        return f"{m.group(1)}-{int(m.group(2)):02d}-01"

    # Pattern 3: YYYY年度 or YYYY年 (use Jan 1)
    m = re.search(r'(\d{4})年度?', title)
    if m and 2000 <= int(m.group(1)) <= 2030:
        return f"{m.group(1)}-01-01"

    # Pattern 4: Bare 4-digit year at word boundary
    m = re.search(r'\b(20[0-2]\d)\b', title)
    if m:
        return f"{m.group(1)}-01-01"

    return ""


def main():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Count current state
    r = conn.execute("MATCH (lr:LawOrRegulation) WHERE lr.effectiveDate IS NULL RETURN count(lr)")
    null_count = r.get_next()[0]
    r = conn.execute("MATCH (lr:LawOrRegulation) RETURN count(lr)")
    total = r.get_next()[0]
    log.info("Before: %d/%d have effectiveDate (%.1f%%), %d remaining",
             total - null_count, total, (total - null_count) / total * 100, null_count)

    if null_count == 0:
        log.info("All records have effectiveDate, nothing to do")
        del conn; del db
        return

    # Fetch all null records
    r = conn.execute(
        "MATCH (lr:LawOrRegulation) WHERE lr.effectiveDate IS NULL "
        "RETURN lr.id, lr.title, lr.issuedDate, lr.sourceUrl, lr.regulationNumber"
    )
    records = []
    while r.has_next():
        records.append(r.get_next())
    log.info("Fetched %d null-date records", len(records))

    # Strategy 1: Extract from title
    title_fixed = 0
    issued_fixed = 0
    url_fixed = 0

    for lr_id, title, issued_date, source_url, reg_num in records:
        date_str = ""

        # Try title extraction first
        date_str = extract_date_from_title(title or "")

        # Fallback: issuedDate if available
        if not date_str and issued_date:
            date_str = str(issued_date)[:10]
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                issued_fixed += 1
            else:
                date_str = ""

        if date_str and re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            try:
                conn.execute(
                    f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{lr_id}' "
                    f"SET lr.effectiveDate = date('{date_str}')"
                )
                if not issued_date:
                    title_fixed += 1
                # else counted as issued_fixed above
            except Exception as e:
                log.warning("Failed to set date for %s: %s", lr_id, e)

    # Recount
    r = conn.execute("MATCH (lr:LawOrRegulation) WHERE lr.effectiveDate IS NULL RETURN count(lr)")
    new_null = r.get_next()[0]
    fixed = null_count - new_null

    log.info("Round 3 results:")
    log.info("  Title extraction: %d", title_fixed)
    log.info("  issuedDate fallback: %d", issued_fixed)
    log.info("  Total fixed: %d", fixed)
    log.info("After: %d/%d have effectiveDate (%.1f%%)",
             total - new_null, total, (total - new_null) / total * 100)

    del conn
    del db


if __name__ == "__main__":
    main()
