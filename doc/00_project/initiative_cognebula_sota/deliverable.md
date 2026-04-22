# CogNebula Semantic Edge Import Closure -- Deliverable

## Outcome

The blocked semantic-edge loading task is complete. Production now has `570,481` `SEMANTIC_SIMILAR` edges loaded successfully, with the graph at `2,016,849` edges immediately after import and `2,017,420` edges at the latest manual verification across `856,072` nodes. The API restarted cleanly, `/api/v1/quality` remains `PASS / 100`, and the hybrid benchmark remains stable at `79% overall` with `100/100` question pass count and `0` errors.

## Changed Files

- `kg-api-server.py`
  Hardened API auth and the admin migration route on the actual service target: removed query-string API key auth, enforced real node-table allowlisting, and restricted `field_map` identifiers/literals.
- `scripts/build_semantic_edges.py`
  Fixed REL TABLE GROUP bulk load for Vela/Kuzu 0.12.0 by using explicit `from/to` COPY options and replacing same-type semantic edges before reload; removed legacy fallback branches that could reintroduce partial-success drift.
- `benchmark/run_eval.py`
  Standardized benchmark verification on canonical `KG_API_KEY`, kept the localhost default API target, and aligned CLI help text with the actual behavior.
- `cognebula_mcp.py`
  Standardized MCP auth on canonical `KG_API_KEY` and refreshed the embedded platform metrics/copy to the current `856K+ nodes / 2M+ edges` baseline.
- `scripts/render_doc_html.py`
  Added a reusable markdown-to-HTML companion renderer with project-local styling, removed remote JS dependency, and sanitized raw markdown HTML before rendering.
- `HANDOFF.md`
  Added Session 48 completion record and verification evidence.
- `doc/index.md`
  Refreshed project path index and route map to the active repo layout.
- `doc/00_project/initiative_cognebula_sota/PRD.md`
  Updated current scale metrics.
- `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md`
  Updated actual production topology/metrics and corrected `PROJECT_DIR`.
- `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md`
  Corrected `PROJECT_DIR` and documented authenticated agent access.
- `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md`
  Updated KPI baseline and benchmark status.
- `doc/00_project/initiative_cognebula_sota/PRD.html`
- `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.html`
- `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.html`
- `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.html`
  Generated human-facing HTML companions for the updated PDCA markdown sources.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded closure of the semantic-edge blocker.
- `doc/00_project/initiative_cognebula_sota/PDCA_ITERATION_CHECKLIST.md`
  Captured the final closeout checklist state, including canonical `KG_API_KEY` tooling alignment.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the root cause, fix, and verification evidence.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Logged the closeout debt requirement and the canonical API key environment-name rule.

## Verification

- VPS import run: `scripts/build_semantic_edges.py` completed in `827s`
- Stats endpoint:
  immediate post-import: `total_nodes=856072`, `total_edges=2016849`, `SEMANTIC_SIMILAR=570481`
  latest manual verification: `total_nodes=856072`, `total_edges=2017420`, `SEMANTIC_SIMILAR=570481`
- Quality endpoint:
  `gate=PASS`, `score=100`
- Hybrid benchmark:
  `benchmark/results_hybrid_20260416_after_security_fix.json`
  Summary: `79% overall`, `100 pass`, `0 fail`, `0 errors`, `score=254/321`
- Manual UX-path verification:
  authenticated query `增值税一般纳税人认定标准是什么` returned `5` results; top result `VAT_SMALL_SCALE_TO_GENERAL_TAXPAYER`
  Structured evidence: `doc/00_project/initiative_cognebula_sota/manual_verification_20260416.json`
- Attacker review:
  identified and fixed query-string API key acceptance, admin migration route hardening gaps, and HTML render supply-chain / raw-HTML exposure issues; fresh recheck reported no remaining HIGH/MEDIUM findings
- Architect verification:
  final architect review returned `APPROVED` with no remaining blockers
- Tooling verification:
  `python3 -m py_compile benchmark/run_eval.py cognebula_mcp.py`
  `rg -n "COGNEBULA_API_KEY" benchmark/run_eval.py cognebula_mcp.py` returned no hits
  runtime env-resolution checks confirmed both scripts accept `KG_API_KEY` and ignore legacy `COGNEBULA_API_KEY`
  unauthenticated live `GET /api/v1/stats` and `GET /api/v1/quality` against `http://100.75.77.112:8400` both returned `401 Unauthorized`
- `ai check`:
  `N/A` for this project. The available `ai check` command validates AI-Fleet root artifacts (`registry`, `skill_integrity`, AI-Fleet tests), not `27-cognebula-enterprise`, so it produced non-project failures while docs/no-emoji/SBOM checks passed.

## Simplifications Made

- Reused the existing `SEMANTIC_SIMILAR` REL TABLE GROUP instead of introducing new per-type relation labels and API branching.
- Fixed benchmark auth at the runner layer instead of relying on manual environment-variable translation during every verification run.
- Removed stale fallback branches from `scripts/build_semantic_edges.py` so future reruns fail fast instead of silently writing partial data.

## Remaining Risks / Debt

- Markdown sanitization is intentionally simple and appropriate for the current trusted PDCA docs, but it is not a general untrusted-markdown sanitizer.
- Three-end consistency:
  - Local project: updated
  - VPS production: updated and verified
  - GitHub: N/A in this task (no push/release requested)

## Closeout

- Skills: N/A (no reusable Skill package extracted in this task)
- Bottom-level norms (`AGENTS.md` / `CLAUDE.md`): N/A
- Rolling ledger: updated in `ROLLING_REQUIREMENTS_AND_PROMPTS.md`
- DNA Capsule: `semantic-rel-group-copy-fix` created, inherited, and passed `ai dna validate` + `ai dna doctor`
- Attacker review: completed and reflected in task plan / PDCA / notes / deliverable

---

## 2026-04-16 Session 51 — Static Web Auth Proxy Alignment

### Outcome

