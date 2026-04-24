# Finance-Tax Crawler Restart Decision — Swarm Synthesis

**Swarm**: finance-tax-swarm · scope-control variant
**Date**: 2026-04-24
**Participants**: advisor-drucker (value lens) · advisor-munger (decision lens) · advisor-meadows (systems lens)
**Question**: Restart the finance-tax KB crawler NOW, or defer until Session 74 Wave 1 closes?
**Final Verdict**: **DEFER-UNTIL-WAVE1-DONE** — 3/3 unanimous, no coordination

---

## Executive Summary

- **All three advisors independently converged on DEFER.** No advisor recommended RESTART-NOW; no advisor recommended SPLIT. Consensus is structural, not a compromise.
- **The dominant failure mode is schema entropy, not data staleness.** Injecting 37 days of fresh policy data into a graph with 43 rogue node types and 46 over-ceiling types amplifies the ontology debt the C0 gate was deployed to measure.
- **The "crawler stopped" framing was a 4-bias lollapalooza**, not a real incident. The March 15-18 sprint delivered 8 high-value sites as a designed one-shot and parked — the VPS is Tailscale-active, not crashed.
- **Primary action: install P0 whitelist guard FIRST.** This is Leverage Point #8 (balancing feedback loop strength) per Meadows. Fresh data is Leverage Point #12 (a parameter). Acting at #12 before #8 is the classical low-leverage trap.
- **Two cheap mitigations neutralize both top-risks**: (a) a single manual `flk.npc.gov.cn` diff-scan for 2026-03-18 → 2026-04-24 (covers Drucker + Munger risk of a material post-snapshot policy change); (b) a 5-line SSH restore runbook for `do-us-crawl` (covers Meadows risk of the VPS drifting unrecoverable).

---

## Current State Snapshot (facts, not opinions)

| Dimension | Value |
|---|---|
| Latest `data/raw/` directory | `2026-03-18` (37 days old) |
| Mar 15-18 crawl scope | chinatax.gov.cn full-text · 12366 QA · flk.npc.gov.cn national law DB · 7 provincial tax bureaus · HS codes · CICPA/CCTAA/ASBE accounting standards · chinaacc |
| KG state | 547,761 nodes / 1,302,476 edges / 83 live node types vs 35 canonical v4.2 |
| Wave 1 C0 verdict (post-deploy) | `composite_gate=FAIL` · coverage 0.306 · 43 domain rogue types · 46 over-ceiling |
| Wave 1 remaining (7 items) | P0 whitelist guard install · D1 prod Kuzu snapshot · B3/B4/B0/B2/H1/H2 schema migrations |
| VPS `do-us-crawl` (100.75.77.112) | Tailscale-active (direct IP 165.232.147.244:41641, ping 270ms); SSH:22 closed |
| Audit 2026-04-21 Must-Fix #2 | "12366 manual labeling" — needs legal counsel, NOT fresh data |
| Audit 2026-04-21 Must-Fix #4 | "Kuzu perf benchmark" — needs prod slice, NOT fresh data |

---

## Synthesis (MECE-merged across 3 advisors)

### 1. Customer Value Axis (Drucker primary, Munger supporting)

Tax compliance customers value **correct** answers, not **fresh** answers. The KG currently produces wrong answers on ontology-level queries because 43 non-canonical node types distort relationship lookups. A 37-day stale but schema-correct graph serves customers better than a 0-day fresh graph running over broken types. Tax law does not change daily; quarterly policy cycles and annual legislative sessions are the real clock.

### 2. Opportunity Cost Axis (Munger primary, Drucker supporting)

Wave 1 has a defined exit gate (`composite_gate=PASS`), a known 7-item critical path, and all items are executable with existing data. Restarting the crawler inserts a 3-5 day side quest (VPS repair + crawl + rsync + inject) that has ZERO unblocking effect on either Must-Fix #2 (legal) or Must-Fix #4 (prod slice). It converts one completable sprint into two half-finished workstreams.

### 3. Systems / Leverage Axis (Meadows primary, Munger supporting)

The schema-crawl relationship is a reinforcing loop: crawl → inject → rogue types multiply → gate deepens. The balancing loop (P0 whitelist guard) is designed but not yet installed. Running the reinforcing loop (restart crawler) before the balancing loop (P0 install) accelerates entropy. P0 is a Level-8 structural intervention; fresh data is a Level-12 parameter tweak. Ordering reversed = classical low-leverage trap.

### 4. Bias Audit (Munger only, not flagged by others)

The user's "是不是停了" (is it stopped?) framing layered 4 biases:

- **Loss aversion**: 37 days of "missed" data feels like loss
- **Availability bias**: recent Boss-pipeline running process made "live crawlers" salient
- **Sunk cost**: VPS still paid for, feels wasteful dormant
- **Action bias**: "doing something" feels productive

None of these survive first-principles examination: the March sprint **delivered** (8 sites covered end-to-end) and **parked** (designed behavior). There is no incident.

---

## Per-Advisor Verbatim Evidence

### advisor-drucker (customer value lens)

> Customer: Tax accounting firms and 12366 hotline operators making compliance decisions on specific tax questions — they need *accurate* answers, not *recent* ones. Value Created: A structurally sound ontology that returns correct, non-contradictory answers. A graph with 43 rogue types and composite_gate=FAIL poisons every query result regardless of data freshness. Abandon: The intuition that "newer data = more value."

