"""Ontology conformance auditor — diff live Kuzu against canonical v4.2 schema.

Read-only: never writes, never alters the graph. Safe to run against production.

Canonical source: schemas/ontology_v4.2.cypher (35 node types, Brooks ceiling 37).

Output shape (dict):
    {
        "canonical_count": 35,
        "live_count": 62,
        "brooks_ceiling": 37,
        "over_ceiling": True,
        "intersection": [...],
        "missing_from_prod": [...],
        "rogue_in_prod": [...],
        "rogue_buckets": {
            "v1_v2_bleed": [...],
            "duplicate_clusters": {...},
            "saas_leak": [...],
            "legacy": [...],
            "other": [...],
        },
        "verdict": "PASS" | "FAIL",
        "severity": "low" | "medium" | "high",
    }
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

BROOKS_CEILING = 37

# Rogue buckets from ONTOLOGY_DRIFT_REPORT.md §3. Keep in sync when
# new rogue types appear in production.
V1_V2_BLEED = {
    "ComplianceRuleV2": "ComplianceRule",
    "FilingFormV2": "FilingForm",
    "RiskIndicatorV2": "RiskIndicator",
    "TaxIncentiveV2": "TaxIncentive",
    "FormTemplate": "FilingForm",
}

DUPLICATE_CLUSTERS = {
    # Note: TaxCalculationRule is a legitimate v4.2 canonical (Tier 2), NOT a
    # rate duplicate. Keep it out of this bucket even though the drift report
    # initially misfiled it. TaxRateSchedule stays: v4.2 does not include it,
    # progressive brackets fold into TaxRate via the tier columns in Phase 2D.
    "tax_rate": {
        "TaxRateMapping",
        "TaxRateDetail",
        "TaxRateSchedule",
        "TaxpayerRatePolicy",
        "TaxCodeIndustryMap",
    },
    "accounting": {
        "AccountEntry",
        "AccountingEntry",
        "AccountRuleMapping",
        "ChartOfAccount",
        "ChartOfAccountDetail",
        "DepreciationRule",
    },
    "industry": {
        "Industry",
        "FTIndustry",
        "IndustryKnowledge",
        "IndustryBookkeeping",
        "IndustryRiskProfile",
    },
    "policy": {
        "TaxPolicy",
        "RegionalTaxPolicy",
        "TaxExemptionThreshold",
    },
}

SAAS_LEAK = {
    "CustomerProfile",
    "EnterpriseType",
    "EntityTypeProfile",
    "ServiceCatalog",
    "CrossSellTrigger",
    "ChurnIndicator",
}

LEGACY_PRE_V41 = {
    "CPAKnowledge",
    "DocumentSection",
    "FAQEntry",
    "MindmapNode",
    "HSCode",
    "TaxClassificationCode",
    "TaxCodeDetail",
}

# Session 74 Wave 1 — noise classification. These sub-categorize the `other`
# bucket without changing its contents; `audit()` exposes them at top level as
# `noise_classification` so the 5-key `rogue_buckets` contract stays intact.
#
# CODE_GRAPH_POLLUTION: tree-sitter indexing leftovers with 0 finance-tax
# semantics. Hara (Session 74 swarm): delete; these are not domain nodes.
CODE_GRAPH_POLLUTION = {
    "ArrowFunction",
    "Class",
    "Community",
    "Document",
    "External",
    "File",
    "Folder",
    "Function",
    "Interface",
    "LifecycleActivity",
    "LifecycleStage",
    "Method",
    "Section",
    "SpecialZone",
    "Topic",
}

# METADATA_ONLY: taxonomy/navigation nodes that carry no prose `content` by
# design. Including them in content_coverage denominator produces a false
# negative; the Session 74 audit's 29pp coverage gap is ~80% attributable to
# including these in the denominator.
METADATA_ONLY = {
    "HSCode",
    "Classification",
    "MindmapNode",
    "DocumentSection",
}

# Edge-level rogue patterns (REL table name prefixes).
# Code-analysis residue: tree-sitter extractor leftovers, same origin as the
# orphan nodes in ORPHAN_NODES. These carry no finance-tax semantics.
CODE_ANALYSIS_REL_PREFIXES = {
    "CALLS_",
    "DEFINES_",
    "DEFINES",
    "IMPORTS_",
    "EXTENDS_",
    "IMPLEMENTS_",
    "CONTAINS_",
    "CONTAINS",
    "MEMBER_OF",
}

# Pre-v4.2 finance vocabulary prefixes. These edges carry real data but use
# the old namespacing (FT_/OP_/CO_/XL_/DOC_) instead of canonical v4.2 names.
# Phase 2/4 migrations collapse them into canonical edge labels.
LEGACY_REL_PREFIXES = {"FT_", "OP_", "CO_", "XL_", "DOC_"}


def _match_prefix(name: str, prefixes: set[str]) -> bool:
    """True if `name` starts with any member of `prefixes`, or matches exactly
    a prefix that was declared without a trailing underscore."""
    for p in prefixes:
        if p.endswith("_"):
            if name.startswith(p):
                return True
        elif name == p:
            return True
    return False


def classify_rogue_edges(rogue_edges: set[str]) -> dict[str, Any]:
    """Bucket rogue REL table names by origin.

    Returns keys: code_analysis_residue, legacy_prefixes, other.
    """
    code = sorted(
        n for n in rogue_edges if _match_prefix(n, CODE_ANALYSIS_REL_PREFIXES)
    )
    legacy = sorted(n for n in rogue_edges if _match_prefix(n, LEGACY_REL_PREFIXES))
    classified = set(code) | set(legacy)
    return {
        "code_analysis_residue": code,
        "legacy_prefixes": legacy,
        "other": sorted(rogue_edges - classified),
    }


def parse_canonical_schema(schema_path: Path) -> set[str]:
    """Extract node-type names from a Kuzu Cypher schema file."""
    pattern = re.compile(
        r"CREATE NODE TABLE(?: IF NOT EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)"
    )
    text = schema_path.read_text(encoding="utf-8")
    return {m.group(1) for m in pattern.finditer(text)}


def parse_canonical_rel_tables(schema_path: Path) -> set[str]:
    """Extract REL table names from a Kuzu Cypher schema file.

    Matches both `CREATE REL TABLE` and `CREATE REL TABLE GROUP` forms.
    """
    pattern = re.compile(
        r"CREATE REL TABLE(?:\s+GROUP)?(?:\s+IF NOT EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)"
    )
    text = schema_path.read_text(encoding="utf-8")
    return {m.group(1) for m in pattern.finditer(text)}


def list_live_node_tables(conn) -> set[str]:
    """Return all NODE table names from a live Kuzu connection."""
    result = conn.execute("CALL show_tables() RETURN *")
    tables: set[str] = set()
    while result.has_next():
        row = result.get_next()
        if len(row) >= 3 and row[2] == "NODE":
            tables.add(row[1])
    return tables


def list_live_rel_tables(conn) -> set[str]:
    """Return all REL table names from a live Kuzu connection."""
    result = conn.execute("CALL show_tables() RETURN *")
    tables: set[str] = set()
    while result.has_next():
        row = result.get_next()
        if len(row) >= 3 and row[2] == "REL":
            tables.add(row[1])
    return tables


def classify_rogue(rogue: set[str]) -> dict[str, Any]:
    buckets: dict[str, Any] = {
        "v1_v2_bleed": sorted(rogue & set(V1_V2_BLEED.keys())),
        "duplicate_clusters": {},
        "saas_leak": sorted(rogue & SAAS_LEAK),
        "legacy": sorted(rogue & LEGACY_PRE_V41),
    }

    classified: set[str] = (
        set(buckets["v1_v2_bleed"]) | set(buckets["saas_leak"]) | set(buckets["legacy"])
    )

    for cluster_name, members in DUPLICATE_CLUSTERS.items():
        hits = sorted(rogue & members)
        if hits:
            buckets["duplicate_clusters"][cluster_name] = hits
            classified |= set(hits)

    buckets["other"] = sorted(rogue - classified)
    return buckets


def classify_noise(other_bucket: list[str]) -> dict[str, list[str]]:
    """Sub-categorize the `other` rogue bucket for Session 74 remediation plan.

    Splits the catch-all `other` into:
      - code_graph_pollution: tree-sitter indexing leftovers (delete candidates)
      - metadata_only: taxonomy/navigation nodes (exclude from coverage)
      - misc: everything else (needs per-type decision)

    Pure, read-only; does not alter the `rogue_buckets` contract.
    """
    other = set(other_bucket)
    code_graph = sorted(other & CODE_GRAPH_POLLUTION)
    metadata = sorted(other & METADATA_ONLY)
    classified = set(code_graph) | set(metadata)
    return {
        "code_graph_pollution": code_graph,
        "metadata_only": metadata,
        "misc": sorted(other - classified),
    }


def count_rows_per_type(conn, table_names: set[str] | list[str]) -> dict[str, int]:
    """Pure read: COUNT(*) per node table. Returns {table: row_count}.

    Empty/missing tables return 0. Used by Round-4 stub-backfill detector
    (a canonical type with row_count below threshold is a DDL-only ghost).
    """
    counts: dict[str, int] = {}
    for tbl in sorted(set(table_names)):
        try:
            res = conn.execute(f"MATCH (n:{tbl}) RETURN COUNT(*) AS c")
            row = res.get_next() if res.has_next() else None
            counts[tbl] = int(row[0]) if row else 0
        except Exception:
            counts[tbl] = 0
    return counts


def count_rels_per_type(conn, rel_names: set[str] | list[str]) -> dict[str, int]:
    """Pure read: COUNT(*) per REL table. Returns {rel: edge_count}.

    Companion to count_rows_per_type. Round-4 stub-backfill detector cares
    about edge backbone tables (INTERPRETS, KU_ABOUT_TAX) too — a thin edge
    table is the same anti-pattern as a thin node table.
    """
    counts: dict[str, int] = {}
    for rel in sorted(set(rel_names)):
        try:
            res = conn.execute(f"MATCH ()-[r:{rel}]->() RETURN COUNT(*) AS c")
            row = res.get_next() if res.has_next() else None
            counts[rel] = int(row[0]) if row else 0
        except Exception:
            counts[rel] = 0
    return counts


def parse_canonical_columns(schema_path: Path) -> dict[str, list[str]]:
    """FU6 — extract per-table column declarations from canonical Cypher.

    Reads each NODE-TABLE declaration block (regex below) and returns
    {table_name: [col1, col2, ...]} preserving declaration order,
    excluding the trailing PRIMARY KEY clause.

    Catches the 2026-04-27 AccountingSubject incident: canonical declared
    `balanceSide / code / parentId` but live had `balanceDirection / fullText`.
    With this parser + compute_schema_shape_drift downstream, drift surfaces
    in the audit endpoint instead of silently breaking seed application.
    """
    text = schema_path.read_text(encoding="utf-8")
    block_re = re.compile(
        r"CREATE NODE TABLE(?:\s+IF NOT EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*;",
        re.DOTALL,
    )
    out: dict[str, list[str]] = {}
    for m in block_re.finditer(text):
        name = m.group(1)
        body = m.group(2)
        # Strip line comments (`// ...` and `-- ...`) before splitting
        body = re.sub(r"(--|//)[^\n]*", "", body)
        cols: list[str] = []
        for piece in body.split(","):
            piece = piece.strip()
            if not piece:
                continue
            if piece.upper().startswith("PRIMARY KEY"):
                continue
            tok = piece.split(None, 1)
            if tok and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tok[0]):
                cols.append(tok[0])
        out[name] = cols
    return out


def list_live_columns(conn, table_names: set[str] | list[str]) -> dict[str, list[str]]:
    """FU6 — pure read of live column lists per NODE table.

    Uses Kuzu `CALL table_info(<name>) RETURN *`. Returns {table: [col1, ...]}.
    Tables that error (missing or unauthorized) get an empty list — same
    convention as count_rows_per_type so downstream diff treats them uniformly.
    """
    out: dict[str, list[str]] = {}
    for tbl in sorted(set(table_names)):
        try:
            res = conn.execute(f"CALL table_info('{tbl}') RETURN *")
            cols: list[str] = []
            while res.has_next():
                row = res.get_next()
                # Kuzu table_info returns: [property_id, name, type, ...]
                if len(row) >= 2 and isinstance(row[1], str):
                    cols.append(row[1])
            out[tbl] = cols
        except Exception:
            out[tbl] = []
    return out


def compute_schema_shape_drift(
    canonical_cols: dict[str, list[str]],
    live_cols: dict[str, list[str]],
    intersection: set[str] | list[str],
) -> dict[str, Any]:
    """FU6 — per-table column diff for tables present in both canonical and live.

    For each intersection table:
      - declared_only: columns in canonical CREATE block but missing in live
      - live_only:     columns in live table but absent from canonical
      - matched:       columns present in both

    Returns:
        {
            "by_table": {table: {"declared_only": [...], "live_only": [...], "matched": [...]}},
            "drift_count": int,                       # tables with any drift
            "tables_with_declared_only": [...],       # canonical declares column not in live
            "tables_with_live_only": [...],           # live has column canonical does not declare
        }

    A canonical type with empty drift is shape-conforming. drift_count > 0
    means at least one canonical type's CREATE block lies about live shape.
    """
    by_table: dict[str, dict[str, list[str]]] = {}
    declared_only_tables: list[str] = []
    live_only_tables: list[str] = []
    drift = 0
    for tbl in sorted(set(intersection)):
        declared = set(canonical_cols.get(tbl, []))
        live = set(live_cols.get(tbl, []))
        do = sorted(declared - live)
        lo = sorted(live - declared)
        matched = sorted(declared & live)
        if do or lo:
            drift += 1
            if do:
                declared_only_tables.append(tbl)
            if lo:
                live_only_tables.append(tbl)
        by_table[tbl] = {
            "declared_only": do,
            "live_only": lo,
            "matched": matched,
        }
    return {
        "by_table": by_table,
        "drift_count": drift,
        "tables_with_declared_only": declared_only_tables,
        "tables_with_live_only": live_only_tables,
    }


# Round-4 stub-backfill detector thresholds.
# Per Munger STOP rule (`outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md`):
# canonical_coverage_ratio is redefined as `Σ(row_count > MIN_ROWS_DEFAULT) / 35`,
# with stricter floors on the 5 priority backbone types. A canonical type with
# rows below its threshold counts as DDL-only ghost (does not contribute to ratio).
MIN_ROWS_DEFAULT = 1000
MIN_ROWS_PER_TYPE: dict[str, int] = {
    "INTERPRETS": 300_000,           # the 390K give-up bucket (Hickey ratio 4.6:1)
    "KU_ABOUT_TAX": 100_000,         # the 166K second elephant (H1 split target)
    "AccountingSubject": 1_000,      # 企业会计准则 + 小企业会计准则 target ~1500
    "BusinessActivity": 1_000,       # GB/T 4754 国民经济行业分类 target ~1500
    "RegulationArticle": 1_000,      # legal-clause backbone
    "ComplianceRule": 100,           # smaller domain expected
}
MIN_ROWS_TARGET_RATIO: float = 0.50  # below this, only data-ingest work allowed


def compute_min_rows_metric(
    canonical: set[str] | list[str],
    row_counts: dict[str, int],
    min_rows_default: int = MIN_ROWS_DEFAULT,
    min_rows_per_type: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Compute the gaming-resistant variant of canonical_coverage_ratio.

    For each canonical type t:
      threshold(t) = min_rows_per_type.get(t, min_rows_default)
      passes(t)    = row_counts.get(t, 0) >= threshold(t)

    canonical_coverage_ratio_with_min_rows = (# passes) / |canonical|

    A DDL-only stub (row_count=0) cannot satisfy this metric. Closes the
    Goodhart loop opened in 2026-04-25 → 2026-04-27 stub-backfill incident.
    """
    if min_rows_per_type is None:
        min_rows_per_type = MIN_ROWS_PER_TYPE
    canonical_set = set(canonical)
    if not canonical_set:
        return {
            "canonical_coverage_ratio_with_min_rows": 0.0,
            "min_rows_default": min_rows_default,
            "passes": [],
            "fails": [],
            "tier_empty": [],
            "tier_tiny": [],
            "tier_small": [],
            "tier_ok": [],
        }
    passes: list[str] = []
    fails: list[dict[str, Any]] = []
    tier_empty: list[str] = []
    tier_tiny: list[str] = []
    tier_small: list[str] = []
    tier_ok: list[str] = []
    for t in sorted(canonical_set):
        cnt = row_counts.get(t, 0)
        threshold = min_rows_per_type.get(t, min_rows_default)
        if cnt >= threshold:
            passes.append(t)
        else:
            fails.append({"type": t, "rows": cnt, "threshold": threshold})
        if cnt == 0:
            tier_empty.append(t)
        elif cnt < 50:
            tier_tiny.append(t)
        elif cnt < 500:
            tier_small.append(t)
        else:
            tier_ok.append(t)
    ratio = len(passes) / len(canonical_set)
    return {
        "canonical_coverage_ratio_with_min_rows": round(ratio, 3),
        "min_rows_default": min_rows_default,
        "min_rows_per_type": min_rows_per_type,
        "passes": passes,
        "fails": fails,
        "tier_empty": tier_empty,
        "tier_tiny": tier_tiny,
        "tier_small": tier_small,
        "tier_ok": tier_ok,
        "stub_suspect_count": len(tier_empty) + len(tier_tiny),
    }


