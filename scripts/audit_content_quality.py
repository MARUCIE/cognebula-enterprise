#!/usr/bin/env python3
"""Audit content quality across all major KG node types.

Samples nodes from KuzuDB, runs junk detection, outputs a comprehensive report.

Run on kg-node (API must be stopped for direct KuzuDB access):
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 scripts/audit_content_quality.py
    sudo systemctl start kg-api

Or use --api mode (API must be running, samples via /api/v1/nodes):
    /home/kg/kg-env/bin/python3 scripts/audit_content_quality.py --api
"""
import json
import os
import sys
import argparse
from datetime import datetime, timezone

# Add scripts dir to path for content_validator import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_validator import is_junk, is_llm_generated, content_quality_score

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

# Node types and their primary content fields
AUDIT_TYPES = [
    ("LawOrRegulation", "fullText", "authoritative"),
    ("LegalDocument", "description", "authoritative"),
    ("KnowledgeUnit", "content", "ai_expandable"),
    ("LegalClause", "content", "authoritative"),
    ("RegulationClause", "fullText", "authoritative"),
    ("DocumentSection", "content", "ai_expandable"),
    ("MindmapNode", "content", "ai_expandable"),
    ("CPAKnowledge", "content", "ai_expandable"),
    ("FAQEntry", "content", "ai_expandable"),
    ("TaxRate", "description", "structured"),
]


def audit_via_kuzu(sample_size: int = 500) -> dict:
    """Audit content by directly querying KuzuDB."""
    import kuzu
    db = kuzu.Database(DB_PATH, read_only=True)
    conn = kuzu.Connection(db)

    results = {}
    for type_name, field, policy in AUDIT_TYPES:
        print(f"\n  Auditing {type_name}.{field} ({policy})...")

        try:
            # Get total count
            r = conn.execute(f"MATCH (n:{type_name}) RETURN count(n)")
            total = r.get_next()[0]

            # Sample nodes with content
            r = conn.execute(
                f"MATCH (n:{type_name}) "
                f"RETURN n.{field} "
                f"LIMIT {sample_size}"
            )

            empty = 0
            junk_count = 0
            llm_count = 0
            real_count = 0
            junk_reasons = {}
            samples_junk = []
            samples_real = []

            sampled = 0
            while r.has_next():
                row = r.get_next()
                text = str(row[0] or "")
                sampled += 1

                if not text or len(text.strip()) < 10:
                    empty += 1
                    continue

                junk, reason = is_junk(text)
                if junk:
                    junk_count += 1
                    junk_reasons[reason] = junk_reasons.get(reason, 0) + 1
                    if len(samples_junk) < 3:
                        samples_junk.append(text[:100])
                else:
                    llm, _ = is_llm_generated(text)
                    if llm and policy == "authoritative":
                        llm_count += 1
                    else:
                        real_count += 1
                    if len(samples_real) < 2:
                        samples_real.append(text[:100])

            junk_ratio = junk_count / max(sampled - empty, 1)
            real_ratio = real_count / max(sampled - empty, 1)

            results[type_name] = {
                "total": total,
                "sampled": sampled,
                "empty": empty,
                "junk": junk_count,
                "llm_in_authoritative": llm_count,
                "real": real_count,
                "junk_ratio": round(junk_ratio, 3),
                "real_ratio": round(real_ratio, 3),
                "policy": policy,
                "field": field,
                "junk_reasons": junk_reasons,
                "samples_junk": samples_junk,
                "samples_real": samples_real,
            }

            status = "OK" if junk_ratio < 0.1 else ("WARN" if junk_ratio < 0.3 else "CRITICAL")
            print(f"    {status}: {total:,} total | sampled {sampled} | "
                  f"real={real_count} junk={junk_count} empty={empty} "
                  f"| junk_ratio={junk_ratio:.1%}")

        except Exception as e:
            print(f"    ERROR: {e}")
            results[type_name] = {"error": str(e)}

    del conn
    del db
    return results


