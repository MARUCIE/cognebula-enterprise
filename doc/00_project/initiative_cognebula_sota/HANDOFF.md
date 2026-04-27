---
initiative: cognebula_sota
last_session_utc: 2026-04-28T20:30:00Z
status: ACTIVE
---

# HANDOFF — CogNebula SOTA

> Per-initiative HANDOFF per CLAUDE.md `Per-Initiative HANDOFF Convention` (added 2026-04-27).
> Identity anchor: `initiative: cognebula_sota` matches directory slug `initiative_cognebula_sota`.
> Root `HANDOFF.md` (1,374 lines, conflates this initiative with Lingque Desktop) — full migration deferred (see §Deferred-half).

## Current state (2026-04-28)

**Active sprint**: SOP 3.2 API contract drift probe — **CLOSED** with commit `90aa691`.
**Cumulative deliverable**: 6 capabilities flipped LACKING→PRESENT across G1+G2+G3+H. Audit gate now wired into nightly tier as `tests/test_api_contract_drift.py` (7 tests).

### Last 3 commits on `main`

| SHA | Sprint | Date |
|---|---|---|
| `90aa691` | sop-3.2 SOTA closure — reachability + MCP coverage + PDCA artifacts (G3+H+closeout) | 2026-04-28 |
| `8c5acc2` | sop-3.2 deploy-manifest layer added to drift probe (G2) | 2026-04-27 |
| `abbc78c` | sop-3.2 API contract drift probe — advisory→enforcing (G1) | 2026-04-26 |

### Probe metrics (current)

```
backend_a_route_count: 23                   (kg-api-server.py)
backend_b_route_count: 25                   (src.api.kg_api)
route_overlap_count: 3
dual_backend_drift_ratio: 0.12              (under 0.25 gate)
dual_backend_split_signal: true             (HITL — Maurice owns merge/split decision)
module_mismatch_signal: true                (Dockerfile=kg-api-server:app, systemd=src.api.kg_api:app — REPORTED, NOT GATED)
frontend_distinct_path_count: 9
frontend_orphan_count: 1                    (whitelisted /api/v1/ka/)
frontend_paths_with_deploy_mode_drift: 10
mcp_orphan_count: 0
mcp_tool_count: 7
```

### Test counts (current)

```
nightly: 5,856 PASS + 11 known schema_completeness HITL fails = 5,867 collected
standard: 1,582 collected (drift tests are nightly-tagged only)
test_api_contract_drift.py: 7/7 PASS in 0.17s
```

### Capability ledger (cumulative this sprint)

| Capability | Pre G1 | After H | Source |
|---|---|---|---|
| `audit_api_contract` | LACKING | **PRESENT** | `scripts/audit_api_contract.py` |
| `frontend_orphan_gate_in_ci` | LACKING | **PRESENT** | `tests/test_api_contract_drift.py` (nightly) |
| `deploy_manifest_parsing` | LACKING | **PRESENT** | parse Dockerfile/systemd/nginx/docker-compose |
| `module_mismatch_signal_reported` | LACKING | **PRESENT** | reported in JSON, non-gating per HITL discipline |
| `reachability_per_deploy_mode` | LACKING | **PRESENT** | `compute_reachability_per_deploy_mode()` |
| `mcp_vs_backend_coverage` | LACKING | **PRESENT** | `compute_mcp_attribution()` + `mcp_orphan_count == 0` gate |
| `runtime_capability_endpoint` | LACKING | LACKING | Sprint G4 forward-scope |
| `live_running_backend_probe` | LACKING | LACKING | Sprint G4 forward-scope |
| `cross_repo_audit_lingque_desktop` | LACKING | LACKING | separate codebase, separate session |

## Open HITL decisions (Maurice owns)

