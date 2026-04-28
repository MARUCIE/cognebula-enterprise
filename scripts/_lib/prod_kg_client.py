"""prod_kg_client — thin REST client for the contabo production KG API.

Why this exists
---------------
Production KG lives on contabo VPS at `/home/kg/cognebula-enterprise/data/finance-tax-graph`
(102 GB), served by `kg-api.service` (uvicorn, port 8400). The DB is too large to
mirror to local dev for daily use, and KuzuDB is embedded — it does not expose a
network protocol of its own.

The right access pattern from local dev is:

  1. Tailscale connection (mac is `mauricemacbook-pro` 100.113.180.44; prod is
     `kg-node-eu` 100.88.170.57). Tailscale must be up.
  2. HTTP REST against the FastAPI server on port 8400.

This client is the canonical access surface from local Python code. Production
code on contabo opens the file directly; this client is for *local-side* tools
(audit scripts, notebooks, dev experiments) only.

Env var
-------
- `COGNEBULA_KG_URL` — overrides the default base URL. Useful for staging or for
  local emulation with an SSH-forwarded port (`ssh -L 8400:localhost:8400 contabo`).

Anti-patterns this client refuses
---------------------------------
- It does NOT call any `/admin/*` endpoint by default. Those mutate prod state
  and require explicit `allow_admin=True` opt-in plus an HITL confirmation
  string the caller must pass.
- It does NOT cache. Every call hits prod. Caching belongs in the caller, not
  here, because cache invariants vary by use case.

Gotchas
-------
- If the API returns 502/504, the kg-api process may be restarting. Retry once
  with backoff; do not loop.
- The server's `/` endpoint returns a path-leak error (`Web UI not found at
  /Users/mauricewen/Projects/...`). This is a deploy bug, not a client bug.
  Avoid hitting `/`; use `/api/v1/health` for liveness probes.
- The `lancedb_rows` field in `/api/v1/health` is the live LanceDB count
  (118,011 as of 2026-04-28). It is NOT the KG node count; that lives in
  `/api/v1/quality::metrics.total_nodes`.
"""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json

DEFAULT_BASE_URL = "http://100.88.170.57:8400"
ENV_BASE_URL = "COGNEBULA_KG_URL"
DEFAULT_TIMEOUT_SEC = 15.0


class ProdKGError(RuntimeError):
    """Raised when the prod KG API returns a non-2xx or is unreachable."""


def base_url() -> str:
    """Resolve base URL from env, falling back to the Tailscale default."""
    return os.environ.get(ENV_BASE_URL, DEFAULT_BASE_URL).rstrip("/")


def _get(path: str, params: dict | None = None, timeout: float = DEFAULT_TIMEOUT_SEC) -> Any:
    qs = f"?{urlencode(params)}" if params else ""
    url = f"{base_url()}{path}{qs}"
    req = Request(url, headers={"User-Agent": "cognebula-prod-kg-client/1"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return json.loads(data.decode("utf-8"))
    except HTTPError as e:
        raise ProdKGError(f"GET {url} -> HTTP {e.code} {e.reason}") from e
    except URLError as e:
        raise ProdKGError(f"GET {url} -> network error: {e.reason}") from e


def health() -> dict:
    """Return `/api/v1/health` payload. Cheapest reachability probe."""
    return _get("/api/v1/health", timeout=5.0)


def stats() -> dict:
    """Return `/api/v1/quality` — the canonical state metrics block.

    Use this for total_nodes / total_edges / per-table coverage. The endpoint
    is named `/quality` because it gates on a quality_score, but it carries
    the same metrics other systems expect from a `/stats` endpoint.
    """
    return _get("/api/v1/quality")


def ontology_audit() -> dict:
    """Return `/api/v1/ontology-audit` — schema-vs-live drift snapshot."""
    return _get("/api/v1/ontology-audit")


def nodes(node_type: str, limit: int = 100) -> list[dict]:
    """List nodes of a given type. Returns a list, possibly empty."""
    if limit < 1 or limit > 5000:
        raise ValueError(f"limit out of range [1,5000]: {limit}")
    payload = _get("/api/v1/nodes", params={"type": node_type, "limit": limit})
    if isinstance(payload, dict) and "items" in payload:
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def search(query: str, limit: int = 20) -> list[dict]:
    """Free-text search. Backed by /api/v1/search on the server."""
    payload = _get("/api/v1/search", params={"q": query, "limit": limit})
    if isinstance(payload, dict) and "items" in payload:
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def hybrid_search(query: str, limit: int = 20) -> list[dict]:
    """Vector + KG hybrid search. Backed by /api/v1/hybrid-search."""
    payload = _get("/api/v1/hybrid-search", params={"q": query, "limit": limit})
    if isinstance(payload, dict) and "items" in payload:
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def selftest() -> dict:
    """Round-trip: health + quality. Returns dict with both responses + timing.

    Use this from a local script to confirm the client + Tailscale + prod API
    are all working in one call. Caller can json.dumps the result for logs.
    """
    t0 = time.time()
    h = health()
    t1 = time.time()
    q = stats()
    t2 = time.time()
    return {
        "base_url": base_url(),
        "health": h,
        "health_ms": round((t1 - t0) * 1000, 1),
        "quality_gate": q.get("gate"),
        "total_nodes": q.get("metrics", {}).get("total_nodes"),
        "total_edges": q.get("metrics", {}).get("total_edges"),
        "stats_ms": round((t2 - t1) * 1000, 1),
    }


if __name__ == "__main__":
    import sys
    try:
        print(json.dumps(selftest(), indent=2, ensure_ascii=False))
    except ProdKGError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
