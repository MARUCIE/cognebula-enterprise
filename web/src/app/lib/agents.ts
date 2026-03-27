/* Shared agent constants -- single source of truth for name → slug mapping.
   Used by: dashboard, ai-team, ops/agents, ops/alerts */

export const AGENT_SLUG: Record<string, string> = {
  "林税安": "lin-shui-an",
  "赵合规": "zhao-he-gui",
  "陈税策": "chen-shui-ce",
  "王记账": "wang-ji-zhang",
  "张审核": "zhang-shen-he",
  "李客服": "li-ke-fu",
  "周小秘": "zhou-xiao-mi",
};

export function findAgentSlug(title: string): string | null {
  for (const [name, slug] of Object.entries(AGENT_SLUG)) {
    if (title.includes(name)) return slug;
  }
  return null;
}
