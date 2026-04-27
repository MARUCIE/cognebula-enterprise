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

---

## 2026-04 Update: 4-Agent Swarm Refresh (20+ products, 80+ sources)

Research date: 2026-04-10. Four parallel agents covering Code Intelligence, KG/Graph RAG, Agent Infra, Enterprise DevTools.

### Key Delta vs Previous Research

**1. KuzuDB Status Clarification**
- Previous note: "acquired by Apple Oct 2025"
- Updated: KuzuDB original team archived the project Oct 2025. **Vela Partners** maintains an active fork with concurrent multi-writer support added
- FalkorDB offers documented migration path from KuzuDB (Cypher-compatible)
- CogNebula currently has 620K nodes / 1M edges on the original KuzuDB — still functional but no upstream patches

**2. Augment Code Context Engine MCP (GA)**
- Semantic dependency graph architecture — closest competitor to CogNebula's graph approach
- Context Engine MCP is generally available: local CLI mode + remote API mode
- Benchmark: Claude Code +80% performance, Cursor+Opus +71%, pass rate +41%
- ISO 42001 + SOC 2 Type II + CMEK certified
- Only covers CODE context, not domain knowledge (tax/compliance)

**3. Neo4j Agent Ecosystem ($100M Investment)**
- Aura Agent GA (Feb 2026): hosted MCP Server, one-click deploy
- $100M committed to agentic AI ecosystem
- Official neo4j-graphrag Python package
- Only graph DB with full MCP + hosted agent deployment

**4. Industry Convergence: "Code Graph + RAG" = Consensus Architecture**
- GitLab: Knowledge Graph (Rust, GA 18.4) for code entity graph
- Qodo: Context Engine with multi-repo graph + agentic reasoning
- Tabnine: Enterprise Context Engine (vector + graph + agentic RAG)
- All three invested in the same architecture pattern in 2025, independently

**5. Agent Infra: Universal Context Gap**
All 7 agent platforms (LangChain, CrewAI, Devin, SWE-Agent, Aider, Codex CLI, Claude Code) lack native structured knowledge graph access for regulated domains. Context management is either vector search, file-system traversal, or proprietary indexing. None supports graph traversal over domain-specific ontologies.

**6. LightRAG as Lightweight Alternative**
- EMNLP 2025 paper. Incremental graph update (50% cheaper than MS GraphRAG)
- Retrieval latency ~80ms. Pluggable backends (PostgreSQL, Neo4j, MongoDB, Redis)
- Can use KuzuDB/fork as storage backend
- MIT license, active development

### Updated Strategic Position for CogNebula

Previous research positioned CogNebula as a **code intelligence** platform competing with Sourcegraph/Augment/Cursor. The 2026-04 refresh reveals a cleaner positioning:

**CogNebula is a DOMAIN knowledge graph for AI agents, not a code graph.**

The competitive landscape has two separate markets:
1. **Code Context Engines** (Sourcegraph, Augment, Cursor, Copilot) — graph/vector over source code
2. **Domain Knowledge Graphs** (CogNebula) — structured regulatory knowledge for AI agents in finance/tax

CogNebula has **zero direct competitors** in category 2. The validation from category 1 is that the architecture (graph + RAG + MCP) works — CogNebula applies it to a different knowledge domain.

### Updated Priority Actions

| # | Action | Status (Previous) | Update |
|---|--------|-------------------|--------|
| P0-1 | Graph engine migration | CRITICAL: KuzuDB archived | Vela fork available; FalkorDB migration documented. Can defer if Vela fork stable |
| P0-2 | MCP Server for agent consumption | HIGH | Now CRITICAL: Neo4j Aura Agent GA, Augment MCP GA, CrewAI bidirectional MCP. Window closing |
| P0-3 | Hybrid RAG (vector + graph) | HIGH | Validated by 6 independent platforms. LightRAG or LanceDB as vector complement |
| P1-1 | Enterprise auth (SSO/RBAC) | HIGH | Market confirms: $19-60/user/mo for enterprise AI add-ons |
| P1-2 | Deployment flexibility | MEDIUM → HIGH | 5/6 enterprise platforms support on-prem/air-gapped. Table stakes for regulated industries |
| NEW | Published benchmarks | — | Augment's 300+ PR benchmark + specific numbers (+80%, 100ms) are sales differentiators. CogNebula needs equivalent |

### Pricing Reference (2026 Market)

| Tier | Market Range | CogNebula Analog |
|------|-------------|------------------|
| Individual developer | $10-20/mo | N/A (CogNebula is B2B) |
| Team AI add-on | $19-40/user/mo | Basic MCP access + query API |
| Enterprise AI platform | $39-60/user/mo + custom | Full KG + compliance rules + audit trail |
| Self-hosted/air-gapped | +50-100% premium | Finance/gov customers will pay premium |

### Sources (2026-04 Refresh)

Code Intelligence: Sourcegraph Amp pricing, GitHub Copilot agent mode docs, Cursor indexing architecture (Turbopuffer), Augment Context Engine MCP GA blog, CursorBench
KG/Graph RAG: Neo4j Aura Agent GA, NebulaGraph 2025 review, lance-graph crate, Weaviate Hybrid Search 2.0, MS GraphRAG v1.0 token cost reduction, LightRAG EMNLP 2025, KuzuDB archived (The Register), Vela Partners fork blog, FalkorDB migration guide
Agent Infra: LangChain/LangGraph memory docs, CrewAI enterprise review, Devin 2.0 technical design, SWE-Agent NeurIPS 2024, Aider repomap, OpenAI Codex CLI/MCP, Claude Agent SDK
Enterprise DevTools: GitLab Duo Knowledge Graph docs, GitLab FY2026 earnings, JetBrains AI plans, Snyk DeepCode AI, Qodo Context Engine, Tabnine Enterprise Context Engine launch, Amazon Q Developer features

---

## 2026-04-16 Session 48 — Semantic Edge Import Closure

### Objective
- Resume the blocked Session 47 handoff and finish semantic-edge loading to production without user interaction.

### Findings
- Vela/Kuzu `0.12.0` rejects `COPY <rel-group> FROM ... (header=false)` when the REL TABLE GROUP has multiple `FROM/TO` pairs.
- The production-safe syntax is:
  `COPY SEMANTIC_SIMILAR FROM "<csv>" (from='Type', to='Type', header=false)`.
- The previous fallback had already inserted exactly `1000` same-type semantic edges for each of the 7 tables, so rerun safety required deleting existing same-type `SEMANTIC_SIMILAR` edges before bulk reload.
- Benchmark verification initially failed with `HTTP 401` because the API server reads `KG_API_KEY`, while `benchmark/run_eval.py` only read `COGNEBULA_API_KEY`.

