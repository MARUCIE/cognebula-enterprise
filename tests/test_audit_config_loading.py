"""Tests for `configs/audit-manifest.json` + `configs/backend-registry.json`.

Sweep-4 / S18.19 + S18.20 — locks the contract so future edits to the JSON
configs that drop required keys are caught at PR time, not at the next
nightly audit run that suddenly produces empty results.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

AUDIT_MANIFEST_PATH = REPO_ROOT / "configs" / "audit-manifest.json"
BACKEND_REGISTRY_PATH = REPO_ROOT / "configs" / "backend-registry.json"


# ── audit-manifest.json ──────────────────────────────────────────────


def test_audit_manifest_exists_and_parses() -> None:
    assert AUDIT_MANIFEST_PATH.exists(), AUDIT_MANIFEST_PATH
    data = json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1


def test_audit_manifest_required_keys() -> None:
    data = json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    for key in (
        "backend_files",
        "frontend_files",
        "deploy_manifest_files",
        "mcp_tool_file",
    ):
        assert key in data, f"missing required key: {key}"


@pytest.mark.parametrize(
    "key,subkeys",
    [
        ("backend_files", ["A_kg-api-server", "B_src_api_kg_api"]),
        ("deploy_manifest_files", ["dockerfile", "systemd", "nginx", "docker_compose"]),
    ],
)
def test_audit_manifest_known_subkeys(key: str, subkeys: list[str]) -> None:
    """Pin the dict-shape so reorganizations don't silently drop a backend
    or a deploy artifact from the audit. New entries are fine; missing
    ones are not."""
    data = json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    for sub in subkeys:
        assert sub in data[key], f"{key}.{sub} missing"


def test_audit_manifest_paths_resolve() -> None:
    """Every declared path must point at a real file in the repo. Stale
    entries (e.g. a deleted frontend HTML) would silently lower the
    audit's coverage; this catches them at PR time."""
    data = json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    missing: list[str] = []
    for rel in data["backend_files"].values():
        if not (REPO_ROOT / rel).exists():
            missing.append(rel)
    for rel in data["frontend_files"]:
        if not (REPO_ROOT / rel).exists():
            missing.append(rel)
    for rel in data["deploy_manifest_files"].values():
        if not (REPO_ROOT / rel).exists():
            missing.append(rel)
    if not (REPO_ROOT / data["mcp_tool_file"]).exists():
        missing.append(data["mcp_tool_file"])
    assert not missing, f"manifest paths point at missing files: {missing}"


# ── backend-registry.json ────────────────────────────────────────────


def test_backend_registry_exists_and_parses() -> None:
    assert BACKEND_REGISTRY_PATH.exists(), BACKEND_REGISTRY_PATH
    data = json.loads(BACKEND_REGISTRY_PATH.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1


def test_backend_registry_module_to_key_present() -> None:
    data = json.loads(BACKEND_REGISTRY_PATH.read_text(encoding="utf-8"))
    m2k = data["module_to_backend_key"]
    assert m2k["kg-api-server:app"] == "A_kg-api-server"
    assert m2k["src.api.kg_api:app"] == "B_src_api_kg_api"


def test_backend_registry_keys_match_manifest() -> None:
    """Cross-config consistency: every backend key the registry maps TO
    must exist as a key in audit-manifest.backend_files. Otherwise the
    audit would attribute a uvicorn module to a backend that has no
    file path in the manifest."""
    manifest = json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    registry = json.loads(BACKEND_REGISTRY_PATH.read_text(encoding="utf-8"))
    backend_keys = set(manifest["backend_files"].keys())
    for module, key in registry["module_to_backend_key"].items():
        assert key in backend_keys, (
            f"registry maps {module} to {key} but manifest has no such backend file"
        )


# ── audit_api_contract.py uses externalized configs ──────────────────


def test_audit_module_loads_from_externalized_configs() -> None:
    """End-to-end: importing the audit module must produce the expected
    constants by reading from the JSON configs (not from inlined Python
    literals). Catches an accidental revert of the externalization."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "audit_api_contract",
        REPO_ROOT / "scripts" / "audit_api_contract.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    # The audit module must use the externalized config paths.
    assert mod.AUDIT_MANIFEST_PATH == AUDIT_MANIFEST_PATH
    assert mod.BACKEND_REGISTRY_PATH == BACKEND_REGISTRY_PATH

    # And the resolved constants must match the JSON contents.
    manifest = json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(mod.BACKEND_FILES.keys()) == set(manifest["backend_files"].keys())
    assert len(mod.FRONTEND_FILES) == len(manifest["frontend_files"])
    assert set(mod.DEPLOY_MANIFEST_FILES.keys()) == set(
        manifest["deploy_manifest_files"].keys()
    )

    registry = json.loads(BACKEND_REGISTRY_PATH.read_text(encoding="utf-8"))
    assert mod.MODULE_TO_BACKEND_KEY == registry["module_to_backend_key"]
