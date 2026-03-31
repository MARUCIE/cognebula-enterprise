#!/usr/bin/env python3
"""v4.2 Phase 4 Seed — FilingFormField + FIELD_OF / DERIVES_FROM edges.

FilingFormField: 50 key fields from major Chinese tax filing forms.
FIELD_OF: FilingFormField → FilingForm edges.
DERIVES_FROM: FilingFormField → FilingFormField cross-form references.

WARNING: Not idempotent. See docs/KG_GOTCHAS.md #8.
"""

import json
import urllib.request

API_BASE = "http://100.75.77.112:8400"


def api_ddl(statements):
    data = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/execute-ddl", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def cn(table, props):
    parts = []
    for k, v in props.items():
        if v is None:
            continue
        safe = str(v).replace("\\", "\\\\").replace("'", "\\'")
        parts.append(f"{k}: '{safe}'")
    return f"CREATE (n:{table} {{{', '.join(parts)}}})"


def ce(et, ft, fid, tt, tid, p=None):
    ps = ""
    if p:
        parts = [f"{k}: '{str(v).replace(chr(39), chr(92)+chr(39))}'" for k, v in p.items() if v]
        if parts:
            ps = " {" + ", ".join(parts) + "}"
    return (
        f"MATCH (a:{ft}), (b:{tt}) WHERE a.id = '{fid}' AND b.id = '{tid}' "
        f"CREATE (a)-[:{et}{ps}]->(b)"
    )


def batch(stmts, label, bs=20):
    ok = err = 0
    for i in range(0, len(stmts), bs):
        r = api_ddl(stmts[i:i + bs])
        ok += r.get("ok", 0)
        err += r.get("errors", 0)
        for x in r.get("results", []):
            if x.get("status") == "ERROR":
                print(f"  ERROR: {x.get('reason', '')[:120]}")
    print(f"  {label}: {ok} OK, {err} err (of {len(stmts)})")
    return ok, err


# ═══════════════════════════════════════════════════════════════
# DDL: Create FilingFormField node table + edge tables
# ═══════════════════════════════════════════════════════════════
DDL_STATEMENTS = [
    # Node table
    "CREATE NODE TABLE FilingFormField (id STRING, name STRING, chineseName STRING, "
    "formCode STRING, fieldNumber STRING, fieldType STRING, dataType STRING, "
    "formula STRING, description STRING, fullText STRING, "
    "PRIMARY KEY (id))",
    # Edge tables
    "CREATE REL TABLE FIELD_OF (FROM FilingFormField TO FilingForm, description STRING)",
    "CREATE REL TABLE DERIVES_FROM (FROM FilingFormField TO FilingFormField, description STRING)",
]


