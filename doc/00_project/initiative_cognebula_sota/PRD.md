# CogNebula SOTA Enterprise Context Brain - PRD

> v2.0 -- Updated 2026-03-03 based on SOTA Product SOP Benchmarking (20+ products, 4 domains, 60+ sources)

## 1. Objective

Transform CogNebula from a high-performance local developer tool into the industry-standard, out-of-the-box **Enterprise Context Brain for AI Agents**. It will serve as the structural memory and blast-radius analysis engine for any LLM-powered software engineering agent, enabling them to operate safely in large corporate codebases.

## 2. Scope

### In Scope
- Graph engine migration (KuzuDB -> Memgraph/Neo4j) due to KuzuDB archival
- Hybrid RAG: LanceDB (vector entry) + Graph DB (structural traversal)
- Universal Tree-sitter parsing (40+ languages, replacing regex/AST hybrid)
- MCP Server for agent consumption (table stakes per SOTA benchmarking)
- Real-time incremental indexing (<5s updates)
- Multi-tenant shared-nothing isolation
- RBAC + SSO/SAML + audit trails
- Helm charts + Docker Compose deployment

### Non-Goals
- IDE plugin/extension (CogNebula is backend infrastructure, not UI)
- Code generation (validation/context provider only, per Greptile's philosophy)
- Autonomous agent orchestration (provide brain, not orchestrator)
- Mobile/desktop client applications

## 3. Competitive Positioning

Based on SOTA benchmarking (Mar 2025 - Mar 2026):

| Competitor | Their Strength | CogNebula Differentiation |
|-----------|---------------|--------------------------|
| Sourcegraph Cody | Legacy monorepo search (54B+ lines) | Graph-first (not search-first), blast radius analysis |
| Greptile v3 | 82% bug catch rate, validation-only | Structural graph context (not just review), multi-tenant |
| GitHub Copilot | Platform integration, agentic DevOps | Neutral backend brain (not GitHub-locked), self-hosted |
| Augment Code | 400K+ file semantic indexing | Open-source, self-hosted, graph + vector hybrid |
| Neo4j | Enterprise graph with RBAC | Code-specialized (not generic graph), embedded-first |

**Unique positioning**: API-first, neutral backend brain with graph-native code intelligence. Unlike Sourcegraph (closed UI) or Neo4j (generic graph, heavy Java), CogNebula is purpose-built for code structure and agent consumption.

## 4. Product Packaging & Out-of-the-box Experience

- **Deployment Tiers**:
  - MVP: Docker Compose for