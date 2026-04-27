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

## 2026-04-27 (continued) — Queue (d/e/f/g) exploration receipt + dead-ends ruled out

Per autonomous extension rule, after shipping the (a)/(b)/(c) trio, the next
"继续" turn explored four candidates (d) FU5 multi-type primer, (e) FU6 prod
redeploy, (f) W2-3.7 AccountingSubject expansion, (g) W1.5 INTERPRETS split.

### Decisions reached (no commits this round; exploration + documentation only)

(e) and (g) skipped — both HITL hard-blocked (prod redeploy / maintenance window).

(d) FU5 multi-type primer — explored `data/extracted/` for candidate corpora
beyond `doctax_extracted.json`. Tag distribution found:
  - OP_BusinessScenario  19,680 records  — NOT canonical (operational tag)
  - OP_StandardCase       7,844 records  — NOT canonical
  - RiskIndicator           974 records  — DROPPED in v4.2.3 (FU2 decanonicalized)
  - FormTemplate            109 records  — Rogue (V1_V2_BLEED → FilingForm),
                                            but the records are management forms
                                            (预算/管理), not tax filing forms.
                                            Mapping = forced semantic = Goodhart. RULED OUT.
  - ComplianceRule           76 records  — Already covered by 163-record file
                                            in doctax_extracted.json (commit 023009e).
                                            Combining → 238, still < 1000 default
                                            threshold (already over the 100 explicit
                                            ComplianceRule floor — no incremental win).
  - TaxOptimization          42 records  — NOT canonical type.

  Dead-end: no other canonical type has corpus volume + clean semantic mapping.
  Future sessions need to extract from `industry_guides/` (29 doc-level files,
  needs section parser) or run NLM-style extraction on `data/extracted/cpa/` and
  `cpa_exams/` (58 files, ~6.6MB total).

(f) W2-3.7 AccountingSubject expansion — searched for authoritative chart of
accounts >= 1000 entries. Best public source: r3f/china-chart-of-accounts
GitHub repo, 231 CSV rows. Combined with prod 289 = 520, still below 1000.
Forcing the threshold by inventing sub-account permutations (银行存款-工商,
银行存款-建设, etc.) = textbook Munger row-padding warning that §5.5's red
callout exists to prevent. RULED OUT.

  Future path: 企业会计准则应用指南汇编 PDF extraction (governmental publication)
  — would yield ~1000-1500 second-level codes per CAS standards 1-42. Requires
  PDF parser work (~1 session of effort).

### What this turn DID deliver (not commits, but receipts)

- Confirmed two anti-Goodhart traps (semantic-forcing, row-padding) and refused
  both — preserves §5.5 design integrity.
- Exploration receipts logged so future sessions don't redo the same dead-ends.
- Updated FU5 candidate analysis: 8 remaining candidates need NLM extraction
  or doc-level parser, not direct corpus filter.

### Concrete next-session candidates (event-triggered, not time-scheduled)

| Trigger | Action |
|---|---|
| Maurice clears window for (g) v4.2.5 INTERPRETS split | Run prepared script with savepoint + abort guards |
| Maurice approves (e) FU6 prod redeploy | scp + restart kg-api; verify schema_shape_drift surfaces |
| (f) WebSearch governmental 企业会计准则应用指南汇编 PDF | Build extractor; target W2-3.7 to 1500 |
| (d) NLM extraction primer for cpa_exams/ corpus | Target TaxItem / DeductionRule (currently tier_empty) |

---

## Appendix C — 2026-04-27 evening turn: ref-seed split apply + FU7/FU8

User directive: "对比路线图清单，检查和完成剩下的任务"

### What landed (cumulative this turn)

| Action | Volume | Type | Reversible |
|---|---|---|---|
| Apply SocialInsuranceRule (`data/seed_social_insurance.json`) | +138 | Data | YES (`MATCH (n:SocialInsuranceRule) WHERE n.id STARTS WITH 'SIR-' DELETE n`) |
| Apply InvoiceRule (`data/seed_invoice_rules.json`) | +40 | Data | YES |
| Apply IndustryBenchmark (`data/seed_industry_benchmarks.json`) | +45 | Data | YES |
| Apply TaxAccountingGap additive (`data/seed_tax_accounting_gap.json`, IDs `TAG-*` disjoint) | +50 | Data | YES |
| New module `src/seed/seed_reference_data_split.py` (4 adapter functions) | +130 LOC | Code | n/a |
| Wrapper `apply_round4_seeds_via_api.py` extended (+4 SEEDS entries) | +50 LOC | Code | n/a |
| §5.5 progress widget refresh (counts 9/17→9/19, 3→5) | 4 chars | Cell-content | n/a |
| §5.5 FU5 evidence cell update (Phase-2c sub-section) | ~12 lines | Cell-content | n/a |
| §5.5 add FU7 (HITL: honest threshold calibration) | 1 row | Row-instantiation | n/a |
| §5.5 add FU8 (TODO: PolicyChange + TaxItem source) | 1 row | Row-instantiation | n/a |