# ═══════════════════════════════════════════════════════════════
# FilingFormField data — key fields from major tax forms
# ═══════════════════════════════════════════════════════════════
FIELDS = [
    # --- VAT Main Form (增值税纳税申报表主表) ---
    {"id": "FFF_VAT_MAIN_01", "name": "Sales Amount (Tax-inclusive)", "chineseName": "按适用税率计税销售额",
     "formCode": "VAT_MAIN", "fieldNumber": "第1栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "一般计税方法的含税销售额，包括开票和未开票收入"},
    {"id": "FFF_VAT_MAIN_02", "name": "Output Tax", "chineseName": "销项税额",
     "formCode": "VAT_MAIN", "fieldNumber": "第11栏", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第1栏×适用税率", "description": "按适用税率计算的销项税额"},
    {"id": "FFF_VAT_MAIN_03", "name": "Input Tax", "chineseName": "进项税额",
     "formCode": "VAT_MAIN", "fieldNumber": "第12栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "本期认证相符且本期申报抵扣的进项税额"},
    {"id": "FFF_VAT_MAIN_04", "name": "Input Tax Transferred Out", "chineseName": "进项税额转出",
     "formCode": "VAT_MAIN", "fieldNumber": "第14栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "用于非应税项目/免税项目/集体福利等不得抵扣的进项"},
    {"id": "FFF_VAT_MAIN_05", "name": "Tax Payable", "chineseName": "应纳税额",
     "formCode": "VAT_MAIN", "fieldNumber": "第19栏", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第11栏-第18栏", "description": "销项税额减去可抵扣进项后的应纳税额"},
    {"id": "FFF_VAT_MAIN_06", "name": "Simple Method Sales", "chineseName": "简易计税办法销售额",
     "formCode": "VAT_MAIN", "fieldNumber": "第5栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "按简易计税方法的销售额(如小规模/特定业务)"},
    {"id": "FFF_VAT_MAIN_07", "name": "Tax Exempt Sales", "chineseName": "免税销售额",
     "formCode": "VAT_MAIN", "fieldNumber": "第8栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "免征增值税的销售额"},
    {"id": "FFF_VAT_MAIN_08", "name": "Tax Retained Credit", "chineseName": "期末留抵税额",
     "formCode": "VAT_MAIN", "fieldNumber": "第20栏", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第18栏-第11栏(当进项>销项)", "description": "进项大于销项时结转下期的留抵税额"},

    # --- VAT Schedule 1 (附列资料一：销售额明细) ---
    {"id": "FFF_VAT_S1_01", "name": "13% Rate Sales", "chineseName": "13%税率销售额",
     "formCode": "VAT_SCHEDULE1", "fieldNumber": "第1行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "适用13%税率的货物及加工修理修配劳务销售额"},
    {"id": "FFF_VAT_S1_02", "name": "9% Rate Sales", "chineseName": "9%税率销售额",
     "formCode": "VAT_SCHEDULE1", "fieldNumber": "第3行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "适用9%税率的交通运输/建筑/不动产等销售额"},
    {"id": "FFF_VAT_S1_03", "name": "6% Rate Sales", "chineseName": "6%税率销售额",
     "formCode": "VAT_SCHEDULE1", "fieldNumber": "第5行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "适用6%税率的现代服务/生活服务/金融服务等销售额"},

    # --- VAT Schedule 2 (附列资料二：进项税额明细) ---
    {"id": "FFF_VAT_S2_01", "name": "Certified Deductible Input", "chineseName": "认证相符的增值税专用发票",
     "formCode": "VAT_SCHEDULE2", "fieldNumber": "第1栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "本期认证相符且申报抵扣的增值税专用发票税额"},
    {"id": "FFF_VAT_S2_02", "name": "Customs Import VAT", "chineseName": "海关进口增值税专用缴款书",
     "formCode": "VAT_SCHEDULE2", "fieldNumber": "第5栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "进口货物缴纳的增值税"},
    {"id": "FFF_VAT_S2_03", "name": "Agri Product Purchase Input", "chineseName": "农产品收购发票或销售发票",
     "formCode": "VAT_SCHEDULE2", "fieldNumber": "第6栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "农产品收购/销售发票计算抵扣的进项税额"},
    {"id": "FFF_VAT_S2_04", "name": "Transfer Out Detail", "chineseName": "本期进项税额转出额",
     "formCode": "VAT_SCHEDULE2", "fieldNumber": "第13栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "不得抵扣的进项需转出的合计金额"},

    # --- CIT Annual Return Main (企业所得税年度申报表A类主表) ---
    {"id": "FFF_CIT_MAIN_01", "name": "Total Revenue", "chineseName": "营业收入",
     "formCode": "CIT_A100000", "fieldNumber": "第1行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "主营业务收入+其他业务收入"},
    {"id": "FFF_CIT_MAIN_02", "name": "Total Cost", "chineseName": "营业成本",
     "formCode": "CIT_A100000", "fieldNumber": "第2行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "主营业务成本+其他业务成本"},
    {"id": "FFF_CIT_MAIN_03", "name": "Total Profit", "chineseName": "利润总额",
     "formCode": "CIT_A100000", "fieldNumber": "第13行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第1行-第2行-第3行-...-第12行", "description": "按会计准则计算的税前利润"},
    {"id": "FFF_CIT_MAIN_04", "name": "Tax Adjustment Increase", "chineseName": "纳税调增额",
     "formCode": "CIT_A100000", "fieldNumber": "第15行", "fieldType": "input", "dataType": "decimal",
     "formula": "来自A105000", "description": "需要调增应纳税所得额的项目合计"},
    {"id": "FFF_CIT_MAIN_05", "name": "Tax Adjustment Decrease", "chineseName": "纳税调减额",
     "formCode": "CIT_A100000", "fieldNumber": "第16行", "fieldType": "input", "dataType": "decimal",
     "formula": "来自A105000", "description": "可以调减应纳税所得额的项目合计"},
    {"id": "FFF_CIT_MAIN_06", "name": "Taxable Income", "chineseName": "应纳税所得额",
     "formCode": "CIT_A100000", "fieldNumber": "第23行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第13行+第14行+第15行-第16行-...", "description": "计算企业所得税的税基"},
    {"id": "FFF_CIT_MAIN_07", "name": "CIT Payable", "chineseName": "应纳所得税额",
     "formCode": "CIT_A100000", "fieldNumber": "第25行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第23行×第24行(税率)", "description": "应纳税所得额乘以适用税率"},
    {"id": "FFF_CIT_MAIN_08", "name": "Tax Credits", "chineseName": "减免所得税额",
     "formCode": "CIT_A100000", "fieldNumber": "第26行", "fieldType": "input", "dataType": "decimal",
     "formula": "来自A107040", "description": "高新技术/小微/西部开发等减免税额"},

    # --- CIT A105000 (纳税调整项目明细表) ---
    {"id": "FFF_CIT_A105_01", "name": "Entertainment Expense Adjustment", "chineseName": "业务招待费调增",
     "formCode": "CIT_A105000", "fieldNumber": "第15行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "实际发生额-min(发生额×60%,收入×5‰)", "description": "业务招待费超出限额部分需纳税调增"},
    {"id": "FFF_CIT_A105_02", "name": "Advertising Expense Adjustment", "chineseName": "广告宣传费调增",
     "formCode": "CIT_A105000", "fieldNumber": "第16行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "实际发生额-收入×15%(或30%)", "description": "广告费和业务宣传费超出限额部分"},
    {"id": "FFF_CIT_A105_03", "name": "R&D Super Deduction", "chineseName": "研发费用加计扣除调减",
     "formCode": "CIT_A105000", "fieldNumber": "第26行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "研发费用×100%加计", "description": "研发费用100%加计扣除优惠"},
    {"id": "FFF_CIT_A105_04", "name": "Depreciation Adjustment", "chineseName": "折旧摊销调增",
     "formCode": "CIT_A105000", "fieldNumber": "第31行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "会计折旧与税法折旧差异调整"},

    # --- PIT Annual Return (个人所得税年度汇算清缴) ---
    {"id": "FFF_PIT_MAIN_01", "name": "Comprehensive Income", "chineseName": "综合所得收入额",
     "formCode": "PIT_ANNUAL", "fieldNumber": "第1行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "工资薪金+劳务报酬+稿酬+特许权使用费"},
    {"id": "FFF_PIT_MAIN_02", "name": "Standard Deduction", "chineseName": "减除费用",
     "formCode": "PIT_ANNUAL", "fieldNumber": "第5行", "fieldType": "fixed", "dataType": "decimal",
     "formula": "60000元/年", "description": "基本减除费用6万元/年"},
    {"id": "FFF_PIT_MAIN_03", "name": "Special Deductions", "chineseName": "专项扣除",
     "formCode": "PIT_ANNUAL", "fieldNumber": "第6行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "三险一金(养老/医疗/失业+住房公积金)"},
    {"id": "FFF_PIT_MAIN_04", "name": "Special Additional Deductions", "chineseName": "专项附加扣除",
     "formCode": "PIT_ANNUAL", "fieldNumber": "第7行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "子女教育/继续教育/大病医疗/住房贷款/住房租金/赡养老人/婴幼儿照护"},
    {"id": "FFF_PIT_MAIN_05", "name": "PIT Taxable Income", "chineseName": "应纳税所得额",
     "formCode": "PIT_ANNUAL", "fieldNumber": "第11行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "第1行-第5行-第6行-第7行-...", "description": "综合所得减去各项扣除后的应税金额"},

    # --- Stamp Tax Return (印花税申报) ---
    {"id": "FFF_STAMP_01", "name": "Contract Amount", "chineseName": "应税合同计税金额",
     "formCode": "STAMP_RETURN", "fieldNumber": "第1栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "买卖/加工承揽/建设工程等合同的不含税金额"},
    {"id": "FFF_STAMP_02", "name": "Business Book Amount", "chineseName": "营业账簿计税金额",
     "formCode": "STAMP_RETURN", "fieldNumber": "第4栏", "fieldType": "input", "dataType": "decimal",
     "formula": "实收资本+资本公积", "description": "资金账簿按实收资本和资本公积合计计税"},

    # --- VAT Prepayment (增值税预缴) ---
    {"id": "FFF_VAT_PRE_01", "name": "Construction Prepaid VAT", "chineseName": "建筑服务预缴税款",
     "formCode": "VAT_PREPAY", "fieldNumber": "第1栏", "fieldType": "calculated", "dataType": "decimal",
     "formula": "(全部价款-分包款)÷(1+税率)×预征率", "description": "跨区域建筑服务的预缴增值税"},

    # --- City Maintenance & Construction Tax (城市维护建设税) ---
    {"id": "FFF_CITY_01", "name": "City Tax Base", "chineseName": "城建税计税依据",
     "formCode": "CITY_TAX", "fieldNumber": "第1栏", "fieldType": "calculated", "dataType": "decimal",
     "formula": "增值税+消费税实缴税额", "description": "以实际缴纳的增值税和消费税为计税依据"},

    # --- Education Surcharge (教育费附加) ---
    {"id": "FFF_EDU_01", "name": "Education Surcharge", "chineseName": "教育费附加",
     "formCode": "SURCHARGE", "fieldNumber": "第1栏", "fieldType": "calculated", "dataType": "decimal",
     "formula": "(增值税+消费税)×3%", "description": "按增值税和消费税实缴税额的3%征收"},

    # --- Quarterly CIT Prepayment (企业所得税季度预缴) ---
    {"id": "FFF_CIT_Q_01", "name": "Quarterly Revenue", "chineseName": "营业收入(季度)",
     "formCode": "CIT_QUARTERLY", "fieldNumber": "第1行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "本年累计营业收入"},
    {"id": "FFF_CIT_Q_02", "name": "Quarterly Profit", "chineseName": "利润总额(季度)",
     "formCode": "CIT_QUARTERLY", "fieldNumber": "第4行", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "本年累计利润总额(按实际利润额预缴)"},
    {"id": "FFF_CIT_Q_03", "name": "Small Enterprise Reduction", "chineseName": "小微企业减免",
     "formCode": "CIT_QUARTERLY", "fieldNumber": "第12行", "fieldType": "calculated", "dataType": "decimal",
     "formula": "应纳税所得额≤300万的减免额", "description": "小型微利企业所得税减免"},

    # --- Property Tax (房产税申报) ---
    {"id": "FFF_PROP_01", "name": "Original Value Method", "chineseName": "从价计征(原值)",
     "formCode": "PROPERTY_TAX", "fieldNumber": "第1栏", "fieldType": "input", "dataType": "decimal",
     "formula": "原值×(1-30%)×1.2%", "description": "自用房产按原值减除30%后的余值×1.2%"},
    {"id": "FFF_PROP_02", "name": "Rental Value Method", "chineseName": "从租计征(租金)",
     "formCode": "PROPERTY_TAX", "fieldNumber": "第2栏", "fieldType": "input", "dataType": "decimal",
     "formula": "租金收入×12%", "description": "出租房产按租金收入×12%(个人出租住房4%)"},

    # --- Land Use Tax (城镇土地使用税) ---
    {"id": "FFF_LAND_01", "name": "Taxable Area", "chineseName": "应税土地面积",
     "formCode": "LAND_USE_TAX", "fieldNumber": "第1栏", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "实际占用的应税土地面积(平方米)"},

    # --- Withholding PIT (个人所得税扣缴申报) ---
    {"id": "FFF_PIT_WH_01", "name": "Cumulative Income", "chineseName": "累计收入额",
     "formCode": "PIT_WITHHOLDING", "fieldNumber": "第6列", "fieldType": "input", "dataType": "decimal",
     "formula": "", "description": "本年累计工资薪金收入"},
    {"id": "FFF_PIT_WH_02", "name": "Cumulative Withholding Tax", "chineseName": "累计已预扣预缴税额",
     "formCode": "PIT_WITHHOLDING", "fieldNumber": "第16列", "fieldType": "calculated", "dataType": "decimal",
     "formula": "累计应预扣税额-累计减免-累计已扣", "description": "本月应补扣或退还的个税金额"},
]

# ═══════════════════════════════════════════════════════════════
# FIELD_OF edges: FilingFormField → FilingForm
# Map formCode to known FilingForm IDs in KuzuDB
# ═══════════════════════════════════════════════════════════════
FORM_ID_MAP = {
    "VAT_MAIN": "FF_VAT_GENERAL",
    "VAT_SCHEDULE1": "FF_VAT_SCHEDULE1",
    "VAT_SCHEDULE2": "FF_VAT_SCHEDULE2",
    "CIT_A100000": "FF_CIT_ANNUAL",
    "CIT_A105000": "FF_CIT_A105000",
    "PIT_ANNUAL": "FF_PIT_ANNUAL",
    "STAMP_RETURN": "FF_STAMP",
    "VAT_PREPAY": "FF_VAT_PREPAY",
    "CITY_TAX": "FF_CITY_TAX",
    "SURCHARGE": "FF_SURCHARGE",
    "CIT_QUARTERLY": "FF_CIT_QUARTERLY",
    "PROPERTY_TAX": "FF_PROPERTY_TAX",
    "LAND_USE_TAX": "FF_LAND_USE_TAX",
    "PIT_WITHHOLDING": "FF_PIT_WITHHOLDING",
}

# DERIVES_FROM edges: cross-form field references
DERIVES_FROM_EDGES = [
    # CIT main ← A105000
    ("FFF_CIT_MAIN_04", "FFF_CIT_A105_01", "业务招待费调增流入纳税调增额"),
    ("FFF_CIT_MAIN_04", "FFF_CIT_A105_02", "广告费调增流入纳税调增额"),
    ("FFF_CIT_MAIN_04", "FFF_CIT_A105_04", "折旧调增流入纳税调增额"),
    ("FFF_CIT_MAIN_05", "FFF_CIT_A105_03", "研发加计扣除流入纳税调减额"),
    # VAT main ← schedules
    ("FFF_VAT_MAIN_02", "FFF_VAT_S1_01", "13%税率销售额汇总到销项税额"),
    ("FFF_VAT_MAIN_02", "FFF_VAT_S1_02", "9%税率销售额汇总到销项税额"),
    ("FFF_VAT_MAIN_02", "FFF_VAT_S1_03", "6%税率销售额汇总到销项税额"),
    ("FFF_VAT_MAIN_03", "FFF_VAT_S2_01", "专票进项汇总到主表进项税额"),
    ("FFF_VAT_MAIN_04", "FFF_VAT_S2_04", "附表二进项转出汇总到主表"),
    # City tax ← VAT
    ("FFF_CITY_01", "FFF_VAT_MAIN_05", "城建税计税依据来自增值税应纳税额"),
    ("FFF_EDU_01", "FFF_VAT_MAIN_05", "教育费附加计税依据来自增值税应纳税额"),
]


def main():
    print("=== v4.2 Phase 4: FilingFormField Seed ===\n")

    # Step 1: DDL
    print("--- DDL ---")
    r = api_ddl(DDL_STATEMENTS)
    for x in r.get("results", []):
        status = x.get("status", "?")
        stmt_short = x.get("statement", "")[:80]
        reason = x.get("reason", "")
        if status == "ERROR" and "already exists" in reason:
            print(f"  SKIP (exists): {stmt_short}")
        elif status == "ERROR":
            print(f"  ERROR: {reason[:120]}")
        else:
            print(f"  {status}: {stmt_short}")

    # Step 2: Create nodes — only use original schema columns in CREATE,
    # then SET ALTER-added columns (formCode, dataType, formula, fullText, description)
    # See docs/KG_GOTCHAS.md #3: ALTER columns cannot be used in CREATE.
    print("\n--- Nodes ---")
    create_stmts = []
    set_stmts = []
    for f in FIELDS:
        # CREATE with only original columns: id, name, chineseName, fieldNumber, fieldType
        create_stmts.append(cn("FilingFormField", {
            "id": f["id"],
            "name": f["chineseName"],
            "chineseName": f["chineseName"],
            "fieldNumber": f["fieldNumber"],
            "fieldType": f["fieldType"],
        }))
        # SET ALTER-added columns: formCode, dataType, formula, fullText, description
        ft = (
            f"【{f['chineseName']}】表单：{f['formCode']}，栏次：{f['fieldNumber']}，"
            f"类型：{f['fieldType']}。{f['description']}"
        )
        if f["formula"]:
            ft += f"。公式：{f['formula']}"
        safe_ft = ft.replace("'", "\\'")
        safe_desc = f["description"].replace("'", "\\'")
        safe_formula = f.get("formula", "").replace("'", "\\'")
        safe_fc = f["formCode"].replace("'", "\\'")
        safe_dt = f["dataType"].replace("'", "\\'")
        set_stmts.append(
            f"MATCH (n:FilingFormField) WHERE n.id = '{f['id']}' "
            f"SET n.fullText = '{safe_ft}', n.description = '{safe_desc}', "
            f"n.formula = '{safe_formula}', n.formCode = '{safe_fc}', "
            f"n.dataType = '{safe_dt}'"
        )
    batch(create_stmts, "FilingFormField CREATE")
    batch(set_stmts, "FilingFormField SET")

    # Step 3: FIELD_OF edges
    print("\n--- FIELD_OF edges ---")
    field_of_stmts = []
    for f in FIELDS:
        form_id = FORM_ID_MAP.get(f["formCode"])
        if form_id:
            field_of_stmts.append(
                ce("FIELD_OF", "FilingFormField", f["id"],
                   "FilingForm", form_id,
                   {"description": f"{f['chineseName']}→{f['formCode']}"})
            )
    batch(field_of_stmts, "FIELD_OF")

    # Step 4: DERIVES_FROM edges
    print("\n--- DERIVES_FROM edges ---")
    derives_stmts = []
    for src, tgt, desc in DERIVES_FROM_EDGES:
        derives_stmts.append(
            ce("DERIVES_FROM", "FilingFormField", src,
               "FilingFormField", tgt,
               {"description": desc})
        )
    batch(derives_stmts, "DERIVES_FROM")

    print(f"\n=== Summary ===")
    print(f"FilingFormField nodes: {len(FIELDS)}")
    print(f"FIELD_OF edges: {len(field_of_stmts)}")
    print(f"DERIVES_FROM edges: {len(derives_stmts)}")


if __name__ == "__main__":
    main()
