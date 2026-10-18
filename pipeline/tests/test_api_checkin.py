"""The safety check-in routes, the push and the server's own countdown (SPEC §18).

The same seven Project KAZE scenarios as `test_checkin.py`, this time over HTTP and
the live WebSocket, plus the three things only the API can be held to:

* the safety PIN and the duress PIN answer with **the same bytes**;
* the countdown is the **server's** - the background tick fires the alarm with nobody
  connected at all (`test_the_background_tick_alarms_with_nobody_connected`);
* a flagged session asks that person to check in, once per alert, and a socket that
  never asked for check-ins still sends only its session.

The clock is the test's (`CheckinStore(clock=...)`), so nothing here waits. Fakes only:
no call, no SMS and no paid API is involved in any of it.
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from routine_watch import api_checkin, api_state
from routine_watch.api import app
from routine_watch.checkin import (
    DEMO_ACK_WINDOW_S,
    DEMO_CHECKIN_WINDOW_S,
    DEMO_DURESS_PIN,
    DEMO_SAFETY_PIN,
    CheckinState,
    CheckinStore,
    use_checkin_store,
)
from routine_watch.monitoring import get_monitoring_store

BASE = datetime(2026, 1, 1, tzinfo=UTC)

#: Mrs. K's supporters, in the order they are alarmed, and what each may see.
FIRST = "nurse-ana"  # location, alert details and replays
SECOND = "care-line"  # the alarm and nothing else

#: The demo's bad session (SPEC §10 beat 4): the one that flags a change for review.
FLAGGING_SCENARIO = "tea_skip_teabag_pour_twice"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


class FakeClock:
    def __init__(self, now: datetime = BASE):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> datetime:
        self.now += timedelta(seconds=seconds)
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def store(clock, tmp_path) -> CheckinStore:
    """The one store the app uses for this test, on the test's clock."""
    store = CheckinStore(clock=clock, directory=tmp_path / "safety")
    use_checkin_store(store)
    yield store
    use_checkin_store(None)


@pytest.fixture
def client(store):
    api_state.reset()
    get_monitoring_store().reset()
    with TestClient(app) as test_client:
        yield test_client
    api_state.reset()
    get_monitoring_store().reset()


def start_checkin(client, person: str = "mrs-k", **body) -> dict:
    """`POST /checkins/demo`, as the demo's "ask me to check in" button does."""
    response = client.post("/checkins/demo", json={"person": person, **body})
    assert response.status_code == 200, response.text
    return response.json()["checkin"]


def seen_by(client, supporter: str) -> list[dict]:
    response = client.get("/checkins/active", params={"supporter": supporter})
    assert response.status_code == 200, response.text
    return response.json()["checkins"]


def seen_by_person(client, person: str) -> list[dict]:
    response = client.get("/checkins/active", params={"person": person})
    assert response.status_code == 200, response.text
    return response.json()["checkins"]


# ------------------------------------------------------------------ 1. safe


def test_a_person_who_checks_in_is_safe(client, clock):
    started = start_checkin(client)
    assert started["state"] == "pending"
    assert started["seconds_left"] == DEMO_CHECKIN_WINDOW_S
    assert seen_by(client, FIRST) == []  # nobody has been woken

    clock.advance(5)
    answered = client.post(
        f"/checkins/{started['checkin_id']}/respond", json={"pin": DEMO_SAFETY_PIN}
    )

    assert answered.status_code == 200
    assert answered.json()["checkin"]["state"] == "ok"
    assert seen_by_person(client, "mrs-k") == []
    assert seen_by(client, FIRST) == []


# ------------------------------------------------- 2. no response -> alarm


def test_no_answer_alarms_the_first_supporter(client, clock):
    started = start_checkin(client)

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = seen_by(client, FIRST)

    assert [one["state"] for one in alarmed] == ["alarm"]
    assert alarmed[0]["checkin_id"] == started["checkin_id"]
    assert alarmed[0]["ask"] == "Is everyone okay?"
    assert alarmed[0]["seconds_left"] == DEMO_ACK_WINDOW_S
    assert seen_by(client, SECOND) == []  # not their turn yet
    # The person's own screen still shows the question that ran out.
    assert seen_by_person(client, "mrs-k")[0]["state"] == "alarm"


# --------------------------------------------------------------- 3. duress


