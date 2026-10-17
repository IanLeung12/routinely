"""Direct coverage of the live WebSocket's stream and terminal responses."""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from routine_watch import api_state
from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.monitoring import get_monitoring_store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    api_state.reset()
    get_monitoring_store().reset()
    with TestClient(app) as test_client:
        yield test_client
    api_state.reset()
    get_monitoring_store().reset()


def test_normal_session_sends_events_then_session_end_and_closes(client):
    with client.websocket_connect("/ws/live?scenario=tea_normal&speed=1000000") as websocket:
        messages = []
        with pytest.raises(WebSocketDisconnect) as closed:
            while True:
                messages.append(websocket.receive_json())

    assert closed.value.code == 1000
    assert len(messages) > 1
    assert messages[0]["type"] == "session_start"
    assert any(message["type"] == "frame" for message in messages[:-1])
    assert messages[-1]["type"] == "session_end"
    assert sum(message["type"] == "session_end" for message in messages) == 1


def test_paused_room_sends_only_paused_then_closes(client):
    room = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)
    response = client.put(f"/rooms/{room}/monitoring", json={"on": False})
    assert response.status_code == 200

    with client.websocket_connect("/ws/live?scenario=tea_normal&speed=1000000") as websocket:
        assert websocket.receive_json() == {"type": "paused", "room": room}
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()

    assert closed.value.code == 1000


@pytest.mark.parametrize("scenario", ["does-not-exist", ""])
def test_unknown_scenario_closes_without_events(client, scenario):
    with client.websocket_connect(f"/ws/live?scenario={scenario}") as websocket:
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()

    assert closed.value.code == 4404
