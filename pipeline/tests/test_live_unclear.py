"""An unclear live session is never one of the resident's (SPEC section 12, T342).

Pose and detection are less reliable with walkers, wheelchairs or bad lighting, so a
session too much of which the pipeline could not read is `unclear`
(`routine_watch.quality`) and `replay.score_session` refuses to score or flag it. That
refusal only holds if the session also stays out of the resident's history: `demo`
scores a recorded session from its errors again and only leaves out assisted ones, so
an unclear session recorded anyway would put its errors in the 24-48 h window the flag
is read over and have bad lighting flag a change for review.

The recording here is the demo's bad session written twice at step level, once as
recorded and once with four of its seven steps barely seen. Both classify the *same*
two errors - the teabag omission and the second pour - so the only difference between
them is whether the capture can be trusted, which is exactly the thing under test.

The autouse `_empty_log` fixture (`conftest.py`) resets the process-global session log
around every test.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from routine_watch import api_live, session_log
from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT
from routine_watch.live import scenario_path, session_messages
from routine_watch.replay import load_scenario, session_id_of

#: The demo's bad session (`tests/scenarios/tea_skip_teabag_pour_twice`), step by step:
#: the teabag never goes in and the kettle is poured twice, with a stir in between.
_STEPS: tuple[tuple[str, tuple[str, ...], float, float], ...] = (
    ("fill_kettle", ("kettle",), 1.5, 8.0),
    ("boil", ("kettle",), 9.5, 12.0),
    ("get_cup", ("cup",), 13.5, 17.0),
    ("pour", ("kettle", "cup"), 70.0, 79.0),
    ("stir", ("spoon", "cup"), 81.5, 88.0),
    ("pour", ("kettle", "cup"), 90.0, 96.5),
    ("remove_teabag", ("teabag", "spoon"), 99.0, 104.0),
)

#: Which steps the capture barely saw in the unclear recording: more than
#: `quality.session_quality`'s share of them, and neither of the two the errors are
#: on, so the unclear session still ends on the same errors the clear one does.
_BARELY_SEEN = (0, 1, 2, 6)

#: Another recorded bad session, so a test can add one the resident's history does
#: count without replaying the same recording twice (one session, not two).
ALSO_BAD = "tea_kettle_twice"

#: A resident the seeded demo leaves alone, so a flag that appears is this run's.
QUIET_RESIDENT = "mrs-ahmed"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


def write_scenario(path: Path, session_id: str, *, unclear: Sequence[int] = ()) -> Path:
    """Write `_STEPS` as a scenario of its own at `path`, the steps at `unclear`
    recorded as barely-seen ones (below `recogniser.MIN_STEP_CONFIDENCE`).

    A live session reads only `task` and `history` out of `expected.yaml` - the flag it
    reports is the resident's, not the recording's - so `steps`, `errors` and `flag`
    here are the loader's required minimum rather than assertions.
    """
    path.mkdir(parents=True)
    (path / "steps.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "event_id": f"{session_id}:s{index}",
                    "session_id": session_id,
                    "step_id": step_id,
                    "objects": list(objects),
                    "t_start": t_start,
                    "t_end": t_end,
                    "confidence": 0.4 if index in unclear else 0.93,
                    "source": "rule",
                    "unclear": index in unclear,
                }
            )
            + "\n"
            for index, (step_id, objects, t_start, t_end) in enumerate(_STEPS)
        ),
        encoding="utf-8",
    )
    (path / "expected.yaml").write_text(
        "task: tea\nsteps: [{}]\nerrors: []\nflag: false\n".format(
            ", ".join(step_id for step_id, *_ in _STEPS)
        ),
        encoding="utf-8",
    )
    return path


def play(scenario: Path, resident_id: str) -> dict[str, Any]:
    """Play one scenario directory as `resident_id`'s live session; return
    its `session_end`."""

    async def session() -> dict[str, Any]:
        messages = session_messages(scenario, speed=FAST, resident_id=resident_id)
        return [message async for message in messages][-1]

    end = asyncio.run(session())
    assert end["type"] == "session_end"
    return end


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


def errors_of(session_id: str) -> set[tuple[str, str | None]]:
    """One recorded session's errors, as (type, step) pairs."""
    return {(str(error.type), error.step_id) for error in session_log.errors_for(session_id)}


