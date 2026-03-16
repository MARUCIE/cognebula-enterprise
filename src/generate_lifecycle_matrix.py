#!/usr/bin/env python3
"""Generate lifecycle x incentive + filing guide matrices.

Matrix 3: LifecycleStage x TaxIncentive x Industry guidance
Matrix 4: TaxType x Industry x scenario detailed filing guides

Usage:
    python src/generate_lifecycle_matrix.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import sys


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


LIFECYCLE_TAX_GUIDANCE = {
    "设立": [
        "营业执照办理后30日内办理税务登记",
        "选择纳税人类型(一般纳税人/小规模纳税人)",
        "签订三方协议(银行-企业-税务)",
        "领购发票、开通电子税务局",
        "确定会计制度和核算方法",
    ],
    "筹建": [
        "筹建期间费用可在开始经营后扣除",
        "固定资产购置进项税可抵扣",
        "筹建期利息支出资本化vs费用化判断",
        "印花税: 注册资本实缴部分万分之二点五",
    ],
    "运营": [
        "增值税月度/季度申报",
        "企业所得税季度预缴+年度汇算清缴",
        "个税代扣代缴月度申报",
        "印花税按次/汇总申报",
        "城建税/教育费附加随增值税申报",
    ],
    "扩张": [
        "分支机构税务登记+汇总纳税",
        "股权融资的税务处理(增资vs股权转让)",
        "高新技术企业认定(15%优惠税率)",
        "研发费用加计扣除(120%)",
        "跨区域经营预缴税款",
    ],
    "重组": [
        "资产重组特殊性税务处理(递延纳税)",
        "企业合并/分立的增值税处理",
        "债转股的企业所得税处理",
        "股权收购的税务成本确认",
    ],
    "注销": [
        "清税证明办理流程",
        "未抵扣进项税额处理",
        "剩余资产分配的所得税处理",
        "发票缴销和税控设备注销",
    ],
    "清算": [
        "清算所得=资产处置收入-清算费用-负债-所有者权益",
        "清算期为独立纳税期间",
        "剩余资产分配顺序: 职工工资→社保→税款→普通债权→股东",
    ],
}

INDUSTRY_FILING_SCENARIOS = {
    "制造业": [
        ("一般纳税人增值税申报", "制造业一般纳税人按月申报增值税。主表填写销项税额(13%)、进项税额、应纳税额。附表一填写销售明细，附表二填写进项明细。"),
        ("出口退税申报", "有出口业务的制造企业需要申报出口退税。免抵退税额=出口货物离岸价x退税率。需要提供报关单、增值税专用发票等单据。"),
        ("研发费用加计扣除", "制造业企业研发费用可100%加计扣除(2023年起)。需要单独设立研发费用辅助账，区分人员人工费、直接投入费用、折旧费等。"),
    ],
    "建筑业": [
        ("预缴增值税", "建筑企业跨县(市、区)提供建筑服务需要预缴增值税。一般计税预缴率2%，简易计税预缴率3%。"),
        ("异地施工税务处理", "项目所在地预缴，机构所在地申报。需要开具《外管证》或通过电子税务局报验。"),
        ("工程完工结算", "工程完工后需要确认收入、结转成本、计算应纳税所得额。注意收入确认时点与完工进度的关系。"),
    ],
    "房地产业": [
        ("土地增值税预缴", "预售商品房需按预收款预缴土地增值税。各地预征率不同(一般2%-5%)。"),
        ("增值税预缴", "预售商品房需按3%预缴增值税。应预缴税款=预收款/(1+9%或5%)x3%。"),
        ("企业所得税预缴", "房地产企业预售收入需按计税毛利率预缴企业所得税。各地毛利率标准不同(一般15%-30%)。"),
    ],
    "软件和信息技术": [
        ("增值税即征即退", "软件产品增值税实际税负超过3%的部分即征即退。需要单独核算软件产品收入和成本。"),
        ("高新技术企业", "符合条件的软件企业可认定高新技术企业，享受15%企业所得税优惠税率。需要研发费用占比达标。"),
        ("无形资产加速摊销", "软件企业购入的软件可缩短摊销年限至2年或采用加速摊销方法。"),
    ],
    "医疗美容": [
        ("生活服务增值税", "医美服务按生活服务6%税率缴纳增值税。美容手术与医疗美容的税率区分是关键。"),
        ("消费税风险", "高端化妆品零售环节需关注消费税。进口化妆品消费税率15%。"),
    ],
    "物业管理": [
        ("简易计税选择", "物业公司可选择简易计税(5%)或一般计税(6%)。一旦选择36个月内不得变更。"),
        ("代收代缴水电", "代收水电费可选择差额征税或全额征税。差额征税只对服务费部分缴税。"),
    ],
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

    count = 0

    # Matrix 3: Lifecycle x Industry guidance
    print("=== Lifecycle Tax Guidance ===")
    industries_sample = ["制造业", "建筑业", "房地产业", "软件和信息技术", "医疗美容",
                         "物业管理", "人力资源服务", "网络直播", "汽车经销", "采矿业",
                         "学前教育", "律师事务所", "合伙企业", "民间非营利组织",
                         "煤炭开采和洗选", "混凝土搅拌", "黄金零售", "再生资源", "出口退税企业",
                         "劳务派遣", "高新技术企业", "跨境电商", "餐饮业", "物流运输",
                         "医疗卫生", "教育培训", "农业"]

    for stage, items in LIFECYCLE_TAX_GUIDANCE.items():
        for ind in industries_sample:
            for i, item in enumerate(items):
                nid = f"LR_LIFE_{hashlib.md5(f'{stage}_{ind}_{i}'.encode()).hexdigest()[:8]}"
                title = f"[生命周期指南] {ind} - {stage}阶段 - {item[:40]}"
                content = f"{ind}企业在{stage}阶段的税务要点:\n{item}\n\n适用行业: {ind}\n生命周期阶段: {stage}"

                if args.dry_run:
                    count += 1
                    continue

                sql = (
                    f"CREATE (n:LawOrRegulation {{"
                    f"id: '{esc(nid)}', title: '{esc(title[:200])}', "
                    f"regulationNumber: '', issuingAuthority: 'lifecycle-matrix', "
                    f"regulationType: 'lifecycle_guidance', "
                    f"issuedDate: date('2026-01-01'), effectiveDate: date('2026-01-01'), "
                    f"expiryDate: date('2099-12-31'), status: 'reference', hierarchyLevel: 99, "
                    f"sourceUrl: '', contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
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

    print(f"Lifecycle guidance: +{count}")

    # Matrix 4: Industry-specific filing scenarios
    print("=== Industry Filing Scenarios ===")
    filing_count = 0
    for ind, scenarios in INDUSTRY_FILING_SCENARIOS.items():
        for title_text, content_text in scenarios:
            nid = f"LR_FILING_{hashlib.md5(f'{ind}_{title_text}'.encode()).hexdigest()[:8]}"
            title = f"[申报指南] {ind} - {title_text}"
            content = f"{ind}{title_text}:\n{content_text}"

            if args.dry_run:
                filing_count += 1
                continue

            sql = (
                f"CREATE (n:LawOrRegulation {{"
                f"id: '{esc(nid)}', title: '{esc(title[:200])}', "
                f"regulationNumber: '', issuingAuthority: 'filing-guide-matrix', "
                f"regulationType: 'filing_guide', "
                f"issuedDate: date('2026-01-01'), effectiveDate: date('2026-01-01'), "
                f"expiryDate: date('2099-12-31'), status: 'reference', hierarchyLevel: 99, "
                f"sourceUrl: '', contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
                f"fullText: '{esc(content[:1000])}', "
                f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
                f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
                f"txTimeCreated: timestamp('2026-03-16 00:00:00'), "
                f"txTimeUpdated: timestamp('2026-03-16 00:00:00')"
                f"}})"
            )
            try:
                conn.execute(sql)
                filing_count += 1
            except Exception:
                pass

    print(f"Filing scenarios: +{filing_count}")
    print(f"Total new: +{count + filing_count}")

    if conn:
        r = conn.execute("MATCH (n) RETURN count(n)")
        print(f"Grand total: {r.get_next()[0]}")


if __name__ == "__main__":
    main()
