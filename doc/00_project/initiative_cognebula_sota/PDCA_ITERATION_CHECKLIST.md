# CogNebula SOTA -- PDCA Iteration Checklist

## Plan

- [x] Objective and closeout scope clarified for semantic-edge completion
- [x] Constraints and non-goals captured in `.omx/plans/prd-semantic-edge-closeout.md`
- [x] Verification strategy captured in `.omx/plans/test-spec-semantic-edge-closeout.md`

## Do

- [x] Fixed semantic-edge bulk load for Vela/Kuzu 0.12.0
- [x] Re-ran production import and restored API service
- [x] Standardized benchmark + MCP auth tooling on canonical `KG_API_KEY`
- [x] Generated HTML companions for updated PDCA markdown docs
- [x] Aligned the static web access path to the HTTPS Worker proxy so browser flows do not require `KG_API_KEY`

## Check

- [x] Production stats verified
- [x] Production quality gate verified
- [x] Hybrid benchmark verified
- [x] Manual UX-path verification recorded
- [x] Attacker review recorded and fixups applied
- [x] DNA capsule captured/validated
- [x] Packaged `cognebula-api` + `cognebula-web` stack verified locally on a non-default web port
- [x] Local packaged API health verified with `kuzu=true` against the bundled baseline graph

## Act

- [x] Handoff updated
- [x] Rolling ledger updated
- [x] Deliverable updated
- [x] Final closeout updated with attacker-review and DNA outcomes

---

# PDCA Iteration — SOP 3.2 API Contract Drift Probe (it-01)

> **Sprint**: sop-3.2-drift-probe (G1 + G2 + G3 + H closeout)
> **Iteration**: `it-01`
> **Kickoff**: 2026-04-26 (G1 audit), closed 2026-04-28 (G3 + H + PDCA)
> **Risk level**: LOW — parse-only audit probe, no runtime/backend code change
> **Canonical rule**: `knowledge/facts/engineering-baseline/17-pdca-iteration-pipeline.md`
> **Gates evidence**: `outputs/pdca-evidence/sop-3.2-drift-probe/it-01/gates.json`

## 0. Task Boundaries

- **Objective**: turn the post-2026-04-26 SOP 3.2 hand-written audit ("frontend↔backend drift, dual-backend split, MCP coverage gap, deploy-mode reachability") into a reproducible probe + nightly CI gate.
- **Non-objectives**: backend merge / split-formalize / deprecate decision (HITL); 灵阙 desktop frontend cross-repo audit (separate session); runtime `OPTIONS /.well-known/capabilities` endpoint (Sprint G4).
- **User value**: any new frontend HTML reference to an undeclared API path now fails CI before reaching production; module mismatch and dual-backend split are visible at every nightly run.
- **Constraints**: parse-only (no live HTTP probing in this iteration); MVS-pattern (each slice 30–60 min vertical + regression gate); HITL discipline preserved (probe reports signals, does not gate on HITL-pending divergence).
- **Success metrics**:
  1. probe ships and emits 4 in-scope JSON blocks: `backends`, `deploy_manifests`, `reachability_per_deploy_mode`, `mcp_attribution`
  2. nightly tier grows by exactly +5 tests (G1 +1, G2 +1, G3 +1, H +1, plus pre-existing +1 from G1 split — net 5,862 → 5,867)
  3. zero MCP tool orphans; one known frontend orphan (`/api/v1/ka/`) whitelisted
  4. test count delta lands as planned per slice (no surprise +N)

## 1. Stage Plan / Gate Outcomes

| Stage | Gate | Outcome | Evidence |
|---|---|---|---|
| **Spec** | task_plan.md §11/§12/§13/§14 atomic queue materialized | PASS | `doc/00_project/initiative_cognebula_sota/task_plan.md` |
| **Build** | 4 vertical slices land in `scripts/audit_api_contract.py` | PASS | commits `8c5acc2` (G1+G2) + closure commit (G3+H+PDCA) |
| **Test** | `tests/test_api_contract_drift.py` 7/7 PASS | PASS | nightly count 5,865 → 5,867 confirmed |
| **Typecheck** | stdlib-only Python; clean import under .venv | PASS | (pure regex/json, no mypy strict surface) |
| **Security** | grep battery clean (eval/Function/shell=True/secrets) | PASS | inline in `gates.json` |
| **Release** | nightly tier ships; standard tier unchanged at 1,582 | PASS | `outputs/reports/consistency-audit/2026-04-28-api-contract-drift.json` |
| **Observe** | notes.md cumulative ledger updated; `[BOOTSTRAP-EVOLUTION]` traces emit | PASS | `doc/00_project/initiative_cognebula_sota/notes.md` (this entry) |
| **Learn** | catalog delta + DNA capsule candidates captured | PASS | `gates.json.gates.learn.capability_catalog_delta` |

## 2. Iteration Log

### it-01 (2026-04-26 → 2026-04-28)

**Hypothesis**: a parse-only audit probe + a nightly pytest gate is sufficient to convert the SOP 3.2 hand-written audit into a forcing function — no backend code change, no runtime fixture needed at this iteration's scope.

