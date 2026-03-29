"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { listNodes, getGraph, getStats, type KGNeighbor, type KGStats, LAYER_GROUPS, NODE_COLORS, EDGE_LABELS_ZH, EDGE_COLORS } from "../../lib/kg-api";
import { CN, cnCard, cnBadge, cnInput, cnBtn, cnBtnPrimary } from "../../lib/cognebula-theme";

/* ── Regulation-relevant node types (L1 + L3 layers + key L2) ── */
const BROWSABLE_TYPES = [
  { table: "LegalClause", label: "法规条款", layer: "L1" },
  { table: "LegalDocument", label: "法律文件", layer: "L1" },
  { table: "LawOrRegulation", label: "法律法规", layer: "L1" },
  { table: "RegulationClause", label: "规章条款", layer: "L1" },
  { table: "ComplianceRuleV2", label: "合规规则", layer: "L3" },
  { table: "RiskIndicatorV2", label: "风险指标", layer: "L3" },
  { table: "AuditTrigger", label: "审计触发", layer: "L3" },
  { table: "Penalty", label: "处罚规定", layer: "L3" },
  { table: "KnowledgeUnit", label: "知识单元", layer: "Shared" },
  { table: "CPAKnowledge", label: "CPA知识", layer: "Shared" },
  { table: "FAQEntry", label: "问答条目", layer: "Shared" },
  { table: "TaxIncentiveV2", label: "税收优惠", layer: "L2" },
  { table: "TaxRate", label: "税率", layer: "L2" },
  { table: "AccountingSubject", label: "会计科目", layer: "L2" },
];

interface NodeRow {
  id: string;
  title: string;
  subtitle: string;
  content: string;
  col1: string;
  col2: string;
  col3: string;
  raw: Record<string, unknown>;
}

interface NodeDetail {
  node: NodeRow;
  neighbors: KGNeighbor[];
  parentDocName?: string;
}

/* ── Type-specific column definitions ── */
const TYPE_COLUMNS: Record<string, { c1: string; c2: string; c3: string }> = {
  LegalClause: { c1: "条款号", c2: "所属法规", c3: "条款内容" },
  LegalDocument: { c1: "文件名称", c2: "类型", c3: "生效日期" },
  LawOrRegulation: { c1: "法规名称", c2: "发布机关", c3: "文号" },
  RegulationClause: { c1: "条款号", c2: "所属规章", c3: "条款内容" },
  ComplianceRuleV2: { c1: "规则名称", c2: "分类", c3: "违规后果" },
  RiskIndicatorV2: { c1: "指标名称", c2: "分类", c3: "说明" },
  AuditTrigger: { c1: "触发条件", c2: "分类", c3: "说明" },
  Penalty: { c1: "处罚名称", c2: "分类", c3: "说明" },
  KnowledgeUnit: { c1: "知识主题", c2: "类型", c3: "来源" },
  CPAKnowledge: { c1: "知识主题", c2: "分类", c3: "内容" },
  FAQEntry: { c1: "问题", c2: "分类", c3: "回答" },
  TaxIncentiveV2: { c1: "优惠名称", c2: "类型", c3: "说明" },
  TaxRate: { c1: "税率名称", c2: "税种", c3: "税率值" },
  AccountingSubject: { c1: "科目名称", c2: "编号", c3: "说明" },
};

const DEFAULT_COLUMNS = { c1: "名称", c2: "分类", c3: "说明" };

/* ── Document name cache (documentId → name) ── */
const docNameCache: Record<string, string> = {};

async function resolveDocName(documentId: string): Promise<string> {
  if (!documentId) return "";
  if (docNameCache[documentId]) return docNameCache[documentId];
  try {
    // Try LawOrRegulation first
    const res = await getGraph("LawOrRegulation", documentId);
    if (res.node) {
      const name = String(res.node.title || res.node.name || res.node._label || "");
      // Clean up crawled article titles
      const cleaned = name.replace(/^收藏[！!]\s*/, "").replace(/^转发[！!]\s*/, "").replace(/^重磅[！!]\s*/, "");
      docNameCache[documentId] = cleaned;
      return cleaned;
    }
  } catch { /* skip */ }
  docNameCache[documentId] = `Doc-${documentId.slice(-8)}`;
  return docNameCache[documentId];
}

