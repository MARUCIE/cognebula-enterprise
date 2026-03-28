"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getStats, getQuality, type KGStats, type KGQuality } from "../lib/kg-api";
import { CN, cnCard, cnLabel, cnValue, cnBadge } from "../lib/cognebula-theme";

export default function ExpertDashboardPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getQuality()])
      .then(([s, q]) => { setStats(s); setQuality(q); })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "20px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: CN.text, marginBottom: 4 }}>
          System A Overview
        </h1>
        <p style={{ fontSize: 13, color: CN.textSecondary }}>
          CogNebula KG infrastructure health + pipeline monitoring
        </p>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: CN.redBg, border: `1px solid ${CN.red}`, color: CN.red, fontSize: 13, marginBottom: 20 }}>
          KG API connection failed: {error}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1px", background: CN.border, marginBottom: 24 }}>
        <div style={cnCard}>
          <div style={cnLabel}>Total Nodes</div>
          <div style={cnValue(CN.blue)}>{stats ? (stats.total_nodes || 0).toLocaleString() : "..."}</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>KuzuDB + LanceDB</div>
        </div>
        <div style={cnCard}>
          <div style={cnLabel}>Total Edges</div>
          <div style={cnValue(CN.blue)}>{stats ? (stats.total_edges || 0).toLocaleString() : "..."}</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>Relationship graph</div>
        </div>
        <div style={cnCard}>
          <div style={cnLabel}>Edge Density</div>
          <div style={cnValue(CN.purple)}>{stats ? (stats.total_nodes > 0 ? (stats.total_edges / stats.total_nodes).toFixed(3) : "0") : "..."}</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>edges / nodes</div>
        </div>
        <div style={cnCard}>
          <div style={cnLabel}>Quality Score</div>
          <div style={cnValue(quality && quality.quality_score >= 80 ? CN.green : CN.amber)}>
            {quality ? `${(quality.quality_score || 0).toFixed(1)}%` : "..."}
          </div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>Composite quality</div>
        </div>
      </div>

      {/* Quick Access Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 24 }}>
        <QuickCard href="/expert/kg" title="KG Explorer" desc="Interactive graph visualization with Cytoscape.js fcose layout. Search, expand neighbors, layered coloring." tag="CORE TOOL" tagColor={CN.blue} />
        <QuickCard href="/expert/data-quality" title="Data Quality Dashboard" desc="Real-time monitoring of title coverage, content coverage, node type distribution. Connected to KG API /quality." tag="MONITORING" tagColor={CN.green} />
        <QuickCard href="/expert/reasoning" title="Reasoning Inspector" desc="Agent reasoning process visualization. Shows INPUT > RETRIEVAL > REASONING > VALIDATION > OUTPUT confidence per stage." tag="DIAGNOSTIC" tagColor={CN.purple} />
        <QuickCard href="/expert/rules" title="Rules Debugger" desc="8 compliance rules status monitoring (active/warning/critical/deprecated), hit counts, recent trigger log." tag="DIAGNOSTIC" tagColor={CN.purple} />
      </div>

      {/* System Status */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 11, fontWeight: 700, color: CN.blue, letterSpacing: "2px", marginBottom: 12 }}>
          SYSTEM STATUS
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1px", background: CN.border }}>
          <StatusRow label="KG API (FastAPI :8400)" status="ok" detail="100.75.77.112 via Tailscale" />
          <StatusRow label="KuzuDB" status="warn" detail="Archived -- evaluate migration by 2026-09" />
          <StatusRow label="LanceDB (Vectors)" status="ok" detail="Semantic search operational" />
          <StatusRow label="Know-Arc Pipeline" status="ok" detail="Triple generation + expert review" />
          <StatusRow label="Edge Engine" status="ok" detail="SUPERSEDES edges, 107 last run" />
          <StatusRow label="CF Worker Proxy" status="pending" detail="Not yet deployed" />
        </div>
      </div>

      {/* Cross-System Link */}
      <div style={{ ...cnCard, borderLeft: `3px solid ${CN.blue}` }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: CN.blue, letterSpacing: "1.5px", marginBottom: 6 }}>
          ARCHITECTURE NOTE
        </div>
        <div style={{ fontSize: 13, color: CN.textSecondary, lineHeight: 1.7 }}>
          System A (CogNebula) is internal infrastructure only. KG serves System B (Lingque) agents via CF Worker proxy as an invisible knowledge query layer.
          Customers see &quot;high accuracy&quot;, not &quot;knowledge graph&quot;.
        </div>
        <Link href="/expert/bridge" style={{ display: "inline-block", marginTop: 12, padding: "6px 16px", background: CN.blueBg, color: CN.blue, textDecoration: "none", fontSize: 12, fontWeight: 600, border: `1px solid ${CN.border}` }}>
          View System Bridge &rarr;
        </Link>
      </div>
    </div>
  );
}

function QuickCard({ href, title, desc, tag, tagColor }: { href: string; title: string; desc: string; tag: string; tagColor: string }) {
  return (
    <Link href={href} style={{ textDecoration: "none" }}>
      <div style={{
        ...cnCard, borderTop: `2px solid ${tagColor}`,
        transition: "border-color 0.15s",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: CN.text }}>{title}</span>
          <span style={cnBadge(tagColor, `${tagColor}20`)}>{tag}</span>
        </div>
        <div style={{ fontSize: 12, color: CN.textSecondary, lineHeight: 1.6 }}>{desc}</div>
      </div>
    </Link>
  );
}

function StatusRow({ label, status, detail }: { label: string; status: "ok" | "warn" | "pending" | "error"; detail: string }) {
  const colors = { ok: CN.green, warn: CN.amber, pending: CN.textMuted, error: CN.red };
  const bgs = { ok: CN.greenBg, warn: CN.amberBg, pending: CN.bgElevated, error: CN.redBg };
  const labels = { ok: "ONLINE", warn: "WARNING", pending: "PENDING", error: "ERROR" };
  return (
    <div style={{ padding: "12px 16px", background: CN.bg, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: CN.text }}>{label}</div>
        <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 2 }}>{detail}</div>
      </div>
      <span style={cnBadge(colors[status], bgs[status])}>{labels[status]}</span>
    </div>
  );
}