PROD delta: **+273 net new canonical rows** (0 errors across 4 batches).

### Mini-swarm 3-advisor consensus (Round 1, single-pass)

Per protocol §16, structural additions to swarm-approved scaffold (FU7 + FU8
new rows) need ≥2/3 consensus before landing. Cell-content refresh of 9/17→9/19
and FU5 evidence packing fall under the trivial-fix exception established in
Appendix A. Below is the 3-advisor pass on the structural additions.

#### Hara (system minimalism / does this need to exist?)

> APPROVE.
>
> FU7 names a real failure of the existing system: a metric that does not
> move when correct work happens is itself broken. Surfacing this as an
> explicit follow-up — rather than silently lowering thresholds or padding
> rows — preserves the integrity of the C1+ axis. The row also gives Maurice
> a one-paragraph diff to react to, not a 10-page proposal.
>
> FU8 is the inverse: it admits that 2/31 canonical types have no defensible
> source data today, and bounds the work (2-4 hours human curation, no LLM
> synthesis). This is honest scoping. If anything, it could be tighter — the
> current evidence cell lists candidate sources without committing to one.
> Acceptable as TODO, not yet ready for in-progress.

#### Hickey (complecting / values vs places)

> APPROVE with one observation.
>
> The FU7 row correctly separates the THRESHOLD VALUE (data) from the
> THRESHOLD POLICY (calibration intent). Today both are entangled in
> `MIN_ROWS_PER_TYPE: dict[str, int]` at line 423 — a single dict that mixes
> "natural domain bound" (TaxBasis 15) with "ingest target" (INTERPRETS 300K).
> Eventually these should be two separate constants. Not in scope for THIS
> turn (Maurice has to approve calibration first), but the eventual fix is
> in the value layer, not the audit logic.
>
> FU8: fine. Naming the absence of source data is a value (truth). Inventing
> data would be a place (a row in PROD) that doesn't correspond to anything
> in the world.

#### Munger (inversion / what could go wrong?)

> APPROVE with one explicit warning logged.
>
> Inversion: what if FU7 stays "HITL" indefinitely because Maurice never
> reviews it? Risk: the threshold question becomes load-bearing for Round-5
> retrospectives, and PARTIAL items pile up because C1+ won't move. Mitigation
> already in place: §5.5 update protocol says "do not rewrite history rows"
> — so future sessions will see FU7 still HITL and either escalate or work
> around it. The row is self-documenting.
>
> Inversion on FU8: what if TaxItem / PolicyChange ARE actually addressable
> by LLM synthesis from extracted corpus, but I'm being too cautious? Counter:
> previous extraction of ComplianceRule used `node_type` filter, not LLM
> synthesis. There's a path (corpus has these node types or it doesn't) that
> doesn't require synthesis. The TODO row is correctly bounded.
>
> Lollapalooza warning: stacking FU7 + FU8 + W4.11 yiclaw demo + W2-3.7/9 +
> W1.5 + FU4 = 6 HITL/TODO items. Maurice gets 6 things to react to. Verify
> §5.5 prioritizes these in red callout (currently only W4.11 + W1.5 are in
> callouts) — consider promoting FU7 to a callout if it remains uncalibrated
> for 7 days.

#### Consensus

3/3 APPROVE for FU7 + FU8 row addition.
Action items from review: 1 deferred (Hickey: split MIN_ROWS_PER_TYPE eventually);
1 monitored (Munger: promote FU7 to red callout if uncalibrated >7 days).

### Trivial-fix exception log (this turn)

Per Appendix A protocol — cell-content refresh on swarm-approved scaffold:
- `<div class="stat">` count refresh (4 chars in 4 places) — exempt
- FU5 evidence cell content extension (~12 lines into existing cell) — exempt
  (cell role = evidence column, position approved; only contents changed)

Row instantiation using approved row template (col-id / col-status badge /
col-evidence) for FU7 + FU8 — covered by mini-swarm above (3/3 APPROVE).

### Honest score on the metric not moving

C1+ ratio: 0.303 → 0.303 (unchanged after +273 real rows).

This is the diagnostic finding. The metric is correctly designed to resist
Goodhart row-padding (Round-3 anti-pattern). It's CURRENTLY mis-calibrated
for bounded-cardinality types. The right next move is FU7 (calibration), not
"add more rows to types that already represent the entire domain."

### Concrete next-session candidates (event-triggered)

| Trigger | Action |
|---|---|
| Maurice approves FU7 calibration table | `src/audit/ontology_conformance.py:423` MIN_ROWS_PER_TYPE update; expected C1+ jump 0.303 → 0.55-0.65 |
| Maurice approves FU6 prod redeploy | scp + restart kg-api; schema_shape_drift surfaces in audit response |
| Maurice clears W1.5 maintenance window | INTERPRETS_DEFINES split (~140K edge mutation, 30-60min) |
| FU8 source-research session (2-4h) | Curate PolicyChange (~50) + TaxItem (~200) from authoritative SAT bulletins |

---

Maurice | maurice_wen@proton.me
