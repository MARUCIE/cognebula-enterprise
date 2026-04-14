<div align="center">

# CogNebula Enterprise

**The Out-of-the-Box Enterprise Context Brain for AI Agents**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Commercial-orange.svg)](#license)
[![Docker](https://img.shields.io/badge/Docker-One--Click-2496ED.svg)](#one-click-deployment)
[![KuzuDB](https://img.shields.io/badge/Graph-KuzuDB-blueviolet.svg)](https://kuzudb.com)

</div>

CogNebula is a SOTA codebase and domain knowledge graph platform that provides structural and semantic context (Graph RAG) to AI Agents — LangChain, CrewAI, Claude Desktop, Cursor, and any MCP-compatible client.

Completely self-contained. Air-gapped ready. Built for enterprise commercialization.

<p align="center">
  <img src="design/screenshots/01-dashboard.png" width="80%" alt="CogNebula Dashboard" />
</p>

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CogNebula Enterprise                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────────────┐   │
│   │  WebGL   │    │  REST    │    │  MCP Server      │   │
│   │  3D UI   │    │  API     │    │  (stdio/SSE)     │   │
│   └────┬─────┘    └────┬─────┘    └────────┬─────────┘   │
│        │               │                   │             │
│        └───────────┬───┴───────────────────┘             │
│                    │                                     │
│          ┌────────┴────────┐                             │
│          │   Graph RAG     │  Hybrid retrieval:          │
│          │   Engine        │  Vector + Graph Topology    │
│          └────────┬────────┘                             │
│                   │                                      │
│     ┌─────────────┼─────────────┐                        │
│     │             │             │                        │
│  ┌──┴──┐    ┌─────┴─────┐   ┌──┴───┐                    │
│  │Kuzu │    │  LanceDB  │   │Redis │  Event-driven      │
│  │ DB  │    │  Vectors  │   │Queue │  sync worker        │
│  └─────┘    └───────────┘   └──────┘                    │
│                                                          │
│  Per-tenant isolated DB dirs (shared-nothing)            │
└──────────────────────────────────────────────────────────┘
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Pure Local & Air-gapped** | KuzuDB (MIT) + LanceDB (Apache). Zero external dependencies. Enterprise code stays secure |
| **Hybrid Graph RAG** | Vector embeddings (semantic search) + graph topology (structural blast-radius analysis) for precision context |
| **Adaptive Context Windowing** | Tiered detail degradation — Depth 0 returns full code, Depth 1 returns signatures. Prevents LLM token explosion |
| **Shared-Nothing Tenancy** | Each repo/tenant gets a dedicated DB directory. Zero cross-tenant data leakage |
| **Event-Driven Sync** | Webhook-driven Redis queue keeps AI context fresh via continuous indexing |
| **WebGL 3D Console** | Interactive knowledge graph visualization for exploration and debugging |

## One-Click Deployment

### 1. Mount your data
```bash
# Place repos in ./data
cp -r ~/my-java-backend ./data/
cp -r ~/my-react-frontend ./data/
```

### 2. Start the cluster
```bash
docker-compose up -d --build
```

### 3. Access
- **Visual Control Plane (WebGL 3D)**: http://localhost:8766/
- **Swagger/OpenAPI Docs**: http://localhost:8766/docs

## Agent Integration (Graph RAG)

```bash
curl -X POST http://localhost:8766/api/rag \
  -H "Content-Type: application/json" \
  -d '{"repo": "/data/my-java-backend", "query": "Where is JWT auth handled?"}'
```

Returns hyper-dense, markdown-formatted structural context optimized for LLM context windows.

## Screenshots

<table>
  <tr>
    <td><img src="design/screenshots/01-dashboard.png" alt="Dashboard" /></td>
    <td><img src="design/screenshots/04-clients.png" alt="Clients" /></td>
  </tr>
  <tr>
    <td><img src="design/screenshots/05-compliance.png" alt="Compliance" /></td>
    <td><img src="design/screenshots/06-reports.png" alt="Reports" /></td>
  </tr>
</table>

## Tech Stack

- **Graph DB**: KuzuDB (MIT) — property graph with Cypher queries
- **Vector DB**: LanceDB (Apache/MIT) — columnar vector search
- **API**: FastAPI + Pydantic v2
- **Queue**: Redis — event-driven ingestion worker
- **Frontend**: WebGL 3D knowledge graph console
- **Deploy**: Docker Compose (API Gateway + Ingestion Worker + Redis)

## License

Commercial. Built on MIT/Apache open-source foundations (KuzuDB, LanceDB, FastAPI). Designed for integration into proprietary B2B SaaS and private cloud environments.

---

<p align="center"><sub>Maurice | maurice_wen@proton.me</sub></p>
