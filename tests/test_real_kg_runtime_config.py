"""Regression checks for real-KG runtime wiring.

These tests prevent the packaged API path from silently falling back to local
demo snapshots. Unit-test fixtures can still seed temporary Kuzu databases, but
runtime config must require explicit real DB/Lance mounts or the Tailscale prod
API client.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_runtime_configs_do_not_reference_demo_kg_paths() -> None:
    forbidden = (
        "finance-tax-graph.demo",
        "finance-tax-graph.archived.157nodes",
        "local-demo-key",
        "bootstrap_local_demo_graph.py",
    )
    runtime_files = (
        ".env",
        "docker-compose.yml",
        "README.md",
        "web/.env.local",
    )

    offenders: list[str] = []
    for file_path in runtime_files:
        text = _read(file_path)
        for token in forbidden:
            if token in text:
                offenders.append(f"{file_path}: {token}")

    assert offenders == []


def test_compose_requires_explicit_real_database_mounts() -> None:
    compose = _read("docker-compose.yml")

    assert "${COGNEBULA_GRAPH_PATH:?" in compose
    assert "${COGNEBULA_LANCE_PATH:?" in compose
    assert "read_only: true" in compose
    assert "finance-tax-graph.archived" not in compose
    assert "finance-tax-graph.demo" not in compose


def test_api_server_refuses_demo_or_empty_database_paths() -> None:
    server = _read("kg-api-server.py")

    assert "FORBIDDEN_DB_PATH_MARKERS" in server
    assert "finance-tax-graph.demo" in server
    assert "finance-tax-graph.archived" in server
    assert "empty_database_directory" in server
    assert "Refusing to open KG DB" in server
