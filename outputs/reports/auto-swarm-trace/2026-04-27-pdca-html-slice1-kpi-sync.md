# Auto Visual Swarm Review Trace — Slice 1 PDCA HTML KPI sync (2026-04-27)

**Deliverable**: `outputs/reports/data-quality-audit/2026-04-27-prod-data-quality-pdca.html` (KPI band line 209 sync to Sprint D nightly state)
**Trigger**: PostToolUse hook on Edit (visual deliverable detected, third swarm cycle of the day)
**Rule**: `knowledge/facts/engineering-baseline/16-auto-visual-swarm-review.md`
**Protocol**: 3 advisors × min 3 rounds × ≥2/3 consensus per patch
**Termination**: 3/3 APPROVE in Round 3

---

## Slice 1 scope (per §7 task_plan.md)

User directive: "队列全部执行" (execute the entire queue) under MVS-pattern memory rule (`feedback_minimal_viable_sprint_pattern`). Slice 1 = HTML KPI sync only — full Sprint D narrative section deferred to S7.F bundled housekeeping.

Initial change: bumped KPI line 209 `5 832 → 5 853` IDs, added inline Sprint D mutation table at lines 269-282 (between test-delta table and Run 2 h3).

---

## Round 1 — parallel dispatch (3 advisors)

### Hara R1 — REQUEST_CHANGES

Patches:
1. **Position error (high)**: Sprint D block inserted between Run 1 → Run 2 chronology. Run 2 verifies the Sprint B-era null_coverage gate; Sprint D is a later self-test infrastructure sprint. Inserting Sprint D between them implies false causal link.
2. **Density (medium)**: 1 paragraph + 4-row grid table + summary paragraph ≈ standalone section weight; should not be inline.
3. **KPI band sub-line (low)**: `~102K → ~222K assertions` jump too large without anti-anchoring.

Principle: 每个结构插入点都应问：它属于哪个叙事层级，而非仅仅"时间上发生在这之间"。

### Hickey R1 — BLOCKED

Files not found at `/Users/mauricewen/00-AI-Fleet/...` (advisor CWD). Required absolute project path. Refused to make up review without artifact.

### Munger R1 — REQUEST_CHANGES (HIGH risk)

Inversion: Reader sees `5 853 · ~222K assertions · Sprint A+B+C+D` green KPI vs `0/5 backfilled` red pill in same above-the-fold → either "report contradicts itself" (credibility kill) or "lots of work done so STRUCTURAL FAIL must be less serious" (anesthetizes board exactly when red pill needs to bite).

Patches:
1. KPI band revert: drop `~222K assertions` (mutation steps ≠ pytest assertions; category mix; Goodhart re-emergence — prior swarm killed `~102K` for same reason).
2. Verdict pill above-fold dominance check.
3. Sprint D scope disclaimer ("audit-code self-tested — no new PROD data tests").
4. Optional: red KPI for `0/5 backfilled` juxtaposition.

Aphorism: « Ne confonds jamais l'amélioration de la balance avec la perte de poids du patient. »

### R1 consensus

| Patch theme | Hara | Hickey | Munger | Decision |
|---|---|---|---|---|
| KPI band drop assertion-count Goodhart | YES | (blocked) | YES | **2/2 APPLY** |
| Sprint D block out of §D · Do | YES | (blocked) | YES (via section dédiée) | **2/2 APPLY** |
| Sprint D scope disclaimer | (compatible) | (blocked) | YES | DEFER (block removed = moot) |
| Red KPI for `0/5 backfilled` | (silent) | (blocked) | OPTIONAL | DEFER (Slice 2 cadence) |

---

## R1 → R2 — patches applied

| # | File · line | Patch |
|---|---|---|
| A | HTML line 209 | `<div class="val green">5 853</div><div class="sub">test IDs · ~222K assertions · nightly 43s · Sprint A+B+C+D</div>` → `<div class="val green">5 853</div><div class="sub">pytest IDs · nightly 43s</div>`. Aggressive cut (drop ~222K AND ~102K AND sprint suffix). |
| B | HTML lines 269-282 | Sprint D block REMOVED entirely. Restored Run 1 → code-change → test-delta (45→53) → Run 2 chronology. Sprint D narrative deferred to S7.F bundled commit. |

---

## Round 2 — verification (3 advisors, all read absolute path)

### Hara R2 — APPROVE

"Une donnée manquante est préférable à une donnée trompeuse." Drop `~102K` is not over-correction — it was a 2nd-order inferred value; current `5 853 IDs · nightly 43s` are both 1st-order verifiable measurements (pytest --collect-only output + CI log direct read). Less, more real.

### Hickey R2 — REQUEST_CHANGES (single 1-char patch)

Hammock 6/10. Single drift: HTML `nightly 43s` vs `.md ~45s`. Two facts braided in same `<div class="sub">`, one updated, one not.

Patch: `nightly 43s` → `nightly ~45s` to match .md canonical.

