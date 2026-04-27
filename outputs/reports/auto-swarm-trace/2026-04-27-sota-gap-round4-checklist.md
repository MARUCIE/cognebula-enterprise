# Auto Visual Swarm Review Trace — SOTA Gap Round-4 Checklist Insertion

**Deliverable**: `outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.html` §5.5 原子任务清单
**Trigger**: PostToolUse hook on Edit (visual deliverable detected)
**Rule**: `knowledge/facts/engineering-baseline/16-auto-visual-swarm-review.md`
**Min rounds**: 3 · **Consensus threshold**: ≥2/3 per patch · **Termination**: all APPROVE in round ≥3 or 5-round escalation

---

## Edit Summary (pre-swarm baseline)

Added new §5.5 atomic task checklist between §5 (timeline) and §6 (no-go list). Components:
- 120 lines of CSS (status badges, progress widget, phase rows)
- ~180 lines of HTML markup with 17 tracked items (11 originals W1.x/W2-3.x/W4.x + 6 executed-discovery FUs)
- Initial framing as "Living Document" with 5-stat-card row + 4-segment color bar

---

## Round 1 (3 advisors parallel · all REVISE)

### Hara — structural minimalism

| Axis | Verdict | Note |
|---|---|---|
| §5.5 vs §5 merge | KEEP separate | semantic split (plan axis vs execution axis) |
| 5-status taxonomy | KEEP all 5 | HITL ≠ HELD; collapsing loses routing info |
| Color bar | DELETE | shadow of stat cards, zero info increment |
| Phase row separators | KEEP | navigation anchors in 17-row table |
| "Living Document" | DELETE/downgrade | self-aggrandizement when callout already explains |

**Verdict**: REVISE · Top-1 patch: delete `.bar` div (lines 717-725)

### Jobs — UX experience

| Axis | Verdict | Note |
|---|---|---|
| 3-second answer | FIX | flat hierarchy; HELD blocker buried at row 5 |
| Status badge contrast | KEEP | icons disambiguate close pairs |
| Evidence column SHA-first | FIX | developer-only; should lead with outcome |
| Update protocol callout | DELETE | author process docs, not reader info |
| Numerical proof format | KEEP | "289/1500 (+130/+1341)" honest and concrete |

**Verdict**: REVISE_LIGHT · Top-1 patch: pin W1.5/FU1 blocker callout above table

### Munger — anti-Goodhart inversion

| Axis | Verdict | Note |
|---|---|---|
| 5/11 stat | SUSCEPTIBLE | 11 small enough that splitting moves needle ~9pp |
| 289/1500 ratio | GAMED-ALREADY-RISK | row count is the disease C1 had |
| HELD vs TODO | SUSCEPTIBLE | HELD has no expiry; "waiting for window" is comfort label |
| FU1-FU6 separated from W1-W4 | GAMED-ALREADY | "+6" sits beside denominator instead of entering it |
| "Living document" | SUSCEPTIBLE | three-phrase combo excuses never declaring DONE |

**Verdict**: REVISE_LIGHT · Top-1 patch: replace 5-stat row with single 5/17 honest fraction + pin W4.11 in red as the only non-fakeable outcome

---

## Round 1 Consensus Synthesis

Cross-tabulating patches by ≥2/3 advisor support:

| Patch | Hara | Jobs | Munger | Consensus | Action |
|---|---|---|---|---|---|
| Delete .bar color segment | ✓ | — | — | 1/3 | NO APPLY |
| Surface HELD blocker above table | — | ✓ | — | 1/3 | (covered by next) |
| Demote SHA in evidence column | — | ✓ | — | 1/3 | NO APPLY |
| Delete update protocol callout | — | ✓ | — | 1/3 | NO APPLY |
| Replace 5-stat with 5/17 + pin W4.11 | — | ✓ semantic | ✓ | **2/3** | **APPLY** |
| Downgrade "Living Document" framing | ✓ | — | ✓ | **2/3** | **APPLY** |

Note: Jobs' "surface blocker" + Munger's "make W4.11 dominate" = same semantic patch (break flat hierarchy). Counted as single consensus patch.

---

## Patches Applied between Round 1 → Round 2

**Patch A — Title/framing minimalism (Hara + Munger consensus)**:
- Title: `5.5 · 原子任务清单 · Living Document` → `5.5 · 原子任务清单`
- Removed `.living-note` callout entirely

