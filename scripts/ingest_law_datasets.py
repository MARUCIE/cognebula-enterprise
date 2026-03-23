"""Ingest law-datasets 509 tax laws content into flk_npc KU nodes.

Match by title. No reconnect (8GB VPS safety).
"""
import json
import kuzu
import time

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
LAW_PATH = "/home/kg/cognebula-enterprise/data/law-datasets/laws_tax_filtered.json"

db = kuzu.Database(DB_PATH)
conn = kuzu.Connection(db)

with open(LAW_PATH) as f:
    laws = json.load(f)

print(f"Loaded {len(laws)} laws")

# Pre-flight
r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.source = 'flk_npc' AND k.content IS NOT NULL AND size(k.content) >= 100 RETURN count(k)")
before = r.get_next()[0]
print(f"Before: {before} flk_npc KU with content>=100c")

updated = 0
not_found = 0
skipped = 0
writes = 0

for i, law in enumerate(laws):
    title = law.get("title", "").strip()
    content = law.get("content", "")
    if len(content) < 100 or len(title) < 5:
        skipped += 1
        continue

    content = content[:3000]

    # Find matching KU by title
    r = conn.execute(
        "MATCH (k:KnowledgeUnit) WHERE k.title = $t RETURN k.id, CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END LIMIT 1",
        {"t": title}
    )
    if r.has_next():
        row = r.get_next()
        kid = str(row[0])
        existing_len = row[1]
        if existing_len < len(content):
            conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                {"id": kid, "c": content}
            )
            writes += 1
            updated += 1
            if writes % 50 == 0:
                conn.execute("CHECKPOINT")
        else:
            skipped += 1
    else:
        # Try partial title match
        short_title = title[:20]
        r2 = conn.execute(
            "MATCH (k:KnowledgeUnit) WHERE contains(k.title, $t) AND k.source = 'flk_npc' RETURN k.id, CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END LIMIT 1",
            {"t": short_title}
        )
        if r2.has_next():
            row = r2.get_next()
            kid = str(row[0])
            existing_len = row[1]
            if existing_len < len(content):
                conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                    {"id": kid, "c": content}
                )
                writes += 1
                updated += 1
                if writes % 50 == 0:
                    conn.execute("CHECKPOINT")
            else:
                skipped += 1
        else:
            not_found += 1

    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(laws)}: updated={updated}, not_found={not_found}, skipped={skipped}")

# Final checkpoint
conn.execute("CHECKPOINT")

r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.source = 'flk_npc' AND k.content IS NOT NULL AND size(k.content) >= 100 RETURN count(k)")
after = r.get_next()[0]

r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content) >= 100 RETURN count(k)")
total_good = r.get_next()[0]
r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
total_ku = r.get_next()[0]

print(f"\n=== DONE ===")
print(f"Updated: {updated} | Not found: {not_found} | Skipped: {skipped}")
print(f"flk_npc content: {before} -> {after}")
print(f"Total KU coverage: {total_good}/{total_ku} ({100*total_good/total_ku:.1f}%)")

del conn, db
