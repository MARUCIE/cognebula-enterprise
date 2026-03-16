# CogNebula Enterprise -- System Architecture

> Version: 0.1 (Draft) | Last updated: 2026-03-03

<!-- AI-TOOLS:PROJECT_DIR:BEGIN -->
PROJECT_DIR: /Users/mauricewen/Projects/cognebula-enterprise
<!-- AI-TOOLS:PROJECT_DIR:END -->

## Current Architecture (v1.0)

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[CLI 14 cmds]
        MCP[MCP stdio 7 tools]
        WEB[D3.js WebGL UI]
        API[REST /api/rag]
    end

    subgraph "Engine Layer"
        PIPE[6-Phase AST Pipeline]
        COMM[Community Detection]
        QE[Cypher Query Engine]
    end

    subgraph "Storage Layer"
        KUZU[(KuzuDB per-repo)]
        REG[Registry JSON]
    end

    CLI --> PIPE
    MCP --> QE
    WEB --> QE
    API --> QE
    PIPE --> KUZU
    PIPE --> COMM
    COMM --> KUZU
    QE --> KUZU
    PIPE --> REG
```

### Pipeline Phases
1. **Extract** -- discover source files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`)
2. **Structure** -- build folder/file hierarchy nodes
3. **Parse** -- AST (Python) / regex (JS/TS) symbol extraction
4. **Imports** -- resolve import/require edges
5. **Calls** -- resolve function/method call edges
6. **Heritage** -- resolve class inheritance/implementation edges
7. **Community** -- simplified Leiden community detection

### Storage Model
- Per-repo KuzuDB at `<repo>/.cognebula/graph/`
- Node tables: Module, File, Folder, Function, Class, Interface, Method, ArrowFunction, External, Community
- Edge types: CONTAINS, DEFINES, IMPORTS, CALLS, EXTENDS, IMPLEMENTS, MEMBER_OF (+ variants)

## Target Architecture (v2.0 -- SOTA)

```mermaid
graph TB
    subgraph "Client Layer"
        CLI2[CLI]
        MCP2[MCP Expanded]
        REST2[REST API Gateway]
        SDK[Client SDKs Python/TS]
    end

    subgraph "Gateway Layer"
        GW[API Gateway + JWT]
        TENANT[Tenant Router]
    end

    subgraph "Processing Layer"
        TS[Tree-sitter Parser]
        SYNC[Event-Driven Sync Worker]
        NL2G[NL2Graph Engine]
    end

    subgraph "Hybrid RAG Layer"
        LANCE[(LanceDB Vector)]
        KUZU2[(KuzuDB Graph per-tenant)]
        ORCH[RAG Orchestrator]
    end

    subgraph "Infrastructure"
        REDIS[(Redis Queue)]
        WEBHOOK[Webhook Receiver]
    end

    CLI2 --> GW
    MCP2 --> GW
    REST2 --> GW
    SDK --> GW
    GW --> TENANT
    TENANT --> ORCH
    ORCH --> LANCE
    ORCH --> KUZU2
    WEBHOOK --> REDIS
    REDIS --> SYNC
    SYNC --> TS
    TS --> KUZU2
    TS --> LANCE
    NL2G --> ORCH
```

### Key Architecture Decisions
1. **Shared-Nothing**: One KuzuDB directory per repo/tenant (hardware isolation)
2. **Late-Binding Hybrid RAG**: LanceDB finds semantic entry point -> KuzuDB maps blast radius
3. **Tree-sitter**: Universal parser with error recovery (replaces regex for JS/TS)
4. **Event-Driven**: Webhook -> Redis -> Single-threaded ingester per repo
5. **API Gateway**: JWT validation + tenant routing before any DB access

## System Boundaries
(to be refined after SOTA research -- competitive feature matrix will inform boundary decisions)

---

Maurice | maurice_wen@proton.me
