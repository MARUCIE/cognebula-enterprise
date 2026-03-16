# CogNebula Enterprise -- Documentation Index

## Project Path Index

| Path | Description |
|------|-------------|
| `/Users/mauricewen/Projects/cognebula-enterprise` | PROJECT_DIR (git root) |
| `src/cognebula.py` | Main engine (2620 lines, monolith) |
| `docker-compose.yml` | API + Worker + Redis cluster |
| `Dockerfile` | API container build |
| `data/` | Repository mount point for analysis |
| `docs/COMMERCIAL_SOLUTION.html` | Commercial solution overview |

## Documentation Map

| Document | Path | Status |
|----------|------|--------|
| PRD | `doc/00_project/initiative_cognebula_sota/PRD.md` | Draft |
| System Architecture | `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md` | Draft |
| User Experience Map | `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md` | Draft |
| Platform Optimization | `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md` | Draft |
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
| `cognebula setup` | CLI | Initialize registry |
| `cognebula analyze <path>` | CLI | Build knowledge graph |
| `cognebula serve --port 8766` | HTTP | API + WebGL visualization |
| `cognebula mcp` | stdio | MCP server (7 tools) |
| `POST /api/rag` | REST | Hybrid RAG endpoint |
| `http://localhost:8766/` | Web | D3.js 3D visualization |
| `http://localhost:8766/docs` | Web | Swagger/OpenAPI |
