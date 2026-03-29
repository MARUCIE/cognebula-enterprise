/* KG API Client — connects to CogNebula KG service.
   Production: CF Worker proxy (HTTPS) → VPS public IP.
   Local dev:  Direct Tailscale HTTP. */

const KG_API_BASE =
  typeof window !== "undefined" && window.location.protocol === "https:"
    ? "https://cognebula-kg-proxy.maoyuan-wen-683.workers.dev/api/v1"
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
  return kgFetch("/quality");
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

export async function searchNodes(query: string, limit = 10): Promise<{ results: KGSearchResult[] }> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return kgFetch(`/search?${params}`);
}

export async function listNodes(table: string, limit = 20): Promise<{ nodes: Record<string, unknown>[] }> {
  const params = new URLSearchParams({ table, limit: String(limit) });
  return kgFetch(`/nodes?${params}`);
}

/* Layer classification for node types */
export const LAYER_GROUPS: Record<string, { color: string; darkColor: string; nodes: string[] }> = {
  "L1 法规层": { color: "#FEE2E2", darkColor: "#7F1D1D", nodes: ["LegalDocument", "LawOrRegulation", "LegalClause", "IssuingBody", "RegulationClause", "DocumentSection"] },
  "L2 业务层": { color: "#DBEAFE", darkColor: "#1E3A5F", nodes: ["TaxRate", "AccountingSubject", "FilingFormV2", "BusinessActivity", "TaxEntity", "HSCode", "TaxClassificationCode", "TaxCodeDetail", "TaxCodeIndustryMap", "AccountingEntry", "AccountRuleMapping", "ChartOfAccount", "ChartOfAccountDetail", "FormTemplate", "SpreadsheetEntry"] },
  "L3 合规层": { color: "#FEF3C7", darkColor: "#78350F", nodes: ["ComplianceRuleV2", "RiskIndicatorV2", "Penalty", "AuditTrigger", "TaxRiskScenario"] },
  "Shared 共享": { color: "#F0FDF4", darkColor: "#14532D", nodes: ["TaxType", "TaxIncentiveV2", "TaxIncentive", "KnowledgeUnit", "Classification", "Region", "RegionalTaxPolicy", "FAQEntry", "CPAKnowledge", "MindmapNode", "IndustryRiskProfile"] },
};

export const NODE_COLORS: Record<string, string> = {
  LegalDocument: "#EF4444", LawOrRegulation: "#F87171", LegalClause: "#FB923C", IssuingBody: "#FCA5A5",
  RegulationClause: "#F97316", DocumentSection: "#FDBA74",
  TaxRate: "#3B82F6", AccountingSubject: "#60A5FA", FilingFormV2: "#93C5FD",
  BusinessActivity: "#2563EB", TaxEntity: "#1D4ED8", HSCode: "#38BDF8", TaxClassificationCode: "#0EA5E9",
  ComplianceRuleV2: "#F59E0B", RiskIndicatorV2: "#FBBF24", Penalty: "#DC2626", AuditTrigger: "#F97316",
  TaxType: "#8B5CF6", TaxIncentiveV2: "#A78BFA", KnowledgeUnit: "#10B981",
  Classification: "#6EE7B7", Region: "#34D399", CPAKnowledge: "#14B8A6",
  MindmapNode: "#06B6D4", FAQEntry: "#22D3EE", IndustryRiskProfile: "#F472B6",
  RegionalTaxPolicy: "#4ADE80", TaxRiskScenario: "#FB7185",
};

export const EDGE_LABELS_ZH: Record<string, string> = {
  INTERPRETS: "解释", EXEMPLIFIED_BY: "案例", EXPLAINS_RATE: "税率说明",
  WARNS_ABOUT: "风险提示", DESCRIBES_INCENTIVE: "优惠说明", GUIDES_FILING: "申报指南",
  ISSUED_BY: "发布", PART_OF: "属于", SUPERSEDES: "替代", AMENDS: "修订",
  APPLIES_TO_TAX: "适用税种", BASED_ON: "依据", CHILD_OF: "子分类",
  REFERENCES_CLAUSE: "引用", GOVERNED_BY: "受约束", TRIGGERS_TAX: "触发税种",
  KU_ABOUT_TAX: "知识税种", TRIGGERED_BY: "触发", PENALIZED_BY: "处罚",
};

export const EDGE_COLORS: Record<string, string> = {
  SUPERSEDES: "#D97706", AMENDS: "#D97706", CONFLICTS_WITH: "#DC2626",
  REFERENCES_CLAUSE: "#3B82F6", BASED_ON: "#60A5FA", ISSUED_BY: "#6366F1",
  APPLIES_TO_TAX: "#059669", INTERPRETS: "#F59E0B", WARNS_ABOUT: "#EF4444",
  DESCRIBES_INCENTIVE: "#10B981", GUIDES_FILING: "#8B5CF6", EXPLAINS_RATE: "#EAB308",
  PART_OF: "#94A3B8", CHILD_OF: "#94A3B8", GOVERNED_BY: "#7C3AED",
  TRIGGERS_TAX: "#0891B2", KU_ABOUT_TAX: "#0891B2",
};

export function getNodeLayer(type: string): string {
  for (const [group, info] of Object.entries(LAYER_GROUPS)) {
    if (info.nodes.includes(type)) return group;
  }
  return "Shared 共享";
}
