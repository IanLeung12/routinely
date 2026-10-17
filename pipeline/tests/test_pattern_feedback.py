"""The pattern feedback loop: a nurse's answers re-weight her resident's patterns.

SPEC Nice to have 8. What a nurse confirmed before ranks higher on this resident's
next alerts, what she dismissed ranks lower, and the band the weight lives in is
narrow enough that the ranking is still rules over features (`routine_watch.patterns`)
rather than a tally of opinions.
"""

from datetime import UTC, datetime, timedelta

import pytest

from routine_watch.alerts import build_alerts
from routine_watch.change_detection import build_baseline
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import demo_residents
from routine_watch.feedback import (
    MAX_PATTERN_WEIGHT,
    MIN_PATTERN_WEIGHT,
    PATTERN_STEP,
    FeedbackStore,
)
from routine_watch.patterns import Features, extract_features, score_patterns
from routine_watch.scoring import session_score

NOW = datetime(2026, 1, 1, tzinfo=UTC)
DAYS = 14
START = NOW - timedelta(days=DAYS)

#: Each day's two sessions: morning, then late afternoon.
HOURS = (8, 18)

RESIDENT = "res-1"
OTHER_RESIDENT = "res-2"

MRS_K = "mrs-k"
MRS_K_ALERT = f"alert-{MRS_K}"


def _feedback(verdict: FeedbackVerdict) -> AlertFeedback:
    return AlertFeedback(verdict=verdict, by="nurse-1", at=NOW)


def _confirmed(store: FeedbackStore, alert_id: str, cause: str, resident: str = RESIDENT) -> None:
    store.record(alert_id, resident, _feedback(FeedbackVerdict.CONFIRMED), cause=cause)


def _dismissed(
    store: FeedbackStore, alert_id: str, top_pattern: str, resident: str = RESIDENT
) -> None:
    store.record(
        alert_id,
        resident,
        _feedback(FeedbackVerdict.FALSE_ALARM),
        top_pattern=top_pattern,
    )


# ------------------------------------------------------- the weights in the store


def test_no_feedback_has_no_weights():
    store = FeedbackStore()

    assert store.pattern_weights(RESIDENT) == {}
    assert store.pattern_answers(RESIDENT) == {}


def test_one_confirmed_cause_nudges_that_pattern_up():
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")

    assert store.pattern_weights(RESIDENT) == {"slow_drift": 1.0 + PATTERN_STEP}
    assert store.pattern_answers(RESIDENT) == {"slow_drift": 1}


def test_two_confirmed_causes_nudge_it_further_up():
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")
    _confirmed(store, "alert-2", "slow_drift")

    assert store.pattern_weights(RESIDENT) == {"slow_drift": 1.0 + 2 * PATTERN_STEP}
    assert store.pattern_answers(RESIDENT) == {"slow_drift": 2}


def test_a_false_alarm_nudges_the_pattern_the_alert_led_with_down():
    store = FeedbackStore()
    _dismissed(store, "alert-1", "sudden_change")

    assert store.pattern_weights(RESIDENT) == {"sudden_change": 1.0 - PATTERN_STEP}
    assert store.pattern_answers(RESIDENT) == {"sudden_change": 1}


def test_a_false_alarm_on_an_alert_with_no_pattern_weighs_nothing():
    """A change with no clear pattern is a real answer, and dismissing it blames
    nothing."""
    store = FeedbackStore()
    _dismissed(store, "alert-1", top_pattern=None)

    assert store.pattern_weights(RESIDENT) == {}


def test_a_cause_the_library_has_no_pattern_for_weighs_nothing():
    """An answer of "other" means the library had no pattern for it: none to weigh."""
    store = FeedbackStore()
    _confirmed(store, "alert-1", "other")
    _confirmed(store, "alert-2", "not_a_pattern")

    assert store.pattern_weights(RESIDENT) == {}


def test_a_confirmed_alert_with_no_cause_weighs_nothing():
    store = FeedbackStore()
    store.record("alert-1", RESIDENT, _feedback(FeedbackVerdict.CONFIRMED))

    assert store.pattern_weights(RESIDENT) == {}


