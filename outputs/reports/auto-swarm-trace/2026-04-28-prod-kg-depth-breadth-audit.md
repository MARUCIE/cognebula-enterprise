# Auto-Swarm Trace · Prod KG Depth × Breadth Audit · 2026-04-28

> **Targets**: `outputs/audits/2026-04-28-prod-kg-depth-breadth-audit.{md,html}` (companion 2份制 pair).
> **Outcome**: 3/3 APPROVE in both content R3 AND visual R3 → ship.
> **Distinguishing feature**: this audit ran TWO nested swarms on the same deliverable — content swarm on findings/framing (Meadows/Hickey/Munger × 3 rounds) and visual swarm on rendered HTML (Hara/Jobs/Orwell × 3 rounds). Six unique advisors, no lens overlap.

---

## Why two swarms instead of one

The deliverable has two distinct review surfaces:

1. **Audit content** — leverage logic, complecting hypothesis, falsifiable framing, inversion checklist. Lens needed: systems thinking + architecture + risk inversion.
2. **Rendered artifact** — typography hierarchy, color discipline, prose clarity in rendered Chinese, information density. Lens needed: structural minimalism + design excellence + clarity-of-language.

Running one combined swarm would have collapsed the two surfaces and either (a) produced shallow verdicts on both or (b) under-served whichever surface the chosen advisor trio wasn't well-matched to. The two-swarm split is per the auto-visual-swarm-review rule (`16-auto-visual-swarm-review.md`) and the memory `feedback_auto_swarm_review`.

---

## Swarm A — Content (Meadows / Hickey / Munger)

### Round 1 — Verdicts

