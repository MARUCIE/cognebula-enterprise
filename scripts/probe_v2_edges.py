#!/usr/bin/env python3
"""probe_v2_edges.py — read-only edge enumeration for V1+V2 lineage tables.

Why this exists
---------------
B2 lineage unification (audit §20) requires rewiring every edge whose FROM or
TO endpoint is a V1 or V2 table. The kg-api server has no Cypher proxy, so we
can't run a single graph-pattern query to enumerate edges per table. This
script samples nodes per V1/V2 table and aggregates incident-edge labels,
then extrapolates to the population using `/api/v1/stats::edge_counts` for
total-edge ground truth.

Output is a CSV-shaped report on stdout. The aggregation is a sample, not an
exhaustive enumeration; precision is enough for migration planning, not for
reconciliation. For exact post-cutover verification, run `MATCH ()-[e]-(n:V1)
RETURN type(e), count(e)` directly on contabo via kuzu-shell after the kg-api
process is stopped.

Why we don't write a CSV file
-----------------------------
Edge counts are derived from prod KG state at probe time and may include
sensitive table relationships. Keeping the output on stdout (not committed)
matches the project's principle that prod data does not enter git.

Usage
-----
  python3 scripts/probe_v2_edges.py
  python3 scripts/probe_v2_edges.py --sample-size 50
  python3 scripts/probe_v2_edges.py --tables ComplianceRule,FilingForm

Requires
--------
- Tailscale UP (mac is `mauricemacbook-pro` 100.113.180.44; prod is
  `kg-node-eu` 100.88.170.57)
- prod_kg_client reachable (see scripts/_lib/prod_kg_client.py)

Audit ref
---------
- §20 Phase B2 (V1+V2 lineage unification)
- outputs/audits/2026-04-28-prod-kg-b2-execution-readiness.md §3 (Edge rewire)
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# Hoist sibling library on path for direct invocation
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "_lib"))
import prod_kg_client as kg  # noqa: E402


# Default V1+V2 tables in scope per B2 design.
DEFAULT_TABLES = (
    "ComplianceRule",
    "ComplianceRuleV2",
    "FilingForm",
    "FilingFormV2",
    "TaxIncentive",
    "TaxIncentiveV2",
    "RiskIndicatorV2",  # orphan post-M3; rename target only
)


def probe_table(table: str, sample_size: int) -> dict:
    """Sample `sample_size` nodes from `table` and aggregate incident edges.

    Returns:
      {
        "table": <name>,
        "total_rows": <int>,            # from /api/v1/quality::title_stats
        "sampled_rows": <int>,
        "sampled_with_zero_edges": <int>,
        "edge_tuples": Counter[(direction, edge_type, target_type)] -> sample count
      }
    """
    nodes = kg.nodes(table, limit=sample_size)
    edge_tuples: Counter = Counter()
    zero_edge_rows = 0
    sampled = 0

    for n in nodes:
        nid = n.get("id")
        if not nid:
            continue
        try:
            payload = kg._get(
                "/api/v1/graph",
                params={"table": table, "id_field": "id", "id_value": str(nid), "depth": 1},
                timeout=8.0,
            )
        except Exception:
            # Skip transient timeouts; sample size will absorb them
            continue
        sampled += 1
        neighbors = payload.get("neighbors", [])
        if not neighbors:
            zero_edge_rows += 1
            continue
        for nb in neighbors:
            key = (nb.get("direction") or "?", nb.get("edge_type") or "?", nb.get("target_type") or "?")
            edge_tuples[key] += 1

    return {
        "table": table,
        "total_rows": _get_total_rows(table),
        "sampled_rows": sampled,
        "sampled_with_zero_edges": zero_edge_rows,
        "edge_tuples": edge_tuples,
    }


def _get_total_rows(table: str) -> int | None:
    """Look up total row count via /api/v1/quality::title_stats. Returns None on miss."""
    try:
        q = kg.stats()
    except Exception:
        return None
    ts = q.get("title_stats") or {}
    entry = ts.get(table)
    if isinstance(entry, dict):
        return entry.get("total")
    return None


def render_csv(reports: list[dict]) -> str:
    """Render aggregated reports as CSV on stdout.

    Columns: source_table, total_rows, sampled, edges_per_sampled_row,
             extrapolated_edges, direction, edge_type, target_type,
             sample_count, share_of_sampled_edges
    """
    lines = [
        "source_table,total_rows,sampled,edges_per_sampled_row,extrapolated_edges_total,"
        "direction,edge_type,target_type,sample_count,share_of_sampled_edges"
    ]
    for r in reports:
        sampled = r["sampled_rows"]
        if not sampled:
            lines.append(
                f"{r['table']},{r['total_rows'] or 0},0,0.0,0,(no-sample),(no-sample),(no-sample),0,0.000"
            )
            continue
        sampled_edges = sum(r["edge_tuples"].values())
        per_row = sampled_edges / sampled if sampled else 0.0
        extrapolated = int(per_row * (r["total_rows"] or 0))
        if not r["edge_tuples"]:
            lines.append(
                f"{r['table']},{r['total_rows'] or 0},{sampled},0.000,0,(zero-edges),(zero-edges),(zero-edges),0,0.000"
            )
            continue
        for (direction, edge_type, target_type), count in r["edge_tuples"].most_common():
            share = count / sampled_edges if sampled_edges else 0.0
            lines.append(
                f"{r['table']},{r['total_rows'] or 0},{sampled},{per_row:.3f},{extrapolated},"
                f"{direction},{edge_type},{target_type},{count},{share:.3f}"
            )
    return "\n".join(lines)


def render_summary(reports: list[dict]) -> str:
    """Human-readable summary of total edge-rewire scope."""
    out = ["", "=" * 70, "EDGE REWIRE SCOPE SUMMARY (extrapolated from samples)", "=" * 70]
    grand_total = 0
    for r in reports:
        sampled = r["sampled_rows"]
        total_rows = r["total_rows"] or 0
        if not sampled:
            out.append(f"{r['table']:<25s} no-sample")
            continue
        sampled_edges = sum(r["edge_tuples"].values())
        per_row = sampled_edges / sampled if sampled else 0.0
        extrapolated = int(per_row * total_rows)
        grand_total += extrapolated
        unique_tuples = len(r["edge_tuples"])
        zero_pct = 100 * r["sampled_with_zero_edges"] / sampled if sampled else 0
        out.append(
            f"{r['table']:<25s}  rows={total_rows:>5d}  "
            f"sample={sampled:>3d}  edges/row={per_row:5.2f}  "
            f"extrap_edges={extrapolated:>6d}  "
            f"distinct_edge_tuples={unique_tuples:>3d}  zero_edge_rows={zero_pct:5.1f}%"
        )
    out.append("-" * 70)
    out.append(f"GRAND-TOTAL extrapolated edges to rewire: ~{grand_total:,}")
    out.append("=" * 70)
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only edge enumeration for V1/V2 lineage tables")
    parser.add_argument("--sample-size", type=int, default=50, help="Nodes to sample per table (default 50)")
    parser.add_argument(
        "--tables",
        type=str,
        default="",
        help="Comma-separated list of tables to probe (default: B2 V1+V2 set)",
    )
    parser.add_argument("--csv-only", action="store_true", help="Suppress summary; emit CSV only")
    args = parser.parse_args()

    tables = tuple(t.strip() for t in args.tables.split(",") if t.strip()) if args.tables else DEFAULT_TABLES

    # Liveness probe before doing real work
    try:
        h = kg.health()
        if h.get("status") != "healthy":
            print(f"ERROR: kg-api unhealthy: {h}", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"ERROR: kg-api unreachable: {e}", file=sys.stderr)
        return 2

    reports = []
    for table in tables:
        print(f"# probing {table} ...", file=sys.stderr)
        reports.append(probe_table(table, args.sample_size))

    print(render_csv(reports))
    if not args.csv_only:
        print(render_summary(reports), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
