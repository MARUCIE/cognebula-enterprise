"""Waves 17+18 — VAT_MAIN field deepening + VAT general-taxpayer TCR seed.

Wave 17: extend FilingFormField for VAT_MAIN form (8 → 28 fields) covering
  the full 一般纳税人 calculation chain (销项 / 进项 / 应纳 + 即征即退 +
  留抵 + 出口退税).

Wave 18: seed 15 VAT TaxCalculationRule entries for 一般纳税人 mechanics
  (existing 15 entries are all 小规模; this fills the general-taxpayer gap).

Both waves source from 增值税暂行条例 + 营改增 36 号文 + 财政部税务总局公告
(2017-2025). Together they close the eval set v0 anchor gap for vat_001-005.

Reversibility:
    MATCH (n:FilingFormField {extracted_by: 'wave_17_vat_main'}) DETACH DELETE n;
    MATCH (n:TaxCalculationRule {extracted_by: 'wave_18_vat_general'}) DELETE n;
"""

from __future__ import annotations

import argparse
import sys
import time

import kuzu

# ---- Wave 17: VAT_MAIN deep fields (lines 9-28; lines 1-8 already present) ----

VAT_MAIN_FIELDS: list[tuple[int, str, str, str]] = [
    (9, "即征即退销售额", "input", "软件 / 资源综合利用 / 安置残疾人等享受即征即退优惠的销售额；超过实际税负 3% 部分退还"),
    (10, "免抵退销售额", "input", "出口货物适用免抵退办法的离岸价 FOB（人民币折算）"),
    (11, "免抵退税额", "calculated", "出口销售额 × 退税率；用于计算实际可退税额上限"),
    (12, "应抵扣税额合计", "calculated", "上期留抵 + 本期进项 - 进项转出 + 海关代征已交"),
    (13, "实际抵扣税额", "calculated", "MIN(应抵扣税额合计, 销项税额)；超出部分进入留抵"),
    (14, "应纳税额减征额", "input", "享受减征优惠的金额（如增值税附加税费减半政策导致的减征）"),
    (15, "本期应缴税额", "calculated", "销项税额 - 实际抵扣税额 - 减征额；按月或按季缴纳"),
    (16, "本期已缴税额", "input", "本期已实际缴入国库的税款 + 已缴的预缴税款"),
    (17, "期末未缴税额", "calculated", "本期应缴税额 - 本期已缴税额；正数为欠税，零为正常"),
    (18, "其中：欠缴税额", "calculated", "期末未缴中超过缴纳期限的部分（产生滞纳金）"),
    (19, "本期应退税额", "calculated", "免抵退应退税额 = MIN(免抵退税额, 期末留抵税额)"),
    (20, "应纳税额合计", "calculated", "全部销售额 × 适用税率 - 全部允许抵扣进项 - 全部减免（含小规模、即征即退、免抵退归集）"),
    (21, "海关进口增值税", "input", "进口环节由海关代征的增值税；计入进项可抵扣"),
    (22, "上期留抵税额", "input", "上一申报期结转的留抵税额；可用于本期销项抵扣"),
    (23, "进项转出_免税项目", "input", "用于免税项目的购进货物 / 服务 / 不动产对应的进项需转出"),
    (24, "进项转出_集体福利", "input", "用于集体福利或个人消费的购进对应的进项需转出"),
    (25, "进项转出_非正常损失", "input", "因被盗、丢失、霉烂变质等非正常损失对应的购进进项需转出"),
    (26, "加计抵减额", "input", "邮政、电信、现代服务、生活服务业一般纳税人按进项 5%/10%/15% 加计抵减"),
    (27, "留抵退税额", "calculated", "增量留抵 × 进项构成比例 × 60% (一般行业) / 100% (先进制造业)"),
    (28, "本期未抵扣完结转下期留抵", "calculated", "本期应抵扣 - 本期实际抵扣；下一申报期可继续抵扣"),
]


# ---- Wave 18: VAT general-taxpayer TaxCalculationRule (15 entries) ----

