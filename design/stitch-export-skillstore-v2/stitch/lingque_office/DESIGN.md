# Design System Document: Precision & Prestige

## 1. Overview & Creative North Star
**The Creative North Star: "The Digital Registrar"**
This design system moves beyond the cold, sterile nature of traditional fintech to embrace the warmth of a high-end, AI-staffed accounting firm. The aesthetic is "Editorial Professionalism"—borrowing the layout logic of luxury financial broadsheets and the tactile quality of premium stationery. 

We break the "template" look by rejecting rigid, boxed-in grids. Instead, we use **Intentional Asymmetry** and **Tonal Depth**. Large, authoritative typography meets generous white space, creating a sense of calm reliability. The interface does not "shout" with borders; it "whispers" through layered surfaces and sophisticated color shifts.

---

## 2. Color Strategy: The Tonal Architecture
We utilize a sophisticated palette where the background isn't just "white," but a textured parchment base (`surface: #f9f9f7`).

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders for sectioning or layout containment. Structural boundaries must be defined solely through background color shifts. 
*   Place a `surface-container-low (#f4f4f2)` section directly against a `surface (#f9f9f7)` background to define a sidebar. 
*   Use `surface-container (#eeeeec)` for inner content areas. 
*   Lines create visual noise; tonal shifts create focus.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. 
1.  **Base Layer:** `surface` (#f9f9f7) – The desk.
2.  **Section Layer:** `surface-container-low` (#f4f4f2) – The folder.
3.  **Action Layer:** `surface-container-lowest` (#ffffff) – The active document.

### The "Glass & Gold" Signature
Use the Accent Gold (`secondary: #815600`) sparingly for high-value status indicators or signature "verification" marks. To move beyond a generic feel, utilize **Glassmorphism** for floating AI modals:
*   **Fill:** `surface_container_lowest` at 85% opacity.
*   **Effect:** `backdrop-blur: 20px`.
*   **Accent:** A subtle top-to-bottom gradient from `primary` (#00244a) to `primary_container` (#003a70) for primary CTAs.

---

## 3. Typography: The Editorial Voice
We use a high-contrast scale to mirror professional financial reports.

*   **Display & Headlines (Manrope):** These are our "Statement" fonts. `display-lg` (3.5rem) should be used for high-level data summaries. The font choice is architectural and confident.
*   **Titles & Body (Inter):** This is our "Functional" font. It provides maximum legibility for complex ledger data.
*   **Hierarchy as Authority:** Use `title-lg` (#1d1b19) for section headers and `label-sm` (#434750) for metadata. The gap between title and body sizes should be pronounced to create clear entry points for the eye.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are too "software-heavy." We use **Ambient Depth**.

*   **The Layering Principle:** Depth is achieved by "stacking." A card (`surface-container-lowest`) placed on a section (`surface-container-low`) creates a natural lift without a single pixel of shadow.
*   **Ambient Shadows:** For floating elements (e.g., AI chat bubbles), use a shadow color tinted with the primary blue: `rgba(0, 36, 74, 0.06)` with a 40px blur.
*   **The Ghost Border Fallback:** If a border is required for accessibility, use `outline-variant` (#c3c6d1) at **15% opacity**. Anything higher is prohibited.

---

## 5. Components: Defined for Excellence

### Sophisticated Data Tables (数据表格)
*   **Structure:** No vertical or horizontal lines. 
*   **Separation:** Use `surface-container-low` for the header row and alternating `surface` and `surface-container-lowest` for body rows.
*   **Alignment:** Numbers must be tabular-lining and right-aligned for financial comparison.

### AI Status Indicators (AI 状态指示灯)
*   **Active:** A subtle "breathing" glow using `primary_fixed` (#d5e3ff).
*   **Processing:** A 2px height-animated bar at the top of the container, using a gradient of `secondary` (#815600) to `primary` (#00244a).

### Professional Sidebar (侧边栏)
*   **Background:** `surface-container-low` (#f4f4f2).
*   **Active State:** No "highlight box." Instead, use a 4px vertical "pillar" of `secondary` (#815600) on the left of the active label.

### Buttons (按钮)
*   **Primary (主要):** Gradient from `primary` to `primary_container`. Text in `on_primary` (#ffffff).
*   **Secondary (次要):** Transparent background with a "Ghost Border" and `primary` text.
*   **Ghost (幽灵):** No border, `primary` text. Only shows a `surface-variant` background on hover.

### Input Fields (输入框)
*   **Style:** Minimalist. Only a bottom border (2px) of `outline_variant`. On focus, the border transitions to `primary` and the background shifts to `surface_container_lowest`.
*   **Label:** `label-md` (#434750) positioned above the input.

---

## 6. Do’s and Don’ts

### Do (务必做到)
*   **Use breathing room:** Utilize `spacing-12` (3rem) or `spacing-16` (4rem) between major sections.
*   **Embrace Chinese Typography:** Ensure line heights for Chinese characters are 1.5x to 1.8x the font size to maintain "airiness."
*   **Contextual Gold:** Use Gold (`#C5913E`) only for "Value" (Tax savings, premium status, verified audits).

### Don't (禁止行为)
*   **No 1px Dividers:** Never use a solid line to separate two pieces of content. Use whitespace or a subtle background color change.
*   **No Pure Grey Shadows:** Shadows must always be tinted with a hint of the brand blue to avoid looking "dirty."
*   **No Rounded Edges > 8px:** Keep the `DEFAULT` (0.25rem) or `md` (0.375rem) for a sharp, professional look. Avoid "bubble" UI.

---

## 7. Token Reference Summary

| Token Type | Value | Usage |
| :--- | :--- | :--- |
| **Primary Base** | #003A70 | Primary Brand Identity |
| **Accent Gold** | #C5913E | Professionalism, Verification, Value |
| **Main Text** | #1D1B19 | High-contrast readability |
| **Surface Base** | #F9F9F7 | The "Paper" background |
| **Elevation Low**| #F4F4F2 | Sidebar & Sectioning |
| **Elevation High**| #FFFFFF | Cards & Active Inputs |