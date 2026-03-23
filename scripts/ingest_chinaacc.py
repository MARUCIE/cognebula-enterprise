"""Ingest chinaacc (会计学习网) 2,092 items + local-doctax 1,424 items into KU.
No reconnect.
"""
import json, os, hashlib, kuzu

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DATA_DIR = "/home/kg/cognebula-enterprise/data"

# Wait for QA gen to release DB lock
import time
for attempt in range(5):
    try:
        db = kuzu.Database(DB_PATH)
        conn = kuzu.Connection(db)
        print("DB connected")
        break
    except:
        print(f"DB locked (attempt {attempt+1}), waiting 10s...")
        time.sleep(10)
else:
    print("ERROR: DB still locked after 5 attempts")
    exit(1)

writes = 0

def safe_create_ku(node_id, title, content, source):
    global writes
    content = content[:3000]
    if len(content) < 100 or len(title) < 5:
        return False
    try:
        # Check if exists
        r = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": node_id})
        if r.has_next():
            # Update content if better
            r2 = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN CASE WHEN k.content IS NOT NULL THEN size(k.content) ELSE 0 END", {"id": node_id})
            if r2.has_next() and r2.get_next()[0] < len(content):
                conn.execute("MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c", {"id": node_id, "c": content})
                writes += 1
                if writes % 50 == 0: conn.execute("CHECKPOINT")
                return True
        else:
            # Create new
            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $id, title: $t, content: $c, source: $s})",
                {"id": node_id, "t": title[:200], "c": content, "s": source}
            )
            writes += 1
            if writes % 50 == 0: conn.execute("CHECKPOINT")
            return True
    except Exception as e:
        if writes == 0:
            print(f"  Error: {str(e)[:100]}")
    return False

r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
before = r.get_next()[0]
r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
total_before = r.get_next()[0]
print(f"Before: {before}/{total_before}")

# 1. chinaacc-v2
print("\n[1] chinaacc-v2 (2092 items)...")
chinaacc_path = os.path.join(DATA_DIR, "raw/20260315-chinaacc-v2/chinaacc.json")
created = 0
if os.path.exists(chinaacc_path):
    with open(chinaacc_path) as f:
        data = json.load(f)
    for item in data:
        title = item.get("title", "")
        content = item.get("content", "") or item.get("text", "") or ""
        iid = item.get("id", "") or hashlib.sha256(f"chinaacc:{title}".encode()).hexdigest()[:16]
        node_id = f"KU_chinaacc_{iid}"
        if safe_create_ku(node_id, title, content, "chinaacc"):
            created += 1
    conn.execute("CHECKPOINT")
    print(f"  chinaacc: +{created}")

# 2. local-doctax
print("\n[2] local-doctax (1424 items)...")
doctax_path = os.path.join(DATA_DIR, "raw/local-doctax/local_docs.json")
created2 = 0
if os.path.exists(doctax_path):
    with open(doctax_path) as f:
        data = json.load(f)
    for item in data:
        title = item.get("title", "") or item.get("name", "")
        content = item.get("content", "") or item.get("text", "") or ""
        iid = item.get("id", "") or hashlib.sha256(f"doctax:{title}".encode()).hexdigest()[:16]
        node_id = f"KU_doctax_{iid}"
        if safe_create_ku(node_id, title, content, "local_doctax"):
            created2 += 1
    conn.execute("CHECKPOINT")
    print(f"  local-doctax: +{created2}")

# Final
r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
after = r.get_next()[0]
r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
total_after = r.get_next()[0]

print(f"\n=== DONE ===")
print(f"KU: {total_before} -> {total_after} (+{total_after-total_before})")
print(f"Content>=100c: {before} -> {after} (+{after-before})")
print(f"Coverage: {100*after/total_after:.1f}%")

del conn, db
