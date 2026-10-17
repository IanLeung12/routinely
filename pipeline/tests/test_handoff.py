"""The shift handoff: one view of who changed while this nurse was away (T062).

The demo's data lives on `demo.DEMO_NOW`, so that is the clock every window here ends
at, the way the `/handoff` route does.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from routine_watch import api as api_module
from routine_watch import handoff as handoff_module
from routine_watch.alerts import build_alerts, distinct_clauses, normal_error_rate
from routine_watch.api import app
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import DEMO_NOW, demo_residents
from routine_watch.explain import TemplateExplainer
from routine_watch.feedback import FeedbackStore
from routine_watch.handoff import DEFAULT_WINDOW_H, build_handoff
from routine_watch.monitoring import get_monitoring_store
from routine_watch.tasks import load_task

#: The demo resident with the sudden spike, and one the seeded demo leaves alone.
FLAGGED_RESIDENT = "mrs-k"
STABLE_RESIDENT = "mrs-ahmed"

#: The alert `build_alerts` raises for the flagged resident.
FLAGGED_ALERT = "alert-mrs-k"

#: The demo resident on a slow drift, and a session of theirs that sits just under
#: their own threshold until a nurse's feedback lowers it.
DRIFT_RESIDENT = "mr-chen"

#: Enough confirmed alerts to pull a threshold down to its floor (`feedback.MIN_FACTOR`).
MANY_CONFIRMED = 6

#: The baseline comparison both the handoff and an alert end their sentence with.
NORMALLY = re.compile(r"vs \S+ normally over \S+ days")


@pytest.fixture(autouse=True)
def _nothing_reviewed():
    """Each test starts with a clean feedback store: the API module keeps it global.
    (`conftest._empty_log` already puts the session log back.)"""
    api_module._feedback_store = FeedbackStore()
    yield
    api_module._feedback_store = FeedbackStore()


@pytest.fixture(autouse=True)
def _every_room_on():
    """Each test starts and ends with every room monitored: the store is global."""
    get_monitoring_store().reset()
    yield
    get_monitoring_store().reset()


def _needs_review(entry: dict) -> bool:
    return bool(entry["flags"] or entry["pending_review"] or entry["trending"])


def resident(resident_id: str) -> dict:
    """One seeded demo resident, the way `build_handoff` sees them."""
    return next(r for r in demo_residents() if r["id"] == resident_id)


def explainer_call() -> tuple[list[dict], dict, list[str]]:
    """The `(errors, baseline, context)` the handoff hands its explainer."""
    seen: list[tuple[list[dict], dict, list[str]]] = []

    class RecordingExplainer:
        def summarise(self, errors, baseline, context):
            seen.append((errors, baseline, context))
            return "recorded"

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(handoff_module, "_get_explainer", lambda: RecordingExplainer())
        build_handoff(DEMO_NOW, 12)

    return seen[0]


def row(result: dict, resident_id: str) -> dict:
    rows = [row for row in result["residents"] if row["resident_id"] == resident_id]
    assert rows, f"{resident_id} is missing from the handoff"
    return rows[0]


def confirmed(resident_id: str, n: int) -> FeedbackStore:
    """A feedback store with `n` confirmed alerts logged against `resident_id`."""
    store = FeedbackStore()
    for i in range(n):
        store.record(
            f"alert-{i}",
            resident_id,
            AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="nurse", at=DEMO_NOW),
        )
    return store


def test_handoff_has_the_window_every_resident_and_a_summary() -> None:
    result = build_handoff(DEMO_NOW, 12)

    assert result["window_hours"] == 12
    assert isinstance(result["summary"], str) and result["summary"]
    assert len(result["residents"]) == 6
    assert result["paused"] == []
    for entry in result["residents"]:
        assert set(entry) == {
            "resident_id",
            "name",
            "flags",
            "pending_review",
            "trending",
            "monitoring_paused",
        }
        assert isinstance(entry["flags"], int)
        assert isinstance(entry["pending_review"], int)
        assert isinstance(entry["trending"], bool)
        assert entry["monitoring_paused"] is False


def test_default_window_is_a_shift() -> None:
    assert DEFAULT_WINDOW_H == 12
    assert build_handoff(DEMO_NOW)["window_hours"] == 12


def test_flagged_resident_appears_with_her_flag_in_the_demo_window() -> None:
    entry = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    assert entry["name"] == "Mrs. K"
    assert entry["flags"] == 1, "her bad session is in the window"
    assert entry["pending_review"] == 0, "one session above baseline is not yet an alert"


def test_the_live_session_shows_up_as_a_flag_and_an_alert_to_review(mrs_k_flagged) -> None:
    """The demo's fourth beat (SPEC section 10): the session a teammate just made tea
    for is Mrs. K's, and the nurse coming on shift sees it and its alert."""
    entry = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    assert entry["flags"] == 2
    assert entry["pending_review"] == 1