1. **Backend split formalization** — `kg-api-server:app` (root file, dockerfile) vs `src.api.kg_api:app` (layered, systemd). Probe makes the divergence visible at every nightly run; the operational impact (10 frontend paths reachable in one mode but not the other) is now quantified. **Decision options**: (a) merge into single canonical module, (b) formalize the split with explicit per-mode docs, (c) deprecate one. Probe does NOT force the choice — it surfaces the data.
   - **decide_by**: `2026-05-28` (30 days from current iteration close) OR earlier if §18.3 `hitl_age_days` gate fires.
   - **trigger_condition**: any one of (i) `dual_backend_drift_ratio > 0.20` for ≥3 consecutive nightly runs, (ii) `frontend_paths_with_deploy_mode_drift > 12` (current 10), (iii) any production incident attributed to module mismatch on Contabo. First trigger that fires forces decision-or-explicit-redeferral.
2. **Schema-vs-PROD drift on partial-attribution types** — 11 nightly-tier `test_schema_completeness.py` failures are pre-existing. Partial-attribution columns (`source_doc_id`, audited lineage columns) carried in PROD but not declared in canonical schema. **Decision options**: (a) extend canonical schema to declare lineage columns, (b) drop lineage from PROD, (c) document as intentional partial.
   - **decide_by**: `2026-06-01` (xfail deadline planted by §18.8 — once the date passes, all 11 xfail tests flip to FAIL and break nightly).
   - **trigger_condition**: any one of (i) the `2026-06-01` xfail deadline lapses without decision, (ii) `schema_completeness` failure count grows beyond the §18.6/§18.8 baseline of 11 (new lineage columns appearing in PROD without canonical update), (iii) any consumer of canonical schema (audit script, ingestion pipeline, MCP tool) hits a NULL lineage column on a row claimed to have one.

## Escalation criteria for non-gating signals (added §18.12)

The audit emits several "REPORTED, NOT GATED" signals (current: `module_mismatch_signal`, future: anything tagged HITL). Without a written escalation rule, these signals risk aging into permanent furniture (Munger P0). Escalation rule:

- **`module_mismatch_signal=true` flips REPORTED → GATED** when ANY of:
  - The HITL-1 `trigger_condition` above fires (ratio drift / unreachable-path growth / production incident).
  - Two consecutive iterations (≥2 sprint closures) fail to either resolve the underlying drift OR explicitly re-defer with updated `decide_by` date.
  - The audit's `signal_age_days` field (planted by §18.4) exceeds 180 days for this signal specifically.
- When a signal flips to GATED, the corresponding nightly assertion in `tests/test_api_contract_drift.py` becomes a hard `assert not signal_present` rather than a soft `signal_reported` log line. The flip itself is a code edit (PR-visible decision).

## Next-cycle queue (Sprint G4 in-flight)

Materialized in `task_plan.md §15`. MVS-shaped, decoupled-runtime-audit approach to keep per-slice budget under 60 min:

1. **S15.1 Backend A OPTIONS endpoint** — **DONE 2026-04-28** (commit `e1f65bb`). `OPTIONS /api/v1/.well-known/capabilities` added to `kg-api-server.py` returning `{module, deploy_anchor, route_count, routes[]}`. APIKeyMiddleware already exempts OPTIONS for CORS preflight, no auth-whitelist edit needed. TestClient round-trip 200 OK / route_count=28 / endpoint self-includes / `CN_DEPLOY_ANCHOR` env var honored with `'unknown'` fallback. **Pre-counted nightly test delta = +0** (per S15.5 OPTIONAL note, runtime probing lives in S15.3 bash CLI not pytest).
2. **S15.2 Backend B OPTIONS endpoint** — mirror S15.1 pattern on `src/api/kg_api.py` (~30 min). **Pre-counted nightly test delta = +0** (same rationale as S15.1; runtime probe lives in S15.3 bash). **NOT STARTED**.
3. **S15.3 `scripts/runtime_audit.sh`** — bash CLI taking a base URL, calls OPTIONS + samples ≥3 random real routes, compares declared+observed route set to `audit_api_contract.py` parse output (Munger P1: three independent witnesses, not one) (~45 min). **Pre-counted nightly test delta = +0** (script invoked from deploy hook, not pytest; lives in `scripts/` and is shellcheck-linted). **NOT STARTED**.
4. **S15.4 Deploy-runbook integration** — wire `runtime_audit.sh` into `deploy/contabo/` post-deploy hook so it runs after `systemctl start kg-api` (~20 min). **Pre-counted nightly test delta = +0** (deploy-time gate, not nightly CI). **NOT STARTED**.
5. **S15.5 (optional)** — pytest fixture wrapper that spins up backend A in subprocess on a dynamic port, runs runtime_audit.sh against it, asserts zero unreachable paths (~60 min, OPTIONAL — gate is on deploy runbook, not on nightly CI). **Pre-counted nightly test delta = +1 IF taken** (single integration test). **NOT STARTED**.

