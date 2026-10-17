"""Pausing a room, end to end: monitoring store, `/handoff`, `/ws/live`, `/demo/reset`.

Pausing mrs-k's room now touches four places built in separate PRs (T149, T251, T252,
T254's neighbours): the monitoring store itself, the shift handoff's per-resident
`monitoring_paused` flag and `paused` list (T251), the live session's `paused` message
(`routine_watch.live`), and `/demo/reset` resuming every room again. One test walks
the whole flow so a regression in any of the four shows up here instead of in four
separate files that each only see their own slice.
"""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.monitoring import get_monitoring_store

#: mrs-k's room (`demo._RESIDENTS`): the room the task asks this test to pause.
MRS_K_ROOM = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)
MRS_K_NAME = next(r["name"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)

#: Any recorded scenario; which one plays doesn't matter for this test.
SCENARIO = "tea_normal"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch):
    """Every test starts and ends with every room on, no feedback and `/demo/reset` reachable."""
    monkeypatch.setenv("DEMO_RESET", "1")
    get_monitoring_store().reset()
    yield
    get_monitoring_store().reset()


def test_pause_flow_end_to_end():
    with TestClient(app) as client:
        paused = client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
        monitoring_after_pause = client.get("/monitoring")
        handoff_after_pause = client.get("/handoff")

        with client.websocket_connect(
            f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        ) as websocket, pytest.raises(WebSocketDisconnect):
            first_live_message = websocket.receive_json()
            websocket.receive_json()

        reset_response = client.post("/demo/reset")
        monitoring_after_reset = client.get("/monitoring")

        with client.websocket_connect(
            f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        ) as websocket:
            first_message_after_reset = websocket.receive_json()
            messages_after_reset = [first_message_after_reset]
            while messages_after_reset[-1]["type"] != "session_end":
                messages_after_reset.append(websocket.receive_json())

    assert paused.status_code == 200
    assert paused.json() == {"room": MRS_K_ROOM, "on": False}

    assert monitoring_after_pause.json() == {"paused_rooms": [MRS_K_ROOM]}

    handoff_body = handoff_after_pause.json()
    assert handoff_body["paused"] == [
        {"room": MRS_K_ROOM, "resident_id": DEMO_RESIDENT, "name": MRS_K_NAME}
    ]
    mrs_k_row = next(
        row for row in handoff_body["residents"] if row["resident_id"] == DEMO_RESIDENT
    )
    assert mrs_k_row["monitoring_paused"] is True

    assert first_live_message == {"type": "paused", "room": MRS_K_ROOM}

    assert reset_response.status_code == 200
    assert reset_response.json() == {"ok": True}
    assert monitoring_after_reset.json() == {"paused_rooms": []}

    assert first_message_after_reset["type"] == "session_start"
