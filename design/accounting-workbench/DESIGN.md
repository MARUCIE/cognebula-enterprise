# Accounting Workbench Design Specification

> Design System: Heritage Monolith ("The Architectural Ledger")
> Target Page: `/workbench/accounting`
> Parent App: Lingque Desktop (灵阙财税)
> Date: 2026-03-31

## 1. Page Purpose

Core accounting workbench where bookkeepers upload invoices and review AI-generated journal entries. This is the **production workspace** — not a dashboard. Every interaction leads to a posted journal entry or a flagged exception.

Pipeline: Upload Invoice → Parse → Classify → Generate Entry → Validate → Approve → Post

## 2. Design System Constraints (Heritage Monolith)

| Rule | Implementation |
|------|----------------|
| Zero-Radius | All `border-radius: 0px` |
| Zero-Shadow | Depth via tonal layering only |
| No-Line Rule | No 1px borders for sectioning; use `surface` → `surface-container-low` color shifts |
| Ghost Border | `outline-variant` at 15% opacity, only in high-density data views |
| Gold = Value | `#C5913E` only for totals, approved items, savings |
| Typography | Manrope (display/heading), Inter (body/data), tabular-nums for amounts |
| Input Fields | Bottom-line only, 2px primary bottom border on focus |
| Zebra Striping | Alternating `surface` / `surface-container-low` for table rows |
| CJK Typography | `word-break: keep-all`, `text-wrap: balance` for headings |

## 3. Color Palette (Inherited)

```
Primary:     #003A70 (Heritage Blue)
Primary Deep: #00244A
Gold Accent:  #C5913E (value moments only)
Surface:      #F9F9F7 (base)
Container Low: #F4F4F2 (inlay)
Container:    #EEEEEC (secondary)
White:        #FFFFFF (focus/data entry)
Text Primary: #1D1B19
Text Secondary: #434750
Text Tertiary: #6B7280
Success:      #1B7A4E
Warning:      #C5913E
Danger:       #C44536
```

## 4. Page Layout (Top → Bottom)

### 4.0 Page Header Strip
- Left: Breadcrumb `WORKBENCH / ACCOUNTING` (11px, uppercase, tracking 2px, primary color)
- Left below: `核算工作台` (1.5rem, 800 weight)
- Right: Action buttons row:
  - `导入发票` (gradient CTA button, primary fill)
  - `本月汇总` (secondary, surface-container fill)
  - `科目表` (secondary)
  - `凭证模板` (secondary)
- Background: `surface`, bottom border via color shift to `surface-container`

