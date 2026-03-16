# CogNebula Enterprise -- User Experience Map

> Version: 0.1 (Draft) | Last updated: 2026-03-03

<!-- AI-TOOLS:PROJECT_DIR:BEGIN -->
PROJECT_DIR: /Users/mauricewen/Projects/cognebula-enterprise
<!-- AI-TOOLS:PROJECT_DIR:END -->

## User Personas

### Persona 1: AI Agent Developer
- **Goal**: Integrate code understanding into my agent pipeline
- **Pain**: LLM-only context is shallow; keyword search misses structural dependencies
- **Need**: API/MCP that returns dense, structured code context within token budget

### Persona 2: Enterprise Platform Engineer
- **Goal**: Deploy code intelligence as an internal service for dev teams
- **Pain**: Sourcegraph is expensive; Neo4j is too generic; building from scratch is slow
- **Need**: Docker Compose / Helm one-click deploy, air-gapped ready, per-repo isolation

### Persona 3: IDE Plugin Developer
- **Goal**: Add "blast radius" and "architecture overview" to my editor plugin
- **Pain**: LSP only gives file-level info; no cross-repo structural view
- **Need**: MCP server with rich graph traversal tools

## User Journeys

### Journey 1: First-Time Setup (Persona 2)
```
1. git clone cognebula-enterprise
2. Place repos in ./data/
3. docker-compose up -d --build
4. Visit http://localhost:8766/ (WebGL viz)
5. Visit http://localhost:8766/docs (Swagger)
6. POST /api/rag with first query
```
**Quality Gate**: Time-to-first-insight < 5 minutes

### Journey 2: Agent Integration (Persona 1)
```
1. Configure MCP in agent config (cognebula mcp-config)
2. Agent calls query/context/impact tools via MCP
3. Agent receives tiered context (body/signature/name)
4. Agent uses blast radius to identify downstream changes
```
**Quality Gate**: Context precision > 90%, token budget respected

### Journey 3: Incremental Sync (Persona 2)
```
1. Developer pushes to repo
2. Webhook fires -> Redis queue
3. Worker picks up job, re-indexes changed files only
4. Graph updated incrementally (no full rebuild)
5. Agent's next query reflects latest changes
```
**Quality Gate**: Sync latency < 30s for incremental, < 10min for full

## Test Scenarios
(to be refined after SOTA research)

---

Maurice | maurice_wen@proton.me
