# Design System Strategy: The Digital Atelier

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Atelier."** 

Unlike generic "SaaS-blue" financial tools, this system reimagines the AI-staffed accounting firm as a high-end, bespoke consulting suite. We are moving away from the "dashboard" aesthetic and toward a "digital editorial" experience. The interface should feel like a physical desk in a prestigious firm—structured, authoritative, and meticulously organized. 

We break the "template" look through **intentional asymmetry** and **tonal depth**. Instead of centering everything, we use generous whitespace (the "breathing room" of luxury) and overlapping elements to create a sense of architectural layers. The UI doesn't just display data; it curates it.

## 2. Colors & Surface Philosophy
The palette is rooted in heritage and stability. The interaction between the deep Primary Blue and the Accent Gold creates a "Prestige-First" hierarchy.

### The "No-Line" Rule
To achieve a high-end feel, **1px solid borders are strictly prohibited** for sectioning. Boundaries must be defined solely through background color shifts. For example, a `surface-container-low` (#f4f4f2) sidebar should sit against a `surface` (#f9f9f7) main canvas. This creates a "soft-edge" layout that feels organic rather than mechanical.

### Surface Hierarchy & Nesting
Treat the UI as a series of stacked, fine paper sheets.
- **Base Layer:** `surface` (#f9f9f7)
- **Content Blocks:** `surface-container-lowest` (#ffffff) for high-focus cards.
- **Recessed Areas:** `surface-container-high` (#e8e8e6) for utility panels or search bars.
By nesting these tones, we create "implied sections" without the clutter of lines.

### Signature Textures & Glass
- **The AI Presence:** For "AI-staffed" components (chat bots, automated insights), use **Glassmorphism**. Apply `surface_container_lowest` at 70% opacity with a `20px` backdrop-blur. This suggests the AI is a fluid, modern layer sitting atop the stable financial foundation.
- **CTA Soul:** Never use flat blue for primary actions. Use a subtle linear gradient from `primary` (#00244a) to `primary_container` (#003a70) at a 135° angle.

## 3. Typography: Editorial Authority
The typography uses a high-contrast scale to mimic financial broadsheets and premium reports.

- **Display & Headlines (Manrope):** Use `display-lg` to `headline-sm` for high-impact numbers and section titles. The geometric nature of Manrope feels modern and "AI-forward."
- **Body & Titles (Inter/Nicos-Sans):** For Chinese text, Nicos-Sans provides a professional, stable weight. `title-lg` should be used for document headers to convey authority.
- **Functional Labels:** `label-md` and `label-sm` must always use `on_surface_variant` (#434750) to ensure they feel like "metadata" rather than primary content.

## 4. Elevation & Depth: Tonal Layering
We reject heavy, muddy shadows. Elevation is a whisper, not a shout.

- **The Layering Principle:** Depth is achieved by stacking. A `surface-container-lowest` card placed on a `surface-container-low` background creates a natural lift.
- **Ambient Shadows:** When a floating element (like a modal or dropdown) is required, use a shadow with a 40px blur, 0% spread, and 6% opacity of `on_tertiary` (#1d1b19). It should feel like a soft shadow cast on cream paper.
- **The "Ghost Border" Fallback:** If a border is required for accessibility, use `outline_variant` at **15% opacity**. It should be barely visible, serving as a hint rather than a wall.

## 5. Components

### Buttons
- **Primary:** Gradient (`primary` to `primary_container`), white text, `rounded-md` (0.375rem). The slight gold accent (`secondary`) can be used for a 2px bottom "underline" on hover to signal prestige.
- **Secondary:** Transparent background with a `secondary` (#815600) text color. No border.
- **Tertiary:** `on_surface_variant` text, used for low-priority actions like "Cancel."

### Input Fields & Search
- **Styling:** Use `surface-container-low` as the field background. No border. Upon focus, the background shifts to `surface-container-lowest` with a subtle `secondary` (Gold) ghost-border (20% opacity).
- **Labels:** Floating labels using `label-md` style.

### Cards & Intelligence Modules
- **Rule:** **Forbid divider lines.** Use vertical whitespace (Spacing Scale `6` or `8`) to separate headers from body text. 
- **AI Insights:** Use a `surface-container-lowest` card with a 1px `secondary_fixed` (Gold) ghost-border to denote a "Premium AI" suggestion.

### Data Tables (The Ledger)
- Instead of rows separated by lines, use alternating background tints: `surface` and `surface-container-low`. 
- Header row should use `tertiary_fixed` (#e7e1de) with `label-md` uppercase text for a professional, "archival" feel.

## 6. Do's and Don'ts

### Do
- **Use Asymmetry:** Place important "At-a-glance" AI metrics in a larger, left-aligned container, with secondary actions tucked into a narrower right-hand column.
- **Embrace the Gold:** Use the `secondary` gold color sparingly—only for "Success" states, premium insights, or "Finalized" financial markers. It is a reward for the user.
- **Respect the Cream:** Ensure the `#FAFAF8` background remains the dominant "air" in the design. It prevents the deep blue from feeling heavy.

### Don't
- **Don't use pure black:** Never use #000000. Use `tertiary` (#262422) or `on_surface` (#1a1c1b) for text to maintain the "warm" high-end feel.
- **Don't use harsh corners:** Avoid `none` or `sm` rounding for main containers. Stick to `md` (0.375rem) or `lg` (0.5rem) to balance "Professional" with "Modern AI."
- **Don't use standard alerts:** Avoid bright neon reds/greens. Use the refined `error` (#ba1a1a) and `secondary` (Gold for success) to keep the palette sophisticated.