### Actions Executed
- Patched `scripts/build_semantic_edges.py` to:
  - bulk load with explicit `from/to`
  - delete existing same-type semantic edges before reload
- Synced the script to `kg-node`
- Stopped `kg-api`, reran the full semantic-edge builder, restarted `kg-api`
- Patched `benchmark/run_eval.py` to fall back to `KG_API_KEY`
- Synced benchmark runner to `kg-node` and re-ran hybrid benchmark

### Evidence
- Post-load graph totals immediately after import: `856,072` nodes / `2,016,849` edges / density `2.356`
- Latest manual verification totals: `856,072` nodes / `2,017,420` edges / density `2.357`
- Post-load semantic edges: `570,481`
- Quality gate: `PASS / 100`
- Hybrid benchmark: `79% overall`, `100/100` question pass, `0` failures, `0` errors
  - canonical artifact: `benchmark/results_hybrid_20260416_after_security_fix.json`
- Runtime: semantic import completed in `827s`
- Manual UX-path verification (`增值税一般纳税人认定标准是什么`): `5` results returned; top result `VAT_SMALL_SCALE_TO_GENERAL_TAXPAYER`

### Anti-Regression Notes
- Do not split `SEMANTIC_SIMILAR` into per-type relation tables unless API queries are updated too; the explicit `from/to` COPY path works and preserves the existing relation label.
- Future benchmark runs against production should work with either `COGNEBULA_API_KEY` or `KG_API_KEY`.

---

## 2026-04-16 Session 49 — Ralph Workflow Grounding

### New Constraints Applied
- Root agent stays on orchestration; security/testing lanes should run as specialized subagents where useful.
- Ralph loop requires explicit grounding artifacts before continued execution.
- DNA capture is required for verified remediation paths.

### Grounding Artifacts
- Context snapshot: `.omx/context/semantic-edge-closeout-20260416T001600Z.md`
- Ralph PRD: `.omx/plans/prd-semantic-edge-closeout.md`
- Ralph test spec: `.omx/plans/test-spec-semantic-edge-closeout.md`
- PDCA checklist: `doc/00_project/initiative_cognebula_sota/PDCA_ITERATION_CHECKLIST.md`

### DNA Capsule
- Created: `/Users/mauricewen/00-AI-Fleet/dna/capsules/semantic-rel-group-copy-fix/SKILL.md`
- Registry: `/Users/mauricewen/00-AI-Fleet/configs/dna-registry.json`
- Validation:
  - `ai dna validate` → PASS
  - `ai dna inherit semantic-rel-group-copy-fix --force` → synced
  - `ai dna doctor` → PASS

### Attacker Review Follow-up
- `kg-api-server.py`
  - Removed query-string API key acceptance; auth now only reads `X-API-Key`
  - Hardened `migrate_table()` so `source/target` must be real node tables and `field_map` is restricted to target-schema fields plus simple source identifiers/literals
  - Deployed the fix to the actual systemd service target `/home/kg/kg-api-server.py`
- `scripts/build_semantic_edges.py`
  - Removed legacy fallback branches that created per-type relation-table alternatives or partial 1000-row inserts
  - The script now fails fast if REL TABLE GROUP creation or typed COPY fails, preventing partial-success drift
- `scripts/render_doc_html.py`
  - Removed remote JS dependency
  - Added markdown raw-HTML sanitization before pandoc rendering
- `benchmark/run_eval.py`
  - Help text updated to match the new localhost default and `KG_API_KEY` fallback
- Fresh attacker-review verdict:
  - no remaining HIGH/MEDIUM findings in scope
  - residual low risk: markdown sanitization is line-oriented rather than a full untrusted-markdown sanitizer
  - residual low risk: benchmark fallback to `KG_API_KEY` is mild env-name coupling, not an auth gap

### Final Architect Verification
- Verdict: `APPROVED`
- Remaining blockers: none
- Residual low risks:
  - markdown hardening is lightweight and intended for trusted docs
  - benchmark env fallback is mild name coupling
  - `HANDOFF.md` keeps superseded historical text for audit continuity

## 2026-04-16 Session 50 — Closeout Tail Cleanup

### Objective
- Remove the last active auth/env naming drift and stale handoff wording left behind after Session 49 approval.

### Actions Executed
- Standardized `benchmark/run_eval.py` on canonical `KG_API_KEY`
- Standardized `cognebula_mcp.py` on canonical `KG_API_KEY`
- Updated MCP copy/metrics to the current `856K+ / 2M+` baseline
- Reworded the Session 47 handoff density target as historical-only so it no longer conflicts with the canonical `2M+` KPI

### Verification
- `python3 -m py_compile benchmark/run_eval.py cognebula_mcp.py`
- `rg -n "COGNEBULA_API_KEY" benchmark/run_eval.py cognebula_mcp.py` → no hits
- Runtime env-resolution checks:
  - `run_eval.py`: `KG_ONLY=True`, `OLD_ONLY_EMPTY=True`
  - `cognebula_mcp.py`: `KG_ONLY=True`, `OLD_ONLY_EMPTY=True`
- Live remote auth checks:
  - `GET http://100.75.77.112:8400/api/v1/stats` without auth → `401 Unauthorized`
  - `GET http://100.75.77.112:8400/api/v1/quality` without auth → `401 Unauthorized`

### Residual Low Risks
- Markdown sanitization remains intentionally lightweight and only suitable for trusted project docs
- Historical notes still mention the old env mismatch as root cause evidence, but active code paths now use only `KG_API_KEY`

## 2026-04-16 Session 51 — Static Web Auth Proxy Alignment

### Objective
- Close the remaining browser-side auth gap: the static Next.js frontend must not call the protected KG API directly or hold `KG_API_KEY`.

### Findings
- `web/src/app/lib/kg-api.ts` was still pointing the browser at a direct remote API/tunnel path.
- The web app is built with `output: export`, so a Next.js App Route proxy would break the static export model.
- The repo already contains a Cloudflare Worker proxy (`worker/src/index.ts`), but it was not yet aligned with the current API-key auth model.

### Actions Executed
- Removed the incompatible App Route proxy attempt and preserved static export.
- Repointed `web/src/app/lib/kg-api.ts` to the HTTPS Worker proxy (`NEXT_PUBLIC_KG_API_BASE` override; Worker URL by default).
- Updated `worker/src/index.ts` to:
  - read `KG_API_ORIGIN` from Worker vars
  - inject `X-API-Key` from Worker secret/env binding
  - forward `Accept` / `Content-Type`
  - preserve upstream JSON content type
- Updated `worker/wrangler.toml` with canonical `KG_API_ORIGIN` config.
- Synced PDCA docs to the browser-safe access path.

