"""`pattern_features.extract_features`: sessions and care records into Features.

Each test builds its own small, deterministic history rather than reaching for
`demo_residents` or a replayed scenario, so a regression here points straight at
this file rather than at the scorer or the demo data (SPEC §7.5).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from routine_watch.change_detection import build_baseline
from routine_watch.pattern_features import Features, extract_features
from routine_watch.scoring import session_score

NOW = datetime(2026, 1, 1, tzinfo=UTC)

#: A baseline built from clean sessions: build_baseline needs >= 3 scores.
CLEAN_BASELINE = build_baseline([0.0, 0.0, 0.0])


def _session(
    days_ago: float,
    errors: dict | None = None,
    hour: int = 10,
    duration_s: float = 180.0,
    self_corrected: int = 0,
    assisted: bool = False,
) -> dict:
    ts = (NOW - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return {
        "resident_id": "test-resident",
        "ts": ts.isoformat(),
        "task": "tea",
        "errors": dict(errors or {}),
        "self_corrected": self_corrected,
        "duration_s": duration_s,
        "assisted": assisted,
    }


def _baseline_from(sessions: list[dict]):
    return build_baseline(
        [session_score(s["errors"], s["self_corrected"], s["assisted"]) for s in sessions]
    )


def _care_record(kind: str, value, days_ago: float, note: str | None = None) -> dict:
    record = {
        "resident_id": "test-resident",
        "ts": (NOW - timedelta(days=days_ago)).isoformat(),
        "kind": kind,
        "value": value,
    }
    if note is not None:
        record["note"] = note
    return record


# --------------------------------------------------------------------- flat history


def test_flat_history_has_no_drift_and_no_change():
    sessions = [
        _session(days_ago=d, errors={"hesitation": 1} if d % 3 == 0 else {}) for d in range(14)
    ]
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.drift_trending is False
    assert features.change_strength == 0.0 or features.recent_sessions == 0


def test_flat_history_within_window_has_no_change_strength():
    sessions = [_session(days_ago=d, errors={}) for d in range(14)]
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.change_days is None
    assert features.change_strength == 0.0


# ------------------------------------------------------------------ slow downward trend


def test_slow_downward_trend_is_read_as_drift_not_a_run():
    """Errors creep up every couple of days over a fortnight: a trend, not a spike."""
    sessions = [
        _session(days_ago=13 - d, errors={"hesitation": d // 2} if d >= 2 else {})
        for d in range(14)
    ]
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.drift_trending is True
    assert features.drift_slope_per_day > 0.0
    assert features.change_days == float(features.drift_days)


def test_slow_downward_trend_is_not_mistaken_for_a_sudden_change():
    sessions = [
        _session(days_ago=13 - d, errors={"hesitation": d // 2} if d >= 2 else {})
        for d in range(14)
    ]
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    # A real drift has been building for most of the window, not just the last day or two.
    assert features.change_days is not None
    assert features.change_days > 2.0


# ---------------------------------------------------------------------- sudden change


def test_sudden_change_is_a_short_run_with_high_change_strength():
    """Twelve clean days, then two days of several error types at once."""
    sessions = [
        _session(days_ago=13 - d, errors={"omission": 1, "sequence": 1} if d >= 12 else {})
        for d in range(14)
    ]
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.drift_trending is False
    assert features.change_days is not None
    assert features.change_days <= 2.0
    assert features.change_strength > 0.5


def test_sudden_change_recent_peak_is_the_worst_session_not_the_mean():
    sessions = [
        _session(days_ago=13 - d, errors={"omission": 1, "sequence": 1} if d >= 12 else {})
        for d in range(14)
    ]
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.recent_score_peak == session_score({"omission": 1, "sequence": 1})


# ------------------------------------------------------------------- evening worsening


def test_evening_only_worsening_is_visible_as_recurring_late_day_errors():
    """Three-plus quiet weeks, then six days where every evening session runs long
    while that same day's morning session stays clean."""
    quiet = [_session(days_ago=20 + d, hour=10, errors={}) for d in range(10)]
    recent = []
    for d in range(6, 0, -1):
        recent.append(_session(days_ago=d, hour=9, errors={}))
        recent.append(_session(days_ago=d - 0.3, hour=18, errors={"hesitation": 4}))
    sessions = quiet + recent
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.compared_days == 6
    assert features.evening_worse_days == 6
    assert features.evening_recurrence == 1.0
    assert features.evening_error_rate is not None
    assert features.morning_error_rate is not None
    assert features.evening_error_rate > features.morning_error_rate
    assert features.morning_error_rate == 0.0


def test_a_single_bad_evening_does_not_count_as_recurring():
    sessions = [_session(days_ago=d, hour=9, errors={}) for d in range(1, 7)]
    sessions.append(_session(days_ago=6, hour=18, errors={"hesitation": 4}))
    baseline = _baseline_from(sessions)

    features = extract_features(sessions, baseline, now=NOW)

    assert features.compared_days == 1
    assert features.evening_worse_days == 1
    # Still "recurring" by the raw ratio for that single day, but compared_days
    # itself is the signal that distinguishes one bad evening from a pattern.
    assert features.compared_days < 6


