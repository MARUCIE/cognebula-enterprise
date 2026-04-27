#!/usr/bin/env python3
"""FU5 Phase-2 primer — seed ComplianceRule from data/extracted corpus.

Round-4 §5.5 FU5 (phase-2 PDF extraction): pushes 9+ canonical types over
their min-rows threshold so C1+ ratio breaks 0.5. This script handles ONE
type as a primer: ComplianceRule.

Source: data/extracted/doctax_extracted.json — 6628 pre-processed records
already tagged with `node_type`. Filtering `node_type == "ComplianceRule"`
yields 163 records, just above the 100-row C1+ threshold for ComplianceRule.

Canonical schema (schemas/ontology_v4.2.cypher line 93):
    id STRING, name STRING, description STRING,
    severity STRING, sourceClauseId STRING, status STRING

Field mapping (extracted -> canonical):
    id           = "CR_EXT_" + extracted.id     (16-hex; collision-safe)
    name         = extracted.title              (≤80 char headline)
    description  = extracted.content            (200-400 char body)
    severity     = inferred from category/keywords (low/medium/high)
    sourceClauseId = extracted.source_file      (lineage to .docx/.pdf)
    status       = "active"                     (all extracted are current)

Reversibility:
    MATCH (n:ComplianceRule) WHERE n.id STARTS WITH 'CR_EXT_' DELETE n;

Usage:
    python src/seed/seed_compliance_rule_extracted.py --dry-run
    python src/seed/seed_compliance_rule_extracted.py
    # Then apply via wrapper:
    python scripts/apply_round4_seeds_via_api.py --only ComplianceRule

HITL note: ONLY adds rows; safe on prod. Records to ingestion-manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion_manifest import record_ingestion  # noqa: E402

CORPUS_PATH = PROJECT_ROOT / "data" / "extracted" / "doctax_extracted.json"

# Severity heuristics — keyword-based, no LLM. Conservative defaults
# (medium) so over-classification of high doesn't create noise.
HIGH_KEYWORDS = {
    "重大", "严重", "刑事", "犯罪", "偷税", "逃税", "虚开", "洗钱",
    "高风险", "重要", "强制", "禁止",
}
LOW_KEYWORDS = {
    "建议", "提示", "参考", "可选", "一般", "常规",
}


def _infer_severity(record: dict) -> str:
    blob = " ".join([
        record.get("title", ""),
        record.get("content", ""),
        " ".join(record.get("keywords", [])),
        record.get("category", ""),
    ])
    if any(k in blob for k in HIGH_KEYWORDS):
        return "high"
    if any(k in blob for k in LOW_KEYWORDS):
        return "low"
    return "medium"


def _build_records() -> list[dict]:
    """Filter and map ComplianceRule records from extracted corpus."""
    if not CORPUS_PATH.is_file():
        raise FileNotFoundError(
            f"corpus missing: {CORPUS_PATH}. "
            f"This seed requires the .gitignored data/extracted/ tree."
        )
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    out: list[dict] = []
    for r in raw:
        if r.get("node_type") != "ComplianceRule":
            continue
        ext_id = r.get("id")
        if not ext_id:
            continue
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "").strip()
        if not title or not content:
            continue  # skip degenerate records
        out.append(
            {
                "id": f"CR_EXT_{ext_id}",
                "name": title[:200],         # name kept compact
                "category": (r.get("category") or "未分类")[:80],
                # Below this line: canonical-declared but live ComplianceRule
                # rejects them (probed 2026-04-27). Wrapper SEEDS entry has
                # them in drop_keys; kept here so the seed is self-describing
                # and immediately re-applicable after FU6 prod-side ALTER.
                "description": content[:1500],
                "severity": _infer_severity(r),
                "sourceClauseId": r.get("source_file", ""),
                "status": "active",
                "_tier": "extracted",
            }
        )
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="Build records and print summary; do not write")
    p.add_argument("--db", help="(unused; apply via execute-ddl wrapper)")
    args = p.parse_args()

    records = _build_records()
    print(f"FU5 primer: {len(records)} ComplianceRule records prepared")
    sev_counts = {}
    for r in records:
        sev_counts[r["severity"]] = sev_counts.get(r["severity"], 0) + 1
    print(f"  severity distribution: {sev_counts}")
    print(f"  apply via: python scripts/apply_round4_seeds_via_api.py --only ComplianceRule")

    if args.dry_run:
        record_ingestion(
            source_file=__file__,
            rows_written={"ComplianceRule": 0},
            duration_s=0.0,
            dry_run=True,
            note=f"dry-run: would add {len(records)} ComplianceRule rows from extracted corpus",
        )
        return 0

    # This script does not write directly — wrapper handles the API POST.
    # Print first/last sample for review.
    if records:
        print("  sample[0]:", json.dumps({
            k: v for k, v in records[0].items() if not k.startswith("_")
        }, ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
