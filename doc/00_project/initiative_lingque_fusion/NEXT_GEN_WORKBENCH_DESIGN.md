# Next-Gen Intelligent Compliance Bookkeeping Workbench

> Deep design for Lingque System B Layer 1 (代账工作台).
> Based on: 41-task real accounting workflow + OpenClaw proactive Agent + batch automation.
> Prerequisite: OPTIMIZED_ARCHITECTURE_V2.md (2-system split, 4-layer product).

---

## 0. Executive Summary

A bookkeeping company is a **factory production line**, not a knowledge workplace. Every month, it processes the same 41 operations on up to 999 enterprises. The challenge is not "what to do" (rules are known and deterministic) but "how to do it at scale without errors or missed deadlines."

**This design transforms the workbench from a task checklist into a calendar-driven, dependency-aware, batch-processing factory floor where AI agents act as autonomous factory foremen.**

Key metrics that define success:

| Metric | Competitor (manual) | Lingque Target |
|--------|-------------------|----------------|
| Monthly task-enterprise units | 40,959 (manual click per unit) | 40,959 (batch auto) |
| W2 filing completion rate | ~95% by deadline (human stress) | 100% by day 14 (auto-early) |
| Avg enterprise processing time | 45 min/enterprise/month | < 5 min/enterprise/month |
| Human intervention rate | 100% (all tasks manual) | < 15% (exceptions only) |
| Error detection | Post-hoc (quality check after filing) | Pre-hoc (agent catches before filing) |

### Core Design Decisions

1. **Calendar-driven, not command-driven**: Agents activate based on calendar date, not human clicks
2. **Per-enterprise pipeline parallelism**: Enterprise A can be at Task 5 while Enterprise B is still at Task 4
3. **Two dependency types**: Per-enterprise (strict serial) and batch-level (all must complete)
4. **Agent = factory foreman**: Named identity, trust record, accuracy tracking — not a chatbot
5. **Skill = swappable tool**: Each task backed by 1+ OpenClaw Skills, upgradeable independently
6. **KG invisible**: Compliance knowledge powers agent accuracy, never exposed to customer

---

## 1. Core Model: Calendar-Driven State Machine

### 1.1 The Monthly Cycle is Deterministic

Unlike generic project management (variable scope, unknown tasks), bookkeeping has a **fixed monthly rhythm**. Every month, the same 41 tasks execute in the same order. The only variables are:

- **Which enterprises** need each task (filter conditions change monthly)
- **Exception handling** (new edge cases, regulatory changes)
- **Client responsiveness** (approval delays)

This determinism is the foundation: we can model the entire month as a **state machine** with known states, transitions, and deadlines.

### 1.2 Four Time Windows (W1-W4)

```
     1st ──────── 5th ──────── 6th ──────────── 15th ──────── 16th ──────── 24th ──── 25th ──── 31st
     │            │            │                │             │             │          │          │
     │  W1 采集期  │            │   W2 征期       │             │  W3 质检期   │          │ W4 准备期 │
     │  11 tasks  │            │   14 tasks      │             │  10 tasks   │          │ 7 tasks  │
     │  DATA IN   │            │   LEGAL FILING  │             │  QUALITY    │          │ NEXT MO  │
     │            │            │   ⚠ DEADLINE    │             │  ASSURANCE  │          │ PREP     │
     └────────────┘            └─────────────────┘             └────────────┘          └──────────┘
```

**W1 采集期 (1-5th, 11 tasks)**: Data collection + initial bookkeeping. The factory receives raw materials.

**W2 征期 (6-15th, 14 tasks)**: Tax filing. LEGAL DEADLINE — 15th is the hard cutoff for VAT, CIT, PIT. Late filing incurs penalties (滞纳金). This window operates at CRITICAL priority.

**W3 质检期 (16-24th, 10 tasks)**: Quality audit + risk reporting. The factory's quality control department.

**W4 准备期 (25-31st, 7 tasks)**: Next month preparation. Collect current month data, generate e-ledgers, send reminders.

### 1.3 Calendar Activation Rules

```yaml
# Proactive activation — agents initiate, humans don't need to click
activation_rules:
  - trigger: calendar_day == 1
    action: activate_w1_tasks([1..11])
    agent: [collector, bookkeeper, tax_specialist]
    priority: HIGH

  - trigger: calendar_day == 6
    action: activate_w2_tasks([12..25])
    agent: [tax_specialist, bookkeeper]
    priority: CRITICAL  # legal deadline
    deadline_warning: day_13  # 2 days before
    deadline_alert: day_14    # 1 day before

  - trigger: calendar_day == 16
    action: activate_w3_tasks([26..34])
    agent: [auditor, risk_specialist]
    priority: NORMAL

  - trigger: calendar_day == 25
    action: activate_w4_tasks([35..41])
    agent: [collector, client_service]
    priority: NORMAL

  # Exception: if W1 tasks not complete by day 5
  - trigger: calendar_day == 5 AND w1_incomplete > 0
    action: escalate_to_supervisor
    message: "W1 未完成 {count} 项任务，将影响 W2 征期"
```

---

## 2. Agent Architecture: 7 Digital Employees

### 2.1 Agent Roster

Each agent is a **named digital employee** with a persistent identity, specialization, and trust record. Agents are not interchangeable — they accumulate expertise and trust over time.

