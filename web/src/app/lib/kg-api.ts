/* KG API Client — connects to CogNebula KG service.
   Production: Cloudflare Tunnel (HTTPS) → VPS KuzuDB.
   Local dev:  Direct Tailscale HTTP. */

const KG_API_BASE =
  typeof window !== "undefined" && window.location.protocol === "https:"
    ? "https://opportunity-pentium-blessed-notes.trycloudflare.com/api/v1"
    : "http://100.75.77.112:8400/api/v1";

export interface KGStats {
  total_nodes: number;
  total_edges: number;
  total_entities: number;
  node_tables: number;
  rel_tables: number;
  nodes_by_type: Record<string, number>;
}

export interface KGNeighbor {
  edge_type: string;
  target_type: string;
  target_id: string;
  target_label: string;
  direction: "incoming" | "outgoing";
}

export interface KGGraphResult {
  node: Record<string, string | null> & { _label?: string };
  neighbors: KGNeighbor[];
  depth: number;
}

export interface KGSearchResult {
  id: string;
  table: string;
  title?: string;
  text?: string;
  name?: string;
  score?: number;
  source_table?: string;
  node_id?: string;
}

export interface KGQuality {
  total_nodes: number;
  total_edges: number;
  edge_density: number;
  title_coverage: number;
  content_coverage: number;
  tables_checked: number;
  quality_score: number;
  grade: string;
  details?: Record<string, unknown>[];
}

async function kgFetch<T>(path: string): Promise<T> {
  const resp = await fetch(`${KG_API_BASE}${path}`);
  if (!resp.ok) throw new Error(`KG API ${resp.status}: ${resp.statusText}`);
  return resp.json();
}

export async function getStats(): Promise<KGStats> {
  return kgFetch("/stats");
}

export async function getQuality(): Promise<KGQuality> {
  const raw = await kgFetch<{
    gate: string; score: number;
    metrics: Record<string, number>;
    title_stats?: Record<string, unknown>;
    issues?: unknown[];
  }>("/quality");
  // Backend nests data inside metrics — flatten for frontend
  const m = raw.metrics || {};
  return {
    total_nodes: m.total_nodes || 0,
    total_edges: m.total_edges || 0,
    edge_density: m.edge_density || 0,
    title_coverage: (m.title_coverage || 0) * 100,
    content_coverage: (m.content_coverage || 0) * 100,
    tables_checked: 0,
    quality_score: m.quality_score || raw.score || 0,
    grade: raw.gate === "PASS" ? (m.quality_score >= 90 ? "A" : m.quality_score >= 70 ? "B" : "C") : "F",
    details: raw.issues as Record<string, unknown>[],
  };
}

export async function getGraph(
  table: string,
  idValue: string,
  idField = "id",
  depth = 1
): Promise<KGGraphResult> {
  const params = new URLSearchParams({ table, id_field: idField, id_value: idValue, depth: String(depth) });
  return kgFetch(`/graph?${params}`);
}

export async function getConstellation(limit = 500): Promise<{
  nodes: { id: string; label: string; type: string; size: number }[];
  edges: { source: string; target: string; type: string }[];
  total_nodes: number;
  total_edges: number;
}> {
  return kgFetch(`/constellation?limit=${limit}`);
}

export async function searchNodes(query: string, limit = 10): Promise<{ results: KGSearchResult[] }> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return kgFetch(`/search?${params}`);
}

export async function listNodes(table: string, limit = 20, offset = 0, q?: string): Promise<{ type: string; count: number; offset: number; results: Record<string, unknown>[] }> {
  const params = new URLSearchParams({ type: table, limit: String(limit), offset: String(offset) });
  if (q) params.set("q", q);
  return kgFetch(`/nodes?${params}`);
}

/* ── Node Detail ────────────────────────────── */
export interface KGNodeDetail {
  id: string;
  title?: string;
  name?: string;
  fullText?: string;
  content?: string;
  description?: string;
  sourceUrl?: string;
  regulationNumber?: string;
  effectiveDate?: string;
  hierarchyLevel?: string;
  regulationType?: string;
  status?: string;
  _display_label?: string;
  [key: string]: unknown;
}

export async function getNodeDetail(table: string, id: string): Promise<KGNodeDetail | null> {
  const graphResult = await getGraph(table, id);
  if (!graphResult.node) return null;
  return { ...graphResult.node, id } as KGNodeDetail;
}

/* ── Chat RAG ───────────────────────────────── */
export interface ChatSource {
  id: string;
  text: string;
  table: string;
  category?: string;
  score?: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  cypher?: string;
  html?: string;
  mode: string;
  tokens_used?: number;
}

