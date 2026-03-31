"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { listNodes, getGraph, getStats, type KGNeighbor, type KGStats, LAYER_GROUPS, NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS } from "../../lib/kg-api";
import { CN, cnCard, cnBadge, cnInput, cnBtn, cnBtnPrimary } from "../../lib/cognebula-theme";

/* ── v4.2 ontology: 35 node types across 4 layers ── */
const BROWSABLE_TYPES = [
  // L1 法规层
  { table: "LegalClause", label: "法规条款", layer: "L1 法规层" },
  { table: "LegalDocument", label: "法律文件", layer: "L1 法规层" },
  { table: "IssuingBody", label: "发布机构", layer: "L1 法规层" },
  { table: "AccountingStandard", label: "会计准则", layer: "L1 法规层" },
  { table: "TaxTreaty", label: "税收协定", layer: "L1 法规层" },
  // L2 业务层
  { table: "TaxRate", label: "税率", layer: "L2 业务层" },
  { table: "AccountingSubject", label: "会计科目", layer: "L2 业务层" },
  { table: "Classification", label: "HS海关编码", layer: "L2 业务层" },
  { table: "TaxClassificationCode", label: "税收分类编码", layer: "L2 业务层" },
  { table: "TaxEntity", label: "纳税主体", layer: "L2 业务层" },
  { table: "Region", label: "行政区域", layer: "L2 业务层" },
  { table: "FilingForm", label: "申报表", layer: "L2 业务层" },
  { table: "BusinessActivity", label: "业务活动", layer: "L2 业务层" },
  { table: "JournalEntryTemplate", label: "分录模板", layer: "L2 业务层" },
  { table: "FinancialStatementItem", label: "报表项目", layer: "L2 业务层" },
  { table: "FilingFormField", label: "申报栏次", layer: "L2 业务层" },
  { table: "TaxItem", label: "税目", layer: "L2 业务层" },
  { table: "TaxBasis", label: "计税依据", layer: "L2 业务层" },
  { table: "TaxLiabilityTrigger", label: "纳税义务时点", layer: "L2 业务层" },
  { table: "TaxMilestoneEvent", label: "生命周期事件", layer: "L2 业务层" },
  // L3 合规层
  { table: "ComplianceRule", label: "合规规则", layer: "L3 合规层" },
  { table: "RiskIndicator", label: "风险指标", layer: "L3 合规层" },
  { table: "TaxIncentive", label: "税收优惠", layer: "L3 合规层" },
  { table: "Penalty", label: "处罚规定", layer: "L3 合规层" },
  { table: "AuditTrigger", label: "审计触发", layer: "L3 合规层" },
  { table: "TaxAccountingGap", label: "税会差异", layer: "L3 合规层" },
  { table: "SocialInsuranceRule", label: "社保公积金", layer: "L3 合规层" },
  { table: "InvoiceRule", label: "发票规则", layer: "L3 合规层" },
  { table: "IndustryBenchmark", label: "行业基准", layer: "L3 合规层" },
  { table: "TaxCalculationRule", label: "计算规则", layer: "L3 合规层" },
  { table: "FinancialIndicator", label: "财务指标", layer: "L3 合规层" },
  { table: "DeductionRule", label: "扣除限额", layer: "L3 合规层" },
  { table: "ResponseStrategy", label: "应对策略", layer: "L3 合规层" },
  { table: "PolicyChange", label: "政策变动", layer: "L3 合规层" },
  // L4 知识层
  { table: "TaxType", label: "税种", layer: "L4 知识层" },
  { table: "KnowledgeUnit", label: "知识单元", layer: "L4 知识层" },
];

interface NodeRow {
  id: string;
  title: string;
  subtitle: string;
  content: string;
  col1: string;
  col2: string;
  col3: string;
  raw: Record<string, unknown>;
}

interface NodeDetail {
  node: NodeRow;
  neighbors: KGNeighbor[];
  parentDocName?: string;
}

