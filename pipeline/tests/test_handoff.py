"""The shift handoff: one view of who changed while this nurse was away (T062).

The demo's data lives on `demo.DEMO_NOW`, so that is the clock every window here ends
at, the way the `/handoff` route does.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from routine_watch import api as api_module
from routine_watch import handoff as handoff_module
from routine_watch import session_log
from routine_watch.api import app
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import DEMO_NOW
from routine_watch.explain import TemplateExplainer
from routine_watch.feedback import FeedbackStore
from routine_watch.handoff import DEFAULT_WINDOW_H, build_handoff

#: The demo resident with the sudden spike, and one the seeded demo leaves alone.
FLAGGED_RESIDENT = "mrs-k"
STABLE_RESIDENT = "mrs-ahmed"

#: The alert `build_alerts` raises for the flagged resident.
FLAGGED_ALERT = "alert-mrs-k"

#: Enough false alarms to push a threshold to its ceiling (`feedback.MAX_FACTOR`).
MANY_FALSE_ALARMS = 6


@pytest.fixture(autouse=True)
def _seeded_demo():
    """The seeded demo, nothing recorded and nothing reviewed: both are global state,
    so every test here puts them back (`session_log`, `api._feedback_store`)."""
    session_log.reset()
    api_module._feedback_store = FeedbackStore()
    yield
    session_log.reset()
    api_module._feedback_store = FeedbackStore()


def _needs_review(entry: dict) -> bool:
    return bool(entry["flags"] or entry["pending_review"] or entry["trending"])


def row(result: dict, resident_id: str) -> dict:
    rows = [row for row in result["residents"] if row["resident_id"] == resident_id]
    assert rows, f"{resident_id} is missing from the handoff"
    return rows[0]


def false_alarms(resident_id: str, n: int) -> FeedbackStore:
    """A feedback store with `n` false alarms logged against `resident_id`."""
    store = FeedbackStore()
    for i in range(n):
        store.record(
            f"alert-{i}",
            resident_id,
            AlertFeedback(verdict=FeedbackVerdict.FALSE_ALARM, by="nurse", at=DEMO_NOW),
        )
    return store


def test_handoff_has_the_window_every_resident_and_a_summary() -> None:
    result = build_handoff(DEMO_NOW, 12)

    assert result["window_hours"] == 12
    assert isinstance(result["summary"], str) and result["summary"]
    assert len(result["residents"]) == 6
    for entry in result["residents"]:
        assert set(entry) == {"resident_id", "name", "flags", "pending_review", "trending"}
        assert isinstance(entry["flags"], int)
        assert isinstance(entry["pending_review"], int)
        assert isinstance(entry["trending"], bool)


def test_default_window_is_a_shift() -> None:
    assert DEFAULT_WINDOW_H == 12
    assert build_handoff(DEMO_NOW)["window_hours"] == 12


def test_flagged_resident_appears_with_her_flag_in_the_demo_window() -> None:
    entry = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    assert entry["name"] == "Mrs. K"
    assert entry["flags"] == 1
    assert entry["pending_review"] == 1


def test_stable_resident_is_listed_with_no_flags() -> None:
    entry = row(build_handoff(DEMO_NOW, 12), STABLE_RESIDENT)

    assert entry["flags"] == 0
    assert entry["pending_review"] == 0
    assert entry["trending"] is False


def test_a_wider_window_catches_more_of_the_same_resident_s_sessions() -> None:
    twelve = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)["flags"]
    two_days = row(build_handoff(DEMO_NOW, 48), FLAGGED_RESIDENT)["flags"]

    assert two_days > twelve


def test_a_window_with_no_sessions_in_it_flags_nothing() -> None:
    result = build_handoff(DEMO_NOW - timedelta(days=30), 12)

    assert all(entry["flags"] == 0 for entry in result["residents"])
    assert all(entry["pending_review"] == 0 for entry in result["residents"])
    assert "flagged for review" not in result["summary"].replace(
        "with no change flagged for review", ""
    )


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


def test_reviewed_alerts_stop_being_pending() -> None:
    store = FeedbackStore()
    store.record(
        FLAGGED_ALERT,
        FLAGGED_RESIDENT,
        AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="nurse", at=DEMO_NOW),
    )

    entry = row(build_handoff(DEMO_NOW, 12, feedback=store), FLAGGED_RESIDENT)

    assert entry["pending_review"] == 0
    assert entry["flags"] == 1, "reviewing the alert does not unflag the session"


def test_false_alarms_raise_the_threshold_a_session_is_measured_against() -> None:
    store = false_alarms(FLAGGED_RESIDENT, MANY_FALSE_ALARMS)

    entry = row(build_handoff(DEMO_NOW, 12, feedback=store), FLAGGED_RESIDENT)

    assert entry["flags"] == 0, "a nurse who keeps saying 'false alarm' gets fewer flags"


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
    assert "Mrs. K: 1 session flagged for review, 1 alert pending review" in summary
    assert "Mr. Chen: error score trending up" in summary
    assert "3 residents with no change flagged for review" in summary


def test_the_explainer_only_sees_the_errors_the_pipeline_found() -> None:
    """The summary is written from detected evidence, never from invented facts."""
    seen: list[tuple[list[dict], dict, list[str]]] = []

    class RecordingExplainer:
        def summarise(self, errors, baseline, context):
            seen.append((errors, baseline, context))
            return "recorded"

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(handoff_module, "_get_explainer", lambda: RecordingExplainer())
        build_handoff(DEMO_NOW, 12)

    (errors, baseline, context) = seen[0]
    assert baseline["observed"] == len(errors)
    assert {error["type"] for error in errors} == {"omission", "perseveration"}
    assert context[0] == "last 12 h, 6 residents"
    assert context[1].startswith("Mrs. K:")


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


def test_route_applies_the_feedback_a_nurse_has_already_given() -> None:
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
