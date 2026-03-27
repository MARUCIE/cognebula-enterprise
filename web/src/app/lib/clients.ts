/* Shared client entity data -- single source of truth.
   Used by: /clients (list), /clients/[id] (detail) */

export interface Client {
  id: string;
  name: string;
  initial: string;
  initialColor: string;
  industry: string;
  tier: "enterprise" | "professional" | "starter";
  agent: string;
  agentDept: "tax" | "bookkeeping" | "compliance" | "admin";
  lastDate: string;
  status: "done" | "review" | "progress";
  statusLabel: string;
  // Detail fields (for /clients/[id])
  registrationNo: string;
  legalRep: string;
  address: string;
  phone: string;
  taxId: string;
  annualRevenue: string;
  employeeCount: number;
  serviceStartDate: string;
  monthlyFee: string;
  complianceScore: number;
  aiTasksCompleted: number;
  aiTasksPending: number;
  recentActivity: Array<{
    date: string;
    action: string;
    agent: string;
    status: "done" | "progress" | "error";
  }>;
}

export const CLIENTS: Client[] = [
  {
    id: "zhongtie-jianshe",
    name: "中铁建设集团有限公司",
    initial: "中",
    initialColor: "var(--color-dept-tax)",
    industry: "基础建设 / 大型国企",
    tier: "enterprise",
    agent: "灵阙智税-01",
    agentDept: "tax",
    lastDate: "2024-11-15",
    status: "done",
    statusLabel: "已完成",
    registrationNo: "91110000100018235P",
    legalRep: "戴和根",
    address: "北京市海淀区复兴路40号",
    phone: "010-5198-8888",
    taxId: "91110000100018235P",
    annualRevenue: "¥45,280,000",
    employeeCount: 12400,
    serviceStartDate: "2023-03-15",
    monthlyFee: "¥8,999",
    complianceScore: 98,
    aiTasksCompleted: 1284,
    aiTasksPending: 3,
    recentActivity: [
      { date: "2024-11-15", action: "Q3 增值税申报完成", agent: "林税安", status: "done" },
      { date: "2024-11-14", action: "月度凭证批量录入", agent: "王记账", status: "done" },
      { date: "2024-11-13", action: "合规风险扫描", agent: "赵合规", status: "done" },
      { date: "2024-11-12", action: "现金流异常检测", agent: "张审核", status: "progress" },
    ],
  },
  {
    id: "alibaba-wangluo",
    name: "阿里巴巴（中国）网络技术",
    initial: "阿",
    initialColor: "var(--color-dept-bookkeeping)",
    industry: "互联网科技 / 一般纳税人",
    tier: "enterprise",
    agent: "灵阙审计-04",
    agentDept: "bookkeeping",
    lastDate: "2024-11-12",
    status: "review",
    statusLabel: "待审核",
    registrationNo: "91330100799655058B",
    legalRep: "蒋芳",
    address: "浙江省杭州市余杭区文一西路969号",
    phone: "0571-8502-2088",
    taxId: "91330100799655058B",
    annualRevenue: "¥128,450,200",
    employeeCount: 28000,
    serviceStartDate: "2023-01-08",
    monthlyFee: "¥12,999",
    complianceScore: 100,
    aiTasksCompleted: 3842,
    aiTasksPending: 12,
    recentActivity: [
      { date: "2024-11-12", action: "年度审计底稿准备", agent: "张审核", status: "progress" },
      { date: "2024-11-11", action: "损益表自动生成", agent: "王记账", status: "done" },
      { date: "2024-11-10", action: "跨境税务合规检查", agent: "赵合规", status: "done" },
      { date: "2024-11-09", action: "进项税额抵扣核验", agent: "林税安", status: "done" },
    ],
  },
  {
    id: "tengxun-keji",
    name: "腾讯科技（深圳）有限公司",
    initial: "腾",
    initialColor: "var(--color-dept-client)",
    industry: "互联网科技 / 上市企业",
    tier: "enterprise",
    agent: "灵阙智税-02",
    agentDept: "tax",
    lastDate: "2024-11-10",
    status: "progress",
    statusLabel: "进行中",
    registrationNo: "9144030071526726XG",
    legalRep: "马化腾",
    address: "深圳市南山区科技中一路腾讯大厦",
    phone: "0755-8601-3388",
    taxId: "9144030071526726XG",
    annualRevenue: "¥92,000,540",
    employeeCount: 56000,
    serviceStartDate: "2023-06-20",
    monthlyFee: "¥12,999",
    complianceScore: 97,
    aiTasksCompleted: 2156,
    aiTasksPending: 8,
    recentActivity: [
      { date: "2024-11-10", action: "现金流量表编制中", agent: "王记账", status: "progress" },
      { date: "2024-11-09", action: "研发费用加计扣除", agent: "陈税策", status: "done" },
      { date: "2024-11-08", action: "月度纳税申报", agent: "林税安", status: "done" },
      { date: "2024-11-07", action: "合规规则库更新", agent: "赵合规", status: "done" },
    ],
  },
  {
    id: "meituan-dianping",
    name: "美团点评（北京）科技有限公司",
    initial: "美",
    initialColor: "var(--color-dept-compliance)",
    industry: "生活服务 / 上市企业",
    tier: "enterprise",
    agent: "灵阙合规-01",
    agentDept: "compliance",
    lastDate: "2024-10-31",
    status: "done",
    statusLabel: "已完成",
    registrationNo: "91110108MA01KRHX3K",
    legalRep: "王兴",
    address: "北京市朝阳区望京东路6号",
    phone: "010-5979-1000",
    taxId: "91110108MA01KRHX3K",
    annualRevenue: "¥34,120,000",
    employeeCount: 18000,
    serviceStartDate: "2023-09-01",
    monthlyFee: "¥8,999",
    complianceScore: 95,
    aiTasksCompleted: 986,
    aiTasksPending: 0,
    recentActivity: [
      { date: "2024-10-31", action: "Q3 合规审查完成", agent: "赵合规", status: "done" },
      { date: "2024-10-30", action: "年度财务摘要生成", agent: "王记账", status: "done" },
      { date: "2024-10-28", action: "附加税计算复核", agent: "林税安", status: "done" },
      { date: "2024-10-25", action: "审计异常检测", agent: "张审核", status: "done" },
    ],
  },
  {
    id: "shenzhen-jizhi",
    name: "深圳极智科技有限公司",
    initial: "深",
    initialColor: "var(--color-dept-tax)",
    industry: "高新信息技术 / 一般纳税人",
    tier: "professional",
    agent: "灵阙智税-01",
    agentDept: "tax",
    lastDate: "2024-10-28",
    status: "done",
    statusLabel: "已完成",
    registrationNo: "91440300MA5G1K2Q3A",
    legalRep: "李明辉",
    address: "深圳市南山区高新技术产业园",
    phone: "0755-2345-6789",
    taxId: "91440300MA5G1K2Q3A",
    annualRevenue: "¥12,800,000",
    employeeCount: 320,
    serviceStartDate: "2024-01-15",
    monthlyFee: "¥2,999",
    complianceScore: 92,
    aiTasksCompleted: 456,
    aiTasksPending: 2,
    recentActivity: [
      { date: "2024-10-28", action: "增值税申报提交", agent: "林税安", status: "done" },
      { date: "2024-10-25", action: "银行对账完成", agent: "王记账", status: "done" },
      { date: "2024-10-20", action: "高新认定材料准备", agent: "陈税策", status: "done" },
      { date: "2024-10-18", action: "凭证录入批量处理", agent: "王记账", status: "done" },
    ],
  },
  {
    id: "huaxia-maoyi",
    name: "华夏贸易进出口有限公司",
    initial: "华",
    initialColor: "var(--color-secondary-dim)",
    industry: "跨境电商 / 外资企业",
    tier: "professional",
    agent: "灵阙审计-04",
    agentDept: "bookkeeping",
    lastDate: "2024-10-25",
    status: "review",
    statusLabel: "待审核",
    registrationNo: "91440300MA5H9N6K1B",
    legalRep: "张伟",
    address: "广州市天河区珠江新城",
    phone: "020-3456-7890",
    taxId: "91440300MA5H9N6K1B",
    annualRevenue: "¥8,600,000",
    employeeCount: 85,
    serviceStartDate: "2024-03-10",
    monthlyFee: "¥2,999",
    complianceScore: 88,
    aiTasksCompleted: 234,
    aiTasksPending: 5,
    recentActivity: [
      { date: "2024-10-25", action: "跨境转让定价文档审查", agent: "赵合规", status: "progress" },
      { date: "2024-10-22", action: "进口关税计算", agent: "林税安", status: "done" },
      { date: "2024-10-20", action: "外币账务处理", agent: "王记账", status: "done" },
      { date: "2024-10-18", action: "出口退税申报", agent: "陈税策", status: "done" },
    ],
  },
  {
    id: "guangying-chuanmei",
    name: "光影传媒艺术工作室",
    initial: "光",
    initialColor: "var(--color-tertiary)",
    industry: "文化创意 / 小规模纳税人",
    tier: "starter",
    agent: "灵阙智税-02",
    agentDept: "tax",
    lastDate: "2024-10-20",
    status: "progress",
    statusLabel: "进行中",
    registrationNo: "91310115MA1K3A9X2N",
    legalRep: "刘艺",
    address: "上海市静安区愚园路",
    phone: "021-5678-1234",
    taxId: "91310115MA1K3A9X2N",
    annualRevenue: "¥1,200,000",
    employeeCount: 12,
    serviceStartDate: "2024-06-01",
    monthlyFee: "¥999",
    complianceScore: 100,
    aiTasksCompleted: 89,
    aiTasksPending: 1,
    recentActivity: [
      { date: "2024-10-20", action: "季度纳税申报处理中", agent: "林税安", status: "progress" },
      { date: "2024-10-15", action: "发票开具与管理", agent: "王记账", status: "done" },
      { date: "2024-10-10", action: "个人所得税代扣代缴", agent: "林税安", status: "done" },
      { date: "2024-10-05", action: "月度记账完成", agent: "王记账", status: "done" },
    ],
  },
  {
    id: "taihe-yanglao",
    name: "泰和养老服务集团",
    initial: "泰",
    initialColor: "var(--color-dept-client)",
    industry: "医疗健康 / 连锁经营",
    tier: "professional",
    agent: "灵阙智税-01",
    agentDept: "tax",
    lastDate: "2024-10-15",
    status: "done",
    statusLabel: "已完成",
    registrationNo: "91500000MA5U1G8H4D",
    legalRep: "陈建华",
    address: "重庆市渝北区新牌坊",
    phone: "023-6789-0123",
    taxId: "91500000MA5U1G8H4D",
    annualRevenue: "¥22,500,000",
    employeeCount: 1200,
    serviceStartDate: "2023-11-20",
    monthlyFee: "¥5,999",
    complianceScore: 96,
    aiTasksCompleted: 678,
    aiTasksPending: 0,
    recentActivity: [
      { date: "2024-10-15", action: "所得税优化方案确认", agent: "陈税策", status: "done" },
      { date: "2024-10-12", action: "社保公积金核算", agent: "王记账", status: "done" },
      { date: "2024-10-10", action: "连锁分店合并报表", agent: "王记账", status: "done" },
      { date: "2024-10-08", action: "医疗行业合规检查", agent: "赵合规", status: "done" },
    ],
  },
];

export const CLIENT_IDS = CLIENTS.map((c) => c.id);

export function getClientById(id: string): Client | undefined {
  return CLIENTS.find((c) => c.id === id);
}
