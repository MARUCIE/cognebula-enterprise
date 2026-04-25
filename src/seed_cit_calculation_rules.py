"""Seed CIT (Corporate Income Tax) TaxCalculationRule entries.

Source authority: 《中华人民共和国企业所得税法》(2007 主席令 §63) + 实施条例
(2007 国务院令 §512) + 后续修订 + 财政部税务总局公告 (2018-2025).

Each rule is keyed `CIT_<slug>` for easy filtering. fullText is the
canonical statutory paraphrase (≤200 chars) suitable for both LLM
ingestion and accountant audit.

This closes the eval set v0 reasoning anchor gap: cit_001-005 reference
several `TaxCalculationRule:CIT_*` nodes that did not exist before this seed.

Reversibility:
    MATCH (n:TaxCalculationRule) WHERE n.id STARTS WITH 'CIT_' DELETE n;
"""

from __future__ import annotations

import argparse
import sys
import time

import kuzu


CIT_RULES: list[tuple[str, str, str]] = [
    # (id_slug, title, fullText)
    ("CIT_应纳税所得额公式",
     "企业所得税应纳税所得额计算公式",
     "应纳税所得额 = 收入总额 - 不征税收入 - 免税收入 - 各项扣除 - 允许弥补的以前年度亏损。来源：CIT 法 §5。"),

    ("CIT_基本税率",
     "企业所得税基本税率 25%",
     "居民企业及在中国境内设立机构、场所的非居民企业，适用 25% 基本税率。来源：CIT 法 §4。"),

    ("CIT_小微企业减半",
     "小型微利企业税收优惠（2024-2027）",
     "应纳税所得额 100 万元以内部分按 5% 征收（即减按 25% 计入应纳税所得额×20%）；100-300 万元部分按 10% 征收。来源：财政部税务总局 2024 年第 12 号公告。"),

    ("CIT_高新企业",
     "高新技术企业 15% 优惠税率",
     "国家需要重点扶持的高新技术企业，减按 15% 税率征收企业所得税。来源：CIT 法 §28。"),

    ("CIT_西部大开发",
     "西部大开发 15% 优惠税率",
     "设在西部地区的鼓励类产业企业，减按 15% 税率征收企业所得税（2030 年底前延续）。来源：财政部税务总局 2020 年第 23 号公告。"),

    ("CIT_境外抵免",
     "居民企业境外所得税收抵免",
     "居民企业来源于中国境外的应税所得，已在境外缴纳的所得税额，可从其当期应纳税额中抵免；抵免限额为该项所得依本法计算的应纳税额。来源：CIT 法 §23。"),

    ("CIT_弥补亏损5年",
     "企业亏损五年弥补期",
     "企业纳税年度发生的亏损，准予向以后年度结转，用以后年度的所得弥补，但结转年限最长不得超过五年（高新技术企业延长至 10 年）。来源：CIT 法 §18 + 财税[2018]76号。"),

    ("CIT_业务招待费",
     "业务招待费扣除限额",
     "企业发生的与生产经营活动有关的业务招待费支出，按发生额的 60% 扣除，但最高不得超过当年销售（营业）收入的 5‰。来源：CIT 实施条例 §43。"),

    ("CIT_广告宣传费",
     "广告宣传费扣除限额",
     "企业发生的符合条件的广告费和业务宣传费支出，不超过当年销售（营业）收入 15% 的部分准予扣除；超过部分准予在以后纳税年度结转扣除。来源：CIT 实施条例 §44。"),

    ("CIT_公益捐赠",
     "公益性捐赠 12% 扣除限额",
     "企业发生的公益性捐赠支出，在年度利润总额 12% 以内的部分，准予在计算应纳税所得额时扣除；超过部分准予在以后三年内结转扣除。来源：CIT 法 §9 + 财税[2018]15号。"),

    ("CIT_研发费用加计",
     "研发费用加计扣除（2023.1.1 起）",
     "企业开展研发活动发生的研发费用，未形成无形资产计入当期损益的，按实际发生额的 100% 加计扣除；形成无形资产的按成本 200% 摊销。来源：财政部税务总局 2023 年第 7 号公告。"),

    ("CIT_残疾人工资加计",
     "安置残疾人工资 100% 加计扣除",
     "企业安置残疾人员的，在按支付给残疾人员工资据实扣除的基础上，再按支付给残疾人员工资 100% 加计扣除。来源：CIT 法 §30 + 财税[2009]70号。"),

    ("CIT_职工教育经费",
     "职工教育经费 8% 扣除限额",
     "企业发生的职工教育经费支出，不超过工资薪金总额 8% 的部分，准予在计算应纳税所得额时扣除；超过部分准予在以后纳税年度结转扣除。来源：财税[2018]51号。"),

    ("CIT_工会经费",
     "工会经费 2% 扣除限额",
     "企业拨缴的工会经费，不超过工资薪金总额 2% 的部分准予扣除。须凭工会经费收入专用收据。来源：CIT 实施条例 §41。"),

    ("CIT_福利费",
     "职工福利费 14% 扣除限额",
     "企业发生的职工福利费支出，不超过工资薪金总额 14% 的部分准予扣除。来源：CIT 实施条例 §40。"),

    ("CIT_利息支出",
     "关联方利息支出资本弱化限制",
     "企业从其关联方接受的债权性投资与权益性投资比例（金融企业 5:1 / 其他 2:1）超过规定标准而发生的利息支出，不得在计算应纳税所得额时扣除。来源：CIT 法 §46 + 财税[2008]121号。"),

    ("CIT_固定资产折旧",
     "固定资产最低折旧年限",
     "房屋建筑物 20 年；飞机火车轮船机器机械生产设备 10 年；与生产经营活动有关的器具工具家具等 5 年；飞机火车轮船以外运输工具 4 年；电子设备 3 年。来源：CIT 实施条例 §60。"),

    ("CIT_500万一次扣除",
     "设备器具一次性税前扣除（500 万以下）",
     "企业新购进的单位价值不超过 500 万元的设备、器具，允许一次性计入当期成本费用在计算应纳税所得额时扣除（2024-2027 年延续）。来源：财政部税务总局 2023 年第 37 号公告。"),

    ("CIT_无形资产摊销",
     "无形资产摊销年限",
     "无形资产按直线法摊销，摊销年限不得低于 10 年；作为投资或受让的无形资产，有关法律规定或合同约定使用年限的，可按其规定或约定使用年限分期摊销。来源：CIT 实施条例 §67。"),

    ("CIT_长期待摊费用",
     "长期待摊费用摊销年限",
     "已足额提取折旧的固定资产改建支出按预计尚可使用年限分期摊销；租入固定资产改建支出按合同约定剩余租赁期限分期摊销；其他不得低于 3 年。来源：CIT 实施条例 §70。"),

    ("CIT_季度预缴",
     "企业所得税季度预缴",
     "企业所得税分月或者分季度预缴；月度或季度终了之日起 15 日内向税务机关报送预缴企业所得税纳税申报表，预缴税款。来源：CIT 法 §54。"),

    ("CIT_年度汇算",
     "企业所得税年度汇算清缴",
     "自年度终了之日起五个月内（即次年 1 月 1 日 - 5 月 31 日），向税务机关报送年度企业所得税纳税申报表，并汇算清缴，结清应缴应退税款。来源：CIT 法 §54。"),

    ("CIT_预提所得税",
     "非居民企业预提所得税 10%",
     "非居民企业取得来源于中国境内的股息、红利、利息、租金、特许权使用费、转让财产所得等，适用 10% 税率（与中国签订税收协定的可适用协定优惠）。来源：CIT 法 §3 + §27。"),

    ("CIT_技术转让免税",
     "符合条件的技术转让所得",
     "一个纳税年度内，居民企业技术转让所得不超过 500 万元的部分免征企业所得税；超过 500 万元的部分减半征收。来源：CIT 法 §27 + 财税[2010]111号。"),

    ("CIT_农林牧渔减免",
     "农林牧渔业项目税收优惠",
     "企业从事农、林、牧、渔业项目所得（蔬菜、谷物、薯类、油料、豆类、棉花等种植免征；花卉、茶以及其他饮料作物和香料作物的种植减半征收）。来源：CIT 法 §27 + 实施条例 §86。"),

    ("CIT_集成电路10",
     "集成电路企业 10% 优惠",
     "国家鼓励的线宽小于 28 纳米（含）且经营期 15 年以上的集成电路生产企业或项目，第 1-10 年免征企业所得税。来源：财政部税务总局 2020 年第 45 号公告。"),

    ("CIT_软件即征即退",
     "软件产品增值税即征即退（CIT 关联）",
     "增值税一般纳税人销售自行开发生产的软件产品，按 13% 税率征收增值税后，对其增值税实际税负超过 3% 的部分实行即征即退；退还款项不计入企业当年所得税应纳税所得额。来源：财税[2011]100号。"),

    ("CIT_政策性搬迁",
     "政策性搬迁所得分期纳税",
     "企业政策性搬迁取得的搬迁收入，扣除搬迁支出后的余额，应在搬迁完成年度计入应纳税所得额；搬迁期一般不超过 5 年。来源：国家税务总局公告 2012 年第 40 号。"),

    ("CIT_跨年度发票",
     "跨年度发票税前扣除",
     "企业当年度实际发生的相关成本、费用，由于各种原因未能及时取得有效凭证的，企业在预缴季度所得税时，可暂按账面发生金额进行核算；但在汇算清缴时，应补充提供有效凭证。来源：国家税务总局公告 2018 年第 28 号 §6。"),

    ("CIT_关联交易转让定价",
     "关联交易独立交易原则",
     "企业与其关联方之间的业务往来，不符合独立交易原则而减少企业或者其关联方应纳税收入或者所得额的，税务机关有权按合理方法调整。来源：CIT 法 §41 + 国家税务总局公告 2017 年第 6 号。"),
]


