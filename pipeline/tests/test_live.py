"""The live session, end to end over the WebSocket (SPEC section 16 decision B).

The three acceptance cases are the demo's: the bad session flashes red and amber while
it is still running and flags at the end, the good session never does, and a scenario
that is not there closes the socket rather than hanging the dashboard. Everything runs
at `FAST`, so a two-minute recording takes milliseconds and the suite has no clock of
its own to be flaky about.
"""

import asyncio
import re
from collections import Counter
from dataclasses import replace
from itertools import pairwise
from pathlib import Path
from typing import Any, get_args

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from routine_watch import live
from routine_watch.api import app
from routine_watch.contracts import (
    CaptureFrame,
    CaptureSource,
    StepEvent,
    StepSource,
    TaskError,
    repo_root,
)
from routine_watch.errors import classify_errors
from routine_watch.live import (
    MAX_FRAME_FPS,
    SCENARIO_NOT_FOUND,
    StepState,
    scenario_path,
    session_messages,
    step_states,
)
from routine_watch.replay import ReplayError, load_scenario, run, scenario_dirs, session_id_of
from routine_watch.tasks import load_task

#: The demo's bad session, the good one, and the one written as capture frames.
BAD = "tea_skip_teabag_pour_twice"
GOOD = "tea_normal"
FRAMES = "tea_no_kettle"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


def test_session_messages_rejects_an_empty_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    path = scenario_path(GOOD)
    scenario = replace(load_scenario(path), frames=(), events=())
    monkeypatch.setattr(live, "load_scenario", lambda _: scenario)

    async def first() -> dict[str, Any]:
        return await anext(session_messages(path, speed=FAST))

    with pytest.raises(ReplayError, match="no frames or events"):
        asyncio.run(first())

#: The dashboard's task map, whose states `live.StepState` has to match.
TASK_MAP = repo_root() / "web" / "src" / "live" / "TaskMap.tsx"

#: A policy violation: how FastAPI turns down a request with an impossible `?speed=`.
WS_POLICY_VIOLATION = 1008


def live_session(scenario: str, speed: float = FAST) -> list[dict[str, Any]]:
    """Every message of one live session, as JSON, the way the dashboard receives it."""
    with TestClient(app) as client:
        url = f"/ws/live?scenario={scenario}&speed={speed}"
        with client.websocket_connect(url) as websocket:
            messages = []
            while True:
                messages.append(websocket.receive_json())
                if messages[-1]["type"] == "session_end":
                    return messages


def played(scenario_dir: Path, speed: float = FAST) -> list[dict[str, Any]]:
    """Every message of one live session as the generator yields it, contracts and all."""

    async def collect() -> list[dict[str, Any]]:
        return [message async for message in session_messages(scenario_dir, speed=speed)]

    return asyncio.run(collect())


def of_type(messages: list[dict[str, Any]], type_: str) -> list[dict[str, Any]]:
    return [message for message in messages if message["type"] == type_]


def reported(messages: list[dict[str, Any]]) -> list[tuple[str, str | None]]:
    """The errors sent, as (type, step), in the order a nurse would see them."""
    return [(m["error"]["type"], m["error"]["step_id"]) for m in of_type(messages, "error")]


def frame(seq: int, t: float) -> CaptureFrame:
    """A capture record with nothing in it: these tests only look at its timing."""
    return CaptureFrame(
        session_id="live-1", seq=seq, t=t, source=CaptureSource.SYNTHETIC,
        poses=[], hands=[], objects=[],
    )


# ------------------------------------------------------------------- the demo session


def test_bad_session_reports_an_omission_and_a_repeat() -> None:
    messages = live_session(BAD)

    assert reported(messages) == [("omission", "teabag_in_cup"), ("perseveration", "pour")]


def test_bad_session_task_map_goes_red_and_amber() -> None:
    states = of_type(live_session(BAD), "step_state")[-1]["states"]

    assert states["teabag_in_cup"] == "omission"
    assert states["pour"] == "repeat"
    assert states["fill_kettle"] == "done"


