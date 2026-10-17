"""The live session from a camera (SPEC section 16 decision B, section 10).

The acceptance case is that a camera and the pre-recorded fallback cannot disagree: the
same capture stream through `live_camera.camera_session_messages` and through
`live.session_messages` has to produce the same steps, the same errors, the same task
map and the same verdict, in the same order. That is checked over every recorded capture
stream in the repo - the one scenario written at frame level, and the recogniser's own
fixture clips, which are the same format (SPEC section 16, "single capture stream").

Nothing here needs a camera, MediaPipe, the detector weights or a network: the capture
process is driven with the fakes it already has (`FakeLandmarker`, `FakeDetector`), and
everything else is read back off a recording.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_recogniser import (
    CUP,
    KETTLE_BASE,
    KETTLE_CARRIED,
    KETTLE_TAP,
    SPOON_COUNTER,
    TEABAG_COUNTER,
    TEABAG_IN_CUP,
    Take,
    grip,
)

from routine_watch import live, live_camera
from routine_watch.capture import (
    DEFAULT_FPS,
    FakeLandmarker,
    Hand,
    Landmarks,
    frame_record,
    record_stream,
)
from routine_watch.contracts import (
    HAND_LANDMARK_COUNT,
    POSE_LANDMARK_COUNT,
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    Landmark,
    ObjectDetection,
    ObjectLabel,
    StepEvent,
    TaskError,
)
from routine_watch.detector import FakeDetector
from routine_watch.live import as_json, session_messages
from routine_watch.live_camera import camera_session_messages
from routine_watch.recogniser import recognise
from routine_watch.replay import ASSISTED_MIN_S, SCENARIOS_DIR, ReplayError
from routine_watch.tasks import TaskGraphError, load_task

#: The make-tea graph is immutable and cached, so every test shares one.
TEA = load_task("tea")

#: Fast enough that a recorded session replays inside a test.
FAST = 1000.0

#: Frames at the capture rate for as long as a second person has to stay before the
#: session counts as assisted (`replay.assisted_of`), and for a moment less than that.
ASSISTED_FRAMES = int(ASSISTED_MIN_S * DEFAULT_FPS) + 1
PASSING_FRAMES = int(ASSISTED_MIN_S * DEFAULT_FPS) - 1

#: Every recorded capture stream in the repo: the one scenario written at frame level,
#: and the recogniser's fixture clips.
CLIPS = Path(__file__).parent / "fixtures" / "recogniser"
RECORDINGS: dict[str, Path] = {
    "tea_no_kettle": SCENARIOS_DIR / "tea_no_kettle" / "frames.jsonl",
    **{
        name: CLIPS / f"{name}.jsonl"
        for name in ("fill_kettle", "teabag_in_cup", "pour", "stir", "barely_seen_teabag",
                     "make_tea")
    },
}


# ------------------------------------------------------------------------- the helpers


def load_frames(path: Path) -> list[CaptureFrame]:
    """One recording, read the way the pipeline reads a capture stream."""
    return [
        CaptureFrame.model_validate_json(line)
        for line in path.read_text("utf-8").splitlines()
        if line.strip()
    ]


def camera(
    frames: AsyncIterator[CaptureFrame] | Iterable[CaptureFrame], task: str = "tea"
) -> list[dict[str, Any]]:
    """Every message of one live camera session, as the generator yields it."""

    async def collect() -> list[dict[str, Any]]:
        return [message async for message in camera_session_messages(frames, task)]

    return asyncio.run(collect())


def replayed(scenario_dir: Path) -> list[dict[str, Any]]:
    """Every message of the same recording played back as the pre-recorded fallback."""

    async def collect() -> list[dict[str, Any]]:
        return [message async for message in session_messages(scenario_dir, speed=FAST)]

    return asyncio.run(collect())


def as_scenario(frames: Sequence[CaptureFrame], path: Path) -> Path:
    """These frames as a scenario directory, so a replay can play them.

    Only the frames matter: a replay reads the task graph, the frames and the resident's
    history out of a scenario, and a clip has no history. `expected.yaml` is here because
    `replay.load_scenario` insists on one, not because anything compares against it.
    """
    path.mkdir(parents=True)
    (path / "frames.jsonl").write_text(
        "".join(frame.model_dump_json() + "\n" for frame in frames), encoding="utf-8"
    )
    (path / "expected.yaml").write_text(
        yaml.safe_dump({"task": "tea", "steps": [], "errors": [], "flag": False}),
        encoding="utf-8",
    )
    return path


def of_type(messages: Sequence[dict[str, Any]], type_: str) -> list[dict[str, Any]]:
    return [message for message in messages if message["type"] == type_]


def without_frames(messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Everything a session says about the task: the steps, the errors, the map and the
    verdict. The frames themselves are compared separately, because a camera sends a
    step a beat after the frames it was read off rather than exactly on the last of them.
    """
    return [message for message in messages if message["type"] != "frame"]


