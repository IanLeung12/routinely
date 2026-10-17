"""A live session counts toward the resident it was played for (SPEC section 10, step 4).

The demo's fourth beat: a teammate makes tea on stage, skips the teabag and pours
twice, and by the time the nurse looks at the dashboard that session is one of Mrs.
K's - her sparkline has spiked and her flag and its alert are there. These tests play
the recorded scenarios through `session_messages` (the camera's stand-in and the
demo's fallback) and then ask the API what a dashboard would see.

The shared autouse fixture resets the process-global log around every test.
"""

import asyncio
from typing import Any

from fastapi.testclient import TestClient

from routine_watch import session_log
from routine_watch.api import app
from routine_watch.contracts import ErrorType, Session, TaskError
from routine_watch.demo import DEMO_NOW, DEMO_RESIDENT, demo_residents
from routine_watch.live import scenario_path, session_messages

#: The demo's bad session, a second bad one (a different recording, so a second
#: session rather than the same one twice), and the good one.
BAD = "tea_skip_teabag_pour_twice"
ALSO_BAD = "tea_kettle_twice"
GOOD = "tea_normal"

#: A resident the seeded demo leaves alone, so a flag that appears is this run's.
QUIET_RESIDENT = "mrs-ahmed"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


def play(scenario: str, resident_id: str = DEMO_RESIDENT) -> dict[str, Any]:
    """Play one scenario as `resident_id`'s live session; return its `session_end`."""

    async def session() -> dict[str, Any]:
        messages = session_messages(scenario_path(scenario), speed=FAST, resident_id=resident_id)
        return [message async for message in messages][-1]

    end = asyncio.run(session())
    assert end["type"] == "session_end"
    return end


def resident(resident_id: str) -> dict[str, Any]:
    """One resident's detail, the way the dashboard fetches it."""
    with TestClient(app) as client:
        response = client.get(f"/residents/{resident_id}")
    assert response.status_code == 200
    return response.json()


def overview() -> dict[str, dict[str, Any]]:
    """The unit overview (SPEC section 9, screen 1), by resident id."""
    with TestClient(app) as client:
        response = client.get("/residents")
    assert response.status_code == 200
    return {row["id"]: row for row in response.json()}


def alerts() -> dict[str, dict[str, Any]]:
    """Every current alert, by resident id."""
    with TestClient(app) as client:
        response = client.get("/alerts")
    assert response.status_code == 200
    return {alert["resident_id"]: alert for alert in response.json()}


# ------------------------------------------------- the demo: a live session counts


def test_the_live_session_becomes_one_of_the_residents_sessions() -> None:
    before = len(resident(DEMO_RESIDENT)["sessions"])

    play(BAD)

    sessions = resident(DEMO_RESIDENT)["sessions"]
    assert len(sessions) == before + 1
    newest = sessions[-1]
    assert newest["errors"] == {"omission": 1, "perseveration": 1}
    assert newest["assisted"] is False
    assert newest["duration_s"] > 0
    assert newest["ts"] <= DEMO_NOW.isoformat()  # inside the window the flag is read over


def test_the_live_score_spikes_the_sparkline() -> None:
    play(BAD)

    row = overview()[DEMO_RESIDENT]
    assert row["status"] == "flagged"
    assert row["scores"][-1]["score"] == 5.0  # omission 3.0 + perseveration 2.0
    assert row["scores"][-1]["score"] > resident(DEMO_RESIDENT)["baseline"]["threshold"]


def test_the_alert_counts_the_live_session_and_its_errors() -> None:
    assert DEMO_RESIDENT not in alerts()  # beat 2-3: normal weeks, one watch session

    play(BAD)

    after = alerts()[DEMO_RESIDENT]
    assert len(after["session_ids"]) == 2  # the seeded watch session plus this live one
    assert len(after["errors"]) == 4  # omission + perseveration, in each of the two
    assert after["baseline"]["observed"] == 5.0
    assert after["patterns"][0]["pattern_id"] == "sudden_change"


def test_session_end_points_at_the_residents_alert() -> None:
    end = play(BAD)

    assert end["flag"] is True
    assert end["alert_id"] == f"alert-{DEMO_RESIDENT}"
    with TestClient(app) as client:
        assert client.get(f"/alerts/{end['alert_id']}").status_code == 200


def test_the_websocket_records_the_session_too() -> None:
    """The demo drives this over `/ws/live`, with no resident of its own to name."""
    before = len(resident(DEMO_RESIDENT)["sessions"])

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live?scenario={BAD}&speed={FAST}") as websocket:
            while websocket.receive_json()["type"] != "session_end":
                pass

    assert len(resident(DEMO_RESIDENT)["sessions"]) == before + 1