def test_a_cause_on_a_dismissed_alert_never_raises_that_pattern():
    """It is not evidence the pattern matched (`cause_counts`), so it never lifts it."""
    store = FeedbackStore()
    store.record(
        "alert-1",
        RESIDENT,
        _feedback(FeedbackVerdict.FALSE_ALARM),
        cause="slow_drift",
        top_pattern="sudden_change",
    )

    assert store.pattern_weights(RESIDENT) == {"sudden_change": 1.0 - PATTERN_STEP}


def test_weights_are_per_resident():
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")
    _dismissed(store, "alert-2", "slow_drift", resident=OTHER_RESIDENT)

    assert store.pattern_weights(RESIDENT) == {"slow_drift": 1.0 + PATTERN_STEP}
    assert store.pattern_weights(OTHER_RESIDENT) == {"slow_drift": 1.0 - PATTERN_STEP}


def test_changing_an_answer_does_not_double_count_it():
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")
    _dismissed(store, "alert-1", "slow_drift")

    assert store.pattern_weights(RESIDENT) == {"slow_drift": 1.0 - PATTERN_STEP}
    assert store.pattern_answers(RESIDENT) == {"slow_drift": 1}


def test_a_pattern_dismissed_as_often_as_it_was_confirmed_is_unweighted():
    store = FeedbackStore()
    for i in range(3):
        _confirmed(store, f"up-{i}", "slow_drift")
        _dismissed(store, f"down-{i}", "slow_drift")

    assert store.pattern_weights(RESIDENT) == {"slow_drift": 1.0}
    assert store.pattern_answers(RESIDENT) == {"slow_drift": 6}


def test_many_confirmed_causes_stay_inside_the_upper_bound():
    store = FeedbackStore()
    for i in range(40):
        _confirmed(store, f"alert-{i}", "slow_drift")

    assert store.pattern_weights(RESIDENT) == {"slow_drift": MAX_PATTERN_WEIGHT}


def test_many_false_alarms_stay_inside_the_lower_bound():
    store = FeedbackStore()
    for i in range(40):
        _dismissed(store, f"alert-{i}", "slow_drift")

    assert store.pattern_weights(RESIDENT) == {"slow_drift": MIN_PATTERN_WEIGHT}


@pytest.mark.parametrize("ups,downs", [(0, 0), (1, 0), (0, 1), (9, 2), (2, 9), (40, 40)])
def test_weights_stay_within_bounds_however_the_answers_fall(ups, downs):
    store = FeedbackStore()
    for i in range(ups):
        _confirmed(store, f"up-{i}", "slow_drift")
    for i in range(downs):
        _dismissed(store, f"down-{i}", "slow_drift")

    for weight in store.pattern_weights(RESIDENT).values():
        assert MIN_PATTERN_WEIGHT <= weight <= MAX_PATTERN_WEIGHT


def test_the_weights_leave_the_tuned_threshold_alone():
    """The two loops are separate: a cause does not make her threshold move twice."""
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")

    assert store.threshold(RESIDENT, base=0.5) == 0.5 * 0.95
    assert store.cause_counts(RESIDENT) == {"slow_drift": 1}


# --------------------------------------------------------------- the scorer

# One resident's own history, as `routine_watch.synth.history` writes it.


def _session(day: int, hour: int, errors: dict | None = None) -> dict:
    return {
        "resident_id": RESIDENT,
        "ts": (START + timedelta(days=day, hours=hour)).isoformat(),
        "task": "tea",
        "errors": dict(errors or {}),
        "self_corrected": 0,
        "duration_s": 180.0,
        "assisted": False,
    }


def _history(errors_on) -> list[dict]:
    return [_session(day, hour, errors_on(day)) for day in range(DAYS) for hour in HOURS]


def _features(sessions: list[dict]) -> Features:
    baseline = build_baseline(
        [session_score(s["errors"], s["self_corrected"], s["assisted"]) for s in sessions]
    )
    return extract_features(sessions, baseline, [], now=NOW)


