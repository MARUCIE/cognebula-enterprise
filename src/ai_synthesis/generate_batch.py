#!/usr/bin/env python3
"""Batch generator for AI-synthesized finance/tax knowledge nodes.

Generates N candidate nodes for a given industry, runs each through
the full 4-swarm QC pipeline, and writes results to data/synthesized/{industry}/.

Usage:
    python -m ai_synthesis.generate_batch --industry manufacturing --count 10
    python -m ai_synthesis.generate_batch --industry retail --count 5 --dry-run
    python -m ai_synthesis.generate_batch --industry technology --count 20 --evaluate

Dependencies: requests (pip install requests)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure parent dir is on path so we can import as package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_synthesis.swarm_pipeline import (
    SwarmPipeline,
    GateDecision,
    PipelineResult,
)

logger = logging.getLogger("generate_batch")

# Common scenario types per industry
INDUSTRY_SCENARIOS: dict[str, list[str]] = {
    "manufacturing": [
        "vat_input_credit", "vat_output_13pct", "vat_export_refund",
        "cit_rd_super_deduction", "cit_accelerated_depreciation",
        "pit_salary_withholding", "risk_vat_burden_low",
        "vat_input_transfer_out", "cit_hnte_15pct", "risk_invoice_mismatch",
    ],
    "technology": [
        "vat_service_6pct", "cit_hnte_15pct", "cit_rd_super_deduction",
        "cit_ip_box_deduction", "pit_equity_incentive",
        "risk_rd_ratio", "risk_hnte_renewal", "vat_software_refund",
        "pit_salary_comprehensive", "cit_loss_carryforward",
    ],
    "retail": [
        "vat_output_13pct", "vat_small_taxpayer_3pct", "cit_standard_25pct",
        "cit_small_profit_5pct", "pit_bonus_separate",
        "risk_invoice_void_rate", "risk_zero_declaration",
        "vat_mixed_sales", "pit_labor_service", "risk_cost_ratio",
    ],
    "construction": [
        "vat_construction_9pct", "vat_simple_method_3pct", "cit_standard_25pct",
        "pit_labor_service", "risk_invoice_mismatch",
        "cit_wage_deduction", "risk_input_concentration",
        "vat_input_credit", "cit_depreciation_accelerated", "risk_late_filing",
    ],
    "financial": [
        "vat_loan_interest_6pct", "cit_standard_25pct", "pit_stock_dividend",
        "risk_transfer_pricing", "risk_large_cash",
        "vat_service_6pct", "cit_bad_debt", "pit_bonus_separate",
        "risk_personal_account", "cit_charity_deduction",
    ],
    "real_estate": [
        "vat_property_sale_9pct", "cit_standard_25pct", "land_vat_clearance",
        "risk_land_vat_avoidance", "pit_property_transfer",
        "cit_deferred_revenue", "stamp_tax_contract", "risk_depreciation_mismatch",
        "vat_simple_method_5pct", "risk_surplus_distribution",
    ],
    "general": [
        "cit_standard_25pct", "pit_salary_comprehensive", "vat_output_13pct",
        "risk_late_filing", "cit_entertainment_deduction",
        "pit_special_deductions", "risk_zero_declaration",
        "cit_advertising_deduction", "vat_input_credit", "pit_annual_reconciliation",
    ],
}


def _get_scenarios(industry: str, count: int) -> list[str]:
    """Return a list of scenario types for the given industry."""
    base = INDUSTRY_SCENARIOS.get(industry, INDUSTRY_SCENARIOS["general"])
    # Cycle through scenarios if count exceeds available types
    result = []
    for i in range(count):
        result.append(base[i % len(base)])
    return result


def run_batch(
    industry: str,
    count: int,
    graph_path: str = "data/finance-tax-graph",
    dry_run: bool = False,
    output_dir: str | None = None,
) -> dict:
    """Generate N nodes and run through the pipeline.

    Returns summary statistics.
    """
    pipeline = SwarmPipeline(graph_path=graph_path, dry_run=dry_run)
    scenarios = _get_scenarios(industry, count)

    # Output directory
    if output_dir is None:
        project_root = Path(__file__).resolve().parent.parent.parent
        out_path = project_root / "data" / "synthesized" / industry
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Run timestamp for this batch
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    batch_id = f"batch_{run_ts}"

    results: list[PipelineResult] = []
    stats = {
        "batch_id": batch_id,
        "industry": industry,
        "count": count,
        "dry_run": dry_run,
        "auto_inject": 0,
        "human_review": 0,
        "reject": 0,
        "total_elapsed": 0.0,
    }

    logger.info("Starting batch: industry=%s count=%d dry_run=%s", industry, count, dry_run)
    batch_start = time.monotonic()

    for i, scenario in enumerate(scenarios):
        logger.info("--- Node %d/%d: scenario=%s ---", i + 1, count, scenario)
        result = pipeline.run(industry=industry, scenario_type=scenario)
        results.append(result)

        # Tally
        if result.gate_decision == GateDecision.AUTO_INJECT:
            stats["auto_inject"] += 1
        elif result.gate_decision == GateDecision.HUMAN_REVIEW:
            stats["human_review"] += 1
        else:
            stats["reject"] += 1

        # Write individual result
        node_file = out_path / f"{batch_id}_{i:03d}_{scenario}.json"
        with open(node_file, "w") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(
            "Node %d: decision=%s confidence=%.2f -> %s",
            i + 1, result.gate_decision.value, result.final_confidence, node_file.name,
        )

    stats["total_elapsed"] = round(time.monotonic() - batch_start, 2)
    stats["avg_elapsed"] = round(stats["total_elapsed"] / count, 2) if count > 0 else 0
    stats["acceptance_rate"] = round(
        (stats["auto_inject"] + stats["human_review"]) / count, 3
    ) if count > 0 else 0

    # Write batch summary
    summary_file = out_path / f"{batch_id}_summary.json"
    with open(summary_file, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info("Batch complete: %s", json.dumps(stats, indent=2))

    return stats


def run_evaluation(
    golden_path: str,
    graph_path: str = "data/finance-tax-graph",
    dry_run: bool = False,
) -> dict:
    """Evaluate pipeline against golden test set."""
    pipeline = SwarmPipeline(graph_path=graph_path, dry_run=dry_run)
    return pipeline.evaluate(golden_path)


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate and QC finance/tax knowledge nodes"
    )
    parser.add_argument(
        "--industry", default="manufacturing",
        help="Target industry (manufacturing/technology/retail/construction/financial/real_estate/general)",
    )
    parser.add_argument("--count", type=int, default=10, help="Number of nodes to generate")
    parser.add_argument("--graph", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Use mock LLM responses")
    parser.add_argument("--output", help="Custom output directory")
    parser.add_argument(
        "--evaluate", action="store_true",
        help="Run evaluation against golden test set instead of batch generation",
    )
    parser.add_argument(
        "--golden", default=None,
        help="Path to golden test set JSON (default: src/ai_synthesis/golden_test_set.json)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.evaluate:
        golden = args.golden or str(
            Path(__file__).resolve().parent / "golden_test_set.json"
        )
        stats = run_evaluation(golden, graph_path=args.graph, dry_run=args.dry_run)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    stats = run_batch(
        industry=args.industry,
        count=args.count,
        graph_path=args.graph,
        dry_run=args.dry_run,
        output_dir=args.output,
    )
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
