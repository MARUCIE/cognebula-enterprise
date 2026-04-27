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

BACKEND_FILES: dict[str, Path] = {
    "A_kg-api-server": REPO_ROOT / "kg-api-server.py",
    "B_src_api_kg_api": REPO_ROOT / "src" / "api" / "kg_api.py",
}

FRONTEND_FILES: list[Path] = [
    REPO_ROOT / "src" / "web" / "inspect.html",
    REPO_ROOT / "src" / "web" / "kg_explorer.html",
    REPO_ROOT / "src" / "web" / "kg_explorer_v2.html",
    REPO_ROOT / "src" / "web" / "unified.html",
]

DECORATOR_RE = re.compile(
    r'^\s*@app\.(?:get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)

FRONTEND_PATH_RE = re.compile(r'(/api(?:/v\d+)?/[a-zA-Z0-9_/{}.\-]+)')

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
        },
        "frontend_orphans": frontend_orphans,
        "dual_backend_split": {
            "a_only_routes": sorted(a_routes - b_routes),
            "b_only_routes": sorted(b_routes - a_routes),
            "overlap_routes": overlap,
        },
        "frontend_attribution": frontend_attribution,
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
