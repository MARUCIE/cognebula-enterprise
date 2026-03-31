#!/usr/bin/env python3
"""Phase 0 remediation: highest-leverage fixes from 2026-03-31 ontology audit.

Actions:
  1. Fill TaxType.code (19 rows, 10 min leverage)
  2. Fill AccountingStandard.effectiveDate (43 rows)
  3. Fix LegalDocument.level from type field mapping
  4. Fix LegalDocument.type standardization

Usage:
  python3 scripts/fix_audit_phase0.py [--dry-run] [--db-path DATA_DIR]
"""
import argparse
import sys
import os

def get_conn(db_path: str):
    import kuzu
    db = kuzu.Database(db_path)
    return kuzu.Connection(db)


# ── Fix 1: TaxType.code (Golden Tax IV codes) ────────────────────────
TAX_TYPE_CODES = {
    "增值税": "10100",
    "消费税": "10101",
    "企业所得税": "10104",
    "个人所得税": "10120",
    "城市维护建设税": "10110",
    "房产税": "10501",
    "城镇土地使用税": "10503",
    "土地增值税": "10502",
    "车辆购置税": "10401",
    "车船税": "10504",
    "契税": "10505",
    "印花税": "10506",
    "资源税": "10301",
    "环境保护税": "10601",
    "烟叶税": "10302",
    "耕地占用税": "10507",
    "船舶吨税": "10402",
    "关税": "10200",
    "房地产税": "10508",
}


def fix_tax_type_code(conn, dry_run: bool) -> int:
    """Fill TaxType.code with Golden Tax IV standard codes."""
    fixed = 0
    for name, code in TAX_TYPE_CODES.items():
        try:
            r = conn.execute(f'MATCH (t:TaxType) WHERE t.name = "{name}" RETURN t.id, t.code')
            if r.has_next():
                row = r.get_next()
                tid, existing = row[0], row[1]
                if existing and existing.strip() and existing != "0":
                    continue
                if dry_run:
                    print(f"  [DRY] Would set TaxType '{name}' code = '{code}'")
                else:
                    conn.execute(f'MATCH (t:TaxType) WHERE t.id = "{tid}" SET t.code = "{code}"')
                    print(f"  [OK] TaxType '{name}' code = '{code}'")
                fixed += 1
        except Exception as e:
            print(f"  [WARN] TaxType '{name}': {e}")
    return fixed


# ── Fix 2: AccountingStandard.effectiveDate ───────────────────────────
CAS_DATES = {
    "企业会计准则——基本准则": "2007-01-01",
    "企业会计准则第1号——存货": "2007-01-01",
    "企业会计准则第2号——长期股权投资": "2014-07-01",
    "企业会计准则第3号——投资性房地产": "2007-01-01",
    "企业会计准则第4号——固定资产": "2007-01-01",
    "企业会计准则第5号——生物资产": "2007-01-01",
    "企业会计准则第6号——无形资产": "2007-01-01",
    "企业会计准则第7号——非货币性资产交换": "2019-06-10",
    "企业会计准则第8号——资产减值": "2007-01-01",
    "企业会计准则第9号——职工薪酬": "2014-07-01",
    "企业会计准则第10号——企业年金基金": "2007-01-01",
    "企业会计准则第11号——股份支付": "2007-01-01",
    "企业会计准则第12号——债务重组": "2019-06-17",
    "企业会计准则第13号——或有事项": "2007-01-01",
    "企业会计准则第14号——收入": "2021-01-01",
    "企业会计准则第16号——政府补助": "2017-06-12",
    "企业会计准则第17号——借款费用": "2007-01-01",
    "企业会计准则第19号——外币折算": "2007-01-01",
    "企业会计准则第20号——企业合并": "2007-01-01",
    "企业会计准则第21号——租赁": "2021-01-01",
    "企业会计准则第22号——金融工具确认和计量": "2021-01-01",
    "企业会计准则第23号——金融资产转移": "2017-03-31",
    "企业会计准则第24号——套期会计": "2017-03-31",
    "企业会计准则第25号——保险合同": "2023-01-01",
    "企业会计准则第27号——石油天然气开采": "2007-01-01",
    "企业会计准则第28号——会计政策、会计估计变更和差错更正": "2007-01-01",
    "企业会计准则第29号——资产负债表日后事项": "2007-01-01",
    "企业会计准则第30号——财务报表列报": "2014-07-01",
    "企业会计准则第31号——现金流量表": "2007-01-01",
    "企业会计准则第32号——中期财务报告": "2007-01-01",
    "企业会计准则第33号——合并财务报表": "2014-07-01",
    "企业会计准则第34号——每股收益": "2007-01-01",
    "企业会计准则第35号——分部报告": "2007-01-01",
    "企业会计准则第36号——关联方披露": "2007-01-01",
    "企业会计准则第37号——金融工具列报": "2017-03-31",
    "企业会计准则第38号——首次执行企业会计准则": "2007-01-01",
    "企业会计准则第39号——公允价值计量": "2014-07-01",
    "企业会计准则第40号——合营安排": "2014-07-01",
    "企业会计准则第41号——在其他主体中权益的披露": "2014-07-01",
    "企业会计准则第42号——持有待售的非流动资产、处置组和终止经营": "2017-05-28",
}


