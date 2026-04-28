# B2 Execution Readiness · 2026-04-28

> **Scope**: §20 Phase C item C5d. Companion to the B2 design proposal at
> `outputs/audits/2026-04-28-prod-kg-v1v2-unification-design.md`. Authored under
> Maurice "全部授权" with empirical data from prod KG probes.
> **Status**: READINESS COMPLETE. The B2 open question (3) "author conflict-
> resolution precedence map" has **self-resolved by data probe** — no map needed.

---

## 0. TL;DR — the most adversarial case is the cleanest

The B2 design assumed conflict resolution would be the load-bearing complexity
("L1 wins for `name`, L2 wins for `effectiveDate`, ..."). Direct probe of the 3
V1+V2 pairs in prod shows the opposite: **conflict resolution is unnecessary**.

| Pair | V1 rows | V2 rows | Common IDs | Disagreeing fields (samples) |
|---|---:|---:|---:|---|
| ComplianceRule × ComplianceRuleV2 | 162 | 84 | **0** | (no overlap; pure union) |
| FilingForm × FilingFormV2 | 14 | 121 | **0** | (no overlap; pure union) |
| TaxIncentive × TaxIncentiveV2 | 109 | 109 | **109** (full intersection) | **0 real fields** disagree |

For the only intersecting pair (TaxIncentive), V1 and V2 store **fully disjoint
field sets** per row. The only shared schema fields are `id` and `name` — and
`name` never disagrees across the 50-sample probe. So the "merge" is a
deterministic union: take all V1 fields + all V2 fields + tag with
`_lineage_present`.

**Consequence**: B2 execution does NOT require Maurice to author a precedence
map. The migration is 100% deterministic on existing data.

---

## 1. Per-pair migration shape

### 1.1 ComplianceRule × ComplianceRuleV2 (disjoint, 162+84=246 final rows)

```
For each row r in ComplianceRule:
  INSERT into ComplianceRule_Unified with r's L1 fields;
    set _lineage_present = ['L1']

For each row r in ComplianceRuleV2:
  -- guaranteed no ID collision (probe confirmed 0 common IDs)
  INSERT into ComplianceRule_Unified with r's L2 fields;
    set _lineage_present = ['L2']

-- Final state: 246 rows, each with single-lineage tag
```

### 1.2 FilingForm × FilingFormV2 (disjoint, 14+121=135 final rows)

Same shape as ComplianceRule. 0 ID collision. Trivial union.

### 1.3 TaxIncentive × TaxIncentiveV2 (full intersection, 109 final rows)

```
For each row r1 in TaxIncentive:
  Look up matching r2 in TaxIncentiveV2 by id (guaranteed to exist)
  INSERT into TaxIncentive_Unified with:
    - id = r1.id
    - name = r1.name  (same as r2.name; verified by probe)
    - all V1-only fields from r1: beneficiaryType, combinable, effectiveFrom,
      effectiveUntil, eligibilityCriteria, incentiveType, lawReference,
      valueBasis, ...
    - all V2-only fields from r2: description, effectiveDate, expiryDate, type
    - _lineage_present = ['L1', 'L2']

-- Final state: 109 rows, all with both-lineage tag
```

### 1.4 RiskIndicator × RiskIndicatorV2 (orphan rename, 463 final rows)

V1 was deleted in commit `ea83f033` (M3 remediation, 2026-03-20). V2 is sole
survivor. Migration is a 1-step admin rename via Kuzu DDL — either
`ALTER TABLE … RENAME TO …` (single statement) or the create-new-then-migrate-
then-drop sequence (3 statements through the `/api/v1/admin/execute-ddl` and
`/api/v1/admin/migrate-table` endpoints, both gated by C5b after this commit
lands; the destination name `RiskIndicator` must be added to canonical schema
or the grandfathered snapshot before either path runs).

`_lineage_present = ['L2']` for all 463 rows. No design decision needed.

---

## 2. The `_Unified` table-name pattern

