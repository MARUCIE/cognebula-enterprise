# HANDOFF.md -- CogNebula / Lingque Desktop

> Last updated: 2026-04-17T19:40+08:00

## Session 69 — Ontology Conformance Ruler (2026-04-17)

### Status: COMPLETE — canonical v4.2 schema now versioned, drift auditor shipped as read-only API endpoint, no production data touched

### Why this session
Session 68 deployed the frontend. The follow-up user audit question was "是否符合本体设计标准?" (does the production data conform to the ontology design standard?). The answer required comparing live types against a canonical target — but the canonical schema file did not exist in git: `ONTOLOGY_V42_DESIGN.html` (35 types target) had never been translated to a Cypher schema. `/api/v1/quality` reports score 100 because it only audits 17 curated V2 tables; it had no concept of type-count, V1/V2 coexistence, or design drift. Measurement without a ruler means the drift had no surface area.

### What was delivered
1. **Canonical v4.2 schema**: `schemas/ontology_v4.2.cypher` — 35 node types in 4 tiers (Legal Backbone 7 / Tax Domain Primitives 9 / Operational Rules 10 / Accounting + Reporting 9). Brooks ceiling headroom 2. Every type has a `PRIMARY KEY` and typed properties. Edge tables deferred to a second pass since they need explicit `CREATE REL TABLE GROUP` with multiple `(from,to)` tuples.
2. **Conformance auditor**: `src/audit/ontology_conformance.py` — pure read, parses the canonical Cypher, diffs against `show_tables()` output, classifies rogue types into five buckets (V1/V2 bleed, semantic duplicate clusters, SaaS-surface leak, legacy pre-v4.1, other). Severity FAIL if over ceiling or V1/V2 bleed present.
3. **API endpoint**: `GET /api/v1/ontology-audit` — thin wrapper that imports the auditor. Kept separate from `/quality` so the existing content-quality score semantics are unchanged.
4. **Dockerfile**: now `COPY src/audit/` + `COPY schemas/` so the endpoint works inside the container.
5. **Drift report pair** (2份制): `doc/00_project/initiative_cognebula_sota/ONTOLOGY_DRIFT_REPORT.md` (English, canonical, machine-readable) + `ONTOLOGY_DRIFT_REPORT.html` (Chinese, BCG-styled, human-readable). HTML opened in browser after write.

### Production drift numbers (from contabo `GET /api/v1/stats` snapshot)
- Canonical v4.2 declared node types: 35 (Brooks ceiling 37)
- Production live node types: **62** (over ceiling by 25)
- Intersection (clean): 16 (e.g. `AccountingStandard`, `TaxType`, `LegalClause`, `KnowledgeUnit`, `AuditTrigger`, `BusinessActivity`, `Classification`, `IssuingBody`, `Penalty`, `Region`, `TaxCalculationRule`, `TaxEntity`, `TaxIncentive`, `TaxRate`, `AccountingSubject`, `LegalDocument`)
- v4.2 declared but missing from production: 19 (e.g. `ComplianceRule` superseded by live `ComplianceRuleV2`, `FilingFormField`, `JournalEntryTemplate`, `ResponseStrategy`, `TaxMilestoneEvent`, `TaxBasis`, `TaxItem`)
- Production rogue not in v4.2: 46. Classified:
  - V1/V2 bleed (5): `ComplianceRuleV2`, `FilingFormV2`, `RiskIndicatorV2`, `TaxIncentiveV2`, `FormTemplate`
  - Semantic duplicates (19 over 4 clusters): tax-rate (6), accounting (6), industry (5), policy (3)
  - SaaS-layer leak (6): `CustomerProfile`, `EnterpriseType`, `EntityTypeProfile`, `ServiceCatalog`, `CrossSellTrigger`, `ChurnIndicator` — these should live in System B's relational store, not the KG
  - Legacy pre-v4.1 (7): `CPAKnowledge` (7,371 rows, Session 43 FAIL), `MindmapNode` (28,526 rows, structural-only by design), `DocumentSection`, `FAQEntry`, `HSCode`, `TaxClassificationCode`, `TaxCodeDetail`
  - Other (9): `DeductionStandard`, `TaxCreditIndicator`, `TaxWarningIndicator`, `TaxCalendar`, `TaxpayerStatus`, `TaxRiskScenario`, `SpreadsheetEntry`, `RegulationClause`, `DepreciationRule`

### Verification (auditor runs against local Session-67 demo graph)
- Rebuilt `cognebula-api` Docker image with new Dockerfile
- `curl -H "X-API-Key: local-demo-key" http://localhost:8400/api/v1/ontology-audit` → HTTP 200, 2302B, 0.27s
- Returned shape: `verdict=FAIL severity=high over_ceiling=True over_ceiling_by=19 canonical=35 live=56 intersection=12 missing_from_prod=23 rogue_in_prod=44`
- Buckets populated correctly: V1/V2 bleed detected `FormTemplate` in demo; SaaS leak caught `EnterpriseType`, `EntityTypeProfile`; legacy caught `CPAKnowledge`, `FAQEntry`, `MindmapNode`; duplicate clusters found tax_rate/accounting/industry mates
- Differences local-demo vs prod: local is 56 types (has extra code-intelligence tables like `ArrowFunction`, `Class`, `Function`, `Method`, `Module` from an unrelated code-analysis corpus that is not in prod); prod is 62. The auditor classifies both correctly.

### Done post-turn (in this same session, after user said "继续")

**Action A — Deploy audit endpoint to contabo production** (completed)

- Backed up `/home/kg/cognebula-enterprise/kg-api-server.py` → `.pre-session69.bak` before any write
- `rsync -az` shipped local `kg-api-server.py` + `src/audit/` + `schemas/` to contabo
- Fixed rsync path so `audit/` landed as `src/audit/` not top-level `/audit/`
- Discovered a pre-existing path divergence: the backup had `LANCE_PATH="/home/kg/data/lancedb"` hardcoded, my local has `LANCE_PATH=/home/kg/cognebula-enterprise/data/lancedb-build` — these point to different directories (the real 1.1 GB LanceDB lives in `/home/kg/data/lancedb`, the other is an empty stub from March)
- Patched `kg-api-server.py:25-26` to read `DB_PATH` and `LANCE_PATH` from environment first, hardcoded default as fallback. Re-uploaded
- Created `/etc/systemd/system/kg-api.service.d/override.conf` with `Environment=LANCE_PATH=/home/kg/data/lancedb` + `Environment=DB_PATH=/home/kg/cognebula-enterprise/data/finance-tax-graph`
- `systemctl daemon-reload && systemctl restart kg-api.service` — new PID, up in ~5s
- Verified `/api/v1/health` returned to `healthy / kuzu=true / lancedb=true / 118011 rows` (was briefly `degraded / lancedb=false / 0 rows` between the first rsync and the systemd override)
- Verified new endpoint: `curl http://167.86.74.172/api/v1/ontology-audit` returned HTTP 200 in 0.34s, `verdict=FAIL severity=high over_ceiling=True over_ceiling_by=46 canonical=35 live=83 rogue=64`
- Verified non-regression: `/stats`, `/quality`, `/`, `/expert/` all still HTTP 200

**Action C — CI gate wired** (completed)

- `scripts/check_ontology_conformance.py`: CLI that supports `--remote URL` (hits the endpoint) or `--local DB_PATH` (opens Kuzu directly). Exit 0 on PASS, 1 on FAIL, 2 on tool/config error. Supports `--max-rogue N` threshold override, `--allow-over-ceiling` for grace period, `--json` for machine-readable output
- `.github/workflows/ontology-gate.yml`: triggers on push/PR touching schema/auditor/API code, plus daily cron at 06:00 UTC (after nightly pipeline), plus manual `workflow_dispatch`. Probes `http://167.86.74.172/api/v1/ontology-audit` via the repo secret `COGNEBULA_PROD_URL`, fails if rogue count exceeds 70 (current baseline 64). Uploads `audit-output.txt` as artifact for 30 days
- Intentionally set the threshold at 70 not 0: the current drift is 64 rogue, we do not want the gate to be red from day one. The roadmap is to tighten the number as migration phases complete: 70 → 55 (after V1/V2 rename) → 35 (after duplicate collapse) → 15 (after SaaS eviction) → 0 (after legacy folding)
- Manual test passed in both directions: `--max-rogue 70` → exit 0, `--max-rogue 10` → exit 1

### Also done (after second "继续") — Phase 0 staged and validated locally

**Phase 0 — drop empty rogue tables, no data loss**

- `scripts/migrate_phase0_drop_empty.py`: `--dry-run` default, `--execute` to commit. Discovers the REL dependency graph via `CALL show_connection(rel_name)`, refuses to drop any node that has non-zero rows or any REL with non-zero edges, reports a full plan before execution
- Targets 19 orphan node types: 15 code-analysis residue (`ArrowFunction`, `Class`, `Community`, `Document`, `External`, `File`, `Folder`, `Function`, `Interface`, `LifecycleActivity`, `LifecycleStage`, `Method`, `Module`, `Section`, `Topic`) + 4 finance-tax legacy empties (`FilingObligation`, `SpecialZone`, `TaxPlanningStrategy`, `TaxRateVersion`)
- Also drops 39 empty REL tables that reference these nodes (Kuzu rejects node DROP while any REL table declares it as FROM or TO, even if edge count is 0 — this was the first-pass trap that made the hardcoded `.cypher` script fail 16/18 times)
- Validated on a full `cp -a data/finance-tax-graph.demo data/finance-tax-graph.demo.phase0-test` copy: before = 56 types / 44 rogue / over_by 19; after = **37 types (= Brooks ceiling exactly) / 25 rogue / over_by 0**. 39 REL + 19 nodes dropped with zero errors. Test copy removed after validation
- Staged cypher in `deploy/contabo/migrations/phase0_drop_empty_tables.cypher` (for review) — prefer running the Python wrapper, which handles REL dependency order automatically

**Phase 1 — V1/V2 reconciliation (staged, not executed)**

- `deploy/contabo/migrations/phase1_v1_v2_rename.cypher`: four-phase script with dry-run queries before every destructive statement
  - 1a: DROP the three empty canonical stubs (`ComplianceRule`, `FilingForm`, `RiskIndicator`) that exist as placeholder tables
  - 1b: `ALTER TABLE ComplianceRuleV2 RENAME TO ComplianceRule` (+ FilingForm, RiskIndicator). Depends on Vela 0.12 fork supporting `ALTER TABLE ... RENAME`
  - 1c: fallback using CREATE+COPY+DROP if RENAME not supported (requires rewiring all REL edges per edge label — much heavier)
  - 1d: `TaxIncentiveV2 → TaxIncentive` merge — both tables populated, needs row-level MERGE with conflict detection; deferred to its own script with explicit dedup key rule
- Expected post-Phase-1 audit: `live_count=61, rogue=42, intersection=23, missing=12, v1_v2_bleed=[]`

### Also done (after third "继续") — Phase 1 syntax proven + schema edges filled in

**B1 — ALTER TABLE RENAME syntax validated**
- `ALTER TABLE FormTemplate RENAME TO FormTemplate_test` on a copy of the demo graph: succeeded, 109 rows preserved, rename-back succeeded
- Confirms Kuzu 0.12 Vela fork supports in-place node table rename
- Phase 1b (`ComplianceRuleV2 → ComplianceRule` + two more) is now a **30-second one-liner trio** in prod, not the heavier CREATE+COPY+DROP fallback
- Phase 1c fallback remains in the staged script only as a belt-and-braces option

**D — `schemas/ontology_v4.2.cypher` edges section**
- Parsed `ONTOLOGY_V42_DESIGN.html` table rows: 79 unique `EDGE_NAME: FromType -> ToType` declarations, every FROM/TO references a node in the canonical 35-type set
- Categorised into 4 tiers matching the node tiers, emitted `CREATE REL TABLE IF NOT EXISTS <NAME>(FROM <A> TO <B>, sourceClauseId, effectiveAt, supersededAt)` blocks
- Validated by replaying the full schema against a fresh empty Kuzu: 114 DDL statements, 114 executed OK, 0 errors, final schema `35 NODE tables + 79 REL tables` — matches design doc target
- `schemas/ontology_v4.2.cypher` now 20 KB / 371 lines, canonical in git, ready to seed a from-scratch replica

### Still not done (HITL-required on prod)

- **Phase 0 execution on contabo**: script ready, zero-data-loss by construction. Prod run ≈ 10 min downtime (`systemctl stop + migrate_phase0 --execute + start`). No full backup required (tables are empty)
- **Phase 1 execution on contabo**: with ALTER TABLE RENAME now proven, Phase 1a (drop 3 empty canonical stubs) + 1b (3 renames) is ≈ 60 seconds; 1d (TaxIncentiveV2 → TaxIncentive row merge) is a separate script
- **Phases 2-4**: duplicate cluster collapse (19 → 4 types), SaaS layer eviction (needs System B backend to host evicted rows), legacy folding (CPAKnowledge + MindmapNode fold into KnowledgeUnit)
- **CI workflow**: relies on public HTTP reachability. Tailscale GitHub Action path is a follow-up if we firewall public 80/8400 later

### Notes for the next session
- The canonical v4.2 schema currently has **no edge-table declarations**. Next pass should add `CREATE REL TABLE GROUP` declarations for the ~72 design-doc edge types against the 35 node types. The existing `V2_EDGES` set in `kg-api-server.py:415` (34 names) is the starting vocabulary
- When/if ontology-audit deploys to prod, Session 43's "quality 92.4/100 PASS" headline needs to be retired or reframed: quality and ontology conformance are orthogonal axes; a graph can score 100 on the former while being 2× over the structural ceiling on the latter (exactly what we have today)
- If System B is going to get real backend endpoints (see §6.4 in drift report), the SaaS-leak cluster (§3c: `CustomerProfile` etc.) needs a target home first — otherwise the eviction has nowhere to go

## Session 68 — First-time Frontend Deploy to Contabo VPS (2026-04-17)

### Status: COMPLETE — Next.js static frontend now live on Contabo in front of the production 547K-node KG API, no mock data on the critical path

