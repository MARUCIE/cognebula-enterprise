#!/usr/bin/env python3
"""Ingest flk content trees into KG — update existing nodes + create clause edges.

Phase 1: Update 318 KnowledgeUnit nodes that have structure trees
Phase 2: Flatten tree into readable content + create LegalClause edges for density

Run from Mac:
    python3 scripts/flk_content_ingest.py [--host 100.88.170.57] [--dry-run]
"""
import argparse
import ast
import json
import logging
import os
import sys
import hashlib
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_ingest")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "recrawl")


def api_post(host, path, data, timeout=30):
    url = f"http://{host}:8400{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()[:200]}
    except Exception as e:
        return {"error": str(e)[:200]}


def escape_cypher(s):
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")


def flatten_tree(node, depth=0):
    lines = []
    title = node.get("title", "").strip()
    if title and title not in ("目录",):
        indent = "  " * depth
        lines.append(f"{indent}{title}")
    for child in node.get("children", []):
        lines.extend(flatten_tree(child, depth + 1))
    return lines


def count_tree_nodes(node):
    total = 1
    for c in node.get("children", []):
        total += count_tree_nodes(c)
    return total


def extract_clauses(node, law_title):
    clauses = []
    title = node.get("title", "").strip()
    if title and len(title) >= 3 and ("第" in title and "条" in title):
        clause_id = hashlib.sha256(f"flk:{law_title}:{title}".encode()).hexdigest()[:16]
        clauses.append({"id": clause_id, "title": f"{law_title} {title}", "clause_num": title})
    for child in node.get("children", []):
        clauses.extend(extract_clauses(child, law_title))
    return clauses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="100.88.170.57")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    content_path = os.path.join(DATA_DIR, "flk_with_content.jsonl")
    details_path = os.path.join(DATA_DIR, "flk_details.jsonl")

    with open(content_path) as f:
        content_items = [json.loads(l) for l in f if l.strip()]
    log.info("Loaded %d items with content trees", len(content_items))

    meta_lookup = {}
    if os.path.exists(details_path):
        with open(details_path) as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    meta_lookup[d.get("bbbs", "")] = d
        log.info("Loaded %d metadata records", len(meta_lookup))

    # ── Phase 1: Update content on existing KU nodes ────────────────
    log.info("=== Phase 1: Content update (%d items) ===", len(content_items))
    updated = 0
    errors = 0
    new_nodes = 0
    total_clauses = 0

    for i, item in enumerate(content_items):
        bbbs = item["bbbs"]
        title = item["title"]
        meta = meta_lookup.get(bbbs, {})

        try:
            tree = ast.literal_eval(item["content"])
        except (ValueError, SyntaxError):
            log.warning("  Bad tree for %s, skip", title[:30])
            errors += 1
            continue

        outline_lines = flatten_tree(tree)
        content_text = "\n".join(outline_lines)
        if len(content_text) < 20:
            continue

        law_type = meta.get("flxz", "法律")
        pub_date = meta.get("gbrq", "")
        eff_date = meta.get("sxrq", "")
        issuer = meta.get("zdjgName", "")
        header = f"[{law_type}] {title}"
        if issuer:
            header += f" | 发布机关: {issuer}"
        if pub_date:
            header += f" | 公布日期: {pub_date}"
        if eff_date:
            header += f" | 施行日期: {eff_date}"
        full_content = f"{header}\n\n{content_text}"

        eid = escape_cypher(bbbs)
        et = escape_cypher(title[:500])
        ec = escape_cypher(full_content[:5000])

        clauses = extract_clauses(tree, title)
        total_clauses += len(clauses)

        if args.dry_run:
            log.info("  [DRY] %s: %d tree nodes, %d clauses, %d chars",
                     title[:40], count_tree_nodes(tree), len(clauses), len(full_content))
            if i >= 4:
                log.info("  ... (showing first 5 only in dry-run)")
                break
            continue

        # Update content
        stmt = f"MATCH (k:KnowledgeUnit {{id: '{eid}'}}) SET k.content = '{ec}'"
        result = api_post(args.host, "/api/v1/admin/execute-ddl", {"statements": [stmt]})
        if "error" not in result:
            updated += 1
        else:
            create = (
                f"CREATE (k:KnowledgeUnit {{id: '{eid}', title: '{et}', "
                f"content: '{ec}', source: 'flk_npc', type: '{escape_cypher(law_type)}'}})"
            )
            result = api_post(args.host, "/api/v1/admin/execute-ddl", {"statements": [create]})
            if "error" not in result:
                new_nodes += 1
            else:
                errors += 1

        if (i + 1) % 50 == 0:
            log.info("  %d/%d: %d updated, %d new, %d errors",
                     i + 1, len(content_items), updated, new_nodes, errors)

    log.info("Phase 1 done: %d updated, %d new, %d errors", updated, new_nodes, errors)

    if args.dry_run:
        log.info("[DRY] Phase 2 would create ~%d clause nodes + edges", total_clauses)
        return

    # ── Phase 2: Create clause nodes + CLAUSE_OF edges ──────────────
    log.info("=== Phase 2: Clause nodes + edges (~%d) ===", total_clauses)
    clause_created = 0
    edge_created = 0

    for item in content_items:
        bbbs = item["bbbs"]
        title = item["title"]
        try:
            tree = ast.literal_eval(item["content"])
        except (ValueError, SyntaxError):
            continue

        clauses = extract_clauses(tree, title)
        if not clauses:
            continue

        parent_id = escape_cypher(bbbs)
        for clause in clauses:
            cid = escape_cypher(clause["id"])
            ct = escape_cypher(clause["title"][:300])

            stmt = (
                f"CREATE (c:KnowledgeUnit {{id: '{cid}', title: '{ct}', "
                f"content: '', source: 'flk_clause', type: 'clause'}})"
            )
            result = api_post(args.host, "/api/v1/admin/execute-ddl", {"statements": [stmt]})
            if "error" not in result:
                clause_created += 1

            edge_stmt = (
                f"MATCH (c:KnowledgeUnit {{id: '{cid}'}}), (p:KnowledgeUnit {{id: '{parent_id}'}}) "
                f"CREATE (c)-[:HAS_CLAUSE]->(p)"
            )
            result = api_post(args.host, "/api/v1/admin/execute-ddl", {"statements": [edge_stmt]})
            if "error" not in result:
                edge_created += 1

        if clause_created % 500 == 0 and clause_created > 0:
            log.info("  %d clauses, %d edges", clause_created, edge_created)

    log.info("Phase 2 done: %d clauses, %d edges", clause_created, edge_created)
    log.info("=== TOTAL: %d content updates + %d new + %d clauses + %d edges ===",
             updated, new_nodes, clause_created, edge_created)


if __name__ == "__main__":
    main()