### Verification
- `npm run build` passed in `web/`
- Static build completed successfully across all 38 routes
- `./web/node_modules/.bin/tsc --noEmit --target es2022 --module esnext --lib es2022,dom worker/src/index.ts` passed
- Confirmed no App Route remains under `web/src/app/api/`
- Verified the browser KG client now defaults to `https://cognebula-kg-proxy.workers.dev/api/v1`
- Regenerated HTML companions for the updated PDCA markdown docs

### Residual Low Risks
- Cloudflare runtime secret state is external to the repo; the deployed Worker still needs `KG_API_KEY` configured in Cloudflare

## 2026-04-16 Session 52 — Self-hosted Compose Packaging

### Objective
- Start closing the last major Phase D gap by packaging the current topology for self-hosted use without exposing `KG_API_KEY` to the browser.

### Actions Executed
- Added `web/Dockerfile` to build the exported Next.js app into a static image
- Added `docker/nginx.web.conf.template` to serve the static web app and proxy `/api/v1/*` to `cognebula-api` with injected `X-API-Key`
- Expanded `docker-compose.yml` to run:
  - `cognebula-api`
  - `cognebula-web`
- Added root `.dockerignore` so the web image build context only contains the files it actually needs
- Replaced the API image's repo-wide `requirements.txt` install with a minimal runtime dependency set for `kg-api-server.py`
- Fixed the web healthcheck probe to use `127.0.0.1`
- Changed the default packaged graph mount to `data/finance-tax-graph.archived.157nodes`, which is the only real local Kuzu file in the repo
- Changed the packaged web default port from `3000` to `3001` to avoid the local port collision observed during runtime verification
- Updated `README.md` to document the new local access points (`:3001` web, `:8400` API)

### Verification
- `docker compose config` passed
- `KG_API_KEY=dummy docker compose config` passed and showed:
  - `cognebula-api` receives `KG_API_KEY=dummy`
  - `cognebula-web` receives `KG_API_KEY=dummy` and `KG_API_UPSTREAM=http://cognebula-api:8400`
- `KG_API_KEY=dummy docker compose build cognebula-web` passed after `.dockerignore` reduced the web build context from ~`1.29GB` to ~`896KB`
- `KG_API_KEY=dummy docker compose build cognebula-api` passed after replacing the repo-wide dependency install with a minimal API runtime dependency set
- `KG_API_KEY=dummy docker compose up -d` started the packaged stack on its default ports
- `curl http://localhost:8400/api/v1/health` → `status=healthy`, `kuzu=true`, `lancedb=true`
- `curl -I http://localhost:3001/` → `200 OK`
- `curl http://localhost:3001/api/v1/health` → packaged web proxy returned `status=healthy`, `kuzu=true`
- `docker inspect -f '{{.State.Health.Status}}' cognebula-web` → `healthy`
- `KG_API_KEY=dummy docker compose down` removed the local verification stack cleanly
- Docker CLI is installed (`Docker version 29.2.0`)
- Docker context inspection showed `desktop-linux` points to `unix:///Users/mauricewen/.docker/run/docker.sock`
- Re-rendered HTML companions for `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `USER_EXPERIENCE_MAP.md`, and `PLATFORM_OPTIMIZATION_PLAN.md`

### Residual Local Runtime Note
- The packaged stack is healthy against the bundled baseline graph (`157` nodes / `35` edges). Richer local QA still depends on mounting a fuller Kuzu file via `COGNEBULA_GRAPH_PATH`.

## 2026-04-16 Session 53 — Phase C Script Portability

### Objective
- Remove the “single machine only” constraint from the remaining Phase C backfill scripts so they can be preflighted locally and run against arbitrary Kuzu files.

### Actions Executed
- Updated:
  - `scripts/cpa_content_backfill.py`
  - `scripts/mindmap_batch_backfill.py`
  - `scripts/ld_description_backfill.py`
- Added `--db-path` to all three scripts
- Added `KUZU_DB_PATH` env fallback to all three scripts
- Added `--dry-run` read-only inspection mode to all three scripts
- Added missing `MindmapNode` table-existence precheck so dry-run exits cleanly instead of throwing a binder exception

### Verification
- `python3 -m py_compile` passed for all three scripts
- `--help` output on all three scripts now shows `--db-path`
- `rg -n -- '--dry-run|KUZU_DB_PATH|db-path' ...` confirms the new interface exists across all three files
- Local baseline-graph dry-run behavior:
  - `cpa_content_backfill.py` → `SKIP: CPAKnowledge table does not exist`
  - `mindmap_batch_backfill.py` → `SKIP: MindmapNode table does not exist`
  - `ld_description_backfill.py` → `SKIP: LegalDocument table does not exist in this DB`

### Residual Note
- This change removes portability/precheck friction, but it does not create missing node tables or fill missing content by itself.

## 2026-04-16 Session 54 — Local Demo Graph Bootstrap

### Objective
- Create a reproducible richer local Kuzu file for demos and packaged local verification, without mutating the archived baseline graph in-place.

### Actions Executed
- Added `scripts/bootstrap_local_demo_graph.py`
- The bootstrap script:
  - copies `data/finance-tax-graph.archived.157nodes`
  - injects FAQ data
  - auto-creates `OP_` accounting schema when CPA enrichment is requested
  - injects CPA case data by default
  - injects tax incentive data by default
  - injects administrative region data by default
  - injects native MindmapNode data by default
  - reports final node count
- Generated `data/finance-tax-graph.demo`
- Verified the packaged API against the richer demo graph with `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo`

### Verification
- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully
- Demo graph file counts:
  - baseline: `157` nodes / `35` edges
  - demo: `3847` nodes / `642` edges
  - `FAQEntry`: `1152`
  - `CPAKnowledge`: `649`
  - `MindmapNode`: `990`
  - `LawOrRegulation`: `0`
  - `OP_StandardCase`: `266`
  - `TaxIncentive`: `109`
  - `AdministrativeRegion`: `477`
- Packaged runtime proof:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d cognebula-api`
  - authenticated `/api/v1/stats` returned `nodes=3847`, `edges=642`, `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `LawOrRegulation=0`, `OP_StandardCase=266`, `TaxIncentive=109`, `AdministrativeRegion=477`
  - when the full stack is run with the richer demo graph, packaged web proxy requests still return `status=healthy`, `kuzu=true`

### Residual Note
- The richer demo graph is still a local convenience artifact, not a substitute for a fuller production-like graph snapshot.

## 2026-04-16 Session 55 — Demo Bootstrap Parity Fix

### Objective
- Close the remaining parity gap between the documented demo-bootstrap behavior and the actual default script path, then collect fresh runtime evidence from the rebuilt local stack.

### Actions Executed
- Fixed `scripts/bootstrap_local_demo_graph.py` so the default `--include` set explicitly contains `mindmap`
- Rebuilt `data/finance-tax-graph.demo` from the archived baseline after the fix
- Re-read the rebuilt Kuzu file directly to confirm the real node/edge distribution
- Re-ran the packaged local Compose stack against the rebuilt demo graph and verified both direct API and packaged web-proxy stats/health

### Verification
- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_faq_data.py src/inject_cpa_data.py src/inject_mindmap_native.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` now shows the `[mindmap] ... src/inject_mindmap_native.py` step in the default flow and ends with `Node count: 3847`
- Direct Kuzu verification on `data/finance-tax-graph.demo`:
  - `nodes=3847`, `edges=642`
  - `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `AdministrativeRegion=477`, `OP_StandardCase=266`, `TaxIncentive=109`, `LawOrRegulation=0`
- Packaged runtime verification:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - authenticated `curl -H 'X-API-Key: dummy' http://localhost:8400/api/v1/stats` returned the same `3847 / 642` native-table distribution as the direct Kuzu check
  - `curl http://localhost:3001/api/v1/stats` through the packaged web proxy returned the same `3847 / 642` native-table distribution without browser-side secrets
  - `curl -I http://localhost:3001/` returned `200 OK`
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`

### Residual Note
- The richer local demo graph is now internally consistent with the bootstrap default path, but it is still a local convenience artifact rather than a production-scale graph snapshot.

## 2026-04-17 Session 56 — README Packaged API Sync

### Objective
- Remove the last stale self-hosted access example from `README.md` so it no longer points users at the legacy `localhost:8766/api/rag` path that is not part of the current packaged stack.

### Actions Executed
- Replaced the old README "Agent Integration" example with the current packaged entrypoints:
  - protected API on `http://localhost:8400/api/v1/*`
  - browser-safe local proxy on `http://localhost:3001/api/v1/*`