# --------------------------------------------------------------- care record context


def test_sedating_medication_inside_its_window_appears_in_context():
    sessions = [_session(days_ago=d, errors={}) for d in range(3)]
    baseline = _baseline_from(sessions)
    records = [
        _care_record(
            "med_change",
            "diphenhydramine",
            days_ago=2,
            note="new sedating medication started",
        )
    ]

    features = extract_features(sessions, baseline, records, now=NOW)

    assert "new_sedating_medication" in features.context
    assert "new sedating medication started" in features.context_notes["new_sedating_medication"]
    assert "2 days ago" in features.context_notes["new_sedating_medication"]


def test_sedating_medication_outside_its_window_does_not_appear():
    sessions = [_session(days_ago=d, errors={}) for d in range(3)]
    baseline = _baseline_from(sessions)
    # 14 days is MEDICATION_LOOKBACK_H's boundary (14 * 24h); 20 days is well outside it.
    records = [
        _care_record("med_change", "diphenhydramine", days_ago=20, note="started 20 days ago")
    ]

    features = extract_features(sessions, baseline, records, now=NOW)

    assert "new_sedating_medication" not in features.context
    assert "recent_medication_change" not in features.context
    assert features.context_notes == {}


def test_recent_but_not_new_medication_change_still_flagged_as_recent():
    sessions = [_session(days_ago=d, errors={}) for d in range(3)]
    baseline = _baseline_from(sessions)
    # Past NEW_MEDICATION_H (72h = 3 days) but inside MEDICATION_LOOKBACK_H (14 days).
    records = [_care_record("med_change", "statin", days_ago=5, note="dose adjusted")]

    features = extract_features(sessions, baseline, records, now=NOW)

    assert "recent_medication_change" in features.context
    assert "new_medication" not in features.context
    assert "new_sedating_medication" not in features.context


def test_normal_vitals_are_recorded_as_context_without_being_a_concern():
    sessions = [_session(days_ago=d, errors={}) for d in range(3)]
    baseline = _baseline_from(sessions)
    records = [
        _care_record("temperature", 37.0, days_ago=1),
        _care_record("fluid_intake", 1500, days_ago=1),
    ]

    features = extract_features(sessions, baseline, records, now=NOW)

    assert "normal_temperature" in features.context
    assert "normal_fluids" in features.context
    assert "fever" not in features.context
    assert "low_fluids" not in features.context


def test_fever_and_low_fluids_are_flagged():
    sessions = [_session(days_ago=d, errors={}) for d in range(3)]
    baseline = _baseline_from(sessions)
    records = [
        _care_record("temperature", 38.5, days_ago=1),
        _care_record("fluid_intake", 400, days_ago=1),
    ]

    features = extract_features(sessions, baseline, records, now=NOW)

    assert "fever" in features.context
    assert "low_fluids" in features.context


# --------------------------------------------------------------------- empty sessions


def test_empty_sessions_do_not_crash_and_use_the_baseline():
    features = extract_features([], CLEAN_BASELINE)

    assert features == Features(
        threshold=CLEAN_BASELINE.threshold, baseline_score_mean=CLEAN_BASELINE.mean
    )
    assert features.recent_sessions == 0
    assert features.change_strength == 0.0
    assert features.risen_error_types() == ()
    assert features.evening_recurrence is None


def test_sessions_with_only_assisted_attempts_are_treated_as_empty():
    sessions = [_session(days_ago=d, errors={"omission": 2}, assisted=True) for d in range(3)]

    features = extract_features(sessions, CLEAN_BASELINE, now=NOW)

    assert features.recent_sessions == 0
    assert features.baseline_sessions == 0


def test_sessions_after_now_are_ignored():
    """A capture record from the future (clock skew, a stale fixture) is dropped,
    not used to compute `now` or counted in the window."""
    sessions = [_session(days_ago=d, errors={}) for d in (0.1, 1, 2)]
    sessions.append(_session(days_ago=-5, errors={"omission": 5}))

    features = extract_features(sessions, CLEAN_BASELINE, now=NOW)

    assert features.recent_sessions == 3
    assert features.total_error_rate == 0.0


# ------------------------------------------------------------------------ properties


def test_rate_and_baseline_rate_default_to_zero_for_unseen_types():
    features = Features(error_rates={"omission": 2.0}, baseline_error_rates={})

    assert features.rate("omission") == 2.0
    assert features.rate("sequence") == 0.0
    assert features.baseline_rate("omission") == 0.0


def test_risen_error_types_needs_a_clear_rise_over_baseline():
    features = Features(
        error_rates={"omission": 1.0, "sequence": 0.1},
        baseline_error_rates={"omission": 0.5, "sequence": 0.0},
    )

    # omission rose by 0.5 (>= BREADTH_MIN), sequence only by 0.1 (< BREADTH_MIN).
    assert features.risen_error_types() == ("omission",)


def test_change_strength_is_zero_with_no_recent_sessions():
    features = Features(recent_sessions=0, recent_score_peak=9.0, threshold=1.0)

    assert features.change_strength == 0.0
