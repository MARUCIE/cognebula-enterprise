#!/usr/bin/env python3
"""Create ALL clause nodes THEN edges. Batched DDL for speed."""
import ast, json, logging, os, sys, hashlib, time
import urllib.request, urllib.error

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk")

HOST = sys.argv[1] if len(sys.argv) > 1 else "100.88.170.57"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "recrawl")
BATCH = 10


def api(path, data, timeout=60):
    url = f"http://{HOST}:8400{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)[:200]}


def esc(s):
    if not s: return ""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")


def get_clauses(node, law_title):
    out = []
    t = node.get("title", "").strip()
    if t and len(t) >= 3 and "第" in t and "条" in t:
        cid = hashlib.sha256(f"flk:{law_title}:{t}".encode()).hexdigest()[:16]
        out.append({"id": cid, "title": f"{law_title} {t}"})
    for c in node.get("children", []):
        out.extend(get_clauses(c, law_title))
    return out


def send_batch(stmts):
    ok = err = 0
    for i in range(0, len(stmts), BATCH):
        batch = stmts[i:i+BATCH]
        r = api("/api/v1/admin/execute-ddl", {"statements": batch})
        if "error" not in r:
            ok += r.get("ok", 0)
            err += r.get("errors", 0)
        else:
            err += len(batch)
    return ok, err


def main():
    with open(os.path.join(DATA_DIR, "flk_with_content.jsonl")) as f:
        items = [json.loads(l) for l in f if l.strip()]
    log.info("Loaded %d items", len(items))

    # Collect ALL clause data
    all_clauses = []  # (clause_id, clause_title, parent_bbbs)
    for item in items:
        try:
            tree = ast.literal_eval(item["content"])
        except (ValueError, SyntaxError):
            continue
        for cl in get_clauses(tree, item["title"]):
            all_clauses.append((cl["id"], cl["title"], item["bbbs"]))

    log.info("Total clauses to create: %d", len(all_clauses))

    # ── Step 1: Create ALL clause nodes ─────────────────────────────
    log.info("=== Step 1: Create clause nodes ===")
    create_stmts = []
    for cid, ct, _ in all_clauses:
        create_stmts.append(
            f"CREATE (c:KnowledgeUnit {{id: '{esc(cid)}', title: '{esc(ct[:300])}', "
            f"content: '', source: 'flk_clause', type: 'clause'}})"
        )

    n_ok, n_err = send_batch(create_stmts)
    log.info("Nodes: %d ok, %d err (duplicates expected)", n_ok, n_err)

    # ── Step 2: Create ALL HAS_CLAUSE edges ─────────────────────────
    log.info("=== Step 2: Create HAS_CLAUSE edges ===")
    edge_stmts = []
    for cid, _, pid in all_clauses:
        edge_stmts.append(
            f"MATCH (c:KnowledgeUnit {{id: '{esc(cid)}'}}), (p:KnowledgeUnit {{id: '{esc(pid)}'}}) "
            f"CREATE (c)-[:HAS_CLAUSE]->(p)"
        )

    e_ok, e_err = send_batch(edge_stmts)
    log.info("Edges: %d ok, %d err", e_ok, e_err)
    log.info("=== DONE: %d nodes + %d edges ===", n_ok, e_ok)


if __name__ == "__main__":
    main()
