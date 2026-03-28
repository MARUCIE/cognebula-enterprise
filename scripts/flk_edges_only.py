#!/usr/bin/env python3
"""Phase 2 only: create HAS_CLAUSE edges for 461 existing flk_clause nodes.

Batch mode: send multiple DDL statements per request for speed.
"""
import ast, json, logging, os, sys, hashlib, urllib.request, urllib.error

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_edges")

HOST = sys.argv[1] if len(sys.argv) > 1 else "100.88.170.57"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "recrawl")
BATCH_SIZE = 10


def api_post(path, data, timeout=60):
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


def extract_clauses(node, law_title):
    clauses = []
    t = node.get("title", "").strip()
    if t and len(t) >= 3 and "第" in t and "条" in t:
        cid = hashlib.sha256(f"flk:{law_title}:{t}".encode()).hexdigest()[:16]
        clauses.append({"id": cid, "title": f"{law_title} {t}"})
    for c in node.get("children", []):
        clauses.extend(extract_clauses(c, law_title))
    return clauses


def main():
    with open(os.path.join(DATA_DIR, "flk_with_content.jsonl")) as f:
        items = [json.loads(l) for l in f if l.strip()]
    log.info("Loaded %d items", len(items))

    edge_ok = 0
    edge_err = 0
    total_stmts = 0

    for idx, item in enumerate(items):
        bbbs = item["bbbs"]
        title = item["title"]
        try:
            tree = ast.literal_eval(item["content"])
        except (ValueError, SyntaxError):
            continue

        clauses = extract_clauses(tree, title)
        if not clauses:
            continue

        pid = esc(bbbs)
        stmts = []
        for cl in clauses:
            cid = esc(cl["id"])
            stmts.append(
                f"MATCH (c:KnowledgeUnit {{id: '{cid}'}}), (p:KnowledgeUnit {{id: '{pid}'}}) "
                f"CREATE (c)-[:HAS_CLAUSE]->(p)"
            )

        # Send in batches
        for i in range(0, len(stmts), BATCH_SIZE):
            batch = stmts[i:i+BATCH_SIZE]
            result = api_post("/api/v1/admin/execute-ddl", {"statements": batch})
            if "error" not in result:
                ok = result.get("ok", 0)
                edge_ok += ok
                edge_err += len(batch) - ok
            else:
                edge_err += len(batch)
            total_stmts += len(batch)

        if (idx + 1) % 50 == 0:
            log.info("  %d/%d laws: %d edges OK, %d err (%d stmts sent)",
                     idx + 1, len(items), edge_ok, edge_err, total_stmts)

    log.info("DONE: %d edges OK, %d errors (%d total stmts)", edge_ok, edge_err, total_stmts)


if __name__ == "__main__":
    main()
