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


def compute_composite_gate(
    audit_result: dict[str, Any],
    canonical_coverage_target: float = 0.80,
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
    verdict = "PASS" if (c1 and c2 and c3) else "FAIL"

    return {
        "verdict": verdict,
        "canonical_coverage_ratio": round(coverage, 3),
        "canonical_coverage_target": canonical_coverage_target,
        "domain_types_count": len(domain_types),
        "noise_types_excluded": len(live & noise_types),
        "domain_rogue_count": rogue_count,
        "over_ceiling_by": over_ceiling_by,
        "breakdown": {
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
        },
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
    }
    result["composite_gate"] = compute_composite_gate(result)
    return result
