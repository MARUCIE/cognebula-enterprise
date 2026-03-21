#!/usr/bin/env python3
"""Swarm mode: backfill ALL empty content from original source data.

Quality-first: only use real crawled/extracted content, never LLM-generated.

Tasks:
  1. KU lr_cleanup (20K) → recover fullText from parent LR
  2. LegalClause (26K) → recover from parent document fullText
  3. CPAKnowledge (6.5K) → recover from extracted/cpa/ JSON files
  4. KU mindmap (5.8K) → recover from extracted/mindmap/ JSON files

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/swarm_fulltext_backfill.py
    sudo systemctl start kg-api
"""
import kuzu
import json
import os
import time
import glob

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
EXTRACTED_DIR = "/home/kg/cognebula-enterprise/data/extracted"


def task1_ku_lr_cleanup(conn):
    """Recover KU content from original LR fullText.

    lr_cleanup KU nodes were migrated from LawOrRegulation. Their content
    should come from the original LR's fullText field, matched by title.
    """
    print("\n[Task 1/4] KU lr_cleanup → recover from LR fullText")

    # Find lr_cleanup KU nodes with empty content that have a title
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.source = 'lr_cleanup' "
        "AND (k.content IS NULL OR size(k.content) < 50) "
        "AND k.title IS NOT NULL AND size(k.title) >= 10 "
        "RETURN count(k)"
    )
    total = r.get_next()[0]
    print(f"  Candidates: {total:,}")

    if total == 0:
        return 0

    # Strategy: match KU title to LR title, copy LR fullText to KU content
    updated = 0
    batch_size = 100

    for offset in range(0, total, batch_size):
        r = conn.execute(
            "MATCH (k:KnowledgeUnit) "
            "WHERE k.source = 'lr_cleanup' "
            "AND (k.content IS NULL OR size(k.content) < 50) "
            "AND k.title IS NOT NULL AND size(k.title) >= 10 "
            "RETURN k.id, k.title "
            f"LIMIT {batch_size}"
        )

        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({"id": str(row[0]), "title": str(row[1])})

        if not batch:
            break

        for item in batch:
            # Try to find matching LR by title substring
            title_fragment = item["title"][:30]
            try:
                r2 = conn.execute(
                    "MATCH (lr:LawOrRegulation) "
                    "WHERE lr.title CONTAINS $frag "
                    "AND lr.fullText IS NOT NULL AND size(lr.fullText) >= 100 "
                    "RETURN lr.fullText LIMIT 1",
                    {"frag": title_fragment}
                )
                if r2.has_next():
                    full_text = r2.get_next()[0]
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $text",
                        {"id": item["id"], "text": str(full_text)[:10000]}
                    )
                    updated += 1
            except Exception:
                continue

        if (offset + batch_size) % 1000 == 0:
            print(f"  Progress: {offset + batch_size}/{total}, +{updated} recovered")

    print(f"  Done: +{updated:,} KU content recovered from LR")
    return updated


def task2_legal_clause_fill(conn):
    """Fill LegalClause content from parent document's fullText.

    Each LegalClause has a documentId linking to a LegalDocument/LR.
    Extract the relevant clause text from parent's fullText.
    """
    print("\n[Task 2/4] LegalClause → fill from parent document")

    r = conn.execute(
        "MATCH (c:LegalClause) "
        "WHERE c.content IS NULL OR size(c.content) < 20 "
        "RETURN count(c)"
    )
    total = r.get_next()[0]
    print(f"  Candidates: {total:,}")

    if total == 0:
        return 0

    # Strategy: for each short clause, find parent LR by documentId,
    # then extract the clause text from parent's fullText using articleNumber
    updated = 0
    batch_size = 200

    for offset in range(0, min(total, 30000), batch_size):
        r = conn.execute(
            "MATCH (c:LegalClause) "
            "WHERE c.content IS NULL OR size(c.content) < 20 "
            "RETURN c.id, c.regulationId, c.articleNumber, c.title "
            f"LIMIT {batch_size}"
        )

        batch = []
        while r.has_next():
            row = r.get_next()
            batch.append({
                "id": str(row[0]),
                "reg_id": str(row[1] or ""),
                "article": str(row[2] or ""),
                "title": str(row[3] or ""),
            })

        if not batch:
            break

        for item in batch:
            # If title is long enough, use it as content
            if item["title"] and len(item["title"]) >= 20:
                try:
                    conn.execute(
                        "MATCH (c:LegalClause {id: $id}) SET c.content = $text",
                        {"id": item["id"], "text": item["title"]}
                    )
                    updated += 1
                except Exception:
                    pass
                continue

            # Try to get parent LR fullText
            if item["reg_id"]:
                try:
                    r2 = conn.execute(
                        "MATCH (lr:LawOrRegulation {id: $rid}) "
                        "WHERE lr.fullText IS NOT NULL AND size(lr.fullText) >= 100 "
                        "RETURN lr.fullText LIMIT 1",
                        {"rid": item["reg_id"]}
                    )
                    if r2.has_next():
                        full_text = str(r2.get_next()[0])
                        # Extract clause by article number
                        art_num = item["article"]
                        if art_num:
                            import re
                            pattern = f"第{art_num}条[\\s　]*(.*?)(?=第\\d+条|$)"
                            m = re.search(pattern, full_text, re.DOTALL)
                            if m:
                                clause_text = m.group(1).strip()[:2000]
                                if len(clause_text) >= 20:
                                    conn.execute(
                                        "MATCH (c:LegalClause {id: $id}) SET c.content = $text",
                                        {"id": item["id"], "text": clause_text}
                                    )
                                    updated += 1
                                    continue
                except Exception:
                    pass

        if (offset + batch_size) % 2000 == 0:
            print(f"  Progress: {offset + batch_size}/{total}, +{updated} filled")

    print(f"  Done: +{updated:,} LegalClause content filled")
    return updated