def steps_in(messages: Sequence[dict[str, Any]]) -> list[str]:
    return [message["event"].step_id for message in of_type(messages, "step")]


def kinds_of(messages: Sequence[dict[str, Any]]) -> list[str]:
    return [message["type"] for message in messages]


def last_of(kinds: Sequence[str], type_: str) -> int:
    return max(index for index, kind in enumerate(kinds) if kind == type_)


def blank_frame(seq: int, t: float, session: str = "camera-1") -> CaptureFrame:
    """A record with nobody and nothing in it: the camera is on, the kitchen is empty."""
    return CaptureFrame(
        session_id=session, seq=seq, t=t, source=CaptureSource.CAMERA,
        poses=[], hands=[], objects=[],
    )


def crowded_frame(seq: int, t: float, people: int = 2) -> CaptureFrame:
    """A record with `people` people in it, built through the capture boundary itself."""
    person = [Landmark(x=0.5, y=0.5, z=0.0)] * POSE_LANDMARK_COUNT
    return frame_record(
        t, [person] * people, [], [], CaptureSource.CAMERA, session_id="helped-1", seq=seq
    )


def hand_on(where: BoundingBox) -> Hand:
    """A hand holding `where`: MediaPipe's twenty-one landmarks, all in the middle of it."""
    x, y = grip(where)
    return Hand(
        handedness="Right", score=0.9, landmarks=[Landmark(x=x, y=y, z=0.0)] * HAND_LANDMARK_COUNT
    )


def seen(label: str, where: BoundingBox) -> ObjectDetection:
    """One object the detector found, as sure of it as the fixtures are."""
    return ObjectDetection(label=ObjectLabel(label), confidence=0.9, box=where)


# ------------------------------------------------- the camera and the fallback agree


@pytest.mark.parametrize("name", list(RECORDINGS))
def test_a_camera_session_says_what_a_replay_of_it_says(name: str, tmp_path: Path) -> None:
    """The acceptance case: one recording, both paths, message for message.

    A camera session reads the steps off the frames as they arrive and a replay reads
    them off the whole file, so this is also what pins `live_camera._settled`: a step the
    camera sends early and the finished recording disagrees with would show up here.
    """
    frames = load_frames(RECORDINGS[name])
    recorded = SCENARIOS_DIR / name  # a real scenario plays from its own directory,
    scenario = recorded if recorded.is_dir() else as_scenario(frames, tmp_path / name)

    messages, fallback = camera(frames), replayed(scenario)

    assert without_frames(messages) == without_frames(fallback)
    assert of_type(messages, "frame") == of_type(fallback, "frame")
    assert messages[-1]["type"] == "session_end"


def test_the_map_starts_out_all_pending() -> None:
    """The task map is sent before anything has happened, so the dashboard can draw the
    task from the pipeline's data rather than from a mock of it."""
    first = camera(load_frames(RECORDINGS["make_tea"]))[0]

    assert first["type"] == "step_state"
    assert set(first["states"]) == set(TEA.step_ids)
    assert set(first["states"].values()) == {"pending"}


def test_steps_arrive_while_the_session_is_still_running() -> None:
    """The point of reading the frames as they arrive: the map fills in during the
    session, not after it (SPEC section 10, "in real time")."""
    kinds = kinds_of(camera(load_frames(RECORDINGS["make_tea"])))

    assert kinds.count("step") == len(TEA.step_ids) - 2  # milk and sugar are skipped
    assert kinds.index("step") < last_of(kinds, "frame")


def test_the_map_goes_red_while_the_session_is_still_running() -> None:
    """The same for errors: cold water is flagged before the tea is finished."""
    kinds = kinds_of(camera(load_frames(RECORDINGS["tea_no_kettle"])))

    assert kinds.index("error") < last_of(kinds, "frame")


