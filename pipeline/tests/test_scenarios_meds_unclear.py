"""Scenario: meds_session_unclear_no_flag (SPEC section 12).

The medication task's twin of tea_session_unclear_no_flag (T344): a session whose
capture is low-confidence throughout must be classed unclear by session_quality,
score 0.0, raise no errors toward the resident's history and never flag, even
against a history that would otherwise flag a change.
"""

from __future__ import annotations

from routine_watch.quality import session_quality
from routine_watch.replay import SCENARIOS_DIR, load_scenario, replay


def test_meds_session_unclear_no_flag_is_unclear() -> None:
    scenario = load_scenario(SCENARIOS_DIR / "meds_session_unclear_no_flag")
    assert session_quality(scenario.events) == "unclear"


def test_meds_session_unclear_no_flag_never_scores_or_flags() -> None:
    result = replay(SCENARIOS_DIR / "meds_session_unclear_no_flag")
    assert result["quality"] == "unclear"
    assert result["score"] == 0.0
    assert result["flag"] is False