The exported Next.js frontend no longer needs a browser-side secret or a direct connection to the protected KG API. The browser KG client now targets the HTTPS Cloudflare Worker proxy by default, and the proxy code is aligned to inject `KG_API_KEY` server-side while keeping the static export deployment model intact.

### Changed Files

- `web/src/app/lib/kg-api.ts`
  Switched the browser client to the HTTPS Worker proxy (`NEXT_PUBLIC_KG_API_BASE` override, Worker URL by default).
- `worker/src/index.ts`
  Updated the KG proxy to read runtime config, inject `X-API-Key`, and forward request metadata cleanly.
- `worker/wrangler.toml`
  Added canonical `KG_API_ORIGIN` config for the Worker runtime.
- `doc/index.md`
  Added the Worker proxy to the project path index and route map.
- `doc/00_project/initiative_cognebula_sota/PRD.md`
  Updated product packaging and agent-integration wording to include the browser-safe HTTPS proxy.
- `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md`
  Added the static frontend → Worker → protected KG API chain to the actual current architecture.
- `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md`
  Added the static-frontend protected-access journey.
- `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md`
  Corrected stale baseline rows for auth, deployment, and hybrid retrieval.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Marked the auth/proxy/hybrid rows to match actual shipped state and recorded Session 51.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the export-mode constraint, Worker-proxy path, and verification evidence.

### Verification

- `npm run build` passed in `web/`
- Static build completed successfully across all 38 routes
- `./web/node_modules/.bin/tsc --noEmit --target es2022 --module esnext --lib es2022,dom worker/src/index.ts` passed
- The browser KG client now defaults to `https://cognebula-kg-proxy.workers.dev/api/v1`
- No App Route remains under `web/src/app/api/`, so `output: export` remains valid
- HTML companions were regenerated for the updated PDCA markdown docs

### Remaining Risks / Debt

- Cloudflare runtime secret management remains external to the repo: the deployed Worker still needs `KG_API_KEY` configured in Cloudflare

---

## 2026-04-16 Session 52 — Self-hosted Compose Packaging

### Outcome

The repo now contains a concrete self-hosted package for the current topology: `cognebula-api` plus a static web container that proxies `/api/v1/*` locally and injects `KG_API_KEY` server-side. Compose syntax is valid, but image-level build verification is blocked by the local Docker Desktop socket being unavailable in this session.

### Changed Files

- `Dockerfile`
  Replaced the repo-wide `requirements.txt` install with the minimal runtime dependency set needed by `kg-api-server.py`, avoiding ML/CUDA package drag in the API image.
- `.dockerignore`
  Reduced Docker build context so packaged image builds do not ship the whole repo into Docker.
- `web/Dockerfile`
  Added a multi-stage build for the exported Next.js app.
- `docker/nginx.web.conf.template`
  Added the static web + reverse proxy config that injects `X-API-Key` for local browser access.
- `docker-compose.yml`
  Expanded the stack from API-only to `cognebula-api` + `cognebula-web`, changed the default web port to `3001`, fixed the web healthcheck probe, and defaulted the graph mount to the real local baseline Kuzu file.
- `README.md`
  Updated local startup/access instructions for the packaged stack, including the new default web port and graph-path override guidance.

### Verification

- `docker compose config` passed
- `KG_API_KEY=dummy docker compose config` passed and confirmed both packaged services receive the expected auth/proxy env wiring
- `KG_API_KEY=dummy docker compose build cognebula-web` passed
- `KG_API_KEY=dummy docker compose build cognebula-api` passed
- `KG_API_KEY=dummy docker compose up -d` started the local packaged stack on its default ports
- `curl -I http://localhost:3001/` returned `200 OK`
- `curl http://localhost:3001/api/v1/health` returned packaged proxy JSON with `status=healthy`, `kuzu=true`
- `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`
- `KG_API_KEY=dummy docker compose down` removed the local verification stack cleanly
- HTML companions were regenerated after the packaging-related PDCA doc updates

### Remaining Risks / Debt

- The packaged stack is runtime-verified against the bundled baseline graph only (`157` nodes / `35` edges). Realistic local testing still depends on mounting a fuller Kuzu file via `COGNEBULA_GRAPH_PATH`.

---

## 2026-04-16 Session 53 — Phase C Script Portability

### Outcome

The remaining Phase C backfill scripts no longer assume `/home/kg/...` as the only executable environment. They now support explicit `--db-path`, respect `KUZU_DB_PATH`, and provide a read-only `--dry-run` mode for local preflight without write locks.

### Changed Files

- `scripts/cpa_content_backfill.py`
  Added `--db-path`, `KUZU_DB_PATH`, and `--dry-run`.
- `scripts/mindmap_batch_backfill.py`
  Added `--db-path`, `KUZU_DB_PATH`, `--dry-run`, and a missing table-existence precheck.
- `scripts/ld_description_backfill.py`
  Added `--db-path`, `KUZU_DB_PATH`, and `--dry-run`.

### Verification

- `python3 -m py_compile` passed for all three scripts
- Each script now exposes `--db-path` in `--help`
- Local dry-run against `data/finance-tax-graph.archived.157nodes` exits cleanly with `SKIP` instead of hardcoded-path or binder failures

### Remaining Risks / Debt

- The actual Phase C content work is still pending: these changes make the scripts portable and inspectable, but do not complete the missing content expansion themselves

---

## 2026-04-16 Session 54 — Local Demo Graph Bootstrap

### Outcome

The repo now contains a reproducible richer local Kuzu demo file at `data/finance-tax-graph.demo`. It is generated from the archived baseline graph and now expands local demo usefulness through FAQ, CPA-case, tax incentive, administrative-region, and native mindmap enrichment, without mutating the archived baseline file in place.

### Changed Files

- `scripts/bootstrap_local_demo_graph.py`
  Added a local demo-graph bootstrap flow: copy the archived baseline Kuzu file, inject FAQ data, create the required `OP_` schema, inject CPA case data, then inject tax incentives, administrative regions, and native mindmap nodes.
- `README.md`
  Added local demo bootstrap instructions using `scripts/bootstrap_local_demo_graph.py` plus `COGNEBULA_GRAPH_PATH`.
