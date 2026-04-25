#!/usr/bin/env python3
"""Seed canonical Region table with GB/T 2260 administrative + special tax zones.

Reads embedded data from src.inject_admin_regions (PROVINCE_LEVEL +
PREFECTURE_CITIES + SPECIAL_TAX_ZONES, ~400 records) and inserts into the
canonical Region(id, name, code, level, parentId) table.

ID convention:
- Province: reg_gb2260_<code>     e.g. reg_gb2260_110000
- Prefecture: reg_gb2260_<code>   e.g. reg_gb2260_130100
- Special zone: reg_zone_<code>   e.g. reg_zone_SZ_HAINAN_FTP

Reversibility:
    MATCH (r:Region) WHERE r.id STARTS WITH 'reg_gb2260_' OR r.id STARTS WITH 'reg_zone_' DELETE r;

Usage:
    python src/seed_canonical_regions.py --db data/finance-tax-graph
    python src/seed_canonical_regions.py --db data/finance-tax-graph --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.inject_admin_regions import PROVINCE_LEVEL, PREFECTURE_CITIES, SPECIAL_TAX_ZONES


def province_id(code: str) -> str:
    return f"reg_gb2260_{code}"


def prefecture_id(code: str) -> str:
    return f"reg_gb2260_{code}"


def zone_id(code: str) -> str:
    return f"reg_zone_{code}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, help="Kuzu DB path")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    rows = []
    for prov in PROVINCE_LEVEL:
        rows.append({
            "id": province_id(prov["code"]),
            "name": prov["name"],
            "code": prov["code"],
            "level": prov["regionType"],
            "parentId": "",
        })
    for pref in PREFECTURE_CITIES:
        rows.append({
            "id": prefecture_id(pref["code"]),
            "name": pref["name"],
            "code": pref["code"],
            "level": "prefecture",
            "parentId": province_id(pref["parent"]),
        })
    for zone in SPECIAL_TAX_ZONES:
        rows.append({
            "id": zone_id(zone["code"]),
            "name": zone["name"],
            "code": zone["code"],
            "level": zone["regionType"],
            "parentId": province_id(zone.get("parentCode", "")) if zone.get("parentCode") else "",
        })

    print(f"[seed] target=canonical Region · rows={len(rows)} (provinces={len(PROVINCE_LEVEL)} + prefectures={len(PREFECTURE_CITIES)} + zones={len(SPECIAL_TAX_ZONES)})")

    if args.dry_run:
        print(f"[DRY-RUN] would insert {len(rows)} rows")
        for r in rows[:3]:
            print("  sample:", r)
        return 0

    import kuzu
    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    added = skipped = failed = 0
    t0 = time.time()
    for r in rows:
        try:
            conn.execute(
                "MERGE (n:Region {id: $id}) SET n.name=$name, n.code=$code, n.level=$level, n.parentId=$parentId",
                {"id": r["id"], "name": r["name"], "code": r["code"], "level": r["level"], "parentId": r["parentId"]},
            )
            added += 1
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "duplicate" in msg:
                skipped += 1
            else:
                failed += 1
                print(f"  FAIL: id={r['id']} name={r['name']} → {e}")

    elapsed = int((time.time() - t0) * 1000)
    print(f"[APPLY] total={len(rows)} added={added} skipped={skipped} failed={failed} elapsed={elapsed}ms")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