VAT_GENERAL_RULES: list[tuple[str, str, str]] = [
    ("VAT_当期应纳",
     "增值税一般纳税人当期应纳税额公式",
     "当期应纳税额 = 当期销项税额 - 当期可抵扣进项税额；当期销项 < 当期进项时形成留抵。来源：《增值税暂行条例》§4。"),

    ("VAT_销项计算",
     "增值税销项税额计算",
     "销项税额 = 销售额 × 适用税率；销售额不含增值税。13% 适用一般货物；9% 适用粮油食品 / 农产品 / 自来水 / 图书等；6% 适用现代服务 / 金融 / 生活服务。来源：《增值税暂行条例》§5 + 财税[2017]58号。"),

    ("VAT_销项含税转换",
     "含税销售额换算不含税",
     "不含税销售额 = 含税销售额 ÷ (1 + 适用税率)；常见错误：用 1 + 征收率 (3%/5%) 换算一般纳税人金额。来源：《增值税暂行条例》§6。"),

    ("VAT_进项抵扣范围",
     "增值税进项可抵扣范围",
     "可抵扣进项包括：购进货物 / 加工修理修配劳务 / 服务 / 无形资产 / 不动产 (取得增值税专用发票或海关进口缴款书)。来源：《增值税暂行条例》§8。"),

    ("VAT_进项不得抵扣",
     "增值税进项不得抵扣项目",
     "不得抵扣：用于简易计税方法 / 免征增值税项目 / 集体福利或个人消费 / 非正常损失对应的进项。来源：《增值税暂行条例》§10。"),

    ("VAT_即征即退",
     "增值税即征即退（软件 / 资源综合利用）",
     "增值税一般纳税人销售自行开发生产的软件产品按 13% 征收后，对实际税负超过 3% 的部分实行即征即退。资源综合利用按 30%-100% 退税不等。来源：财税[2011]100号 + 财税[2015]78号。"),

    ("VAT_免抵退",
     "出口货物免抵退税",
     "免抵退税额 = 出口销售额 × 退税率；当期应纳 = 销项 - (进项 - 当期不得免征和抵扣税额)；如应纳为负，留抵金额与免抵退税额比较，取小者退税。来源：国税总局 2012 年第 24 号公告。"),

    ("VAT_出口退税不得免征抵扣",
     "出口退税中的不得免征和抵扣税额",
     "当期不得免征和抵扣税额 = 出口销售额 × (适用税率 - 退税率)；该部分进项需转入成本。来源：国税总局 2012 年第 24 号公告 §5。"),

    ("VAT_加计抵减",
     "邮政电信现代服务生活服务业加计抵减",
     "邮政、电信、现代服务、生活服务业一般纳税人，按当期可抵扣进项 5% / 10% / 15% 加计抵减应纳税额。生活服务业 2025 年延续 10%。来源：财税[2019]87号 + 后续延续。"),

    ("VAT_留抵退税",
     "增量留抵退税（2022 全行业）",
     "符合条件的纳税人可申请增量留抵退税。允许退还的增量留抵 = 增量留抵税额 × 进项构成比例 × 60% (一般行业) / 100% (先进制造业、制造业等行业)。来源：财政部税务总局 2022 年第 14 号公告。"),

    ("VAT_简易计税",
     "增值税简易计税办法",
     "一般纳税人销售特定货物或服务可选择简易计税：3% 征收率（原销售自己使用过的固定资产、转让二手车等）；5% 征收率（销售不动产、出租不动产、劳务派遣等）。来源：财税[2016]36号。"),

    ("VAT_兼营",
     "增值税兼营不同税率适用规则",
     "纳税人兼营不同税率或征收率的销售额、营业额，应当分别核算；未分别核算的从高适用税率。来源：《增值税暂行条例》§3。"),

    ("VAT_视同销售",
     "增值税视同销售情形",
     "8 类视同销售：自产/委托加工货物用于非应税项目 / 集体福利 / 个人消费 / 投资分配 / 无偿赠送等。视同销售按市场价或组成计税价计算销项税。来源：《增值税暂行条例实施细则》§4。"),

    ("VAT_预缴",
     "异地建筑/不动产预缴增值税",
     "建筑服务跨县(市、区)提供按 2% (一般计税) 或 3% (简易计税) 预征率预缴；销售自建不动产按 5% 简易计税预缴。来源：国税总局 2016 年第 17 号 + 14 号公告。"),

    ("VAT_纳税义务时间",
     "增值税纳税义务发生时间",
     "采取直接收款方式：收到销售款或取得索取销售款凭据当天；赊销和分期收款：合同约定收款日期当天；预收货款：货物发出当天 (生产周期 12 个月以上为收到预收款当天)。来源：《增值税暂行条例》§19 + 实施细则 §38。"),
]