### Context

Sessions 54-67 expanded the local demo graph. This session addresses the observation that neither the 灵阙 client system (`/workbench/*`) nor the CogNebula internal system (`/expert/*`) had ever been deployed to the production VPS — only the API was running there. User instruction: "全部要真实打通，绝不能 mock" — ship the whole frontend to the existing production server, wired to the real production KG API, no mock data on any path I control.

### Target VPS

- **contabo** (SSH alias), Tailscale IP `100.88.170.57`, public IP `167.86.74.172`
- Contabo EU, Ubuntu 24.04.4 LTS, hostname `kg-node-eu`, 12C / 47 GiB RAM / 242 GB disk (46% used, 132 GB free)
- `~/.ssh/config` already annotated `Role: CogNebula KG` — chosen over dmit-us-proxy (reverse-proxy role), do-us-crawl (crawler), cc-us-c2 (c2), openclaw (different project)

### Pre-existing on contabo (not touched)

- `/home/kg/cognebula-enterprise/` rsync-deployed code tree (not a git checkout)
- `systemd` unit `kg-api.service` runs `uvicorn kg-api-server:app --host 0.0.0.0 --port 8400` from `/home/kg-env` venv. PID 747855, up since 2026-04-15, memory 3.8 GB
- Production KG: `data/finance-tax-graph` = 110 GB single Kuzu file, 547,761 nodes, 1,302,476 edges (verified via `/api/v1/stats` through Tailscale before deploying anything)
- LanceDB vector store: 118,011 rows, live

### Changes I made this session

1. Created `deploy/contabo/nginx-cognebula.conf` in the repo. `listen 80`, `root /home/kg/cognebula-web`, `/api/v1/` reverse-proxies to `http://127.0.0.1:8400/api/v1/`, SPA fallback `try_files $uri $uri/ $uri.html $uri/index.html /index.html`, 1-year immutable cache for `/_next/static/`, gzip, dedicated access/error logs under `/var/log/nginx/cognebula-*.log`
2. Built the frontend locally: `cd web && NEXT_PUBLIC_KG_API_BASE=/api/v1 npm run build`. `next.config.ts` already had `output: "export"` and `trailingSlash: true`; build produced `web/out/` = 5.8 MB containing every route (`/`, `/workbench/*`, `/expert/*`, `/dashboard`, `/clients`, `/reports`, `/skills`, `/settings`). Injecting `/api/v1` as a relative base means the browser talks to nginx on the same origin — no CORS, no leaked upstream host, no client-side secret
3. On contabo: `apt install -y nginx` (nginx/1.24.0 Ubuntu), created `/home/kg/cognebula-web/` owned by `www-data`, fixed home directory traversal perms `chmod o+rx /home /home/kg` + `chmod -R o+rX /home/kg/cognebula-web` (initial deploy 500-errored with "Permission denied on /home/kg/cognebula-web/index.html" because root home tree was `700`)
4. `scp` uploaded `deploy/contabo/nginx-cognebula.conf` → `/etc/nginx/sites-available/cognebula`, removed `/etc/nginx/sites-enabled/default`, symlinked the new config. `nginx -t` passed, `systemctl reload nginx` OK
5. `rsync -az --delete` shipped `web/out/` → `contabo:/home/kg/cognebula-web/`. Had to override the SSH config's default `RemoteCommand tmux new-session` + `RequestTTY force` with `-e "ssh -o RemoteCommand=none -o RequestTTY=no"` (the tmux wrapper breaks non-interactive ssh/scp/rsync)

### What was NOT changed

- `kg-api.service` left untouched — same uvicorn process, same port, same binding
- Production KG file `data/finance-tax-graph` not touched, not copied, not edited
- No firewall rules added (UFW was inactive on contabo and I did not enable it, since the change would risk locking myself out via ssh)
- No DNS / domain / TLS certificate provisioned — IP-only deploy for now
- Session 54-67 local-demo work not yet committed; non-committed diff still outstanding from Session 54 onward

### Verification (all real, no mock on my path)

- `/api/v1/health` via public IP: `{"status":"healthy","kuzu":true,"lancedb":true,"lancedb_rows":118011}`
- `/api/v1/stats` via public IP: `total_nodes=547761, total_edges=1302476`, top node types `KnowledgeUnit 185455 / LegalClause 83443 / LegalDocument 54865 / DocumentSection 42252 / LawOrRegulation 39651 / RegulationClause 29655 / MindmapNode 28526 / Classification 28035`, top edges `INTERPRETS 390756 / KU_ABOUT_TAX 166466 / ISSUED_BY 128203 / REFERENCES 111271 / LR_CROSS_REF 76965`. Response 2.4-3.2 seconds
- Public HTTP smoke test of 12 routes (single curl loop): `/ /workbench/ /expert/ /expert/kg/ /expert/data-quality/ /expert/reasoning/ /expert/rules/ /dashboard/ /clients/ /reports/ /skills/ /api/v1/health` — all HTTP 200
- Chrome DevTools MCP screenshot of `http://167.86.74.172/expert/` after a 6-second wait for React hydration + `/stats` resolution: shows real production KPIs `节点总数 547,761 / 边总数 1,302,476 / 边密度 2.378 / 质量评分 100.0%`, system state panel shows KG API `在线`, KuzuDB `警告 — 已归档 -- 计划 2026-09 前评估迁移`, LanceDB `在线`, Know-Arc 管线 `在线`, Edge Engine `在线 — SUPERSEDES 边关系，上次运行 107 条`, CF Worker 代理 `待部署`
- Chrome DevTools MCP screenshot of `http://167.86.74.172/` shows 灵阙 月度看板 rendered identically to local with real fonts (Manrope + Inter), all sidebar links present, Kanban swim lanes W1-W4 populated
- Saved artifacts: `state/screenshots/contabo-public-homepage.png` (580 KB), `state/screenshots/contabo-public-expert-loaded.png` (real-data variant)

### Known gaps / follow-ups (material, not blocking)

1. **API still exposes port 8400 on `0.0.0.0`** — anyone with the public IP or any Tailscale peer can hit `:8400` directly without the nginx proxy layer. To close: set `uvicorn --host 127.0.0.1`, add `Environment=KG_API_KEY=<secret>` to `kg-api.service`, have nginx inject `proxy_set_header X-API-Key $kg_api_key;` from a server-side variable. This is a production service restart, HITL-required
2. **No HTTPS / no domain** — public is plain HTTP. Certbot + DNS A record are the next step once a domain is picked
3. **UFW inactive on contabo** — ports 22, 80, 8400, 443, 54443 all publicly reachable. Enabling UFW needs careful `ufw allow OpenSSH` + explicit `:80` rule before `ufw enable` or we self-lock
4. **`/workbench/*` and most of `/clients/*` pages render seed/demo data at the React layer**, not a mock I injected. The current kg-api-server has no `/api/v1/workbench/*` or `/api/v1/tasks/*` endpoints — turning those panels into real production views requires a new backend surface, not just a deploy. This is a feature backlog item, not a Session 68 regression
5. **Session 54-67 uncommitted diff still outstanding** — the local demo graph extension work from the prior 14 sessions has never been committed. User has not yet authorized a commit
6. **Sidebar of the 灵阙 client system deliberately has no link to `/expert/*`** — this is the intended client/internal partition documented on the expert page itself ("System A 仅作为内部基础设施"). Not a gap, a feature. If you ever want internal-only IP allowlisting or basic-auth on `/expert/*`, that is a future nginx location block

### Rollback procedure

If the nginx config causes any regression:
```bash
ssh contabo
rm /etc/nginx/sites-enabled/cognebula
ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
systemctl reload nginx
```
The kg-api.service is untouched so rolling back nginx is sufficient to restore the pre-session state (API-only, port 8400 Tailscale).

## Session 67 — CPA Exam Questions + RELATED_TO Schema Fix (2026-04-17)

### Status: COMPLETE — local richer demo graph now ships 854 CPA exam questions and closes Session 66's deferred RELATED_TO schema gap

### What was done

1. Fixed the Session 66 blocker at the origin: `src/inject_cpa_exams.py` now owns its own schema prerequisite. Right after the Kuzu connection opens, the script runs `CREATE REL TABLE GROUP IF NOT EXISTS RELATED_TO(FROM OP_StandardCase TO TaxType, FROM OP_StandardCase TO AccountingStandard, relType STRING, weight DOUBLE)`. This follows the fat-skill / thin-harness rule: injector scripts own their DDL, the bootstrap orchestrator only orchestrates.
2. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable `cpa-exams`. The new block reuses `ensure_accounting_schema()` so that if a user runs `--include cpa-exams` without `cpa` the `OP_StandardCase` base table is still guaranteed present.
3. Updated the docstring to list "CPA exam questions" alongside the existing twelve corpora.
4. Rebuilt `data/finance-tax-graph.demo` from the archived baseline via `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` with the expanded default path.
5. Re-verified the rebuilt demo graph directly in Kuzu, including the new RELATED_TO edge set and a spot-check of the `cpa_exam_question` case rows.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_cpa_exams.py` passed.
- Injector dry-run reported 854 questions across 2018/2019/2020 exam years and 6 subjects (accounting 110 / audit 167 / economic_law 174 / financial_management 121 / strategy 118 / tax_law 164), with 157 tax_type edges + 144 accounting_standard edges parsed.
- Final bootstrap step printed `Nodes: 854 created, 0 failed` and `Edges: 301 created, 0 failed`.
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=6219` (from `5365` in Session 66; delta exactly `+854` from the new `OP_StandardCase` rows).
  - `edges=876` (from `772` in Session 66; delta `+104`).
  - `OP_StandardCase=1246` (from `392`; delta `+854`, all with `caseType='cpa_exam_question'`).
  - `LawOrRegulation=431`, `TaxType=19`, `AccountingStandard=43`, `RiskIndicator=235`, `ChartOfAccount=159`, `TaxRateMapping=80`, `TaxRateSchedule=23` — unchanged, confirming cpa-exams is additive-only.
- RELATED_TO edge distribution (first population of this rel table in the demo graph):
  - 104 edges, all `(OP_StandardCase)-[RELATED_TO]->(TaxType)`.
  - Spread across 11 TaxTypes: TT_VAT 27, TT_CIT 25, TT_CONSUMPTION 17, TT_STAMP 9, TT_PROPERTY 7, TT_LAND_USE 5, TT_VEHICLE 4, TT_RESOURCE 4, TT_LAND_VAT 4, TT_TOBACCO 1, TT_TONNAGE 1.
- Spot-check: `MATCH (c:OP_StandardCase {caseType: 'cpa_exam_question'}) RETURN c.id, c.name LIMIT 3` returns CPA question rows with human-readable `name` fields (e.g. `2018年CPA《会计》单项选择题 第1题`).

### Known gaps and follow-ups

- Injector printed `Edges: 301 created, 0 failed` but only 104 edges persisted. The script uses `MATCH (a:OP_StandardCase {id:...}), (t:TaxType {id:...})` + `MERGE` — when the right-hand `id` does not exist in the baseline, the whole MATCH fails and no edge is created, but the loop counter increments. Root cause: the extraction phase in `src/inject_cpa_exams.py` emits more TaxType / AccountingStandard ID candidates than what exists in the 19-TaxType / 43-AccountingStandard baseline. Concretely 53/157 tax-type candidates and 144/144 accounting-standard candidates miss. AccountingStandard edges are the larger gap and the correct follow-up is to align the extractor's AS ID vocabulary with baseline AS IDs (or to add the missing AS nodes) in a future session. Today's session intentionally scopes out that alignment to keep the increment reviewable.
- The injector's MATCH-then-MERGE shape silently swallows missed IDs. Future schema-owning injectors should either (a) explicitly count drops and warn, or (b) use `MATCH ... WHERE ... WITH count(*) AS n` to detect zero-match patterns. Adding this diagnostic belongs in a dedicated small task, not this bootstrap-extension session.
- Packaged Compose verification was skipped again: the change only adds node/edge content (no API surface, no query path changes). Session 62 remains the latest Compose-runtime proof.
- Remaining Phase C work is still on production-scale enrichment for the non-demo graph. The local demo path has now absorbed every available static corpus that fit the "additive, idempotent, semantically partitioned" bar.

### Notes for the next session

- Every currently-known local corpus with a dedicated injector is now wired into the demo graph bootstrap. Future local-demo additions will likely require either a new extracted corpus (e.g. more recent CPA years beyond 2020) or cross-linking passes (e.g. `FT_INTERPRETS` edges between enforcement cases and relevant LawOrRegulation anchors). These are no longer bootstrap-orchestration changes but new injector work.
- The 144 missing AccountingStandard→CPA edges are the highest-value dangling piece: once the AS ID alignment lands, the CPA exam corpus becomes much more useful for `ft-accountant` and `ft-journal-engine` when agents need to retrieve worked examples per accounting standard.
- Sessions 54-67 have accumulated non-committed changes across `scripts/bootstrap_local_demo_graph.py`, 13 `src/inject_*.py` files, `data/finance-tax-graph.demo`, `HANDOFF.md`, and `doc/00_project/initiative_cognebula_sota/task_plan.md`. A commit authorization is still outstanding — the user has not yet authorized a commit since Session 54.

## Session 66 — Enterprise Report Templates (2026-04-17)

### Status: COMPLETE — local richer demo graph now ships seven enterprise report template corpora

### What was done

1. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable `reports`.
2. Routed `reports` through `src/inject_enterprise_reports.py`, which reads `data/extracted/enterprise_reports/*.json` and:
   - inserts report chapters as `LawOrRegulation` nodes with `regulationType='report_template'`, `issuingAuthority='doc-tax-enterprise-reports'`, and `regulationNumber='RPT-<type>-P<page>'`,
   - inserts report indicators as `RiskIndicator` nodes.