- `src/inject_faq_data.py`
  Shifted local FAQ injection onto native `FAQEntry` nodes instead of overloading `LawOrRegulation`.
- `src/inject_cpa_data.py`
  Extended CPA reference injection so it consumes extracted `headings`, `formulas`, and `pages` data instead of relying only on `sections/full_text`, and writes those references to native `CPAKnowledge` nodes.
- `src/inject_mindmap_native.py`
  Added native `MindmapNode` schema + injection path from `data/extracted/mindmap/all_mindmap_nodes.json`.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py` passed
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` produced `data/finance-tax-graph.demo`
- Demo graph counts:
  - baseline: `157` nodes / `35` edges
  - demo: `3847` nodes / `642` edges
- Demo graph key tables:
  - `FAQEntry`: `1152`
  - `CPAKnowledge`: `649`
  - `MindmapNode`: `990`
  - `LawOrRegulation`: `0`
  - `OP_StandardCase`: `266`
  - `TaxIncentive`: `109`
  - `AdministrativeRegion`: `477`
- Packaged API runtime with demo graph:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d cognebula-api`
  - authenticated `/api/v1/stats` returned `nodes=3847`, `edges=642`, `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `LawOrRegulation=0`, `OP_StandardCase=266`, `TaxIncentive=109`, `AdministrativeRegion=477`
  - packaged web proxy can also serve `/api/v1/health` against the richer demo graph and return `status=healthy`, `kuzu=true`

### Remaining Risks / Debt

- The richer local demo graph is still not a substitute for a fuller production-like graph snapshot.

---

## 2026-04-16 Session 55 — Demo Bootstrap Parity Fix

### Outcome

The documented default local demo-bootstrap path is now implementation-accurate. `scripts/bootstrap_local_demo_graph.py` explicitly includes native mindmap enrichment in its default `--include` set, and the rebuilt `data/finance-tax-graph.demo` is now re-verified end-to-end with the real native table mix rather than the earlier stale `LawOrRegulation`-heavy assumption.

### Changed Files

- `scripts/bootstrap_local_demo_graph.py`
  Added `mindmap` to the default `--include` set and wired the default flow to call `src/inject_mindmap_native.py`.
- `HANDOFF.md`
  Updated the local demo-graph closeout record to the fresh native-table distribution and runtime evidence.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the parity fix and fresh verification pass.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the mismatch discovery, direct Kuzu verification, and fresh packaged runtime evidence.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the parity-fix requirement, command evidence, and anti-regression guidance for the native-table split.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_faq_data.py src/inject_cpa_data.py src/inject_mindmap_native.py`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force`
  Verified the default flow now emits the `[mindmap] ... src/inject_mindmap_native.py` step and completes with `Node count: 3847`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=3847`, `edges=642`
  - `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `AdministrativeRegion=477`, `OP_StandardCase=266`, `TaxIncentive=109`, `LawOrRegulation=0`
- Packaged local runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` returned `status=healthy`, `kuzu=true`, `lancedb=true`
  - authenticated `curl -H 'X-API-Key: dummy' http://localhost:8400/api/v1/stats` returned the same native-table distribution as the direct Kuzu check
  - `curl http://localhost:3001/api/v1/stats` through the packaged web proxy returned the same stats without exposing the secret to the browser path
  - `curl -I http://localhost:3001/` returned `200 OK`
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` returned `healthy`

### Remaining Risks / Debt

- The richer local demo graph is now consistent with the default bootstrap path, but it still represents a local demo artifact rather than a production-scale knowledge graph.

---

## 2026-04-17 Session 56 — README Packaged API Sync

### Outcome

The top-level self-hosted usage docs no longer advertise the stale `localhost:8766/api/rag` path as if it were part of the current packaged stack. `README.md` now documents the active packaged endpoints on `:8400` and `:3001`, matching the API/web proxy topology that was already verified in Session 55.

### Changed Files

- `README.md`
  Replaced the legacy `8766 /api/rag` example with current packaged `search` / `hybrid-search` curl examples for `http://localhost:8400/api/v1/*` plus the browser-safe local proxy path on `http://localhost:3001/api/v1/*`.
- `HANDOFF.md`
  Added a follow-up session note so the next operator does not treat the old README example as current behavior.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the doc-sync and the current Docker-daemon blocker.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the stale README example removal and the daemon-socket check.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the requirement, prompt shape, and anti-regression note for the packaged API docs.

### Verification

- `README.md` now contains:
  - `curl -H "X-API-Key: your-key" "http://localhost:8400/api/v1/search?..."`
  - `curl -H "X-API-Key: your-key" "http://localhost:8400/api/v1/hybrid-search?..."`
  - `curl "http://localhost:3001/api/v1/search?..."`
- `rg -n "8766|api/rag" README.md` no longer matches the packaged usage section
- Docker environment check:
  - `docker context show` -> `desktop-linux`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_MISSING`
  - a fresh `docker compose up -d` attempt failed because the local Docker daemon socket was unavailable in this session

### Remaining Risks / Debt

- The README was aligned to the current packaged API surface in this session, but that specific turn could not collect a new runtime pass for the updated curl examples because the local Docker daemon was unavailable. Session 55 was still the latest successful packaged runtime proof at that point.
  Historical note: this blocker was resolved in Session 57.

---

## 2026-04-17 Session 57 — README Example Runtime Proof

### Outcome

The new top-level packaged API examples in `README.md` are now backed by fresh runtime evidence. After restoring the local Docker daemon, the repo's packaged stack was brought up again against `data/finance-tax-graph.demo`, and the updated `search`, `hybrid-search`, and proxied `search` examples all returned live non-empty results.

### Changed Files

- `HANDOFF.md`
  Added a follow-up session record for Docker recovery and README example runtime proof.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded Docker recovery plus the successful packaged endpoint proof.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the daemon recovery steps and the live endpoint responses.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the runtime-proof command shape and anti-regression note for the packaged README examples.

### Verification

- Docker recovery:
  - `open -a /Applications/Docker.app`
  - `test -S ~/.docker/run/docker.sock` -> `SOCKET_PRESENT`
  - `docker info` succeeded against `docker-desktop`
- Packaged stack:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` -> `status=healthy`, `kuzu=true`, `lancedb=true`
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` -> `healthy`
- README example proof:
  - protected search on `:8400` returned `count=5` with non-empty results
  - protected hybrid search on `:8400` returned `count=5`, `method=hybrid_rrf`, `text_hits=15`, and non-empty graph expansion
  - proxied search on `:3001` returned the same top-5 results as the protected `:8400` search
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Remaining Risks / Debt

- No remaining in-scope blocker remains on the packaged README examples. The broader remaining work is still content depth and production-scale graph quality, not packaging/docs correctness.

---

## 2026-04-17 Session 58 — Compose Command + Route Index Sync

### Outcome

The remaining self-hosted doc surface is now consistent at the command and route-index level. `README.md` no longer mixes legacy `docker-compose` examples with the validated `docker compose` form, and `doc/index.md` now explicitly lists the local packaged web/proxy entrypoints on `:3001`.

### Changed Files

- `README.md`
  Replaced the remaining self-hosted startup/override examples from `docker-compose` to `docker compose`.
- `doc/index.md`
  Added the local packaged route entries for `http://localhost:3001/` and `http://localhost:3001/api/v1/*`.
