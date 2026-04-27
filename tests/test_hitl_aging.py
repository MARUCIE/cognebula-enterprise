"""§18.3 + §18.4 — HITL & non-gating-signal aging guard.

Closes the Munger-flagged failure mode where "REPORTED, NOT GATED" items
sit indefinitely and become permanent furniture. Reads
`outputs/pdca-evidence/hitl-aging.json` and asserts:

  §18.3 — every HITL decision has been reviewed within `hitl_max_age_days`
          of today, OR has an explicit `decide_by_utc` deadline in the future.
  §18.4 — every non-gating signal that has been true for longer than
          `signal_max_age_days` is escalated (i.e., `last_reviewed_utc` is
          recent enough that the signal hasn't been ignored).

When a test fails, the failure message names the specific item and what
must be done (re-defer with new dates, escalate to gate, or close).
This is signal-not-gate discipline applied to itself: the gate doesn't
force the decision, it forces a re-review event.

Wired into nightly tier (NOT fast/standard) — same tier as the drift probe.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HITL_AGING_PATH = REPO_ROOT / "outputs" / "pdca-evidence" / "hitl-aging.json"


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _parse_iso(s: str) -> _dt.datetime:
    """Parse ISO 8601 timestamp, accepting both `Z` and `+00:00` suffixes."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return _dt.datetime.fromisoformat(s)


@pytest.fixture(scope="module")
def aging_doc() -> dict:
    assert HITL_AGING_PATH.exists(), (
        f"hitl-aging.json missing at {HITL_AGING_PATH}. This file is the "
        f"aging-decay anchor for §18.3 + §18.4 — recreate it before this test "
        f"can run. See task_plan.md §18 for schema."
    )
    return json.loads(HITL_AGING_PATH.read_text(encoding="utf-8"))


def _max_hitl_age(policy: dict) -> int:
    return int(policy.get("hitl_max_age_days", 30))


def _max_signal_age(policy: dict) -> int:
    return int(policy.get("signal_max_age_days", 180))


def test_hitl_aging_doc_well_formed(aging_doc: dict) -> None:
    """The aging doc itself must carry policy + at least one HITL row +
    at least one non-gating signal row. Empty file = drift not detected.
    """
    assert "policy" in aging_doc, "missing policy block"
    assert "hitl_decisions" in aging_doc, "missing hitl_decisions array"
    assert "non_gating_signals" in aging_doc, "missing non_gating_signals array"
    assert len(aging_doc["hitl_decisions"]) > 0, (
        "no HITL items recorded — either the team has zero HITL state "
        "(implausible) or the doc is empty drift"
    )
    assert len(aging_doc["non_gating_signals"]) > 0, (
        "no non-gating signals recorded — same drift mode as above"
    )


def test_hitl_decisions_reviewed_within_policy(aging_doc: dict) -> None:
    """§18.3 — every HITL item's last_reviewed_utc must be within
    `hitl_max_age_days` of today. Re-deferral counts as review (it forces
    an explicit decision-or-redefer event, which is the point).
    """
    max_age = _max_hitl_age(aging_doc["policy"])
    now = _now_utc()
    stale = []
    for h in aging_doc["hitl_decisions"]:
        last = _parse_iso(h["last_reviewed_utc"])
        age = (now - last).days
        if age > max_age:
            stale.append((h["id"], age))
    assert not stale, (
        f"§18.3 HITL aging gate: {len(stale)} item(s) un-reviewed past "
        f"{max_age}-day policy ceiling: "
        f"{sorted(stale, key=lambda x: -x[1])}. Action: for each item, "
        f"either (a) make the decision and flip status accordingly, "
        f"(b) re-defer with updated last_reviewed_utc + decide_by_utc + "
        f"increment re_defer_count, or (c) close as no-longer-applicable. "
        f"Silent ignore is the failure mode this gate prevents."
    )


def test_hitl_decide_by_in_future_or_passed_with_action(aging_doc: dict) -> None:
    """§18.3 corollary — every HITL item whose decide_by_utc has lapsed
    must show an action (status != open_hitl). A lapsed decide_by with
    status still open_hitl is exactly the furniture-becoming pattern.
    """
    now = _now_utc()
    lapsed_open = []
    for h in aging_doc["hitl_decisions"]:
        deadline = _parse_iso(h["decide_by_utc"])
        if deadline < now and h.get("status") == "open_hitl":
            lapsed_open.append(
                (h["id"], deadline.isoformat(), h.get("status"))
            )
    assert not lapsed_open, (
        f"§18.3 decide-by lapsed without action: {lapsed_open}. The "
        f"deadline passed and the item is still 'open_hitl'. Either flip "
        f"to a concrete status (decided, deferred_explicit, closed) or "
        f"re-defer with a new decide_by_utc and bump re_defer_count."
    )


def test_non_gating_signals_recently_reviewed(aging_doc: dict) -> None:
    """§18.4 — every non-gating signal that is currently true must have
    been reviewed within `signal_max_age_days`. A signal that flipped
    true 200 days ago and was never re-examined is the regress mode.
    """
    max_age = _max_signal_age(aging_doc["policy"])
    now = _now_utc()
    stale = []
    for s in aging_doc["non_gating_signals"]:
        if not s.get("current_value"):
            continue  # signal currently false — no aging concern
        last = _parse_iso(s["last_reviewed_utc"])
        age = (now - last).days
        if age > max_age:
            stale.append((s["id"], age))
    assert not stale, (
        f"§18.4 signal aging gate: {len(stale)} non-gating signal(s) "
        f"true and un-reviewed past {max_age}-day ceiling: "
        f"{sorted(stale, key=lambda x: -x[1])}. Action: review the "
        f"escalation_rule_path entry for each signal, then either flip to "
        f"GATED (per HANDOFF §Escalation criteria) or update "
        f"last_reviewed_utc with a notes.md entry explaining why the "
        f"signal can stay non-gating."
    )
