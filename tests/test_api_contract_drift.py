"""test_api_contract_drift — gate against new front-back API drift.

Locks the post-2026-04-27 SOP 3.2 audit contract: the only acceptable frontend
orphan is `/api/v1/ka/`. Any new path called by frontend HTML but undeclared
by either backend triggers a hard fail — this is the forcing function that
turns the hand-written audit into an enforcing gate.

Wired into nightly tier (NOT fast/standard) on purpose. The test fails when
either the audit script breaks OR when frontend code grows references to a
new undeclared API path. Both are P0 signals worth stopping the build for.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Imported after sys.path mutation; avoids requiring scripts/ to be a package.
import audit_api_contract  # noqa: E402

# The known set, locked by yesterday's audit. Any orphan beyond this is new
# drift and must fail the gate. Removing an entry here is allowed (it means
# the orphan has been fixed); adding an entry requires explicit Maurice
# decision and a notes.md log entry — that is the human-in-the-loop discipline.
KNOWN_FRONTEND_ORPHANS: frozenset[str] = frozenset({"/api/v1/ka/"})

# Floor on dual-backend drift ratio. If overlap grows past 25% of max(|A|, |B|),
# the backends are converging — that is good news (means a merge is happening)
# and the gate's purpose is exhausted, not bad news. The threshold matches
# `audit_api_contract.dual_backend_split_signal` calculation.
DRIFT_RATIO_GATE: float = 0.25


@pytest.fixture(scope="module")
def report() -> dict:
    return audit_api_contract.build_report(today="test")


def test_no_new_frontend_orphans(report: dict) -> None:
    actual = frozenset(report["frontend_orphans"])
    new_orphans = actual - KNOWN_FRONTEND_ORPHANS
    assert not new_orphans, (
        f"New frontend orphan(s) detected: {sorted(new_orphans)}. "
        f"Either declare these on a backend, remove the frontend reference, "
        f"or — if intentional — update KNOWN_FRONTEND_ORPHANS in this test "
        f"with a notes.md log entry explaining why."
    )


def test_known_orphans_still_orphans(report: dict) -> None:
    """If a known orphan is no longer orphan, prune the fixture."""
    actual = frozenset(report["frontend_orphans"])
    resolved = KNOWN_FRONTEND_ORPHANS - actual
    assert not resolved, (
        f"Orphan(s) {sorted(resolved)} are now declared by a backend — "
        f"remove from KNOWN_FRONTEND_ORPHANS in this test (cleanup). "
        f"This is good news: the frontend reference is now valid."
    )


def test_dual_backend_drift_signal_present(report: dict) -> None:
    """Until the dual-backend drift is resolved, the signal must stay on.

    This test exists as a tripwire: when the drift_ratio crosses 0.25, it
    means someone has been merging routes — at that point either the backends
    have been deliberately unified (drop this test) or it's an accident worth
    investigating. Either way, the test forces the conversation.
    """
    summary = report["summary"]
    assert summary["dual_backend_split_signal"], (
        f"Dual-backend split signal flipped off — drift_ratio="
        f"{summary['dual_backend_drift_ratio']} crossed the {DRIFT_RATIO_GATE} "
        f"threshold. Either confirm the merge is intentional and drop this "
        f"tripwire test, or investigate which routes were added to both "
        f"backends recently."
    )


def test_backends_both_present(report: dict) -> None:
    """The two-backend topology is the audit's premise. If either disappears
    (e.g. one was merged-out or deleted), the audit's frame is invalidated and
    this test should be retired."""
    summary = report["summary"]
    assert summary["backend_a_route_count"] > 0, "Backend A has zero routes — file moved or removed?"
    assert summary["backend_b_route_count"] > 0, "Backend B has zero routes — file moved or removed?"


def test_deploy_manifests_parsable_and_nonempty(report: dict) -> None:
    """Sprint G2 — every deploy manifest must produce a non-empty fingerprint.

    This test deliberately does NOT assert dockerfile_module == systemd_module.
    The mismatch is the P0 condition the audit found, and resolving it is
    Maurice's HITL decision (merge / split-formalize / deprecate). Forcing
    equality here would convert a HITL pause into a CI failure — bad shape.

    What this test catches:
      - Dockerfile got rewritten and we lost the CMD module reference
      - systemd unit moved/renamed and ExecStart no longer parses
      - nginx config split and the upstream regex no longer matches
      - docker-compose.yml restructured and ports moved into a different shape
    Any of those are real maintenance signals and should fail the build.
    """
    manifests = report["deploy_manifests"]

    assert manifests["dockerfile"]["module"], "Dockerfile uvicorn module not parsed"
    assert manifests["dockerfile"]["port"], "Dockerfile bound port not parsed"
    assert manifests["systemd"]["module"], "systemd uvicorn module not parsed"
    assert manifests["systemd"]["port"], "systemd bound port not parsed"
    assert manifests["nginx"]["upstreams"], "nginx proxy_pass upstreams not parsed"
    assert manifests["docker_compose"]["ports"], "docker-compose ports not parsed"
