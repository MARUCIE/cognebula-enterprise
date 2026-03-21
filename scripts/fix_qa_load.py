#!/usr/bin/env python3
"""Fix: Load QA nodes from CSV into KuzuDB using parameterized INSERT.

The COPY FROM failed due to CSV parsing issues. This script uses
individual parameterized INSERT statements which handle all escaping.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u /home/kg/cognebula-enterprise/scripts/fix_qa_load.py
    sudo systemctl start kg-api
"""
import kuzu
import csv
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CSV_PATH = "/home/kg/cognebula-enterprise/data/edge_csv/m3_qa/qa_nodes.csv"
TAX_CSV = "/home/kg/cognebula-enterprise/data/edge_csv/m3_qa/qa_ku_about_tax.csv"

TAX_KEYWORDS = {
    "增值税": "TT_VAT", "企业所得税": "TT_CIT", "个人所得税": "TT_PIT",
    "消费税": "TT_CONSUMPTION", "关税": "TT_TARIFF",
    "城市维护建设税": "TT_URBAN", "城建税": "TT_URBAN",
    "教育费附加": "TT_EDUCATION", "地方教育附加": "TT_LOCAL_EDU",
    "资源税": "TT_RESOURCE", "土地增值税": "TT_LAND_VAT",
    "房产税": "TT_PROPERTY", "城镇土地使用税": "TT_LAND_USE",
    "车船税": "TT_VEHICLE", "印花税": "TT_STAMP",
    "契税": "TT_CONTRACT", "耕地占用税": "TT_CULTIVATED",
    "烟叶税": "TT_TOBACCO", "环境保护税": "TT_ENV",
    "个税": "TT_PIT", "所得税": "TT_CIT",
}


def main():
    print("=" * 60)
    print("Fix: Load QA nodes via parameterized INSERT")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Check existing QA nodes
    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.id STARTS WITH 'QA_' RETURN count(k)")
    existing = r.get_next()[0]
    print(f"Existing QA nodes: {existing}")

    # Load QA nodes
    t0 = time.time()
    success = 0
    skip = 0
    fail = 0
    tax_edges = 0

    with open(CSV_PATH) as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if len(row) != 5:
                fail += 1
                continue

            ku_id, ku_type, title, content, source = row

            try:
                conn.execute(
                    "CREATE (k:KnowledgeUnit {id: $id, type: $type, title: $title, content: $content, source: $source})",
                    {"id": ku_id, "type": ku_type, "title": title, "content": content, "source": source}
                )
                success += 1

                # Create KU_ABOUT_TAX edge
                text = title + " " + content
                for kw, tid in TAX_KEYWORDS.items():
                    if kw in text:
                        try:
                            conn.execute(
                                "MATCH (k:KnowledgeUnit), (t:TaxType) "
                                "WHERE k.id = $kid AND t.id = $tid "
                                "CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                                {"kid": ku_id, "tid": tid}
                            )
                            tax_edges += 1
                        except Exception:
                            pass
                        break

            except Exception as e:
                err = str(e)
                if "already exists" in err or "duplicate" in err.lower():
                    skip += 1
                else:
                    fail += 1
                    if fail <= 3:
                        print(f"  Row {i}: {err[:100]}")

            if (i + 1) % 1000 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                print(f"  {i+1} rows: +{success} inserted, {skip} skipped, {fail} failed, {tax_edges} edges ({rate:.0f} rows/s)")

    elapsed = time.time() - t0

    # Final stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.id STARTS WITH 'QA_' RETURN count(k)")
    qa_count = r.get_next()[0]

    print(f"\n{'='*60}")
    print(f"QA Load Done ({elapsed:.0f}s)")
    print(f"  Inserted: {success:,}")
    print(f"  Skipped (dup): {skip:,}")
    print(f"  Failed: {fail:,}")
    print(f"  Tax edges: +{tax_edges:,}")
    print(f"  QA nodes total: {qa_count:,}")
    print(f"  Graph: {nodes:,} nodes / {edges:,} edges / density {edges/nodes:.3f}")

    del conn
    del db


if __name__ == "__main__":
    main()