- Added concrete `search` and `hybrid-search` curl examples that match the current packaged auth model.
- Re-checked the local Docker environment before attempting a fresh third runtime pass.

### Verification
- `README.md` now documents:
  - `curl -H "X-API-Key: your-key" "http://localhost:8400/api/v1/search?..."`
  - `curl -H "X-API-Key: your-key" "http://localhost:8400/api/v1/hybrid-search?..."`
  - `curl "http://localhost:3001/api/v1/search?..."`
- `rg -n "8766|api/rag" README.md` no longer matches the packaged API instructions.
- Docker environment check on 2026-04-17:
  - `docker context show` -> `desktop-linux`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_MISSING`
  - `docker compose up -d` could not proceed because the Docker daemon socket was unavailable in this session.

### Residual Note
- The README was aligned to the current packaged API surface in this session, but at that moment this specific turn could not collect a brand-new runtime proof because the local Docker daemon was unavailable (`~/.docker/run/docker.sock` missing). Session 55 was still the latest successful packaged proof at that point.
  Historical note: this blocker was resolved in Session 57.

## 2026-04-17 Session 57 — README Example Runtime Proof

### Objective
- Close the last verification gap from Session 56 by proving that the new README packaged API examples work against a live local stack rather than only matching the code/docs surface.

### Actions Executed
- Relaunched Docker Desktop after confirming `desktop-linux` was the active context but `~/.docker/run/docker.sock` was missing.
- Waited for the local Docker daemon socket to reappear and confirmed `docker info` succeeded.
- Re-ran the packaged stack with `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`.
- Executed the new README endpoint shapes against the live stack:
  - protected `search` on `:8400`
  - protected `hybrid-search` on `:8400`
  - browser-safe proxied `search` on `:3001`
- Torn the stack back down after verification.

### Verification
- Docker recovery:
  - `open -a /Applications/Docker.app`
  - `test -S ~/.docker/run/docker.sock` transitioned to `SOCKET_PRESENT`
  - `docker info` succeeded against `docker-desktop`
- Packaged runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
- README example proof:
  - `curl -H 'X-API-Key: dummy' 'http://localhost:8400/api/v1/search?q=%E5%A2%9E%E5%80%BC%E7%A8%8E&limit=5'`
    returned `count=5` with non-empty results headed by `TT_VAT` / `TT_LAND_VAT`
  - `curl -H 'X-API-Key: dummy' 'http://localhost:8400/api/v1/hybrid-search?q=%E5%A2%9E%E5%80%BC%E7%A8%8E&limit=5&expand=true'`
    returned `count=5`, `method=hybrid_rrf`, `text_hits=15`, and non-empty `graph_expansion`
  - `curl 'http://localhost:3001/api/v1/search?q=%E5%A2%9E%E5%80%BC%E7%A8%8E&limit=5'`
    returned the same top-5 search results as the protected `:8400` endpoint
  - `docker compose down` completed, and `docker compose ps` returned no running services

### Residual Note
- Session 56's Docker-socket blocker is now cleared. README packaged examples are both textually correct and runtime-verified against the local packaged stack.

## 2026-04-17 Session 58 — Compose Command + Route Index Sync

### Objective
- Remove the last documentation-level drift inside the current self-hosted closeout set: README command syntax should match the validated `docker compose` form, and `doc/index.md` should explicitly advertise the local packaged `:3001` entrypoints.

### Actions Executed
- Replaced remaining `docker-compose` command examples in `README.md` with `docker compose`.
- Added local packaged route entries to `doc/index.md`:
  - `http://localhost:3001/`
  - `http://localhost:3001/api/v1/*`
- Re-ran `docker compose config` after the doc-only sync as a guard that the documented command surface still matches the actual compose file.

### Verification
- `if rg -n 'docker-compose' README.md; then ... else echo README_COMPOSE_CLEAN; fi` -> `README_COMPOSE_CLEAN`
- `rg -n 'http://localhost:3001/|http://localhost:3001/api/v1/\\*' doc/index.md` returned both new packaged route entries
- `docker compose config` exited `0`

### Residual Note
- The self-hosted closeout docs are now internally consistent on command syntax (`docker compose`) and on the local packaged route map (`:3001` web + proxy).

## 2026-04-17 Session 59 — PDCA Packaged Topology Sync

### Objective
- Bring the PDCA canonical docs fully in line with the packaged self-hosted topology, so the project-level PRD / architecture / UX / optimization documents no longer retain any stale `:8766`, `/api/rag`, `docker-compose`, or “Compose only packages the API container” wording.

### Actions Executed
- Updated `PRD.md` current packaging text to include the local `docker compose` package (`:8400` protected API + `:3001` web/proxy).
- Updated `SYSTEM_ARCHITECTURE.md`:
  - renamed the old `Current Architecture (v1.0)` heading to `Historical Prototype Architecture (v1.0)`
  - replaced the stale diagram label `REST /api/rag` with `REST /api/v1/*`
  - added the local packaged topology block (`:3001` web/proxy, `:8400` protected API)
