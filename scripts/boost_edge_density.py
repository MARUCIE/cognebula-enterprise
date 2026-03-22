#!/usr/bin/env python3
"""Boost edge density via batch edge creation.

Strategy (Meadows Edge-First):
  1. KU→TaxType: keyword matching (企业所得税→CIT, 增值税→VAT, etc.)
  2. KU→LR: regulation reference extraction (《XX法》→ match LR by title)
  3. LR→LR: SUPERSEDES chain (temporal version linking)
  4. KU→KU: RELATED (same industry/lifecycle from compliance matrix)
  5. Orphan rescue: connect isolated nodes to nearest hub

Target: density 2.24 → 5.0+  (need ~2.7M more edges on 458K nodes)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/boost_edge_density.py
    sudo systemctl start kg-api
"""
import kuzu
import logging
import re
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("edge_boost")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

# Tax keyword → TaxType name fragments for matching
TAX_KEYWORDS = {
    "企业所得税": ["企业所得"],
    "增值税": ["增值税"],
    "个人所得税": ["个人所得"],
    "消费税": ["消费税"],
    "关税": ["关税"],
    "城市维护建设税": ["城市维护", "城建税"],
    "土地增值税": ["土地增值"],
    "房产税": ["房产税"],
    "印花税": ["印花税"],
    "契税": ["契税"],
    "车辆购置税": ["车辆购置"],
    "车船税": ["车船税"],
    "资源税": ["资源税"],
    "环境保护税": ["环境保护", "环保税"],
    "烟叶税": ["烟叶税"],
    "耕地占用税": ["耕地占用"],
    "城镇土地使用税": ["城镇土地", "土地使用税"],
    "教育费附加": ["教育费附加", "教育附加"],
}


def task1_ku_to_taxtype(conn) -> int:
    """Create KU_ABOUT_TAX edges by keyword matching in KU content/title."""
    log.info("\n[Task 1] KU → TaxType keyword matching")

    # Get all TaxType nodes
    r = conn.execute("MATCH (t:TaxType) RETURN t.id, t.name")
    tax_types = {}
    while r.has_next():
        row = r.get_next()
        tax_types[str(row[0])] = str(row[1])
    log.info("  TaxType nodes: %d", len(tax_types))

    if not tax_types:
        log.warning("  No TaxType nodes found, skipping")
        return 0

    # Build keyword→taxtype_id mapping
    kw_to_tt = {}
    for tt_id, tt_name in tax_types.items():
        for tax_name, keywords in TAX_KEYWORDS.items():
            for kw in keywords:
                if kw in tt_name:
                    kw_to_tt[tax_name] = tt_id
                    break

    log.info("  Mapped %d tax keywords to TaxType IDs", len(kw_to_tt))

    # Find KU without KU_ABOUT_TAX edges
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE NOT EXISTS { MATCH (k)-[:KU_ABOUT_TAX]->() } "
        "AND k.content IS NOT NULL AND size(k.content) >= 50 "
        "RETURN count(k)"
    )
    total = r.get_next()[0]
    log.info("  KU without tax edges: %d", total)

    created = 0
    batch_size = 500

    for offset in range(0, min(total, 100000), batch_size):
        r = conn.execute(
            "MATCH (k:KnowledgeUnit) "
            "WHERE NOT EXISTS { MATCH (k)-[:KU_ABOUT_TAX]->() } "
            "AND k.content IS NOT NULL AND size(k.content) >= 50 "
            "RETURN k.id, k.title, substring(k.content, 0, 500) "
            f"LIMIT {batch_size}"
        )

        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({"id": str(row[0]), "title": str(row[1] or ""), "content": str(row[2] or "")})

        if not batch:
            break

        for item in batch:
            text = item["title"] + " " + item["content"]
            matched_tts = set()
            for tax_name, tt_id in kw_to_tt.items():
                if tax_name in text or any(kw in text for kw in TAX_KEYWORDS.get(tax_name, [])):
                    matched_tts.add(tt_id)

            for tt_id in matched_tts:
                try:
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType {id: $tid}) "
                        "CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                        {"kid": item["id"], "tid": tt_id}
                    )
                    created += 1
                except Exception:
                    pass

        if (offset + batch_size) % 5000 == 0:
            log.info("  Progress: %d/%d, +%d edges", offset + batch_size, total, created)

    log.info("  Done: +%d KU_ABOUT_TAX edges", created)
    return created