| Agent | Name | Specialty | Task Coverage | Tier |
|-------|------|-----------|---------------|------|
| 采集专员 | 小智 | Data collection, OCR, API integration | 1,2,3,8,12,35,36,37,39 | Starter |
| 记账专员 | 小算 | Voucher generation, bookkeeping, closing | 4,5,6,7,13,14,38 | Starter |
| 申报专员 | 小税 | Tax calculation, e-filing, declarations | 9,10,11,15-22,25 | Starter |
| 质检专员 | 小检 | Quality audit, error detection, completeness | 5*,26,27,30 | Professional |
| 主管 | 总监 | Orchestration, exception handling, metrics | 23,24,28 | Professional |
| 风控专员 | 小安 | Risk reports, compliance alerts, reminders | 29,31,32,33,34,40 | Enterprise |
| 客服专员 | 小客 | Client communication, approvals, onboarding | 24*,28*,29*,37,41 | Enterprise |

*Note: Some tasks appear in multiple agents because they involve cross-functional collaboration. The primary agent owns the task; the secondary assists.*

### 2.2 Pricing Tier Mapping

| Tier | Agents | Monthly Price | Capability |
|------|--------|-------------|------------|
| Starter | 3 (小智+小算+小税) | ¥999 | Core workflow: collect → book → file |
| Professional | 5 (+小检+总监) | ¥2,999 | + Quality audit + orchestration + exception handling |
| Enterprise | 7 (+小安+小客) | ¥8,999 | + Risk management + client service + full automation |

**Degradation on lower tiers**: When an agent is not available (e.g., Starter has no 质检专员), its tasks fall back to **manual human processing** — the system still shows the task, but the human does it instead of the agent. This creates natural upgrade pressure.

### 2.3 Agent Trust Record (The Moat)

Each agent maintains a running trust record per customer:

```typescript
interface AgentTrustRecord {
  agent_id: string;          // e.g., "tax-specialist-xiaoshui"
  customer_id: string;       // which accounting firm
  tenure_months: number;     // how many months serving this customer
  total_tasks: number;       // lifetime task count
  error_count: number;       // lifetime errors
  accuracy_rate: number;     // total_tasks - error_count / total_tasks
  avg_processing_time: number; // seconds per enterprise per task
  w2_deadline_miss: number;  // critical: how many filing deadlines missed (should be 0)
  last_error: {
    date: string;
    task_id: number;
    enterprise_id: string;
    description: string;
    resolution: string;
  } | null;
}
```

**Why this is the moat**: After 12 months of zero-error operation on 999 enterprises, the trust record is effectively irreplaceable. Competitors can copy the UI, but they can't copy 12 months of proven reliability on YOUR client data. Switching costs are astronomical — would you trust a new "AI accountant" with your clients' taxes after 小税 has filed perfectly for a year?

### 2.4 Agent Behavior Model

Agents follow the **Proactive Agent** pattern (from OpenClaw architecture):

```
OBSERVE → DECIDE → ACT → REPORT

1. OBSERVE: Check calendar date, pending tasks, enterprise readiness
2. DECIDE: Which enterprises can be processed? Any blockers?
3. ACT: Execute batch using Skill(s)
4. REPORT: Log results, update progress, trigger downstream
```

Agents do NOT wait for commands. They:
- Wake up at scheduled intervals (e.g., every 30 minutes during W2)
- Check what's ready to process
- Process all ready enterprises in one batch
- Report results and trigger next tasks in the dependency chain

---

## 3. Batch Automation Engine

### 3.1 The Batch Processing Unit

Each task operates on a **batch** of enterprises, not one at a time. The batch size varies:

| Batch Size | Meaning | Examples | Processing Strategy |
|-----------|---------|---------|-------------------|
| 999 | All enterprises | Bank collection, VAT filing | Full parallel, chunked |
| 789-856 | Most enterprises | Payroll, tax payment | Full parallel, chunked |
| 345-567 | Conditional subset | Property tax, social insurance | Filter → parallel |
| 89-234 | Exception handling | Adjustments, special filings | Filtered → serial or small parallel |
| 23-67 | Rare events | New enterprises, business income | Individual processing OK |

### 3.2 Chunk Processing Model

For large batches (>100 enterprises), processing is chunked to manage resources:

```
Batch(999 enterprises, task="VAT Filing")
  │
  ├── Chunk 1: enterprises[0..49]    → Agent processes 50 in parallel
  ├── Chunk 2: enterprises[50..99]   → Next chunk starts when Chunk 1 done
  ├── Chunk 3: enterprises[100..149] → ...
  │   ...
  └── Chunk 20: enterprises[950..999] → Final chunk
  │
  └── Batch Complete → trigger downstream tasks
```

Chunk size is configurable per task complexity:

| Task Complexity | Chunk Size | Example |
|----------------|-----------|---------|
| Simple (data collection, reminders) | 100 | Tasks 1,2,3,37 |
| Standard (bookkeeping, filing) | 50 | Tasks 4,15,18 |
| Complex (quality audit, risk report) | 20 | Tasks 26,31 |
| Manual (requires client approval) | 1 | Tasks 24,29 |

### 3.3 Enterprise Readiness Filter

Before processing, each enterprise is checked for readiness:

```typescript
interface EnterpriseReadiness {
  enterprise_id: string;
  task_id: number;
  ready: boolean;
  blockers: Blocker[];
}

interface Blocker {
  type: "missing_data" | "upstream_incomplete" | "awaiting_approval" | "exception";
  description: string;
  action: "wait" | "remind_client" | "escalate" | "skip";
}

// Example: Task 18 (VAT Filing) for Enterprise #456
{
  enterprise_id: "ENT-456",
  task_id: 18,
  ready: false,
  blockers: [
    {
      type: "upstream_incomplete",
      description: "Task 14 (税金账结账) not completed for this enterprise",
      action: "wait"
    }
  ]
}
```