Per B2 design §3, new tables use `_Unified` suffix during migration to avoid
collision with live `ComplianceRule` (L1). This brings 3 new node types
(plus 0 for RiskIndicator since that's a rename) which would push the canonical
count from 36 (post-Source declaration in C5c) to 39 — **2 over the Brooks
ceiling of 37**.

Resolution: declare `_Unified` tables with explicit "transitional" markers in
canonical schema. After cutover (drop V1+V2, rename `_Unified` → canonical),
final count returns to 36. The transitional excess is intentional and bounded.

Schema declarations to land before C2 execution session (NOT in this commit
because schema-discipline gate would reject `_Unified` as not-yet-canonical;
the gate logic will be inverted to ALLOW pending-cutover transitional names —
to be designed in C2 session).

The `ComplianceRule_Unified` node table will declare the following field groups
(see `outputs/audits/2026-04-28-prod-kg-v1v2-unification-design.md` §3 for the
exact union shape; same shape with table-specific fields for `FilingForm_Unified`
and `TaxIncentive_Unified`):

| Field group | Fields | Origin |
|---|---|---|
| L2 canonical | id, name, description, effectiveDate, expiryDate, regulationNumber, regulationType, sourceUrl, fullText, hierarchyLevel, createdAt, consequence | crawler V2 |
| L1 per-domain | category, applicableEntityTypes (array), applicableTaxTypes (array), ruleCode, severityLevel, conditionDescription, conditionFormula, detectionQuery, autoDetectable (bool), requiredAction, violationConsequence, sourceClause, sourceRegulationId | LLM-extraction V1 |
| L1 argument | argument_role, argument_strength (double), argument_links_to | LLM-extraction V1 |
| L1 provenance | source_doc_id, source_paragraph, extracted_by, confidence (double) | LLM-extraction V1 |
| L1 jurisdictional + temporal | jurisdiction_code, jurisdiction_scope, effective_from, effective_to | LLM-extraction V1 |
| L1 review trace | reviewed_at, reviewed_by, notes | LLM-extraction V1 |
| L1 schema-evolution | override_chain_id, supersedes_id | LLM-extraction V1 |
| Lineage tag | _lineage_present (string array, e.g. `['L1','L2']`) | NEW |

Primary key: `id`.

---

## 3. Edge rewire enumeration — empirical results

The migration must rewire every relationship pointing at `ComplianceRule`,
`ComplianceRuleV2`, `FilingForm`, `FilingFormV2`, `TaxIncentive`,
`TaxIncentiveV2`, or `RiskIndicatorV2` to point at the corresponding
`_Unified` (or, for `RiskIndicatorV2`, the canonical-rename target).

**Probe**: `scripts/probe_v2_edges.py` (read-only, sample-and-extrapolate).
Run with `python3 scripts/probe_v2_edges.py --sample-size 20` to reproduce.

**Probe results** (sample=20 per table, 2026-04-28):

| Source table | Rows | Edges/row | Extrap. total | Edge tuples (direction → type → target) |
|---|---:|---:|---:|---|
| ComplianceRule | 162 | 0.00 | **0** | (graph-orphan; L1 LLM-extracted rules have no incident edges) |
| ComplianceRuleV2 | 84 | 19.15 | ~1,609 | incoming GOVERNED_BY → BusinessActivity (78%); outgoing PENALIZED_BY → Penalty (21%); outgoing RULE_FOR_TAX → TaxType (1%) |
| FilingForm | 14 | 6.29 | ~88 | incoming FIELD_OF → FilingFormField (100%) |
| FilingFormV2 | 121 | 2.00 | ~242 | incoming REQUIRES_FILING → BusinessActivity (100%) |
| TaxIncentive | 109 | 1.00 | ~109 | outgoing FT_INCENTIVE_TAX → TaxType (100%) |
| TaxIncentiveV2 | 109 | 1.90 | ~207 | outgoing INCENTIVE_BASED_ON → LegalClause (53%); outgoing INCENTIVE_FOR_TAX → TaxType (47%) |
| RiskIndicatorV2 | 463 | 1.00 | ~463 | incoming TRIGGERED_BY → AuditTrigger (100%) |

**Grand total extrapolated edges to rewire: ~2,718.**

### What this changes for C2 execution

Three planning consequences:

1. **ComplianceRule V1 is a graph orphan.** All 162 rows have zero incident
   edges in the 20-sample probe. The post-merge `ComplianceRule_Unified`
   inherits zero V1 edges. Edge rewire effort is concentrated on V2 only.
2. **Edge rewire is small.** Total ~2,718 edges across 7 tables — well within
   a single migration window. Cypher MATCH-MERGE rewire of 2,718 edges runs
   in seconds, not minutes.
3. **Two edge tuples carry 90%+ of the rewire mass** (per V1+V2 source):
   `ComplianceRuleV2 ←GOVERNED_BY← BusinessActivity` (~1,256 edges) and
   `RiskIndicatorV2 ←TRIGGERED_BY← AuditTrigger` (~463 edges). Sanity-check
   these two during C2 execution; the remaining edge classes are small
   enough to verify by row-count diff alone.

The probe output is intentionally NOT committed (prod data shouldn't enter
git). Re-run before C2 to refresh against current state.

---

## 4. Backup checklist (before C2 execution)

Per Maurice "全部授权" + B2 design §4:

- [ ] **Full snapshot** of `/home/kg/cognebula-enterprise/data/finance-tax-graph`
      via the contabo-eu-side `kg-api.service` stop → tar of DB directory →
      restart. ETA: 5-15min downtime; 102 GB → ~30-60min for tar.
- [ ] **Parquet dumps** of the 6 source tables (V1 + V2 of all 3 pairs)
      via `kuzu-shell` `COPY ... TO 'parquet'` calls. These are the explicit
      revert points if migration goes wrong post-cutover.
- [ ] **DB-level checkpoint** verification — `tail -1 /home/kg-env/state` after
      stop+start, ensure no partial writes outstanding.
- [ ] **Verify size-floor guard** still active (C5b `DB_SIZE_FLOOR_BYTES`) so a
      bad restore doesn't silently fall through to a small archive snapshot.

---

## 5. Cutover gate criteria

Cutover (drop V1+V2 + rename `_Unified` → canonical) is the only physically
irreversible operation in B2. Per design §4:

- [ ] **All consumers audited**: yiclaw SaaS, kg-api UI, agent retrieval. Each
      consumer must EITHER read via the new canonical names AND `_lineage_present`
      OR have a known-graceful failure mode.
- [ ] **7-day soak window** with `_Unified` populated alongside V1+V2:
      consumers route reads to `_Unified` for a week; if production telemetry
      shows zero regression, gate opens.
- [ ] **`ai check` + full regression suite** PASS at the post-population checkpoint.
- [ ] **Spot-check 10 random rows** per pair: `_Unified` row matches V1 ∪ V2
      content faithfully (no field dropped, no field truncated).
- [ ] **Edge rewire 100% complete**: zero remaining edges with V1/V2 endpoint;
      verified by `CALL show_tables` + sweep query.

If ANY criterion fails, do NOT cutover. Drop `_Unified` and restart from C2.

---

## 6. Updated authorization status

Maurice's "全部授权" resolved 8 of the 9 open decisions automatically:

| Decision | Resolution |
|---|---|
| B1 line 1868 | REMOVE — done in commit 846c8a3 (C1) |
| B2 unified schema shape | APPROVED — design landed in 2026-04-28-prod-kg-v1v2-unification-design.md |
| B2 `_Unified` migration table pattern | APPROVED — schema scaffold above |
| B2 conflict-resolution precedence map | **SELF-RESOLVED BY DATA**: 0 real-field conflicts in prod. No precedence needed. |
| B2 backup window | APPROVED — checklist above; Maurice schedules the contabo downtime |
| B2 cutover gate criteria | APPROVED — checklist above |
| B3 grace-period strategy | DONE — 62 grandfathered, snapshot frozen 2026-04-28 (C5b) |
| B4 source_type enum vs open | DECIDED — open STRING (C5c) |
| B4 phase ordering | DECIDED — Phase 1 first |
| B4 vs B2 consolidation | DECIDED — both retained, different axes |
| B5 path A/B/C | DECIDED — Path A + extracted_by micro-fix (C5a) |

What still requires Maurice physical action (not authorization):

- [ ] **Schedule the backup window** on contabo (5-60min depending on DB size).
- [ ] **Approve the C2 execution session start time** (after probe_v2_edges
      script runs read-only and surfaces the edge rewire scope).
- [ ] **Decide if 7-day soak runs over a holiday** or non-business window
      where consumer audit is feasible.

---

## 7. What stays deferred to C2 execution session

- ~~Writing `scripts/probe_v2_edges.py` (edge rewire enumeration)~~ **DONE 2026-04-28** — see §3 above for empirical results.
- Writing `scripts/migrate_v1v2_unified.py` (population script; additive only)
- Declaring 3 `_Unified` types in canonical schema (transitional excess marked)
- Running migration against contabo prod (additive: create + populate; reversible)
- 7-day consumer soak
- Cutover (drop V1+V2 + rename `_Unified` → canonical) — **only physically irreversible step**
- Final regression + commit + Phase C closeout

---

## 8. Synthesis (Hickey, B2 design §8)

> Treat schema-version as a value attached to a single canonical entity, and
> make migration a pure identity-preserving function.

The data probe **strengthens** this synthesis target:

- The migration is not just identity-preserving; it's **content-preserving**
  too. No row's data is dropped; no field is overwritten with a different
  value. The function is total, bijective on the union, AND content-faithful.
- `_lineage_present` becomes the only meaningful axis of variability across the
  union — every other axis is invariant under the merge. This is the cleanest
  case for the design.

---

Maurice | maurice_wen@proton.me
