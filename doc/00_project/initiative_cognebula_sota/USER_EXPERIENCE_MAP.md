# CogNebula Enterprise -- User Experience Map

> Version: 0.5 | Last updated: 2026-04-23

<!-- AI-TOOLS:PROJECT_DIR:BEGIN -->
PROJECT_DIR: /Users/mauricewen/Projects/27-cognebula-enterprise
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
2. On the production host, export real KG mounts:
   COGNEBULA_GRAPH_PATH=/home/kg/cognebula-enterprise/data/finance-tax-graph
   COGNEBULA_LANCE_PATH=/home/kg/data/lancedb
   KG_API_KEY=<real key>
3. docker compose up -d --build
4. Visit http://localhost:3001/ (packaged static web app)
5. Visit http://localhost:8400/docs (Swagger)
6. Run `GET /api/v1/search` or `GET /api/v1/hybrid-search` with `X-API-Key`, or use the packaged `:3001` proxy path
```
**Quality Gate**: Runtime health reports `runtime_database=production` or an explicit real mount, never demo/archived/empty KG data.

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

## Updated Personas (2026-04 SOTA Refresh)

The original personas targeted code intelligence users. Actual users are in the finance/tax domain:

### Persona A: AI Tax Agent Developer (yiclaw)
- **Goal**: Build an AI bookkeeping agent that answers tax compliance questions accurately
- **Pain**: LLM hallucination on tax regulations; vector RAG loses hierarchical law structure
- **Need**: MCP Server that returns verified regulatory context with citation traceability

### Persona B: Tax Compliance Auditor
- **Goal**: Verify that a tax filing follows all applicable regulations
- **Pain**: Cross-referencing 50K+ regulations manually; rules change frequently
- **Need**: Graph traversal API: "given scenario X, which regulations apply?"

### Persona C: Accounting Firm Platform Engineer
- **Goal**: Integrate structured tax knowledge into firm's existing SaaS tools
- **Pain**: Building a tax KB from scratch is expensive; buying from tax authorities is incomplete
- **Need**: REST/MCP API with daily-updated content from authoritative sources

## Updated User Journeys (2026-04)

### Journey A: AI Agent Integration via MCP (Persona A)
```
1. Configure CogNebula MCP in Claude Code / LangGraph / CrewAI, or call REST with `X-API-Key`
2. Agent queries: "增值税一般纳税人认定标准是什么？"
3. CogNebula returns hybrid retrieval results backed by graph traversal, citations, and semantic neighbors
4. Agent incorporates verified context into response
5. Response includes traceable source (law name + clause ID)
```
**Quality Gate**: Citation accuracy > 95%, response latency < 500ms

### Journey B: Compliance Rule Check (Persona B)
```
1. Auditor opens the static expert workbench
2. Browser calls `https://cognebula-kg-proxy.workers.dev/api/v1/search?...`
3. Cloudflare Worker injects `KG_API_KEY` and forwards to the protected KG API
4. API returns matching LawOrRegulation nodes + related TaxIncentive nodes
5. Auditor reviews INTERPRETS / SUPERSEDES / APPLIES_TO_TAX edges for scope and freshness verification
```
**Quality Gate**: Regulation freshness < 7 days, coverage > 90% of applicable rules

### Journey C: Static Frontend Access to Protected KG API (Persona C)
```
1. User loads the exported Next.js frontend over HTTPS
2. Frontend requests KG data through the Cloudflare Worker proxy
3. Worker injects `X-API-Key` server-side; browser never receives the secret
4. Protected KG API responds with stats/search/hybrid-search data
5. UI renders expert workbench / graph exploration without leaking credentials
```
**Quality Gate**: Browser path uses HTTPS only, no browser-side `KG_API_KEY`, and protected API remains `401` when called directly without auth

## Test Scenarios (from SOTA research)

| Scenario | Method | Target |
|----------|--------|--------|
| Tax query accuracy | 100 curated Q&A pairs vs KG answers | > 90% match |
| Graph freshness | Days since last successful crawl per source | < 7 days |
| MCP latency | p99 response time for graph traversal queries | < 500ms |
| Data quality | Structural gate PASS + hygiene score > 80 | `/api/v1/ontology-audit` + `/api/v1/quality` both trustworthy |
| Agent performance lift | Agent task completion with vs without CogNebula | > 30% improvement |

---

Maurice | maurice_wen@proton.me

## Journey D: Clause Semantic Inspection (Persona D — Finance/Tax Operator)

**Entry point (production)**: `/expert/data-quality` page-level "结构质量 / 基础卫生" summary, then section "条款语义审核 — Clause Inspector"
(Next.js page `web/src/app/expert/data-quality/page.tsx` mounting component
`web/src/app/components/ClauseInspector.tsx`). Operator reaches it from the
sidebar "数据质量" tab of the main CogNebula expert workbench.

**Validation surface (release smoke / visual regression)**:
`/expert/data-quality/fixture` (Next.js page
`web/src/app/expert/data-quality/fixture/page.tsx`) preloads a real production
snapshot captured from `app.hegui.org` on 2026-04-23. Purpose: stable desktop /
mobile screenshots, CTA path smoke, keyboard smoke, and Lighthouse without
depending on the protected `ops.hegui.org` shell or live API availability.

**Dev self-test surface**: `http://<backend>:8400/inspect` (FastAPI-served
`src/web/inspect.html`). Purpose: per-endpoint smoke test for the POST
`/api/v1/inspect/clause[/batch]` routes without spinning up the Next.js
frontend. NOT the product UI — do not link from customer-facing docs.

