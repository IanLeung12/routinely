"""The monitoring audit trail: who paused or resumed a room, and when (SPEC §12, T262).

Pausing a camera has to be accountable rather than silent, so every change to the
switch is logged against the room: `MonitoringStore.history` keeps it, the API serves
it at `GET /rooms/{room}/monitoring/history` for the resident screen, and
`/demo/reset` empties it with the rest of the demo's state.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.monitoring import (
    DEFAULT_BY,
    MAX_HISTORY,
    MonitoringStore,
    get_monitoring_store,
)

#: mrs-k's room (`demo._RESIDENTS`): the room the demo pauses.
MRS_K_ROOM = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)

#: Another resident's room, so the per-room trails can be told apart.
OTHER_ROOM = next(r["room"] for r in demo_residents() if r["id"] != DEMO_RESIDENT)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch):
    """Every test starts and ends with every room on, nothing logged, and
    `/demo/reset` reachable (it 404s outside a demo/dev stack)."""
    monkeypatch.setenv("DEMO_RESET", "1")
    get_monitoring_store().reset()
    yield
    get_monitoring_store().reset()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def at(minute: int) -> datetime:
    """A fixed timestamp, so the logged times are the test's and not the clock's."""
    return datetime(2026, 10, 17, 9, minute, tzinfo=UTC)


# --- the store ---------------------------------------------------------------


def test_a_room_nobody_has_touched_has_no_history():
    assert MonitoringStore().history(MRS_K_ROOM) == []


def test_pause_then_resume_is_logged_newest_first():
    store = MonitoringStore()

    store.set(MRS_K_ROOM, False, by="nurse-amy", at=at(10))
    store.set(MRS_K_ROOM, True, by="nurse-bo", at=at(25))

    assert store.history(MRS_K_ROOM) == [
        {"on": True, "by": "nurse-bo", "at": at(25).isoformat()},
        {"on": False, "by": "nurse-amy", "at": at(10).isoformat()},
    ]


def test_a_change_defaults_to_the_anonymous_nurse_and_now():
    store = MonitoringStore()
    before = datetime.now(UTC)

    store.set(MRS_K_ROOM, False)

    change = store.history(MRS_K_ROOM)[0]
    assert change["by"] == DEFAULT_BY
    assert before <= datetime.fromisoformat(change["at"]) <= datetime.now(UTC)


def test_each_room_keeps_its_own_trail():
    store = MonitoringStore()

    store.set(MRS_K_ROOM, False, at=at(10))
    store.set(OTHER_ROOM, False, at=at(11))

    assert [change["at"] for change in store.history(MRS_K_ROOM)] == [at(10).isoformat()]
    assert [change["at"] for change in store.history(OTHER_ROOM)] == [at(11).isoformat()]


def test_a_tap_that_changes_nothing_is_not_logged():
    """A second pause on an already-paused room isn't a second pause to answer for."""
    store = MonitoringStore()

    store.set(MRS_K_ROOM, True, at=at(1))
    store.set(MRS_K_ROOM, False, at=at(2))
    store.set(MRS_K_ROOM, False, at=at(3))

    assert [change["at"] for change in store.history(MRS_K_ROOM)] == [at(2).isoformat()]


def test_the_trail_keeps_the_newest_changes_only():
    store = MonitoringStore()
    for minute in range(MAX_HISTORY + 4):
        store.set(MRS_K_ROOM, minute % 2 == 0, at=at(minute))

    history = store.history(MRS_K_ROOM)

    assert len(history) == MAX_HISTORY
    assert history[0]["at"] == at(MAX_HISTORY + 3).isoformat()
    assert history[-1]["at"] == at(4).isoformat()


def test_reading_the_trail_cannot_edit_it():
    store = MonitoringStore()
    store.set(MRS_K_ROOM, False, at=at(10))

    store.history(MRS_K_ROOM)[0]["by"] = "somebody else"

    assert store.history(MRS_K_ROOM)[0]["by"] == DEFAULT_BY


def test_reset_clears_the_trail_with_the_pauses():
    store = MonitoringStore()
    store.set(MRS_K_ROOM, False, at=at(10))

    store.reset()

    assert store.history(MRS_K_ROOM) == []
    assert store.paused_rooms() == []


# --- the API -----------------------------------------------------------------


def test_history_is_empty_before_anybody_touches_the_switch(client: TestClient):
    response = client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history")

    assert response.status_code == 200
    assert response.json() == {"room": MRS_K_ROOM, "history": []}


def test_history_lists_a_pause_then_a_resume_newest_first(client: TestClient):
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False, "by": "nurse-amy"})
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": True})

    history = client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()["history"]

    assert [(change["on"], change["by"]) for change in history] == [
        (True, DEFAULT_BY),
        (False, "nurse-amy"),
    ]
    assert datetime.fromisoformat(history[0]["at"]) >= datetime.fromisoformat(history[1]["at"])


def test_pausing_one_room_leaves_another_rooms_history_empty(client: TestClient):
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})

    assert client.get(f"/rooms/{OTHER_ROOM}/monitoring/history").json()["history"] == []


def test_the_api_serves_at_most_max_history_changes(client: TestClient):
    for index in range(MAX_HISTORY + 4):
        client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": index % 2 == 0})

    history = client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()["history"]

    assert len(history) == MAX_HISTORY


def test_a_blank_by_is_rejected_rather_than_logged_as_nobody(client: TestClient):
    response = client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False, "by": ""})

    assert response.status_code == 422
    assert client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()["history"] == []


def test_history_404s_for_an_unknown_room(client: TestClient):
    response = client.get("/rooms/does-not-exist/monitoring/history")

    assert response.status_code == 404


def test_demo_reset_clears_the_trail(client: TestClient):
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False, "by": "nurse-amy"})
    paused_history = client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()["history"]

    reset = client.post("/demo/reset")

    assert reset.status_code == 200
    assert len(paused_history) == 1
    assert client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()["history"] == []
    assert client.get("/monitoring").json() == {"paused_rooms": []}