> §18.10 closure: Sprint G4 queue now declares `vertical-slice-pre-counted-test-delta` per-slice. Cumulative delta if S15.1-S15.5 all ship: +1 (S15.5 only).

Decoupling rationale: keeping the audit out of pytest avoids the runtime-fixture-complexity blow-up (port management, async startup, DB seeding). Bash + post-deploy is a smaller capital investment that catches the same class of bugs (backend compiles but deploys wrong).

## Deferred-half (logged, not asked)

- **Root HANDOFF.md migration** — root file is 1,374 lines mixing CogNebula and Lingque Desktop initiatives; per CLAUDE.md per-initiative convention should be migrated to (a) thin index of active initiatives at root, (b) per-initiative HANDOFF for cognebula_sota (this file, started), (c) per-initiative HANDOFF for lingque_desktop. The Lingque Desktop split is the larger half — needs a separate slice, possibly in the lingque-desktop repo if that's where the desktop initiative actually lives. **NOT STARTED** in this slice — out of MVS budget.
- **Sprint G4 implementation** — S15.1 shipped 2026-04-28; S15.2 / S15.3 / S15.4 / S15.5 still pending.
- **Cross-repo 灵阙 desktop frontend audit** — separate codebase. Either (a) copy `audit_api_contract.py` pattern there, or (b) generalize the pattern into a shared AI-Fleet skill once the 2nd consumer surfaces (per Skill design rule "do it manually 3-10 times before codifying" — currently only 1 consumer).
- **Full nginx config grammar parser** — current parser is regex-narrow on `proxy_pass` only. Out of MVS budget (~200 LOC for hand-rolled state machine). Use `python-nginx` library if Sprint G4+ scope needs it.
- **`scripts/audit_content_quality.py` gate-wiring** — runtime probe (KuzuDB direct or `/api/v1/nodes`); falls into the same runtime-fixture-cost bucket as Sprint G4. After Sprint G4 ships its runtime probe infrastructure, this becomes a 30-min copy-pattern slice (re-use the OPTIONS endpoint + runtime_audit.sh shape).

## Cross-session signals

- **PDCA evidence path**: `outputs/pdca-evidence/sop-3.2-drift-probe/it-01/gates.json` (schema-validated, 9 gates, 6 P0 PASS + 3 P1 BLOCKED-HITL/TODO, 4 remaining_risks, 2 dna_capsule_candidates).
- **PDCA iteration log**: `doc/00_project/initiative_cognebula_sota/PDCA_ITERATION_CHECKLIST.md` (it-01 entry covering G1+G2+G3+H per pdca-iteration-pipeline template).
- **Deliverable rolling log**: `doc/00_project/initiative_cognebula_sota/deliverable.md` — most recent entry `2026-04-28 — Sprint G3 + Sprint H + PDCA closeout`.
- **Notes (cumulative)**: `doc/00_project/initiative_cognebula_sota/notes.md` — most recent entry same date, includes capability ledger flip + design-rule capture (HITL-signal-not-gate, pre-counted-test-delta).