3. Rebuilt `data/finance-tax-graph.demo` from the archived baseline with the expanded default path.
4. Re-verified the rebuilt demo graph directly in Kuzu.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap,accounting,enforcement,rates,reports}`
- `./.venv/bin/python src/inject_enterprise_reports.py --dry-run` reported `+423 chapters` + `+110 indicators` across 7 report types
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 5365`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=5365`, `edges=772` (from `4919`/`772` in Session 65; `reports` adds nodes only, no new edges)
  - `LawOrRegulation=431`: `regulationType='report_template'=336`, `enforcement_*`=95 (Session 64 enforcement LR unchanged)
  - `RiskIndicator=235` (from `125`; `+110` from report indicators)
  - `TaxRateMapping=80`, `ChartOfAccount=159` unchanged
- Report-template breakdown by source report (from `regulationNumber` prefix):
  - 投资尽调 100, 经营参谋 75, 全景 43, 税务风险 37, 企业尽调 34, 供应商尽调 24, 财政补贴 23 — total 336
- Actual injected total (`336 LR + 110 RI = 446`) is below the dry-run total (`423 + 110 = 533`) because the injector uses plain `CREATE` without `MERGE`, so intra-report `regulationNumber+title` hash collisions are rejected by KuzuDB primary-key constraints. This is consistent with the dry-run vs live delta pattern and not a new regression.

### Notes for the next session

- The local/demo side of Phase C now also covers enterprise-report skeletons (投资尽调 / 经营参谋 / 全景 / 税务风险 / 企业尽调 / 供应商尽调 / 财政补贴), which unblocks `ft-business-analyst` / `ft-risk-assessment` workflows that need concrete chapter anchors for prompted report drafting.
- `inject_enterprise_reports.py` does not create any new edges. If we later want to connect report-template LR nodes to `FTIndustry` / `TaxType`, that is a follow-up wiring task, not a bootstrap change.
- `inject_cpa_exams.py` was evaluated this session but deferred: it emits `RELATED_TO` edges whose rel table does not exist in baseline, so adding it to `--include` would silently drop all 301 edges. Closing that gap needs a schema-owning fix in the injector (or a new `ensure_related_to_schema` helper), not a bootstrap-only change.
- Packaged Compose verification was skipped again; the change only adds node content and does not alter API behaviour. Session 62 remains the latest Compose-runtime proof.
- Remaining Phase C work is still on production-scale enrichment, not the local packaged demo path.

## Session 65 — Tax Rate Tables (2026-04-17)

### Status: COMPLETE — local richer demo graph now ships the CAS flat-rate and progressive tax-rate tables

### What was done

1. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable `rates`.
2. Routed `rates` through `src/inject_tax_rates.py`, which:
   - creates the `TaxRateSchedule` node table + `FT_RATE_SCHEDULE` rel table when absent,
   - upserts 69 `TaxRateMapping` flat-rate rows (VAT 13%/9%/6%/zero/simplified, consumption tax, vehicle purchase tax, etc.) via MERGE,
   - inserts 23 `TaxRateSchedule` progressive brackets for 4 schedules (综合所得/经营所得/全年一次性奖金/土地增值税),
   - wires matching `OP_MAPS_TO_RATE` and `FT_RATE_SCHEDULE` edges to `TaxType`.
3. Rebuilt `data/finance-tax-graph.demo` from the archived baseline with the expanded default path.
4. Re-verified the rebuilt demo graph directly in Kuzu (nodes, edges, and two schedule breakdowns).

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap,accounting,enforcement,rates}`
- `./.venv/bin/python src/inject_tax_rates.py --dry-run` reported 69 mappings + 23 brackets + 92 edges
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4919`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4919`, `edges=772` (from `4827`/`680` in Session 64)
  - `TaxRateMapping=80` (11 baseline preserved + 69 CAS-authoritative from the injector)
  - `TaxRateSchedule=23` (new table; 4 schedules populated)
  - `OP_MAPS_TO_RATE=80` (+69), `FT_RATE_SCHEDULE=23` (+23)
  - `FT_GOVERNED_BY=38`, `LawOrRegulation=95`, `ChartOfAccount=159` unchanged
- TaxRateMapping coverage for `TT_VAT` spans standard 13%, low 9%, service 6%, zero-rate, and simplified 1.5%/3%/5% buckets, plus vehicle purchase tax 10%
- TaxRateSchedule bracket counts match the real CAS/individual-income tax structures:
  - 综合所得年度税率表 = 7 brackets
  - 经营所得年度税率表 = 5 brackets
  - 全年一次性奖金月度税率表 = 7 brackets
  - 土地增值税4级超率累进税率表 = 4 brackets

### Notes for the next session

- The local/demo side of Phase C now carries an authoritative flat-rate and progressive-rate table, which unblocks `ft-tax-advisor` / `ft-tax-planner` / `ft-invoice-manager` calculations that previously had to guess rates or hard-code them in prompts.
- Packaged Compose verification was skipped again; the change only adds node content plus already-declared edge types and does not alter API behaviour. Session 62 remains the latest Compose-runtime proof. Re-run `docker compose up -d` next time API routing/auth changes.
- Remaining Phase C work is still on production-scale enrichment, not the local packaged demo path.

## Session 64 — Tax Enforcement Cases (2026-04-17)

### Status: COMPLETE — local richer demo graph now ships enforcement-case content with TaxType edges

### What was done

1. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable `enforcement`.
2. Routed `enforcement` through `src/inject_tax_cases.py --create-edges`, which injects enforcement content as `LawOrRegulation` nodes tagged with `regulationType IN {enforcement_case, enforcement_qa, enforcement_policy, enforcement_provincial}` and wires them to `TaxType` via `FT_GOVERNED_BY`.
3. Rebuilt `data/finance-tax-graph.demo` from the archived baseline with the expanded default path.
4. Re-verified the rebuilt demo graph directly in Kuzu (nodes, edges, and a sample TaxType→LR traversal).

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap,accounting,enforcement}`
- `python3 src/inject_tax_cases.py --dry-run --create-edges` reported `170` loaded, `95` would inject, `38` edges, by-source `{sat_case_report:20, 12366_enforcement:150}`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4827`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4827`, `edges=680` (from `4732`/`642` in Session 63)
  - `LawOrRegulation=95` (all with `regulationType` starting with `enforcement_`; breakdown: `enforcement_qa=75`, `enforcement_case=20`)
  - `FT_GOVERNED_BY=38` (new; from `0` in Session 63)
  - `ChartOfAccount=159` unchanged
- Sample `TaxType-[:FT_GOVERNED_BY]->LawOrRegulation` edges all point from `TT_VAT` to concrete VAT-fraud enforcement cases (e.g. 嘉峪关宏兴西域能源、安徽星印网络、扬州春风船舶机械), confirming the edges wire semantics correctly

### Notes for the next session

- The local/demo side of Phase C now ships a small but real enforcement-case corpus, which unblocks `ft-compliance-auditor` / `ft-risk-assessment` / `ft-legal-counsel` workflows that need concrete fraud patterns and penalty anchors.
- Packaged Compose verification was skipped again; the change only adds node content plus one existing edge type and does not alter API behaviour. Session 62 remains the latest Compose-runtime proof. Re-run `docker compose up -d` next time API routing/auth changes.
- Remaining Phase C work is still on production-scale enrichment, not the local packaged demo path.

## Session 63 — Chart of Accounts Expansion (2026-04-17)

### Status: COMPLETE — local richer demo graph now ships the full CAS standard chart of accounts

### What was done

1. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable `accounting`.
2. Routed `accounting` through the existing `src/inject_chart_of_accounts.py` injector (CAS 2024 standard, 157 first-level accounts across 6 categories).
3. Rebuilt `data/finance-tax-graph.demo` from the archived baseline with the expanded default path.
4. Re-verified the rebuilt demo graph directly against Kuzu.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_chart_of_accounts.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap,accounting}`
- `python3 src/inject_chart_of_accounts.py --dry-run` reported 157 standard accounts (68 资产 / 36 负债 / 5 共同 / 9 所有者权益 / 5 成本 / 34 损益)
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4732`
- Inline `inject_chart_of_accounts` verification reported `Total: 159` `ChartOfAccount` nodes (70 资产 / 36 负债 / 5 共同 / 9 所有者权益 / 5 成本 / 34 损益; the extra 2 资产 rows are legacy baseline entries preserved by MERGE)
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4732`, `edges=642`
  - `ChartOfAccount=159` (from `30` in Session 62)
  - `FAQEntry=1152`, `SocialInsuranceRule=138`, `InvoiceRule=40`, `ComplianceRule=84` (all unchanged)
- CoA sample spot-check across all six CAS categories:
  - `1001 库存现金` (资产), `1101 交易性金融资产` (资产)
  - `2001 短期借款` (负债)
  - `4001 实收资本` (所有者权益)
  - `5001 生产成本` (成本)
  - `6001 主营业务收入` (损益)

### Notes for the next session

- The local/demo side of Phase C now ships the full CAS standard chart of accounts by default, which unblocks `ft-accountant` / `ft-journal-engine` workflows that depend on the full first-level account set.
- Packaged Compose verification was skipped this session because the CoA change only adds node content and does not alter API behaviour; Session 62 remains the latest Compose-runtime proof. If the next task changes API routing or auth, run a fresh `docker compose up -d` pass before closing.
- Remaining Phase C work is still on production-scale enrichment, not the local packaged demo path.

## Session 62 — Seed Reference Expansion (2026-04-17)

### Status: COMPLETE — local richer demo graph now includes seed-backed reference types by default

### What was done

1. Added `src/inject_seed_reference_data.py` for:
   - `SocialInsuranceRule`
   - `TaxAccountingGap`
   - `IndustryBenchmark`
2. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable `seedrefs`.
3. Rebuilt `data/finance-tax-graph.demo` from the archived baseline with the expanded default path.
4. Re-verified the packaged stack against the rebuilt demo graph, including search hits for the new seed-backed types.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_seed_reference_data.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap}`
- `python3 src/inject_seed_reference_data.py --dry-run` reported:
  - `SocialInsuranceRule +138`
  - `TaxAccountingGap +50`
  - `IndustryBenchmark +45`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4563`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4563`, `edges=642`
  - `SocialInsuranceRule=138`
  - `TaxAccountingGap=50`
  - `IndustryBenchmark=45`
  - `ComplianceRule=84`
  - `FormTemplate=109`
  - `FTIndustry=19`
  - `RiskIndicator=125`
- Packaged runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - authenticated `/api/v1/stats` returned `total_nodes=4563`, `total_edges=642`, `node_tables=26`
  - proxied search for `养老保险` returned `SocialInsuranceRule` hits
  - proxied search for `税负率` returned `IndustryBenchmark` hits
  - proxied search for `预收账款` returned `TaxAccountingGap` hits
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Notes for the next session

- The local/demo side of Phase C now covers extracted content plus seed-backed reference types.
- Remaining Phase C work is still on production-scale enrichment, not the local packaged demo path.

## Session 61 — Demo Graph Small-Type Expansion (2026-04-17)

### Status: COMPLETE — local richer demo graph now includes compliance and industry content by default

### What was done

1. Extended `scripts/bootstrap_local_demo_graph.py` to support and default-enable:
   - `compliance`
   - `industry`
2. Reused the accounting-schema bootstrap for industry enrichment so `OP_*` tables are present before insertion.
3. Rebuilt `data/finance-tax-graph.demo` from the archived baseline with the expanded default path.
4. Re-verified the packaged stack against the rebuilt demo graph.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_compliance_data.py src/inject_industry_data.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help` now shows `--include {faq,cpa,compliance,industry,incentives,regions,mindmap}`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully and ended with `Node count: 4330`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4330`, `edges=642`
  - `ComplianceRule=84`
  - `FormTemplate=109`
  - `FTIndustry=19`
  - `RiskIndicator=125`
  - `OP_BusinessScenario=43`
  - `OP_StandardCase=392`
  - `FAQEntry=1152`
  - `CPAKnowledge=649`
  - `MindmapNode=990`
  - `TaxIncentive=109`
  - `AdministrativeRegion=477`
- Packaged runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - authenticated `/api/v1/stats` returned `total_nodes=4330`, `total_edges=642`, `node_tables=23`, plus the same enriched node mix
  - `curl 'http://localhost:3001/api/v1/search?q=%E5%90%88%E8%A7%84&limit=5'` returned `count=5` with `RiskIndicator` results
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Notes for the next session

- The local/demo side of Phase C has moved beyond FAQ/CPA into compliance and industry content.
- Remaining Phase C work is still production-scale enrichment, not the local packaged demo path.

## Session 60 — Delivery-Surface Audit (2026-04-17)

### Status: COMPLETE — rendered HTML and local runtime state are also clean

### What was done

1. Scanned the four PDCA HTML companions for stale `:8766`, `/api/rag`, `docker-compose`, and API-only Compose wording.
2. Recovered Docker daemon availability after a transient disconnect.
3. Re-checked the local Compose runtime state with `docker compose ps`.

### Verification

- HTML companion scan:
  - `rg -n '8766|/api/rag|docker-compose|packages only the API container|api container only|packages? only the api' doc/00_project/initiative_cognebula_sota/PRD.html doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.html doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.html doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.html` returned no matches
- Docker recovery:
  - `open -a /Applications/Docker.app`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_PRESENT`
  - `docker info` succeeded again
- Runtime state:
  - `docker compose ps` returned no running services
- Independent verifier verdict:
  - `PASS`
  - HTML delivery surface presents the packaged topology (`docker compose`, `:8400`, `:3001`) and contains no stale `:8766` / `/api/rag` / API-only Compose wording

### Notes for the next session

- The self-hosted packaging/docs closeout lane is now clean across:
  - README
  - `doc/index.md`
  - PDCA markdown truth sources
  - PDCA HTML companions
  - local Compose runtime state

## Session 59 — PDCA Packaged Topology Sync (2026-04-17)

### Status: COMPLETE — PDCA canonical docs are now aligned to the packaged topology

### What was done

1. Updated the PDCA markdown sources:
   - `PRD.md`
   - `SYSTEM_ARCHITECTURE.md`
   - `USER_EXPERIENCE_MAP.md`
   - `PLATFORM_OPTIMIZATION_PLAN.md`
2. Removed the remaining stale `:8766` / `/api/rag` / API-only Compose wording from those sources.
3. Re-rendered the corresponding HTML companions.
4. Ran an independent verifier pass over the four PDCA markdown sources.