# ------------------------------------------------------ what must not flag a change


def test_a_good_live_session_is_listed_without_qualifying() -> None:
    sessions_before = len(resident(DEMO_RESIDENT)["sessions"])

    end = play(GOOD)

    assert (end["score"], end["flag"], end["alert_id"]) == (0.0, False, None)
    detail = resident(DEMO_RESIDENT)
    assert len(detail["sessions"]) == sessions_before + 1
    assert detail["sessions"][-1]["errors"] == {}
    # A good session never qualifies, so it never raises a flag on its own.
    assert DEMO_RESIDENT not in alerts()


def test_a_good_live_session_leaves_a_quiet_resident_alone() -> None:
    play(GOOD, QUIET_RESIDENT)

    assert overview()[QUIET_RESIDENT]["status"] == "normal"
    assert QUIET_RESIDENT not in alerts()


def test_a_single_bad_live_session_never_alerts() -> None:
    """SPEC section 7: one session above the threshold is a watch, not a flag."""
    play(BAD, QUIET_RESIDENT)

    assert overview()[QUIET_RESIDENT]["status"] == "watch"
    assert QUIET_RESIDENT not in alerts()


def test_the_second_qualifying_session_flags_a_change() -> None:
    play(BAD, QUIET_RESIDENT)
    play(ALSO_BAD, QUIET_RESIDENT)

    assert overview()[QUIET_RESIDENT]["status"] == "flagged"
    alert = alerts()[QUIET_RESIDENT]
    assert len(alert["session_ids"]) == 2
    assert "diagnos" not in alert["summary"].lower()


def test_live_sessions_never_move_the_resident_s_own_baseline() -> None:
    """The baseline is what this resident is normally like. If the sessions being
    judged raised it, two bad sessions in a row would hide the change they are."""
    before = resident(QUIET_RESIDENT)["baseline"]

    play(BAD, QUIET_RESIDENT)
    play(ALSO_BAD, QUIET_RESIDENT)

    assert resident(QUIET_RESIDENT)["baseline"] == before


def test_an_unfinished_session_is_not_recorded() -> None:
    """The dashboard closing the socket mid-session: nothing to count."""

    async def half() -> None:
        messages = session_messages(scenario_path(BAD), speed=FAST)
        await anext(messages)
        await messages.aclose()

    asyncio.run(half())

    assert session_log.sessions_for(DEMO_RESIDENT) == []


def test_replaying_the_same_recording_is_one_session() -> None:
    play(BAD)
    sessions = len(resident(DEMO_RESIDENT)["sessions"])

    play(BAD)

    assert len(resident(DEMO_RESIDENT)["sessions"]) == sessions


def test_reset_restores_the_seeded_demo() -> None:
    seeded = demo_residents()

    play(BAD)
    assert demo_residents() != seeded

    session_log.reset()
    assert demo_residents() == seeded


# ------------------------------------------------------------------- the log itself


def a_session(session_id: str = "s1", resident_id: str = "someone") -> Session:
    return Session(
        session_id=session_id,
        resident_id=resident_id,
        task_id="make_tea",
        started_at=DEMO_NOW,
        ended_at=DEMO_NOW,
        score=1.0,
    )


def an_error(session_id: str = "s1") -> TaskError:
    return TaskError(
        error_id=f"{session_id}:1",
        session_id=session_id,
        type=ErrorType.OMISSION,
        step_id="teabag_in_cup",
        t_start=1.0,
        t_end=2.0,
        evidence=[],
    )


def test_record_keeps_the_sessions_and_their_errors() -> None:
    session_log.record("mrs-k", a_session("s1"), [an_error("s1")])
    session_log.record("mrs-k", a_session("s2"))

    assert [s.session_id for s in session_log.sessions_for("mrs-k")] == ["s1", "s2"]
    assert [e.error_id for e in session_log.errors_for("s1")] == ["s1:1"]
    assert session_log.errors_for("s2") == []


def test_the_resident_recorded_against_wins() -> None:
    session_log.record("mrs-k", a_session(resident_id="someone-else"))

    assert [s.resident_id for s in session_log.sessions_for("mrs-k")] == ["mrs-k"]
    assert session_log.sessions_for("someone-else") == []


def test_recording_the_same_session_again_replaces_it() -> None:
    session_log.record("mrs-k", a_session("s1"), [an_error("s1")])
    session_log.record("mrs-k", a_session("s1"))

    assert len(session_log.sessions_for("mrs-k")) == 1
    assert session_log.errors_for("s1") == []


def test_an_unknown_resident_has_no_sessions() -> None:
    assert session_log.sessions_for("nobody") == []
    assert session_log.errors_for("no-such-session") == []
