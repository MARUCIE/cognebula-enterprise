# CogNebula Enterprise -- PRD

> v3.1 -- Updated 2026-04-23 based on 2-round SOTA benchmarking (25+ products, 4 domains, 80+ sources)

## 1. Objective

CogNebula is a **domain knowledge graph for AI agents** — currently serving the finance/tax compliance domain from the live production KG (**368,910 nodes, 1,014,862 edges, 118,011 LanceDB rows verified 2026-04-28**). It provides structured regulatory knowledge (laws, regulations, interpretations, tax rates, compliance rules) to LLM-powered agents via REST API, a browser-safe HTTPS proxy for static web surfaces, with MCP Server as the priority integration path.

Unlike code intelligence platforms (Sourcegraph, Augment, Cursor), CogNebula applies the same validated architecture (graph + RAG + MCP) to **regulated domain knowledge** — a market with zero direct competitors.

## 2. Scope

### In Scope
- MCP Server for agent consumption (P0 — competitive window closing)
- KuzuDB sustainability assessment (archived Oct 2025; Vela fork or FalkorDB migration)
- Hybrid RAG: vector entry + graph traversal for tax law retrieval
- Published benchmarks for trust-building (query accuracy, latency, coverage)
- Dual quality gates for compliance verification workflows: `/api/v1/quality` (content hygiene) + `/api/v1/ontology-audit` (canonical structure / drift)
- Daily pipeline automation (M3 orchestrator, crawl, enrichment)
- Validation surfaces for release readiness: responsive screenshots, fixture-backed visual regression, and browser smoke against a production snapshot

### Non-Goals
- Code intelligence (separate market; Sourcegraph/Augment/Cursor own this)
- IDE plugin/extension (CogNebula is backend infrastructure)
- Autonomous agent orchestration (provide knowledge brain, not orchestrator)
- Generic graph DB product (domain-specific, not competing with Neo4j)

## 3. Competitive Positioning

Based on SOTA benchmarking (Mar 2025 - Apr 2026, 25+ products):

**Market 1: Code Context Engines (reference, not competitors)**

| Platform | Architecture | MCP | CogNebula Takeaway |
|----------|-------------|-----|-------------------|
| Augment Code | Semantic dependency graph | GA (Context Engine MCP) | Same architecture pattern, different knowledge domain |
| Sourcegraph Amp | Code graph + vector hybrid | Not public | Graph+vector hybrid is validated at scale |
| GitLab Duo | Knowledge Graph (Rust) | N/A | Enterprise code graph validates the approach |
| Qodo | Context Engine + agentic RAG | N/A | Multi-agent + domain graph is the direction |

**Market 2: Domain Knowledge Graphs (CogNebula's market)**

| Dimension | CogNebula | Nearest Analog |
|-----------|-----------|---------------|
| Domain | Finance/tax (856K nodes, 18 tax types, 2.0M+ edges) | None (greenfield) |
| Architecture | KuzuDB embedded graph + Gemini enrichment | Snyk DeepCode (same pattern: domain AI + structured knowledge) |
| Agent integration | REST API + HTTPS proxy + MCP | Neo4j Aura Agent (MCP GA, but generic graph) |
| Content pipeline | Daily crawl + M3 orchestrator + quality gate | No equivalent in domain KG space |

**Unique positioning**: The only structured, graph-native knowledge base for AI agents operating in Chinese finance/tax compliance. Competitors offer generic graph DBs (Neo4j) or code-specific graphs (Augment); none provides domain-specific regulatory knowledge with compliance semantics.

## 4. Product Packaging

- **Current**: FastAPI server (port 8400) + live Kuzu/Vela graph on contabo + static Next.js frontend + Cloudflare Worker HTTPS proxy + explicit-only `docker compose` package (`:8400` protected API, `:3001` static web/proxy) + daily pipeline on VPS. The packaged API no longer defaults to demo, archived, or empty local KG data; real DB/Lance mounts are required, and local development should use the Tailscale REST API at `http://100.88.170.57:8400`.
- **Current**: The operator-facing data-quality page now treats ontology conformance as the primary gate and coverage metrics as secondary hygiene signals. A validation-only production-snapshot route keeps the page testable without depending on live auth/network.
- **Next**: Harden the browser-safe proxy path, keep benchmark green, and align self-hosted packaging with the current auth model
- **Target**: Customer-facing self-hosted package with protected API, static frontend, and documented proxy/auth bootstrap
