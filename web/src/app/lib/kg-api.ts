/* KG API Client — browser-safe access via HTTPS proxy.
   The Cloudflare Worker injects KG_API_KEY server-side, so the browser never handles secrets. */

// Same-origin by default: the browser fetches `/api/v1/*`, which nginx on the
// same host (app.hegui.org / ops.hegui.org / local dev proxy) forwards to the
// KG API backend. Override via NEXT_PUBLIC_KG_API_BASE for split-domain deploys.
const KG_API_BASE =
  process.env.NEXT_PUBLIC_KG_API_BASE || "/api/v1";

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

export async function getConstellationByType(type: string, limit = 300): Promise<{
  nodes: { id: string; label: string; type: string; size: number }[];
  edges: { source: string; target: string; type: string }[];
  total_nodes: number;
  total_edges: number;
  focus_type: string;
}> {
  return kgFetch(`/constellation/type?type=${encodeURIComponent(type)}&limit=${limit}`);
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

/* Hybrid search — text + LanceDB vector fused via RRF, with 1-hop graph expansion */

export interface HybridSearchHit {
  id: string;
  text: string;
  table: string;
  title: string;
  name: string;
  rrf_score: number;
}

export interface HybridSearchResponse {
  query: string;
  method: string;
  count: number;
  text_hits: number;
  vector_hits: number;
  results: HybridSearchHit[];
  graph_expansion: unknown[];
}

export async function hybridSearch(
  q: string,
  limit = 10,
  opts: { expand?: boolean; tableFilter?: string } = {},
): Promise<HybridSearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (opts.expand === false) params.set("expand", "false");
  if (opts.tableFilter) params.set("table_filter", opts.tableFilter);
  return kgFetch<HybridSearchResponse>(`/hybrid-search?${params.toString()}`);
}

/* Reasoning chain — structured justification rooted at a node (SOTA Must #4) */

export interface ReasoningEdge {
  edge_type: string;
  direction: "in" | "out";
  target: { id: string; type: string | null; label: string | null };
  source_clause_id: string | null;
  effective_at: string | null;
  superseded_at: string | null;
  via?: { id: string; type: string | null; edge: string };
}

export interface ReasoningChain {
  query_node: { id: string; type: string | null; label: string | null };
  direct_evidence: ReasoningEdge[];
  related_2hop: ReasoningEdge[];
  trace: { rel_types_scanned: number; queries_run: number; node_resolved: boolean };
}

export async function getReasoningChain(
  nodeId: string,
  include2Hop = true,
): Promise<ReasoningChain> {
  const qs = new URLSearchParams({ node_id: nodeId, include_2hop: String(include2Hop) });
  return kgFetch<ReasoningChain>(`/reasoning-chain?${qs.toString()}`);
}

/* Clause inspector — single-row + batch, pure-function façade over
   src/kg/clause_inspector.py. Mirrors backend describe() shape. */

export interface ClauseInspectRow {
  argument_role?: string | null;
  argument_strength?: number | null;
  override_chain_id?: string | null;
  override_chain_parents?: string[] | null;
  jurisdiction_code?: string | null;
  jurisdiction_scope?: string | null;
}

export interface ClauseInspectResult {
  clean: boolean;
  defect_flags: string[];
  argument: {
    role: {
      key: string;
      label_zh: string;
      gloss_en: string;
      system: string;
      prohibited_in_tax_law: boolean;
    } | null;
    role_prohibited_in_tax_law: boolean;
    strength: {
      tier: string | null;
      label_zh: string;
      label_en: string;
      color_token: string;
      raw: number | null;
    };
  };
  override_chain: {
    code: string | null;
    valid: boolean;
    kind: string;
    label_zh: string | null;
    chain: string[];
    reason: string | null;
  };
  override_chain_breadcrumb_zh: string;
  multiparent: {
    valid: boolean;
    reason: string | null;
    resolved: unknown[];
  } | null;
  consistency: {
    code: string | null;
    scope: string | null;
    verdict: string;
    reason: string | null;
    expected_scopes: string[];
  };
}

export interface ClauseInspectBatchResponse {
  count: number;
  clean_count: number;
  defect_count: number;
  results: ClauseInspectResult[];
}

export async function inspectClause(row: ClauseInspectRow): Promise<ClauseInspectResult> {
  const resp = await fetch(`${KG_API_BASE}/inspect/clause`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(row),
  });
  if (!resp.ok) throw new Error(`Inspect API ${resp.status}: ${resp.statusText}`);
  return resp.json();
}

