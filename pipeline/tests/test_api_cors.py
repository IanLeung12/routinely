from fastapi.testclient import TestClient

from routine_watch.api import app

_DASHBOARD_ORIGIN = "http://localhost:5173"


def test_get_sends_cors_header_for_dashboard_origin() -> None:
    with TestClient(app) as client:
        response = client.get("/residents", headers={"Origin": _DASHBOARD_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _DASHBOARD_ORIGIN


def test_feedback_preflight_succeeds() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/alerts/alert-mrs-k/feedback",
            headers={
                "Origin": _DASHBOARD_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _DASHBOARD_ORIGIN
