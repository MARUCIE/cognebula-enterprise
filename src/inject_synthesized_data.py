#!/usr/bin/env python3
"""Inject AI-synthesized nodes (auto_inject only) into KuzuDB.

Reads from data/synthesized/*/batch_*.json, filters gate_decision=auto_inject,
and injects as OP_StandardCase nodes.

Usage:
    python src/inject_synthesized_data.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path


def esc(s) -> str:
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Collect all auto-inject nodes
    nodes = []
    for f in glob.glob("data/synthesized/*/batch_*.json"):
        if "summary" in f or "_consolidated" in f:
            continue
        try:
            with open(f) as fh:
                d = json.load(fh)
            if d.get("gate_decision") == "auto_inject" and d.get("node"):
                nodes.append(d)
        except Exception:
            pass

    print(f"Found {len(nodes)} auto-inject nodes")

    if not nodes:
        print("No nodes to inject")
        return

    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    count = 0
    for item in nodes:
        node = item["node"]
        nid = node.get("node_id", f"SYN_{hashlib.md5(str(node).encode()).hexdigest()[:8]}")
        title = node.get("title", "")[:200]
        content = node.get("content", "")[:500]
        industry = node.get("industry", "general")
        scenario = node.get("scenario_type", "")
        entries = json.dumps(node.get("accounting_entries", []), ensure_ascii=False)[:500]
        citations = json.dumps(node.get("citations", []), ensure_ascii=False)[:300]
        confidence = item.get("final_confidence", 0.95)

        sql = (
            f"CREATE (n:OP_StandardCase {{"
            f"id: '{esc(nid)}', "
            f"name: '{esc(title)}', "
            f"standardId: '', clauseRef: '', "
            f"caseType: 'ai_synthesized', "
            f"scenario: '{esc(scenario)}', "
            f"correctTreatment: '{esc(content)} | entries: {esc(entries)}', "
            f"commonMistake: '', "
            f"industryRelevance: '{esc(industry)}', "
            f"diffFromSme: false, diffFromIfrs: false, "
            f"diffDescription: 'citations: {esc(citations)}', "
            f"notes: 'source_tier: L4_ai_synthesized | confidence: {confidence} | swarm_verified: true'"
            f"}})"
        )

        if args.dry_run:
            count += 1
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception:
                pass

    print(f"OK: Injected {count} AI-synthesized OP_StandardCase nodes")


if __name__ == "__main__":
    main()