def fix_accounting_standard_date(conn, dry_run: bool) -> int:
    """Fill AccountingStandard.effectiveDate using known CAS dates."""
    fixed = 0
    r = conn.execute('MATCH (s:AccountingStandard) RETURN s.id, s.name, s.effectiveDate')
    rows = []
    while r.has_next():
        rows.append(r.get_next())

    for sid, name, existing in rows:
        if existing and existing.strip() and existing != "--" and existing != "0":
            continue
        # Try exact match first, then fuzzy
        date = CAS_DATES.get(name)
        if not date:
            for cas_name, cas_date in CAS_DATES.items():
                if cas_name in name or name in cas_name:
                    date = cas_date
                    break
        if date:
            if dry_run:
                print(f"  [DRY] Would set AccountingStandard '{name}' effectiveDate = '{date}'")
            else:
                try:
                    conn.execute(f'MATCH (s:AccountingStandard) WHERE s.id = "{sid}" SET s.effectiveDate = date("{date}")')
                except Exception:
                    # Fallback: effectiveDate might be STRING in some schemas
                    conn.execute(f'MATCH (s:AccountingStandard) WHERE s.id = "{sid}" SET s.effectiveDate = "{date}"')
                print(f"  [OK] AccountingStandard '{name}' effectiveDate = '{date}'")
            fixed += 1
        else:
            print(f"  [SKIP] No date found for '{name}'")
    return fixed


# ── Fix 3: LegalDocument.level from type mapping ─────────────────────
TYPE_TO_LEVEL = {
    "policy_law": 1,           # 法律
    "admin_regulation": 2,     # 行政法规
    "shuiwu": 3,               # 部门规章 (税务)
    "kuaiji": 3,               # 部门规章 (会计)
    "tax_policy_announce": 4,  # 规范性文件
    "法律": 1,
    "行政法规": 2,
    "部门规章": 3,
    "规范性文件": 4,
    "司法解释": 2,
    "会计准则": 3,
}


def fix_legal_document_level(conn, dry_run: bool) -> int:
    """Map LegalDocument.level from type field where level is 0 or missing."""
    fixed = 0
    try:
        r = conn.execute('''
            MATCH (d:LegalDocument)
            WHERE d.level = 0 OR d.level IS NULL
            RETURN d.id, d.type, d.level
        ''')
    except Exception:
        print("  [SKIP] LegalDocument table not found (local DB may not have v2 tables)")
        return 0

    rows = []
    while r.has_next():
        rows.append(r.get_next())

    for did, dtype, level in rows:
        if not dtype:
            continue
        new_level = TYPE_TO_LEVEL.get(dtype.strip().lower())
        if not new_level:
            # Try partial match
            for key, val in TYPE_TO_LEVEL.items():
                if key in str(dtype).lower():
                    new_level = val
                    break
        if new_level:
            if dry_run:
                print(f"  [DRY] LegalDocument {did[:16]}... type='{dtype}' → level={new_level}")
            else:
                conn.execute(f'MATCH (d:LegalDocument) WHERE d.id = "{did}" SET d.level = {new_level}')
            fixed += 1
    if fixed:
        print(f"  [OK] Fixed {fixed} LegalDocument level values")
    else:
        print("  [INFO] No LegalDocument rows needed level fix (or table not present)")
    return fixed


# ── Main ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Phase 0 audit remediation")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--db-path", default="data/finance-tax-graph", help="KuzuDB path")
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        print(f"ERROR: DB path '{args.db_path}' not found")
        sys.exit(1)

    conn = get_conn(args.db_path)
    mode = "[DRY RUN]" if args.dry_run else "[LIVE]"
    print(f"\n=== Phase 0 Remediation {mode} ===\n")

    print("── Fix 1: TaxType.code ──")
    n1 = fix_tax_type_code(conn, args.dry_run)
    print(f"  Result: {n1} rows\n")

    print("── Fix 2: AccountingStandard.effectiveDate ──")
    n2 = fix_accounting_standard_date(conn, args.dry_run)
    print(f"  Result: {n2} rows\n")

    print("── Fix 3: LegalDocument.level ──")
    n3 = fix_legal_document_level(conn, args.dry_run)
    print(f"  Result: {n3} rows\n")

    total = n1 + n2 + n3
    print(f"=== Phase 0 Complete: {total} fixes {'(dry run)' if args.dry_run else 'applied'} ===")


if __name__ == "__main__":
    main()
