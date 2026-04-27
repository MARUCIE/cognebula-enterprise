#!/usr/bin/env python3
"""audit_api_contract.py — Front-back API contract drift probe.

Parses backend FastAPI decorators and frontend fetch paths, emits a JSON drift
report covering three axes derived from the 2026-04-27 SOP 3.2 hand-written
audit:

  1. frontend_orphans    — paths referenced by frontend HTML/JS but declared by
                           NEITHER backend
  2. dual_backend_split  — routes declared by exactly one of {A, B}; route_overlap
                           = 0 is the P0 signal for the dual-backend drift
  3. frontend_attribution — per-frontend-file mapping of API path -> backends
                            that cover it (helps localize "this frontend page
                            only works against backend B")

This is the code-enforced reproduction of yesterday's hand-written audit. Exits
non-zero when frontend_orphans is non-empty so it can gate nightly tests.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent

# Sweep-4 / S18.19 + S18.20 — manifest data and backend identity registry are
# externalized to JSON configs. Renaming a backend file or adding a new
# frontend HTML no longer requires a code edit; PR-reviewed config edit suffices.
AUDIT_MANIFEST_PATH = REPO_ROOT / "configs" / "audit-manifest.json"
BACKEND_REGISTRY_PATH = REPO_ROOT / "configs" / "backend-registry.json"


def _load_audit_manifest() -> dict:
    if not AUDIT_MANIFEST_PATH.exists():
        print(
            f"ERROR: audit manifest missing at {AUDIT_MANIFEST_PATH}",
            file=sys.stderr,
        )
        sys.exit(2)
    return json.loads(AUDIT_MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_backend_registry() -> dict:
    if not BACKEND_REGISTRY_PATH.exists():
        print(
            f"ERROR: backend registry missing at {BACKEND_REGISTRY_PATH}",
            file=sys.stderr,
        )
        sys.exit(2)
    return json.loads(BACKEND_REGISTRY_PATH.read_text(encoding="utf-8"))


_MANIFEST = _load_audit_manifest()
_REGISTRY = _load_backend_registry()

BACKEND_FILES: dict[str, Path] = {
    key: REPO_ROOT / rel for key, rel in _MANIFEST["backend_files"].items()
}

FRONTEND_FILES: list[Path] = [
    REPO_ROOT / rel for rel in _MANIFEST["frontend_files"]
]

DEPLOY_MANIFEST_FILES: dict[str, Path] = {
    key: REPO_ROOT / rel for key, rel in _MANIFEST["deploy_manifest_files"].items()
}

MCP_TOOL_FILE: Path = REPO_ROOT / _MANIFEST["mcp_tool_file"]

# Mapping from uvicorn module reference to the backend key in `backends` dict.
# Externalized to configs/backend-registry.json; renaming a backend now
# requires a JSON edit, not a code edit.
MODULE_TO_BACKEND_KEY: dict[str, str] = dict(_REGISTRY["module_to_backend_key"])

DECORATOR_RE = re.compile(
    r'^\s*@app\.(?:get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)

FRONTEND_PATH_RE = re.compile(r'(/api(?:/v\d+)?/[a-zA-Z0-9_/{}.\-]+)')

# Deploy-manifest anchor regexes (intentionally narrow — we extract the uvicorn
# module reference and the bound port, not the full deploy spec).
DOCKERFILE_CMD_RE = re.compile(r'^\s*CMD\s*\[([^\]]+)\]', re.MULTILINE)
SYSTEMD_EXECSTART_RE = re.compile(
    r'^\s*ExecStart=.*?uvicorn\s+(\S+)(?:\s+.*?--port\s+(\d+))?',
    re.MULTILINE,
)
NGINX_PROXY_PASS_RE = re.compile(r'proxy_pass\s+https?://([\d.]+|[a-zA-Z][\w.\-]*):(\d+)')
COMPOSE_PORT_RE = re.compile(r'^\s*-\s*["\']?(\d+):(\d+)["\']?\s*$', re.MULTILINE)

# Sprint H — MCP tool extraction.
MCP_TOOL_DECORATOR_RE = re.compile(
    r'@mcp\.tool\(\)\s*\n\s*(?:async\s+)?def\s+(\w+)\s*\(',
)
MCP_API_CALL_RE = re.compile(r'_api_(?:get|post)\s*\(\s*["\']([^"\']+)["\']')

# Base-URL false positives. /api/v1 alone is the constant `window.location.origin
# + '/api/v1'` — it's a prefix, not an endpoint. /api alone is similarly a prefix.
# Real endpoints always have at least one path segment AFTER /api[/vN].
BASE_URL_RE = re.compile(r'^/api(?:/v\d+)?/?$')


def _strip_query(path: str) -> str:
    return path.split("?", 1)[0].rstrip()


def _is_base_url(path: str) -> bool:
    return bool(BASE_URL_RE.match(path))


def parse_backend(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(1) for m in DECORATOR_RE.finditer(text)}


def parse_frontend(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        cleaned
        for m in FRONTEND_PATH_RE.finditer(text)
        if not _is_base_url(cleaned := _strip_query(m.group(1)))
    }


def _extract_dockerfile_uvicorn(path: Path) -> dict[str, str | int | None]:
    """Parse Dockerfile CMD line — returns {module, port} from JSON-array form."""
    if not path.exists():
        return {"module": None, "port": None}
    text = path.read_text(encoding="utf-8", errors="replace")
    match = DOCKERFILE_CMD_RE.search(text)
    if not match:
        return {"module": None, "port": None}
    # Crude tokenizer for the JSON-array CMD body: pull quoted strings.
    tokens = re.findall(r'"([^"]*)"', match.group(1))
    module: str | None = None
    port: int | None = None
    for i, tok in enumerate(tokens):
        if tok == "uvicorn" and i + 1 < len(tokens):
            module = tokens[i + 1]
        if tok == "--port" and i + 1 < len(tokens):
            try:
                port = int(tokens[i + 1])
            except ValueError:
                pass
    return {"module": module, "port": port}


def _extract_systemd_uvicorn(path: Path) -> dict[str, str | int | None]:
    """Parse systemd unit ExecStart line — shell-style, not JSON."""
    if not path.exists():
        return {"module": None, "port": None}
    text = path.read_text(encoding="utf-8", errors="replace")
    match = SYSTEMD_EXECSTART_RE.search(text)
    if not match:
        return {"module": None, "port": None}
    module = match.group(1)
    port_str = match.group(2)
    return {
        "module": module,
        "port": int(port_str) if port_str else None,
    }


def _extract_nginx_upstreams(path: Path) -> list[dict[str, str | int]]:
    """Return distinct (host, port) upstream pairs from proxy_pass directives."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    seen: set[tuple[str, int]] = set()
    for m in NGINX_PROXY_PASS_RE.finditer(text):
        seen.add((m.group(1), int(m.group(2))))
    return [{"host": h, "port": p} for h, p in sorted(seen)]