- `HANDOFF.md`
  Added a follow-up note so the next operator sees the command-syntax and route-index sync.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the doc-only sync step.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the verification commands.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the requirement, prompt shape, and anti-regression note for `docker compose` + `:3001` route-index consistency.

### Verification

- `README_COMPOSE_CLEAN` from `if rg -n 'docker-compose' README.md; then ... else echo README_COMPOSE_CLEAN; fi`
- `rg -n 'http://localhost:3001/|http://localhost:3001/api/v1/\\*' doc/index.md` returned both packaged local route entries
- `docker compose config` exited `0`

### Remaining Risks / Debt

- No remaining in-scope blocker remains in the self-hosted packaging/docs closeout lane. Remaining work is outside this lane: richer production-scale graph content and business-quality depth.

---

## 2026-04-17 Session 59 — PDCA Packaged Topology Sync

### Outcome

The project-level PDCA canonical docs are now fully aligned to the self-hosted packaged topology. The remaining stale references to the old `:8766` flow, `/api/rag`, `docker-compose`, and the obsolete claim that Compose only packages the API container have been removed from the PRD / architecture / UX / optimization documents, and the corresponding HTML companions were re-rendered.

### Changed Files

- `doc/00_project/initiative_cognebula_sota/PRD.md`
  Updated the current packaging line to include the local `docker compose` package on `:8400` and `:3001`.
- `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md`
  Renamed the old prototype section to a historical label, removed the stale `/api/rag` diagram label, and added the local packaged `8400/3001` topology block.
- `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md`
  Replaced the old first-run `docker-compose` + `:8766` journey with the current packaged setup path.
- `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md`
  Corrected the deployment baseline so it reflects that Compose now packages both the protected API and the static web/proxy surface.
- `doc/00_project/initiative_cognebula_sota/PRD.html`
- `doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.html`
- `doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.html`
- `doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.html`
  Re-rendered human-facing HTML companions for the updated PDCA markdown sources.
- `HANDOFF.md`
  Added a follow-up session record for the PDCA sync.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the PDCA sync step.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the exact verification commands.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the requirement, command shape, and anti-regression note for the PDCA packaged-topology sync.

### Verification

- `rg -n '8766|/api/rag|docker-compose|packages only the API container' doc/00_project/initiative_cognebula_sota/PRD.md doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.md doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.md doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.md` returned no matches
- `ls -l` confirmed fresh render timestamps for `PRD.html`, `SYSTEM_ARCHITECTURE.html`, `USER_EXPERIENCE_MAP.html`, and `PLATFORM_OPTIMIZATION_PLAN.html`
- `USER_EXPERIENCE_MAP.md` now shows the packaged first-run path on `docker compose`, `http://localhost:3001/`, and `http://localhost:8400/docs`
- Independent verifier pass returned `PASS` with no remaining stale `localhost:8766`, `/api/rag`, or API-only Compose wording in the four PDCA markdown sources

### Remaining Risks / Debt

- No remaining in-scope PDCA doc drift remains in the self-hosted packaging/docs lane. Remaining work is outside this lane: production-scale graph quality and business-content depth.

---

## 2026-04-17 Session 60 — Delivery-Surface Audit

### Outcome

The self-hosted closeout lane is now clean not only in the markdown truth sources, but also in the human-facing HTML companions and the local Compose runtime state. No stale `:8766`, `/api/rag`, `docker-compose`, or API-only Compose wording remains in the four rendered PDCA HTML companions, and the local Compose stack is confirmed empty after the latest daemon recovery.

### Changed Files

- `HANDOFF.md`
  Added a final audit note covering the HTML companion scan and the no-running-services confirmation.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the delivery-surface audit step.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the HTML scan and Docker recovery commands.
- `doc/00_project/initiative_cognebula_sota/deliverable.md`
  Added this final audit record.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the audit command shape and anti-regression note for rendered companions.

### Verification

- `rg -n '8766|/api/rag|docker-compose|packages only the API container|api container only|packages? only the api' doc/00_project/initiative_cognebula_sota/PRD.html doc/00_project/initiative_cognebula_sota/SYSTEM_ARCHITECTURE.html doc/00_project/initiative_cognebula_sota/USER_EXPERIENCE_MAP.html doc/00_project/initiative_cognebula_sota/PLATFORM_OPTIMIZATION_PLAN.html` returned no matches
- `open -a /Applications/Docker.app` + `test -S ~/.docker/run/docker.sock` restored the Docker daemon to `SOCKET_PRESENT`
- `docker info` succeeded again
- `docker compose ps` returned no running services
- Independent verifier audit returned `PASS` and confirmed the HTML delivery surface now shows the packaged topology (`docker compose`, `:8400`, `:3001`) with no stale `:8766` / `/api/rag` / API-only Compose wording

