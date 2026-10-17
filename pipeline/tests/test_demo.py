"""Guards that the pinned seeds in `demo.py` keep each demo resident on its
intended status (SPEC section 8: most normal, one spike, one slow drift).

The seeds are load-bearing: pattern work that touches the generators or the
scoring weights can silently move a resident between tiers and leave the demo
without its flagged resident.
"""

from datetime import datetime, timedelta

import pytest

from routine_watch.demo import (
    BASELINE_DAYS,
    DEMO_DAYS,
    DEMO_NOW,
    _usual,
    demo_residents,
)
from routine_watch.synth.history import EVENING_RECENT_DAYS

STATUSES = {"normal", "watch", "flagged"}


def _by_id() -> dict[str, dict]:
    return {resident["id"]: resident for resident in demo_residents()}


def _total_errors(session: dict) -> int:
    return sum(session["errors"].values())


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def test_is_deterministic() -> None:
    assert demo_residents() == demo_residents()


def test_demo_resident_status_snapshot() -> None:
    assert {resident["id"]: resident["status"] for resident in demo_residents()} == {
        "mrs-k": "watch",
        "mr-chen": "watch",
        "mrs-ahmed": "normal",
        "mr-silva": "normal",
        "mr-nguyen": "watch",
        "mrs-patel": "watch",
    }


def test_statuses_are_known_tiers() -> None:
    assert {resident["status"] for resident in demo_residents()} <= STATUSES


def test_spike_resident_is_on_watch_before_the_live_session() -> None:
    """SPEC section 10 beats 2-3: her normal weeks leave one qualifying session,
    not yet the two a flag needs - the live session on stage is the second."""
    assert _by_id()["mrs-k"]["status"] == "watch"


def test_no_resident_is_flagged_before_a_live_session() -> None:
    """Flagging mrs-k purely from the seed would make beat 4 - the live session
    that is "the second qualifying session" - a no-op (SPEC section 10)."""
    statuses = [resident["status"] for resident in demo_residents()]
    assert statuses.count("flagged") == 0


@pytest.mark.parametrize("resident_id", ["mrs-ahmed", "mr-silva"])
def test_normal_residents_are_normal(resident_id: str) -> None:
    assert _by_id()[resident_id]["status"] == "normal"


def test_drift_resident_errors_trend_upward() -> None:
    """The drift resident's own scores must rise across the window, whatever
    status tier that lands on."""
    scores = [point["score"] for point in _by_id()["mr-chen"]["scores"]]
    half = len(scores) // 2
    early = sum(scores[:half]) / half
    late = sum(scores[half:]) / (len(scores) - half)
    assert late > early


def test_drift_resident_is_on_watch() -> None:
    """SPEC section 8 beat 6: a baseline built from the whole history rises right
    along with a slow drift, so the resident never crosses their own threshold and
    the slow-drift pattern never gets a demo. Measuring against the resident's
    earliest sessions instead catches it."""
    assert _by_id()["mr-chen"]["status"] == "watch"


def test_every_resident_has_the_full_score_window() -> None:
    for resident in demo_residents():
        points = resident["scores"]
        assert points, f"{resident['id']} has no score points"
        days = {datetime.fromisoformat(point["ts"]).date() for point in points}
        assert len(days) == DEMO_DAYS, f"{resident['id']} covers {len(days)} days"


def test_score_points_are_sorted_by_ts() -> None:
    for resident in demo_residents():
        stamps = [datetime.fromisoformat(point["ts"]) for point in resident["scores"]]
        assert stamps == sorted(stamps), f"{resident['id']} score points are unsorted"


def test_new_pattern_residents_appear() -> None:
    ids = {resident["id"] for resident in demo_residents()}
    assert {"mr-nguyen", "mrs-patel"} <= ids


