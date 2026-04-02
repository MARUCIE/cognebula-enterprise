#!/usr/bin/env python3
"""Round 3b: Aggressive date extraction from fullText AI summaries."""
import kuzu
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fix_dates_r3b")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

def main():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    r = conn.execute("MATCH (lr:LawOrRegulation) WHERE lr.effectiveDate IS NULL RETURN count(lr)")
    null_before = r.get_next()[0]
    r = conn.execute("MATCH (lr:LawOrRegulation) RETURN count(lr)")
    total = r.get_next()[0]
    log.info("Before: %d/%d (%.1f%%), %d remaining", total - null_before, total, (total-null_before)/total*100, null_before)

    r = conn.execute(
        "MATCH (lr:LawOrRegulation) "
        "WHERE lr.effectiveDate IS NULL AND lr.fullText IS NOT NULL AND size(lr.fullText) > 50 "
        "RETURN lr.id, lr.fullText, lr.regulationType"
    )
    records = []
    while r.has_next():
        records.append(r.get_next())
    log.info("Fetched %d candidates", len(records))

    fixed = 0
    for lr_id, text, rtype in records:
        if not text:
            continue
        if rtype and str(rtype).startswith("工具"):
            continue

        date = ""
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
        if m and 1990 <= int(m.group(1)) <= 2030:
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        else:
            m = re.search(r'(\d{4})年(\d{1,2})月', text)
            if m and 1990 <= int(m.group(1)) <= 2030:
                date = f"{m.group(1)}-{int(m.group(2)):02d}-01"

        if date and re.match(r'\d{4}-\d{2}-\d{2}', date):
            try:
                escaped_id = lr_id.replace("'", "\\'")
                conn.execute(
                    f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{escaped_id}' "
                    f"SET lr.effectiveDate = date('{date}')"
                )
                fixed += 1
            except Exception as e:
                pass

    r = conn.execute("MATCH (lr:LawOrRegulation) WHERE lr.effectiveDate IS NULL RETURN count(lr)")
    null_after = r.get_next()[0]
    log.info("R3b: fixed %d, After: %d/%d (%.1f%%)", fixed, total - null_after, total, (total-null_after)/total*100)

    del conn; del db

if __name__ == "__main__":
    main()
