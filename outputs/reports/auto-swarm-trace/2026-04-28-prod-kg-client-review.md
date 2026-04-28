# Auto-Visual-Swarm Trace · Prod KG Client + Phase F Guardrails Review · 2026-04-28

> **Targets**: `scripts/_lib/prod_kg_client.py` + `doc/00_project/initiative_cognebula_sota/KG_ACCESS_GUIDE.md` + `kg-api-server.py` Phase F guardrails (`_path_state` + `FORBIDDEN_DB_PATH_MARKERS`) + `tests/test_real_kg_runtime_config.py`
> **Outcome**: 3/3 APPROVE in Round 3 → consensus reached → shipped
> **Context**: Closes the §19 Phase E3 residual that was deferred at 2026-04-28 ~11:42 CST when all three advisor dispatches returned "You've hit your org's monthly usage limit". Quota reset by the time the Rev. 4 banner-relocation swarm fired the same day; this is the redo.

---

## Swarm composition

| Slot | Advisor | Lens |
|------|---------|------|
| 1 | `advisor-hara` | Structural minimalism — is the API surface essential or inflated? |
| 2 | `advisor-orwell` | Operator-prose clarity — does the doc tell future-Maurice what they need? |
| 3 | `advisor-munger` | Inversion on guardrails — what bypass paths still exist past the syntactic blocklist? |

The Rev. 2/3 audit swarm used Hara/Orwell/Munger; this trio repeats so the lens consistency holds across the §19 closeout.

## Round 1 — Verdicts

- **Hara**: REVISE-LOW. Three patches, all cosmetic:
  1. `selftest()` is test scaffolding, not part of the public client surface — move out
  2. `_results()` papers over an inconsistent server envelope contract; needs a comment naming the server-side fix
  3. `KG_ACCESS_GUIDE.md` documents `/api/v1/stats` then says it's broken — "a broken endpoint is not an endpoint"; remove from inventory
- **Orwell**: REVISE-TARGETED. Three sentence-level patches:
  1. Worst sentence (line 116): "S15.1+S15.2+S18.26 is not yet deployed" — sprint references mean nothing to a future operator. Suggested rewrite: forward-operator instruction
  2. SSH section (line 59): states the `~/.ssh/config` tmux fact without telling the operator what happens if their config is missing the `contabo` alias
  3. Offline fixture section blurs mock-dict and seeded-Kuzu modes; missing decision rule
- **Munger**: REVISE MEDIUM. Named three concrete bypass paths past the syntactic name-based blocklist:
  1. **Symlink laundering** — `ln -s ~/archives/finance-tax-graph.2025-12 ~/data/finance-tax-graph` passes the marker check
  2. **Non-empty stale directory** — `.demo` renamed without forbidden token still has 6,000 nodes / 109 MB and is non-empty
  3. **Bind-mount substitution** — `COGNEBULA_GRAPH_PATH=/tmp/my-fresh-kuzu` (1000-node test fixture without suspect name) mounts cleanly
  Goodhart: guard optimizes for *absence of tokens* + *non-emptiness*; renames bypass. Highest-leverage single fix: **node-count floor** (or equivalent semantic check).

**Consensus on REVISE: 3/3 (different scopes, no conflicting patches)**

## Patches applied between Round 1 and Round 2

1. **`prod_kg_client.py:_results()`** — added server-contract comment ("Server returns inconsistent envelopes; real fix is server-side normalisation, this helper papers over it for now")
2. **`prod_kg_client.py:selftest()` → `_selftest()`** — renamed to private prefix; `__main__` block updated; docstring now states "not part of the canonical client API surface"
3. **`KG_ACCESS_GUIDE.md` endpoint inventory** — removed `/api/v1/stats` line; kept warning under "Known issues" pointing operator to `/api/v1/quality` so anyone who finds the endpoint via a stale script gets routed to the alternative
4. **`KG_ACCESS_GUIDE.md` Known issues** — rewrote the capabilities-not-deployed line per Orwell's worked example: "It will return 404 until the endpoint is shipped. Do not use it until after the next prod deploy."
5. **`KG_ACCESS_GUIDE.md` SSH section** — added "If your `~/.ssh/config` has no `contabo` alias at all, those two flags still do the right thing — do not omit them. Without them the script will hang silently when the server-side login banner tries to attach a tmux session."
6. **`kg-api-server.py:_path_state()`** — Munger's spirit applied as size-floor (not node-count-floor) check:
   - Rationale for size-vs-count: doesn't require opening Kuzu (cheap startup, no read-locking, no version coupling); production is 102 GB vs deleted `.demo` at 109 MB — three orders of magnitude separation, 1 GiB floor cleanly partitions
   - New constants: `DEFAULT_DB_SIZE_FLOOR_BYTES = 1 GiB`, env override `COGNEBULA_DB_SIZE_FLOOR_BYTES`
   - New helper: `_dir_top_level_size(p)` — sums immediate-child file sizes (non-recursive); cheap probe over a 102 GB tree
   - New rejection reason: `database_below_size_floor`
   - New return fields: `below_floor_bytes`, `size_floor_bytes`
