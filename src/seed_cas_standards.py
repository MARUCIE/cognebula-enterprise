#!/usr/bin/env python3
"""Seed 42 CAS (Chinese Accounting Standards) into L1 + IndustryBookkeeping into L2.

Usage: python seed_cas_standards.py --db data/finance-tax-graph
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cognebula import init_kuzu_db

def _m(conn, q, p=None):
    try:
        conn.execute(q, p) if p else conn.execute(q)
    except Exception as e:
        print(f"WARN: {e}")

def seed_cas(conn):
    """42 CAS + Basic Standard."""
    standards = [
        (0, "基本准则", "Basic Standard", "Framework", "All enterprises"),
        (1, "存货", "Inventories", "IAS 2", "Manufacturing, retail"),
        (2, "长期股权投资", "Long-term Equity Investments", "IAS 28", "Holdings, investment"),
        (3, "投资性房地产", "Investment Property", "IAS 40", "Real estate, finance"),
        (4, "固定资产", "Fixed Assets", "IAS 16", "All industries"),
        (5, "生物资产", "Biological Assets", "IAS 41", "Agriculture"),
        (6, "无形资产", "Intangible Assets", "IAS 38", "Software, pharma"),
        (7, "非货币性资产交换", "Non-monetary Asset Exchanges", "IAS 18", "Multi-party"),
        (8, "资产减值", "Asset Impairment", "IAS 36", "All industries"),
        (9, "职工薪酬", "Employee Benefits", "IAS 19", "All enterprises"),
        (10, "企业年金基金", "Enterprise Annuity Fund", "IAS 26", "Pension plans"),
        (11, "股份支付", "Share-based Payments", "IFRS 2", "Listed companies"),
        (12, "债务重组", "Debt Restructuring", "IAS 39", "Distressed firms"),
        (13, "或有事项", "Contingencies", "IAS 37", "Legal disputes"),
        (14, "收入", "Revenue", "IFRS 15", "All sales-based"),
        (15, "建造合同", "Construction Contracts", "IFRS 15", "Construction"),
        (16, "政府补助", "Government Grants", "IAS 20", "Subsidized firms"),
        (17, "借款费用", "Borrowing Costs", "IAS 23", "Capital-intensive"),
        (18, "所得税", "Income Taxes", "IAS 12", "All taxable"),
        (19, "外币折算", "Foreign Currency Translation", "IAS 21", "Multinationals"),
        (20, "企业合并", "Business Combinations", "IFRS 3", "M&A"),
        (21, "租赁", "Leases", "IFRS 16", "All enterprises"),
        (22, "金融工具确认和计量", "Financial Instruments Recognition", "IFRS 9", "Banks"),
        (23, "金融资产转移", "Financial Asset Transfers", "IFRS 9", "Finance"),
        (24, "套期会计", "Hedge Accounting", "IAS 39", "Derivatives"),
        (25, "保险合同", "Insurance Contracts", "IFRS 4", "Insurance"),
        (26, "再保险合同", "Reinsurance Contracts", "IFRS 4", "Reinsurers"),
        (27, "石油天然气开采", "Oil & Gas Extraction", "IFRS 6", "Oil/gas"),
        (28, "会计政策变更和差错更正", "Accounting Policy Changes", "IAS 8", "All"),
        (29, "资产负债表日后事项", "Events After BS Date", "IAS 10", "All"),
        (30, "财务报表列报", "Financial Statement Presentation", "IAS 1", "All"),
        (31, "现金流量表", "Cash Flow Statement", "IAS 7", "All"),
        (32, "中期财务报告", "Interim Financial Reporting", "IAS 34", "Listed"),
        (33, "合并财务报表", "Consolidated Financial Statements", "IFRS 10", "Groups"),
        (34, "每股收益", "Earnings Per Share", "IAS 33", "Listed"),
        (35, "分部报告", "Segment Reporting", "IFRS 8", "Large groups"),
        (36, "关联方披露", "Related Party Disclosure", "IAS 24", "Groups"),
        (37, "金融工具列报", "Financial Instrument Presentation", "IFRS 7", "Finance"),
        (38, "首次执行企业会计准则", "First-time Adoption", "IFRS 1", "Transitioning"),
        (39, "公允价值计量", "Fair Value Measurement", "IFRS 13", "Trading"),
        (40, "合营安排", "Joint Arrangements", "IFRS 11", "JV"),
        (41, "在其他主体中权益的披露", "Interests in Other Entities", "IFRS 12", "Holdings"),
        (42, "持有待售非流动资产", "Non-current Assets Held for Sale", "IFRS 5", "Disposals"),
    ]
    for s in standards:
        _m(conn, "MERGE (n:AccountingStandard {id: $id}) SET n.name=$name, n.casNumber=$cas, n.ifrsEquivalent=$ifrs, n.scope=$scope, n.status='active'",
           {"id": f"CAS_{s[0]:02d}", "name": s[1], "cas": s[0], "ifrs": s[3], "scope": s[4]})
    print(f"OK: Seeded {len(standards)} CAS standards")

def seed_industry_bookkeeping(conn):
    """L2: Industry-specific bookkeeping rules."""
    industries = [
        ("IB_MFG", "制造业", "品种法/分批法/分步法", "按交付确认", "1403原材料→5001生产成本→1405库存商品", "加权平均/先进先出", "直线法10-13年(机器)", "N/A"),
        ("IB_CONSTRUCT", "建筑业", "分步法(工程项目)", "完工百分比法(CAS 15)", "5103合同成本→1530工程施工→6401工程成本", "个别计价", "直线法20-40年(建筑)", "N/A"),
        ("IB_REALESTATE", "房地产", "开发成本法", "实质完工交付时确认(CAS 14)", "5103开发成本→1405开发产品→6401销售成本", "N/A", "直线法(建筑20-40年)", "N/A"),
        ("IB_SOFTWARE", "软件/科技", "项目制", "SaaS按期/License按交付/定制按里程碑", "1631研发支出→1621无形资产(满足5条件)", "N/A", "直线法3-5年(设备)", "满足5条件可资本化"),
        ("IB_ECOMMERCE", "电商/零售", "批次法", "发货确认(自营)/佣金确认(平台)", "1405库存商品→6401销售成本(自营)/6001佣金收入(平台)", "加权平均", "直线法5-10年", "N/A"),
        ("IB_FINANCE", "金融/银行", "金融工具分类", "利息收入按实际利率法", "ECL模型(预期信用损失)", "N/A", "直线法(办公设备)", "N/A"),
        ("IB_CATERING", "餐饮/服务", "简易核算", "收现即确认", "食材成本=期初+采购-期末", "先进先出(食材)", "直线法5-10年(设备)", "N/A"),
    ]
    for i in industries:
        _m(conn, "MERGE (n:IndustryBookkeeping {id: $id}) SET n.industryName=$name, n.costMethod=$cm, n.revenueRecognition=$rr, n.specialAccounts=$sa, n.inventoryMethod=$im, n.depreciationPolicy=$dp, n.rdCapitalization=$rd",
           {"id": i[0], "name": i[1], "cm": i[2], "rr": i[3], "sa": i[4], "im": i[5], "dp": i[6], "rd": i[7]})
    print(f"OK: Seeded {len(industries)} industry bookkeeping rules")

def seed_account_entries(conn):
    """L2: Common journal entry templates."""
    entries = [
        ("AE_PURCHASE", "采购原材料", "购入原材料并取得增值税专用发票", "1403", "原材料", "2201", "应付账款", "含税价/(1+13%)", "进项税抵扣13%"),
        ("AE_SALE", "销售商品", "销售商品确认收入", "1002", "银行存款", "6001", "主营业务收入", "不含税销售额", "销项税13%/9%/6%"),
        ("AE_COGS", "结转销售成本", "月末结转已售商品成本", "6401", "主营业务成本", "1405", "库存商品", "加权平均单位成本×数量", "N/A"),
        ("AE_PAYROLL", "计提工资", "计提当月员工工资", "6602", "管理费用", "2211", "应付职工薪酬", "工资总额", "代扣个税+社保"),
        ("AE_DEPREC", "计提折旧", "月度固定资产折旧", "6602", "管理费用", "1584", "累计折旧", "(原值-残值)/年限/12", "N/A"),
        ("AE_VAT_PAY", "缴纳增值税", "月度申报缴纳增值税", "2221", "应交税费", "1002", "银行存款", "销项-进项", "15日前申报"),
        ("AE_CIT_PREPAY", "预缴企业所得税", "季度预缴企业所得税", "2221", "应交税费", "1002", "银行存款", "利润×25%", "季末15日内"),
        ("AE_SURTAX", "计提附加税", "计提城建税+教育费附加", "6602", "税金及附加", "2221", "应交税费", "增值税×(7%+3%+1%)", "与VAT同期申报"),
        ("AE_RD_EXPENSE", "研发费用化", "不满足资本化条件的研发支出", "6602", "管理费用-研发", "1002", "银行存款", "实际发生额", "加计扣除100%"),
        ("AE_RD_CAPITAL", "研发资本化", "满足5条件的研发支出资本化", "1631", "研发支出", "1002", "银行存款", "实际发生额", "完成后转无形资产"),
    ]
    for e in entries:
        # KuzuDB MERGE has issues with many SET params; use CREATE with existence check
        try:
            r = conn.execute("MATCH (n:AccountEntry {id: $id}) RETURN n.id", {"id": e[0]})
            if r.has_next():
                continue  # already exists
        except Exception:
            pass
        _m(conn, f"CREATE (n:AccountEntry {{id: '{e[0]}', name: '{e[1]}', scenarioDescription: '{e[2]}', debitAccountCode: '{e[3]}', debitAccountName: '{e[4]}', creditAccountCode: '{e[5]}', creditAccountName: '{e[6]}', amountFormula: '{e[7]}', taxImplication: '{e[8]}'}})")
    # Create OP_DEBITS and OP_CREDITS edges
    for e in entries:
        _m(conn, "MATCH (ae:AccountEntry {id: $ae_id}), (coa:ChartOfAccount {code: $code}) MERGE (ae)-[:OP_DEBITS {lineOrder: 1, confidence: 1.0}]->(coa)",
           {"ae_id": e[0], "code": e[3]})
        _m(conn, "MATCH (ae:AccountEntry {id: $ae_id}), (coa:ChartOfAccount {code: $code}) MERGE (ae)-[:OP_CREDITS {lineOrder: 1, confidence: 1.0}]->(coa)",
           {"ae_id": e[0], "code": e[5]})
    print(f"OK: Seeded {len(entries)} journal entry templates + edges")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    db, conn = init_kuzu_db(Path(args.db))
    seed_cas(conn)
    seed_industry_bookkeeping(conn)
    seed_account_entries(conn)

    # Final count
    total = 0
    for t in ["AccountingStandard", "IndustryBookkeeping", "AccountEntry"]:
        r = conn.execute(f"MATCH (n:{t}) RETURN count(n)")
        c = r.get_next()[0]
        total += c
        print(f"  {t}: {c}")
    print(f"Total new nodes: {total}")

if __name__ == "__main__":
    main()
