#!/usr/bin/env python3
"""Generate compliance obligation matrix: TaxType x Industry x Period.

Creates LawOrRegulation nodes for each valid combination.
19 tax types x 27 industries x 3 periods = 1,539 potential (filter ~60% valid = ~920)

Usage:
    python src/generate_compliance_matrix.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import sys


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


PERIOD_MAP = {
    "monthly": ("每月", "每月15日前"),
    "quarterly": ("每季度", "季后15日前"),
    "annually": ("每年", "次年5月31日前"),
}

# Tax types that have specific period obligations
TAX_PERIOD_RULES = {
    "TT_VAT": ["monthly", "quarterly"],
    "TT_CIT": ["quarterly", "annually"],
    "TT_PIT": ["monthly", "annually"],
    "TT_STAMP": ["monthly", "quarterly"],
    "TT_URBAN": ["monthly"],
    "TT_EDUCATION": ["monthly"],
    "TT_LOCAL_EDU": ["monthly"],
    "TT_PROPERTY": ["quarterly", "annually"],
    "TT_LAND_USE": ["quarterly", "annually"],
    "TT_VEHICLE": ["annually"],
    "TT_CONSUMPTION": ["monthly"],
    "TT_RESOURCE": ["monthly"],
    "TT_ENV": ["quarterly"],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    # Get tax types and industries from DB or use defaults
    tax_types = []
    industries = []

    if conn:
        r = conn.execute("MATCH (t:TaxType) RETURN t.id, t.name")
        while r.has_next():
            row = r.get_next()
            tax_types.append({"id": row[0], "name": row[1] or ""})

        r = conn.execute("MATCH (i:FTIndustry) RETURN i.id, i.name")
        while r.has_next():
            row = r.get_next()
            industries.append({"id": row[0], "name": row[1] or ""})
    else:
        tax_types = [{"id": f"TT_{i}", "name": f"Tax{i}"} for i in range(19)]
        industries = [{"id": f"IND_{i}", "name": f"Ind{i}"} for i in range(27)]

    print(f"TaxTypes: {len(tax_types)}, Industries: {len(industries)}")

    count = 0
    for tt in tax_types:
        periods = TAX_PERIOD_RULES.get(tt["id"], ["annually"])
        for ind in industries:
            for period in periods:
                period_cn, deadline = PERIOD_MAP[period]
                nid = f"LR_COMP_{hashlib.md5(f'{tt['id']}_{ind['id']}_{period}'.encode()).hexdigest()[:8]}"
                title = f"[合规义务] {ind['name']} - {tt['name']} - {period_cn}"
                content = (
                    f"{ind['name']}企业{tt['name']}合规义务({period_cn}):\n"
                    f"申报频率: {period_cn}\n"
                    f"截止日期: {deadline}\n"
                    f"操作: 登录电子税务局 -> 税费申报 -> {tt['name']}申报\n"
                    f"注意: 逾期申报将产生滞纳金(每日万分之五)和信用扣分"
                )

                if args.dry_run:
                    count += 1
                    continue

                sql = (
                    f"CREATE (n:LawOrRegulation {{"
                    f"id: '{esc(nid)}', "
                    f"title: '{esc(title[:200])}', "
                    f"regulationNumber: '', "
                    f"issuingAuthority: 'compliance-matrix', "
                    f"regulationType: 'compliance_obligation', "
                    f"issuedDate: date('2026-01-01'), "
                    f"effectiveDate: date('2026-01-01'), "
                    f"expiryDate: date('2099-12-31'), "
                    f"status: 'reference', "
                    f"hierarchyLevel: 99, "
                    f"sourceUrl: '', "
                    f"contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
                    f"fullText: '{esc(content[:1000])}', "
                    f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
                    f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
                    f"txTimeCreated: timestamp('2026-03-16 00:00:00'), "
                    f"txTimeUpdated: timestamp('2026-03-16 00:00:00')"
                    f"}})"
                )
                try:
                    conn.execute(sql)
                    count += 1
                except Exception:
                    pass

    print(f"OK: +{count} compliance obligation nodes")

    if conn:
        r = conn.execute("MATCH (n) RETURN count(n)")
        print(f"Total: {r.get_next()[0]}")


if __name__ == "__main__":
    main()
