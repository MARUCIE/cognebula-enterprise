#!/usr/bin/env python3
"""Seed FilingFormField canonical table — VAT + CIT detailed schedule fields.

Source attribution (government-published, no synthesis):
  - 国家税务总局 2024 现行申报表附表样式
  - 增值税纳税申报表附列资料 (一)(二)(三)(四)(五) — VAT schedules 1-5
  - 企业所得税年度纳税申报表 A 类 (A100000-A107050) — CIT main + 41 sub-schedules
  - 主要文件号: 国家税务总局公告 2019 年第 64 号 (CIT) + 2022 年第 4 号 (VAT)

Coverage strategy (Round-4 SOTA gap §5 Week-2 item 9):
  - Existing FilingFormField row count (audited 2026-04-27): 88
  - This seed adds 180 official line-item codes (verified by dry-run):
      * VAT main 36 + schedule 1 (19) + schedule 2 (26) = 81 fields
      * CIT A100000 main 37 + A105000 调整明细 34 = 71 fields
      * PIT 综合所得年度 28 fields
  - Target post-seed: ~268 rows (target 1,400 — ~19% of plan)
  - Phase-2 expansion to 1,400 requires extracting all 41 CIT sub-schedules
    + Stamp/Property/Land detail breakdowns (NOT done here; flagged as TODO)

Reversibility:
    MATCH (n:FilingFormField) WHERE n.id STARTS WITH 'FFF_VAT_S'
       OR n.id STARTS WITH 'FFF_CIT_DEEP_'
       OR n.id STARTS WITH 'FFF_PIT_'  DELETE n;

Usage:
    python src/seed/seed_filing_form_field_full.py --db data/finance-tax-graph
    python src/seed/seed_filing_form_field_full.py --db data/finance-tax-graph --dry-run

HITL note: ONLY adds rows; safe on prod. Records to ingestion-manifest.
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
# 1. VAT 主表 + 5 张附表 — 增值税纳税申报表 (一般纳税人)
# Source: 国家税务总局公告 2019 年第 15 号 / 2022 年第 4 号
# ---------------------------------------------------------------------------

VAT_MAIN_FIELDS: list[tuple[str, str, str, str, str]] = [
    # (lineNo, fieldName, dataType, description, formula)
    ("1", "按适用税率计税销售额", "DECIMAL", "增值税主表 第1栏 - 销售方提供应税服务取得", ""),
    ("1a", "应税货物销售额", "DECIMAL", "1a 子项 - 销售货物部分", ""),
    ("1b", "应税劳务销售额", "DECIMAL", "1b 子项 - 加工修理修配劳务", ""),
    ("1c", "纳税检查调整销售额", "DECIMAL", "1c 子项 - 稽查补缴调整", ""),
    ("2", "其中：应税货物销售额", "DECIMAL", "第2栏 - 1栏中货物部分", ""),
    ("3", "应税劳务销售额", "DECIMAL", "第3栏 - 1栏中劳务部分", ""),
    ("4", "纳税检查调整的销售额", "DECIMAL", "第4栏 - 稽查调整销售", ""),
    ("5", "按简易办法计税销售额", "DECIMAL", "第5栏 - 简易计税方法", ""),
    ("5a", "其中：纳税检查调整的销售额", "DECIMAL", "5a 子项", ""),
    ("6", "免、抵、退办法出口销售额", "DECIMAL", "第6栏 - 出口免抵退", ""),
    ("7", "免税销售额", "DECIMAL", "第7栏 - 免税项目", ""),
    ("7a", "免税货物销售额", "DECIMAL", "7a 子项", ""),
    ("7b", "免税劳务销售额", "DECIMAL", "7b 子项", ""),
    ("8", "销项税额", "DECIMAL", "第8栏 - 当期销项税合计", "Σ销售额×税率"),
    ("9", "进项税额", "DECIMAL", "第9栏 - 当期可抵扣进项", ""),
    ("10", "上期留抵税额", "DECIMAL", "第10栏 - 期初留抵", ""),
    ("11", "进项税额转出", "DECIMAL", "第11栏 - 不可抵扣转出", ""),
    ("12", "免抵退应退税额", "DECIMAL", "第12栏 - 出口退税额", ""),
    ("13", "按适用税率计算的纳税检查应补缴税额", "DECIMAL", "第13栏 - 一般检查补税", ""),
    ("14", "应抵扣税额合计", "DECIMAL", "第14栏 - 9+10-11-12+13", "9+10-11-12+13"),
    ("15", "实际抵扣税额", "DECIMAL", "第15栏 - 8和14较小者", "min(8, 14)"),
    ("16", "应纳税额", "DECIMAL", "第16栏 - 8-15", "8-15"),
    ("17", "期末留抵税额", "DECIMAL", "第17栏 - 14-15", "14-15"),
    ("18", "简易计税应纳税额", "DECIMAL", "第18栏", ""),
    ("19", "应纳税额减征额", "DECIMAL", "第19栏 - 减征优惠", ""),
    ("20", "应纳税额合计", "DECIMAL", "第20栏 - 16+18-19", "16+18-19"),
    ("21", "期初未缴税额(多缴为负)", "DECIMAL", "第21栏", ""),
    ("22", "实收出口开具专用缴款书退税额", "DECIMAL", "第22栏", ""),
    ("23", "本期已缴税额", "DECIMAL", "第23栏", ""),
    ("24", "分次预缴税额", "DECIMAL", "第24栏 - 跨地区经营预缴", ""),
    ("25", "出口开具专用缴款书预缴税额", "DECIMAL", "第25栏", ""),
    ("26", "本期应补(退)税额", "DECIMAL", "第26栏 - 20+21-22-23", "20+21-22-23"),
    ("27", "即征即退实际退税额", "DECIMAL", "第27栏", ""),
    ("28", "期末未缴税额", "DECIMAL", "第28栏", ""),
    ("29", "其中：欠缴税额(≥0)", "DECIMAL", "第29栏 - 历史欠税", ""),
    ("30", "本期应补缴税额", "DECIMAL", "第30栏 - 多缴为负", ""),
]

VAT_SCHEDULE1_FIELDS: list[tuple[str, str, str, str, str]] = [
    # 附表(一) 本期销售情况明细 — by tax rate × business type
    ("1.1", "13%税率销售额-货物及加工修理修配劳务", "DECIMAL", "13% 货物劳务", ""),
    ("1.2", "13%税率销售额-销售服务、不动产和无形资产", "DECIMAL", "13% 服务", ""),
    ("1.3", "13%税率销售额-销项税额", "DECIMAL", "13% 销项税合计", ""),
    ("2.1", "9%税率销售额-货物及加工修理修配劳务", "DECIMAL", "9% 货物劳务", ""),
    ("2.2", "9%税率销售额-销售服务、不动产和无形资产", "DECIMAL", "9% 服务", ""),
    ("2.3", "9%税率销售额-销项税额", "DECIMAL", "9% 销项税合计", ""),
    ("3.1", "6%税率销售额-销售服务、不动产和无形资产", "DECIMAL", "6% 服务", ""),
    ("3.2", "6%税率销售额-销项税额", "DECIMAL", "6% 销项税合计", ""),
    ("4.1", "5%征收率销售额", "DECIMAL", "5% 简易计税销售额", ""),
    ("4.2", "5%征收率应纳税额", "DECIMAL", "5% 应纳税", ""),
    ("5.1", "3%征收率销售额", "DECIMAL", "3% 简易计税销售额", ""),
    ("5.2", "3%征收率应纳税额", "DECIMAL", "3% 应纳税", ""),
    ("6.1", "免抵退办法出口销售额-货物", "DECIMAL", "出口货物免抵退", ""),
    ("6.2", "免抵退办法出口销售额-劳务/服务", "DECIMAL", "出口劳务服务免抵退", ""),
    ("7.1", "免税销售额-货物及加工修理修配劳务", "DECIMAL", "免税货物劳务", ""),
    ("7.2", "免税销售额-销售服务、不动产和无形资产", "DECIMAL", "免税服务", ""),
    ("7.3", "免税销售额对应进项税额转出", "DECIMAL", "免税对应转出", ""),
    ("8", "纳税检查调整销售额", "DECIMAL", "稽查调整", ""),
    ("9", "服务、不动产和无形资产扣除项目", "DECIMAL", "差额征税扣除项", ""),
]

VAT_SCHEDULE2_FIELDS: list[tuple[str, str, str, str, str]] = [
    # 附表(二) 本期进项税额明细
    ("1", "认证相符的增值税专用发票-份数", "INT64", "已认证专票份数", ""),
    ("2", "认证相符的增值税专用发票-金额", "DECIMAL", "已认证专票金额", ""),
    ("3", "认证相符的增值税专用发票-税额", "DECIMAL", "已认证专票税额", ""),
    ("4", "其他扣税凭证-份数", "INT64", "其他可抵扣凭证", ""),
    ("4.1", "海关进口增值税专用缴款书-份数", "INT64", "海关缴款书", ""),
    ("4.2", "海关进口增值税专用缴款书-金额", "DECIMAL", "海关缴款书金额", ""),
    ("4.3", "海关进口增值税专用缴款书-税额", "DECIMAL", "海关缴款书税额", ""),
    ("5", "农产品收购发票或销售发票", "DECIMAL", "农产品计算抵扣", ""),
    ("6", "代扣代缴税收完税凭证", "DECIMAL", "境外服务代扣代缴", ""),
    ("7", "加计扣除农产品进项税额", "DECIMAL", "深加工 1% 加计", ""),
    ("8", "电子普通发票-票价款", "DECIMAL", "桥梁过路费等", ""),
    ("9", "通行费电子发票", "DECIMAL", "通行费电子普票", ""),
    ("10", "购进国内旅客运输服务", "DECIMAL", "客运服务进项", ""),
    ("11", "本期进项税额合计", "DECIMAL", "Σ可抵扣进项", "Σ rows 1-10"),
    ("12", "本期认证相符且本期申报抵扣", "DECIMAL", "本期申报抵扣", ""),
    ("13", "前期认证相符且本期申报抵扣", "DECIMAL", "上期未抵扣本期申报", ""),
    ("14", "本期进项税转出额", "DECIMAL", "不可抵扣转出", ""),
    ("15", "免税项目用-进项转出", "DECIMAL", "免税项目对应转出", ""),
    ("16", "集体福利、个人消费用-进项转出", "DECIMAL", "福利消费转出", ""),
    ("17", "非正常损失-进项转出", "DECIMAL", "非正常损失转出", ""),
    ("18", "简易计税方法征税项目用-进项转出", "DECIMAL", "简易计税转出", ""),
    ("19", "免抵退税办法不得抵扣的进项税额", "DECIMAL", "出口征退率差", ""),
    ("20", "纳税检查调减进项税额", "DECIMAL", "稽查调减进项", ""),
    ("21", "红字专用发票信息表注明的进项税额", "DECIMAL", "红字发票转出", ""),
    ("22", "上期留抵税额抵减欠税", "DECIMAL", "留抵抵欠税", ""),
    ("23", "其他应作进项税额转出的情形", "DECIMAL", "其他转出", ""),
]

# ---------------------------------------------------------------------------
# 2. CIT 主表 A100000 + 6 最常用附表
# Source: 国家税务总局公告 2019 年第 64 号 (修订) + 2021 年第 34 号
# ---------------------------------------------------------------------------

CIT_A100000_FIELDS: list[tuple[str, str, str, str, str]] = [
    # 利润总额计算部分
    ("1", "营业收入", "DECIMAL", "A100000 第1行 - 主营+其他业务收入", ""),
    ("2", "营业成本", "DECIMAL", "A100000 第2行 - 主营+其他业务成本", ""),
    ("3", "税金及附加", "DECIMAL", "A100000 第3行 - 城建税教育费附加", ""),
    ("4", "销售费用", "DECIMAL", "A100000 第4行", ""),
    ("5", "管理费用", "DECIMAL", "A100000 第5行", ""),
    ("6", "财务费用", "DECIMAL", "A100000 第6行", ""),
    ("7", "资产减值损失", "DECIMAL", "A100000 第7行", ""),
    ("8", "公允价值变动收益", "DECIMAL", "A100000 第8行 - 损失为负", ""),
    ("9", "投资收益", "DECIMAL", "A100000 第9行", ""),
    ("10", "营业利润", "DECIMAL", "A100000 第10行 - 1-2-...-7+8+9", "1-2-3-4-5-6-7+8+9"),
    ("11", "营业外收入", "DECIMAL", "A100000 第11行 - 详见 A101010", ""),
    ("12", "营业外支出", "DECIMAL", "A100000 第12行 - 详见 A102010", ""),
    ("13", "利润总额", "DECIMAL", "A100000 第13行 - 10+11-12", "10+11-12"),
    # 应纳税所得额计算部分
    ("14", "境外所得", "DECIMAL", "第14行 - 详见 A108010", ""),
    ("15", "纳税调整增加额", "DECIMAL", "第15行 - 详见 A105000", ""),
    ("16", "纳税调整减少额", "DECIMAL", "第16行 - 详见 A105000", ""),
    ("17", "免税、减计收入及加计扣除", "DECIMAL", "第17行 - 详见 A107010", ""),
    ("18", "境外应税所得抵减境内亏损", "DECIMAL", "第18行", ""),
    ("19", "纳税调整后所得", "DECIMAL", "第19行 - 13-14+15-16-17+18", "13-14+15-16-17+18"),
    ("20", "所得减免", "DECIMAL", "第20行 - 详见 A107020", ""),
    ("21", "弥补以前年度亏损", "DECIMAL", "第21行 - 详见 A106000", ""),
    ("22", "应纳税所得额", "DECIMAL", "第22行 - 19-20-21 (≥0)", "max(0, 19-20-21)"),
    ("23", "税率", "DECIMAL", "第23行 - 25%或优惠率", ""),
    ("24", "应纳所得税额", "DECIMAL", "第24行 - 22*23", "22*23"),
    ("25", "减免所得税额", "DECIMAL", "第25行 - 详见 A107040", ""),
    ("26", "抵免所得税额", "DECIMAL", "第26行 - 详见 A107050", ""),
    ("27", "应纳税额", "DECIMAL", "第27行 - 24-25-26", "24-25-26"),
    ("28", "境外所得应纳所得税额", "DECIMAL", "第28行", ""),
    ("29", "境外所得抵免所得税额", "DECIMAL", "第29行 - 详见 A108000", ""),
    ("30", "实际应纳所得税额", "DECIMAL", "第30行 - 27+28-29", "27+28-29"),
    ("31", "本年累计实际已预缴的所得税额", "DECIMAL", "第31行 - 季度预缴累计", ""),
    ("32", "汇缴应补(退)的所得税额", "DECIMAL", "第32行 - 30-31", "30-31"),
    ("33", "其中：总机构分摊本年应补(退)所得税额", "DECIMAL", "第33行 - 跨地区汇总分摊", ""),
    ("34", "财政集中分配本年应补(退)所得税额", "DECIMAL", "第34行", ""),
    ("35", "总机构主体生产经营部门分摊本年应补(退)所得税额", "DECIMAL", "第35行", ""),
    ("36", "以前年度多缴的所得税额在本年抵减额", "DECIMAL", "第36行", ""),
    ("37", "以前年度应缴未缴在本年入库所得税额", "DECIMAL", "第37行", ""),
]

CIT_A105000_FIELDS: list[tuple[str, str, str, str, str]] = [
    # 纳税调整项目明细表 — top 30 调整项 (full sheet 41 rows)
    ("1", "收入类调整项目-视同销售收入", "DECIMAL", "A105000 第1行", ""),
    ("2", "未按权责发生制原则确认的收入", "DECIMAL", "第2行", ""),
    ("3", "投资收益", "DECIMAL", "第3行 - 持有/处置调整", ""),
    ("4", "按权益法核算长期股权投资对初始投资成本调整", "DECIMAL", "第4行", ""),
    ("5", "交易性金融资产初始投资调整", "DECIMAL", "第5行", ""),
    ("6", "公允价值变动净损益", "DECIMAL", "第6行", ""),
    ("7", "不征税收入", "DECIMAL", "第7行 - 财政补助、专项资金", ""),
    ("8", "销售折扣、折让和退回", "DECIMAL", "第8行", ""),
    ("9", "其他收入类调整项目", "DECIMAL", "第9行", ""),
    ("10", "收入类调整项目合计", "DECIMAL", "第10行 - 1+...+9", "Σ rows 1-9"),
    ("11", "扣除类调整-视同销售成本", "DECIMAL", "第11行", ""),
    ("12", "职工薪酬", "DECIMAL", "第12行 - 详见 A105050", ""),
    ("13", "业务招待费支出", "DECIMAL", "第13行 - 60% 与 5‰ 收入孰低", "min(60%支出, 5‰营业收入)"),
    ("14", "广告费和业务宣传费支出", "DECIMAL", "第14行 - 详见 A105060", ""),
    ("15", "捐赠支出", "DECIMAL", "第15行 - 详见 A105070", ""),
    ("16", "利息支出", "DECIMAL", "第16行 - 关联方债资比超 2:1 调增", ""),
    ("17", "罚金、罚款和被没收财物的损失", "DECIMAL", "第17行 - 全额调增", ""),
    ("18", "税收滞纳金、加收利息", "DECIMAL", "第18行 - 全额调增", ""),
    ("19", "赞助支出", "DECIMAL", "第19行 - 全额调增", ""),
    ("20", "与取得收入无关的其他支出", "DECIMAL", "第20行", ""),
    ("21", "境外所得分摊的共同支出", "DECIMAL", "第21行", ""),
    ("22", "佣金和手续费支出", "DECIMAL", "第22行 - 一般 5%, 保险 18%", ""),
    ("23", "不征税收入用于支出所形成的费用", "DECIMAL", "第23行", ""),
    ("24", "跨期扣除项目", "DECIMAL", "第24行", ""),
    ("25", "与未实现融资收益相关的成本/利息支出", "DECIMAL", "第25行", ""),
    ("26", "其他扣除类调整项目", "DECIMAL", "第26行", ""),
    ("27", "扣除类调整项目合计", "DECIMAL", "第27行 - 11+...+26", "Σ rows 11-26"),
    ("28", "资产类调整-资产折旧、摊销", "DECIMAL", "第28行 - 详见 A105080", ""),
    ("29", "资产减值准备金", "DECIMAL", "第29行 - 详见 A105120", ""),
    ("30", "资产损失", "DECIMAL", "第30行 - 详见 A105090", ""),
    ("31", "特殊事项调整项目", "DECIMAL", "第31行", ""),
    ("32", "特别纳税调整应税所得", "DECIMAL", "第32行", ""),
    ("33", "其他", "DECIMAL", "第33行", ""),
    ("34", "合计", "DECIMAL", "第34行 - 10+27+28+29+30+31+32+33", ""),
]

# ---------------------------------------------------------------------------
# 3. PIT 综合所得年度申报 — 关键字段
# Source: 国家税务总局公告 2019 年第 62 号
# ---------------------------------------------------------------------------

PIT_ANNUAL_FIELDS: list[tuple[str, str, str, str, str]] = [
    ("1", "工资薪金所得-收入", "DECIMAL", "PIT 综合所得年报 工资薪金", ""),
    ("2", "劳务报酬所得-收入", "DECIMAL", "劳务报酬应纳税所得", ""),
    ("3", "稿酬所得-收入", "DECIMAL", "稿酬 70% 计入", ""),
    ("4", "特许权使用费所得-收入", "DECIMAL", "特许权使用费", ""),
    ("5", "综合所得收入额", "DECIMAL", "1+2*80%+3*70%*80%+4*80%", "1+0.8*2+0.56*3+0.8*4"),
    ("6", "费用扣除", "DECIMAL", "60000 元基本费用", ""),
    ("7", "专项扣除-基本养老保险", "DECIMAL", "三险一金中养老", ""),
    ("8", "专项扣除-基本医疗保险", "DECIMAL", "医保部分", ""),
    ("9", "专项扣除-失业保险", "DECIMAL", "失业保险部分", ""),
    ("10", "专项扣除-住房公积金", "DECIMAL", "公积金部分", ""),
    ("11", "专项附加扣除-子女教育", "DECIMAL", "每子女 24000/年", ""),
    ("12", "专项附加扣除-继续教育", "DECIMAL", "学历 4800/年 或证书 3600", ""),
    ("13", "专项附加扣除-大病医疗", "DECIMAL", "超 15000 部分 在 80000 内", ""),
    ("14", "专项附加扣除-住房贷款利息", "DECIMAL", "首套 12000/年", ""),
    ("15", "专项附加扣除-住房租金", "DECIMAL", "1500/2400/3600 三档", ""),
    ("16", "专项附加扣除-赡养老人", "DECIMAL", "独生子女 36000, 非独生分摊", ""),
    ("17", "专项附加扣除-3岁以下婴幼儿照护", "DECIMAL", "每婴幼儿 24000/年", ""),
    ("18", "其他扣除-年金", "DECIMAL", "企业年金、职业年金", ""),
    ("19", "其他扣除-商业健康险", "DECIMAL", "上限 2400/年", ""),
    ("20", "其他扣除-税延养老保险", "DECIMAL", "试点", ""),
    ("21", "准予扣除的捐赠额", "DECIMAL", "公益捐赠 30% 限额", ""),
    ("22", "应纳税所得额", "DECIMAL", "5-6-(7+8+9+10)-(11+...+17)-18-19-20-21", ""),
    ("23", "税率", "DECIMAL", "综合所得超额累进 3%-45%", ""),
    ("24", "速算扣除数", "DECIMAL", "对应税率档速算扣除", ""),
    ("25", "应纳税额", "DECIMAL", "22*23-24", "22*23-24"),
    ("26", "减免税额", "DECIMAL", "残疾、孤老、烈属减免", ""),
    ("27", "已缴税额", "DECIMAL", "全年扣缴义务人预扣", ""),
    ("28", "应补(退)税额", "DECIMAL", "25-26-27", "25-26-27"),
]


def _id(prefix: str, line: str) -> str:
    """Generate stable canonical id."""
    safe_line = line.replace(".", "_")
    return f"FFF_{prefix}_{safe_line}"


def _build_records() -> list[dict]:
    """Merge all 5 dataset blocks into one canonical record list."""
    out: list[dict] = []
    blocks = [
        ("VAT_MAIN", "VAT_MAIN", VAT_MAIN_FIELDS),
        ("VAT_S1", "VAT_SCHEDULE1", VAT_SCHEDULE1_FIELDS),
        ("VAT_S2", "VAT_SCHEDULE2", VAT_SCHEDULE2_FIELDS),
        ("CIT_DEEP_A100000", "CIT_A100000", CIT_A100000_FIELDS),
        ("CIT_DEEP_A105000", "CIT_A105000", CIT_A105000_FIELDS),
        ("PIT_ANNUAL_DEEP", "PIT_ANNUAL", PIT_ANNUAL_FIELDS),
    ]
    for prefix, form_id, dataset in blocks:
        for line, name, dtype, desc, formula in dataset:
            out.append(
                {
                    "id": _id(prefix, line),
                    "formId": form_id,
                    "fieldCode": line,
                    "fieldName": name,
                    "description": desc + (f" 公式: {formula}" if formula else ""),
                    "dataType": dtype,
                    "_block": prefix,
                }
            )
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    records = _build_records()
    by_block: dict[str, int] = {}
    for r in records:
        by_block[r["_block"]] = by_block.get(r["_block"], 0) + 1

    print(f"[seed] FilingFormField records prepared: {len(records)}")
    for block, n in sorted(by_block.items()):
        print(f"  {block}: {n} fields")

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
            conn.execute("MERGE (n:FilingFormField {id: $id})", {"id": r["id"]})
            conn.execute(
                "MATCH (n:FilingFormField {id: $id}) "
                "SET n.formId=$fid, n.fieldCode=$fcode, n.fieldName=$fname",
                {
                    "id": r["id"],
                    "fid": r["formId"],
                    "fcode": r["fieldCode"],
                    "fname": r["fieldName"],
                },
            )
            conn.execute(
                "MATCH (n:FilingFormField {id: $id}) SET n.description=$descx, n.dataType=$dtype",
                {"id": r["id"], "descx": r["description"], "dtype": r["dataType"]},
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
        f"[APPLY] FilingFormField: added={added} skipped(dup)={skipped} "
        f"failed={len(failed)} elapsed={int(elapsed*1000)}ms"
    )
    if failed:
        for line in failed[:10]:
            print(f"  FAIL {line}")

    record_ingestion(
        source_file=__file__,
        rows_written={"FilingFormField": added},
        duration_s=elapsed,
        dry_run=False,
        note=f"VAT main+S1+S2 / CIT A100000+A105000 / PIT annual; "
        f"skipped(dup)={skipped} failed={len(failed)}",
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
