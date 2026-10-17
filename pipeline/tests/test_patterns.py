"""The pattern scorer: rules over features, and "no clear pattern" is an answer."""

from datetime import UTC, datetime, timedelta

import pytest

from routine_watch.alerts import build_alerts
from routine_watch.change_detection import Baseline, build_baseline
from routine_watch.contracts import PatternUrgency, SuggestedCheck
from routine_watch.demo import demo_residents
from routine_watch.patterns import (
    MAX_PATTERNS,
    PATTERN_THRESHOLD,
    Features,
    extract_features,
    score_patterns,
    signals,
    time_fit,
)
from routine_watch.patterns_library import CONTEXT_FLAGS, LIBRARY, Pattern, TimeProfile
from routine_watch.scoring import session_score

NOW = datetime(2026, 1, 1, tzinfo=UTC)
DAYS = 14
START = NOW - timedelta(days=DAYS)

#: Each day's two sessions: morning, then late afternoon.
HOURS = (8, 18)


def _at(day: int, hour: int) -> datetime:
    return START + timedelta(days=day, hours=hour)


def _session(day: int, hour: int, errors: dict | None = None, duration_s: float = 180.0) -> dict:
    return {
        "resident_id": "test-resident",
        "ts": _at(day, hour).isoformat(),
        "task": "tea",
        "errors": dict(errors or {}),
        "self_corrected": 0,
        "duration_s": duration_s,
        "assisted": False,
    }


def _history(errors_on, duration_on=lambda day: 180.0) -> list[dict]:
    """Two sessions a day for a fortnight, from a per-day rule."""
    return [
        _session(day, hour, errors_on(day, hour), duration_on(day))
        for day in range(DAYS)
        for hour in HOURS
    ]


def _features(sessions: list[dict], care_records: list[dict] | None = None) -> Features:
    """Features against a baseline built from this resident's own history."""
    baseline = build_baseline(
        [session_score(s["errors"], s["self_corrected"], s["assisted"]) for s in sessions]
    )
    return extract_features(sessions, baseline, care_records or [], now=NOW)


def _ranked(sessions: list[dict], care_records: list[dict] | None = None) -> list[str]:
    return [match.pattern_id for match in score_patterns(_features(sessions, care_records))]


# The histories: one shape of change each, deterministic, no generator in the loop.


def _sudden_spike() -> list[dict]:
    """Clean for twelve days, then several kinds of error at once."""
    spike = {"omission": 1, "sequence": 1, "perseveration": 1}
    return _history(lambda day, hour: spike if day >= DAYS - 2 else {})