def compute_composite_gate(
    audit_result: dict[str, Any],
    canonical_coverage_target: float = 0.80,
    min_rows_target_ratio: float = MIN_ROWS_TARGET_RATIO,
) -> dict[str, Any]:
    """Three-condition ANDed gate per Session 74 PDCA Wave 1.

    Conditions (all must pass):
      C1: canonical_coverage_ratio >= canonical_coverage_target  (default 0.80)
      C2: rogue_types_count == 0
      C3: over_ceiling_by <= 0

    canonical_coverage_ratio = |intersection| / |domain_types|, where
    domain_types = live_types - code_graph_pollution - saas_leak.

    Note: METADATA_ONLY is deliberately NOT excluded here. Canonical types like
    `Classification` belong to METADATA_ONLY but are legitimate domain types —
    they just happen to carry no prose `content`. Excluding them from the
    canonical_coverage denominator would penalize progress on types that are
    already correctly canonical. METADATA_ONLY is meant for the separate
    content_coverage metric (where nodes without `content` fields should drop
    out of the denominator), not for type-level canonical conformance.

    Type-based (not node-count-based); cheap to compute, does not need conn.

    Returns {verdict, breakdown[C1/C2/C3], canonical_coverage_ratio, domain_types_count}.
    Pure — takes the result of audit() and returns a derived view.
    """
    live = set(audit_result.get("rogue_in_prod", [])) | set(
        audit_result.get("intersection", [])
    )
    noise_types = CODE_GRAPH_POLLUTION | SAAS_LEAK
    domain_types = live - noise_types
    intersection = set(audit_result.get("intersection", []))
    domain_canonical = intersection & domain_types
    # Canonical types are always domain (by definition of v4.2 spec); use the
    # domain_types count as denominator so adding noise types cannot inflate it.
    coverage = (
        len(domain_canonical) / len(domain_types) if domain_types else 0.0
    )
    rogue_count = len(set(audit_result.get("rogue_in_prod", [])) - noise_types)
    over_ceiling_by = audit_result.get("over_ceiling_by", 0)

    c1 = coverage >= canonical_coverage_target
    c2 = rogue_count == 0
    c3 = over_ceiling_by <= 0

    # C1+ Round-4 stub-backfill detector (additive; Munger STOP rule).
    # Reads `canonical_min_rows_metric` if `audit()` populated it, else
    # falls back to a permissive PASS so unit tests of the legacy 3-axis
    # gate keep working.
    min_rows_metric = audit_result.get("canonical_min_rows_metric") or {}
    coverage_min = min_rows_metric.get("canonical_coverage_ratio_with_min_rows")
    if coverage_min is None:
        c1_plus = True
        c1_plus_block = None
    else:
        c1_plus = coverage_min >= min_rows_target_ratio
        c1_plus_block = {
            "value": coverage_min,
            "target": min_rows_target_ratio,
            "pass": c1_plus,
            "stub_suspect_count": min_rows_metric.get("stub_suspect_count", 0),
            "tier_empty": min_rows_metric.get("tier_empty", []),
            "tier_tiny": min_rows_metric.get("tier_tiny", []),
        }

    verdict = "PASS" if (c1 and c2 and c3 and c1_plus) else "FAIL"

    breakdown = {
        "C1_canonical_coverage": {
            "value": round(coverage, 3),
            "target": canonical_coverage_target,
            "pass": c1,
        },
        "C2_zero_domain_rogues": {
            "value": rogue_count,
            "target": 0,
            "pass": c2,
        },
        "C3_under_brooks_ceiling": {
            "value": over_ceiling_by,
            "target": 0,
            "pass": c3,
        },
    }
    if c1_plus_block is not None:
        breakdown["C1_plus_canonical_with_min_rows"] = c1_plus_block

    return {
        "verdict": verdict,
        "canonical_coverage_ratio": round(coverage, 3),
        "canonical_coverage_target": canonical_coverage_target,
        "canonical_coverage_ratio_with_min_rows": coverage_min,
        "min_rows_target_ratio": min_rows_target_ratio,
        "domain_types_count": len(domain_types),
        "noise_types_excluded": len(live & noise_types),
        "domain_rogue_count": rogue_count,
        "over_ceiling_by": over_ceiling_by,
        "breakdown": breakdown,
    }