def test_reading_the_frames_less_often_changes_only_when(monkeypatch: pytest.MonkeyPatch) -> None:
    """`REREAD_EVERY_S` is a cost, not a rule: reading the session once at the very end
    sends the same messages as reading it twice a second."""
    frames = load_frames(RECORDINGS["make_tea"])
    often = camera(frames)
    monkeypatch.setattr(live_camera, "REREAD_EVERY_S", 60.0)

    seldom = camera(frames)

    assert without_frames(seldom) == without_frames(often)


# ------------------------------------------------------ a step is sent once, and late


def two_handed_clip() -> list[CaptureFrame]:
    """One hand resting on the kettle while the other puts the teabag in the cup, and
    then the kettle carried off to the tap.

    The resting hand reads as `boil` for as long as the kettle stays where it is, and the
    moment it is carried off the whole contact is `fill_kettle` instead: the same frames,
    read a different way, which is what a live session must not have sent already. The
    second hand is what makes the trap reachable - it gives the session a step in the
    middle of that contact, so there is a `boil` with something after it.
    """
    counter = {"cup": CUP, "spoon": SPOON_COUNTER}
    sure = {"teabag": 0.95}  # so the teabag wins its frames over the hand on the kettle
    take = Take("two-handed")
    kettle_still = {**counter, "kettle": KETTLE_BASE}
    take.shot({**kettle_still, "teabag": TEABAG_COUNTER}, [grip(KETTLE_BASE)], repeat=2)
    # A hand on the teabag on the counter, so the teabag goes *into* the cup from here.
    take.shot(
        {**kettle_still, "teabag": TEABAG_COUNTER},
        [grip(KETTLE_BASE), grip(TEABAG_COUNTER)],
        confidence=sure,
    )
    take.shot(
        {**kettle_still, "teabag": TEABAG_IN_CUP},
        [grip(KETTLE_BASE), grip(TEABAG_IN_CUP)],
        confidence=sure,
        repeat=2,
    )
    take.shot({**kettle_still, "teabag": TEABAG_IN_CUP}, [grip(KETTLE_BASE)], confidence=sure)
    for where in (KETTLE_CARRIED, KETTLE_TAP, KETTLE_TAP):
        take.shot({**counter, "kettle": where, "teabag": TEABAG_IN_CUP}, [grip(where)],
                  confidence=sure)
    take.shot({**counter, "kettle": KETTLE_TAP, "teabag": TEABAG_IN_CUP}, confidence=sure)
    return take.frames


def test_a_step_the_frames_later_disown_is_never_sent() -> None:
    """Why a step waits for its contact to end. Read off the first few frames the
    recogniser proposes `boil`; read off the whole recording there is no `boil` at all,
    and the live session only ever sent what the recording says."""
    frames = two_handed_clip()
    session = frames[0].session_id
    early = recognise(frames[:6], TEA, session_id=session)
    whole = recognise(frames, TEA, session_id=session)

    messages = camera(frames)

    assert "boil" in [event.step_id for event in early]
    assert steps_in(messages) == [event.step_id for event in whole]
    assert "boil" not in steps_in(messages)
    assert [message["event"] for message in of_type(messages, "step")] == whole


def test_a_step_still_being_done_is_not_sent_yet() -> None:
    """A recording cut off mid-step: the step is the one the whole recording reads as,
    and it is sent when the stream ends rather than while the kettle is still in hand."""
    frames = load_frames(RECORDINGS["fill_kettle"])[:5]  # cut with the kettle at the tap
    whole = recognise(frames, TEA, session_id=frames[0].session_id)

    messages = camera(frames)
    kinds = kinds_of(messages)

    assert [message["event"] for message in of_type(messages, "step")] == whole
    assert steps_in(messages) == ["fill_kettle"]
    assert kinds.index("step") > last_of(kinds, "frame")


# ------------------------------------------------------------------------- the frames


def test_frames_are_sent_at_the_same_rate_as_a_replay() -> None:
    """The dashboard draws the same skeletons either way: `live`'s cap on frames per
    second of session time, applied a frame at a time instead of to a whole file."""
    recorded = [blank_frame(seq, seq / 30.0) for seq in range(90)]  # 3 s at 30 fps

    sent = [message["frame"] for message in of_type(camera(recorded), "frame")]

    assert sent == live._downsampled(recorded)
    assert len(sent) == 30


