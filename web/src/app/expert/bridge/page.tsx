"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getStats, getQuality, type KGStats, type KGQuality } from "../../lib/kg-api";
import { CN, cnCard, cnLabel, cnValue, cnBadge } from "../../lib/cognebula-theme";

export default function SystemBridgePage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [quality, setQuality] = useState<KGQuality | null>(null);
  const [kgOk, setKgOk] = useState<boolean | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getQuality()])
      .then(([s, q]) => { setStats(s); setQuality(q); setKgOk(true); })
      .catch(() => setKgOk(false));
  }, []);

  return (
    <div style={{ padding: "20px 24px" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: CN.text, marginBottom: 4 }}>
          System Bridge
        </h1>
        <p style={{ fontSize: 13, color: CN.textSecondary }}>
          Cross-system navigation and data flow between CogNebula (A) and Lingque (B)
        </p>
      </div>

      {/* Split View: System A | Data Flow | System B */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 240px 1fr", gap: 0, marginBottom: 24 }}>
        {/* System A Card */}
        <div style={{ ...cnCard, borderTop: `3px solid ${CN.blue}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, background: CN.blueBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 18, fontWeight: 900, color: CN.blue }}>A</span>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: CN.blue }}>CogNebula</div>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>
                Internal KG Infrastructure
              </div>
            </div>
          </div>

          {/* KPI */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: CN.border, marginBottom: 16 }}>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>Nodes</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: CN.blue }}>{stats ? `${(stats.total_nodes / 1000).toFixed(0)}K` : "..."}</div>
            </div>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>Edges</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: CN.blue }}>{stats ? `${(stats.total_edges / 1000).toFixed(0)}K` : "..."}</div>
            </div>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>Quality</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: quality && (quality.quality_score || 0) >= 80 ? CN.green : CN.amber }}>
                {quality ? `${(quality.quality_score || 0).toFixed(1)}%` : "..."}
              </div>
            </div>
            <div style={{ padding: "10px 12px", background: CN.bg }}>
              <div style={{ ...cnLabel, fontSize: 9 }}>API</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: kgOk ? CN.green : kgOk === false ? CN.red : CN.textMuted }}>
                {kgOk === null ? "..." : kgOk ? "OK" : "DOWN"}
              </div>
            </div>
          </div>

          {/* Quick Nav */}
          <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 8 }}>
            TOOLS
          </div>
          {[
            { href: "/expert/kg", label: "KG Explorer", color: CN.blue },
            { href: "/expert/data-quality", label: "Data Quality", color: CN.green },
            { href: "/expert/reasoning", label: "Reasoning Inspector", color: CN.purple },
            { href: "/expert/rules", label: "Rules Debugger", color: CN.purple },
          ].map((item) => (
            <Link key={item.href} href={item.href} style={{
              display: "block", padding: "6px 10px", marginBottom: 2,
              color: CN.text, textDecoration: "none", fontSize: 12,
              background: "transparent", borderLeft: `2px solid ${item.color}`,
            }}>
              {item.label}
            </Link>
          ))}
        </div>

        {/* Center: Data Flow Arrows */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: "0 8px" }}>
          {/* A -> B */}
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: CN.blue, letterSpacing: "1px", marginBottom: 4 }}>KG QUERY API</div>
            <svg width="120" height="32" viewBox="0 0 120 32">
              <defs>
                <marker id="arrowR" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                  <path d="M0,0 L8,3 L0,6" fill={CN.blue} />
                </marker>
              </defs>
              <line x1="10" y1="16" x2="100" y2="16" stroke={CN.blue} strokeWidth="2" markerEnd="url(#arrowR)" strokeDasharray="6,3" />
            </svg>
            <div style={{ fontSize: 9, color: CN.textMuted }}>via CF Worker Proxy</div>
          </div>

          <div style={{ width: 1, height: 24, background: CN.border }} />

          {/* B -> A */}
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: CN.green, letterSpacing: "1px", marginBottom: 4 }}>AGENT FEEDBACK</div>
            <svg width="120" height="32" viewBox="0 0 120 32">
              <defs>
                <marker id="arrowL" markerWidth="8" markerHeight="6" refX="0" refY="3" orient="auto">
                  <path d="M8,0 L0,3 L8,6" fill={CN.green} />
                </marker>
              </defs>
              <line x1="20" y1="16" x2="110" y2="16" stroke={CN.green} strokeWidth="2" markerStart="url(#arrowL)" strokeDasharray="6,3" />
            </svg>
            <div style={{ fontSize: 9, color: CN.textMuted }}>Quality signals</div>
          </div>
        </div>

        {/* System B Card — Light theme styling to show contrast */}
        <div style={{
          padding: "16px 20px", border: `1px solid ${CN.border}`,
          background: "#F9F9F7", borderTop: "3px solid #003A70",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, background: "rgba(0,58,112,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 18, fontWeight: 900, color: "#003A70" }}>B</span>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: "#003A70" }}>Lingque</div>
              <div style={{ fontSize: 10, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>
                Customer-Facing Product
              </div>
            </div>
          </div>

          {/* Mock KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: "#E5E7EB", marginBottom: 16 }}>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>Enterprises</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#003A70" }}>999</div>
            </div>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>Agents</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#003A70" }}>7</div>
            </div>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>Tasks</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#1B7A4E" }}>41</div>
            </div>
            <div style={{ padding: "10px 12px", background: "#FFFFFF" }}>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1px" }}>Skills</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#1B7A4E" }}>79</div>
            </div>
          </div>

          {/* Quick Nav */}
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6B7280", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 8 }}>
            WORKBENCH
          </div>
          {[
            { href: "/workbench/", label: "Monthly Kanban" },
            { href: "/workbench/agents/", label: "Digital Employees" },
            { href: "/workbench/batch/", label: "Batch Operations" },
            { href: "/workbench/calendar/", label: "Calendar View" },
          ].map((item) => (
            <Link key={item.href} href={item.href} style={{
              display: "block", padding: "6px 10px", marginBottom: 2,
              color: "#1D1B19", textDecoration: "none", fontSize: 12,
              background: "transparent", borderLeft: "2px solid #003A70",
            }}>
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Unified Status Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1px", background: CN.border }}>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>KG API</span>
          <span style={cnBadge(kgOk ? CN.green : CN.red, kgOk ? CN.greenBg : CN.redBg)}>{kgOk ? "ONLINE" : "OFFLINE"}</span>
        </div>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>CF Worker Proxy</span>
          <span style={cnBadge(CN.textMuted, CN.bgElevated)}>PENDING</span>
        </div>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>Lingque Frontend</span>
          <span style={cnBadge(CN.green, CN.greenBg)}>ONLINE</span>
        </div>
        <div style={{ padding: "10px 16px", background: CN.bgCard, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: CN.textSecondary }}>Agent Engine</span>
          <span style={cnBadge(CN.green, CN.greenBg)}>ONLINE</span>
        </div>
      </div>
    </div>
  );
}
