"""Deepen FilingFormField for CIT 年度 A100000 主表.

The CIT_A100000 form (企业所得税年度纳税申报表主表) has ~50 fields. Wave 5
seeded only the top 8 calculation fields. This wave adds 20 more covering
the full 利润总额 → 应纳税所得额 → 应纳所得税额 chain (lines 1-23 of the
form per 国家税务总局公告 2024 年第 16 号 latest revision).

Each field links to FilingForm via FIELD_OF edge.

Reversibility:
    MATCH (n:FilingFormField {extracted_by: 'wave_16_cit_main'}) DETACH DELETE n;
"""

from __future__ import annotations

import argparse
import sys
import time

import kuzu

FORM_ID = "CIT_A100000"

# Each entry: (line_no, chineseName, field_type, formula_or_source_line)
# Lines reference the official A100000 row numbers.
CIT_MAIN_FIELDS: list[tuple[int, str, str, str]] = [
    (1, "营业收入", "input", "取自利润表-营业收入栏"),
    (2, "营业成本", "input", "取自利润表-营业成本栏"),
    (3, "利润总额", "calculated", "利润表-利润总额；此为本表起始项"),
    (4, "境外所得", "input", "境外分支机构、子公司利润；适用补税或抵免规则"),
    (5, "纳税调整增加额", "calculated", "汇总 A105000 调整明细表第 38 行（费用类调增）"),
    (6, "纳税调整减少额", "calculated", "汇总 A105000 调整明细表第 39 行（收入类调减）"),
    (7, "免税、减计收入及加计扣除", "calculated", "免税收入 + 减计收入 + 研发费用加计扣除等"),
    (8, "境外应税所得抵减境内亏损", "input", "境外利润可用以抵减境内亏损"),
    (9, "纳税调整后所得", "calculated", "第 3 行 + 第 5 行 - 第 6 行 - 第 7 行 + 第 8 行"),
    (10, "所得减免", "input", "符合条件的农林牧渔、技术转让所得等可减免项"),
    (11, "弥补以前年度亏损", "input", "前 5 年度内可弥补的亏损额（高新企业 10 年）"),
    (12, "应纳税所得额", "calculated", "第 9 行 - 第 10 行 - 第 11 行；如为负则为亏损额"),
    (13, "税率", "input", "基本 25%；小微 5/10%；高新 15%；西部大开发 15% 等"),
    (14, "应纳所得税额", "calculated", "第 12 行 × 第 13 行"),
    (15, "减免所得税额", "calculated", "汇总各项减免税；引用 A107040 减免明细表"),
    (16, "抵免所得税额", "calculated", "境外已纳税抵免 + 设备投资抵免；引用 A107050"),
    (17, "应纳税额", "calculated", "第 14 行 - 第 15 行 - 第 16 行"),
    (18, "境外所得应纳所得税额", "calculated", "境外所得 × 25% 计算限额；超额部分不抵免"),
    (19, "境外所得抵免所得税额", "calculated", "实际抵免 = MIN(已纳税额, 限额)"),
    (20, "实际应纳所得税额", "calculated", "第 17 行 + 第 18 行 - 第 19 行"),
    (21, "本年累计实际已预缴的所得税额", "input", "取自季度预缴申报记录汇总"),
    (22, "本年应补（退）的所得税额", "calculated", "第 20 行 - 第 21 行；正数补缴负数退税"),
    (23, "总机构分摊比例（跨地区）", "input", "适用 A109000 跨地区汇总纳税分摊表"),
]


def field_id(line_no: int) -> str:
    return f"{FORM_ID}_L{line_no:02d}"


def seed(conn: kuzu.Connection, dry_run: bool) -> tuple[int, int]:
    added = 0
    skipped = 0
    t0 = time.perf_counter()

    for line_no, name, ftype, formula in CIT_MAIN_FIELDS:
        nid = field_id(line_no)
        # Skip if already present
        res = conn.execute(
            "MATCH (n:FilingFormField {id: $nid}) RETURN n.id LIMIT 1",
            {"nid": nid},
        )
        if res.has_next():
            skipped += 1
            continue

        if dry_run:
            added += 1
            continue

        # Node create + props
        conn.execute("MERGE (n:FilingFormField {id: $nid})", {"nid": nid})
        conn.execute(
            "MATCH (n:FilingFormField {id: $nid}) "
            "SET n.chineseName = $cn, n.fieldType = $ft, n.formula = $fm",
            {"nid": nid, "cn": name, "ft": ftype, "fm": formula},
        )
        conn.execute(
            "MATCH (n:FilingFormField {id: $nid}) "
            "SET n.source_doc_id = $sdi, n.extracted_by = $eb, n.confidence = $conf",
            {"nid": nid, "sdi": "CIT_A100000_2024_v16", "eb": "wave_16_cit_main", "conf": 1.0},
        )

        # FIELD_OF edge to the form
        conn.execute(
            "MATCH (f:FilingForm {id: $fid}), (n:FilingFormField {id: $nid}) "
            "MERGE (n)-[:FIELD_OF]->(f)",
            {"fid": FORM_ID, "nid": nid},
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

    print(f"[seed CIT A100000 fields] candidate count: {len(CIT_MAIN_FIELDS)}")
    verb = "[DRY-RUN]" if args.dry_run else "[APPLY]"
    print(f"{verb} FilingFormField (CIT_A100000 deep):")
    seed(conn, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