**Patch B — Hierarchy break + non-fakeable metric domination (Jobs + Munger consensus)**:
- Replaced 5-stat-card row with:
  - Red callout (top): "唯一不可伪造的度量 · W4.11 yiclaw 端到端 VAT 申报演示：NOT STARTED" + Drucker quote
  - Blue callout (below): "当前唯一阻塞 · W1.5 / FU1 INTERPRETS_DEFINES 拆分"
  - Smaller 4-stat row below callouts: 5/17 (combining originals + FUs) · 3 PARTIAL · 2 HELD/HITL · 3 TODO

NOT applied (insufficient consensus): delete .bar color segment, demote SHA, delete update protocol callout.

---

## Round 2 (re-review by same 3 advisors via SendMessage)

### Hara

**Verdict**: APPROVE (conditional)
- Title minimalism correct
- New stat composition honest, no internal redundancy
- Re-flagged: `.bar` color segment now MORE redundant given callouts carry visual weight; the parenthetical "(11 原计划 + 6 执行中发现)" is now derivable from callouts and could be deleted

### Jobs

**Verdict**: REVISE_LIGHT
- Stacked red+blue callouts achieve 3-second test (barely)
- Drucker quote line "其余 16 项原子任务的全部进度都不能替代这一项" reads as preachy; data already speaks ("NOT STARTED · 前置条件差 1,000+ 行")
- Blue callout's `<strong>` should be reduced to widen visual gap between red (priority) and blue (context)

### Munger

**Verdict**: APPROVE
- Reframe worked — eye lands on red first, FUs entered denominator
- PARTIAL=3 still gameable via row-padding, HELD/HITL=2 still has comfort-label risk
- NEW concern: red callout itself becomes phrase-armor by Day 30 → suggests dynamic countdown ("距 5/27 还剩 N 天")

---

## Round 2 Consensus Check

State: 2 APPROVE (Hara, Munger) + 1 REVISE_LIGHT (Jobs)

New patches surfaced:

| Patch | Hara | Jobs | Munger | Consensus | Round 3 vote needed |
|---|---|---|---|---|---|
| Delete .bar color segment | ✓ (re-flag) | — | — | 1/3 | YES |
| Delete parenthetical "(11 原计划 + 6 执行中发现)" | ✓ | — | — | 1/3 | YES |
| Delete Drucker quote line "preachy" | — | ✓ | — | 1/3 | YES |
| Reduce blue callout `<strong>` | — | ✓ | — | 1/3 | YES |
| Add dynamic countdown to W4.11 | — | — | ✓ | 1/3 | YES |

No 2/3 consensus → no patches applied between Round 2 → Round 3.
Round 3 dispatched as **focused convergence round**: explicit ✓/✗ vote on each minority suggestion + final APPROVE verdict.

---

## Round 3 (focused convergence vote)

Vote tally on the 5 minority patches surfaced in Round 2:

| Patch | Hara | Jobs | Munger | Total ✓ | Apply? |
|---|---|---|---|---|---|
| (A) Delete .bar color CSS | ✓ | ✗ | ✓ | **2/3** | **APPLY** |
| (B) Delete parenthetical "(11 原计划 + 6 执行中发现)" | ✗ | ✗ | ✗ | 0/3 | NO |
| (C) Delete Drucker quote line "其余 16 项..." | ✓ | ✓ | ✗ | **2/3** | **APPLY** |
| (D) Reduce blue callout `<strong>` to non-bold | ✓ | ✓ | ✓ | **3/3** | **APPLY** |
| (E) Add dynamic countdown "距 5/27 还剩 N 天" | ✗ | ✗ | ✓ | 1/3 | NO |

Final verdicts:
- **Hara**: APPROVE (conditional on A/C/D landing)
- **Jobs**: APPROVE (conditional on C+D landing; A is dead-CSS cleanup, neutral)
- **Munger**: APPROVE (anti-Goodhart concerns logged for future iteration; 3/5 patches improve signal-to-armor ratio)

### Notable Round 3 reasoning

**Hara reversed on patch B**: own original suggestion withdrawn after recognizing the parenthetical "(11 原计划 + 6 执行中发现)" is "white-space-internal substantive info, not noise" — explains denominator composition.

