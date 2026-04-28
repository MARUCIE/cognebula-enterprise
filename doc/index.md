# CogNebula Enterprise -- Documentation Index

> PROJECT_DIR: `/Users/mauricewen/Projects/27-cognebula-enterprise`
>
> **Last topology contract update**: 2026-04-28 — `SYSTEM_ARCHITECTURE.md` §5 **Two-Frontend Topology** (symmetric-write mirror of canonical authoring at `MARUCIE/30-lingque-agent` SYSTEM_ARCHITECTURE.md §1.3 ; CogNebula owns 1 of 2 frontends, `hegui.io`). Boundary correction commits: `49b83c2` (.md) + `58a98d0` (.html) + `e44ddcf` (deliverable.md symmetric-write). Future updates to the topology contract MUST update both repos in the same task per `task_plan.md` §21.2.A3.

## Project Path Index

| Path | Description |
|------|-------------|
| `/Users/mauricewen/Projects/27-cognebula-enterprise` | PROJECT_DIR (git root) |
| `kg-api-server.py` | Production FastAPI service |
| `benchmark/run_eval.py` | Hybrid/search benchmark runner |
| `scripts/build_semantic_edges.py` | Semantic edge generation + bulk load |
| `web/src/app/` | Next.js app router UI |
| `docker-compose.yml` | Self-hosted package: API + static web reverse proxy topology |
| `worker/src/index.ts` | Cloudflare Worker HTTPS proxy for static web → protected KG API |
| `Dockerfile` | API container build |
| `data/` | KG data, LanceDB, CSV artifacts |
| `doc/00_project/initiative_cognebula_sota/` | Current project planning + evidence docs |

## Documentation Map

| Document | Path | Status |
|----------|------|--------|
| PRD | `doc/00_project/initiative_cognebula_sota/PRD.md` | Updated + HTML companion |
| System Architecture | `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md` | Active + HTML companion ; §5 **Two-Frontend Topology** mirrored from lingque-agent §1.3 (boundary correction 2026-04-28, see header note above) |
| User Experience Map | `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md` | Updated + HTML companion |
| Platform Optimization | `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md` | Updated + HTML companion |
| Task Plan | `doc/00_project/initiative_cognebula_sota/task_plan.md` | Active |
| Notes | `doc/00_project/initiative_cognebula_sota/notes.md` | Active |
| Deliverables | `doc/00_project/initiative_cognebula_sota/deliverable.md` | Active |

### Initiative: finance_tax_kb (Finance/Tax Knowledge Base)

| Document | Path | Status |
|----------|------|--------|
| PRD | `doc/00_project/initiative_finance_tax_kb/PRD.md` | v2.0 (v3.0 pending) |
| System Architecture | `doc/00_project/initiative_finance_tax_kb/SYSTEM_ARCHITECTURE.md` | v2.0 (v3.0 pending) |
| User Experience Map | `doc/00_project/initiative_finance_tax_kb/USER_EXPERIENCE_MAP.md` | v1.0 |
| Platform Optimization | `doc/00_project/initiative_finance_tax_kb/PLATFORM_OPTIMIZATION_PLAN.md` | v2.0 (v3.0 pending) |
| 3-Layer Architecture | `doc/00_project/initiative_finance_tax_kb/THREE_LAYER_ARCHITECTURE.md` | v1.0 (1170 lines) |
| Knowledge Pipeline | `doc/00_project/initiative_finance_tax_kb/KNOWLEDGE_PIPELINE.md` | v1.0 (831 lines) |
| Task Plan | `doc/00_project/initiative_finance_tax_kb/task_plan.md` | Active |
| Notes | `doc/00_project/initiative_finance_tax_kb/notes.md` | Active |

## Key Routes / Entry Points

| Entry | Type | Description |
|-------|------|-------------|
| `kg-api-server.py` | API | Production service on port `8400` |
| `GET /api/v1/stats` | REST | Graph totals and per-type counts |
| `GET /api/v1/quality` | REST | Quality gate snapshot |
| `GET /api/v1/ontology-audit` | REST | Canonical ontology conformance and rogue-type drift audit |
| `GET /api/v1/search` | REST | Search endpoint |
| `GET /api/v1/hybrid-search` | REST | Hybrid retrieval endpoint |
| `https://cognebula-kg-proxy.workers.dev/api/v1/*` | HTTPS Proxy | Browser-safe static frontend path to protected KG API |
| `http://localhost:3001/` | Web | Packaged static web app |
| `http://localhost:3001/api/v1/*` | HTTP Proxy | Packaged local browser-safe proxy path to protected KG API |
| `http://localhost:8400/docs` | Web | Swagger/OpenAPI |
| `http://100.88.170.57:8400/api/v1/*` | REST | Real production KG API over Tailscale; local dev default after demo cleanup |
| `web/src/app/expert/*` | Web | Expert console routes (`/expert/data-quality` now consumes `/stats + /quality + /ontology-audit`) |
| `web/src/app/expert/data-quality/fixture` | Web | Validation-only production-snapshot fixture route for screenshots / E2E / visual regression |
