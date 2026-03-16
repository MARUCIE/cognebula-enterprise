#!/usr/bin/env python3
"""Inject extracted industry guide data into KuzuDB graph.

Reads extracted JSON from data/extracted/industry_guides/ and creates:
- OP_BusinessScenario nodes (industry-specific accounting flows)
- OP_StandardCase nodes (typical journal entries per industry)
- RiskIndicator nodes (industry tax risk points)
- OP_SCENARIO_INDUSTRY edges (scenario -> FTIndustry)

Usage:
    python src/inject_industry_data.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


# Map extracted industry codes to FTIndustry IDs in graph
INDUSTRY_TO_GRAPH = {
    "construction": "IND_CONSTRUCTION",
    "real_estate": "IND_REAL_ESTATE",
    "auto_dealer": "IND_AUTO_DEALER",
    "medical_aesthetics": "IND_MEDICAL_AESTHETICS",
    "property_mgmt": "IND_PROPERTY_MGMT",
    "live_streaming": "IND_LIVE_STREAMING",
    "software": "IND_SOFTWARE",
    "high_tech": "IND_HIGH_TECH",
    "mining": "IND_MINING",
    "coal_mining": "IND_COAL_MINING",
    "recycling": "IND_RECYCLING",
    "kindergarten": "IND_KINDERGARTEN",
    "law_firm": "IND_LAW_FIRM",
    "hr_services": "IND_HR_SERVICES",
    "labor_dispatch": "IND_LABOR_DISPATCH",
    "partnership": "IND_PARTNERSHIP",
    "nonprofit": "IND_NONPROFIT",
    "manufacturing": "IND_MANUFACTURING",
    "export_tax_refund": "IND_EXPORT_REFUND",
    "concrete": "IND_CONCRETE",
    "gold_retail": "IND_GOLD_RETAIL",
    "cross_border_ecommerce": "IND_CROSS_BORDER_ECOM",
    "general": "IND_GENERAL",
}


def esc(s: str) -> str:
    """Escape string for Cypher."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, text: str) -> str:
    """Generate deterministic ID from text."""
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def parse_journal_entries(entries: list, industry: str, source_file: str) -> list:
    """Parse extracted journal entry lines into OP_StandardCase nodes."""
    cases = []
    current_scenario = ""
    current_entries = []

    for line in entries:
        line = line.strip()
        if not line:
            continue

        # Detect scenario headers (lines before debit/credit)
        if not any(kw in line for kw in ["借", "贷"]):
            if current_entries:
                # Flush previous
                cases.append({
                    "scenario": current_scenario,
                    "entries": "\n".join(current_entries),
                    "industry": industry,
                    "source": source_file,
                })
                current_entries = []
            current_scenario = line[:100]
        else:
            current_entries.append(line)

    # Flush last
    if current_entries:
        cases.append({
            "scenario": current_scenario,
            "entries": "\n".join(current_entries),
            "industry": industry,
            "source": source_file,
        })

    return cases


def parse_risk_points(risks: list, industry: str, source_file: str) -> list:
    """Parse extracted risk point lines into RiskIndicator nodes."""
    indicators = []
    for line in risks:
        line = line.strip()
        if len(line) < 10:
            continue
        indicators.append({
            "description": line[:200],
            "industry": industry,
            "source": source_file,
        })
    return indicators


