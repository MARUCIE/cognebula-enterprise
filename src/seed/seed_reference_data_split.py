#!/usr/bin/env python3
"""Wrapper-compatible adapters for the 3 tier_empty reference seeds.

Source JSONs ship in `data/seed_*.json` (45-138 records each). The legacy
`src/inject_seed_reference_data.py` opened a direct kuzu.Connection, which
fails against the uvicorn-locked PROD instance. This module exposes
`_build_records()`-style builders so `scripts/apply_round4_seeds_via_api.py`
can route them through the admin-DDL endpoint.

Live-shape probe (2026-04-27, CREATE-and-error mining):
    SocialInsuranceRule  : id, name, description, regionId       (+ lineage envelope)
    InvoiceRule          : id, name, description, invoiceType    (+ lineage envelope)
    IndustryBenchmark    : id, metric, industryId                (+ lineage envelope)

Field mapping is encoded in apply_round4_seeds_via_api.py SEEDS entries; here
we just synthesize the description blobs that pack the dropped JSON fields
(rates / floors / ceilings / units / years) so consumers don't lose them.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load(rel: str) -> list[dict]:
    p = PROJECT_ROOT / rel
    if not p.is_file():
        raise FileNotFoundError(f"reference seed missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _build_records_social_insurance() -> list[dict]:
    """Read seed_social_insurance.json (138 records) -> wrapper records.

    Live keeps {id, name, description, regionId}. We pack the rate/base/month
    structure into description so downstream queries can still tokenize.
    """
    raw = _load("data/seed_social_insurance.json")
    out: list[dict] = []
    for r in raw:
        rid = r.get("id")
        name = (r.get("name") or "").strip()
        if not rid or not name:
            continue
        desc = (
            f"险种：{r.get('insuranceType', '')}；"
            f"单位费率：{r.get('employerRate', '')}；"
            f"个人费率：{r.get('employeeRate', '')}；"
            f"基数下限：{r.get('baseFloor', '')}；"
            f"基数上限：{r.get('baseCeiling', '')}；"
            f"调整月份：{r.get('adjustmentMonth', '')}；"
            f"生效日期：{r.get('effectiveDate', '')}。"
        )
        out.append(
            {
                "id": rid,
                "name": name[:200],
                "description": desc[:1500],
                "regionId": (r.get("regionId") or "")[:80],
                "_tier": "reference_seed_split",
            }
        )
    return out


def _build_records_invoice_rule() -> list[dict]:
    """Read seed_invoice_rules.json (40 records) -> wrapper records.

    Live keeps {id, name, description, invoiceType}. Pack ruleType/condition/
    procedure/legalBasis into description.
    """
    raw = _load("data/seed_invoice_rules.json")
    out: list[dict] = []
    for r in raw:
        rid = r.get("id")
        name = (r.get("name") or "").strip()
        if not rid or not name:
            continue
        desc = (
            f"规则类型：{r.get('ruleType', '')}；"
            f"条件：{r.get('condition', '')}；"
            f"流程：{r.get('procedure', '')}；"
            f"法律依据：{r.get('legalBasis', '')}。"
        )
        out.append(
            {
                "id": rid,
                "name": name[:200],
                "description": desc[:1500],
                "invoiceType": (r.get("invoiceType") or "")[:80],
                "_tier": "reference_seed_split",
            }
        )
    return out


def _build_records_tax_accounting_gap_extended() -> list[dict]:
    """Read seed_tax_accounting_gap.json (50 records, IDs TAG-* — disjoint from
    Q1 batch IDs tag_NN) -> wrapper records.

    Live TaxAccountingGap (probe 2026-04-27):
      id, name, description, gapKind, direction + lineage envelope.
    JSON adds 50 new gaps with accountingTreatment / taxTreatment / impact /
    example / legalBasis structure — all packed into description so consumers
    don't lose semantic detail. Field map: gapType -> gapKind,
    adjustmentDirection -> direction.
    """
    raw = _load("data/seed_tax_accounting_gap.json")
    out: list[dict] = []
    for r in raw:
        rid = r.get("id")
        name = (r.get("name") or "").strip()
        if not rid or not name:
            continue
        desc = (
            f"会计处理：{r.get('accountingTreatment', '')}；"
            f"税务处理：{r.get('taxTreatment', '')}；"
            f"影响：{r.get('impact', '')}；"
            f"示例：{r.get('example', '')}；"
            f"A105000线索：{r.get('A105000LineRef', '')}；"
            f"递延税项类型：{r.get('deferredTaxType', '')}；"
            f"法条依据：{r.get('legalBasis', '')}。"
        )
        out.append(
            {
                "id": rid,
                "name": name[:200],
                "description": desc[:1500],
                "gapType": (r.get("gapType") or "")[:40],
                "adjustmentDirection": (r.get("adjustmentDirection") or "")[:20],
                "_tier": "reference_seed_split_tag",
            }
        )
    return out


def _build_records_industry_benchmark() -> list[dict]:
    """Read seed_industry_benchmarks.json (45 records) -> wrapper records.

    Live keeps {id, metric, industryId}. No description field on this table
    (probe-confirmed). Pack the value range + year + region into the metric
    string so the consumer side can still parse it.
    """
    raw = _load("data/seed_industry_benchmarks.json")
    out: list[dict] = []
    for r in raw:
        rid = r.get("id")
        ratio = (r.get("ratioName") or "").strip()
        ind = (r.get("industryCode") or "").strip()
        if not rid or not ratio:
            continue
        # metric encodes name + range + unit + year + region in one string
        # since live has no separate value/unit/year columns
        unit = r.get("unit", "")
        metric = (
            f"{ratio} [{r.get('minValue', '')}-{r.get('maxValue', '')}]{unit}"
            f" · {r.get('year', '')} · {r.get('regionId', '')}"
        )
        out.append(
            {
                "id": rid,
                "metric": metric[:200],
                "industryId": ind[:80],
                "_tier": "reference_seed_split",
            }
        )
    return out


def main() -> int:
    sir = _build_records_social_insurance()
    inv = _build_records_invoice_rule()
    ind = _build_records_industry_benchmark()
    print(f"SocialInsuranceRule: {len(sir)} records")
    print(f"InvoiceRule:         {len(inv)} records")
    print(f"IndustryBenchmark:   {len(ind)} records")
    print(f"Total: {len(sir) + len(inv) + len(ind)} new rows")
    if sir:
        print(f"  SIR sample: {json.dumps(sir[0], ensure_ascii=False)[:200]}")
    if inv:
        print(f"  INV sample: {json.dumps(inv[0], ensure_ascii=False)[:200]}")
    if ind:
        print(f"  IND sample: {json.dumps(ind[0], ensure_ascii=False)[:200]}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