def test_evening_resident_worsens_in_the_evening() -> None:
    """The sundowning resident's recent evening sessions must average at least
    3x the errors of their recent morning ones (SPEC §7.5)."""
    sessions = _by_id()["mr-nguyen"]["sessions"]
    cutoff = DEMO_NOW - timedelta(days=EVENING_RECENT_DAYS)
    recent = [s for s in sessions if datetime.fromisoformat(s["ts"]) >= cutoff]
    morning = [s for s in recent if datetime.fromisoformat(s["ts"]).hour < 16]
    evening = [s for s in recent if datetime.fromisoformat(s["ts"]).hour >= 16]
    assert morning and evening

    def total_errors(session: dict) -> int:
        return sum(session["errors"].values())

    morning_avg = sum(total_errors(s) for s in morning) / len(morning)
    evening_avg = sum(total_errors(s) for s in evening) / len(evening)
    assert evening_avg >= 3 * morning_avg


def test_motor_resident_sessions_slow_down() -> None:
    """The motor-slowing resident's sessions get longer after the sedating
    medication starts (SPEC §7.5)."""
    durations = [session["duration_s"] for session in _by_id()["mrs-patel"]["sessions"]]
    half = len(durations) // 2
    early = sum(durations[:half]) / half
    late = sum(durations[half:]) / (len(durations) - half)
    assert late > early


def test_evening_resident_is_on_watch() -> None:
    """SPEC section 8 beat 6: the sundowning resident's own evenings worsen enough
    to break their earliest-days threshold."""
    assert _by_id()["mr-nguyen"]["status"] == "watch"


def test_motor_resident_is_on_watch() -> None:
    """SPEC section 8 beat 6: the motor-slowing resident barely touches error
    counts (SPEC §7.5), so it is their sessions running long that must catch it."""
    assert _by_id()["mrs-patel"]["status"] == "watch"


def test_usual_is_averaged_over_the_early_window_not_the_whole_history() -> None:
    """The live screen reads these back as "usually ~Xs / ~N errors" when a session
    ends (SPEC section 9, screen 3), so they have to be the resident's old normal:
    averaged over her whole history, mrs-k's "usual" would include the bad sessions
    that put her on watch and quietly excuse them (SPEC section 8 beat 6)."""
    resident = _by_id()["mrs-k"]
    cutoff = DEMO_NOW - timedelta(days=DEMO_DAYS - BASELINE_DAYS)
    early = [s for s in resident["sessions"] if datetime.fromisoformat(s["ts"]) < cutoff]
    assert 0 < len(early) < len(resident["sessions"])

    baseline = resident["baseline"]
    assert baseline["usual_errors"] == pytest.approx(
        _mean([_total_errors(s) for s in early])
    )
    assert baseline["usual_duration_s"] == pytest.approx(
        _mean([s["duration_s"] for s in early])
    )
    assert baseline["usual_errors"] < _mean(
        [_total_errors(s) for s in resident["sessions"]]
    )


def test_every_resident_has_a_usual_duration_and_error_count() -> None:
    for resident in demo_residents():
        baseline = resident["baseline"]
        assert baseline["usual_duration_s"] > 0, f"{resident['id']} has no usual duration"
        assert baseline["usual_errors"] >= 0, f"{resident['id']} has no usual errors"


def test_usual_leaves_out_assisted_sessions() -> None:
    """An assisted session is somebody else's hands as much as the resident's, so it
    is no more part of their usual than it is of their baseline."""
    early_ts = (DEMO_NOW - timedelta(days=DEMO_DAYS)).isoformat()
    own = {"ts": early_ts, "duration_s": 100.0, "errors": {"hesitation": 1}, "assisted": False}
    assisted = {"ts": early_ts, "duration_s": 300.0, "errors": {"omission": 5}, "assisted": True}

    assert _usual([own, assisted]) == {"usual_duration_s": 100.0, "usual_errors": 1.0}


def test_usual_is_absent_when_there_is_no_early_history() -> None:
    """No number at all, so the screen leaves the "usually" half out instead of
    showing a guess drawn from the days being flagged."""
    recent = {
        "ts": DEMO_NOW.isoformat(),
        "duration_s": 100.0,
        "errors": {},
        "assisted": False,
    }

    assert _usual([recent]) == {}


def test_every_resident_is_presentable() -> None:
    """Empty names or rooms would render as blank rows on the dashboard."""
    residents = demo_residents()
    for resident in residents:
        assert resident["name"].strip(), f"{resident['id']} has an empty name"
        assert resident["room"].strip(), f"{resident['id']} has an empty room"
    ids = [resident["id"] for resident in residents]
    assert len(set(ids)) == len(ids)