The batch engine only processes **ready** enterprises. Blocked enterprises are queued with their blockers, and the agent periodically re-checks.

### 3.4 One-Click Batch Pattern

The signature UX pattern: **"一键处理 999 家企业的 [task]"**

```
┌──────────────────────────────────────────────────────┐
│  Task 1: 上月银行流水采集                               │
│  ──────────────────────────────────────────────────── │
│  Ready: 987/999    Blocked: 12    Completed: 0       │
│                                                       │
│  [▶ 一键处理 987 家企业]    [查看 12 家阻塞]             │
│                                                       │
│  Progress: ██████████████████████░░░░░░ 72%           │
│  Estimated: 12 min remaining                          │
│  Agent: 小智 (采集专员) | Skill: bank-statement-collector│
└──────────────────────────────────────────────────────┘
```

---

## 4. Dependency Graph Engine

### 4.1 Two Dependency Types

**Critical insight**: Dependencies exist at TWO levels, and confusing them causes either unnecessary blocking or premature execution.

#### Type 1: Per-Enterprise Dependency

Task B for enterprise X depends on Task A completing **for that same enterprise X**.

```
Enterprise #001: [Task 4: 记账] ──→ [Task 5: 质检] ──→ [Task 6: 调整]
Enterprise #002:    [Task 4: 记账] ──→ [Task 5: 质检] ──→ ...
Enterprise #003:       [Task 4: 记账] ──→ ...
```

Enterprise #001 can enter Task 5 while Enterprise #003 is still in Task 4. This is **pipeline parallelism** — the key efficiency gain over sequential batch processing.

#### Type 2: Batch-Level Dependency

Task B depends on Task A completing **for ALL enterprises in the batch**.

```
ALL enterprises must complete Tasks 15-22 (各类申报)
  ──→ THEN Task 23 (漏报检查) can start for ALL enterprises
```

Batch-level dependencies are rarer but critical for aggregate operations (audits, reports, completeness checks).

### 4.2 Complete Dependency Graph

```
W1 (Day 1-5):
  [1: 银行流水] ──┐
  [2: 工资表]  ──┤
  [3: 报销单]  ──┼──→ [4: 票据记账] ──→ [5: 质检] ──→ [6: 调整] ──→ [7: 无税金结账]
  [8: 发票采集] ──┘                                                        │
                                                          ┌────────────────┘
                                                          ▼
                                                   [9: 税项清册] ──→ [10: 税盘抄报]
                                                          │              │
                                                          ▼              ▼
                                                   [11: 进项勾选]

W2 (Day 6-15):                                    CRITICAL DEADLINE: 15th
  [12: 工资补采] ──→ [13: 税金记账] ──→ [14: 税金结账]
                                              │
                      ┌───────────────────────┘
                      ▼
    ┌─── [15: 个税申报]
    ├─── [16: 经营所得]
    ├─── [17: 财报申报] ←── requires [7] + [14] (全盘结账)
    ├─── [18: 增值税]
    ├─── [19: 企业所得税]      All 15-22 run in PARALLEL
    ├─── [20: 定期定额]        (different tax types, independent)
    ├─── [21: 财产行为税]
    └─── [22: 非税收入]
                      │
                      ▼ (BATCH-LEVEL: all 15-22 must complete for ALL enterprises)
               [23: 漏报检查] ──→ [24: 申报反馈] ──→ [25: 税金统计]
                                        │
                                 (HITL: client approval needed)

W3 (Day 16-24):
  [26: 全盘质检] ──→ [27: 调整] ──→ [28: 反馈] ──→ [29: 异常调账] ──→ [30: 漏账检查]
                                       │                  │
                                (HITL: client confirm)  (HITL: client authorize)
                                                                    │
                                                                    ▼
                                                          [31: 风险报告] ──→ [32: 风险提醒]
                                                                          ──→ [33: 线索转化]
                                                                          ──→ [34: 社保提醒]

W4 (Day 25-31):
  [35: 无票收入] ──┐
  [36: 报销单]   ──┼──→ [37: 预提醒] ──→ [38: 电子账本] ──→ [39: 发票采集]
                   │                                           │
                   │                                           ▼
                   │                                     [40: 税费预提醒]
                   │                                     [41: 新增企业确认]
```

### 4.3 Dependency Resolution Engine

```typescript
interface TaskDependency {
  task_id: number;
  depends_on: DependencySpec[];
}

interface DependencySpec {
  task_id: number;
  type: "per_enterprise" | "batch_level";
  condition?: string;  // optional filter, e.g., "only_general_taxpayer"
}

// Example: Task 17 (财务报表申报)
{
  task_id: 17,
  depends_on: [
    { task_id: 7,  type: "per_enterprise" },   // 无税金结账 must complete for this enterprise
    { task_id: 14, type: "per_enterprise" },   // 税金结账 must complete for this enterprise
  ]
}

// Example: Task 23 (漏报检查)
{
  task_id: 23,
  depends_on: [
    { task_id: 15, type: "batch_level" },  // ALL enterprises must complete individual tax
    { task_id: 16, type: "batch_level" },
    { task_id: 17, type: "batch_level" },
    { task_id: 18, type: "batch_level" },
    { task_id: 19, type: "batch_level" },
    { task_id: 20, type: "batch_level" },
    { task_id: 21, type: "batch_level" },
    { task_id: 22, type: "batch_level" },
  ]
}
```

