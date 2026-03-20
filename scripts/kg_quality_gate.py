#!/usr/bin/env python3
"""KG Quality Gate — validate data before ingestion.

Standalone script that checks JSON data against quality thresholds.
Can be used as CLI tool or imported as module.

Usage:
    python3 scripts/kg_quality_gate.py data/extracted/doctax_extracted.json
    python3 scripts/kg_quality_gate.py --check-api  # audit live KG via API
"""
import json
import sys
import urllib.request
from pathlib import Path

# Quality thresholds (must match kg_api.py constants)
TITLE_MIN_LEN = 5
CONTENT_MIN_LEN = 20
TITLE_COVERAGE_TARGET = 0.95
EDGE_DENSITY_TARGET = 0.5

KG_API = "http://100.75.77.112:8400"


def validate_node(node: dict, index: int = 0) -> list[dict]:
    """Validate a single node. Returns list of issues (empty = pass)."""
    issues = []
    nid = (node.get("id") or "").strip()
    title = (node.get("title") or "").strip()
    content = (node.get("content") or node.get("fullText") or "").strip()

    if not nid:
        issues.append({"index": index, "severity": "high", "reason": "missing_id"})
    if len(title) < TITLE_MIN_LEN:
        issues.append({
            "index": index, "id": nid, "severity": "high",
            "reason": f"title_too_short ({len(title)}/{TITLE_MIN_LEN})",
            "value": title[:50],
        })
    if len(content) < CONTENT_MIN_LEN:
        issues.append({
            "index": index, "id": nid, "severity": "medium",
            "reason": f"content_too_short ({len(content)}/{CONTENT_MIN_LEN})",
        })
    # Raw ID leak detection
    if title.startswith("{'_id':") or title.startswith("{'offset':"):
        issues.append({
            "index": index, "id": nid, "severity": "high",
            "reason": "title_is_raw_id",
        })
    # TRM_ code without readable name
    if title.startswith("TRM_"):
        issues.append({
            "index": index, "id": nid, "severity": "medium",
            "reason": f"title_is_code ({title})",
        })
    return issues


def validate_batch(nodes: list[dict]) -> dict:
    """Validate a batch of nodes. Returns quality report."""
    all_issues = []
    for i, node in enumerate(nodes):
        all_issues.extend(validate_node(node, i))

    total = len(nodes)
    high_count = sum(1 for i in all_issues if i["severity"] == "high")
    medium_count = sum(1 for i in all_issues if i["severity"] == "medium")
    pass_count = total - len(set(i.get("index") for i in all_issues))

    return {
        "gate": "PASS" if high_count == 0 else "FAIL",
        "total": total,
        "passed": pass_count,
        "pass_rate": round(pass_count / total, 3) if total > 0 else 0,
        "issues_high": high_count,
        "issues_medium": medium_count,
        "issues": all_issues[:100],  # Cap output
    }


def check_api():
    """Check live KG quality via API."""
    try:
        with urllib.request.urlopen(f"{KG_API}/api/v1/quality", timeout=30) as resp:
            data = json.loads(resp.read())
            return data
    except Exception as e:
        return {"error": str(e)}


def main():
    if "--check-api" in sys.argv:
        result = check_api()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("gate") == "PASS" else 1)

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <json_file> [--check-api]")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    with open(filepath) as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("ERROR: Expected JSON array")
        sys.exit(1)

    result = validate_batch(data)
    print(f"=== KG Quality Gate: {result['gate']} ===")
    print(f"Total: {result['total']}, Passed: {result['passed']}, Rate: {result['pass_rate']:.1%}")
    print(f"High issues: {result['issues_high']}, Medium issues: {result['issues_medium']}")

    if result["issues"]:
        print("\nTop issues:")
        for issue in result["issues"][:20]:
            print(f"  [{issue['severity'].upper()}] #{issue.get('index', '?')}: {issue['reason']}"
                  + (f" — {issue.get('value', '')}" if issue.get("value") else ""))

    sys.exit(0 if result["gate"] == "PASS" else 1)


if __name__ == "__main__":
    main()