def test_bad_session_flags_a_change_for_review() -> None:
    end = live_session(BAD)[-1]

    assert end["flag"] is True
    assert end["score"] == 5.0  # omission 3.0 + perseveration 2.0
    assert end["alert_id"]


def test_errors_arrive_while_the_session_is_still_running() -> None:
    """The point of classifying incrementally: the map flashes mid-session, not after."""
    kinds = [message["type"] for message in live_session(BAD)]
    last_step = max(index for index, kind in enumerate(kinds) if kind == "step")

    assert kinds.index("error") < last_step


def test_session_starts_with_the_task_graph() -> None:
    """The first message tells the client what task is being watched and what its
    steps are, so the dashboard draws the map the session actually ran, not tea by
    default (SPEC section 10)."""
    scenario = load_scenario(scenario_path("tea_abandoned"))
    messages = played(scenario_path("tea_abandoned"))

    assert messages[0] == {
        "type": "session_start",
        "session_id": session_id_of(scenario),
        "task_id": scenario.graph.id,
        "steps": [
            {"id": step.id, "label": step.label, "optional": step.optional}
            for step in scenario.graph.steps
        ],
    }
    assert [step["id"] for step in messages[0]["steps"]] == list(scenario.graph.step_ids)


def test_the_map_starts_out_all_pending() -> None:
    first = of_type(live_session(BAD), "step_state")[0]

    assert set(first["states"]) == set(load_task("tea").step_ids)
    assert set(first["states"].values()) == {"pending"}


def test_normal_session_reports_nothing() -> None:
    messages = live_session(GOOD)
    states = of_type(messages, "step_state")[-1]["states"]
    end = messages[-1]

    assert reported(messages) == []
    assert states.pop("sugar") == "pending"  # optional and skipped: not an omission
    assert set(states.values()) == {"done"}
    assert (end["score"], end["flag"], end["alert_id"]) == (0.0, False, None)


@pytest.mark.parametrize("scenario", ["", "nope", "../../pipeline/src", "Tea_Normal"])
def test_unknown_scenario_closes_4404(scenario: str) -> None:
    with TestClient(app) as client, pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/live?scenario={scenario}") as websocket:
            websocket.receive_json()

    assert closed.value.code == SCENARIO_NOT_FOUND


def test_socket_closes_when_the_session_ends() -> None:
    with TestClient(app) as client, pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/live?scenario={GOOD}&speed={FAST}") as websocket:
            while websocket.receive_json()["type"] != "session_end":
                pass
            websocket.receive_json()

    assert closed.value.code == 1000


# --------------------------------------------------------------------------- frames


def test_frames_scenario_sends_skeleton_frames() -> None:
    messages = live_session(FRAMES)
    frames = [CaptureFrame.model_validate(m["frame"]) for m in of_type(messages, "frame")]
    gaps = [later.t - earlier.t for earlier, later in pairwise(frames)]

    assert [f.seq for f in frames] == sorted(f.seq for f in frames)
    assert min(gaps) >= 1.0 / MAX_FRAME_FPS - 1e-9
    assert reported(messages) == [("omission", "boil"), ("omission", "fill_kettle")]


def test_step_scenario_sends_no_frames() -> None:
    """A scenario written at step level has no frames to send, so it sends none."""
    assert of_type(live_session(BAD), "frame") == []


@pytest.mark.parametrize(
    ("fps", "kept"),
    [(30.0, 30), (MAX_FRAME_FPS, 30), (2.0, 6)],  # 3 s at 30 fps, 10 fps, 2 fps
)
def test_frames_are_capped_at_ten_per_second(fps: float, kept: int) -> None:
    recorded = [frame(seq, seq / fps) for seq in range(int(3 * fps))]

    sent = live._downsampled(recorded)

    assert len(sent) == kept
    assert sent[0] is recorded[0]


def test_every_message_is_a_contract() -> None:
    """Contracts forbid unknown fields, so validating is also the privacy check: a
    message cannot carry an image or a clip (SPEC section 8, `test_contracts.py`)."""
    messages = live_session(FRAMES)

    for message in of_type(messages, "frame"):
        CaptureFrame.model_validate(message["frame"])
    for message in of_type(messages, "step"):
        StepEvent.model_validate(message["event"])
    for message in of_type(messages, "error"):
        TaskError.model_validate(message["error"])
    assert {m["type"] for m in messages} <= {
        "session_start", "frame", "step", "step_state", "error", "session_end"
    }


