#!/usr/bin/env python3
"""Edge enrichment via KG API — no direct DB access needed.

Uses /api/v1/nodes to read, /api/v1/ingest for new nodes,
and falls back to stopping API for edge creation (KuzuDB limitation).

Usage:
    python3 scripts/edge_enrichment_api.py [--api URL] [--dry-run]
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = os.environ.get("KG_API", "http://localhost:8400")
DRY_RUN = "--dry-run" in sys.argv
for i, a in enumerate(sys.argv):
    if a == "--api" and i + 1 < len(sys.argv):
        API = sys.argv[i + 1]

TAX_KEYWORDS = {
    "TT_VAT": ["增值税", "进项税", "销项税", "发票"],
    "TT_CIT": ["企业所得税", "所得税", "纳税调整", "汇算清缴"],
    "TT_PIT": ["个人所得税", "个税", "工资薪金", "劳务报酬"],
    "TT_STAMP": ["印花税"],
    "TT_CONSUMPTION": ["消费税"],
    "TT_TARIFF": ["关税", "进口税"],
    "TT_PROPERTY": ["房产税"],
    "TT_LAND_VAT": ["土地增值税"],
    "TT_VEHICLE": ["车船税", "车辆购置税"],
    "TT_RESOURCE": ["资源税"],
    "TT_CONTRACT": ["契税"],
    "TT_URBAN": ["城建税", "城市维护建设税"],
    "TT_EDUCATION": ["教育费附加"],
    "TT_ENV": ["环境保护税", "环保税"],
}


def api_get(path):
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  API error: {e}")
        return None


def get_nodes(table, limit=500, offset=0):
    return api_get(f"/api/v1/nodes?type={table}&limit={limit}&offset={offset}")


print(f"=== Edge Enrichment (API mode) ===")
print(f"API: {API}")
print(f"Dry run: {DRY_RUN}")
print()

# Get current stats
stats = api_get("/api/v1/stats")
if stats:
    total_n = stats.get("total_nodes", 0)
    total_e = stats.get("total_edges", 0)
    print(f"Start: {total_n:,} nodes / {total_e:,} edges / density={total_e/total_n:.3f}")
else:
    print("ERROR: API not reachable")
    sys.exit(1)

# --- Phase 1: Scan LawOrRegulation for tax keyword matches ---
print()
print("=== Phase 1: Classify LR by tax type ===")
matches = []  # (lr_id, tax_type_id)
scanned = 0

for offset in range(0, 200000, 500):
    data = get_nodes("LawOrRegulation", limit=500, offset=offset)
    if not data or not data.get("results"):
        break

    for node in data["results"]:
        scanned += 1
        nid = node.get("id", "")
        text = ((node.get("title") or "") + " " + (node.get("fullText") or ""))[:2000]
        for tid, keywords in TAX_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                matches.append((nid, tid))

    if scanned % 5000 == 0:
        print(f"  Scanned {scanned:,} LR nodes, {len(matches):,} matches so far", flush=True)

print(f"  Total scanned: {scanned:,} | Matches: {len(matches):,}")

# --- Phase 2: Write match results as a batch file for edge creation ---
# Edge creation requires direct DB access (API is read-only for edges)
# Save matches to JSON, then run edge creation with API stopped

match_file = "/home/kg/cognebula-enterprise/data/edge_enrichment_matches.json"
if not DRY_RUN:
    # Write to VPS if running locally
    match_data = json.dumps({"tax_matches": matches, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
    try:
        # Try writing locally first
        with open(match_file, "w") as f:
            f.write(match_data)
        print(f"  Saved {len(matches)} matches to {match_file}")
    except:
        # If running remotely, save locally
        local_file = "data/edge_enrichment_matches.json"
        with open(local_file, "w") as f:
            f.write(match_data)
        print(f"  Saved {len(matches)} matches to {local_file}")

print()
print(f"=== Phase 2: Create edges (requires DB stop) ===")
print(f"  Run: sudo systemctl stop kg-api")
print(f"  Then: python3 scripts/edge_enrichment_apply.py")
print(f"  Then: sudo systemctl start kg-api")

if not DRY_RUN and os.path.exists(match_file):
    # If running on VPS, we can stop API and apply directly
    print("  Attempting direct edge creation...")
    try:
        subprocess.run(["sudo", "systemctl", "stop", "kg-api"], timeout=10)
        time.sleep(2)

        import kuzu
        db = kuzu.Database("/home/kg/cognebula-enterprise/data/finance-tax-graph")
        conn = kuzu.Connection(db)

        # Ensure edge tables
        for sql in [
            "CREATE REL TABLE IF NOT EXISTS CLASSIFIED_UNDER_TAX(FROM LawOrRegulation TO TaxType)",
        ]:
            try:
                conn.execute(sql)
            except:
                pass

        created = 0
        for nid, tid in matches:
            try:
                conn.execute(
                    "MATCH (a:LawOrRegulation), (b:TaxType) WHERE a.id = $aid AND b.id = $bid "
                    "CREATE (a)-[:CLASSIFIED_UNDER_TAX]->(b)",
                    {"aid": nid, "bid": tid}
                )
                created += 1
            except:
                pass
            if created % 1000 == 0 and created > 0:
                print(f"    Created {created:,} edges...", flush=True)

        del conn, db
        print(f"  Created: {created:,} CLASSIFIED_UNDER_TAX edges")

        subprocess.run(["sudo", "systemctl", "start", "kg-api"], timeout=10)
        time.sleep(3)

        # Verify
        stats2 = api_get("/api/v1/stats")
        if stats2:
            new_e = stats2.get("total_edges", 0)
            print(f"  Final: {new_e:,} edges (was {total_e:,}, +{new_e - total_e:,})")
            print(f"  Density: {new_e/stats2['total_nodes']:.3f}")
    except Exception as e:
        print(f"  Edge creation failed: {e}")
        subprocess.run(["sudo", "systemctl", "start", "kg-api"], timeout=10, check=False)