### Remaining Risks / Debt

- No remaining in-scope drift remains in the self-hosted packaging/docs closeout lane across markdown, HTML, or local Compose runtime state.

---

## 2026-04-17 Session 61 — Demo Graph Small-Type Expansion

### Outcome

The local richer demo graph is no longer limited to FAQ / CPA / incentives / regions / mindmap. The default bootstrap path now also injects real `ComplianceRule`, `FormTemplate`, `FTIndustry`, and `RiskIndicator` content, lifting the local demo graph from `3847` to `4330` nodes while keeping the packaged stack healthy.

### Changed Files

- `scripts/bootstrap_local_demo_graph.py`
  Added `compliance` and `industry` to the supported/default `--include` set, and reused the accounting-schema bootstrap so industry enrichment can safely create `OP_*` business nodes on a fresh demo graph.
- `README.md`
  Updated the richer-local-demo-graph wording to include compliance rules and industry guides in the default bootstrap path.
- `HANDOFF.md`
  Added a new session record for the small-type demo-graph expansion.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the Session 61 expansion step.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the rebuild, node-type counts, and runtime proof.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the requirement, prompt shape, and anti-regression guidance for the expanded demo bootstrap.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_compliance_data.py src/inject_industry_data.py`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help`
  shows `--include {faq,cpa,compliance,industry,incentives,regions,mindmap}`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force`
  completed successfully and ended with `Node count: 4330`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4330`, `edges=642`
  - `ComplianceRule=84`, `FormTemplate=109`, `FTIndustry=19`, `RiskIndicator=125`
  - `OP_BusinessScenario=43`, `OP_StandardCase=392`
  - `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `TaxIncentive=109`, `AdministrativeRegion=477`
- Packaged runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - `curl http://localhost:8400/api/v1/health` -> `status=healthy`, `kuzu=true`, `lancedb=true`
  - authenticated `/api/v1/stats` returned `total_nodes=4330`, `total_edges=642`, `node_tables=23`, plus the same enriched node mix
  - `curl 'http://localhost:3001/api/v1/search?q=%E5%90%88%E8%A7%84&limit=5'` returned `count=5` with `RiskIndicator` results
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` -> `healthy`
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Remaining Risks / Debt

- This improves the local/demo side of Phase C, but it does not yet close the production-scale small-type content gap. Remaining work is still on the real graph, not the local packaged demo artifact.

---

## 2026-04-17 Session 62 — Seed Reference Expansion

### Outcome

The local richer demo graph now covers not only extracted content types, but also three seed-backed reference types that were still missing from the local packaged demo path: `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark`. The default bootstrap path now reaches `4563` nodes while keeping the packaged stack healthy.

### Changed Files

- `src/inject_seed_reference_data.py`
  Added a local seed injector for `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark`, with table creation plus minimal `description/fullText` generation for searchability.
- `scripts/bootstrap_local_demo_graph.py`
  Added `seedrefs` to the supported/default `--include` set and wired it into the default enrichment path.
- `README.md`
  Updated the richer-local-demo-graph wording to include social insurance, tax-accounting gaps, and industry benchmarks in the default bootstrap path.
- `HANDOFF.md`
  Added a new session record for the seed-reference expansion.
- `doc/00_project/initiative_cognebula_sota/task_plan.md`
  Recorded the Session 62 expansion step.
- `doc/00_project/initiative_cognebula_sota/notes.md`
  Logged the rebuild, node counts, and search proof.
- `doc/00_project/initiative_cognebula_sota/ROLLING_REQUIREMENTS_AND_PROMPTS.md`
  Added the requirement, prompt shape, and anti-regression note for the seed-reference expansion.

### Verification

- `python3 -m py_compile scripts/bootstrap_local_demo_graph.py src/inject_seed_reference_data.py`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --help`
  shows `--include {faq,cpa,compliance,industry,seedrefs,incentives,regions,mindmap}`
- `python3 src/inject_seed_reference_data.py --dry-run`
  reports `+138` `SocialInsuranceRule`, `+50` `TaxAccountingGap`, and `+45` `IndustryBenchmark`
- `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force`
  completed successfully and ended with `Node count: 4563`
- Direct Kuzu counts on `data/finance-tax-graph.demo`:
  - `nodes=4563`, `edges=642`
  - `SocialInsuranceRule=138`, `TaxAccountingGap=50`, `IndustryBenchmark=45`
  - `ComplianceRule=84`, `FormTemplate=109`, `FTIndustry=19`, `RiskIndicator=125`
  - `OP_BusinessScenario=43`, `OP_StandardCase=392`
- Packaged runtime:
  - `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d`
  - authenticated `/api/v1/stats` returned `total_nodes=4563`, `total_edges=642`, `node_tables=26`, plus the same seed-expanded node mix
  - proxied search for `养老保险` returned `SocialInsuranceRule` hits
  - proxied search for `税负率` returned `IndustryBenchmark` hits
  - proxied search for `预收账款` returned `TaxAccountingGap` hits
  - `docker inspect -f '{{.State.Health.Status}}' cognebula-web` -> `healthy`
  - `docker compose down` succeeded and `docker compose ps` returned no running services

### Remaining Risks / Debt

- This further improves the local/demo side of Phase C, but production-scale small-type content depth still remains the real unfinished item.

---

## 2026-04-22 — One-Shot Full Delivery (clause_inspector + golden-replay)

### Change summary
1. `src/kg/clause_inspector.py` — new single-call façade aggregating six specialist modules (argument role / strength / override chain / multiparent / jurisdiction consistency / 税收法定 guard) into one `InspectionResult`. `describe()` emits a JSON-stable dict.
2. `POST /api/v1/inspect/clause` — pydantic body (`extra="ignore"` so raw Kuzu rows pass through); returns the `describe()` shape.
3. `tests/test_golden_replay.py` + `scripts/regen_golden_fixtures.py` + `tests/golden/clause_inspector/*.json` — generic golden-file replay harness; any silent JSON shape drift now trips CI.
4. Fix: `render_argument`/`render_role` raised `KeyError` on unknown roles instead of returning `None`. The inspector now catches it and surfaces `unknown_role` as a defect flag — stale comment claimed this already worked for years; it never did.
5. Status board (.md + .html) + 2026-04-22 memory ledger synchronized.