export async function inspectClauseBatch(rows: ClauseInspectRow[]): Promise<ClauseInspectBatchResponse> {
  const resp = await fetch(`${KG_API_BASE}/inspect/clause/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows }),
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (body?.detail) detail = body.detail;
    } catch { /* keep statusText */ }
    throw new Error(`Inspect batch API ${resp.status}: ${detail}`);
  }
  return resp.json();
}

/* v4.2 Ontology: 27 node types across 4 layers (+6 P0 types, -2 garbage)
   Color scheme: 4 layer colors (not per-type) for visual clarity */
export const LAYER_GROUPS: Record<string, { color: string; darkColor: string; nodes: string[] }> = {
  "L1 法规层": { color: "#DBEAFE", darkColor: "#1E3A5F", nodes: ["LegalDocument", "LegalClause", "IssuingBody", "AccountingStandard", "TaxTreaty"] },
  "L2 业务层": { color: "#CFFAFE", darkColor: "#164E63", nodes: ["TaxRate", "AccountingSubject", "Classification", "TaxEntity", "Region", "FilingForm", "BusinessActivity", "JournalEntryTemplate", "FinancialStatementItem", "FilingFormField", "TaxItem", "TaxBasis", "TaxLiabilityTrigger", "TaxMilestoneEvent"] },
  "L3 合规层": { color: "#FEF3C7", darkColor: "#78350F", nodes: ["ComplianceRule", "RiskIndicator", "TaxIncentive", "Penalty", "AuditTrigger", "TaxAccountingGap", "SocialInsuranceRule", "InvoiceRule", "IndustryBenchmark", "TaxCalculationRule", "FinancialIndicator", "DeductionRule", "ResponseStrategy", "PolicyChange"] },
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
  AccountingStandard: L1_COLOR, TaxTreaty: L1_COLOR,
  // L2 Business (cyan)
  TaxRate: L2_COLOR, AccountingSubject: L2_COLOR, Classification: L2_COLOR,
  TaxEntity: L2_COLOR, Region: L2_COLOR, FilingForm: L2_COLOR, BusinessActivity: L2_COLOR,
  JournalEntryTemplate: L2_COLOR, FinancialStatementItem: L2_COLOR, FilingFormField: L2_COLOR,
  TaxItem: L2_COLOR, TaxBasis: L2_COLOR, TaxLiabilityTrigger: L2_COLOR, TaxMilestoneEvent: L2_COLOR,
  // L3 Compliance (amber)
  ComplianceRule: L3_COLOR, RiskIndicator: L3_COLOR, TaxIncentive: L3_COLOR,
  Penalty: L3_COLOR, AuditTrigger: L3_COLOR, TaxAccountingGap: L3_COLOR,
  SocialInsuranceRule: L3_COLOR, InvoiceRule: L3_COLOR, IndustryBenchmark: L3_COLOR,
  TaxCalculationRule: L3_COLOR, FinancialIndicator: L3_COLOR, DeductionRule: L3_COLOR,
  ResponseStrategy: L3_COLOR, PolicyChange: L3_COLOR,
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
  // Mapping/entity edges (missing from screenshot)
  APPLIES_TO_ENTITY: "适用主体", APPLIES_IN_REGION: "适用地区", APPLIES_TO_CLASS: "适用分类",
  REQUIRES_FILING: "需申报", ENTITY_FOR_TAX: "主体税种",
  INCENTIVE_BASED_ON: "优惠依据", FT_GOVERNED_BY: "受监管", FT_QUALIFIES_FOR: "符合条件",
  DEBITS_V2: "借方", CREDITS_V2: "贷方",
  // v4.2 P0 edges
  HAS_ENTRY_TEMPLATE: "分录模板", ENTRY_DEBITS: "借方科目", ENTRY_CREDITS: "贷方科目",
  POPULATES: "填列", FIELD_OF: "栏次属于", DERIVES_FROM: "来源于",
  CALCULATION_FOR_TAX: "计算规则", DECOMPOSES_INTO: "分解为", COMPUTED_FROM: "数据来源",
  HAS_BENCHMARK: "行业基准", PARTY_TO: "缔约方", OVERRIDES_RATE: "协定税率",
  // v4.2 P1 edges
  HAS_ITEM: "税目", COMPUTED_BY: "计税依据", LIABILITY_TRIGGERED_BY: "纳税义务触发",
  INDICATES_RISK: "触发预警", PENALIZED_FOR: "处罚对象", ESCALATES_TO: "升级为",
  SPLITS_INTO: "分拆为", DEDUCTS_FROM: "从...扣除",
  // v4.2 P2 edges
  RESPONDS_TO: "风险应对", TRIGGERED_BY_CHANGE: "政策影响", SUPERSEDES_POLICY: "替代政策",
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