## Working tree state (updated 2026-04-28T20:30Z)

Branch `main` is **in sync with `origin/main`** at session-end. 5 commits added this session and pushed cleanly:
- `b662ff4` ontology-guard docstring + IF backtrack skip
- `e1f65bb` kg-api-server.py S15.1 OPTIONS endpoint
- `c5dce32` §18 atomic queue materialization + Tier-0 closure
- `871759f` SOTA-Sweep-1 (6 P0 closed)
- `d57e81d` ontology-guard CI wire + drift probe push/PR + G4 deltas
- `42b3acf` SOTA-Sweep-2 (7 P0: aging gates + xfail + selftest)
- `8731728` SOTA-Sweep-3 (Sprint G4 runtime layer S15.2-S15.4 = §18.15-§18.17)

### IMPORTANT pickup caveats

1. **kg-api-server.py drift**: working tree carries 100+ pre-existing mods from prior sessions; HEAD has the surgically-extracted S15.1 only. Live state restored from `/tmp/kg-server-live-backup-1777329507.py`. Next session: either bring those WIP mods forward via scoped commits OR explicitly archive WIP if abandoned.

2. **src/api/kg_api.py drift NEW (Sprint G4 Sweep-3)**: same surgical extract pattern used for S15.2. HEAD now has the OPTIONS endpoint (30 lines after `/health`); working tree restored from `/tmp/kg_api-live-backup-1777333262.py`. **The live working tree does NOT contain S15.2** — `git diff HEAD` shows +765 / -146 (the 146 includes the 30 lines of S15.2 that are in HEAD but not in the WIP). Next session must reconcile: `git stash` the WIP, `git checkout` to verify S15.2 is on disk in clean checkout, then re-apply WIP on top OR cherry-pick S15.2 patch into WIP.

3. **Working-tree NOT bulk-stage-safe**: still applies. Scope each commit per file. The five session commits were each scope-narrow (1-6 files) and clean.

### Pickup queue (Sprint G4 = CLOSED; Tier-P1 polish remaining)

`§18` queue state: all P0 (14) closed including S18.6 subsumed. Remaining:
- **Tier-P1 (8 items)**: S18.18 (ontology_parser extract) / S18.19 (audit-manifest config) / S18.20 (backend-registry config) / S18.21 (regex non-backtracking) / S18.22 (diff-only scan) / S18.23 (evidence-link template) / S18.24 (rules promoted to ROLLING_REQUIREMENTS) / S18.25 (HANDOFF SHA validator wire). All ≤90min, mostly decomplecting + culture polish.
- **Tier-P2 (6 items)**: S18.26 (S15.1+S15.2 shared module — now ripe since both backends have OPTIONS) / S18.27-S18.29 (KuzuDB restore drill + snapshot guard + rollback test, all gated on prod access HITL) / S18.30 (working-tree triage manifest) / S18.31 (cross-session parallel-write detector).
- **HITL (5 items)**: HITL-1 backend split / HITL-2 schema-vs-PROD / HITL-3 KU_ABOUT_TAX / HITL-4 orphan project shell / HITL-5 doctax March batch. All carry `decide_by_utc` + 3 trigger conditions; tracked in `outputs/pdca-evidence/hitl-aging.json`.

## DNA capsule candidates (this iteration)

Captured in gates.json for future `ai dna validate`:

1. `audit-probe-with-hitl-signal-not-gate` — for any audit around HITL-pending state, gate must assert parseability + premise, not equality of diverged values. Forcing equality converts HITL pause into CI failure (anti-pattern: pressures rushed decision OR trains team to ignore CI).
2. `vertical-slice-pre-counted-test-delta` — atomic queue must pre-count test count delta per slice (e.g. `5,866 → 5,867 (+1, pre-counted)`). Catches G1-style `+1 vs +4` thinkos before triggering confusing nightly diffs.

---

Maurice | maurice_wen@proton.me
