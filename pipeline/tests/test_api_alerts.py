import pytest
from fastapi.testclient import TestClient

from routine_watch import api as api_module
from routine_watch.alerts import build_alerts
from routine_watch.api import app
from routine_watch.demo import demo_residents
from routine_watch.feedback import FeedbackStore

MRS_K = "mrs-k"
MRS_K_ALERT = f"alert-{MRS_K}"

#: These tests are all about the alert endpoints, so every test here plays mrs-k's
#: live session first (T124: the seeded demo alone leaves her on watch, not flagged).
pytestmark = pytest.mark.usefixtures("mrs_k_flagged")


@pytest.fixture(autouse=True)
def _reset_feedback_store():
    """Each test gets a clean feedback store: the API module keeps it global."""
    api_module._feedback_store = FeedbackStore()


def test_build_alerts_flags_only_mrs_k():
    alerts = build_alerts(demo_residents())

    assert [alert.resident_id for alert in alerts] == [MRS_K]


def test_alert_summary_never_mentions_diagnosis():
    alerts = build_alerts(demo_residents())

    assert "diagnos" not in alerts[0].summary.lower()


def test_alert_has_at_least_two_sessions_and_errors():
    alerts = build_alerts(demo_residents())

    assert len(alerts[0].session_ids) >= 2
    assert alerts[0].errors
    assert alerts[0].feedback is None


def test_list_alerts_returns_mrs_k_only():
    with TestClient(app) as client:
        response = client.get("/alerts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["resident_id"] == MRS_K
    assert body[0]["feedback"] is None
    assert "diagnos" not in body[0]["summary"].lower()


def test_get_alert_returns_detail():
    with TestClient(app) as client:
        response = client.get(f"/alerts/{MRS_K_ALERT}")

    assert response.status_code == 200
    body = response.json()
    assert body["alert_id"] == MRS_K_ALERT
    assert body["errors"]
    assert body["suggested_checks"]


def test_get_alert_404s_for_unknown_id():
    with TestClient(app) as client:
        response = client.get("/alerts/does-not-exist")

    assert response.status_code == 404


def test_feedback_round_trip_adjusts_threshold():
    with TestClient(app) as client:
        before = client.get(f"/alerts/{MRS_K_ALERT}").json()
        response = client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "false_alarm"})

    assert response.status_code == 200
    body = response.json()
    assert body["feedback"]["verdict"] == "false_alarm"
    assert body["feedback"]["by"]
    assert body["baseline"]["threshold"] > before["baseline"]["threshold"]


def test_reposting_feedback_replaces_the_verdict():
    with TestClient(app) as client:
        client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "false_alarm"})
        response = client.post(
            f"/alerts/{MRS_K_ALERT}/feedback",
            json={"verdict": "confirmed", "note": "checked, nothing unusual"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["feedback"]["verdict"] == "confirmed"
    assert body["feedback"]["note"] == "checked, nothing unusual"


def test_bad_verdict_is_422():
    with TestClient(app) as client:
        response = client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "maybe"})

    assert response.status_code == 422


def test_feedback_on_unknown_alert_404s():
    with TestClient(app) as client:
        response = client.post("/alerts/does-not-exist/feedback", json={"verdict": "confirmed"})

    assert response.status_code == 404
