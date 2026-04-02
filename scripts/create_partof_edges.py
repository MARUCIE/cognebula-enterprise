#!/usr/bin/env python3
"""Create PART_OF edges for LegalClauses missing parent document links.

LegalClause IDs: CL_{docHash16}_{suffix}
LegalDocument IDs: {hash16}
Match by hash prefix to create PART_OF edges.
"""
import kuzu
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("partof")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

def main():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    r = conn.execute("MATCH ()-[e:PART_OF]->() RETURN count(e)")
    before = r.get_next()[0]
    log.info("Existing PART_OF edges: %d", before)

    # Get orphan LegalClauses (no PART_OF outgoing)
    r = conn.execute("""
        MATCH (c:LegalClause)
        WHERE NOT EXISTS { MATCH (c)-[:PART_OF]->() }
        RETURN c.id
    """)
    orphans = []
    while r.has_next():
        orphans.append(r.get_next()[0])
    log.info("Orphan LegalClauses: %d", len(orphans))

    # Build LegalDocument ID set
    ld_ids = set()
    r = conn.execute("MATCH (d:LegalDocument) RETURN d.id")
    while r.has_next():
        ld_ids.add(r.get_next()[0])
    log.info("LegalDocument IDs: %d", len(ld_ids))

    # Extract parent hash and match
    created = 0
    no_match = 0
    for cid in orphans:
        m = re.match(r'CL_([a-f0-9]{16})_', cid)
        if not m:
            no_match += 1
            continue
        parent_hash = m.group(1)
        if parent_hash not in ld_ids:
            no_match += 1
            continue
        try:
            conn.execute(
                f"MATCH (c:LegalClause), (d:LegalDocument) "
                f"WHERE c.id = '{cid}' AND d.id = '{parent_hash}' "
                f"CREATE (c)-[:PART_OF]->(d)"
            )
            created += 1
        except:
            pass
        if created % 5000 == 0 and created > 0:
            log.info("  %d created...", created)

    r = conn.execute("MATCH ()-[e:PART_OF]->() RETURN count(e)")
    after = r.get_next()[0]
    log.info("DONE: +%d PART_OF edges (before: %d, after: %d, unmatched: %d)",
             created, before, after, no_match)

    del conn; del db

if __name__ == "__main__":
    main()
