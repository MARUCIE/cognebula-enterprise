# CogNebula SOTA Council - Brainstorming Notes & Evidence

## Context
CogNebula currently provides a KuzuDB+Cypher graph engine with a 6-phase AST pipeline, handling ~20k file repositories in ~10s. It has a FastAPI backend, Graph RAG endpoints, and WebGL 3D visualization.
**The Goal**: Make it the ultimate "out-of-the-box, fast-deployment enterprise context brain for Agents".

---

## Agent Council Inputs

### 1. PM Perspective (Product & Out-of-the-Box UX)
- **Product Packaging**: Cloud-native (Helm, k8s operators), Docker Compose for POCs. Packaged MCP Proxy for zero-config Agent connections. Enterprise Connectors (GitLab, GitHub, Jira).
- **UX/DX**: Protocol-First Integration (MCP + REST). Natural Language to Graph (NL2Graph) engine. Visual Control Plane for monitoring graph freshness. Client SDKs (Python/TS).
- **SOTA Features**: Hybrid Graph-Vector RAG. Adaptive Context Windowing (PageRank-based pruning). Real-time Incremental Sync via Webhooks. Blast Radius Analysis API.
- **Positioning**: An API-first, neutral backend brain, unlike Sourcegraph Cody (closed UI) or Neo4j (heavy Java, generic graph).

### 2. Architect Perspective (SOTA Graph & RAG Tech)
- **Hybrid RAG**: Option A (Orchestrator-Level Join). LanceDB/Milvus for vector search, mapping UUIDs to KuzuDB for structural traversal. Keeps components optimized and decoupled.
- **Enterprise Scale**: Option B (Database-per-Tenant). Shared-Nothing architecture. One KuzuDB directory per Repo/Tenant to ensure hardware-level isolation and prevent write-lock contention.
- **Event-Driven Sync**: Option B (Queue + Worker). Webhook -> Redis/Kafka -> Single-threaded ingester per repo. Safely handles Git bursts.
- **Parsing Engine**: Option B (Universal Tree-sitter). Crucial for broken/incomplete code during active dev. Provides true error recovery and a unified schema across languages.

### 3. Security/Compliance Perspective (Enterprise Isolation)
- **Data Isolation**: Logical Database/Namespace isolation for standard SaaS; strict S3 prefixing for raw code. KuzuDB routing per tenant.
- **Access Control (RBAC)**: OIDC/SAML for humans. Short-lived JWT tokens (OAuth2) for M2M Agents. Agent-specific `ServiceAccount` bound to single repos. API Gateway enforces isolation before KuzuDB.
- **Secure Git Auth**: GitHub App / GitLab Integration for dynamic, ephemeral, short-lived Installation Tokens. Absolutely NO long-lived PATs. Secret scrubbers in logs.
- **Mitigations**: AST-level injection prevention (force tenant_id in Cypher).

### 4. QA/Integration Perspective (LLM/Agent Consumption)
- **MCP Completeness**: Need `explore_architecture`, `semantic_search`, `get_symbol_outline`, `analyze_blast_radius`, `trace_dependencies`, `get_decision_history`.
- **Context Density**: Tiered Detail Degradation (Depth 0 = body, Depth 1 = signature, Depth 2 = name). Semantic Pruning based on token ceiling. Boilerplate stripping. LLM-summarized edges.
- **Agent E2E Testing**: A/B SWE-benchmarking vs generic agents. Blast Radius regression tests (agent must fix all 5 downstream breakages). Precision/Recall tracking on Graph RAG output. Deterministic shadowing for Cypher queries.

---

## Synthesis & Consensus
1. **Architecture Pivot**: CogNebula must transition to a **Shared-Nothing Multi-Tenant Architecture** (One KuzuDB per repo), backed by a Queue (Redis) for webhook-driven real-time incremental sync.
2. **Parsing Upgrade**: We must replace Regex/AST hybrid with **Universal Tree-sitter** for fault-tolerant, cross-language fidelity.
3. **Hybrid RAG**: Establish **Late-Binding Hybrid RAG**: Vector DB (LanceDB) finds the entry point -> KuzuDB maps the Blast Radius.
4. **Security Priority**: Drop PAT support in favor of **GitHub App Ephemeral Tokens** + API Gateway JWT validation.
5. **Agent Interface (MCP)**: Expand MCP to include `analyze_blast_radius` and enforce **Tiered Detail Degradation** to protect LLM context windows.