Principle: When two facts are braided into the same string, you must update both or neither — partial updates manufacture drift faster than no update at all.

### Munger R2 — APPROVE (LOW risk, was HIGH)

Risk reduced HIGH → LOW. `~222K`/`~102K` Goodhart eliminated. Pill at line 198 still hard-red dominant above-the-fold. MVS pattern respected. Patch 4 (red KPI juxtaposition) already partially achieved via line 207's red `0/5 backfilled · P1 unstarted` — not blocking.

Insight: 子标题不是审计报告——它是 2 秒读图的锚点。`5 853 pytest IDs · nightly 43s` 同时给了 count + wall-clock + 可重复性，三个都可被外部验证。

### R2 consensus

| Patch theme | Hara | Hickey | Munger | Decision |
|---|---|---|---|---|
| Slice 1 patches A+B accepted | YES | (implicit YES via patches accepted) | YES | **3/3 APPROVE** |
| Runtime drift `43s` vs `~45s` | (silent) | YES | (silent) | **1/3 APPLY** (single source of truth rule) |

Disposition of Hickey's drift patch: Investigated. Empirical nightly run produced `42.56s`. The `~45s` in .md was an ESTIMATE (`31s baseline + 14s heuristic`), not a measurement. Hickey's diagnosis (HTML 43s pre-dates Sprint D) was inverted — actually .md `~45s` was the back-of-envelope figure and HTML `43s` (rounded from 42.56s) was the empirical truth. **Fix direction: update .md to match empirical, not HTML to match estimate.**

---

## R2 → R3 — patches applied

| # | File · line | Patch |
|---|---|---|
| C | .md Sprint D subtotal line 201 | `13s runtime delta` → `~12s runtime delta (empirical: nightly 31s baseline → 42.56s post-D)` |
| D | .md Final test suite status line 235 | `~45s (was 31s; +14s for Sprint D mutation machines)` → `~43s (empirical 42.56s — was 31s; +~12s for Sprint D mutation machines)` |

---

## Round 3 — termination verification

### Hara R3 — APPROVE

`~43s (empirical 42.56s)` est une précision, pas une contradiction — la tilde préserve la nature approximative, et le chiffre empirique est en accord avec `nightly 43s` dans le HTML. Aucun problème structurel introduit par cette correction.

### Hickey R3 — APPROVE

Hammock Score 8/10. Drift closed. `42.56s` now stated with named provenance (`empirical`, `baseline 31s`, `+~12s delta`); previous `~45s` was a slot. Values > places.

Principle: A number without provenance is a place; a number with provenance is a value. Reports must traffic in values.

### Munger R3 — APPROVE (LOW risk)

Strict information gain. No new Goodhart loop (number is descriptive, not a target). No KPI gate, no bonus tied to it. Only watch-out: prevent `42.56s` from mutating into an SLO benchmark later. Keep `~43s` as descriptive prose.

One-liner: APPROVE — empirical correction with preserved provenance, no Goodhart loop, no scope drift.

### R3 consensus

| Patch theme | Hara | Hickey | Munger | Decision |
|---|---|---|---|---|
| Final state OK | APPROVE | APPROVE | APPROVE | **3/3 TERMINATE** |

---

## Final delta (Slice 1 ship-ready)

| File | Line | Before | After |
|---|---|---|---|
| HTML | 209 | `5 832 · test IDs · ~102K assertions · nightly 31s` | `5 853 · pytest IDs · nightly 43s` |
| HTML | 269-282 | (no Sprint D block, original Run 1 → Run 2 chronology) | (no Sprint D block, original Run 1 → Run 2 chronology) — net zero, intermediate Sprint D insertion was reverted |
| .md | 201 (P0.8b) | `13s runtime delta` | `~12s runtime delta (empirical: nightly 31s baseline → 42.56s post-D)` |
| .md | 235 (Final stats) | `~45s (was 31s; +14s for Sprint D mutation machines)` | `~43s (empirical 42.56s — was 31s; +~12s for Sprint D mutation machines)` |

## Lessons

1. **Hook fired on intermediate state** — first edit added a Sprint D inline block that violated chronology + Goodhart pattern; swarm caught both before commit. Without the hook, this would have shipped.
2. **Estimate vs measurement category error** — wrote `~45s` from arithmetic (`31+14`) when the actual nightly run had measured `42.56s`. Hickey caught the drift; root cause was using estimate as if it were measurement. Provenance annotation (`empirical 42.56s`) prevents recurrence.
3. **Sub-line minimalism wins over completeness** — prior swarm cycle's `~102K assertions` retention was a compromise; this cycle's full removal is cleaner. Munger: "子标题不是审计报告——它是 2 秒读图的锚点".

## Out of scope (deferred)

- Sprint D narrative HTML section (proper §A · Act h3 placement) → S7.F bundled commit
- Red KPI for `0/5 backfilled` juxtaposition → S7 future cadence
- Sprint E narrative (clause-axis machines + property invariants)

---

Maurice | maurice_wen@proton.me
