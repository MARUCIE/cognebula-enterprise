#!/usr/bin/env python3
"""Enrich isolated TaxType nodes with edges to related content.

Problem: 18 of 19 TaxType nodes are near-isolated (only VAT has rich connections).
Solution: Create edges by matching tax names in DocumentSection/RegulationClause content.

Run on kg-node: python3 scripts/enrich_tax_edges.py [--dry-run]
"""
import sys

DRY_RUN = "--dry-run" in sys.argv

# Tax types and their Chinese name variants for content matching
TAX_TYPE_KEYWORDS = {
    "TT_VAT": ["增值税"],
    "TT_CIT": ["企业所得税", "企业所得"],
    "TT_PIT": ["个人所得税", "个税", "个人所得"],
    "TT_CONSUMPTION": ["消费税"],
    "TT_RESOURCE": ["资源税"],
    "TT_PROPERTY": ["房产税", "房屋税"],
    "TT_VEHICLE": ["车船税", "车船使用税"],
    "TT_CONTRACT": ["契税"],              # DB uses TT_CONTRACT not TT_DEED
    "TT_STAMP": ["印花税"],
    "TT_TARIFF": ["关税", "进口关税", "出口关税"],  # DB uses TT_TARIFF not TT_CUSTOMS
    "TT_URBAN": ["城市维护建设税", "城建税"],        # DB uses TT_URBAN
    "TT_CULTIVATED": ["耕地占用税"],                 # DB uses TT_CULTIVATED
    "TT_TOBACCO": ["烟叶税"],
    "TT_LAND_VAT": ["土地增值税"],
    "TT_LAND_USE": ["城镇土地使用税", "土地使用税"], # DB uses TT_LAND_USE
    "TT_ENV": ["环境保护税", "环保税"],
    "TT_EDUCATION": ["教育费附加", "教育附加"],
    "TT_LOCAL_EDU": ["地方教育附加"],                # DB uses TT_LOCAL_EDU
    "TT_TONNAGE": ["船舶吨税"],
}

# Edge types to create
EDGE_CONTENT_MATCH = "MENTIONS"  # DocumentSection/RegulationClause mentions a tax type
EDGE_LAW_APPLIES = "FT_APPLIES_TO"  # LawOrRegulation applies to a tax type


def create_edge_table_if_missing(conn, rel_name, from_table, to_table):
    """Create relationship table if it doesn't exist."""
    try:
        conn.execute(f"MATCH ()-[r:{rel_name}]->() RETURN count(r) LIMIT 1")
    except:
        try:
            conn.execute(
                f"CREATE REL TABLE IF NOT EXISTS {rel_name} (FROM {from_table} TO {to_table})"
            )
            print(f"  Created edge table: {rel_name} ({from_table} -> {to_table})")
        except Exception as e:
            print(f"  WARN: Cannot create {rel_name}: {e}")


def enrich_from_content(conn, tax_id: str, keywords: list[str],
                        source_table: str, content_field: str) -> int:
    """Find content nodes mentioning tax keywords and create edges."""
    created = 0
    for kw in keywords:
        try:
            r = conn.execute(f"""
                MATCH (d:{source_table})
                WHERE d.{content_field} CONTAINS $kw
                AND NOT exists {{ (d)-[:{EDGE_CONTENT_MATCH}]->(t:TaxType {{id: $tid}}) }}
                RETURN d.id
                LIMIT 50
            """, {"kw": kw, "tid": tax_id})

            while r.has_next():
                did = r.get_next()[0]
                if not did:
                    continue
                if DRY_RUN:
                    created += 1
                    continue
                try:
                    conn.execute(f"""
                        MATCH (d:{source_table} {{id: $did}}), (t:TaxType {{id: $tid}})
                        CREATE (d)-[:{EDGE_CONTENT_MATCH}]->(t)
                    """, {"did": did, "tid": tax_id})
                    created += 1
                except:
                    pass
        except Exception as e:
            if "not exist" not in str(e).lower():
                print(f"    WARN: query failed for {source_table}/{kw}: {str(e)[:80]}")
    return created


def main():
    try:
        import kuzu
    except ImportError:
        print("ERROR: kuzu not installed")
        sys.exit(1)

    db_path = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
    print(f"=== Enrich Tax Edges {'(DRY RUN)' if DRY_RUN else ''} ===")

    try:
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Ensure MENTIONS edge tables exist for all source -> TaxType combinations
    for src in ["DocumentSection", "RegulationClause", "LawOrRegulation",
                "CPAKnowledge", "FAQEntry", "MindmapNode"]:
        create_edge_table_if_missing(conn, EDGE_CONTENT_MATCH, src, "TaxType")

    # Get current edge count per TaxType
    print("\nCurrent connectivity:")
    for tax_id in TAX_TYPE_KEYWORDS:
        try:
            r = conn.execute(
                "MATCH (t:TaxType {id: $id})-[]-() RETURN count(*)",
                {"id": tax_id}
            )
            cnt = r.get_next()[0]
            print(f"  {tax_id}: {cnt} edges")
        except:
            print(f"  {tax_id}: (not found)")

    # Enrich each tax type
    print("\nEnriching edges:")
    total_created = 0
    for tax_id, keywords in TAX_TYPE_KEYWORDS.items():
        tax_total = 0

        # Match in DocumentSection content
        n = enrich_from_content(conn, tax_id, keywords, "DocumentSection", "content")
        tax_total += n

        # Match in RegulationClause fullText
        n = enrich_from_content(conn, tax_id, keywords, "RegulationClause", "fullText")
        tax_total += n

        # Match in LawOrRegulation title (more specific)
        n = enrich_from_content(conn, tax_id, keywords, "LawOrRegulation", "title")
        tax_total += n

        # Match in CPAKnowledge content
        n = enrich_from_content(conn, tax_id, keywords, "CPAKnowledge", "content")
        tax_total += n

        if tax_total > 0:
            print(f"  {tax_id} ({keywords[0]}): +{tax_total} edges")
            total_created += tax_total

    print(f"\n=== DONE: Created {total_created} new edges ===")
    if DRY_RUN:
        print("(Dry run — remove --dry-run to apply)")

    # Final stats
    if not DRY_RUN:
        try:
            r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
            print(f"Total edges now: {r.get_next()[0]}")
        except:
            pass


if __name__ == "__main__":
    main()