- Updated `USER_EXPERIENCE_MAP.md` Journey 1 from the old `docker-compose` + `:8766` flow to the current `docker compose` + `:3001` / `:8400` first-run path.
- Updated `PLATFORM_OPTIMIZATION_PLAN.md` deployment baseline so it no longer claims Docker Compose only packages the API container.
- Re-rendered the four HTML companions plus `PRD.html`.

### Verification
- `rg -n '8766|/api/rag|docker-compose|packages only the API container' doc/00_project/initiative_cognebula_sota/PRD.md doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md` returned no matches
- `ls -l` confirmed fresh render timestamps for:
  - `PRD.html`
  - `SYSTEM_ARCHITECTURE.html`
  - `USER_EXPERIENCE_MAP.html`
  - `PLATFORM_OPTIMIZATION_PLAN.html`
- Spot check of `USER_EXPERIENCE_MAP.md` now shows:
  - `docker compose up -d --build`
  - `http://localhost:3001/`
  - `http://localhost:8400/docs`
  - `GET /api/v1/search` / `GET /api/v1/hybrid-search`
- Independent verifier scan returned `PASS` with no remaining stale `localhost:8766`, `/api/rag`, or API-only Compose wording in the four PDCA markdown sources

### Residual Note
- The PDCA canonical docs are now aligned to the same packaged topology already verified in Sessions 57-58. Remaining work is no longer doc drift inside the self-hosted lane.

## 2026-04-17 Session 60 — Delivery-Surface Audit

### Objective
- Confirm that the human-facing delivery surface is fully clean after Session 59: not only the markdown PDCA sources, but also the rendered HTML companions and the local Compose runtime state.

### Actions Executed
- Searched the four PDCA HTML companions for stale `:8766`, `/api/rag`, `docker-compose`, and API-only Compose wording.
- Observed a transient Docker daemon disconnect while checking `docker compose ps`.
- Relaunched Docker Desktop, waited for the socket to return, and re-ran `docker compose ps`.

### Verification
- `rg -n '8766|/api/rag|docker-compose|packages only the API container|api container only|packages? only the api' doc/00_project/initiative_cognebula_sota/PRD.html doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.html doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.html doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.html` returned no matches
- Docker recovery:
  - `open -a /Applications/Docker.app`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_PRESENT`
  - `docker info` succeeded again
- Runtime state check:
  - `docker compose ps` returned no running services
- Independent verifier audit on the four HTML companions returned `PASS` and confirmed the delivery surface shows the packaged topology (`docker compose`, `:8400`, `:3001`) rather than any stale `:8766` / `/api/rag` path

### Residual Note
- The self-hosted closeout lane is now clean across markdown, HTML companions, and local Compose runtime state. Remaining work is outside this lane.

## 2026-04-17 Session 61 — Demo Graph Small-Type Expansion

### Objective
- Move the next unresolved mainline item after the self-hosted doc closeout: expand the local richer demo graph with more real small-type business content instead of only FAQ / CPA / incentives / regions / mindmap.

### Actions Executed
- Extended `scripts/bootstrap_local_demo_graph.py`:
  - added `compliance` and `industry` to the supported `--include` set
  - promoted both to the default enrichment path
  - reused `create_accounting_schema.py` as a shared prerequisite for both CPA and industry enrichment so `OP_*` tables exist before insertion
- Rebuilt `data/finance-tax-graph.demo` with `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force`
- Added real local enrichment from:
  - `src/inject_compliance_data.py` -> `ComplianceRule` + `FormTemplate`
  - `src/inject_industry_data.py` -> `FTIndustry` + extra `OP_BusinessScenario` + extra `OP_StandardCase` + `RiskIndicator`
- Re-ran the packaged stack against the rebuilt demo graph and verified both stats and a search query targeting the new compliance/risk surface.

### Verification
- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_compliance_data.py src/inject_industry_data.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,incentives,regions,mindmap}`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4330`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4330`, `edges=642`
  - `FAQEntry=1152`
  - `CPAKnowledge=649`
  - `MindmapNode=990`
  - `ComplianceRule=84`
  - `FormTemplate=109`
  - `FTIndustry=19`
  - `RiskIndicator=125`
  - `OP_BusinessScenario=43`
  - `OP_StandardCase=392`
  - `TaxIncentive=109`
  - `AdministrativeRegion=477`
  - `LawOrRegulation=0`
- Packaged runtime verification:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - authenticated `/api/v1/stats` returned `total_nodes=4330`, `total_edges=642`, `node_tables=23`, and the same enriched node mix
  - `curl 'http://localhost:3001/api/v1/search?q=%E5%90%88%E8%A7%84&limit=5'` returned `count=5` with `RiskIndicator` hits, proving the proxy path can surface the new compliance/risk content
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Residual Note
- This advances the local/demo side of Phase C small-type expansion, but it does not mean the production-scale graph has been backfilled to the same quality level. The main remaining work is still production-scale content depth, not the local packaged demo path.

## 2026-04-17 Session 62 — Seed Reference Expansion

### Objective
- Push the local/demo side of Phase C one step further by injecting three remaining seed-backed small types that already exist in the repo: `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark`.

### Actions Executed
- Added `src/inject_seed_reference_data.py`:
  - creates `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark` tables if missing
  - injects the repo's local seed JSONs
  - generates minimal `description` / `fullText` fields for searchability
- Extended `scripts/bootstrap_local_demo_graph.py`:
  - added `seedrefs` to the supported/default `--include` set
  - wired it to call `src/inject_seed_reference_data.py`
- Rebuilt `data/finance-tax-graph.demo` with the expanded default path
- Re-ran the packaged stack and tested search queries aimed at the new seed-backed types