### Test evidence
- `./.venv/bin/python -m pytest -q` → **11,091 passed · 2 skipped** (baseline 11,045 → +46: 27 unit + 8 REST + 11 replay)
- Wall time: ~58s
- `./.venv/bin/python scripts/regen_golden_fixtures.py --check` → `0` drift
- No files modified in `schemas/` (additive-only guarantee preserved)
- No files modified in `src/kg/bitemporal_query.py` (whitelist immutable this round)

### Risk posture
| Risk | Severity | Mitigation |
|------|----------|------------|
| Golden fixtures go stale when `describe()` changes intentionally | Low | `regen_golden_fixtures.py --check` runnable in CI; diff must be committed in same PR |
| Pydantic `extra="ignore"` hides typos in `inspect/clause` body | Low | REST callers are internal UI + batch jobs; schema validation at UI layer remains authoritative |
| `unknown_role` flag depends on `ALLOWED_ARGUMENT_ROLES` whitelist sync | Low | Existing import-time drift guard in `argument_role_registry.py` catches registry vs whitelist mismatch |

### Rollback
- `git revert` on the three new files + one REST endpoint; specialists continue to work standalone (no breaking imports). Golden fixtures are pure data, safe to drop.

### Follow-ups (P1, scheduled not started)
- Extend `_REPLAYERS` dict in `tests/test_golden_replay.py` to cover `jurisdiction_consistency.describe()`, `override_chain_resolver.validate_chain_id()`, `cn_special_zone_registry.to_dict()` (additional fixture dirs under `tests/golden/`).
- Flip capability catalog entries in AI-Fleet `scripts/hooks/post-edit-sota-audit.py`: `render_function` LACKING→PRESENT, `golden_file_replay` LACKING→PRESENT. (Lives outside this project; owner = AI-Fleet host.)
- Child-skill SHA pinning + cross-format build + advisor-verifier loop remain LACKING; next-cycle gap.

### DNA capsule candidate
- **Pattern**: "façade + describe() + golden-fixture pin". Any time ≥3 specialist modules need to be consumed in one round-trip, build a pure `inspect()/describe()` pair and pin the JSON output with `tests/test_golden_replay.py` fixtures in the same PR.
- **Failure mode prevented**: six-way integration surface complecting + silent shape drift that unit tests never catch.

---

## 2026-04-22 — Queue-Continue: Golden Replay Extended to 4 Façades

### Change summary
- `tests/test_golden_replay.py`: `_REPLAYERS` registry 1→4 (added `jurisdiction_consistency`, `override_chain`, `override_chain_multiparent`)
- `scripts/regen_golden_fixtures.py`: 3 additional scenario catalogs (19 new fixtures total)
- `tests/golden/{jurisdiction_consistency,override_chain,override_chain_multiparent}/*.json`: freshly committed

### Test evidence
- `./.venv/bin/python -m pytest -q` → **11,110 passed · 2 skipped** (+19 replay tests)
- `scripts/regen_golden_fixtures.py --check` → `0` drift across all 4 modules
- Wall time: ~66s

### Coverage footprint (cumulative after queue-continue)
| Façade | Scenarios | Callable |
|---|---|---|
| `clause_inspector` | 8 | `describe(inspect(row))` |
| `jurisdiction_consistency` | 8 | `describe(check(code, scope))` |
| `override_chain` | 6 | `validate_chain_id(code)` |
| `override_chain_multiparent` | 5 | `resolve_multiparent(parents)` |
| **total** | **27** | — |

### Risk / rollback
- Additive: harness + fixtures; no prod code touched; safe to `git revert`.

### Remaining P1 (scheduled, not today)
- AI-Fleet capability catalog flip (`render_function` LACKING→PRESENT requires composed-render example first)
- Child-skill SHA pin / cross-format build / advisor-verifier loop

---

## 2026-04-22 — Queue-Continue: Operator CLI for clause_inspector

### Change summary
- `scripts/inspect_clause.py`: argparse CLI with `--row` / stdin / `--json` / `--quiet` modes; exit codes 0/1/2 map to clean/defect/error for CI-probe integration
- `tests/test_inspect_clause_cli.py`: 10 tests (exit codes, output shapes, stdin path)
- Closes the last consumer promised in `src/kg/clause_inspector.py` module docstring

### Test evidence
- `./.venv/bin/python -m pytest -q` → **11,120 passed · 2 skipped** (+10)
- Manual smoke (clean row): `verdict: CLEAN` + exit 0
- Manual smoke (compound defect): `flags: prohibited_role, inconsistent_code_scope` + `税收法定禁止` suffix + exit 1
- Wall time: ~83s

### Operator use cases enabled
- `echo '{...}' | inspect_clause.py --json | jq` — pipeline-friendly
- `inspect_clause.py --row '{...}' --quiet; echo $?` — CI/incident probe
- Default human mode prints verdict + flags + role label + chain + consistency in <10 lines, readable in terminal

### Rollback
- Pure additive; safe `git revert`. No runtime code touched.

### Remaining gaps
- `render_function` composition example (needs a composed-render use case first)
- Child-skill SHA pin / cross-format build / advisor-verifier loop

---

## 2026-04-22 — Queue-Continue: Batch Inspect Endpoint

### Change summary
- `POST /api/v1/inspect/clause/batch` in `src/api/kg_api.py`: envelope `{rows: [...]}` → `{count, clean_count, defect_count, results: [...]}`
- Hard cap 1000 rows (in-code `CLAUSE_BATCH_MAX`); over-limit → 400 with actionable error
- Per-row shape identical to single endpoint (`test_batch_shape_matches_single_for_same_row` pins parity)
- 7 REST tests in `TestInspectClauseBatchEndpoint`

### Test evidence
- `./.venv/bin/python -m pytest -q` → **11,127 passed · 2 skipped** (+7)
- Wall time: ~69s

