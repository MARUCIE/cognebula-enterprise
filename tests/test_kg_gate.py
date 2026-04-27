"""SOTA composite-gate CI guard.

Asserts that the live `/api/v1/ontology-audit` composite_gate verdict is PASS.
Today this test FAILS (C1=0.449 / C2=43 / C3=+62) — that is the design.

Per SOTA gap doc Day-1 action and Meadows leverage #6 (Information Flows):
"Add `tests/test_kg_gate.py` asserting C0 verdict==PASS in CI on every merge.
Changes when FAIL information reaches decision-makers from 'on demand' to
'every commit.' Higher leverage than tightening gate logic."

Configuration:
  KG_AUDIT_API_URL  Audit endpoint base URL.
                    Default: http://localhost:8400
                    CI sets this to the contabo prod URL via Tailscale.
  KG_AUDIT_TIMEOUT  Per-request timeout seconds. Default: 10.

Skip behavior: if the endpoint is unreachable, the test SKIPS (with reason)
rather than ERRORs — local dev machines without VPN access can run the full
suite without spurious failures. CI infrastructure is responsible for
ensuring KG_AUDIT_API_URL points to a reachable endpoint.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest


AUDIT_URL_BASE = os.environ.get("KG_AUDIT_API_URL", "http://localhost:8400")
AUDIT_TIMEOUT = int(os.environ.get("KG_AUDIT_TIMEOUT", "10"))
AUDIT_PATH = "/api/v1/ontology-audit"


def _fetch_audit() -> dict:
    """Pull live audit JSON; SKIP the test if endpoint unreachable."""
    url = f"{AUDIT_URL_BASE.rstrip('/')}{AUDIT_PATH}"
    try:
        with urllib.request.urlopen(url, timeout=AUDIT_TIMEOUT) as resp:
            return json.load(resp)
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        pytest.skip(f"audit endpoint unreachable at {url}: {exc}")


def test_composite_gate_passes() -> None:
    """C0 verdict must be PASS for the SOTA gate to be considered closed."""
    audit = _fetch_audit()
    cg = audit.get("composite_gate", {})
    verdict = cg.get("verdict")

    if verdict != "PASS":
        breakdown = cg.get("breakdown", {})
        failing = [k for k, v in breakdown.items() if not v.get("pass")]
        details = json.dumps(
            {k: breakdown[k] for k in failing}, indent=2, ensure_ascii=False
        )
        pytest.fail(
            f"composite_gate verdict={verdict!r} (expected PASS); "
            f"failing axes={failing}; details:\n{details}"
        )


def test_canonical_inventory_complete() -> None:
    """All 35 canonical types must be present in production (inventory layer).

    Even when ratio gates fail, missing_from_prod must stay empty — that's the
    one Wave-1 deliverable that should never regress.
    """
    audit = _fetch_audit()
    missing = audit.get("missing_from_prod", [])
    assert missing == [], (
        f"canonical types missing from prod: {missing}; "
        "Wave 1 (B0 build-table batch) must keep this at zero"
    )


def test_audit_endpoint_shape_stable() -> None:
    """Guard against silent breaking changes to the audit endpoint shape.

    Failing this test means the audit JSON contract drifted; downstream
    dashboards (HTML receipt + KPI grid) and this gate itself break together.
    """
    audit = _fetch_audit()
    required_top = {
        "canonical_count",
        "live_count",
        "intersection",
        "missing_from_prod",
        "rogue_in_prod",
        "composite_gate",
    }
    missing_keys = required_top - set(audit.keys())
    assert not missing_keys, f"audit JSON missing keys: {missing_keys}"

    cg = audit["composite_gate"]
    required_cg = {
        "verdict",
        "canonical_coverage_ratio",
        "domain_rogue_count",
        "over_ceiling_by",
        "breakdown",
    }
    missing_cg = required_cg - set(cg.keys())
    assert not missing_cg, f"composite_gate missing keys: {missing_cg}"

    breakdown = cg["breakdown"]
    required_axes = {
        "C1_canonical_coverage",
        "C2_zero_domain_rogues",
        "C3_under_brooks_ceiling",
    }
    missing_axes = required_axes - set(breakdown.keys())
    assert not missing_axes, f"breakdown missing axes: {missing_axes}"


# ---------------------------------------------------------------------------
# Round-4 stub-backfill detector (Munger STOP rule + Meadows test_no_empty)
# ---------------------------------------------------------------------------
#
# These three tests close the Goodhart loop opened on 2026-04-25 → 2026-04-27:
# the legacy C1 canonical_coverage_ratio counts type *presence*, so DDL stubs
# satisfy it. The new tests count type *mass* (rows) and refuse to pass when
# canonical types are empty/tiny ghosts.
#
# Reference: outputs/reports/ontology-audit-swarm/2026-04-27-sota-gap-round4.md
# (5-lens swarm consensus). After stub-backfill remediation completes, these
# tests should turn GREEN. Until then they are DESIGN-FAIL — that is the point.


def test_no_empty_canonical_tables() -> None:
    """No canonical type may have row_count == 0.

    A canonical type registered in v4.2 schema with zero rows is a DDL-only
    ghost (anti-pattern #1 from Round-3 SOTA gap doc). This test fails the
    build the moment a stub-backfill is deployed.
    """
    audit = _fetch_audit()
    metric = audit.get("canonical_min_rows_metric")
    if metric is None:
        pytest.skip(
            "canonical_min_rows_metric not present — "
            "endpoint predates Round-4 stub-backfill detector"
        )
    empty = metric.get("tier_empty", [])
    assert not empty, (
        f"{len(empty)} canonical types are EMPTY (0 rows): {empty}. "
        f"DDL stubs are not coverage. Fill data or remove the schema entry."
    )


def test_c1_canonical_min_rows() -> None:
    """canonical_coverage_ratio_with_min_rows must clear the floor.

    Per Munger STOP rule: until the new ratio crosses 0.50, the ONLY allowed
    work is data ingestion into thin canonical types.
    """
    audit = _fetch_audit()
    cg = audit.get("composite_gate", {})
    ratio = cg.get("canonical_coverage_ratio_with_min_rows")
    target = cg.get("min_rows_target_ratio", 0.50)
    if ratio is None:
        pytest.skip(
            "canonical_coverage_ratio_with_min_rows not present — "
            "endpoint predates Round-4 stub-backfill detector"
        )
    metric = audit.get("canonical_min_rows_metric") or {}
    fails = metric.get("fails", [])
    assert ratio >= target, (
        f"canonical_coverage_ratio_with_min_rows={ratio} < target={target}. "
        f"{len(fails)} canonical types below min-rows threshold; "
        f"first 5: {fails[:5]}"
    )


def test_canonical_types_meet_priority_min_rows() -> None:
    """Backbone canonical types must meet stricter row floors.

    The 5 priority tables (INTERPRETS / KU_ABOUT_TAX / AccountingSubject /
    BusinessActivity / RegulationArticle / ComplianceRule) carry the workload.
    A 50-row stub on AccountingSubject is technically not EMPTY but cannot
    answer 客户 reference-data questions. This test is stricter than
    `test_c1_canonical_min_rows` — it fails on individual priority misses.
    """
    audit = _fetch_audit()
    metric = audit.get("canonical_min_rows_metric") or {}
    if not metric:
        pytest.skip("canonical_min_rows_metric absent — endpoint pre-Round-4")
    PRIORITY = {
        "INTERPRETS": 300_000,
        "KU_ABOUT_TAX": 100_000,
        "AccountingSubject": 1_000,
        "BusinessActivity": 1_000,
    }
    counts = audit.get("canonical_row_counts", {})
    misses: list[str] = []
    for tbl, floor in PRIORITY.items():
        n = counts.get(tbl, 0)
        if n < floor:
            misses.append(f"{tbl}={n}<{floor}")
    assert not misses, (
        f"{len(misses)} priority canonical types below floor: {misses}. "
        f"These are backbone tables; their gap caps anchor_recall ceiling."
    )


def test_schema_shape_drift_below_tolerance() -> None:
    """FU6 anti-drift gate: prevent canonical CREATE blocks diverging from live.

    Catches the 2026-04-27 AccountingSubject incident where canonical declared
    `balanceSide / code / parentId` while live had `balanceDirection / fullText`.
    Without this gate, seed scripts silently drop unmapped fields and feed the
    illusion of progress while real shape drift accumulates.

    Tolerance is intentionally generous on first deploy (audit existing drift,
    don't wedge CI). Tighten as drift gets fixed table-by-table.
    """
    audit = _fetch_audit()
    drift = audit.get("schema_shape_drift")
    if drift is None:
        pytest.skip("schema_shape_drift absent — endpoint pre-FU6 redeploy")
    DRIFT_TOLERANCE = 10  # tune down toward 0 as drift gets fixed
    drift_count = drift.get("drift_count", 0)
    assert drift_count <= DRIFT_TOLERANCE, (
        f"schema-shape drift exceeded tolerance: {drift_count} tables drift "
        f"(tolerance {DRIFT_TOLERANCE}).\n"
        f"  declared_only (canonical claims, live missing): {drift.get('tables_with_declared_only', [])}\n"
        f"  live_only (live has, canonical does not declare): {drift.get('tables_with_live_only', [])}"
    )


# ---------------------------------------------------------------------------
# LegalBench-Tax Stage 1 runner — offline tests (no API call)
# ---------------------------------------------------------------------------


def _import_runner():
    """Load benchmark/run_legalbench_tax.py as a module."""
    import importlib.util
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "lbt_runner", repo_root / "benchmark" / "run_legalbench_tax.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lbt_runner_score_perfect_match() -> None:
    """score_case must return high composite when answer + sources fully cover anchors."""
    runner = _import_runner()
    case = {
        "id": "test_perfect",
        "domain": "CIT",
        "expected_answer": "应纳税所得额 = 1000 × 25% = 250 万元，适用 25% 税率",
        "reasoning_anchors": [
            "TaxCalculationRule:CIT_基本税率",
            "FilingFormField:CIT_A100000_L05",
        ],
        "sources": ["CIT 法 §4"],
    }
    response = {
        "answer": "应纳税所得额 = 1000 × 25% = 250 万元 适用 CIT 法 §4 规定 25% 税率",
        "sources": [{"rows": [["CIT_基本税率"], ["CIT_A100000_L05"]]}],
    }
    result = runner.score_case(case, response)
    assert result["anchor_recall"] == 1.0
    assert result["keyword_overlap"] >= 0.8
    assert result["source_citation"] == 1.0
    assert result["composite"] >= 0.9


def test_lbt_runner_score_zero_match() -> None:
    """score_case must return 0 composite when response is empty/irrelevant."""
    runner = _import_runner()
    case = {
        "id": "test_zero",
        "domain": "VAT",
        "expected_answer": "销项税额 = 100 × 13% = 13 元",
        "reasoning_anchors": ["TaxCalculationRule:VAT_当期应纳"],
        "sources": ["增值税暂行条例 §4"],
    }
    response = {"answer": "未找到相关信息", "sources": []}
    result = runner.score_case(case, response)
    assert result["composite"] == 0.0


def test_lbt_runner_dry_run_does_not_call_api() -> None:
    """run_dry_run must build request bodies without performing network I/O."""
    runner = _import_runner()
    cases = [
        {
            "id": "cit_001",
            "domain": "CIT",
            "question": "招待费扣除限额？",
            "expected_answer": "60% × 5‰",
            "reasoning_anchors": [],
            "sources": [],
        },
    ]
    result = runner.run_dry_run(cases, limit=10, max_preview=1)
    assert result["mode"] == "dry-run"
    assert result["previewed_count"] == 1
    assert result["preview"][0]["request_body"]["mode"] == "rag"
    assert "would_send_to" in result


def test_lbt_runner_chat_request_body_shape() -> None:
    """chat_request_body must produce the exact wire shape kg-api-server expects."""
    runner = _import_runner()
    case = {"question": "测试问题", "id": "x"}
    body = runner.chat_request_body(case, limit=5)
    assert body == {"question": "测试问题", "mode": "rag", "limit": 5}


# ---------------------------------------------------------------------------
# Stage 1 Poe provider tests (offline, no network)
# ---------------------------------------------------------------------------


def test_lbt_runner_build_rag_prompt_contains_context_and_question() -> None:
    """build_rag_prompt must inject all 5 fields per result + question section."""
    runner = _import_runner()
    results = [
        {
            "id": "TaxCalculationRule:CIT_基本税率",
            "table": "TaxCalculationRule",
            "title": "企业所得税基本税率 25%",
            "name": "",
            "text": "居民企业适用 25% 基本税率",
        },
        {
            "id": "FilingFormField:CIT_A100000_L05",
            "table": "FilingFormField",
            "title": "纳税调整增加额",
            "name": "",
            "text": "汇总 A105000 调整明细表",
        },
    ]
    prompt = runner.build_rag_prompt("CIT 基本税率是多少？", results)
    assert "知识图谱上下文" in prompt
    assert "用户问题" in prompt
    assert "CIT 基本税率是多少？" in prompt
    assert "TaxCalculationRule" in prompt
    assert "CIT_A100000_L05" in prompt
    assert "结构化的回答" in prompt


def test_lbt_runner_build_rag_prompt_handles_empty_results() -> None:
    """Empty retrieval must produce a prompt that signals no context found."""
    runner = _import_runner()
    prompt = runner.build_rag_prompt("某问题", [])
    assert "未检索到" in prompt
    assert "某问题" in prompt


def test_lbt_runner_poe_chat_payload_shape() -> None:
    """poe_chat_payload must produce OpenAI-compatible chat-completions shape.

    Uses real Poe bot name (lowercase-dot-version) per Poe pricing page.
    """
    runner = _import_runner()
    payload = runner.poe_chat_payload(
        model="gemini-3.1-pro",
        system="你是 CogNebula 助手",
        prompt="问题：CIT 税率？",
    )
    assert payload["model"] == "gemini-3.1-pro"
    assert payload["messages"][0] == {"role": "system", "content": "你是 CogNebula 助手"}
    assert payload["messages"][1] == {"role": "user", "content": "问题：CIT 税率？"}
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 4096


def test_lbt_runner_poe_chat_payload_omits_system_when_empty() -> None:
    """Empty system prompt must yield messages without a system entry."""
    runner = _import_runner()
    payload = runner.poe_chat_payload(model="gpt-5.4-nano", system="", prompt="hi")
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"


def test_lbt_runner_call_poe_errors_without_key() -> None:
    """call_poe must short-circuit with error when api_key is empty (no network call)."""
    runner = _import_runner()
    result = runner.call_poe(api_key="", model="gpt-5.4-nano", system="", prompt="q")
    assert "error" in result
    assert "POE_API_KEY" in result["error"]


def test_lbt_runner_default_poe_model_is_real_poe_name() -> None:
    """POE_MODEL_DEFAULT must match a real Poe bot (lowercase-dot-version).

    Guards against regressing to assumed names like 'Gemini-3-Pro'. Pinned
    against the pricing snapshot dict so any drift is visible at test time.
    """
    runner = _import_runner()
    assert runner.POE_MODEL_DEFAULT in runner.POE_MODEL_PRICING_USD_PER_1M
    # Naming convention check: lowercase, contains hyphen, no caps in body
    assert runner.POE_MODEL_DEFAULT == runner.POE_MODEL_DEFAULT.lower()
    assert "-" in runner.POE_MODEL_DEFAULT


def test_lbt_runner_eval_system_prompt_excludes_genui() -> None:
    """SYSTEM_PROMPT_EVAL must NOT carry the server's GenUI HTML directives.

    The server's SYSTEM_PROMPT_RAG includes <!--GENUI--> instructions that
    pollute answer text and skew keyword scoring. The eval-mode prompt is
    intentionally simpler.
    """
    runner = _import_runner()
    p = runner.SYSTEM_PROMPT_EVAL
    assert "GENUI" not in p
    assert "HTML" not in p or "不输出 HTML" in p
    assert "法规文号" in p  # must demand statute citation
