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


def test_api_server_enforces_db_size_floor_against_drift() -> None:
    """Semantic guard: even a name-clean directory must exceed a size floor.

    Closes the Munger inversion gap (symlink to small legacy snapshot, fixture
    renamed without a forbidden marker, bind-mount substitution) — these all
    pass the syntactic blocklist but fail a content-volume check.
    """
    server = _read("kg-api-server.py")

    assert "DB_SIZE_FLOOR_BYTES" in server
    assert "COGNEBULA_DB_SIZE_FLOOR_BYTES" in server
    assert "database_below_size_floor" in server
    assert "_dir_top_level_size" in server


def test_all_ku_creators_populate_extracted_by_field() -> None:
    """Regression: every script that runs `CREATE (k:KnowledgeUnit ...)` must
    set the `extracted_by` field. The schema declares this field; B5 found
    100% of 2,500 sampled production KUs had it empty because no ingest
    script wrote it. Forward-looking patches (B5 micro-fix, 2026-04-28) added
    `extracted_by` to all three identified KU creators. This test prevents
    regressions when new ingest scripts are added.

    A new KU-creator that does not name `extracted_by` will fail this gate.
    """
    import re

    ku_creator_scripts = [
        "scripts/ingest_all_matrix.py",
        "scripts/ingest_chinaacc.py",
        "scripts/flk_pipeline_v2.py",
    ]
    create_pattern = re.compile(r"CREATE\s*\(\s*\w+\s*:\s*KnowledgeUnit\s*\{[^}]*\}", re.IGNORECASE | re.DOTALL)

    for path in ku_creator_scripts:
        text = _read(path)
        creates = create_pattern.findall(text)
        assert creates, f"{path}: expected to find at least one CREATE (k:KnowledgeUnit ...) statement"
        for stmt in creates:
            assert "extracted_by" in stmt, (
                f"{path}: CREATE (k:KnowledgeUnit ...) missing extracted_by field. "
                f"Statement: {stmt[:200]}"
            )


def test_migrate_table_no_500_char_clamp_on_string_props() -> None:
    """Regression: the migrate-table inner loop must NOT silently truncate
    string values to 500 chars. That clamp was a stale Chesterton's fence
    from M3 batch migration (commit ea83f033, 2026-03-20). Removed
    2026-04-28 per audit F2 / B1.

    The audit found this clamp had silently truncated LegalClause content
    during migrations. Per-field length is the schema's job; the migration
    mechanism must not have opinions about value length.
    """
    server = _read("kg-api-server.py")

    # The exact clamp pattern we removed
    assert "props[field] = str(val)[:500]" not in server
    # The replacement contract
    assert "props[field] = str(val)" in server
    # The receipt comment must remain so future readers know why
    assert "stale Chesterton's fence" in server
    assert "ea83f033" in server