### 4.1 Pipeline Status Bar
Full-width strip showing current batch processing status.
- Background: `surface-container-lowest` (#FFFFFF)
- 5-step pipeline: 解析 → 分类 → 生成 → 校验 → 审核
- Each step: icon + label + count badge
- Active step: primary color fill, white text
- Completed steps: success color tick
- Pending steps: text-tertiary, dashed underline
- Progress text: `本批次: 12/20 张发票  |  预计剩余: ~30s`
- Compact height: 56px

### 4.2 Main Content Area (Two-Column Layout)

**Left Column (60%)**: Invoice List + Detail
**Right Column (40%)**: Journal Entry Preview + Validation

#### 4.2.1 Left: Invoice Queue Table

Header row:
- Background: `surface-container-low`
- Columns: `状态` (60px) | `发票号码` (140px) | `购方/销方` (1fr) | `金额` (100px) | `税额` (80px) | `价税合计` (100px)
- Font: 11px, uppercase, 700 weight, text-secondary

Data rows:
- Zebra striping: alternating `#FFFFFF` / `surface`
- Selected row: `primary-fixed` (#D5E3FF) background
- Status column: colored dot (green=posted, blue=processing, amber=review, gray=queued)
- Amount columns: `tabular-nums`, right-aligned
- Row height: 48px
- Click to select → loads detail in right panel

Below table: Upload Drop Zone
- Dashed border (ghost-border opacity): `outline-variant` at 30%
- Icon: upload cloud (24px, text-tertiary)
- Text: `拖拽发票文件到此处，或点击选择` (13px, text-secondary)
- Subtext: `支持 Excel / PDF / 图片，可批量上传` (11px, text-tertiary)
- Height: 80px
- Background: `surface-container-low`
- Hover: background shift to `surface-container`

#### 4.2.2 Right: Journal Entry Preview Panel

Title bar:
- `凭证预览` (14px, 700 weight) + `记-1` badge (gold background, dark gold text)
- Status chip: `已校验` / `待审核` / `异常` (reverse-tonal style per Heritage Monolith)

Entry metadata:
- Row: `日期: 2026-01-31` | `附件: 1张` | `规则: JR001`
- Font: 12px, text-secondary
- Background: `surface-container-low`, padding var(--space-4)

Journal lines table (the core "ledger" view):
- Header: `摘要 / 科目编码 / 科目名称 / 借方 / 贷方`
- Summary row spans full width: `销售软饮料和方便食品` (13px, 600 weight)
- Debit lines: amount in `借方` column, `贷方` empty
- Credit lines: amount in `贷方` column, `借方` empty
- Total row: gold background (#FDF6EB), bold amounts, verify `借方合计 = 贷方合计`
- Balance indicator: green checkmark if balanced, red X if not
- All amounts: `tabular-nums`, right-aligned, 14px

Action buttons:
- `通过` (success gradient: #1B7A4E → slightly lighter)
- `修改` (secondary fill)
- `拒绝` (text-only, danger color)
- Layout: left-aligned button row, var(--space-3) gap

#### 4.2.3 Right Below: Validation & Warnings Panel

- Background: `surface`
- Section title: `校验结果` (13px, 600 weight)
- Warning items: icon (amber triangle) + text + rule reference
  - Example: `WARN: 科目 1122005 未在客户科目表中注册`
  - Example: `NOTE: 适用小企业会计准则第59条`
- Icon colors: warning=#C5913E, info=#003A70, error=#C44536
- Font: 12px, line-height 1.75

### 4.3 Bottom: Batch Summary Strip

Full-width, background: `primary-deep` (#00244A)
- 4 data points in a row, white text:
  - `本月发票: 45张` | `生成凭证: 42笔` | `借方合计: ¥1,234,567.89` | `贷方合计: ¥1,234,567.89`
- Gold accent for monetary totals (var(--color-secondary))
- Compact: 48px height
- Font: 13px, Inter, tabular-nums for amounts

## 5. Interaction States

### 5.1 Empty State (No Invoices)
- Full-width upload zone, centered
- Illustration: simplified invoice stack icon (line art, primary color)
- Title: `开始批量核算` (1.25rem, 700)
- Subtitle: `上传发票 Excel 或扫描件，AI 自动生成记账凭证` (13px, text-secondary)
- CTA: `导入发票` (gradient primary button)

### 5.2 Processing State
- Pipeline bar animates: active step pulses gently
- Invoice list shows processing spinner on active row
- Right panel shows skeleton loading for journal entry

### 5.3 Exception State
- Row background: `color-mix(in srgb, var(--color-danger) 8%, transparent)`
- Right panel: validation warnings expanded, action buttons emphasize `修改`
- Badge: `需人工审核` in danger reverse-tonal chip

## 6. Responsive Behavior

- Minimum width: 1280px (enterprise desktop app, not mobile)
- At 1280px: left column 55%, right column 45%
- At 1920px+: left column 60%, right column 40%
- Table columns compress amounts first, then truncate company names

## 7. Component Inventory

| Component | Variant | Heritage Monolith Rule |
|-----------|---------|----------------------|
| PipelineSteps | 5-step horizontal | No borders between steps, tonal shift |
| InvoiceTable | zebra, selectable | No row dividers, bg color alternation |
| JournalEntryCard | readonly, editable | White bg on surface, ghost border |
| ValidationAlert | warn, info, error | Icon + text, no box decoration |
| UploadZone | empty, hover, dragging | Ghost border (30% outline-variant) |
| AmountCell | debit, credit, total | tabular-nums, right-aligned |
| StatusDot | queued, processing, review, posted | 8px circle, colored |
| BatchSummary | dark strip | primary-deep bg, gold amounts |
| ActionButton | approve, edit, reject | success/secondary/danger-text |

---

Maurice | maurice_wen@proton.me