- **Meadows**: REVISE. Leverage ranking — source-attribution gap (#1, LP#6) and over_ceiling drift (#2, LP#5) ranked highest; KU/LC truncation as parameters (#5-6). Identified the upstream broken balancing loop: ingest pipeline lacks a schema-validation feedback gate. Single high-leverage intervention: schema validation + source_id + content cap as gate parameters.
- **Hickey**: REVISE. Six bugs are 3 complections — content-role split (preview/summary/body conflated), schema-as-value drift, identity-vs-occurrence (no canonical anchor for repeated ingestions). Principle: "A truncation cap is the schema confessing it doesn't know what the field is for."
- **Munger**: REVISE, **HIGH RISK** confirmation bias warning. "You measured the API surface, not the data." 200/368,910 = 0.054% sample insufficient for 369K-node action. Demanded a falsifying probe (direct DB query bypassing API + git log on 500-ceiling design intent) before any remediation begins.

### Falsification probe (between R1 and R2)

Direct schema introspection via `/api/v1/nodes` 404 response (returns full valid_tables list) + code grep on `kg-api-server.py` produced these corrections:

| R1 finding | Falsification result |
|---|---|
| KnowledgeFact / CPAKnowledge unreachable | Tables **do not exist** in 93-table valid_tables list. HTTP 404 was correct. **Drop finding.** |
| LegalDocument zero content | LegalDocument is **metadata-only by schema design** (fields: name/type/issueDate/source_doc_id/...). Content lives in LegalClause by intentional decomposition. **Drop finding.** |
| LegalClause 500-cap | Root cause located: `/api/v1/admin/migrate-table` line 1708 `props[field] = str(val)[:500]`. **Specific fix, not a 369K-node project.** |
| KU 200-cap | Confirmed at storage layer (`/api/v1/nodes` does NOT truncate). Genuine fragmentation. |
| 56 over-ceiling | Confirmed via 93-31 = 62 (close to claimed 56, order-of-magnitude consistent). |
| Source attribution broken | Confirmed; only LegalClause uses `CL_*` semantic IDs. |
| **NEW** | 5+ V2 tables (TaxIncentiveV2, ComplianceRuleV2, FilingFormV2, RiskIndicatorV2, ...) — Hickey's identity-vs-occurrence at TABLE level. |

Munger's HIGH-RISK warning was vindicated: 2 of 6 R1 findings were API↔storage confusion; 1 had a precise 5-line root cause not requiring a re-ingest project.

### Round 2 — Verdicts (with corrected framing)

- **Meadows**: REVISE on R1-as-shipped. Reranked: V2 proliferation now #1 (LP#4 system structure); migrate-table line 1708 #2 (LP#10 stock-flow, separate intervention from generic ingest gate); source-attribution drops to #3-4. Two findings dropped per falsification.
- **Hickey**: REVISE. Identity-vs-occurrence at TABLE level promoted to #1 complection. Migration-mechanism braided with data semantics (line 1708) is NEW #2 axis: "the migrator has opinions; opinions belong in schemas, not in transport." Content-role split WITHDRAWN (LegalDocument-as-metadata is correct values-vs-places).
- **Munger**: APPROVE-MEDIUM, MEDIUM risk. R1 vindication accepted, but added pendulum-bias warnings: (a) don't under-weight 3 surviving findings; (b) Chesterton's fence on line 1708 — find WHY before removing the clamp; (c) V1+V2 separation has legitimate cases (live downstream consumers / semantic divergence / experimental rollback).

**Consensus**: 2/3 REVISE on R1-as-shipped + 1/3 APPROVE-MEDIUM on R2-corrected framing → write the corrected deliverable.

### Round 3 — Final ship verdict on .md deliverable

- **Meadows**: APPROVE — leverage ranking captured accurately, F1 at top, next-round work actionable per finding.
- **Hickey**: APPROVE — content-role-split withdrawal documented, migration-mechanism as standalone axis, 3-axis decomposition reflected in Complection map. Notes the synthesis sentence ("schema-version as value + migration as identity-preserving function") could be made more explicit but flags this as next-round-queue concern, not blocker.
- **Munger**: APPROVE-LOW — Chesterton's fence on line 1708 explicit with 4 falsifiable hypotheses; V1+V2 caveat present with 3 legitimate-separation conditions; inversion checklist authentic (4/5 items specific).

**Final consensus**: 3/3 APPROVE on content → write the HTML companion + run visual swarm.

### Patch applied between Content R3 and Visual R1

Per Hickey's R3 hint (non-blocker), added explicit synthesis-target section to the .md before the "What this audit does NOT do" block:

> Treat schema-version as a value attached to a single canonical entity, and make migration a pure identity-preserving function.

This binds F1 (V2 consolidation) and F2 (line 1708 de-truncation) into one design intent rather than two parallel cleanup streams.

---

## Swarm B — Visual (Hara / Jobs / Orwell)

### Round 1 — Verdicts

- **Hara**: REVISE. 4 patches: [HIGH] delete `.lp` accent badges from h3 headers (LP info already in table); [HIGH] remove dead CSS (`.scope-block`, `pre`); [MEDIUM] change `th` background from `--rule` near-black to neutral grey to avoid third color register; [LOW] increase blockquote margin-top to 32px when before/after h2.
- **Jobs**: REVISE. Single highest-impact: move retract block above the fold (immediately after executive summary, before methodology). The retract block is the document's intellectual-honesty climax and should land in the 30-second scan window. Praises H1 ("当事实仍在迁移管线里被截断") as earned. Also noted leverage-ranking table redundancy (deferred — see R2).
- **Orwell**: REVISE. 3 patches: rewrite F2 worst sentence ("过去经此代码路径的迁移把 ≤500 字的内容冻结到了 canonical store 里" — translation-ese); fix swarm-trace passive-stack ("使...被撤回"); add diagnostic sentence to thin F5 section.

### Patches applied between Visual R1 and Visual R2

| # | Patch | Source |
|---|---|---|
| V1 | Remove `<span class="lp">` badges from all 5 h3 headers | Hara HIGH |
| V2 | Remove `.scope-block` and `pre` from CSS (dead code) | Hara HIGH |
| V3 | Change `th` background from `var(--rule)` to `var(--ink-soft)` | Hara MEDIUM |
| V4 | Increase blockquote margin from 18px to 32px | Hara LOW |
| V5 | Verify retract block already sits between summary and methodology; add italic framing line naming its narrative role | Jobs HIGHEST-IMPACT |
| V6 | Rewrite F2 sentence: "所有经此路径的迁移，数据已被截至 500 字写死在库里" | Orwell P1 |
| V7 | Add F5 diagnostic sentence on consequence (downstream agent quoting failure) | Orwell P3 |
| V8 | Rewrite swarm-trace passive: "反证探针撤回了 6 条 finding 中的 2 条 framing error、..." (initial fix, refined in R2→R3) | Orwell P2 |
| **Skipped** | Leverage-ranking table cut (Jobs only, 1/3) — kept because table earns its place by collapsing 5 prose sections into 30-second scan | — |

### Round 2 — Verdicts

- **Hara**: APPROVE — all 4 structural patches landed cleanly.
- **Jobs**: APPROVE — retract block in correct position with explicit narrative-role framing; accepts the rationale for keeping the leverage table ("The Economist doesn't cut tables that do real work").
- **Orwell**: REVISE on V8 only — perceived passive-stack remained ("2 条 framing error 撤回了" agentless reading). Other 2 prose patches APPROVE.

### Patch applied between Visual R2 and Visual R3

V8 refinement: subject `反证探针` moved to lead the sentence so the reader cannot mis-parse it as a temporal complement. Final form: "反证探针在 R1 与 R2 之间撤回了 6 条 finding 中的 2 条 framing error、把 1 条根因定位到 line 1708、并新发现 1 条（V2 增殖）晋升首位。"

### Round 3 — Final ship verdict

- **Hara**: APPROVE — no structural noise introduced, sentence-order tweak doesn't change architecture.
- **Jobs**: APPROVE (Experience Score 9/10) — active voice sharpens the trace.
- **Orwell**: APPROVE (Clarity Score 9/10) — `反证探针` holds subject position; four verbs chain cleanly; "no passive fog."

**Final consensus**: 3/3 APPROVE on visual → ship the .html.

---

## Patches NOT applied (single-advisor, non-binding)

1. **Jobs's Round 1 cut-the-leverage-ranking-table** — Jobs himself accepted the rationale in R2 ("you are right to keep it"); the table collapses 5 prose sections into a scan-friendly view.
2. **Hickey's R3 explicit synthesis sentence "lives across F1+F2 instead of one synthesized line"** — partially addressed by adding a "Synthesis target for next-round queue" mini-section to the .md (not to the .html, where space is tighter and the same content lives in the blockquote).

---

## Falsifying probes used (audit's own evidence chain)

```
SAMPLE-200/api/v1/nodes        →  per-type content length distribution
GET /api/v1/nodes?type=<bad>   →  schema-validity check via 404 valid_tables list
GET /api/v1/nodes?type=LegalDocument&limit=1  →  field enumeration on representative node
SSH grep kg-api-server.py      →  truncation logic localization (line 1123/1140/1708)
SSH ls /home/kg-env/bin/       →  kuzu venv discovery (lock-conflict noted)
```

This evidence chain is what made 2 framing errors falsifiable rather than waving away with "we measured 200 nodes."

---

## What this trace establishes for the next audit

- **Two-swarm pattern is repeatable**: separate content from rendering; pick non-overlapping lens trios per surface.
- **Falsifying probe is non-optional when Munger flags HIGH-risk confirmation bias** — it's the difference between a 5-line fix and a phantom 3-week project.
- **1/3 patches can land if the reasoning is good and cost is low**, but they should NOT bind. The Jobs-on-table case (1/3 that was correctly skipped after R2 self-revision) and the Orwell-on-passive-stack case (1/3 that was applied because the cost was one sentence) show both directions of this heuristic in action.

---

Maurice | maurice_wen@proton.me
