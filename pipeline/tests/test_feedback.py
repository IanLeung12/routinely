from datetime import UTC, datetime

from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.feedback import FeedbackStore

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _feedback(verdict: FeedbackVerdict) -> AlertFeedback:
    return AlertFeedback(verdict=verdict, by="nurse-1", at=NOW)


def test_no_feedback_gives_base():
    store = FeedbackStore()
    assert store.threshold("res-1", base=0.5) == 0.5


def test_one_false_alarm_raises_threshold():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.FALSE_ALARM))
    assert store.threshold("res-1", base=0.5) == 0.5 * 1.1


def test_confirmed_lowers_threshold():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED))
    assert store.threshold("res-1", base=0.5) == 0.5 * 0.95


def test_many_false_alarms_clamp_at_max_factor():
    store = FeedbackStore()
    for i in range(20):
        store.record(f"alert-{i}", "res-1", _feedback(FeedbackVerdict.FALSE_ALARM))
    assert store.threshold("res-1", base=0.5) == 0.5 * 1.5


def test_many_confirmed_clamp_at_min_factor():
    store = FeedbackStore()
    for i in range(20):
        store.record(f"alert-{i}", "res-1", _feedback(FeedbackVerdict.CONFIRMED))
    assert store.threshold("res-1", base=0.5) == 0.5 * 0.8


def test_replacing_a_verdict_does_not_double_count():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.FALSE_ALARM))
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED))
    assert store.threshold("res-1", base=0.5) == 0.5 * 0.95


def test_residents_are_independent():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.FALSE_ALARM))
    store.record("alert-2", "res-2", _feedback(FeedbackVerdict.CONFIRMED))
    assert store.threshold("res-1", base=0.5) == 0.5 * 1.1
    assert store.threshold("res-2", base=0.5) == 0.5 * 0.95


def test_get_returns_none_when_unrecorded():
    store = FeedbackStore()
    assert store.get("alert-1") is None


def test_get_returns_stored_feedback():
    store = FeedbackStore()
    feedback = _feedback(FeedbackVerdict.FALSE_ALARM)
    store.record("alert-1", "res-1", feedback)
    assert store.get("alert-1") == feedback


def test_get_returns_latest_after_replacement():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.FALSE_ALARM))
    replacement = _feedback(FeedbackVerdict.CONFIRMED)
    store.record("alert-1", "res-1", replacement)
    assert store.get("alert-1") == replacement


def test_cause_of_returns_none_when_unrecorded():
    store = FeedbackStore()
    assert store.cause_of("alert-1") is None


def test_cause_of_returns_stored_cause():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    assert store.cause_of("alert-1") == "forgot-step"


def test_cause_is_replaced_on_rerecord():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="other")
    assert store.cause_of("alert-1") == "other"


def test_cause_counts_only_confirmed_alerts():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    store.record("alert-2", "res-1", _feedback(FeedbackVerdict.FALSE_ALARM), cause="forgot-step")
    assert store.cause_counts("res-1") == {"forgot-step": 1}


def test_cause_counts_tally_per_cause():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    store.record("alert-2", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    store.record("alert-3", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="other")
    assert store.cause_counts("res-1") == {"forgot-step": 2, "other": 1}


def test_cause_counts_are_per_resident():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    store.record("alert-2", "res-2", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    assert store.cause_counts("res-1") == {"forgot-step": 1}
    assert store.cause_counts("res-2") == {"forgot-step": 1}


def test_cause_counts_empty_when_no_cause_recorded():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED))
    assert store.cause_counts("res-1") == {}


def test_replacing_cause_does_not_double_count():
    store = FeedbackStore()
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="forgot-step")
    store.record("alert-1", "res-1", _feedback(FeedbackVerdict.CONFIRMED), cause="other")
    assert store.cause_counts("res-1") == {"other": 1}
