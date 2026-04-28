# Prod KG Audit §20 Session Receipt · 2026-04-28

> **Scope**: closeout document for the §20 depth-breadth audit + Phase A
> investigation + Phase C remediation queue. Captures the session's
> non-obvious learning so the next audit session can start from
> evidence rather than rediscover it.
> **Sister docs**: `task_plan.md` §20 (atomic queue + Phase receipts),
> `HANDOFF.md` (cross-session state), individual audit deliverables under
> `outputs/audits/2026-04-28-prod-kg-*.md`.

---

## 0. Why this document exists

The session shipped 13 commits implementing audit findings, but the higher-leverage
output is the **methodology that produced them**. Specifically: direct prod
probes falsified five framing claims that would have sent execution down wrong
paths. Without this receipt, that pattern lives only in this conversation's
context — `/compact` would erase it. The receipt makes the pattern grep-able
for the next audit.

The pattern in one sentence:

> **A qualitative coverage matrix (LOW/MEDIUM/HIGH) is a hypothesis, not a
> conclusion. Probe before commit-mode runs.**

---

## 1. Five framing falsifications, chronologically

Each entry: original claim (from earlier audit material) → what the probe
showed → commit where the falsification was recorded.

### 1.1 Framing error #1 — KnowledgeFact / CPAKnowledge unreachable

| Original claim | "These tables exist but are unreachable via API" |
|---|---|
| Probe | `GET /api/v1/nodes?type=KnowledgeFact` returned a 404 with the valid_tables list (93 entries) — neither table was in it |
| Reality | The tables **do not exist**. The 404 was correct. |
| Commit | `1154578` (depth-breadth audit retract block) |
| Lesson | "Unreachable via API" can mean "API is broken" OR "the thing isn't there" — the 404 body distinguishes them, but only if you read it. |

### 1.2 Framing error #2 — LegalDocument zero content

| Original claim | "LegalDocument table has no content; major data quality issue" |
|---|---|
| Probe | `/api/v1/nodes?type=LegalDocument&limit=1` field enumeration |
| Reality | LegalDocument is **metadata-only by schema design** (name, type, issueDate, source_doc_id, ...). Content lives in LegalClause by intentional decomposition. |
| Commit | `1154578` |
| Lesson | "Empty content" might be a feature, not a bug. Read the schema before declaring data absence. |

### 1.3 Framing error #3 — KnowledgeUnit 200-char truncation cap

| Original claim | "KU content is truncated at 200 chars in storage" |
|---|---|
| Probe | `scripts/_lib/prod_kg_client.py` paged 5 × 500 KU samples (n=2,500) |
| Reality | Max content length **193 chars**. No `==200` spike. Smooth bell distribution (median 137, p99 175). 100% have `source_doc_id`; 100% have empty `extracted_by`. KUs are **chapter-level abstracts from CPA-textbook JSON ingest**, not truncated paragraphs. The "cap" is a granularity choice. |
| Commit | `eea90bc` (B5 fragmentation investigation) |
| Lesson | A truncation cap leaves a spike at the cap value (5-15% of rows landing at exactly the cap). No spike → no cap. Distribution shape is the diagnostic. |

### 1.4 Framing error #4 — B2 conflict-resolution precedence map needed

| Original claim | "V1+V2 lineage merge needs Maurice to author a precedence map per pair" (B2 design open question 3) |
|---|---|
| Probe | `prod_kg_client` ID-overlap probes for ComplianceRule/V2, FilingForm/V2, TaxIncentive/V2; field-disagreement scan on the intersecting pair |
| Reality | ComplianceRule and FilingForm have **0 ID overlap** (pure UNION). TaxIncentive has full intersection (109/109/109) BUT **fully disjoint field sets per row** — only `id` and `name` are shared, and `name` never disagrees in 50-row probe. **No precedence map needed.** Migration is 100% deterministic. |
| Commit | `0efab53` (B2 execution readiness) |
| Lesson | "What if there are conflicts" is a design fear. Probe the actual data and the question often dissolves. |

### 1.5 Framing error #5 — B4 Phase-1 LOW-cost paths feasible