def test_the_duress_and_safety_answers_are_byte_identical(client, store):
    """Same check-in, same clock, two PINs: the person's device cannot tell them
    apart, because the two answers are the same bytes (SPEC §18)."""
    safely = start_checkin(client)
    safe_answer = client.post(
        f"/checkins/{safely['checkin_id']}/respond", json={"pin": DEMO_SAFETY_PIN}
    )

    store.reset()  # the clock has not moved, so the next check-in has the same id
    coerced = start_checkin(client)
    duress_answer = client.post(
        f"/checkins/{coerced['checkin_id']}/respond", json={"pin": DEMO_DURESS_PIN}
    )

    assert coerced["checkin_id"] == safely["checkin_id"]
    assert duress_answer.status_code == safe_answer.status_code == 200
    assert duress_answer.content == safe_answer.content
    assert b"duress" not in duress_answer.content


def test_a_duress_alarm_reaches_the_supporter_and_not_the_person_screen(client):
    started = start_checkin(client)

    client.post(f"/checkins/{started['checkin_id']}/respond", json={"pin": DEMO_DURESS_PIN})

    alarmed = seen_by(client, FIRST)
    assert [one["state"] for one in alarmed] == ["alarm"]
    assert alarmed[0]["duress"] is True
    assert alarmed[0]["silent"] is True
    # Their own screen says the check-in is over, exactly as if they had cancelled it.
    assert seen_by_person(client, "mrs-k") == []


# ----------------------------------------- 4. the device drops off the net


def test_a_disconnected_device_still_alarms(client, clock):
    """KAZE's connectivity failure: the countdown is the server's."""
    started = start_checkin(client)

    clock.advance(3)
    simulated = client.post(
        f"/checkins/{started['checkin_id']}/simulate", json={"event": "disconnect"}
    )
    assert simulated.status_code == 200
    assert simulated.json()["checkin"]["device_online"] is False
    assert simulated.json()["checkin"]["deadline"] == started["deadline"]

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = seen_by(client, FIRST)

    assert [one["state"] for one in alarmed] == ["alarm"]
    assert alarmed[0]["device_online"] is False


# ------------------------------------------------------------ 5. escalation


def test_an_unacknowledged_alarm_escalates_then_a_supporter_takes_it(client, clock):
    started = start_checkin(client)

    clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S)
    escalated = seen_by(client, SECOND)
    assert [one["state"] for one in escalated] == ["escalated"]
    assert escalated[0]["supporter"] == SECOND
    assert seen_by(client, FIRST)[0]["notified"] == [FIRST, SECOND]

    taken = client.post(f"/checkins/{started['checkin_id']}/ack", json={"supporter": SECOND})

    assert taken.status_code == 200
    assert taken.json()["checkin"]["state"] == "acknowledged"
    assert taken.json()["checkin"]["acknowledged_by"] == SECOND
    assert taken.json()["checkin"]["seconds_left"] is None

    clock.advance(DEMO_ACK_WINDOW_S * 10)
    assert seen_by(client, SECOND)[0]["state"] == "acknowledged"  # no further escalation


def test_a_supporter_who_is_not_on_the_list_cannot_acknowledge(client, clock):
    started = start_checkin(client)
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    refused = client.post(f"/checkins/{started['checkin_id']}/ack", json={"supporter": "lena"})

    assert refused.status_code == 404
    assert seen_by(client, FIRST)[0]["state"] == "alarm"


def test_a_pending_checkin_cannot_be_acknowledged(client):
    started = start_checkin(client)

    refused = client.post(f"/checkins/{started['checkin_id']}/ack", json={"supporter": FIRST})

    assert refused.status_code == 409


# ---------------------------------------------------------- 6. false alarm


def test_a_false_alarm_resolved_by_a_supporter(client, clock):
    started = start_checkin(client)
    clock.advance(DEMO_CHECKIN_WINDOW_S)
    client.post(f"/checkins/{started['checkin_id']}/ack", json={"supporter": FIRST})

    clock.advance(20)
    closed = client.post(
        f"/checkins/{started['checkin_id']}/resolve",
        json={"by": FIRST, "reason": "false_alarm"},
    )

    assert closed.status_code == 200
    assert closed.json()["checkin"]["state"] == "resolved"
    assert closed.json()["checkin"]["resolved_by"] == FIRST
    assert closed.json()["checkin"]["resolved_reason"] == "false_alarm"
    assert seen_by(client, FIRST) == []
    assert seen_by_person(client, "mrs-k") == []


