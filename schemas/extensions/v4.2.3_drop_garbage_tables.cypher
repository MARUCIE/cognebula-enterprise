// ============================================================================
// Ontology v4.2.3 — Round-4 deletion: 3 admitted-garbage tables
// ============================================================================
//
// Per `outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md`
// §3.1 (Hara structural-minimalism lens, swarm-confirmed).
//
// Targets:
//   1. RiskIndicator   (463 rows)  — superseded by RiskIndicatorV2 (463); the
//      ontology_v4.2.cypher header itself reads "TRUNCATE only designated
//      garbage when superseded by V2 counterpart". Schema authors marked it.
//   2. CPAKnowledge    (7,371 rows, quality_score=0.0) — zero domain signal.
//      Has never been queried by any active retrieval path.
//   3. MindmapNode     (28,526 rows, "no content by design") — explicit
//      shipper-side admission that the table holds no signal. SaaS artifact.
//
// REVERSIBILITY:
//   Pre-deploy MANDATORY:
//     1. Snapshot prod Kuzu DB:
//        docker exec cognebula-api tar -czf /tmp/pre-v423-snap.tgz /app/data/kg.kuzu
//        docker cp cognebula-api:/tmp/pre-v423-snap.tgz ./snapshots/
//     2. Verify counts match expected (audit endpoint /api/v1/stats):
//        RiskIndicator=463, CPAKnowledge=7371, MindmapNode=28526
//     3. rclone the snapshot to gdrive:VPS-Backups/cognebula-snapshots/<date>/
//
//   Restore (if regret within 24h): `kuzu_restore_from_snapshot.sh pre-v423-snap.tgz`
//
// HITL CHECKLIST (Maurice must confirm):
//   [ ] Pre-deploy snapshot taken and uploaded to GDrive
//   [ ] Audit endpoint confirms row counts within ±5% of expected
//   [ ] Downstream consumers (灵阙 Agents, yiclaw planning) checked for
//       references to RiskIndicator (use RiskIndicatorV2 instead) — only
//       MCP query logs from past 30 days need check
//   [ ] /api/v1/quality and /api/v1/ontology-audit captured pre-deploy
// ============================================================================

// --- Drop edges first (Kuzu requires REL tables removed before NODE tables) ---
// Idempotent: each match returns gracefully if relations are absent.

// RiskIndicator legacy edges (V2 carries equivalents)
DROP TABLE IF EXISTS REL_RiskIndicator_INFLUENCES;
DROP TABLE IF EXISTS REL_RiskIndicator_DETECTED_BY;
DROP TABLE IF EXISTS REL_RiskIndicator_TARGETS;

// CPAKnowledge edges
DROP TABLE IF EXISTS REL_CPAKnowledge_REFERENCES;
DROP TABLE IF EXISTS REL_CPAKnowledge_DESCRIBES;
DROP TABLE IF EXISTS REL_CPAKnowledge_PART_OF;

// MindmapNode edges
DROP TABLE IF EXISTS REL_MindmapNode_PARENT_OF;
DROP TABLE IF EXISTS REL_MindmapNode_LINKS_TO;
DROP TABLE IF EXISTS REL_MindmapNode_TAGGED_AS;

// --- Drop nodes (canonical name match; idempotent IF EXISTS) ---
DROP TABLE IF EXISTS RiskIndicator;
DROP TABLE IF EXISTS CPAKnowledge;
DROP TABLE IF EXISTS MindmapNode;

// --- Post-deploy verification queries (manual, not part of migration) ---
//   /api/v1/ontology-audit → live_count should drop by 3
//   /api/v1/stats → total_nodes should drop by ~36,360 (463+7371+28526)
//   /api/v1/quality → no `unlabeled_edge_targets` regression
