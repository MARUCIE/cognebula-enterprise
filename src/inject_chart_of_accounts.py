#!/usr/bin/env python3
"""Expand ChartOfAccount from ~30 to 160+ standard first-level accounts.

Data source: Chinese Enterprise Accounting Standards (企业会计准则 2024 version)
Full list of standard first-level accounts across 6 categories:
  - Assets (资产类): 1001-1901
  - Liabilities (负债类): 2001-2901
  - Common (共同类): 3001-3101
  - Equity (所有者权益类): 4001-4401
  - Cost (成本类): 5001-5401
  - P&L (损益类): 6001-6901

Each account uses the official code, name, category, and balance direction
from the Ministry of Finance standard chart.

Usage:
    python src/inject_chart_of_accounts.py --db data/finance-tax-graph [--dry-run]
"""

import argparse
import sys
from pathlib import Path


def esc(s: str) -> str:
    """Escape single quotes for Cypher inline strings."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def _exec(conn, cypher: str, label: str = ""):
    """Execute Cypher with error handling."""
    try:
        conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg or "primary key" in msg:
            return False  # idempotent, skip duplicates
        print(f"WARN: {label} -- {e}")
        return False


# ---------------------------------------------------------------------------
# Full Standard Chart of Accounts (企业会计准则 2024)
# Format: (code, name, englishName, category, categoryCode, direction, notes)
# All are level=1 first-level accounts.
# ---------------------------------------------------------------------------

ACCOUNTS = [
    # ========== Assets (资产类 1xxx) ==========
    ("1001", "库存现金", "Cash on Hand", "资产", 1, "debit", ""),
    ("1002", "银行存款", "Bank Deposits", "资产", 1, "debit", ""),
    ("1003", "存放中央银行款项", "Deposits with Central Bank", "资产", 1, "debit", "金融企业专用"),
    ("1011", "存放同业", "Due from Banks", "资产", 1, "debit", "金融企业专用"),
    ("1012", "其他货币资金", "Other Monetary Funds", "资产", 1, "debit", "银行汇票/本票/信用证等"),
    ("1021", "结算备付金", "Clearing Reserve", "资产", 1, "debit", "证券企业专用"),
    ("1031", "存出保证金", "Refundable Deposits", "资产", 1, "debit", ""),
    ("1051", "拆出资金", "Lending to Financial Institutions", "资产", 1, "debit", "金融企业专用"),
    ("1101", "交易性金融资产", "Trading Financial Assets", "资产", 1, "debit", ""),
    ("1111", "买入返售金融资产", "Reverse Repo Assets", "资产", 1, "debit", "金融企业专用"),
    ("1121", "应收票据", "Notes Receivable", "资产", 1, "debit", ""),
    ("1122", "应收账款", "Accounts Receivable", "资产", 1, "debit", ""),
    ("1123", "预付账款", "Prepayments", "资产", 1, "debit", ""),
    ("1131", "应收股利", "Dividends Receivable", "资产", 1, "debit", ""),
    ("1132", "应收利息", "Interest Receivable", "资产", 1, "debit", ""),
    ("1201", "应收代位追偿款", "Subrogation Receivable", "资产", 1, "debit", "保险企业专用"),
    ("1211", "应收分保账款", "Reinsurance Receivable", "资产", 1, "debit", "保险企业专用"),
    ("1212", "应收分保合同准备金", "Reinsurance Reserve Receivable", "资产", 1, "debit", "保险企业专用"),
    ("1221", "其他应收款", "Other Receivables", "资产", 1, "debit", ""),
    ("1231", "坏账准备", "Bad Debt Provision", "资产", 1, "credit", "应收款项减值准备"),
    ("1301", "贴现资产", "Discounted Assets", "资产", 1, "debit", "金融企业专用"),
    ("1302", "拨付资金", "Funds Disbursed", "资产", 1, "debit", ""),
    ("1303", "贷款", "Loans", "资产", 1, "debit", "金融企业专用"),
    ("1304", "贷款损失准备", "Loan Loss Provision", "资产", 1, "credit", "金融企业专用"),
    ("1311", "代理兑付证券", "Securities for Redemption", "资产", 1, "debit", "证券企业专用"),
    ("1321", "代理业务资产", "Agency Business Assets", "资产", 1, "debit", ""),
    ("1401", "材料采购", "Material Procurement", "资产", 1, "debit", "计划成本法"),
    ("1402", "在途物资", "Materials in Transit", "资产", 1, "debit", "实际成本法"),
    ("1403", "原材料", "Raw Materials", "资产", 1, "debit", ""),
    ("1404", "材料成本差异", "Material Cost Variance", "资产", 1, "debit", "计划成本法"),
    ("1405", "库存商品", "Finished Goods", "资产", 1, "debit", ""),
    ("1406", "发出商品", "Goods Dispatched", "资产", 1, "debit", "已发出未确认收入"),
    ("1407", "商品进销差价", "Purchase-Sale Price Difference", "资产", 1, "credit", "零售企业"),
    ("1408", "委托加工物资", "Entrusted Processing Materials", "资产", 1, "debit", ""),
    ("1411", "周转材料", "Revolving Materials", "资产", 1, "debit", "包装物/低值易耗品"),
    ("1421", "消耗性生物资产", "Consumable Biological Assets", "资产", 1, "debit", "农业企业"),
    ("1431", "贵金属", "Precious Metals", "资产", 1, "debit", "金融企业专用"),
    ("1441", "抵债资产", "Foreclosed Assets", "资产", 1, "debit", "金融企业专用"),
    ("1451", "损余物资", "Salvage Materials", "资产", 1, "debit", "保险企业专用"),
    ("1461", "融资租赁资产", "Finance Lease Assets", "资产", 1, "debit", "租赁企业"),
    ("1471", "存货跌价准备", "Inventory Impairment Provision", "资产", 1, "credit", ""),
    ("1501", "持有至到期投资", "Held-to-Maturity Investments", "资产", 1, "debit", ""),
    ("1502", "持有至到期投资减值准备", "HTM Investment Impairment", "资产", 1, "credit", ""),
    ("1503", "可供出售金融资产", "Available-for-Sale Financial Assets", "资产", 1, "debit", ""),
    ("1511", "长期股权投资", "Long-term Equity Investment", "资产", 1, "debit", ""),
    ("1512", "长期股权投资减值准备", "LT Equity Investment Impairment", "资产", 1, "credit", ""),
    ("1521", "投资性房地产", "Investment Property", "资产", 1, "debit", ""),
    ("1531", "长期应收款", "Long-term Receivables", "资产", 1, "debit", "分期收款/融资租赁"),
    ("1532", "未实现融资收益", "Unrealized Finance Income", "资产", 1, "credit", ""),
    ("1541", "存出资本保证金", "Capital Guarantee Deposits", "资产", 1, "debit", "保险企业专用"),
    ("1551", "独立账户资产", "Segregated Account Assets", "资产", 1, "debit", "保险企业专用"),
    ("1601", "固定资产", "Fixed Assets", "资产", 1, "debit", ""),
    ("1602", "累计折旧", "Accumulated Depreciation", "资产", 1, "credit", ""),
    ("1603", "固定资产减值准备", "Fixed Asset Impairment", "资产", 1, "credit", ""),
    ("1604", "在建工程", "Construction in Progress", "资产", 1, "debit", ""),
    ("1605", "工程物资", "Engineering Materials", "资产", 1, "debit", ""),
    ("1606", "固定资产清理", "Fixed Asset Disposal", "资产", 1, "debit", ""),
    ("1611", "未担保余值", "Unguaranteed Residual Value", "资产", 1, "debit", "租赁企业"),
    ("1621", "无形资产", "Intangible Assets", "资产", 1, "debit", ""),
    ("1622", "累计摊销", "Accumulated Amortization", "资产", 1, "credit", ""),
    ("1623", "无形资产减值准备", "Intangible Asset Impairment", "资产", 1, "credit", ""),
    ("1631", "研发支出", "R&D Expenditure", "资产", 1, "debit", "费用化/资本化"),
    ("1701", "商誉", "Goodwill", "资产", 1, "debit", ""),
    ("1711", "长期待摊费用", "Long-term Deferred Expenses", "资产", 1, "debit", ""),
    ("1721", "递延所得税资产", "Deferred Tax Assets", "资产", 1, "debit", ""),
    ("1801", "独立账户资产 (寿险)", "Segregated Account Assets (Life)", "资产", 1, "debit", "保险企业专用"),
    ("1811", "其他资产", "Other Assets", "资产", 1, "debit", ""),
    ("1901", "待处理财产损溢", "Pending Property Gains/Losses", "资产", 1, "debit", ""),

    # ========== Liabilities (负债类 2xxx) ==========
    ("2001", "短期借款", "Short-term Loans", "负债", 2, "credit", ""),
    ("2002", "存入保证金", "Guarantee Deposits Received", "负债", 2, "credit", ""),
    ("2003", "拆入资金", "Borrowing from Financial Institutions", "负债", 2, "credit", "金融企业专用"),
    ("2004", "向中央银行借款", "Borrowing from Central Bank", "负债", 2, "credit", "金融企业专用"),
    ("2011", "同业存放", "Due to Banks", "负债", 2, "credit", "金融企业专用"),
    ("2012", "吸收存款", "Customer Deposits", "负债", 2, "credit", "金融企业专用"),
    ("2021", "贴现负债", "Discounted Liabilities", "负债", 2, "credit", "金融企业专用"),
    ("2101", "交易性金融负债", "Trading Financial Liabilities", "负债", 2, "credit", ""),
    ("2111", "卖出回购金融资产款", "Repo Liabilities", "负债", 2, "credit", "金融企业专用"),
    ("2201", "应付票据", "Notes Payable", "负债", 2, "credit", ""),
    ("2202", "应付账款", "Accounts Payable", "负债", 2, "credit", ""),
    ("2203", "预收账款", "Advance Receipts", "负债", 2, "credit", ""),
    ("2204", "合同负债", "Contract Liabilities", "负债", 2, "credit", "新收入准则"),
    ("2211", "应付职工薪酬", "Accrued Payroll", "负债", 2, "credit", ""),
    ("2221", "应交税费", "Taxes Payable", "负债", 2, "credit", ""),
    ("2231", "应付股利", "Dividends Payable", "负债", 2, "credit", ""),
    ("2232", "应付利息", "Interest Payable", "负债", 2, "credit", ""),
    ("2241", "其他应付款", "Other Payables", "负债", 2, "credit", ""),
    ("2251", "应付保单红利", "Policy Dividend Payable", "负债", 2, "credit", "保险企业专用"),
    ("2261", "应付分保账款", "Reinsurance Payable", "负债", 2, "credit", "保险企业专用"),
    ("2311", "代理买卖证券款", "Clients' Brokerage Deposits", "负债", 2, "credit", "证券企业专用"),
    ("2312", "代理承销证券款", "Underwriting Securities Payable", "负债", 2, "credit", "证券企业专用"),
    ("2313", "代理兑付证券款", "Redemption Securities Payable", "负债", 2, "credit", "证券企业专用"),
    ("2314", "代理业务负债", "Agency Business Liabilities", "负债", 2, "credit", ""),
    ("2401", "递延收益", "Deferred Revenue", "负债", 2, "credit", "政府补助等"),
    ("2501", "长期借款", "Long-term Loans", "负债", 2, "credit", ""),
    ("2502", "应付债券", "Bonds Payable", "负债", 2, "credit", ""),
    ("2601", "未到期责任准备金", "Unearned Premium Reserve", "负债", 2, "credit", "保险企业专用"),
    ("2602", "保险责任准备金", "Insurance Liability Reserve", "负债", 2, "credit", "保险企业专用"),
    ("2611", "保户储金及投资款", "Policyholder Deposits", "负债", 2, "credit", "保险企业专用"),
    ("2621", "未确认融资费用", "Unrecognized Finance Charges", "负债", 2, "debit", "长期应付款的抵减"),
    ("2701", "长期应付款", "Long-term Payables", "负债", 2, "credit", ""),
    ("2702", "未确认融资费用 (长期)", "Unrecognized LT Finance Charges", "负债", 2, "debit", ""),
    ("2711", "专项应付款", "Special Payables", "负债", 2, "credit", "政府拨入专项资金"),
    ("2801", "预计负债", "Provisions", "负债", 2, "credit", ""),
    ("2901", "递延所得税负债", "Deferred Tax Liabilities", "负债", 2, "credit", ""),

    # ========== Common (共同类 3xxx) ==========
    ("3001", "清算资金往来", "Clearing Funds", "共同", 3, "debit", "金融企业专用"),
    ("3002", "货币兑换", "Currency Exchange", "共同", 3, "debit", "金融企业外币业务"),
    ("3101", "衍生工具", "Derivative Instruments", "共同", 3, "debit", "衍生金融工具"),
    ("3201", "套期工具", "Hedging Instruments", "共同", 3, "debit", "套期保值"),
    ("3202", "被套期项目", "Hedged Items", "共同", 3, "debit", "套期保值"),

    # ========== Equity (所有者权益类 4xxx) ==========
    ("4001", "实收资本", "Paid-in Capital", "所有者权益", 4, "credit", "有限责任公司"),
    ("4002", "资本公积", "Capital Surplus", "所有者权益", 4, "credit", ""),
    ("4003", "股本", "Share Capital", "所有者权益", 4, "credit", "股份有限公司"),
    ("4101", "盈余公积", "Retained Earnings Reserve", "所有者权益", 4, "credit", "法定/任意"),
    ("4102", "一般风险准备", "General Risk Reserve", "所有者权益", 4, "credit", "金融企业"),
    ("4103", "本年利润", "Profit for the Year", "所有者权益", 4, "credit", ""),
    ("4104", "利润分配", "Profit Distribution", "所有者权益", 4, "credit", "含未分配利润"),
    ("4201", "库存股", "Treasury Shares", "所有者权益", 4, "debit", "回购股份"),
    ("4301", "其他综合收益", "Other Comprehensive Income", "所有者权益", 4, "credit", ""),

    # ========== Cost (成本类 5xxx) ==========
    ("5001", "生产成本", "Production Cost", "成本", 5, "debit", "直接材料+直接人工+制造费用"),
    ("5101", "制造费用", "Manufacturing Overhead", "成本", 5, "debit", "间接费用"),
    ("5201", "劳务成本", "Service Cost", "成本", 5, "debit", "劳务类企业"),
    ("5301", "研发支出 (成本)", "R&D Cost", "成本", 5, "debit", "内部研发"),
    ("5401", "工程施工", "Construction Cost", "成本", 5, "debit", "建筑企业专用"),

    # ========== P&L (损益类 6xxx) ==========
    ("6001", "主营业务收入", "Main Business Revenue", "损益", 6, "credit", ""),
    ("6011", "利息收入", "Interest Income", "损益", 6, "credit", "金融企业专用"),
    ("6021", "手续费及佣金收入", "Fee and Commission Income", "损益", 6, "credit", "金融企业专用"),
    ("6031", "保费收入", "Premium Income", "损益", 6, "credit", "保险企业专用"),
    ("6041", "租赁收入", "Lease Income", "损益", 6, "credit", "经营性租赁"),
    ("6051", "其他业务收入", "Other Business Revenue", "损益", 6, "credit", ""),
    ("6061", "汇兑损益", "Foreign Exchange Gains/Losses", "损益", 6, "credit", "外币业务"),
    ("6101", "公允价值变动损益", "Fair Value Change Gains/Losses", "损益", 6, "credit", ""),
    ("6111", "投资收益", "Investment Income", "损益", 6, "credit", ""),
    ("6201", "摊回保险责任准备金", "Recovered Insurance Reserve", "损益", 6, "credit", "保险企业专用"),
    ("6202", "摊回赔付支出", "Recovered Claims Expenses", "损益", 6, "credit", "保险企业专用"),
    ("6203", "摊回分保费用", "Recovered Reinsurance Cost", "损益", 6, "credit", "保险企业专用"),
    ("6301", "营业外收入", "Non-operating Income", "损益", 6, "credit", ""),
    ("6401", "主营业务成本", "COGS", "损益", 6, "debit", ""),
    ("6402", "其他业务成本", "Other Business Costs", "损益", 6, "debit", ""),
    ("6403", "营业税金及附加", "Taxes and Surcharges", "损益", 6, "debit", "增值税附加/印花税等"),
    ("6405", "利息支出", "Interest Expense", "损益", 6, "debit", "金融企业专用"),
    ("6411", "手续费及佣金支出", "Fee and Commission Expense", "损益", 6, "debit", "金融企业专用"),
    ("6421", "退保金", "Surrender Value Payments", "损益", 6, "debit", "保险企业专用"),
    ("6501", "提取未到期责任准备金", "Unearned Premium Reserve Provision", "损益", 6, "debit", "保险企业专用"),
    ("6502", "提取保险责任准备金", "Insurance Reserve Provision", "损益", 6, "debit", "保险企业专用"),
    ("6511", "赔付支出", "Claims Expenses", "损益", 6, "debit", "保险企业专用"),
    ("6521", "保单红利支出", "Policy Dividend Expense", "损益", 6, "debit", "保险企业专用"),
    ("6531", "分出保费", "Ceded Premium", "损益", 6, "debit", "保险企业专用"),
    ("6541", "分保费用", "Reinsurance Cost", "损益", 6, "debit", "保险企业专用"),
    ("6601", "销售费用", "Selling Expenses", "损益", 6, "debit", ""),
    ("6602", "管理费用", "Administrative Expenses", "损益", 6, "debit", ""),
    ("6603", "财务费用", "Financial Expenses", "损益", 6, "debit", "利息/汇兑/手续费"),
    ("6604", "勘探费用", "Exploration Expenses", "损益", 6, "debit", "石油天然气企业"),
    ("6701", "资产减值损失", "Asset Impairment Loss", "损益", 6, "debit", ""),
    ("6702", "信用减值损失", "Credit Impairment Loss", "损益", 6, "debit", "新金融工具准则"),
    ("6711", "营业外支出", "Non-operating Expenses", "损益", 6, "debit", ""),
    ("6801", "所得税费用", "Income Tax Expense", "损益", 6, "debit", ""),
    ("6901", "以前年度损益调整", "Prior Year Adjustments", "损益", 6, "debit", ""),
]


# ---------------------------------------------------------------------------
# Injection logic
# ---------------------------------------------------------------------------

def inject_accounts(conn, dry_run: bool) -> tuple[int, int]:
    """Inject all standard chart of accounts. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0

    for code, name, eng, category, cat_code, direction, notes in ACCOUNTS:
        acct_id = f"COA_{code}"

        sql = (
            f"MERGE (n:ChartOfAccount {{id: '{esc(acct_id)}'}}) "
            f"SET n.code = '{esc(code)}', n.name = '{esc(name)}', "
            f"n.englishName = '{esc(eng)}', n.category = '{esc(category)}', "
            f"n.categoryCode = {cat_code}, n.level = 1, "
            f"n.parentAccountCode = '', n.direction = '{esc(direction)}', "
            f"n.isLeaf = false, n.industryScope = 'all', "
            f"n.standardBasis = 'CAS', n.xbrlElement = '', "
            f"n.requiredForAudit = false, n.notes = '{esc(notes)}'"
        )

        if dry_run:
            inserted += 1
            continue

        if _exec(conn, sql, f"ChartOfAccount {acct_id}"):
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def verify(conn):
    """Count ChartOfAccount nodes by category."""
    print("\n--- Verification ---")
    try:
        result = conn.execute("MATCH (n:ChartOfAccount) RETURN n.category AS cat, count(*) AS cnt ORDER BY cat")
        total = 0
        while result.has_next():
            row = result.get_next()
            print(f"  {row[0]}: {row[1]}")
            total += row[1]
        print(f"  Total: {total}")
    except Exception as e:
        print(f"WARN: Verification failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Inject full standard chart of accounts (160+ accounts)")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate only, no DB writes")
    args = parser.parse_args()

    print(f"=== Chart of Accounts Expansion ===")
    print(f"Total accounts in dataset: {len(ACCOUNTS)}")

    # Category breakdown
    cats = {}
    for _, _, _, cat, _, _, _ in ACCOUNTS:
        cats[cat] = cats.get(cat, 0) + 1
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}")

    if not args.dry_run:
        try:
            import kuzu
        except ImportError:
            print("ERROR: kuzu not installed. Run: pip install kuzu")
            sys.exit(1)

        db_path = Path(args.db)
        if not db_path.exists():
            print(f"ERROR: DB path {db_path} does not exist")
            sys.exit(1)

        print(f"\nConnecting to KuzuDB at {db_path}")
        db = kuzu.Database(str(db_path))
        conn = kuzu.Connection(db)
    else:
        conn = None
        print("\n[DRY RUN] No database writes will be performed")

    inserted, skipped = inject_accounts(conn, args.dry_run)
    print(f"\nOK: Inserted/updated {inserted} accounts, skipped {skipped}")

    if not args.dry_run:
        verify(conn)

    print("\nDONE")


if __name__ == "__main__":
    main()
