// ============================================================================
// Ontology v4.2.4 — Round-4 deletion: 3 schema-overreach stubs
// ============================================================================
//
// Per `outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md`
// §3.1 (Hara) — admit schema overreach, REMOVE empty stubs (do not keep
// "deferred 90-day filling" on types whose existence cannot be justified).
//
// Targets (each currently 0 rows from v4.2.0_create_missing_canonicals.cypher):
//
//   1. TaxTreaty (0 rows)
//      - Multi-jurisdiction extension is anti-pattern A2 (forbidden until
//        金税四期 coverage > 90% AND ≥1 paying CN customer renews).
//      - Empty stub for a banned direction = self-contradicting schema.
//
//   2. ResponseStrategy (0 rows)
//      - Payload `recommendedSteps STRING` is consulting prose, not graph-
//        queryable structure.
//      - No SOTA tax KG (TaxLOD / ONESOURCE / Bloomberg Tax) carries this.
//      - Risk handled via ComplianceRule + Penalty + RiskIndicatorV2 chains.
//
//   3. TaxLiabilityTrigger (0 rows)
//      - Functionally identical to ComplianceRule (severity + sourceClauseId)
//        + TaxCalculationRule (formula + taxTypeId). Semantic duplication.
//
// REVERSIBILITY:
//   - These were created as DDL-only stubs in v4.2.0_create_missing_canonicals.cypher.
//     Restore = re-running v4.2.0 (idempotent IF NOT EXISTS).
//   - No data loss (rows = 0 for all three).
//   - Composite gate canonical_count drops from 35 → 32; override domain by
//     removing them from `schemas/ontology_v4.2.cypher` in a follow-up commit.
//
// HITL CHECKLIST (Maurice must confirm):
//   [ ] Pre-deploy snapshot per v4.2.3 procedure (combine with v4.2.3 deploy)
//   [ ] /api/v1/ontology-audit confirms each target has 0 rows immediately
//       before deploy (no race-condition data added between snapshot and drop)
//   [ ] schemas/ontology_v4.2.cypher updated to remove the 3 type definitions
//       in the SAME commit that ships this migration
//   [ ] Audit gate updated: canonical_count target adjusted 35 → 32
// ============================================================================

// All three are leaf tables (no edges defined yet). Pure DROP.
DROP TABLE IF EXISTS TaxTreaty;
DROP TABLE IF EXISTS ResponseStrategy;
DROP TABLE IF EXISTS TaxLiabilityTrigger;

// --- Post-deploy expected state ---
//   canonical_count: 35 → 32   (after schemas/ontology_v4.2.cypher update)
//   intersection: 35 → 32       (the 3 dropped types leave the canonical set)
//   live_count: drops by 3      (no data lost; tables were 0-row stubs)
//   composite_gate.C1_plus: improves (denominator shrinks; ratio rises)