def test_stable_resident_is_listed_with_no_flags() -> None:
    entry = row(build_handoff(DEMO_NOW, 12), STABLE_RESIDENT)

    assert entry["flags"] == 0
    assert entry["pending_review"] == 0
    assert entry["trending"] is False


def test_nothing_paused_leaves_an_empty_list_and_every_row_unpaused() -> None:
    result = build_handoff(DEMO_NOW, 12)

    assert result["paused"] == []
    assert all(entry["monitoring_paused"] is False for entry in result["residents"])


def test_pausing_a_room_lists_its_resident_once_and_marks_her_row() -> None:
    mrs_k = resident(FLAGGED_RESIDENT)
    get_monitoring_store().set(mrs_k["room"], False)

    result = build_handoff(DEMO_NOW, 12)

    assert result["paused"] == [
        {"room": mrs_k["room"], "resident_id": mrs_k["id"], "name": mrs_k["name"]}
    ]
    for entry in result["residents"]:
        expected = entry["resident_id"] == FLAGGED_RESIDENT
        assert entry["monitoring_paused"] is expected


def test_resuming_a_room_clears_it_from_paused_again() -> None:
    mrs_k = resident(FLAGGED_RESIDENT)
    store = get_monitoring_store()
    store.set(mrs_k["room"], False)
    store.set(mrs_k["room"], True)

    result = build_handoff(DEMO_NOW, 12)

    assert result["paused"] == []
    assert all(entry["monitoring_paused"] is False for entry in result["residents"])


def test_pausing_a_room_does_not_change_flag_or_pending_counts(mrs_k_flagged) -> None:
    mrs_k = resident(FLAGGED_RESIDENT)
    before = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    get_monitoring_store().set(mrs_k["room"], False)
    after = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    assert after["flags"] == before["flags"]
    assert after["pending_review"] == before["pending_review"]
    assert after["monitoring_paused"] is True
    assert before["monitoring_paused"] is False


def test_summary_names_a_paused_room_instead_of_reading_all_quiet() -> None:
    mrs_k = resident(FLAGGED_RESIDENT)
    get_monitoring_store().set(mrs_k["room"], False)

    summary = build_handoff(DEMO_NOW, 12)["summary"]

    assert f"Room {mrs_k['room']} (Mrs. K) was paused" in summary
    assert "no flags are expected from it" in summary
    assert "diagnos" not in summary.lower()


def test_summary_is_unchanged_when_nothing_is_paused() -> None:
    assert "paused" not in build_handoff(DEMO_NOW, 12)["summary"].lower()


def test_context_carries_one_line_per_paused_room() -> None:
    mrs_k = resident(FLAGGED_RESIDENT)
    get_monitoring_store().set(mrs_k["room"], False)

    (_, _, context) = explainer_call()

    assert f"Room {mrs_k['room']} (Mrs. K) was paused, so no flags are expected from it" in context


def test_pausing_a_quiet_room_drops_it_from_the_nothing_to_review_count() -> None:
    """T259 added the paused line so a paused room stops reading as 'all quiet'; the
    quiet count must drop by one too, or the paused resident is counted twice."""
    mrs_ahmed = resident(STABLE_RESIDENT)

    before = build_handoff(DEMO_NOW, 12)["summary"]
    get_monitoring_store().set(mrs_ahmed["room"], False)
    after = build_handoff(DEMO_NOW, 12)["summary"]

    before_quiet = int(re.search(r"(\d+) residents? with nothing to review", before).group(1))
    after_match = re.search(r"(\d+) residents? with nothing to review", after)
    after_quiet = int(after_match.group(1)) if after_match else 0

    assert after_quiet == before_quiet - 1
    assert f"Room {mrs_ahmed['room']} (Mrs. Ahmed) was paused" in after


def test_a_window_only_counts_what_happened_inside_it() -> None:
    """Mrs. K's bad session is about six hours before the demo's clock, so a four-hour
    window has not seen it yet and a shift-long one has."""
    assert row(build_handoff(DEMO_NOW, 4), FLAGGED_RESIDENT)["flags"] == 0
    assert row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)["flags"] == 1


