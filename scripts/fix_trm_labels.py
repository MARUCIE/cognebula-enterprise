#!/usr/bin/env python3
"""Fix TaxRateMapping nodes: replace TRM_ codes with Chinese labels.

Run on kg-node: python3 scripts/fix_trm_labels.py [--dry-run]
"""
import sys

DRY_RUN = "--dry-run" in sys.argv

# TRM code -> Chinese industry name
TRM_LABELS = {
    "TRM_TRANSPORT": "交通运输业",
    "TRM_FINANCE": "金融业",
    "TRM_TELECOM": "电信业",
    "TRM_SOFTWARE": "软件和信息技术服务业",
    "TRM_AGRI": "农业",
    "TRM_EXPORT": "出口退税",
    "TRM_REALESTATE": "房地产业",
    "TRM_CONSTRUCT": "建筑业",
    "TRM_SERVICE": "现代服务业",
    "TRM_GOODS": "货物销售",
    "TRM_CATERING": "餐饮住宿业",
    "TRM_CULTURE": "文化体育业",
    "TRM_EDUCATION": "教育服务",
    "TRM_MEDICAL": "医疗卫生",
    "TRM_LOGISTICS": "物流仓储业",
    "TRM_ENERGY": "能源行业",
    "TRM_MINING": "采矿业",
    "TRM_RETAIL": "零售批发业",
}


def decode_trm(trm_id: str) -> str:
    """Decode TRM_INDUSTRY_RATE to '行业名称 RATE%'."""
    parts = trm_id.rsplit("_", 1)
    base = parts[0] if len(parts) > 1 else trm_id
    rate = parts[1] if len(parts) > 1 and parts[1].replace(".", "").isdigit() else ""
    label = TRM_LABELS.get(base, base.replace("TRM_", "").replace("_", " ").title())
    if rate:
        return f"{label} {rate}%"
    return label


def main():
    try:
        import kuzu
    except ImportError:
        print("ERROR: kuzu not installed")
        sys.exit(1)

    db_path = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
    print(f"=== Fix TaxRateMapping Labels {'(DRY RUN)' if DRY_RUN else ''} ===")

    try:
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Get all TaxRateMapping nodes
    try:
        r = conn.execute("MATCH (n:TaxRateMapping) RETURN n.id, n.title, n.name LIMIT 500")
    except Exception as e:
        print(f"ERROR querying TaxRateMapping: {e}")
        sys.exit(1)

    fixed = 0
    total = 0
    while r.has_next():
        row = r.get_next()
        nid = row[0] or ""
        title = row[1] or ""
        name = row[2] or ""
        total += 1

        # Check if title needs fixing
        needs_fix = (
            title.startswith("TRM_") or
            not title or
            len(title) < 3 or
            nid.startswith("TRM_") and title == nid
        )
        if not needs_fix:
            continue

        new_label = decode_trm(nid)
        if DRY_RUN:
            print(f"  [DRY] {nid} -> '{new_label}'")
        else:
            # Update both title and name for maximum coverage
            try:
                conn.execute(
                    "MATCH (n:TaxRateMapping) WHERE n.id = $id SET n.title = $title",
                    {"id": nid, "title": new_label},
                )
            except:
                pass
            try:
                conn.execute(
                    "MATCH (n:TaxRateMapping) WHERE n.id = $id SET n.name = $name",
                    {"id": nid, "name": new_label},
                )
            except:
                pass
        fixed += 1

    print(f"Fixed {fixed}/{total} TaxRateMapping labels")
    if DRY_RUN:
        print("(Dry run — remove --dry-run to apply)")


if __name__ == "__main__":
    main()
