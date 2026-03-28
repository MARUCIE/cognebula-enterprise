/* 41-Task Accounting Workflow Model
   Source: Competitor workbench HTML (16,709 lines, 2025-05)
   Architecture: NEXT_GEN_WORKBENCH_DESIGN.md Section 1-4 */

export type TimeWindow = "W1" | "W2" | "W3" | "W4";
export type TaskStatus = "completed" | "processing" | "ready" | "pending" | "blocked";
export type AgentTier = "starter" | "professional" | "enterprise";

export interface Agent {
  id: string;
  name: string;
  role: string;
  tier: AgentTier;
  trustScore: number;
  totalTasks: number;
  errors: number;
  tenureMonths: number;
}

export interface TaskDef {
  id: number;
  name: string;
  window: TimeWindow;
  enterpriseCount: number;
  agentId: string;
  primarySkill: string;
  hitl: boolean;
  hitlType?: string;
}

export interface TaskInstance extends TaskDef {
  status: TaskStatus;
  progress: number; // 0-100
  completedEnterprises: number;
  blockedEnterprises: number;
}

export const AGENTS: Agent[] = [
  { id: "xiaozhi", name: "小智", role: "采集专员", tier: "starter", trustScore: 98.2, totalTasks: 3421, errors: 5, tenureMonths: 8 },
  { id: "xiaosuan", name: "小算", role: "记账专员", tier: "starter", trustScore: 99.1, totalTasks: 4156, errors: 3, tenureMonths: 8 },
  { id: "xiaoshui", name: "小税", role: "申报专员", tier: "starter", trustScore: 99.7, totalTasks: 2847, errors: 0, tenureMonths: 8 },
  { id: "xiaojian", name: "小检", role: "质检专员", tier: "professional", trustScore: 99.4, totalTasks: 2998, errors: 2, tenureMonths: 6 },
  { id: "zongjian", name: "总监", role: "主管", tier: "professional", trustScore: 100, totalTasks: 1203, errors: 0, tenureMonths: 8 },
  { id: "xiaoan", name: "小安", role: "风控专员", tier: "enterprise", trustScore: 99.8, totalTasks: 1567, errors: 1, tenureMonths: 4 },
  { id: "xiaoke", name: "小客", role: "客服专员", tier: "enterprise", trustScore: 97.5, totalTasks: 1089, errors: 8, tenureMonths: 3 },
];

export const AGENT_MAP = Object.fromEntries(AGENTS.map((a) => [a.id, a]));

export const TIME_WINDOWS: Record<TimeWindow, { label: string; days: string; color: string; bgColor: string; priority: string }> = {
  W1: { label: "采集期", days: "1-5号", color: "#003A70", bgColor: "#E8F0FE", priority: "HIGH" },
  W2: { label: "征期", days: "6-15号", color: "#C4281C", bgColor: "#FDECEB", priority: "CRITICAL" },
  W3: { label: "质检期", days: "16-24号", color: "#1B7F4B", bgColor: "#E6F4EC", priority: "NORMAL" },
  W4: { label: "准备期", days: "25-31号", color: "#5A5A72", bgColor: "#F4F4F2", priority: "NORMAL" },
};