/* ── Type-specific column definitions (v4.1 ontology) ── */
const TYPE_COLUMNS: Record<string, { c1: string; c2: string; c3: string }> = {
  // L1
  LegalClause: { c1: "条款号", c2: "所属法规", c3: "条款内容" },
  LegalDocument: { c1: "文件名称", c2: "类型", c3: "生效日期" },
  IssuingBody: { c1: "机构名称", c2: "级别", c3: "管辖范围" },
  // L2
  TaxRate: { c1: "税率名称", c2: "税率范围", c3: "适用条件" },
  AccountingSubject: { c1: "科目名称", c2: "科目编号", c3: "方向" },
  Classification: { c1: "分类名称", c2: "编码体系", c3: "说明" },
  TaxClassificationCode: { c1: "税收编码", c2: "品类", c3: "说明" },
  TaxEntity: { c1: "纳税主体", c2: "类型", c3: "适用税种" },
  Region: { c1: "地区名称", c2: "级别", c3: "适用政策" },
  FilingForm: { c1: "表单名称", c2: "所属税种", c3: "申报周期" },
  BusinessActivity: { c1: "业务活动", c2: "风险等级", c3: "说明" },
  // L3
  ComplianceRule: { c1: "规则名称", c2: "规则类型", c3: "内容摘要" },
  RiskIndicator: { c1: "指标名称", c2: "风险等级", c3: "说明" },
  TaxIncentive: { c1: "优惠名称", c2: "优惠类型", c3: "法律依据" },
  Penalty: { c1: "处罚名称", c2: "处罚类型", c3: "说明" },
  AuditTrigger: { c1: "触发条件", c2: "风险等级", c3: "说明" },
  TaxAccountingGap: { c1: "差异名称", c2: "差异类型", c3: "会计处理 vs 税务处理" },
  SocialInsuranceRule: { c1: "险种名称", c2: "单位费率", c3: "个人费率" },
  InvoiceRule: { c1: "规则名称", c2: "规则类型", c3: "适用条件" },
  IndustryBenchmark: { c1: "指标名称", c2: "行业代码", c3: "基准范围" },
  // L4
  TaxType: { c1: "税种名称", c2: "税率范围", c3: "申报周期" },
  KnowledgeUnit: { c1: "知识主题", c2: "类型", c3: "来源" },
  // v4.2 types
  AccountingStandard: { c1: "准则名称", c2: "CAS编号", c3: "适用范围" },
  TaxTreaty: { c1: "协定名称", c2: "签约方", c3: "生效日期" },
  JournalEntryTemplate: { c1: "分录名称", c2: "借方科目", c3: "贷方科目" },
  FinancialStatementItem: { c1: "项目名称", c2: "所属报表", c3: "计算公式" },
  FilingFormField: { c1: "栏次名称", c2: "所属表单", c3: "填报规则" },
  TaxItem: { c1: "税目名称", c2: "所属税种", c3: "税率" },
  TaxBasis: { c1: "计税依据", c2: "计税方式", c3: "说明" },
  TaxLiabilityTrigger: { c1: "触发条件", c2: "适用税种", c3: "时点规则" },
  TaxMilestoneEvent: { c1: "事件名称", c2: "阶段", c3: "税务影响" },
  TaxCalculationRule: { c1: "规则名称", c2: "适用税种", c3: "公式" },
  FinancialIndicator: { c1: "指标名称", c2: "指标类型", c3: "计算公式" },
  DeductionRule: { c1: "扣除项目", c2: "限额标准", c3: "超限处理" },
  ResponseStrategy: { c1: "策略名称", c2: "策略类型", c3: "操作步骤" },
  PolicyChange: { c1: "政策名称", c2: "变更类型", c3: "影响范围" },
};

const DEFAULT_COLUMNS = { c1: "名称", c2: "分类", c3: "说明" };

/* ── Hierarchical category menus for large tables ── */
interface CategoryItem { label: string; query: string; desc?: string }
interface CategoryGroup { title: string; icon: string; items: CategoryItem[] }

