"""Shared OPTIONS capabilities endpoint factory — Sweep-7 / S18.26.

Extracted from the duplicated 30-line OPTIONS handler in `kg-api-server.py`
(Sprint G4 / S15.1) and `src/api/kg_api.py` (Sprint G4 / S15.2). Both
backends now register the same endpoint via this factory:

    from src._lib.capabilities import register_capabilities_endpoint
    register_capabilities_endpoint(app, module_name=__name__)

Why a factory and not a route definition imported directly:
  FastAPI's `@app.api_route(...)` decorator binds at decoration time to a
  specific app instance. The factory takes `app` as parameter and binds
  the closure-captured handler at registration time, so the same code
  serves two different FastAPI instances. Closures capture `app` so the
  handler's route-introspection (`for r in app.routes`) reads the live
  state of whichever backend invoked the factory.

What stays in each backend (intentionally NOT extracted):
  - The `module_name` argument is supplied by each backend (usually
    `__name__`, which differs: `kg_api_server` vs `src.api.kg_api`).
    This keeps backend identity explicit at registration site.
  - Any backend-specific middleware, auth, etc. — the endpoint is
    intentionally OPTIONS-only and CORS-friendly.

Failure modes prevented (Munger inversion):
  - Forgetting to register on a new backend: factory call is grep-able
    on `register_capabilities_endpoint`.
  - Drift between the two backends: there's only one source.
  - Wrong route catalog: the closure reads `app.routes` live, not a
    cached snapshot, so all subsequently-registered routes appear.

Single regression test in tests/test_capabilities_factory.py covers:
  signature contract, payload shape, route enumeration, and the
  module_name parameter being honored.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse


CAPABILITIES_PATH = "/api/v1/.well-known/capabilities"
DEFAULT_DEPLOY_ANCHOR_ENV = "CN_DEPLOY_ANCHOR"


def register_capabilities_endpoint(
    app: FastAPI,
    module_name: str,
    deploy_anchor_env: str = DEFAULT_DEPLOY_ANCHOR_ENV,
    path: str = CAPABILITIES_PATH,
) -> None:
    """Register the runtime capability introspection OPTIONS endpoint on `app`.

    Reports `{module, deploy_anchor, route_count, routes[]}` so
    `scripts/runtime_audit.sh` can compare the live route catalog against
    `audit_api_contract.py` static parse output.

    Args:
      app: FastAPI instance to register against.
      module_name: identity string returned in the payload's `module` field.
        Usually `__name__` of the calling backend module.
      deploy_anchor_env: env var name to read the deploy anchor from
        (default: `CN_DEPLOY_ANCHOR`). Returns "unknown" if unset.
      path: route path to register on (default: `/api/v1/.well-known/capabilities`).
    """

    @app.api_route(path, methods=["OPTIONS"])
    async def capabilities():
        try:
            routes = []
            for r in app.routes:
                if hasattr(r, "path") and hasattr(r, "methods") and r.methods:
                    methods = sorted(m for m in r.methods if m not in {"HEAD"})
                    if methods and r.path:
                        routes.append({"path": r.path, "methods": methods})
            return JSONResponse(content={
                "module": module_name,
                "deploy_anchor": os.environ.get(deploy_anchor_env, "unknown"),
                "route_count": len(routes),
                "routes": sorted(routes, key=lambda x: x["path"]),
            })
        except Exception as e:
            return JSONResponse(status_code=500, content={
                "error": "capabilities_introspection_failed",
                "detail": str(e)[:200],
            })