def test_a_false_alarm_resolved_by_the_person(client, clock):
    started = start_checkin(client)
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    closed = client.post(
        f"/checkins/{started['checkin_id']}/resolve",
        json={"by": "person", "reason": "false_alarm"},
    )

    assert closed.status_code == 200
    assert closed.json()["checkin"] == {
        "checkin_id": started["checkin_id"],
        "person_id": "mrs-k",
        "state": "resolved",
        "ask": started["ask"],
        "started_at": started["started_at"],
        "deadline": None,
        "seconds_left": None,
        "device_online": True,
        "resolved_reason": "false_alarm",
    }
    assert seen_by(client, FIRST) == []

    again = client.post(
        f"/checkins/{started['checkin_id']}/resolve", json={"by": FIRST, "reason": "helped"}
    )
    assert again.status_code == 409  # the first answer stands


def test_an_unknown_checkin_is_a_404(client):
    for route, body in (
        ("respond", {"pin": DEMO_SAFETY_PIN}),
        ("ack", {"supporter": FIRST}),
        ("resolve", {"by": "person", "reason": "other"}),
        ("simulate", {"event": "disconnect"}),
    ):
        response = client.post(f"/checkins/checkin-nobody/{route}", json=body)
        assert response.status_code == 404, route


# --------------------------------------------------------- 7. permissions


def test_a_supporter_without_location_never_gets_it(client, clock):
    start_checkin(client, alert_id="alert-mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S)

    allowed = seen_by(client, FIRST)[0]
    not_allowed = seen_by(client, SECOND)[0]

    assert allowed["location"] == "Room 204, care home"
    assert allowed["alert_id"] == "alert-mrs-k"
    assert allowed["replays_url"] == "/people/mrs-k/replays"
    assert "location" not in not_allowed
    assert "alert_id" not in not_allowed
    assert "events" not in not_allowed
    assert "replays_url" not in not_allowed
    response = client.get("/checkins/active", params={"supporter": SECOND})
    assert "Room 204" not in response.text


def test_a_supporter_only_sees_the_check_ins_that_reached_them(client, clock):
    """Being on somebody's list is not watching them: a supporter is shown an alarm
    once it is theirs (SPEC §18)."""
    start_checkin(client, person="mr-d")

    assert seen_by(client, "lena") == []

    clock.advance(DEMO_CHECKIN_WINDOW_S)

    assert [one["person_id"] for one in seen_by(client, "lena")] == ["mr-d"]
    assert seen_by(client, FIRST) == []  # Mrs. K's nurse hears nothing about Mr. D
    assert seen_by(client, "nobody-at-all") == []


def test_the_audience_must_be_one_of_the_two(client):
    assert client.get("/checkins/active").status_code == 422
    both = client.get("/checkins/active", params={"person": "mrs-k", "supporter": FIRST})
    assert both.status_code == 422
    assert client.get("/checkins/active", params={"person": "nobody"}).status_code == 404


# --------------------------------------------------------- PINs and settings


def test_a_wrong_pin_is_a_401_and_the_countdown_carries_on(client, clock):
    started = start_checkin(client)

    clock.advance(2)
    refused = client.post(f"/checkins/{started['checkin_id']}/respond", json={"pin": "0000"})

    assert refused.status_code == 401
    assert seen_by_person(client, "mrs-k")[0]["state"] == "pending"

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    assert [one["state"] for one in seen_by(client, FIRST)] == ["alarm"]


def test_pins_never_appear_in_a_response_or_a_log(client, store, caplog):
    caplog.set_level(logging.DEBUG)
    changed = client.put(
        "/people/mrs-k/safety", json={"safety_pin": "8426", "duress_pin": "1357"}
    )
    assert changed.status_code == 200

    started = start_checkin(client)
    answered = client.post(f"/checkins/{started['checkin_id']}/respond", json={"pin": "1357"})
    refused = client.post(f"/checkins/{started['checkin_id']}/respond", json={"pin": "9999"})
    bodies = "".join(
        [
            changed.text,
            client.get("/people/mrs-k/safety").text,
            started["checkin_id"],
            answered.text,
            refused.text,
            client.get("/checkins/active", params={"supporter": FIRST}).text,
        ]
    )

    for pin in ("8426", "1357", "9999", DEMO_SAFETY_PIN, DEMO_DURESS_PIN):
        assert pin not in bodies
        assert pin not in caplog.text
    assert "hash" not in bodies and "salt" not in bodies
    assert (store.directory / "mrs-k.json").read_text(encoding="utf-8").count("8426") == 0


def test_the_settings_route_shows_everything_but_the_pins(client):
    settings = client.get("/people/mrs-k/safety").json()

    assert settings["checkin_window_s"] == DEMO_CHECKIN_WINDOW_S
    assert settings["ack_window_s"] == DEMO_ACK_WINDOW_S
    assert settings["location_simulated"] is True
    assert [one["id"] for one in settings["supporters"]] == [FIRST, SECOND]
    assert settings["supporters"][1]["share"] == {
        "location": False,
        "alert_details": False,
        "replay": False,
    }
    assert settings == {**settings, "safety_pin_set": True, "duress_pin_set": True}
    assert "safety_pin" not in settings
    assert client.get("/people/nobody/safety").status_code == 404


def test_settings_can_be_changed_and_are_used_by_the_next_check_in(client, clock):
    changed = client.put(
        "/people/sam/safety",
        json={
            "checkin_window_s": 60.0,
            "ack_window_s": 30.0,
            "location": "Flat 3, by the park",
            "supporters": [
                {
                    "id": "lena",
                    "name": "Lena",
                    "relationship": "family",
                    "share": {"location": True, "alert_details": False, "replay": False},
                }
            ],
        },
    )

    assert changed.status_code == 200, changed.text
    started = start_checkin(client, person="sam")
    assert started["seconds_left"] == 60.0

    clock.advance(60)
    alarmed = seen_by(client, "lena")
    assert [one["state"] for one in alarmed] == ["alarm"]
    assert alarmed[0]["location"] == "Flat 3, by the park"
    assert alarmed[0]["seconds_left"] == 30.0


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"safety_pin": "555"}, id="too-short"),
        pytest.param({"safety_pin": "5555555555555"}, id="too-long"),
        pytest.param({"safety_pin": "55 55"}, id="has-a-space"),
        pytest.param({"safety_pin": "5555", "duress_pin": "5555"}, id="the-same-twice"),
    ],
)
def test_a_pin_a_person_could_not_use_is_refused_without_quoting_it(client, body):
    response = client.put("/people/mrs-k/safety", json=body)

    assert response.status_code == 422
    for pin in body.values():
        assert pin not in response.text


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"checkin_window_s": 0.5}, id="window-too-short"),
        pytest.param({"ack_window_s": 999_999}, id="window-too-long"),
        pytest.param({"supporters": [{"id": "a", "name": "A"}, {"id": "a", "name": "A"}]},
                     id="same-supporter-twice"),
        pytest.param({"unknown_field": 1}, id="unknown-field"),
    ],
)
def test_settings_that_make_no_sense_are_refused(client, body):
    assert client.put("/people/mrs-k/safety", json=body).status_code == 422