const LARGE_TABLE_CATEGORIES: Record<string, CategoryGroup[]> = {
  LegalClause: [
    { title: "流转税", icon: "O", items: [
      { label: "增值税", query: "增值税" },
      { label: "消费税", query: "消费税" },
      { label: "关税", query: "关税" },
      { label: "出口退税", query: "出口退税" },
    ]},
    { title: "所得税", icon: "O", items: [
      { label: "企业所得税", query: "企业所得税" },
      { label: "个人所得税", query: "个人所得税" },
      { label: "预缴/汇缴", query: "预缴" },
      { label: "纳税调整", query: "纳税调整" },
    ]},
    { title: "财产行为税", icon: "O", items: [
      { label: "印花税", query: "印花税" },
      { label: "土地增值税", query: "土地增值税" },
      { label: "房产税", query: "房产税" },
      { label: "契税", query: "契税" },
      { label: "车船税", query: "车船税" },
      { label: "城镇土地使用税", query: "城镇土地使用税" },
      { label: "耕地占用税", query: "耕地占用税" },
      { label: "资源税", query: "资源税" },
      { label: "环境保护税", query: "环境保护税" },
    ]},
    { title: "征管与程序", icon: "O", items: [
      { label: "税收征管", query: "征管" },
      { label: "纳税申报", query: "申报" },
      { label: "发票管理", query: "发票" },
      { label: "税务登记", query: "税务登记" },
      { label: "税务检查", query: "检查" },
      { label: "行政处罚", query: "处罚" },
      { label: "行政复议", query: "复议" },
    ]},
    { title: "优惠与减免", icon: "O", items: [
      { label: "税收优惠", query: "优惠" },
      { label: "减免税", query: "减免" },
      { label: "加计扣除", query: "加计扣除" },
      { label: "小微企业", query: "小微" },
      { label: "高新技术", query: "高新" },
      { label: "即征即退", query: "即征即退" },
    ]},
    { title: "社保与人力", icon: "O", items: [
      { label: "社会保险", query: "社会保险" },
      { label: "住房公积金", query: "住房公积金" },
      { label: "工资薪金", query: "工资" },
      { label: "劳动合同", query: "劳动" },
    ]},
    { title: "附加税费", icon: "O", items: [
      { label: "城市维护建设税", query: "城市维护建设税" },
      { label: "教育费附加", query: "教育费附加" },
      { label: "残疾人保障金", query: "残疾" },
      { label: "水利建设基金", query: "水利" },
    ]},
    { title: "会计与核算", icon: "O", items: [
      { label: "会计准则", query: "会计准则" },
      { label: "收入", query: "收入" },
      { label: "成本费用", query: "成本" },
      { label: "折旧", query: "折旧" },
      { label: "资产", query: "资产" },
      { label: "负债", query: "负债" },
    ]},
    { title: "特殊业务", icon: "O", items: [
      { label: "关联交易", query: "关联" },
      { label: "股权转让", query: "股权" },
      { label: "并购重组", query: "并购" },
      { label: "清算注销", query: "清算" },
      { label: "跨境交易", query: "跨境" },
      { label: "电子商务", query: "电子商务" },
    ]},
  ],
  LegalDocument: [
    { title: "按税种", icon: "O", items: [
      { label: "增值税", query: "增值税" },
      { label: "企业所得税", query: "企业所得税" },
      { label: "个人所得税", query: "个人所得税" },
      { label: "印花税", query: "印花税" },
      { label: "土地增值税", query: "土地增值税" },
      { label: "消费税", query: "消费税" },
      { label: "关税", query: "关税" },
      { label: "房产税", query: "房产税" },
    ]},
    { title: "按主题", icon: "O", items: [
      { label: "税收优惠", query: "优惠" },
      { label: "征管程序", query: "征管" },
      { label: "发票管理", query: "发票" },
      { label: "出口退税", query: "出口退税" },
      { label: "社会保险", query: "社保" },
      { label: "反避税", query: "避税" },
      { label: "纳税信用", query: "信用" },
      { label: "电子税务", query: "电子" },
    ]},
    { title: "按发文机关", icon: "O", items: [
      { label: "财政部", query: "财政部" },
      { label: "税务总局", query: "税务总局" },
      { label: "国务院", query: "国务院" },
      { label: "人社部", query: "人社" },
      { label: "海关总署", query: "海关" },
    ]},
  ],
  KnowledgeUnit: [
    { title: "纳税申报", icon: "O", items: [
      { label: "增值税申报", query: "增值税申报" },
      { label: "企业所得税申报", query: "企业所得税申报" },
      { label: "个税申报", query: "个税申报" },
      { label: "汇算清缴", query: "汇算清缴" },
      { label: "预缴申报", query: "预缴" },
    ]},
    { title: "税务实务", icon: "O", items: [
      { label: "税务登记", query: "税务登记" },
      { label: "发票", query: "发票" },
      { label: "纳税调整", query: "纳税调整" },
      { label: "加计扣除", query: "加计扣除" },
      { label: "小微企业", query: "小微" },
      { label: "出口退税", query: "出口退税" },
      { label: "税收筹划", query: "筹划" },
    ]},
    { title: "会计核算", icon: "O", items: [
      { label: "收入确认", query: "收入" },
      { label: "成本核算", query: "成本" },
      { label: "折旧摊销", query: "折旧" },
      { label: "减值准备", query: "减值" },
      { label: "合并报表", query: "合并" },
      { label: "财务报表", query: "报表" },
    ]},
    { title: "行业专题", icon: "O", items: [
      { label: "房地产", query: "房地产" },
      { label: "建筑业", query: "建筑" },
      { label: "金融", query: "金融" },
      { label: "电子商务", query: "电商" },
      { label: "制造业", query: "制造" },
      { label: "服务业", query: "服务" },
    ]},
    { title: "合规与风险", icon: "O", items: [
      { label: "税务风险", query: "风险" },
      { label: "稽查应对", query: "稽查" },
      { label: "反避税", query: "避税" },
      { label: "关联交易", query: "关联" },
      { label: "处罚案例", query: "处罚" },
    ]},
  ],
  Classification: [
    { title: "编码体系", icon: "O", items: [
      { label: "HS 海关编码", query: "HS编码" },
      { label: "行业分类", query: "行业" },
      { label: "国民经济行业", query: "国民经济" },
    ]},
    { title: "按商品类型", icon: "O", items: [
      { label: "电子产品", query: "电子" },
      { label: "机械设备", query: "机械" },
      { label: "化工产品", query: "化工" },
      { label: "纺织品", query: "纺织" },
      { label: "农产品", query: "农产" },
      { label: "金属矿产", query: "金属" },
    ]},
  ],
  TaxClassificationCode: [
    { title: "按品类", icon: "O", items: [
      { label: "货物", query: "货物" },
      { label: "服务", query: "服务" },
      { label: "不动产", query: "不动产" },
      { label: "无形资产", query: "无形资产" },
    ]},
    { title: "货物细分", icon: "O", items: [
      { label: "农产品", query: "农产品" },
      { label: "矿产品", query: "矿产" },
      { label: "加工", query: "加工" },
      { label: "修理修配", query: "修理" },
    ]},
    { title: "服务细分", icon: "O", items: [
      { label: "金融", query: "金融" },
      { label: "建筑", query: "建筑" },
      { label: "运输", query: "运输" },
      { label: "信息技术", query: "信息" },
    ]},
  ],
  TaxRate: [
    { title: "增值税税率", icon: "O", items: [
      { label: "13%税率", query: "13" },
      { label: "9%税率", query: "9" },
      { label: "6%税率", query: "6" },
      { label: "零税率", query: "零税率" },
      { label: "简易征收", query: "简易" },
      { label: "小规模", query: "小规模" },
    ]},
    { title: "所得税税率", icon: "O", items: [
      { label: "企业所得税", query: "企业所得税" },
      { label: "个人所得税", query: "个人所得税" },
      { label: "预提所得税", query: "预提" },
      { label: "协定税率", query: "协定" },
    ]},
    { title: "其他税种", icon: "O", items: [
      { label: "消费税", query: "消费税" },
      { label: "印花税", query: "印花税" },
      { label: "契税", query: "契税" },
      { label: "房产税", query: "房产税" },
      { label: "土地增值税", query: "土地增值税" },
      { label: "资源税", query: "资源税" },
      { label: "城建税", query: "城建" },
    ]},
  ],
};

