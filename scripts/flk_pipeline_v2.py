#!/usr/bin/env python3
"""Full flk pipeline: create nodes → generate content → ingest.

Phase 1: Create KnowledgeUnit nodes for all items in flk_details.jsonl
Phase 2: Generate content via Poe LLM for items without content
Phase 3: Ingest generated content back into KG

Run on VPS (needs direct kuzu access, kg-api must be stopped):
    systemctl stop kg-api
    python3 scripts/flk_pipeline_v2.py [--phase 1|2|3|all] [--limit 100]
"""
import json, os, sys, time, re

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
DETAILS = "/home/kg/cognebula-enterprise/data/recrawl/flk_details.jsonl"
CONTENT_OUT = "/home/kg/cognebula-enterprise/data/backfill/flk_content_poe_v2.jsonl"
BATCH_SIZE = 8

# Load env
for p in ["/home/kg/.env.kg-api"]:
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, "/home/kg/cognebula-enterprise/scripts")

# Parse args
phase = "all"
limit = None
for i, a in enumerate(sys.argv):
    if a == "--phase" and i + 1 < len(sys.argv):
        phase = sys.argv[i + 1]
    if a == "--limit" and i + 1 < len(sys.argv):
        limit = int(sys.argv[i + 1])


def load_details():
    items = []
    with open(DETAILS) as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items


def phase1_create_nodes():
    """Create KnowledgeUnit nodes for items not yet in KG."""
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    items = load_details()
    print(f"[Phase 1] Loaded {len(items)} detail records")

    # Check existing nodes
    existing = set()
    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.id STARTS WITH 'KU_flk_' RETURN k.id")
    while r.has_next():
        existing.add(r.get_next()[0])
    print(f"  Existing KU_flk_ nodes: {len(existing)}")

    to_create = []
    for it in items:
        bbbs = it.get("bbbs", "")
        if not bbbs:
            continue
        node_id = "KU_flk_" + bbbs[:16]
        if node_id not in existing:
            to_create.append(it)

    if limit:
        to_create = to_create[:limit]
    print(f"  To create: {len(to_create)}")

    created = 0
    errors = 0
    t0 = time.time()

    for i, it in enumerate(to_create):
        bbbs = it["bbbs"]
        node_id = "KU_flk_" + bbbs[:16]
        title = it.get("title", "")[:500].replace("'", "\\'")
        flxz = it.get("flxz", "法规").replace("'", "\\'")
        gbrq = it.get("gbrq", "")
        zdjg = it.get("zdjgName", "").replace("'", "\\'")

        try:
            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $nid, title: $t, content: '', "
                "source: 'flk_npc', type: $tp})",
                {"nid": node_id, "t": title, "tp": flxz}
            )
            created += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  err: {str(e)[:80]}")

        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(to_create)}: {created} ok, {errors} err ({time.time()-t0:.0f}s)")

    print(f"  Phase 1 done: {created} created, {errors} errors ({time.time()-t0:.0f}s)")
    return created


