"""
Seed Tier 4 Bridge → TaxType FK edges.

Creates REL TABLE `BELONGS_TO_TAX_TYPE` (multi-pair: DeductionRule|TaxMilestoneEvent → TaxType).

Source-side identifier `taxTypeId` (e.g. 'tax_cit') → canonical TaxType.id (e.g. 'TT_CIT')
mapping is held in code; existing TaxType nodes are not modified.

Reversibility: `DROP TABLE BELONGS_TO_TAX_TYPE;` removes all edges in one statement.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

import kuzu

# Map seed-side taxTypeId (lowercase, used in DeductionRule + TaxMilestoneEvent seeds)
# to canonical TaxType.id (uppercase TT_* convention) actually present in the graph.
TAX_TYPE_MAPPING: dict[str, str] = {
    "tax_vat": "TT_VAT",
    "tax_cit": "TT_CIT",
    "tax_pit": "TT_PIT",
    "tax_stamp": "TT_STAMP",
    "tax_property": "TT_PROPERTY",
    "tax_land_use": "TT_LAND_USE",
    "tax_resource": "TT_RESOURCE",
    "tax_city_maintenance": "TT_URBAN",      # 城市维护建设税
    "tax_customs": "TT_TARIFF",               # 关税
    "tax_surcharge": "TT_EDUCATION",          # 教育费附加 (primary; LOCAL_EDU is parallel)
}


def ensure_rel_table(conn: kuzu.Connection) -> None:
    """Create the multi-pair REL TABLE if it does not already exist."""
    # Kuzu multi-pair REL TABLE syntax: list FROM/TO pairs explicitly.
    ddl = """
    CREATE REL TABLE IF NOT EXISTS BELONGS_TO_TAX_TYPE(
      FROM DeductionRule TO TaxType,
      FROM TaxMilestoneEvent TO TaxType,
      sourceField STRING
    )
    """
    conn.execute(ddl)


def fetch_source_nodes(conn: kuzu.Connection, label: str) -> list[tuple[str, str]]:
    """Return [(node_id, taxTypeId), ...] for the given source label."""
    res = conn.execute(
        f"MATCH (n:{label}) WHERE n.taxTypeId IS NOT NULL RETURN n.id, n.taxTypeId"
    )
    pairs: list[tuple[str, str]] = []
    while res.has_next():
        row = res.get_next()
        pairs.append((row[0], row[1]))
    return pairs


def seed_edges_for_label(
    conn: kuzu.Connection,
    label: str,
    dry_run: bool,
) -> tuple[int, int, list[str]]:
    """Seed BELONGS_TO_TAX_TYPE edges from `label` nodes.

    Returns (added, skipped_unmapped, unmapped_seed_keys).
    """
    pairs = fetch_source_nodes(conn, label)
    added = 0
    skipped = 0
    unmapped: set[str] = set()

    for src_id, seed_tt_id in pairs:
        canonical = TAX_TYPE_MAPPING.get(seed_tt_id)
        if canonical is None:
            skipped += 1
            unmapped.add(seed_tt_id)
            continue

        if dry_run:
            added += 1
            continue

        # MATCH existing TaxType target (do nothing if missing)
        # MATCH source by id
        # MERGE the edge with sourceField='taxTypeId' for provenance
        cypher = (
            f"MATCH (s:{label} {{id: $sid}}), (t:TaxType {{id: $tid}}) "
            "MERGE (s)-[e:BELONGS_TO_TAX_TYPE]->(t) "
            "ON CREATE SET e.sourceField = 'taxTypeId'"
        )
        conn.execute(cypher, {"sid": src_id, "tid": canonical})
        added += 1

    return added, skipped, sorted(unmapped)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Kuzu database path")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not write")
    args = parser.parse_args()

    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    if not args.dry_run:
        print("[create] REL TABLE BELONGS_TO_TAX_TYPE (idempotent)")
        ensure_rel_table(conn)

    grand_added = 0
    grand_skipped = 0
    grand_unmapped: set[str] = set()

    for label in ("DeductionRule", "TaxMilestoneEvent"):
        t0 = time.perf_counter()
        added, skipped, unmapped = seed_edges_for_label(conn, label, args.dry_run)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        verb = "[DRY-RUN]" if args.dry_run else "[APPLY]"
        print(
            f"  {verb} {label}: edges_added={added} unmapped={skipped} elapsed={elapsed_ms}ms"
        )
        grand_added += added
        grand_skipped += skipped
        grand_unmapped.update(unmapped)

    print(
        f"[TOTAL] edges_added={grand_added} unmapped_skipped={grand_skipped} "
        f"distinct_unmapped_keys={sorted(grand_unmapped)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