def seed_wave_17(conn: kuzu.Connection, dry_run: bool) -> tuple[int, int]:
    added = 0
    skipped = 0
    t0 = time.perf_counter()
    form_id = "VAT_MAIN"

    for line_no, name, ftype, formula in VAT_MAIN_FIELDS:
        nid = f"FFF_{form_id}_L{line_no:02d}"
        res = conn.execute(
            "MATCH (n:FilingFormField {id: $nid}) RETURN n.id LIMIT 1", {"nid": nid}
        )
        if res.has_next():
            skipped += 1
            continue
        if dry_run:
            added += 1
            continue
        conn.execute("MERGE (n:FilingFormField {id: $nid})", {"nid": nid})
        conn.execute(
            "MATCH (n:FilingFormField {id: $nid}) "
            "SET n.chineseName = $cn, n.fieldType = $ft, n.formula = $fm",
            {"nid": nid, "cn": name, "ft": ftype, "fm": formula},
        )
        conn.execute(
            "MATCH (n:FilingFormField {id: $nid}) "
            "SET n.source_doc_id = $sdi, n.extracted_by = $eb, n.confidence = $conf",
            {"nid": nid, "sdi": "VAT_MAIN_2024", "eb": "wave_17_vat_main", "conf": 1.0},
        )
        conn.execute(
            "MATCH (f:FilingForm {id: $fid}), (n:FilingFormField {id: $nid}) "
            "MERGE (n)-[:FIELD_OF]->(f)",
            {"fid": form_id, "nid": nid},
        )
        added += 1

    print(f"  Wave 17 added={added} skipped={skipped} elapsed={int((time.perf_counter()-t0)*1000)}ms")
    return added, skipped


def seed_wave_18(conn: kuzu.Connection, dry_run: bool) -> tuple[int, int]:
    added = 0
    skipped = 0
    t0 = time.perf_counter()

    for slug, title, full_text in VAT_GENERAL_RULES:
        nid = slug if slug.startswith("VAT_") else f"VAT_{slug}"
        res = conn.execute(
            "MATCH (n:TaxCalculationRule {id: $nid}) RETURN n.id LIMIT 1", {"nid": nid}
        )
        if res.has_next():
            skipped += 1
            continue
        if dry_run:
            added += 1
            continue
        conn.execute("MERGE (n:TaxCalculationRule {id: $nid})", {"nid": nid})
        conn.execute(
            "MATCH (n:TaxCalculationRule {id: $nid}) "
            "SET n.title = $ttl, n.fullText = $ft, n.regulationType = $rt, n.status = $st",
            {"nid": nid, "ttl": title, "ft": full_text, "rt": "statutory", "st": "active"},
        )
        conn.execute(
            "MATCH (n:TaxCalculationRule {id: $nid}) "
            "SET n.source_doc_id = $sdi, n.extracted_by = $eb, n.confidence = $conf",
            {"nid": nid, "sdi": "vat_general_2017", "eb": "wave_18_vat_general", "conf": 1.0},
        )
        added += 1

    print(f"  Wave 18 added={added} skipped={skipped} elapsed={int((time.perf_counter()-t0)*1000)}ms")
    return added, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    print(f"[wave 17] VAT_MAIN deep candidate: {len(VAT_MAIN_FIELDS)}")
    print(f"[wave 18] VAT general TCR candidate: {len(VAT_GENERAL_RULES)}")
    verb = "[DRY-RUN]" if args.dry_run else "[APPLY]"
    print(verb)
    seed_wave_17(conn, args.dry_run)
    seed_wave_18(conn, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