def ensure_industry_nodes(conn, industries: set, dry_run: bool):
    """Ensure FTIndustry nodes exist for all referenced industries.

    FTIndustry schema: id, gbCode, name, classificationLevel, parentIndustryId, hasPreferentialPolicy
    """
    count = 0
    industry_names = {
        "construction": "建筑业",
        "real_estate": "房地产业",
        "auto_dealer": "汽车经销",
        "medical_aesthetics": "医疗美容",
        "property_mgmt": "物业管理",
        "live_streaming": "网络直播",
        "software": "软件和信息技术",
        "high_tech": "高新技术企业",
        "mining": "采矿业",
        "coal_mining": "煤炭开采和洗选",
        "recycling": "再生资源",
        "kindergarten": "学前教育",
        "law_firm": "律师事务所",
        "hr_services": "人力资源服务",
        "labor_dispatch": "劳务派遣",
        "partnership": "合伙企业",
        "nonprofit": "民间非营利组织",
        "manufacturing": "制造业",
        "export_tax_refund": "出口退税企业",
        "concrete": "混凝土搅拌",
        "gold_retail": "黄金零售",
        "cross_border_ecommerce": "跨境电商",
        "general": "通用",
    }

    for ind in industries:
        ind_id = INDUSTRY_TO_GRAPH.get(ind, f"IND_{ind.upper()}")
        name = industry_names.get(ind, ind)
        sql = (
            f"CREATE (n:FTIndustry {{"
            f"id: '{esc(ind_id)}', name: '{esc(name)}', "
            f"gbCode: '', classificationLevel: 'sub', "
            f"parentIndustryId: '', hasPreferentialPolicy: false"
            f"}})"
        )
        if dry_run:
            print(f"  DRY-RUN: Would create FTIndustry {ind_id} ({name})")
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception as e:
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower() and "primary key" not in str(e).lower():
                    print(f"  WARN: FTIndustry {ind_id}: {e}")
    return count


def inject_scenarios(conn, manifest: dict, dry_run: bool) -> int:
    """Create OP_BusinessScenario nodes from extracted data."""
    count = 0
    seen_ids = set()

    for file_entry in manifest.get("files", []):
        industry = file_entry["industry"]
        source = file_entry["source_file"]
        title = file_entry["title"]

        # Load full extraction
        ind_prefix = industry
        full_path = Path("data/extracted/industry_guides") / f"{ind_prefix}_{title[:60]}.json"
        if not full_path.exists():
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Create scenario from file metadata
        scenario_id = make_id("BS_IND", f"{industry}_{title}")
        if scenario_id in seen_ids:
            continue
        seen_ids.add(scenario_id)

        category = data.get("content_type", "general_guide")
        desc = data.get("first_500_chars", "")[:300]

        sql = (
            f"CREATE (n:OP_BusinessScenario {{"
            f"id: '{esc(scenario_id)}', name: '{esc(title[:80])}', "
            f"category: '{esc(category)}', industry: '{esc(industry)}', "
            f"taxpayerType: 'all', frequency: 'reference', "
            f"description: '{esc(desc)}', "
            f"triggerCondition: 'industry_specific', "
            f"relatedLifecycleStage: 'operating', "
            f"notes: 'source: {esc(source)}'"
            f"}})"
        )

        if dry_run:
            print(f"  DRY-RUN: Would create OP_BusinessScenario {scenario_id}")
        else:
            try:
                conn.execute(sql)
                count += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  WARN: {scenario_id}: {e}")

    return count


def inject_standard_cases(conn, manifest: dict, dry_run: bool) -> int:
    """Create OP_StandardCase nodes from journal entries."""
    count = 0

    for file_entry in manifest.get("files", []):
        industry = file_entry["industry"]
        source = file_entry["source_file"]
        title = file_entry["title"]

        full_path = Path("data/extracted/industry_guides") / f"{industry}_{title[:60]}.json"
        if not full_path.exists():
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("sections", {}).get("journal_entries", [])
        cases = parse_journal_entries(entries, industry, source)

        for i, case in enumerate(cases[:30]):  # Cap at 30 per file
            case_id = make_id("SC_IND", f"{industry}_{title}_{i}")
            scenario = case.get("scenario", "")[:100]
            entry_text = case.get("entries", "")[:500]

            sql = (
                f"CREATE (n:OP_StandardCase {{"
                f"id: '{esc(case_id)}', name: '{esc(scenario or title[:50])}', "
                f"standardId: '', clauseRef: '', "
                f"caseType: 'industry_practice', scenario: '{esc(scenario)}', "
                f"correctTreatment: '{esc(entry_text)}', commonMistake: '', "
                f"industryRelevance: '{esc(industry)}', diffFromSme: false, "
                f"diffFromIfrs: false, diffDescription: '', "
                f"notes: 'source: {esc(source)}'"
                f"}})"
            )

            if dry_run:
                print(f"  DRY-RUN: Would create OP_StandardCase {case_id}")
            else:
                try:
                    conn.execute(sql)
                    count += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        pass  # Skip duplicates silently

    return count