When a task completes for an enterprise, the engine:
1. Checks all downstream per-enterprise dependencies
2. If all upstream per-enterprise deps satisfied → mark enterprise as **ready** for next task
3. For batch-level deps: check if ALL enterprises have completed upstream → activate next task

---

## 5. Skill Ecosystem: 41 Tasks → 100+ Skills

### 5.1 Skill Mapping

Each of 41 tasks maps to 1 **primary skill** (the core operation) and 0-N **supporting skills** (helpers).

#### W1 Skills (Data Collection + Bookkeeping)

| # | Task | Primary Skill | Supporting Skills |
|---|------|--------------|-------------------|
| 1 | 银行流水采集 | `bank-statement-collector` | `ocr-extractor`, `bank-api-adapter` |
| 2 | 工资表采集 | `payroll-collector` | `excel-parser`, `template-recognizer` |
| 3 | 报销单采集 | `expense-collector` | `receipt-ocr`, `category-classifier` |
| 4 | 票据记账 | `invoice-to-voucher` | `account-matcher`, `voucher-template` |
| 5 | 票据记账质检 | `voucher-quality-check` | `balance-verifier`, `rule-engine` |
| 6 | 票据记账调整 | `voucher-adjustment` | `error-corrector` |
| 7 | 无税金账结账 | `period-close-notax` | `trial-balance`, `close-procedure` |
| 8 | 发票完整采集 | `invoice-collector` | `e-invoice-api`, `ocr-extractor` |
| 9 | 税项清册 | `tax-schedule-generator` | `tax-rate-lookup`, `period-calculator` |
| 10 | 税盘抄报 | `tax-disk-report` | `tax-disk-api` |
| 11 | 进项勾选抵扣 | `input-vat-matching` | `invoice-reconciler`, `deduction-optimizer` |

#### W2 Skills (Tax Filing — CRITICAL)

| # | Task | Primary Skill | Supporting Skills |
|---|------|--------------|-------------------|
| 12 | 工资表补采集 | `payroll-followup` | `client-reminder`, `payroll-collector` |
| 13 | 税金记账 | `tax-voucher-generator` | `tax-schedule-reader`, `voucher-template` |
| 14 | 税金账结账 | `period-close-tax` | `trial-balance`, `close-procedure` |
| 15 | 个税申报 | `pit-filing` | `e-tax-api`, `payroll-calculator` |
| 16 | 经营所得申报 | `business-income-filing` | `e-tax-api`, `sole-prop-calculator` |
| 17 | 财报申报 | `financial-statement-filing` | `e-tax-api`, `statement-generator` |
| 18 | 增值税申报 | `vat-filing` | `e-tax-api`, `invoice-reconciler` |
| 19 | 企业所得税申报 | `cit-filing` | `e-tax-api`, `income-calculator` |
| 20 | 定期定额核定及申报 | `fixed-quota-filing` | `e-tax-api` |
| 21 | 财产和行为税申报 | `property-behavior-tax` | `e-tax-api`, `stamp-duty-calc` |
| 22 | 非税收入申报 | `non-tax-revenue` | `e-tax-api` |
| 23 | 漏报检查 | `missing-filing-check` | `filing-record-scanner`, `alert-engine` |
| 24 | 税种申报反馈 | `filing-feedback` | `client-notifier`, `approval-collector` |
| 25 | 税金统计及划扣 | `tax-payment-record` | `bank-debit-tracker` |

#### W3 Skills (Quality Audit)

| # | Task | Primary Skill | Supporting Skills |
|---|------|--------------|-------------------|
| 26 | 全盘账务质检 | `full-account-audit` | `balance-checker`, `cross-ref-validator` |
| 27 | 全盘账务调整 | `full-account-adjustment` | `error-corrector`, `adjustment-log` |
| 28 | 全盘账务反馈 | `account-feedback` | `client-notifier`, `report-generator` |
| 29 | 全盘异常调账 | `exception-adjustment` | `client-approval`, `audit-trail` |
| 30 | 全盘漏账检查 | `missing-entry-check` | `completeness-scanner` |
| 31 | 税务风险报告 | `tax-risk-reporter` | `risk-model`, `kg-query-engine` |
| 32 | 风险提醒 | `risk-alert` | `client-notifier`, `threshold-engine` |
| 33 | 线索转化商机推送 | `lead-conversion` | `crm-connector`, `opportunity-scorer` |
| 34 | 社保公积金扣费提醒 | `social-insurance-reminder` | `calendar-scheduler` |

#### W4 Skills (Next Month Prep)

| # | Task | Primary Skill | Supporting Skills |
|---|------|--------------|-------------------|
| 35 | 无票收入采集 | `unreceipted-income-collector` | `client-questionnaire` |
| 36 | 当月报销单采集 | `current-expense-collector` | `expense-collector` |
| 37 | 资料采集预提醒 | `collection-pre-reminder` | `calendar-scheduler`, `client-notifier` |
| 38 | 生成电子账本 | `e-ledger-generator` | `pdf-generator`, `archive-manager` |
| 39 | 当月发票采集 | `current-invoice-collector` | `invoice-collector` |
| 40 | 税费预提醒 | `tax-pre-reminder` | `calendar-scheduler`, `tax-estimator` |
| 41 | 新增企业确认 | `new-enterprise-onboard` | `client-profile`, `tax-registration` |