def _extract_compose_ports(path: Path) -> list[dict[str, int]]:
    """Return distinct host:container port pairs from docker-compose ports lists."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    seen: set[tuple[int, int]] = set()
    for m in COMPOSE_PORT_RE.finditer(text):
        seen.add((int(m.group(1)), int(m.group(2))))
    return [{"host_port": h, "container_port": c} for h, c in sorted(seen)]


def compute_reachability_per_deploy_mode(
    backends: dict[str, set[str]],
    all_frontend_paths: set[str],
    deploy_manifests: dict,
) -> dict:
    """Sprint G3 — translate `module_mismatch_signal` into operational impact.

    For each deploy mode (dockerfile, systemd), figure out which uvicorn module
    it actually starts → which backend's route set is in effect → which
    frontend paths are reachable vs unreachable under that mode.

    This is the parse-only equivalent of an OPTIONS-endpoint runtime probe.
    The "reachable" guarantee is weaker (depends on accurate MODULE_TO_BACKEND_KEY
    map) but requires no backend code change and no live HTTP fixture.
    """
    result: dict = {}
    for mode_name in ("dockerfile", "systemd"):
        manifest_block = deploy_manifests.get(mode_name) or {}
        module_ref = manifest_block.get("module")
        if module_ref is None:
            result[mode_name] = {
                "module": None,
                "module_unknown": True,
                "reachable_paths": [],
                "unreachable_paths": sorted(all_frontend_paths),
            }
            continue
        backend_key = MODULE_TO_BACKEND_KEY.get(module_ref)
        routes = backends.get(backend_key or "", set())
        reachable = sorted(p for p in all_frontend_paths if p in routes)
        unreachable = sorted(p for p in all_frontend_paths if p not in routes)
        result[mode_name] = {
            "module": module_ref,
            "backend_key": backend_key,
            "module_unknown": backend_key is None,
            "reachable_paths": reachable,
            "unreachable_paths": unreachable,
            "reachable_count": len(reachable),
            "unreachable_count": len(unreachable),
        }
    return result


def parse_mcp_tools(path: Path) -> dict[str, list[str]]:
    """Sprint H — extract @mcp.tool() functions and the API endpoints each calls.

    Returns {tool_name: [endpoint_path, ...]}. Endpoints come from `_api_get(...)`
    and `_api_post(...)` calls inside the tool function body. Query strings are
    stripped to match the path-only contract used by the rest of the audit.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")

    decorator_positions = [
        (m.start(), m.group(1)) for m in MCP_TOOL_DECORATOR_RE.finditer(text)
    ]
    if not decorator_positions:
        return {}

    tools: dict[str, list[str]] = {}
    for i, (start, name) in enumerate(decorator_positions):
        end = (
            decorator_positions[i + 1][0]
            if i + 1 < len(decorator_positions)
            else len(text)
        )
        body = text[start:end]
        endpoints = sorted(
            {_strip_query(m.group(1)) for m in MCP_API_CALL_RE.finditer(body)}
        )
        tools[name] = endpoints
    return tools