def test_every_message_is_a_contract() -> None:
    """Contracts forbid unknown fields, so validating every message as the socket would
    send it is also the privacy check: nothing here can carry an image or a clip (SPEC
    section 8, `test_contracts.py`)."""
    messages = [as_json(message) for message in camera(load_frames(RECORDINGS["make_tea"]))]

    for message in of_type(messages, "frame"):
        CaptureFrame.model_validate(message["frame"])
    for message in of_type(messages, "step"):
        StepEvent.model_validate(message["event"])
    for message in of_type(messages, "error"):
        TaskError.model_validate(message["error"])
    assert {message["type"] for message in messages} <= {
        "frame", "step", "step_state", "error", "session_end"
    }


# ----------------------------------------------------------------- what comes in, and out


def test_the_capture_process_feeds_a_live_session(tmp_path: Path) -> None:
    """Capture to live session, the whole camera path: a hand resting on the kettle,
    fifteen records a second, read as `boil`.

    `FakeLandmarker` and `FakeDetector` are what capture uses anywhere a camera, a
    MediaPipe bundle or detector weights would be needed, so this runs in CI.
    """
    out = tmp_path / "session.jsonl"
    images = ((seq / 15.0, None) for seq in range(25))  # the fakes never look at the image

    result = record_stream(
        images,
        out,
        landmarker=FakeLandmarker(Landmarks(hands=(hand_on(KETTLE_BASE),))),
        detector=FakeDetector([seen("kettle", KETTLE_BASE), seen("cup", CUP)]),
        source=CaptureSource.CAMERA,
        session_id="camera-1",
    )
    messages = camera(load_frames(out))

    assert result.frames == 25
    assert steps_in(messages) == ["boil"]
    assert messages[-1]["type"] == "session_end"
    assert messages[-1]["flag"] is False  # no prior sessions, so nothing to flag against
    assert messages[-1]["alert_id"] is None


def test_an_async_stream_reads_the_same_as_a_list() -> None:
    """A camera hands its frames over asynchronously; a recording off disk is a list.
    Both are the same session."""
    frames = load_frames(RECORDINGS["make_tea"])

    async def streamed() -> AsyncIterator[CaptureFrame]:
        for frame in frames:
            yield frame

    assert camera(streamed()) == camera(frames)


def test_a_session_with_two_people_in_frame_is_not_scored() -> None:
    """The verdict is `replay.score_session`'s, frames and all: someone who stays to help
    means the session was assisted, and an assisted session is left out of the resident's
    baseline rather than scored against it (SPEC section 7)."""
    helped = camera([crowded_frame(seq, seq / DEFAULT_FPS) for seq in range(ASSISTED_FRAMES)])
    alone = camera(
        [crowded_frame(seq, seq / DEFAULT_FPS, people=1) for seq in range(ASSISTED_FRAMES)]
    )

    assert helped[-1]["score"] == 0.0
    assert alone[-1]["score"] > 0.0  # the same session with nobody helping: scored, badly


def test_someone_passing_through_still_leaves_a_session_scored() -> None:
    """The other half of the same rule: a second person has to stay for `ASSISTED_MIN_S`
    before the session counts as assisted, so a passer-by does not quietly zero a
    resident's session (`replay.assisted_of`)."""
    passing = [crowded_frame(seq, seq / DEFAULT_FPS) for seq in range(PASSING_FRAMES)]
    after = [  # they move on; the resident is alone again for the rest of the session
        crowded_frame(seq, seq / DEFAULT_FPS, people=1)
        for seq in range(PASSING_FRAMES, ASSISTED_FRAMES * 2)
    ]

    assert camera(passing + after)[-1]["score"] > 0.0


def test_a_stream_with_no_frames_is_not_a_session() -> None:
    """A camera that saw nothing is not a session, which is what a replay says about a
    recording with nothing in it."""
    with pytest.raises(ReplayError, match="no records"):
        camera([])


def test_an_unknown_task_is_turned_down() -> None:
    with pytest.raises(TaskGraphError):
        camera(load_frames(RECORDINGS["make_tea"]), task="making-toast")