### 5.2 Skill Totals

| Category | Count | Description |
|----------|-------|-------------|
| Primary Skills | 41 | One per task, the core operation |
| Supporting Skills | 38 | Unique helpers (deduplicated across tasks) |
| Shared Infrastructure | 6 | `e-tax-api`, `client-notifier`, `calendar-scheduler`, `ocr-extractor`, `voucher-template`, `trial-balance` |
| **Total Unique Skills** | **79** | In the accounting domain |

### 5.3 Skill Marketplace Tiers

| Tier | Examples | Pricing | Description |
|------|---------|---------|-------------|
| Free | `bank-statement-collector`, `voucher-template` | ¥0 | Basic operations, included with agent |
| Premium | `deduction-optimizer`, `risk-model`, `kg-query-engine` | ¥99-499/month | Advanced AI-powered features |
| Enterprise | `e-tax-api` (direct integration), `audit-trail` | Custom | Requires API access + compliance cert |

Revenue model: 70% to skill creator / 30% to platform. Skills FROM OpenClaw supply chain get additional curation quality.

---

## 6. Human-in-the-Loop Protocol

### 6.1 Three HITL Points

The 41-task workflow has exactly 3 tasks that require human intervention:

| Task | HITL Type | Why | Agent Behavior |
|------|----------|-----|----------------|
| 24. 税种申报反馈 | **Client approval** | Client must confirm tax amounts before bank deduction | Agent sends summary → waits for client "同意扣款" → proceeds |
| 28. 全盘账务反馈 | **Client confirmation** | Client reviews account status and confirms accuracy | Agent sends report → waits for client "确认无误" → proceeds |
| 29. 全盘异常调账 | **Client authorization** | Adjustments to anomalous entries require client's explicit written consent (legal requirement) | Agent flags anomaly → presents options → waits for client decision → executes |

### 6.2 HITL Timeout Escalation

```yaml
hitl_protocol:
  initial_reminder: 24h after request
  second_reminder: 48h after request
  escalation_to_supervisor: 72h after request
  auto_skip_with_flag: 96h (mark as "客户未确认" and proceed with next tasks)

  channels:
    - wechat_service_account  # primary
    - sms                     # fallback
    - phone_call              # supervisor escalation
```

### 6.3 Beyond the 3 HITL Points: Soft Interventions

Some tasks have **soft intervention** points where the agent should notify but not block:

| Task | Notification | Block? |
|------|-------------|--------|
| 6. 票据记账调整 | "发现 234 家企业有异常项需调整" | No — auto-adjust standard patterns |
| 23. 漏报检查 | "发现 X 家企业有漏报" | No — auto-file if within tolerance |
| 31. 风险报告 | "X 家企业存在税务风险" | No — generate report, send to client |
| 32. 风险提醒 | Alert message to client | No — informational only |
| 41. 新增企业确认 | "本月新增 23 家企业，请确认信息" | Semi — needs basic info confirmation |

---

## 7. Data Model

### 7.1 Core Entities

```typescript
// Task definition (static, loaded from config)
interface TaskDefinition {
  id: number;                    // 1-41
  name: string;                  // e.g., "上月银行流水采集"
  module: "collection" | "accounting" | "filing" | "management";
  window: "W1" | "W2" | "W3" | "W4";
  window_start_day: number;      // e.g., 1 for W1
  window_end_day: number;        // e.g., 5 for W1
  default_enterprise_count: number; // e.g., 999
  filter_condition?: string;     // e.g., "has_tax_disk" for task 10
  primary_skill_id: string;
  supporting_skill_ids: string[];
  assigned_agent: string;        // agent ID
  dependencies: DependencySpec[];
  hitl_required: boolean;
  chunk_size: number;            // batch processing chunk size
  priority: "NORMAL" | "HIGH" | "CRITICAL";
}

// Monthly task instance (created per month)
interface TaskInstance {
  id: string;                    // "2026-04-T01" (year-month-TaskID)
  task_def_id: number;
  month: string;                 // "2026-04"
  status: "pending" | "ready" | "processing" | "awaiting_human" | "completed" | "failed";
  enterprises_total: number;
  enterprises_ready: number;
  enterprises_completed: number;
  enterprises_blocked: number;
  enterprises_failed: number;
  agent_id: string;
  started_at?: string;
  completed_at?: string;
  processing_time_seconds?: number;
}

// Per-enterprise task status
interface EnterpriseTaskStatus {
  enterprise_id: string;
  task_instance_id: string;
  status: "not_started" | "ready" | "processing" | "completed" | "failed" | "blocked" | "awaiting_human";
  blockers: Blocker[];
  started_at?: string;
  completed_at?: string;
  agent_id: string;
  skill_execution_log?: SkillExecutionLog;
}

// Skill execution log (audit trail)
interface SkillExecutionLog {
  skill_id: string;
  input_hash: string;           // hash of input data for reproducibility
  output_summary: string;
  errors: string[];
  warnings: string[];
  duration_ms: number;
  kg_queries_made: number;      // how many KG lookups (invisible to customer)
}

// Enterprise (customer's client)
interface Enterprise {
  id: string;
  name: string;
  tax_type: "general" | "small_scale" | "sole_prop";
  has_tax_disk: boolean;
  industry: string;
  registered_capital: number;
  monthly_invoice_volume: number;
  risk_level: "low" | "medium" | "high";
  last_month_status: "normal" | "exception" | "new";
}
```