/* ── Type-specific row mapping ── */
function mapNodeRow(n: Record<string, unknown>, type: string): NodeRow {
  const id = String(n.id || "");
  const raw = n;

  switch (type) {
    case "LegalClause": {
      const clauseNum = n.clauseNumber ? `第${n.clauseNumber}条` : "";
      const docId = String(n.documentId || "");
      return {
        id, raw,
        title: clauseNum || id,
        subtitle: docId,
        content: String(n.content || n.title || ""),
        col1: clauseNum,
        col2: docNameCache[docId] || `[${docId.slice(-8)}]`,
        col3: String(n.content || n.title || "").slice(0, 80),
      };
    }
    case "RegulationClause": {
      const artNum = n.articleNumber ? `第${n.articleNumber}条` : "";
      const regId = String(n.regulationId || "");
      return {
        id, raw,
        title: artNum || id,
        subtitle: regId,
        content: String(n.fullText || n.title || ""),
        col1: artNum,
        col2: docNameCache[regId] || `[${regId.slice(-8)}]`,
        col3: String(n.fullText || n.title || "").slice(0, 80),
      };
    }
    case "LawOrRegulation": {
      const title = String(n.title || n.name || "");
      return {
        id, raw,
        title,
        subtitle: String(n.regulationNumber || ""),
        content: String(n.fullText || ""),
        col1: title,
        col2: String(n.issuingAuthority || "").replace("chinatax", "国家税务总局").replace("mof", "财政部"),
        col3: String(n.regulationNumber || n.effectiveDate || ""),
      };
    }
    case "LegalDocument": {
      return {
        id, raw,
        title: String(n.name || n.title || ""),
        subtitle: String(n.type || ""),
        content: "",
        col1: String(n.name || n.title || ""),
        col2: String(n.type || ""),
        col3: String(n.effectiveDate || n.issueDate || ""),
      };
    }
    case "ComplianceRuleV2": {
      return {
        id, raw,
        title: String(n.name || ""),
        subtitle: String(n.category || ""),
        content: String(n.fullText || n.description || ""),
        col1: String(n.name || ""),
        col2: String(n.category || ""),
        col3: String(n.consequence || ""),
      };
    }
    case "KnowledgeUnit": {
      return {
        id, raw,
        title: String(n.title || n.topic || ""),
        subtitle: String(n.type || ""),
        content: String(n.content || ""),
        col1: String(n.title || n.topic || ""),
        col2: String(n.type || ""),
        col3: String(n.source || ""),
      };
    }
    default: {
      const title = String(n.title || n.name || n.topic || n.question || n._display_label || "");
      return {
        id, raw,
        title,
        subtitle: "",
        content: String(n.fullText || n.content || n.description || ""),
        col1: title,
        col2: String(n.category || n.type || ""),
        col3: String(n.description || n.content || "").slice(0, 80),
      };
    }
  }
}