export async function chatRAG(question: string, limit = 8): Promise<ChatResponse> {
  const resp = await fetch(`${KG_API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode: "rag", limit }),
  });
  if (!resp.ok) throw new Error(`Chat API ${resp.status}: ${resp.statusText}`);
  return resp.json();
}

/* v4.1 Ontology: 21 node types across 4 layers
   Color scheme: 4 layer colors (not 21 type colors) for visual clarity */
export const LAYER_GROUPS: Record<string, { color: string; darkColor: string; nodes: string[] }> = {
  "L1 法规层": { color: "#DBEAFE", darkColor: "#1E3A5F", nodes: ["LegalDocument", "LegalClause", "IssuingBody"] },
  "L2 业务层": { color: "#CFFAFE", darkColor: "#164E63", nodes: ["TaxRate", "AccountingSubject", "Classification", "TaxEntity", "Region", "FilingForm", "BusinessActivity"] },
  "L3 合规层": { color: "#FEF3C7", darkColor: "#78350F", nodes: ["ComplianceRule", "RiskIndicator", "TaxIncentive", "Penalty", "AuditTrigger", "TaxAccountingGap", "SocialInsuranceRule", "InvoiceRule", "IndustryBenchmark"] },
  "L4 知识层": { color: "#F3F4F6", darkColor: "#1F2937", nodes: ["TaxType", "KnowledgeUnit"] },
};

// Layer-based colors: 4 distinct hues, high contrast on dark background
const L1_COLOR = "#60A5FA"; // Blue — regulations/law
const L2_COLOR = "#22D3EE"; // Cyan — business operations
const L3_COLOR = "#FBBF24"; // Amber — compliance/risk
const L4_COLOR = "#9CA3AF"; // Gray — knowledge/reference

export const NODE_COLORS: Record<string, string> = {
  // L1 Legal (blue)
  LegalDocument: L1_COLOR, LegalClause: L1_COLOR, IssuingBody: L1_COLOR,
  // L2 Business (cyan)
  TaxRate: L2_COLOR, AccountingSubject: L2_COLOR, Classification: L2_COLOR,
  TaxEntity: L2_COLOR, Region: L2_COLOR, FilingForm: L2_COLOR, BusinessActivity: L2_COLOR,
  // L3 Compliance (amber)
  ComplianceRule: L3_COLOR, RiskIndicator: L3_COLOR, TaxIncentive: L3_COLOR,
  Penalty: L3_COLOR, AuditTrigger: L3_COLOR, TaxAccountingGap: L3_COLOR,
  SocialInsuranceRule: L3_COLOR, InvoiceRule: L3_COLOR, IndustryBenchmark: L3_COLOR,
  // L4 Knowledge (gray)
  TaxType: L4_COLOR, KnowledgeUnit: L4_COLOR,
};

export const EDGE_LABELS_ZH: Record<string, string> = {
  INTERPRETS: "解释", EXEMPLIFIED_BY: "案例", EXPLAINS_RATE: "税率说明",
  WARNS_ABOUT: "风险提示", DESCRIBES_INCENTIVE: "优惠说明", GUIDES_FILING: "申报指南",
  ISSUED_BY: "发布", PART_OF: "属于", SUPERSEDES: "替代", AMENDS: "修订",
  APPLIES_TO_TAX: "适用税种", BASED_ON: "依据", CHILD_OF: "子分类",
  REFERENCES_CLAUSE: "引用", GOVERNED_BY: "受约束", TRIGGERS_TAX: "触发税种",
  KU_ABOUT_TAX: "知识税种", TRIGGERED_BY: "触发", PENALIZED_BY: "处罚",
  // v4.1 new edges
  PARENT_CLAUSE: "上级条款", PARENT_SUBJECT: "上级科目",
  MAPS_TO_SUBJECT: "对应科目", STACKS_WITH: "可叠加", EXCLUDES: "互斥",
  CREATES_GAP: "产生差异", HAS_GAP: "税会差异", GAP_FOR_TAX: "差异税种",
  HAS_BUSINESS_GAP: "业务差异", RELATED_PARTY: "关联方",
  HAS_RATE: "适用税率", INSURANCE_IN_REGION: "社保地区",
  INVOICE_FOR_TAX: "发票税种", BENCHMARK_FOR: "行业基准",
  RULE_FOR_INDUSTRY: "行业规则", OVERRIDES_IN: "地方覆盖", AUDIT_TRIGGERS: "审计触发",
  // Backbone edges (v4.1)
  INCENTIVE_FOR_TAX: "优惠政策", RULE_FOR_TAX: "合规规则", AUDIT_FOR_TAX: "审计指标",
  RISK_FOR_TAX: "风险指标", FILING_FOR_TAX: "申报表", CALCULATED_FROM: "计税基础",
  SURCHARGE_OF: "附加税", RELATED_TAX: "关联税种", FT_INCENTIVE_TAX: "优惠",
  FT_APPLIES_TO: "适用于", CLASSIFIED_UNDER_TAX: "归属法规", MAPS_TO_ACCOUNT: "会计科目",
};

// Quiet edge colors: only 3 semantic groups (not per-edge rainbow)
const EDGE_STRUCTURAL = "#4B5563"; // Gray — structural (PART_OF, CHILD_OF, ISSUED_BY)
const EDGE_SEMANTIC = "#6B7280";   // Lighter gray — semantic (INTERPRETS, EXPLAINS, GUIDES)
const EDGE_RISK = "#DC2626";       // Red — only for conflict/risk edges
export const EDGE_COLORS: Record<string, string> = {
  SUPERSEDES: EDGE_STRUCTURAL, AMENDS: EDGE_STRUCTURAL, ISSUED_BY: EDGE_STRUCTURAL,
  PART_OF: EDGE_STRUCTURAL, CHILD_OF: EDGE_STRUCTURAL, GOVERNED_BY: EDGE_STRUCTURAL,
  REFERENCES_CLAUSE: EDGE_SEMANTIC, BASED_ON: EDGE_SEMANTIC,
  APPLIES_TO_TAX: EDGE_SEMANTIC, INTERPRETS: EDGE_SEMANTIC,
  DESCRIBES_INCENTIVE: EDGE_SEMANTIC, GUIDES_FILING: EDGE_SEMANTIC,
  EXPLAINS_RATE: EDGE_SEMANTIC, TRIGGERS_TAX: EDGE_SEMANTIC, KU_ABOUT_TAX: EDGE_SEMANTIC,
  CONFLICTS_WITH: EDGE_RISK, WARNS_ABOUT: EDGE_RISK,
};

export function getNodeLayer(type: string): string {
  for (const [group, info] of Object.entries(LAYER_GROUPS)) {
    if (info.nodes.includes(type)) return group;
  }
  return "L4 知识层";
}