def test_a_window_with_no_sessions_in_it_flags_nothing() -> None:
    result = build_handoff(DEMO_NOW - timedelta(days=30), 12)

    assert all(entry["flags"] == 0 for entry in result["residents"])
    assert all(entry["pending_review"] == 0 for entry in result["residents"])
    assert "above baseline" not in result["summary"]
    assert "pending review" not in result["summary"]


def test_residents_to_review_come_first() -> None:
    rows = build_handoff(DEMO_NOW, 12)["residents"]
    order = [entry["resident_id"] for entry in rows]
    quiet = [entry["resident_id"] for entry in rows if not _needs_review(entry)]

    assert order[0] == FLAGGED_RESIDENT, "the flagged resident is read first"
    assert order.index("mr-chen") < order.index(quiet[0]), "a rising trend beats nothing"
    assert quiet == sorted(quiet), "quiet residents come out in a stable order"


def test_drift_resident_is_trending_without_a_flag_this_shift() -> None:
    entry = row(build_handoff(DEMO_NOW, 12), "mr-chen")

    assert entry["trending"] is True
    assert entry["flags"] == 0, "a slow drift is not a flagged session"


def test_reviewed_alerts_stop_being_pending(mrs_k_flagged) -> None:
    store = FeedbackStore()
    store.record(
        FLAGGED_ALERT,
        FLAGGED_RESIDENT,
        AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="nurse", at=DEMO_NOW),
    )

    entry = row(build_handoff(DEMO_NOW, 12, feedback=store), FLAGGED_RESIDENT)

    assert entry["pending_review"] == 0
    assert entry["flags"] == 2, "reviewing the alert does not unflag the sessions"


def test_confirmed_alerts_lower_the_bar_a_session_is_measured_against() -> None:
    """Feedback tunes the threshold (MVP 7), so the handoff counts against the bar the
    nurse's own answers have moved, not the untouched one."""
    assert row(build_handoff(DEMO_NOW, 12), DRIFT_RESIDENT)["flags"] == 0

    store = confirmed(DRIFT_RESIDENT, MANY_CONFIRMED)

    assert row(build_handoff(DEMO_NOW, 12, feedback=store), DRIFT_RESIDENT)["flags"] == 1


def test_summary_comes_from_the_explainer() -> None:
    class FakeExplainer:
        def summarise(self, errors, baseline, context):
            return "FAKE"

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(handoff_module, "_get_explainer", lambda: FakeExplainer())
        result = build_handoff(DEMO_NOW, 12)

    assert result["summary"] == "FAKE"


def test_summary_defaults_to_the_template_explainer_and_never_diagnoses() -> None:
    """With LIVE_API unset, `get_explainer()` resolves to the template explainer, so
    the default summary is what an explicit `TemplateExplainer` would have written."""
    default = build_handoff(DEMO_NOW, 12)["summary"]

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(handoff_module, "_get_explainer", lambda: TemplateExplainer())
        explicit = build_handoff(DEMO_NOW, 12)["summary"]

    assert default == explicit
    assert "flagged for review" in default.lower()
    assert "diagnos" not in default.lower()


def test_summary_names_who_to_look_at_and_counts_the_quiet_rest() -> None:
    summary = build_handoff(DEMO_NOW, 12)["summary"]

    assert "last 12 h, 6 residents" in summary
    assert "Mrs. K: 1 session above baseline" in summary
    assert "Mr. Chen: error score trending up" in summary
    assert "3 residents with nothing to review" in summary


def test_the_explainer_only_sees_the_errors_the_pipeline_found() -> None:
    """The summary is written from detected evidence, never from invented facts."""
    (errors, baseline, context) = explainer_call()

    assert baseline["observed"] == 2, "both errors in Mrs. K's flagged session"
    assert len(errors) <= baseline["observed"], "repeated clauses are said once"
    assert {error["type"] for error in errors} == {"omission", "perseveration"}
    assert context[1] == "last 12 h, 6 residents"
    assert context[2].startswith("Mrs. K:")


def test_summary_names_steps_of_the_task_not_a_placeholder() -> None:
    """T121 gave the alert screen a real step per error; the handoff reads that same
    evidence (`alerts.task_errors`) instead of synthesising "the task" again (T166)."""
    (errors, _, _) = explainer_call()
    steps = set(load_task("tea").step_ids)
    summary = build_handoff(DEMO_NOW, 12)["summary"]

    assert errors, "Mrs. K's flagged session is in the window"
    assert {error["step_id"] for error in errors} <= steps
    assert "the task" not in summary
    assert any(step.replace("_", " ") in summary for step in steps)


