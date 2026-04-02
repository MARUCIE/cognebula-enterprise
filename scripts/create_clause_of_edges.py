#!/usr/bin/env python3
"""Create CLAUSE_OF edges for LegalClauses missing parent links.

LegalClause IDs follow pattern: CL_{docHash}_{artN}
The docHash matches LawOrRegulation.id or LegalDocument.id.
This script extracts the hash and creates CLAUSE_OF edges.
"""
import kuzu
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clause_of")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"


def main():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Get existing CLAUSE_OF count
    r = conn.execute("MATCH ()-[e:CLAUSE_OF]->() RETURN count(e)")
    before = r.get_next()[0]
    log.info("Existing CLAUSE_OF edges: %d", before)

    # Get all LegalClause IDs without CLAUSE_OF edge
    r = conn.execute("""
        MATCH (c:LegalClause)
        WHERE NOT EXISTS { MATCH (c)-[:CLAUSE_OF]->() }
        RETURN c.id
    """)
    orphan_ids = []
    while r.has_next():
        orphan_ids.append(r.get_next()[0])
    log.info("Orphan clauses (no CLAUSE_OF): %d", len(orphan_ids))

    if not orphan_ids:
        log.info("No orphan clauses, done")
        del conn; del db
        return

    # Extract parent doc hash from clause ID
    # Pattern: CL_{hash16}_art{N} or CL_{hash16}_art{N}_p{M}
    parent_map = {}  # hash -> [clause_ids]
    for cid in orphan_ids:
        m = re.match(r'CL_([a-f0-9]{16})_', cid)
        if m:
            parent_hash = m.group(1)
            parent_map.setdefault(parent_hash, []).append(cid)

    log.info("Unique parent hashes: %d", len(parent_map))

    # Build lookup: which hashes exist as LawOrRegulation or LegalDocument IDs?
    lr_ids = set()
    r = conn.execute("MATCH (lr:LawOrRegulation) RETURN lr.id")
    while r.has_next():
        lr_ids.add(r.get_next()[0])

    ld_ids = set()
    r = conn.execute("MATCH (ld:LegalDocument) RETURN ld.id")
    while r.has_next():
        ld_ids.add(r.get_next()[0])

    log.info("LR IDs loaded: %d, LD IDs loaded: %d", len(lr_ids), len(ld_ids))

    # Check what CLAUSE_OF connects to
    r = conn.execute("MATCH (c:LegalClause)-[e:CLAUSE_OF]->(d) RETURN labels(d)[0] LIMIT 1")
    if r.has_next():
        target_type = r.get_next()[0]
        log.info("CLAUSE_OF target type: %s", target_type)
    else:
        # Check edge definition
        log.info("CLAUSE_OF empty, trying both LR and LD")
        target_type = None

    created = 0
    errors = 0

    for parent_hash, clause_ids in parent_map.items():
        # Try LawOrRegulation first, then LegalDocument
        target_id = None
        target_label = None

        if parent_hash in lr_ids:
            target_id = parent_hash
            target_label = "LawOrRegulation"
        elif parent_hash in ld_ids:
            target_id = parent_hash
            target_label = "LegalDocument"

        if not target_id:
            continue

        for cid in clause_ids:
            try:
                conn.execute(
                    f"MATCH (c:LegalClause), (d:{target_label}) "
                    f"WHERE c.id = '{cid}' AND d.id = '{target_id}' "
                    f"CREATE (c)-[:CLAUSE_OF]->(d)"
                )
                created += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    log.warning("Failed: %s -> %s: %s", cid[:30], target_id, str(e)[:60])

        if created % 5000 == 0 and created > 0:
            log.info("  Progress: %d created, %d errors", created, errors)

    r = conn.execute("MATCH ()-[e:CLAUSE_OF]->() RETURN count(e)")
    after = r.get_next()[0]
    log.info("DONE: +%d CLAUSE_OF edges (before: %d, after: %d, errors: %d)",
             created, before, after, errors)

    del conn; del db


if __name__ == "__main__":
    main()