def phase2_generate_content():
    """Generate content via Poe LLM for items without content."""
    from llm_client import llm_generate

    items = load_details()
    print(f"[Phase 2] Loaded {len(items)} detail records")

    # Load already-generated content
    done = set()
    if os.path.exists(CONTENT_OUT):
        with open(CONTENT_OUT) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["bbbs"])
                except Exception:
                    pass
    # Also check old content file
    old_out = "/home/kg/cognebula-enterprise/data/backfill/flk_content_poe.jsonl"
    if os.path.exists(old_out):
        with open(old_out) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["bbbs"])
                except Exception:
                    pass
    print(f"  Already generated: {len(done)}")

    # Filter to items needing content
    pending = [it for it in items if it["bbbs"] not in done and not it.get("has_content")]
    if limit:
        pending = pending[:limit]
    print(f"  Pending: {len(pending)}")

    if not pending:
        print("  Nothing to do!")
        return 0

    outf = open(CONTENT_OUT, "a", encoding="utf-8")
    total = 0
    t0 = time.time()
    n_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    for bi in range(n_batches):
        batch = pending[bi * BATCH_SIZE:(bi + 1) * BATCH_SIZE]
        if not batch:
            break

        lines = []
        for j, it in enumerate(batch):
            meta = f"[{it.get('flxz', '法规')}] {it['title']}"
            if it.get("zdjgName"):
                meta += f" (发布机关: {it['zdjgName']})"
            if it.get("gbrq"):
                meta += f" (公布: {it['gbrq']})"
            lines.append(f"[{j+1}] {meta}")

        prompt = (
            "你是中国法律法规专家。请为以下法律法规各生成一段权威摘要。\n\n"
            + "\n".join(lines)
            + "\n\n要求：\n"
            "1. 每段 200-500 字中文\n"
            "2. 涵盖：立法目的、适用范围、核心条款、实务影响\n"
            "3. 引用具体条文编号（如有）\n"
            "4. 用 [1] [2] [3] ... 编号分隔\n"
            "5. 直接输出，不加额外标题"
        )
        raw = llm_generate(prompt, model="gemini-3.1-pro", max_tokens=8000, temperature=0.3)
        if raw.startswith("[ERROR]"):
            if total <= 3:
                print(f"  LLM error: {raw[:100]}")
            time.sleep(1)
            continue

        sections = re.split(r'\[(\d+)\]', raw)
        for k in range(1, len(sections) - 1, 2):
            try:
                idx = int(sections[k]) - 1
                content = sections[k + 1].strip()
                if idx < len(batch) and len(content) >= 100:
                    record = {
                        "bbbs": batch[idx]["bbbs"],
                        "title": batch[idx]["title"],
                        "content": content[:5000],
                        "source": "flk_npc",
                        "type": batch[idx].get("flxz", ""),
                    }
                    outf.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total += 1
            except (ValueError, IndexError):
                continue

        if (bi + 1) % 50 == 0:
            outf.flush()
            elapsed = time.time() - t0
            rate = total / elapsed * 3600 if elapsed > 0 else 0
            print(f"  Batch {bi+1}/{n_batches}: +{total} ({rate:.0f}/hr)")

        time.sleep(0.3)

    outf.close()
    print(f"  Phase 2 done: {total} items ({time.time()-t0:.0f}s)")
    return total


def phase3_ingest():
    """Ingest generated content into KG."""
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    files = [
        (CONTENT_OUT, "bbbs"),
        ("/home/kg/cognebula-enterprise/data/backfill/flk_content_poe.jsonl", "bbbs"),
    ]

    total_ok = 0
    for fpath, id_key in files:
        if not os.path.exists(fpath):
            continue
        name = os.path.basename(fpath)

        items = []
        with open(fpath) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("content") and len(d["content"]) >= 80:
                        items.append(d)
                except Exception:
                    pass

        if limit:
            items = items[:limit]
        print(f"[Phase 3] {name}: {len(items)} items")

        ok = skip = 0
        t0 = time.time()
        for i, item in enumerate(items):
            node_id = item.get(id_key, "")
            if not node_id:
                skip += 1
                continue
            if id_key == "bbbs":
                node_id = "KU_flk_" + node_id[:16]

            content = item["content"][:5000]
            try:
                conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $nid}) SET k.content = $c",
                    {"nid": node_id, "c": content}
                )
                ok += 1
            except Exception:
                skip += 1

            if (i + 1) % 2000 == 0:
                print(f"  {i+1}/{len(items)}: {ok} ok, {skip} skip")

        print(f"  {name}: {ok} ok, {skip} skip ({time.time()-t0:.0f}s)")
        total_ok += ok

    # Final stats
    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content) >= 50 RETURN count(k)")
    while r.has_next():
        print(f"\nKU with content >= 50 chars: {r.get_next()[0]}")
    r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    while r.has_next():
        print(f"Total KU: {r.get_next()[0]}")

    return total_ok


def main():
    print(f"=== flk Pipeline v2 (phase={phase}) ===")
    print(f"DB: {DB_PATH}")
    print(f"Details: {DETAILS}")

    if phase in ("1", "all"):
        phase1_create_nodes()
    if phase in ("2", "all"):
        phase2_generate_content()
    if phase in ("3", "all"):
        phase3_ingest()

    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    main()