def test_summary_measures_the_session_against_that_residents_own_baseline() -> None:
    """SPEC section 7: a resident is compared with her own history, never with the
    unit's mixed-together average."""
    mrs_k = resident(FLAGGED_RESIDENT)
    unit_sessions = [s for r in demo_residents() for s in r["sessions"]]
    unit_rate = sum(sum(s["errors"].values()) for s in unit_sessions) / len(unit_sessions)

    (_, baseline, _) = explainer_call()

    assert baseline["baseline_mean"] == round(normal_error_rate(mrs_k), 2)
    assert baseline["baseline_days"] == 14, "her own two weeks of history"
    assert baseline["baseline_mean"] != round(unit_rate, 2), "not the unit's average"


def test_handoff_and_the_alert_say_the_same_thing_about_the_same_session(
    mrs_k_flagged,
) -> None:
    """A nurse reads the handoff line, opens the alert it points at and must find the
    same errors at the same steps and the same normal - not a second guess at them."""
    (errors, _, _) = explainer_call()
    summary = build_handoff(DEMO_NOW, 12)["summary"]
    alert = next(a for a in build_alerts(demo_residents()) if a.resident_id == FLAGGED_RESIDENT)

    assert errors, "her live session is in the window"
    assert all(clause in distinct_clauses(alert.errors) for clause in errors)
    assert NORMALLY.search(summary)[0] == NORMALLY.search(alert.summary)[0]


def test_summary_says_whose_session_it_is() -> None:
    """A handoff line about an unnamed session is a line a nurse cannot act on."""
    (_, _, context) = explainer_call()

    assert context[0] == "this session is Mrs. K's"
    assert "Mrs. K's" in build_handoff(DEMO_NOW, 12)["summary"]


def test_a_quiet_window_compares_nobody_with_anybody() -> None:
    """With no flagged session there is nothing to measure, so the numbers are zeros
    rather than some other resident's average."""
    seen: list[dict] = []

    class RecordingExplainer:
        def summarise(self, errors, baseline, context):
            seen.append(baseline)
            return "recorded"

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(handoff_module, "_get_explainer", lambda: RecordingExplainer())
        build_handoff(DEMO_NOW - timedelta(days=30), 12)

    assert seen[0] == {"observed": 0, "baseline_mean": 0.0, "baseline_days": 0}


def test_naive_now_is_rejected_rather_than_silently_wrong() -> None:
    """An empty handoff would look like a quiet unit, so a clockless `now` says so."""
    with pytest.raises(ValueError, match="timezone-aware"):
        build_handoff(datetime(2026, 1, 1), 12)  # noqa: DTZ001 - the point of the test


def test_route_serves_the_handoff_for_the_demo_window() -> None:
    with TestClient(app) as client:
        response = client.get("/handoff", params={"hours": 12})

    assert response.status_code == 200
    body = response.json()
    assert body["window_hours"] == 12
    assert body == build_handoff(DEMO_NOW, 12)


def test_route_defaults_to_a_twelve_hour_window() -> None:
    with TestClient(app) as client:
        response = client.get("/handoff")

    assert response.status_code == 200
    assert response.json()["window_hours"] == DEFAULT_WINDOW_H


@pytest.mark.parametrize("hours", [0, -1, 169, "soon"])
def test_route_rejects_a_window_it_cannot_serve(hours: object) -> None:
    with TestClient(app) as client:
        response = client.get("/handoff", params={"hours": hours})

    assert response.status_code == 422


def test_route_applies_the_feedback_a_nurse_has_already_given(mrs_k_flagged) -> None:
    """Confirming the alert through the API takes it out of `pending_review`."""
    with TestClient(app) as client:
        before = client.get("/handoff", params={"hours": 12}).json()
        posted = client.post(f"/alerts/{FLAGGED_ALERT}/feedback", json={"verdict": "confirmed"})
        after = client.get("/handoff", params={"hours": 12}).json()

    assert posted.status_code == 200
    assert row(before, FLAGGED_RESIDENT)["pending_review"] == 1
    assert row(after, FLAGGED_RESIDENT)["pending_review"] == 0


def test_route_window_ends_on_the_demo_clock_not_the_wall_clock() -> None:
    """The demo's sessions and its live session are both anchored to `DEMO_NOW`, so a
    handoff measured from today's date would always be empty."""
    assert datetime.now(UTC) - DEMO_NOW > timedelta(days=30)

    with TestClient(app) as client:
        body = client.get("/handoff", params={"hours": 12}).json()

    assert row(body, FLAGGED_RESIDENT)["flags"] == 1