### Verification

- Local command verification:
  - `rg -n '8766|/api/rag|docker-compose|packages only the API container' ...` across the four PDCA markdown sources returned no matches
  - `ls -l` confirmed fresh render timestamps for `PRD.html`, `SYSTEM_ARCHITECTURE.html`, `USER_EXPERIENCE_MAP.html`, and `PLATFORM_OPTIMIZATION_PLAN.html`
- Independent verifier verdict:
  - `PASS`
  - no remaining stale `localhost:8766`, `/api/rag`, or API-only Compose wording in the four PDCA docs

### Notes for the next session

- The self-hosted packaging/docs closeout lane now covers:
  - README examples
  - `doc/index.md` route index
  - PDCA canonical markdown + HTML companions
- Remaining work is outside this lane: graph scale and business-content depth.

## Session 58 — Compose Command + Route Index Sync (2026-04-17)

### Status: COMPLETE — self-hosted docs are now consistent on command syntax and local route indexing

### What was done

1. Replaced the remaining self-hosted `docker-compose` examples in `README.md` with `docker compose`.
2. Added the local packaged `:3001` route entries to `doc/index.md`:
   - `http://localhost:3001/`
   - `http://localhost:3001/api/v1/*`
3. Re-ran `docker compose config` after the doc-only sync.

### Verification

- `if rg -n 'docker-compose' README.md; then ... else echo README_COMPOSE_CLEAN; fi` -> `README_COMPOSE_CLEAN`
- `rg -n 'http://localhost:3001/|http://localhost:3001/api/v1/\\*' doc/index.md` returned both packaged local route entries
- `docker compose config` exited `0`

### Notes for the next session

- The self-hosted packaging/docs lane is now internally consistent on:
  - command syntax: `docker compose`
  - protected API: `:8400`
  - packaged local web/proxy: `:3001`

## Session 57 — README Example Runtime Proof (2026-04-17)

### Status: COMPLETE — updated README packaged API examples are now runtime-verified

### What was done

1. Restored the local Docker daemon by relaunching Docker Desktop.
2. Re-ran the packaged stack against `data/finance-tax-graph.demo`.
3. Executed the new README example shapes against the live stack:
   - protected `:8400 /api/v1/search`
   - protected `:8400 /api/v1/hybrid-search`
   - proxied `:3001 /api/v1/search`
4. Shut the stack back down after verification.

### Verification

- Docker recovery:
  - `open -a /Applications/Docker.app`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_PRESENT`
  - `docker info` succeeded against `docker-desktop`
- Packaged runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
- README example proof:
  - protected `search` returned `count=5` with top hits including `TT_VAT` and `TT_LAND_VAT`
  - protected `hybrid-search` returned `count=5`, `method=hybrid_rrf`, `text_hits=15`, and non-empty `graph_expansion`
  - proxied `:3001` `search` returned the same top-5 result set as the protected `:8400` search
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Notes for the next session

- Session 56's Docker-socket blocker is resolved.
- The packaged README examples are now backed by fresh live-stack proof, not just code/doc inspection.

## Session 56 — README Packaged API Sync (2026-04-17)

### Status: COMPLETE — top-level self-hosted docs now match the active packaged API surface

### What was done

1. Removed the stale `localhost:8766/api/rag` example from the README self-hosted usage section.
2. Replaced it with current packaged examples for:
   - `http://localhost:8400/api/v1/search`
   - `http://localhost:8400/api/v1/hybrid-search`
   - `http://localhost:3001/api/v1/search`
3. Recorded the current Docker-daemon blocker instead of pretending a fresh third runtime pass succeeded.

### Verification

- `README.md` now documents the active packaged API entrypoints on `:8400` and `:3001`
- `rg -n "8766|api/rag" README.md` no longer matches the packaged usage section
- Docker environment check:
  - `docker context show` -> `desktop-linux`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_MISSING`
  - a fresh `docker compose up -d` attempt could not connect to the local Docker daemon in this session

### Notes for the next session

- At the end of Session 56, Session 55 remained the latest successful packaged runtime proof.
- If a new runtime proof is needed, first restore the local Docker daemon so `~/.docker/run/docker.sock` exists again.
  Historical note: this blocker was resolved in Session 57.

## Session 55 — Demo Bootstrap Parity Fix (2026-04-16)

### Status: COMPLETE — default bootstrap path and runtime evidence are now consistent

### What was done

1. Fixed `scripts/bootstrap_local_demo_graph.py` so its default `--include` set explicitly includes `mindmap`.
2. Rebuilt `data/finance-tax-graph.demo` from the archived baseline after the fix.
3. Re-verified the rebuilt demo graph directly in KuzuDB and through the packaged API/web-proxy stack.
4. Corrected the closeout record to the real native table mix (`FAQEntry` / `CPAKnowledge` / `MindmapNode`) instead of the stale `LawOrRegulation`-heavy assumption.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_faq_data.py src/inject_cpa_data.py src/inject_mindmap_native.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` now shows the `[mindmap] ... src/inject_mindmap_native.py` step in the default flow and ends with `Node count: 3847`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=3847`, `edges=642`
  - `FAQEntry=1152`
  - `CPAKnowledge=649`
  - `MindmapNode=990`
  - `AdministrativeRegion=477`
  - `OP_StandardCase=266`
  - `TaxIncentive=109`
  - `LawOrRegulation=0`
- Packaged stack with demo graph:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - authenticated `curl -H 'X-API-Key: dummy' http://localhost:8400/api/v1/stats` returned `nodes=3847`, `edges=642`, `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `AdministrativeRegion=477`, `OP_StandardCase=266`, `TaxIncentive=109`, `LawOrRegulation=0`
  - `curl http://localhost:3001/api/v1/stats` through the packaged web proxy returned the same stats
  - `curl -I http://localhost:3001/` returned `200 OK`
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
  - verification stack was torn down with `docker compose down`

### Notes for the next session

- If the next task needs richer local graph exploration, use `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo`.
- Trust `FAQEntry` / `CPAKnowledge` / `MindmapNode` as the current richer-demo node mix; do not rely on the earlier `LawOrRegulation=1801` assumption.

## Session 54 — Local Demo Graph Bootstrap (2026-04-16)

### Status: COMPLETE — richer local demo graph is now reproducible

### What was done