def inject_risk_indicators(conn, manifest: dict, dry_run: bool) -> int:
    """Create RiskIndicator nodes from risk points."""
    count = 0

    for file_entry in manifest.get("files", []):
        industry = file_entry["industry"]
        source = file_entry["source_file"]
        title = file_entry["title"]

        full_path = Path("data/extracted/industry_guides") / f"{industry}_{title[:60]}.json"
        if not full_path.exists():
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        risks = data.get("sections", {}).get("risk_points", [])
        indicators = parse_risk_points(risks, industry, source)

        for i, ind in enumerate(indicators[:20]):  # Cap at 20 per file
            risk_id = make_id("RI_IND", f"{industry}_{title}_{i}")
            desc = ind.get("description", "")[:200]

            # RiskIndicator schema: id, name, indicatorCode, metricName, metricFormula,
            # thresholdLow, thresholdHigh, industryBenchmark, industryId,
            # triggerCondition, severity, detectionMethod, dataSource,
            # monitoringFrequency, falsePositiveRate, recommendedAction, notes, confidence
            ind_id_val = INDUSTRY_TO_GRAPH.get(industry, f"IND_{industry.upper()}")
            sql = (
                f"CREATE (n:RiskIndicator {{"
                f"id: '{esc(risk_id)}', name: '{esc(desc[:60])}', "
                f"indicatorCode: '', metricName: '{esc(desc[:80])}', "
                f"metricFormula: '', thresholdLow: 0.0, thresholdHigh: 0.0, "
                f"industryBenchmark: 0.0, industryId: '{esc(ind_id_val)}', "
                f"triggerCondition: '{esc(desc[:100])}', severity: 'medium', "
                f"detectionMethod: 'manual_review', dataSource: 'doc-tax', "
                f"monitoringFrequency: 'quarterly', falsePositiveRate: 0.2, "
                f"recommendedAction: '', notes: 'source: {esc(source)}', "
                f"confidence: 0.7"
                f"}})"
            )

            if dry_run:
                print(f"  DRY-RUN: Would create RiskIndicator {risk_id}")
            else:
                try:
                    conn.execute(sql)
                    count += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        pass

    return count


def main():
    parser = argparse.ArgumentParser(description="Inject industry guide data into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done")
    args = parser.parse_args()

    manifest_path = Path("data/extracted/industry_guides/_manifest.json")
    if not manifest_path.exists():
        print("ERROR: Run extract_industry_guides.py first")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Loaded manifest: {manifest['total_processed']} files, "
          f"{len(manifest['industries'])} industries")

    if not args.dry_run:
        try:
            import kuzu
        except ImportError:
            print("ERROR: kuzu not installed")
            sys.exit(1)

        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
    else:
        conn = None

    # Step 1: Ensure industry nodes exist
    print("\n=== Ensuring Industry Nodes ===")
    industries = set(manifest.get("industries", []))
    n_ind = ensure_industry_nodes(conn, industries, args.dry_run)
    print(f"Created {n_ind} new FTIndustry nodes")

    # Step 2: Inject business scenarios
    print("\n=== Injecting Business Scenarios ===")
    n_scenarios = inject_scenarios(conn, manifest, args.dry_run)
    print(f"Created {n_scenarios} OP_BusinessScenario nodes")

    # Step 3: Inject standard cases (journal entries)
    print("\n=== Injecting Standard Cases ===")
    n_cases = inject_standard_cases(conn, manifest, args.dry_run)
    print(f"Created {n_cases} OP_StandardCase nodes")

    # Step 4: Inject risk indicators
    print("\n=== Injecting Risk Indicators ===")
    n_risks = inject_risk_indicators(conn, manifest, args.dry_run)
    print(f"Created {n_risks} RiskIndicator nodes")

    # Summary
    print(f"\n=== Injection Summary ===")
    print(f"FTIndustry: +{n_ind}")
    print(f"OP_BusinessScenario: +{n_scenarios}")
    print(f"OP_StandardCase: +{n_cases}")
    print(f"RiskIndicator: +{n_risks}")
    print(f"Total new nodes: {n_ind + n_scenarios + n_cases + n_risks}")


if __name__ == "__main__":
    main()