# ------------------------------------------------------- the pipeline, and the clock


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_live_session_says_what_the_replay_says(path: Path) -> None:
    """A live replay and `scripts/e2e.sh` must never disagree about a recording: same
    steps, same errors at the end, same score and the same flag."""
    scenario = load_scenario(path)
    messages = played(path)
    result = run(scenario)

    assert [m["event"].step_id for m in of_type(messages, "step")] == list(
        scenario.expected.steps
    )
    sent = Counter((m["error"].type, m["error"].step_id) for m in of_type(messages, "error"))
    assert sent >= Counter((e["type"], e["step"]) for e in result["errors"])
    assert messages[-1]["score"] == result["score"]
    assert messages[-1]["flag"] == result["flag"]


def test_each_error_is_sent_once() -> None:
    """Classifying every few seconds finds the same error again and again (its id is
    stable on purpose); the client hears about it once."""
    ids = [m["error"].error_id for m in of_type(played(scenario_path(BAD)), "error")]

    assert len(ids) == len(set(ids))


def test_a_step_that_turns_out_not_to_be_missing_goes_back_to_done() -> None:
    """A step done out of order reports its dependency missing, then reports the step
    itself as a sequence error once the dependency lands. The error messages keep both;
    the map heals."""
    graph = load_task("tea")
    events = [
        StepEvent(
            event_id=f"out-of-order:s{index}",
            session_id="out-of-order",
            step_id=step_id,
            objects=list(graph.step(step_id).objects),
            t_start=float(index * 60),
            t_end=float(index * 60 + 5),
            confidence=0.9,
            source=StepSource.RULE,
        )
        # Far enough apart that putting the teabag in late is a sequence error rather
        # than a slip the resident caught straight away.
        for index, step_id in enumerate(["get_cup", "pour", "teabag_in_cup"])
    ]

    def states(seen: list[StepEvent]) -> dict[str, str]:
        found = classify_errors(seen, graph, session_id="out-of-order", ended=False)
        return step_states(graph, seen, found)

    assert states(events[:2])["teabag_in_cup"] == "omission"
    assert states(events)["teabag_in_cup"] == "done"
    assert states(events)["pour"] == "sequence"


def test_step_states_are_the_ones_the_task_map_draws() -> None:
    """`step_state` is for `web/src/live/TaskMap.tsx`: one state per step, and only
    the states it has a colour for."""
    union = re.search(r"type StepState = (.+)", TASK_MAP.read_text("utf-8"))

    assert union is not None
    assert set(re.findall(r"'([a-z]+)'", union.group(1))) == set(get_args(StepState))


def test_clock_plays_session_time_at_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    waited: list[float] = []

    async def fake_sleep(delay: float) -> None:
        waited.append(delay)

    monkeypatch.setattr(live.asyncio, "sleep", fake_sleep)

    async def play() -> None:
        clock = live._Clock(speed=2.0)
        for t in (1.0, 4.0, 3.0):  # the third is in the past: no waiting backwards
            await clock.wait_until(t)

    asyncio.run(play())

    assert waited == [0.5, 1.5, 0.0]


def test_speed_must_be_positive() -> None:
    async def first() -> dict[str, Any]:
        return await anext(session_messages(scenario_path(GOOD), speed=0.0))

    with pytest.raises(ValueError, match="speed"):
        asyncio.run(first())


def test_impossible_speed_is_turned_down() -> None:
    with TestClient(app) as client, pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/live?scenario={GOOD}&speed=0") as websocket:
            websocket.receive_json()

    assert closed.value.code == WS_POLICY_VIOLATION


@pytest.mark.parametrize("name", ["nope", "", "../tea_normal", "tea normal"])
def test_scenario_path_only_names_a_scenario(name: str) -> None:
    with pytest.raises(ReplayError):
        scenario_path(name)