def compute_mcp_attribution(
    backends: dict[str, set[str]],
    mcp_tools: dict[str, list[str]],
) -> dict:
    """For each MCP tool's endpoints, which backend(s) declare them.

    Emits orphan_count = endpoints declared by NEITHER backend (would 404 at
    runtime regardless of which backend is deployed). This is a hard
    inconsistency — the MCP server promises a tool that no backend implements.
    """
    attribution: dict[str, dict] = {}
    orphan_endpoints: list[tuple[str, str]] = []
    for tool_name, endpoints in mcp_tools.items():
        per_endpoint: dict[str, list[str]] = {}
        for ep in endpoints:
            declaring = [
                key for key, routes in backends.items() if ep in routes
            ]
            per_endpoint[ep] = declaring if declaring else ["NONE"]
            if not declaring:
                orphan_endpoints.append((tool_name, ep))
        attribution[tool_name] = {"endpoints": per_endpoint}
    return {
        "by_tool": attribution,
        "orphan_endpoints": [
            {"tool": t, "endpoint": e} for t, e in sorted(orphan_endpoints)
        ],
        "orphan_count": len(orphan_endpoints),
        "tool_count": len(mcp_tools),
    }


def parse_deploy_manifests() -> dict:
    """Parse all 4 deploy manifests and emit module/port fingerprints.

    Returns a dict shaped for the JSON report. Includes a derived
    `module_mismatch_signal` that flags the P0 case where Dockerfile and
    systemd start different uvicorn modules — but does NOT fail the gate
    (HITL decision turf: the user picks merge / split-formalize / deprecate).
    """
    docker = _extract_dockerfile_uvicorn(DEPLOY_MANIFEST_FILES["dockerfile"])
    systemd = _extract_systemd_uvicorn(DEPLOY_MANIFEST_FILES["systemd"])
    nginx_upstreams = _extract_nginx_upstreams(DEPLOY_MANIFEST_FILES["nginx"])
    compose_ports = _extract_compose_ports(DEPLOY_MANIFEST_FILES["docker_compose"])

    module_mismatch = bool(
        docker["module"]
        and systemd["module"]
        and docker["module"] != systemd["module"]
    )

    return {
        "dockerfile": docker,
        "systemd": systemd,
        "nginx": {"upstreams": nginx_upstreams},
        "docker_compose": {"ports": compose_ports},
        "module_mismatch_signal": module_mismatch,
    }