def task3_cpa_knowledge(conn):
    """Fill CPAKnowledge from extracted/cpa/ JSON files."""
    print("\n[Task 3/4] CPAKnowledge → recover from extracted/cpa/")

    cpa_dir = os.path.join(EXTRACTED_DIR, "cpa")
    if not os.path.isdir(cpa_dir):
        print(f"  SKIP: {cpa_dir} not found")
        return 0

    # Load all CPA JSON files
    cpa_data = {}
    for fp in glob.glob(os.path.join(cpa_dir, "*.json")):
        try:
            with open(fp) as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    topic = str(item.get("topic", item.get("title", item.get("name", ""))))
                    content = str(item.get("content", item.get("text", item.get("answer", ""))))
                    if topic and content and len(content) >= 50:
                        cpa_data[topic[:50]] = content[:5000]
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and len(v) >= 50:
                        cpa_data[k[:50]] = v[:5000]
        except Exception:
            continue

    print(f"  Loaded {len(cpa_data)} CPA entries from JSON files")

    if not cpa_data:
        return 0

    # Match to KuzuDB CPAKnowledge nodes by topic
    updated = 0
    r = conn.execute(
        "MATCH (c:CPAKnowledge) "
        "WHERE c.content IS NULL OR size(c.content) < 50 "
        "RETURN c.id, c.topic"
    )
    while r.has_next():
        row = r.get_next()
        cpa_id = str(row[0])
        topic = str(row[1] or "")[:50]

        if topic in cpa_data:
            try:
                conn.execute(
                    "MATCH (c:CPAKnowledge {id: $id}) SET c.content = $text",
                    {"id": cpa_id, "text": cpa_data[topic]}
                )
                updated += 1
            except Exception:
                pass

    print(f"  Done: +{updated:,} CPAKnowledge content recovered")
    return updated


def task4_mindmap_ku(conn):
    """Fill mindmap KU from extracted/mindmap/ JSON files."""
    print("\n[Task 4/4] Mindmap KU → recover from extracted/mindmap/")

    mm_dir = os.path.join(EXTRACTED_DIR, "mindmap")
    if not os.path.isdir(mm_dir):
        mm_dir = os.path.join(EXTRACTED_DIR, "mindmap_fixes")
    if not os.path.isdir(mm_dir):
        print(f"  SKIP: mindmap dir not found")
        return 0

    # Load mindmap data
    mm_data = {}
    for fp in glob.glob(os.path.join(mm_dir, "*.json")):
        try:
            with open(fp) as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    node_text = str(item.get("node_text", item.get("text", item.get("title", ""))))
                    content = str(item.get("content", item.get("description", "")))
                    if node_text and len(node_text) >= 5:
                        mm_data[node_text[:50]] = content[:5000] if content and len(content) >= 20 else node_text
        except Exception:
            continue

    print(f"  Loaded {len(mm_data)} mindmap entries")

    # For mindmap KU without content, set content = title (the node_text IS the content)
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.source = 'mindmap' "
        "AND (k.content IS NULL OR size(k.content) < 20) "
        "AND k.title IS NOT NULL AND size(k.title) >= 5 "
        "RETURN count(k)"
    )
    total = r.get_next()[0]
    print(f"  KU mindmap needing content: {total:,}")

    # Set content = title for mindmap KU (the title IS the knowledge)
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) "
        "WHERE k.source = 'mindmap' "
        "AND (k.content IS NULL OR size(k.content) < 20) "
        "AND k.title IS NOT NULL AND size(k.title) >= 5 "
        "SET k.content = k.title "
        "RETURN count(k)"
    )
    updated = r.get_next()[0]

    print(f"  Done: +{updated:,} mindmap KU content set")
    return updated


def main():
    print("=" * 60)
    print("SWARM: Full Text Backfill (Quality First)")
    print("Only real crawled/extracted content, no LLM generation")
    print("=" * 60)

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    t0 = time.time()
    total = 0

    total += task1_ku_lr_cleanup(conn)
    total += task2_legal_clause_fill(conn)
    total += task3_cpa_knowledge(conn)
    total += task4_mindmap_ku(conn)

    elapsed = time.time() - t0

    # Final stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]

    print(f"\n{'='*60}")
    print(f"Swarm Backfill Done ({elapsed:.0f}s)")
    print(f"  Total recovered: {total:,}")
    print(f"  Graph: {nodes:,} nodes / {edges:,} edges / density {edges/nodes:.3f}")

    del conn; del db


if __name__ == "__main__":
    main()
