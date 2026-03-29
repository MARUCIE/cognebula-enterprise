/* CogNebula Light — Developer Tool Aesthetic
   System A uses cool-white + slate-blue to distinguish from
   System B's warm-cream Heritage Monolith theme.
   Graph canvas stays dark (#0D1117) — standard for network visualization. */

export const CN = {
  // Backgrounds
  bg: "#FFFFFF",
  bgCard: "#F8FAFC",
  bgElevated: "#F1F5F9",
  bgSidebar: "#1E293B",
  bgTopbar: "#FFFFFF",
  bgCanvas: "#0D1117", // graph canvas stays dark

  // Borders
  border: "#E2E8F0",
  borderStrong: "#CBD5E1",
  borderFocus: "#2563EB",

  // Text
  text: "#0F172A",
  textSecondary: "#475569",
  textMuted: "#94A3B8",
  textOnDark: "#E2E8F0",    // for sidebar/canvas text
  textOnDarkMuted: "#94A3B8",

  // Accent (technical blue — distinguishes from Heritage navy #003A70)
  blue: "#2563EB",
  blueBg: "rgba(37,99,235,0.08)",
  blueLight: "#DBEAFE",
  green: "#16A34A",
  greenBg: "rgba(22,163,74,0.08)",
  amber: "#D97706",
  amberBg: "rgba(217,119,6,0.08)",
  red: "#DC2626",
  redBg: "rgba(220,38,38,0.08)",
  purple: "#7C3AED",
  purpleBg: "rgba(124,58,237,0.08)",
} as const;

/* Shared inline style helpers */
export const cnCard: React.CSSProperties = {
  background: CN.bgCard,
  border: `1px solid ${CN.border}`,
  borderRadius: 6,
  padding: "16px 20px",
};

export const cnLabel: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  color: CN.textMuted,
  textTransform: "uppercase",
  letterSpacing: "1.5px",
};

export const cnValue = (color: string = CN.blue): React.CSSProperties => ({
  fontSize: "1.4rem",
  fontWeight: 800,
  color,
  lineHeight: 1.2,
  fontVariantNumeric: "tabular-nums",
});

export const cnBadge = (color: string, bg: string): React.CSSProperties => ({
  fontSize: 10,
  fontWeight: 700,
  padding: "2px 8px",
  borderRadius: 4,
  color,
  background: bg,
  letterSpacing: "0.5px",
});

export const cnInput: React.CSSProperties = {
  padding: "7px 14px",
  border: `1px solid ${CN.border}`,
  borderRadius: 6,
  background: CN.bg,
  color: CN.text,
  fontSize: 13,
  outline: "none",
};

export const cnBtn: React.CSSProperties = {
  padding: "7px 14px",
  background: CN.bgElevated,
  color: CN.textSecondary,
  fontSize: 12,
  fontWeight: 500,
  border: `1px solid ${CN.border}`,
  borderRadius: 6,
  cursor: "pointer",
};

export const cnBtnPrimary: React.CSSProperties = {
  padding: "7px 18px",
  background: CN.blue,
  color: "#FFFFFF",
  fontSize: 13,
  fontWeight: 600,
  border: "none",
  borderRadius: 6,
  cursor: "pointer",
};