/* ── Large table guide component ── */
function LargeTableGuide({ type, total, label, onSearch, onBrowse, pageSize }: {
  type: string; total: number; label: string;
  onSearch: (kw: string) => void; onBrowse: () => void; pageSize: number;
}) {
  const categories = LARGE_TABLE_CATEGORIES[type];
  const [counts, setCounts] = useState<Record<string, number>>({});

  // Async fetch counts for each category item
  useEffect(() => {
    if (!categories) return;
    const queries = categories.flatMap((g) => g.items.map((i) => i.query));
    const unique = [...new Set(queries)];
    // Batch: fetch count for each query (limit=1 just to get count header)
    unique.forEach(async (q) => {
      try {
        const res = await listNodes(type, 1, 0, q);
        setCounts((prev) => ({ ...prev, [q]: (res as Record<string, unknown>).total as number || res.count || 0 }));
      } catch { /* skip */ }
    });
  }, [type, categories]);

  return (
    <div style={{ padding: "32px 40px", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 28, textAlign: "center" }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: CN.text, marginBottom: 6 }}>
          {label} 共 {total.toLocaleString()} 条
        </div>
        <div style={{ fontSize: 12, color: CN.textMuted }}>
          按分类浏览，或使用上方搜索框精确查找
        </div>
      </div>

      {/* Category grid */}
      {categories ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, maxWidth: 960, margin: "0 auto" }}>
          {categories.map((group) => (
            <div key={group.title} style={{
              background: CN.bgCard, border: `1px solid ${CN.border}`, borderRadius: 8,
              padding: "16px 18px", transition: "box-shadow 0.15s",
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: CN.text, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                <span>{group.icon}</span> {group.title}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {group.items.map((item) => (
                  <button key={item.query}
                    onClick={() => onSearch(item.query)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      width: "100%", padding: "7px 10px", fontSize: 12,
                      color: CN.text, background: CN.bgElevated, border: `1px solid transparent`,
                      borderRadius: 6, cursor: "pointer", textAlign: "left",
                      transition: "all 0.12s",
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = CN.blue; e.currentTarget.style.background = CN.blueBg; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = "transparent"; e.currentTarget.style.background = CN.bgElevated; }}
                  >
                    <span>{item.label}</span>
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {item.desc && <span style={{ fontSize: 10, color: CN.textMuted }}>{item.desc}</span>}
                      {counts[item.query] !== undefined && (
                        <span style={{ fontSize: 10, color: CN.blue, fontVariantNumeric: "tabular-nums", minWidth: 28, textAlign: "right" }}>
                          {counts[item.query].toLocaleString()}
                        </span>
                      )}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Fallback for tables without curated categories */
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 500, margin: "0 auto" }}>
          {["增值税", "企业所得税", "个人所得税", "发票", "合规", "优惠"].map((kw) => (
            <button key={kw}
              onClick={() => onSearch(kw)}
              style={{
                padding: "8px 18px", fontSize: 12, borderRadius: 20,
                border: `1px solid ${CN.border}`, background: CN.bgElevated,
                color: CN.text, cursor: "pointer",
              }}
            >
              {kw}
            </button>
          ))}
        </div>
      )}

      {/* Browse all link */}
      <div style={{ textAlign: "center", marginTop: 24, fontSize: 11, color: CN.textMuted }}>
        或{" "}
        <button
          onClick={onBrowse}
          style={{ background: "none", border: "none", color: CN.blue, cursor: "pointer", fontSize: 11, textDecoration: "underline" }}
        >
          直接浏览前 {pageSize} 条
        </button>
      </div>
    </div>
  );
}

/* ── Document name cache (documentId → name) ── */
const docNameCache: Record<string, string> = {};

async function resolveDocName(documentId: string): Promise<string> {
  if (!documentId) return "";
  if (docNameCache[documentId]) return docNameCache[documentId];
  try {
    // Try LawOrRegulation first
    const res = await getGraph("LawOrRegulation", documentId);
    if (res.node) {
      const name = String(res.node.title || res.node.name || res.node._label || "");
      // Clean up crawled article titles
      const cleaned = name.replace(/^收藏[！!]\s*/, "").replace(/^转发[！!]\s*/, "").replace(/^重磅[！!]\s*/, "");
      docNameCache[documentId] = cleaned;
      return cleaned;
    }
  } catch { /* skip */ }
  docNameCache[documentId] = `Doc-${documentId.slice(-8)}`;
  return docNameCache[documentId];
}

/* ── Type-specific row mapping ── */
function mapNodeRow(n: Record<string, unknown>, type: string): NodeRow {
  const id = String(n.id || "");
  const raw = n;

  switch (type) {
    case "LegalClause": {
      const clauseNum = n.clauseNumber ? `第${n.clauseNumber}条` : "";
      const docId = String(n.documentId || "");
      return {
        id, raw,
        title: clauseNum || id,
        subtitle: docId,
        content: String(n.content || n.title || ""),
        col1: clauseNum,
        col2: docNameCache[docId] || `[${docId.slice(-8)}]`,
        col3: String(n.content || n.title || "").slice(0, 80),
      };
    }
    case "Region": {
      return {
        id, raw,
        title: String(n.name || n._display_label || ""),
        subtitle: "",
        content: "",
        col1: String(n.name || n._display_label || ""),
        col2: String(n.level || ""),
        col3: "",
      };
    }
    case "FilingForm": {
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: "",
        content: String(n.fullText || ""),
        col1: String(n.name || ""),
        col2: String(n.taxTypeId || ""),
        col3: String(n.frequency || "").replace("monthly", "月报").replace("quarterly", "季报").replace("annual", "年报"),
      };
    }
    case "LegalDocument": {
      return {
        id, raw,
        title: String(n.name || n.title || ""),
        subtitle: String(n.regulationType || n.type || ""),
        content: String(n.fullText || ""),
        col1: String(n.name || n.title || ""),
        col2: String(n.regulationType || n.type || ""),
        col3: String(n.effectiveDate || ""),
      };
    }
    case "ComplianceRule": {
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.ruleType || ""),
        content: String(n.fullText || n.description || ""),
        col1: String(n.name || ""),
        col2: String(n.ruleType || ""),
        col3: String(n.fullText || n.description || "").slice(0, 80),
      };
    }
    case "TaxIncentive": {
      const TYPE_ZH: Record<string, string> = { exemption: "免征", rate_reduction: "减征", refund: "退税", deduction: "扣除", deferral: "递延", credit: "抵免" };
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.incentiveType || ""),
        content: String(n.fullText || ""),
        col1: String(n.name || ""),
        col2: TYPE_ZH[String(n.incentiveType || "")] || String(n.incentiveType || ""),
        col3: String(n.lawReference || ""),
      };
    }
    case "TaxAccountingGap": {
      const GAP_ZH: Record<string, string> = { timing: "时间性差异", permanent: "永久性差异" };
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.gapType || ""),
        content: String(n.fullText || `会计：${n.accountingTreatment || ""}\n税务：${n.taxTreatment || ""}`),
        col1: String(n.name || ""),
        col2: GAP_ZH[String(n.gapType || "")] || String(n.gapType || ""),
        col3: `会计: ${String(n.accountingTreatment || "").slice(0, 30)} / 税务: ${String(n.taxTreatment || "").slice(0, 30)}`,
      };
    }
    case "SocialInsuranceRule": {
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.insuranceType || ""),
        content: String(n.fullText || ""),
        col1: String(n.name || ""),
        col2: String(n.employerRate || ""),
        col3: String(n.employeeRate || ""),
      };
    }
    case "InvoiceRule": {
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.ruleType || ""),
        content: String(n.fullText || n.condition || ""),
        col1: String(n.name || ""),
        col2: String(n.ruleType || ""),
        col3: String(n.condition || "").slice(0, 80),
      };
    }
    case "IndustryBenchmark": {
      return {
        id, raw,
        title: String(n.ratioName || n.name || ""),
        subtitle: String(n.industryCode || ""),
        content: "",
        col1: String(n.ratioName || n.name || ""),
        col2: String(n.industryCode || ""),
        col3: `${n.minValue || ""}~${n.maxValue || ""} ${n.unit || ""}`,
      };
    }
    case "TaxType": {
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.governingLaw || ""),
        content: String(n.fullText || ""),
        col1: String(n.name || ""),
        col2: String(n.rateRange || ""),
        col3: String(n.filingFrequency || "").replace("monthly", "月报").replace("quarterly", "季报").replace("annual", "年报"),
      };
    }
    case "IssuingBody": {
      return {
        id, raw,
        title: String(n.name || n._display_label || ""),
        subtitle: "",
        content: "",
        col1: String(n.name || n._display_label || ""),
        col2: String(n.level || ""),
        col3: "",
      };
    }
    case "KnowledgeUnit": {
      return {
        id, raw,
        title: String(n.title || n.topic || ""),
        subtitle: String(n.type || ""),
        content: String(n.content || n.fullText || ""),
        col1: String(n.title || n.topic || ""),
        col2: String(n.type || ""),
        col3: String(n.source || ""),
      };
    }
    default: {
      const title = String(n.title || n.name || n.topic || n.question || n._display_label || "");
      return {
        id, raw,
        title,
        subtitle: "",
        content: String(n.fullText || n.content || n.description || ""),
        col1: title,
        col2: String(n.category || n.type || ""),
        col3: String(n.description || n.content || "").slice(0, 80),
      };
    }
  }
}

