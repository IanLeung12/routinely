"""The monitoring pause switch, over HTTP and on `/ws/live` (SPEC §12, T149).

`GET /monitoring` and `PUT /rooms/{room}/monitoring` expose `routine_watch.monitoring`'s
store to the dashboard; `/ws/live` reads it for `demo.DEMO_RESIDENT`'s room, since every
scenario it plays lands against her (`routine_watch.live`).
"""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.monitoring import get_monitoring_store

#: mrs-k's room (`demo._RESIDENTS`): every `/ws/live` session lands against her.
MRS_K_ROOM = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)

#: Any recorded scenario; which one plays doesn't matter for these tests.
SCENARIO = "tea_normal"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


@pytest.fixture(autouse=True)
def _empty_monitoring_store():
    """Every test starts and ends with every room on."""
    get_monitoring_store().reset()
    yield
    get_monitoring_store().reset()


def test_monitoring_starts_with_no_paused_rooms():
    with TestClient(app) as client:
        response = client.get("/monitoring")

    assert response.status_code == 200
    assert response.json() == {"paused_rooms": []}


def test_pause_then_resume_round_trip():
    with TestClient(app) as client:
        paused = client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
        listed_paused = client.get("/monitoring")
        resumed = client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": True})
        listed_resumed = client.get("/monitoring")

    assert paused.status_code == 200
    assert paused.json() == {"room": MRS_K_ROOM, "on": False}
    assert listed_paused.json() == {"paused_rooms": [MRS_K_ROOM]}
    assert resumed.status_code == 200
    assert resumed.json() == {"room": MRS_K_ROOM, "on": True}
    assert listed_resumed.json() == {"paused_rooms": []}


def test_pausing_an_unknown_room_404s():
    with TestClient(app) as client:
        response = client.put("/rooms/does-not-exist/monitoring", json={"on": False})

    assert response.status_code == 404


def test_live_session_streams_frames_when_not_paused():
    with TestClient(app) as client:
        url = f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        with client.websocket_connect(url) as websocket:
            messages = []
            while True:
                messages.append(websocket.receive_json())
                if messages[-1]["type"] == "session_end":
                    break

    assert any(message["type"] == "frame" for message in messages)
    assert all(message["type"] != "paused" for message in messages)


def test_live_session_is_paused_for_a_room_on_pause():
    with TestClient(app) as client:
        client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
        url = f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        with client.websocket_connect(url) as websocket, pytest.raises(WebSocketDisconnect):
            message = websocket.receive_json()
            websocket.receive_json()

    assert message == {"type": "paused", "room": MRS_K_ROOM}


def test_pausing_a_different_room_does_not_affect_live():
    with TestClient(app) as client:
        other_room = next(r["room"] for r in demo_residents() if r["id"] != DEMO_RESIDENT)
        client.put(f"/rooms/{other_room}/monitoring", json={"on": False})
        url = f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        with client.websocket_connect(url) as websocket:
            first = websocket.receive_json()

    assert first["type"] == "session_start"


def test_pausing_a_room_mid_session_stops_it_and_does_not_record_it():
    with TestClient(app) as client:
        sessions_before = len(client.get(f"/residents/{DEMO_RESIDENT}").json()["sessions"])
        url = f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        with client.websocket_connect(url) as websocket, pytest.raises(WebSocketDisconnect):
            first = websocket.receive_json()
            client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
            messages = [websocket.receive_json()]
            while True:
                messages.append(websocket.receive_json())
        sessions_after = len(client.get(f"/residents/{DEMO_RESIDENT}").json()["sessions"])

    assert first["type"] == "session_start"
    assert messages[-1] == {"type": "paused", "room": MRS_K_ROOM}
    assert all(message["type"] != "session_end" for message in messages)
    assert sessions_after == sessions_before