**Primary task**: Operator on-call gets alerted that the graph is becoming unusable (ontology drift, catch-all node buckets, or clause-row anomalies). They first need to decide whether the problem is structural data quality or clause semantics, without spinning up a new debugging harness.

**Key task → Main path**:

```
1. Operator opens the CogNebula expert workbench and clicks "数据质量" (Sidebar)
2. Reads the hero verdict and "发布门 / 最大桶 / 结构漂移 / 卫生分" four-card summary
3. Clicks the page primary action (e.g. "先处理 KnowledgeUnit") to jump to the governance lane
4. Reviews the治理优先级 list and node-distribution panel to spot catch-all buckets such as oversized `KnowledgeUnit` or legacy/rogue tables
5. Scrolls to "条款语义审核 — Clause Inspector" section at the bottom of the page
6. Single row mode: selects argument_role / strength / jurisdiction_code / scope
7. Clicks "审核" (Primary Action)
8. Verdict card appears within ~100 ms:
   - CLEAN (green) — no defect
   - DEFECTS (red) — list of flag chips: 税收法定禁止 / 辖区代码与作用域不一致 / ...
9. KV table below shows role label (ZH + prohibition marker) + strength tier + chain
   breadcrumb + consistency verdict + reason (if inconsistent)
10. For batch: switch tab, paste NDJSON (one row per line), click "批量审核"
11. Summary card: total / clean / defect counts + scrollable per-row list
```

**Failure paths**:

| Trigger | UI reaction | Signal |
|---|---|---|
| Invalid JSON in batch textarea | Yellow "error" verdict card naming line number + parse error | `role="alert"` live region announces to SR |
| HTTP 400 from server (>1000 rows) | Yellow card with server `detail` message | Actionable: "paginate on the client" |
| Network error (service down) | Yellow card with TypeError message | Operator knows to check API health |
| Empty batch input | Immediate inline error without HTTP call | Saves a round-trip |

**Empty state**: gray placeholder card "等待输入 · 点击「审核」或「批量审核」，结果将在此显示。"

**Loading state**: inline spinner + "审核中…" or "批量审核中… (N 行)"

**Permissions**: inspect endpoint is pure-function; no auth required (safe per current design — no data exposure).

**Quality Gates (verified 2026-04-22)**:

- Data-quality shell surfaces structural FAIL/PASS, rogue counts, and dominant-bucket share before the inspector so operators do not mistake `/quality` 100/100 for whole-graph usability
- Page-level primary action scrolls to the governance lane; secondary action scrolls to the inspector
- Browser console: 0 errors, 0 warnings (favicon + font + POST only)
- Network: only `POST /api/v1/inspect/clause[/batch]` submitted; no PII / secrets / token in URL
- Responsive: 2-column at ≥860 px, single-column mobile at 375 × 667 (screenshot evidence)
- Keyboard a11y: tab order ok, arrow keys switch tabs, `role="alert"` on errors, skip-link to main
- E2E golden path: clean row → CLEAN verdict; defect row (analogy + CN-FTZ-SHA/municipal) → 2 flags rendered with ZH labels
- Primary action single (单行) + single (批量) — no decision ambiguity

**Validation evidence (2026-04-24 fixture route)**:
- `outputs/reports/ontology-audit-swarm/screens/2026-04-24-data-quality-fixture-desktop.png`
- `outputs/reports/ontology-audit-swarm/screens/2026-04-24-data-quality-fixture-mobile.png`
- `outputs/reports/ontology-audit-swarm/2026-04-24-data-quality-fixture-smoke.json`
- `outputs/reports/ontology-audit-swarm/2026-04-24-data-quality-fixture-lighthouse.report.html`
- `outputs/reports/ontology-audit-swarm/2026-04-24-data-quality-fixture-lighthouse.report.json`

**Screenshot evidence (production integration, 2026-04-22)**:
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-data-quality-with-inspector.png` — Clause Inspector rendered inside the real Data Quality page, under CogNebula sidebar + "514K nodes / 1.1M edges / API OK" header
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-data-quality-inspector-result.png` — form state captured post-submit attempt

**Screenshot evidence (dev self-test page, 2026-04-22)**:
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-inspect-desktop-initial.png` (empty state)
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-inspect-defect-result.png` (compound defect)
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-inspect-batch-result.png` (3-row batch)
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-inspect-error-path.png` (JSON parse error)
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-inspect-mobile-375.png` (responsive)
