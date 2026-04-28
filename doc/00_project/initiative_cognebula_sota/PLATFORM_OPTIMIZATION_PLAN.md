# CogNebula Enterprise -- Platform Optimization Plan

> Version: 0.3 (Updated) | Last updated: 2026-04-23

## Current Baseline
- **Parsing**: Python AST (robust) + JS/TS regex (fragile, misses complex patterns)
- **Scale**: ~20k files in ~10s (single-threaded, adequate for medium repos)
- **RAG**: Hybrid retrieval live (`/api/v1/hybrid-search`: text + vector + graph)
- **Deployment**: Single VPS + static Next.js export + Cloudflare Worker HTTPS proxy; `docker compose` package now runs the protected API on `:8400` plus the static web/proxy surface on `:3001`, but requires explicit real DB/Lance mounts and refuses demo/archived/empty KG paths
- **Tenant Isolation**: Per-repo KuzuDB directory (basic, no gateway enforcement)
- **Agent Interface**: REST API + browser-safe HTTPS proxy + MCP with 7 tools

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
| Auth | API key middleware + Worker-side secret injection | JWT + GitHub App | API Gateway + ephemeral tokens |
| Tenant Isolation | File-level | Gateway-enforced | Tenant router + per-repo DB |
| MCP Tools | 7 basic | 12+ SOTA | blast_radius, semantic_search, trace_deps |

### P2: Competitive Edge
| Target | Current | Goal | Approach |
|--------|---------|------|----------|
| NL2Graph | None | Natural language -> Cypher | LLM-powered query translation |
| Context Windowing | Full dump | Tiered Degradation | Depth 0=body, 1=signature, 2=name |
| Language Coverage | py/js/ts | +java/go/rust/c++ | Tree-sitter grammars |

## Updated Priorities (2026-04 SOTA Refresh)

Previous priorities assumed code intelligence platform. Updated for domain KG:

### P0: Immediate (MCP window closing)
| Target | Current | Goal | Approach | SOTA Reference |
|--------|---------|------|----------|----------------|
| MCP Server | None | Agent-native API | Expose graph queries as MCP tools | Neo4j Aura Agent GA, Augment MCP GA |
| KuzuDB assessment | Original (archived) | Stable engine | Evaluate Vela fork; fallback to FalkorDB | KuzuDB archived Oct 2025 |
| Published benchmark | Hybrid benchmark live (79% overall, 100/100 pass) | Trust signal | 100 curated Q&A pairs, measure accuracy | Augment "+80%, 300+ PR" benchmark |

### P1: Quality & Content (competitive moat)
| Target | Current | Goal | Approach | SOTA Reference |
|--------|---------|------|----------|----------------|
| Embedding gap | 328K/620K | Full coverage | Fill remaining 289K vectors | LanceDB embedded vector, <20ms |
| Content freshness | Daily crawl | < 7 day lag | Fix chinatax anti-bot, add more sources | Augment "real-time indexing" |
| M3 stability | Segfault-prone | Zero crash | KU_ABOUT_TAX fixed; 500-write checkpoint | Session 38 fix |
| Data Quality Gate | `100/100` hygiene but structural drift still visible | Hygiene > 90 **and** structural gate PASS | Surface `/ontology-audit` in operator UI; canonical cleanup before trusting `/quality` | MS GraphRAG 92% entity extraction |

### P2: Enterprise Readiness (for yiclaw integration)
| Target | Current | Goal | Approach | SOTA Reference |
|--------|---------|------|----------|----------------|
| Auth | API key live; browser-safe proxy now aligned | API key + JWT | API Gateway for yiclaw agent access + Worker secret management | GitLab RBAC, Augment SSO |
| Deployment | Single VPS + static export + Worker proxy | Customer-ready self-hosted package | Package the current auth/proxy topology for customer self-hosting | 5/6 enterprise tools support on-prem |
| Hybrid RAG | `/api/v1/hybrid-search` live | Stronger vector + graph orchestration | LanceDB/LightRAG tuning for semantic entry and expansion quality | Neo4j + LanceDB hybrid validated |

## Metrics & KPIs

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Nodes | 368,910 live prod (2026-04-28) | 1M+ | `/api/v1/quality::metrics.total_nodes` |
| Edges | 1,014,862 live prod (2026-04-28) | 2M+ | `/api/v1/quality::metrics.total_edges` |
| Hygiene Score | 100/100 | > 90/100 | `/api/v1/quality` |
| Structural Conformance | FAIL when rogue / over-ceiling drift persists | PASS | `/api/v1/ontology-audit` |
| LanceDB rows | 118,011 live prod (2026-04-28) | > 95% node coverage after next rebuild | `/api/v1/health::lancedb_rows` |
| M3 success rate | ~50% (segfaults) | > 95% | cron log analysis |
| Content sources | 5 | 10+ | Active crawler count |
| MCP tools | 0 | 6+ | Exposed tool count |
| Agent perf lift | 79% hybrid benchmark baseline | > 30% | `benchmark/run_eval.py --mode hybrid` |

## Risk Register (updated 2026-04)

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|-----------|------------|--------|
| KuzuDB no longer maintained | CRITICAL | CERTAIN | Vela fork evaluation + FalkorDB migration path | MONITORING |
| MCP adoption window closing | HIGH | HIGH | Ship MCP server as next engineering task | PLANNED |
| M3 pipeline segfaults | HIGH | MEDIUM | KU_ABOUT_TAX fixed Session 38; 500-write checkpoint | MITIGATED |
| Chinatax anti-bot blocks | MEDIUM | HIGH | Cookie-refresh retry; diversify sources | PARTIAL FIX |
| 8GB VPS memory limit | MEDIUM | MEDIUM | WAL checkpoint v2; consider VPS upgrade | MITIGATED |
| Benchmark drift after retrieval changes | MEDIUM | MEDIUM | Re-run hybrid benchmark after search/edge changes | MITIGATED |

---

Maurice | maurice_wen@proton.me