### Verification
- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_seed_reference_data.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap}`
- `python3 src/inject_seed_reference_data.py --dry-run` reported:
  - `+138` `SocialInsuranceRule`
  - `+50` `TaxAccountingGap`
  - `+45` `IndustryBenchmark`
  - grand total `+233`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4563`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4563`, `edges=642`
  - `SocialInsuranceRule=138`
  - `TaxAccountingGap=50`
  - `IndustryBenchmark=45`
  - `ComplianceRule=84`
  - `FormTemplate=109`
  - `FTIndustry=19`
  - `RiskIndicator=125`
  - `OP_BusinessScenario=43`
  - `OP_StandardCase=392`
- Packaged runtime verification:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - authenticated `/api/v1/stats` returned `total_nodes=4563`, `total_edges=642`, `node_tables=26`, and the same seed-expanded node mix
  - `curl 'http://localhost:3001/api/v1/search?q=%E5%85%BB%E8%80%81%E4%BF%9D%E9%99%A9&limit=5'` returned `SocialInsuranceRule` hits
  - `curl 'http://localhost:3001/api/v1/search?q=%E7%A8%8E%E8%B4%9F%E7%8E%87&limit=5'` returned `IndustryBenchmark` hits
  - `curl 'http://localhost:3001/api/v1/search?q=%E9%A2%84%E6%94%B6%E8%B4%A6%E6%AC%BE&limit=5'` returned `TaxAccountingGap` hits
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Residual Note
- The local/demo side of Phase C now covers both extracted content and seed-backed reference types, but the production-scale graph still has not been brought up to the same small-type coverage level.

## 2026-04-23 — Data-quality page reframed around ontology conformance

### Observation
- The page could show `quality_score=100` while the ontology remained structurally broken (`/api/v1/ontology-audit` already documented rogue types, over-ceiling drift, V1/V2 coexistence, duplicate clusters, and legacy residue).
- This created a dangerous false positive: operators saw “质量评分 100 / 等级 A” and inferred the graph was usable even when catch-all buckets such as `KnowledgeUnit` were swallowing heterogeneous content.

### Root cause
- `web/src/app/expert/data-quality/page.tsx` only consumed `/stats` + `/quality` and elevated coverage / density to the top KPI strip.
- Structural drift data already existed in the repo (`/api/v1/ontology-audit`, `ONTOLOGY_DRIFT_REPORT.md`) but never reached the operator UI.

### Fix
- Added `getOntologyAudit()` and typed `OntologyAudit` support to `web/src/app/lib/kg-api.ts`.
- Reworked `data-quality/page.tsx` so the page:
  - loads `/stats`, `/quality`, and `/ontology-audit` with `Promise.allSettled`
  - shows a structural-failure hero card before hygiene metrics
  - promotes rogue counts, dominant bucket share, V1/V2 bleed, duplicate clusters, legacy tables, and rogue edges into first-class risk cards
  - demotes coverage metrics to “基础卫生指标”
- Updated PDCA docs so the product contract now says “data quality = structure + hygiene”.

### Evidence / blockers
- `Computer Use` plugin could not be used for live visual inspection in this session (`Transport closed` on `list_apps` / `get_app_state`).
- Direct unauthenticated fetch of `https://ops.hegui.org/expert/data-quality/` returned `401 Authorization Required`, so browser-shell proof for the live protected page remains a follow-up item.

### Live production snapshot (fetched 2026-04-23 from `https://app.hegui.org/api/v1/*`)
- `/stats`: `total_nodes=547,761`, `total_edges=1,302,476`, `node_tables=62`, `rel_tables=73`
- Dominant bucket: `KnowledgeUnit=185,455` (`33.9%` of all live nodes)
- Other oversized legacy / drift buckets visible in TOP-15: `DocumentSection=42,252`, `LawOrRegulation=39,651`, `MindmapNode=28,526`, `CPAKnowledge=7,371`
- `/quality`: `score=100 PASS`, `content_coverage=51.0%`, `edge_density=2.795`
- `/ontology-audit`: `verdict=FAIL`, `severity=high`, `live_count=83`, `canonical_count=35`, `over_ceiling_by=46`
- Confirmed drift buckets:
  - `v1_v2_bleed=5`
  - duplicate clusters: `tax_rate`, `accounting`, `industry`, `policy`
  - `saas_leak=6`
  - `legacy=7`

## 2026-04-24 — UI/UX hardening for the data-quality workbench

### UX diagnosis
- The old page behaved like a report: six same-weight KPI cards, a long bar chart, a methodology wall of text, then Clause Inspector at the bottom.
- That made the core task ambiguous. Operators could see `100` and `51%`, but the UI still did not answer the operational question: "what do I do first?"

### Design baseline applied
- App-shell utility mode: no decorative hero, no marketing structure, utility-first content order
- Single page-level primary action: jump directly to the治理优先级 lane
- 8pt/4pt spacing discipline via `page.module.css`
- Surface hierarchy by background step + border + shadow, not heavy ornament
- Responsive breakpoints at 1280 / 960 / 720
- A11y/testability: stable `data-testid`s, details/summary disclosure, keyboard smoke captured against the fixture route

### Implementation
- `web/src/app/expert/data-quality/page.tsx`
  - extracted a reusable `DataQualityWorkbench`
  - converted the page into a task-first layout: verdict hero, operator flow rail, metric strip, governance lane, distribution evidence, risk breakdown, hygiene panel, inspector shell
  - added lightweight `cognebula:data-quality` custom-event tracking for load and CTA interactions
- `web/src/app/expert/data-quality/page.module.css`
  - centralized spacing, layout, responsive, skeleton, and section styles
- `web/src/app/expert/data-quality/prodSnapshot.ts`
  - stored a production-derived snapshot from 2026-04-23 (`app.hegui.org`) for validation use
- `web/src/app/expert/data-quality/fixture/page.tsx`
  - exposed `/expert/data-quality/fixture` as a stable validation surface
- `web/src/app/expert/layout.tsx`
  - removed stale hard-coded graph counts from the shell top bar and replaced them with trust-safe environment status text

### Validation summary
- Lint: pass
- TypeScript: pass (source-only tsconfig override to ignore transient `.next/dev` validator corruption)
- Build: pass
- Fixture smoke: no console errors, no `/api/v1/*` requests, no secret-bearing URLs, primary CTA scrolls governance lane into view, secondary CTA scrolls inspector into view, keyboard tab lands inside inspector controls
- Lighthouse: performance `76`, accessibility `96`, best-practices `100`, SEO `100`
- Main budget pressure: LCP `7.4s`; TBT `10ms`; CLS `0`

## 2026-04-27 — Schema-completeness gate wired into nightly tier

### Continuation of Sprint A+B+C close-out

Sprint commit `4956d5b` ("schema-vs-audit drift test — close the 102K-suite escape") added `tests/test_schema_completeness.py` (17 tests, 6 pass + 11 fail by design) but did NOT wire it into `scripts/run_data_quality_tests.sh`. CI's `unit` job picks it up via default pytest discovery; local-dev tier-runner did not. Closing that visibility gap.

### What was changed
- `scripts/run_data_quality_tests.sh`: added `tests/test_schema_completeness.py` to `NIGHTLY_FILES`. Not added to `fast` or `standard` because the 11 designed-failures are a HITL forcing function (pending Plan A/B/C/D from `2026-04-27-p1.5-jurisdiction-recon-memo.md`); blocking PR-tier on a known-pending HITL would silence rather than amplify the signal.

### Verification
- `./scripts/run_data_quality_tests.sh count`:
  - fast: 163 tests (unchanged)
  - standard: 1,582 tests (unchanged)
  - nightly: 5,832 → 5,849 (+17 = `test_schema_completeness.py`)
- Direct run `pytest tests/test_schema_completeness.py -v`: 11 fail / 6 pass / 0.13s — matches design comment "DAY-1 EXPECTATION: these tests FAIL — that's the signal that schema sync is needed".

