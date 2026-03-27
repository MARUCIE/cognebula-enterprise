# L2 Page Design Decision — 灵阙 Desktop 二级页面设计决策

> Swarm decision: Jobs + Drucker + Hara (2026-03-27)
> Status: APPROVED — ready for implementation

## Context

16 first-level pages deployed with 78 dead-end interactive elements.
Product feels like "16 beautiful menus with no food" (Drucker).

## Decision Matrix

| Priority | Page | Type | Rationale |
|----------|------|------|-----------|
| **P0** | Notification Popover | Popover component | "铃铛不响=产品是假的" (Hara). Lowest cost, highest credibility impact |
| **P0** | `/clients/[id]` | Full page | 128 "查看详情" buttons → "承诺违约" (Drucker). Demo 核心 |
| **P1** | `/reports/[id]` | Full page | AI 价值闭环证明。"AI生成+人工审批"完整动作 (Jobs) |
| **P2** | Skills Sheet | Side drawer | ~50 lines, no new route. Sheet on `/skills` page (Hara) |
| **DEFER** | `/help` | Remove | "帮助中心 = 设计失败的证明" (Hara). Remove from sidebar |

## P0: Notification Popover Design

**Location**: TopBar bell icon (already has red dot "3")
**Component**: Popover, 380px width, click to open

**Content structure**:
```
[待处理 2 件 | 今日动态 8 条]

── 需要处理 ──
• 云峰智源: Q3增值税申报异常，需人工确认  [立即处理]
• 深圳极智: 2份报告待审批              [审批]

── 今日动态 ──
• 林税安完成42家Q3增值税批量申报
• 赵合规更新合规规则库 (+47条)
• 王记账完成腾讯科技月度凭证录入

[查看全部 →]
```

**Key design rules** (Jobs):
- First line = "有几件事需要你处理" (anxiety resolution)
- "需要处理" group always on top, even if empty
- One-click action buttons inside notifications (no page jump)
- "今日动态" = info-only, no action needed

## P0: `/clients/[id]` Page Design

**User intent**: "这个客户现在有没有问题？" (risk scan, not info browse)

**First screen (above fold)**:
```
┌─────────────────────────────────────────────┐
│ [← 返回客户列表]  中铁建设集团有限公司       │
│                                              │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐ │
│ │ 正常  │ │ 待申报│ │ 合规98│ │ AI风险嗅探    │ │
│ │ 状态  │ │ 2项  │ │  分  │ │ "该客户连续3 │ │
│ └──────┘ └──────┘ └──────┘ │ 个月增值税税  │ │
│                              │ 负率低于行业  │ │
│ ── 当前 AI 专员活动 ──       │ 均值0.3%"    │ │
│ 林税安: Q3增值税核验中 ETA 2h│              │ │
│ 王记账: 11月凭证录入完成     │              │ │
│ 赵合规: 合规扫描 ✓          └──────────────┘ │
│                                              │
│ ── 待审批事项 (2) ──                         │
│ • Q3损益表 [AI生成] → [审批]                 │
│ • 现金流异常报告 [需关注] → [核查]           │
└─────────────────────────────────────────────┘
```

**Below fold**: 本月已完成任务 → 历史申报记录 → 客户基本档案
**Delighter**: "AI风险嗅探"卡片 — 一句话风险提示 (Jobs: "值10万顾问费")
**Kill**: 不要做成 CRM 信息表单。删掉70%字段 (Jobs)

## P1: `/reports/[id]` Page Design

**User intent**: "这份报告能不能发给客户？" (quality check + approval)

**First screen**:
```
┌─────────────────────────────────────────────┐
│ [← 返回报告列表]                             │
│                                              │
│ 中铁建设集团 — 2024Q3 资产负债表             │
│ AI 生成 | 2024-11-24 14:20 | ¥45,280,000    │
│                                              │
│ AI 置信度: 97.2%  |  ⚠ 2处需人工确认         │
│                                              │
│ [导出PDF] [发送给客户] [标记问题] [✓ 批准]    │
│                                              │
│ ── 报告正文 (结构化，非PDF) ──               │
│ 资产合计: ¥45,280,000  [△ +12% vs Q2] ←AI标注│
│   流动资产: ¥28,500,000                      │
│     货币资金: ¥15,200,000 [查看依据]         │
│     ...                                      │
│                                              │
│ ⚠ AI 标注: 应收账款增长38%，超出行业均值     │
│   "主因: 9月大额订单延迟回款，已记录"        │
└─────────────────────────────────────────────┘
```

**Key features** (Jobs):
- "变动高亮": auto-compare with last period, color-code >20% changes
- "查看依据": side panel showing source vouchers for each number
- Structured interactive report, NOT PDF iframe
- AI confidence score at top

## P2: Skills Sheet Design

**Component**: Right-side Sheet/Drawer on `/skills` page
**Width**: 400px
**Content**: Skill name + description + 3 recent execution records + "开通" button
**Scope**: ~50 lines, 0 new routes

## Dead Button Triage

**Add Toast feedback** to remaining dead buttons:
- "全部批准" → Toast: "已发起批量审批，预计2分钟完成"
- "批量导出" → Toast: "正在生成导出文件..."
- "新增客户" → Toast: "功能即将上线"
- "邀请成员" → Toast: "功能即将上线"
- All pagination → leave as visual-only (only 8-10 items shown)

**Remove**: /help from sidebar nav + bottomItems

## Shared Data Layer

Already prepared:
- `lib/agents.ts` — 7 agents, name→slug mapping
- `lib/clients.ts` — 8 clients, full entity with detail fields + activity records

Need to create:
- `lib/reports.ts` — 7 reports with detail fields (AI annotations, confidence, highlights)

## Implementation Order

```
Session 13:
  1. Remove /help from sidebar
  2. Build Notification Popover (P0)
  3. Build /clients/[id] page (P0)
  4. Build /reports/[id] page (P1)
  5. Add Toast feedback to dead buttons
  6. Build Skills Sheet (P2)
  7. Deploy + screenshot evidence
```

## Stitch Prototype

Before coding, create Stitch prototypes for:
1. Notification Popover (1 screen)
2. Client Detail page (2 screens: above fold + below fold)
3. Report Detail page (2 screens: overview + AI annotations)

Stitch project: use existing Lingque Office design system.