def _drifting() -> Features:
    """Pauses creeping up over a fortnight: slow drift, on its own."""
    return _features(_history(lambda day: {"hesitation": day // 2} if day >= 2 else {}))


def _drifting_with_repeats() -> Features:
    """The same drift, with repeated steps in the last two days: two patterns, a
    clear gap between them (slow drift 1.0, the executive pattern 0.7)."""
    return _features(
        _history(
            lambda day: {"hesitation": day // 2, "omission": 1, "perseveration": 1}
            if day >= DAYS - 2
            else ({"hesitation": day // 2} if day >= 2 else {})
        )
    )


def _ranked(features: Features, **kwargs) -> list[tuple[str, float]]:
    return [(m.pattern_id, m.confidence) for m in score_patterns(features, **kwargs)]


def test_no_weights_ranks_exactly_as_it_does_today():
    features = _drifting_with_repeats()
    today = score_patterns(features)

    assert score_patterns(features, weights={}, answers={}) == today
    assert score_patterns(features, weights=None, answers=None) == today


def test_a_weight_for_another_pattern_leaves_this_ranking_alone():
    features = _drifting_with_repeats()

    assert score_patterns(
        features, weights={"one_sided_change": 1.3}, answers={"one_sided_change": 3}
    ) == score_patterns(features)


def test_two_confirmed_causes_raise_that_patterns_confidence_for_that_resident_only():
    features = _drifting()
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")
    _confirmed(store, "alert-2", "slow_drift")

    mine = _ranked(
        features,
        weights=store.pattern_weights(RESIDENT),
        answers=store.pattern_answers(RESIDENT),
    )
    theirs = _ranked(
        features,
        weights=store.pattern_weights(OTHER_RESIDENT),
        answers=store.pattern_answers(OTHER_RESIDENT),
    )

    assert _ranked(features) == [("slow_drift", 0.75)]
    assert mine == [("slow_drift", 0.9)]
    assert theirs == _ranked(features)


def test_past_false_alarms_lower_that_patterns_confidence():
    features = _drifting()
    store = FeedbackStore()
    _dismissed(store, "alert-1", "slow_drift")

    assert _ranked(
        features,
        weights=store.pattern_weights(RESIDENT),
        answers=store.pattern_answers(RESIDENT),
    ) == [("slow_drift", 0.675)]


def test_the_weight_applies_before_the_threshold():
    """A dismissed pattern can fall below the bar, and a confirmed one can clear it."""
    features = _drifting()

    assert _ranked(features, threshold=0.6) == [("slow_drift", 0.75)]
    assert (
        _ranked(features, threshold=0.6, weights={"slow_drift": 0.7}, answers={"slow_drift": 3})
        == []
    )
    assert _ranked(features, threshold=0.8) == []
    assert _ranked(
        features, threshold=0.8, weights={"slow_drift": 1.2}, answers={"slow_drift": 2}
    ) == [("slow_drift", 0.9)]


def test_answers_both_ways_can_reorder_the_patterns():
    features = _drifting_with_repeats()
    store = FeedbackStore()
    _confirmed(store, "alert-1", "executive_pattern")
    _confirmed(store, "alert-2", "executive_pattern")
    _dismissed(store, "alert-3", "slow_drift")
    _dismissed(store, "alert-4", "slow_drift")

    assert [pattern_id for pattern_id, _ in _ranked(features)] == [
        "slow_drift",
        "executive_pattern",
    ]
    assert _ranked(
        features,
        weights=store.pattern_weights(RESIDENT),
        answers=store.pattern_answers(RESIDENT),
    ) == [("executive_pattern", 0.84), ("slow_drift", 0.8)]


def test_feedback_alone_cannot_flip_a_clear_ranking():
    """The bound is the point: however many answers pile up on the runner-up, a
    pattern the features back clearly stays on top (SPEC Nice to have 8)."""
    features = _drifting_with_repeats()
    store = FeedbackStore()
    for i in range(40):
        _confirmed(store, f"alert-{i}", "executive_pattern")

    ranked = _ranked(
        features,
        weights=store.pattern_weights(RESIDENT),
        answers=store.pattern_answers(RESIDENT),
    )

    assert [pattern_id for pattern_id, _ in ranked] == ["slow_drift", "executive_pattern"]


def test_a_weighted_confidence_never_leaves_nought_to_one():
    features = _drifting_with_repeats()

    for _, confidence in _ranked(
        features, weights={"slow_drift": MAX_PATTERN_WEIGHT}, answers={"slow_drift": 3}
    ):
        assert 0.0 <= confidence <= 1.0


def test_a_pattern_the_features_do_not_back_is_not_lifted_by_feedback():
    """Feedback moves a pattern's place in the ranking, never conjures a match."""
    nothing = extract_features([], build_baseline([1.0, 1.0, 1.2]), [], now=NOW)

    assert score_patterns(nothing) == []
    assert (
        score_patterns(
            nothing, weights={"slow_drift": MAX_PATTERN_WEIGHT}, answers={"slow_drift": 9}
        )
        == []
    )


# --------------------------------------------------------------- the wording


def test_the_evidence_says_how_many_answers_weighed_the_pattern():
    features = _drifting()
    store = FeedbackStore()
    _confirmed(store, "alert-1", "slow_drift")
    _confirmed(store, "alert-2", "slow_drift")

    match = score_patterns(
        features,
        weights=store.pattern_weights(RESIDENT),
        answers=store.pattern_answers(RESIDENT),
    )[0]

    assert "weighted by 2 past nurse answers for this resident" in match.evidence[-1]
    assert "up 20%" in match.evidence[-1]


def test_one_answer_reads_as_one_answer():
    features = _drifting()

    match = score_patterns(features, weights={"slow_drift": 0.9}, answers={"slow_drift": 1})[0]

    assert "weighted by 1 past nurse answer for this resident" in match.evidence[-1]
    assert "down 10%" in match.evidence[-1]


def test_an_unweighted_pattern_says_nothing_about_nurse_answers():
    features = _drifting()
    store = FeedbackStore()
    for i in range(2):
        _confirmed(store, f"up-{i}", "slow_drift")
        _dismissed(store, f"down-{i}", "slow_drift")

    unweighted = score_patterns(features)[0]
    cancelled = score_patterns(
        features,
        weights=store.pattern_weights(RESIDENT),
        answers=store.pattern_answers(RESIDENT),
    )[0]

    assert not any("nurse" in line for line in unweighted.evidence)
    assert cancelled == unweighted


def test_weighted_patterns_are_still_only_consistent_with_something():
    features = _drifting_with_repeats()
    matches = score_patterns(
        features,
        weights={"slow_drift": MIN_PATTERN_WEIGHT, "executive_pattern": MAX_PATTERN_WEIGHT},
        answers={"slow_drift": 3, "executive_pattern": 3},
    )

    assert matches
    for match in matches:
        assert any("consistent with" in line for line in match.evidence)
        assert not any("diagnos" in line.lower() for line in match.evidence)
        assert "diagnos" not in match.name.lower()


# ----------------------------------------------------------------- the alert


def test_the_alert_ranks_as_today_when_nothing_has_been_answered(mrs_k_flagged):
    residents = demo_residents()

    assert build_alerts(residents, feedback=FeedbackStore()) == build_alerts(residents)


def test_a_confirmed_cause_raises_that_pattern_on_her_next_alert(mrs_k_flagged):
    today = build_alerts(demo_residents())[0]
    top = today.patterns[0].pattern_id
    store = FeedbackStore()
    _confirmed(store, MRS_K_ALERT, top, resident=MRS_K)
    _confirmed(store, "alert-mrs-k-earlier", top, resident=MRS_K)

    alert = build_alerts(demo_residents(), feedback=store)[0]

    assert alert.patterns[0].pattern_id == top
    assert alert.patterns[0].confidence > today.patterns[0].confidence
    assert "weighted by 2 past nurse answers" in alert.patterns[0].evidence[-1]


def test_another_residents_answers_do_not_move_her_patterns(mrs_k_flagged):
    store = FeedbackStore()
    _confirmed(store, "alert-mr-chen", "slow_drift", resident="mr-chen")
    _dismissed(store, "alert-mr-chen-2", "sudden_change", resident="mr-chen")

    assert build_alerts(demo_residents(), feedback=store) == build_alerts(demo_residents())


def test_repeated_false_alarms_demote_the_pattern_she_keeps_dismissing(mrs_k_flagged):
    today = build_alerts(demo_residents())[0]
    top = today.patterns[0].pattern_id
    assert len(today.patterns) >= 2, "this test needs a runner-up to promote"
    store = FeedbackStore()

    _dismissed(store, MRS_K_ALERT, top, resident=MRS_K)
    one_answer = build_alerts(demo_residents(), feedback=store)[0]

    for i in range(9):
        _dismissed(store, f"alert-mrs-k-{i}", top, resident=MRS_K)
    many_answers = build_alerts(demo_residents(), feedback=store)[0]

    assert one_answer.patterns[0].pattern_id == top, "one answer cannot flip the ranking"
    assert one_answer.patterns[0].confidence < today.patterns[0].confidence
    assert many_answers.patterns[0].pattern_id != top