### Failure inventory (the signal)
The 11 designed failures fall into two classes:
- 8 × `test_audited_lineage_column_appears_in_at_least_one_canonical_type[<col>]`: snake_case columns `effective_from`, `confidence`, `extracted_by`, `jurisdiction_code`, `jurisdiction_scope`, `override_chain_id`, `reviewed_by`, `source_doc_id` — ZERO of 31 canonical types declare them. PROD has them via runtime ALTER TABLE that was never back-ported.
- 3 × `test_partial_attribution_types_declare_source_doc_id[<type>]`: `LegalClause`, `FilingFormField`, `TaxCalculationRule` carry `source_doc_id` in PROD (corpus regression discovered) but canonical schema is silent.

### What is NOT changed
- No edit to `schemas/ontology_v4.2.cypher`. Schema sync is HITL — the recon memo holds Plan A/B/C/D pending Maurice. Reconciliation is what flips these tests green; doing it autonomously would mask the forcing function.
- No edit to `pytest.ini`, no `xfail` markers added. The CI `unit` job is intentionally RED until reconciliation. Adding `xfail(strict=True)` is a design call (signal vs blocking) and belongs to Maurice.
- No PDCA stat bump (`Final test suite status` table still says 11 files / 5,832 IDs). The PDCA was synced before `test_schema_completeness.py` landed; refreshing the table is a separate housekeeping task.

### Deferred items (logged here, not asked)
1. **HITL Plan A/B/C/D selection** — `outputs/reports/data-quality-audit/2026-04-27-p1.5-jurisdiction-recon-memo.md`. Once Maurice picks, schema sync can proceed and the 11 failing tests flip green.
2. **PDCA `Final test suite status` refresh** — bump 11→12 files, 5,832→5,849 IDs, ~3,700→~4,000 LOC. Sync `.md` and `.html` together per 2份制.
3. **xfail policy decision** — option (a) keep CI RED as forcing function, option (b) add `xfail(strict=True, reason="HITL pending P1.5")` to unblock PR-tier while preserving the signal. Recommend (b) once HITL has an ETA.

## 2026-04-27 — Sprint D: mutation expansion (4 → 8 machines)

### Why
Sprint B (the flagship mutation axis) covered only 3 of 9 audit dimensions in single-axis machines (placeholder / duplicate_id / null_coverage) plus 1 compound. Six dimensions had ZERO single-axis path-independence verification. Plus the cross-dimension orthogonality property — "mutating dimension A leaves dimension B count untouched" — had no test. Sprint D closes both gaps.

### What was added (`tests/test_data_quality_mutation.py`)
- `StaleMutationMachine` (400 × 50, 2 invariants) — toggle `effective_from` between fresh/stale/null/alternate-fresh; verify `stale_count` matches the tracked stale-index set, and `stale_rate` stays consistent. Caught a bug in my first pass: `_is_stale` uses `timedelta(days=10*365) = 3650 days` (not 10 calendar years), so the threshold lands ~2-3 days after 10y due to leap-day drift; my "borderline" date `2014-06-02` was actually stale by 1 day. Replaced with an unambiguous `2018-06-01` second fresh date.
- `IntegrityViolationMutationMachine` (400 × 50, 1 invariant) — independently toggle `reviewed_at` and `reviewed_by`; verify `integrity_violations` matches `bool(at) ^ bool(by)` per row.
- `JurisdictionMismatchMutationMachine` (400 × 50, 1 invariant) — toggle `jurisdiction_code` / `jurisdiction_scope`, plus inject invalid scope (`galactic`); verify count matches the audit's actual rule (scope set + not in ALLOWED → +1, else XOR(code, scope) → +1).
- `OrthogonalityMachine` (400 × 50, 2 invariants) — non-overlapping field-routing per dim (placeholder→`extracted_by` / duplicate→`id` / stale→`effective_from` set to old date NOT None / integrity→`reviewed_by`→None / null_coverage→`confidence`→None). Invariant: dimensions NOT in `expected_pos` stay at baseline 0. Plus static-zero invariant for `jurisdiction_mismatches`/`prohibited_role_count`/`invalid_chain_count`/`inconsistent_scope_count` (no rule mutates them; should always be 0).

### Cumulative state (Sprint B + D)
- 8 mutation machines, ~170,000 mutation steps, ~345,000 invariant evaluations, 34s runtime
- Nightly tier: 5,849 → 5,853 IDs (+4 TestCase classes)
- Test files: 11 → 12 (`test_schema_completeness.py` from earlier today + this expansion stays inside the existing mutation file)
- Effective cases: ~102K → ~222K

### Failure mode caught at write-time
First pass had `BORDERLINE_DATE = "2014-06-02"` based on naïve "10 years before today" math. Hypothesis found the falsifying example on the first run (`make_borderline(row_idx=0)` → `stale_count=1, expected=0`). Lesson: Python's `timedelta(days=N)` is days-exact, not calendar-aware; never pick test boundary dates without computing them from the actual code's threshold. Fix shipped the same iteration; no follow-up debt.

### Out of scope (deferred)
- Single-axis machines for `prohibited_role` / `invalid_chain` / `inconsistent_scope` — these dimensions delegate to `clause_inspector.inspect()` which expects specific row-shape inputs that don't fit the `_clean_row` baseline cleanly. Building proper test fixtures for clause-axis defects is a separate sprint (E?) bounded by the inspector's own contract.
- New audit dimensions (P4 orphan_fk_count) — product-level call, still pending.
- HITL Plan A/B/C/D for jurisdiction backfill — still pending.

---

## 2026-04-27 — Sprint E1+E2: property invariants +3 + first clause-axis mutation machine

Sprint E was scoped under "队列全部执行" MVS-pattern (each slice 30-90 min, vertical, with regression gate + explicit deferred-half log). Two slices shipped: S7.2 (Sprint E1, property invariants) and S7.3 (Sprint E2, prohibited_role mutation machine). Sprint D's deferred clause-axis machines are now PARTIALLY shipped — prohibited_role is done; invalid_chain and inconsistent_scope remain deferred (logged below).

### Sprint E1 — property invariant +3 (5 test methods, commit `73ba8b3`)

3 conceptual invariants materialized as 5 test methods at `@settings(max_examples=300)`:

| Invariant class | Methods | What it proves |
|-----------------|---------|----------------|
| `TestIdempotence` | `test_survey_type_is_pure_function` + `test_survey_type_does_not_mutate_input` | Calling survey_type twice on the same input yields the same output; input rows are not mutated in-place. |
| `TestDefectsUpperBound` | `test_defects_total_is_bounded` + `test_per_dimension_counts_bounded_by_sampled` | defects_total ≤ 11×sampled + |CRITICAL_COLUMNS|; per row-axis dim ≤ sampled. Catches a future audit-dim addition that double-counts. |
| `TestDefectsMonotoneAddOnly` | `test_adding_row_does_not_decrease_non_global_dims` | Adding a row with a unique id never decreases row-axis dim counts. Excludes `duplicate_id_count` because that dimension can swing under add-only mutation. |