def task2_regulation_refs(conn) -> int:
    """Extract 《法规名》 references from KU content and link to LR nodes."""
    log.info("\n[Task 2] KU → LR regulation reference linking")

    # Pattern: 《XX法》《XX条例》《XX办法》etc.
    reg_pattern = re.compile(r'《([^》]{4,30}(?:法|条例|办法|规定|通知|决定|意见|准则|制度|规则|细则))》')

    # Get KU with content containing 《》
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.content CONTAINS '《' "
        "AND NOT EXISTS { MATCH (k)-[:REFERENCES]->(:LawOrRegulation) } "
        "RETURN count(k)"
    )
    total = r.get_next()[0]
    log.info("  KU with 《》 references: %d", total)

    created = 0
    batch_size = 200

    for offset in range(0, min(total, 50000), batch_size):
        r = conn.execute(
            "MATCH (k:KnowledgeUnit) "
            "WHERE k.content CONTAINS '《' "
            "AND NOT EXISTS { MATCH (k)-[:REFERENCES]->(:LawOrRegulation) } "
            "RETURN k.id, k.content "
            f"LIMIT {batch_size}"
        )

        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({"id": str(row[0]), "content": str(row[1] or "")})

        if not batch:
            break

        for item in batch:
            refs = reg_pattern.findall(item["content"])
            if not refs:
                continue

            for ref_name in set(refs[:5]):  # Max 5 refs per KU
                try:
                    r2 = conn.execute(
                        "MATCH (lr:LawOrRegulation) "
                        "WHERE lr.title CONTAINS $frag "
                        "RETURN lr.id LIMIT 1",
                        {"frag": ref_name[:15]}
                    )
                    if r2.has_next():
                        lr_id = str(r2.get_next()[0])
                        try:
                            conn.execute(
                                "MATCH (k:KnowledgeUnit {id: $kid}), (lr:LawOrRegulation {id: $lid}) "
                                "CREATE (k)-[:REFERENCES]->(lr)",
                                {"kid": item["id"], "lid": lr_id}
                            )
                            created += 1
                        except Exception:
                            pass
                except Exception:
                    pass

        if (offset + batch_size) % 2000 == 0:
            log.info("  Progress: %d/%d, +%d edges", offset + batch_size, total, created)

    log.info("  Done: +%d REFERENCES edges", created)
    return created


def task3_ku_related(conn) -> int:
    """Create RELATED edges between compliance matrix KU nodes sharing same tax type."""
    log.info("\n[Task 3] KU↔KU RELATED edges (same tax type within compliance matrix)")

    # Count compliance matrix nodes by type (which stores taxType)
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.source = 'compliance_matrix' "
        "RETURN k.type, count(k) ORDER BY count(k) DESC LIMIT 30"
    )
    type_counts = {}
    while r.has_next():
        row = r.get_next()
        type_counts[str(row[0])] = row[1]
    log.info("  Compliance matrix types: %d distinct", len(type_counts))

    created = 0
    # For each type group, connect nodes pairwise (max 20 per group to avoid N^2 explosion)
    for tp, cnt in type_counts.items():
        if cnt < 2:
            continue
        try:
            r = conn.execute(
                "MATCH (k:KnowledgeUnit) "
                "WHERE k.source = 'compliance_matrix' AND k.type = $tp "
                "RETURN k.id LIMIT 20",
                {"tp": tp}
            )
            ids = []
            while r.has_next():
                ids.append(str(r.get_next()[0]))

            # Connect each to next (chain, not full mesh)
            for i in range(len(ids) - 1):
                try:
                    conn.execute(
                        "MATCH (a:KnowledgeUnit {id: $a}), (b:KnowledgeUnit {id: $b}) "
                        "CREATE (a)-[:RELATED]->(b)",
                        {"a": ids[i], "b": ids[i + 1]}
                    )
                    created += 1
                except Exception:
                    pass
        except Exception:
            pass

    log.info("  Done: +%d RELATED edges", created)
    return created


