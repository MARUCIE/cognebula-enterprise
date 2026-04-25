"""Seed canonical Region county/district level from GB/T 2260 (cpca dataset).

Data source: `cpca` Python package's bundled `resources/adcodes.csv`
(3,511 records of canonical Chinese administrative codes maintained by 民政部).
Each adcode is a 12-digit string; the first 6 digits are the GB/T 2260 code,
positions 4-5 indicate county/district (00 means prefecture-level only).

This seed adds ONLY county-level rows, skipping any code already present in
the existing 477-row Region spine (province + municipality + SAR + prefecture).

ID convention: `reg_gb2260_<6-digit-code>` (matches existing seed convention).
Provenance: every county node is tagged with `extracted_by = 'wave_13_cpca'`
and `source_doc_id = 'cpca_gb2260'` for clean rollback and audit trail.

Reversibility:
    MATCH (n:Region) WHERE n.extracted_by = 'wave_13_cpca' DELETE n;

This is REAL ingestion (民政部-maintained authoritative data via cpca lib),
not stub-backfill — anti-pattern A4 compliant per "first real row arrives via
real ingestion" criterion.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import kuzu


CPCA_CSV_PATH = (
    "/home/kg-env/lib/python3.12/site-packages/cpca/resources/adcodes.csv"
)


def load_county_records(csv_path: str) -> list[dict[str, str]]:
    """Read cpca adcodes.csv and filter to county-level (6-digit GB/T 2260).

    A county-level code has:
      - positions 0-1 = province code (non-00)
      - positions 2-3 = prefecture code (non-00 for normal counties; can be
        '00' for municipality-administered counties like 北京 110105)
      - positions 4-5 = county code (non-00)
      - positions 6-11 = trailing zeros
    """
    records: list[dict[str, str]] = []
    with open(csv_path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            adcode = row.get("adcode", "").strip()
            name = row.get("name", "").strip()
            if len(adcode) != 12 or not adcode.isdigit():
                continue
            if not adcode.endswith("000000"):
                continue  # only standard 6-digit GB/T 2260 entries
            code6 = adcode[:6]
            if code6[4:6] == "00":
                continue  # prefecture-level or higher (already in existing seed)
            if code6[0:2] == "00":
                continue  # malformed
            records.append(
                {
                    "code": code6,
                    "name": name,
                    "province_code": code6[0:2] + "0000",
                    "prefecture_code": code6[0:4] + "00",
                }
            )
    return records


def existing_region_ids(conn: kuzu.Connection) -> set[str]:
    res = conn.execute("MATCH (n:Region) RETURN n.id")
    out: set[str] = set()
    while res.has_next():
        out.add(res.get_next()[0])
    return out


def determine_parent_id(record: dict[str, str], existing: set[str]) -> str | None:
    """Pick the closest existing parent: prefecture if present, else province.

    Some municipality-administered counties (北京/上海/天津/重庆) skip the
    prefecture layer — their parent is the municipality directly.
    """
    pref = f"reg_gb2260_{record['prefecture_code']}"
    if pref in existing:
        return pref
    prov = f"reg_gb2260_{record['province_code']}"
    if prov in existing:
        return prov
    return None  # orphan county (rare; e.g. data drift). Skip.


def seed_counties(
    conn: kuzu.Connection,
    records: list[dict[str, str]],
    existing: set[str],
    dry_run: bool,
) -> tuple[int, int, int]:
    """Apply seed; returns (added, skipped_already_present, skipped_orphan)."""
    added = 0
    skipped_present = 0
    skipped_orphan = 0
    t0 = time.perf_counter()

    for rec in records:
        node_id = f"reg_gb2260_{rec['code']}"
        if node_id in existing:
            skipped_present += 1
            continue

        parent_id = determine_parent_id(rec, existing)
        if parent_id is None:
            skipped_orphan += 1
            continue

        if dry_run:
            added += 1
            continue

        # Use the validated Kuzu pattern: MERGE-id then chained SET batches ≤4 props
        conn.execute(
            "MERGE (n:Region {id: $nid})",
            {"nid": node_id},
        )
        conn.execute(
            "MATCH (n:Region {id: $nid}) "
            "SET n.code = $code, n.name = $name, n.level = $lvl, n.parentId = $pid",
            {
                "nid": node_id,
                "code": rec["code"],
                "name": rec["name"],
                "lvl": "county",
                "pid": parent_id,
            },
        )
        conn.execute(
            "MATCH (n:Region {id: $nid}) "
            "SET n.source_doc_id = $sdi, n.extracted_by = $eb, n.confidence = $conf, n.title = $ttl",
            {
                "nid": node_id,
                "sdi": "cpca_gb2260",
                "eb": "wave_13_cpca",
                "conf": 1.0,
                "ttl": rec["name"],
            },
        )
        added += 1

        # Mark in the in-memory set so subsequent records can reference it as a parent
        existing.add(node_id)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    print(
        f"  added={added} skipped_already_present={skipped_present} "
        f"skipped_orphan={skipped_orphan} elapsed={elapsed_ms}ms"
    )
    return added, skipped_present, skipped_orphan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--csv", default=CPCA_CSV_PATH, help="cpca adcodes.csv path")
    args = parser.parse_args()

    if not Path(args.csv).is_file():
        print(f"[error] cpca adcodes.csv not found at {args.csv}", file=sys.stderr)
        return 2

    records = load_county_records(args.csv)
    print(f"[load] county-level GB/T 2260 records parsed: {len(records)}")

    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    existing = existing_region_ids(conn)
    print(f"[load] existing Region ids in graph: {len(existing)}")

    verb = "[DRY-RUN]" if args.dry_run else "[APPLY]"
    print(f"{verb} Region county-level seed:")
    seed_counties(conn, records, existing, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