# ------------------------------------------- the server owns the countdown


def test_the_background_tick_alarms_with_nobody_connected(store, clock):
    """No route is called and no socket is open: the tick itself fires the alarm and
    pushes it to the supporter's feed (SPEC §18, KAZE's connectivity failure)."""
    started = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    async def watch() -> dict:
        subscriber = api_checkin.subscribe(supporter=FIRST)
        ticker = asyncio.create_task(api_checkin.tick_forever(0.01))
        try:
            return await asyncio.wait_for(subscriber.get(), timeout=10)
        finally:
            ticker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ticker
            api_checkin.release(subscriber)

    pushed = asyncio.run(watch())

    assert pushed["type"] == "checkin"
    assert pushed["checkin"]["checkin_id"] == started.checkin_id
    assert pushed["checkin"]["state"] == "alarm"
    assert pushed["checkin"]["for_supporter"] == FIRST


def test_the_app_runs_the_tick_for_as_long_as_it_is_up(store, clock):
    """`api.lifespan` owns the ticker: it is running inside the client's lifetime and
    stopped after it, so a test client leaves nothing counting behind it."""
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        running = [
            task
            for task in asyncio.all_tasks(client.portal.call(asyncio.get_running_loop))
            if "tick_forever" in repr(task)
        ]
        assert running, "no check-in tick is running"
        assert not any(task.done() for task in running)


# ----------------------------------------------------- the push and the hook


def test_the_live_socket_pushes_a_persons_own_check_in(client, clock):
    with client.websocket_connect("/ws/live?source=checkins&checkin_person=mrs-k") as socket:
        started = start_checkin(client)
        asked = socket.receive_json()

        client.post(f"/checkins/{started['checkin_id']}/respond", json={"pin": DEMO_SAFETY_PIN})
        answered = socket.receive_json()

    assert asked == {"type": "checkin", "checkin": started}
    assert answered["type"] == "checkin"
    assert answered["checkin"]["state"] == "ok"