// 41 atomic tasks with current month mock status
export const TASK_INSTANCES: TaskInstance[] = [
  // W1 采集期 (1-5号, 11 tasks) — all completed
  { id: 1, name: "上月银行流水采集", window: "W1", enterpriseCount: 999, agentId: "xiaozhi", primarySkill: "bank-statement-collector", hitl: false, status: "completed", progress: 100, completedEnterprises: 999, blockedEnterprises: 0 },
  { id: 2, name: "上月工资表采集", window: "W1", enterpriseCount: 856, agentId: "xiaozhi", primarySkill: "payroll-collector", hitl: false, status: "completed", progress: 100, completedEnterprises: 856, blockedEnterprises: 0 },
  { id: 3, name: "上月报销单采集", window: "W1", enterpriseCount: 734, agentId: "xiaozhi", primarySkill: "expense-collector", hitl: false, status: "completed", progress: 100, completedEnterprises: 734, blockedEnterprises: 0 },
  { id: 4, name: "上月票据记账", window: "W1", enterpriseCount: 999, agentId: "xiaosuan", primarySkill: "invoice-to-voucher", hitl: false, status: "completed", progress: 100, completedEnterprises: 999, blockedEnterprises: 0 },
  { id: 5, name: "票据记账质检", window: "W1", enterpriseCount: 999, agentId: "xiaojian", primarySkill: "voucher-quality-check", hitl: false, status: "completed", progress: 100, completedEnterprises: 999, blockedEnterprises: 0 },
  { id: 6, name: "票据记账调整", window: "W1", enterpriseCount: 234, agentId: "xiaosuan", primarySkill: "voucher-adjustment", hitl: false, status: "completed", progress: 100, completedEnterprises: 234, blockedEnterprises: 0 },
  { id: 7, name: "无税金账结账", window: "W1", enterpriseCount: 567, agentId: "xiaosuan", primarySkill: "period-close-notax", hitl: false, status: "completed", progress: 100, completedEnterprises: 567, blockedEnterprises: 0 },
  { id: 8, name: "发票完整采集", window: "W1", enterpriseCount: 999, agentId: "xiaozhi", primarySkill: "invoice-collector", hitl: false, status: "completed", progress: 100, completedEnterprises: 999, blockedEnterprises: 0 },
  { id: 9, name: "税项清册", window: "W1", enterpriseCount: 999, agentId: "xiaoshui", primarySkill: "tax-schedule-generator", hitl: false, status: "completed", progress: 100, completedEnterprises: 999, blockedEnterprises: 0 },
  { id: 10, name: "税盘抄报", window: "W1", enterpriseCount: 456, agentId: "xiaoshui", primarySkill: "tax-disk-report", hitl: false, status: "completed", progress: 100, completedEnterprises: 456, blockedEnterprises: 0 },
  { id: 11, name: "进项勾选抵扣", window: "W1", enterpriseCount: 234, agentId: "xiaoshui", primarySkill: "input-vat-matching", hitl: false, status: "completed", progress: 100, completedEnterprises: 234, blockedEnterprises: 0 },

  // W2 征期 (6-15号, 14 tasks) — mixed status
  { id: 12, name: "工资表补采集", window: "W2", enterpriseCount: 143, agentId: "xiaozhi", primarySkill: "payroll-followup", hitl: false, status: "completed", progress: 100, completedEnterprises: 143, blockedEnterprises: 0 },
  { id: 13, name: "税金记账", window: "W2", enterpriseCount: 789, agentId: "xiaosuan", primarySkill: "tax-voucher-generator", hitl: false, status: "completed", progress: 100, completedEnterprises: 789, blockedEnterprises: 0 },
  { id: 14, name: "税金账结账", window: "W2", enterpriseCount: 432, agentId: "xiaosuan", primarySkill: "period-close-tax", hitl: false, status: "completed", progress: 100, completedEnterprises: 432, blockedEnterprises: 0 },
  { id: 15, name: "个税申报", window: "W2", enterpriseCount: 856, agentId: "xiaoshui", primarySkill: "pit-filing", hitl: false, status: "processing", progress: 72, completedEnterprises: 616, blockedEnterprises: 23 },
  { id: 16, name: "经营所得申报", window: "W2", enterpriseCount: 67, agentId: "xiaoshui", primarySkill: "business-income-filing", hitl: false, status: "processing", progress: 45, completedEnterprises: 30, blockedEnterprises: 5 },
  { id: 17, name: "财报申报", window: "W2", enterpriseCount: 999, agentId: "xiaoshui", primarySkill: "financial-statement-filing", hitl: false, status: "processing", progress: 38, completedEnterprises: 380, blockedEnterprises: 51 },
  { id: 18, name: "增值税申报", window: "W2", enterpriseCount: 999, agentId: "xiaoshui", primarySkill: "vat-filing", hitl: false, status: "processing", progress: 11, completedEnterprises: 110, blockedEnterprises: 51 },
  { id: 19, name: "企业所得税申报", window: "W2", enterpriseCount: 999, agentId: "xiaoshui", primarySkill: "cit-filing", hitl: false, status: "ready", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 20, name: "定期定额核定", window: "W2", enterpriseCount: 89, agentId: "xiaoshui", primarySkill: "fixed-quota-filing", hitl: false, status: "ready", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 21, name: "财产行为税", window: "W2", enterpriseCount: 345, agentId: "xiaoshui", primarySkill: "property-behavior-tax", hitl: false, status: "ready", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 22, name: "非税收入申报", window: "W2", enterpriseCount: 123, agentId: "xiaoshui", primarySkill: "non-tax-revenue", hitl: false, status: "ready", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 23, name: "漏报检查", window: "W2", enterpriseCount: 999, agentId: "zongjian", primarySkill: "missing-filing-check", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 24, name: "税种申报反馈", window: "W2", enterpriseCount: 789, agentId: "xiaoke", primarySkill: "filing-feedback", hitl: true, hitlType: "客户同意扣款", status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 25, name: "税金统计及划扣", window: "W2", enterpriseCount: 789, agentId: "xiaoshui", primarySkill: "tax-payment-record", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },

  // W3 质检期 (16-24号, 10 tasks) — all pending
  { id: 26, name: "全盘账务质检", window: "W3", enterpriseCount: 999, agentId: "xiaojian", primarySkill: "full-account-audit", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 27, name: "全盘账务调整", window: "W3", enterpriseCount: 234, agentId: "xiaosuan", primarySkill: "full-account-adjustment", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 28, name: "全盘账务反馈", window: "W3", enterpriseCount: 999, agentId: "zongjian", primarySkill: "account-feedback", hitl: true, hitlType: "客户确认", status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 29, name: "全盘异常调账", window: "W3", enterpriseCount: 89, agentId: "xiaoan", primarySkill: "exception-adjustment", hitl: true, hitlType: "客户授意", status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 30, name: "全盘漏账检查", window: "W3", enterpriseCount: 999, agentId: "xiaojian", primarySkill: "missing-entry-check", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 31, name: "生成税务风险报告", window: "W3", enterpriseCount: 999, agentId: "xiaoan", primarySkill: "tax-risk-reporter", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 32, name: "风险提醒", window: "W3", enterpriseCount: 152, agentId: "xiaoan", primarySkill: "risk-alert", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 33, name: "线索转化商机推送", window: "W3", enterpriseCount: 67, agentId: "xiaoan", primarySkill: "lead-conversion", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 34, name: "社保公积金扣费提醒", window: "W3", enterpriseCount: 456, agentId: "xiaoan", primarySkill: "social-insurance-reminder", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },

  // PLACEHOLDER for task 35 (index consistency)
  // There's no task between 34 and 35 (34 is last W3, 35 is first W4)

  // W4 准备期 (25-31号, 7 tasks) — all pending
  { id: 35, name: "无票收入信息采集", window: "W4", enterpriseCount: 234, agentId: "xiaozhi", primarySkill: "unreceipted-income-collector", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 36, name: "当月报销单采集", window: "W4", enterpriseCount: 567, agentId: "xiaozhi", primarySkill: "current-expense-collector", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 37, name: "资料采集预提醒", window: "W4", enterpriseCount: 999, agentId: "xiaoke", primarySkill: "collection-pre-reminder", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 38, name: "生成电子账本", window: "W4", enterpriseCount: 999, agentId: "xiaosuan", primarySkill: "e-ledger-generator", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 39, name: "当月发票数据采集", window: "W4", enterpriseCount: 999, agentId: "xiaozhi", primarySkill: "current-invoice-collector", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 40, name: "当月税费预提醒", window: "W4", enterpriseCount: 789, agentId: "xiaoan", primarySkill: "tax-pre-reminder", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
  { id: 41, name: "新增企业确认", window: "W4", enterpriseCount: 23, agentId: "xiaoke", primarySkill: "new-enterprise-onboard", hitl: false, status: "pending", progress: 0, completedEnterprises: 0, blockedEnterprises: 0 },
];

// Computed KPIs
export function getKPIs() {
  const completed = TASK_INSTANCES.filter((t) => t.status === "completed").length;
  const total = TASK_INSTANCES.length;
  const totalUnits = TASK_INSTANCES.reduce((s, t) => s + t.enterpriseCount, 0);
  const processedUnits = TASK_INSTANCES.reduce((s, t) => s + t.completedEnterprises, 0);
  const exceptions = TASK_INSTANCES.reduce((s, t) => s + t.blockedEnterprises, 0);

  // Filing deadline: day 15. Current mock: day 12 of month
  const today = 12;
  const deadlineDaysLeft = 15 - today;

  return {
    tasksCompleted: completed,
    tasksTotal: total,
    tasksPercent: Math.round((completed / total) * 100),
    processedUnits,
    totalUnits,
    unitsPercent: Math.round((processedUnits / totalUnits) * 100),
    deadlineDaysLeft,
    exceptions,
  };
}

export function getTasksByWindow(window: TimeWindow): TaskInstance[] {
  return TASK_INSTANCES.filter((t) => t.window === window);
}

export const STATUS_STYLES: Record<TaskStatus, { bg: string; text: string; label: string }> = {
  completed: { bg: "#E6F4EC", text: "#1B7F4B", label: "已完成" },
  processing: { bg: "#E8F0FE", text: "#003A70", label: "处理中" },
  ready: { bg: "#FEF3E0", text: "#815600", label: "就绪" },
  pending: { bg: "#F4F4F2", text: "#5A5A72", label: "待启动" },
  blocked: { bg: "#FDECEB", text: "#C4281C", label: "阻塞" },
};

export const TIER_STYLES: Record<AgentTier, { bg: string; text: string; label: string }> = {
  starter: { bg: "#E8F0FE", text: "#003A70", label: "STARTER" },
  professional: { bg: "#FEF3E0", text: "#815600", label: "PROFESSIONAL" },
  enterprise: { bg: "#E6F4EC", text: "#1B7F4B", label: "ENTERPRISE" },
};