| Original claim | "7 tables have LOW-cost source-attribution paths (~70% F5 closure)" (B4 design coverage matrix) |
|---|---|
| Probe | `scripts/probe_source_attribution.py` (n=200 per table) |
| Reality | **5 of 7 paths FALSIFIED**: LegalDocument `source_doc_id` empty (0/200); all 4 V2 tables `sourceUrl` empty (0/sampled). The V2 crawler pipeline declared the schema column but never populated it. Confirmed LOW: only LegalClause `CL_<doc-hash>_<clause>` and KnowledgeUnit `source_doc_id`. **Phase 1 closure: ~50% NOT ~70%.** |
| Commit | `fe04748` (probe_source_attribution + B4 doc revision) |
| Lesson | A field declared in schema is a promise the pipeline can break. Schema-coverage ≠ data-coverage. The two need separate verification. |

---

## 2. The probe-before-assertion methodology

The five falsifications above share a structural pattern that is reusable
across future audits:

### 2.1 What it is

Before committing to remediation work based on a design-time claim, run a
small read-only probe against prod (or staging) that **measures** the claim
rather than assumes it. The probe targets:

- **Existence**: does this table/column/edge actually exist?
- **Population**: is the column/field actually written to in practice?
- **Distribution**: does the data shape match the assumed shape?
- **Overlap**: do two related sets actually intersect/disjoint?

### 2.2 When it pays

The pattern paid 5 times in this session because each falsified claim sat at
the head of a planned remediation chain. Avoiding wrong-path remediation costs
30-60 minutes of probe per claim; running the wrong remediation would have
cost hours-to-days plus possible irreversible damage.

The pay-off ratio is asymmetric: probes are cheap to run, framing errors are
expensive to land on. Run the probe whenever a remediation depends on a
claim about prod data shape that hasn't been independently checked.

### 2.3 When it doesn't pay

- For trivial reversible patches (remove a 5-line clamp, rename a private
  function): probing is overhead. Just ship.
- For claims grounded in code (`grep` the source): the probe is reading the
  code; no separate prod probe needed.
- For pure-design decisions (which advisor model wins R3): probing is
  category error.

### 2.4 Probe-script library produced this session

| Script | Purpose | Pattern reusable for |
|---|---|---|
| `scripts/_lib/prod_kg_client.py` | Read-only REST client | Any prod KG read access |
| `scripts/probe_v2_edges.py` | Per-table edge enumeration via sample-and-extrapolate | Any "what's the edge scope around table X" question |
| `scripts/probe_source_attribution.py` | Schema-declared vs actually-populated rate per field | Any "is field X populated in practice" question |

These three together cover most "what's actually true in prod KG" probes the
next audit will need. Extending the pattern to a 4th script is cheaper than
rolling a new one — the import + boilerplate is already established.

---

## 3. Session commit chain (audit-relevant only)

```
8582ef3 docs(§20): Phase A4+A5 receipts + B2/B4 design proposals
eea90bc feat(audit/B5): KU fragmentation investigation — F3 framing falsified (3rd Munger validation)
846c8a3 fix(audit/B1+C1): remove stale [:500] clamp from migrate-table inner loop
f685834 fix(audit/B5): populate extracted_by on KU ingest paths (forward-looking)
0afe1a5 feat(audit/B3+C5b): schema-discipline gate at admin DDL + migrate-table endpoints
a02220b feat(audit/B4+C5c): declare Source node in canonical schema (Tier 5 Provenance)
0efab53 docs(audit/B2+C5d): B2 execution readiness — precedence map self-resolved by data
8f9bb85 docs(audit/§20): HANDOFF receipt for 5-commit Phase C atomic queue under '全部授权'
2b0b29d feat(audit/B2+C5e): probe_v2_edges.py — read-only edge rewire enumeration
1a6d323 feat(audit/B2+C5f): migrate_v1v2_unified.py — additive merge scaffold (dry-run default)
00b9a16 docs(audit/§20): HANDOFF receipt for C5e + C5f ships under '继续'
fe04748 feat(audit/B4+C5g): probe_source_attribution.py — 5th Munger validation falsifies B4 Phase-1 claim
26ca38b docs(audit/§20): HANDOFF receipt for C5g — 5th Munger validation under '继续'
```

13 commits. 8 of 9 Phase C atomic items shipped. 5 framing falsifications
landed.

---

## 4. What is NOT done — physically gated

These items remain on the queue but cannot ship without prerequisites that
this session does not control:

| Item | Blocker | What unblocks it |
|---|---|---|
| Wire `--commit` body of `migrate_v1v2_unified.py` | contabo backup window | Maurice schedules 5-60min downtime for full snapshot |
| C2 prod migration run (additive part) | Same as above | Same |
| C2 cutover (drop V1+V2 + rename) | 7-day consumer soak | Population complete + soak window starts + zero regression observed |
| C3 source_id backfill (revised: ~50% Phase 1 scope) | Source registry built first; ALTER TABLE on KnowledgeUnit + LegalClause | A separate session that authors Source registry from probe data, INSERTs into Source table, then ALTERs |
| C4 KU rename per B5 Path A | Decision is made (Path A) but rename is destructive in name space; needs coordinated rewrite of all ingest scripts simultaneously | A separate session focused on the rename + all-script sweep |
| C5 final regression + Phase C closeout | All above must complete | Sequential gate |