**Verdict**: DEFER-UNTIL-WAVE1-DONE

**Reasoning**:
- Customer's core failure mode is a wrong answer on compliance, not a slightly stale one. A FAIL-gated graph with 43 rogue types actively produces wrong answers today; 37-day-old correct answers are safer than fresh data injected into a broken schema.
- Must-Fix #2 and #4 require legal counsel and a prod slice — neither unblocks by restarting the crawler.
- Wave 1 has 7 concrete items with a defined exit gate. Splitting attention converts a completable sprint into two half-finished workstreams.

**Top Risk**: Tax policy changes enacted after March 18 are genuinely material for compliance queries — if a major VAT or CIT rule changed in 37 days, deferral is wrong.

### advisor-munger (decision lens)

**Verdict**: DEFER-UNTIL-WAVE1-DONE

**Reasoning**:
- Inversion (restart now): VPS repair + crawl + rsync + inject is a 3-5 day side quest that stalls a JUST-DEPLOYED composite gate mid-flight. Injecting MORE nodes into an un-reconciled schema makes 0.306 coverage worse, not better. Pouring water into a leaking bucket while holding the patch in the other hand.
- Opportunity cost: Wave 1 B-batch migrations are the ONLY path to prod quality; Must-Fix #2 needs a lawyer and #4 needs a prod slice — neither unlocked by fresh crawl. Zero cascade benefit, full cascade cost.
- Lollapalooza detected: "37 days stopped" triggers loss-aversion + availability bias + sunk-cost + action bias. Four biases stacking on a non-problem — the March sprint DELIVERED, it didn't break. Tax policy cycles are quarterly, not daily.

**Top Risk**: A Q2 policy shock (e.g., 增值税 rate change) lands before Wave 1 closes and the KG answers with stale March law — mitigated by a single manual `flk.npc.gov.cn` diff check, not a full crawler restart.

### advisor-meadows (systems lens)

> Stocks: Schema integrity (contaminated — 43 rogue types, 46 over-ceiling). Flows: Ingest rate flowing IN; cleanup rate NOT YET flowing. Dominant Loop: REINFORCING (destructive) — crawl → inject → rogue types multiply → composite_gate FAIL deepens. Delay Risk: P0 absent = zero signal lag; dirty types enter graph silently. Leverage Point: P0 = #8 (balancing loop strength). Fresh data = #12 (parameter).

**Verdict**: DEFER-UNTIL-WAVE1-DONE

**Reasoning**:
- Dominant loop is reinforcing and destructive: without P0 installed, every new crawl cycle injects directly into a dirty schema — blocker compounds, not resolves.
- Must-Fix #2 (legal counsel) and #4 (prod slice) require zero fresh data; the 37-day gap causes no leverage loss on the critical path.
- Fresh data is Leverage Point #12 (parameter); P0 guard is Leverage Point #8 (balancing feedback loop). Intervening at #8 first is the structurally correct order; reversing it accelerates schema entropy.

**Top Risk**: Wave 1 finishes but the `do-us-crawl` infrastructure (SSH:22 blocked) has drifted further into an unrecoverable state, making restart harder than a one-day fix once the gate is ready.

---

## Decision — Recommended Path (executable)

| Priority | Action | Why | Trigger |
|---|---|---|---|
| P0 (now) | Install `ontology-whitelist-guard.py` as `.git/hooks/pre-commit` | Meadows #8 balancing loop — must precede any data ingest | Local `ln -s`, 1 command, no HITL |
| P1 (now) | Write this swarm report (MD + HTML) + memory log | 2份制 + auditable trace | Automatic |
| P2 (next cycle) | Manual `flk.npc.gov.cn` 2026-03-18 → 2026-04-24 diff scan | Neutralizes Drucker + Munger top-risks with 30-minute browser task vs. 3-day crawler rebuild | Manual when Wave 1 passes C0 gate mid-B-batch |
| P3 (deferred) | VPS SSH restore runbook for `do-us-crawl` | Meadows top-risk mitigation — prevents infrastructure drift | 5-line doc, next time Maurice touches VPS fleet |
| P4 (deferred) | Crawler restart (full or incremental) | Unblocked only AFTER `composite_gate=PASS` on Wave 1 | Post-Wave 1 explicit trigger |

---

## Discarded Alternatives (what was NOT done)

- **RESTART-NOW**: zero advisor support, would accelerate schema entropy per Meadows
- **SPLIT (narrow-scope daily incremental)**: would still trigger reinforcing loop without P0, rejected by Meadows
- **5-advisor swarm**: marginal info gain below 3-advisor baseline for a scope-control decision
- **Single-operator decision**: user explicitly requested swarm treatment; single-operator would violate 蜂群执行 directive

---

## Follow-up Ledger (to `state/memory/2026-04-24.md`)

One-line swarm trace entry appended per swarm output contract. Cross-reference: Wave 1 C0 deploy receipt `81ceef9` — the crawler deferral preserves the gate that commit delivered.

---

Maurice | maurice_wen@proton.me
CogNebula Enterprise — finance-tax-swarm · crawler-restart decision synthesis — 2026-04-24
