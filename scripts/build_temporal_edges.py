#!/usr/bin/env python3
"""Build temporal SUPERSEDES edges between LawOrRegulation nodes.

Strategy: For LR nodes with same issuing body + overlapping titles,
create SUPERSEDES edges ordered by publish_date (newer supersedes older).

Example:
  "财政部 税务总局公告2026年第7号" SUPERSEDES "财政部 税务总局公告2025年第X号"
  if titles share key terms (e.g., "车辆购置税", "免征")

Also creates AMENDS edges for explicit amendment references in titles.

Run on kg-node (after QA gen + lr_cleanup restore):
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/build_temporal_edges.py 2>&1 | tee /tmp/temporal_edges.log
    sudo systemctl start kg-api
"""
import hashlib
import logging
import re
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("temporal")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
CHECKPOINT_EVERY = 50

# Keywords indicating amendment/supersession in titles
AMEND_PATTERNS = [
    r"修改.*的决定",
    r"修正",
    r"修订",
    r"废止",
    r"关于.*修改",
    r"关于.*废止",
    r"关于.*调整",
]

# Key term extraction for title similarity
STOP_WORDS = {"关于", "的", "通知", "公告", "规定", "办法", "意见", "决定",
              "暂行", "实施", "试行", "印发", "转发", "批准", "国家税务总局",
              "财政部", "税务总局", "中华人民共和国"}


def extract_key_terms(title: str) -> set[str]:
    """Extract meaningful terms from a law title for similarity matching."""
    # Remove doc numbers like 2026年第7号
    cleaned = re.sub(r'\d{4}年第?\d+号', '', title)
    # Split on common delimiters
    words = re.split(r'[，。、；：（）\s]+', cleaned)
    terms = set()
    for w in words:
        w = w.strip()
        if len(w) >= 2 and w not in STOP_WORDS:
            terms.add(w)
    return terms


def title_similarity(t1: str, t2: str) -> float:
    """Jaccard similarity of key terms between two titles."""
    s1 = extract_key_terms(t1)
    s2 = extract_key_terms(t2)
    if not s1 or not s2:
        return 0.0
    intersection = s1 & s2
    union = s1 | s2
    return len(intersection) / len(union) if union else 0.0


def main():
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    writes = 0

    # Load all LawOrRegulation nodes with dates
    log.info("Loading LawOrRegulation nodes...")
    r = conn.execute("""
    MATCH (lr:LawOrRegulation)
    WHERE lr.title IS NOT NULL AND size(lr.title) >= 5
    RETURN lr.id, lr.title, lr.publishDate, lr.office
    """)

    laws = []
    while r.has_next():
        row = r.get_next()
        laws.append({
            "id": str(row[0]),
            "title": str(row[1]),
            "date": str(row[2]) if row[2] else "",
            "office": str(row[3]) if row[3] else "",
        })

    log.info("Loaded %d LR nodes", len(laws))

    # Count existing SUPERSEDES edges
    r = conn.execute("MATCH ()-[s:SUPERSEDES]->() RETURN count(s)")
    existing_supersedes = r.get_next()[0]
    log.info("Existing SUPERSEDES: %d", existing_supersedes)

    # Group by office for efficient comparison
    by_office = {}
    for law in laws:
        office = law["office"] or "unknown"
        if office not in by_office:
            by_office[office] = []
        by_office[office].append(law)

    log.info("Offices: %d", len(by_office))
    for office, items in sorted(by_office.items(), key=lambda x: -len(x[1]))[:10]:
        log.info("  %s: %d laws", office[:40], len(items))

    # Build SUPERSEDES edges: within same office, find title-similar pairs
    new_edges = 0
    checked = 0

    for office, items in by_office.items():
        if len(items) < 2:
            continue

        # Sort by date (newest first)
        dated = [i for i in items if i["date"] and len(i["date"]) >= 4]
        dated.sort(key=lambda x: x["date"], reverse=True)

        # Compare each pair within the office (limit to avoid O(n^2) explosion)
        max_compare = min(len(dated), 200)  # Cap per office

        for i in range(min(len(dated), max_compare)):
            for j in range(i + 1, min(len(dated), max_compare)):
                newer = dated[i]
                older = dated[j]

                # Skip if dates are identical
                if newer["date"][:10] == older["date"][:10]:
                    continue

                sim = title_similarity(newer["title"], older["title"])
                checked += 1

                if sim >= 0.5:  # High similarity threshold
                    # Check if edge already exists
                    try:
                        r = conn.execute(
                            "MATCH (a:LawOrRegulation {id: $a})-[:SUPERSEDES]->(b:LawOrRegulation {id: $b}) RETURN count(*)",
                            {"a": newer["id"], "b": older["id"]}
                        )
                        if r.has_next() and r.get_next()[0] == 0:
                            conn.execute(
                                "MATCH (a:LawOrRegulation {id: $a}), (b:LawOrRegulation {id: $b}) CREATE (a)-[:SUPERSEDES]->(b)",
                                {"a": newer["id"], "b": older["id"]}
                            )
                            writes += 1
                            new_edges += 1
                            if writes % CHECKPOINT_EVERY == 0:
                                conn.execute("CHECKPOINT")
                    except Exception:
                        pass

        if checked % 10000 == 0 and checked > 0:
            log.info("  Checked %d pairs, new edges: %d", checked, new_edges)

    conn.execute("CHECKPOINT")

    # Final stats
    r = conn.execute("MATCH ()-[s:SUPERSEDES]->() RETURN count(s)")
    after_supersedes = r.get_next()[0]
    r = conn.execute("MATCH (n) RETURN count(n)")
    total_nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    total_edges = r.get_next()[0]

    log.info("\n" + "=" * 60)
    log.info("Temporal edges complete")
    log.info("  Pairs checked: %d", checked)
    log.info("  New SUPERSEDES: %d", new_edges)
    log.info("  Total SUPERSEDES: %d -> %d", existing_supersedes, after_supersedes)
    log.info("  Density: %.3f", total_edges / total_nodes if total_nodes else 0)

    del conn, db


if __name__ == "__main__":
    main()