# ------------------------------------------- an unclear session stays out of history


def test_an_unclear_live_session_is_not_recorded_against_the_resident(tmp_path: Path) -> None:
    before = overview()[QUIET_RESIDENT]
    scenario = write_scenario(tmp_path / "unclear", "unclear-1", unclear=_BARELY_SEEN)

    play(scenario, QUIET_RESIDENT)

    assert session_log.sessions_for(QUIET_RESIDENT) == []
    assert errors_of("unclear-1") == set()
    assert overview()[QUIET_RESIDENT] == before


def test_an_unclear_session_ends_scored_zero_and_unflagged(tmp_path: Path) -> None:
    """What `session_end` says is unchanged: `replay.score_session` already scores an
    unclear session 0.0, and the flag and alert are still the resident's own."""
    scenario = write_scenario(tmp_path / "unclear", "unclear-1", unclear=_BARELY_SEEN)

    end = play(scenario, QUIET_RESIDENT)

    assert (end["score"], end["flag"], end["alert_id"]) == (0.0, False, None)
    # Streaming the session is not the question: its errors were shown to the nurse
    # live, they just say nothing about this resident's own history.
    assert {(error.type.value, error.step_id) for error in end["errors"]} == {
        ("omission", "teabag_in_cup"),
        ("perseveration", "pour"),
    }


def test_an_unclear_session_never_counts_toward_the_flag(tmp_path: Path) -> None:
    """SPEC section 7 flags on two qualifying sessions inside 48 hours. An unclear
    session is not one of them, so one real bad session beside it is still a watch."""
    play(write_scenario(tmp_path / "unclear", "unclear-1", unclear=_BARELY_SEEN), QUIET_RESIDENT)
    play(scenario_path(ALSO_BAD), QUIET_RESIDENT)

    recorded = [session.session_id for session in session_log.sessions_for(QUIET_RESIDENT)]
    assert recorded == [session_id_of(load_scenario(scenario_path(ALSO_BAD)))]
    assert overview()[QUIET_RESIDENT]["status"] == "watch"
    assert QUIET_RESIDENT not in alerts()


# ------------------------------------------------ the same recording, clearly enough


def test_a_clear_live_session_is_still_recorded(tmp_path: Path) -> None:
    scenario = write_scenario(tmp_path / "clear", "clear-1")

    end = play(scenario, QUIET_RESIDENT)

    assert [session.session_id for session in session_log.sessions_for(QUIET_RESIDENT)] == [
        "clear-1"
    ]
    assert errors_of("clear-1") == {("omission", "teabag_in_cup"), ("perseveration", "pour")}
    assert end["score"] == 5.0  # omission 3.0 + perseveration 2.0
    assert overview()[QUIET_RESIDENT]["status"] == "watch"


def test_two_clear_sessions_in_the_window_still_flag(tmp_path: Path) -> None:
    """The control for `test_an_unclear_session_never_counts_toward_the_flag`: the
    same recording, read clearly, is the second qualifying session and does flag."""
    play(write_scenario(tmp_path / "clear", "clear-1"), QUIET_RESIDENT)
    play(scenario_path(ALSO_BAD), QUIET_RESIDENT)

    assert overview()[QUIET_RESIDENT]["status"] == "flagged"
    assert len(alerts()[QUIET_RESIDENT]["session_ids"]) == 2


# -------------------------------------------------------- over the socket the demo uses


def test_the_websocket_does_not_record_an_unclear_session(tmp_path: Path, monkeypatch) -> None:
    """The demo drives this over `/ws/live`, against `demo.DEMO_RESIDENT`, who the
    seeded history leaves on watch: recording this session would flag her.

    `?scenario=` only names a directory under `tests/scenarios`, so the in-test
    recording is reached by pointing `api_live.scenario_path` at this test's root.
    """
    write_scenario(tmp_path / "unclear", "unclear-1", unclear=_BARELY_SEEN)
    monkeypatch.setattr(api_live, "scenario_path", lambda name: scenario_path(name, tmp_path))

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live?scenario=unclear&speed={FAST}") as websocket:
            while websocket.receive_json()["type"] != "session_end":
                pass

    assert session_log.sessions_for(DEMO_RESIDENT) == []
    assert overview()[DEMO_RESIDENT]["status"] == "watch"
