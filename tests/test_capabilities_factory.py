"""Tests for `src/_lib/capabilities.py` — Sweep-7 / S18.26.

Locks the factory's signature contract + payload shape so a future
refactor can't silently regress what `scripts/runtime_audit.sh`
expects from the OPTIONS endpoint.

Coverage:
  1. register_capabilities_endpoint binds an OPTIONS route at the
     expected path
  2. payload shape: {module, deploy_anchor, route_count, routes[]}
  3. module_name parameter is honored (not hardcoded)
  4. routes[] enumerates all registered routes (live read, not snapshot)
  5. deploy_anchor reads from env var, defaults to "unknown" when unset
  6. CAPABILITIES_PATH constant is the canonical path runtime_audit.sh
     hits — single source of truth pinned by test
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src._lib.capabilities import (  # noqa: E402
    CAPABILITIES_PATH,
    DEFAULT_DEPLOY_ANCHOR_ENV,
    register_capabilities_endpoint,
)


def _build_app_with_capabilities(module_name: str = "test_module"):
    """Helper: build a fresh FastAPI app + register the capabilities
    endpoint + add a couple of dummy routes for enumeration testing."""
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/dummy/alpha")
    def alpha():
        return {"ok": True}

    @app.get("/dummy/beta")
    def beta():
        return {"ok": True}

    register_capabilities_endpoint(app, module_name=module_name)
    return app


def test_capabilities_path_constant() -> None:
    """The well-known path is what runtime_audit.sh hits. If this changes,
    the audit script breaks silently."""
    assert CAPABILITIES_PATH == "/api/v1/.well-known/capabilities"


def test_default_deploy_anchor_env_constant() -> None:
    assert DEFAULT_DEPLOY_ANCHOR_ENV == "CN_DEPLOY_ANCHOR"


def test_register_binds_options_route_at_expected_path() -> None:
    app = _build_app_with_capabilities()
    paths_with_options = [
        r.path
        for r in app.routes
        if hasattr(r, "methods") and "OPTIONS" in (r.methods or set())
    ]
    assert CAPABILITIES_PATH in paths_with_options


def test_payload_shape_via_test_client() -> None:
    """Hit the endpoint via FastAPI TestClient, verify the JSON shape
    matches what `scripts/runtime_audit.sh` parses with jq."""
    from fastapi.testclient import TestClient

    app = _build_app_with_capabilities(module_name="test_module")
    client = TestClient(app)

    # Use OPTIONS request with same path runtime_audit.sh hits.
    resp = client.request("OPTIONS", CAPABILITIES_PATH)
    assert resp.status_code == 200
    payload = resp.json()

    # Required keys (matches OPTIONS body parsing in runtime_audit.sh).
    assert set(payload.keys()) == {"module", "deploy_anchor", "route_count", "routes"}
    assert payload["module"] == "test_module"
    assert isinstance(payload["route_count"], int)
    assert isinstance(payload["routes"], list)
    assert payload["route_count"] == len(payload["routes"])


def test_routes_array_enumerates_dummy_routes() -> None:
    """The factory's closure reads `app.routes` live, so the dummy alpha
    and beta routes registered before the factory must appear."""
    from fastapi.testclient import TestClient

    app = _build_app_with_capabilities()
    client = TestClient(app)
    payload = client.request("OPTIONS", CAPABILITIES_PATH).json()

    paths_in_payload = {entry["path"] for entry in payload["routes"]}
    assert "/dummy/alpha" in paths_in_payload
    assert "/dummy/beta" in paths_in_payload
    # The capabilities endpoint itself is also enumerated (self-listing).
    assert CAPABILITIES_PATH in paths_in_payload


def test_module_name_parameter_honored() -> None:
    """Different `module_name` values must produce different `module`
    fields. This is what lets runtime_audit.sh distinguish Backend A
    (`kg_api_server`) from Backend B (`src.api.kg_api`)."""
    from fastapi.testclient import TestClient

    app_a = _build_app_with_capabilities(module_name="backend_a_kg_api_server")
    app_b = _build_app_with_capabilities(module_name="backend_b_src_api_kg_api")
    client_a = TestClient(app_a)
    client_b = TestClient(app_b)

    p_a = client_a.request("OPTIONS", CAPABILITIES_PATH).json()
    p_b = client_b.request("OPTIONS", CAPABILITIES_PATH).json()

    assert p_a["module"] == "backend_a_kg_api_server"
    assert p_b["module"] == "backend_b_src_api_kg_api"
    assert p_a["module"] != p_b["module"]


def test_deploy_anchor_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setenv(DEFAULT_DEPLOY_ANCHOR_ENV, "test-anchor-abc123")
    app = _build_app_with_capabilities()
    client = TestClient(app)
    payload = client.request("OPTIONS", CAPABILITIES_PATH).json()
    assert payload["deploy_anchor"] == "test-anchor-abc123"


def test_deploy_anchor_defaults_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.delenv(DEFAULT_DEPLOY_ANCHOR_ENV, raising=False)
    app = _build_app_with_capabilities()
    client = TestClient(app)
    payload = client.request("OPTIONS", CAPABILITIES_PATH).json()
    assert payload["deploy_anchor"] == "unknown"


def test_no_duplicate_definitions_remain_in_backends() -> None:
    """Sweep-7 invariant: the OPTIONS handler must NOT be redefined inline
    in either backend file. Future maintainers might paste the old
    block back; this test catches that regression."""
    backend_a = (REPO_ROOT / "kg-api-server.py").read_text(encoding="utf-8")
    backend_b = (REPO_ROOT / "src" / "api" / "kg_api.py").read_text(encoding="utf-8")

    # The factory call is allowed; the inline `async def capabilities()`
    # block is not.
    assert "async def capabilities()" not in backend_a, (
        "kg-api-server.py still defines `async def capabilities()` inline; "
        "it should call register_capabilities_endpoint instead"
    )
    assert "async def capabilities()" not in backend_b, (
        "src/api/kg_api.py still defines `async def capabilities()` inline; "
        "it should call register_capabilities_endpoint instead"
    )
    assert "register_capabilities_endpoint(app, module_name=__name__)" in backend_a
    assert "register_capabilities_endpoint(app, module_name=__name__)" in backend_b