None of these are authorization-gated. Maurice already authorized them under
"全部授权". They are physically gated.

---

## 5. Open questions surfaced (not answered) this session

These came up during probes but didn't fit any single deliverable's scope:

- **Why is V2 sourceUrl universally empty?** The crawler pipeline that produces
  V2 rows clearly didn't write the URL. Was it a missed code path? A
  permission issue with the crawl logs? An intentional defer? The answer
  determines whether B4 Phase 3 is "fix the crawler" (1-week project) or
  "re-crawl from scratch" (multi-month project).
- **Why is LegalDocument source_doc_id empty?** Same question for a different
  pipeline. The extraction pipeline declared the field; nothing wrote it.
- **What populated `extracted_by`?** Per B5, 100% of KU rows have empty
  `extracted_by`. The C5a forward-looking patch fixes future ingests but
  doesn't backfill the 185k existing rows. Is the value derivable from other
  fields (e.g., source_doc_id namespace)? If yes, backfill is feasible; if
  no, the field stays NULL forever for legacy rows.
- **Are there other "schema-declared, never populated" fields?** This
  session's probe covered 7 fields in 7 tables. A wider sweep across all
  93 live tables × all schema fields would surface the full population
  matrix. Likely valuable; not done this session.

---

## 6. Suggested next-session start

When the next audit / migration session opens (whenever Maurice schedules):

1. **Pull `HANDOFF.md` first** (per per-initiative convention). It has the
   current state.
2. **Re-run both probes** before assuming any state from this receipt is
   still current:
   ```
   python3 scripts/probe_v2_edges.py --sample-size 20
   python3 scripts/probe_source_attribution.py --sample-size 200
   ```
   If output diverges from this receipt's numbers, prod state has drifted.
3. **Decide which physical gate to clear first**: backup window (unlocks
   C2 + C3) or KU rename coordination (unlocks C4). Independent paths.
4. **If backup window is scheduled**: implement `migrate_v1v2_unified.py`
   `--commit` body. The dry-run plan is already validated; only the
   execution layer is missing. Reuse `prod_kg_client._post()` (to be added —
   the client currently only has `_get`).
5. **If C3 path is chosen**: author `scripts/build_source_registry.py` that
   probes LegalClause + KU for distinct Source candidates, INSERTs into the
   Source node, then ALTERs the two source-bearing tables to add `source_id`.
   Follow C5g's pattern.

---

## 7. Synthesis target progress (Hickey, B2 design §8)

> Treat schema-version as a value attached to a single canonical entity,
> and make migration a pure identity-preserving function.

Progress:
- ✅ `_lineage_present STRING[]` declared as the lineage-as-value mechanism
  (B2 design + readiness).
- ✅ Probed empirically: the migration IS identity-preserving AND
  content-preserving (no row dropped, no field overwritten with different
  value, 0 real-field conflicts).
- ⏳ NOT YET RUN: the migration itself. Until ship, the synthesis is design,
  not reality.
- ⏳ NOT YET RUN: post-cutover canonical-name restoration. Currently
  staging tables would be `_experimental_*_Unified`; final canonical names
  are restored at cutover.

---

## 8. Final note on "继续" and diminishing returns

Maurice signaled "继续" four times in this session. Each signal extracted
real value through commit 12. The reason this receipt is the natural ship
for "继续 #4" is because:

- Schema/code shipping is exhausted (8 of 9 Phase C atomic items done; 9th
  needs backup window).
- The session's tacit knowledge has not yet been captured outside conversation
  context. `/compact` would erase the 5-falsification pattern.
- A receipt is durable and grep-able. It survives compaction. It tells the
  next session what to assume vs probe.

If "继续 #5" arrives: the honest answer is the marginal surface is
genuinely exhausted. The next ship requires either (a) Maurice scheduling
a contabo backup window OR (b) a strategic new task outside §20 audit. I
should not invent work to satisfy the literal "继续" signal — the
autonomous-extension rule's spirit is "execute through committed steps", not
"manufacture new steps when the queue is dry".

---

Maurice | maurice_wen@proton.me