1. Added `scripts/bootstrap_local_demo_graph.py`.
2. The bootstrap flow now copies `data/finance-tax-graph.archived.157nodes` into `data/finance-tax-graph.demo`.
3. FAQ, CPA-case, tax incentive, administrative-region, and native `MindmapNode` injection are now part of the default local enrichment path.
4. CPA enrichment auto-creates the required `OP_` schema before injecting CPA case nodes.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` completed successfully
- Demo graph counts:
  - baseline: `157` nodes / `35` edges
  - demo: `3847` nodes / `642` edges
  - `FAQEntry`: `1152`
  - `CPAKnowledge`: `649`
  - `MindmapNode`: `990`
  - `LawOrRegulation`: `0`
  - `OP_StandardCase`: `266`
  - `TaxIncentive`: `109`
  - `AdministrativeRegion`: `477`
- Packaged API with demo graph:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d cognebula-api`
  - authenticated `/api/v1/stats` returned `nodes=3847`, `edges=642`, `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `LawOrRegulation=0`, `OP_StandardCase=266`, `TaxIncentive=109`, `AdministrativeRegion=477`
  - packaged web proxy also returned `status=healthy`, `kuzu=true` when the full stack was run against the richer demo graph

### Notes for the next session

- If the next task needs richer local graph exploration, use `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo`.

## Session 53 — Phase C Script Portability (2026-04-16)

### Status: COMPLETE — remaining content-backfill scripts are now portable and preflightable

### What was done

1. Added `--db-path` and `KUZU_DB_PATH` support to:
   - `scripts/cpa_content_backfill.py`
   - `scripts/mindmap_batch_backfill.py`
   - `scripts/ld_description_backfill.py`
2. Added `--dry-run` read-only inspection mode to those three scripts.
3. Added the missing `MindmapNode` table-existence precheck so local dry-run exits cleanly instead of crashing with a binder exception.

### Verification

- `python3 -m py_compile` passed for all three scripts
- `--help` now shows `--db-path` for all three scripts
- Local dry-run against the bundled baseline graph:
  - `cpa_content_backfill.py` → `SKIP: CPAKnowledge table does not exist`
  - `mindmap_batch_backfill.py` → `SKIP: MindmapNode table does not exist`
  - `ld_description_backfill.py` → `SKIP: LegalDocument table does not exist in this DB`

### Notes for the next session

- The remaining Phase C work is now content/data work, not script portability work.

## Session 52 — Self-hosted Compose Packaging (2026-04-16)

### Status: COMPLETE — self-hosted packaging is runtime-verified locally

### What was done

1. Added `web/Dockerfile` to build the exported Next.js app into a static image.
2. Added `docker/nginx.web.conf.template` so the packaged web container can proxy `/api/v1/*` to `cognebula-api` and inject `X-API-Key` server-side.
3. Expanded `docker-compose.yml` to run `cognebula-api` plus `cognebula-web`.
4. Added root `.dockerignore` so the web build context no longer ships the whole repo into Docker.
5. Reworked the API image to install only the minimal runtime dependencies used by `kg-api-server.py` instead of the repo-wide ML-heavy requirements set.
6. Fixed the web healthcheck to probe `127.0.0.1` instead of `localhost`, avoiding false `unhealthy` status from IPv6 loopback resolution.
7. Pointed the packaged API mount at the real local baseline Kuzu file (`data/finance-tax-graph.archived.157nodes`) instead of the empty `data/finance-tax-graph/` directory, with env override support for a richer local graph.
8. Changed the packaged web default port to `3001` so the stack starts cleanly in this environment without a manual port override.
9. Updated `README.md` for the packaged access points (`:3001` web, `:8400` API), configurable web port override, and graph-path override.

### Verification

- `docker compose config` passed
- `KG_API_KEY=dummy docker compose config` passed with both `cognebula-api` and `cognebula-web` receiving the expected env wiring
- `KG_API_KEY=dummy docker compose build cognebula-web` passed after adding `.dockerignore`
- `KG_API_KEY=dummy docker compose build cognebula-api` passed after switching the API image to a minimal runtime dependency set
- `KG_API_KEY=dummy docker compose up -d` started the packaged stack on its default ports
- `curl -I http://localhost:3001/` returned `200 OK`
- `curl http://localhost:3001/api/v1/health` returned `status=healthy`, `kuzu=true` through the packaged web proxy
- `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
- `KG_API_KEY=dummy docker compose down` removed the local verification stack cleanly
- Docker CLI is installed locally (`docker --version` succeeded)
- Active Docker context is `desktop-linux`
- Re-rendered HTML companions for the updated PDCA markdown docs after Session 52 packaging changes

### Residual Local Runtime Note

- The packaged stack is healthy against the bundled baseline graph (`157` nodes / `35` edges). For richer local behavior, override `COGNEBULA_GRAPH_PATH` to a larger Kuzu file.

### Notes for the next session

- If the next task needs a richer local graph than the bundled baseline, point `COGNEBULA_GRAPH_PATH` at `./data/finance-tax-graph.demo`.

## Session 51 — Static Web Auth Proxy Alignment (2026-04-16)

### Status: COMPLETE — browser-safe frontend access path aligned to protected API

### What was done

1. Confirmed the Next.js app must remain `output: export`, so a Next App Route proxy cannot be used.
2. Repointed the browser KG client to `https://cognebula-kg-proxy.workers.dev/api/v1`.
3. Updated the Cloudflare Worker proxy to inject `KG_API_KEY` from Worker env/secret and use `KG_API_ORIGIN` config.
4. Synced PRD / architecture / UX / optimization docs to the new static-frontend access path.

### Verification

- `npm run build` passed in `web/`
- Static build completed successfully across all 38 routes
- `./web/node_modules/.bin/tsc --noEmit --target es2022 --module esnext --lib es2022,dom worker/src/index.ts` passed
- No App Route remains under `web/src/app/api/`
- `web/src/app/lib/kg-api.ts` now defaults to `https://cognebula-kg-proxy.workers.dev/api/v1`
- Regenerated HTML companions for `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `USER_EXPERIENCE_MAP.md`, and `PLATFORM_OPTIMIZATION_PLAN.md`

### Notes for the next session

- The next unresolved Phase D item is still customer-facing Docker Compose packaging; auth and hybrid retrieval are no longer the blocking gaps.

## Session 50 — Closeout Tail Cleanup (2026-04-16)

### Status: COMPLETE — closeout debt removed from active tooling/docs

### What was done

1. Standardized active tooling auth on `KG_API_KEY` by removing the remaining `COGNEBULA_API_KEY` dependency from `benchmark/run_eval.py` and `cognebula_mcp.py`.
2. Updated MCP server copy/metrics to the current `856K+ nodes / 2M+ edges` platform baseline.
3. Aligned the superseded Session 47 density target wording with the canonical `2M+ total edges` KPI so the handoff no longer carries a stale target as if it were current.

### Verification

- `python3 -m py_compile benchmark/run_eval.py cognebula_mcp.py`
- `rg -n "COGNEBULA_API_KEY" benchmark/run_eval.py cognebula_mcp.py` returns no hits
- Runtime env-resolution check:
  - `run_eval.py` reads `KG_API_KEY` when set and ignores legacy `COGNEBULA_API_KEY`
  - `cognebula_mcp.py` reads `KG_API_KEY` when set and ignores legacy `COGNEBULA_API_KEY`
- Live auth check on the active remote API:
  - unauthenticated `GET /api/v1/stats` → `401 Unauthorized`
  - unauthenticated `GET /api/v1/quality` → `401 Unauthorized`
- Session 48 production evidence remains canonical: `benchmark/results_hybrid_20260416_after_security_fix.json`, `/api/v1/stats`, `/api/v1/quality`

## Session 48 — Semantic Edges Load Closure (2026-04-16)

### Status: COMPLETE — semantic edge blocker resolved end-to-end

### Final State

| Metric | Value | Verification |
|--------|-------|--------------|
| Nodes | 856,072 | `/api/v1/stats` |
| Edges | 2,017,420 | `/api/v1/stats` (latest manual verification) |
| Density | 2.356 | post-load script summary |
| `SEMANTIC_SIMILAR` | 570,481 | `/api/v1/stats` |
| Quality Gate | PASS / 100 | `/api/v1/quality` |
| Hybrid Benchmark | 79% overall / 100 pass / 0 fail / 0 errors | `benchmark/results_hybrid_20260416_after_security_fix.json` |

### What was done

1. Fixed `scripts/build_semantic_edges.py` to bulk load REL TABLE GROUP edges with explicit `from/to` COPY options.
2. Added per-type cleanup before reload so the earlier 1000-edge fallback residue does not accumulate on rerun.
3. Synced the script to `kg-node`, stopped `kg-api`, reran the full semantic-edge builder, and restarted `kg-api`.
4. Fixed `benchmark/run_eval.py` so it falls back to `KG_API_KEY` when `COGNEBULA_API_KEY` is unset, matching the production API auth.

### Key Evidence

- Import runtime: `827s`
- Semantic edges added: `+570,481`
- Total edges immediately after import: `2,016,849`
- Total edges at latest manual verification: `2,017,420` (`SEMANTIC_SIMILAR` unchanged at `570,481`; delta came from background non-semantic writes)
- Quality endpoint remained `PASS / 100`
- Hybrid benchmark remained stable at `79%` overall with `100/100` question pass count; canonical evidence is `benchmark/results_hybrid_20260416_after_security_fix.json`

### Notes for the next session

- The Session 47 blocker is fully resolved. Do not re-open it unless `/api/v1/stats` shows `SEMANTIC_SIMILAR` materially below `570,481`.
- Session 47 density wording has been aligned to the canonical `2M+ total edges` KPI; treat any density figure there as historical context only.

## Session 47 — Semantic Edges (2026-04-16)

### Status: HISTORICAL — superseded by Session 48

### Current State

| Metric | Value | PRD Target |
|--------|-------|-----------|
| Nodes | 856,072 | 800K+ |
| Edges | 1,453,368 | 2M |
| Density | 1.70 | Historical proxy only; superseded by `2M+` total edges KPI |
| Vectors | 869,882 | ~100% coverage |
| Quality | 100/100 | 95+ |
| Hybrid | 100/100 (79% overall) | 75%+ |
| API | HEALTHY | -- |

### What was done

1. **Semantic edge CSV generation COMPLETE** (`scripts/build_semantic_edges.py`):
   - Used numpy batch cosine similarity (not per-vector LanceDB search)
   - Pre-filtered IDs against KuzuDB to remove stale entries
   - Generated 570,481 edge pairs across 7 tables:

   | Table | Edges | K | Time |
   |-------|-------|---|------|
   | LawOrRegulation | 129,050 | 8 | 27s |
   | KnowledgeUnit | 121,218 | 6 | 55s |
   | DocumentSection | 121,332 | 4 | -- |
   | RegulationClause | 96,589 | 2 | 7min |
   | MindmapNode | 74,663 | 4 | -- |
   | CPAKnowledge | 23,697 | 5 | -- |
   | FAQEntry | 3,932 | 5 | -- |

   CSV location on VPS: `/home/kg/cognebula-enterprise/data/edge_csv/semantic/`

2. **Two bugs found and partially fixed**:

   - **Bug 1 (FIXED): LanceDB filter syntax** — `tbl.search()` empty query + `.where("\"table\" = 'X'")` returns 0 in LanceDB 0.29. Fix: use `tbl.to_lance().to_table(filter=pa_ds.field("table") == table)` with PyArrow expression for data loading, backtick quoting for KNN search.

   - **Bug 2 (NOT FIXED): KuzuDB REL TABLE GROUP COPY FROM** — Created `SEMANTIC_SIMILAR` as REL TABLE GROUP (7 FROM/TO pairs). COPY FROM fails with: `"The table SEMANTIC_SIMILAR has multiple FROM and TO pairs defined in the schema. A specific pair of FROM and TO options is expected when copying data into the SEMANTIC_SIMILAR table."` Fallback to individual CREATE only inserts 1000 per table.

### Blocker: How to fix the COPY FROM

**Option A (recommended)**: Drop the REL TABLE GROUP and create per-type tables:
```sql
DROP TABLE SEMANTIC_SIMILAR;
CREATE REL TABLE SEMANTIC_SIM_LR(FROM LawOrRegulation TO LawOrRegulation);
CREATE REL TABLE SEMANTIC_SIM_KU(FROM KnowledgeUnit TO KnowledgeUnit);
-- etc for each type
COPY SEMANTIC_SIM_LR FROM "/path/laworregulation_similar.csv" (header=false);
COPY SEMANTIC_SIM_KU FROM "/path/knowledgeunit_similar.csv" (header=false);
```

**Option B**: Use the internal sub-table name that KuzuDB creates for GROUP members (need to check `CALL show_tables()` for exact names), then COPY into each sub-table.

**Option C**: In COPY command, specify the FROM/TO pair:
```sql
COPY SEMANTIC_SIMILAR FROM "file.csv" (FROM LawOrRegulation TO LawOrRegulation, header=false)
```
(Untested — check KuzuDB 0.x docs for syntax)

### What to do next

1. **Stop API**: `sudo systemctl stop kg-api`
2. **Fix edge loading**: Use Option A/B/C above to COPY all 7 CSVs into KuzuDB
3. **Restart API**: `sudo systemctl start kg-api`
4. **Verify**: Check total edges (should be ~1,420,536 + 570,481 = ~1,991,017 → ~2M target)
5. **Run benchmarks**: Quality + Hybrid to confirm no regression
6. **If edges reach 2M**: All PRD metrics met. Update HANDOFF as COMPLETE.

### Files modified this session

| File | Change |
|------|--------|
| `scripts/build_semantic_edges.py` | Fixed LanceDB filter (PyArrow), numpy batch cosine, KuzuDB ID pre-filter, REL TABLE GROUP creation |

### Key decisions

- **Numpy batch over LanceDB per-vector search**: 23K vectors processed in 27s vs estimated 40min. Orders of magnitude faster.
- **Cosine distance threshold 0.35** (~82% similarity): Produces reasonable edge counts without over-connecting.
- **RC limited to K=2, max 100K**: Avoids explosion on 645K table while still generating ~97K edges.

---

## Session 46 — Edge Boost v2 + Benchmark Fixes (2026-04-14)

### Status: DONE

### What was done

1. **Embedding round 2 COMPLETE**: 453,361 RegulationClause vectors, 597 min, IVF index built
   - LanceDB total: 869,882 vectors (~100% coverage)
   - Quality score: 100/100

2. **RRF type boost rebalancing** (kg-api-server.py):
   - TaxType 0.005→0.012, KU 0.003→0.010, LR 0.003→0.001, RC/MN/DS→0
   - Hybrid benchmark: 100/100 PASS (79% overall)

3. **Edge density boost v2** (`scripts/boost_edge_density_v2.py`):
   - NEXT_CLAUSE: +628,130 (sequential RC ordering)
   - FAQ_ABOUT_TAX/CPA_ABOUT_TAX: +674
   - Inline edge boost v3: SUPERSEDES +179, NEXT_SECTION +41K
   - Total: 723K → 1,420,536 edges

4. **eval_stats() fixes**: nodes_by_type lookup, edge_type detection, _KNOWLEDGE_TYPES expansion

### Key files

- `kg-api-server.py` — RRF boost table, _TABLE_COLUMNS mapping
- `benchmark/run_eval.py` — eval_stats, _KNOWLEDGE_TYPES
- `scripts/boost_edge_density_v2.py` — 7-task edge generation
- `scripts/rebuild_embeddings.py` — OOM fix (resume mode uses to_lance())

## Session 69 finishing touches (2026-04-17 post-summary)

- Fixed `tests/test_ontology_conformance.py` syntax error (removed invalid walrus `ORPHAN_NODES := None` from import tuple — `ORPHAN_NODES` lives only in `scripts/migrate_phase0_drop_empty.py`, never exported from the audit module)
- Adjusted 2 test expectations to match real auditor logic: empty DB => FAIL/medium (35 missing > 5 threshold); 10-node canonical subset => FAIL/medium (25 missing > 5); added `test_audit_full_canonical_coverage_passes` for the true PASS path
- **19/19 tests green** via `.venv/bin/python -m pytest tests/test_ontology_conformance.py -v`
- Validated CLI `scripts/check_ontology_conformance.py --local data/finance-tax-graph.demo` → 56 types / 44 rogue / high severity / V1/V2 bleed=[FormTemplate] (expected pre-Phase 0 baseline)
- Validated `.github/workflows/ontology-gate.yml` YAML syntax (yaml.safe_load OK)
- Added `scripts/migrate_phase1d_taxincentive_merge.py` — staged TaxIncentiveV2 → TaxIncentive row merge with schema-diff probe + conflict count + REL dependency enumeration; `--dry-run` default, `--execute` requires zero `v2_only` columns and reports non-empty REL deps for manual rewrite. Dry-run on demo correctly returns "no V2 table present" (V2 is prod-only).
- Updated `doc/00_project/initiative_cognebula_sota/task_plan.md` with Session 68 + 69 entries; B0/B2 prod execution still HITL-gated waiting for explicit "B0 B2" trigger

Still pending (HITL):
- B0 — Phase 0 prod drop of 19 orphan node tables (~10 min downtime)
- B2 — Phase 1 prod ALTER RENAME of 3 V2 stubs (~60s downtime)
- Phase 1d — TaxIncentiveV2 merge on prod (script now ready; same HITL gate)
- Phases 3-4 — SaaS eviction / legacy folding (still design-only)

## Session 69 finishing touches (part 2, 2026-04-17)

- **Phase 1d end-to-end validation on a throwaway DB copy** (`data/finance-tax-graph.demo.phase1d-test`): injected TaxIncentiveV2 with 5 rows (2 id-conflicts with canonical + 3 net-new), ran dry-run → EXECUTE, confirmed:
  - canonical TaxIncentive went 109 → 112 rows (exactly +3 net-new)
  - 2 conflict ids kept canonical name (ON CREATE SET didn't overwrite existing rows)
  - 3 new V2 rows inserted with their V2 names
  - TaxIncentiveV2 table dropped
  - throwaway DB cleaned up after verification
- **Phase 2 staged cypher authored** (`deploy/contabo/migrations/phase2_duplicate_cluster_collapse.cypher`):
  - 4 cluster blocks: 2A policy (3→1 TaxIncentive), 2B industry (5→1 IndustryBenchmark), 2C accounting (6→2 AccountingSubject + JournalEntryTemplate), 2D tax_rate (6→1+ TaxRate, TaxRateSchedule may stay)
  - Each cluster has dry-run probe queries + merge-scaffold pattern + per-cluster sub-phase contract (audit / confirm / widen / author / execute / re-audit)
  - Cluster 2C flagged as the riskiest (6-way fold, split targets)
  - Cluster 2D note: `TaxCalculationRule` is a legitimate v4.2 canonical, NOT a rate — must be removed from duplicate_clusters bucket (minor fix to `src/audit/ontology_conformance.py` once confirmed from prod sample)
  - Phase 2 NOT executable as-is; requires per-cluster dry-run row counts + merge-block authoring before EXECUTE

## Session 69 finishing touches (part 3, 2026-04-17)

- **Fixed TaxCalculationRule misclassification** in `src/audit/ontology_conformance.py` — removed from `DUPLICATE_CLUSTERS["tax_rate"]` (schema line 73 confirms it's a canonical v4.2 Tier 2 node, not a rate duplicate). Added regression test `test_classify_taxcalculationrule_is_not_duplicate` to prevent silent re-addition. **20/20 tests now green.**
- **Phase 4 staged cypher authored** (`deploy/contabo/migrations/phase4_legacy_folding.cypher`):
  - 4a: widen `KnowledgeUnit` with `legacyType` / `legacyParentId` / `legacyPath` columns via ALTER TABLE ADD (with CREATE+COPY+DROP fallback noted)
  - 4b: CPAKnowledge (~7,371 rows) → KnowledgeUnit with `id = 'CPAK_' + src.id` prefix scheme, `legacyType='cpa_knowledge'`
  - 4c: MindmapNode (~28,526 rows) → KnowledgeUnit with `id = 'MIND_' + src.id`, flattens tree via `legacyParentId` + `legacyPath`, `legacyType='mindmap_node'`
  - 4d: verification queries by legacyType partition + expected audit deltas
  - Risks & abort criteria: ALTER TABLE column add (Vela 0.12), id-collision prevention via prefix, throughput floor 500 rows/sec (36k rows total)
  - Order: 4a → 4b (smaller, validates pattern) → 4c (larger, reuses pattern) → 4d

## Session 69 finishing touches (part 4, 2026-04-17)

- **End-to-end canonical-schema validation as integration test**: `test_canonical_schema_applied_to_fresh_db_passes_audit` parses all 114 DDL statements from `schemas/ontology_v4.2.cypher`, applies them to a fresh in-memory Kuzu DB, then asserts auditor returns `canonical_count=35`, `live_count=35`, `rogue=[]`, `missing=[]`, `verdict=PASS`, `severity=low`. This is the golden path: proof that our canonical source of truth is internally consistent and produces the expected audit shape when realized.
- **21/21 tests green** — the suite now covers: canonical schema parsing, live-table listing, rogue classification (6 buckets + mixed + TaxCalculationRule regression), audit integration (empty / partial / full / V1V2 / over-ceiling / medium-threshold / shape), Brooks constant, end-to-end canonical application.

## Session 69 finishing touches (part 5, 2026-04-18)

- **Phase 0 migration integration tests** (`tests/test_migrate_phase0.py`): 4 subprocess-level tests against `scripts/migrate_phase0_drop_empty.py`:
  - `test_dry_run_reports_plan_without_mutating` — probes plan output, verifies no state change
  - `test_execute_drops_empty_orphans_and_dependent_rels` — seeds 3 orphans + 2 empty orphan-touching RELs + 1 untouched REL + 1 canonical + 1 non-orphan rogue; verifies post-execute state: orphans gone, empty RELs gone, canonical + non-orphan rogue + untouched REL preserved
  - `test_execute_is_idempotent` — second run after execute finds "No orphan node tables present"
  - `test_script_refuses_nonexistent_db` — exit code 2 on missing path
- **Full suite: 25/25 green** (21 auditor + 4 Phase 0 migration)

## Session 69 finishing touches (part 6, 2026-04-19)

- **Phase 1d migration integration tests** (`tests/test_migrate_phase1d.py`): 6 subprocess-level tests against `scripts/migrate_phase1d_taxincentive_merge.py`:
  - `test_no_v2_exits_zero_with_friendly_message` — canonical-only DB returns "No TaxIncentiveV2 table"
  - `test_dry_run_reports_plan_without_mutating` — 3 V2 + 2 canonical (1 conflict), dry-run reports counts and conflicts without writing
  - `test_execute_merges_and_preserves_conflicts` — end-to-end: 2→4 canonical rows, conflict id (`INCE_A`) keeps `canonical-A` name (not V2 overwrite), 2 net-new rows appear, V2 table dropped
  - `test_execute_refuses_schema_mismatch` — V2 with extra column beyond canonical triggers exit 2 without mutation
  - `test_execute_is_idempotent` — second run finds no V2 table
  - `test_script_refuses_nonexistent_db` — exit 2 on missing path
- **Full suite: 31/31 green** (21 auditor + 4 Phase 0 + 6 Phase 1d)

Every migration script that can execute against prod (Phase 0 + Phase 1d) is now regression-tested at subprocess level. Phase 1 ALTER RENAME (`B2`) is a 3-line inline cypher and Phase 2/4 are per-cluster authored blocks — both require bespoke tests when the actual merge bodies get written.

## Session 69 finishing touches (part 7, 2026-04-19)

- **Auditor extended to REL tables (edge drift)** — `src/audit/ontology_conformance.py`:
  - New helpers `parse_canonical_rel_tables()` (regex handles both `CREATE REL TABLE` and `CREATE REL TABLE GROUP`) and `list_live_rel_tables()` (filters `show_tables()` rows where type=REL)
  - `audit()` result now includes top-level `edges` dict: `{canonical_count, live_count, intersection, missing_from_prod, rogue_in_prod}` — additive, verdict/severity unchanged (backward compatible for the CI gate)
  - CLI `scripts/check_ontology_conformance.py` `print_report()` now shows an edges block
- **New surface**: on demo DB the auditor reveals 75 missing canonical RELs + 75 rogue RELs (code-analysis residue like `CALLS_AA/CALLS_FA/…`, same origin as orphan nodes). Phase 0 execution on demo previously dropped 39 of these empty RELs already; the remaining gap is real data rewiring needed for Phase 4 legacy folding.
- **5 new edge-level tests**:
  - `test_parse_canonical_rel_tables_matches_schema`
  - `test_list_live_rel_tables_empty_db`
  - `test_list_live_rel_tables_excludes_node_tables`
  - `test_audit_includes_edges_section_with_canonical_schema`
  - `test_audit_edges_detects_rogue_rel`
  - Plus: strengthened `test_canonical_schema_applied_to_fresh_db_passes_audit` to also assert 0 edge drift
- **Full suite: 36/36 green** (26 auditor + 4 Phase 0 + 6 Phase 1d)
- Ontology audit is now node+edge complete. Future CI gate tightening can add `--max-rogue-edges` as another threshold alongside `--max-rogue`.

## Session 69 finishing touches (part 8, 2026-04-19)

- **CI gate gains edge threshold** `--max-rogue-edges` in `scripts/check_ontology_conformance.py`:
  - Parallel to `--max-rogue`: if either threshold is set, the server verdict is ignored and the decision comes from threshold comparisons
  - Either failure fails the gate; pass message reports both actuals
  - Exit 1 confirmed on edge threshold breach (75 > 50 → FAIL); exit 0 confirmed on both within-threshold
- **CI workflow wired** `.github/workflows/ontology-gate.yml` now invokes `--max-rogue 70 --max-rogue-edges 100` (baseline grace; prod ~75 edge rogue today)
- **Runbook threshold schedule extended** to two columns (node + edge ratchet), 9 rows tracking `--max-rogue` / `--max-rogue-edges` targets per phase: baseline `70/100` → after all phases `0/0`
- Full suite still green (36/36)

## Session 69 finishing touches (part 9, 2026-04-19)

- **Edge rogue classification** added to auditor (`src/audit/ontology_conformance.py`):
  - Constants `CODE_ANALYSIS_REL_PREFIXES` (CALLS_, DEFINES_, IMPORTS_, EXTENDS_, IMPLEMENTS_, CONTAINS, MEMBER_OF) and `LEGACY_REL_PREFIXES` (FT_, OP_, CO_, XL_, DOC_)
  - Helper `_match_prefix()` handles both trailing-underscore prefixes and exact-name matches (e.g., `CONTAINS` alone vs `CONTAINS_FOLDER`)
  - New `classify_rogue_edges()` function buckets rogue REL names into `code_analysis_residue` / `legacy_prefixes` / `other`
  - Added under `result["edges"]["rogue_buckets"]` (additive, backward compat preserved)
- **Demo baseline** (75 rogue edges): 24 code-analysis residue + 49 legacy prefixes + 2 other (RELATED_TO, REGION_PARENT_OF). Maps directly to migration phases:
  - code_analysis_residue → Phase 0 (dropped as part of orphan-touching empty RELs)
  - legacy_prefixes → Phase 2/4 (folded into canonical edge labels when their node endpoints collapse)
  - other → case-by-case review
- **5 new edge-classification tests**:
  - `test_classify_rogue_edges_code_analysis`
  - `test_classify_rogue_edges_legacy_prefixes`
  - `test_classify_rogue_edges_other_bucket`
  - `test_classify_rogue_edges_mixed`
  - `test_audit_edges_has_rogue_buckets` (integration with `audit()`)
- **CLI `print_report()` shows edge bucket counts** (code-analysis residue / legacy prefixes / unclassified)
- **Full suite: 41/41 green** (31 auditor + 4 Phase 0 + 6 Phase 1d). Audit now gives phase planners a direct "how many edges each phase will dissolve" read.

## Session 69 finishing touches (part 10, 2026-04-19)

- **CLI test suite** `tests/test_check_cli.py` — 10 subprocess tests against `scripts/check_ontology_conformance.py`:
  - `test_local_no_thresholds_fails_on_fresh_db` — server-verdict fallback (FAIL/medium on empty)
  - `test_max_rogue_threshold_pass` / `fail` — node rogue gate
  - `test_max_rogue_edges_threshold_pass` / `fail` — edge rogue gate (new code path)
  - `test_both_thresholds_pass` — combined gate: both reported
  - `test_both_thresholds_one_fails` — either failure fails overall, only the failing side surfaces
  - `test_json_stdout_is_pure_json` — `--json` stdout parses, FAIL lines go to stderr
  - `test_missing_required_group_exits_with_error` — argparse group error = exit 2
  - `test_nonexistent_local_db_exit_2` — missing path = exit 2
- **Full suite: 51/51 green** (31 auditor + 4 Phase 0 + 6 Phase 1d + 10 CLI). The CI gate decision logic, threshold parsing, and JSON output surface are now regression-locked.

## Session 69 finishing touches (part 11, 2026-04-20)

- **Drift report refreshed with edge audit** (was pre-edge-audit):
  - `ONTOLOGY_DRIFT_REPORT.md` — new §7 "Edge-level drift": counts table (canonical 79 / live 79 / intersection 4 / missing 75 / rogue 75), 3-row rogue bucket table (24 code_analysis_residue → Phase 0, 49 legacy_prefixes → Phase 2/4, 2 other → case-by-case), explanation of the 4/79 intersection gap, pointer to CI gate `--max-rogue-edges 100` and threshold schedule
  - `ONTOLOGY_DRIFT_REPORT.html` — Chinese companion (2份制 rule), mirror §七 with same tables + dated footer "2026-04-17（初版）· 2026-04-19（边层审计增补）", HTML parses cleanly
- **Drift report now captures both dimensions** that the auditor measures; downstream consumers (PR reviewers, audit swarms) see the full picture without having to re-probe the auditor API.
- Full suite still green (51/51)

## Session 69 finishing touches (part 12, 2026-04-20) — SOTA Gap Swarm Audit

- **3-round × 17-lens swarm audit** delivered on "距离 SOTA 还差什么":
  - `outputs/reports/ontology-audit-swarm/2026-04-20-kg-sota-gap.md` (English canonical)
  - `outputs/reports/ontology-audit-swarm/2026-04-20-kg-sota-gap.html` (Chinese BCG style — benchmark/gap analysis per html-style-router §Tier-2)
  - Memory log: `state/memory/2026-04-20.md`
- **Structural finding**: infrastructure maturity > capability maturity. Auditor / CI gate / migration pipeline / test suite are production-grade, but there is no benchmark, no explainability surface, no user.
- **6 Must-Have** items gate the leap from "experimental KG" to "benchmarkable system":
  1. B0 prod execution
  2. B2 prod execution
  3. Bitemporal schema upgrade (valid-time × transaction-time)
  4. `/api/v1/reasoning-chain` explainability API
  5. TaxBench eval harness + first run
  6. 1 paid pilot customer (3-month, unlocks real query distribution)
- **4 Should-Have** (authority PageRank, GraphRAG, ER, multi-jurisdiction depth), **4 Could-Have** (OWL, multilingual, confidence edges, OSS release), **3 Won't** (金税四期直连, self-hosted OWL reasoner, global scope)
- The 11 Should/Could items only compound **after** the 6 Musts ship — without real queries from a pilot, every improvement is based on internal assumptions.

## Session 69 finishing touches (part 13, 2026-04-20)

- **Dev utility `scripts/bootstrap_canonical_schema.py`** — apply v4.2 canonical schema to a Kuzu DB:
  - Default: refuses to run if DB has any existing NODE/REL tables
  - `--force`: overlay on top of existing (IF NOT EXISTS guards make it idempotent)
  - `--dry-run`: parse + count statements without opening DB
  - `--schema PATH`: alternate schema file
  - Fresh DB → 35 NODE + 79 REL tables, 0 errors
- **5 integration tests** (`tests/test_bootstrap_schema.py`): dry-run counts, fresh-DB apply, refuses-nonempty, force-overlay, missing-schema exit 2
- **Full suite: 56/56 green** (31 auditor + 4 Phase 0 + 6 Phase 1d + 10 CLI + 5 bootstrap)
- Bootstrap utility is the first "dev quality-of-life" artifact — lets anyone recreate the canonical schema on demand (useful for tests, post-destructive-experiment reset, clean bench for new pilot).

## Session 69 finishing touches (part 14, 2026-04-20) — SOTA Must #4 v0

- **Reasoning-chain library** (`src/reasoning/chain.py`) — first cut toward `/api/v1/reasoning-chain`:
  - `build_reasoning_chain(conn, node_id, include_2hop=True)` walks the graph and returns a structured justification DAG
  - Resolves root node across all NODE tables by id; extracts label from `name`/`title`/`id` in priority order
  - Iterates all REL tables; queries each in both directions (`out` = node is FROM, `in` = node is TO); extracts v4.2 edge attrs `sourceClauseId`/`effectiveAt`/`supersededAt` when present
  - 2-hop expansion: caps first 10 direct targets to avoid fanout explosion; deduplicates via `(type, id)` set; each 2-hop edge records `via` metadata showing the 1-hop it came through
  - Pure read, never raises on missing node (returns `trace.node_resolved = False`)
- **8 integration tests** (`tests/test_reasoning_chain.py`) — minimal 4-node/3-edge seeded graph (LegalDocument → TaxIncentive → TaxEntity + LegalClause):
  - Root resolution + label extraction
  - Direct evidence in both directions (3 edges: 1 inbound + 2 outbound)
  - Edge attribute extraction (sourceClauseId / effectiveAt / supersededAt)
  - 2-hop expansion reaches Entity + Clause with `via` trace
  - 2-hop disabled flag
  - Missing node → unresolved trace
  - Isolated node → empty evidence
  - Query-count monotonicity (2-hop > 1-hop)
- **Full suite: 64/64 green** (31 auditor + 4 Phase 0 + 6 Phase 1d + 10 CLI + 5 bootstrap + 8 reasoning-chain)
- Next: wire `build_reasoning_chain()` into `kg-api-server.py` as `GET /api/v1/reasoning-chain?node_id=...` (simple 8-line handler + Dockerfile `COPY src/reasoning/` line). Deployment to prod is still HITL (service restart).

## Session 69 finishing touches (part 15, 2026-04-20) — Must #4 API wiring

- **`GET /api/v1/reasoning-chain` endpoint** added to `kg-api-server.py` (~15-line handler after `ontology-audit`):
  - Query params: `node_id` (required) + `include_2hop` (default true)
  - Imports `build_reasoning_chain` from the tested `src/reasoning/chain.py` library; no additional logic in the handler
- **Dockerfile updated**: `COPY src/reasoning/ ./src/reasoning/` added alongside existing `src/audit/` copy
- **Validated against real demo DB** (port 8400, API key auth, `KG_API_KEY=test`):
  - Query `INCE_VAT_SMALL_EXEMPT` → resolved as `TaxIncentive: 小规模纳税人月销售额10万以下免征增值税`
  - 1 direct edge (`[out] -FT_INCENTIVE_TAX-> TT_VAT`) — the incentive is scoped to VAT
  - 22 2-hop ripples (LawOrRegulation enforcement cases, TaxEntity scopes, OP_SubAccount mappings)
  - Trace: 79 REL types scanned, 239 queries run, ~300ms total
- **64/64 tests still green** — library code unchanged, only handler added
- Deployment path to prod: (1) `rsync -a src/reasoning/ kg-api-server.py Dockerfile contabo:/home/kg/cognebula-enterprise/` (2) `systemctl restart kg-api.service` — both HITL per existing rule
- Must #4 status: **v1 complete locally** (library + endpoint + real-data validation). Activation on prod = HITL gate.

## Session 69 finishing touches (part 16, 2026-04-20) — Must #4 HTTP contract lock-in

- **`tests/test_reasoning_chain_api.py`** added (6 tests, ~180 lines) — spawns a real uvicorn subprocess pointed at a seeded tmp Kuzu DB and exercises the endpoint over HTTP. Locks in the wire contract before prod deployment.
- Coverage: known-node resolution, direct-evidence shape + provenance fields, 2-hop default-on, missing-node → 200 with `trace.node_resolved=false`, missing required param → 422, `include_2hop=false` short-circuit verified via query-count monotonicity
- Module-scoped fixture: one server process per module run (~2.4s total); free-port picker avoids port collision with running prod demo on 8400
- `KG_API_KEY=""` in subprocess env disables auth middleware so tests stay self-contained (still exercises the full middleware stack)
- **70/70 tests green** (was 64 before this part): 31 auditor + 4 Phase 0 + 6 Phase 1d + 10 CLI + 5 bootstrap + 8 reasoning library + **6 reasoning API**
- Must #4 status: **v1 locked** — library unit tested + HTTP contract tested + real-data validated. Safe to `rsync + systemctl restart` on user's B-signal.

## Session 69 finishing touches (part 17, 2026-04-20) — SOTA Must #5 v0 (TaxBench harness)

- **`src/eval/taxbench.py`** (~180 lines, new module) — evaluation harness skeleton, pure Python, zero network, zero LLM:
  - `Question` / `EvalResult` dataclasses
  - `load_questions(conn, node_type="OP_StandardCase", case_type="cpa_exam_question", limit=None)` — pluggable loader; `node_type` is a parameter because OP_StandardCase is a legacy rogue bucket (not canonical v4.2) that Phase 4 may rename
  - Metadata parser extracts `year:` / `subject:` / `type:` tokens from the freeform `notes` field for per-slice analysis later
  - Three reference scorers: `score_exact` (whitespace-normalized equality), `score_contains` (substring), `score_keyword_overlap` (Jaccard over Chinese char + ASCII word tokens — `_TOKEN_RE = [\u4e00-\u9fff]|[A-Za-z0-9]+`)
  - `run_eval(questions, predictor, scorer)` + `aggregate(results)` — predictor is caller-supplied so the harness stays decoupled from any specific LLM / retrieval strategy
- **`tests/test_taxbench.py`** (17 tests) — seeds a tmp Kuzu DB with 2 CPA + 1 non-CPA rows; covers: loader filter, limit, disabled filter, metadata parsing, populated prompt/expected, missing-node-type resilience; exact/contains/overlap scorer edge cases; run_eval shape, dumb predictor, aggregate math, empty aggregate, end-to-end perfect + end-to-end overlap
- **87/87 tests green** (was 70 before this part): previous 70 + 17 new taxbench tests
- v0 design rationale: predictor is a `Callable[[Question], str]`, so v1 can plug in (a) raw LLM, (b) reasoning-chain-assisted LLM (via `/api/v1/reasoning-chain`), (c) retrieval-augmented LLM — all without changing harness code. Scorer protocol stays the same; we'll add LLM-judge scorer alongside the three reference scorers when the first real predictor lands.
- Must #5 status: **v0 locked locally** — harness contract + 3 scorers + runner. Next gate (v1, HITL): wire a real predictor against demo DB, run on ≤100 questions, publish leaderboard row.

## Session 69 finishing touches (part 18, 2026-04-20) — Must #5 v0.5 (CLI + baseline predictors)

- **`src/eval/predictors.py`** (new, ~60 lines) — 2 non-LLM predictor strategies implementing the `Callable[[Question], str]` contract:
  - `echo_prompt` — returns `q.prompt` verbatim; baseline floor for keyword-overlap scorer
  - `reasoning_chain_predictor(conn, include_2hop=False)` — closure that calls `build_reasoning_chain` and concatenates target labels as the prediction. Pure-graph baseline: measures whether the CPA question node's out-edges surface tokens that overlap with the gold answer, with zero LLM involvement. Establishes a signal-vs-noise floor before any model lands.
- **`scripts/run_taxbench.py`** (new, ~130 lines) — first-class CLI:
  - Args: `--db`, `--node-type` (default `OP_StandardCase`), `--case-type` (default `cpa_exam_question`; pass empty string to disable filter), `--limit`, `--predictor` {echo, expected, reasoning_chain}, `--scorer` {exact, contains, keyword_overlap}, `--include-2hop`, `--output`, `--per-question`
  - Emits leaderboard-shaped JSON on stdout: `{run: {...run config...}, summary: {count, mean, pass_rate, scorer}, results?: [...]}`
  - Exit codes: 0 success / 2 argparse or missing DB / 1 runtime
  - `--output` writes the same JSON to disk at an arbitrary path (default folder convention: `outputs/taxbench/YYYY-MM-DD-<slug>.json`)
- **Tests** (11 new, all green):
  - `tests/test_taxbench_predictors.py` (4): echo shape, reasoning_chain over a linked question surfaces both TaxType and AccountingStandard labels, unknown-node returns empty string, isolated-node returns empty string
  - `tests/test_run_taxbench_cli.py` (7): default echo+overlap run, oracle `--predictor expected` + `--scorer exact` passes 100%, `--limit` respected, `--per-question` includes results, `--output` writes file, missing-DB exits 2, `--case-type ""` disables filter
- **98/98 tests green** (was 87 before this part): previous 87 + 4 predictor tests + 7 CLI tests
- Local demo DB at `data/finance-tax-graph/` is empty (real data only on prod), so the first real leaderboard row is HITL-gated on `ssh contabo` access. The CLI is proven on tmp DBs and ready to run with `--db /home/kg/cognebula-enterprise/data/finance-tax-graph --output outputs/taxbench/2026-04-20-baseline.json --predictor reasoning_chain --limit 100`.
- Must #5 status: **v0.5 locked** — CLI + baseline predictors + 11 tests. First real-data row = single-command HITL execution on prod.

## Session 69 finishing touches (part 19, 2026-04-20) — Must #5 v0.6 (per-slice breakdown)

- **`aggregate_by(results, metadata_key, unknown_label="unknown")`** added to `src/eval/taxbench.py` — groups EvalResults by `metadata[key]`, returns `{group: aggregate, ..., "__all__": overall_aggregate}`. Missing-key rows bucket as `"unknown"` so no row is silently dropped (a visible 3@0.0 bucket is more actionable than an invisibly-depressed global mean).
- **`EvalResult.metadata`** new field (defaults to `{}`); `run_eval` now copies `q.metadata` onto each result so slicing doesn't need a re-join against the loader.
- **CLI `--group-by KEY` (repeatable)** added to `scripts/run_taxbench.py`:
  - `report["breakdown"][key] = aggregate_by(results, key)` for each `--group-by` flag
  - `--per-question` output now also includes `metadata` for full traceability
  - Example: `--group-by year --group-by subject --group-by type` gives 3 breakdowns in one run
- **Tests** (6 new): `test_run_eval_carries_metadata` + 3 `aggregate_by` tests in `tests/test_taxbench.py`; 2 `--group-by` CLI tests in `tests/test_run_taxbench_cli.py`. Also updated `test_cli_per_question_includes_results` for new `metadata` field.
- **104/104 tests green** (was 98 before this part)
- Strategic rationale: the first real CPA-exam run would return one opaque 0.37 mean without slices. With `--group-by subject`, it returns `tax_law: 0.58, accounting: 0.21, audit: 0.15` → a clear diagnosis of where the graph needs richer edges. This is the same pattern as the CI ratchet (per-bucket rogue counts) — overall numbers hide; slices force action.
- Must #5 status: **v0.6 locked** — per-slice breakdown wired from dataclass → aggregator → CLI with full test coverage. Ready for first real-data HITL run.

## Session 69 finishing touches (part 20, 2026-04-20) — Must #5 v0.7 (leaderboard index)

- **`scripts/taxbench_leaderboard.py`** (new, ~130 lines) — scans a directory of `run_taxbench.py` JSON outputs and emits a markdown comparison table:
  - **Overall section**: one row per run (file, predictor, scorer, count, mean, pass_rate, timestamp) sorted by mean desc
  - **Breakdown section(s)**: one per `--breakdown-key`, unions all slice labels across runs (with `__all__` first), cells show `mean (n=count)`
  - Ignores non-run JSON gracefully: a file missing `run`/`summary` keys is skipped silently; malformed JSON is skipped; empty dir yields a "_(no runs found)_" placeholder
  - `--output PATH` also writes the markdown to disk
- **Tests** (8 new): empty dir, missing dir (exit 2), sort order, non-run JSON ignored, single `--breakdown-key`, missing-key note, `--output` file write, multiple `--breakdown-key` flags
- **112/112 tests green** (was 104 before this part)
- **Smoke-verified live**: two hand-crafted runs (echo + reasoning_chain) rendered a side-by-side table:
  ```
  | run       | predictor        | ... | mean  |
  | b.json    | reasoning_chain  | ... | 0.410 |
  | a.json    | echo             | ... | 0.120 |

  subject: tax_law 0.180 → 0.580 ; accounting 0.060 → 0.240
  ```
  This is exactly the output shape a paper-style leaderboard needs: drop 3-4 run JSONs into one folder, one command, publishable markdown.
- Must #5 status: **v0.7 locked** — complete eval loop (loader → scorer → runner → CLI → per-slice → leaderboard index). All 4 layers test-covered. Only remaining v1 gate is wiring an actual LLM predictor + running on prod demo DB (HITL).
- Remaining SOTA Must gaps (unchanged): Must #3 bitemporal design doc (local, not yet drafted); Must #6 pilot customer (non-engineering)

## Session 69 finishing touches (part 21, 2026-04-20) — SOTA Must #3 design doc (2份制)

- **`doc/00_project/initiative_cognebula_sota/BITEMPORAL_SCHEMA_DESIGN.md`** (English, canonical) — v4.3 proposal, 11 sections:
  1. Problem: 3 unanswerable questions today (audit reproducibility / retroactive law correction / reasoning-chain evidence completeness)
  2. Non-goals: not a correctness rewrite / not a perf project / not UI / not in-place prod migration
  3. Current state: 79 REL × {sourceClauseId, effectiveAt, supersededAt} — one time axis only
  4. Proposed edge shape: add `recordedAt` (required) + `retractedAt` (nullable); half-open `[start, end)` intervals; textbook bitemporal rectangle semantics
  5. Scope: 79 RELs × 2 new attrs via `ALTER TABLE ... ADD` (Kuzu/Vela 0.12 supports it); single backfill pass
  6. Migration B6A–B6E (B6A–B6D all zero-HITL; B6E = same trigger word class as existing B0/B2/B3)
  7. Reasoning-chain wire-format impact: 2 new optional string fields per edge dict; HTTP contract test grows 2 assertions; back-compat preserved
  8. Query patterns unlocked: as-of-valid, as-of-transaction, bitemporal point, rectangle
  9. Risks: storage (<150 MB incremental on 110 GB DB), loader drift (auditor gates), interval semantics (hard-code half-open), client-loader race (ship together)
  10. Acceptance criteria: 6-item checklist including conformance auditor invariants + HTTP contract test updates
  11. Unlocks: SOTA parity with ONESOURCE/CCH/Bloomberg Tax
- **`doc/00_project/initiative_cognebula_sota/BITEMPORAL_SCHEMA_DESIGN.html`** (Chinese, human-facing) — same 11 sections, Claude Warm Academic style (cream #FAF7F2 / ink #1F1A16 / terracotta accent #BF4D1E / Source Serif body / Inter headings / JetBrains Mono code). Auto-opened in Preview.
- 2份制 rule honored: English `.md` as canonical source for AI agents + Chinese `.html` as styled human-facing companion
- Implementation path (zero-HITL, all five next slots):
  - B6A author v4.3 DDL + diff: ~80 lines Python transformation of v4.2
  - B6B extend `bootstrap_canonical_schema.py`: accept `--schema v4.2|v4.3`
  - B6C staging backfill script: `scripts/migrate_v43_backfill.py`
  - B6D auditor extension: `recordedAt IS NOT NULL` + `recordedAt ≤ retractedAt` check
  - B6E prod cutover: user trigger word "B6"
- **112/112 tests still green** (design doc doesn't touch code)
- Must #3 status: **design locked**. Implementation on user signal.

## Session 69 finishing touches (part 22, 2026-04-20) — Scope refocus + reasoning-chain wired to `/expert/kg/`

**Scope refocus** (user direction): project is internal-only now. Paused paid-module development (`/workbench/*`, `/clients/*`, `/reports/*` and the blocked System-B backend endpoints). Focus is **KG query page + expert workbench** (`/expert/*`). Must #6 (paid pilot) deferred indefinitely; non-paid surface area is the product.

**Frontend delta this part**:
- `web/src/app/lib/kg-api.ts` — added `ReasoningEdge` + `ReasoningChain` types + `getReasoningChain(nodeId, include2Hop=true)` fetcher wired to `/api/v1/reasoning-chain`
- `web/src/app/components/ReasoningChainPanel.tsx` (new, ~110 lines) — on-demand panel component:
  - Mounts per selected node; calls `getReasoningChain`
  - Renders direct-evidence edge rows with v4.2 provenance (`source_clause_id` / `effective_at` / `superseded_at`)
  - Toggle checkbox "含 2-hop 扩散" flips `include2Hop` (re-fires fetch via useEffect dep); 2-hop rows shown with `经由 X (EDGE)` breadcrumb + 0.85 opacity to distinguish
  - Node labels are click-navigable (calls parent `handleNodeSelect`); uses existing `EDGE_LABELS_ZH` + `EDGE_COLORS` theme maps
  - Trace footer: `扫描 N REL · M 次查询`
- `web/src/app/expert/kg/page.tsx` — 2-line wiring: dynamic import of the panel + insertion between existing "关联" neighbors list and "以此节点为中心展开" button
- **Build verified**: `npx tsc --noEmit` clean; `npm run build` with `NEXT_DISABLE_FONT_DOWNLOADS=1` (Google Fonts offline locally) compiles in 4.0s, `/expert/kg` prerendered as static content. Production build on contabo will pull fonts normally.
- **Backend 112/112 tests still green** (no backend code touched)
- Deployment path: `rsync web/out/ contabo:/home/kg/cognebula-web/` (Session 68 established), takes ~30s. HITL-gated.
- First expert-visible capability upgrade since Session 68 — every selected node in `/expert/kg/` now shows its structured justification chain, not just a flat neighbor list.

## Session 69 finishing touches (part 23, 2026-04-20) — "继续全部完成": semantic search + security staging

**A. Semantic search wired to `/expert/kg/`**:
- `kg-api.ts` — added `HybridSearchHit` / `HybridSearchResponse` types + `hybridSearch(q, limit, {expand, tableFilter})` client; backs onto existing `/api/v1/hybrid-search` (RRF fusion of Cypher text + LanceDB vector)
- `/expert/kg/page.tsx` — added `searchMode: "exact" | "hybrid"` state + segmented-control toggle 精确/语义 next to the search button (title hint: "精确 = Cypher 名称匹配；语义 = LanceDB 向量 + 文本 RRF 融合")
- `handleSearch` branches on mode: exact path unchanged, hybrid path calls `hybridSearch(q, 10, {expand: false})` and reuses the same first-hit selection UX
- Type reconciliation: first-hit accessor cast via `unknown → Record<string, string | undefined>` because `KGSearchResult` and `HybridSearchHit` share some keys (id, table, title, name, text) but differ on optional fallback keys (`node_id`, `source_table`)

**B. Security hardening staged (no prod touch)**:
- `deploy/contabo/nginx-cognebula.conf` — added `set $kg_api_key ""` (empty default, safe) + `proxy_set_header X-API-Key $kg_api_key` on the `/api/v1/` location. Operator sets the real value via a mode-640 `/etc/nginx/conf.d/cognebula-apikey.conf` snippet (kept out of the main config so the secret doesn't enter git)
- `deploy/contabo/systemd/kg-api.service.d/override.conf` (new) — drop-in overriding ExecStart to `--host 127.0.0.1` + `Environment=KG_API_KEY=CHANGE_ME_LONG_RANDOM`. Comments document the install + verify + rollback sequence inline
- `deploy/contabo/SECURITY_HARDENING_RUNBOOK.md` (new) — single-command cutover: pick secret with `openssl rand -hex 32`, push to both nginx snippet + systemd override, `systemctl daemon-reload && restart kg-api && reload nginx`. Verification asserts: (1) `http://127.0.0.1/api/v1/health` 200 via nginx, (2) `http://167.86.74.172:8400/api/v1/health` must fail with connection refused, (3) direct `127.0.0.1:8400` without header returns 401, with header returns 200
- HITL trigger word: `执行 SH`
- Known follow-ups listed in runbook (not blocking): `/expert/*` IP allowlist, HTTPS/Certbot, UFW enable

**C. Sidebar pause visibility**: client-system sidebar (Sidebar.tsx) untouched this session — deleting nav items would be destructive in a reversible-focused refactor. The `/expert/` layout already excludes paid modules; navigating to `/expert/*` directly is the focus path for internal operators.

**Verification**:
- `npx tsc --noEmit` clean
- `npm run build` compiles in 5.0s; `/expert/kg` still prerendered
- Backend `pytest tests/ -q` 112/112 green

**Deploy path (HITL-gated)**: one rsync for frontend (`web/out/ → contabo:/home/kg/cognebula-web/`), one security cutover (`执行 SH` trigger).

All three engineering SOTA Musts now at a clean stopping point:
- **#3 bitemporal**: design locked, implementation path traced (B6A–B6E)
- **#4 reasoning-chain**: library + API + HTTP contract tests + frontend panel — end-to-end complete, prod activation pending rsync
- **#5 TaxBench**: full eval loop (library + CLI + per-slice + leaderboard index) + 61 tests — first real-data row pending single HITL command

## Session 69 finishing touches (part 24, 2026-04-20) — Search endpoint coverage lock-in

Backend coverage gap: part 23 wired `/api/v1/search` (精确 mode) and `/api/v1/hybrid-search` (语义 mode) to the frontend, but neither had HTTP contract tests. Plugging that gap now.

- **`tests/test_search_api.py`** (new, 9 tests) — uvicorn subprocess + tmp Kuzu DB seeded with 3 `TaxType` rows (增值税 / 企业所得税 / 个人所得税). Both endpoints degrade gracefully without `GEMINI_API_KEY` + LanceDB; tests force the text-only path by passing `GEMINI_API_KEY=""` + `LANCE_PATH=<non-existent>`.
- Coverage:
  - `/api/v1/search`: returns matching rows, result shape (`id`/`text`/`table`/`title`/`name`/`score`), no-match empty list, `--limit` honored, missing `q` → 422
  - `/api/v1/hybrid-search`: text-only path (`vector_hits == 0`), every hit has `rrf_score > 0`, missing `q` → 422, `--limit` honored
- Verification: module-scoped fixture spins one server per module (~1.7s total)
- **121/121 tests green** (was 112 before this part): 31 auditor + 4 Phase 0 + 6 Phase 1d + 10 CLI + 5 bootstrap + 8 reasoning lib + 6 reasoning HTTP + **9 search HTTP (new)** + 17 taxbench + 4 taxbench predictors + 7 taxbench CLI + 6 taxbench aggregate_by + 8 taxbench leaderboard

Every HTTP endpoint the frontend now calls (`/api/v1/search`, `/api/v1/hybrid-search`, `/api/v1/reasoning-chain`, `/api/v1/health`) has contract tests. Safe to deploy frontend + backend changes as one rsync + restart batch.

## Session 69 finishing touches (part 25, 2026-04-20) — Rename "工程观察" → "工程进度报告" + promote to reusable template

User direction: rename the section name in the existing progress report AND make it a template for future issues.

**Rename**:
- `doc/PROGRESS_REPORT_2026-04-20.html` — 3 occurrences of "工程观察" → "工程进度报告" (title, brand masthead, footer)

**New reusable template** under `doc/templates/`:
- `PROGRESS_REPORT.template.md` — English canonical skeleton with `{{TOKEN}}` placeholders covering identity, window, volume, headline, streams, commit mix, activity chart, deletions, churn, observations (5), risks (4), recommendations (3), footer source-note
- `PROGRESS_REPORT.template.html` — Victorian-broadsheet-styled Chinese skeleton. Identity (title / masthead / kicker / footer) + headline (lede + standfirst + 6 metric tiles) are tokenized; chart bodies (heatmap / commit-mix / velocity SVG) keep intact class structure and have in-place data that author swaps per-issue (not single-token because chart data is multi-dimensional)
- `README.md` — workflow + full token reference table grouped by scope (Identity / Window / Volume / Headline / Streams / Commit mix / Activity / Deletions / Churn / Observations / Risks / Recommendations / Footer) + "enforced vs left open" contract

Template discipline (written into README.md):
- Enforced: Victorian-broadsheet style, section order, 2份制 pair, `.md` English / `.html` Chinese language policy, footer line shape
- Open per-issue: stream count (default 3), risk/rec counts (default 4/3), chart numbers, lede + standfirst prose

Workflow is one shell block: `cp template → doc/PROGRESS_REPORT_$DATE.{md,html}` then search-replace tokens + swap chart cells.

**121/121 tests still green** (docs-only change, no code touched).

From now on: every project progress report follows this template. Prior ad-hoc style retired; issue counter is monotonic.

Migration suite now complete in `deploy/contabo/migrations/`:
- `phase0_drop_empty_tables.cypher` (review-only; real execution via `scripts/migrate_phase0_drop_empty.py`)
- `phase1_v1_v2_rename.cypher`
- `phase2_duplicate_cluster_collapse.cypher` (staged, per-cluster contract required before execute)
- `phase4_legacy_folding.cypher` (staged)
- `MIGRATION_RUNBOOK.md` — consolidated ops runbook with exact ssh/systemd commands, trigger phrases (B0/B2/B3/B4A-D/B5), per-phase rollback, threshold-tightening schedule (CI `max-rogue` ratchet 70→0), emergency procedures
- Phase 3 (SaaS eviction) deferred: needs System B backend endpoints first (`/api/v1/workbench/*`, `/api/v1/clients/*`, `/api/v1/reports/*`) as the eviction destination

---

## Session 26 — 2026-04-20 — `SH2` · domain + TLS cutover on `hegui.org`

User directive: "放到hegui.org" + "继续". Pause payment module, focus on KG query + expert workbench deployment hygiene.

**Outcome**: both subdomains live on HTTPS with Let's Encrypt certs; xray Trojan VPN preserved via sslh SNI demux.

Final topology on contabo (167.86.74.172):

```
public :443 ──► sslh 0.0.0.0:443 (SNI routing)
                 ├─► SNI ∈ {app.hegui.org, ops.hegui.org} → nginx 127.0.0.1:8443  (LE certs)
                 └─► any other SNI                         → xray 127.0.0.1:8444  (Trojan VPN)
public :80  ──► nginx 0.0.0.0:80 → 301 https
```

**URLs**:
- `https://app.hegui.org/` — client-facing (灵阙 workbench, `/`, `/workbench/*`, `/clients/*`). `/expert/*` returns 404 here (path-level isolation, same bundle)
- `https://ops.hegui.org/` — internal (CogNebula expert console, `/expert/*`). Basic Auth `maurice` / password in 1Password. `/workbench/*` and `/clients/*` return 404

**Let's Encrypt**: two separate certs issued via `certbot --webroot -w /var/www/certbot`. Issuer `C=US, O=Let's Encrypt, CN=E7`. Expires 2026-07-19. `certbot.timer` active; `certbot renew --dry-run` passes for both.

**xray conflict resolution**: xray had been bound to `0.0.0.0:443` (Trojan) since 2026-03-24. Moved to `127.0.0.1:8444`, installed `sslh-fork 1.22c-1` at `/etc/sslh/sslh.cfg` with SNI routing. Trojan clients unchanged (still connect to `:443`, sslh dispatches by SNI). xray config backup at `/usr/local/etc/xray/config.json.bak-pre-sslh.1776679755`.

**nginx hardening**: `absolute_redirect off; port_in_redirect off;` in both HTTPS blocks (prevents nginx from inflating redirects with internal port `8443`). API paths (`/api/v1/`, `/api/v1/health`) have `auth_basic off;` on ops — they have their own X-API-Key layer.

**Files added / modified**:
- `deploy/contabo/nginx-cognebula.conf` — 3 server blocks (HTTP redirect + app HTTPS + ops HTTPS); listeners bound to `127.0.0.1:8443`
- `deploy/contabo/sslh.cfg` — SNI demux config (synced from live server)
- `deploy/contabo/nginx-cognebula-staging.conf` — HTTP-only intermediate used during certbot issuance; removed from contabo after cutover
- `deploy/contabo/nginx-cognebula.conf.s0-iponly` — rollback baseline pulled from the live pre-cutover config
- `deploy/contabo/DOMAIN_TLS_RUNBOOK.md` — 9-step cutover + rollback + trigger words
- `doc/templates/screenshot-report.sh` — headless Chrome + PIL trim helper for tight-fit progress-report PNGs (viewport matches body outer box, PAD=48 CSS-px breathing room, DPR auto-scaled)
- `doc/templates/README.md` — added "Capturing screenshots" section

**PROXY protocol attempted, rolled back**: added `proxyprotocol: 2` to sslh.cfg + `proxy_protocol` / `set_real_ip_from` / `real_ip_header` to nginx. `sslh 1.22c-1` silently ignored the config key (`Unknown settings: /protocols[0]/proxyprotocol:2` in journal), forwarded raw TLS bytes, nginx emitted `broken header` and all HTTPS requests got SSL_ERROR_SYSCALL. Rolled back within ~30s. Access log now shows source IP `127.0.0.1` for all HTTPS requests. Upgrade path: replace sslh with HAProxy for SNI routing (native `send-proxy-v2` support). Deferred.

**Known nits** (not blockers):
- `https://ops.hegui.org/` without auth returns 302 to `/expert/` rather than 401, because nginx rewrite phase precedes access phase. User follows 302 to `/expert/` which correctly prompts auth. No credential leakage
- Client IP unobservable in nginx access log until HAProxy replacement

**`B0` executed 2026-04-20 18:55 CEST** — `rsync -az --delete web/out/ contabo:/home/kg/cognebula-web/` pushed 377/420 files (4.9 MB, 19× speedup). `chown -R www-data:www-data` + `chmod -R o+rX` reapplied. Verified features live: `/expert/kg/` page HTML contains Chinese label `精确` (search-mode toggle); JS chunks contain `getReasoningChain`, `hybridSearch`, `reasoning-chain`. Both `https://app.hegui.org/` and `https://ops.hegui.org/expert/kg/` opened in browser for manual eye-check.

**Scheduled follow-ups** (logged, not asking):
- Replace sslh with HAProxy for SNI demux + PROXY v2 (recovers real client IP)
- Cloudflare Access over ops.hegui.org to retire Basic Auth — gated on CF Zone provisioning
- UFW enable `22,80,443/tcp` with SSH allow-first — manual, SSH self-lock risk
- Git commit `deploy/contabo/` + `doc/templates/` deltas — user has not authorized commit of sessions 54-67 yet either, keep pending

**Verification evidence** (all 2026-04-20):
- `openssl s_client -connect app.hegui.org:443` → `issuer=C=US, O=Let's Encrypt, CN=E7`
- `curl https://app.hegui.org/` → 200. `curl https://app.hegui.org/expert/` → 404
- `curl -u maurice:PASS -L https://ops.hegui.org/expert/` → 200
- `openssl s_client -connect 167.86.74.172:443 -servername vpn-test.example` → `subject=CN=eu-proxy.cloudcc.io` (xray path intact)
- `certbot renew --dry-run` → "all simulated renewals succeeded" for both certs

---

Maurice | maurice_wen@proton.me
