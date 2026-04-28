# CogNebula SOTA -- Rolling Requirements and Prompts

## REQ Ledger

| Date | Req ID | Requirement | Status | Evidence |
|------|--------|-------------|--------|----------|
| 2026-04-16 | REQ-S48-001 | Read the project handoff, continue the unfinished semantic-edge task, and deliver it to completion without asking the user for permission. | DONE | `HANDOFF.md` Session 48, `deliverable.md`, VPS import run, benchmark results |
| 2026-04-16 | REQ-S50-001 | Close the remaining in-scope technical debt from semantic-edge closeout by removing tooling auth env drift and stale handoff KPI wording. | DONE | `HANDOFF.md` Session 50, `benchmark/run_eval.py`, `cognebula_mcp.py`, `deliverable.md` |
| 2026-04-16 | REQ-S51-001 | Keep the static web frontend browser-safe under protected API auth by routing it through an HTTPS proxy instead of exposing `KG_API_KEY` in browser code. | DONE | `web/src/app/lib/kg-api.ts`, `worker/src/index.ts`, `worker/wrangler.toml`, `deliverable.md` |
| 2026-04-16 | REQ-S52-001 | Add a self-hosted Docker Compose package for the current API + static web topology without browser-side secrets. | DONE | `docker-compose.yml`, `web/Dockerfile`, `docker/nginx.web.conf.template`, local runtime verification on default ports |
| 2026-04-16 | REQ-S53-001 | Make the remaining Phase C content-backfill scripts portable across local, Compose, and kg-node environments. | DONE | `scripts/cpa_content_backfill.py`, `scripts/mindmap_batch_backfill.py`, `scripts/ld_description_backfill.py`, local dry-run evidence |
| 2026-04-16 | REQ-S54-001 | Create a reproducible richer local demo graph so packaged local runs can use more than the bundled 157-node baseline. | DONE | `scripts/bootstrap_local_demo_graph.py`, `data/finance-tax-graph.demo`, packaged stats verification |
| 2026-04-16 | REQ-S55-001 | Remove the remaining parity gap between the documented richer demo-bootstrap default path and the actual default script/runtime behavior. | DONE | `scripts/bootstrap_local_demo_graph.py`, direct Kuzu counts, packaged API + web-proxy stats verification |
| 2026-04-17 | REQ-S56-001 | Remove the stale packaged API example from `README.md` so self-hosted docs match the current `:8400` / `:3001` stack instead of the legacy `8766 /api/rag` path. | DONE | `README.md`, doc-sync records, Docker daemon socket check |
| 2026-04-17 | REQ-S57-001 | Gather fresh runtime proof that the new README packaged API examples actually work on the live local stack. | DONE | Docker recovery, packaged stack runtime, live `search` / `hybrid-search` / proxied `search` responses |
| 2026-04-17 | REQ-S58-001 | Normalize the remaining self-hosted docs to the validated `docker compose` syntax and add the local packaged `:3001` entrypoints to the project route index. | DONE | `README.md`, `doc/index.md`, `docker compose config` verification |
| 2026-04-17 | REQ-S59-001 | Align the PDCA canonical docs to the current packaged self-hosted topology and clear the last stale `:8766` / `/api/rag` / API-only Compose wording. | DONE | `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `USER_EXPERIENCE_MAP.md`, `PLATFORM_OPTIMIZATION_PLAN.md`, re-rendered HTML companions, independent verifier PASS |
| 2026-04-17 | REQ-S60-001 | Verify that the human-facing HTML companions and the local Compose runtime state are also clean after the self-hosted doc sync. | DONE | HTML companion scan, Docker recovery, `docker compose ps` empty |
| 2026-04-17 | REQ-S61-001 | Advance Phase C small-type content expansion by extending the local demo bootstrap with compliance and industry enrichment, then re-verify the packaged stack against the rebuilt demo graph. | DONE | `scripts/bootstrap_local_demo_graph.py`, rebuilt `data/finance-tax-graph.demo`, packaged stats/search proof |
| 2026-04-17 | REQ-S62-001 | Extend the local demo bootstrap with seed-backed `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark` content, then re-verify packaged stats and search behavior. | DONE | `src/inject_seed_reference_data.py`, rebuilt `data/finance-tax-graph.demo`, packaged stats/search proof |
| 2026-04-23 | REQ-S70-001 | Rework `/expert/data-quality` so ontology conformance, rogue buckets, and dominant-type concentration are shown ahead of `/quality` score, preventing false “100/100 means usable” conclusions. | DONE | `web/src/app/expert/data-quality/page.tsx`, `web/src/app/lib/kg-api.ts`, PDCA doc sync |
| 2026-04-24 | REQ-S71-001 | Turn `/expert/data-quality` into a task-first operator workbench, add a production-snapshot validation route, and capture release-readiness evidence (responsive screenshots, smoke, Lighthouse). | DONE | `web/src/app/expert/data-quality/page.tsx`, `page.module.css`, `fixture/page.tsx`, screenshot + Lighthouse artifacts |
| 2026-04-28 | REQ-S75-001 | Accept Step 0 autonomous operating preamble, restore project root, run bounded preflight, and record the active docs/routes/test/security baseline before implementation. | DONE | `.omx/context/project-preflight-step0-20260427T161242Z.md`, `task_plan.md`, `notes.md`, subagent mapping |

## Prompt / Command Ledger

| Date | Prompt ID | Context | Command / Prompt Shape | Outcome |
|------|-----------|---------|------------------------|---------|
| 2026-04-16 | PROMPT-S48-001 | Production semantic-edge reload | `COPY SEMANTIC_SIMILAR FROM "<csv>" (from='Type', to='Type', header=false)` | Works on Vela/Kuzu `0.12.0` REL TABLE GROUP |
| 2026-04-16 | PROMPT-S48-002 | Production benchmark verification | `benchmark/run_eval.py --api http://localhost:8400 --mode hybrid` with `KG_API_KEY` present | 79% overall / 100 pass / 0 fail / 0 errors |
| 2026-04-16 | PROMPT-S48-003 | Human-facing PDCA docs | `python3 scripts/render_doc_html.py <md> <html> --title "<中文标题>" --summary "<中文摘要>"` | Generates styled standalone HTML companion with Mermaid support |
| 2026-04-16 | PROMPT-S51-001 | Static web + protected KG API | Static frontend calls `https://cognebula-kg-proxy.workers.dev/api/v1`; Worker injects `KG_API_KEY` from secret | Preserves `output: export` and keeps secrets out of browser code |
| 2026-04-16 | PROMPT-S52-001 | Self-hosted browser-safe packaging | Static web container proxies `/api/v1/*` to `cognebula-api` and injects `X-API-Key` via Nginx env template | Runtime-verified locally after image-build, baseline-graph, healthcheck, and default-port fixes |
| 2026-04-16 | PROMPT-S52-002 | Compose env wiring verification | `KG_API_KEY=dummy docker compose config` | Confirms both packaged services receive the expected auth/proxy env wiring without relying on host env state |
| 2026-04-16 | PROMPT-S52-003 | Local packaged stack runtime proof | `COGNEBULA_WEB_PORT=3001 KG_API_KEY=dummy docker compose up -d` + curl homepage and proxy health | Confirms the packaged web proxy and API container run end-to-end on a non-default local port |
| 2026-04-16 | PROMPT-S52-004 | Web health verification | `docker inspect -f '{{.State.Health.Status}}' cognebula-web` | Confirms the packaged web container reaches `healthy` after startup |
| 2026-04-16 | PROMPT-S52-005 | Default packaged stack runtime proof | `KG_API_KEY=dummy docker compose up -d` + curl `:3001` homepage and proxy health | Confirms the packaged stack now runs on its default ports without a manual web-port override |
| 2026-04-16 | PROMPT-S53-001 | Phase C script preflight | `KUZU_DB_PATH=<path> ... --dry-run` | Allows local read-only inspection of pending backfill targets without requiring a writable production Kuzu file |
| 2026-04-16 | PROMPT-S54-001 | Local demo graph bootstrap | `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` | Produces `data/finance-tax-graph.demo` with `3847` nodes from the archived baseline plus FAQ, CPA-case, tax incentive, administrative-region, and native mindmap enrichment |
| 2026-04-16 | PROMPT-S54-002 | Richer local stack runtime proof | `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d` + authenticated stats/health reads | Confirms the packaged stack can serve the richer `3847` node demo graph end-to-end |
| 2026-04-16 | PROMPT-S55-001 | Demo-bootstrap parity proof | `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` | Confirms the default flow now explicitly runs the `[mindmap] ... src/inject_mindmap_native.py` step before finishing at `Node count: 3847` |
| 2026-04-16 | PROMPT-S55-002 | Native table mix verification | direct Kuzu count query + `curl -H 'X-API-Key: dummy' http://localhost:8400/api/v1/stats` + `curl http://localhost:3001/api/v1/stats` | Confirms the rebuilt richer demo graph is `3847 / 642` with native `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `AdministrativeRegion=477`, `OP_StandardCase=266`, `TaxIncentive=109`, `LawOrRegulation=0` |
| 2026-04-17 | PROMPT-S56-001 | Packaged API README sync | Replace the stale `localhost:8766/api/rag` example with current `:8400` / `:3001` curl examples for `/api/v1/search` and `/api/v1/hybrid-search` | Keeps the top-level self-hosted docs aligned to the current packaged topology |
| 2026-04-17 | PROMPT-S56-002 | Docker runtime availability check | `docker context show` + `test -S ~/.docker/run/docker.sock` + `docker compose up -d` | Confirms whether a fresh runtime proof can be collected in the current session or whether the local Docker daemon is unavailable |
| 2026-04-17 | PROMPT-S57-001 | README example runtime proof | `COGNEBULA_GRAPH_PATH=./data/finance-tax-graph.demo KG_API_KEY=dummy docker compose up -d` + `curl` against `:8400 /api/v1/search`, `:8400 /api/v1/hybrid-search`, and `:3001 /api/v1/search` | Confirms the updated packaged README examples work against the live local stack |
| 2026-04-17 | PROMPT-S58-001 | Self-hosted doc syntax/index sync | Replace remaining `docker-compose` examples with `docker compose`, add `:3001` packaged routes to `doc/index.md`, then run `docker compose config` | Keeps the self-hosted docs aligned with the verified CLI syntax and the local packaged route map |
| 2026-04-17 | PROMPT-S59-001 | PDCA packaged-topology sync | Replace stale `:8766` / `/api/rag` / API-only Compose wording in PRD / architecture / UX / optimization docs, then re-render the HTML companions | Keeps the PDCA canonical docs aligned with the already verified self-hosted topology |
| 2026-04-17 | PROMPT-S60-001 | Delivery-surface audit | Scan the four PDCA HTML companions for stale `:8766` / `/api/rag` / `docker-compose` / API-only Compose wording, then confirm `docker compose ps` is empty | Verifies that both the rendered human-facing docs and the local runtime state are clean |
| 2026-04-17 | PROMPT-S61-001 | Demo graph small-type expansion | Extend `bootstrap_local_demo_graph.py` with `compliance` + `industry`, rebuild `data/finance-tax-graph.demo`, then verify stats and a proxied compliance search on the packaged stack | Advances the local Phase C demo graph beyond FAQ/CPA into compliance and industry content |
| 2026-04-17 | PROMPT-S62-001 | Seed reference expansion | Add `seedrefs` to the demo bootstrap, rebuild `data/finance-tax-graph.demo`, then verify `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark` counts plus proxied `养老保险` / `税负率` / `预收账款` search hits | Advances the local Phase C demo graph with seed-backed small reference types |
| 2026-04-23 | PROMPT-S70-001 | Dual-gate operator UI | `Promise.allSettled([getStats(), getQuality(), getOntologyAudit()])` + surface structural drift before hygiene metrics | Prevents partial endpoint failure from blanking the page and keeps `/quality` from masking ontology drift |
| 2026-04-24 | PROMPT-S71-001 | Validation fixture route | Preload a real production snapshot into `/expert/data-quality/fixture` so screenshots, smoke tests, and Lighthouse can run without live auth/network | Makes the workbench visually testable and release-checkable |
| 2026-04-28 | PROMPT-S75-001 | Bounded project preflight | `find web/src/app -type f \( -name 'page.tsx' -o -name 'layout.tsx' -o -name 'route.ts' \)` plus explicit root manifest reads (`web/package.json`, `requirements.txt`, `pytest.ini`) | Captures route/test/build baseline without traversing `web/node_modules` or generated `.next` output |

## Anti-Regression Q&A

| Question | Answer |
|----------|--------|
| Why did `SEMANTIC_SIMILAR` bulk load fail? | Because Vela/Kuzu `0.12.0` requires explicit `from/to` options when copying into a REL TABLE GROUP with multiple `FROM/TO` pairs. |
| Why did the first benchmark rerun return `401` for every case? | The API runtime authenticates with `KG_API_KEY`, while the runner originally only read `COGNEBULA_API_KEY`. |
| Which API key env name is canonical for active CogNebula tooling? | `KG_API_KEY`. Active benchmark and MCP code paths should not depend on `COGNEBULA_API_KEY`. |
| How can we quickly verify the auth hardening is still active after future changes? | An unauthenticated live request to `/api/v1/stats` or `/api/v1/quality` should return `401 Unauthorized`, and runtime env-resolution checks for `benchmark/run_eval.py` / `cognebula_mcp.py` should show `KG_ONLY=True` and `OLD_ONLY_EMPTY=True`. |
| How should the static web frontend reach the protected KG API? | Through the HTTPS Cloudflare Worker proxy (`cognebula-kg-proxy.workers.dev`), with `KG_API_KEY` injected in the Worker runtime rather than shipped to the browser. |
| Why did the packaged web container first report `unhealthy` even though the homepage worked? | Its healthcheck probed `http://localhost/`, which resolved to IPv6 loopback in the container while Nginx was only listening on `0.0.0.0:80`; switching the probe to `127.0.0.1` removed the false negative. |
| Why was the API image build trying to download huge CUDA/NVIDIA wheels? | The repo-wide `requirements.txt` includes embedding/ML dependencies that the API container does not need. The packaged API image now installs only the minimal runtime dependencies used by `kg-api-server.py`. |
| Why was local packaged health previously `kuzu=false`? | `docker-compose.yml` was mounting the empty directory `data/finance-tax-graph/` into a path that Kuzu expects to be a database file. The packaged stack now defaults to the real local baseline file `data/finance-tax-graph.archived.157nodes`, with `COGNEBULA_GRAPH_PATH` as an override. |
| Why does the packaged stack now default to port `3001` instead of `3000`? | `3000` is commonly occupied by other local dev stacks. The package now defaults to `3001` so its default `docker compose up -d` path succeeds more often without manual overrides. |
| How should the remaining Phase C backfill scripts be preflighted locally? | Use `--db-path` or `KUZU_DB_PATH` together with `--dry-run` against a local Kuzu file. The scripts should now exit cleanly with counts or `SKIP` messages instead of assuming `/home/kg/...` or crashing on missing tables. |
| How can we get a richer local graph without modifying the archived baseline file? | Run `./.venv/bin/python scripts/bootstrap_local_demo_graph.py --force` to create `data/finance-tax-graph.demo`, then point `COGNEBULA_GRAPH_PATH` at that file for local packaged runs. The default bootstrap now adds FAQ, CPA-case, compliance rules, industry guides, tax incentives, administrative regions, and native mindmap data. |
| Why did the richer demo graph stop showing `LawOrRegulation=1801` after the rebuild? | Because FAQ data now lands in native `FAQEntry` nodes and CPA reference content now lands in native `CPAKnowledge` nodes. After the rebuild, the richer demo graph is still `3847 / 642`, but its distribution is `FAQEntry=1152`, `CPAKnowledge=649`, `MindmapNode=990`, `AdministrativeRegion=477`, `OP_StandardCase=266`, `TaxIncentive=109`, and `LawOrRegulation=0`. |
| What regression does the demo-bootstrap parity fix prevent? | It prevents the default bootstrap path from silently omitting native mindmap enrichment. `scripts/bootstrap_local_demo_graph.py` must keep `mindmap` in its default `--include` set so the rebuilt demo graph matches the documented richer local stack behavior. |
| Why was the README `8766 /api/rag` example removed from the self-hosted usage section? | Because the current packaged stack exposes the active KG API on `http://localhost:8400/api/v1/*` and the browser-safe local proxy on `http://localhost:3001/api/v1/*`. The old `8766 /api/rag` example refers to a different legacy app surface and is misleading in the packaged deployment section. |
| What blocked a fresh third packaged runtime pass on 2026-04-17? | The Docker CLI context still points to `desktop-linux`, but `~/.docker/run/docker.sock` was missing in the session, so `docker compose up -d` could not connect to the local Docker daemon. |
| How was the 2026-04-17 Docker blocker resolved later? | Docker Desktop was relaunched, `~/.docker/run/docker.sock` returned, and Session 57 re-ran the packaged stack plus the README `search` / `hybrid-search` examples successfully. |
| How do we know the new README packaged API examples are not just textually correct? | Because after restoring the Docker daemon, the local packaged stack was re-run against `data/finance-tax-graph.demo`, and the exact README-shaped requests to `:8400 /api/v1/search`, `:8400 /api/v1/hybrid-search`, and `:3001 /api/v1/search` all returned live non-empty results. |
| Why did we replace `docker-compose` with `docker compose` in the self-hosted docs? | Because the validation and runtime evidence in this closeout lane all use `docker compose`, and the docs should match the command surface that was actually re-verified. Mixing the legacy hyphenated form back into README creates avoidable operator drift. |
| Why was `doc/index.md` updated with `http://localhost:3001/` and `http://localhost:3001/api/v1/*`? | Because the packaged stack now includes a local static web app and a browser-safe local proxy on `:3001`. The project path/route index should explicitly advertise those entrypoints, not only the remote Worker proxy and `:8400` docs endpoint. |
| How do we know the PDCA canonical docs are now aligned to the packaged topology? | An independent verifier scan on `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `USER_EXPERIENCE_MAP.md`, and `PLATFORM_OPTIMIZATION_PLAN.md` returned PASS and found no remaining stale `localhost:8766`, `/api/rag`, or API-only Compose wording. |
| How do we know the rendered HTML companions are also clean? | A direct scan across `PRD.html`, `SYSTEM_ARCHITECTURE.html`, `USER_EXPERIENCE_MAP.html`, and `PLATFORM_OPTIMIZATION_PLAN.html` returned no stale `:8766`, `/api/rag`, `docker-compose`, or API-only Compose wording. |
| Why is `/api/v1/quality` alone an unsafe proxy for graph usability? | Because it measures hygiene only inside curated tables (title/content coverage + edge density). The graph can still be unusable when `/api/v1/ontology-audit` reports rogue types, V1/V2 bleed, duplicate clusters, or catch-all buckets such as oversized `KnowledgeUnit`. |
| How do we run visual regression and responsive checks for the data-quality workbench without the protected `ops.hegui.org` shell? | Use `/expert/data-quality/fixture`, which preloads a real production snapshot captured from `app.hegui.org` and avoids live auth/network dependency during screenshots, smoke tests, and Lighthouse. |
| Was the HTML delivery surface checked independently, not just by the main agent? | Yes. An independent verifier audit returned PASS and confirmed the four HTML companions present the packaged topology (`docker compose`, `:8400`, `:3001`) with no stale `:8766` / `/api/rag` / API-only Compose wording. |
| What changed in the newest local demo graph expansion? | The default bootstrap now injects `ComplianceRule`, `FormTemplate`, `FTIndustry`, and `RiskIndicator` content in addition to FAQ / CPA / incentives / regions / mindmap, raising the demo graph to `4330` nodes while keeping the packaged stack healthy. |
| What changed in the latest seed-reference expansion? | The default bootstrap now also injects `SocialInsuranceRule`, `TaxAccountingGap`, and `IndustryBenchmark`, raising the demo graph to `4563` nodes and making those three small types searchable through the packaged `:3001` proxy path. |
| What makes semantic-edge reruns safe now? | The loader deletes existing same-type `SEMANTIC_SIMILAR` edges before re-importing that table's CSV, so partial fallback inserts do not accumulate. |
| Why must project preflight avoid broad `find` over `web/`? | Because `web/node_modules` and `.next` contain thousands of generated dependency files. Preflight should read root manifests explicitly and search source routes under `web/src/app` only. |
| What is the active P0 architecture blocker after Step 0 preflight? | Dual-backend drift: `kg-api-server.py` and `src/api/kg_api.py` both target port `8400` with disjoint route sets. Existing docs mark merge / formalize-split / deprecate-one as Maurice HITL. |

## Promoted Design Rules

Captured during Sprint G4 / §18 SOTA loop. These two rules emerged from
the 5-lens swarm audit (Hickey/Catmull/Munger/Meadows/Taleb) and survived
multi-Sweep evidence review. Promoted into the rolling ledger here so
future sessions can retrieve them by name without re-deriving from
scattered notes references.

### `audit-probe-with-hitl-signal-not-gate`

**Rule**: When an audit probe surfaces a finding that requires a HITL
(human-in-the-loop) decision (formalization, deprecation, irreversible
data migration), the probe reports the finding as a SIGNAL, not a GATE.
Pair the signal with an aging policy (`hitl_max_age_days` /
`signal_max_age_days`) that escalates only on staleness, not on first
detection.

**Why** (Munger inversion + Taleb): a gate that fires on first detection
forces the human into a decision before they have context. A signal +
aging timer preserves the HITL pause as a feature while preventing
silent eternal HITL. Goodhart's Law variant prevented: agent
optimizing for "no signals" by suppressing reports.

**Evidence**: §18.3 (HITL aging gate) + §18.4 (signal aging) + §18.12
(escalation criteria) — all closed Sprint G4 Sweep-2.
**Captured as DNA capsule**: `~/00-AI-Fleet/dna/capsules/audit-probe-with-hitl-signal-not-gate/`.

### `vertical-slice-pre-counted-test-delta`

**Rule**: Before starting a vertical-slice batch (30-90 min unit), declare
the planned test delta in numbers. After the batch completes, compare
actual vs planned. Mismatches are not failures, but they ARE evidence
about either scope estimation or scope drift.

**Why** (Meadows + Catmull): the pre-counted number is a balancing-loop
target that prevents the natural drift toward scope inflation ("might as
well add one more test while I'm here") and scope deflation ("this
particular case is annoying, I'll skip it"). The post-batch comparison
makes both drifts visible.

**Evidence**: Sprints G3 + G4 + Sweeps 1-5 all declared `+N` in commit
messages and matched against actual `git diff --stat` test counts.
Sweep-4 Batch A pre-counted +2, shipped +10 (planned scope exceeded
safely with explicit log). Sweep-5 Batch C pre-counted ≥1, shipped +6.
**Captured as DNA capsule**: `~/00-AI-Fleet/dna/capsules/vertical-slice-pre-counted-test-delta/`.

## References

- `HANDOFF.md`
- `doc/00_project/initiative_cognebula_sota/notes.md`
- `doc/00_project/initiative_cognebula_sota/deliverable.md`
- `benchmark/results_hybrid_20260416_after_security_fix.json`
- `doc/00_project/initiative_cognebula_sota/manual_verification_20260416.json`
