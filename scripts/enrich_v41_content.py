#!/usr/bin/env python3
"""Enrich v4.1 node fullText via Cypher SET through admin API.

Generates domain-accurate content based on existing node metadata (name,
lawReference, incentiveType, rateRange, etc.) without LLM calls.

Run: python3 scripts/enrich_v41_content.py
"""
import json
import urllib.request
import urllib.parse

API = "http://100.75.77.112:8400/api/v1"


def execute_set(statements: list[str]) -> dict:
    """Run SET statements via admin/execute-ddl."""
    payload = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(
        f"{API}/admin/execute-ddl",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def safe(text: str) -> str:
    """Escape single quotes for Cypher."""
    return text.replace("\\", "\\\\").replace("'", "\\'")


# ═══════════════════════════════════════════════════
# 1. TaxType (19 nodes) — comprehensive tax descriptions
# ═══════════════════════════════════════════════════

TAX_TYPE_CONTENT = {
    "TT_VAT": "增值税（Value-Added Tax）是对商品和服务在生产、流通环节产生的增值额征收的流转税。基本税率：13%（销售货物、提供加工修理修配劳务）；9%（交通运输、邮政、基础电信、建筑、不动产租赁、销售不动产、转让土地使用权、农产品等）；6%（增值电信、金融、现代服务、生活服务、销售无形资产）；0%（出口货物，国际运输服务）。小规模纳税人适用3%征收率（2023年至2027年减按1%）。纳税人分为一般纳税人（年销售额超500万元）和小规模纳税人。一般纳税人按销项税额减进项税额计税。法律依据：《中华人民共和国增值税法》（2026年1月1日起施行）。",
    "TT_CIT": "企业所得税是对中国境内企业和其他取得收入的组织的生产经营所得和其他所得征收的税种。基本税率25%。优惠税率：小型微利企业按20%（实际税负5%或2.5%）；高新技术企业15%；技术先进型服务企业15%；西部大开发企业15%。应纳税所得额=收入总额-不征税收入-免税收入-各项扣除-以前年度亏损。按月或按季预缴，年度汇算清缴（次年5月31日前）。法律依据：《中华人民共和国企业所得税法》。",
    "TT_PIT": "个人所得税对居民个人取得的综合所得、经营所得和其他所得征收。综合所得（工资薪金、劳务报酬、稿酬、特许权使用费）适用3%-45%超额累进税率。经营所得适用5%-35%超额累进税率。综合所得年度汇算清缴（次年3月1日至6月30日）。专项附加扣除：子女教育、继续教育、大病医疗、住房贷款利息、住房租金、赡养老人、3岁以下婴幼儿照护。每月基本减除费用5000元。法律依据：《中华人民共和国个人所得税法》。",
    "TT_CONSUMPTION": "消费税是对特定消费品（烟、酒、化妆品、贵重首饰、鞭炮、成品油、摩托车、小汽车、高尔夫球具、高档手表、游艇、木制一次性筷子、实木地板、涂料、电池）在生产、委托加工或进口环节征收的流转税。采用从价定率或从量定额或复合计税方式。税率3%-56%不等。卷烟、白酒采用复合计税。法律依据：《中华人民共和国消费税暂行条例》。",
    "TT_TARIFF": "关税是对进出境货物和物品征收的税种。进口关税税率包括：最惠国税率（适用WTO成员国）、协定税率（自贸协定）、特惠税率（最不发达国家）、普通税率。关税完税价格以CIF价为基础。出口关税仅对少数资源性产品征收。特殊关税：反倾销税、反补贴税、保障措施关税、报复性关税。法律依据：《中华人民共和国关税法》（2024年12月1日起施行）。",
    "TT_URBAN": "城市维护建设税以实际缴纳的增值税、消费税为计税依据，税率按纳税人所在地区分：市区7%、县城/镇5%、其他1%。与增值税、消费税同时缴纳。教育费附加和地方教育附加同样以增值税、消费税为基数。法律依据：《中华人民共和国城市维护建设税法》。",
    "TT_EDUCATION": "教育费附加以实际缴纳的增值税、消费税为计税依据，费率3%。与增值税、消费税同时申报缴纳。月销售额不超过10万元（季度30万元）的小规模纳税人免征。法律依据：《征收教育费附加的暂行规定》。",
    "TT_LOCAL_EDU": "地方教育附加以实际缴纳的增值税、消费税为计税依据，费率2%（部分地区1%）。与增值税、消费税同时申报缴纳。月销售额不超过10万元（季度30万元）的小规模纳税人免征。法律依据：各省地方教育附加征收管理办法。",
    "TT_RESOURCE": "资源税对在中国境内开采应税矿产品或生产盐的单位和个人征收。实行从价计征或从量计征。主要税目：能源矿产（原油、天然气、煤、煤层气、页岩气等）、金属矿产（铁、铜、铝等）、非金属矿产（石灰石、大理石等）、水气矿产（矿泉水、天然卤水等）、盐。税率2%-10%不等。法律依据：《中华人民共和国资源税法》。",
    "TT_LAND_VAT": "土地增值税对转让国有土地使用权、地上建筑物及其附着物并取得收入的单位和个人征收。采用四级超率累进税率：增值额不超过扣除项目金额50%的部分，税率30%；超过50%至100%的部分，40%；超过100%至200%的部分，50%；超过200%的部分，60%。房地产开发企业预征率1%-5%。普通住宅增值率不超过20%免征。法律依据：《中华人民共和国土地增值税暂行条例》。",
    "TT_PROPERTY": "房产税对在城市、县城、建制镇和工矿区的房屋征收。从价计征：按房产原值一次减除10%-30%后余值的1.2%；从租计征：按租金收入的12%（个人出租住房按4%）。自用房产按年征收，分期缴纳。法律依据：《中华人民共和国房产税暂行条例》。",
    "TT_LAND_USE": "城镇土地使用税对在城市、县城、建制镇和工矿区范围内使用土地的单位和个人按年征收。税额标准因城市等级而异：大城市1.5-30元/平方米；中等城市1.2-24元/平方米；小城市0.9-18元/平方米；县城/建制镇/工矿区0.6-12元/平方米。法律依据：《中华人民共和国城镇土地使用税暂行条例》。",
    "TT_VEHICLE": "车船税对在中国境内的车辆和船舶的所有人或管理人征收。乘用车按排量计税：1.0升以下60-360元/年，1.0-1.6升300-540元/年，1.6-2.0升360-660元/年，2.0-2.5升660-1200元/年，2.5-3.0升1200-2400元/年，3.0-4.0升2400-3600元/年，4.0升以上3600-5400元/年。新能源汽车免征。法律依据：《中华人民共和国车船税法》。",
    "TT_STAMP": "印花税对经济活动和经济交往中书立、领受、使用的应税凭证征收。借款合同0.05‰；买卖合同0.3‰；技术合同0.3‰；租赁合同1‰；保管合同1‰；仓储合同1‰；财产保险合同1‰；证券交易1‰（卖方单边）；产权转移书据0.5‰；营业账簿按实收资本和资本公积0.25‰。法律依据：《中华人民共和国印花税法》。",
    "TT_CONTRACT": "契税对转移土地、房屋权属（国有土地使用权出让、转让，房屋买卖、赠与、互换）行为征收。税率1%-5%（具体由省级确定）。个人购买家庭唯一住房：90平方米以下减按1%，90平方米以上减按1.5%。个人购买家庭第二套改善性住房：90平方米以下减按1%，90平方米以上减按2%。法律依据：《中华人民共和国契税法》。",
    "TT_CULTIVATED": "耕地占用税对占用耕地建设建筑物、构筑物或从事非农业建设的单位和个人一次性征收。税额因地区而异：人均耕地不超过1亩的地区，每平方米10-50元；1-2亩，8-40元；2-3亩，6-30元；超过3亩，5-25元。经批准占用耕地的军事设施、学校、幼儿园、社会福利机构、医疗机构免征。法律依据：《中华人民共和国耕地占用税法》。",
    "TT_TOBACCO": "烟叶税对在中国境内收购晾晒烟叶、烤烟叶的单位征收。税率20%。计税依据为烟叶收购金额（包括收购价款和价外补贴，价外补贴统一按收购价款的10%计算）。纳税义务发生时间为收购烟叶的当日。按月计征。法律依据：《中华人民共和国烟叶税法》。",
    "TT_TONNAGE": "船舶吨税对自中国境外港口进入境内港口的船舶征收。按船舶净吨位和吨税执照期限（30日、90日、1年）分级计征。优惠税率适用于与中国签订互惠协定的国家船舶；普通税率适用于其他国家船舶。法律依据：《中华人民共和国船舶吨税法》。",
    "TT_ENV": "环境保护税对直接向环境排放应税污染物的企事业单位和生产经营者征收，替代原排污费。税目：大气污染物（每当量1.2-12元）、水污染物（每当量1.4-14元）、固体废物（每吨5-1000元）、工业噪声（每月350-11200元）。达标排放的城镇污水处理厂、生活垃圾处理场免征。法律依据：《中华人民共和国环境保护税法》。",
}

# ═══════════════════════════════════════════════════
# 2. ComplianceRule — regulatory rules (first 8)
# ═══════════════════════════════════════════════════

COMPLIANCE_RULE_CONTENT = {
    "CR_TAX_REG_30D": "企业自领取营业执照之日起30日内，须持有关证件向税务机关申报办理税务登记。逾期未办理的，由税务机关责令限期改正，可处二千元以下罚款；情节严重的，处二千元以上一万元以下罚款。变更登记事项的，应自工商变更之日起30日内办理变更税务登记。注销时应先办理税务注销，再办理工商注销。法律依据：《税收征收管理法》第十五条。",
    "CR_VAT_MONTHLY": "增值税一般纳税人按月申报缴纳增值税，申报期为次月1-15日（遇法定节假日顺延）。小规模纳税人可选择按月或按季申报。申报时需填报《增值税及附加税费申报表》，附列进项税额明细、销项税额明细等附表。电子税务局申报后通过三方协议自动扣款。逾期申报将产生滞纳金（每日万分之五）。",
    "CR_CIT_QUARTERLY": "企业所得税实行按月或按季预缴、年度汇算清缴的征收方式。预缴期为季度终了之日起15日内。预缴方式：按实际利润额预缴或按上年应纳税所得额的1/4（或1/12）预缴。预缴税款=应纳税所得额×适用税率-减免税额-已预缴税额。跨地区经营汇总纳税企业按总分机构分摊预缴。",
    "CR_CIT_ANNUAL": "企业所得税年度汇算清缴期限为年度终了之日起5个月内（即次年1月1日至5月31日）。需完成：年度纳税申报表填报、税收优惠备案、关联交易申报（符合条件的）、资产损失税前扣除申报。补缴税款或申请退税。逾期未汇缴的，加收滞纳金。重点事项：纳税调增（业务招待费、广告费超限额等）、纳税调减（研发费用加计扣除等）。",
    "CR_PIT_ANNUAL": "综合所得年度汇算清缴期限为次年3月1日至6月30日。需要办理的情形：预缴税额大于汇算应纳税额（可申请退税）；取得两处以上综合所得且合计超过6万元扣除专项后有应纳税额。无需办理的情形：汇算需补税但综合所得不超过12万元；汇算需补税金额不超过400元。通过个人所得税APP办理。",
    "CR_BIZ_ANNUAL": "企业应于每年1月1日至6月30日通过国家企业信用信息公示系统向工商行政管理部门报送上一年度年度报告。内容包括：企业通信地址、联系电话、经营状态、从业人数、资产总额、营业总收入、纳税总额、对外担保、股东出资、股权变更等。逾期未报送的，列入经营异常名录。连续3年未报送的，列入严重违法失信企业名单。",
    "CR_THREE_FLOWS": "三流一致是指发票流、资金流、货物/服务流三者必须一致，即开票方、收款方、发货方须为同一主体。三流不一致的发票不得抵扣进项税额，且可能被认定为虚开发票。常见风险场景：A公司开票但B公司收款（资金流不一致）；合同签订方与发票开具方不一致（发票流不一致）；实际发货方与开票方不一致（货物流不一致）。法律依据：国税发[1995]192号。",
    "CR_INVOICE_AUTH": "增值税专用发票用途确认（原认证/勾选）：自2020年3月1日起取消360天认证期限。一般纳税人取得增值税专用发票后，通过增值税发票综合服务平台进行用途确认（勾选认证）。数电发票（全电发票）系统自动完成用途确认，无需手动勾选。进项发票须在当期申报前完成用途确认。",
}


def enrich_tax_types():
    """Enrich TaxType fullText."""
    print("=== Enriching TaxType (19 nodes) ===")
    stmts = []
    for tid, content in TAX_TYPE_CONTENT.items():
        stmts.append(
            f"MATCH (n:TaxType) WHERE n.id = '{tid}' SET n.fullText = '{safe(content)}'"
        )
    # Batch in groups of 5
    for i in range(0, len(stmts), 5):
        batch = stmts[i:i+5]
        result = execute_set(batch)
        ok = result.get("ok", 0)
        err = result.get("errors", 0)
        print(f"  Batch {i//5+1}: {ok} OK, {err} errors")
        for r in result.get("results", []):
            if r["status"] == "ERROR":
                print(f"    ERROR: {r['reason'][:100]}")


def enrich_compliance_rules():
    """Enrich ComplianceRule fullText (regulatory rules only)."""
    print("=== Enriching ComplianceRule (8 regulatory rules) ===")
    stmts = []
    for crid, content in COMPLIANCE_RULE_CONTENT.items():
        stmts.append(
            f"MATCH (n:ComplianceRule) WHERE n.id = '{crid}' SET n.fullText = '{safe(content)}'"
        )
    result = execute_set(stmts)
    ok = result.get("ok", 0)
    err = result.get("errors", 0)
    print(f"  {ok} OK, {err} errors")
    for r in result.get("results", []):
        if r["status"] == "ERROR":
            print(f"    ERROR: {r['reason'][:100]}")


def enrich_tax_incentives():
    """Enrich TaxIncentive fullText based on existing metadata."""
    print("=== Enriching TaxIncentive ===")

    # Fetch all TaxIncentive nodes
    url = f"{API}/nodes?type=TaxIncentive&limit=120"
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read())

    nodes = data.get("results", [])
    print(f"  Found {len(nodes)} TaxIncentive nodes")

    # Generate fullText from metadata
    type_desc = {
        "exemption": "免征",
        "rate_reduction": "减征/减按",
        "refund": "即征即退/退税",
        "deduction": "加计扣除/税前扣除",
        "deferral": "递延纳税/分期缴纳",
        "credit": "税额抵免",
    }

    stmts = []
    for node in nodes:
        nid = node.get("id", "")
        name = node.get("name", "")
        itype = node.get("incentiveType", "")
        law = node.get("lawReference", "")
        value = node.get("value", "")
        eligibility = node.get("eligibilityCriteria", "")
        max_benefit = node.get("maxAnnualBenefit", "")
        eff_from = node.get("effectiveFrom", "")
        eff_until = node.get("effectiveUntil", "")

        # Build fullText from available metadata
        parts = [f"【{name}】"]
        if itype:
            parts.append(f"优惠类型：{type_desc.get(itype, itype)}")
        if value:
            parts.append(f"优惠内容：{value}")
        if eligibility:
            parts.append(f"适用条件：{eligibility}")
        if max_benefit:
            parts.append(f"年度上限：{max_benefit}")
        if eff_from or eff_until:
            period = f"有效期：{eff_from or '—'} 至 {eff_until or '长期有效'}"
            parts.append(period)
        if law:
            parts.append(f"法律依据：{law}")

        content = "。".join(parts)
        if len(content) < 20:
            continue  # Skip if too little info

        stmts.append(
            f"MATCH (n:TaxIncentive) WHERE n.id = '{safe(nid)}' SET n.fullText = '{safe(content)}'"
        )

    # Execute in batches
    total_ok = 0
    total_err = 0
    for i in range(0, len(stmts), 10):
        batch = stmts[i:i+10]
        result = execute_set(batch)
        total_ok += result.get("ok", 0)
        total_err += result.get("errors", 0)
        for r in result.get("results", []):
            if r["status"] == "ERROR":
                print(f"    ERROR [{r['statement'][:40]}]: {r['reason'][:80]}")

    print(f"  Done: {total_ok} OK, {total_err} errors (of {len(stmts)} statements)")


if __name__ == "__main__":
    enrich_tax_types()
    enrich_compliance_rules()
    enrich_tax_incentives()
    print("\nAll enrichment complete.")
