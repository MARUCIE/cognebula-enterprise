# CogNebula Enterprise -- Platform Optimization Plan

> Version: 0.1 (Draft) | Last updated: 2026-03-03

## Current Baseline
- **Parsing**: Python AST (robust) + JS/TS regex (fragile, misses complex patterns)
- **Scale**: ~20k files in ~10s (single-threaded, adequate for medium repos)
- **RAG**: Graph-only (no vector/semantic layer)
- **Deployment**: Docker Compose (API + placeholder Worker + Redis)
- **Tenant Isolation**: Per-repo KuzuDB directory (basic, no gateway enforcement)
- **Agent Interface**: MCP with 7 tools (basic query/context/impact)

## Optimization Targets (informed by SOTA research)

### P0: Critical Path
| Target | Current | Goal | Approach |
|--------|---------|------|----------|
| JS/TS Parsing | Regex | Tree-sitter | Universal parser with error recovery |
| Hybrid RAG | Graph-only | Vector + Graph | LanceDB semantic entry -> KuzuDB blast radius |
| Worker | Sleep loop | Redis consumer | Real incremental sync per commit |

### P1: Enterprise Ready
| Target | Current | Goal | Approach |
|--------|---------|------|----------|
| Auth | None | JWT + GitHub App | API Gateway + ephemeral tokens |
| Tenant Isolation | File-level | Gateway-enforced | Tenant router + per-repo DB |
| MCP Tools | 7 basic | 12+ SOTA | blast_radius, semantic_search, trace_deps |

### P2: Competitive Edge
| Target | Current | Goal | Approach |
|--------|---------|------|----------|
| NL2Graph | None | Natural language -> Cypher | LLM-powered query translation |
| Context Windowing | Full dump | Tiered Degradation | Depth 0=body, 1=signature, 2=name |
| Language Coverage | py/js/ts | +java/go/rust/c++ | Tree-sitter grammars |

## Metrics & KPIs
(to be refined after SOTA research)

## Risk Register
(to be refined after SOTA research)

---

Maurice | maurice_wen@proton.me