def build_report(*, today: str) -> dict:
    backends = {name: parse_backend(p) for name, p in BACKEND_FILES.items()}
    a_routes = backends["A_kg-api-server"]
    b_routes = backends["B_src_api_kg_api"]
    all_backend_routes = a_routes | b_routes

    frontends = {p.name: parse_frontend(p) for p in FRONTEND_FILES}
    all_frontend_paths: set[str] = set().union(*frontends.values()) if frontends else set()

    # Strict orphan = path used by frontend but declared by neither backend.
    # Note: paths only on /api/vN are excluded from frontend_orphans if a backend
    # exposes the same un-versioned form, but we keep the exact-match contract
    # for now — false positives are healthier than missed orphans.
    frontend_orphans = sorted(all_frontend_paths - all_backend_routes)
    overlap = sorted(a_routes & b_routes)

    frontend_attribution: dict[str, dict[str, list[str]]] = {}
    for fe_name, fe_paths in frontends.items():
        per_path: dict[str, list[str]] = {}
        for p in sorted(fe_paths):
            covers = [name for name, routes in backends.items() if p in routes]
            per_path[p] = covers if covers else ["NONE"]
        frontend_attribution[fe_name] = per_path

    deploy_manifests = parse_deploy_manifests()
    reachability = compute_reachability_per_deploy_mode(
        backends, all_frontend_paths, deploy_manifests
    )
    mcp_tools = parse_mcp_tools(MCP_TOOL_FILE)
    mcp_attribution = compute_mcp_attribution(backends, mcp_tools)

    return {
        "audit_date": today,
        "audit_source": "scripts/audit_api_contract.py",
        "summary": {
            "backend_a_route_count": len(a_routes),
            "backend_b_route_count": len(b_routes),
            "backend_total_distinct": len(all_backend_routes),
            "frontend_distinct_path_count": len(all_frontend_paths),
            "frontend_orphan_count": len(frontend_orphans),
            "route_overlap_count": len(overlap),
            # Dual-backend drift signal: most routes are disjoint. We pick a 25%
            # threshold against max(|A|, |B|) — anything above that means the
            # backends are converging (could be merged) rather than drifting.
            # Below that means they have substantively different responsibilities
            # despite sharing the same port; that is the P0 condition.
            "dual_backend_drift_ratio": (
                round(len(overlap) / max(len(a_routes), len(b_routes), 1), 3)
            ),
            "dual_backend_split_signal": (
                bool(a_routes)
                and bool(b_routes)
                and len(overlap) < 0.25 * max(len(a_routes), len(b_routes))
            ),
            # Sprint G2 addition: module mismatch is the *symptom* of dual-backend
            # split visible at the deploy layer. Reported but does NOT fail the
            # gate — that decision is HITL turf (merge / split-formalize / deprecate).
            "module_mismatch_signal": deploy_manifests["module_mismatch_signal"],
            # Sprint G3 summary metric: count of frontend paths NOT reachable
            # under at least one of the two deploy modes. >0 means dual-backend
            # split has visible operational impact.
            "frontend_paths_with_deploy_mode_drift": (
                len(reachability.get("dockerfile", {}).get("unreachable_paths", []))
                + len(reachability.get("systemd", {}).get("unreachable_paths", []))
            ),
            # Sprint H summary metric: MCP tools whose endpoints are declared
            # by NEITHER backend = hard inconsistency.
            "mcp_orphan_count": mcp_attribution["orphan_count"],
            "mcp_tool_count": mcp_attribution["tool_count"],
        },
        "frontend_orphans": frontend_orphans,
        "dual_backend_split": {
            "a_only_routes": sorted(a_routes - b_routes),
            "b_only_routes": sorted(b_routes - a_routes),
            "overlap_routes": overlap,
        },
        "frontend_attribution": frontend_attribution,
        "deploy_manifests": deploy_manifests,
        "reachability_per_deploy_mode": reachability,
        "mcp_attribution": mcp_attribution,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    today = date.today().isoformat()
    default_out = (
        REPO_ROOT
        / "outputs"
        / "reports"
        / "consistency-audit"
        / f"{today}-api-contract-drift.json"
    )
    parser.add_argument("--out", type=Path, default=default_out)
    parser.add_argument(
        "--no-fail-on-orphan",
        action="store_true",
        help="Emit report but exit 0 even if frontend_orphans is non-empty",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = build_report(today=today)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"audit_api_contract: report written to {args.out}", file=sys.stderr)
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))

    if report["frontend_orphans"] and not args.no_fail_on_orphan:
        print(
            f"FAIL: {len(report['frontend_orphans'])} frontend orphan(s): "
            f"{report['frontend_orphans']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
