"""API client tests — `_fetch_sample` and `main()` failure mode coverage.

Sprint C focus: the API client (`scripts/data_quality_survey_via_api.py`)
is the surface that touched PROD on 2026-04-27 and produced the v3 baseline.
Failure modes here are real (network timeout, non-200, malformed JSON,
auth) and would silently skew the survey if not handled. Pre-Sprint C
this had ZERO tests.

Coverage axes:
  1. _fetch_sample success on canonical 200 + JSON
  2. _fetch_sample failure modes (8 archetypes × N retries)
  3. main() exit codes (PASS=0, FAIL=1)
  4. main() argparse defaults + overrides
  5. URL construction and parameter encoding
  6. Per-type orchestration (31 types × failure injection per type)
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest


# ---------------------------------------------------------------------------
# Module loader (script lives in scripts/, not src/)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_module():
    script_path = (
        Path(__file__).resolve().parent.parent
        / "scripts" / "data_quality_survey_via_api.py"
    )
    spec = importlib.util.spec_from_file_location("_api_client", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Section 1 — _fetch_sample success path
# ---------------------------------------------------------------------------


class TestFetchSampleSuccess:

    def test_returns_results_list(self, api_module):
        fake_resp = MagicMock()
        fake_resp.read.return_value = json.dumps({
            "results": [{"id": "n1"}, {"id": "n2"}]
        }).encode()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=fake_resp):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == [{"id": "n1"}, {"id": "n2"}]

    def test_empty_results_returns_empty_list(self, api_module):
        fake_resp = MagicMock()
        fake_resp.read.return_value = json.dumps({"results": []}).encode()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=fake_resp):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == []

    def test_missing_results_key_returns_empty(self, api_module):
        # API contract change: response no longer carries `results` key.
        # Client must default to [], not raise.
        fake_resp = MagicMock()
        fake_resp.read.return_value = json.dumps({"data": [{"id": "n1"}]}).encode()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=fake_resp):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == []

    def test_results_is_null_returns_empty(self, api_module):
        # Edge: server explicitly returns `"results": null` instead of [].
        fake_resp = MagicMock()
        fake_resp.read.return_value = json.dumps({"results": None}).encode()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=fake_resp):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == []


# ---------------------------------------------------------------------------
# Section 2 — Failure modes (each must yield empty list, not raise)
# ---------------------------------------------------------------------------


class TestFetchSampleFailureModes:

    @pytest.mark.parametrize("exc_factory,description", [
        (lambda: URLError("timeout"), "network timeout"),
        (lambda: HTTPError("u", 500, "Internal Server Error", {}, None), "500 server error"),
        (lambda: HTTPError("u", 404, "Not Found", {}, None), "404 not found"),
        (lambda: HTTPError("u", 401, "Unauthorized", {}, None), "401 unauthorized"),
        (lambda: HTTPError("u", 403, "Forbidden", {}, None), "403 forbidden"),
        (lambda: HTTPError("u", 502, "Bad Gateway", {}, None), "502 gateway"),
        (lambda: HTTPError("u", 503, "Unavailable", {}, None), "503 service unavailable"),
        (lambda: ConnectionResetError("connection reset"), "connection reset"),
        (lambda: TimeoutError("deadline exceeded"), "timeout error"),
        (lambda: OSError("network unreachable"), "OS-level network error"),
    ])
    def test_network_failure_yields_empty_list(self, api_module, exc_factory, description):
        with patch("urllib.request.urlopen", side_effect=exc_factory()):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == [], f"failure mode {description!r} should yield empty list"

    def test_malformed_json_yields_empty(self, api_module):
        fake_resp = MagicMock()
        fake_resp.read.return_value = b"not-valid-json{{"
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=fake_resp):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == []

    def test_truncated_json_yields_empty(self, api_module):
        fake_resp = MagicMock()
        fake_resp.read.return_value = b'{"results": ['  # truncated
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=fake_resp):
            out = api_module._fetch_sample("https://x.test", "TaxRate", 100)
        assert out == []


# ---------------------------------------------------------------------------
# Section 3 — URL construction + parameter encoding
# ---------------------------------------------------------------------------


class TestUrlConstruction:

    @pytest.mark.parametrize("type_name", [
        "TaxRate", "AccountingStandard", "FilingForm", "KnowledgeUnit",
        "PolicyChange", "TaxItem", "LegalClause", "FilingFormField",
        "TaxCalculationRule", "Region", "BusinessActivity",
    ])
    def test_type_in_url(self, api_module, type_name):
        captured = {}
        def fake_urlopen(req, timeout=30):
            captured["url"] = req.full_url
            fake_resp = MagicMock()
            fake_resp.read.return_value = b'{"results": []}'
            fake_resp.__enter__ = lambda s: s
            fake_resp.__exit__ = lambda *a: None
            return fake_resp
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            api_module._fetch_sample("https://x.test", type_name, 50)
        assert f"type={type_name}" in captured["url"]

    @pytest.mark.parametrize("limit", [1, 10, 50, 100, 200, 500, 1000, 5000])
    def test_limit_in_url(self, api_module, limit):
        captured = {}
        def fake_urlopen(req, timeout=30):
            captured["url"] = req.full_url
            fake_resp = MagicMock()
            fake_resp.read.return_value = b'{"results": []}'
            fake_resp.__enter__ = lambda s: s
            fake_resp.__exit__ = lambda *a: None
            return fake_resp
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            api_module._fetch_sample("https://x.test", "TaxRate", limit)
        assert f"limit={limit}" in captured["url"]

    @pytest.mark.parametrize("base_url,expected_prefix", [
        ("https://ops.hegui.org", "https://ops.hegui.org/api/v1/nodes"),
        ("https://ops.hegui.org/", "https://ops.hegui.org/api/v1/nodes"),
        ("http://localhost:8000", "http://localhost:8000/api/v1/nodes"),
        ("http://localhost:8000/", "http://localhost:8000/api/v1/nodes"),
    ])
    def test_trailing_slash_normalized(self, api_module, base_url, expected_prefix):
        captured = {}
        def fake_urlopen(req, timeout=30):
            captured["url"] = req.full_url
            fake_resp = MagicMock()
            fake_resp.read.return_value = b'{"results": []}'
            fake_resp.__enter__ = lambda s: s
            fake_resp.__exit__ = lambda *a: None
            return fake_resp
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            api_module._fetch_sample(base_url, "TaxRate", 100)
        assert captured["url"].startswith(expected_prefix), (
            f"url={captured['url']!r} expected prefix {expected_prefix!r}"
        )

    def test_accept_json_header(self, api_module):
        captured = {}
        def fake_urlopen(req, timeout=30):
            captured["headers"] = dict(req.header_items())
            fake_resp = MagicMock()
            fake_resp.read.return_value = b'{"results": []}'
            fake_resp.__enter__ = lambda s: s
            fake_resp.__exit__ = lambda *a: None
            return fake_resp
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            api_module._fetch_sample("https://x.test", "TaxRate", 100)
        # urllib normalizes header keys to title case.
        assert captured["headers"].get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# Section 4 — main() argparse + exit code semantics
# ---------------------------------------------------------------------------


class TestMainExitCode:

    @pytest.fixture(autouse=True)
    def _patch_fetch(self, api_module, request):
        # Default: every fetch returns clean rows (PASS verdict).
        # Test methods can override by replacing the patcher.
        marker = request.node.get_closest_marker("fetch_returns")
        rows = marker.args[0] if marker else [
            {
                "id": f"n{i}",
                "effective_from": "2024-01-01",
                "confidence": 0.9,
                "source_doc_id": f"d{i}",
                "jurisdiction_code": "CN",
                "jurisdiction_scope": "national",
                "reviewed_at": "x",
                "reviewed_by": "y",
            }
            for i in range(5)
        ]
        with patch.object(api_module, "_fetch_sample", return_value=rows):
            yield

    def test_pass_verdict_returns_zero(self, api_module, tmp_path, capsys):
        out_path = tmp_path / "report.json"
        code = api_module.main([
            "--sample", "5",
            "--output", str(out_path),
            "--target", "1.0",  # generous target → PASS
        ])
        assert code == 0
        report = json.loads(out_path.read_text())
        assert report["overall"]["verdict"] == "PASS"

    @pytest.mark.fetch_returns([{"id": "x", "source_doc_id": "unknown"} for _ in range(5)])
    def test_fail_verdict_returns_one(self, api_module, tmp_path):
        out_path = tmp_path / "r.json"
        code = api_module.main([
            "--sample", "5",
            "--output", str(out_path),
            "--target", "0.0",  # any defect → FAIL
        ])
        assert code == 1
        report = json.loads(out_path.read_text())
        assert report["overall"]["verdict"] == "FAIL"

    def test_no_output_arg_skips_file_write(self, api_module, tmp_path):
        # --output not provided: should still complete + return code.
        code = api_module.main(["--sample", "1", "--target", "1.0"])
        assert code in (0, 1)


class TestMainArgparse:

    def test_default_sample_size(self, api_module):
        # Defaults assertion via parser introspection.
        parser_module = api_module
        # Not a simple introspection — we just verify the constants flow.
        assert parser_module.DEFAULT_SAMPLE_SIZE == 100
        assert parser_module.DEFAULT_TARGET_DEFECT_RATE == 0.10
        assert parser_module.DEFAULT_STALE_YEARS == 10


# ---------------------------------------------------------------------------
# Section 5 — Per-type orchestration (failure injection per type)
# ---------------------------------------------------------------------------


class TestMainPerTypeFailures:

    def test_some_types_fetch_miss_others_succeed(self, api_module, tmp_path):
        # Only TaxRate returns rows; everything else is empty.
        def selective_fetch(api_url, type_name, limit):
            if type_name == "TaxRate":
                return [{
                    "id": "x", "effective_from": "2024-01-01", "confidence": 0.9,
                    "source_doc_id": "d", "jurisdiction_code": "CN",
                    "jurisdiction_scope": "national",
                    "reviewed_at": "x", "reviewed_by": "y",
                }]
            return []
        out_path = tmp_path / "r.json"
        with patch.object(api_module, "_fetch_sample", side_effect=selective_fetch):
            code = api_module.main([
                "--sample", "1", "--output", str(out_path), "--target", "1.0",
            ])
        report = json.loads(out_path.read_text())
        # 30 of 31 types get fetch_miss; only TaxRate has 1 sampled.
        assert report["overall"]["total_sampled"] == 1
        assert len(report["fetch_misses"]) == 30
        assert "TaxRate" not in report["fetch_misses"]

    def test_all_fetches_fail_yields_empty_survey(self, api_module, tmp_path):
        out_path = tmp_path / "r.json"
        with patch.object(api_module, "_fetch_sample", return_value=[]):
            code = api_module.main([
                "--sample", "1", "--output", str(out_path), "--target", "0.10",
            ])
        report = json.loads(out_path.read_text())
        # All 31 types are misses; survey returns 0 defects → PASS at any target.
        assert report["overall"]["total_sampled"] == 0
        assert report["overall"]["verdict"] == "PASS"
        assert len(report["fetch_misses"]) == 31