export default function RulesPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [activeType, setActiveType] = useState("ComplianceRule");
  const [nodes, setNodes] = useState<NodeRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const PAGE_SIZE = 50;

  // Load stats for counts
  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  // Load nodes when type or page changes
  const [serverQuery, setServerQuery] = useState("");

  const loadNodes = useCallback(async (type: string, pageNum: number, q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await listNodes(type, PAGE_SIZE, pageNum * PAGE_SIZE, (q && q !== "__BROWSE__") ? q : undefined);
      const mapped = (res.results || []).map((n) => mapNodeRow(n, type));
      setNodes(mapped);
      setTotal(q ? res.count || mapped.length : stats?.nodes_by_type?.[type] || res.count || mapped.length);

      // For clause types, batch-resolve parent document names
      if (type === "LegalClause" || type === "RegulationClause") {
        const docField = type === "LegalClause" ? "documentId" : "regulationId";
        const uniqueDocIds = [...new Set(
          (res.results || []).map((n) => String(n[docField] || "")).filter(Boolean)
        )];
        // Resolve up to 10 unique doc IDs
        const toResolve = uniqueDocIds.filter((id) => !docNameCache[id]).slice(0, 10);
        if (toResolve.length > 0) {
          await Promise.all(toResolve.map((id) => resolveDocName(id)));
          // Re-map with resolved names
          const remapped = (res.results || []).map((n) => mapNodeRow(n, type));
          setNodes(remapped);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "API error");
    }
    setLoading(false);
  }, [stats]);

  // Large tables (>1000 nodes) require explicit search or "browse" action
  const LARGE_TABLE_THRESHOLD = 1000;
  const isLargeTable = (type: string) => (stats?.nodes_by_type?.[type] || 0) > LARGE_TABLE_THRESHOLD;
  const [browseConfirmed, setBrowseConfirmed] = useState(false);

  useEffect(() => {
    // Wait for stats before deciding load strategy
    if (!stats) return;
    // Skip auto-load for large tables unless user confirmed browsing or has a search query
    if (isLargeTable(activeType) && !serverQuery && !browseConfirmed) {
      setNodes([]);
      setTotal(stats?.nodes_by_type?.[activeType] || 0);
      setLoading(false);
      setError(null);
      return;
    }
    loadNodes(activeType, page, (serverQuery && serverQuery !== "__BROWSE__") ? serverQuery : undefined);
  }, [activeType, page, loadNodes, serverQuery, browseConfirmed, stats]);

  // Change type
  const switchType = (type: string) => {
    setActiveType(type);
    setPage(0);
    setDetail(null);
    setSearch("");
    setServerQuery("");
    setBrowseConfirmed(false);
  };

  // Open detail panel with parent doc resolution
  const openDetail = useCallback(async (node: NodeRow) => {
    setDetailLoading(true);
    let parentDocName = "";
    try {
      const graphResult = await getGraph(activeType, node.id);
      // Resolve parent doc name for clause types
      if (activeType === "LegalClause" || activeType === "RegulationClause") {
        const docField = activeType === "LegalClause" ? "documentId" : "regulationId";
        const docId = String(node.raw[docField] || "");
        if (docId) parentDocName = await resolveDocName(docId);
      }
      setDetail({ node, neighbors: graphResult.neighbors || [], parentDocName });
    } catch {
      setDetail({ node, neighbors: [], parentDocName });
    }
    setDetailLoading(false);
  }, [activeType]);

  // Filter: server-side when query submitted, client-side for live typing
  const filtered = (search && !serverQuery)
    ? nodes.filter((n) => {
        const q = search.toLowerCase();
        return n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q) || n.id.toLowerCase().includes(q);
      })
    : nodes;

  const typeCount = (table: string) => stats?.nodes_by_type?.[table] || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 49px)" }}>
      {/* Left: Type Selector */}
      <div style={{
        width: 220, flexShrink: 0, overflowY: "auto",
        background: CN.bgCard, borderRight: `1px solid ${CN.border}`,
      }}>
        <div style={{ padding: "14px 16px", borderBottom: `1px solid ${CN.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: CN.text }}>法规条款浏览器</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>
            {stats ? `${(stats.total_nodes / 1000).toFixed(0)}K 节点 / ${stats.node_tables} 张表` : "..."}
          </div>
        </div>

        {/* Group by layer */}
        {["L1 法规层", "L2 业务层", "L3 合规层", "L4 知识层"].map((layer) => {
          const types = BROWSABLE_TYPES.filter((t) => t.layer === layer);
          const layerLabel = layer;
          return (
            <div key={layer}>
              <div style={{ padding: "10px 16px 4px", fontSize: 9, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px" }}>
                {layerLabel}
              </div>
              {types.map((t) => {
                const count = typeCount(t.table);
                const active = activeType === t.table;
                return (
                  <button key={t.table}
                    onClick={() => switchType(t.table)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      width: "100%", padding: "7px 16px", fontSize: 12,
                      color: active ? CN.blue : CN.text,
                      background: active ? CN.blueBg : "transparent",
                      borderLeft: `2px solid ${active ? CN.blue : "transparent"}`,
                      border: "none", borderBottom: "none",
                      cursor: "pointer", textAlign: "left",
                    }}
                  >
                    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: NODE_COLORS[t.table] || "#94A3B8", flexShrink: 0 }} />
                      {t.label}
                    </span>
                    <span style={{ fontSize: 10, color: CN.textMuted, fontVariantNumeric: "tabular-nums" }}>
                      {count > 999 ? `${(count / 1000).toFixed(1)}K` : count}
                    </span>
                  </button>
                );
              })}
            </div>
          );
        })}

        {/* Link to KG Explorer */}
        <div style={{ padding: 12, borderTop: `1px solid ${CN.border}`, marginTop: 8 }}>
          <Link href="/expert/kg" style={{
            display: "block", padding: "8px 12px", textAlign: "center",
            color: CN.blue, textDecoration: "none", fontSize: 11, fontWeight: 600,
            border: `1px solid ${CN.border}`, borderRadius: 4, background: CN.blueBg,
          }}>
            在知识图谱中探索 &rarr;
          </Link>
        </div>
      </div>

      {/* Center: Node List */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {/* Toolbar */}
        <div style={{
          padding: "10px 24px", borderBottom: `1px solid ${CN.border}`,
          display: "flex", alignItems: "center", gap: 12, flexShrink: 0, background: CN.bg,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: CN.text }}>
            {BROWSABLE_TYPES.find((t) => t.table === activeType)?.label || activeType}
          </div>
          <span style={cnBadge(CN.blue, CN.blueBg)}>{total.toLocaleString()}</span>
          <input
            type="text" placeholder="搜索当前页..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && search.trim()) {
                setServerQuery(search.trim());
                setPage(0);
              }
            }}
            style={{ ...cnInput, flex: 1, maxWidth: 320 }}
          />
          {search.trim() && (
            <button
              onClick={() => { setServerQuery(search.trim()); setPage(0); }}
              style={{ ...cnBtnPrimary, padding: "5px 12px", fontSize: 12 }}
            >
              搜索全库
            </button>
          )}
          {serverQuery && (
            <button
              onClick={() => { setServerQuery(""); setSearch(""); setPage(0); }}
              style={{ ...cnBtn, padding: "5px 12px", fontSize: 12 }}
            >
              清除
            </button>
          )}
          {/* Pagination */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: CN.textMuted }}>
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              style={{ ...cnBtn, padding: "5px 10px", opacity: page === 0 ? 0.3 : 1 }}>
              &lt;
            </button>
            <span>{page + 1} / {totalPages || 1}</span>
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
              style={{ ...cnBtn, padding: "5px 10px", opacity: page >= totalPages - 1 ? 0.3 : 1 }}>
              &gt;
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: "10px 24px", background: CN.redBg, color: CN.red, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Node table */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {/* Large-table guide: hierarchical category navigation */}
          {!loading && isLargeTable(activeType) && !serverQuery && !browseConfirmed ? (
            <LargeTableGuide
              type={activeType}
              total={total}
              label={BROWSABLE_TYPES.find((t) => t.table === activeType)?.label || activeType}
              onSearch={(kw) => { setSearch(kw); setServerQuery(kw); setPage(0); }}
              onBrowse={() => { setBrowseConfirmed(true); setPage(0); }}
              pageSize={PAGE_SIZE}
            />
          ) : loading ? (
            <div style={{ padding: 40, textAlign: "center", color: CN.textMuted }}>加载中...</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: CN.textMuted }}>
              {search ? `未找到匹配 "${search}" 的条目` : "暂无数据"}
            </div>
          ) : (
            (() => {
              const cols = TYPE_COLUMNS[activeType] || DEFAULT_COLUMNS;
              const thStyle: React.CSSProperties = { padding: "8px 14px", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" };
              return (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${CN.border}`, position: "sticky", top: 0, background: CN.bgElevated, zIndex: 1 }}>
                      <th style={{ ...thStyle, width: 120 }}>{cols.c1}</th>
                      <th style={thStyle}>{cols.c2}</th>
                      <th style={thStyle}>{cols.c3}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((n) => {
                      const isSelected = detail?.node.id === n.id;
                      return (
                        <tr key={n.id}
                          style={{ cursor: "pointer", background: isSelected ? CN.blueBg : "transparent" }}
                          onClick={() => openDetail(n)}
                        >
                          <td style={{ padding: "8px 14px", color: CN.text, fontWeight: 600, borderBottom: `1px solid ${CN.bgElevated}`, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.col1 || "--"}
                          </td>
                          <td style={{ padding: "8px 14px", color: CN.textSecondary, fontSize: 12, borderBottom: `1px solid ${CN.bgElevated}`, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.col2 || "--"}
                          </td>
                          <td style={{ padding: "8px 14px", color: CN.textSecondary, fontSize: 12, borderBottom: `1px solid ${CN.bgElevated}`, maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.col3 || "--"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              );
            })()
          )}
        </div>
      </div>

      {/* Right: Detail Panel */}
      {detail && (
        <div style={{
          width: 400, flexShrink: 0, overflowY: "auto",
          background: CN.bgCard, borderLeft: `1px solid ${CN.border}`, padding: 20,
        }}>
          <div style={{ display: "flex", alignItems: "start", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: CN.text, margin: 0, lineHeight: 1.5, maxWidth: 320 }}>
              {detail.node.title}
            </h3>
            <button onClick={() => setDetail(null)}
              style={{ background: "none", border: "none", color: CN.textMuted, cursor: "pointer", fontSize: 18, flexShrink: 0 }}>
              x
            </button>
          </div>

          {/* Type badge + parent doc */}
          <div style={{ marginBottom: 16, display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={cnBadge(NODE_COLORS[activeType] || CN.blue, CN.blueBg)}>
              {BROWSABLE_TYPES.find((t) => t.table === activeType)?.label || activeType}
            </span>
            {detail.parentDocName && (
              <div style={{ fontSize: 13, color: CN.blue, fontWeight: 600, lineHeight: 1.5 }}>
                {detail.parentDocName}
              </div>
            )}
          </div>

          {detailLoading && <div style={{ color: CN.textMuted, fontSize: 12, marginBottom: 12 }}>加载关联...</div>}

          {/* Full Content */}
          {detail.node.content && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>全文内容</span>
                {detail.node.content.length >= 195 && !detail.node.content.endsWith("。") && (
                  <span style={cnBadge(CN.amber, CN.amberBg)}>可能截断</span>
                )}
              </div>
              <div style={{
                fontSize: 13, color: CN.text, lineHeight: 1.9,
                padding: "14px 16px", background: CN.bg, border: `1px solid ${CN.border}`,
                borderRadius: 4, whiteSpace: "pre-wrap",
                maxHeight: "50vh", overflowY: "auto",
              }}>
                {detail.node.content.replace(/\s*\|\s*/g, "\n\n")}
              </div>
            </div>
          )}

          {/* All metadata fields */}
          {(() => {
            const skipFields = new Set(["_id", "_label", "_display_label", "id", "title", "name", "fullText", "content", "description", "text", "topic", "question", "node_text"]);
            const meta = Object.entries(detail.node.raw).filter(
              ([k, v]) => !skipFields.has(k) && v !== null && v !== undefined && String(v).length > 0 && String(v) !== "undefined" && String(v) !== ""
            );
            if (meta.length === 0) return null;
            return (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>属性</div>
                <div style={{ fontSize: 12, lineHeight: 1.7 }}>
                  {meta.map(([k, v]) => (
                    <div key={k} style={{ display: "flex", gap: 8, marginBottom: 4, paddingBottom: 4, borderBottom: `1px solid ${CN.bgElevated}` }}>
                      <span style={{ color: CN.textMuted, fontWeight: 600, minWidth: 100, flexShrink: 0 }}>{k}</span>
                      {String(v).startsWith("http") ? (
                        <a href={String(v)} target="_blank" rel="noopener noreferrer"
                          style={{ color: CN.blue, textDecoration: "none", wordBreak: "break-all" }}>
                          {String(v).length > 50 ? `${String(v).slice(0, 50)}...` : String(v)}
                        </a>
                      ) : (
                        <span style={{ color: CN.text, wordBreak: "break-all" }}>{String(v).slice(0, 300)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Node ID */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, letterSpacing: "1px", marginBottom: 4 }}>节点 ID</div>
            <div style={{ fontSize: 11, color: CN.textMuted, fontFamily: "monospace", wordBreak: "break-all" }}>
              {detail.node.id}
            </div>
          </div>

          {/* Neighbors */}
          {detail.neighbors.length > 0 && (
            <div style={{ borderTop: `1px solid ${CN.border}`, paddingTop: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 10 }}>
                关联节点 ({detail.neighbors.length})
              </div>
              {detail.neighbors.map((nb, i) => (
                <div key={i} style={{
                  padding: "8px 12px", marginBottom: 4,
                  background: CN.bg, border: `1px solid ${CN.border}`, borderRadius: 4,
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: CN.text, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {nb.direction === "incoming" ? "\u2190 " : "\u2192 "}{nb.target_label}
                    </span>
                    <span style={cnBadge(EDGE_COLORS[nb.edge_type] || CN.purple, CN.purpleBg)}>
                      {EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: CN.textMuted }}>{nb.target_type}</div>
                </div>
              ))}
            </div>
          )}

          {/* Navigate to KG */}
          <Link href={`/expert/kg`}
            style={{
              display: "block", width: "100%", marginTop: 16, padding: "8px 0",
              background: CN.blueBg, border: `1px solid ${CN.border}`,
              color: CN.blue, fontSize: 12, fontWeight: 600, cursor: "pointer",
              borderRadius: 6, textAlign: "center", textDecoration: "none",
            }}
          >
            在知识图谱中查看此节点 &rarr;
          </Link>
        </div>
      )}
    </div>
  );
}
