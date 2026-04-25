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