def task4_part_of_backfill(conn) -> int:
    """Create PART_OF edges for LegalClause → LegalDocument using documentId."""
    log.info("\n[Task 4] LegalClause → LegalDocument PART_OF edges")

    r = conn.execute(
        "MATCH (c:LegalClause) "
        "WHERE c.documentId IS NOT NULL AND size(c.documentId) > 0 "
        "AND NOT EXISTS { MATCH (c)-[:PART_OF]->() } "
        "RETURN count(c)"
    )
    total = r.get_next()[0]
    log.info("  LegalClause without PART_OF: %d", total)

    created = 0
    batch_size = 500

    for offset in range(0, min(total, 100000), batch_size):
        r = conn.execute(
            "MATCH (c:LegalClause) "
            "WHERE c.documentId IS NOT NULL AND size(c.documentId) > 0 "
            "AND NOT EXISTS { MATCH (c)-[:PART_OF]->() } "
            "RETURN c.id, c.documentId "
            f"LIMIT {batch_size}"
        )

        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({"id": str(row[0]), "doc_id": str(row[1])})

        if not batch:
            break

        for item in batch:
            try:
                r2 = conn.execute(
                    "MATCH (ld:LegalDocument {id: $did}) RETURN ld.id",
                    {"did": item["doc_id"]}
                )
                if r2.has_next():
                    conn.execute(
                        "MATCH (c:LegalClause {id: $cid}), (ld:LegalDocument {id: $did}) "
                        "CREATE (c)-[:PART_OF]->(ld)",
                        {"cid": item["id"], "did": item["doc_id"]}
                    )
                    created += 1
            except Exception:
                pass

        if (offset + batch_size) % 5000 == 0:
            log.info("  Progress: %d/%d, +%d edges", offset + batch_size, total, created)

    log.info("  Done: +%d PART_OF edges", created)
    return created


def main():
    log.info("=" * 60)
    log.info("Edge Density Boost")
    log.info("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    t0 = time.time()

    # Pre-check
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    log.info("Before: %s nodes / %s edges / density %.3f", f"{nodes:,}", f"{edges:,}", edges / nodes)

    total_new = 0

    # Check if REFERENCES and RELATED edge tables exist
    try:
        conn.execute("MATCH ()-[e:REFERENCES]->() RETURN count(e) LIMIT 1")
    except Exception:
        log.info("Creating REFERENCES edge table...")
        conn.execute("CREATE REL TABLE IF NOT EXISTS REFERENCES (FROM KnowledgeUnit TO LawOrRegulation)")

    try:
        conn.execute("MATCH ()-[e:RELATED]->() RETURN count(e) LIMIT 1")
    except Exception:
        log.info("Creating RELATED edge table...")
        conn.execute("CREATE REL TABLE IF NOT EXISTS RELATED (FROM KnowledgeUnit TO KnowledgeUnit)")

    total_new += task1_ku_to_taxtype(conn)
    total_new += task2_regulation_refs(conn)
    total_new += task3_ku_related(conn)
    total_new += task4_part_of_backfill(conn)

    elapsed = time.time() - t0

    # Post-check
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]

    log.info("\n" + "=" * 60)
    log.info("Edge Boost Done (%.0fs)", elapsed)
    log.info("  New edges: +%d", total_new)
    log.info("  After: %s nodes / %s edges / density %.3f", f"{nodes:,}", f"{edges:,}", edges / nodes)


if __name__ == "__main__":
    main()