### 7.2 Monthly State Machine

Each month, the system creates 41 TaskInstances and ~41,000 EnterpriseTaskStatus records. The state machine:

```
                    ┌──────────────────────────────────────────────┐
                    │            Monthly Lifecycle                  │
                    │                                              │
  Calendar Day 1 ──→│  CREATE 41 TaskInstances                     │
                    │  CREATE enterprise_count × 41 EnterpriseTask  │
                    │  ACTIVATE W1 tasks                            │
                    │                                              │
  Calendar Day 6 ──→│  ACTIVATE W2 tasks (CRITICAL)                │
                    │                                              │
  Calendar Day 16 ─→│  ACTIVATE W3 tasks                           │
                    │                                              │
  Calendar Day 25 ─→│  ACTIVATE W4 tasks                           │
                    │                                              │
  Calendar Day 31 ─→│  CLOSE month                                 │
                    │  ARCHIVE all records                          │
                    │  GENERATE monthly report                     │
                    └──────────────────────────────────────────────┘
```

---

## 8. UI/UX: Workbench Views

### 8.1 Six Core Views

#### View 1: 月度看板 (Monthly Kanban) — DEFAULT VIEW

```
┌─────────────┬─────────────┬──────────────┬─────────────┐
│ W1 采集期    │ W2 征期      │ W3 质检期     │ W4 准备期    │
│ Day 1-5     │ Day 6-15    │ Day 16-24    │ Day 25-31   │
│ ────────    │ ────────    │ ────────     │ ────────    │
│ ████ 11/11  │ ████ 12/14  │ ░░░░ 0/10   │ ░░░░ 0/7   │
│ COMPLETED   │ IN PROGRESS │ PENDING      │ PENDING     │
│             │             │              │             │
│ ✓ 银行流水   │ ✓ 工资补采   │ ○ 全盘质检    │ ○ 无票收入   │
│ ✓ 工资表     │ ✓ 税金记账   │ ○ 全盘调整    │ ○ 报销单     │
│ ✓ 报销单     │ ✓ 税金结账   │ ○ 账务反馈    │ ○ 预提醒     │
│ ✓ 票据记账   │ ● 个税申报   │ ○ 异常调账    │ ○ 电子账本   │
│ ✓ 质检      │ ● 增值税     │ ○ 漏账检查    │ ○ 发票采集   │
│ ✓ 调整      │ ● 企业所得税  │ ○ 风险报告    │ ○ 税费提醒   │
│ ✓ 结账      │ ● 财报申报   │ ○ 风险提醒    │ ○ 新增企业   │
│ ✓ 发票采集   │ ○ 漏报检查   │ ○ 线索转化    │             │
│ ✓ 税项清册   │ ○ 申报反馈   │ ○ 社保提醒    │             │
│ ✓ 税盘抄报   │ ○ 税金统计   │              │             │
│ ✓ 进项勾选   │             │              │             │
│             │ ⚠ Deadline:  │              │             │
│             │   Day 15     │              │             │
└─────────────┴─────────────┴──────────────┴─────────────┘
```

#### View 2: 批量操作台 (Batch Control) — POWER VIEW

Click any task → expand to batch control panel:

```
┌────────────────────────────────────────────────────────┐
│ Task 18: 增值税及附加税申报                               │
│ Agent: 小税 (申报专员) | Skill: vat-filing                │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│ │  Ready   │  │Processing│  │ Blocked  │  │Completed │ │
│ │   834    │  │   102    │  │    51    │  │    12    │ │
│ │  83.5%   │  │  10.2%   │  │   5.1%   │  │   1.2%  │ │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                         │
│ [▶ 一键处理 834 家就绪企业]   [⟳ 重试 3 家失败]            │
│                                                         │
│ Progress: ████████████░░░░░░░░░░░░░░░░░░░ 11.4%        │
│ Speed: 8.2 enterprises/min | ETA: 1h 42min             │
│                                                         │
│ Blocked enterprises (51):                               │
│ ┌───────────────────────────────────────────────────┐   │
│ │ ENT-234 深圳市XX公司 | Blocker: Task 14 未完成      │   │
│ │ ENT-567 广州市YY公司 | Blocker: 发票数据缺失         │   │
│ │ ENT-891 北京市ZZ公司 | Blocker: 客户未确认           │   │
│ │ ...                                               │   │
│ └───────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

#### View 3: Agent 工位 (Agent Workstation)

Per-agent view showing their current workload:

```
┌────────────────────────────────────────────────────────┐
│ 小税 (申报专员)                                          │
│ ─────────────────────────────────────────────────────── │
│ Trust Score: 99.7% | Tasks this month: 2,847            │
│ Errors: 0 | Tenure: 8 months                            │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Active Tasks:                                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ● T15 个税申报      856 enterprises  Processing 72%  │ │
│ │ ● T18 增值税申报     999 enterprises  Processing 11%  │ │
│ │ ● T19 企业所得税     999 enterprises  Queued          │ │
│ │ ○ T20 定期定额       89 enterprises   Waiting deps   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Skills in use: pit-filing, vat-filing, e-tax-api        │
│ KG queries today: 1,247 (invisible to client)           │
└────────────────────────────────────────────────────────┘
```

#### View 4: 依赖图 (Dependency Graph)

Interactive DAG visualization (reuse Cytoscape.js from KG Explorer):

- Nodes = 41 tasks, colored by window (W1 blue, W2 red, W3 green, W4 gray)
- Edges = dependencies, solid for per-enterprise, dashed for batch-level
- Node size = enterprise count (999 = large, 23 = small)
- Node status coloring: completed (green), processing (amber), pending (gray), blocked (red)

#### View 5: 日历视图 (Calendar View)

Monthly calendar with tasks overlaid as horizontal bars:

```
Mon   Tue   Wed   Thu   Fri   Sat   Sun
                  1     2     3     4
                  ├─ W1 采集期 ──────────┤
