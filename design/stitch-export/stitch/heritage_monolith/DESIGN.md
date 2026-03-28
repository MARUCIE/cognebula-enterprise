# Design System Strategy: The Architectural Ledger

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Architectural Ledger."** 

Moving away from the generic "bubble" aesthetics of modern SaaS, this system embraces the precision of traditional Chinese book-keeping and the authoritative weight of heritage banking. By utilizing a **Zero-Radius, Zero-Shadow** framework, we create a digital environment that feels constructed rather than rendered. 

We break the "template" look through **Intentional Asymmetry** and **Tonal Layering**. The design rejects the "boxed-in" feel of standard grids, opting instead for an editorial layout where white space acts as a structural element. The lack of rounded corners communicates a "No-Nonsense" efficiency—every pixel is intentional, every edge is sharp, and every transaction is precise.

---

## 2. Colors: Tonal Architecture
The palette is rooted in *Heritage Blue* and *Gold*, evoking stability and prosperity. However, the sophistication lies in the neutral shifts.

### The "No-Line" Rule
**Prohibit 1px solid borders for sectioning.** To define boundaries, you must use background color shifts. 
- A `surface-container-low` (#f4f4f2) sidebar sitting against a `surface` (#f9f9f7) main stage provides all the definition a professional needs without the visual "noise" of a stroke.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like high-quality bond paper stacked on a desk.
- **Level 1 (Base):** `surface` (#f9f9f7)
- **Level 2 (Inlay):** `surface-container` (#eeeeec) for secondary modules.
- **Level 3 (Focus):** `surface-container-lowest` (#ffffff) for primary data entry cards.

### Signature Textures
Avoid flat, dead fills on large CTA areas. Use a subtle linear gradient (135°) from `primary` (#00244a) to `primary_container` (#003a70) to give action buttons a "die-cast" metallic depth that feels premium and tactile.

---

## 3. Typography: Editorial Authority
We pair **Inter** (for numeric precision) with **Noto Sans SC** (for legible, authoritative Chinese glyphs).

- **Display & Headline:** Used sparingly to anchor the page. These should feel like mastheads in a financial journal. High contrast between `display-lg` (3.5rem) and `body-md` (0.875rem) creates an "Editorial" hierarchy.
- **Title & Label:** These are the workhorses. Labels in `label-sm` (0.6875rem) should be used in All Caps or with wide letter-spacing (0.05rem) to denote categories, mimicking the headers of a ledger.
- **The Power of #1D1B19:** Use the primary text color for headers to provide a "Deep Ink" feel against the `Cream` background.

---

## 4. Elevation & Depth: The Sharp Edge
Since shadows and rounded corners are forbidden, depth is achieved through **Tonal Layering** and **Ghosting**.

### The Layering Principle
Depth is "stacked." To make a data table feel elevated, do not add a shadow. Instead, place the table on a `surface-container-lowest` (#ffffff) background and set the surrounding page to `surface-container-low` (#f4f4f2). The sharp change in hex code creates a "cut-out" effect.

### The "Ghost Border" Fallback
If visual separation is failing in high-density data views, use a "Ghost Border." Use the `outline_variant` (#c3c6d1) at **15% opacity**. It should be felt, not seen.

### Intentional Asymmetry
In hero sections or dashboards, align text to a strict left margin while allowing data visualizations to "bleed" or offset to the right. This breaks the rigid container feel and makes the software feel like a bespoke financial report.

---

## 5. Components: Precision Primitives

### Buttons (The "Monolith")
- **Style:** 0px radius. No shadows.
- **Primary:** Gradient fill (Primary to Primary-Container). Text: On-Primary (#ffffff).
- **Secondary:** Surface-container-highest fill (#e2e3e1). No border.
- **Tertiary:** Text-only in Gold (#815600) with a 2px bottom "underline" accent that only appears on hover.

### Input Fields
- **Style:** Never use 4-sided boxes. Use a "Bottom-Line Only" approach or a subtle `surface-container-high` (#e8e8e6) fill with a 2px `primary` bottom border on focus. This mimics the lines of a physical ledger.

### Cards & Lists
- **The Anti-Divider Rule:** Forbid 1px horizontal lines between list items. Use `spacing-4` (0.9rem) of vertical white space to separate items. If items must be grouped, use alternating row fills (Zebra striping) using `surface` and `surface-container-low`.

### Intelligent Ledger Chips
- Used for status (e.g., "Audited," "Pending"). Use a "Reverse-Tonal" style: A background of `secondary_fixed` (#ffddb1) with text in `on_secondary_container` (#785000). No borders.

---

## 6. Do's and Don'ts

### Do
- **Do** use `Gold` (#C5913E) strictly as an accent for "Value" moments (Total balances, "Approve" actions, or VIP status).
- **Do** utilize the spacing scale religiously. 0.9rem (`spacing-4`) is your baseline for all internal padding.
- **Do** align all icons to a strict 24px grid to maintain the "Architectural" feel.

### Don'ts
- **Don't** use a 1px border to separate the sidebar from the main content; use the shift from `surface-container` to `surface`.
- **Don't** use "Blue" for success messages. Use `Success` (#1B7F4B) but keep it grounded—no neon glows.
- **Don't** use any transparency on text. Use the specific `on_surface_variant` (#434750) for secondary information to maintain accessibility.
- **Don't** let any corner be anything other than a 90-degree angle. Precision is the brand.