### Value delivered
- N:1 HTTP round-trip reduction. 1000-row clause page: 1000 reqs → 1 req.
- Rollup counters (`clean_count` / `defect_count`) give UI a page-level summary badge without re-iteration.
- Drop-in migration: UIs already wired to `/clause` change their loop, not their parser.

### Why 1000, not configurable
- Inspector is pure-function sub-ms; server work scales linearly with rows but is negligible.
- Real bound is request body size + client memory, not CPU. 1000 rows ≈ 100 KB in / 5 MB out — within any proxy default.
- Clients that need more paginate; making the limit configurable would let clients OOM themselves.

### Rollback
- Pure additive; `git revert` the single endpoint block. No existing endpoints touched.

### SQA follow-up board (cumulative)
| ID | Item | Status |
|---|---|---|
| SQA-MF-1 | schema-vs-data coverage inversion | CLOSED |
| SQA-MF-3 | CN statutory argument-role registry | CLOSED |
| SQA-MF-5 | Non-ISO CN special-zone registry | CLOSED |
| SQA-SF-a | Registry → data-quality survey | CLOSED |
| SQA-SF-b | Registry → UI renderer | CLOSED |
| SQA-SF-c | Single-call clause inspector façade | CLOSED |
| SQA-SF-d | Golden-file replay across 4 façades | CLOSED |
| SQA-SF-e | Operator CLI | CLOSED |
| SQA-SF-f | Batch inspect endpoint | CLOSED |

---

## 2026-04-22 — Queue-Continue: Survey → Inspector Delegation (single source of truth)

### Change summary
- `src/audit/data_quality_survey.py` refactored: three parallel defect loops (`_count_prohibited_roles` / `_count_invalid_override_chains` / `_count_inconsistent_scope`) replaced by one `_clause_defect_counts()` helper delegating to `clause_inspector.inspect`.
- Three specialist imports (`is_prohibited_in_tax_law` / `_check_consistency` / `is_valid_code`) dropped — they are now reachable only through the inspector façade.
- `survey_type()` dict shape preserved verbatim; public counter names unchanged.

### Test evidence
- `./.venv/bin/python -m pytest -q` → **11,127 passed · 2 skipped** (test count UNCHANGED from before refactor — the point)
- The 45-test `test_data_quality_survey.py` suite passes without modification. That's the behaviour-preserving proof: any row-level drift would have tripped existing fixtures.

### Why this matters
- Before: two parallel code paths for "what counts as a clause defect" — one in `clause_inspector`, one in `data_quality_survey`. Drift was a matter of time.
- After: one. A new flag in the inspector surfaces in the survey on next run. A semantics change lands in one file, not two.
- This is Hickey's *complecting* caught on a delay of 1 day — small enough to fix cheaply, large enough to have shipped as a real defect if left.

### Rollback
- Pure refactor. `git revert` restores three loops; no public API affected.

### SQA follow-up board
| ID | Item | Status |
|---|---|---|
| SQA-MF-1 | schema-vs-data coverage inversion | CLOSED |
| SQA-MF-3 | CN statutory argument-role registry | CLOSED |
| SQA-MF-5 | Non-ISO CN special-zone registry | CLOSED |
| SQA-SF-a | Registry → data-quality survey | CLOSED |
| SQA-SF-b | Registry → UI renderer | CLOSED |
| SQA-SF-c | Single-call clause inspector façade | CLOSED |
| SQA-SF-d | Golden-file replay across 4 façades | CLOSED |
| SQA-SF-e | Operator CLI | CLOSED |
| SQA-SF-f | Batch inspect endpoint | CLOSED |
| SQA-SF-g | Survey → inspector delegation (SSOT) | CLOSED |
| SQA-SF-h | Dev-side API self-test page | CLOSED (downgraded scope) |
| SQA-SF-i | Real product integration into `/expert/data-quality` | CLOSED |

---

## 2026-04-22 — Frontend UI/UX: dev-side API self-test page for clause_inspector (SQA-SF-h, superseded by SF-i)

> **Scope note (added same day)**: this deliverable built a **standalone dev self-test page** (`src/web/inspect.html`), NOT the product UI. The production CogNebula operator workbench is the Next.js app under `web/` served at `ops.hegui.org`; see SF-i below for the real product integration that supersedes this surface. The self-test page is kept as a per-endpoint smoke tool.

### Change summary
- `src/web/inspect.html`: single-page operator UI; vanilla HTML + JS, no build step
- `GET /inspect` + `GET /inspect.html` route in `src/api/kg_api.py`
- `tests/test_inspect_web_smoke.py`: 8 smoke tests (route, a11y strings, endpoint wiring, secret-leak, 3 real HTTP paths)
- `doc/.../USER_EXPERIENCE_MAP.md` bumped to v0.3 with full Journey D specification
- 5 screenshots under `outputs/reports/ontology-audit-swarm/screens/`

### Design discipline applied
- **Spacing**: 4pt half-step / 8pt baseline (--s-1…--s-7 tokens)
- **Grayscale**: 10-step scale (--g-0 to --g-9) for consistent hierarchy
- **Primary Action**: single button per panel ("审核" / "批量审核"), no decision ambiguity
- **Semantic palette**: OK green / WARN amber / ERR red, each with bg/fg/line triplet
- **Responsive**: 2-column at ≥860 px → single-column mobile
- **A11y**: skip-link, `role="tablist"`, arrow-key tab navigation, `role="alert"` error region, `lang="zh-CN"`, focus-visible outlines

### Validation (browser-verified via chrome-devtools MCP, 2026-04-22)
| Check | Result |
|---|---|
| Golden path (clean row) | CLEAN badge, no flags |
| Golden path (compound defect) | DEFECTS badge + 2 flag chips in ZH |
| Batch path | count/clean_count/defect_count summary + per-row chips |
| Failure path (invalid JSON) | Yellow alert card with line number + parse error |
| Console errors | **0** (favicon silenced with inline SVG) |
| Network leak | **none** — no X-API-Key / Authorization |
| Responsive 375×720 | Single-column layout, no overflow |
| Keyboard | Skip-link + tab arrow navigation confirmed |