def test_the_live_socket_pushes_a_supporter_the_alarm_that_reached_them(client, clock):
    """A supporter's socket is quiet until the alarm is theirs: the question the
    person was asked is never pushed to them, so the first thing they hear is the
    alarm itself (SPEC §18)."""
    with client.websocket_connect(
        f"/ws/live?source=checkins&checkin_supporter={FIRST}"
    ) as socket:
        started = start_checkin(client)  # pending: not this supporter's business yet
        clock.advance(DEMO_CHECKIN_WINDOW_S)
        client.post(f"/checkins/{started['checkin_id']}/simulate", json={"event": "disconnect"})
        pushed = socket.receive_json()

    assert pushed["type"] == "checkin"
    assert pushed["checkin"]["state"] == "alarm"
    assert pushed["checkin"]["for_supporter"] == FIRST
    assert pushed["checkin"]["device_online"] is False
    assert pushed["checkin"]["location"] == "Room 204, care home"


def test_an_escalation_reaches_the_next_supporter_on_the_socket(client, clock):
    with client.websocket_connect(
        f"/ws/live?source=checkins&checkin_supporter={SECOND}"
    ) as socket:
        started = start_checkin(client)
        clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S)
        client.post(f"/checkins/{started['checkin_id']}/simulate", json={"event": "disconnect"})
        pushed = socket.receive_json()

    assert pushed["checkin"]["state"] == "escalated"
    assert pushed["checkin"]["for_supporter"] == SECOND
    assert "location" not in pushed["checkin"]  # the care line was never shown it


def test_a_socket_must_say_whose_check_ins_it_is_watching(client):
    for url in (
        "/ws/live?source=checkins",
        f"/ws/live?source=checkins&checkin_person=mrs-k&checkin_supporter={FIRST}",
        f"/ws/live?scenario=tea_normal&checkin_person=mrs-k&checkin_supporter={FIRST}",
    ):
        with client.websocket_connect(url) as socket:
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
        assert closed.value.code == api_checkin.CHECKIN_AUDIENCE, url


def test_a_flagged_session_asks_the_person_to_check_in(client, store):
    """The hook from an alert to a check-in (SPEC §18): a session that flags a change
    asks that person to check in, and the same alert never asks twice."""
    messages = play(client, f"/ws/live?scenario={FLAGGING_SCENARIO}&speed={FAST}")
    end = messages[-1]
    assert end["type"] == "session_end"
    assert end["flag"] is True

    asked = store.checkin_for_alert(end["alert_id"])
    assert asked is not None
    assert asked.person_id == "mrs-k"
    assert asked.state is CheckinState.PENDING
    assert seen_by_person(client, "mrs-k")[0]["checkin_id"] == asked.checkin_id

    play(client, f"/ws/live?scenario={FLAGGING_SCENARIO}&speed={FAST}")

    assert [one.checkin_id for one in store.active()] == [asked.checkin_id]


def test_a_session_that_flags_pushes_the_check_in_on_the_same_socket(client, store):
    url = f"/ws/live?scenario={FLAGGING_SCENARIO}&speed={FAST}&checkin_person=mrs-k"
    with client.websocket_connect(url) as socket:
        kinds = []
        while True:
            message = socket.receive_json()
            kinds.append(message["type"])
            if message["type"] == "checkin":
                break

    assert kinds[-2:] == ["session_end", "checkin"]  # never in front of the session's end
    assert message["checkin"]["state"] == "pending"
    assert message["checkin"]["ask"] == "Can you check in?"


def test_a_socket_that_asks_for_nothing_sends_only_its_session(client, store):
    """Every client that existed before check-ins did: same messages, same order, and
    the socket still closes when the session ends (`test_live_contract.py`)."""
    messages = play(client, f"/ws/live?scenario={FLAGGING_SCENARIO}&speed={FAST}")

    assert "checkin" not in {message["type"] for message in messages}
    assert messages[-1]["type"] == "session_end"
    assert store.active()  # the hook still ran


def test_demo_reset_forgets_every_check_in(client, store, monkeypatch):
    monkeypatch.setenv("DEMO_RESET", "1")
    started = start_checkin(client, alert_id="alert-mrs-k")

    assert client.post("/demo/reset").json() == {"ok": True}

    assert store.active() == []
    assert store.checkin_for_alert("alert-mrs-k") is None
    assert seen_by_person(client, "mrs-k") == []
    forgotten = client.post(
        f"/checkins/{started['checkin_id']}/respond", json={"pin": DEMO_SAFETY_PIN}
    )
    assert forgotten.status_code == 404


def play(client, url: str) -> list[dict]:
    """Every message one live session sends, up to and including `session_end`."""
    with client.websocket_connect(url) as socket:
        messages = []
        while True:
            messages.append(socket.receive_json())
            if messages[-1]["type"] == "session_end":
                return messages