**Jobs distinct take on patch A**: pointed out the `.bar` CSS exists but no corresponding `<div class="bar">` markup appears in §5.5 (it was removed during Round 1→Round 2 patch B widget rewrite). So A is dead-CSS cleanup, not visible visual change. Voted DON'T APPLY because it doesn't affect §5.5 user experience — but doesn't object to cleanup happening separately.

**Munger held on patch C** (kept the Drucker line as enforcement against "16/17 完成，凑合交付" rationalization). Lost 1-2 to Hara+Jobs. Documented as design dissent.

**Munger's E patch** (countdown) lost on grounds Hara+Jobs both raised: dynamic JS in static archive HTML degrades to misinformation post-archival. The right venue for the Day-30 anti-armor mechanism is `tests/test_kg_gate.py` assertion, not a render-time timer.

---

## Patches Applied between Round 2 → Round 3 → Final

**Patch A (Hara+Munger)**: Removed dead `.checklist-progress .bar` CSS rule block (lines 717-725). Eliminates color-segment styling no longer referenced by markup.

**Patch C (Hara+Jobs)**: Removed sentence "其余 16 项原子任务的全部进度都不能替代这一项" from the red W4.11 callout. Drucker italic at the end now carries the punch alone.

**Patch D (Hara+Jobs+Munger, unanimous)**: Removed `<strong>` wrap from the blue W1.5 callout opener. The blue callout now reads as plain prose with the colored left-border doing the visual labeling, restoring the red>blue severity hierarchy.

NOT applied (failed 2/3): patch B (parenthetical kept as anti-Goodhart receipt), patch E (countdown — wrong venue, belongs in gate test).

---

## Final State (Round 3 close)

**Consensus achieved**: 3/3 APPROVE in Round 3 (conditional patches now landed).

**Termination criterion satisfied**: "all APPROVE in round ≥3" met at end of Round 3 + post-application.

**Total rounds**: 3 (minimum threshold met).

**Total patches applied across all rounds**:
- Round 1→2: 2 patches (title minimalism, hierarchy break + non-fakeable metric domination)
- Round 2→3 (final): 3 patches (dead CSS cleanup, Drucker line removal, blue callout strong removal)
- Total: 5 patches applied, 6 patches rejected for insufficient consensus

**Carried forward as design dissent**:
- Munger's countdown idea — re-routed to gate-test layer (test_w4_11_yiclaw_demo_progress with date-aware assertion). Tracked as new FU7 candidate for the §5.5 list itself.

**Carried forward as design risk acknowledged**:
- PARTIAL row-count gameability (W2-3.7/8/9) and HELD comfort-label risk (W1.5/FU4) — neither swarm round produced a 2/3 fix. Mitigation lives in the W4.11 outcome metric being non-fakeable.

---

## Post-Approval Updates (data refresh, no structural change)

Per the §5.5 design contract ("更新协议" callout) and per the trivial-fix exception
in `16-auto-visual-swarm-review.md`, atomic-item progress refreshes on the
swarm-approved scaffold do NOT trigger new swarm rounds. The criterion is
**structural visual change vs data refresh**, not "file was edited".

### 2026-04-27 (this session, post-Round-3-close)

- **W2-3.8 BusinessActivity row refresh**: 502 → 549 (+47).
  - seed/seed_business_activity_gbt4754.py phase-1b: +48 SME-relevant 3-digit
    groups across 10 previously-uncovered divisions (02 林业 / 04 渔业 /
    16 烟草 / 19 皮革 / 20 木材 / 21 家具 / 22 造纸 / 23 印刷 /
    30 非金属矿物 / 33 金属制品).
  - Applied via `scripts/apply_round4_seeds_via_api.py --only BusinessActivity`:
    47 added, 298 dup_skipped, 0 errors, 9.5s elapsed.
  - Status remains PARTIAL (gap to 1000 threshold: 451 rows).
  - No structural change to checklist; only cell content `<td class="col-evidence">`
    updated. Falls under trivial-fix exception.

### Future-update protocol carried forward

- Cell-content refresh (status flip, count update, evidence cell update) → no swarm
- Status badge color/label change → no swarm (uses approved palette)
- Adding a new row to the table → no swarm (uses approved row template)
- Adding a NEW phase-row block (e.g., "Week 5") → swarm Round 1 only (single round)
- Removing/restructuring callouts, modifying CSS classes, changing table columns → full ≥3-round swarm

This protocol prevents hook-tax inflation while preserving structural review discipline.

---

Maurice | maurice_wen@proton.me