export default function RulesPage() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [activeType, setActiveType] = useState("LawOrRegulation");
  const [nodes, setNodes] = useState<NodeRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const PAGE_SIZE = 50;

  // Load stats for counts
  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  // Load nodes when type or page changes
  const loadNodes = useCallback(async (type: string, pageNum: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await listNodes(type, PAGE_SIZE, pageNum * PAGE_SIZE);
      const mapped = (res.results || []).map((n) => mapNodeRow(n, type));
      setNodes(mapped);
      setTotal(stats?.nodes_by_type?.[type] || res.count || mapped.length);

      // For clause types, batch-resolve parent document names
      if (type === "LegalClause" || type === "RegulationClause") {
        const docField = type === "LegalClause" ? "documentId" : "regulationId";
        const uniqueDocIds = [...new Set(
          (res.results || []).map((n) => String(n[docField] || "")).filter(Boolean)
        )];
        // Resolve up to 10 unique doc IDs
        const toResolve = uniqueDocIds.filter((id) => !docNameCache[id]).slice(0, 10);
        if (toResolve.length > 0) {
          await Promise.all(toResolve.map((id) => resolveDocName(id)));
          // Re-map with resolved names
          const remapped = (res.results || []).map((n) => mapNodeRow(n, type));
          setNodes(remapped);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "API error");
    }
    setLoading(false);
  }, [stats]);

  useEffect(() => {
    loadNodes(activeType, page);
  }, [activeType, page, loadNodes]);

  // Change type
  const switchType = (type: string) => {
    setActiveType(type);
    setPage(0);
    setDetail(null);
    setSearch("");
  };

  // Open detail panel with parent doc resolution
  const openDetail = useCallback(async (node: NodeRow) => {
    setDetailLoading(true);
    let parentDocName = "";
    try {
      const graphResult = await getGraph(activeType, node.id);
      // Resolve parent doc name for clause types
      if (activeType === "LegalClause" || activeType === "RegulationClause") {
        const docField = activeType === "LegalClause" ? "documentId" : "regulationId";
        const docId = String(node.raw[docField] || "");
        if (docId) parentDocName = await resolveDocName(docId);
      }
      setDetail({ node, neighbors: graphResult.neighbors || [], parentDocName });
    } catch {
      setDetail({ node, neighbors: [], parentDocName });
    }
    setDetailLoading(false);
  }, [activeType]);

  // Filter by search
  const filtered = search
    ? nodes.filter((n) => {
        const q = search.toLowerCase();
        return n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q) || n.id.toLowerCase().includes(q);
      })
    : nodes;

  const typeCount = (table: string) => stats?.nodes_by_type?.[table] || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 49px)" }}>
      {/* Left: Type Selector */}
      <div style={{
        width: 220, flexShrink: 0, overflowY: "auto",
        background: CN.bgCard, borderRight: `1px solid ${CN.border}`,
      }}>
        <div style={{ padding: "14px 16px", borderBottom: `1px solid ${CN.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: CN.text }}>法规条款浏览器</div>
          <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>
            {stats ? `${(stats.total_nodes / 1000).toFixed(0)}K 节点 / ${stats.node_tables} 张表` : "..."}
          </div>
        </div>

        {/* Group by layer */}
        {["L1", "L3", "L2", "Shared"].map((layer) => {
          const types = BROWSABLE_TYPES.filter((t) => t.layer === layer);
          const layerLabel = { L1: "L1 法规层", L3: "L3 合规层", L2: "L2 业务层", Shared: "共享层" }[layer];
          return (
            <div key={layer}>
              <div style={{ padding: "10px 16px 4px", fontSize: 9, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1.5px" }}>
                {layerLabel}
              </div>
              {types.map((t) => {
                const count = typeCount(t.table);
                const active = activeType === t.table;
                return (
                  <button key={t.table}
                    onClick={() => switchType(t.table)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      width: "100%", padding: "7px 16px", fontSize: 12,
                      color: active ? CN.blue : CN.text,
                      background: active ? CN.blueBg : "transparent",
                      borderLeft: `2px solid ${active ? CN.blue : "transparent"}`,
                      border: "none", borderBottom: "none",
                      cursor: "pointer", textAlign: "left",
                    }}
                  >
                    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: NODE_COLORS[t.table] || "#94A3B8", flexShrink: 0 }} />
                      {t.label}
                    </span>
                    <span style={{ fontSize: 10, color: CN.textMuted, fontVariantNumeric: "tabular-nums" }}>
                      {count > 999 ? `${(count / 1000).toFixed(1)}K` : count}
                    </span>
                  </button>
                );
              })}
            </div>
          );
        })}

        {/* Link to KG Explorer */}
        <div style={{ padding: 12, borderTop: `1px solid ${CN.border}`, marginTop: 8 }}>
          <Link href="/expert/kg" style={{
            display: "block", padding: "8px 12px", textAlign: "center",
            color: CN.blue, textDecoration: "none", fontSize: 11, fontWeight: 600,
            border: `1px solid ${CN.border}`, borderRadius: 4, background: CN.blueBg,
          }}>
            在知识图谱中探索 &rarr;
          </Link>
        </div>
      </div>

      {/* Center: Node List */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {/* Toolbar */}
        <div style={{
          padding: "10px 24px", borderBottom: `1px solid ${CN.border}`,
          display: "flex", alignItems: "center", gap: 12, flexShrink: 0, background: CN.bg,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: CN.text }}>
            {BROWSABLE_TYPES.find((t) => t.table === activeType)?.label || activeType}
          </div>
          <span style={cnBadge(CN.blue, CN.blueBg)}>{total.toLocaleString()}</span>
          <input
            type="text" placeholder="搜索当前页..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            style={{ ...cnInput, flex: 1, maxWidth: 320 }}
          />
          {/* Pagination */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: CN.textMuted }}>
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              style={{ ...cnBtn, padding: "5px 10px", opacity: page === 0 ? 0.3 : 1 }}>
              &lt;
            </button>
            <span>{page + 1} / {totalPages || 1}</span>
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
              style={{ ...cnBtn, padding: "5px 10px", opacity: page >= totalPages - 1 ? 0.3 : 1 }}>
              &gt;
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: "10px 24px", background: CN.redBg, color: CN.red, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Node table */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: "center", color: CN.textMuted }}>加载中...</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: CN.textMuted }}>
              {search ? `未找到匹配 "${search}" 的条目` : "暂无数据"}
            </div>
          ) : (
            (() => {
              const cols = TYPE_COLUMNS[activeType] || DEFAULT_COLUMNS;
              const thStyle: React.CSSProperties = { padding: "8px 14px", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" };
              return (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${CN.border}`, position: "sticky", top: 0, background: CN.bgElevated, zIndex: 1 }}>
                      <th style={{ ...thStyle, width: 120 }}>{cols.c1}</th>
                      <th style={thStyle}>{cols.c2}</th>
                      <th style={thStyle}>{cols.c3}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((n) => {
                      const isSelected = detail?.node.id === n.id;
                      return (
                        <tr key={n.id}
                          style={{ cursor: "pointer", background: isSelected ? CN.blueBg : "transparent" }}
                          onClick={() => openDetail(n)}
                        >
                          <td style={{ padding: "8px 14px", color: CN.text, fontWeight: 600, borderBottom: `1px solid ${CN.bgElevated}`, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.col1 || "--"}
                          </td>
                          <td style={{ padding: "8px 14px", color: CN.textSecondary, fontSize: 12, borderBottom: `1px solid ${CN.bgElevated}`, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.col2 || "--"}
                          </td>
                          <td style={{ padding: "8px 14px", color: CN.textSecondary, fontSize: 12, borderBottom: `1px solid ${CN.bgElevated}`, maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.col3 || "--"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              );
            })()
          )}
        </div>
      </div>

      {/* Right: Detail Panel */}
      {detail && (
        <div style={{
          width: 400, flexShrink: 0, overflowY: "auto",
          background: CN.bgCard, borderLeft: `1px solid ${CN.border}`, padding: 20,
        }}>
          <div style={{ display: "flex", alignItems: "start", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: CN.text, margin: 0, lineHeight: 1.5, maxWidth: 320 }}>
              {detail.node.title}
            </h3>
            <button onClick={() => setDetail(null)}
              style={{ background: "none", border: "none", color: CN.textMuted, cursor: "pointer", fontSize: 18, flexShrink: 0 }}>
              x
            </button>
          </div>

          {/* Type badge + parent doc */}
          <div style={{ marginBottom: 16, display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={cnBadge(NODE_COLORS[activeType] || CN.blue, CN.blueBg)}>
              {BROWSABLE_TYPES.find((t) => t.table === activeType)?.label || activeType}
            </span>
            {detail.parentDocName && (
              <div style={{ fontSize: 13, color: CN.blue, fontWeight: 600, lineHeight: 1.5 }}>
                {detail.parentDocName}
              </div>
            )}
          </div>

          {detailLoading && <div style={{ color: CN.textMuted, fontSize: 12, marginBottom: 12 }}>加载关联...</div>}

          {/* Full Content */}
          {detail.node.content && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>全文内容</span>
                {detail.node.content.length >= 195 && !detail.node.content.endsWith("。") && (
                  <span style={cnBadge(CN.amber, CN.amberBg)}>可能截断</span>
                )}
              </div>
              <div style={{
                fontSize: 13, color: CN.text, lineHeight: 1.9,
                padding: "14px 16px", background: CN.bg, border: `1px solid ${CN.border}`,
                borderRadius: 4, whiteSpace: "pre-wrap",
                maxHeight: "50vh", overflowY: "auto",
              }}>
                {detail.node.content.replace(/\s*\|\s*/g, "\n\n")}
              </div>
            </div>
          )}

          {/* All metadata fields */}
          {(() => {
            const skipFields = new Set(["_id", "_label", "_display_label", "id", "title", "name", "fullText", "content", "description", "text", "topic", "question", "node_text"]);
            const meta = Object.entries(detail.node.raw).filter(
              ([k, v]) => !skipFields.has(k) && v !== null && v !== undefined && String(v).length > 0 && String(v) !== "undefined" && String(v) !== ""
            );
            if (meta.length === 0) return null;
            return (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>属性</div>
                <div style={{ fontSize: 12, lineHeight: 1.7 }}>
                  {meta.map(([k, v]) => (
                    <div key={k} style={{ display: "flex", gap: 8, marginBottom: 4, paddingBottom: 4, borderBottom: `1px solid ${CN.bgElevated}` }}>
                      <span style={{ color: CN.textMuted, fontWeight: 600, minWidth: 100, flexShrink: 0 }}>{k}</span>
                      {String(v).startsWith("http") ? (
                        <a href={String(v)} target="_blank" rel="noopener noreferrer"
                          style={{ color: CN.blue, textDecoration: "none", wordBreak: "break-all" }}>
                          {String(v).length > 50 ? `${String(v).slice(0, 50)}...` : String(v)}
                        </a>
                      ) : (
                        <span style={{ color: CN.text, wordBreak: "break-all" }}>{String(v).slice(0, 300)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Node ID */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, letterSpacing: "1px", marginBottom: 4 }}>节点 ID</div>
            <div style={{ fontSize: 11, color: CN.textMuted, fontFamily: "monospace", wordBreak: "break-all" }}>
              {detail.node.id}
            </div>
          </div>

          {/* Neighbors */}
          {detail.neighbors.length > 0 && (
            <div style={{ borderTop: `1px solid ${CN.border}`, paddingTop: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 10 }}>
                关联节点 ({detail.neighbors.length})
              </div>
              {detail.neighbors.map((nb, i) => (
                <div key={i} style={{
                  padding: "8px 12px", marginBottom: 4,
                  background: CN.bg, border: `1px solid ${CN.border}`, borderRadius: 4,
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: CN.text, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {nb.direction === "incoming" ? "\u2190 " : "\u2192 "}{nb.target_label}
                    </span>
                    <span style={cnBadge(EDGE_COLORS[nb.edge_type] || CN.purple, CN.purpleBg)}>
                      {EDGE_LABELS_ZH[nb.edge_type] || nb.edge_type}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: CN.textMuted }}>{nb.target_type}</div>
                </div>
              ))}
            </div>
          )}

          {/* Navigate to KG */}
          <Link href={`/expert/kg`}
            style={{
              display: "block", width: "100%", marginTop: 16, padding: "8px 0",
              background: CN.blueBg, border: `1px solid ${CN.border}`,
              color: CN.blue, fontSize: 12, fontWeight: 600, cursor: "pointer",
              borderRadius: 6, textAlign: "center", textDecoration: "none",
            }}
          >
            在知识图谱中查看此节点 &rarr;
          </Link>
        </div>
      )}
    </div>
  );
}
