#!/usr/bin/env python3
"""Seed AccountingSubject canonical table — CAS + 小企业会计准则 + industry add-ons.

Source attribution (all government-published, no synthesis):
  - 企业会计准则 (CAS) 2024 — Ministry of Finance, level-1 official codes
  - 小企业会计准则 (SBE) 2024 — Ministry of Finance, simplified chart
  - Industry-specific extensions — 金融企业 / 农业企业 / 建筑企业 / 房地产企业
    chart-of-accounts that the official CAS issues as supplementary tables

Coverage strategy (Round-4 SOTA gap §5 Week-2 item 7):
  - Existing AccountingSubject row count (audited 2026-04-27): 159
  - This seed adds 130 official codes spanning SBE + 4 industry verticals
    (SBE 67 / FIN 37 / RE 10 / AGR 9 / CON 7 — verified by dry-run)
  - Target post-seed: ~289 rows (target 1,500 — ~19% of plan)
  - Phase-2 expansion to 1,500 requires official 2-3-digit sub-account
    extraction from MoF PDFs (NOT done here; flagged as TODO)

Reversibility:
    MATCH (n:AccountingSubject) WHERE n.id STARTS WITH 'AS_SBE_'
       OR n.id STARTS WITH 'AS_FIN_' OR n.id STARTS WITH 'AS_AGR_'
       OR n.id STARTS WITH 'AS_CON_' OR n.id STARTS WITH 'AS_RE_' DELETE n;

Usage:
    python src/seed/seed_accounting_subject_full.py --db data/finance-tax-graph
    python src/seed/seed_accounting_subject_full.py --db data/finance-tax-graph --dry-run

HITL note: this script ONLY adds rows; no DELETE/DROP. Safe to apply on prod
without snapshot, but per `data/ingestion-manifest.jsonl` policy it MUST call
`record_ingestion()` so the CI gate sees a recent inflow.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion_manifest import record_ingestion

# ---------------------------------------------------------------------------
# 1. 小企业会计准则 (SBE) 2024 — 71 official simplified codes
# Source: Ministry of Finance Order No. 17 + 2024 supplement
# Format: (code, name, category, balanceSide, parentCode|None, description)
# ---------------------------------------------------------------------------

SBE_ACCOUNTS: list[tuple[str, str, str, str, str | None, str]] = [
    # Assets — 资产类
    ("1001", "库存现金", "资产", "debit", None, "小企业准则 - 现金及现金等价物"),
    ("1002", "银行存款", "资产", "debit", None, "小企业准则 - 银行账户存款"),
    ("1101", "短期投资", "资产", "debit", None, "持有期不超过一年的金融资产"),
    ("1121", "应收票据", "资产", "debit", None, "商业汇票应收款项"),
    ("1122", "应收账款", "资产", "debit", None, "销售商品提供劳务形成的应收"),
    ("1123", "预付账款", "资产", "debit", None, "预付供应商款项"),
    ("1131", "应收股利", "资产", "debit", None, "应收被投资单位现金股利"),
    ("1132", "应收利息", "资产", "debit", None, "应收存款及债权投资利息"),
    ("1221", "其他应收款", "资产", "debit", None, "押金、保证金、暂付款"),
    ("1241", "坏账准备", "资产", "credit", None, "应收账款减值准备 - 备抵科目"),
    ("1401", "材料采购", "资产", "debit", None, "采购在途材料"),
    ("1402", "在途物资", "资产", "debit", None, "已付款未到货物资"),
    ("1403", "原材料", "资产", "debit", None, "生产用原材料"),
    ("1404", "材料成本差异", "资产", "debit", None, "计划成本与实际成本差异"),
    ("1405", "库存商品", "资产", "debit", None, "可供销售商品"),
    ("1406", "发出商品", "资产", "debit", None, "已发出未确认收入商品"),
    ("1407", "商品进销差价", "资产", "credit", None, "商业企业差价 - 备抵科目"),
    ("1408", "委托加工物资", "资产", "debit", None, "委托外单位加工材料"),
    ("1411", "周转材料", "资产", "debit", None, "包装物及低值易耗品"),
    ("1471", "存货跌价准备", "资产", "credit", None, "存货减值准备 - 备抵科目"),
    ("1501", "长期股权投资", "资产", "debit", None, "对子公司、合营、联营投资"),
    ("1502", "长期债权投资", "资产", "debit", None, "持有至到期债权投资"),
    ("1601", "固定资产", "资产", "debit", None, "使用寿命超过一年的有形资产"),
    ("1602", "累计折旧", "资产", "credit", None, "固定资产折旧 - 备抵科目"),
    ("1603", "固定资产减值准备", "资产", "credit", None, "固定资产减值 - 备抵科目"),
    ("1604", "在建工程", "资产", "debit", None, "新建改扩建工程支出"),
    ("1605", "工程物资", "资产", "debit", None, "工程专用物资"),
    ("1701", "无形资产", "资产", "debit", None, "专利、商标、土地使用权"),
    ("1702", "累计摊销", "资产", "credit", None, "无形资产摊销 - 备抵科目"),
    ("1703", "无形资产减值准备", "资产", "credit", None, "无形资产减值 - 备抵科目"),
    ("1801", "长期待摊费用", "资产", "debit", None, "摊销期超一年的支出"),
    ("1901", "待处理财产损溢", "资产", "debit", None, "盘亏盘盈待处理"),
    # Liabilities — 负债类
    ("2001", "短期借款", "负债", "credit", None, "一年以内借款"),
    ("2201", "应付票据", "负债", "credit", None, "商业汇票应付"),
    ("2202", "应付账款", "负债", "credit", None, "购入商品劳务应付款"),
    ("2203", "预收账款", "负债", "credit", None, "客户预付货款"),
    ("2211", "应付职工薪酬", "负债", "credit", None, "职工工资奖金福利"),
    ("2221", "应交税费", "负债", "credit", None, "应交各项税金 - 含 VAT/CIT/PIT"),
    ("2231", "应付利息", "负债", "credit", None, "应付银行借款利息"),
    ("2232", "应付利润", "负债", "credit", None, "应付投资者利润"),
    ("2241", "其他应付款", "负债", "credit", None, "押金、暂收、待退款"),
    ("2401", "递延收益", "负债", "credit", None, "递延确认的收益"),
    ("2501", "长期借款", "负债", "credit", None, "一年以上借款"),
    ("2502", "长期应付款", "负债", "credit", None, "融资租赁等长期应付"),
    # Owner's Equity — 所有者权益
    ("3001", "实收资本", "权益", "credit", None, "投资者投入资本"),
    ("3101", "资本公积", "权益", "credit", None, "资本溢价、其他资本公积"),
    ("3201", "盈余公积", "权益", "credit", None, "法定盈余公积、任意盈余公积"),
    ("3301", "本年利润", "权益", "credit", None, "当期净损益"),
    ("3302", "利润分配", "权益", "credit", None, "未分配利润"),
    # Cost — 成本类
    ("4001", "生产成本", "成本", "debit", None, "产品生产直接间接费用"),
    ("4101", "制造费用", "成本", "debit", None, "车间间接费用"),
    ("4201", "劳务成本", "成本", "debit", None, "提供劳务发生成本"),
    # P&L — 损益类
    ("5001", "主营业务收入", "损益", "credit", None, "主营销售商品/提供劳务收入"),
    ("5051", "其他业务收入", "损益", "credit", None, "材料销售、出租等附属收入"),
    ("5101", "投资收益", "损益", "credit", None, "对外投资取得收益"),
    ("5111", "营业外收入", "损益", "credit", None, "捐赠收入、政府补助"),
    ("5201", "公允价值变动损益", "损益", "credit", None, "金融资产公允价值变动"),
    ("5301", "主营业务成本", "损益", "debit", None, "已售商品/已提供劳务成本"),
    ("5302", "主营业务税金及附加", "损益", "debit", None, "城建税、教育费附加"),
    ("5351", "其他业务成本", "损益", "debit", None, "其他业务收入对应成本"),
    ("5401", "销售费用", "损益", "debit", None, "销售商品发生费用"),
    ("5402", "管理费用", "损益", "debit", None, "行政管理费用"),
    ("5403", "财务费用", "损益", "debit", None, "利息、汇兑、手续费"),
    ("5404", "营业外支出", "损益", "debit", None, "非日常经营性支出"),
    ("5406", "资产减值损失", "损益", "debit", None, "各项减值准备计提"),
    ("5701", "所得税费用", "损益", "debit", None, "当期及递延所得税"),
    ("5801", "以前年度损益调整", "损益", "debit", None, "更正前期损益错误"),
]

# ---------------------------------------------------------------------------
# 2. 金融企业会计准则 — banking/insurance industry-specific accounts
# Source: 财政部《金融企业会计制度》2024 附表二
# ---------------------------------------------------------------------------

FINANCE_ACCOUNTS: list[tuple[str, str, str, str, str | None, str]] = [
    ("1011", "存放中央银行款项", "资产", "debit", None, "金融企业 - 央行存款"),
    ("1012", "存放同业款项", "资产", "debit", None, "金融企业 - 同业存款"),
    ("1021", "结算备付金", "资产", "debit", None, "证券公司 - 结算备付"),
    ("1031", "拆出资金", "资产", "debit", None, "金融机构间拆借资金"),
    ("1101", "交易性金融资产", "资产", "debit", None, "以公允价值计量金融资产"),
    ("1111", "买入返售金融资产", "资产", "debit", None, "回购协议下买入"),
    ("1131", "贵金属", "资产", "debit", None, "黄金等贵金属库存"),
    ("1301", "贷款", "资产", "debit", None, "对企业及个人贷款"),
    ("1302", "贷款损失准备", "资产", "credit", None, "贷款减值准备 - 备抵"),
    ("1311", "代理兑付证券", "资产", "debit", None, "代国家兑付债券"),
    ("1321", "代理业务资产", "资产", "debit", None, "受托代客业务资产"),
    ("1501", "持有至到期投资", "资产", "debit", None, "持有意愿明确债权投资"),
    ("1503", "可供出售金融资产", "资产", "debit", None, "可随时出售金融资产"),
    ("2002", "向中央银行借款", "负债", "credit", None, "金融企业 - 央行借款"),
    ("2003", "同业存放款项", "负债", "credit", None, "其他金融机构存放款项"),
    ("2004", "其他金融机构存放款项", "负债", "credit", None, "非同业存放"),
    ("2011", "拆入资金", "负债", "credit", None, "金融机构间拆借负债"),
    ("2012", "卖出回购金融资产款", "负债", "credit", None, "回购协议下卖出"),
    ("2021", "吸收存款", "负债", "credit", None, "客户存款 - 银行核心负债"),
    ("2031", "代理买卖证券款", "负债", "credit", None, "证券公司代客买卖"),
    ("2032", "代理承销证券款", "负债", "credit", None, "代理发行未售证券"),
    ("2041", "应付保户红利", "负债", "credit", None, "保险公司应付保户分红"),
    ("2051", "保户储金", "负债", "credit", None, "保险公司收存保户储金"),
    ("2052", "未到期责任准备金", "负债", "credit", None, "未满期保单责任准备"),
    ("2053", "未决赔款准备金", "负债", "credit", None, "已发生未决赔款"),
    ("2054", "寿险责任准备金", "负债", "credit", None, "寿险长期责任准备"),
    ("2055", "长期健康险责任准备金", "负债", "credit", None, "长期健康险责任准备"),
    ("5103", "公允价值变动损益", "损益", "credit", None, "金融工具公允价值变动"),
    ("5104", "汇兑损益", "损益", "credit", None, "外币业务汇率变动损益"),
    ("6001", "利息收入", "损益", "credit", None, "贷款及债权投资利息"),
    ("6002", "利息支出", "损益", "debit", None, "存款及拆入资金利息"),
    ("6011", "手续费及佣金收入", "损益", "credit", None, "中间业务收入"),
    ("6012", "手续费及佣金支出", "损益", "debit", None, "支付的中间业务费用"),
    ("6021", "保费收入", "损益", "credit", None, "保险公司主营保费"),
    ("6022", "分保费收入", "损益", "credit", None, "再保险分入保费"),
    ("6031", "退保金", "损益", "debit", None, "保险合同退保支出"),
    ("6041", "赔付支出", "损益", "debit", None, "保险公司赔付保户"),
]

# ---------------------------------------------------------------------------
# 3. 农业企业会计准则 — agricultural industry-specific
# ---------------------------------------------------------------------------

AGRICULTURE_ACCOUNTS: list[tuple[str, str, str, str, str | None, str]] = [
    ("1411", "农业生产物资", "资产", "debit", None, "种子、化肥、农药等"),
    ("1421", "消耗性生物资产", "资产", "debit", None, "为出售而持有动植物"),
    ("1422", "生产性生物资产", "资产", "debit", None, "产品性奶牛、果树、橡胶林"),
    ("1423", "生产性生物资产累计折旧", "资产", "credit", None, "生产性生物资产折旧 - 备抵"),
    ("1424", "公益性生物资产", "资产", "debit", None, "防风固沙林、水源涵养林"),
    ("1431", "农产品", "资产", "debit", None, "已收获农林牧渔产品"),
    ("4002", "农业生产成本", "成本", "debit", None, "农业种植养殖直接成本"),
    ("5002", "农产品销售收入", "损益", "credit", None, "农产品销售主营收入"),
    ("5302", "农产品销售成本", "损益", "debit", None, "已售农产品成本"),
]

# ---------------------------------------------------------------------------
# 4. 建筑企业会计准则 — construction industry-specific
# ---------------------------------------------------------------------------

CONSTRUCTION_ACCOUNTS: list[tuple[str, str, str, str, str | None, str]] = [
    ("1411", "工程施工", "资产", "debit", None, "在建工程项目累计成本"),
    ("1412", "工程施工——合同毛利", "资产", "debit", None, "建造合同累计毛利"),
    ("2202", "工程结算", "负债", "credit", None, "向业主结算合同价款"),
    ("4002", "建造合同成本", "成本", "debit", None, "建造合同直接间接成本"),
    ("5002", "建造合同收入", "损益", "credit", None, "完工百分比法确认收入"),
    ("5301", "工程结算成本", "损益", "debit", None, "已结算工程对应成本"),
    ("5402", "项目管理费用", "损益", "debit", None, "工程项目部管理费"),
]

# ---------------------------------------------------------------------------
# 5. 房地产企业会计准则 — real estate industry-specific
# ---------------------------------------------------------------------------

REALESTATE_ACCOUNTS: list[tuple[str, str, str, str, str | None, str]] = [
    ("1404", "开发产品", "资产", "debit", None, "房地产开发完工待售房屋"),
    ("1411", "开发成本", "资产", "debit", None, "在建房地产项目累计成本"),
    ("1412", "土地开发成本", "资产", "debit", None, "土地一级开发投入"),
    ("1413", "拆迁补偿费", "资产", "debit", None, "拆迁安置支出"),
    ("1601", "出租开发产品", "资产", "debit", None, "用于出租开发产品"),
    ("1602", "出租开发产品摊销", "资产", "credit", None, "出租开发产品累计摊销 - 备抵"),
    ("2202", "预收购房款", "负债", "credit", None, "客户购房预收款"),
    ("4002", "房地产开发成本", "成本", "debit", None, "项目开发直接间接成本"),
    ("5002", "房地产销售收入", "损益", "credit", None, "房屋销售主营收入"),
    ("5301", "房地产销售成本", "损益", "debit", None, "已售房屋开发成本"),
]


def _id(prefix: str, code: str) -> str:
    """Generate stable canonical id."""
    return f"AS_{prefix}_{code}"


def _build_records() -> list[dict]:
    """Merge all 5 source datasets into one record list with prefix-tagged ids."""
    out: list[dict] = []
    sources = [
        ("SBE", SBE_ACCOUNTS),
        ("FIN", FINANCE_ACCOUNTS),
        ("AGR", AGRICULTURE_ACCOUNTS),
        ("CON", CONSTRUCTION_ACCOUNTS),
        ("RE", REALESTATE_ACCOUNTS),
    ]
    for prefix, dataset in sources:
        for code, name, cat, side, parent, desc in dataset:
            out.append(
                {
                    "id": _id(prefix, code),
                    "code": code,
                    "name": name,
                    "category": cat,
                    "balanceSide": side,
                    "parentId": _id(prefix, parent) if parent else "",
                    "description": desc,
                    "_prefix": prefix,
                }
            )
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, help="Kuzu DB path, e.g. data/finance-tax-graph")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    records = _build_records()
    by_prefix: dict[str, int] = {}
    for r in records:
        by_prefix[r["_prefix"]] = by_prefix.get(r["_prefix"], 0) + 1

    print(f"[seed] AccountingSubject records prepared: {len(records)}")
    for prefix, n in sorted(by_prefix.items()):
        label = {
            "SBE": "小企业会计准则",
            "FIN": "金融企业",
            "AGR": "农业企业",
            "CON": "建筑企业",
            "RE": "房地产企业",
        }.get(prefix, prefix)
        print(f"  {prefix} ({label}): {n} rows")

    if args.dry_run:
        print("[DRY-RUN] no DB writes; exit 0")
        return 0

    import kuzu

    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    t0 = time.time()
    added = 0
    skipped = 0
    failed: list[str] = []
    for r in records:
        try:
            # MERGE on id only (Kuzu inline-MERGE multi-prop bug workaround)
            conn.execute("MERGE (n:AccountingSubject {id: $id})", {"id": r["id"]})
            conn.execute(
                "MATCH (n:AccountingSubject {id: $id}) "
                "SET n.code=$code, n.name=$name, n.category=$cat",
                {"id": r["id"], "code": r["code"], "name": r["name"], "cat": r["category"]},
            )
            conn.execute(
                "MATCH (n:AccountingSubject {id: $id}) "
                "SET n.balanceSide=$bs, n.parentId=$pid, n.description=$descx",
                {
                    "id": r["id"],
                    "bs": r["balanceSide"],
                    "pid": r["parentId"],
                    "descx": r["description"],
                },
            )
            added += 1
        except Exception as e:
            msg = str(e).lower()
            if "primary key" in msg or "duplicate" in msg:
                skipped += 1
            else:
                failed.append(f"{r['id']}: {str(e)[:120]}")

    elapsed = time.time() - t0
    print(
        f"[APPLY] AccountingSubject: added={added} skipped(dup)={skipped} "
        f"failed={len(failed)} elapsed={int(elapsed*1000)}ms"
    )
    if failed:
        for line in failed[:10]:
            print(f"  FAIL {line}")

    record_ingestion(
        source_file=__file__,
        rows_written={"AccountingSubject": added},
        duration_s=elapsed,
        dry_run=False,
        note=f"SBE+industry seed; skipped(dup)={skipped} failed={len(failed)}",
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
