# CogNebula Enterprise

**The Out-of-the-Box Enterprise Context Brain for AI Agents**

CogNebula is a State-of-the-Art (SOTA) codebase knowledge graph platform designed specifically to provide structural and semantic context (Graph RAG) to AI Agents (like LangChain, CrewAI, Claude Desktop, and Cursor). 

It is completely self-contained, air-gapped ready, and heavily optimized for enterprise commercialization.

## 🌟 Key SOTA Features

1. **Pure Local & Air-gapped Ready**: Powered by KuzuDB (MIT) and LanceDB (Apache/MIT). Zero external dependencies. Keeps your enterprise code absolutely secure.
2. **Hybrid Graph RAG**: Combines Vector Embeddings (Semantic Search) with exact Graph Topology (Structural Blast-radius Analysis) for 100% precision context retrieval.
3. **Adaptive Context Windowing**: Uses Tiered Detail Degradation (returns Depth 0 as full code, Depth 1 as signatures) to prevent LLM token explosion.
4. **Shared-Nothing Tenant Isolation**: Designed so each repository/tenant gets a dedicated database directory, completely eliminating cross-tenant data leakage.
5. **Event-Driven Sync (Worker)**: Supports continuous indexing via a webhook-driven Redis queue, keeping the AI's context always fresh.

## 🚀 One-Click Deployment (Docker Compose)

Deploy the entire CogNebula cluster (API Gateway, Ingestion Worker, and Redis Queue) in seconds.

### 1. Mount your data
Place the enterprise repositories you want to analyze in the `./data` directory.
For example: `./data/my-java-backend/`, `./data/my-react-frontend/`

### 2. Start the cluster
```bash
docker-compose up -d --build
```

### 3. Access
- **Visual Control Plane (WebGL 3D)**: [http://localhost:8766/](http://localhost:8766/)
- **Swagger/OpenAPI Docs**: [http://localhost:8766/docs](http://localhost:8766/docs)

## 🤖 Agent Integration (Graph RAG)

Once running, configure your AI Agents to POST to the RAG endpoint:

**Endpoint**: `POST http://localhost:8766/api/rag`
**Payload**:
```json
{
  "repo": "/data/my-java-backend",
  "query": "Where is the JWT authentication logic handled?"
}
```
**Response**: A hyper-dense, markdown-formatted structural context tailored perfectly for an LLM's context window.

## 📄 License
This commercial package (CogNebula Enterprise) is built on MIT-licensed open-source foundations (KuzuDB, FastAPI). It can be seamlessly integrated into your proprietary B2B SaaS offerings or private cloud environments.