---

## SOTA Product SOP Benchmarking (2025-2026)

Research window: 12 months (Mar 2025 - Mar 2026). Conducted by 4 parallel research agents covering 20+ products across 4 domains.

### CRITICAL FINDING: KuzuDB Archived

KuzuDB (CogNebula's current graph engine) was **acquired by Apple in October 2025** and the GitHub repository is **archived**. No active maintenance, no public roadmap. This is a **blocking risk** requiring immediate migration planning.

**Recommended replacements**:
- MVP/Single-project: LanceDB (embedded vectors) + DuckDB with PGQ extension (embedded graph)
- Growth/Multi-tenant: LanceDB (S3) + Memgraph Community (3-8x faster than Neo4j, MCP toolkit, free replication)
- Enterprise: LanceDB (distributed) + Neo4j Aura (managed, RBAC, clustering, GraphRAG ai.* functions)

---

### Domain A: Code Intelligence & Search Platforms

| Product | Positioning | Key SOP Pattern | Quality Gates | Enterprise | Differentiator |
|---------|------------|-----------------|---------------|------------|----------------|
| **Sourcegraph Cody** | Big code + legacy monorepos | SCIP semantic indexing, search-first | Copyright guardrails, zero data retention | SOC2, RBAC, SSO, BYOK LLM | 54B+ lines indexed, 800K+ devs, 15+ US gov agencies |
| **Greptile v3** | Bug detection + validation | Graph-based codebase context (NOT RAG) | 82% catch rate benchmark, severity segmentation | MCP server, team learning, air-gapped | Validation-only (no codegen), 82% bug catch rate |
| **GitHub Copilot** | Agentic DevOps platform | Agent Mode in GitHub Actions | CI/CD approval gates, branch protection | MCP GA (Aug 2025), multi-IDE | Deepest platform integration, agentic infra automation |
| **Bloop** | Agent orchestration (pivot) | Tantivy + Qdrant dual-index | N/A (archived Jan 2025) | Multi-agent teams | Pivoting from search to orchestration |

**Key takeaways**:
- Graph > RAG: Greptile explicitly states "codebases are graphs, not documents"
- MCP is table stakes: GitHub Copilot MCP GA Aug 2025; Greptile v3 MCP-native
- Validation-only for compliance: Greptile's no-codegen philosophy wins in regulated industries
- Learning from team patterns: auto-extract coding standards from org's own review comments

---

### Domain B: Knowledge Graph / Graph RAG

**Products Researched**: Neo4j, NebulaGraph, Weaviate, LanceDB, Microsoft GraphRAG

#### Key Findings (Decision Matrix)

| Criteria | Neo4j | NebulaGraph | Weaviate | LanceDB | MS GraphRAG |
|----------|-------|-------------|----------|---------|-------------|
| Architecture | Index-free adjacency | Compute-storage separated | Multi-tenant vector+graph | Embedded/serverless | Hierarchical community |
| RAG Strategy | Graph traversal + vectors | Hybrid (graph+text+vector) | BM25+dense vector fusion | Vector + metadata SQL | LLM entity/community extraction |
| Query Latency | 24ms avg (LDBC SNB) | 4x Neo4j on SNB | <100ms per-tenant | <1ms vector search | 100ms-10s (local vs global) |
| Tenant Isolation | Logical (label-based) | Logical (namespace) | Physical shard/tenant | Not built-in | Not built-in |
| Max Scale | 10s of billions nodes | 100s of billions nodes | 50k+ tenants/node | Petabytes vectorized | Depends on backend |
| Entity Extraction | LLM-based (80-85%) | LLM-based | Not focused | Not focused | 92% accuracy (v2.0) |
| MCP/Agent | MCP server available | REST API + connectors | Planned (2026) | LangChain/LlamaIndex | Pluggable via Python |
| License | AGPL/Commercial | Apache 2.0 | BSD 3-Clause | Apache 2.0 | MIT |
| Pricing | $65-146/GB/mo (Aura) | Usage-based cloud | $25-150/mo SaaS | Free OSS, $16/mo cloud | Free OSS |

#### SOTA Patterns Identified
1. **Hybrid RAG = Vector Entry + Graph Expansion**: All leaders combine vector similarity (find entry point) with graph traversal (map relationships). Neo4j does vector+Cypher in one query. MS GraphRAG uses hierarchical community summaries for global questions.
2. **Tiered Retrieval**: Local search (entity-focused, fast) vs Global search (community summaries, comprehensive). CogNebula should implement both modes.
3. **Entity Extraction Quality**: MS GraphRAG v2.0 achieves 92% accuracy with neural model. This is the benchmark CogNebula should target.
4. **Community Detection**: Leiden algorithm is the standard (Neo4j, MS GraphRAG). CogNebula's simplified Leiden is directionally correct.
5. **Physical Tenant Isolation**: Weaviate leads with 50k+ tenants per node via physical shard isolation. CogNebula's per-repo KuzuDB is architecturally similar (shared-nothing).
6. **Embedded-First**: LanceDB proves embedded vector DB is viable at scale (default for MS GraphRAG). CogNebula's embedded KuzuDB + embedded LanceDB is a strong combination.

#### Transferable to CogNebula
- Neo4j's in-database LLM procedures (Cypher AI) -- could inspire NL2Graph
- MS GraphRAG's hierarchical community summarization -- upgrade from simple Leiden
- Weaviate's ACORN (2-hop expansion for filtered search) -- useful for blast radius
- LanceDB's zero-copy versioning -- useful for incremental sync rollback
- Neo4j's MCP server pattern -- direct reference for CogNebula MCP expansion

Sources: neo4j.com, nebula-graph.io, weaviate.io, lancedb.com, microsoft.github.io/graphrag, arxiv.org (2025-2026)

---

### Domain C: AI Coding Agents & Tools

| Product | Autonomy | Context Management | Quality Gate | Enterprise Compliance | Key Metric |
|---------|----------|-------------------|-------------|----------------------|------------|
| **Cursor** | Semi (foreground + background) | Editor buffer + Git worktrees | CI/CD + PR review | Team Rules, Hooks | 8 parallel agents |
| **Devin** | Full autonomous | Auto-indexing every 2h + long-term reasoning | SWE-bench 13.86%, autofix loops | Slack/Teams/Jira | 67% PR merge rate, 4x speed YoY |
| **Codex CLI** | Full (with approval gates) | PLANS.md durable memory | Long-horizon 25h+ testing | AGENTS.md, local execution | 25h runtime, 30K lines |
| **Augment Code** | Semi (suggestion) | Real-time semantic indexing (seconds) | Precision/recall on real codebases | ISO 42001, SOC2, zero data retention | 400K+ files, 200K token window |
| **Windsurf** | Semi (human-approved) | Cascade Flows + Memories | User feedback + real-world | SOC2, FedRAMP High, HIPAA | 8 parallel agents, air-gapped |

**Key takeaways**:
- Context is the new compiler: Augment's semantic indexing (seconds, not minutes) is the benchmark
- Verification loops > single-pass: Devin's write-agent + review-agent pattern reduces merged bugs
- Durable project memory: Codex's PLANS.md pattern is industry-standard for long-horizon tasks
- Multi-agent isolation: Git worktrees (Cursor/Windsurf) enable 8+ parallel agents without conflicts
- Real-time indexing is non-negotiable: <5s for index updates (Augment benchmark)

---

### Domain D: Enterprise Developer Platforms

| Product | SOP Maturity | Quality Gates | Deployment | Compliance | Time-to-Value |
|---------|-------------|---------------|------------|------------|---------------|
| **GitLab Duo** | Enterprise (AI-governed) | MR bots, CI gates, custom compliance frameworks | K8s/Helm/Self-hosted | SOC2, ISO 27001, custom | 1 week |
| **Backstage** | Mid-market (plugin) | Service scorecards (L1-L5 maturity) | K8s/Helm/Plugins | Not built-in | 1-2 weeks |
| **Atlassian Compass** | Enterprise (SaaS) | Health scorecards, DORA automation | SaaS-only | Via integrations | 3-5 days |
| **Linear** | Startup/Mid (Git-native) | Integration-based (PR status) | SaaS-only | Not built-in | 1 day |
| **Vercel** | Startup/Mid (Git-native) | Build checks, Lighthouse, CWV | SaaS Edge (300+ nodes) | SOC2, GDPR | <1 hour |
| **SurfSense** | Enterprise (self-hosted) | KG validation, confidence scoring | Docker/K8s | GDPR (self-hosted) | 1-2 days |

**Key takeaways**:
- Helm-based deployment is the enterprise standard (GitLab, Backstage patterns)
- DORA metrics (Lead Time, Deploy Freq, Change Failure Rate, MTTR) are the universal platform health language
- Service scorecards drive maturity (Backstage L1-L5, Compass health)
- Golden paths reduce time-to-value (Backstage 3-5 clicks to production service)
- SurfSense validates Neo4j-based KG for self-hosted research platforms

---

### Domain E: Graph Databases & Knowledge Graphs (Technical Deep-Dive)

| Product | Type | Latency vs Neo4j | Vector Search | RBAC | MCP | Status |
|---------|------|-------------------|---------------|------|-----|--------|
| **Neo4j** | Server graph DB | Baseline (slow: 46.9s p99) | 2025 ai.* functions | Yes | Emerging | Active, enterprise leader |
| **LanceDB** | Embedded vector DB | N/A (vector, not graph) | <20ms, 2-3x faster than ES | No | Community | Active, 7K+ stars |
| **Memgraph** | In-memory graph DB | 3-8x faster (41x on latency) | 3.0+ feature | Yes | Official toolkit | Active, growing |
| **KuzuDB** | Embedded graph DB | 100x faster (path queries) | N/A | No | N/A | **ARCHIVED (Apple, Oct 2025)** |
| **GraphRAG** | Pattern (not DB) | N/A | Central | N/A | Native | Active (MS + LlamaIndex) |
| **Tree-sitter** | Parser library | N/A | N/A | N/A | Available | Active, 21K+ stars, 40+ langs |

**Optimal Hybrid RAG Architecture (SOTA consensus)**:
```
Code Repo -> Tree-sitter AST Parsing (semantic chunks)
  |-> Vector Embeddings -> LanceDB (semantic entry point, <20ms)
  |-> Code Graph (calls/imports/defs) -> Memgraph/Neo4j (structural traversal, <200ms)
  |-> Metadata -> LanceDB columns
  |-> Agent (Claude + MCP) -> Hybrid Search via RRF re-ranking -> Context Assembly -> LLM
```

**Performance targets derived from SOTA**:
- Incremental parse: <100ms/file (tree-sitter)
- Vector search: <50ms p99 (LanceDB)
- Graph traversal (3-hop): <200ms (Memgraph)
- Hybrid search total: <500ms
- Full codebase indexing (10K LOC): <5s
- Symbol retrieval recall: >95%

---

## Comparison Matrix: All 20+ Products x 8 Dimensions

| Dimension | Best-in-Class | CogNebula Current | Gap | Priority |
|-----------|--------------|-------------------|-----|----------|
| **Graph Engine** | Memgraph (speed) / Neo4j (enterprise) | KuzuDB (ARCHIVED) | CRITICAL | P0 - Migrate immediately |
| **Vector Search** | LanceDB (<20ms, embedded) | None | HIGH | P0 - Add hybrid RAG |
| **Parsing** | Tree-sitter (40+ langs, incremental) | Regex/AST hybrid | HIGH | P1 - Replace parser |
| **Agent Protocol** | MCP (GitHub GA, Greptile native) | REST only | HIGH | P1 - Add MCP server |
| **Context Mgmt** | Augment (400K files, seconds) | ~20K files, ~10s | MEDIUM | P2 - Scale indexing |
| **Quality Gates** | Greptile (82% catch rate benchmark) | None formal | MEDIUM | P2 - Add benchmarks |
| **Enterprise Auth** | Augment (ISO 42001, SOC2, RBAC) | Basic | HIGH | P1 - Add RBAC/SSO |
| **Deployment** | GitLab (Helm/K8s/Self-hosted) | Docker Compose | MEDIUM | P2 - Add Helm charts |
| **Observability** | DORA metrics + SLOs | None | MEDIUM | P3 - Add dashboards |
| **Multi-tenancy** | Augment (hardware-backed isolation) | Single-tenant | HIGH | P1 - Shared-nothing |

---

## Gap Analysis

CogNebula has 3 **CRITICAL/HIGH** gaps that must be addressed before any competitive positioning:

1. **Graph Engine (CRITICAL)**: KuzuDB is dead. Migration to Memgraph (speed) or Neo4j (enterprise) is non-negotiable. Cypher compatibility eases the path.
2. **No Hybrid RAG (HIGH)**: Every competitor combines vector + graph. CogNebula has graph-only, missing the semantic entry point that makes context retrieval usable for agents.
3. **No MCP Server (HIGH)**: MCP is table stakes since Aug 2025. Without it, agents cannot consume CogNebula's context natively.

Secondary gaps (enterprise blockers):
4. Auth/RBAC: No SSO, no JWT, no audit -- enterprise non-starter
5. Multi-tenancy: Single-tenant architecture limits B2B SaaS
6. Parser: Regex parsing is fragile for real-world JS/TS codebases

---

## Transferable Capability Checklist

Capabilities CogNebula should adopt from SOTA products, ranked by impact:

**P0 - Blocking / Must-Have (before any new features)**:
1. [KuzuDB -> Memgraph/Neo4j] Graph engine migration (KuzuDB archived)
2. [LanceDB] Add embedded vector DB for hybrid RAG entry point
3. [Tree-sitter] Replace regex/AST parser with universal tree-sitter (40+ langs)
4. [MCP Server] Expose graph as MCP tools for agent consumption

**P1 - High Impact (enterprise readiness)**:
5. [Augment] Real-time incremental indexing (<5s updates via webhooks)
6. [Greptile] Graph-based code context (NOT simple RAG) -- dependency traversal for blast radius
7. [Devin] Verification loops: write-agent + review-agent pattern
8. [GitLab] RBAC + SSO/SAML + audit trails
9. [Memgraph] Shared-nothing multi-tenant (one graph per repo/tenant)
10. [Codex] Durable project memory (ADRs, architecture decisions as graph nodes)

**P2 - Competitive Advantage**:
11. [Greptile] Team learning: auto-extract coding standards from review comments
12. [Augment] Tiered detail degradation (body -> signature -> name) for LLM context protection
13. [GitLab] Helm charts + K8s operator for enterprise deployment
14. [Backstage] Service scorecards + golden paths for onboarding
15. [Cursor] Branch-aware graphs (different graph states per git branch)

**P3 - Differentiation**:
16. [GraphRAG] Community detection + hierarchical summarization
17. [SurfSense] Self-hosted knowledge graph with confidence scoring
18. [Linear] MCP integration for project management agent orchestration
19. [Vercel] Core Web Vitals tracking for visualization frontend
20. [Devin] Auto-indexing with architecture wiki generation every 2h

---

## Risk Analysis

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| KuzuDB no longer maintained | CRITICAL | CERTAIN | Migrate to Memgraph (speed) or Neo4j (enterprise) immediately |
| MCP adoption window closing | HIGH | HIGH | Ship MCP server in next release; all competitors already have it |
| Augment/Greptile outpace on context quality | HIGH | MEDIUM | Invest in real-time incremental indexing + tree-sitter |
| Enterprise buyers require SOC2/ISO | HIGH | HIGH | Start compliance process; adopt zero-data-retention default |
| Neo4j performance gap (41x slower) | MEDIUM | LOW | Use Memgraph for speed-critical; Neo4j for enterprise features |
| Tree-sitter parser quality variance | MEDIUM | MEDIUM | Pin grammar versions; test on target languages before shipping |
| Multi-tenant isolation complexity | MEDIUM | MEDIUM | Start with database-per-tenant (simple); evolve to namespace isolation |
| Agent orchestration market consolidation | MEDIUM | MEDIUM | Position as infrastructure layer (brain), not orchestrator |

---

## Research Sources (consolidated, 60+ URLs across 4 research agents)

Code Intelligence: Sourcegraph SCIP blog, Greptile benchmarks/series-a, GitHub Copilot docs/changelog, Bloop GitHub
AI Agents: Cursor changelog/blog, Cognition Devin blog, OpenAI Codex cookbook, Augment Code reviews, Windsurf docs/enterprise
Graph/KG: Neo4j 2025 blog, LanceDB benchmarks, Memgraph comparisons, KuzuDB GitHub (archived), LlamaIndex GraphRAG v2, Tree-sitter ecosystem
Enterprise: GitLab 2025 releases, Backstage 1.43/CNCF, Atlassian Compass, Linear guide, Vercel/Netlify comparisons, SurfSense GitHub
