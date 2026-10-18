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
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    ObjectLabel,
    StepEvent,
    StepSource,
    TaskError,
    repo_root,
)
from routine_watch.demo import DEMO_RESIDENT
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

#: Pouring before the teabag goes in: the session whose error list heals, because the
#: dependency reported missing mid-session is done later on.
SEQUENCE = "tea_sequence_error"

#: The two recordings whose own verdict and whose effect on Mrs. K disagree (T236):
#: against its own history `tea_kettle_twice` flags and `tea_no_kettle` does not, while
#: her history, with the session now in it, reads them the other way round.
ONE_SIDED = ("tea_kettle_twice", FRAMES)

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
            {
                "id": step.id,
                "label": step.label,
                "deps": sorted(step.deps),
                "optional": step.optional,
            }
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


@pytest.mark.parametrize("scenario", [*ONE_SIDED, BAD, GOOD])
def test_session_end_says_what_the_dashboard_says(scenario: str) -> None:
    """The verdict a live session ends on is the resident's, the same reading
    `/residents` and `/alerts` give a nurse (T236).

    Judging the recording against the scenario's own history instead could say either
    thing the dashboard does not: "flagged" with an `alert_id` `/alerts` 404s on, so
    "View alert" dead-ends, or "nothing flagged" while her row has gone red.
    """
    end = played(scenario_path(scenario))[-1]
    with TestClient(app) as client:
        status = client.get(f"/residents/{DEMO_RESIDENT}").json()["status"]
        alert = client.get(f"/alerts/alert-{DEMO_RESIDENT}")

    assert end["flag"] == (status == "flagged")
    assert (end["alert_id"] is not None) == (alert.status_code == 200)
    assert end["alert_id"] in (None, f"alert-{DEMO_RESIDENT}")


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


def test_step_scenario_sends_synthetic_frames() -> None:
    """A scenario written at step level has no recorded frames, so the skeleton view
    gets made-up ones instead of staying empty the whole session: one every
    `1 / SYNTHETIC_FPS` seconds, from the start of the session to its last step."""
    events = load_scenario(scenario_path(BAD)).events
    frames = [CaptureFrame.model_validate(m["frame"]) for m in of_type(live_session(BAD), "frame")]

    assert [f.seq for f in frames] == list(range(len(frames)))
    assert frames[0].t == 0.0
    assert frames[-1].t == pytest.approx(max(event.t_end for event in events))
    gaps = {round(later.t - earlier.t, 6) for earlier, later in pairwise(frames)}
    assert gaps == {round(1.0 / live.SYNTHETIC_FPS, 6)}


def test_synthetic_frames_carry_a_skeleton_and_not_just_boxes() -> None:
    """The bug this is a regression for: every made-up frame had `poses=[]`, so the
    live skeleton view (SPEC section 10, step 3) drew labelled boxes and no body."""
    frames = [CaptureFrame.model_validate(m["frame"]) for m in of_type(live_session(BAD), "frame")]

    assert frames
    for frame in frames:
        assert len(frame.poses) == 1  # one person, so the session is not "assisted"
        assert len(frame.hands) == 1
        for landmark in [*frame.poses[0].landmarks, *frame.hands[0].landmarks]:
            assert 0.0 <= landmark.x <= 1.0
            assert 0.0 <= landmark.y <= 1.0


def test_the_synthetic_hand_travels_between_the_objects_of_the_steps() -> None:
    """A still skeleton is barely better than no skeleton: the hand has to be on the
    object of the step being done, and somewhere else between steps."""
    events = load_scenario(scenario_path(BAD)).events
    frames = [CaptureFrame.model_validate(m["frame"]) for m in of_type(live_session(BAD), "frame")]

    for event in events:
        middle = min(frames, key=lambda f: abs(f.t - (event.t_start + event.t_end) / 2.0))
        target = next(o for o in middle.objects if str(o.label) == str(event.objects[0]))
        assert _overlaps(_hand_box(middle), target.box), f"{event.step_id} at {middle.t}"

    places = {(f.hands[0].landmarks[0].x, f.hands[0].landmarks[0].y) for f in frames}
    assert len(places) > len(events)  # it moves between the steps, not only at them


def _hand_box(frame: CaptureFrame) -> BoundingBox:
    """The box the detector would put around the hand in this frame."""
    return next(found.box for found in frame.objects if found.label is ObjectLabel.HAND)


def _overlaps(one: BoundingBox, other: BoundingBox) -> bool:
    return (
        one.x1 <= other.x2 and other.x1 <= one.x2 and one.y1 <= other.y2 and other.y1 <= one.y2
    )


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
    for error in messages[-1]["errors"]:  # `session_end` carries a list of them
        TaskError.model_validate(error)
    assert {m["type"] for m in messages} <= {
        "session_start", "frame", "step", "step_state", "error", "session_end"
    }


# ------------------------------------------------------- the pipeline, and the clock


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_live_session_says_what_the_replay_says(path: Path) -> None:
    """A live replay and `scripts/e2e.sh` must never disagree about a recording: same
    steps, same errors at the end and the same score.

    Not the same flag: `session_end`'s is the resident's reading, over their own history
    with this session in it, and the recording's own is the offline replay's
    (`test_session_end_says_what_the_dashboard_says`, T236).
    """
    scenario = load_scenario(path)
    messages = played(path)
    result = run(scenario)

    assert [m["event"].step_id for m in of_type(messages, "step")] == list(
        scenario.expected.steps
    )
    want = Counter((e["type"], e["step"]) for e in result["errors"])
    sent = Counter((m["error"].type, m["error"].step_id) for m in of_type(messages, "error"))
    ended = Counter((error.type, error.step_id) for error in messages[-1]["errors"])
    assert sent >= want  # the stream also keeps what healed on the way
    assert ended == want  # the end is exactly the offline replay's reading
    assert messages[-1]["score"] == result["score"]


def test_each_error_is_sent_once() -> None:
    """Classifying every few seconds finds the same error again and again (its id is
    stable on purpose); the client hears about it once."""
    ids = [m["error"].error_id for m in of_type(played(scenario_path(BAD)), "error")]

    assert len(ids) == len(set(ids))


def test_session_end_carries_the_errors_the_session_ended_on() -> None:
    """A streamed error is provisional; `session_end`'s `errors` is the list to settle
    on, so the screen ends up showing the errors `expected.yaml` (and so
    `scripts/e2e.sh`) has for this recording rather than the gap that healed."""
    messages = live_session(SEQUENCE)

    assert reported(messages) == [("omission", "teabag_in_cup"), ("sequence", "pour")]
    assert [(e["type"], e["step_id"]) for e in messages[-1]["errors"]] == [("sequence", "pour")]


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