def audit_via_api(sample_size: int = 50) -> dict:
    """Audit content by querying the running API."""
    import urllib.request

    results = {}
    for type_name, field, policy in AUDIT_TYPES:
        print(f"\n  Auditing {type_name}.{field} ({policy})...")
        try:
            url = f"http://localhost:8400/api/v1/nodes?type={type_name}&limit={sample_size}"
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())

            total = data.get("total", 0)
            nodes = data.get("results", [])

            empty = 0
            junk_count = 0
            llm_count = 0
            real_count = 0
            junk_reasons = {}

            for node in nodes:
                text = str(node.get(field, "") or "")
                if not text or len(text.strip()) < 10:
                    empty += 1
                    continue
                junk, reason = is_junk(text)
                if junk:
                    junk_count += 1
                    junk_reasons[reason] = junk_reasons.get(reason, 0) + 1
                else:
                    llm, _ = is_llm_generated(text)
                    if llm and policy == "authoritative":
                        llm_count += 1
                    else:
                        real_count += 1

            sampled = len(nodes)
            junk_ratio = junk_count / max(sampled - empty, 1)

            results[type_name] = {
                "total": total,
                "sampled": sampled,
                "empty": empty,
                "junk": junk_count,
                "llm_in_authoritative": llm_count,
                "real": real_count,
                "junk_ratio": round(junk_ratio, 3),
                "real_ratio": round(real_count / max(sampled - empty, 1), 3),
                "policy": policy,
                "field": field,
                "junk_reasons": junk_reasons,
            }

            status = "OK" if junk_ratio < 0.1 else ("WARN" if junk_ratio < 0.3 else "CRITICAL")
            print(f"    {status}: {total:,} total | sampled {sampled} | "
                  f"real={real_count} junk={junk_count} empty={empty} "
                  f"| junk_ratio={junk_ratio:.1%}")

        except Exception as e:
            print(f"    ERROR: {e}")
            results[type_name] = {"error": str(e)}

    return results


def main():
    parser = argparse.ArgumentParser(description="Audit KG content quality")
    parser.add_argument("--api", action="store_true",
                        help="Use API instead of direct KuzuDB access")
    parser.add_argument("--sample", type=int, default=500,
                        help="Sample size per type (default 500, 50 for --api)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON only")
    args = parser.parse_args()

    if args.api:
        sample = args.sample if args.sample != 500 else 50
    else:
        sample = args.sample

    print("=" * 70)
    print(f"  KG Content Quality Audit — {datetime.now(timezone.utc).isoformat()}")
    print(f"  Mode: {'API' if args.api else 'KuzuDB direct'} | Sample: {sample}/type")
    print("=" * 70)

    if args.api:
        results = audit_via_api(sample)
    else:
        results = audit_via_kuzu(sample)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"{'Type':30s} {'Total':>8s} {'Real':>6s} {'Junk':>6s} {'Empty':>6s} {'Junk%':>6s} {'Policy':>14s}")
    print("-" * 78)

    total_real = 0
    total_junk = 0
    total_empty = 0
    for type_name, _, _ in AUDIT_TYPES:
        r = results.get(type_name, {})
        if "error" in r:
            print(f"  {type_name:28s} ERROR: {r['error'][:40]}")
            continue
        total_real += r.get("real", 0)
        total_junk += r.get("junk", 0)
        total_empty += r.get("empty", 0)
        jr = r.get("junk_ratio", 0)
        flag = "CRIT" if jr > 0.3 else ("WARN" if jr > 0.1 else "  OK")
        print(f"  {type_name:28s} {r['total']:>8,} {r['real']:>6} {r['junk']:>6} "
              f"{r['empty']:>6} {jr:>5.0%} {r['policy']:>14s} {flag}")

    print("-" * 78)
    all_content = total_real + total_junk
    overall_junk = total_junk / max(all_content, 1)
    print(f"  {'SAMPLED TOTAL':28s} {'':>8s} {total_real:>6} {total_junk:>6} "
          f"{total_empty:>6} {overall_junk:>5.0%}")

    # Save results
    out_dir = "data/stats"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"content_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.json")

    # Clean non-serializable data
    for k in results:
        if isinstance(results[k], dict):
            results[k].pop("samples_junk", None)
            results[k].pop("samples_real", None)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "api" if args.api else "kuzu",
        "sample_size": sample,
        "overall_junk_ratio": round(overall_junk, 3),
        "types": results,
    }

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Report saved to {out_path}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