def _gradual_rise() -> list[dict]:
    """Errors creeping up every day for a fortnight."""
    return _history(lambda day, hour: {"hesitation": day // 2} if day >= 2 else {})


def _flat_noise() -> list[dict]:
    """The odd long pause, in the same proportion all fortnight."""
    return _history(lambda day, hour: {"hesitation": 1} if day % 3 == 0 else {})


def _motor_slowing() -> list[dict]:
    """Sessions half again as long, with pauses, from the tenth day on."""
    return _history(
        lambda day, hour: {"hesitation": 1} if day >= DAYS - 4 else {},
        lambda day: 270.0 if day >= DAYS - 4 else 180.0,
    )


def _med_change(value: str, note: str, days_ago: float) -> list[dict]:
    return [
        {
            "resident_id": "test-resident",
            "ts": (NOW - timedelta(days=days_ago)).isoformat(),
            "kind": "med_change",
            "value": value,
            "note": note,
        }
    ]


# ----------------------------------------------------------- the four acceptance cases


def test_sudden_spike_ranks_sudden_change_first():
    ranked = _ranked(_sudden_spike())

    assert ranked[0] == "sudden_change"


def test_gradual_rise_ranks_slow_drift_first():
    ranked = _ranked(_gradual_rise())

    assert ranked[0] == "slow_drift"
    assert "sudden_change" not in ranked


def test_flat_noise_finds_no_pattern():
    assert _ranked(_flat_noise()) == []


def test_new_sedating_medication_raises_the_medication_pattern():
    records = _med_change("diphenhydramine", "new sedating medication started", days_ago=4)
    sessions = _motor_slowing()

    with_med = {
        match.pattern_id: match.confidence
        for match in score_patterns(_features(sessions, records), threshold=0.0)
    }
    without = {
        match.pattern_id: match.confidence
        for match in score_patterns(_features(sessions), threshold=0.0)
    }

    assert with_med["motor_slowing"] > without["motor_slowing"]
    assert _ranked(sessions, records)[0] == "motor_slowing"


# ------------------------------------------------------------------------- the wording


def _everything_fires() -> Features:
    """Features that light up every signal, so every pattern can be read."""
    return Features(
        recent_sessions=2,
        baseline_sessions=20,
        recent_score_peak=9.0,
        baseline_score_mean=1.0,
        threshold=3.0,
        error_rates={"omission": 1.5, "sequence": 1.5, "perseveration": 1.5, "hesitation": 1.5},
        baseline_error_rates={},
        drift_slope_per_day=0.5,
        drift_days=DAYS,
        drift_trending=True,
        duration_ratio=1.6,
        gap_ratio=1.6,
        movement_speed_ratio=0.5,
        evening_error_rate=1.5,
        morning_error_rate=0.0,
        baseline_morning_error_rate=0.0,
        compared_days=6,
        evening_worse_days=6,
        hand_share_drop=0.6,
        context=CONTEXT_FLAGS,
        context_notes={flag: f"{flag} seen, today" for flag in CONTEXT_FLAGS},
    )


def _every_pattern():
    return score_patterns(_everything_fires(), threshold=0.0, limit=len(LIBRARY))


def test_every_pattern_in_the_library_can_be_scored():
    assert {match.pattern_id for match in _every_pattern()} == {
        pattern.pattern_id for pattern in LIBRARY
    }


def test_evidence_says_what_the_change_is_consistent_with():
    for match in _every_pattern():
        assert any("consistent with" in line for line in match.evidence), match.pattern_id


def test_checks_are_things_to_rule_out_and_never_a_verdict():
    wording = " ".join(str(check) for pattern in LIBRARY for check in pattern.checks).lower()

    assert "rule out" in wording
    for match in _every_pattern():
        assert match.checks, match.pattern_id
        text = " ".join([match.name, *match.evidence, *(str(c) for c in match.checks)]).lower()
        assert "diagnos" not in text
        assert " has " not in text


def test_known_checks_reuse_the_shared_suggested_check_values():
    sudden = next(match for match in _every_pattern() if match.pattern_id == "sudden_change")

    assert SuggestedCheck.CAM_SCREEN in sudden.checks


# -------------------------------------------------------------------------- the library


def test_library_entries_are_complete_and_cite_a_source():
    for pattern in LIBRARY:
        assert pattern.signals, pattern.pattern_id
        assert pattern.checks, pattern.pattern_id
        assert "SPEC" in pattern.source, pattern.pattern_id
        assert pattern.urgency in tuple(PatternUrgency), pattern.pattern_id
        assert 0.0 < pattern.max_confidence <= 1.0, pattern.pattern_id
        assert set(pattern.requires) <= set(pattern.signals), pattern.pattern_id
        assert set(pattern.context_weights) <= set(CONTEXT_FLAGS), pattern.pattern_id


def test_a_pattern_can_be_added_as_data_alone():
    """A new pattern is a library entry: no change to the scorer (SPEC §7.5)."""
    made_up = Pattern(
        pattern_id="made_up",
        name="Made-up pattern",
        signals={"omissions_up": 1.0},
        time_profile=TimeProfile(onset_days=(0.0, 30.0), tolerance_days=5.0, note="any onset"),
        checks=("Rule out nothing at all",),
        urgency=PatternUrgency.ROUTINE,
        source="SPEC §7.5 test",
    )

    matches = score_patterns(_everything_fires(), library=(made_up,), threshold=0.0)

    assert [match.pattern_id for match in matches] == ["made_up"]
    assert matches[0].urgency == "routine"


# --------------------------------------------------------------------------- the scorer


def test_at_most_three_patterns_sorted_by_confidence():
    matches = score_patterns(_everything_fires())

    assert len(matches) <= MAX_PATTERNS
    assert all(match.confidence >= PATTERN_THRESHOLD for match in matches)
    confidences = [match.confidence for match in matches]
    assert confidences == sorted(confidences, reverse=True)


def test_time_profile_separates_a_step_change_from_a_drift():
    profile = TimeProfile(onset_days=(0.0, 3.0), tolerance_days=2.0, note="within 1-3 days")

    assert time_fit(profile, 2.0) == 1.0
    assert time_fit(profile, 4.0) == pytest.approx(0.5)
    assert time_fit(profile, 14.0) == 0.0
    assert time_fit(profile, None) == 1.0


def test_a_pattern_whose_signals_are_not_recorded_is_not_scored():
    """One-sided change needs per-hand shares, which session records do not carry."""
    without_hands = _features(_sudden_spike())
    with_hands = Features(
        recent_sessions=2,
        baseline_sessions=20,
        recent_score_peak=9.0,
        baseline_score_mean=1.0,
        threshold=3.0,
        error_rates={"omission": 1.0},
        baseline_error_rates={},
        change_days=0.5,
        hand_share_drop=0.6,
    )

    assert signals(without_hands)["hand_use_dropped"] is None
    assert "one_sided_change" not in [
        match.pattern_id for match in score_patterns(without_hands)
    ]
    assert "one_sided_change" in [match.pattern_id for match in score_patterns(with_hands)]


def test_normal_vitals_lower_the_sudden_change_pattern_without_ruling_it_out():
    sessions = _sudden_spike()
    normal = [
        {
            "resident_id": "test-resident",
            "ts": (NOW - timedelta(hours=12)).isoformat(),
            "kind": "temperature",
            "value": 36.6,
            "note": "",
        }
    ]

    with_normal = score_patterns(_features(sessions, normal), threshold=0.0)
    quiet = next(match for match in with_normal if match.pattern_id == "sudden_change")
    plain = next(
        match
        for match in score_patterns(_features(sessions), threshold=0.0)
        if match.pattern_id == "sudden_change"
    )

    assert quiet.confidence < plain.confidence
    assert quiet.confidence >= PATTERN_THRESHOLD


# ------------------------------------------------------------------------- the features


def test_features_measure_this_resident_against_themselves():
    features = _features(_sudden_spike())

    assert features.rate("omission") == 1.0
    assert features.baseline_rate("omission") == 0.0
    assert features.risen_error_types() == ("omission", "sequence", "perseveration")
    assert features.change_days == pytest.approx(1.67, abs=0.1)
    assert features.change_strength == 1.0


def test_features_come_from_the_recorded_timestamps_not_the_clock():
    sessions = _sudden_spike()
    baseline = build_baseline([1.0, 1.0, 1.0])
    newest = datetime.fromisoformat(sessions[-1]["ts"])

    assert newest < NOW
    assert extract_features(sessions, baseline, []) == extract_features(
        sessions, baseline, [], now=newest
    )


def test_assisted_sessions_are_left_out():
    sessions = _flat_noise()
    for session in sessions[-2:]:
        session["errors"] = {"omission": 3}
        session["assisted"] = True

    features = _features(sessions)

    assert features.rate("omission") == 0.0
    assert score_patterns(features) == []


def test_no_history_says_nothing():
    features = extract_features([], Baseline(mean=1.0, std=0.5, threshold=2.0), [], now=NOW)

    assert features.change_strength == 0.0
    assert score_patterns(features) == []


# ---------------------------------------------------------------------------- the alert


def test_the_flagged_demo_resident_gets_ranked_patterns():
    alert = build_alerts(demo_residents())[0]

    assert alert.patterns[0].pattern_id == "sudden_change"
    assert alert.patterns[0].urgency == PatternUrgency.SAME_SHIFT
    assert len(alert.patterns) <= MAX_PATTERNS
    assert any("consistent with" in line for line in alert.patterns[0].evidence)
