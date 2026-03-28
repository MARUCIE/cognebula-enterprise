/* Shared report entity data -- single source of truth.
   Used by: /reports (list), /reports/[id] (detail) */

export interface ReportHighlight {
  label: string;
  currentValue: string;
  prevValue: string;
  changePercent: number;
  aiNote: string;
}

export interface Report {
  id: string;
  company: string;
  reportType: string;
  reportTypeEn: string;
  date: string;
  status: "ai" | "reviewed" | "flagged";
  statusLabel: string;
  amount: string;
  confidence: number;
  reviewItems: number;
  period: string;
  highlights: ReportHighlight[];
  aiSummary: string;
}

export const REPORTS: Report[] = [
  {
    id: "zhongtie-asset-q3",
    company: "中铁建设集团有限公司",
    reportType: "资产负债表",
    reportTypeEn: "Asset Balance Sheet",
    date: "2024-11-24 14:20",
    status: "ai",
    statusLabel: "AI 生成",
    amount: "45,280,000.00",
    confidence: 97.2,
    reviewItems: 2,
    period: "2024年Q3",
    highlights: [
      { label: "资产合计", currentValue: "¥45,280,000", prevValue: "¥40,420,000", changePercent: 12, aiNote: "资产稳步增长，主要来自在建工程转固" },
      { label: "应收账款", currentValue: "¥18,200,000", prevValue: "¥13,180,000", changePercent: 38, aiNote: "应收账款增长38%，超出行业均值。主因：9月大额订单延迟回款，已记录" },
      { label: "流动负债", currentValue: "¥12,500,000", prevValue: "¥11,800,000", changePercent: 6, aiNote: "负债小幅增长，处于合理范围" },
    ],
    aiSummary: "本期资产负债表整体健康，资产结构合理。需关注应收账款增速超出行业均值，建议加强回款管理。流动比率 2.1，偿债能力良好。",
  },
  {
    id: "alibaba-pnl-q3",
    company: "阿里巴巴（中国）网络技术",
    reportType: "损益表",
    reportTypeEn: "Profit & Loss Statement",
    date: "2024-11-24 10:15",
    status: "reviewed",
    statusLabel: "已人工复核",
    amount: "128,450,200.00",
    confidence: 99.8,
    reviewItems: 0,
    period: "2024年Q3",
    highlights: [
      { label: "营业收入", currentValue: "¥128,450,200", prevValue: "¥115,200,000", changePercent: 11.5, aiNote: "收入同比增长11.5%，符合市场预期" },
      { label: "研发费用", currentValue: "¥28,500,000", prevValue: "¥18,000,000", changePercent: 58, aiNote: "研发费用增长58%，已确认可加计扣除。建议留存完整研发台账备查" },
      { label: "净利润", currentValue: "¥32,100,000", prevValue: "¥29,800,000", changePercent: 7.7, aiNote: "净利润率 25%，处于行业上游水平" },
    ],
    aiSummary: "本期损益表表现优秀。收入和利润均保持增长态势。研发投入大幅增加，已自动匹配加计扣除政策。无异常发现。",
  },
  {
    id: "tengxun-cashflow-q3",
    company: "腾讯科技（深圳）有限公司",
    reportType: "现金流量表",
    reportTypeEn: "Cash Flow Statement",
    date: "2024-11-23 16:45",
    status: "flagged",
    statusLabel: "需关注",
    amount: "92,000,540.00",
    confidence: 89.3,
    reviewItems: 3,
    period: "2024年Q3",
    highlights: [
      { label: "经营活动现金流", currentValue: "¥45,200,000", prevValue: "¥52,000,000", changePercent: -13, aiNote: "经营现金流下降13%，需关注回款周期延长趋势" },
      { label: "投资活动现金流", currentValue: "-¥28,000,000", prevValue: "-¥15,000,000", changePercent: -87, aiNote: "投资支出大幅增加，主要用于股权投资。建议核实投资合同" },
      { label: "筹资活动现金流", currentValue: "¥12,800,000", prevValue: "¥8,500,000", changePercent: 51, aiNote: "新增银行贷款 1,200 万，利率 4.35%，处于市场合理区间" },
    ],
    aiSummary: "现金流量表存在多处需关注项。经营现金流下降与应收账款增长相关，投资支出超出预算。建议重点核查投资活动明细及资金来源。",
  },
  {
    id: "meituan-annual-summary",
    company: "美团点评（北京）科技有限公司",
    reportType: "年度财务摘要",
    reportTypeEn: "Annual Summary",
    date: "2024-11-23 09:00",
    status: "ai",
    statusLabel: "AI 生成",
    amount: "34,120,000.00",
    confidence: 96.5,
    reviewItems: 1,
    period: "2024年度",
    highlights: [
      { label: "全年营收", currentValue: "¥34,120,000", prevValue: "¥30,500,000", changePercent: 11.9, aiNote: "营收同比增长稳健" },
      { label: "税费支出", currentValue: "¥4,280,000", prevValue: "¥3,960,000", changePercent: 8.1, aiNote: "税费增速低于营收增速，税务筹划有效" },
    ],
    aiSummary: "年度财务摘要显示公司经营状况良好，营收和利润均保持两位数增长。税务筹划效果显著，实际税率同比下降0.8个百分点。",
  },
  {
    id: "huawei-monthly-tax",
    company: "华为技术有限公司",
    reportType: "月度税务报告",
    reportTypeEn: "Monthly Tax Report",
    date: "2024-11-22 17:30",
    status: "reviewed",
    statusLabel: "已人工复核",
    amount: "215,800,000.00",
    confidence: 99.5,
    reviewItems: 0,
    period: "2024年10月",
    highlights: [
      { label: "增值税应纳税额", currentValue: "¥8,520,000", prevValue: "¥7,900,000", changePercent: 7.8, aiNote: "增值税与营收同步增长，税负率稳定在3.95%" },
      { label: "进项税额抵扣", currentValue: "¥6,200,000", prevValue: "¥5,800,000", changePercent: 6.9, aiNote: "抵扣充分，无异常" },
    ],
    aiSummary: "10月税务申报数据正常，所有税种已按时完成申报。进项抵扣充分，税负率处于行业合理区间。",
  },
  {
    id: "jingdong-quarterly-audit",
    company: "京东世纪贸易有限公司",
    reportType: "季度审计报告",
    reportTypeEn: "Quarterly Audit Report",
    date: "2024-11-22 11:00",
    status: "flagged",
    statusLabel: "需关注",
    amount: "67,340,800.00",
    confidence: 91.2,
    reviewItems: 4,
    period: "2024年Q3",
    highlights: [
      { label: "存货周转天数", currentValue: "45天", prevValue: "32天", changePercent: 41, aiNote: "存货周转明显放缓，可能存在滞销风险" },
      { label: "应付账款", currentValue: "¥22,400,000", prevValue: "¥15,600,000", changePercent: 44, aiNote: "应付账款增速超过营收增速，资金链压力增大" },
    ],
    aiSummary: "季度审计发现多项风险点。存货周转放缓和应付账款激增需要重点关注，建议尽快安排与客户沟通确认库存处理方案。",
  },
  {
    id: "byd-annual-report",
    company: "比亚迪股份有限公司",
    reportType: "年度财务报告",
    reportTypeEn: "Annual Financial Report",
    date: "2024-11-21 15:45",
    status: "ai",
    statusLabel: "AI 生成",
    amount: "189,560,000.00",
    confidence: 95.8,
    reviewItems: 2,
    period: "2024年度",
    highlights: [
      { label: "营业总收入", currentValue: "¥189,560,000", prevValue: "¥156,200,000", changePercent: 21.4, aiNote: "新能源补贴退坡后仍保持高增长" },
      { label: "固定资产", currentValue: "¥85,000,000", prevValue: "¥62,000,000", changePercent: 37, aiNote: "产能扩张导致固定资产大幅增加，折旧计提需关注" },
    ],
    aiSummary: "年度报告显示比亚迪营收强劲增长21.4%。固定资产扩张带来的折旧费用将在未来几年逐步体现，需关注对利润的影响。",
  },
];

export const REPORT_IDS = REPORTS.map((r) => r.id);

export function getReportById(id: string): Report | undefined {
  return REPORTS.find((r) => r.id === id);
}