**Action**:
1. Slice S11.1 (Sprint G1): parse dual backends + frontend paths; emit `frontend_orphans`, `dual_backend_drift_ratio`, `dual_backend_split_signal`. Land 1 nightly test enforcing `frontend_orphans ⊆ {/api/v1/ka/}`.
2. Slice S11.2 (Sprint G2): parse Dockerfile / systemd unit / nginx config / docker-compose; emit `deploy_manifests` with module + port + upstreams; emit `module_mismatch_signal`. Land 1 nightly test asserting all four manifests parseable.
3. Slice S12.1 (Sprint G3): compute per-deploy-mode reachability by mapping module → backend route set; emit `reachability_per_deploy_mode.{dockerfile,systemd}.{reachable_paths,unreachable_paths}`. Land 1 nightly test asserting both modes parse and ≥1 frontend path is unreachable in at least one mode (premise check).
4. Slice S13.1 (Sprint H): static-parse `cognebula_mcp.py` for `@mcp.tool()` decorators + `_api_(get|post)` calls; emit `mcp_attribution` per tool with `declared_by_backends`; emit `mcp_orphan_count`. Land 1 nightly test asserting `orphan_count == 0` (hard fail = legitimate CI failure).

**Verification**:
- 7/7 drift tests PASS (5 prior + 2 new in this closeout block)
- nightly count delta: 5,862 (pre-G1) → 5,867 (post-H) = +5 ✓ pre-counted
- standard tier collected count unchanged at 1,582 ✓ (drift tests are nightly-tagged only)
- probe JSON `frontend_orphan_count: 1` (whitelisted), `mcp_orphan_count: 0`, `module_mismatch_signal: true` (reported, non-gating), `frontend_paths_with_deploy_mode_drift: 10`

**Learning**:
- Goodhart's Law shape: when a system property is HITL-pending (e.g. backend split), the audit gate must assert *parseability + premise*, NOT *equality*. Forcing equality converts HITL pause into CI failure — bad shape. Captured as DNA candidate `audit-probe-with-hitl-signal-not-gate`.
- Pre-counting test deltas per slice prevents the Sprint G1 `+1 vs +4` thinko that surfaced during the first regression. Captured as DNA candidate `vertical-slice-pre-counted-test-delta`.
- Static parse of `@mcp.tool()` decorator + body slicing avoided the cost of bringing an AST parser into a 30-min slice — narrow regex was sufficient for the 7-tool surface. Generalizable to other "decorator + body call" patterns.

**Next step**: halt at iteration boundary. Sprint G4 (runtime `OPTIONS` endpoint + live backend probe) is queued as separately-scoped work; cross-repo 灵阙 desktop audit is queued as separate session.

### 2.5 Security scan (it-01, §Security gate)

Scanned the changed files for `eval(`, `Function(`, raw network egress, `subprocess.*shell=True`, `process.env.*TOKEN|SECRET|KEY`, `dangerouslySetInnerHTML`:

- `scripts/audit_api_contract.py`: 0 findings. Probe is read-only — opens repo files via stdlib pathlib, parses with `re`, writes JSON to `outputs/`. No network egress, no shell exec, no secret access.
- `tests/test_api_contract_drift.py`: 0 findings. Pure pytest fixtures over the probe's JSON output.

## 3. Capability Catalog Delta

| Capability | Pre it-01 | Post it-01 |
|---|---|---|
| `audit_api_contract` | LACKING | **PRESENT** (`scripts/audit_api_contract.py`) |
| `frontend_orphan_gate_in_ci` | LACKING | **PRESENT** (`tests/test_api_contract_drift.py`, nightly) |
| `deploy_manifest_parsing` | LACKING | **PRESENT** (Dockerfile / systemd / nginx / docker-compose) |
| `module_mismatch_signal_reported` | LACKING | **PRESENT** (reported, non-gating per HITL discipline) |
| `reachability_per_deploy_mode` | LACKING | **PRESENT** (`compute_reachability_per_deploy_mode`) |
| `mcp_vs_backend_coverage` | LACKING | **PRESENT** (`compute_mcp_attribution`, orphan_count gate) |
| `runtime_capability_endpoint` | LACKING | LACKING (Sprint G4) |
| `live_running_backend_probe` | LACKING | LACKING (Sprint G4) |
| `cross_repo_audit_lingque_desktop` | LACKING | LACKING (separate session) |

## 4. Debt Ledger (carried forward)

| # | Item | Owner | Deadline | Retroactive-defect if slipped |
|---|---|---|---|---|
| 1 | Sprint G4 runtime probe (`OPTIONS /api/v1/.well-known/capabilities` endpoint + live backend pytest fixture) | Maurice | TBD | no — explicit forward-scope |
| 2 | 灵阙 desktop frontend cross-repo audit (separate codebase) | Maurice | TBD | no — separate session |
| 3 | Backend merge / split-formalize / deprecate decision (HITL) | Maurice | open | no — HITL discipline |
| 4 | Full nginx config grammar parse (current parser is regex-narrow on `proxy_pass` only) | Maurice | TBD | no — out of MVS budget |

**Retroactive-defect clause (Hickey)**: items above are explicit forward-scope; none flagged as "should already exist." If Sprint G4 has not opened by the next time a deploy-mode mismatch causes a production incident, item #1 escalates to retroactive-defect.

## 5. Release Readiness Matrix

| Row | Status | Evidence |
|---|---|---|
| Audit probe reproducible | PASS | `python3 scripts/audit_api_contract.py` deterministic; report at `outputs/reports/consistency-audit/2026-04-28-api-contract-drift.json` |
| Nightly gate green | PASS | 7/7 tests pass; 5,867 collected |
| Standard tier unaffected | PASS | 1,582 collected (unchanged from baseline) |
| Module mismatch reported, not enforced | PASS | `module_mismatch_signal: true` in JSON; no test asserts equality |
| MCP coverage clean | PASS | `mcp_orphan_count: 0`, `mcp_tool_count: 7` |
| Known frontend orphan unchanged | PASS | only `/api/v1/ka/` remains, matches `KNOWN_FRONTEND_ORPHANS` in test |
| Deferred half logged not asked | PASS | task_plan §14 explicit deferred-half block + this checklist §4 debt ledger |
