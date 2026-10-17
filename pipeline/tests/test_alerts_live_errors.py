"""T155: the alert opened after a live session shows that session's own errors.

The live session's score was already merged into the resident's history
(`demo._live_sessions`) but its errors were not, so the alert invented a placeholder
step and time per error and a nurse who had just watched "skipped Put the teabag in
the cup · 1:10" opened the alert and read "skipped fill kettle 0:33" instead. These
tests pin the real errors, their session id, and the summary's wording when the flag
rests on more than one session.
"""

import pytest
from fastapi.testclient import TestClient

from routine_watch import session_log
from routine_watch.alerts import build_alerts, session_id_for, task_errors
from routine_watch.api import app
from routine_watch.contracts import Alert
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.evidence import known_session
from routine_watch.explain import TemplateExplainer

MRS_K_ALERT = f"alert-{DEMO_RESIDENT}"

#: What `tests/scenarios/tea_skip_teabag_pour_twice` records, which is what the live
#: view shows on stage: the teabag step never happens, and the water is poured twice.
LIVE_ERRORS = {("omission", "teabag_in_cup"), ("perseveration", "pour")}

#: Every test here is about the alert after the demo's live session, so every test
#: plays it first (`conftest.mrs_k_flagged`: the seeded history alone leaves mrs-k on
#: watch, not flagged).
pytestmark = pytest.mark.usefixtures("mrs_k_flagged")


def _mrs_k_alert() -> Alert:
    return next(
        alert for alert in build_alerts(demo_residents()) if alert.resident_id == DEMO_RESIDENT
    )


def _live_session_id() -> str:
    """The id the live session was recorded under, the one its errors are keyed by."""
    [session] = session_log.sessions_for(DEMO_RESIDENT)
    return session.session_id


def test_alert_lists_the_live_sessions_own_errors() -> None:
    """The acceptance: her alert names the omission of the teabag step and the
    repeated pour, under the live session's id."""
    alert = _mrs_k_alert()
    live = _live_session_id()

    assert live in alert.session_ids
    found = {
        (str(error.type), error.step_id) for error in alert.errors if error.session_id == live
    }
    assert found == LIVE_ERRORS


def test_the_live_errors_are_the_events_the_classifier_found() -> None:
    """Not merely the same steps: the same error events, times and evidence included,
    so the live view and the alert are about one session rather than two readings."""
    live = _live_session_id()
    alert = _mrs_k_alert()

    assert [error for error in alert.errors if error.session_id == live] == (
        session_log.errors_for(live)
    )


def test_no_alert_error_claims_a_step_the_live_session_never_had() -> None:
    """The bug as a nurse met it: errors attributed to the live session that it never
    made (a skipped `fill_kettle`, a repeated `boil`)."""
    live = _live_session_id()
    alert = _mrs_k_alert()

    invented = [
        error
        for error in alert.errors
        if error.session_id == live and (str(error.type), error.step_id) not in LIVE_ERRORS
    ]
    assert invented == []


def test_alerts_endpoint_serves_the_live_sessions_errors() -> None:
    """`curl localhost:8000/alerts/alert-mrs-k` after the live session: what the
    dashboard's "Open alert" actually fetches."""
    live = _live_session_id()

    with TestClient(app) as client:
        response = client.get(f"/alerts/{MRS_K_ALERT}")

    assert response.status_code == 200
    body = response.json()
    found = {
        (error["type"], error["step_id"])
        for error in body["errors"]
        if error["session_id"] == live
    }
    assert found == LIVE_ERRORS


def test_summary_does_not_call_two_sessions_one_session() -> None:
    """Errors from two sessions are not "this session" (SPEC section 7: two bad
    sessions inside 48 h is what a change flag rests on)."""
    alert = _mrs_k_alert()

    assert len(alert.session_ids) == 2
    assert "across 2 sessions" in alert.summary
    assert "this session" not in alert.summary


def test_a_summary_about_one_session_still_says_this_session() -> None:
    """The shift handoff summarises exactly one session, so its wording stays."""
    errors = [{"type": "omission", "step_id": "teabag_in_cup", "t_start": 42.0}]
    baseline = {"observed": 1, "baseline_mean": 0.2, "baseline_days": 14, "sessions": 1}

    summary = TemplateExplainer().summarise(errors, baseline, [])

    assert "this session" in summary
    assert "sessions" not in summary


def test_evidence_can_replay_a_live_sessions_error() -> None:
    """"Open evidence" on one of those errors has to find its session: T155 moved
    them off the `resident-index` ids `routine_watch.evidence` used to parse."""
    live = _live_session_id()
    error = next(error for error in _mrs_k_alert().errors if error.session_id == live)

    assert known_session(live)
    with TestClient(app) as client:
        response = client.get(
            f"/sessions/{live}/replay",
            params={"t_start": error.t_start, "t_end": error.t_end},
        )

    assert response.status_code == 200
    assert response.json()["frames"]


def test_session_id_for_keeps_a_sessions_own_id() -> None:
    assert session_id_for("mrs-k", 3) == "mrs-k-3"
    assert session_id_for("mrs-k", 3, {}) == "mrs-k-3"
    assert session_id_for("mrs-k", 3, {"session_id": "tea-skip-pour-twice-1"}) == (
        "tea-skip-pour-twice-1"
    )


def test_task_errors_reads_recorded_events_instead_of_inventing_them() -> None:
    """A session dict carrying `error_events` is one somebody watched: its errors are
    read as they were classified, under the id they were recorded with."""
    session = {
        "resident_id": "mrs-k",
        "session_id": "live-1",
        "ts": "2025-12-31T23:58:16+00:00",
        "task": "make_tea",
        "errors": {"omission": 1},
        "error_events": [
            {
                "error_id": "live-1:omission:teabag_in_cup",
                "session_id": "live-1",
                "type": "omission",
                "step_id": "teabag_in_cup",
                "t_start": 70.0,
                "t_end": 79.0,
                "evidence": [],
            }
        ],
        "self_corrected": 0,
        "duration_s": 104.0,
        "assisted": False,
    }

    errors = task_errors("mrs-k-23", session)

    assert [(error.session_id, error.step_id, error.t_start) for error in errors] == [
        ("live-1", "teabag_in_cup", 70.0)
    ]


def test_a_self_corrected_slip_is_not_one_of_the_errors() -> None:
    """A mistake the resident fixed is a weaker signal, not an error (SPEC section 7),
    and it is not in the counts the score and the resident's normal are built from."""
    session = {
        "resident_id": "mrs-k",
        "session_id": "live-2",
        "ts": "2025-12-31T23:58:16+00:00",
        "task": "make_tea",
        "errors": {},
        "error_events": [
            {
                "error_id": "live-2:sequence:pour",
                "session_id": "live-2",
                "type": "sequence",
                "step_id": "pour",
                "t_start": 30.0,
                "t_end": 36.0,
                "evidence": [],
                "self_corrected": True,
            }
        ],
        "self_corrected": 1,
        "duration_s": 104.0,
        "assisted": False,
    }

    assert task_errors("mrs-k-23", session) == []


def test_a_live_session_with_no_errors_gets_none_invented() -> None:
    """An empty `error_events` is a real answer - nothing went wrong - so no
    placeholder error is spread across a session that had none."""
    session = {
        "resident_id": "mrs-k",
        "session_id": "live-3",
        "ts": "2025-12-31T23:58:16+00:00",
        "task": "make_tea",
        "errors": {},
        "error_events": [],
        "self_corrected": 0,
        "duration_s": 104.0,
        "assisted": True,
    }

    assert task_errors("mrs-k-23", session) == []