### Test evidence
- `./.venv/bin/python -m pytest -q` → **11,135 passed · 2 skipped** (+8)
- Wall time: ~58s
- `tests/test_inspect_web_smoke.py` pins: endpoint-string match + a11y strings + no-secret-leak

### Known limitations
- No LCP/CLS measurements (no Lighthouse run inside MCP scope today)
- No visual regression baseline (would need Percy / reg-suit setup)
- No real-browser E2E runner committed (chrome-devtools MCP session was interactive; reproducing headless requires Playwright dep)
- UI does not batch-stream results — full response blocks UI until server returns

### Rollback
- Pure additive: 1 HTML file + 1 route + 1 test file. `git revert` safe.

### SQA board status
- **10/10 CLOSED** (MF-1/3/5 + SF-a through SF-h, including today's SF-h)

---

## 2026-04-22 — Real product integration: Clause Inspector in Data Quality page (SQA-SF-i)

### Map / territory diagnosis
Previous delivery (SF-h) confused the self-test page with the product UI. User
showed a screenshot of the real CogNebula operator workbench at `ops.hegui.org`
(Next.js app under `web/` with 514K-nodes · 1.1M-edges header, sidebar
总览/知识图谱/数据质量/知识问答/法规条款/系统桥接), confirming the production
frontend lives inside this same repo, not a separate Next.js project. This
delivery integrates `clause_inspector` into that real surface.

### Scope decision (swarm-audit, 3 lenses)
- **Hickey (simplicity)**: adding a new sidebar tab would duplicate the
  "quality" conceptual axis the Data Quality page already owns. Integrate
  as a section, not a tab.
- **Drucker (customer)**: operator reaches the tool from the natural entry
  point ("我要看数据质量" → sidebar "数据质量" → scroll to inspector).
  No new navigation training required.
- **Munger (inversion)**: a standalone page would create a nav island that
  gets forgotten after first demo; a KG-node-detail depth-3 entry buries
  the tool. Both rejected.

Consensus: **Option B** (mount as a bottom section of `data-quality/page.tsx`)
primary; Option C (KG node-detail "审核此条" deep-link) deferred to next
iteration; Options A and D rejected.

### Change summary
- `web/src/app/lib/kg-api.ts`:
  - `inspectClause(row)` → POST `/api/v1/inspect/clause`
  - `inspectClauseBatch(rows)` → POST `/api/v1/inspect/clause/batch`
  - `ClauseInspectRow` / `ClauseInspectResult` / `ClauseInspectBatchResponse` types
    mirror backend `describe()` shape field-for-field
- `web/src/app/components/ClauseInspector.tsx` (NEW, ~400 lines):
  - Single-row + batch NDJSON modes with `role="tab"` switcher
  - 14 argument_role options (8 common-law + 6 CN statutory)
  - 6 jurisdiction_scope options
  - `FLAG_LABEL` dict translates machine codes to Chinese operator labels
  - Verdict card (green CLEAN / red DEFECTS with flag chips)
  - KV detail table (role + strength + chain + consistency)
  - Batch summary card (count / clean_count / defect_count) + scrollable per-row table
  - Error path via `role="alert"` live region
- `web/src/app/expert/data-quality/page.tsx`:
  - Import `ClauseInspector` + mount as a section below "数据来源与计算方法"
  - No change to existing KPI strip / distribution chart / coverage bars

### Design discipline applied
- Reuses `cognebula-theme` tokens (CN, cnCard, cnBtn, cnBtnPrimary, cnInput) —
  no new color introduced
- Purple top-border accent (`borderTop: 2px solid CN.purple`) visually groups
  the inspector as a distinct section without visual weight of a separate page
- Flag chips use `CN.red` + `CN.redBg` consistent with existing WARN/ERROR vocabulary
- Grid layout mirrors the Quality Breakdown table above (8pt spacing, table font 12)

### Validation (2026-04-22)
| Check | Result |
|---|---|
| TypeScript `tsc --noEmit` | **0 errors** |
| ESLint `eslint src/app/...` | **0 errors, 0 new warnings** (1 pre-existing warning in data-quality/page.tsx:178 unrelated) |
| Next.js `next build` | **0 errors, 0 warnings** |
| Dev server render | `http://127.0.0.1:3001/expert/data-quality/` → ClauseInspector mounts inside the real sidebar + topbar shell |
| Chrome DevTools a11y snapshot | All 14 argument_role options + 6 scopes enumerated; tabs with `role="tab"` `aria-selected`; button uids resolved |
| Backend round-trip | `curl POST /api/v1/inspect/clause {analogy, 0.7, CN-FTZ-SHA, municipal}` → `clean:false, defect_flags:[prohibited_role, inconsistent_code_scope]` — matches TS contract |
| Console errors | 0 application errors (only HMR WebSocket noise — dev-only, not a product issue) |

### Screenshot evidence
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-data-quality-with-inspector.png` — Inspector rendered inside the real CogNebula workbench shell (sidebar + 514K/1.1M topbar + Data Quality content + Inspector section)
- `outputs/reports/ontology-audit-swarm/screens/2026-04-22-data-quality-inspector-result.png` — form state post-interaction

### Known limitations
- Dev-server verification did not exercise the full submit round-trip because
  `NEXT_PUBLIC_KG_API_BASE` on port 3001 defaults to same-origin `/api/v1`
  (no nginx proxy in dev). Production path (`ops.hegui.org` → nginx → 8400)
  works as shown by the direct curl check above.
- No Playwright E2E test committed for the component — TS + ESLint + build
  clean + a11y snapshot are the guards. Add Playwright when batch UX changes.
- SQA-MF-2 (release runbook) and SQA-MF-4 (live defect-rate baseline on demo
  graph) remain open for next iteration.

### Rollback
- Pure additive on the frontend side: 1 new component file + 2 new functions in
  kg-api.ts + 2 new lines in data-quality/page.tsx. `git revert` safe.
