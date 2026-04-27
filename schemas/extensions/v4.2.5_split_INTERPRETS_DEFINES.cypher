// ============================================================================
// Ontology v4.2.5 — Round-4 INTERPRETS_DEFINES decomplection
// ============================================================================
//
// Per `outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md`
// §3.2 (Hickey decomplecting lens). Hickey's Monday-ship-able move:
//
//   Split `INTERPRETS_DEFINES` (~140K edges, 35-40% peel) by lexical
//   signature in source clause text. 5 high-precision Chinese tax-law
//   markers identify "definition-class" edges that the catch-all
//   INTERPRETS predicate currently buries.
//
// Markers (ALL Chinese tax-law definitional patterns):
//   - "是指"           ("means / refers to")
//   - "所称"           ("the term ... refers to" — formal definition)
//   - "本办法所称"     ("as used in these Measures, ... means")
//   - "定义为"         ("defined as")
//   - "包括"           ("includes" — enumerative definition)
//
// EXPECTED IMPACT (per Hickey):
//   - INTERPRETS edges:        390,756 → ~250,000  (peel 140K → DEFINES)
//   - INTERPRETS_DEFINES new:  0 → ~140,000
//   - anchor_recall on definition-seeking eval queries: +0.05+ (Stage 2 baseline)
//   - composite ceiling at 0.31: hop-2 traversal_precision should rise too
//
// REVERSIBILITY:
//   Single Cypher migration. Reverse:
//     MATCH (s)-[r:INTERPRETS_DEFINES]->(t) SET r:INTERPRETS REMOVE r:INTERPRETS_DEFINES;
//   Pre-deploy snapshot mandatory (volume of changes >100K rows).
//
// HITL CHECKLIST (Maurice must confirm):
//   [ ] Pre-deploy snapshot uploaded to GDrive (per v4.2.3 procedure)
//   [ ] Run `EXPLAIN MATCH ... WHERE r.source_clause CONTAINS '是指' RETURN COUNT(*)`
//       to confirm the marker query returns a count in the expected range
//       [120K, 160K] before applying the SET — outside that band = abort
//   [ ] /api/v1/ontology-audit BEFORE: capture INTERPRETS edge count
//   [ ] Run smoke eval (5 cit_definition cases) BEFORE migration to baseline
//   [ ] After migration, run same 5 smoke cases to verify anchor_recall lift
//   [ ] Update Stage 2 eval set to score `INTERPRETS_DEFINES` as a typed anchor
// ============================================================================

// --- Step 1: create the new REL TABLE if missing (idempotent) ---
// In Kuzu, edge labels can be set via SET on existing rels, but a typed
// REL TABLE makes the predicate first-class for retrieval.
//
// NOTE: Kuzu syntax for REL TABLE creation requires FROM/TO node bindings.
// We mirror the original INTERPRETS table's source/target signatures:
CREATE REL TABLE IF NOT EXISTS INTERPRETS_DEFINES(
    FROM LegalClause TO Term,
    FROM LegalClause TO Definition,
    FROM LegalClause TO Concept,
    FROM RegulationClause TO Term,
    FROM RegulationClause TO Definition,
    FROM RegulationClause TO Concept,
    source_clause STRING,
    confidence FLOAT,
    extracted_by STRING,
    sourceClauseId STRING,
    effectiveAt STRING,
    supersededAt STRING
);

// --- Step 2: peel INTERPRETS edges matching definitional markers ---
// Kuzu does not support cross-label re-labeling in a single MATCH+SET.
// Use a copy-and-delete pattern within one transaction equivalent.
//
// Pseudocode (apply via cypher-shell or migration runner that supports
// multi-statement transactions):
//
//   MATCH (s)-[r:INTERPRETS]->(t)
//   WHERE r.source_clause CONTAINS '是指'
//      OR r.source_clause CONTAINS '所称'
//      OR r.source_clause CONTAINS '本办法所称'
//      OR r.source_clause CONTAINS '定义为'
//      OR r.source_clause CONTAINS '包括'
//   CREATE (s)-[d:INTERPRETS_DEFINES {
//       source_clause: r.source_clause,
//       confidence: r.confidence,
//       extracted_by: r.extracted_by,
//       sourceClauseId: r.sourceClauseId,
//       effectiveAt: r.effectiveAt,
//       supersededAt: r.supersededAt
//   }]->(t)
//   DELETE r;
//
// IMPORTANT: Kuzu transactions are per-statement; this migration MUST run
// via the migration runner (`scripts/run_migration.py --file v4.2.5...`)
// which wraps the operation in a savepoint.

// --- Step 3: verification (run AFTER migration) ---
// Expected post-state:
//   MATCH ()-[r:INTERPRETS]->()         RETURN COUNT(*)  // ~250K (was 391K)
//   MATCH ()-[r:INTERPRETS_DEFINES]->() RETURN COUNT(*)  // ~140K (was 0)
//   MATCH ()-[r:INTERPRETS]->() WHERE r.source_clause CONTAINS '是指'
//     RETURN COUNT(*)                   // should be 0 (all definitional moved)

// --- Step 4: register new predicate in retrieval scoring ---
// Update src/retrieval/predicate_weights.py:
//   PREDICATE_WEIGHTS["INTERPRETS_DEFINES"] = 1.5  // high-confidence typed
//   PREDICATE_WEIGHTS["INTERPRETS"] = 0.6           // catch-all penalty
//
// (Code change committed alongside this migration.)