def ensure_id_column(conn: kuzu.Connection) -> None:
    """No-op: TaxCalculationRule already has id column from prior waves."""
    pass


def seed_rules(conn: kuzu.Connection, dry_run: bool) -> tuple[int, int]:
    added = 0
    skipped = 0
    t0 = time.perf_counter()

    for slug, title, full_text in CIT_RULES:
        node_id = f"CIT_{slug.removeprefix('CIT_')}"

        # Skip if already present (idempotent)
        res = conn.execute(
            "MATCH (n:TaxCalculationRule {id: $nid}) RETURN n.id LIMIT 1",
            {"nid": node_id},
        )
        if res.has_next():
            skipped += 1
            continue

        if dry_run:
            added += 1
            continue

        # Validated Kuzu pattern
        conn.execute("MERGE (n:TaxCalculationRule {id: $nid})", {"nid": node_id})
        conn.execute(
            "MATCH (n:TaxCalculationRule {id: $nid}) "
            "SET n.title = $ttl, n.fullText = $ft, n.regulationType = $rt, n.status = $st",
            {"nid": node_id, "ttl": title, "ft": full_text, "rt": "statutory", "st": "active"},
        )
        conn.execute(
            "MATCH (n:TaxCalculationRule {id: $nid}) "
            "SET n.source_doc_id = $sdi, n.extracted_by = $eb, n.confidence = $conf",
            {"nid": node_id, "sdi": "cit_law_2007", "eb": "wave_15_cit", "conf": 1.0},
        )
        added += 1

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    print(f"  added={added} skipped_already_present={skipped} elapsed={elapsed_ms}ms")
    return added, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    print(f"[seed CIT TCR] candidate count: {len(CIT_RULES)}")
    verb = "[DRY-RUN]" if args.dry_run else "[APPLY]"
    print(f"{verb} CIT TaxCalculationRule:")
    seed_rules(conn, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