def audit(conn, schema_path: Path | str | None = None) -> dict[str, Any]:
    """Run a full ontology-conformance audit. Pure read."""
    if schema_path is None:
        schema_path = (
            Path(__file__).resolve().parent.parent.parent
            / "schemas"
            / "ontology_v4.2.cypher"
        )
    schema_path = Path(schema_path)

    canonical = parse_canonical_schema(schema_path)
    live = list_live_node_tables(conn)

    intersection = canonical & live
    missing_from_prod = canonical - live
    rogue_in_prod = live - canonical

    # Edge-level audit (additive; does not affect verdict/severity).
    rel_canonical = parse_canonical_rel_tables(schema_path)
    rel_live = list_live_rel_tables(conn)
    rel_intersection = rel_canonical & rel_live
    rel_missing_from_prod = rel_canonical - rel_live
    rel_rogue_in_prod = rel_live - rel_canonical

    live_count = len(live)
    over_ceiling = live_count > BROOKS_CEILING

    high_severity = (
        over_ceiling
        or any(name in live for name in V1_V2_BLEED)
        or len(rogue_in_prod) > 20
    )
    medium_severity = len(rogue_in_prod) > 5 or len(missing_from_prod) > 5
    severity = "high" if high_severity else ("medium" if medium_severity else "low")
    verdict = "PASS" if severity == "low" else "FAIL"

    rogue_buckets = classify_rogue(rogue_in_prod)

    # Round-4 stub-backfill detector — count rows for canonical NODE types
    # AND edge counts for any REL types named in MIN_ROWS_PER_TYPE
    # (e.g. INTERPRETS, KU_ABOUT_TAX). Cheap: ~35 NODE COUNT(*) + 1-3 REL
    # COUNT(*) queries. Pure read.
    canonical_row_counts = count_rows_per_type(conn, canonical)
    rel_priority_targets = {
        name for name in MIN_ROWS_PER_TYPE if name in rel_live
    }
    if rel_priority_targets:
        rel_counts = count_rels_per_type(conn, rel_priority_targets)
        # Merge: REL keys join NODE keys in same dict; downstream consumers
        # (compute_min_rows_metric + tests) see one unified row_counts map.
        canonical_row_counts = {**canonical_row_counts, **rel_counts}
        # Extend "canonical" set passed to the metric so REL targets are
        # subject to the same threshold check as NODE targets.
        canonical_for_metric = canonical | rel_priority_targets
    else:
        canonical_for_metric = canonical
    canonical_min_rows_metric = compute_min_rows_metric(
        canonical_for_metric, canonical_row_counts
    )

    # FU6 — schema-shape audit. For canonical types present in live, diff the
    # declared CREATE-block columns against actual live columns. Catches the
    # 2026-04-27 AccountingSubject incident pattern (declared balanceSide,
    # live had balanceDirection) so future seeds can fail fast on field_map
    # gaps instead of silently dropping props.
    canonical_columns_decl = parse_canonical_columns(schema_path)
    live_columns_actual = list_live_columns(conn, intersection)
    schema_shape_drift = compute_schema_shape_drift(
        canonical_columns_decl, live_columns_actual, intersection
    )

    result = {
        "schema_source": str(schema_path),
        "canonical_count": len(canonical),
        "live_count": live_count,
        "brooks_ceiling": BROOKS_CEILING,
        "over_ceiling": over_ceiling,
        "over_ceiling_by": max(0, live_count - BROOKS_CEILING),
        "intersection": sorted(intersection),
        "missing_from_prod": sorted(missing_from_prod),
        "rogue_in_prod": sorted(rogue_in_prod),
        "rogue_buckets": rogue_buckets,
        # Session 74 Wave 1 — additive top-level fields; 5-key
        # `rogue_buckets` contract preserved (tested in
        # tests/test_ontology_conformance.py::test_audit_result_shape).
        "noise_classification": classify_noise(rogue_buckets["other"]),
        "edges": {
            "canonical_count": len(rel_canonical),
            "live_count": len(rel_live),
            "intersection": sorted(rel_intersection),
            "missing_from_prod": sorted(rel_missing_from_prod),
            "rogue_in_prod": sorted(rel_rogue_in_prod),
            "rogue_buckets": classify_rogue_edges(rel_rogue_in_prod),
        },
        "verdict": verdict,
        "severity": severity,
        "canonical_row_counts": canonical_row_counts,
        "canonical_min_rows_metric": canonical_min_rows_metric,
        "schema_shape_drift": schema_shape_drift,
    }
    result["composite_gate"] = compute_composite_gate(result)
    return result
