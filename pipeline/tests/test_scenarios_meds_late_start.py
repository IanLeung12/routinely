"""Scenario: meds_late_start_normal.

The medication task's twin of tea_late_start_normal (T362): a resident idles for
200 seconds - well over the 120s abandonment threshold
(routine_watch.errors.ABANDON_AFTER_S) - before touching the pill organiser or the
glass at all, then takes the medication correctly. Abandonment only fires on a
silence *between* events (classify_errors tracks `previous` as None until the first
event), so the long wait before the first step must never be read as abandonment,
an omission, or anything else that flags a change.
"""

from __future__ import annotations

from routine_watch.errors import ABANDON_AFTER_S
from routine_watch.replay import SCENARIOS_DIR, load_scenario, replay


def test_meds_late_start_normal_idles_past_the_abandon_threshold_first() -> None:
    scenario = load_scenario(SCENARIOS_DIR / "meds_late_start_normal")
    assert scenario.events[0].t_start > ABANDON_AFTER_S


def test_meds_late_start_normal_never_errors_or_flags() -> None:
    result = replay(SCENARIOS_DIR / "meds_late_start_normal")
    assert result["errors"] == []
    assert result["score"] == 0.0
    assert result["flag"] is False
