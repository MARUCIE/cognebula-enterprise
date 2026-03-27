/* Ops layout -- Bloomberg Ops density wrapper.
   Applies compact spacing without affecting customer-facing pages. */

export default function OpsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="ops-density"
      style={{
        /* Counteract parent's generous padding, apply ops-tight padding */
        margin: "calc(-1 * var(--space-6)) calc(-1 * var(--space-8))",
        padding: "var(--space-4) var(--space-6)",
        minHeight: "100%",
      }}
    >
      {children}
    </div>
  );
}
