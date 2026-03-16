#!/usr/bin/env python3
"""Create accounting operation tables (OP_*) and seed initial data in KuzuDB.

4 new NODE tables + 12 REL tables + ~50 seed records.

Usage:
    python src/create_accounting_schema.py [--db data/finance-tax-graph]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _exec(conn, cypher: str, label: str = ""):
    """Execute DDL/DML with error handling."""
    try:
        conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e)
        if "already exists" in msg.lower() or "duplicate" in msg.lower():
            print(f"NOTE: {label} already exists, skipping")
        else:
            print(f"WARN: {label} -- {e}")
        return False


def create_node_tables(conn):
    """Create 4 OP_ node tables."""
    count = 0

    ddl = [
        ("OP_BusinessScenario", """CREATE NODE TABLE IF NOT EXISTS OP_BusinessScenario(
            id STRING PRIMARY KEY, name STRING, category STRING, industry STRING,
            taxpayerType STRING, frequency STRING, description STRING,
            triggerCondition STRING, relatedLifecycleStage STRING, notes STRING
        )"""),
        ("OP_FilingStep", """CREATE NODE TABLE IF NOT EXISTS OP_FilingStep(
            id STRING PRIMARY KEY, name STRING, filingFormId STRING, stepOrder INT64,
            actor STRING, channel STRING, inputDocuments STRING, outputDocuments STRING,
            deadlineRule STRING, autoDetectable BOOLEAN, notes STRING
        )"""),
        ("OP_StandardCase", """CREATE NODE TABLE IF NOT EXISTS OP_StandardCase(
            id STRING PRIMARY KEY, name STRING, standardId STRING, clauseRef STRING,
            caseType STRING, scenario STRING, correctTreatment STRING, commonMistake STRING,
            industryRelevance STRING, diffFromSme BOOLEAN, diffFromIfrs BOOLEAN,
            diffDescription STRING, notes STRING
        )"""),
        ("OP_SubAccount", """CREATE NODE TABLE IF NOT EXISTS OP_SubAccount(
            id STRING PRIMARY KEY, code STRING, name STRING, parentAccountId STRING,
            level INT64, direction STRING, taxRelevant BOOLEAN, industryScope STRING,
            standardBasis STRING, notes STRING
        )"""),
    ]

    for name, sql in ddl:
        if _exec(conn, sql, f"NODE {name}"):
            count += 1
            print(f"OK: Created node table {name}")
    return count


def create_rel_tables(conn):
    """Create 12 OP_ relationship tables."""
    count = 0

    rels = [
        ("OP_TRIGGERS_ENTRY", "OP_BusinessScenario", "AccountEntry"),
        ("OP_SCENARIO_INDUSTRY", "OP_BusinessScenario", "FTIndustry"),
        ("OP_SCENARIO_STAGE", "OP_BusinessScenario", "LifecycleStage"),
        ("OP_TAX_ACCOUNT", "TaxType", "OP_SubAccount"),
        ("OP_FILING_NEXT", "OP_FilingStep", "OP_FilingStep"),
        ("OP_FILING_FOR_TAX", "OP_FilingStep", "TaxType"),
        ("OP_INDUSTRY_ACCOUNT", "FTIndustry", "ChartOfAccount"),
        ("OP_INDUSTRY_ENTRY", "FTIndustry", "AccountEntry"),
        ("OP_STANDARD_CASE", "AccountingStandard", "OP_StandardCase"),
        ("OP_STANDARD_ENTRY", "AccountingStandard", "AccountEntry"),
        ("OP_SUB_OF", "OP_SubAccount", "ChartOfAccount"),
        ("OP_SUB_OF_SUB", "OP_SubAccount", "OP_SubAccount"),
    ]

    for name, src, dst in rels:
        sql = f"CREATE REL TABLE IF NOT EXISTS {name}(FROM {src} TO {dst})"
        if _exec(conn, sql, f"REL {name}"):
            count += 1
            print(f"OK: Created rel table {name}")
    return count


def seed_sub_accounts(conn):
    """Seed OP_SubAccount: VAT sub-account hierarchy + other tax payables."""
    count = 0
    items = [
        ("SA_2221_01", "2221-01", "应交增值税", "COA_2221", 2, "credit", True, "all", "CAS", "一级明细"),
        ("SA_2221_01_01", "2221-01-01", "进项税额", "SA_2221_01", 3, "debit", True, "all", "CAS", "购进可抵扣进项"),
        ("SA_2221_01_02", "2221-01-02", "销项税额", "SA_2221_01", 3, "credit", True, "all", "CAS", "销售产生销项"),
        ("SA_2221_01_03", "2221-01-03", "已交税金", "SA_2221_01", 3, "debit", True, "all", "CAS", "预缴增值税"),
        ("SA_2221_01_04", "2221-01-04", "转出未交增值税", "SA_2221_01", 3, "credit", True, "all", "CAS", "月末转出应交未交"),
        ("SA_2221_01_05", "2221-01-05", "转出多交增值税", "SA_2221_01", 3, "debit", True, "all", "CAS", "月末转出多交部分"),
        ("SA_2221_02", "2221-02", "未交增值税", "COA_2221", 2, "credit", True, "all", "CAS", "月末应交未交结转"),
        ("SA_2221_03", "2221-03", "应交企业所得税", "COA_2221", 2, "credit", True, "all", "CAS", "季度预缴+汇算清缴"),
        ("SA_2221_04", "2221-04", "应交个人所得税", "COA_2221", 2, "credit", True, "all", "CAS", "代扣代缴"),
        ("SA_2221_05", "2221-05", "应交消费税", "COA_2221", 2, "credit", True, "specific", "CAS", "消费税应税品目"),
        ("SA_2221_06", "2221-06", "应交城建税", "COA_2221", 2, "credit", True, "all", "CAS", "增值税/消费税附加"),
        ("SA_2221_07", "2221-07", "应交教育费附加", "COA_2221", 2, "credit", True, "all", "CAS", "增值税/消费税3%附加"),
        ("SA_2221_08", "2221-08", "应交地方教育附加", "COA_2221", 2, "credit", True, "all", "CAS", "增值税/消费税2%附加"),
        ("SA_2221_09", "2221-09", "应交印花税", "COA_2221", 2, "credit", True, "all", "CAS", "合同/凭证印花税"),
        ("SA_2221_10", "2221-10", "应交房产税", "COA_2221", 2, "credit", True, "property", "CAS", "自有房产"),
        ("SA_2221_11", "2221-11", "应交土地使用税", "COA_2221", 2, "credit", True, "property", "CAS", "城镇土地"),
        ("SA_2221_12", "2221-12", "应交车船税", "COA_2221", 2, "credit", True, "all", "CAS", "车辆船舶"),
    ]

    for item in items:
        esc = lambda s: str(s).replace("'", "\\'")
        sql = (
            f"CREATE (n:OP_SubAccount {{"
            f"id: '{esc(item[0])}', code: '{esc(item[1])}', name: '{esc(item[2])}', "
            f"parentAccountId: '{esc(item[3])}', level: {item[4]}, direction: '{esc(item[5])}', "
            f"taxRelevant: {str(item[6]).lower()}, industryScope: '{esc(item[7])}', "
            f"standardBasis: '{esc(item[8])}', notes: '{esc(item[9])}'"
            f"}})"
        )
        if _exec(conn, sql, f"SubAccount {item[0]}"):
            count += 1
    print(f"OK: Seeded {count}/{len(items)} sub-accounts")
    return count


def seed_business_scenarios(conn):
    """Seed OP_BusinessScenario: 15 core scenarios."""
    count = 0
    items = [
        ("BS_PURCHASE_RAW_GENERAL", "采购原材料（一般纳税人）", "purchase", "manufacturing", "general", "frequent",
         "一般纳税人采购原材料取得增值税专用发票", "收到采购发票", "operating", ""),
        ("BS_SALE_GOODS_GENERAL", "销售商品确认收入", "revenue", "all", "general", "frequent",
         "销售商品满足收入确认条件时确认收入及销项税额", "发出商品+收款/应收", "operating", ""),
        ("BS_SALARY_PROVISION", "计提工资及社保", "payroll", "all", "all", "monthly",
         "月末计提当月应付职工薪酬及企业承担社保", "月末", "operating", ""),
        ("BS_DEPRECIATION", "计提折旧", "asset", "all", "all", "monthly",
         "按月对固定资产计提折旧", "月末", "operating", ""),
        ("BS_VAT_MONTHLY_TRANSFER", "月末增值税结转", "tax_transfer", "all", "general", "monthly",
         "月末将应交增值税明细科目余额结转至未交增值税", "月末", "operating", ""),
        ("BS_CIT_PROVISION", "计提企业所得税", "tax_provision", "all", "all", "quarterly",
         "季度末按利润总额预计提企业所得税", "季末", "operating", ""),
        ("BS_IIT_WITHHOLD", "代扣代缴个人所得税", "tax_withhold", "all", "all", "monthly",
         "发放工资时代扣个人所得税", "发放工资", "operating", ""),
        ("BS_STAMP_TAX", "计提印花税", "tax_provision", "all", "all", "per_transaction",
         "签订应税合同时计提印花税", "签订合同", "operating", ""),
        ("BS_REALESTATE_PRESALE", "房地产预售收款", "revenue", "real_estate", "general", "per_transaction",
         "房地产企业预售商品房收到预收款", "签订预售合同", "operating", "预缴增值税+土地增值税+企业所得税"),
        ("BS_SOFTWARE_VAT_REFUND", "软件企业增值税即征即退", "tax_refund", "software", "general", "monthly",
         "软件产品增值税实际税负超3%部分即征即退", "月末计算", "operating", "需单独核算软件收入"),
        ("BS_EXPORT_REFUND", "出口退税", "tax_refund", "foreign_trade", "general", "monthly",
         "出口货物申报退免税", "报关出口", "operating", "免抵退/免退"),
        ("BS_BAD_DEBT_PROVISION", "计提坏账准备", "asset_impairment", "all", "all", "quarterly",
         "按预期信用损失模型计提应收账款坏账准备", "季末/年末", "operating", "CAS 22 金融工具确认和计量"),
        ("BS_REVENUE_SAAS", "SaaS收入按时段确认", "revenue", "software", "all", "monthly",
         "SaaS订阅收入按履约进度在服务期间分摊确认", "服务期间", "operating", "CAS 14 收入"),
        ("BS_LEASE_OPERATING", "经营租赁收入确认", "revenue", "all", "all", "monthly",
         "经营租赁出租方按直线法确认租赁收入", "租赁期间", "operating", "CAS 21 租赁"),
        ("BS_INVENTORY_TRANSFER", "存货结转（制造业）", "cost", "manufacturing", "all", "monthly",
         "制造业月末结转完工产品成本", "月末", "operating", "生产成本->库存商品"),
    ]

    for item in items:
        esc = lambda s: str(s).replace("'", "\\'")
        sql = (
            f"CREATE (n:OP_BusinessScenario {{"
            f"id: '{esc(item[0])}', name: '{esc(item[1])}', category: '{esc(item[2])}', "
            f"industry: '{esc(item[3])}', taxpayerType: '{esc(item[4])}', frequency: '{esc(item[5])}', "
            f"description: '{esc(item[6])}', triggerCondition: '{esc(item[7])}', "
            f"relatedLifecycleStage: '{esc(item[8])}', notes: '{esc(item[9])}'"
            f"}})"
        )
        if _exec(conn, sql, f"BusinessScenario {item[0]}"):
            count += 1
    print(f"OK: Seeded {count}/{len(items)} business scenarios")
    return count


def seed_filing_steps(conn):
    """Seed OP_FilingStep: VAT (5) + CIT quarterly (5) + CIT annual (5)."""
    count = 0
    items = [
        # VAT filing flow
        ("FS_VAT_01", "增值税发票认证", "", 1, "accountant", "tax_platform",
         "增值税专用发票", "认证清单", "次月15日前", True, "勾选认证平台"),
        ("FS_VAT_02", "增值税申报表填写", "VAT_FORM_MAIN", 2, "accountant", "etax",
         "认证清单+销项汇总", "增值税申报表", "次月15日前", False, "一般纳税人主表+附表"),
        ("FS_VAT_03", "增值税申报审核", "", 3, "tax_manager", "internal",
         "增值税申报表", "审核签字", "次月15日前", False, "比对税负率"),
        ("FS_VAT_04", "增值税税款缴纳", "", 4, "cashier", "bank_or_etax",
         "审核通过申报表", "完税凭证", "次月15日前", True, "三方协议扣款"),
        ("FS_VAT_05", "增值税完税入账", "", 5, "accountant", "erp",
         "完税凭证", "记账凭证", "缴款当日", False, "借:应交税费-未交增值税 贷:银行存款"),
        # CIT quarterly
        ("FS_CIT_Q_01", "企业所得税季度利润计算", "", 1, "accountant", "erp",
         "本季度利润表", "利润总额", "季后15日前", False, "累计利润总额"),
        ("FS_CIT_Q_02", "企业所得税季度预缴申报表", "CIT_FORM_A", 2, "accountant", "etax",
         "季度利润总额", "A类预缴申报表", "季后15日前", False, "A200000"),
        ("FS_CIT_Q_03", "企业所得税季度审核", "", 3, "tax_manager", "internal",
         "预缴申报表", "审核签字", "季后15日前", False, "关注税收优惠适用"),
        ("FS_CIT_Q_04", "企业所得税季度缴款", "", 4, "cashier", "bank_or_etax",
         "审核通过预缴表", "完税凭证", "季后15日前", True, ""),
        ("FS_CIT_Q_05", "企业所得税季度入账", "", 5, "accountant", "erp",
         "完税凭证", "记账凭证", "缴款当日", False, "借:应交税费-应交企业所得税 贷:银行存款"),
        # CIT annual settlement
        ("FS_CIT_A_01", "企业所得税汇算清缴数据准备", "", 1, "accountant", "erp",
         "年度财务报表+纳税调整台账", "汇算清缴底稿", "次年5月31日前", False, "收集全年纳税调整事项"),
        ("FS_CIT_A_02", "企业所得税年度申报表填报", "CIT_FORM_ANNUAL", 2, "accountant", "etax",
         "汇算清缴底稿", "年度纳税申报表", "次年5月31日前", False, "A100000主表+30余张附表"),
        ("FS_CIT_A_03", "企业所得税汇算审核", "", 3, "tax_manager", "internal",
         "年度纳税申报表", "审核签字", "次年5月31日前", False, "重点审核纳税调整项"),
        ("FS_CIT_A_04", "企业所得税汇算缴退款", "", 4, "cashier", "bank_or_etax",
         "审核通过年度表", "完税凭证/退税通知", "次年5月31日前", True, "补缴或退税"),
        ("FS_CIT_A_05", "企业所得税汇算入账", "", 5, "accountant", "erp",
         "完税凭证", "记账凭证", "办结当日", False, "调整以前年度损益(如需)"),
    ]

    for item in items:
        esc = lambda s: str(s).replace("'", "\\'")
        auto = "true" if item[9] else "false"
        sql = (
            f"CREATE (n:OP_FilingStep {{"
            f"id: '{esc(item[0])}', name: '{esc(item[1])}', filingFormId: '{esc(item[2])}', "
            f"stepOrder: {item[3]}, actor: '{esc(item[4])}', channel: '{esc(item[5])}', "
            f"inputDocuments: '{esc(item[6])}', outputDocuments: '{esc(item[7])}', "
            f"deadlineRule: '{esc(item[8])}', autoDetectable: {auto}, notes: '{esc(item[10])}'"
            f"}})"
        )
        if _exec(conn, sql, f"FilingStep {item[0]}"):
            count += 1
    print(f"OK: Seeded {count}/{len(items)} filing steps")
    return count


def seed_filing_next_rels(conn):
    """Create OP_FILING_NEXT relationships for step sequences."""
    count = 0
    chains = [
        # VAT flow
        [("FS_VAT_01", "FS_VAT_02"), ("FS_VAT_02", "FS_VAT_03"),
         ("FS_VAT_03", "FS_VAT_04"), ("FS_VAT_04", "FS_VAT_05")],
        # CIT quarterly
        [("FS_CIT_Q_01", "FS_CIT_Q_02"), ("FS_CIT_Q_02", "FS_CIT_Q_03"),
         ("FS_CIT_Q_03", "FS_CIT_Q_04"), ("FS_CIT_Q_04", "FS_CIT_Q_05")],
        # CIT annual
        [("FS_CIT_A_01", "FS_CIT_A_02"), ("FS_CIT_A_02", "FS_CIT_A_03"),
         ("FS_CIT_A_03", "FS_CIT_A_04"), ("FS_CIT_A_04", "FS_CIT_A_05")],
    ]
    for chain in chains:
        for src, dst in chain:
            sql = (
                f"MATCH (a:OP_FilingStep {{id: '{src}'}}), (b:OP_FilingStep {{id: '{dst}'}}) "
                f"CREATE (a)-[:OP_FILING_NEXT]->(b)"
            )
            if _exec(conn, sql, f"FILING_NEXT {src}->{dst}"):
                count += 1
    print(f"OK: Created {count} filing-next relationships")
    return count


def seed_filing_tax_rels(conn):
    """Create OP_FILING_FOR_TAX relationships."""
    count = 0
    mappings = [
        ("FS_VAT_01", "TT_VAT"), ("FS_VAT_02", "TT_VAT"), ("FS_VAT_03", "TT_VAT"),
        ("FS_VAT_04", "TT_VAT"), ("FS_VAT_05", "TT_VAT"),
        ("FS_CIT_Q_01", "TT_CIT"), ("FS_CIT_Q_02", "TT_CIT"), ("FS_CIT_Q_03", "TT_CIT"),
        ("FS_CIT_Q_04", "TT_CIT"), ("FS_CIT_Q_05", "TT_CIT"),
        ("FS_CIT_A_01", "TT_CIT"), ("FS_CIT_A_02", "TT_CIT"), ("FS_CIT_A_03", "TT_CIT"),
        ("FS_CIT_A_04", "TT_CIT"), ("FS_CIT_A_05", "TT_CIT"),
    ]
    for src, dst in mappings:
        sql = (
            f"MATCH (a:OP_FilingStep {{id: '{src}'}}), (b:TaxType {{id: '{dst}'}}) "
            f"CREATE (a)-[:OP_FILING_FOR_TAX]->(b)"
        )
        if _exec(conn, sql, f"FILING_FOR_TAX {src}->{dst}"):
            count += 1
    print(f"OK: Created {count} filing-for-tax relationships")
    return count


def seed_sub_of_rels(conn):
    """Create OP_SUB_OF (to ChartOfAccount) and OP_SUB_OF_SUB (parent sub-accounts)."""
    count = 0
    # Top-level subs -> COA_2221
    top_subs = ["SA_2221_01", "SA_2221_02", "SA_2221_03", "SA_2221_04", "SA_2221_05",
                "SA_2221_06", "SA_2221_07", "SA_2221_08", "SA_2221_09", "SA_2221_10",
                "SA_2221_11", "SA_2221_12"]
    for sa in top_subs:
        sql = (
            f"MATCH (a:OP_SubAccount {{id: '{sa}'}}), (b:ChartOfAccount {{id: 'COA_2221'}}) "
            f"CREATE (a)-[:OP_SUB_OF]->(b)"
        )
        if _exec(conn, sql, f"SUB_OF {sa}->COA_2221"):
            count += 1

    # Level-3 subs -> SA_2221_01
    child_subs = ["SA_2221_01_01", "SA_2221_01_02", "SA_2221_01_03",
                  "SA_2221_01_04", "SA_2221_01_05"]
    for sa in child_subs:
        sql = (
            f"MATCH (a:OP_SubAccount {{id: '{sa}'}}), (b:OP_SubAccount {{id: 'SA_2221_01'}}) "
            f"CREATE (a)-[:OP_SUB_OF_SUB]->(b)"
        )
        if _exec(conn, sql, f"SUB_OF_SUB {sa}->SA_2221_01"):
            count += 1

    print(f"OK: Created {count} sub-account hierarchy relationships")
    return count


def seed_tax_account_rels(conn):
    """Create OP_TAX_ACCOUNT relationships (TaxType -> OP_SubAccount)."""
    count = 0
    mappings = [
        ("TT_VAT", "SA_2221_01"), ("TT_VAT", "SA_2221_02"),
        ("TT_CIT", "SA_2221_03"), ("TT_PIT", "SA_2221_04"),
        ("TT_CONSUMPTION", "SA_2221_05"), ("TT_URBAN", "SA_2221_06"),
        ("TT_EDUCATION", "SA_2221_07"), ("TT_LOCAL_EDU", "SA_2221_08"),
        ("TT_STAMP", "SA_2221_09"), ("TT_PROPERTY", "SA_2221_10"),
        ("TT_LAND_USE", "SA_2221_11"), ("TT_VEHICLE", "SA_2221_12"),
    ]
    for src, dst in mappings:
        sql = (
            f"MATCH (a:TaxType {{id: '{src}'}}), (b:OP_SubAccount {{id: '{dst}'}}) "
            f"CREATE (a)-[:OP_TAX_ACCOUNT]->(b)"
        )
        if _exec(conn, sql, f"TAX_ACCOUNT {src}->{dst}"):
            count += 1
    print(f"OK: Created {count} tax-account relationships")
    return count


def count_totals(conn):
    """Report total node and edge counts."""
    print("\n--- Final Counts ---")
    try:
        result = conn.execute("CALL show_tables() RETURN *")
        node_tables = []
        rel_tables = []
        while result.has_next():
            row = result.get_next()
            tname = row[0] if isinstance(row, (list, tuple)) else str(row)
            ttype = row[1] if isinstance(row, (list, tuple)) and len(row) > 1 else ""
            if str(ttype).upper() in ("NODE", "NODE_TABLE"):
                node_tables.append(str(tname))
            elif str(ttype).upper() in ("REL", "REL_TABLE"):
                rel_tables.append(str(tname))
    except Exception as e:
        print(f"WARN: Could not list tables: {e}")
        return

    total_nodes = 0
    total_edges = 0

    for t in node_tables:
        try:
            r = conn.execute(f"MATCH (n:{t}) RETURN count(n)")
            c = r.get_next()[0]
            total_nodes += c
            if t.startswith("OP_"):
                print(f"  {t}: {c} nodes")
        except Exception:
            pass

    for t in rel_tables:
        try:
            r = conn.execute(f"MATCH ()-[r:{t}]->() RETURN count(r)")
            c = r.get_next()[0]
            total_edges += c
            if t.startswith("OP_"):
                print(f"  {t}: {c} edges")
        except Exception:
            pass

    print(f"\nTotal node tables: {len(node_tables)}")
    print(f"Total rel tables: {len(rel_tables)}")
    print(f"Total nodes: {total_nodes}")
    print(f"Total edges: {total_edges}")


def main():
    parser = argparse.ArgumentParser(description="Create OP_ accounting schema + seed data")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    args = parser.parse_args()

    try:
        import kuzu
    except ImportError:
        print("ERROR: kuzu not installed. Run: pip install kuzu")
        sys.exit(1)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB path {db_path} does not exist")
        sys.exit(1)

    print(f"Connecting to KuzuDB at {db_path}")
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    # Step 1: Create tables
    print("\n=== Creating Node Tables ===")
    n_nodes = create_node_tables(conn)

    print("\n=== Creating Rel Tables ===")
    n_rels = create_rel_tables(conn)

    # Step 2: Seed data
    print("\n=== Seeding Sub-Accounts ===")
    s1 = seed_sub_accounts(conn)

    print("\n=== Seeding Business Scenarios ===")
    s2 = seed_business_scenarios(conn)

    print("\n=== Seeding Filing Steps ===")
    s3 = seed_filing_steps(conn)

    # Step 3: Seed relationships
    print("\n=== Seeding Filing-Next Relationships ===")
    r1 = seed_filing_next_rels(conn)

    print("\n=== Seeding Filing-Tax Relationships ===")
    r2 = seed_filing_tax_rels(conn)

    print("\n=== Seeding Sub-Account Hierarchy ===")
    r3 = seed_sub_of_rels(conn)

    print("\n=== Seeding Tax-Account Relationships ===")
    r4 = seed_tax_account_rels(conn)

    # Summary
    print(f"\n=== Summary ===")
    print(f"Tables created: {n_nodes} node + {n_rels} rel = {n_nodes + n_rels}")
    print(f"Nodes seeded: {s1 + s2 + s3} ({s1} sub-accounts + {s2} scenarios + {s3} filing steps)")
    print(f"Rels seeded: {r1 + r2 + r3 + r4} ({r1} filing-next + {r2} filing-tax + {r3} sub-hierarchy + {r4} tax-account)")

    # Final counts
    count_totals(conn)


if __name__ == "__main__":
    main()
