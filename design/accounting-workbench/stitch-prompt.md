# Stitch Prompt — 核算工作台 (Accounting Workbench)

> Copy this prompt into Stitch to generate the prototype.
> Design system: Heritage Monolith. Project: Lingque Desktop (灵阙财税).

---

A precision enterprise accounting workbench for a Chinese AI-staffed bookkeeping firm. This is a dense, data-heavy production workspace — not a marketing page. The visual language is "high-end banking terminal meets traditional Chinese double-entry ledger." Every element is sharp, intentional, and built for efficiency. All text in Chinese (zh-CN). Desktop-only (minimum 1440px wide).

**DESIGN SYSTEM (REQUIRED) — "Heritage Monolith: The Architectural Ledger":**
- Platform: Web, Desktop-first, 1440px+ viewport
- Theme: Light, zero-radius (all corners 0px), zero-shadow (no box-shadow anywhere)
- Depth: Achieved ONLY through background color shifts (tonal layering), never shadows or borders
- RULE: No 1px solid borders for sectioning. Boundaries defined by background color changes.
- Background Base: Warm Cream (#F9F9F7) for page background
- Surface Inlay: Warm Stone (#F4F4F2) for secondary panels, table headers, metadata rows
- Surface Secondary: Soft Putty (#EEEEEC) for divider areas and nested sections
- Surface Focus: Pure White (#FFFFFF) for primary data entry cards and active panels
- Primary Accent: Heritage Blue (#003A70) for active states, links, breadcrumbs, pipeline active step
- Primary Deep: Midnight Navy (#00244A) for bottom summary bar background and gradient CTA buttons
- Gold Accent: Antique Gold (#C5913E) — used ONLY for monetary totals, balanced confirmations, and approved status. Never decorative.
- Text Primary: Deep Ink (#1D1B19) for headings and key data
- Text Secondary: Slate (#434750) for body text and descriptions
- Text Tertiary: Medium Gray (#6B7280) for labels, timestamps, disabled states
- Success: Forest Green (#1B7A4E) for completed steps, approved entries, balance confirmation
- Warning: Amber (#C5913E) for validation warnings, items needing attention
- Danger: Brick Red (#C44536) for errors, rejected entries, failed validation
- Selected Row: Pale Blue (#D5E3FF) for active/selected invoice row highlight
- Gold Tint Background: Warm Parchment (#FDF6EB) for total rows and value-moment areas
- Heading Font: Manrope, weight 500–800, for page titles and section headers
- Body/Data Font: Inter, weight 400–600, for all data, labels, and table content
- Financial Numbers: font-variant-numeric: tabular-nums lining-nums; always right-aligned
- Buttons Primary: Linear gradient 135° from #00244A to #003A70 (die-cast metallic feel), white text, 0px radius
- Buttons Secondary: #EEEEEC fill, dark text, 0px radius, no border
- Input Fields: Bottom-line only style (2px bottom border in primary color on focus), no box outline
- Sidebar: Present but NOT part of this screen (assume 240px dark navy sidebar exists to the left)

**Page Structure (content area only, right of sidebar):**

1. **Page Header** — Full width, #F9F9F7 background, padding 24px 32px
   - Top-left: Breadcrumb text "WORKBENCH / ACCOUNTING" in 11px, uppercase, letter-spacing 2px, Heritage Blue (#003A70), font-weight 700
   - Below breadcrumb: Page title "核算工作台" in Manrope 1.5rem, font-weight 800, Deep Ink color
   - Top-right: Row of 4 buttons aligned right
     - "导入发票" — primary gradient CTA button (dark navy to heritage blue gradient), white text, bold, with small upload icon
     - "本月汇总" — secondary button, #EEEEEC fill, dark text
     - "科目表" — secondary button
     - "凭证模板" — secondary button
   - Bottom edge: visual separation via color shift to next section (no border line)

2. **Pipeline Status Bar** — Full width, 56px height, Pure White (#FFFFFF) background
   - Horizontal 5-step progress indicator, evenly spaced:
     - Step 1: "① 解析" — green checkmark icon, Forest Green text, completed
     - Step 2: "② 分类" — green checkmark icon, Forest Green text, completed
     - Step 3: "③ 生成" — Heritage Blue (#003A70) filled rectangle background with white text, ACTIVE step (pulsing gently)
     - Step 4: "④ 校验" — gray text (#6B7280), pending
     - Step 5: "⑤ 审核" — gray text (#6B7280), pending
   - Right side of bar: "本批次: 12/20 张发票 | 预计剩余: ~30s" in 12px Inter, Slate color
   - Steps connected by thin lines between them (gray for pending, green for completed, blue for active-to-next)

3. **Two-Column Main Content** — 60% left / 40% right split, no gap (separated by tonal shift)

   **LEFT COLUMN (60%) — Invoice Queue:**
   - Table header row: #F4F4F2 background, 11px Inter UPPERCASE font-weight 700, Slate color, letter-spacing 1px
     - Columns: "状态" (60px) | "发票号码" (140px) | "购方 / 销方" (flexible) | "金额" (100px) | "税额" (80px) | "价税合计" (110px)
   - 8 data rows with zebra striping (alternating Pure White #FFFFFF and Warm Cream #F9F9F7):
     - Row 1 (selected, Pale Blue #D5E3FF background): green dot, "01234567", "四川聚清诚建设→成都市朋诚鑫盛", "¥41,283.19", "¥5,366.81", "¥46,650.00"
     - Row 2: green dot, "01234568", "简阳丰印象广告→联合创新贸易", "¥8,490.57", "¥509.43", "¥9,000.00"
     - Row 3: blue processing dot, "01234569", "中唯耘源建设→四川省永绘企业", "¥4,906.43", "¥637.83", "¥5,544.26"
     - Row 4: blue processing dot, "01234570", "成都朋诚鑫盛→恒升投资管理", "¥12,831.86", "¥1,668.14", "¥14,500.00"
     - Row 5: amber dot, "01234571", "简阳丰印象→时代传媒有限", "¥2,654.87", "¥345.13", "¥3,000.00"
     - Row 6: gray dot, "01234572", "中唯耘源建设→大唐信息技术", "¥18,584.07", "¥2,415.93", "¥21,000.00"
     - Row 7: gray dot, "01234573", "成都朋诚鑫盛→鑫海物流集团", "¥7,079.65", "¥920.35", "¥8,000.00"
     - Row 8: gray dot, "01234574", "四川聚清诚建设→云峰智源股份", "¥31,415.93", "¥4,084.07", "¥35,500.00"
   - All amount columns: tabular-nums, right-aligned, 13px Inter
   - Row height: 48px, vertical center aligned
   - Status dots: 8px circles (green=#1B7A4E, blue=#003A70, amber=#C5913E, gray=#6B7280)

   - **Upload Drop Zone** below the table:
     - Height 80px, #F4F4F2 background
     - Dashed border: 1px dashed rgba(195, 198, 209, 0.3) — the only permitted "border" (ghost border exception for drop zones)
     - Centered: cloud upload line icon (24px, gray) + "拖拽发票文件到此处，或点击选择" (13px, Slate) + "支持 Excel / PDF / 图片，可批量上传" (11px, gray)

   **RIGHT COLUMN (40%) — Journal Entry Preview:**
   - Background: Pure White (#FFFFFF), sitting against #F9F9F7 base (tonal elevation)

   - **Title bar**: Padding 16px 20px
     - Left: "凭证预览" in 14px Manrope font-weight 700
     - Right: "记-1" badge with Warm Parchment (#FDF6EB) background and Dark Gold (#815600) text, 10px padding. Next to it: "已校验" chip with pale green background (10% #1B7A4E) and Forest Green text

   - **Metadata strip**: #F4F4F2 background, padding 10px 20px, 12px Inter
     - "日期: 2026-01-31" | "附件: 1张" | "规则: JR001" separated by vertical pipes, Slate color

   - **Journal Entry Ledger Table** (the heart of the page):
     - Summary row spanning full width: "销售软饮料和方便食品" in 13px Inter font-weight 600, Deep Ink, padding 12px 20px, #F4F4F2 background
     - Column headers: "科目编码" | "科目名称" | "借方" | "贷方" in 11px UPPERCASE, Slate, #F4F4F2 background
     - Line 1 (debit): "1122005" | "应收账款_四川省永绘企业管理有限公司" | "5,544.26" | "" — on white background
     - Line 2 (credit): "5001001" | "主营业务收入_销售收入" | "" | "4,906.43" — on #F9F9F7 background
     - Line 3 (credit): "222100106" | "应交税费_应交增值税_销项税额" | "" | "637.83" — on white background
     - **Total row**: Warm Parchment (#FDF6EB) background, bold 14px amounts
       - "合计" | "" | "5,544.26" | "5,544.26" with green checkmark icon indicating "借贷平衡"
       - Amounts in Antique Gold (#C5913E) color — this is a "value moment"

   - **Action Buttons**: Row below table, padding 16px 20px
     - "通过" — Forest Green filled button (#1B7A4E), white text, 0px radius
     - "修改" — #EEEEEC filled button, dark text
     - "拒绝" — text-only button in Brick Red (#C44536), no fill
     - Buttons spaced 12px apart, left-aligned

   - **Validation & Warnings Panel**: Below action buttons, #F9F9F7 background, padding 16px 20px
     - Section title: "校验结果" in 13px font-weight 600
     - Warning item: amber triangle icon + "WARN: 科目 1122005 未在客户科目表中注册" in 12px, line-height 1.75
     - Info item: Heritage Blue circle-i icon + "NOTE: 适用小企业会计准则第59条" in 12px, line-height 1.75
     - Each item has 8px gap between icon and text, 12px vertical spacing between items

4. **Bottom Summary Strip** — Full width, 48px height, Midnight Navy (#00244A) background
   - 4 metrics evenly spaced in a horizontal row, centered vertically:
     - "本月发票: 45张" — white text 13px
     - "生成凭证: 42笔" — white text 13px
     - "借方合计: ¥1,234,567.89" — label white, amount in Antique Gold (#C5913E), tabular-nums
     - "贷方合计: ¥1,234,567.89" — label white, amount in Antique Gold (#C5913E), tabular-nums
   - Separated by subtle vertical dividers (rgba(255,255,255,0.1))

**Critical Constraints:**
- ZERO rounded corners anywhere. Every element is sharp-edged (0px border-radius).
- ZERO box-shadows. Depth comes only from background color differences.
- NO 1px solid lines between sections — only tonal (background color) shifts.
- All Chinese text. All amounts in ¥ with proper thousands separators.
- The overall feel should be a precision financial instrument, not a consumer app.