5     6     7     8     9     10    11
      ├─ W2 征期 ────────────────────────
12    13    14    15    16    17    18
─────────── ⚠ ──┤      ├─ W3 质检期 ────
19    20    21    22    23    24    25
────────────────────────────────┤  ├─ W4
26    27    28    29    30    31
── 准备期 ──────────────────────┤
```

#### View 6: 异常中心 (Exception Center)

Filtered view of all items requiring attention:

- HITL items (awaiting client approval)
- Failed enterprises (processing errors)
- Overdue items (past expected completion)
- Risk alerts (from W3 risk reports)

### 8.2 Dashboard KPIs (Top Bar)

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ 本月进度      │ 已处理企业     │ 征期倒计时    │ 异常待处理    │
│ 23/41 tasks  │ 28,471/40,959│ 3 天          │ 12 项        │
│ 56.1%        │ 69.5%        │ ⚠ CRITICAL   │ 需人工介入    │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 9. KG Integration (Invisible Layer)

### 9.1 How KG Powers Agent Accuracy

The Knowledge Graph (514K nodes, 1.1M edges) is System A infrastructure. Agents in System B query it via CF Worker proxy without the customer ever knowing.

Key KG queries by task:

| Task | KG Query | Purpose |
|------|----------|---------|
| 5. 质检 | `match (r:LawOrRegulation)-[:REGULATES]->(t:TaxType)` | Validate voucher against latest regulations |
| 9. 税项清册 | `match (t:TaxType)-[:HAS_RATE]->(r:TaxRate)` | Get current tax rates for enterprise type |
| 18. 增值税 | `match (p:TaxPolicy)-[:APPLIES_TO]->(i:Industry)` | Industry-specific VAT rules |
| 26. 质检 | `match (r:ComplianceRule)-[:CHECKS]->(a:AccountType)` | Comprehensive audit ruleset |
| 31. 风险报告 | `match (e:Enterprise)-[:HAS_RISK]->(r:RiskFactor)` | Risk model with historical data |

### 9.2 KG as Quality Multiplier

Without KG: Agent uses generic rules → 95% accuracy
With KG: Agent uses domain-specific knowledge → 99.5% accuracy

The 4.5% improvement sounds small, but on 999 enterprises:
- Without KG: 50 errors/month → client trust damage
- With KG: 5 errors/month → manageable exceptions

This is why KG is "invisible but essential" — customers see the result (high accuracy), not the mechanism (knowledge graph).

---

## 10. Migration Plan

### 10.1 From Current State to Production Workbench

| Phase | Timeline | Deliverable | Status |
|-------|----------|-------------|--------|
| P0 | Done | Architecture v2 doc + 41-task model | COMPLETED |
| P1 | Week 1-2 | Task definition config (41 tasks × YAML) + dependency graph | NEXT |
| P2 | Week 3-4 | Batch engine core (chunked processing, readiness filter) | |
| P3 | Week 5-6 | Agent runtime (7 agents, trust record, proactive activation) | |
| P4 | Week 7-8 | Skill integration (top 10 skills with mock → real migration) | |
| P5 | Week 9-10 | Workbench UI (6 views, dashboard KPIs) | |
| P6 | Week 11-12 | KG integration (CF Worker proxy, query layer) | |
| P7 | Week 13-14 | Pilot with 1 real accounting firm (3 scenarios) | |

### 10.2 P1 Deliverables (First Sprint)

1. `configs/task-definitions.yaml` — All 41 tasks with dependencies, agents, skills, chunk sizes
2. `core/dependency-engine.ts` — Dependency resolution (per-enterprise + batch-level)
3. `core/calendar-engine.ts` — Time window activation logic
4. Unit tests for dependency resolution edge cases

---

## 11. Architecture Decision Records

### ADR-W01: Per-Enterprise Pipeline Parallelism

**Context**: Should we process tasks batch-by-batch (all enterprises complete Task 4 before any start Task 5) or pipeline-style (Enterprise A can start Task 5 as soon as its own Task 4 completes)?

**Decision**: Pipeline parallelism for per-enterprise dependencies. Batch synchronization only for batch-level dependencies (Task 23).

**Consequence**: 3-5x throughput improvement at the cost of more complex state tracking.

### ADR-W02: Agent Degradation on Lower Tiers

**Context**: What happens when a Starter customer has no 质检专员 but Task 26 (全盘质检) still needs to happen?

**Decision**: Tasks assigned to missing agents show up in the workbench with "手动处理" tag. The system still tracks progress and dependencies, but a human does the work.

**Consequence**: Natural upgrade pressure without hard feature gates. Customers see the value of agents before paying for them.

### ADR-W03: Chunk Size Per Task Complexity

**Context**: Should all tasks use the same batch processing chunk size?

**Decision**: Variable chunk sizes (100/50/20/1) based on task complexity and resource consumption.

**Consequence**: Prevents resource starvation on complex tasks while maximizing throughput on simple ones.

### ADR-W04: Calendar Activation vs Event-Driven

**Context**: Should tasks activate based on calendar dates or based on upstream completion events?

**Decision**: Both. Calendar activation sets the window; dependency completion triggers readiness within the window.

**Consequence**: Prevents premature activation (can't start filing before day 6 even if data is ready) while enabling fast progression within windows.

### ADR-W05: KG Invisible to Customer

**Context**: Should customers know their agents use a Knowledge Graph?

**Decision**: No. KG is implementation detail. Customers see "高准确率" and "合规检查", not "知识图谱查询".

**Consequence**: Prevents competitor feature-matching (they can copy UI, can't copy 514K-node KG). Also avoids confusing non-technical accounting firm users.

---

## Appendix A: Complete Task-Agent-Skill Matrix

| Task ID | Task Name | Window | Agent | Primary Skill | Enterprises | Dep Type | HITL |
|---------|-----------|--------|-------|--------------|-------------|----------|------|
| 1 | 银行流水采集 | W1 | 小智 | bank-statement-collector | 999 | - | No |
| 2 | 工资表采集 | W1 | 小智 | payroll-collector | 856 | - | No |
| 3 | 报销单采集 | W1 | 小智 | expense-collector | 734 | - | No |
| 4 | 票据记账 | W1 | 小算 | invoice-to-voucher | 999 | PE(1,2,3) | No |
| 5 | 票据记账质检 | W1 | 小检 | voucher-quality-check | 999 | PE(4) | No |
| 6 | 票据记账调整 | W1 | 小算 | voucher-adjustment | 234 | PE(5) | No |
| 7 | 无税金账结账 | W1 | 小算 | period-close-notax | 567 | PE(6) | No |
| 8 | 发票完整采集 | W1 | 小智 | invoice-collector | 999 | - | No |
| 9 | 税项清册 | W1 | 小税 | tax-schedule-generator | 999 | PE(7,8) | No |
| 10 | 税盘抄报 | W1 | 小税 | tax-disk-report | 456 | PE(9) | No |
| 11 | 进项勾选抵扣 | W1 | 小税 | input-vat-matching | 234 | PE(9) | No |
| 12 | 工资表补采集 | W2 | 小智 | payroll-followup | 143 | - | No |
| 13 | 税金记账 | W2 | 小算 | tax-voucher-generator | 789 | PE(9) | No |
| 14 | 税金账结账 | W2 | 小算 | period-close-tax | 432 | PE(13) | No |
| 15 | 个税申报 | W2 | 小税 | pit-filing | 856 | PE(14) | No |
| 16 | 经营所得申报 | W2 | 小税 | business-income-filing | 67 | PE(14) | No |
| 17 | 财报申报 | W2 | 小税 | financial-statement-filing | 999 | PE(7,14) | No |
| 18 | 增值税申报 | W2 | 小税 | vat-filing | 999 | PE(14) | No |
| 19 | 企业所得税申报 | W2 | 小税 | cit-filing | 999 | PE(14) | No |
| 20 | 定期定额核定 | W2 | 小税 | fixed-quota-filing | 89 | PE(14) | No |
| 21 | 财产行为税 | W2 | 小税 | property-behavior-tax | 345 | PE(14) | No |
| 22 | 非税收入 | W2 | 小税 | non-tax-revenue | 123 | PE(14) | No |
| 23 | 漏报检查 | W2 | 总监 | missing-filing-check | 999 | BL(15-22) | No |
| 24 | 申报反馈 | W2 | 小客 | filing-feedback | 789 | PE(23) | **Yes** |
| 25 | 税金统计 | W2 | 小税 | tax-payment-record | 789 | PE(24) | No |
| 26 | 全盘质检 | W3 | 小检 | full-account-audit | 999 | - | No |
| 27 | 全盘调整 | W3 | 小算 | full-account-adjustment | 234 | PE(26) | No |
| 28 | 账务反馈 | W3 | 总监 | account-feedback | 999 | PE(27) | **Yes** |
| 29 | 异常调账 | W3 | 小安 | exception-adjustment | 89 | PE(28) | **Yes** |
| 30 | 漏账检查 | W3 | 小检 | missing-entry-check | 999 | PE(29) | No |
| 31 | 风险报告 | W3 | 小安 | tax-risk-reporter | 999 | PE(30) | No |
| 32 | 风险提醒 | W3 | 小安 | risk-alert | 152 | PE(31) | No |
| 33 | 线索转化 | W3 | 小安 | lead-conversion | 67 | PE(31) | No |
| 34 | 社保提醒 | W3 | 小安 | social-insurance-reminder | 456 | - | No |
| 35 | 无票收入采集 | W4 | 小智 | unreceipted-income-collector | 234 | - | No |
| 36 | 报销单采集 | W4 | 小智 | current-expense-collector | 567 | - | No |
| 37 | 预提醒 | W4 | 小客 | collection-pre-reminder | 999 | - | No |
| 38 | 电子账本 | W4 | 小算 | e-ledger-generator | 999 | BL(W3) | No |
| 39 | 发票采集 | W4 | 小智 | current-invoice-collector | 999 | - | No |
| 40 | 税费预提醒 | W4 | 小安 | tax-pre-reminder | 789 | - | No |
| 41 | 新增企业确认 | W4 | 小客 | new-enterprise-onboard | 23 | - | Semi |

Legend: PE(n) = Per-Enterprise dependency on task n. BL(n-m) = Batch-Level dependency on tasks n through m.

---

Maurice | maurice_wen@proton.me