Verification: `pytest tests/test_data_quality_property.py -q` → `24 passed in 6.12s` (was 19 functions → +5 methods).

Lesson: **+N invariants ≠ +N test methods.** The plan said "+3 IDs"; reality was +5 IDs. Same estimate→measurement category as Slice S7.1's `~45s` vs `42.56s` correction (caught by Hickey R2 in the swarm trace). Logged in commit message so the discrepancy is auditable.

### Sprint E2 — prohibited_role mutation machine (Machine 9, commit `bed5bfb`)

First clause-axis mutation machine. 400 × 50, 5 rules + 1 invariant.

Anchor values from the registry:
- **Prohibited**: `analogy` (类推适用) — `prohibited_in_tax_law=True` per 税收法定 (CN tax law explicitly bars reasoning by analogy to create or extend tax liability)
- **Clean**: `yiju` (依据, statutory basis) + `shouquan` (授权, delegated authority)

Two distinct clean roles avoid Sprint D's single-clean blind spot — same lesson as `make_alt_fresh` after the BORDERLINE_DATE bug. Hypothesis exercises both clean→clean (`yiju↔shouquan`) and prohibited→clean (`analogy↔yiju`/`shouquan`) transitions.

Verification:
- `pytest tests/test_data_quality_mutation.py -q` → `9 passed in 38.50s` (was 8 → +1 machine)
- nightly count → 5,858 → 5,859 (+1 ID, exactly as predicted)
- nightly wall-clock → 42.56s → 48.58s (+6.02s, all Sprint E delta combined)

Coverage delta: mutation testing now covers **7 of 9** audit dimensions (was 6 of 9 post-Sprint-D). Static-zero invariant in `OrthogonalityMachine` still listed `prohibited_role_count` as zero — that's correct because OrthogonalityMachine's field-routing matrix doesn't touch `argument_role`, so the new ProhibitedRoleMutationMachine doesn't conflict.

### Out of scope (Sprint E deferred half, logged not asked)

- `invalid_chain` mutation machine — needs `validate_chain_id` fixture data + `override_chain_id` + `override_chain_parents` truth-table; non-trivial setup
- `inconsistent_scope` mutation machine — needs `_check_consistency` truth-table for jurisdiction code/scope pairs (which `JurisdictionMismatchMutationMachine` already partially exercises but at row-axis only, not clause-axis) [STATUS UPDATE 2026-04-27 evening: shipped via Sprint F1 — see entry below]
- More property invariants (commutativity under restore, hash stability of placeholder-per-field, sample-size scaling) — Sprint F candidate
- New audit dimensions (P4 orphan_fk_count) — product-level call, still HITL
- HITL Plan A/B/C/D for jurisdiction backfill — still HITL

---

## 2026-04-27 — Sprint F1: inconsistent_scope clause-axis machine (8/9 mutation coverage)

After Sprint E2 closed prohibited_role at 7/9 dims, Sprint F1 ships the second clause-axis mutation machine, picked under MVS-pattern budget (60-min slice). Selected over `invalid_chain` because `_check_consistency` has a known 3-row truth table (national / iso_admin / special_zone) that fits inside 90 min; `invalid_chain` requires chain_id traversal fixtures (orphan / cycle / version drift) that don't.

### Sprint F1 — InconsistentScopeMutationMachine (Machine 10, commit `984f1d5`)

400 × 50, 3 mutation rules + 2 invariants.

Anchor pairs (decision-table from `src/kg/jurisdiction_consistency.py:54-95`):
- **Consistent baseline**: `(CN, national)` — national kind expects scope=national ✓
- **Inconsistent #1**: `(CN, subnational)` — national kind, scope mismatch (subnational still in `ALLOWED_JURISDICTION_SCOPES`)
- **Inconsistent #2**: `(CN-31, national)` — iso_admin kind expects {subnational, municipal}, national still whitelisted

Why these specific pairs: every state simultaneously passes row-axis (`_count_jurisdiction_mismatches` returns 0 because scope ∈ whitelist + both fields set so XOR is False) AND triggers clause-axis (`_check_consistency` returns verdict==`inconsistent`, which `clause_inspector.inspect()` translates to `inconsistent_code_scope` flag, which `_clause_defect_counts` increments into `inconsistent_scope_count`). This means the row-axis dim stays at 0 throughout, making the orthogonality contract testable.

Two invariants:
1. `inconsistent_scope_count == |inconsistent_indexes|` (the standard count-match invariant)
2. `jurisdiction_mismatches == 0` for ALL reachable states (the **explicit orthogonality contract** — a clause-axis machine must not leak into the row-axis counter; if this ever fails, a future code change accidentally coupled the two axes)

The 2nd invariant is the design move that elevates this machine above pattern-duplication of Sprint E2. Without it, the machine is just "another single-axis machine"; with it, it's a forcing function against future cross-axis coupling regressions.

`null_scope` rule INTENTIONALLY DROPPED: setting `jurisdiction_scope=None` makes row-axis XOR fire (code set, scope unset), contaminating the row-axis-zero invariant. Mixed clause+row concern logged as Sprint F2 candidate (separate machine — not a rule of this machine).

Verification:
- `pytest tests/test_data_quality_mutation.py -q` → `10 passed in 42.34s` (was 9 → +1 machine)
- nightly count → 5,859 → 5,860 (+1 ID, exactly as predicted)
- nightly wall-clock → 48.58s → 53.30s (+4.72s for the new machine)

Coverage delta: mutation testing now covers **8 of 9** audit dimensions. Remaining uncovered: `invalid_chain` (Sprint F2 candidate, requires chain_id fixtures).

### Out of scope (Sprint F1 deferred half, logged not asked)

- `invalid_chain` mutation machine — needs `validate_chain_id` traversal fixtures (orphan / cycle / version drift modes); Sprint F2 candidate
- `unknown_jurisdiction_code` machine — different flag (`unknown_code` verdict, NOT `inconsistent`), different counter; separate Sprint
- null_scope mixed-concern machine — clause+row joint test (would simultaneously increment `inconsistent_scope_count` AND `jurisdiction_mismatches`); Sprint F2 candidate
- Cross-axis machine running row-axis `JurisdictionMismatchMutationMachine` and clause-axis `InconsistentScopeMutationMachine` simultaneously, asserting they never double-count the same defect; Sprint F3 candidate
- More property invariants (commutativity / hash stability / sample-size scaling) — Sprint F4 candidate
- HITL Plan A/B/C/D, P4 orphan_fk_count, xfail policy — unchanged HITL items
