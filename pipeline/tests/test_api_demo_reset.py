"""POST /demo/reset puts the demo back to its seeded history (T144, SPEC §10, §13).

After a rehearsal, mrs-k stays flagged from the live session recorded against her
(`session_log`) plus any nurse feedback logged against her alert (`FeedbackStore`).
This route forgets both, so demo beat 4 can be replayed without restarting the
server - and only answers when the stack is explicitly a demo/dev one, so it can
never be used to wipe a real deployment's state from outside.
"""

import pytest
from fastapi.testclient import TestClient

from routine_watch import api_state
from routine_watch.api import app

MRS_K = "mrs-k"
MRS_K_ALERT = f"alert-{MRS_K}"

pytestmark = pytest.mark.usefixtures("mrs_k_flagged")


@pytest.fixture(autouse=True)
def _reset_feedback_store():
    """Each test gets a clean feedback store: `api_state` keeps it global."""
    api_state.reset()


def _status_of(client: TestClient, resident_id: str) -> str:
    body = client.get("/residents").json()
    return next(resident["status"] for resident in body if resident["id"] == resident_id)


def test_reset_puts_mrs_k_back_to_her_seeded_status(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_RESET", "1")
    with TestClient(app) as client:
        assert _status_of(client, MRS_K) == "flagged"

        response = client.post("/demo/reset")

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert _status_of(client, MRS_K) == "watch"


def test_reset_also_clears_logged_feedback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_RESET", "1")
    with TestClient(app) as client:
        client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "false_alarm"})
        assert api_state._feedback_store.get(MRS_K_ALERT) is not None

        client.post("/demo/reset")

        assert api_state._feedback_store.get(MRS_K_ALERT) is None


def test_reset_also_resumes_paused_room_monitoring(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_RESET", "1")
    with TestClient(app) as client:
        client.put("/rooms/204/monitoring", json={"on": False})
        assert client.get("/monitoring").json()["paused_rooms"] == ["204"]

        client.post("/demo/reset")

        assert client.get("/monitoring").json()["paused_rooms"] == []


def test_reset_is_404_without_offline_mode_or_demo_reset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OFFLINE_MODE", raising=False)
    monkeypatch.delenv("DEMO_RESET", raising=False)
    with TestClient(app) as client:
        response = client.post("/demo/reset")

    assert response.status_code == 404


def test_reset_is_enabled_by_offline_mode_alone(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    monkeypatch.delenv("DEMO_RESET", raising=False)
    with TestClient(app) as client:
        response = client.post("/demo/reset")

    assert response.status_code == 200


def test_reset_rejects_other_demo_reset_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OFFLINE_MODE", raising=False)
    monkeypatch.setenv("DEMO_RESET", "0")
    with TestClient(app) as client:
        response = client.post("/demo/reset")

    assert response.status_code == 404