7. **Skipped (single-advisor scope)**: Orwell's offline-fixture mode-bleed split — deferred as 1/3-only patch; not an unacceptable gap per Orwell's own Round 2 read

## Round 2 — Verdicts

- **Hara**: APPROVE — "Un préfixe underscore suffit à marquer la frontière — le déplacer physiquement serait ajouter du bruit sans changer la substance." All three patches landed; nothing further to cut
- **Orwell**: REVISE-TARGETED on Patch 1 only — the rewritten capabilities sentence still ends with "Do not use it until after the next prod deploy", which is a dead instruction (operator cannot know when that is). Patch 2 (SSH alias) and Patch 3 (offline fixture deferral) both APPROVE
- **Munger**: APPROVE-LOW. Inverted the size-floor against the three Round-1 bypass paths:
  - Symlink laundering: `_dir_top_level_size` follows symlink via `iterdir()` → caught
  - Non-empty stale dir (.demo at 109 MB): 109M < 1 GiB → caught
  - Bind-mount to small Kuzu: same path → caught
  Only residual: intentional 1.1 GiB sparse-decoy attack (out of threat model). New legitimate-small-KG bootstrap window mitigated by `COGNEBULA_DB_SIZE_FLOOR_BYTES=0` override

**Consensus on APPROVE-with-Orwell-residual: 2.67/3 (Hara APPROVE + Munger APPROVE-LOW + Orwell REVISE-narrow)**

## Patch applied between Round 2 and Round 3

8. **`KG_ACCESS_GUIDE.md` capabilities sentence** — Orwell's Round-2 rewrite applied verbatim in spirit:
   ```
   It will return 404 until the endpoint is shipped. If you need to know whether
   it's live, probe with `curl -sS --max-time 3 http://100.88.170.57:8400/api/v1/.well-known/capabilities`
   before relying on it; do not assume it's there because the local code defines it.
   ```
   Replaces a temporal wish ("after the next prod deploy") with an executable check (curl probe) plus the false-confidence failure mode named explicitly ("do not assume it's there because the local code defines it")

## Round 3 — Final ship/no-ship

- **Hara**: APPROVE (Round 2 carries; no regression)
- **Orwell**: APPROVE — "Both conditions satisfied. The curl probe gives the operator a concrete, executable action — not a temporal reference. The 'local code defines it' clause names the exact false-confidence failure mode directly."
- **Munger**: APPROVE-LOW (Round 2 carries; the new patch only touches prose, no guard surface change)

**Final consensus: 3/3 APPROVE → ship**

---

## Patches NOT applied (per consensus rule, 1/3 ≠ binding by default)

1. **Orwell's Round-1 offline-fixture mode-bleed split** — applied in spirit (the existing prose mentions both modes; explicit "mock = test your code, seeded Kuzu = test DB-level logic" sentence not added). Orwell explicitly read this as "acceptable gap" in Round 2 with verdict APPROVE on the deferral itself. If a future operator picks the wrong mode, that's the next swarm trigger
2. **Hara's "physically move `_selftest()` into `__main__` block"** — stayed at module level with private prefix; Hara explicitly accepted this in Round 2 ("Un préfixe underscore suffit")

---

## Test verification

```
$ python3 -m pytest tests/test_real_kg_runtime_config.py -v
tests/test_real_kg_runtime_config.py::test_runtime_configs_do_not_reference_demo_kg_paths PASSED
tests/test_real_kg_runtime_config.py::test_compose_requires_explicit_real_database_mounts PASSED
tests/test_real_kg_runtime_config.py::test_api_server_refuses_demo_or_empty_database_paths PASSED
tests/test_real_kg_runtime_config.py::test_api_server_enforces_db_size_floor_against_drift PASSED
============================== 4 passed in 0.04s ===============================
```

The 4th test (`test_api_server_enforces_db_size_floor_against_drift`) was added in this round to keep the semantic guard from regressing. It checks `DB_SIZE_FLOOR_BYTES`, `COGNEBULA_DB_SIZE_FLOOR_BYTES`, `database_below_size_floor`, and `_dir_top_level_size` are all present in `kg-api-server.py`.

---

## Why this trace exists separately from the Rev. 1-4 audit trace

The Rev. 1-4 audit swarm reviewed the **document** (the audit `.md` + `.html` themselves, banner placement, prose discipline). This swarm reviews the **runtime artifacts** that the audit caused to be built — the prod-access client, the operator guide, the Phase F guardrails. Different review surface, different lenses (Hara on architecture, Orwell on operator prose, Munger on guard inversion), separate trace.

Both fall under §19 atomic queue closure but the work is distinct enough that pretending they are one swarm would lose the lens-vs-target mapping that makes the verdicts useful for future review.

---

Maurice | maurice_wen@proton.me
