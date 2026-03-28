/* CogNebula Dark — GitHub-Inspired Dark Theme Tokens
   Used exclusively by System A (Expert/CogNebula) pages.
   System B (Lingque) uses Heritage Monolith tokens from globals.css. */

export const CN = {
  // Backgrounds
  bg: "#0D1117",
  bgCard: "#161B22",
  bgElevated: "#21262D",

  // Borders
  border: "#30363D",
  borderFocus: "#58A6FF",

  // Text
  text: "#E6EDF3",
  textSecondary: "#8B949E",
  textMuted: "#484F58",

  // Accent
  blue: "#58A6FF",
  blueBg: "rgba(88,166,255,0.1)",
  green: "#3FB950",
  greenBg: "rgba(63,185,80,0.1)",
  amber: "#D29922",
  amberBg: "rgba(210,153,34,0.1)",
  red: "#F85149",
  redBg: "rgba(248,81,73,0.1)",
  purple: "#D2A8FF",
  purpleBg: "rgba(210,168,255,0.1)",
} as const;

/* Shared inline style helpers */
export const cnCard: React.CSSProperties = {
  background: CN.bgCard,
  border: `1px solid ${CN.border}`,
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
  color,
  background: bg,
  letterSpacing: "0.5px",
});

export const cnInput: React.CSSProperties = {
  padding: "7px 14px",
  border: `1px solid ${CN.border}`,
  background: CN.bgElevated,
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
  cursor: "pointer",
};

export const cnBtnPrimary: React.CSSProperties = {
  padding: "7px 18px",
  background: CN.blue,
  color: "#FFFFFF",
  fontSize: 13,
  fontWeight: 600,
  border: "none",
  cursor: "pointer",
};
